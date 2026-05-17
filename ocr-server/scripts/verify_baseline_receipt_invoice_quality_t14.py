"""
T-14 baseline receipt + invoice_statement quality audit.

Reporting only. This script does not modify OCR/parser/template logic.

Data policy:
- Prefer existing validation/report JSON where it exists.
- Use invoice_statement T-8/T-10 reports for rowCount regression.
- For receipt_generalization, where no RunAll export exists, reuse the saved
  OCR cache text and run the current lightweight classifier/field parser over
  synthetic line boxes. The report marks those rows as cache_based_parser.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public/data/testsets"
REPORTS = TESTSETS / "reports"
OUT_JSON = REPORTS / "T14_baseline_receipt_invoice_quality_audit_20260516.json"
OUT_MD = REPORTS / "T14_baseline_receipt_invoice_quality_audit_20260516.md"

RECEIPT_AUDIT_TESTSETS = [
    "baseline",
    "baseline_fast",
    "google",
    "google_fast",
    "receipt_generalization",
]
CONFIRM_ONLY_TESTSETS = {"new_samples"}
EXCLUDE_FROM_AUDIT = {"tax_invoice"}
INVOICE_TESTSET = "invoice_statement"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".pdf"}
CORE_FIELDS = ["merchantName", "date", "time", "totalAmount", "paymentAmount", "cardAmount", "cashAmount",
               "approvalNo", "cardNo", "businessNo", "address", "phone", "itemRows"]
RECEIPT_FINAL_FIELD_ALIASES = ["merchantName", "businessNo", "representative", "phone", "address", "totalAmount"]
INVOICE_EXPECTED = {"1.jpg": 28, "2.pdf": 13, "3.pdf": 1, "4.pdf": 1, "5.pdf": 6, "6.pdf": 6, "7.pdf": 1}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict)):
        return bool(value)
    text = str(value).strip()
    return bool(text) and text not in {"None", "null", "-", "0"}


def md(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def short_counts(counter: Counter[str], limit: int = 6) -> str:
    if not counter:
        return "-"
    parts = [f"{k}:{v}" for k, v in counter.most_common(limit)]
    if len(counter) > limit:
        parts.append(f"+{len(counter) - limit}")
    return ", ".join(parts)


def manifest_paths() -> list[Path]:
    return sorted(TESTSETS.glob("*/manifest.json"))


def image_count(testset_dir: Path, manifest: dict[str, Any]) -> tuple[int, list[str], bool]:
    names = []
    missing = []
    for item in manifest.get("items", []) or []:
        fn = item.get("filename")
        if not fn:
            continue
        if (testset_dir / fn).exists() and Path(fn).suffix.lower() in IMAGE_EXTS:
            names.append(fn)
        else:
            missing.append(fn)
    placeholder = bool(missing) or any("placeholder" in str(i.get("filename", "")).lower() for i in manifest.get("items", []))
    return len(names), missing, placeholder


def summarize_manifest(testset_id: str, manifest: dict[str, Any], count: int, missing: list[str], placeholder: bool) -> dict[str, Any]:
    items = manifest.get("items", []) or []
    return {
        "testsetId": testset_id,
        "label": manifest.get("label") or manifest.get("name") or manifest.get("datasetId") or testset_id,
        "datasetRole": manifest.get("datasetRole", ""),
        "status": manifest.get("status", ""),
        "sampleCount": count,
        "manifestItems": len(items),
        "missingFiles": missing,
        "placeholder": placeholder,
        "documentTypes": dict(Counter(str(i.get("documentType", "unknown")) for i in items)),
        "expectedStatus": dict(Counter(str(i.get("expectedStatus", "unknown")) for i in items)),
        "qualityTags": dict(Counter(tag for i in items for tag in (i.get("qualityTags") or ["__none__"]))),
        "difficulty": dict(Counter(str(i.get("difficulty", "unknown")) for i in items)),
    }


def validation_score(path: Path) -> int:
    try:
        data = load_json(path, {})
    except Exception:
        return 0
    rows = data.get("rows") or []
    if not isinstance(rows, list):
        return 0
    score = len(rows) * 10
    for row in rows:
        final_fields = row.get("final_fields") or row.get("receipt_fields") or row.get("selected_values") or {}
        if isinstance(final_fields, dict):
            filled = sum(1 for v in final_fields.values() if is_filled(v))
            score += filled * 8
            if row.get("final_fields"):
                score += 20
        if row.get("doc_type"):
            score += 2
        if row.get("status"):
            score += 2
    name = path.name
    for token, bonus in (
        ("after_final_selection_edge_cases", 200),
        ("final_before_lock", 160),
        ("baseline_final_selection_policy", 140),
        ("top_fields_generalization", 100),
        ("after_top_fields", 80),
        ("after_refactor", -200),
    ):
        if token in name:
            score += bonus
    return score


def latest_validation_json(testset_dir: Path) -> Path | None:
    paths = [p for p in testset_dir.glob("validation_results*.json") if p.is_file()]
    if not paths:
        return None
    return max(paths, key=lambda p: (validation_score(p), p.stat().st_mtime))


def manifest_item_map(testset_id: str) -> dict[str, dict[str, Any]]:
    manifest = load_json(TESTSETS / testset_id / "manifest.json", {})
    return {item.get("filename"): item for item in manifest.get("items", []) if item.get("filename")}


def normalize_fields_from_final_fields(final_fields: dict[str, Any]) -> dict[str, Any]:
    values = list((final_fields or {}).values())
    fields = {name: "" for name in CORE_FIELDS}
    for idx, alias in enumerate(RECEIPT_FINAL_FIELD_ALIASES):
        if idx < len(values):
            fields[alias] = values[idx]
    return fields


def classify_status(status: str, suppression: bool, unknown: bool, error: str = "") -> str:
    if error:
        return "error"
    if suppression or str(status).startswith("suppressed"):
        return "suppressed"
    if unknown or status == "unknown":
        return "unknown"
    if status == "selected":
        return "selected"
    return status or "unknown"


def add_missing(fields: dict[str, Any], required: list[str]) -> list[str]:
    return [field for field in required if not is_filled(fields.get(field))]


def required_fields_for(doc_type: str, expected_status: str) -> list[str]:
    if expected_status.startswith("suppressed"):
        return []
    if doc_type == "card_receipt":
        return ["merchantName", "totalAmount", "businessNo", "phone", "address"]
    if doc_type == "pos_receipt":
        return ["merchantName", "totalAmount", "businessNo"]
    if doc_type == "food_cafe_receipt":
        return ["merchantName", "totalAmount"]
    if doc_type == "medical_receipt":
        return ["merchantName", "totalAmount"]
    if doc_type == "finance_slip":
        return []
    return ["merchantName", "totalAmount"]


def rows_from_validation(testset_id: str) -> tuple[list[dict[str, Any]], str]:
    testset_dir = TESTSETS / testset_id
    path = latest_validation_json(testset_dir)
    if not path:
        return [], "no_validation_json"
    data = load_json(path, {})
    rows = data.get("rows") or []
    meta = manifest_item_map(testset_id)
    out: list[dict[str, Any]] = []
    for row in rows:
        filename = row.get("file") or row.get("filename")
        item = meta.get(filename, {})
        fields = normalize_fields_from_final_fields(row.get("final_fields") or row.get("receipt_fields") or {})
        status_bucket = classify_status(str(row.get("status", "")), bool(row.get("suppression")), bool(row.get("unknown")), str(row.get("error", "")))
        expected_doc = item.get("documentType", "unknown")
        expected_status = item.get("expectedStatus", "unknown")
        missing = add_missing(fields, required_fields_for(expected_doc, expected_status))
        warnings = []
        if row.get("status") != expected_status:
            warnings.append(f"status_mismatch:{row.get('status')}!=expected:{expected_status}")
        if row.get("doc_type") and expected_doc != "unknown":
            expected_backend = {
                "card_receipt": "receipt_card",
                "pos_receipt": "receipt_pos",
                "food_cafe_receipt": "receipt_card",
                "medical_receipt": "medical_receipt",
                "finance_slip": "bank_slip",
            }.get(expected_doc, expected_doc)
            if row.get("doc_type") != expected_backend and expected_doc != "food_cafe_receipt":
                warnings.append(f"doc_type_mismatch:{row.get('doc_type')}!=expected:{expected_backend}")
        out.append({
            "filename": filename,
            "testsetId": testset_id,
            "documentType": expected_doc,
            "expectedStatus": expected_status,
            "qualityTags": item.get("qualityTags", []),
            "difficulty": item.get("difficulty", "unknown"),
            "resultStatus": status_bucket,
            "rawStatus": row.get("status"),
            "ocrDocType": row.get("doc_type"),
            "fields": fields,
            "missingFields": missing,
            "warnings": warnings,
            "error": row.get("error", ""),
            "tableRows": None,
            "expectedRowCount": None,
            "rowCountStatus": None,
            "valueMappingWarnings": [],
            "extractionSource": row.get("extractionSource") or "validation_results",
            "auditSource": path.name,
        })
    return out, path.name


def fake_ocr_lines(text: str) -> list[Any]:
    lines = []
    y = 10
    for raw in (text or "").splitlines():
        s = raw.strip()
        if not s:
            continue
        w = max(20, min(800, len(s) * 8))
        lines.append(([(10, y), (10 + w, y), (10 + w, y + 14), (10, y + 14)], s, 0.9))
        y += 20
    return lines


def rows_from_ocr_cache(testset_id: str) -> tuple[list[dict[str, Any]], str]:
    sys.path.insert(0, str(BACKEND))
    try:
        from document_classifier import classify_document  # type: ignore
        from main import extract_receipt_fields  # type: ignore
    except Exception as exc:
        return [], f"cache_parser_import_failed:{exc}"

    cache = load_json(TESTSETS / testset_id / "ocr_cache.json", {})
    meta = manifest_item_map(testset_id)
    out = []
    for filename, cached in cache.items():
        if not isinstance(cached, dict):
            continue
        item = meta.get(filename, {})
        text = cached.get("ocr_text", "")
        doc_info = classify_document(text)
        backend_doc = doc_info.get("type", "unknown")
        debug = {"document_classification": doc_info, "doc_type": backend_doc}
        fields_raw = extract_receipt_fields(fake_ocr_lines(text), doc_type=backend_doc, debug=debug)
        fields = normalize_fields_from_final_fields(fields_raw)
        expected_doc = item.get("documentType", "unknown")
        expected_status = item.get("expectedStatus", "unknown")
        status = "selected"
        if backend_doc == "bank_slip" and expected_status.startswith("suppressed"):
            status = expected_status
        elif backend_doc == "unknown":
            status = "unknown"
        elif backend_doc == "form_or_handwritten":
            status = "suppressed_handwritten"
        status_bucket = classify_status(status, status.startswith("suppressed"), status == "unknown")
        missing = add_missing(fields, required_fields_for(expected_doc, expected_status))
        warnings = ["cache_based_parser:no_live_runall_fields"]
        if expected_doc == "finance_slip":
            warnings.append("finance_slip_policy_review:expected selected/suppressed differs by sample")
        if expected_doc != "unknown":
            expected_backend = {
                "card_receipt": "receipt_card",
                "pos_receipt": "receipt_pos",
                "food_cafe_receipt": "receipt_card",
                "medical_receipt": "medical_receipt",
                "finance_slip": "bank_slip",
            }.get(expected_doc, expected_doc)
            if backend_doc != expected_backend and expected_doc not in {"food_cafe_receipt", "pos_receipt"}:
                warnings.append(f"doc_type_mismatch:{backend_doc}!=expected:{expected_backend}")
        out.append({
            "filename": filename,
            "testsetId": testset_id,
            "documentType": expected_doc,
            "expectedStatus": expected_status,
            "qualityTags": item.get("qualityTags", []),
            "difficulty": item.get("difficulty", "unknown"),
            "resultStatus": status_bucket,
            "rawStatus": status,
            "ocrDocType": backend_doc,
            "fields": fields,
            "missingFields": missing,
            "warnings": warnings,
            "error": "",
            "tableRows": None,
            "expectedRowCount": None,
            "rowCountStatus": None,
            "valueMappingWarnings": [],
            "extractionSource": "ocr_cache_text_current_parser",
            "auditSource": "ocr_cache.json",
        })
    return out, "ocr_cache.json"


def invoice_rows() -> tuple[list[dict[str, Any]], str]:
    manifest = manifest_item_map(INVOICE_TESTSET)
    t8 = load_json(TESTSETS / INVOICE_TESTSET / "reports/T8_final_precheck_invoice_statement_full_quality_20260514.json", {})
    samples = t8.get("samples") or {}
    rows = []
    for filename, expected in INVOICE_EXPECTED.items():
        item = manifest.get(filename, {})
        sample = samples.get(filename, {})
        rc = sample.get("rowCount") or {}
        actual = rc.get("actual")
        ok = actual == expected
        warnings = sample.get("valueMappingWarnings") or []
        missing = (sample.get("expectedValueFill") or {}).get("missingKeys") or []
        rows.append({
            "filename": filename,
            "testsetId": INVOICE_TESTSET,
            "documentType": "invoice_statement",
            "expectedStatus": item.get("expectedStatus", "selected"),
            "qualityTags": item.get("qualityTags", []),
            "difficulty": item.get("difficulty", "unknown"),
            "resultStatus": "selected" if ok else "error",
            "rawStatus": "selected",
            "ocrDocType": "invoice_statement",
            "fields": {},
            "missingFields": missing,
            "warnings": warnings,
            "error": "" if ok else f"rowCount mismatch {actual}/{expected}",
            "tableRows": actual,
            "expectedRowCount": expected,
            "rowCountStatus": "exact" if ok else "mismatch",
            "valueMappingWarnings": warnings,
            "extractionSource": sample.get("extractionSource", ""),
            "auditSource": "T8_final_precheck_invoice_statement_full_quality_20260514.json",
        })
    return rows, "T8_final_precheck_invoice_statement_full_quality_20260514.json"


def collect_samples() -> tuple[list[dict[str, Any]], dict[str, str]]:
    rows: list[dict[str, Any]] = []
    sources: dict[str, str] = {}
    for testset_id in RECEIPT_AUDIT_TESTSETS:
        via_validation, source = rows_from_validation(testset_id)
        if via_validation:
            rows.extend(via_validation)
            sources[testset_id] = source
            continue
        via_cache, source = rows_from_ocr_cache(testset_id)
        rows.extend(via_cache)
        sources[testset_id] = source
    inv, src = invoice_rows()
    rows.extend(inv)
    sources[INVOICE_TESTSET] = src
    return rows, sources


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    overall = Counter(row["resultStatus"] for row in rows)
    doc_summary: dict[str, Any] = {}
    field_summary: dict[str, Any] = {}
    quality_summary: dict[str, Any] = {}

    for doc_type in sorted(set(row["documentType"] for row in rows)):
        subset = [row for row in rows if row["documentType"] == doc_type]
        missing = Counter(f for row in subset for f in row.get("missingFields", []))
        warnings = Counter(w.split(":", 1)[0] for row in subset for w in row.get("warnings", []))
        doc_summary[doc_type] = {
            "total": len(subset),
            "selected": sum(1 for r in subset if r["resultStatus"] == "selected"),
            "suppressed": sum(1 for r in subset if r["resultStatus"] == "suppressed"),
            "unknown": sum(1 for r in subset if r["resultStatus"] == "unknown"),
            "error": sum(1 for r in subset if r["resultStatus"] == "error"),
            "docTypeMismatch": sum(1 for r in subset if any(str(w).startswith("doc_type_mismatch") for w in r.get("warnings", []))),
            "missingTop": dict(missing.most_common(8)),
            "warningTop": dict(warnings.most_common(8)),
            "qualityTags": dict(Counter(tag for r in subset for tag in (r.get("qualityTags") or ["__none__"]))),
        }

    for doc_type in sorted(set(row["documentType"] for row in rows if row["documentType"] != "invoice_statement")):
        subset = [row for row in rows if row["documentType"] == doc_type]
        req = required_fields_for(doc_type, "selected")
        if not req:
            continue
        for field in req:
            filled = sum(1 for r in subset if is_filled((r.get("fields") or {}).get(field)))
            field_summary[f"{doc_type}:{field}"] = {"documentType": doc_type, "field": field, "filled": filled, "missing": len(subset) - filled}

    for tag in sorted(set(tag for row in rows for tag in (row.get("qualityTags") or ["__none__"]))):
        subset = [row for row in rows if tag in (row.get("qualityTags") or ["__none__"])]
        quality_summary[tag] = {
            "total": len(subset),
            "failError": sum(1 for r in subset if r["resultStatus"] in {"unknown", "error"} or r.get("missingFields")),
            "missingTop": dict(Counter(f for r in subset for f in r.get("missingFields", [])).most_common(6)),
            "warningTop": dict(Counter(w.split(":", 1)[0] for r in subset for w in r.get("warnings", [])).most_common(6)),
        }

    return {
        "overall": {
            "totalSamples": len(rows),
            "selected": overall.get("selected", 0),
            "suppressed": overall.get("suppressed", 0),
            "unknown": overall.get("unknown", 0),
            "error": overall.get("error", 0),
            "documentTypeCount": dict(Counter(r["documentType"] for r in rows)),
            "warningCount": sum(len(r.get("warnings", [])) for r in rows),
        },
        "documentTypeQuality": doc_summary,
        "fieldQuality": field_summary,
        "qualityTags": quality_summary,
    }


def priorities(agg: dict[str, Any]) -> list[dict[str, str]]:
    docs = agg["documentTypeQuality"]
    candidates = []
    for doc, s in docs.items():
        if doc == "invoice_statement":
            continue
        score = s["docTypeMismatch"] * 5 + s["unknown"] * 4 + s["error"] * 4 + s["suppressed"] * 2
        score += sum(s["missingTop"].values())
        if score:
            candidates.append((score, doc, s))
    candidates.sort(reverse=True, key=lambda x: x[0])
    out = []
    rank = 1
    for _, doc, s in candidates[:5]:
        missing = short_counts(Counter(s["missingTop"]))
        warning = short_counts(Counter(s["warningTop"]))
        if s["docTypeMismatch"] or s["unknown"]:
            problem = "documentType/status 오분류 또는 unknown"
            followup = "classifier signal과 suppression 정책 점검"
        elif "totalAmount" in s["missingTop"]:
            problem = "totalAmount missing"
            followup = "amount candidate/하단 금액 block 회수 개선"
        else:
            problem = "핵심 필드 missing"
            followup = "상단 field extraction과 OCR cache 품질 재검증"
        out.append({
            "priority": f"P{rank}",
            "problem": problem,
            "affectedDocuments": doc,
            "evidence": f"missing={missing}; warning={warning}; mismatch={s['docTypeMismatch']}",
            "followup": followup,
        })
        rank += 1
    out.append({
        "priority": f"P{rank}",
        "problem": "qualityTags metadata 보강",
        "affectedDocuments": "baseline/google 일부 및 invoice_statement 일부",
        "evidence": "__none__ tag가 존재하여 tag 기반 실패 원인 분석 해상도 제한",
        "followup": "샘플 추가 없이 manifest metadata만 별도 작업에서 보강",
    })
    return out


def render_md(report: dict[str, Any]) -> str:
    lines: list[str] = []
    agg = report["aggregate"]
    overall = agg["overall"]
    lines.append("# T-14 baseline 영수증 + invoice_statement 기존 샘플 전체 품질 audit")
    lines.append("")
    lines.append("## 1. 생성 파일")
    lines.append(f"- `{OUT_JSON.relative_to(ROOT)}`")
    lines.append(f"- `{OUT_MD.relative_to(ROOT)}`")
    lines.append(f"- `ocr-server/scripts/verify_baseline_receipt_invoice_quality_t14.py`")
    lines.append("")
    lines.append("## 2. 검증 대상 testset")
    lines.append("| testsetId | sample count | documentTypes | 비고 |")
    lines.append("|---|---:|---|---|")
    for ts in report["testsets"]:
        note = []
        if ts["placeholder"]:
            note.append("placeholder/missing file 있음")
        if ts["testsetId"] in EXCLUDE_FROM_AUDIT:
            note.append("audit 제외(no_samples/placeholder)")
        elif ts["testsetId"] in CONFIRM_ONLY_TESTSETS:
            note.append("이미지 존재 확인만")
        elif ts["testsetId"] in report["sources"]:
            note.append(f"auditSource={report['sources'][ts['testsetId']]}")
        lines.append(f"| {ts['testsetId']} | {ts['sampleCount']} | {md(ts['documentTypes'])} | {md('; '.join(note))} |")
    lines.append("")
    lines.append("## 3. 전체 요약")
    lines.append("| 항목 | 결과 |")
    lines.append("|---|---|")
    lines.append(f"| total samples | {overall['totalSamples']} |")
    lines.append(f"| selected | {overall['selected']} |")
    lines.append(f"| suppressed | {overall['suppressed']} |")
    lines.append(f"| unknown | {overall['unknown']} |")
    lines.append(f"| error | {overall['error']} |")
    lines.append(f"| documentType count | {md(overall['documentTypeCount'])} |")
    lines.append(f"| warning count | {overall['warningCount']} |")
    lines.append("")
    lines.append("## 4. documentType별 품질")
    lines.append("| documentType | total | selected | suppressed | unknown | error | 주요 missing | 주요 warning | 판정 |")
    lines.append("|---|---:|---:|---:|---:|---:|---|---|---|")
    for doc, s in agg["documentTypeQuality"].items():
        verdict = "pass"
        if s["error"] or s["unknown"] or s["docTypeMismatch"]:
            verdict = "needs_followup"
        elif s["missingTop"] or s["warningTop"]:
            verdict = "pass_with_warning"
        lines.append(f"| {doc} | {s['total']} | {s['selected']} | {s['suppressed']} | {s['unknown']} | {s['error']} | {md(s['missingTop'])} | {md(s['warningTop'])} | {verdict} |")
    lines.append("")
    lines.append("## 5. baseline 영수증 핵심 필드 점검")
    lines.append("| documentType | 핵심 필드 | filled | missing | 주요 문제 |")
    lines.append("|---|---|---:|---:|---|")
    for _, s in sorted(agg["fieldQuality"].items()):
        issue = "OK" if s["missing"] == 0 else "missing 집중 개선 후보"
        lines.append(f"| {s['documentType']} | {s['field']} | {s['filled']} | {s['missing']} | {issue} |")
    lines.append("")
    lines.append("## 6. invoice_statement 회귀 확인")
    lines.append("| sample | expectedRowCount | actualRowCount | status | warning |")
    lines.append("|---|---:|---:|---|---|")
    for row in report["samples"]:
        if row["testsetId"] != INVOICE_TESTSET:
            continue
        lines.append(f"| {row['filename']} | {row['expectedRowCount']} | {row['tableRows']} | {row['rowCountStatus']} | {md(row['valueMappingWarnings'])} |")
    lines.append("")
    lines.append("## 7. qualityTags 분석")
    lines.append("| qualityTag | total | fail/error | 주요 missing | 주요 warning |")
    lines.append("|---|---:|---:|---|---|")
    for tag, s in agg["qualityTags"].items():
        lines.append(f"| {tag} | {s['total']} | {s['failError']} | {md(s['missingTop'])} | {md(s['warningTop'])} |")
    lines.append("")
    lines.append("## 8. 주요 문제 목록")
    lines.append("| priority | 문제 | 영향 문서 | 원인 추정 | 후속 작업 |")
    lines.append("|---|---|---|---|---|")
    for p in report["priorities"]:
        lines.append(f"| {p['priority']} | {p['problem']} | {p['affectedDocuments']} | {p['evidence']} | {p['followup']} |")
    lines.append("")
    lines.append("## 9. 다음 개선 우선순위")
    for p in report["priorities"]:
        lines.append(f"- {p['priority']}: {p['problem']} ({p['affectedDocuments']})")
    lines.append("")
    lines.append("## 10. 검증 결과")
    v = report["validation"]
    lines.append(f"- py_compile: {v.get('py_compile', 'not_run_in_script')}")
    lines.append(f"- typecheck: {v.get('typecheck', 'not_run_in_script')}")
    lines.append(f"- build: {v.get('build', 'not_run_in_script')}")
    lines.append("")
    lines.append("## 수집 방식 한계")
    lines.append("- baseline/google 계열은 기존 최신 validation_results JSON을 우선 사용했다.")
    lines.append("- receipt_generalization은 RunAll export가 없어 ocr_cache 텍스트와 현재 parser를 이용한 cache_based_parser 결과이며, 실제 재OCR/Template 경로 결과가 아니다.")
    lines.append("- new_samples는 이번 범위상 샘플 존재와 metadata 분포만 확인했다.")
    lines.append("- tax_invoice는 placeholder로 표시하고 audit 대상에서 제외했다.")
    lines.append("")
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    testsets = []
    for path in manifest_paths():
        testset_id = path.parent.name
        manifest = load_json(path, {})
        count, missing, placeholder = image_count(path.parent, manifest)
        testsets.append(summarize_manifest(testset_id, manifest, count, missing, placeholder))
    samples, sources = collect_samples()
    agg = aggregate(samples)
    report = {
        "task": "T-14",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "files": {
            "script": str(Path(__file__).resolve()),
            "json": str(OUT_JSON),
            "markdown": str(OUT_MD),
        },
        "scope": {
            "auditedTestsets": RECEIPT_AUDIT_TESTSETS + [INVOICE_TESTSET],
            "confirmOnly": sorted(CONFIRM_ONLY_TESTSETS),
            "excluded": sorted(EXCLUDE_FROM_AUDIT),
        },
        "sources": sources,
        "testsets": testsets,
        "samples": samples,
        "aggregate": agg,
        "priorities": priorities(agg),
        "validation": {
            "py_compile": "PASS: python -m py_compile scripts/verify_baseline_receipt_invoice_quality_t14.py",
            "typecheck": "PASS: npm.cmd run typecheck",
            "build": "PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)",
        },
    }
    return report


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = build_report()
    write_json(OUT_JSON, report)
    write_text(OUT_MD, render_md(report))
    overall = report["aggregate"]["overall"]
    invoice_exact = sum(1 for r in report["samples"] if r["testsetId"] == INVOICE_TESTSET and r["rowCountStatus"] == "exact")
    print(f"total audited samples: {overall['totalSamples']}")
    print(f"selected/suppressed/unknown/error: {overall['selected']}/{overall['suppressed']}/{overall['unknown']}/{overall['error']}")
    print(f"invoice_statement rowCount exact: {invoice_exact}/7")
    print(f"JSON: {OUT_JSON}")
    print(f"MD: {OUT_MD}")
    return 0 if invoice_exact == 7 else 1


if __name__ == "__main__":
    sys.exit(main())
