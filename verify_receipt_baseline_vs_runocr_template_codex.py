from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public" / "data" / "testsets"
DOCS = ROOT / "docs"

OUT_JSON = DOCS / "CODEX_RECEIPT_BASELINE_VS_RUNOCR_TEMPLATE_20260518.json"
OUT_MD = DOCS / "CODEX_RECEIPT_BASELINE_VS_RUNOCR_TEMPLATE_20260518.md"

RECEIPT_MANIFEST = TESTSETS / "receipt_generalization" / "manifest.json"
TEMPLATES_JSON = BACKEND / "data" / "templates.json"
T22_JSON = TESTSETS / "reports" / "T22_testworkspace_preprocessing_options_validation_20260517.json"

RECEIPT_DOC_TYPES = {
    "pos_receipt",
    "food_cafe_receipt",
    "card_receipt",
    "medical_receipt",
}

DOC_TYPE_ALIASES = {
    "pos_receipt": "receipt_pos",
    "food_cafe_receipt": "receipt_card",
    "card_receipt": "receipt_card",
    "medical_receipt": "medical_receipt",
}

CORE_FIELDS = [
    "merchantName",
    "businessNo",
    "totalAmount",
    "transactionDate",
    "phone",
    "address",
    "representative",
]

RECEIPT_VALUE_ORDER = ["merchantName", "businessNo", "representative", "phone", "address", "totalAmount"]

FIELD_ALIASES = {
    "merchantName": ["merchantName", "companyName", "상호", "회사명", "가맹점명"],
    "businessNo": ["businessNo", "businessNumber", "사업자번호", "사업자등록번호", "사업 No"],
    "totalAmount": ["totalAmount", "amount", "총합계금액", "합계", "결제금액"],
    "transactionDate": ["transactionDate", "date", "거래일시", "발행일자"],
    "phone": ["phone", "tel", "전화번호"],
    "address": ["address", "주소"],
    "representative": ["representative", "대표자"],
}

EMPTY_VALUES = {"", "-", "null", "none", "n/a", "na", "undefined"}


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


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("selected", "normalized", "raw", "value"):
            if key in value:
                return clean_value(value.get(key))
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return "" if text.lower() in EMPTY_VALUES else text


def normalize_value(key: str, value: Any) -> str:
    text = clean_value(value)
    if not text:
        return ""
    if key in {"businessNo", "phone"}:
        return re.sub(r"\D+", "", text)
    if key == "totalAmount":
        return re.sub(r"[^\d.-]+", "", text)
    return re.sub(r"\s+", "", text).strip().lower()


def pick_field(fields: dict[str, Any], canonical_key: str) -> str:
    for alias in FIELD_ALIASES.get(canonical_key, [canonical_key]):
        if alias in fields:
            value = clean_value(fields.get(alias))
            if value:
                return value
    return ""


def normalize_fields(raw: dict[str, Any]) -> dict[str, str]:
    result = {key: pick_field(raw or {}, key) for key in CORE_FIELDS}
    # Backend receipt_fields uses Korean labels in insertion order. Some source
    # files are mojibake in this repo, so alias matching alone is not reliable.
    if raw and not any(result.values()):
        values = [clean_value(v) for v in raw.values()]
        for idx, key in enumerate(RECEIPT_VALUE_ORDER):
            if idx < len(values):
                result[key] = values[idx]
    return result


def fake_ocr_lines(text: str) -> list[Any]:
    lines = []
    y = 10
    for raw in (text or "").splitlines():
        s = raw.strip()
        if not s:
            continue
        width = max(20, min(800, len(s) * 8))
        lines.append(([(10, y), (10 + width, y), (10 + width, y + 14), (10, y + 14)], s, 0.9))
        y += 20
    return lines


def load_receipt_samples() -> list[dict[str, Any]]:
    manifest = load_json(RECEIPT_MANIFEST, {})
    samples = []
    for item in manifest.get("items", []):
        if item.get("documentType") not in RECEIPT_DOC_TYPES:
            continue
        if item.get("expectedStatus") != "selected":
            continue
        samples.append(
            {
                "filename": item.get("filename", ""),
                "manifestDocumentType": item.get("documentType", ""),
                "expectedBackendDocType": DOC_TYPE_ALIASES.get(item.get("documentType", ""), item.get("documentType", "")),
                "expectedStatus": item.get("expectedStatus", ""),
                "qualityTags": item.get("qualityTags", []),
                "difficulty": item.get("difficulty", ""),
            }
        )
    return samples


