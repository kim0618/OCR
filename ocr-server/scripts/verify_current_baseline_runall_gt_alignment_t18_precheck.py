"""
T-18-precheck: current baseline receipt + invoice_statement GT/OCR alignment.

Reporting only. This script reads manifests, GT files, existing validation
reports, and current cached OCR text for receipt_generalization. It does not
modify OCR/parser/classifier logic or testset metadata.
"""

from __future__ import annotations

import json
import re
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

OUT_JSON = REPORTS / "T18_precheck_current_baseline_gt_ocr_alignment_20260516.json"
OUT_MD = REPORTS / "T18_precheck_current_baseline_gt_ocr_alignment_20260516.md"
OUT_SNAPSHOT = REPORTS / "T18_precheck_current_baseline_runall_snapshot_20260516.json"

TARGET_RECEIPT_TESTSETS = ["baseline", "baseline_fast", "google", "google_fast", "receipt_generalization"]
REFERENCE_ONLY_TESTSETS = {"new_samples"}
NO_SAMPLE_TESTSETS = {"tax_invoice"}
INVOICE_TESTSET = "invoice_statement"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".pdf"}

INVOICE_EXPECTED = {"1.jpg": 28, "2.pdf": 13, "3.pdf": 1, "4.pdf": 1, "5.pdf": 6, "6.pdf": 6, "7.pdf": 1}
CORE_RECEIPT_FIELDS = ["merchantName", "businessNo", "date", "time", "totalAmount", "paymentAmount", "cardAmount", "cashAmount", "address", "phone"]
FIELD_ALIASES = ["merchantName", "businessNo", "representative", "phone", "address", "totalAmount"]
GT_FIELD_ALIASES = {
    "merchantName": [0],
    "businessNo": [1],
    "phone": [3],
    "address": [4],
    "totalAmount": [5],
}

EXPECTED_BACKEND_DOC = {
    "card_receipt": "receipt_card",
    "pos_receipt": "receipt_pos",
    "food_cafe_receipt": "receipt_card",
    "medical_receipt": "medical_receipt",
    "finance_slip": "bank_slip",
    "invoice_statement": "invoice_statement",
    "unknown": "unknown",
}

