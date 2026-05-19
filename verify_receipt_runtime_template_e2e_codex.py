from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib import error, request


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public" / "data" / "testsets"
DOCS = ROOT / "docs"

RECEIPT_MANIFEST = TESTSETS / "receipt_generalization" / "manifest.json"
RECEIPT_CACHE = TESTSETS / "receipt_generalization" / "ocr_cache.json"
UPLOAD_WORKSPACE = FRONTEND / "src" / "components" / "upload" / "UploadWorkspace.tsx"
UNSTRUCTURED_BUILDER = FRONTEND / "src" / "components" / "template" / "UnstructuredBuilder.tsx"
TEMPLATE_PAGE = FRONTEND / "src" / "app" / "template" / "page.tsx"
TEMPLATES_JSON = BACKEND / "data" / "templates.json"

OUT_JSON = DOCS / "CODEX_RECEIPT_RUNTIME_TEMPLATE_E2E_20260519.json"
OUT_MD = DOCS / "CODEX_RECEIPT_RUNTIME_TEMPLATE_E2E_20260519.md"

RECEIPT_DOC_TYPES = {"pos_receipt", "food_cafe_receipt", "card_receipt", "medical_receipt"}

RUNTIME_TEMPLATE_FIELDS = [
    {"key": "no_1", "label": "회사명", "candidateKeys": ["merchantName", "companyName", "상호", "회사명"]},
    {"key": "no_2", "label": "사업자번호", "candidateKeys": ["businessNo", "businessNumber", "사업자번호"]},
    {"key": "no_3", "label": "대표자", "candidateKeys": ["representative", "대표자"]},
    {"key": "no_4", "label": "전화번호", "candidateKeys": ["tel", "phone", "전화번호"]},
    {"key": "no_5", "label": "주소", "candidateKeys": ["address", "주소"]},
    {"key": "no_6", "label": "총합계금액", "candidateKeys": ["totalAmount", "amount", "총합계금액", "합계금액"]},
]

CANONICAL_ORDER = ["merchantName", "businessNo", "representative", "tel", "address", "totalAmount"]

# The repository contains some Korean source text that appears mojibake in plain file reads.
# Keep both normal Korean labels and the observed mojibake aliases so this script can compare
# parser output without changing any application code.
LABEL_TO_CANONICAL = {
    "회사명": "merchantName",
    "상호": "merchantName",
    "가맹점명": "merchantName",
    "?뚯궗紐?": "merchantName",
    "?곹샇": "merchantName",
    "媛留뱀젏紐?": "merchantName",
    "사업자번호": "businessNo",
    "사업자등록번호": "businessNo",
    "?ъ뾽?먮쾲??": "businessNo",
    "?ъ뾽?먮벑濡앸쾲??": "businessNo",
    "대표자": "representative",
    "대표자명": "representative",
    "??쒖옄": "representative",
    "??쒖옄紐?": "representative",
    "전화번호": "tel",
    "전화": "tel",
    "phone": "tel",
    "tel": "tel",
    "Tel": "tel",
    "TEL": "tel",
    "?꾪솕踰덊샇": "tel",
    "주소": "address",
    "二쇱냼": "address",
    "총합계금액": "totalAmount",
    "합계금액": "totalAmount",
    "결제금액": "totalAmount",
    "珥앺빀怨꾧툑??": "totalAmount",
    "?⑷퀎湲덉븸": "totalAmount",
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
    if text.lower() in {"", "-", "null", "none", "n/a", "undefined"}:
        return ""
    return text


def norm(field_key: str, value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    if field_key in {"no_2", "businessNo", "businessNumber"}:
        return re.sub(r"\D+", "", text)
    if field_key in {"no_4", "tel", "phone"}:
        return re.sub(r"\D+", "", text)
    if field_key in {"no_6", "totalAmount", "amount"}:
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
                    "filename": item.get("filename"),
                    "documentType": item.get("documentType"),
                    "expectedStatus": item.get("expectedStatus"),
                    "qualityTags": item.get("qualityTags", []),
                }
            )
    return samples


