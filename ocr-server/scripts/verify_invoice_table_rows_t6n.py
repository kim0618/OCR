"""T-6n: OP anchor row reconstruction 검증 스크립트.

2.pdf rowCount 13 달성 여부와 기존 샘플 회귀를 함께 확인한다.

Usage:
  cd d:/Free_Vue/OCR/ocr-server
  python scripts/verify_invoice_table_rows_t6n.py
  python scripts/verify_invoice_table_rows_t6n.py --api-url http://127.0.0.1:8200
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except Exception:
    requests = None  # type: ignore

SERVER_ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = SERVER_ROOT.parent
TESTSET_DIR = OCR_ROOT / "mysuit-ocr" / "public" / "data" / "testsets" / "invoice_statement"
MANIFEST_PATH = TESTSET_DIR / "manifest.json"
REPORTS_DIR = TESTSET_DIR / "reports"

GT_ROW_COUNTS = {
    "1.jpg": 28, "2.pdf": 13, "3.pdf": 1, "4.pdf": 1,
    "5.pdf": 6, "6.pdf": 6, "7.pdf": 1,
}


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def get_expected_columns(manifest: dict, filename: str) -> dict:
    for item in manifest.get("items", []):
        if item.get("filename") == filename:
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


def wait_for_server(api_url: str, seconds: int = 30) -> bool:
    for _ in range(seconds):
        try:
            r = requests.get(api_url.rstrip("/") + "/docs", timeout=1.5)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def call_ocr(api_url: str, file_path: Path, expected_columns: dict, timeout: int = 180) -> dict:
    if requests is None:
        return {"error": "requests not available"}
    if not file_path.exists():
        return {"error": f"file not found: {file_path}"}

    suffix = file_path.suffix.lower()
    mime = "application/pdf" if suffix == ".pdf" else "image/jpeg"
    data: dict = {}
    if expected_columns:
        data["tableExpectedColumns"] = json.dumps(expected_columns, ensure_ascii=False)

    url = api_url.rstrip("/") + "/ocr/extract"
    with file_path.open("rb") as fh:
        r = requests.post(
            url,
            files={"file": (file_path.name, fh, mime)},
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

    # Build per-row summary
    row_summaries = []
    for row in table_rows[:15]:
        row_summaries.append({k: str(v)[:25] for k, v in row.items()
                              if v and str(v).strip()
                              and k not in {"sourceBboxes", "_rawText", "rawText", "_source",
                                            "_confidence", "source"}})

    return {
        "row_count": len(table_rows),
        "extraction_source": table_meta.get("extractionSource", ""),
        "op_anchor_attempted": table_meta.get("opAnchorReconstructionAttempted", False),
        "op_anchor_count": table_meta.get("opAnchorCount"),
        "op_anchor_rows_built": table_meta.get("opAnchorRowsBuilt"),
        "previous_row_count": table_meta.get("previousRowCount"),
        "reconstructed_row_count": table_meta.get("reconstructedRowCount"),
        "op_anchor_samples": tbl_debug.get("opAnchorSamples", [])[:4],
        "row_summaries": row_summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="")
    parser.add_argument("--port", type=int, default=8205)
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

    manifest = load_manifest()
    results: list[dict] = []

    for filename, gt in GT_ROW_COUNTS.items():
        file_path = TESTSET_DIR / filename
        expected_cols = get_expected_columns(manifest, filename)
        print(f"  Testing {filename} (GT={gt}) ...", flush=True)
        result = call_ocr(api_url, file_path, expected_cols, timeout=args.timeout)
        result["filename"] = filename
        result["gt_row_count"] = gt
        ocr_count = result.get("row_count", 0)
        status = "exact" if ocr_count == gt else ("over" if ocr_count > gt else "short")
        result["status"] = status
        results.append(result)

        print(f"    rowCount={ocr_count}/{gt} {status} src={result.get('extraction_source','')} "
              f"opAttempted={result.get('op_anchor_attempted')} opCount={result.get('op_anchor_count')}")
        if result.get("op_anchor_attempted"):
            print(f"    prevCount={result.get('previous_row_count')} reconstructed={result.get('reconstructed_row_count')}")
            if result.get("op_anchor_samples"):
                print(f"    samples={result['op_anchor_samples'][:3]}")
        if filename == "2.pdf" and result.get("row_summaries"):
            print(f"    Row preview:")
            for row in result["row_summaries"][:5]:
                print(f"      {row}")

    # Write reports
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d")
    report_json = REPORTS_DIR / f"T6n_op_anchor_reconstruction_report_{ts}.json"
    report_md = REPORTS_DIR / f"T6n_op_anchor_reconstruction_report_{ts}.md"

    report_json.write_text(
        json.dumps({"generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "results": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md_lines = [
        "# T-6n OP Anchor Row Reconstruction 검증 결과\n",
        "## rowCount 비교",
        "| 샘플 | GT | OCR | 상태 | source |",
        "|---|---:|---:|---|---|",
    ]
    for r in results:
        md_lines.append(
            f"| {r['filename']} | {r['gt_row_count']} | {r.get('row_count', '-')} "
            f"| {r['status']} | {r.get('extraction_source', '')} |"
        )

    md_lines += [
        "",
        "## 2.pdf 행 미리보기",
        "| # | itemCode | itemName | quantity | consumerUnitPrice | supplyAmount |",
        "|---|---|---|---|---|---|",
    ]
    two_pdf = next((r for r in results if r["filename"] == "2.pdf"), None)
    if two_pdf:
        for j, row in enumerate(two_pdf.get("row_summaries", []), 1):
            md_lines.append(
                f"| {j} | {row.get('itemCode', '')} | {row.get('itemName', '')} "
                f"| {row.get('quantity', '')} | {row.get('consumerUnitPrice', '')} "
                f"| {row.get('supplyAmount', '')} |"
            )

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
