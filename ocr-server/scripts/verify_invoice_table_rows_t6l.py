"""T-6l invoice_statement GT rowCount / row alignment verifier.

The invoice_statement ground_truth.json currently stores document-level
rowCount/firstRowPreview, not full GT tableRows. This script still reports that
explicitly, compares OCR tableRows to GT rowCount, and uses conservative anchor
matching when manual anchors are available.

Default mode:
  - tries to start a temporary backend and call /ocr/extract for all 7 samples
  - falls back to stored/cached limitations in the report if API collection fails

Usage:
  cd d:/Free_Vue/OCR/ocr-server
  python scripts/verify_invoice_table_rows_t6l.py
  python scripts/verify_invoice_table_rows_t6l.py --api-url http://127.0.0.1:8124
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore[assignment]


SERVER_ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = SERVER_ROOT.parent
FRONTEND_ROOT = OCR_ROOT / "mysuit-ocr"
TESTSET_DIR = FRONTEND_ROOT / "public" / "data" / "testsets" / "invoice_statement"
MANIFEST_PATH = TESTSET_DIR / "manifest.json"
GT_PATH = TESTSET_DIR / "ground_truth.json"
REPORT_DIR = TESTSET_DIR / "reports"
MD_REPORT_PATH = REPORT_DIR / "T6l_gt_row_alignment_report_20260513.md"
JSON_REPORT_PATH = REPORT_DIR / "T6l_gt_row_alignment_report_20260513.json"

SAMPLES = ["1.jpg", "2.pdf", "3.pdf", "4.pdf", "5.pdf", "6.pdf", "7.pdf"]

# Captured by the first T-6l API baseline run before row-only extractor
# filtering was applied in this task.
BASELINE_OCR_ROW_COUNTS = {
    "1.jpg": 29,
    "2.pdf": 2,
    "3.pdf": 1,
    "4.pdf": 3,
    "5.pdf": 6,
    "6.pdf": 5,
    "7.pdf": 1,
}

# Manual anchors are intentionally sparse. They are used only for row identity
# analysis, not for value mapping scoring.
MANUAL_GT_ANCHORS: dict[str, list[dict[str, str]]] = {
    "5.pdf": [
        {"itemName": "노루모에프내복액75ML", "itemCode": "NRFS75M"},
        {"itemName": "노루모듀얼액션현탁액4P", "itemCode": "NRDA4P"},
        {"itemName": "나프록센나트륨정10T100", "itemCode": "NPRT10T"},
        {"itemName": "노루모에스산15P", "itemCode": "NASP15P"},
        {"itemName": "노루모에이스산250G캔", "itemCode": "INAP250G"},
        {"itemName": "두피나액30ML", "itemCode": "DPNL30M"},
    ],
    "6.pdf": [
        {"rowIndex": "1", "itemCode": "ATT100T", "itemName": "알코텔정100T", "quantity": "10", "lotNo": "24001", "expiryDate": "270305"},
        {"rowIndex": "2", "itemCode": "ATGT30T", "itemName": "액티글리정30T", "quantity": "10", "lotNo": "23001", "expiryDate": "260403"},
        {"rowIndex": "3", "itemCode": "OLGT30T", "itemName": "올고탄정10MG30T", "quantity": "30", "lotNo": "23001", "expiryDate": "260809"},
        {"rowIndex": "4", "itemCode": "ASZT28T", "itemName": "에소시움정20MG28T", "quantity": "5", "lotNo": "T17322003", "expiryDate": "251213"},
        {"rowIndex": "5", "itemCode": "ALG30P", "itemName": "알드린현탁액1.5G30P", "quantity": "0"},
        {"rowIndex": "6", "itemCode": "ANDC300C", "itemName": "앤디락생캡슬300C", "quantity": "0"},
    ],
    "7.pdf": [
        {"itemName": "클리마토플란정", "serialLotComposite": "0350623-231024-260811", "unit": "BOX", "quantity": "1,000"},
    ],
}


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.upper()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[()\[\]{}<>,./\\:_\-|·ㆍ'\"`~!@#$%^&*+=?]", "", text)
    return text


def normalize_digits(value: Any) -> str:
    return re.sub(r"\D", "", "" if value is None else str(value))


def row_anchor(row: dict[str, Any]) -> dict[str, str]:
    def get(key: str) -> str:
        value = row.get(key, "")
        return "" if value is None else str(value)

    serial_lot = get("serialLotComposite") or get("serialLot") or get("serialNo") or get("lotNo")
    mfg_exp = get("manufacturingExpiryComposite") or " ".join(
        v for v in [get("manufacturingNo"), get("expiryDate")] if v
    )
    return {
        "rowIndex": get("rowIndex"),
        "itemCode": get("itemCode"),
        "itemName": get("itemName"),
        "lotNo": get("lotNo"),
        "serialLotComposite": serial_lot,
        "manufacturingNo": get("manufacturingNo"),
        "manufacturingExpiryComposite": mfg_exp,
        "expiryDate": get("expiryDate"),
        "quantity": get("quantity"),
        "amount": get("amount"),
        "supplyAmount": get("supplyAmount"),
        "insuranceCode": get("insuranceCode"),
        "raw": get("_rawText"),
    }


def anchor_summary(row: dict[str, Any]) -> str:
    a = row_anchor(row)
    parts = []
    for key in ["rowIndex", "itemCode", "itemName", "lotNo", "serialLotComposite", "manufacturingNo", "expiryDate", "quantity", "amount", "supplyAmount", "insuranceCode"]:
        if a.get(key):
            parts.append(f"{key}={a[key]}")
    return "; ".join(parts) or a.get("raw", "")[:80]


def similarity(gt: dict[str, str], ocr: dict[str, Any], order_penalty: float = 0.0) -> tuple[float, list[str]]:
    oa = row_anchor(ocr)
    score = 0.0
    reasons: list[str] = []

    for key, weight in [("itemCode", 5), ("insuranceCode", 4), ("lotNo", 4), ("manufacturingNo", 4), ("expiryDate", 4)]:
        gv = normalize_text(gt.get(key))
        ov = normalize_text(oa.get(key))
        if gv and ov and gv == ov:
            score += weight
            reasons.append(f"{key}:exact")

    gt_serial = normalize_text(gt.get("serialLotComposite") or gt.get("serialLot") or gt.get("serialNo"))
    ocr_serial = normalize_text(oa.get("serialLotComposite"))
    if gt_serial and ocr_serial and (gt_serial == ocr_serial or gt_serial in ocr_serial or ocr_serial in gt_serial):
        score += 4
        reasons.append("serialLot:match")

    gn = normalize_text(gt.get("itemName"))
    on = normalize_text(oa.get("itemName") or oa.get("raw"))
    if gn and on:
        if gn == on or gn in on or on in gn:
            score += 4
            reasons.append("itemName:strong")
        else:
            common = len(set(gn) & set(on))
            denom = max(len(set(gn)), 1)
            if common / denom >= 0.55:
                score += 2
                reasons.append("itemName:fuzzy")

    for key, weight in [("quantity", 2), ("amount", 2), ("supplyAmount", 2)]:
        gv = normalize_digits(gt.get(key))
        ov = normalize_digits(oa.get(key))
        if gv and ov and gv == ov:
            score += weight
            reasons.append(f"{key}:digits")

    score -= order_penalty
    return score, reasons


def align_rows(gt_rows: list[dict[str, str]], ocr_rows: list[dict[str, Any]]) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    used_ocr: set[int] = set()
    for gi, gt in enumerate(gt_rows):
        best: tuple[float, int, list[str]] | None = None
        for oi, ocr in enumerate(ocr_rows):
            if oi in used_ocr:
                continue
            order_penalty = min(abs(gi - oi) * 0.15, 1.5)
            score, reasons = similarity(gt, ocr, order_penalty)
            if best is None or score > best[0]:
                best = (score, oi, reasons)
        if best and best[0] >= 3.5:
            status = "matched" if best[0] >= 5 else "low_confidence_match"
            used_ocr.add(best[1])
            matches.append({
                "gtIndex": gi + 1,
                "ocrIndex": best[1] + 1,
                "score": round(best[0], 2),
                "status": status,
                "reasons": best[2],
                "gt": gt,
                "ocr": row_anchor(ocr_rows[best[1]]),
            })
        else:
            matches.append({
                "gtIndex": gi + 1,
                "ocrIndex": None,
                "score": round(best[0], 2) if best else 0,
                "status": "missing_gt_row",
                "reasons": best[2] if best else [],
                "gt": gt,
                "ocr": None,
            })

    extra = [
        {"ocrIndex": oi + 1, "ocr": row_anchor(row)}
        for oi, row in enumerate(ocr_rows)
        if oi not in used_ocr
    ]
    return {
        "matches": matches,
        "matched": sum(1 for m in matches if m["status"] == "matched"),
        "lowConfidence": sum(1 for m in matches if m["status"] == "low_confidence_match"),
        "missingGtRows": [m for m in matches if m["status"] == "missing_gt_row"],
        "extraOcrRows": extra,
    }


def get_manifest_expected(filename: str) -> dict[str, list[str]]:
    manifest = load_json(MANIFEST_PATH, {})
    for item in manifest.get("items", []):
        if item.get("filename") == filename:
            tec = (((item.get("invoiceProfile") or {}).get("tableExpectedColumns")) or {})
            return {
                "required": list(tec.get("required") or []),
                "optional": list(tec.get("optional") or []),
                "display": list(tec.get("display") or []),
            }
    return {"required": [], "optional": [], "display": []}


def get_gt_info(filename: str) -> dict[str, Any]:
    gt = load_json(GT_PATH, {})
    entry = gt.get(filename, {}) if isinstance(gt, dict) else {}
    doc = entry.get("documentFields") or {}
    table_rows = doc.get("tableRows") or entry.get("tableRows") or []
    if not isinstance(table_rows, list):
        table_rows = []
    row_count_raw = doc.get("rowCount") or entry.get("rowCount")
    try:
        gt_count = int(str(row_count_raw))
    except Exception:
        gt_count = None
    return {
        "hasGtEntry": bool(entry),
        "hasGtTableRows": bool(table_rows),
        "gtRowCount": gt_count,
        "firstRowPreview": doc.get("firstRowPreview", ""),
        "gtRows": table_rows,
        "manualRows": MANUAL_GT_ANCHORS.get(filename, []),
    }


def start_server(port: int) -> subprocess.Popen[str]:
    python = SERVER_ROOT / ".venv" / "Scripts" / "python.exe"
    if not python.exists():
        python = Path(sys.executable)
    return subprocess.Popen(
        [str(python), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(SERVER_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def wait_for_server(api_url: str, seconds: int = 20) -> bool:
    if requests is None:
        return False
    for _ in range(seconds):
        try:
            r = requests.get(api_url.rstrip("/") + "/docs", timeout=1.5)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def call_api(api_url: str, filename: str, timeout: int) -> dict[str, Any]:
    if requests is None:
        return {"ok": False, "error": "requests unavailable"}
    path = TESTSET_DIR / filename
    expected = get_manifest_expected(filename)
    try:
        with path.open("rb") as f:
            r = requests.post(
                api_url.rstrip("/") + "/ocr/extract",
                files={"file": (filename, f, "application/octet-stream")},
                data={"tableExpectedColumns": json.dumps(expected, ensure_ascii=False)},
                timeout=timeout,
            )
        if r.status_code >= 400:
            return {"ok": False, "status": r.status_code, "error": r.text[:1000]}
        payload = r.json()
        df = payload.get("document_fields") or payload.get("documentFields") or {}
        debug = (payload.get("extract_debug") or {}).get("invoice_statement") or {}
        table_debug = (debug.get("table") or {}).get("tableDebug") or df.get("tableDebug") or {}
        rows = df.get("tableRows") or []
        if not isinstance(rows, list):
            rows = []
        meta = df.get("tableMeta") or {}
        return {
            "ok": True,
            "status": r.status_code,
            "docType": payload.get("doc_type"),
            "rows": [row for row in rows if isinstance(row, dict)],
            "tableMeta": meta if isinstance(meta, dict) else {},
            "tableDebug": table_debug if isinstance(table_debug, dict) else {},
        }
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}


def row_count_status(gt_count: int | None, ocr_count: int | None) -> str:
    if gt_count is None:
        return "unknown_gt"
    if ocr_count is None:
        return "no_ocr"
    if gt_count == ocr_count:
        return "exact"
    return "short" if ocr_count < gt_count else "over"


def summarize_rejections(table_debug: dict[str, Any]) -> dict[str, int]:
    rejected = table_debug.get("rejectedRows")
    if not isinstance(rejected, list):
        return {}
    return dict(Counter(str(r.get("reason", "unknown")) for r in rejected if isinstance(r, dict)))


def analyze(api_url: str | None, timeout: int) -> dict[str, Any]:
    samples: dict[str, Any] = {}
    for filename in SAMPLES:
        gt = get_gt_info(filename)
        api_result = call_api(api_url, filename, timeout) if api_url else {"ok": False, "error": "api_url not provided"}
        rows = api_result.get("rows", []) if api_result.get("ok") else []
        ocr_count = len(rows) if api_result.get("ok") else None
        gt_rows_for_alignment = gt["gtRows"] or gt["manualRows"]
        alignment = align_rows(gt_rows_for_alignment, rows) if gt_rows_for_alignment and rows else {
            "matches": [],
            "matched": 0,
            "lowConfidence": 0,
            "missingGtRows": [],
            "extraOcrRows": [{"ocrIndex": idx + 1, "ocr": row_anchor(row)} for idx, row in enumerate(rows)],
        }
        if gt_rows_for_alignment and not rows:
            alignment["missingGtRows"] = [
                {"gtIndex": idx + 1, "status": "missing_gt_row", "gt": row}
                for idx, row in enumerate(gt_rows_for_alignment)
            ]
        samples[filename] = {
            "gt": gt,
            "expected": get_manifest_expected(filename),
            "collection": {
                "ok": bool(api_result.get("ok")),
                "status": api_result.get("status"),
                "error": api_result.get("error", ""),
                "docType": api_result.get("docType"),
            },
            "ocrBeforeRowCount": BASELINE_OCR_ROW_COUNTS.get(filename),
            "ocrRowCount": ocr_count,
            "rowCountStatus": row_count_status(gt["gtRowCount"], ocr_count),
            "ocrRows": [row_anchor(row) for row in rows],
            "ocrAnchorSummary": [anchor_summary(row) for row in rows[:12]],
            "tableMeta": api_result.get("tableMeta", {}) if api_result.get("ok") else {},
            "tableDebugSummary": {
                "extractionSource": (api_result.get("tableMeta", {}) or {}).get("extractionSource"),
                "tableBoundsUsed": (api_result.get("tableMeta", {}) or {}).get("tableBoundsUsed"),
                "expectedColumnsUsed": (api_result.get("tableMeta", {}) or {}).get("expectedColumnsUsed"),
                "rejectedRows": summarize_rejections(api_result.get("tableDebug", {}) or {}),
                "rowEndReason": (api_result.get("tableDebug", {}) or {}).get("rowEndReason"),
                "fallbackReason": (api_result.get("tableDebug", {}) or {}).get("fallbackReason"),
            },
            "alignment": alignment,
        }
    return {
        "task": "T-6l",
        "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "apiUrl": api_url or "",
        "gtTableRowsAvailable": {
            filename: bool(get_gt_info(filename)["hasGtTableRows"])
            for filename in SAMPLES
        },
        "samples": samples,
    }


def compact(value: Any, max_len: int = 130) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    text = text.replace("\n", " ").replace("|", "\\|")
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def render_report(data: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# T-6l GT tableRows 기준 rowCount / row alignment 리포트\n")
    lines.append("## 1. 데이터 소스")
    lines.append(f"- API: {data.get('apiUrl') or '미사용/실패'}")
    lines.append(f"- GT: `{GT_PATH}`")
    lines.append("- GT tableRows 배열: 7개 샘플 모두 저장되어 있지 않음")
    lines.append("- 따라서 GT rowCount와 수동/문서 기반 anchor가 있는 샘플만 row alignment를 보조 분석함")
    lines.append("")

    lines.append("## 2. GT tableRows 구조 확인")
    lines.append("| 샘플 | GT entry | GT tableRows | GT rowCount | firstRowPreview | manual anchors |")
    lines.append("|---|---|---|---:|---|---:|")
    for filename in SAMPLES:
        gt = data["samples"][filename]["gt"]
        lines.append(
            f"| {filename} | {gt['hasGtEntry']} | {gt['hasGtTableRows']} | {gt['gtRowCount'] if gt['gtRowCount'] is not None else '-'} | "
            f"{compact(gt.get('firstRowPreview'))} | {len(gt.get('manualRows') or [])} |"
        )
    lines.append("")

    lines.append("## 3. 샘플별 rowCount before/after")
    lines.append("- OCR before는 T-6l 시작 시점의 API baseline 실행값이다.")
    lines.append("| 샘플 | GT rowCount | OCR before | OCR after | 상태 | 비고 |")
    lines.append("|---|---:|---:|---:|---|---|")
    for filename in SAMPLES:
        s = data["samples"][filename]
        gt_count = s["gt"]["gtRowCount"]
        after = s["ocrRowCount"]
        before = s.get("ocrBeforeRowCount")
        note = s["collection"].get("error") or s["tableDebugSummary"].get("extractionSource") or ""
        lines.append(
            f"| {filename} | {gt_count if gt_count is not None else '-'} | {before if before is not None else '-'} | "
            f"{after if after is not None else '-'} | {s['rowCountStatus']} | {compact(note)} |"
        )
    lines.append("")

    lines.append("## 4. 샘플별 row alignment")
    lines.append("| 샘플 | matched | missing GT rows | extra OCR rows | low confidence | 판정 |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for filename in SAMPLES:
        a = data["samples"][filename]["alignment"]
        gt_has_rows = data["samples"][filename]["gt"]["hasGtTableRows"]
        manual_count = len(data["samples"][filename]["gt"].get("manualRows") or [])
        verdict = "GT tableRows 없음"
        if gt_has_rows or manual_count:
            verdict = "exact" if not a["missingGtRows"] and not a["extraOcrRows"] else "needs_review"
        lines.append(
            f"| {filename} | {a['matched']} | {len(a['missingGtRows'])} | {len(a['extraOcrRows'])} | {a['lowConfidence']} | {verdict} |"
        )
    lines.append("")

    lines.append("## 5. 샘플별 원인")
    lines.append("| 샘플 | 문제 | 원인 | 수정 여부 | 후속 |")
    lines.append("|---|---|---|---|---|")
    for filename in SAMPLES:
        s = data["samples"][filename]
        status = s["rowCountStatus"]
        debug = s["tableDebugSummary"]
        if status == "exact":
            problem = "rowCount exact"
        else:
            problem = status
        cause = f"source={debug.get('extractionSource')}; rejected={debug.get('rejectedRows')}; rowEnd={debug.get('rowEndReason')}"
        fix = "분석"
        follow = "GT tableRows 추가 필요" if not s["gt"]["hasGtTableRows"] else "row alignment 보정"
        lines.append(f"| {filename} | {problem} | {compact(cause)} | {fix} | {follow} |")
    lines.append("")

    lines.append("## 6. 상세 anchor preview")
    for filename in SAMPLES:
        s = data["samples"][filename]
        lines.append(f"### {filename}")
        lines.append(f"- expected columns: {compact(s['expected'].get('required'))}")
        lines.append(f"- extractionSource: {compact(s['tableDebugSummary'].get('extractionSource'))}")
        lines.append(f"- rejectedRows: {compact(s['tableDebugSummary'].get('rejectedRows'))}")
        lines.append(f"- OCR anchors: {compact(s['ocrAnchorSummary'], 260)}")
        missing = s["alignment"].get("missingGtRows", [])
        extra = s["alignment"].get("extraOcrRows", [])
        if missing:
            lines.append(f"- missingGtRows: {compact(missing, 260)}")
        if extra:
            lines.append(f"- extraOcrRows: {compact(extra[:8], 260)}")
        lines.append("")

    lines.append("## 7. 결론")
    unstable = [
        filename for filename in SAMPLES
        if data["samples"][filename]["rowCountStatus"] != "exact"
    ]
    if unstable:
        lines.append(f"- rowCount 불안정 샘플: {', '.join(unstable)}")
        lines.append("- 다음 단계는 T-6l-fix이며, T-6m/T-7로 이동하기 전 GT tableRows 확보 또는 row 후보 보정이 필요함")
    else:
        lines.append("- GT rowCount 기준으로는 7/7 exact")
        lines.append("- 단, GT tableRows 배열이 없어 row 단위 alignment는 아직 완전 검증이 아님")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="")
    parser.add_argument("--port", type=int, default=8126)
    parser.add_argument("--no-start-server", action="store_true")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    server: subprocess.Popen[str] | None = None
    api_url = args.api_url.strip()
    if not api_url and not args.no_start_server:
        api_url = f"http://127.0.0.1:{args.port}"
        server = start_server(args.port)
        if not wait_for_server(api_url):
            print("WARN: temporary backend did not become ready; report will record API failures")

    try:
        data = analyze(api_url or None, args.timeout)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        JSON_REPORT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        MD_REPORT_PATH.write_text(render_report(data), encoding="utf-8")
        print(f"JSON report: {JSON_REPORT_PATH}")
        print(f"Markdown report: {MD_REPORT_PATH}")
        ok = True
        for filename in SAMPLES:
            sample = data["samples"][filename]
            print(
                f"{filename}: gt={sample['gt']['gtRowCount']} ocr={sample['ocrRowCount']} "
                f"status={sample['rowCountStatus']} source={sample['tableDebugSummary'].get('extractionSource')}"
            )
            if filename == "5.pdf" and sample["ocrRowCount"] != 6:
                ok = False
            if filename == "7.pdf" and sample["ocrRowCount"] != 1:
                ok = False
        return 0 if ok else 2
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
