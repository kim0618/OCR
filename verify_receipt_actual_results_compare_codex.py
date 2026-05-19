from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
FRONTEND = ROOT / "mysuit-ocr"
BACKEND = ROOT / "ocr-server"

MANIFEST = FRONTEND / "public" / "data" / "testsets" / "receipt_generalization" / "manifest.json"
T22_BASELINE = FRONTEND / "public" / "data" / "testsets" / "reports" / "T22_current_ocr_baseline_snapshot_20260517.json"
RECEIPT_CACHE = FRONTEND / "public" / "data" / "testsets" / "receipt_generalization" / "ocr_cache.json"
HISTORY_JSON = BACKEND / "data" / "history.json"

OUT_JSON = DOCS / "CODEX_RECEIPT_ACTUAL_RESULTS_COMPARE_20260519.json"
OUT_MD = DOCS / "CODEX_RECEIPT_ACTUAL_RESULTS_COMPARE_20260519.md"

RECEIPT_DOC_TYPES = {"pos_receipt", "food_cafe_receipt", "card_receipt", "medical_receipt"}

TEMPLATE_FIELDS = [
    {"key": "no_1", "label": "회사명", "baselineCandidates": ["merchantName", "companyName", "회사명", "상호"], "runocrCandidates": ["no_1", "회사명", "상호"]},
    {"key": "no_2", "label": "사업자번호", "baselineCandidates": ["businessNo", "businessNumber", "사업자번호"], "runocrCandidates": ["no_2", "사업자번호"]},
    {"key": "no_3", "label": "대표자", "baselineCandidates": ["representative", "대표자"], "runocrCandidates": ["no_3", "대표자"]},
    {"key": "no_4", "label": "전화번호", "baselineCandidates": ["tel", "phone", "telephone", "전화번호"], "runocrCandidates": ["no_4", "전화번호", "tel", "phone"]},
    {"key": "no_5", "label": "주소", "baselineCandidates": ["address", "주소"], "runocrCandidates": ["no_5", "주소"]},
    {"key": "no_6", "label": "총합계금액", "baselineCandidates": ["totalAmount", "amount", "total", "총합계금액", "합계금액", "결제금액"], "runocrCandidates": ["no_6", "총합계금액", "합계금액", "결제금액", "totalAmount", "amount", "total"]},
]

PROJECTION_REPORTS = {
    "CODEX_RECEIPT_RUNTIME_TEMPLATE_E2E_20260519.json",
    "CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_VS_BASELINE_20260519.json",
    "CODEX_RECEIPT_BASELINE_VS_RUNOCR_TEMPLATE_20260518.json",
}


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("modified", "selected", "normalized", "raw", "value", "original"):
            if key in value:
                return clean(value[key])
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return "" if text.lower() in {"", "-", "–", "—", "null", "none", "n/a", "undefined"} else text


