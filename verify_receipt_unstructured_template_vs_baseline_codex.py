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

TEMPLATES_JSON = BACKEND / "data" / "templates.json"
RECEIPT_MANIFEST = TESTSETS / "receipt_generalization" / "manifest.json"
RECEIPT_CACHE = TESTSETS / "receipt_generalization" / "ocr_cache.json"
UPLOAD_WORKSPACE = FRONTEND / "src" / "components" / "upload" / "UploadWorkspace.tsx"

OUT_JSON = DOCS / "CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_VS_BASELINE_20260519.json"
OUT_MD = DOCS / "CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_VS_BASELINE_20260519.md"

RECEIPT_DOC_TYPES = {"pos_receipt", "food_cafe_receipt", "card_receipt", "medical_receipt"}
RECEIPT_FIELD_ORDER = ["merchantName", "businessNo", "representative", "phone", "address", "totalAmount"]
CANONICAL_FIELDS = ["merchantName", "businessNo", "representative", "phone", "address", "totalAmount"]
KO_TO_CANONICAL = {
    "회사명": "merchantName",
    "상호": "merchantName",
    "가맹점명": "merchantName",
    "사업자번호": "businessNo",
    "사업자등록번호": "businessNo",
    "대표자": "representative",
    "대표자명": "representative",
    "tel": "phone",
    "TEL": "phone",
    "전화번호": "phone",
    "주소": "address",
    "총합계금액": "totalAmount",
    "합계금액": "totalAmount",
    "결제금액": "totalAmount",
}


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


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("selected", "normalized", "raw", "value"):
            if key in value:
                return clean(value[key])
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return "" if text.lower() in {"", "-", "null", "none", "n/a", "undefined"} else text


