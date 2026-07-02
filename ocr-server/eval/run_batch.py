"""run_batch — POST each active sample to the live OCR server, capture results.

Reads manifest (active samples), POSTs each image/PDF to /ocr/extract with
templateMode=unstructured + documentType=invoice_statement (the free-path
trigger: `not region_list and _is_unstructured_template`, main.py:2952-2955),
reads back `resp["document_fields"]`, records extractionSource (free vs
fallback), and writes per-sample results under runs/<ts>/.

Page policy (corrected vs plan): the server is page-0 scoped even for multi-page
PDFs (verified: 5.pdf 22pp -> 6 rows == page-0 GT). So we RECORD pageCount and
flag multiPage, but do NOT hard-fail on it.

Measurement-only: never modifies operational logic or public/data; writes only
under eval/runs/.

CLI:
    python eval/run_batch.py                 # new run -> runs/<ts>/
    python eval/run_batch.py --resume <ts>   # reuse run dir, skip done samples
    python eval/run_batch.py --only 5.pdf    # subset
    python eval/run_batch.py --workers 4 --server http://127.0.0.1:9099
"""

from __future__ import annotations

import argparse
import base64
import datetime
import json
import os
import platform
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

import contract as C
from build_manifest import build_manifest


def _save_processed(data_url: str, out_path: str) -> None:
    """Decode the response's 'data:image/jpeg;base64,...' into a JPEG file.

    This is the EXACT image OCR ran on (main.py processed_image == ocr_img, kept
    in sync through all rotate/deskew/unwarp branches), so ocr_lines_raw bboxes
    line up with it — the faithful crop source for fine-tune, no re-derivation.
    Best-effort: a failure here never breaks the run.
    """
    try:
        b64 = data_url.split(",", 1)[1] if "," in data_url else data_url
        with open(out_path, "wb") as fh:
            fh.write(base64.b64decode(b64))
    except Exception as exc:
        print(f"  [processed save failed] {out_path}: {exc}")