def load_t22_baseline() -> dict[str, dict[str, Any]]:
    data = load_json(T22_JSON, {})
    rows = (((data.get("modeResults") or {}).get("default")) or [])
    baseline: dict[str, dict[str, Any]] = {}
    for row in rows:
        sample = str(row.get("sample", ""))
        if not sample.startswith("receipt_generalization/"):
            continue
        filename = sample.split("/", 1)[1]
        fields = normalize_fields(row)
        baseline[filename] = {
            "source": str(T22_JSON.relative_to(ROOT)),
            "docType": row.get("docType") or "",
            "fields": fields,
            "warnings": row.get("warnings") or [],
            "preprocessingDebug": bool(row.get("preprocessingDebug")),
            "productionApplied": bool(row.get("productionApplied")),
            "raw": row,
        }
    return baseline


def load_cache_parser_baseline(samples: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], str]:
    try:
        sys.path.insert(0, str(BACKEND))
        from document_classifier import classify_document  # type: ignore
        from main import extract_receipt_fields  # type: ignore
    except Exception as exc:
        return {}, f"cache_parser_import_failed:{exc}"

    cache = load_json(TESTSETS / "receipt_generalization" / "ocr_cache.json", {})
    wanted = {s["filename"] for s in samples}
    baseline: dict[str, dict[str, Any]] = {}
    for filename in wanted:
        cached = cache.get(filename)
        if not isinstance(cached, dict):
            continue
        text = cached.get("ocr_text") or ""
        doc_info = classify_document(text)
        doc_type = doc_info.get("type", "unknown")
        debug: dict[str, Any] = {"document_classification": doc_info, "doc_type": doc_type}
        fields_raw = extract_receipt_fields(fake_ocr_lines(text), doc_type=doc_type, debug=debug)
        baseline[filename] = {
            "source": "receipt_generalization/ocr_cache.json + current parser",
            "docType": doc_type,
            "fields": normalize_fields(fields_raw),
            "warnings": ["cache_based_parser:no_live_runocr_export"],
            "preprocessingDebug": False,
            "productionApplied": False,
            "raw": {
                "receipt_fields": fields_raw,
                "classification": doc_info,
                "total_amount": debug.get("total_amount"),
                "field_sources": debug.get("field_sources"),
            },
        }
    return baseline, "cache_parser"


def find_receipt_template() -> dict[str, Any]:
    templates = load_json(TEMPLATES_JSON, [])
    candidates = []
    for item in templates:
        name = str(item.get("template_name") or "")
        inner = ((item.get("template_json") or {}).get("templateName") if isinstance(item.get("template_json"), dict) else "") or ""
        doc_type = ((item.get("template_json") or {}).get("documentType") if isinstance(item.get("template_json"), dict) else "") or ""
        if "영수증" in name or "영수증" in str(inner) or "receipt" in name.lower() or "receipt" in str(doc_type).lower():
            candidates.append(item)
    if candidates:
        return candidates[0]
    for item in templates:
        if str(item.get("template_id")) == "TPL-003":
            return item
    return {}


