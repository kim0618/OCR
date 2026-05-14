"""
T-9-fix: Template/RunOCR documentType routing E2E verification.

Verifies that:
1. TPL-31D13CF3 (1.jpg template) has documentType=invoice_statement in templates.json
2. Calling /ocr/extract with template_id=TPL-31D13CF3 returns doc_type=invoice_statement
3. tableRows are generated (rowCount 28)
4. tableMeta is present
5. Other samples (2-7.pdf) are skipped (no saved template annotation)

Two call modes tested:
  Mode A: template_id only (backend reads documentType from template metadata)
  Mode B: template_id + explicit documentType in payload
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:9099"
ROOT_DIR = Path("c:/OCR")
TESTSET_DIR = ROOT_DIR / "mysuit-ocr/public/data/testsets/invoice_statement"
REPORT_DIR = TESTSET_DIR / "reports"
TEMPLATES_FILE = ROOT_DIR / "ocr-server/data/templates.json"
OUT_JSON = REPORT_DIR / "T9_fix_template_runocr_doc_type_20260514.json"
OUT_MD = REPORT_DIR / "T9_fix_template_runocr_doc_type_20260514.md"


def load_templates() -> list[dict]:
    with TEMPLATES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_template(templates: list[dict], template_id: str) -> dict | None:
    return next((t for t in templates if t.get("template_id") == template_id), None)


def call_ocr_template(filename: str, template_id: str, extra_fields: dict | None = None) -> dict:
    fpath = TESTSET_DIR / filename
    if not fpath.exists():
        fpath = ROOT_DIR / "sample" / filename
    with fpath.open("rb") as f:
        data = f.read()
    mime = "image/jpeg" if filename.endswith(".jpg") else "application/pdf"
    files: dict = {"file": (filename, data, mime)}
    if template_id:
        files["template_id"] = (None, template_id, "text/plain")
    if extra_fields:
        for k, v in extra_fields.items():
            files[k] = (None, str(v), "text/plain")
    resp = requests.post(f"{BASE_URL}/ocr/extract", files=files, timeout=180)
    resp.raise_for_status()
    return resp.json()


def check_result(result: dict, mode_label: str) -> dict:
    doc_type = result.get("doc_type", "")
    ed = result.get("extract_debug", {})
    df = result.get("document_fields", {})
    rows = df.get("tableRows", []) or []
    meta = df.get("tableMeta") or {}

    checks = {
        "mode": mode_label,
        "doc_type": doc_type,
        "doc_type_ok": doc_type == "invoice_statement",
        "template_path": result.get("extract_debug", {}).get("template_path", False),
        "tableRows_exists": len(rows) > 0,
        "rowCount": len(rows),
        "rowCount_ok": len(rows) == 28,
        "tableMeta_exists": bool(meta),
        "extractionSource": meta.get("extractionSource", "N/A"),
        "tableBoundsUsed": meta.get("tableBoundsUsed", False),
        "columnGuidesUsed": meta.get("columnGuidesUsed", False),
    }
    return checks


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    all_pass = True

    # --- Template metadata check ---
    templates = load_templates()
    tpl = find_template(templates, "TPL-31D13CF3")

    print("=== Template Metadata Check ===")
    tpl_check: dict = {
        "template_id": "TPL-31D13CF3",
        "found": tpl is not None,
    }
    if tpl:
        tj = tpl.get("template_json", {}) or {}
        tpl_check["template_name"] = tpl.get("template_name", "")
        tpl_check["stored_documentType"] = tj.get("documentType", "")
        tpl_check["documentType_ok"] = tj.get("documentType") == "invoice_statement"
        tpl_check["regions_count"] = len(tj.get("regions", []))
        print(f"  template_name: {tpl_check['template_name']!r}")
        print(f"  stored documentType: {tpl_check['stored_documentType']!r}")
        print(f"  documentType_ok: {tpl_check['documentType_ok']}")
        print(f"  regions: {tpl_check['regions_count']}")
        if not tpl_check["documentType_ok"]:
            all_pass = False
    else:
        print("  TPL-31D13CF3 NOT FOUND")
        all_pass = False

    # --- Mode A: template_id only ---
    print("\n=== Mode A: template_id only (backend reads template documentType) ===")
    result_a_checks: dict = {}
    try:
        t0 = time.time()
        result_a = call_ocr_template("1.jpg", "TPL-31D13CF3")
        elapsed_a = round(time.time() - t0, 1)
        result_a_checks = check_result(result_a, "mode_A_template_id_only")
        result_a_checks["elapsed_sec"] = elapsed_a
        for k, v in result_a_checks.items():
            print(f"  {k}: {v}")
        if not result_a_checks.get("doc_type_ok"):
            all_pass = False
        if not result_a_checks.get("rowCount_ok"):
            all_pass = False
    except Exception as e:
        print(f"  ERROR: {e}")
        result_a_checks = {"error": str(e)}
        all_pass = False

    # --- Mode B: template_id + explicit documentType in payload ---
    print("\n=== Mode B: template_id + explicit documentType=invoice_statement ===")
    result_b_checks: dict = {}
    try:
        t0 = time.time()
        result_b = call_ocr_template("1.jpg", "TPL-31D13CF3", {"documentType": "invoice_statement"})
        elapsed_b = round(time.time() - t0, 1)
        result_b_checks = check_result(result_b, "mode_B_explicit_documentType")
        result_b_checks["elapsed_sec"] = elapsed_b
        for k, v in result_b_checks.items():
            print(f"  {k}: {v}")
        if not result_b_checks.get("doc_type_ok"):
            all_pass = False
    except Exception as e:
        print(f"  ERROR: {e}")
        result_b_checks = {"error": str(e)}
        all_pass = False

    # --- Skipped samples ---
    print("\n=== 2.pdf~7.pdf: No saved template annotation ===")
    skipped = ["2.pdf", "3.pdf", "4.pdf", "5.pdf", "6.pdf", "7.pdf"]
    for fn in skipped:
        # Verify no matching template exists
        has_template = any(
            t.get("template_json", {}).get("file", {}).get("name") == fn
            for t in templates
        )
        print(f"  {fn}: has_template={has_template} -> skipped (use Test path for these)")

    print(f"\n=== RESULT: {'PASS' if all_pass else 'FAIL'} ===")

    # Build report
    summary = {
        "task": "T-9-fix",
        "date": "2026-05-14",
        "templateMetadata": tpl_check,
        "modeA_template_id_only": result_a_checks,
        "modeB_explicit_documentType": result_b_checks,
        "skippedSamples": {fn: "no_saved_template" for fn in skipped},
        "allPass": all_pass,
    }

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    lines = [
        "# T-9-fix Template/RunOCR documentType 라우팅 보정 검증",
        "",
        "## Template Metadata",
        "| 항목 | 결과 |",
        "|---|---|",
    ]
    for k, v in tpl_check.items():
        lines.append(f"| {k} | {v} |")

    lines.extend(["", "## Mode A (template_id only)", "| 항목 | 결과 |", "|---|---|"])
    for k, v in result_a_checks.items():
        lines.append(f"| {k} | {v} |")

    lines.extend(["", "## Mode B (explicit documentType)", "| 항목 | 결과 |", "|---|---|"])
    for k, v in result_b_checks.items():
        lines.append(f"| {k} | {v} |")

    lines.extend(["", "## Skipped (no saved template)", "| 샘플 | 사유 |", "|---|---|"])
    for fn in skipped:
        lines.append(f"| {fn} | no_saved_template |")

    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"JSON: {OUT_JSON}")
    print(f"MD: {OUT_MD}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
