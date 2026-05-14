"""T-6m: expected column value mapping 검증 스크립트.

7개 샘플의 expected display 컬럼 기준 value fill rate를 수집하고
before/after 비교 리포트를 생성한다.

Usage:
  cd d:/Free_Vue/OCR/ocr-server
  python scripts/verify_invoice_table_rows_t6m.py
  python scripts/verify_invoice_table_rows_t6m.py --api-url http://127.0.0.1:8200
  python scripts/verify_invoice_table_rows_t6m.py --phase after
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

# Expected display columns per sample (from manifest)
EXPECTED_DISPLAY: dict[str, list[dict[str, str]]] = {
    "1.jpg": [
        {"key": "itemName", "label": "품목"},
        {"key": "spec", "label": "규격"},
        {"key": "manufacturingNo", "label": "제조번호"},
        {"key": "expiryDate", "label": "유효기간"},
        {"key": "quantity", "label": "수량"},
        {"key": "unitPrice", "label": "단가"},
        {"key": "amount", "label": "금액"},
    ],
    "2.pdf": [
        {"key": "rowIndex", "label": "NO"},
        {"key": "itemCode", "label": "품목코드"},
        {"key": "itemName", "label": "품목명"},
        {"key": "quantity", "label": "수량"},
        {"key": "consumerUnitPrice", "label": "소비자단가"},
        {"key": "supplyUnitPrice", "label": "공급단가"},
        {"key": "supplyAmount", "label": "공급금액"},
        {"key": "insuranceCode", "label": "보험No"},
    ],
    "3.pdf": [
        {"key": "rowIndex", "label": "순번"},
        {"key": "insuranceCode", "label": "보험코드"},
        {"key": "itemName", "label": "품명"},
        {"key": "spec", "label": "규격"},
        {"key": "quantity", "label": "수량"},
        {"key": "unitPrice", "label": "단가"},
        {"key": "amount", "label": "금액"},
        {"key": "manufacturer", "label": "제조회사"},
        {"key": "manufacturingExpiryComposite", "label": "제조번호/유효기간"},
    ],
    "4.pdf": [
        {"key": "itemName", "label": "품목명"},
        {"key": "lotNo", "label": "LotNo."},
        {"key": "unit", "label": "단위"},
        {"key": "quantity", "label": "수량"},
        {"key": "unitPrice", "label": "단가"},
        {"key": "supplyAmount", "label": "공급가액"},
        {"key": "taxAmount", "label": "세액"},
    ],
    "5.pdf": [
        {"key": "itemName", "label": "품명"},
        {"key": "itemCode", "label": "품목코드"},
        {"key": "quantity", "label": "수량"},
        {"key": "unitPrice", "label": "단가"},
        {"key": "amount", "label": "금액"},
    ],
    "6.pdf": [
        {"key": "rowIndex", "label": "NO"},
        {"key": "itemCode", "label": "제품코드"},
        {"key": "itemName", "label": "제품명"},
        {"key": "quantity", "label": "수량"},
        {"key": "lotNo", "label": "LotNo"},
        {"key": "expiryDate", "label": "유효일자"},
    ],
    "7.pdf": [
        {"key": "itemName", "label": "품명"},
        {"key": "serialLotComposite", "label": "시리얼/로트No."},
        {"key": "unit", "label": "단위"},
        {"key": "quantity", "label": "수량"},
    ],
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

    return {
        "row_count": len(table_rows),
        "table_rows": table_rows,
        "table_meta": table_meta,
        "extraction_source": table_meta.get("extractionSource", ""),
    }


def compute_fill_rate(table_rows: list[dict], display_cols: list[dict]) -> dict:
    """compute per-column and per-row fill rates."""
    n_rows = len(table_rows)
    if n_rows == 0:
        return {
            "n_rows": 0,
            "col_stats": [],
            "overall_fill_rate": 0.0,
            "row_fill_rates": [],
        }

    col_stats = []
    for col in display_cols:
        key = col["key"]
        label = col["label"]
        filled = sum(1 for row in table_rows if str(row.get(key) or "").strip())
        col_stats.append({
            "key": key,
            "label": label,
            "filled": filled,
            "total": n_rows,
            "fill_rate": round(filled / n_rows * 100, 1),
            "sample_values": [
                str(row.get(key) or "")[:25]
                for row in table_rows[:3]
                if str(row.get(key) or "").strip()
            ][:3],
        })

    # Per-row fill count
    row_fill_rates = []
    for i, row in enumerate(table_rows):
        filled_keys = [c["key"] for c in display_cols if str(row.get(c["key"]) or "").strip()]
        row_fill_rates.append({
            "row": i + 1,
            "filled": len(filled_keys),
            "total": len(display_cols),
            "filled_keys": filled_keys,
            "missing_keys": [c["key"] for c in display_cols if c["key"] not in filled_keys],
        })

    total_cells = n_rows * len(display_cols)
    filled_cells = sum(c["filled"] for c in col_stats)
    overall = round(filled_cells / total_cells * 100, 1) if total_cells > 0 else 0.0

    return {
        "n_rows": n_rows,
        "col_stats": col_stats,
        "overall_fill_rate": overall,
        "row_fill_rates": row_fill_rates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="")
    parser.add_argument("--port", type=int, default=8206)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--phase", choices=["before", "after"], default="before",
                        help="Label this run 'before' or 'after' for comparison")
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
        display_cols = EXPECTED_DISPLAY.get(filename, [])
        print(f"  Testing {filename} (GT={gt}) ...", flush=True)
        ocr = call_ocr(api_url, file_path, expected_cols, timeout=args.timeout)

        if "error" in ocr:
            print(f"    ERROR: {ocr['error']}")
            results.append({"filename": filename, "gt_row_count": gt, "error": ocr["error"]})
            continue

        row_count = ocr["row_count"]
        table_rows = ocr["table_rows"]
        extraction_source = ocr["extraction_source"]
        status = "exact" if row_count == gt else ("over" if row_count > gt else "short")

        fill = compute_fill_rate(table_rows, display_cols)

        print(f"    rowCount={row_count}/{gt} {status}  src={extraction_source}")
        print(f"    overall_fill_rate={fill['overall_fill_rate']}%  ({fill['n_rows']} rows × {len(display_cols)} cols)")
        for cs in fill["col_stats"]:
            bar = "OK" if cs["fill_rate"] == 100 else ("--" if cs["fill_rate"] > 0 else "NG")
            print(f"      {bar} {cs['label']:16s} ({cs['key']:28s}) {cs['filled']:2d}/{cs['total']} = {cs['fill_rate']:5.1f}%  samples={cs['sample_values'][:2]}")

        result = {
            "filename": filename,
            "gt_row_count": gt,
            "ocr_row_count": row_count,
            "status": status,
            "extraction_source": extraction_source,
            "display_cols": [c["key"] for c in display_cols],
            "overall_fill_rate": fill["overall_fill_rate"],
            "col_stats": fill["col_stats"],
            "row_fill_rates": fill["row_fill_rates"],
            "table_meta": ocr["table_meta"],
        }
        results.append(result)

    # Write reports
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d")
    phase = args.phase
    report_json = REPORTS_DIR / f"T6m_value_mapping_{phase}_{ts}.json"
    report_md = REPORTS_DIR / f"T6m_value_mapping_{phase}_{ts}.md"

    report_json.write_text(
        json.dumps({"generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "phase": phase, "results": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md_lines = [
        f"# T-6m Expected Column Value Mapping 검증 결과 ({phase})\n",
        "## rowCount 비교",
        "| 샘플 | GT | OCR | 상태 | source |",
        "|---|---:|---:|---|---|",
    ]
    for r in results:
        if "error" in r:
            md_lines.append(f"| {r['filename']} | {r['gt_row_count']} | ERROR | - | {r.get('error','')} |")
        else:
            md_lines.append(
                f"| {r['filename']} | {r['gt_row_count']} | {r['ocr_row_count']} "
                f"| {r['status']} | {r.get('extraction_source', '')} |"
            )

    md_lines += ["", "## 샘플별 Expected Column Fill Rate"]
    for r in results:
        if "error" in r:
            continue
        md_lines.append(f"\n### {r['filename']}  (overall {r['overall_fill_rate']}%)")
        md_lines.append("| 컬럼 | key | filled/total | rate |")
        md_lines.append("|---|---|---:|---:|")
        for cs in r.get("col_stats", []):
            bar = "OK" if cs["fill_rate"] == 100.0 else ("--" if cs["fill_rate"] > 0 else "NG")
            md_lines.append(
                f"| {bar} {cs['label']} | `{cs['key']}` | {cs['filled']}/{cs['total']} | {cs['fill_rate']}% |"
            )

    md_lines += ["", "## 샘플별 Row Fill 상세 (최대 13개)"]
    for r in results:
        if "error" in r:
            continue
        md_lines.append(f"\n### {r['filename']}")
        for rfr in r.get("row_fill_rates", [])[:13]:
            missing = rfr.get("missing_keys", [])
            miss_str = ", ".join(missing) if missing else "없음"
            md_lines.append(
                f"- row {rfr['row']}: {rfr['filled']}/{rfr['total']}  missing=[{miss_str}]"
            )

    report_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"\nJSON: {report_json}")
    print(f"MD:   {report_md}")

    # Summary
    all_exact = all(r.get("status") == "exact" for r in results if "error" not in r)
    print("\n" + ("OK: rowCount all exact" if all_exact else "NG: rowCount regression"))

    if server is not None:
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