DEFAULT_SERVER = "http://127.0.0.1:9099"
EXTRACT_PATH = "/ocr/extract"
_REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def _code_versions(results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Version stamp so a metrics change can be traced to code vs model/data
    (the 035-drift problem: was it the parser edit or the GPU/detector swap?).

    Client-capturable: git rev of the code (= parser+eval version), dirty flag
    (uncommitted => not reproducible), python/platform, and the server-reported
    preprocess policy version. The OCR engine/detector model is server-side and
    not exposed in the response yet — recorded as null until the server emits it.
    """
    def _git(*a: str) -> str:
        try:
            return subprocess.run(["git", *a], cwd=_REPO, capture_output=True,
                                  text=True, timeout=5).stdout.strip()
        except Exception:
            return ""
    policy = None
    for r in results or []:
        pv = (r.get("preprocess") or {}).get("policyVersion")
        if pv:
            policy = pv
            break
    return {
        "codeRevision": _git("rev-parse", "--short", "HEAD") or "unknown",
        "codeDirty": bool(_git("status", "--porcelain")),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "preprocessPolicyVersion": policy,
        "ocrEngine": None,        # server-side; not exposed in response yet
        "detectorProfile": None,  # server-side; not exposed in response yet
    }
MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".pdf": "application/pdf", ".tif": "image/tiff", ".tiff": "image/tiff",
}


def _page_count(path: str) -> int | None:
    """PDF page count via fitz; None for non-PDF or if fitz unavailable."""
    if not path.lower().endswith(".pdf"):
        return 1
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        try:
            return doc.page_count
        finally:
            doc.close()
    except Exception:
        return None


def _classify_source(raw: str | None) -> str:
    if not raw:
        return "unknown"
    return "free" if "free" in raw.lower() else "fallback"


def run_one(sample: dict[str, Any], server: str, timeout: float) -> dict[str, Any]:
    """POST one sample. Errors are caught and recorded (isolation), never raised."""
    src = sample["sourceFile"]
    img_path = os.path.normpath(os.path.join(C.HERE, sample["image"]))
    ext = os.path.splitext(img_path)[1].lower()
    page_count = _page_count(img_path)
    rec: dict[str, Any] = {
        "sourceFile": src,
        "imagePath": os.path.relpath(img_path, C.HERE),
        "pageCount": page_count,
        "multiPage": bool(page_count and page_count > 1),
        "status": "error",
        "httpStatus": None,
        "extractionSourceRaw": None,
        "extractionPath": "unknown",
        "rowCount": None,
        "tableDetected": None,
        "documentFields": None,
        # Preprocessing telemetry (orientation/deskew) captured but NOT analyzed yet.
        # Cheap insurance: lets a future "accuracy by rotation" slice run without re-OCR.
        "preprocess": None,
        "clientMs": None,
        "error": None,
    }
    t0 = time.time()
    try:
        with open(img_path, "rb") as fh:
            resp = requests.post(
                server.rstrip("/") + EXTRACT_PATH,
                files={"file": (os.path.basename(img_path), fh, MIME.get(ext, "application/octet-stream"))},
                data={"documentType": "invoice_statement", "templateMode": "unstructured",
                      "captureOcrSnapshot": "1"},  # ask server to return free-extractor input envelope
                timeout=timeout,
            )
        rec["clientMs"] = round((time.time() - t0) * 1000.0, 1)
        rec["httpStatus"] = resp.status_code
        if resp.status_code != 200:
            rec["error"] = f"HTTP {resp.status_code}: {resp.text[:300]}"
            return rec
        body = resp.json()
        df = body.get("document_fields")
        if not isinstance(df, dict):
            rec["error"] = "response missing document_fields object"
            return rec
        tm = df.get("tableMeta") or {}
        rec["extractionSourceRaw"] = tm.get("extractionSource")
        rec["extractionPath"] = _classify_source(rec["extractionSourceRaw"])
        rec["rowCount"] = df.get("rowCount")
        rec["tableDetected"] = df.get("tableDetected")
        rec["documentFields"] = df
        # Keep only the preprocess subtree (orientation+deskew); drop the rest of
        # extract_debug to stay small. Source: extract_debug.preprocess (verified live).
        rec["preprocess"] = (body.get("extract_debug") or {}).get("preprocess")
        # Free-extractor input envelope for offline parser replay. Stashed under a
        # private key here; run_batch pops it to runs/<ts>/snapshots/ so rec.json
        # (the checker-validated result) keeps its exact schema. None if free path
        # not taken (e.g. fallback) — pop tolerates absence.
        rec["_ocrSnapshot"] = body.get("ocr_snapshot")
        # The EXACT preprocessed image OCR ran on (bbox coordinate space). Stashed
        # private; run_batch pops it to runs/<ts>/processed/<src>.jpg so the scored
        # rec.json schema is untouched. Source of fine-tune crops (no re-derivation).
        rec["_processedImage"] = body.get("processed_image")
        rec["status"] = "ok"
    except Exception as exc:  # network/parse/etc -> isolate
        rec["clientMs"] = round((time.time() - t0) * 1000.0, 1)
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def run_one_canned(sample: dict[str, Any]) -> dict[str, Any]:
    """Canned sample (⓲): the result is the recorded rec envelope — no server.

    Lets a thin/DB testset run with no image and no live OCR. The rec was written
    verbatim from a real run, so it already has documentFields/extractionPath/
    pageCount/multiPage/status.
    """
    src = sample["sourceFile"]
    rec_path = os.path.normpath(os.path.join(C.HERE, sample["rec"]))
    try:
        rec = json.load(open(rec_path, encoding="utf-8"))
    except Exception as exc:
        return {"sourceFile": src, "status": "error", "httpStatus": None,
                "extractionPath": "unknown", "pageCount": None, "documentFields": None,
                "error": f"canned rec unreadable: {exc}"}
    rec["sourceFile"] = src
    rec["canned"] = True
    rec.setdefault("status", "ok")
    return rec


def run_batch(
    server: str = DEFAULT_SERVER,
    workers: int = 4,
    only: list[str] | None = None,
    resume_ts: str | None = None,
    timeout: float = 600.0,  # 300→600: 로컬 CPU에서 28행 무거운 장(1-2 등)이 변동성으로 300s
    # 초과해 드롭→run 회귀 노이즈. GPU에선 무관. 측정 안정성용(정확도 게이트 아님).
    testset: str = C.DEFAULT_TESTSET,
) -> dict[str, Any]:
    manifest = build_manifest(testset)
    actives = [s for s in manifest["samples"] if s["status"] in ("active", "canned")]
    if only:
        actives = [s for s in actives if s["sourceFile"] in set(only)]

    ts = resume_ts or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(C.RUNS_DIR, ts)
    samples_dir = os.path.join(run_dir, "samples")
    os.makedirs(samples_dir, exist_ok=True)
    snapshots_dir = os.path.join(run_dir, "snapshots")  # sidecar: free-extractor input for replay (NOT scored)
    os.makedirs(snapshots_dir, exist_ok=True)
    processed_dir = os.path.join(run_dir, "processed")  # sidecar: exact OCR-input image (bbox space) for crop extraction
    os.makedirs(processed_dir, exist_ok=True)

    todo = []
    skipped = []
    for s in actives:
        out = os.path.join(samples_dir, s["sourceFile"] + ".json")
        if resume_ts and os.path.isfile(out):
            try:
                if json.load(open(out, encoding="utf-8")).get("status") == "ok":
                    skipped.append(s["sourceFile"])
                    continue
            except Exception:
                pass
        todo.append(s)

    def dispatch(s: dict[str, Any]) -> dict[str, Any]:
        return run_one_canned(s) if s["status"] == "canned" else run_one(s, server, timeout)

    results: list[dict[str, Any]] = []
    total = len(todo)   # 진행 카운터용 총 대상 수
    done = 0            # 완료 순서대로 증가(메인 스레드에서만 집계 → 스레드 안전)

    # 고해상(대용량) 이미지는 동시에 처리하면 RAM(16GB) 폭증→스왑→시스템 멈춤/타임아웃.
    # 크기로 분리: 일반은 병렬(빠름), 고해상은 1장씩(박스 독점)으로 돌려 멈춤/ERR 제거.
    HEAVY_BYTES = 2 * 1024 * 1024   # 2MB 초과 = 고해상 위험군(측정상 _1.1.jpg 계열 123장)

    def _is_heavy(s: dict[str, Any]) -> bool:
        p = s.get("image")
        try:
            return bool(p) and os.path.getsize(p) > HEAVY_BYTES
        except OSError:
            return False

    todo_light = [s for s in todo if not _is_heavy(s)]
    todo_heavy = [s for s in todo if _is_heavy(s)]

    def _run_pass(items: list[dict[str, Any]], w: int, label: str) -> None:
        nonlocal done
        if not items:
            return
        print(f"  == {label}: {len(items)}장, 동시 {w} ==")
        with ThreadPoolExecutor(max_workers=max(1, w)) as ex:
            futs = {ex.submit(dispatch, s): s for s in items}
            for fut in as_completed(futs):
                rec = fut.result()
                # Pop sidecars BEFORE writing rec.json so the scored result keeps its schema.
                snap = rec.pop("_ocrSnapshot", None)
                proc = rec.pop("_processedImage", None)
                out = os.path.join(samples_dir, rec["sourceFile"] + ".json")
                with open(out, "w", encoding="utf-8") as fh:
                    json.dump(rec, fh, ensure_ascii=False, indent=2)
                    fh.write("\n")
                if snap:
                    with open(os.path.join(snapshots_dir, rec["sourceFile"] + ".json"),
                              "w", encoding="utf-8") as sfh:
                        json.dump(snap, sfh, ensure_ascii=False)
                        sfh.write("\n")
                if proc:
                    _save_processed(proc, os.path.join(processed_dir, rec["sourceFile"] + ".jpg"))
                done += 1
                flag = "OK " if rec["status"] == "ok" else "ERR"
                print(
                    f"  [{done:>4}/{total}] {flag} {rec['sourceFile']:<8} http={rec['httpStatus']} "
                    f"path={rec['extractionPath']:<8} rows={rec['rowCount']} "
                    f"pages={rec['pageCount']} {rec['clientMs']}ms"
                    + (f"  !! {rec['error']}" if rec["error"] else "")
                )
                results.append(rec)

    print(f"run {ts}: {len(todo)} to run ({len(todo_light)} 일반 + {len(todo_heavy)} 고해상), "
          f"{len(skipped)} resumed-skip, testset={testset}, mode={manifest['runMode']}, server={server}")
    _run_pass(todo_light, workers, "일반(병렬)")     # 일반 이미지: 병렬로 빠르게
    _run_pass(todo_heavy, 1, "고해상(1장씩·독점)")   # 고해상: 1장씩 → RAM 안전, 멈춤 없음

    # merge resumed-skip records into the summary view
    for src in skipped:
        try:
            results.append(json.load(open(os.path.join(samples_dir, src + ".json"), encoding="utf-8")))
        except Exception:
            pass

    summary = {
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "error": sum(1 for r in results if r["status"] != "ok"),
        "free": sum(1 for r in results if r["extractionPath"] == "free"),
        "fallback": sum(1 for r in results if r["extractionPath"] == "fallback"),
        "multiPage": sorted(r["sourceFile"] for r in results if r.get("multiPage")),
    }
    run_meta = {
        "schemaVersion": "eval-run.v1",
        "timestamp": ts,
        "testset": testset,
        "kind": manifest["kind"],
        "runMode": manifest["runMode"],
        "serverUrl": server,
        "extractPath": EXTRACT_PATH,
        "request": {"documentType": "invoice_statement", "templateMode": "unstructured"},
        "versions": _code_versions(results),
        "manifestCounts": manifest["counts"],
        "activeCount": len(actives),
        "ran": [r["sourceFile"] for r in results],
        "summary": summary,
    }
    with open(os.path.join(run_dir, "run_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(run_meta, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"\nrun_dir: {run_dir}")
    print(f"summary: {summary}")
    return {"runDir": run_dir, "ts": ts, "meta": run_meta, "results": results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default=DEFAULT_SERVER)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--resume", dest="resume_ts", default=None)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    args = ap.parse_args()
    out = run_batch(
        server=args.server, workers=args.workers, only=args.only,
        resume_ts=args.resume_ts, timeout=args.timeout, testset=args.testset,
    )
    return 0 if out["meta"]["summary"]["error"] == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