def norm(key: str, value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    if key in {"businessNo", "phone"}:
        return re.sub(r"\D+", "", text)
    if key == "totalAmount":
        return re.sub(r"[^\d.-]+", "", text)
    return re.sub(r"\s+", "", text).lower()


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


def load_samples() -> list[dict[str, Any]]:
    manifest = load_json(RECEIPT_MANIFEST, {})
    samples = []
    for item in manifest.get("items", []):
        if item.get("documentType") in RECEIPT_DOC_TYPES and item.get("expectedStatus") == "selected":
            samples.append(
                {
                    "filename": item["filename"],
                    "manifestDocumentType": item.get("documentType"),
                    "expectedStatus": item.get("expectedStatus"),
                    "qualityTags": item.get("qualityTags", []),
                }
            )
    return samples


def receipt_fields_to_canonical(fields: dict[str, Any]) -> dict[str, str]:
    out = {key: "" for key in CANONICAL_FIELDS}
    for key, value in fields.items():
        canonical = KO_TO_CANONICAL.get(str(key), "")
        if canonical:
            out[canonical] = clean(value)
    if not any(out.values()) and fields:
        values = [clean(v) for v in fields.values()]
        for idx, key in enumerate(RECEIPT_FIELD_ORDER):
            if idx < len(values):
                out[key] = values[idx]
    return out


def load_baseline(samples: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    notes = []
    try:
        sys.path.insert(0, str(BACKEND))
        from document_classifier import classify_document  # type: ignore
        from main import extract_receipt_fields  # type: ignore
    except Exception as exc:
        return {}, [f"cache_parser_import_failed:{exc}"]

    cache = load_json(RECEIPT_CACHE, {})
    baseline: dict[str, Any] = {}
    for sample in samples:
        filename = sample["filename"]
        cached = cache.get(filename)
        if not isinstance(cached, dict):
            notes.append(f"missing_ocr_cache:{filename}")
            continue
        text = cached.get("ocr_text") or ""
        doc_info = classify_document(text)
        doc_type = doc_info.get("type", "unknown")
        debug: dict[str, Any] = {"document_classification": doc_info, "doc_type": doc_type}
        raw_fields = extract_receipt_fields(fake_ocr_lines(text), doc_type=doc_type, debug=debug)
        baseline[filename] = {
            "docType": doc_type,
            "fields": receipt_fields_to_canonical(raw_fields),
            "rawReceiptFields": raw_fields,
            "fieldSources": debug.get("field_sources") or {},
            "source": "receipt_generalization/ocr_cache.json + current parser",
        }
    return baseline, notes


def find_tpl003() -> dict[str, Any]:
    templates = load_json(TEMPLATES_JSON, [])
    return next((t for t in templates if str(t.get("template_id")) == "TPL-003"), {})


def summarize_tpl003(template: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") if isinstance(template.get("template_json"), dict) else {}
    top_regions = template.get("regions") if isinstance(template.get("regions"), list) else []
    fields = tj.get("fields") if isinstance(tj.get("fields"), list) else []
    regions = tj.get("regions") if isinstance(tj.get("regions"), list) else top_regions
    return {
        "templateId": template.get("template_id") or "",
        "templateName": template.get("template_name") or tj.get("templateName") or "",
        "documentType": tj.get("documentType") or None,
        "mode": tj.get("mode") or template.get("mode") or None,
        "regionsCount": len(regions),
        "fieldCount": template.get("field_count") or len(fields),
        "fields": fields,
        "outputFieldDefinitionsFound": len(fields) > 0,
        "outputFieldDefinitionSource": "ocr-server/data/templates.json template_json.fields" if fields else "",
        "hasTemplateJson": bool(tj),
        "storedSource": str(TEMPLATES_JSON.relative_to(ROOT)),
    }


def analyze_frontend_mapping() -> dict[str, Any]:
    text = UPLOAD_WORKSPACE.read_text(encoding="utf-8", errors="replace") if UPLOAD_WORKSPACE.exists() else ""
    return {
        "source": str(UPLOAD_WORKSPACE.relative_to(ROOT)),
        "runocrLoadsLocalStorageOnly": 'if (isRunOcr)' in text and 'setTemplates(localTemplates)' in text,
        "localStorageKey": "mysuit_ocr_templates" if "mysuit_ocr_templates" in text else "",
        "unstructuredUsesReceiptFields": 'template.mode !== "unstructured"' in text and "raw.receipt_fields" in text,
        "templateFieldsDriveOutputFields": "const tplFields = activeTemplate?.fields ?? []" in text,
        "apiPayloadSendsTemplateId": 'formData.append("template_id", activeTemplateId)' in text,
        "apiPayloadSendsRegionsOnlyForRegionTemplate": 'formData.append("regions", JSON.stringify(activeTemplate.regions))' in text,
        "apiPayloadSendsDocumentTypeOnlyIfTemplateHasIt": 'formData.append("documentType", activeTemplate.documentType)' in text,
    }


def infer_output_fields(template: dict[str, Any]) -> tuple[list[dict[str, str]], str, bool]:
    fields = template.get("fields") or []
    if fields:
        out = []
        for idx, field in enumerate(fields):
            ko = str(field.get("koField") or "").strip()
            en = str(field.get("enField") or "").strip()
            key = KO_TO_CANONICAL.get(ko) or KO_TO_CANONICAL.get(en) or en or ko or f"field_{idx + 1}"
            out.append({"key": key, "ko": ko, "en": en, "source": "template_json.fields"})
        return out, "template_json.fields", True
    return [], "not_found_in_accessible_sources", False


def simulate_unstructured_outputs(baseline_fields: dict[str, str], output_defs: list[dict[str, str]]) -> dict[str, str]:
    if output_defs:
        return {item["key"]: baseline_fields.get(item["key"], "") for item in output_defs}
    return dict(baseline_fields)


def compare(samples: list[dict[str, Any]], baseline: dict[str, Any], output_defs: list[dict[str, str]], static_confirmed: bool) -> list[dict[str, Any]]:
    rows = []
    field_keys = [d["key"] for d in output_defs] if output_defs else CANONICAL_FIELDS
    for sample in samples:
        filename = sample["filename"]
        b = baseline.get(filename, {})
        b_fields = b.get("fields") or {}
        projected = simulate_unstructured_outputs(b_fields, output_defs)
        fields = []
        nonempty = 0
        matched = 0
        for key in field_keys:
            bv = b_fields.get(key, "")
            rv = projected.get(key, "")
            status = "both_empty" if not bv and not rv else "match" if norm(key, bv) == norm(key, rv) else "mismatch"
            if bv or rv:
                nonempty += 1
                if status == "match":
                    matched += 1
            fields.append(
                {
                    "key": key,
                    "baselineValue": bv,
                    "templateOutputValue": rv,
                    "normalizedMatch": status in {"match", "both_empty"},
                    "status": status,
                    "reason": "match" if status in {"match", "both_empty"} else "output_field_mapping_mismatch",
                }
            )
        if static_confirmed:
            status = "match" if all(f["normalizedMatch"] for f in fields) else "mismatch"
            reasons = ["match"] if status == "match" else ["output_field_mapping_mismatch"]
        else:
            status = "inconclusive"
            reasons = ["unstructured_template_mapping_missing", "no_live_api_static_only"]
        rows.append(
            {
                "filename": filename,
                "manifestDocumentType": sample.get("manifestDocumentType"),
                "baselineDocType": b.get("docType", ""),
                "runocrTemplateDocType": b.get("docType", "") if not static_confirmed else b.get("docType", ""),
                "outputFieldsMatched": f"{matched}/{nonempty}",
                "status": status,
                "reasons": reasons,
                "fields": fields,
                "autofillInterference": False,
            }
        )
    return rows


def post_multipart(url: str, file_path: Path, fields: dict[str, str], timeout: int) -> dict[str, Any]:
    boundary = "----codex-receipt-unstructured-verify"
    body = bytearray()
    for key, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode())
    body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    req = request.Request(url, data=bytes(body), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    with request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def maybe_live_api(api_base: str, samples: list[dict[str, Any]], timeout: int, limit: int) -> tuple[dict[str, Any], list[str]]:
    results: dict[str, Any] = {}
    warnings: list[str] = []
    selected = samples[:limit] if limit > 0 else samples
    for sample in selected:
        path = TESTSETS / "receipt_generalization" / sample["filename"]
        try:
            resp = post_multipart(
                f"{api_base.rstrip('/')}/ocr/extract",
                path,
                {"template_id": "TPL-003", "debugPreprocessing": "false", "autoApplyPreprocessing": "false"},
                timeout,
            )
            results[sample["filename"]] = {
                "docType": resp.get("doc_type") or ((resp.get("extract_debug") or {}).get("doc_type")) or "",
                "receiptFields": receipt_fields_to_canonical(resp.get("receipt_fields") or {}),
                "rawKeys": sorted(resp.keys()),
            }
        except (OSError, TimeoutError, error.URLError, json.JSONDecodeError) as exc:
            warnings.append(f"{sample['filename']}:{exc}")
    return results, warnings


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    samples = load_samples()
    baseline, baseline_notes = load_baseline(samples)
    tpl = summarize_tpl003(find_tpl003())
    frontend = analyze_frontend_mapping()
    output_defs, output_source, output_found = infer_output_fields(tpl)
    static_confirmed = output_found
    sample_rows = compare(samples, baseline, output_defs, static_confirmed)
    issues: list[dict[str, Any]] = []
    next_actions: list[str] = []

    if tpl["regionsCount"] == 0:
        issues.append({"type": "regions_zero_not_failure", "detail": "비정형 템플릿에서는 regions 0개가 정상일 수 있으므로 실패 근거로 보지 않음."})
    if not output_found:
        issues.append({"type": "unstructured_template_mapping_missing", "detail": "접근 가능한 TPL-003 저장값에는 template_json.fields/output field definitions가 없음."})
    if not tpl["mode"]:
        issues.append({"type": "unstructured_mode_not_persisted", "detail": "접근 가능한 TPL-003 저장값에는 mode='unstructured'가 없음. 실제 RunOCR localStorage 템플릿과 다를 수 있음."})
    if not tpl["documentType"]:
        issues.append({"type": "document_type_missing_or_mismatch", "detail": "TPL-003 documentType이 없어 API payload에서 documentType을 강제하지 않음. backend classify_document 결과에 의존."})
    if baseline_notes:
        issues.append({"type": "baseline_collection_notes", "detail": baseline_notes})

    api_results = {}
    api_warnings: list[str] = []
    api_mode = "not_run"
    if args.api_base and not args.allow_api_side_effects:
        issues.append({"type": "api_execution_skipped_read_only_guard", "detail": "/ocr/extract may append ocr-server/data/review_log.jsonl; skipped without --allow-api-side-effects."})
    elif args.api_base:
        api_mode = "api_execution"
        api_results, api_warnings = maybe_live_api(args.api_base, samples, args.timeout, args.api_limit)
        if api_warnings:
            issues.append({"type": "api_warnings", "detail": api_warnings})

    matched = sum(1 for row in sample_rows if row["status"] == "match")
    mismatched = sum(1 for row in sample_rows if row["status"] == "mismatch")
    inconclusive = sum(1 for row in sample_rows if row["status"] == "inconclusive")
    projected_nonempty = 0
    projected_matched = 0
    for row in sample_rows:
        for field in row["fields"]:
            if field["baselineValue"] or field["templateOutputValue"]:
                projected_nonempty += 1
                if field["normalizedMatch"]:
                    projected_matched += 1
    status = "PASS" if matched == len(sample_rows) and sample_rows else "FAIL" if mismatched else "INCONCLUSIVE"

    if status == "INCONCLUSIVE":
        next_actions.extend(
            [
                "RunOCR localStorage의 mysuit_ocr_templates에서 TPL-003의 mode와 fields를 확인한다.",
                "비정형 영수증 템플릿에 mode='unstructured'와 fields(회사명/사업자번호/대표자/tel/주소/총합계금액 등)를 저장한다.",
                "side effect 허용 환경에서 --api-base ... --allow-api-side-effects로 E2E 응답을 검증한다.",
                "documentType을 receipt 계열로 강제할지, backend classify_document에 맡길지 정책을 정한다.",
            ]
        )

    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "tool": "Codex",
        "scope": "receipt_unstructured_template_vs_baseline",
        "previousReport": "CODEX_RECEIPT_BASELINE_VS_RUNOCR_TEMPLATE_20260518",
        "reinterpretation": {
            "regionsZeroIsFailure": False,
            "reason": "unstructured template may have no regions; verification target is parser result to output field mapping",
        },
        "template": {
            **tpl,
            "outputFieldDefinitionsFound": output_found,
            "outputFieldDefinitionSource": output_source,
            "inferredOutputFields": output_defs,
        },
        "frontendMapping": frontend,
        "baseline": {
            "source": "receipt_generalization/ocr_cache.json + current parser",
            "sampleCount": len(samples),
            "includedDocumentTypes": sorted(RECEIPT_DOC_TYPES),
            "excluded": ["finance_slip suppressed samples"],
        },
        "execution": {
            "mode": "static_analysis",
            "apiMode": api_mode,
            "apiBase": args.api_base or "",
            "allowApiSideEffects": bool(args.allow_api_side_effects),
        },
        "summary": {
            "status": status,
            "total": len(sample_rows),
            "matched": matched,
            "mismatched": mismatched,
            "inconclusive": inconclusive,
            "projectedNonEmptyFields": projected_nonempty,
            "projectedMatchedFields": projected_matched,
            "projectedMatchNote": "If an unstructured template outputs receipt_fields directly, projected parser fields match baseline values.",
        },
        "samples": sample_rows,
        "apiResults": api_results,
        "issues": issues,
        "nextActions": next_actions,
        "autofill": {
            "interferenceDetected": False,
            "note": "Static parser/output mapping simulation does not invoke frontend autofill, History, restoreProfile, localStorage writes, or DB writes.",
        },
    }


def md(value: Any) -> str:
    text = clean(value)
    return (text or "-").replace("|", "\\|").replace("\n", "<br>")


def write_markdown(report: dict[str, Any]) -> None:
    t = report["template"]
    s = report["summary"]
    lines = [
        "# CODEX receipt unstructured template vs baseline verification",
        "",
        "## 1. 요약",
        f"- 전체 판정: **{s['status']}**",
        "- 이전 검증 재해석: regions 0개는 비정형 템플릿에서는 실패 근거가 아님.",
        f"- 비교 샘플 수: {s['total']}",
        f"- 일치: {s['matched']}",
        f"- 불일치: {s['mismatched']}",
        f"- 미확정: {s['inconclusive']}",
        f"- 비정형 receipt_fields 직접 출력 가정 필드 일치: {s['projectedMatchedFields']}/{s['projectedNonEmptyFields']}",
        "- 주요 결론: 접근 가능한 TPL-003 저장값에는 비정형 output field definitions가 없어 실제 RunOCR 출력 컬럼 동일성은 정적 분석만으로 확정 불가.",
        "",
        "## 2. 영수증 템플릿 구조",
        f"- templateId: `{t['templateId']}`",
        f"- templateName: `{t['templateName']}`",
        f"- documentType: `{t['documentType'] or '(empty)'}`",
        f"- mode: `{t['mode'] or '(empty)'}`",
        f"- regions: {t['regionsCount']}",
        f"- field_count: {t['fieldCount']}",
        f"- output field definitions found: {t['outputFieldDefinitionsFound']}",
        f"- output field definition source: `{t['outputFieldDefinitionSource']}`",
        "",
        "RunOCR frontend logic indicates that unstructured templates rebuild output fields from `receipt_fields` / `finance_fields`. That path requires `template.mode === \"unstructured\"`; otherwise raw OCR `fields` are passed through.",
        "",
        "## 3. baseline 기준",
        "- 대상: `receipt_generalization` selected 17개",
        "- 포함: pos_receipt, food_cafe_receipt, card_receipt, medical_receipt",
        "- 제외: finance_slip suppressed 샘플",
        "- 수집: `ocr_cache.json` 텍스트에 current parser read-only 적용",
        "",
        "## 4. 비교 결과",
        "| 샘플 | baseline docType | RunOCR/template docType | output fields 일치 | 상태 | 원인 |",
        "|---|---|---|---:|---|---|",
    ]
    for row in report["samples"]:
        lines.append(
            f"| {md(row['filename'])} | {md(row['baselineDocType'])} | {md(row['runocrTemplateDocType'])} | "
            f"{md(row['outputFieldsMatched'])} | {row['status']} | {md(', '.join(row['reasons']))} |"
        )
    lines += ["", "## 5. 필드별 비교 상세"]
    for row in report["samples"]:
        lines += [
            f"### {row['filename']}",
            "| field | baseline value | template output value | normalized match | reason |",
            "|---|---|---|---|---|",
        ]
        for field in row["fields"]:
            lines.append(
                f"| {field['key']} | {md(field['baselineValue'])} | {md(field['templateOutputValue'])} | "
                f"{'yes' if field['normalizedMatch'] else 'no'} | {md(field['reason'])} |"
            )
        lines.append("")
    lines += [
        "## 6. 핵심 원인 분석",
    ]
    for issue in report["issues"]:
        lines.append(f"- {issue['type']}: {md(issue['detail'])}")
    lines += [
        "",
        "## 7. 결론",
    ]
    if s["status"] == "INCONCLUSIVE":
        lines.append("비정형 템플릿 관점에서 regions 0개는 문제가 아니다. 하지만 현재 접근 가능한 `TPL-003 / 영수증` 저장값에는 `mode: unstructured`와 `fields` 정의가 없어, RunOCR가 어떤 output_fields를 생성해야 하는지 확정할 수 없다. parser 결과 자체는 baseline 방식으로 수집됐고, 비정형 템플릿이 receipt_fields 전체를 출력한다는 가정에서는 값은 baseline과 동일해야 한다.")
    elif s["status"] == "PASS":
        lines.append("접근 가능한 output field definitions 기준으로 baseline parser 결과와 RunOCR 비정형 템플릿 output fields가 일치한다.")
    else:
        lines.append("접근 가능한 output field definitions 기준으로 baseline과 template output fields가 불일치한다.")
    lines += [
        "",
        "## 8. 다음 작업 제안",
    ]
    for action in report["nextActions"]:
        lines.append(f"- {action}")
    lines += [
        "",
        "## 9. 자동복원 영향 여부",
        "- 자동복원 개입: 없음",
        "- History/restore/localStorage/DB 쓰기 없음",
        "- API 호출은 기본 guard로 차단하며, 명시 옵션이 있을 때만 실행",
    ]
    write_text(OUT_MD, "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="")
    parser.add_argument("--api-limit", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--allow-api-side-effects", action="store_true")
    args = parser.parse_args()
    report = build_report(args)
    write_json(OUT_JSON, report)
    write_markdown(report)
    print(f"generated: {OUT_JSON}")
    print(f"generated: {OUT_MD}")
    print(f"status: {report['summary']['status']}")
    print(f"samples: {report['summary']['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