def summarize_template(template: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json")
    template_json = tj if isinstance(tj, dict) else {}
    top_regions = template.get("regions")
    regions = template_json.get("regions") if isinstance(template_json.get("regions"), list) else top_regions
    if not isinstance(regions, list):
        regions = []
    fields = template_json.get("fields")
    if not isinstance(fields, list):
        fields = []
    return {
        "templateId": template.get("template_id") or "",
        "templateName": template.get("template_name") or template_json.get("templateName") or "",
        "innerTemplateName": template_json.get("templateName") or "",
        "documentType": template_json.get("documentType") or "",
        "fieldCount": template.get("field_count") or len(fields),
        "regionCount": len(regions),
        "regions": regions,
        "fields": fields,
        "hasTemplateJson": bool(template_json),
        "hasRegionMapping": bool(regions),
        "file": (template_json.get("file") or {}).get("name") if isinstance(template_json.get("file"), dict) else "",
        "imageWidth": (template_json.get("image") or {}).get("width") if isinstance(template_json.get("image"), dict) else None,
        "imageHeight": (template_json.get("image") or {}).get("height") if isinstance(template_json.get("image"), dict) else None,
    }


def response_fields_from_api(resp: dict[str, Any]) -> dict[str, str]:
    flat: dict[str, Any] = {}
    for item in resp.get("fields") or []:
        if isinstance(item, dict):
            name = str(item.get("name") or "")
            if name:
                flat[name] = item.get("value")
    receipt_fields = resp.get("receipt_fields") if isinstance(resp.get("receipt_fields"), dict) else {}
    flat.update(receipt_fields)
    doc_fields = resp.get("document_fields") if isinstance(resp.get("document_fields"), dict) else {}
    flat.update(doc_fields)
    return normalize_fields(flat)


def post_multipart(url: str, file_path: Path, fields: dict[str, str], timeout: int) -> dict[str, Any]:
    boundary = "----codex-receipt-template-verify"
    body = bytearray()
    for key, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode()
    )
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    req = request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def run_api_compare(api_base: str, samples: list[dict[str, Any]], template: dict[str, Any], limit: int, timeout: int) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    results: dict[str, Any] = {}
    template_id = str(template.get("templateId") or "")
    document_type = str(template.get("documentType") or "")
    regions = template.get("regions") or []
    selected = samples[:limit] if limit > 0 else samples
    for sample in selected:
        file_path = TESTSETS / "receipt_generalization" / sample["filename"]
        if not file_path.exists():
            warnings.append(f"missing_file:{sample['filename']}")
            continue
        form = {
            "template_id": template_id,
            "debugPreprocessing": "false",
            "autoApplyPreprocessing": "false",
        }
        if document_type:
            form["documentType"] = document_type
        if regions:
            form["regions"] = json.dumps(regions, ensure_ascii=False)
        try:
            resp = post_multipart(f"{api_base.rstrip('/')}/ocr/extract", file_path, form, timeout)
        except (error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            warnings.append(f"api_failed:{sample['filename']}:{exc}")
            continue
        results[sample["filename"]] = {
            "source": f"{api_base.rstrip('/')}/ocr/extract",
            "docType": resp.get("doc_type") or ((resp.get("extract_debug") or {}).get("doc_type")) or "",
            "fields": response_fields_from_api(resp),
            "templatePath": bool((resp.get("extract_debug") or {}).get("template_path")),
            "rawKeys": sorted(resp.keys()),
        }
    return results, warnings


def compare_samples(samples: list[dict[str, Any]], baseline: dict[str, Any], runocr: dict[str, Any], template: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    compared = []
    for sample in samples:
        filename = sample["filename"]
        b = baseline.get(filename, {})
        r = runocr.get(filename, {})
        b_fields = b.get("fields") or {}
        r_fields = r.get("fields") or {}
        field_rows = []
        reasons = []
        matched = 0
        considered = 0
        for key in CORE_FIELDS:
            bv = clean_value(b_fields.get(key))
            rv = clean_value(r_fields.get(key))
            bn = normalize_value(key, bv)
            rn = normalize_value(key, rv)
            if not bv and not rv:
                status = "both_empty"
            elif bn == rn:
                status = "match"
                matched += 1
                considered += 1
            elif not bv:
                status = "extra_in_runocr"
                considered += 1
                reasons.append("extra_in_runocr")
            elif not rv:
                status = "missing_in_runocr"
                considered += 1
                reasons.append("missing_in_runocr")
            else:
                status = "mismatch"
                considered += 1
                reasons.append("value_mismatch")
            field_rows.append(
                {
                    "key": key,
                    "baselineValue": bv,
                    "runocrValue": rv,
                    "baselineNormalized": bn,
                    "runocrNormalized": rn,
                    "status": status,
                    "normalizedMatch": status in {"match", "both_empty"},
                    "reason": "" if status in {"match", "both_empty"} else classify_reason(key, b, r, template, mode),
                }
            )
        baseline_doc = clean_value(b.get("docType")) or sample.get("expectedBackendDocType", "")
        runocr_doc = clean_value(r.get("docType")) or ("not_executed" if mode != "api" else "")
        doc_match = bool(runocr_doc and runocr_doc != "not_executed" and baseline_doc == runocr_doc)
        if mode != "api":
            if not template.get("hasRegionMapping") and not template.get("documentType"):
                status = "inconclusive"
                reasons.append("api_not_executed_static_equivalent_path_expected")
            else:
                status = "inconclusive"
        elif not r:
            status = "inconclusive"
            reasons.append("api_result_missing")
        elif baseline_doc and runocr_doc and baseline_doc != runocr_doc:
            status = "mismatch"
            reasons.append("document_type_mismatch")
        elif considered == matched:
            status = "match"
        elif any(row["status"] in {"mismatch", "missing_in_runocr"} for row in field_rows):
            status = "mismatch"
        else:
            status = "match"
        compared.append(
            {
                "filename": filename,
                "manifestDocumentType": sample.get("manifestDocumentType"),
                "baselineDocType": baseline_doc,
                "runocrDocType": runocr_doc,
                "docTypeMatch": doc_match,
                "status": status,
                "fields": field_rows,
                "reasons": sorted(set(reasons)),
                "rowTable": False,
                "baselineWarnings": b.get("warnings") or [],
                "autofillInterference": False,
            }
        )
    return compared


def classify_reason(key: str, baseline: dict[str, Any], runocr: dict[str, Any], template: dict[str, Any], mode: str) -> str:
    if mode != "api":
        return "unknown"
    if (baseline.get("docType") or "") != (runocr.get("docType") or ""):
        return "document_type_mismatch"
    if not template.get("hasRegionMapping"):
        return "parser_vs_template_path_difference"
    if key in {"businessNo", "merchantName", "totalAmount"}:
        return "template_region_mismatch"
    return "unknown"


def build_static_runocr_projection(samples: list[dict[str, Any]], baseline: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    projected = {}
    template_has_no_effect = not template.get("hasRegionMapping") and not template.get("documentType")
    for sample in samples:
        filename = sample["filename"]
        if template_has_no_effect and filename in baseline:
            projected[filename] = {
                **baseline[filename],
                "source": "static_projection:TPL-003_has_no_regions_or_documentType_backend_falls_back_to_full_ocr",
                "templatePath": False,
            }
    return projected


def build_report(api_base: str | None, api_limit: int, timeout: int, allow_api_side_effects: bool) -> dict[str, Any]:
    generated = datetime.now().isoformat(timespec="seconds")
    samples = load_receipt_samples()
    t22_baseline = load_t22_baseline()
    cache_baseline, baseline_mode = load_cache_parser_baseline(samples)
    baseline = cache_baseline or t22_baseline
    template = summarize_template(find_receipt_template())
    issues = []
    next_actions = []
    mode = "static_analysis"
    api_warnings: list[str] = []
    runocr: dict[str, Any] = {}

    if not template.get("templateId"):
        issues.append({"type": "template_not_found", "detail": "No receipt or TPL-003 template found"})
    elif not template.get("hasRegionMapping"):
        issues.append(
            {
                "type": "template_region_mapping_empty",
                "detail": "영수증 template has no regions; backend will not execute template crop/field mapping path from this stored template.",
            }
        )
    if not template.get("documentType"):
        issues.append(
            {
                "type": "template_document_type_empty",
                "detail": "영수증 template has no template_json.documentType; /ocr/extract will classify from OCR text unless explicit documentType is sent.",
            }
        )
    missing_baseline = [s["filename"] for s in samples if s["filename"] not in baseline]
    if missing_baseline:
        issues.append({"type": "baseline_snapshot_missing_samples", "detail": missing_baseline})

    if api_base and not allow_api_side_effects:
        issues.append(
            {
                "type": "api_execution_skipped_read_only_guard",
                "detail": "/ocr/extract appends backend review_log.jsonl in this project; live API mode is skipped unless --allow-api-side-effects is supplied.",
            }
        )
        runocr = build_static_runocr_projection(samples, baseline, template)
    elif api_base:
        mode = "api_execution"
        runocr, api_warnings = run_api_compare(api_base, samples, template, api_limit, timeout)
        if api_warnings:
            issues.append({"type": "api_warnings", "detail": api_warnings})
        if not runocr:
            mode = "static_analysis"
            runocr = build_static_runocr_projection(samples, baseline, template)
    else:
        runocr = build_static_runocr_projection(samples, baseline, template)

    comparisons = compare_samples(samples, baseline, runocr, template, "api" if mode == "api_execution" else "static")
    summary = {
        "total": len(comparisons),
        "matched": sum(1 for s in comparisons if s["status"] == "match"),
        "mismatched": sum(1 for s in comparisons if s["status"] == "mismatch"),
        "inconclusive": sum(1 for s in comparisons if s["status"] == "inconclusive"),
    }
    if mode != "api_execution":
        overall = "INCONCLUSIVE"
        next_actions.extend(
            [
                "Live API execution is intentionally guarded because /ocr/extract can append ocr-server/data/review_log.jsonl.",
                "If that side effect is acceptable, rerun with --api-base http://127.0.0.1:<port> --allow-api-side-effects.",
                "If 영수증 is intended to be a region template, save real regions and documentType in a separate template update task.",
                "Keep autofill/history restore disabled or excluded when doing value equality checks.",
            ]
        )
    elif summary["mismatched"] == 0 and summary["inconclusive"] == 0:
        overall = "PASS"
    elif summary["mismatched"] > 0:
        overall = "FAIL"
    else:
        overall = "INCONCLUSIVE"

    return {
        "generatedAt": generated,
        "tool": "Codex",
        "scope": "receipt_baseline_vs_runocr_template",
        "execution": {
            "mode": mode,
            "apiBase": api_base or "",
            "apiLimit": api_limit,
            "allowApiSideEffects": allow_api_side_effects,
            "apiWarnings": api_warnings,
            "overall": overall,
        },
        "baseline": {
            "source": "receipt_generalization/ocr_cache.json + current parser" if cache_baseline else (str(T22_JSON.relative_to(ROOT)) if T22_JSON.exists() else str(RECEIPT_MANIFEST.relative_to(ROOT))),
            "mode": baseline_mode,
            "definition": "receipt_generalization selected samples with documentType in pos_receipt, food_cafe_receipt, card_receipt, medical_receipt; finance_slip suppressed samples excluded",
            "sampleCount": len(samples),
            "snapshotSampleCount": len(baseline),
            "t22SnapshotSampleCount": len(t22_baseline),
        },
        "template": template,
        "summary": summary,
        "samples": comparisons,
        "issues": issues,
        "nextActions": next_actions,
        "autofill": {
            "interferenceDetected": False,
            "note": "This script reads TestWorkspace baseline snapshot and backend API response only. Frontend autofill/restore and localStorage are not invoked.",
        },
    }


def md_escape(value: Any) -> str:
    text = clean_value(value)
    return (text or "-").replace("|", "\\|").replace("\n", "<br>")


def write_markdown(report: dict[str, Any]) -> None:
    template = report["template"]
    summary = report["summary"]
    lines = [
        "# CODEX receipt baseline vs RunOCR 영수증 template verification",
        "",
        "## 1. 요약",
        f"- 전체 판정: **{report['execution']['overall']}**",
        f"- 실행 방식: `{report['execution']['mode']}`",
        f"- 비교 샘플 수: {summary['total']}",
        f"- 일치: {summary['matched']}",
        f"- 불일치: {summary['mismatched']}",
        f"- 미확정: {summary['inconclusive']}",
        "",
        "## 2. 검증 기준",
        f"- baseline: {report['baseline']['definition']}",
        f"- baseline source: `{report['baseline']['source']}`",
        f"- baseline sample count: {report['baseline']['sampleCount']}",
        f"- RunOCR template: `{template.get('templateId')}` / `{template.get('templateName')}`",
        f"- template documentType: `{template.get('documentType') or '(empty)'}`",
        f"- template regions: {template.get('regionCount')}",
        f"- template fields: {template.get('fieldCount')}",
        "",
        "## 3. 샘플별 비교표",
        "| 샘플 | baseline docType | RunOCR docType | 핵심 필드 일치 | row/table 여부 | 상태 | 원인 |",
        "|---|---|---|---:|---|---|---|",
    ]
    for sample in report["samples"]:
        fields = sample.get("fields") or []
        non_empty = [f for f in fields if f.get("status") != "both_empty"]
        matched = sum(1 for f in non_empty if f.get("normalizedMatch"))
        total = len(non_empty)
        lines.append(
            f"| {md_escape(sample['filename'])} | {md_escape(sample['baselineDocType'])} | "
            f"{md_escape(sample['runocrDocType'])} | {matched}/{total} | "
            f"{'yes' if sample.get('rowTable') else 'no'} | {sample['status']} | "
            f"{md_escape(', '.join(sample.get('reasons') or []))} |"
        )

    lines += [
        "",
        "## 4. 필드별 비교 상세",
    ]
    for sample in report["samples"]:
        lines += [
            f"### {sample['filename']}",
            "| field | baseline | RunOCR template | normalized match | reason |",
            "|---|---|---|---|---|",
        ]
        for field in sample.get("fields") or []:
            lines.append(
                f"| {field['key']} | {md_escape(field['baselineValue'])} | {md_escape(field['runocrValue'])} | "
                f"{'yes' if field['normalizedMatch'] else 'no'} | {md_escape(field.get('reason'))} |"
            )
        lines.append("")

    lines += [
        "## 5. mismatch 원인 분류",
    ]
    reason_counts: dict[str, int] = {}
    for sample in report["samples"]:
        for reason in sample.get("reasons") or []:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    if reason_counts:
        for reason, count in sorted(reason_counts.items()):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- mismatch reason 없음")

    lines += [
        "",
        "## 6. 영수증 템플릿 구조 분석",
        f"- template_id: `{template.get('templateId')}`",
        f"- templateName: `{template.get('templateName')}`",
        f"- documentType: `{template.get('documentType') or '(empty)'}`",
        f"- regions: {template.get('regionCount')}",
        f"- field mapping: {template.get('fieldCount')}",
        "",
        "현재 저장된 `영수증` 템플릿은 region mapping이 비어 있다. 따라서 `template_id=TPL-003`만 RunOCR API에 전달하면 backend는 template crop OCR 경로가 아니라 full-image OCR/parser 경로로 처리한다. documentType도 비어 있어 template metadata가 documentType을 강제하지 않는다.",
        "",
        "## 7. 자동복원 영향 여부",
        "- 자동복원 개입 감지: no",
        "- 이 검증 스크립트는 frontend localStorage, History, restoreProfile 저장소를 읽거나 쓰지 않는다.",
        "- TestWorkspace baseline snapshot과 backend API response 또는 정적 projection만 비교하므로 자동복원 값은 비교 대상에서 제외된다.",
        "",
        "## 8. 결론",
    ]
    if report["execution"]["overall"] == "INCONCLUSIVE":
        lines.append("API live 실행 없이 정적 분석 기준으로는 최종 값 동일성 PASS/FAIL을 확정할 수 없다. 다만 저장된 `영수증` 템플릿은 regions/documentType이 비어 있어, 현재 구조상 template region/field mapping 차이로 결과가 달라질 근거는 없다.")
    elif report["execution"]["overall"] == "PASS":
        lines.append("API live 실행 기준 baseline과 RunOCR `영수증` 템플릿 결과가 정규화 비교에서 일치했다.")
    else:
        lines.append("API live 실행 기준 baseline과 RunOCR `영수증` 템플릿 결과가 일부 샘플/필드에서 불일치했다. 상세 원인은 샘플별 표와 JSON report를 확인한다.")

    lines += [
        "",
        "## 9. 다음 작업 제안",
    ]
    for action in report.get("nextActions") or [
        "Live API mode로 재실행해 실제 RunOCR 응답 값을 확정한다.",
        "영수증 템플릿을 region template으로 사용할 의도라면 별도 작업에서 regions/documentType/field mapping을 저장한다.",
    ]:
        lines.append(f"- {action}")

    lines += [
        "",
        "## 10. 이슈",
    ]
    for issue in report.get("issues") or []:
        lines.append(f"- {issue.get('type')}: {md_escape(issue.get('detail'))}")

    write_text(OUT_MD, "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare receipt baseline snapshot with RunOCR 영수증 template results.")
    parser.add_argument("--api-base", default="", help="Optional running backend base URL, e.g. http://127.0.0.1:8100")
    parser.add_argument("--api-limit", type=int, default=0, help="Limit live API samples; 0 means all")
    parser.add_argument("--timeout", type=int, default=120, help="Per-sample API timeout seconds")
    parser.add_argument(
        "--allow-api-side-effects",
        action="store_true",
        help="Allow live /ocr/extract calls. In this project they may append ocr-server/data/review_log.jsonl.",
    )
    args = parser.parse_args()

    report = build_report(args.api_base or None, args.api_limit, args.timeout, args.allow_api_side_effects)
    write_json(OUT_JSON, report)
    write_markdown(report)

    print(f"generated: {OUT_JSON}")
    print(f"generated: {OUT_MD}")
    print(f"overall: {report['execution']['overall']}")
    print(f"mode: {report['execution']['mode']}")
    print(f"samples: {report['summary']['total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
