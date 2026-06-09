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
import datetime
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

import contract as C
from build_manifest import build_manifest

DEFAULT_SERVER = "http://127.0.0.1:9099"
EXTRACT_PATH = "/ocr/extract"
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
                data={"documentType": "invoice_statement", "templateMode": "unstructured"},
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
        rec["status"] = "ok"
    except Exception as exc:  # network/parse/etc -> isolate
        rec["clientMs"] = round((time.time() - t0) * 1000.0, 1)
        rec["error"] = f"{type(exc).__name__}: {exc}"
    return rec


def run_batch(
    server: str = DEFAULT_SERVER,
    workers: int = 4,
    only: list[str] | None = None,
    resume_ts: str | None = None,
    timeout: float = 300.0,
) -> dict[str, Any]:
    manifest = build_manifest()
    actives = [s for s in manifest["samples"] if s["status"] == "active"]
    if only:
        actives = [s for s in actives if s["sourceFile"] in set(only)]

    ts = resume_ts or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(C.RUNS_DIR, ts)
    samples_dir = os.path.join(run_dir, "samples")
    os.makedirs(samples_dir, exist_ok=True)

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

    print(f"run {ts}: {len(todo)} to run, {len(skipped)} resumed-skip, server={server}")
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(run_one, s, server, timeout): s for s in todo}
        for fut in as_completed(futs):
            rec = fut.result()
            out = os.path.join(samples_dir, rec["sourceFile"] + ".json")
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            flag = "OK " if rec["status"] == "ok" else "ERR"
            print(
                f"  {flag} {rec['sourceFile']:<8} http={rec['httpStatus']} "
                f"path={rec['extractionPath']:<8} rows={rec['rowCount']} "
                f"pages={rec['pageCount']} {rec['clientMs']}ms"
                + (f"  !! {rec['error']}" if rec["error"] else "")
            )
            results.append(rec)

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
        "serverUrl": server,
        "extractPath": EXTRACT_PATH,
        "request": {"documentType": "invoice_statement", "templateMode": "unstructured"},
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
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()
    out = run_batch(
        server=args.server, workers=args.workers, only=args.only,
        resume_ts=args.resume_ts, timeout=args.timeout,
    )
    return 0 if out["meta"]["summary"]["error"] == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