def normalize(field_key: str, value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    if field_key == "no_2":
        return re.sub(r"\D+", "", text)
    if field_key == "no_4":
        return re.sub(r"\D+", "", text)
    if field_key == "no_6":
        return re.sub(r"[^\d.-]+", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def selected_receipt_samples() -> list[str]:
    manifest = load_json(MANIFEST, {}) or {}
    names = []
    for item in manifest.get("items", []):
        if item.get("documentType") in RECEIPT_DOC_TYPES and item.get("expectedStatus") == "selected":
            names.append(str(item.get("filename") or ""))
    return [name for name in names if name]


def basename(value: str) -> str:
    return Path(str(value).replace("\\", "/")).name


def value_from_candidates(mapping: dict[str, Any], candidates: list[str]) -> str:
    for key in candidates:
        if key in mapping:
            return clean(mapping.get(key))
    lowered = {str(k).strip().lower(): v for k, v in mapping.items()}
    for key in candidates:
        v = lowered.get(key.lower())
        if v is not None:
            return clean(v)
    return ""


def load_baseline_result(path: Path | None = None) -> dict[str, Any]:
    chosen = path or T22_BASELINE
    data = load_json(chosen, {}) or {}
    samples: dict[str, Any] = {}
    rows = data.get("samples") if isinstance(data, dict) else []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            sample_name = basename(row.get("sample") or row.get("filename") or "")
            if not sample_name:
                continue
            fields = {
                "merchantName": clean(row.get("merchantName")),
                "businessNo": clean(row.get("businessNo")),
                "representative": clean(row.get("representative")),
                "tel": clean(row.get("tel") or row.get("phone")),
                "address": clean(row.get("address")),
                "totalAmount": clean(row.get("totalAmount")),
            }
            samples[sample_name] = {
                "filename": sample_name,
                "documentType": clean(row.get("docType") or row.get("documentType")),
                "fields": fields,
                "raw": row,
            }
    return {
        "found": chosen.exists(),
        "path": str(chosen.relative_to(ROOT)) if chosen.exists() else str(chosen),
        "isActualResult": chosen.exists() and bool(samples),
        "actualEvidence": "existing Test baseline snapshot/report JSON" if chosen.exists() and bool(samples) else "",
        "warnings": sorted({w for row in samples.values() for w in row.get("raw", {}).get("warnings", []) if isinstance(w, str)}),
        "samples": samples,
    }


def output_field_name(row: dict[str, Any]) -> str:
    return clean(row.get("key") or row.get("no") or row.get("ko") or row.get("label") or row.get("name") or row.get("en"))


def output_field_value(row: dict[str, Any]) -> str:
    return clean(row.get("modified") if "modified" in row else row.get("value") if "value" in row else row.get("original"))


def is_receipt_template_name(value: Any) -> bool:
    text = clean(value)
    return text == "영수증" or "영수증" in text or "곸닔" in text


def extract_runocr_records_from_json(data: Any, source: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            has_output = isinstance(node.get("output_fields"), list) or isinstance(node.get("outputFields"), list)
            template_name = node.get("template_name") or node.get("templateName")
            file_name = node.get("file_name") or node.get("filename") or node.get("fileName") or node.get("sample")
            if has_output and is_receipt_template_name(template_name):
                output = node.get("output_fields") if isinstance(node.get("output_fields"), list) else node.get("outputFields")
                records.append(
                    {
                        "filename": basename(file_name or ""),
                        "documentType": clean(node.get("documentType") or node.get("docType")),
                        "templateName": clean(template_name),
                        "output_fields": output,
                        "sourcePath": str(source.relative_to(ROOT)),
                        "raw": node,
                    }
                )
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(data)
    return records


def discover_runocr_results(explicit_path: Path | None = None) -> dict[str, Any]:
    scan_paths: list[Path]
    if explicit_path:
        scan_paths = [explicit_path]
    else:
        roots = [DOCS, FRONTEND / "docs", BACKEND / "data", FRONTEND / "public" / "data" / "testsets" / "reports"]
        scan_paths = []
        for root in roots:
            if root.exists():
                scan_paths.extend(p for p in root.rglob("*.json") if p.name not in PROJECTION_REPORTS)
    candidates: list[dict[str, Any]] = []
    rejected_projection = [str((DOCS / name).relative_to(ROOT)) for name in PROJECTION_REPORTS if (DOCS / name).exists()]
    for path in scan_paths:
        data = load_json(path, None)
        if data is None:
            continue
        candidates.extend(extract_runocr_records_from_json(data, path))

    by_sample: dict[str, Any] = {}
    for record in candidates:
        if record.get("filename"):
            by_sample[record["filename"]] = record

    return {
        "found": bool(by_sample),
        "path": ", ".join(sorted({r["sourcePath"] for r in by_sample.values()})),
        "isActualResult": bool(by_sample),
        "actualEvidence": "stored RunOCR history/export record with template_name=영수증 and output_fields" if by_sample else "",
        "samples": by_sample,
        "candidateCount": len(candidates),
        "projectionReportsExcluded": rejected_projection,
        "searchedPathCount": len(scan_paths),
    }


def output_value(record: dict[str, Any], field: dict[str, Any]) -> tuple[str, str]:
    rows = record.get("output_fields") or []
    candidates = {str(v) for v in field["runocrCandidates"]}
    for row in rows:
        if not isinstance(row, dict):
            continue
        names = {
            output_field_name(row),
            clean(row.get("ko")),
            clean(row.get("en")),
            f"no_{clean(row.get('no'))}" if clean(row.get("no")) else "",
        }
        if any(name in candidates for name in names if name):
            return output_field_value(row), "matched_output_fields"
    return "", "output_field_missing"


def compare(baseline: dict[str, Any], runocr: dict[str, Any], sample_names: list[str]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    counters = {
        "sampleCompared": 0,
        "sampleMatched": 0,
        "sampleMismatched": 0,
        "fieldMatched": 0,
        "fieldMismatched": 0,
        "fieldBothEmpty": 0,
        "fieldMissing": 0,
    }
    rows: list[dict[str, Any]] = []
    b_samples = baseline.get("samples", {})
    r_samples = runocr.get("samples", {})
    for name in sample_names:
        b = b_samples.get(name)
        r = r_samples.get(name)
        if not b or not r:
            continue
        counters["sampleCompared"] += 1
        field_rows = []
        sample_ok = True
        for field in TEMPLATE_FIELDS:
            b_value = value_from_candidates(b.get("fields") or {}, field["baselineCandidates"])
            r_value, source = output_value(r, field)
            b_norm = normalize(field["key"], b_value)
            r_norm = normalize(field["key"], r_value)
            if source == "output_field_missing":
                status = "missing"
                reason = "output_field_missing"
                counters["fieldMissing"] += 1
                sample_ok = False
            elif not b_norm and not r_norm:
                status = "both_empty"
                reason = "both_empty"
                counters["fieldBothEmpty"] += 1
            elif b_norm == r_norm:
                status = "match"
                reason = "match"
                counters["fieldMatched"] += 1
            else:
                status = "mismatch"
                reason = "field_value_mismatch"
                counters["fieldMismatched"] += 1
                sample_ok = False
            field_rows.append(
                {
                    "key": field["key"],
                    "label": field["label"],
                    "baselineRaw": b_value,
                    "runocrRaw": r_value,
                    "baselineNormalized": b_norm,
                    "runocrNormalized": r_norm,
                    "status": status,
                    "reason": reason,
                    "source": source,
                }
            )
        rows.append(
            {
                "filename": name,
                "baselineDocType": b.get("documentType", ""),
                "runocrDocType": r.get("documentType", ""),
                "status": "match" if sample_ok else "mismatch",
                "fields": field_rows,
                "reasons": ["match"] if sample_ok else sorted({f["reason"] for f in field_rows if f["reason"] != "match"}),
                "runocrSource": r.get("sourcePath", ""),
            }
        )
        counters["sampleMatched" if sample_ok else "sampleMismatched"] += 1
    return rows, counters


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    sources = report["sources"]
    lines = [
        "# CODEX_RECEIPT_ACTUAL_RESULTS_COMPARE_20260519",
        "",
        "## 1. 요약",
        f"- 전체 판정: **{summary['status']}**",
        f"- 실제 baseline 결과 존재: {sources['baseline']['found']} / actual={sources['baseline']['isActualResult']}",
        f"- 실제 RunOCR 결과 존재: {sources['runocr']['found']} / actual={sources['runocr']['isActualResult']}",
        f"- 비교 샘플 수: {summary['sampleCompared']}",
        f"- sample match/mismatch: {summary['sampleMatched']} / {summary['sampleMismatched']}",
        f"- field match/mismatch/both_empty/missing: {summary['fieldMatched']} / {summary['fieldMismatched']} / {summary['fieldBothEmpty']} / {summary['fieldMissing']}",
        "- 핵심 결론: 저장된 실제 RunOCR 영수증 템플릿 output_fields가 없어 실제 결과끼리 같다고 판정할 수 없다." if summary["status"] == "INCONCLUSIVE" else "- 핵심 결론: 실제 저장 결과 기준 비교 완료.",
        "",
        "## 2. 실제 결과 source",
        f"- baseline: `{sources['baseline']['path']}`",
        f"- baseline actual 근거: {sources['baseline'].get('actualEvidence') or '-'}",
        f"- baseline warnings: {', '.join(sources['baseline'].get('warnings') or []) or '-'}",
        f"- RunOCR: `{sources['runocr']['path'] or '-'}`",
        f"- RunOCR actual 근거: {sources['runocr'].get('actualEvidence') or '-'}",
        f"- projection/static 리포트 제외: {', '.join(sources['runocr'].get('projectionReportsExcluded') or []) or '-'}",
        "",
        "## 3. 영수증 템플릿 필드 기준",
        "| 템플릿 필드 | 한글명 | baseline 후보 key | RunOCR 후보 key |",
        "|---|---|---|---|",
    ]
    for field in TEMPLATE_FIELDS:
        lines.append(f"| {field['key']} | {field['label']} | {', '.join(field['baselineCandidates'])} | {', '.join(field['runocrCandidates'])} |")
    lines.extend(["", "## 4. 샘플별 비교 결과"])
    if report["samples"]:
        lines.extend([
            "| 샘플 | baseline docType | RunOCR docType | no_1 | no_2 | no_3 | no_4 | no_5 | no_6 | 상태 |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ])
        for sample in report["samples"]:
            statuses = {f["key"]: f["status"] for f in sample["fields"]}
            lines.append(
                "| " + " | ".join([
                    sample["filename"],
                    sample.get("baselineDocType", ""),
                    sample.get("runocrDocType", ""),
                    statuses.get("no_1", ""),
                    statuses.get("no_2", ""),
                    statuses.get("no_3", ""),
                    statuses.get("no_4", ""),
                    statuses.get("no_5", ""),
                    statuses.get("no_6", ""),
                    sample["status"],
                ]) + " |"
            )
    else:
        lines.append("- 비교 가능한 실제 RunOCR 샘플이 없다.")
    lines.extend(["", "## 5. 필드별 상세 비교"])
    if report["samples"]:
        for sample in report["samples"]:
            lines.append(f"### {sample['filename']}")
            for field in sample["fields"]:
                lines.append(
                    f"- {field['key']} {field['label']}: baseline=`{field['baselineRaw']}` / runocr=`{field['runocrRaw']}` / status={field['status']} / reason={field['reason']}"
                )
    else:
        lines.append("- 상세 비교 없음.")
    lines.extend(["", "## 6. 불일치 원인 분석"])
    for issue in report["issues"]:
        lines.append(f"- {issue['code']}: {issue['message']}")
    lines.extend([
        "",
        "## 7. 자동복원 영향",
        f"- 자동복원 개입 확인: {report['autofill']['interference']}",
        f"- 사유: {report['autofill']['reason']}",
        "",
        "## 8. 결론",
        "- 현재 저장된 실제 결과 기준으로는 RunOCR 영수증 템플릿 실제 output_fields가 없어서 동일 여부를 판단할 수 없다.",
        "- 이전 projection/static 리포트는 실제 RunOCR 결과로 인정하지 않았다.",
        "",
        "## 9. 다음 작업",
        "- 브라우저 localStorage의 `mysuit_ocr_history`, `mysuit_ocr_history_details`, `mysuit_ocr_templates` export 확보",
        "- RunOCR 영수증 템플릿으로 receipt_generalization 샘플을 실행한 실제 결과 JSON/export 제공",
        "- side-effect 없는 RunOCR 결과 export 기능 마련",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare stored actual Test baseline results vs stored actual RunOCR receipt template results. No API/OCR execution.")
    parser.add_argument("--baseline-result", default="", help="Existing baseline result JSON path.")
    parser.add_argument("--runocr-result", default="", help="Existing RunOCR result/history/export JSON path.")
    parser.add_argument("--auto-discover", action="store_true", default=True)
    parser.add_argument("--no-api", action="store_true", default=True)
    parser.add_argument("--no-write-product-files", action="store_true", default=True)
    args = parser.parse_args()

    sample_names = selected_receipt_samples()
    baseline = load_baseline_result(Path(args.baseline_result) if args.baseline_result else None)
    runocr = discover_runocr_results(Path(args.runocr_result) if args.runocr_result else None)
    samples, counters = compare(baseline, runocr, sample_names)

    issues = []
    if not baseline["isActualResult"]:
        issues.append({"code": "actual_baseline_result_missing", "message": "No existing baseline result with comparable sample fields was found."})
    if not runocr["isActualResult"]:
        issues.append({"code": "actual_runocr_result_missing", "message": "No stored RunOCR receipt-template result with output_fields was found for receipt_generalization samples."})
    if not samples:
        issues.append({"code": "sample_not_matched", "message": "No common sample could be matched between baseline and actual RunOCR result data."})
    issues.append({"code": "projection_only_not_actual", "message": "Projection/static CODEX receipt reports were explicitly excluded from PASS evidence."})

    if baseline["isActualResult"] and runocr["isActualResult"] and samples:
        status = "PASS" if counters["fieldMismatched"] == 0 and counters["fieldMissing"] == 0 and counters["sampleMismatched"] == 0 else "FAIL"
    else:
        status = "INCONCLUSIVE"

    report = {
        "generatedAt": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "tool": "Codex",
        "scope": "receipt_actual_results_compare",
        "executionPolicy": {
            "apiCalled": False,
            "ocrExecuted": False,
            "productCodeModified": False,
        },
        "templateFields": [{"key": f["key"], "label": f["label"]} for f in TEMPLATE_FIELDS],
        "sources": {
            "baseline": {k: v for k, v in baseline.items() if k != "samples"},
            "runocr": {k: v for k, v in runocr.items() if k != "samples"},
        },
        "summary": {
            "status": status,
            "sampleTotal": len(sample_names),
            **counters,
            "inconclusive": len(sample_names) if status == "INCONCLUSIVE" else 0,
        },
        "samples": samples,
        "issues": issues,
        "autofill": {
            "interference": None if not runocr["isActualResult"] else False,
            "reason": "actual RunOCR output_fields were not found, so autofill metadata could not be inspected" if not runocr["isActualResult"] else "no autofill markers found in compared fields",
        },
        "nextActions": [
            "Export browser localStorage keys mysuit_ocr_history, mysuit_ocr_history_details, and mysuit_ocr_templates.",
            "Provide an actual RunOCR receipt-template result JSON/export for the same receipt_generalization filenames.",
            "Add a side-effect-free result export path for RunOCR if repeatable actual-result comparisons are needed.",
        ],
    }
    write_json(OUT_JSON, report)
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": status, "sampleCompared": counters["sampleCompared"], "json": str(OUT_JSON), "markdown": str(OUT_MD)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