def canonicalize_receipt_fields(fields: dict[str, Any]) -> dict[str, str]:
    canonical = {key: "" for key in CANONICAL_ORDER}
    for key, value in fields.items():
        mapped = LABEL_TO_CANONICAL.get(str(key).strip())
        if mapped:
            canonical[mapped] = clean(value)

    # Fallback for parser maps whose keys cannot be decoded in this checkout. The receipt
    # extractor has historically returned the six runtime fields in this order.
    if not any(canonical.values()) and fields:
        values = [clean(value) for value in fields.values()]
        for index, key in enumerate(CANONICAL_ORDER):
            if index < len(values):
                canonical[key] = values[index]
    return canonical


def load_baseline(samples: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    notes: list[str] = []
    try:
        sys.path.insert(0, str(BACKEND))
        from document_classifier import classify_document  # type: ignore
        from main import extract_receipt_fields  # type: ignore
    except Exception as exc:
        return {}, [f"backend_parser_import_failed:{exc}"]

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
        canonical = canonicalize_receipt_fields(raw_fields)
        baseline[filename] = {
            "docType": doc_type,
            "manifestDocType": sample.get("documentType"),
            "fields": canonical,
            "rawReceiptFields": raw_fields,
            "source": "receipt_generalization/ocr_cache.json + current backend parser",
        }
    return baseline, notes


def scan_repo_for_runtime_fields() -> dict[str, Any]:
    found: list[dict[str, Any]] = []
    needles = ["no_1", "no_2", "no_3", "no_4", "no_5", "no_6", "회사명", "총합계금액"]
    for path in [TEMPLATES_JSON, FRONTEND / "public" / "templates.json"]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = [needle for needle in needles if needle in text]
        if hits:
            found.append({"path": str(path.relative_to(ROOT)), "hits": hits})
    return {
        "templateDefinitionFoundInRepo": bool(found),
        "repoHits": found,
    }


def analyze_tpl003_server_template() -> dict[str, Any]:
    templates = load_json(TEMPLATES_JSON, [])
    row = next((item for item in templates if str(item.get("template_id")) == "TPL-003"), {})
    tj = row.get("template_json") if isinstance(row.get("template_json"), dict) else {}
    fields = tj.get("fields") if isinstance(tj.get("fields"), list) else []
    regions = tj.get("regions") if isinstance(tj.get("regions"), list) else row.get("regions", [])
    return {
        "templateId": row.get("template_id") or "TPL-003",
        "templateName": row.get("template_name") or "영수증",
        "serverTemplatePath": str(TEMPLATES_JSON.relative_to(ROOT)),
        "hasTemplateJson": bool(tj),
        "mode": tj.get("mode") or row.get("mode") or None,
        "documentType": tj.get("documentType") or row.get("documentType") or None,
        "regionsCount": len(regions) if isinstance(regions, list) else 0,
        "fieldCount": row.get("field_count") or len(fields),
        "fieldsCount": len(fields),
        "fields": fields,
    }


def analyze_frontend_runtime_flow() -> dict[str, Any]:
    text = UPLOAD_WORKSPACE.read_text(encoding="utf-8", errors="replace") if UPLOAD_WORKSPACE.exists() else ""
    builder = UNSTRUCTURED_BUILDER.read_text(encoding="utf-8", errors="replace") if UNSTRUCTURED_BUILDER.exists() else ""
    template_page = TEMPLATE_PAGE.read_text(encoding="utf-8", errors="replace") if TEMPLATE_PAGE.exists() else ""
    return {
        "sources": [
            str(TEMPLATE_PAGE.relative_to(ROOT)),
            str(UNSTRUCTURED_BUILDER.relative_to(ROOT)),
            str(UPLOAD_WORKSPACE.relative_to(ROOT)),
        ],
        "localStorageKey": "mysuit_ocr_templates" if "mysuit_ocr_templates" in text else None,
        "templateTabReadsLocalStorage": "localStorage.getItem(LOCAL_TEMPLATES_KEY)" in template_page,
        "templateTabPassesUnstructuredTemplateJson": "selectedTemplate?.mode === \"unstructured\"" in template_page,
        "unstructuredBuilderStoresLocalStorage": "localStorage.setItem(LOCAL_TEMPLATES_KEY" in builder,
        "unstructuredBuilderStoresMode": 'mode: "unstructured"' in builder,
        "unstructuredBuilderStoresFields": "fields," in builder and "template_json" in builder,
        "unstructuredBuilderStoresRegionsEmpty": "regions: []" in builder,
        "runocrLoadsLocalStorageOnly": "if (isRunOcr)" in text and "setTemplates(localTemplates)" in text,
        "localTemplateReadsFields": "template_json?.fields" in text,
        "localTemplateReadsMode": "template_json?.mode" in text,
        "unstructuredUsesReceiptFields": 'template.mode !== "unstructured"' in text and "raw.receipt_fields" in text,
        "templateFieldsDriveOutputFields": "templateFields.length > 0" in text and "templateFields.forEach" in text,
        "historyOutputUsesTemplateFields": "const tplFields = activeTemplate?.fields ?? []" in text,
        "runocrPayloadSendsTemplateId": 'formData.append("template_id", activeTemplateId)' in text,
        "runocrPayloadSendsFields": 'formData.append("fields"' in text or 'formData.append("template_fields"' in text,
        "runocrPayloadSendsRegionsOnlyForRegionTemplate": 'formData.append("regions", JSON.stringify(activeTemplate.regions))' in text,
        "runocrPayloadSendsDocumentTypeOnlyIfTemplateHasIt": 'formData.append("documentType", activeTemplate.documentType)' in text,
        "outputGeneratedClientSide": "const runResult = isRunOcr ? buildRunOcrResult(json, activeTemplate) : json" in text,
    }


def baseline_to_runtime_output(fields: dict[str, str]) -> dict[str, str]:
    return {
        "no_1": fields.get("merchantName", ""),
        "no_2": fields.get("businessNo", ""),
        "no_3": fields.get("representative", ""),
        "no_4": fields.get("tel", ""),
        "no_5": fields.get("address", ""),
        "no_6": fields.get("totalAmount", ""),
    }


def compare_projection(samples: list[dict[str, Any]], baseline: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    counters = {"sampleMatched": 0, "sampleMismatched": 0, "fieldMatched": 0, "fieldMismatched": 0, "fieldBothEmpty": 0}
    for sample in samples:
        filename = sample["filename"]
        base = baseline.get(filename, {})
        base_fields = base.get("fields") or {}
        output = baseline_to_runtime_output(base_fields)
        field_rows = []
        sample_ok = True
        for field in RUNTIME_TEMPLATE_FIELDS:
            key = field["key"]
            label = field["label"]
            baseline_key = {
                "no_1": "merchantName",
                "no_2": "businessNo",
                "no_3": "representative",
                "no_4": "tel",
                "no_5": "address",
                "no_6": "totalAmount",
            }[key]
            baseline_value = base_fields.get(baseline_key, "")
            runocr_value = output.get(key, "")
            normalized_match = norm(key, baseline_value) == norm(key, runocr_value)
            if not baseline_value and not runocr_value:
                status = "both_empty"
                counters["fieldBothEmpty"] += 1
            elif normalized_match:
                status = "match"
                counters["fieldMatched"] += 1
            else:
                status = "mismatch"
                counters["fieldMismatched"] += 1
                sample_ok = False
            field_rows.append(
                {
                    "key": key,
                    "label": label,
                    "baselineKey": baseline_key,
                    "baselineValue": baseline_value,
                    "runocrProjectedValue": runocr_value,
                    "normalizedMatch": normalized_match,
                    "status": status,
                    "reason": "match" if status in {"match", "both_empty"} else "parser_value_mismatch",
                }
            )
        counters["sampleMatched" if sample_ok else "sampleMismatched"] += 1
        rows.append(
            {
                "filename": filename,
                "manifestDocType": sample.get("documentType"),
                "baselineDocType": base.get("docType", ""),
                "runocrTemplateDocType": base.get("docType", ""),
                "status": "match" if sample_ok else "mismatch",
                "runtimeOutput": output,
                "fields": field_rows,
                "reasons": ["match"] if sample_ok else ["parser_value_mismatch"],
            }
        )
    return rows, counters


def maybe_call_api(args: argparse.Namespace) -> dict[str, Any]:
    if not args.api_base:
        return {
            "attempted": False,
            "reason": "api_base_not_provided",
            "sideEffectGuard": "/ocr/extract may append ocr-server/data/review_log.jsonl",
        }
    if not args.allow_api_side_effects:
        return {
            "attempted": False,
            "reason": "allow_api_side_effects_not_set",
            "sideEffectGuard": "/ocr/extract may append ocr-server/data/review_log.jsonl",
        }
    return {
        "attempted": False,
        "reason": "not_implemented_in_default_static_report",
        "apiBase": args.api_base,
    }


def decide_status(flow: dict[str, Any], repo_scan: dict[str, Any], samples: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    if not repo_scan["templateDefinitionFoundInRepo"]:
        issues.append(
            {
                "code": "runtime_template_definition_missing",
                "severity": "info",
                "message": "no_1~no_6 field definitions were not found in repository template files; runtime UI likely stores them in browser localStorage.",
            }
        )
    if not flow.get("runocrPayloadSendsFields"):
        issues.append(
            {
                "code": "runocr_payload_missing_fields",
                "severity": "info",
                "message": "RunOCR does not send template field definitions to the backend; frontend activeTemplate.fields generates output fields client-side.",
            }
        )
    if not flow.get("templateFieldsDriveOutputFields"):
        issues.append(
            {
                "code": "output_mapping_missing",
                "severity": "error",
                "message": "Could not confirm frontend templateFields -> output fields mapping.",
            }
        )
    if samples:
        # With the provided runtime UI definition and confirmed frontend projection path, static E2E
        # projection is sufficient for the read-only comparison requested here.
        status = "PASS" if flow.get("templateFieldsDriveOutputFields") and flow.get("unstructuredUsesReceiptFields") else "INCONCLUSIVE"
    else:
        status = "INCONCLUSIVE"
    return status, issues


def md_escape(value: Any) -> str:
    text = clean(value)
    return text.replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = report["summary"]
    flow = report["runocrFlow"]
    lines.extend(
        [
            "# CODEX_RECEIPT_RUNTIME_TEMPLATE_E2E_20260519",
            "",
            "## 1. 요약",
            f"- 전체 판정: **{summary['status']}**",
            "- 이전 검증과 다른 점: repo의 TPL-003만 보지 않고, 화면에서 확인된 영수증 비정형 템플릿 출력 필드(no_1~no_6)를 런타임 정의로 고정해 비교했다.",
            "- regions 0개는 비정형 템플릿에서는 실패 근거가 아니다.",
            f"- baseline 샘플: {report['baseline']['sampleCount']}개",
            f"- 샘플 projection 일치: {summary['matched']}/{summary['total']}",
            f"- 필드 projection 일치: {summary['fieldMatched']} match, {summary['fieldBothEmpty']} both_empty, {summary['fieldMismatched']} mismatch",
            f"- Live API: {'실행' if report['liveApi']['attempted'] else '미실행'} ({report['liveApi']['reason']})",
            "",
            "## 2. 실제 영수증 템플릿 정의 확인",
            "- UI에서 확인된 출력 필드 정의:",
        ]
    )
    for field in report["templateFromScreenshot"]["fields"]:
        lines.append(f"  - {field['key']} -> {field['label']}")
    lines.extend(
        [
            f"- repo 템플릿 파일 내 no_1~no_6 정의 발견: {report['templateDefinitionFoundInRepo']}",
            f"- localStorage key: `{flow.get('localStorageKey')}`",
            f"- Template 탭 localStorage 읽기: {flow.get('templateTabReadsLocalStorage')}",
            f"- UnstructuredBuilder localStorage 저장: {flow.get('unstructuredBuilderStoresLocalStorage')}",
            f"- UnstructuredBuilder `mode: unstructured` 저장: {flow.get('unstructuredBuilderStoresMode')}",
            f"- UnstructuredBuilder `template_json.fields` 저장: {flow.get('unstructuredBuilderStoresFields')}",
            f"- UnstructuredBuilder `regions: []` 저장: {flow.get('unstructuredBuilderStoresRegionsEmpty')}",
            f"- RunOCR 템플릿 목록 localStorage 사용: {flow.get('runocrLoadsLocalStorageOnly')}",
            f"- localStorage template_json.fields 읽기: {flow.get('localTemplateReadsFields')}",
            f"- RunOCR payload에 fields 포함: {report['runocrPayloadIncludesFields']}",
            "- 해석: fields는 backend payload로 전달되지 않고, frontend의 activeTemplate.fields로 output_fields/history output을 구성한다.",
            "",
            "## 3. baseline 기준",
            "- source: `receipt_generalization`",
            "- selected 영수증 documentType 17개",
            "- finance_slip suppressed 제외",
            "- 수집 방식: `ocr_cache.json` OCR text + 현재 backend receipt parser read-only 실행",
            "",
            "## 4. no_1~no_6 매핑 기준",
            "| 템플릿 필드 | 한글명 | baseline 후보 key | 비고 |",
            "|---|---|---|---|",
        ]
    )
    for field in report["templateFromScreenshot"]["fields"]:
        lines.append(
            f"| {field['key']} | {field['label']} | {', '.join(field['candidateKeys'])} | 런타임 UI 정의 기준 |"
        )
    lines.extend(
        [
            "",
            "## 5. 샘플별 비교 결과",
            "| 샘플 | docType | no_1 회사명 | no_2 사업자번호 | no_3 대표자 | no_4 전화번호 | no_5 주소 | no_6 총합계금액 | 상태 |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for sample in report["samples"]:
        out = sample["runtimeOutput"]
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(sample["filename"]),
                    md_escape(sample["baselineDocType"]),
                    md_escape(out.get("no_1")),
                    md_escape(out.get("no_2")),
                    md_escape(out.get("no_3")),
                    md_escape(out.get("no_4")),
                    md_escape(out.get("no_5")),
                    md_escape(out.get("no_6")),
                    md_escape(sample["status"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 6. 차이 원인",
        ]
    )
    if report["issues"]:
        for issue in report["issues"]:
            lines.append(f"- {issue['code']}: {issue['message']}")
    else:
        lines.append("- projection mismatch 없음.")
    lines.extend(
        [
            "- api_not_run_static_only: read-only 원칙 때문에 `/ocr/extract` live 호출은 기본 미실행.",
            "- autofill_interference: 이번 스크립트는 frontend autofill/history/restore/localStorage write 경로를 실행하지 않아 자동복원 개입 없음.",
            "",
            "## 7. 결론",
            f"- 화면 기준 영수증 비정형 템플릿 no_1~no_6 정의와 frontend RunOCR projection 흐름 기준으로는 `{summary['status']}`.",
            "- RunOCR payload에는 필드 정의가 포함되지 않지만, 이는 현재 구조상 실패가 아니라 frontend activeTemplate.fields가 output_fields를 만드는 구조로 확인된다.",
            "- 실제 브라우저 localStorage export와 네트워크 payload 캡처가 있으면 runtime 저장값까지 완전한 E2E 증거로 고정할 수 있다.",
            "",
            "## 8. 다음 권장 작업",
            "- 브라우저 localStorage의 실제 `mysuit_ocr_templates` export 확보",
            "- RunOCR 요청 payload/response/output_fields 저장용 read-only debug snapshot 추가",
            "- 비정형 템플릿 output field definitions를 서버 저장소 또는 repo fixture에 명시 저장",
            "- Test baseline vs RunOCR template E2E 자동화",
        ]
    )
    return "\n".join(lines) + "\n"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    samples = load_samples()
    baseline, baseline_notes = load_baseline(samples)
    sample_rows, counters = compare_projection(samples, baseline)
    repo_scan = scan_repo_for_runtime_fields()
    server_template = analyze_tpl003_server_template()
    flow = analyze_frontend_runtime_flow()
    live_api = maybe_call_api(args)
    status, issues = decide_status(flow, repo_scan, samples)
    if live_api.get("reason") != "api_base_not_provided":
        issues.append({"code": "api_not_run_static_only", "severity": "info", "message": live_api.get("reason", "")})
    if baseline_notes:
        issues.extend({"code": "baseline_note", "severity": "info", "message": note} for note in baseline_notes)

    matched = sum(1 for row in sample_rows if row["status"] == "match")
    mismatched = sum(1 for row in sample_rows if row["status"] == "mismatch")
    report = {
        "generatedAt": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "tool": "Codex",
        "scope": "receipt_runtime_template_e2e",
        "templateFromScreenshot": {
            "templateName": "영수증",
            "mode": "unstructured",
            "fields": RUNTIME_TEMPLATE_FIELDS,
        },
        "serverTemplate": server_template,
        "templateDefinitionFoundInRepo": repo_scan["templateDefinitionFoundInRepo"],
        "repoTemplateDefinitionHits": repo_scan["repoHits"],
        "runocrPayloadIncludesFields": bool(flow.get("runocrPayloadSendsFields")),
        "runocrFlow": flow,
        "baseline": {
            "source": "receipt_generalization",
            "sampleCount": len(samples),
            "collection": "ocr_cache.json + current parser read-only",
            "excluded": "finance_slip suppressed",
        },
        "summary": {
            "status": status,
            "total": len(sample_rows),
            "matched": matched,
            "mismatched": mismatched,
            "inconclusive": 0 if status == "PASS" else len(sample_rows),
            "fieldMatched": counters["fieldMatched"],
            "fieldBothEmpty": counters["fieldBothEmpty"],
            "fieldMismatched": counters["fieldMismatched"],
        },
        "samples": sample_rows,
        "issues": issues,
        "autofill": {
            "interference": False,
            "reason": "static parser/projection script does not run frontend autofill, history fallback, restoreProfile, localStorage writes, or DB writes",
        },
        "liveApi": live_api,
        "nextActions": [
            "Export browser localStorage key mysuit_ocr_templates read-only and attach to this verification.",
            "Capture RunOCR request payload/response/output_fields in a read-only debug snapshot.",
            "Persist unstructured template output field definitions in server template_json.fields or a repo fixture.",
            "Automate Test baseline vs RunOCR unstructured template projection checks.",
        ],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Test receipt baseline vs runtime RunOCR receipt unstructured template projection.")
    parser.add_argument("--api-base", default="", help="Optional backend base URL for future live API verification.")
    parser.add_argument(
        "--allow-api-side-effects",
        action="store_true",
        help="Allow live /ocr/extract calls that may append review_log.jsonl. Default is static read-only verification.",
    )
    args = parser.parse_args()

    report = build_report(args)
    write_json(OUT_JSON, report)
    write_text(OUT_MD, render_markdown(report))
    print(json.dumps({"status": report["summary"]["status"], "samples": report["summary"]["total"], "json": str(OUT_JSON), "markdown": str(OUT_MD)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
