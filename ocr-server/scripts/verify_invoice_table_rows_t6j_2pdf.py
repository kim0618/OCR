"""T-6j-real-template-2pdf: 2.pdf colGuides/tableBounds 기반 rowCount 복구 검증.

2.pdf는 전치(transposed) 표 구조 — 각 컬럼이 하나의 품목(13개).
이 스크립트는 다양한 tableBounds/columnGuides 조합을 시도하여
최선의 rowCount와 원인을 기록한다.

Usage:
  cd d:/Free_Vue/OCR/ocr-server
  python scripts/verify_invoice_table_rows_t6j_2pdf.py
  python scripts/verify_invoice_table_rows_t6j_2pdf.py --api-url http://127.0.0.1:8200
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except Exception:
    requests = None  # type: ignore

SERVER_ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = SERVER_ROOT.parent
MANIFEST_PATH = OCR_ROOT / "mysuit-ocr" / "public" / "data" / "testsets" / "invoice_statement" / "manifest.json"
TESTSET_DIR = OCR_ROOT / "mysuit-ocr" / "public" / "data" / "testsets" / "invoice_statement"
REPORTS_DIR = TESTSET_DIR / "reports"

GT_ROW_COUNT = 13

# 2.pdf page dimensions from OCR analysis
PAGE_W = 900
PAGE_H = 639

# 2.pdf structure analysis:
# - Items are written as VERTICAL COLUMNS (rotated text)
# - 13 item codes found at x=458-700, y=47-70 (vertical text, h~60-80px)
# - Price rows horizontal at y~394-397 (소비자단가 row) and y~463-469
# - "소비자단가 공급단가" label at y~365
# - Item names at y~186-200 (LOXOLIFEN, NAPROXO, AMOXIS as horizontal text)
#
# Expected columns: rowIndex, itemCode, itemName, quantity, consumerUnitPrice,
#                   supplyUnitPrice, supplyAmount, insuranceCode


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def get_expected_columns() -> dict:
    data = load_manifest()
    for item in data.get("items", []):
        if item.get("filename") == "2.pdf":
            return item.get("invoiceProfile", {}).get("tableExpectedColumns", {})
    return {}


def start_server(port: int) -> subprocess.Popen:
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


def wait_for_server(api_url: str, seconds: int = 25) -> bool:
    for _ in range(seconds):
        try:
            r = requests.get(api_url.rstrip("/") + "/docs", timeout=1.5)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def call_with_bounds(
    api_url: str,
    pdf_path: Path,
    expected_columns: dict,
    table_bounds: dict | None,
    column_guides: list[float] | None,
    timeout: int = 180,
) -> dict[str, Any]:
    """Call /ocr/extract with optional tableBounds and columnGuides."""
    if requests is None:
        return {"error": "requests not available"}
    if not pdf_path.exists():
        return {"error": f"file not found: {pdf_path}"}

    data: dict[str, Any] = {
        "tableExpectedColumns": json.dumps(expected_columns, ensure_ascii=False),
    }
    if table_bounds:
        data["tableBounds"] = json.dumps(table_bounds, ensure_ascii=False)
    if column_guides:
        data["columnGuides"] = json.dumps(column_guides, ensure_ascii=False)

    url = api_url.rstrip("/") + "/ocr/extract"
    with pdf_path.open("rb") as fh:
        r = requests.post(
            url,
            files={"file": ("2.pdf", fh, "application/octet-stream")},
            data=data,
            timeout=timeout,
        )
    if r.status_code >= 400:
        return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}

    payload = r.json()
    doc_fields = payload.get("document_fields") or {}
    table_rows = doc_fields.get("tableRows") or []
    table_meta = doc_fields.get("tableMeta") or {}
    debug_root = payload.get("extract_debug") or {}
    inv_debug = debug_root.get("invoice_statement") or {}
    tbl = (inv_debug.get("table") or {}) if isinstance(inv_debug, dict) else {}
    tbl_debug = (tbl.get("tableDebug") or {}) if isinstance(tbl, dict) else {}

    rejected = tbl_debug.get("rejectedRows") or []
    cg_rejected = tbl_debug.get("colGuidesRejectedRows") or []
    from collections import Counter
    reason_counts = Counter(
        r.get("reason", "?") for r in rejected if isinstance(r, dict)
    ) if isinstance(rejected, list) else {}
    cg_reason_counts = Counter(
        r.get("reason", "?") for r in cg_rejected if isinstance(r, dict)
    ) if isinstance(cg_rejected, list) else {}

    # Value column fill analysis
    value_cols: dict[str, int] = {}
    for row in table_rows:
        for k, v in row.items():
            if v and str(v).strip() and k not in {"rowIndex", "_rawText", "_confidence", "_source", "sourceBboxes", "rawText"}:
                value_cols[k] = value_cols.get(k, 0) + 1

    return {
        "row_count": len(table_rows),
        "extraction_source": table_meta.get("extractionSource") or tbl_debug.get("extractionSource") or tbl_debug.get("fallbackSource"),
        "table_bounds_used": table_meta.get("tableBoundsUsed", False),
        "column_guides_received": table_meta.get("columnGuidesReceived", False),
        "column_guides_used": table_meta.get("columnGuidesUsed", False),
        "column_guides_count": table_meta.get("columnGuidesCount", 0),
        "column_guides_used_attempted": table_meta.get("columnGuidesUsedAttempted", False),
        "row_candidate_before": table_meta.get("rowCandidateCountBeforeFilter"),
        "row_candidate_after": table_meta.get("rowCandidateCountAfterFilter"),
        "missing_expected_keys": table_meta.get("missingExpectedColumnKeys"),
        "header_band_found": tbl_debug.get("headerBandFound"),
        "header_score": (tbl_debug.get("selectedHeaderBand") or {}).get("score"),
        "rejected_reasons": dict(reason_counts),
        "cg_rejected_reasons": dict(cg_reason_counts),
        "rejected_rows_detail": [
            {"reason": r.get("reason"), "y": r.get("y"), "text": r.get("text", "")[:50]}
            for r in rejected[:6]
        ] if isinstance(rejected, list) else [],
        "cg_rejected_rows_detail": [
            {"reason": r.get("reason"), "y": r.get("y"), "text": r.get("text", "")[:60]}
            for r in cg_rejected[:8]
        ] if isinstance(cg_rejected, list) else [],
        "value_column_fill": value_cols,
        "first_rows": [
            {k: str(v)[:30] for k, v in r.items() if k not in {"sourceBboxes", "_rawText", "rawText"} and str(v or "").strip()}
            for r in table_rows[:3]
        ],
    }


def run_tests(api_url: str, expected_columns: dict, pdf_path: Path) -> list[dict]:
    """Try multiple tableBounds/columnGuides combinations."""

    # Structural analysis:
    # 2.pdf (900x639) has a TRANSPOSED TABLE:
    # - Item codes written VERTICALLY as columns (y=47-70, x=458-700)
    # - 13 items spread horizontally
    # - Standard horizontal row extraction fundamentally incompatible
    #
    # Attempts below try different bounds/guides to maximize row recovery.

    test_cases = [
        {
            "label": "baseline (no bounds/guides)",
            "bounds": None,
            "guides": None,
        },
        {
            "label": "body_only_bounds (y=340-540)",
            "bounds": {"xMin": 0, "yMin": 340, "xMax": 900, "yMax": 540, "source": "test"},
            "guides": None,
        },
        {
            "label": "price_rows_bounds (y=355-490)",
            "bounds": {"xMin": 60, "yMin": 355, "xMax": 900, "yMax": 490, "source": "test"},
            "guides": None,
        },
        {
            "label": "full_table_bounds_no_guides (y=40-560)",
            "bounds": {"xMin": 0, "yMin": 40, "xMax": 900, "yMax": 560, "source": "test"},
            "guides": None,
        },
        {
            "label": "colguides_price_area (8 cols for 8 expected keys)",
            # x-positions of columns from OCR analysis:
            # col boundaries: ~131, ~231, ~340, ~450, ~530, ~600, ~650, ~700, ~760, ~900
            # 7 dividers for 8 columns
            "bounds": {"xMin": 60, "yMin": 355, "xMax": 900, "yMax": 490, "source": "test"},
            "guides": [131, 231, 340, 450, 530, 600, 700],
        },
        {
            "label": "colguides_narrow_price_area (y=385-410)",
            "bounds": {"xMin": 60, "yMin": 385, "xMax": 760, "yMax": 410, "source": "test"},
            "guides": [131, 231, 340, 450, 530, 600, 650],
        },
        {
            "label": "colguides_with_insurance (y=340-500)",
            "bounds": {"xMin": 60, "yMin": 340, "xMax": 900, "yMax": 500, "source": "test"},
            "guides": [100, 200, 340, 455, 530, 580, 645],
        },
        {
            "label": "colguides_full_page (y=40-560)",
            # Full page with colGuides — test if item rows exist in y=40-340 range
            "bounds": {"xMin": 0, "yMin": 40, "xMax": 900, "yMax": 560, "source": "test"},
            "guides": [100, 200, 340, 455, 530, 580, 645],
        },
        {
            "label": "colguides_top_half (y=40-350)",
            # Item rows might be in y=40-340 based on OCR analysis
            "bounds": {"xMin": 0, "yMin": 40, "xMax": 900, "yMax": 350, "source": "test"},
            "guides": [100, 200, 340, 455, 530, 580, 645],
        },
    ]

    results = []
    for tc in test_cases:
        print(f"  Testing: {tc['label']} ...", flush=True)
        result = call_with_bounds(api_url, pdf_path, expected_columns, tc["bounds"], tc["guides"])
        result["label"] = tc["label"]
        result["bounds"] = tc["bounds"]
        result["guides"] = tc["guides"]
        print(f"    rowCount={result.get('row_count')} src={result.get('extraction_source')} cgAttempted={result.get('column_guides_used_attempted')} before={result.get('row_candidate_before')} after={result.get('row_candidate_after')}")
        print(f"      header_rejected={result.get('rejected_reasons')} cg_rejected={result.get('cg_rejected_reasons')}")
        if result.get("column_guides_used_attempted") and result.get("cg_rejected_rows_detail"):
            for rd in result.get("cg_rejected_rows_detail", []):
                print(f"      cg_row: {rd.get('reason')} y={rd.get('y')} text={rd.get('text', '')[:60]!r}")
        results.append(result)

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="")
    parser.add_argument("--port", type=int, default=8201)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    server = None
    api_url = args.api_url.strip()

    if not api_url:
        api_url = f"http://127.0.0.1:{args.port}"
        print(f"Starting server at {api_url} ...", flush=True)
        server = start_server(args.port)
        if not wait_for_server(api_url):
            print("Server did not start.")
            return 1

    expected = get_expected_columns()
    print(f"Expected columns: {expected.get('required', [])}")

    pdf_path = TESTSET_DIR / "2.pdf"
    if not pdf_path.exists():
        print(f"2.pdf not found: {pdf_path}")
        return 1

    print(f"\nRunning {7} test cases for 2.pdf ...", flush=True)
    results = run_tests(api_url, expected, pdf_path)

    best = max(results, key=lambda r: r.get("row_count", 0))
    print(f"\nBest result: {best['label']} → rowCount={best.get('row_count')}")

    # Write reports
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_json = REPORTS_DIR / "T6j_real_template_2pdf_rowcount_report_20260513.json"
    report_md = REPORTS_DIR / "T6j_real_template_2pdf_rowcount_report_20260513.md"

    data = {
        "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gtRowCount": GT_ROW_COUNT,
        "pageSize": [PAGE_W, PAGE_H],
        "structuralAnalysis": {
            "tableType": "transposed_column_major",
            "description": "Each COLUMN is one item (13 items). Items written as vertical columns. Standard horizontal row extraction incompatible.",
            "itemCodeY": "47-70 (vertical/rotated text)",
            "priceRowsY": "394-397, 463-469",
            "estimatedItems": 13,
        },
        "testResults": results,
        "bestResult": best,
    }
    report_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# T-6j-real-template-2pdf rowCount 복구 검증 결과\n",
        f"## 2.pdf 구조 분석",
        f"- **표 유형**: 전치(transposed) 컬럼 주도 표",
        f"- **품목 배치**: 각 컬럼 = 1개 품목 (13개 컬럼)",
        f"- **품목코드 위치**: y=47-70, 세로(회전) 텍스트",
        f"- **가격 행 위치**: y=394-397, 463-469",
        f"- **GT rowCount**: {GT_ROW_COUNT}",
        f"- **표준 세로 행 추출**: 구조적 한계 (가로 표를 세로 표로 오인식)",
        "",
        "## 테스트 결과",
        "| 테스트 | extractionSource | cgUsed | rowCount | rejectedReasons |",
        "|---|---|---|---:|---|",
    ]
    for r in results:
        md_lines.append(
            f"| {r['label'][:45]} | {str(r.get('extraction_source',''))[:30]} | "
            f"{r.get('column_guides_used',False)} | {r.get('row_count',0)} | "
            f"{str(r.get('rejected_reasons',''))[:40]} |"
        )
    md_lines += [
        "",
        "## 결론",
        f"- **최대 달성 rowCount**: {best.get('row_count')} (목표 {GT_ROW_COUNT})",
        "- **근본 원인**: 2.pdf는 전치 표 구조 (가로 = 품목, 세로 = 가격항목). 표준 세로 행 추출기로 13행 복구 불가.",
        "- **Template annotation 없음**: templates.json에 2.pdf 해당 템플릿 없음",
        "- **후속 조치**: 전치 표 전용 추출 로직 개발 또는 2.pdf를 rowCount 검증 대상에서 제외",
    ]
    report_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"\nJSON: {report_json}")
    print(f"MD:   {report_md}")

    if server is not None:
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