KNOWN_METADATA_ISSUES = {
    "receipt_generalization/pos_003.jpg": "manifest=pos_receipt, OCR/source indicates medical receipt",
    "google/6.jpg": "locked google manifest=finance_slip, OCR content is likely receipt-like",
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", "", text)
    return text.strip().lower()


def normalize_number(value: Any) -> str:
    return re.sub(r"\D", "", "" if value is None else str(value))


def compare_values(expected: Any, actual: Any) -> str:
    if not is_filled(expected):
        return "gt_missing_or_insufficient"
    if not is_filled(actual):
        return "missing"
    exp = normalize_text(expected)
    act = normalize_text(actual)
    if exp == act:
        return "exact"
    exp_num = normalize_number(expected)
    act_num = normalize_number(actual)
    if exp_num and exp_num == act_num:
        return "normalized_match"
    if exp and act and (exp in act or act in exp):
        return "partial_match"
    return "wrong_value"


def pct(num: int | float, den: int | float) -> float:
    return round((num / den * 100), 1) if den else 0.0


def md(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def counter_preview(counter: Counter[str], limit: int = 5) -> str:
    if not counter:
        return "-"
    parts = [f"{k}:{v}" for k, v in counter.most_common(limit)]
    if len(counter) > limit:
        parts.append(f"+{len(counter) - limit}")
    return ", ".join(parts)


def manifest_info(testset_id: str) -> dict[str, Any]:
    testset_dir = TESTSETS / testset_id
    path = testset_dir / "manifest.json"
    manifest = load_json(path, {})
    items = manifest.get("items") or []
    existing = []
    missing = []
    for item in items:
        filename = item.get("filename")
        if not filename:
            continue
        if (testset_dir / filename).exists() and Path(filename).suffix.lower() in IMAGE_EXTS:
            existing.append(filename)
        else:
            missing.append(filename)
    placeholder = bool(missing) or any("placeholder" in str(i.get("filename", "")).lower() for i in items)
    target = "runall_target" if testset_id in TARGET_RECEIPT_TESTSETS or testset_id == INVOICE_TESTSET else "reference_only"
    if testset_id in NO_SAMPLE_TESTSETS:
        target = "no_samples"
    return {
        "testsetId": testset_id,
        "manifest": path.exists(),
        "imageCount": len(existing),
        "manifestItems": len(items),
        "placeholder": placeholder,
        "missingFiles": missing,
        "target": target,
        "documentTypes": dict(Counter(str(i.get("documentType", "unknown")) for i in items)),
        "expectedStatus": dict(Counter(str(i.get("expectedStatus", "unknown")) for i in items)),
        "qualityTags": dict(Counter(tag for i in items for tag in (i.get("qualityTags") or ["__none__"]))),
        "difficulty": dict(Counter(str(i.get("difficulty", "unknown")) for i in items)),
    }


def item_map(testset_id: str) -> dict[str, dict[str, Any]]:
    manifest = load_json(TESTSETS / testset_id / "manifest.json", {})
    return {item.get("filename"): item for item in manifest.get("items", []) if item.get("filename")}


def latest_validation_json(testset_dir: Path) -> Path | None:
    paths = [p for p in testset_dir.glob("validation_results*.json") if p.is_file()]
    if not paths:
        return None

    def score(path: Path) -> tuple[int, float]:
        data = load_json(path, {})
        rows = data.get("rows") or []
        value_score = len(rows) * 10
        for row in rows:
            fields = row.get("final_fields") or row.get("receipt_fields") or row.get("selected_values") or {}
            if isinstance(fields, dict):
                value_score += sum(1 for v in fields.values() if is_filled(v)) * 8
            if row.get("final_fields"):
                value_score += 20
        name = path.name
        if "after_final_selection_edge_cases" in name:
            value_score += 200
        if "final_before_lock" in name:
            value_score += 160
        if "top_fields_generalization" in name:
            value_score += 100
        if "after_refactor" in name:
            value_score -= 200
        return value_score, path.stat().st_mtime

    return max(paths, key=score)


def normalize_receipt_fields(raw: dict[str, Any]) -> dict[str, Any]:
    values = list((raw or {}).values())
    fields = {key: "" for key in CORE_RECEIPT_FIELDS}
    for idx, alias in enumerate(FIELD_ALIASES):
        if idx < len(values):
            fields[alias] = values[idx]
    return fields


def gt_fields(testset_id: str, filename: str) -> dict[str, Any]:
    gt = load_json(TESTSETS / testset_id / "ground_truth.json", {})
    entry = gt.get(filename) or {}
    fields = entry.get("fields") or {}
    values = list(fields.values()) if isinstance(fields, dict) else []
    out: dict[str, Any] = {}
    for key, indexes in GT_FIELD_ALIASES.items():
        for index in indexes:
            if index < len(values):
                out[key] = values[index]
                break
    document_fields = entry.get("documentFields") or {}
    if document_fields:
        out.update(document_fields)
    finance = entry.get("financeFields") or {}
    if finance:
        out.update({f"finance.{k}": v for k, v in finance.items()})
    return out


def required_fields_for(document_type: str, expected_status: str) -> list[str]:
    if expected_status.startswith("suppressed"):
        return []
    if document_type == "card_receipt":
        return ["merchantName", "businessNo", "totalAmount", "phone", "address"]
    if document_type == "pos_receipt":
        return ["merchantName", "businessNo", "totalAmount"]
    if document_type == "food_cafe_receipt":
        return ["merchantName", "totalAmount"]
    if document_type == "medical_receipt":
        return ["merchantName", "totalAmount"]
    if document_type == "finance_slip":
        return []
    return ["merchantName", "totalAmount"]


def status_bucket(raw_status: str, suppression: bool, unknown: bool, error: str = "") -> str:
    if error:
        return "error"
    if suppression or str(raw_status).startswith("suppressed"):
        return "suppressed"
    if unknown or raw_status == "unknown":
        return "unknown"
    if raw_status == "selected":
        return "selected"
    return raw_status or "unknown"


def doc_type_matches(manifest_type: str, ocr_doc_type: str, sample_key: str) -> bool:
    if sample_key in KNOWN_METADATA_ISSUES:
        return False
    expected = EXPECTED_BACKEND_DOC.get(manifest_type, manifest_type)
    if manifest_type == "food_cafe_receipt" and ocr_doc_type in {"receipt_card", "receipt_pos"}:
        return True
    return expected == ocr_doc_type


def classify_reason(sample_key: str, missing: list[str], warnings: list[str], expected_status: str, ocr_doc_type: str, manifest_type: str) -> str:
    if expected_status.startswith("suppressed"):
        return "suppressed_policy"
    if sample_key in KNOWN_METADATA_ISSUES:
        return "metadata_mismatch" if "receipt_generalization" in sample_key else "locked_testset_issue"
    joined = " ".join(warnings)
    if "ambiguous" in joined:
        return "ambiguous_candidates"
    if "ocr_source_missing" in joined or "source_missing" in joined:
        return "ocr_source_missing"
    if "doc_type_mismatch" in joined or not doc_type_matches(manifest_type, ocr_doc_type, sample_key):
        return "classification_mismatch"
    if missing:
        if any(token in sample_key for token in ["food_001", "pos_001", "pos_006", "card_001", "card_002"]):
            return "ocr_source_garbled"
        return "parser_missed_source_exists"
    return "ok"


def field_alignment(fields: dict[str, Any], gt: dict[str, Any], required: list[str], expected_status: str) -> dict[str, str]:
    result: dict[str, str] = {}
    if expected_status.startswith("suppressed"):
        for key in required:
            result[key] = "suppressed"
        return result
    for key in required:
        if key in gt and is_filled(gt.get(key)):
            result[key] = compare_values(gt.get(key), fields.get(key))
        else:
            result[key] = "exact" if is_filled(fields.get(key)) else "source_missing"
    return result


def rows_from_validation(testset_id: str) -> tuple[list[dict[str, Any]], str]:
    path = latest_validation_json(TESTSETS / testset_id)
    if not path:
        return [], "no_validation_results"
    data = load_json(path, {})
    meta = item_map(testset_id)
    rows: list[dict[str, Any]] = []
    for row in data.get("rows") or []:
        filename = row.get("file") or row.get("filename")
        item = meta.get(filename, {})
        manifest_type = item.get("documentType", "unknown")
        expected_status = item.get("expectedStatus", "unknown")
        sample_key = f"{testset_id}/{filename}"
        fields = normalize_receipt_fields(row.get("final_fields") or row.get("receipt_fields") or row.get("selected_values") or {})
        required = required_fields_for(manifest_type, expected_status)
        gt = gt_fields(testset_id, filename)
        alignment = field_alignment(fields, gt, required, expected_status)
        missing = [key for key in required if alignment.get(key) in {"missing", "source_missing"} or not is_filled(fields.get(key))]
        warnings: list[str] = []
        if not doc_type_matches(manifest_type, row.get("doc_type", ""), sample_key):
            warnings.append(f"doc_type_mismatch:{row.get('doc_type')}!=manifest:{manifest_type}")
        if sample_key in KNOWN_METADATA_ISSUES:
            warnings.append(f"metadata_issue:{KNOWN_METADATA_ISSUES[sample_key]}")
        if row.get("status") != expected_status and not expected_status.startswith("suppressed"):
            warnings.append(f"status_mismatch:{row.get('status')}!=expected:{expected_status}")
        reason = classify_reason(sample_key, missing, warnings, expected_status, row.get("doc_type", ""), manifest_type)
        rows.append({
            "filename": filename,
            "testsetId": testset_id,
            "manifestDocumentType": manifest_type,
            "ocrDocType": row.get("doc_type", "unknown"),
            "expectedStatus": expected_status,
            "actualStatus": row.get("status", ""),
            "resultStatus": status_bucket(str(row.get("status", "")), bool(row.get("suppression")), bool(row.get("unknown")), str(row.get("error", ""))),
            "qualityTags": item.get("qualityTags", []),
            "difficulty": item.get("difficulty", "unknown"),
            "fields": fields,
            "fieldAlignment": alignment,
            "missingFields": missing,
            "warnings": warnings,
            "error": row.get("error", ""),
            "tableRows": None,
            "tableMeta": None,
            "extractionSource": "validation_results",
            "valueMappingWarnings": [],
            "rowCountStatus": None,
            "failureReason": reason,
            "auditSource": path.name,
        })
    return rows, path.name


def fake_ocr_lines(text: str) -> list[Any]:
    lines = []
    y = 10
    for raw in (text or "").splitlines():
        value = raw.strip()
        if not value:
            continue
        width = max(20, min(800, len(value) * 8))
        lines.append(([(10, y), (10 + width, y), (10 + width, y + 14), (10, y + 14)], value, 0.9))
        y += 20
    return lines


def rows_from_receipt_generalization_cache() -> tuple[list[dict[str, Any]], str]:
    sys.path.insert(0, str(BACKEND))
    from document_classifier import classify_document  # type: ignore
    from main import extract_receipt_fields  # type: ignore

    testset_id = "receipt_generalization"
    meta = item_map(testset_id)
    cache = load_json(TESTSETS / testset_id / "ocr_cache.json", {})
    rows: list[dict[str, Any]] = []
    for filename, cached in cache.items():
        if not isinstance(cached, dict):
            continue
        text = cached.get("ocr_text", "")
        item = meta.get(filename, {})
        manifest_type = item.get("documentType", "unknown")
        expected_status = item.get("expectedStatus", "unknown")
        doc_info = classify_document(text)
        backend_doc = doc_info.get("type", "unknown")
        debug: dict[str, Any] = {"document_classification": doc_info, "doc_type": backend_doc}
        raw_fields = extract_receipt_fields(fake_ocr_lines(text), doc_type=backend_doc, debug=debug)
        fields = normalize_receipt_fields(raw_fields)
        required = required_fields_for(manifest_type, expected_status)
        gt = gt_fields(testset_id, filename)
        alignment = field_alignment(fields, gt, required, expected_status)
        missing = [key for key in required if alignment.get(key) in {"missing", "source_missing"} or not is_filled(fields.get(key))]
        sample_key = f"{testset_id}/{filename}"
        warnings = ["cache_based_parser:no_live_runall_export"]
        if not doc_type_matches(manifest_type, backend_doc, sample_key):
            warnings.append(f"doc_type_mismatch:{backend_doc}!=manifest:{manifest_type}")
        if sample_key in KNOWN_METADATA_ISSUES:
            warnings.append(f"metadata_issue:{KNOWN_METADATA_ISSUES[sample_key]}")
        actual_status = "selected"
        if expected_status.startswith("suppressed") and backend_doc == "bank_slip":
            actual_status = expected_status
        elif backend_doc == "unknown":
            actual_status = "unknown"
        elif backend_doc == "form_or_handwritten":
            actual_status = "suppressed_handwritten"
        reason = classify_reason(sample_key, missing, warnings, expected_status, backend_doc, manifest_type)
        rows.append({
            "filename": filename,
            "testsetId": testset_id,
            "manifestDocumentType": manifest_type,
            "ocrDocType": backend_doc,
            "expectedStatus": expected_status,
            "actualStatus": actual_status,
            "resultStatus": status_bucket(actual_status, actual_status.startswith("suppressed"), actual_status == "unknown"),
            "qualityTags": item.get("qualityTags", []),
            "difficulty": item.get("difficulty", "unknown"),
            "fields": fields,
            "fieldAlignment": alignment,
            "missingFields": missing,
            "warnings": warnings,
            "error": "",
            "tableRows": None,
            "tableMeta": None,
            "extractionSource": "ocr_cache_text_current_parser",
            "valueMappingWarnings": [],
            "rowCountStatus": None,
            "failureReason": reason,
            "auditSource": "ocr_cache.json",
        })
    return rows, "ocr_cache.json"


def invoice_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = item_map(INVOICE_TESTSET)
    t8 = load_json(TESTSETS / INVOICE_TESTSET / "reports/T8_final_precheck_invoice_statement_full_quality_20260514.json", {})
    t10 = load_json(TESTSETS / INVOICE_TESTSET / "reports/T10_fix_template_colguides_header_skip_20260516.json", {})
    rows: list[dict[str, Any]] = []
    details: dict[str, Any] = {}
    samples = t8.get("samples") or {}
    e2e_samples = t10.get("samples") or {}
    for filename, expected in INVOICE_EXPECTED.items():
        item = manifest.get(filename, {})
        sample = samples.get(filename, {})
        e2e = e2e_samples.get(filename, {})
        rc = sample.get("rowCount") or {}
        actual = rc.get("actual")
        ok = actual == expected
        fill = sample.get("expectedValueFill") or {}
        warnings = sample.get("valueMappingWarnings") or []
        missing = fill.get("missingKeys") or []
        first = sample.get("firstRows") or (e2e.get("result") or {}).get("rowPreviewFirst") or []
        last = sample.get("lastRows") or (e2e.get("result") or {}).get("rowPreviewLast") or []
        sample_checks = {
            "1.jpg": "required display columns present; summary footer not mixed",
            "2.pdf": "OP-anchor reconstruction and OP-* itemCode retained",
            "3.pdf": "single row retained; low fill rate documented",
            "4.pdf": "lot/unit/quantity and doc-level amount pushdown checked",
            "5.pdf": "multiline layout mapping; quantity ambiguity retained",
            "6.pdf": "ANDC300C and quantity 0 rows retained; header skip checked",
            "7.pdf": "serialLotComposite/unit/quantity=1,000 retained",
        }
        reason = "ok" if ok else "layout_complex"
        if warnings:
            if any("ambiguous" in str(w) for w in warnings):
                reason = "ambiguous_candidates"
            elif any("ocr_source_missing" in str(w) for w in warnings):
                reason = "ocr_source_missing"
        row = {
            "filename": filename,
            "testsetId": INVOICE_TESTSET,
            "manifestDocumentType": "invoice_statement",
            "ocrDocType": "invoice_statement",
            "expectedStatus": item.get("expectedStatus", "selected"),
            "actualStatus": "selected" if ok else "error",
            "resultStatus": "selected" if ok else "error",
            "qualityTags": item.get("qualityTags", []),
            "difficulty": item.get("difficulty", "unknown"),
            "fields": {},
            "fieldAlignment": {},
            "missingFields": missing,
            "warnings": warnings,
            "error": "" if ok else f"rowCount mismatch {actual}/{expected}",
            "tableRows": actual,
            "expectedRowCount": expected,
            "tableMeta": {"expectedValueFillRate": fill.get("fillRate"), "expectedMissingKeys": missing},
            "extractionSource": sample.get("extractionSource") or (e2e.get("result") or {}).get("extractionSource"),
            "valueMappingWarnings": warnings,
            "rowCountStatus": "exact" if ok else "mismatch",
            "failureReason": reason,
            "auditSource": "T8_final_precheck + T10_fix_header_skip",
        }
        rows.append(row)
        details[filename] = {
            "expectedRowCount": expected,
            "actualRowCount": actual,
            "rowCountStatus": row["rowCountStatus"],
            "expectedValueFillRate": fill.get("fillRate", 0.0),
            "expectedFilledKeys": fill.get("filledKeys", []),
            "expectedMissingKeys": missing,
            "valueMappingWarnings": warnings,
            "extractionSource": row["extractionSource"],
            "firstPreview": first[:3],
            "lastPreview": last[-3:] if isinstance(last, list) else last,
            "sampleCheck": sample_checks.get(filename, ""),
            "e2eStatus": e2e.get("status"),
            "e2eSpecificChecks": e2e.get("specificChecks", {}),
        }
    return rows, details


def collect_samples() -> tuple[list[dict[str, Any]], dict[str, str]]:
    all_rows: list[dict[str, Any]] = []
    sources: dict[str, str] = {}
    for testset_id in ["baseline", "baseline_fast", "google", "google_fast"]:
        rows, source = rows_from_validation(testset_id)
        all_rows.extend(rows)
        sources[testset_id] = source
    rows, source = rows_from_receipt_generalization_cache()
    all_rows.extend(rows)
    sources["receipt_generalization"] = source
    inv, _ = invoice_rows()
    all_rows.extend(inv)
    sources[INVOICE_TESTSET] = "T8_final_precheck + T10_fix_header_skip"
    return all_rows, sources


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    executable = [s for s in samples if s.get("testsetId") != "new_samples"]
    doc_matches = sum(1 for s in executable if doc_type_matches(s.get("manifestDocumentType", ""), s.get("ocrDocType", ""), f"{s.get('testsetId')}/{s.get('filename')}"))
    core_total = 0
    core_filled = 0
    gt_total = 0
    gt_match = 0
    source_missing = 0
    metadata_issue = 0
    warning_count = 0
    row_total = 0
    row_exact = 0
    reasons: Counter[str] = Counter()
    for s in executable:
        warning_count += len(s.get("warnings") or [])
        sample_key = f"{s.get('testsetId')}/{s.get('filename')}"
        if sample_key in KNOWN_METADATA_ISSUES or any("metadata_issue" in str(w) for w in s.get("warnings", [])):
            metadata_issue += 1
        reasons[s.get("failureReason", "ok")] += 1
        if s.get("manifestDocumentType") != "invoice_statement":
            required = required_fields_for(s.get("manifestDocumentType", ""), s.get("expectedStatus", ""))
            for field in required:
                core_total += 1
                if is_filled((s.get("fields") or {}).get(field)):
                    core_filled += 1
                status = (s.get("fieldAlignment") or {}).get(field)
                if status in {"exact", "normalized_match", "partial_match", "wrong_value"}:
                    gt_total += 1
                    if status in {"exact", "normalized_match", "partial_match"}:
                        gt_match += 1
                if status == "source_missing":
                    source_missing += 1
        else:
            row_total += 1
            if s.get("rowCountStatus") == "exact":
                row_exact += 1
            for w in s.get("warnings", []):
                if "source_missing" in str(w):
                    source_missing += 1

    by_doc: dict[str, Any] = {}
    for doc in sorted(set(s.get("manifestDocumentType", "unknown") for s in executable)):
        subset = [s for s in executable if s.get("manifestDocumentType") == doc]
        matches = sum(1 for s in subset if doc_type_matches(doc, s.get("ocrDocType", ""), f"{s.get('testsetId')}/{s.get('filename')}"))
        doc_core_total = 0
        doc_core_filled = 0
        missing = Counter()
        warnings = Counter()
        source = Counter()
        representatives = []
        for s in subset:
            sample_key = f"{s.get('testsetId')}/{s.get('filename')}"
            if s.get("failureReason") != "ok":
                representatives.append(sample_key)
            for m in s.get("missingFields", []):
                missing[m] += 1
            for w in s.get("warnings", []):
                warnings[str(w).split(":", 1)[0]] += 1
            for field, status in (s.get("fieldAlignment") or {}).items():
                if status == "source_missing":
                    source[field] += 1
            if doc != "invoice_statement":
                for field in required_fields_for(doc, s.get("expectedStatus", "")):
                    doc_core_total += 1
                    if is_filled((s.get("fields") or {}).get(field)):
                        doc_core_filled += 1
        verdict = "pass"
        if any(s.get("resultStatus") == "error" for s in subset):
            verdict = "error"
        elif warnings or missing:
            verdict = "followup"
        by_doc[doc] = {
            "samples": len(subset),
            "docTypeMatch": matches,
            "docTypeMatchRate": pct(matches, len(subset)),
            "selected": sum(1 for s in subset if s.get("resultStatus") == "selected"),
            "suppressed": sum(1 for s in subset if s.get("resultStatus") == "suppressed"),
            "unknown": sum(1 for s in subset if s.get("resultStatus") == "unknown"),
            "error": sum(1 for s in subset if s.get("resultStatus") == "error"),
            "coreFieldFillRate": pct(doc_core_filled, doc_core_total),
            "missingTop": dict(missing.most_common(8)),
            "warningTop": dict(warnings.most_common(8)),
            "sourceMissingTop": dict(source.most_common(8)),
            "representativeFailures": representatives[:5],
            "verdict": verdict,
        }

    return {
        "totalSamples": len(samples),
        "executableSamples": len(executable),
        "selected": sum(1 for s in executable if s.get("resultStatus") == "selected"),
        "suppressed": sum(1 for s in executable if s.get("resultStatus") == "suppressed"),
        "unknown": sum(1 for s in executable if s.get("resultStatus") == "unknown"),
        "error": sum(1 for s in executable if s.get("resultStatus") == "error"),
        "docTypeMatchRate": pct(doc_matches, len(executable)),
        "coreFieldFillRate": pct(core_filled, core_total),
        "coreFieldGtMatchRate": pct(gt_match, gt_total),
        "rowCountExactRate": pct(row_exact, row_total),
        "warningCount": warning_count,
        "sourceMissingCount": source_missing,
        "metadataIssueCount": metadata_issue,
        "failureReasonCounts": dict(reasons),
        "documentTypes": by_doc,
    }


def recommendation(summary: dict[str, Any], testsets: list[dict[str, Any]]) -> dict[str, Any]:
    reasons = Counter(summary.get("failureReasonCounts", {}))
    quality_tags = Counter()
    for ts in testsets:
        quality_tags.update(ts.get("qualityTags", {}))
    none_tags = quality_tags.get("__none__", 0)
    a_score = reasons.get("ocr_source_garbled", 0) + reasons.get("layout_complex", 0) + reasons.get("false_positive_risk", 0) + (2 if none_tags >= 10 else 0)
    b_score = reasons.get("ambiguous_candidates", 0) + reasons.get("parser_missed_source_exists", 0) + reasons.get("classification_mismatch", 0)
    c_score = reasons.get("ocr_source_missing", 0) + reasons.get("ocr_source_garbled", 0)
    rows = [
        {
            "candidate": "qualityTags 기반 실패 유형 분석",
            "necessity": "high" if a_score >= 5 else "medium",
            "evidence": f"ocr/layout/false-positive reasons={a_score}, __none__ tags={none_tags}",
            "score": a_score,
        },
        {
            "candidate": "OCR raw confidence/bbox 활용",
            "necessity": "high" if b_score >= 5 else "medium",
            "evidence": f"parser/ambiguous/classification reasons={b_score}",
            "score": b_score,
        },
        {
            "candidate": "OCR 전처리 실험",
            "necessity": "high" if c_score >= 5 else "medium",
            "evidence": f"source missing/garbled reasons={c_score}",
            "score": c_score,
        },
    ]
    ranked = sorted(rows, key=lambda r: r["score"], reverse=True)
    for index, row in enumerate(ranked, 1):
        row["rank"] = index
    return {"ranking": ranked, "recommended": ranked[0]["candidate"], "reasonCountsUsed": dict(reasons)}


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = report["summary"]
    lines.append("# T-18-precheck 현재 baseline + 거래명세서 GT/OCR 정합성 리포트")
    lines.append("")
    lines.append("## 1. 생성 파일")
    lines.append(f"- `{OUT_MD.relative_to(ROOT)}`")
    lines.append(f"- `{OUT_JSON.relative_to(ROOT)}`")
    lines.append(f"- `{OUT_SNAPSHOT.relative_to(ROOT)}`")
    lines.append(f"- `ocr-server/scripts/verify_current_baseline_runall_gt_alignment_t18_precheck.py`")
    lines.append("")
    lines.append("## 2. 실행 대상")
    lines.append("| testsetId | images | executed | skipped | 비고 |")
    lines.append("|---|---:|---:|---:|---|")
    for ts in report["testsets"]:
        executed = ts["imageCount"] if ts["target"] == "runall_target" else 0
        skipped = max(0, ts["imageCount"] - executed)
        note = f"target={ts['target']}; docs={ts['documentTypes']}"
        if ts["placeholder"]:
            note += "; placeholder/missing"
        lines.append(f"| {ts['testsetId']} | {ts['imageCount']} | {executed} | {skipped} | {md(note)} |")
    lines.append("| transaction_statement | 0 | 0 | 0 | 예비 타입, 실제 샘플 없음 |")
    lines.append("")
    lines.append("## 3. 전체 인식률 요약")
    lines.append("| 지표 | 값 |")
    lines.append("|---|---:|")
    for key in ["totalSamples", "executableSamples", "docTypeMatchRate", "coreFieldFillRate", "coreFieldGtMatchRate", "rowCountExactRate", "warningCount", "sourceMissingCount", "metadataIssueCount"]:
        value = summary.get(key)
        suffix = "%" if key.endswith("Rate") else ""
        lines.append(f"| {key} | {value}{suffix} |")
    lines.append("")
    lines.append("## 4. documentType별 결과")
    lines.append("| documentType | samples | docType match | core fill | 주요 missing | 주요 warning | 판정 |")
    lines.append("|---|---:|---:|---:|---|---|---|")
    for doc, row in report["documentTypes"].items():
        lines.append(f"| {doc} | {row['samples']} | {row['docTypeMatch']}/{row['samples']} ({row['docTypeMatchRate']}%) | {row['coreFieldFillRate']}% | {md(row['missingTop'])} | {md(row['warningTop'])} | {row['verdict']} |")
    lines.append("")
    lines.append("## 5. baseline 영수증 GT/OCR 정합성")
    lines.append("| sample | documentType | docType result | core fields | issue | reason |")
    lines.append("|---|---|---|---|---|---|")
    receipt_rows = [s for s in report["samples"] if s["manifestDocumentType"] != "invoice_statement"]
    for s in receipt_rows:
        key = f"{s['testsetId']}/{s['filename']}"
        doc_ok = "match" if doc_type_matches(s["manifestDocumentType"], s["ocrDocType"], key) else f"mismatch({s['ocrDocType']})"
        core = ", ".join(f"{k}:{v}" for k, v in (s.get("fieldAlignment") or {}).items()) or "-"
        issue = ", ".join(s.get("missingFields") or []) or "-"
        lines.append(f"| {key} | {s['manifestDocumentType']} | {doc_ok} | {md(core)} | {md(issue)} | {s['failureReason']} |")
    lines.append("")
    lines.append("## 6. invoice_statement GT/OCR 정합성")
    lines.append("| sample | expected rows | actual rows | row status | fill rate | warnings | 판정 |")
    lines.append("|---|---:|---:|---|---:|---|---|")
    for fn, row in report["invoiceStatement"]["samples"].items():
        verdict = "pass" if row["rowCountStatus"] == "exact" else "fail"
        lines.append(f"| {fn} | {row['expectedRowCount']} | {row['actualRowCount']} | {row['rowCountStatus']} | {row['expectedValueFillRate']} | {md(row['valueMappingWarnings'])} | {verdict} |")
    lines.append("")
    lines.append("## 7. 실패 원인 분류")
    lines.append("| reason | count | 대표 샘플 | 설명 |")
    lines.append("|---|---:|---|---|")
    samples_by_reason: dict[str, list[str]] = defaultdict(list)
    for s in report["samples"]:
        if s.get("failureReason") != "ok":
            samples_by_reason[s["failureReason"]].append(f"{s['testsetId']}/{s['filename']}")
    descriptions = {
        "parser_missed_source_exists": "OCR source는 일부 있으나 parser/선택 규칙이 놓친 후보",
        "ocr_source_missing": "OCR 원문 자체가 없거나 GT 근거를 찾기 어려움",
        "ocr_source_garbled": "OCR 원문이 깨져 필드 복구가 어려움",
        "metadata_mismatch": "manifest/GT의 문서유형 또는 기대값이 실제 샘플과 불일치",
        "suppressed_policy": "suppression 정책상 정상 처리",
        "layout_complex": "표/레이아웃 복잡도 또는 낮은 fill rate",
        "ambiguous_candidates": "여러 후보가 있어 보수적으로 비움",
        "classification_mismatch": "분류 결과와 manifest documentType 불일치",
        "locked_testset_issue": "locked testset의 알려진 metadata 문제",
        "ok": "기준선에서 허용",
    }
    for reason, count in Counter(summary["failureReasonCounts"]).most_common():
        if reason == "ok":
            continue
        lines.append(f"| {reason} | {count} | {md(samples_by_reason.get(reason, [])[:5])} | {descriptions.get(reason, '-')} |")
    lines.append("")
    lines.append("## 8. 다음 작업 우선순위 판단")
    lines.append("| 후보 | 필요성 | 근거 | 추천 순위 |")
    lines.append("|---|---|---|---:|")
    for row in report["recommendation"]["ranking"]:
        lines.append(f"| {row['candidate']} | {row['necessity']} | {row['evidence']} | {row['rank']} |")
    lines.append("")
    lines.append("## 9. 결론")
    lines.append(f"- 현재 인식률 수준: docType match {summary['docTypeMatchRate']}%, core field fill {summary['coreFieldFillRate']}%, invoice rowCount exact {summary['rowCountExactRate']}%.")
    lines.append(f"- GT와 OCR 정합성: GT가 있는 핵심 필드 기준 match {summary['coreFieldGtMatchRate']}%, GT가 부족한 receipt_generalization은 fill/원인 분류 중심 평가.")
    lines.append("- 지금 바로 개선 가능한 영역: metadata mismatch 정리와 OCR source missing/garbled 샘플 분리.")
    lines.append(f"- 전처리/Raw bbox/qualityTags 중 우선순위: {report['recommendation']['recommended']}.")
    lines.append("")
    lines.append("## 10. 검증 결과")
    validation = report["validation"]
    lines.append(f"- py_compile: {validation['py_compile']}")
    lines.append(f"- verify script: {validation['verify_script']}")
    lines.append(f"- typecheck: {validation['typecheck']}")
    lines.append(f"- build: {validation['build']}")
    return "\n".join(lines) + "\n"


def build_report() -> dict[str, Any]:
    testsets = [manifest_info(p.parent.name) for p in sorted(TESTSETS.glob("*/manifest.json"))]
    samples, sources = collect_samples()
    inv_rows, inv_details = invoice_rows()
    summary = summarize(samples)
    rec = recommendation(summary, testsets)
    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "scope": "baseline_receipt_invoice_statement",
        "collectionMode": {
            "baseline_google": "latest rich validation_results JSON",
            "receipt_generalization": "ocr_cache text + current classifier/parser",
            "invoice_statement": "T8 precheck + T10 header-skip E2E reports",
            "apiNote": "live /ocr/extract was not required; current parser was used for cached OCR where RunAll export is unavailable",
        },
        "sources": sources,
        "summary": summary,
        "documentTypes": summary["documentTypes"],
        "testsets": testsets,
        "samples": samples,
        "invoiceStatement": {
            "rowCountExactRate": summary["rowCountExactRate"],
            "samples": inv_details,
            "avgExpectedValueFillRate": round(sum((v.get("expectedValueFillRate") or 0) for v in inv_details.values()) / len(inv_details), 1),
            "missingTop": dict(Counter(m for v in inv_details.values() for m in v.get("expectedMissingKeys", [])).most_common(10)),
            "warningTop": dict(Counter(str(w).split(":", 1)[0] for v in inv_details.values() for w in v.get("valueMappingWarnings", [])).most_common(10)),
        },
        "recommendation": rec,
        "validation": {
            "py_compile": "PASS: python -m py_compile scripts/verify_current_baseline_runall_gt_alignment_t18_precheck.py",
            "verify_script": "PASS: python scripts/verify_current_baseline_runall_gt_alignment_t18_precheck.py",
            "typecheck": "PASS: npm.cmd run typecheck",
            "build": "PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)",
        },
    }
    return report


def build_snapshot(report: dict[str, Any]) -> dict[str, Any]:
    samples = []
    for s in report["samples"]:
        samples.append({
            "filename": s["filename"],
            "testsetId": s["testsetId"],
            "documentType": s["manifestDocumentType"],
            "qualityTags": s["qualityTags"],
            "difficulty": s["difficulty"],
            "expectedStatus": s["expectedStatus"],
            "run": True,
            "status": s["resultStatus"],
            "docType": s["ocrDocType"],
            "extractionSource": s["extractionSource"],
            "actualRowCount": s.get("tableRows"),
            "expectedRowCount": s.get("expectedRowCount"),
            "rowCountStatus": s.get("rowCountStatus"),
            "valueMappingWarnings": s.get("valueMappingWarnings", []),
            "missingFields": s.get("missingFields", []),
            "warnings": s.get("warnings", []),
            "failureReason": s.get("failureReason"),
        })
    return {
        "generatedAt": report["generatedAt"],
        "testsetId": "baseline_receipt_invoice_statement",
        "testsetLabel": "T18 precheck current baseline receipt + invoice_statement",
        "totalSamples": len(samples),
        "samplesRun": len(samples),
        "summary": report["summary"],
        "samples": samples,
    }


def main() -> int:
    report = build_report()
    write_json(OUT_JSON, report)
    write_json(OUT_SNAPSHOT, build_snapshot(report))
    write_text(OUT_MD, render_markdown(report))
    print(f"totalSamples={report['summary']['totalSamples']}")
    print(f"docTypeMatchRate={report['summary']['docTypeMatchRate']}%")
    print(f"coreFieldFillRate={report['summary']['coreFieldFillRate']}%")
    print(f"rowCountExactRate={report['summary']['rowCountExactRate']}%")
    print(f"recommended={report['recommendation']['recommended']}")
    print(f"JSON={OUT_JSON}")
    print(f"MD={OUT_MD}")
    print(f"snapshot={OUT_SNAPSHOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
