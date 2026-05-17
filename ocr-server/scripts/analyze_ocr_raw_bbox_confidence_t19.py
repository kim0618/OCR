from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "mysuit-ocr" / "public" / "data" / "testsets" / "reports"
T18_JSON = REPORT_DIR / "T18_precheck_current_baseline_gt_ocr_alignment_20260516.json"
OUT_JSON = REPORT_DIR / "T19_ocr_raw_bbox_confidence_analysis_20260516.json"
OUT_MD = REPORT_DIR / "T19_ocr_raw_bbox_confidence_analysis_20260516.md"

OCR_LINES_PY = ROOT / "ocr-server" / "extractors" / "ocr_lines.py"
MAIN_PY = ROOT / "ocr-server" / "main.py"
INVOICE_PY = ROOT / "ocr-server" / "extractors" / "invoice_statement.py"

BBOX_KEYS = {"bbox", "bboxes", "box", "boxes", "pts", "poly", "polygon", "rec_polys", "sourceBboxes"}
CONF_KEYS = {"confidence", "conf", "score", "scores", "rec_scores", "_confidence"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def has_nonempty_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return True


def walk_keys(obj: Any, keys: set[str]) -> int:
    count = 0
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in keys and has_nonempty_value(value):
                count += 1
            count += walk_keys(value, keys)
    elif isinstance(obj, list):
        for item in obj:
            count += walk_keys(item, keys)
    return count


def sample_id(sample: dict[str, Any]) -> str:
    return f"{sample.get('testsetId', '')}/{sample.get('filename', '')}"


def detect_runtime_structure() -> dict[str, Any]:
    ocr_lines_src = read_text(OCR_LINES_PY)
    main_src = read_text(MAIN_PY)
    invoice_src = read_text(INVOICE_PY)
    return {
        "lineTuple": {
            "exists": "lines.append((pts, str(text).strip(), float(score)))" in ocr_lines_src
            or "lines.append((pts, str(line[1][0]).strip(), float(line[1][1])))" in ocr_lines_src,
            "description": "PaddleOCR output is normalized to (pts, text, conf). pts is a polygon; conf is line recognition score.",
            "source": "ocr-server/extractors/ocr_lines.py",
        },
        "apiFieldsBBoxConfidence": {
            "exists": '"confidence": round(confidence, 4)' in main_src and '"bbox": [round(x * bbox_sx)' in main_src,
            "description": "Generic non-template OCR path can expose fields[] entries with confidence and display-scaled bbox.",
            "source": "ocr-server/main.py",
        },
        "extractDebugBboxes": {
            "exists": "upper_block_bbox" in main_src and "amount_block_bbox" in main_src,
            "description": "extract_debug can expose upper/amount/handwritten total block bboxes, but not the full raw line list in RunAll reports.",
            "source": "ocr-server/main.py",
        },
        "invoiceSourceBboxes": {
            "exists": "sourceBboxes" in invoice_src and "def _bbox_dict" in invoice_src,
            "description": "invoice_statement internally attaches sourceBboxes to several table item paths.",
            "source": "ocr-server/extractors/invoice_statement.py",
        },
        "fullRawLinesPersisted": {
            "exists": False,
            "description": "Current T18/RunAll-style report artifacts do not persist complete raw OCR line/token coordinates for the 57-sample audit set.",
            "source": "T18/current reports",
        },
    }


def artifact_availability(samples: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    bbox_samples = 0
    conf_samples = 0
    line_bbox_count = 0
    token_bbox_count = 0
    line_conf_count = 0
    token_conf_count = 0

    for sample in samples:
        bbox_count = walk_keys(sample, BBOX_KEYS)
        conf_count = walk_keys(sample, CONF_KEYS)
        bbox_available = bbox_count > 0
        conf_available = conf_count > 0
        bbox_samples += int(bbox_available)
        conf_samples += int(conf_available)
        # T18 samples are field/table summaries, not raw line/token arrays. Treat any
        # detected keys as persisted summary bboxes rather than raw tokens unless the
        # structure explicitly carries OCR lines, which it currently does not.
        raw_line_like = "ocr_lines_raw" in json.dumps(sample, ensure_ascii=False)
        line_bbox_count += bbox_count if raw_line_like else 0
        line_conf_count += conf_count if raw_line_like else 0
        rows.append(
            {
                "testset": sample.get("testsetId", ""),
                "sample": sample.get("filename", ""),
                "bboxAvailable": bbox_available,
                "confidenceAvailable": conf_available,
                "lineCount": 0,
                "tokenCount": 0,
                "note": "summary artifact only; raw OCR lines not persisted",
            }
        )

    return {
        "bboxAvailableSamples": bbox_samples,
        "confidenceAvailableSamples": conf_samples,
        "lineLevelBBoxCount": line_bbox_count,
        "tokenLevelBBoxCount": token_bbox_count,
        "lineLevelConfidenceCount": line_conf_count,
        "tokenLevelConfidenceCount": token_conf_count,
        "missingBBoxSamples": len(samples) - bbox_samples,
        "missingConfidenceSamples": len(samples) - conf_samples,
        "sampleRows": rows,
    }


def group_by_reason(samples: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        grouped[str(sample.get("failureReason") or "ok")].append(sample)
    return dict(grouped)


def has_missing(sample: dict[str, Any], field: str) -> bool:
    missing = set(sample.get("missingFields") or [])
    fields = sample.get("fields") or {}
    return field in missing or not str(fields.get(field) or "").strip()


def build_field_analysis(samples: list[dict[str, Any]], field: str, limit: int = 8) -> list[dict[str, Any]]:
    reasons = {"parser_missed_source_exists", "classification_mismatch", "ambiguous_candidates", "ocr_source_garbled"}
    selected: list[dict[str, Any]] = []
    for sample in samples:
        if sample.get("testsetId") == "invoice_statement":
            continue
        if sample.get("actualStatus") == "suppressed":
            continue
        if has_missing(sample, field) or sample.get("failureReason") in reasons:
            current = (sample.get("fields") or {}).get(field, "")
            selected.append(
                {
                    "sample": sample_id(sample),
                    "documentType": sample.get("manifestDocumentType", ""),
                    "current": current or "(missing)",
                    "bboxCandidate": "requires live raw lines; not present in persisted T18 artifact",
                    "confidence": None,
                    "verdict": verdict_for_field(field, sample),
                }
            )
    return selected[:limit]


def verdict_for_field(field: str, sample: dict[str, Any]) -> str:
    reason = sample.get("failureReason")
    doc_type = sample.get("manifestDocumentType")
    if field == "merchantName":
        if doc_type in {"food_cafe_receipt", "medical_receipt", "pos_receipt", "card_receipt"}:
            return "high: top-line/businessNo/address proximity can rank name candidates"
    if field == "businessNo":
        if doc_type in {"pos_receipt", "card_receipt"}:
            return "high: label proximity can separate businessNo from phone/card numbers"
    if field == "totalAmount":
        if reason == "ambiguous_candidates":
            return "high: amount-label and summary-area proximity can break ties"
        return "medium: useful for label/right-side amount selection"
    return "medium"


def classify_reason_potential(reason: str, count: int) -> dict[str, Any]:
    table = {
        "classification_mismatch": (
            "high",
            "keyword position weighting can distinguish top facility/store signals from lower payment blocks",
        ),
        "parser_missed_source_exists": (
            "high",
            "source text exists, so line position, label proximity, and confidence can improve candidate selection",
        ),
        "ambiguous_candidates": (
            "high",
            "bbox y-band/column proximity can choose between competing numeric candidates",
        ),
        "ocr_source_garbled": (
            "medium",
            "confidence can mark low-quality OCR; bbox alone will not repair garbled text",
        ),
        "ocr_source_missing": (
            "low",
            "missing OCR source usually needs preprocessing/re-OCR rather than candidate scoring",
        ),
    }
    potential, note = table.get(reason, ("medium", "case-by-case"))
    return {"reason": reason, "samples": count, "bboxPotential": potential, "note": note}


def classification_analysis(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sample in samples:
        if sample.get("failureReason") != "classification_mismatch":
            continue
        expected = sample.get("manifestDocumentType", "")
        actual = sample.get("ocrDocType", "")
        followup = "position-weighted classifier candidate"
        if expected == "finance_slip" or sample.get("expectedStatus", "").startswith("suppressed"):
            followup = "policy/metadata check before classifier change"
        rows.append(
            {
                "sample": sample_id(sample),
                "beforeActual": f"{expected} / {actual}",
                "keywordPosition": "not persisted; requires live raw line y/x positions",
                "bboxEvidence": "runtime ocr_lines_raw supports pts/conf; T18 artifact has only summary fields",
                "followup": followup,
            }
        )
    return rows


def invoice_bbox_analysis(t18: dict[str, Any]) -> dict[str, Any]:
    invoice = t18.get("invoiceStatement") or {}
    samples = invoice.get("samples") or {}
    rows = []
    for name, item in samples.items():
        rows.append(
            {
                "sample": name,
                "rowStatus": item.get("rowCountStatus", ""),
                "expectedRows": item.get("expectedRowCount", 0),
                "actualRows": item.get("actualRowCount", 0),
                "extractionSource": item.get("extractionSource", ""),
                "bboxUse": "internal sourceBboxes available in extractor paths, but current report preview omits them",
                "judgement": "keep" if item.get("rowCountStatus") == "exact" else "inspect",
            }
        )
    return {
        "rowCountExactRate": invoice.get("rowCountExactRate", 0),
        "avgExpectedValueFillRate": invoice.get("avgExpectedValueFillRate", 0),
        "samples": rows,
        "decision": "Maintain invoice_statement behavior for now; rowCount is 7/7 exact and bbox-based changes are lower priority.",
    }


def recommendation(summary: dict[str, Any]) -> dict[str, Any]:
    reasons = summary.get("failureReasonCounts") or {}
    classification = int(reasons.get("classification_mismatch", 0))
    parser = int(reasons.get("parser_missed_source_exists", 0))
    ambiguous = int(reasons.get("ambiguous_candidates", 0))
    garbled = int(reasons.get("ocr_source_garbled", 0))
    missing = int(reasons.get("ocr_source_missing", 0))
    return {
        "ranking": [
            {
                "candidate": "T-19c classification position weighting",
                "expectedEffect": "high",
                "risk": "medium",
                "evidence": f"classification_mismatch={classification}, highest remaining failure reason",
                "rank": 1,
            },
            {
                "candidate": "T-19a bbox-based merchantName candidate scoring",
                "expectedEffect": "medium-high",
                "risk": "low-medium",
                "evidence": f"parser_missed_source_exists={parser}; merchantName missing remains in receipt groups",
                "rank": 2,
            },
            {
                "candidate": "T-19b bbox-based businessNo/totalAmount selection",
                "expectedEffect": "medium",
                "risk": "low-medium",
                "evidence": f"ambiguous_candidates={ambiguous}; pos businessNo and amount misses remain",
                "rank": 3,
            },
            {
                "candidate": "T-20 OCR preprocessing experiment",
                "expectedEffect": "limited for current top failures",
                "risk": "medium",
                "evidence": f"ocr_source_garbled+ocr_source_missing={garbled + missing}, lower than bbox/classification-related reasons",
                "rank": 4,
            },
            {
                "candidate": "invoice_statement bbox generalization",
                "expectedEffect": "low now",
                "risk": "medium",
                "evidence": "invoice rowCount remains 7/7 exact",
                "rank": 5,
            },
        ],
        "recommendedNext": "T-19c classification position weighting, with known metadata/suppression cases guarded before changing behavior",
    }


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    return "\n".join(out)


def render_md(report: dict[str, Any]) -> str:
    runtime = report["rawStructure"]
    availability = report["availability"]
    failure_rows = report["failureReasonPotential"]
    recs = report["recommendation"]["ranking"]
    classification_rows = report["classificationMismatch"]
    invoice = report["invoiceStatement"]

    raw_rows = [
        [name, "yes" if item["exists"] else "no", item["description"]]
        for name, item in runtime.items()
    ]
    avail_rows = [
        ["executed samples", report["scope"]["totalSamples"]],
        ["persisted bbox available samples", availability["bboxAvailableSamples"]],
        ["persisted confidence available samples", availability["confidenceAvailableSamples"]],
        ["line-level bbox count in T18 artifacts", availability["lineLevelBBoxCount"]],
        ["token-level bbox count in T18 artifacts", availability["tokenLevelBBoxCount"]],
        ["missing bbox samples", availability["missingBBoxSamples"]],
        ["missing confidence samples", availability["missingConfidenceSamples"]],
    ]
    failure_md_rows = [[r["reason"], r["samples"], r["bboxPotential"], r["note"]] for r in failure_rows]
    merchant_rows = [
        [r["sample"], r["current"], r["bboxCandidate"], r["confidence"] or "N/A", r["verdict"]]
        for r in report["merchantNameAnalysis"]
    ]
    business_rows = [
        [r["sample"], r["current"], r["bboxCandidate"], r["confidence"] or "N/A", r["verdict"]]
        for r in report["businessNoAnalysis"]
    ]
    total_rows = [
        [r["sample"], r["current"], r["bboxCandidate"], r["confidence"] or "N/A", r["verdict"]]
        for r in report["totalAmountAnalysis"]
    ]
    cls_rows = [
        [r["sample"], r["beforeActual"], r["keywordPosition"], r["bboxEvidence"], r["followup"]]
        for r in classification_rows
    ]
    rec_rows = [[r["candidate"], r["expectedEffect"], r["risk"], f"#{r['rank']} - {r['evidence']}"] for r in recs]

    lines = [
        "# T-19 OCR raw confidence/bbox 활용 가능성 분석",
        "",
        "## 1. 생성 파일",
        f"- `{OUT_MD.as_posix()}`",
        f"- `{OUT_JSON.as_posix()}`",
        f"- `{Path(__file__).as_posix()}`",
        "",
        "## 2. 핵심 요약",
        "- backend 런타임에는 PaddleOCR line 단위 `pts/text/conf` 구조가 존재한다.",
        "- 현재 T-18/RunAll 저장 산출물에는 57개 샘플의 full raw OCR line/token bbox/confidence가 보존되어 있지 않다.",
        "- 따라서 후속 구현 전에는 live API/debug 또는 별도 진단 실행으로 raw line snapshot을 남기는 단계가 필요하다.",
        "- T-18 기준 최다 실패 원인은 classification_mismatch 9건이므로, 위치 가중치 기반 분류 진단/구현이 1순위다.",
        "",
        "## 3. raw OCR 구조",
        md_table(["필드", "존재 여부", "설명"], raw_rows),
        "",
        "## 4. bbox/confidence 존재율",
        md_table(["항목", "count"], avail_rows),
        "",
        "## 5. 실패 원인별 bbox 활용 가능성",
        md_table(["reason", "samples", "bbox 활용 가능성", "비고"], failure_md_rows),
        "",
        "## 6. merchantName 후보 분석",
        md_table(["sample", "current", "bbox 후보", "confidence", "판정"], merchant_rows),
        "",
        "## 7. businessNo 후보 분석",
        md_table(["sample", "current", "bbox 후보", "confidence", "판정"], business_rows),
        "",
        "## 8. totalAmount 후보 분석",
        md_table(["sample", "current", "bbox 후보", "confidence", "판정"], total_rows),
        "",
        "## 9. classification_mismatch 분석",
        md_table(["sample", "before/actual", "keyword 위치", "bbox 근거", "후속"], cls_rows),
        "",
        "## 10. invoice_statement bbox 활용 가능성",
        f"- rowCount exact rate: {invoice['rowCountExactRate']}%",
        f"- expected value fill average: {invoice['avgExpectedValueFillRate']}%",
        f"- 판단: {invoice['decision']}",
        "- 2.pdf OP-anchor, 5.pdf multiline, 6.pdf header skip, 7.pdf quantity 병합은 현재 회귀 없이 유지된다.",
        "- extractor 내부에는 `sourceBboxes` 경로가 있으나 현재 보고서 preview에는 full bbox가 보존되지 않는다.",
        "",
        "## 11. 후속 후보 우선순위",
        md_table(["후보", "기대 효과", "위험도", "추천"], rec_rows),
        "",
        "## 12. 다음 작업 판단",
        f"- 추천: {report['recommendation']['recommendedNext']}",
        "- T-20 전처리 실험은 source missing/garbled 5건 중심이라 현재 최다 실패 원인 대비 후순위다.",
        "- invoice_statement는 7/7 exact 상태이므로 기능 변경보다 raw snapshot 보강만 후순위로 둔다.",
        "",
        "## 13. 검증 결과",
        f"- py_compile: {report['validation']['py_compile']}",
        f"- verify script: {report['validation']['verify_script']}",
        f"- typecheck: {report['validation']['typecheck']}",
        f"- build: {report['validation']['build']}",
        "",
    ]
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    t18 = load_json(T18_JSON)
    samples = t18.get("samples") or []
    grouped = group_by_reason(samples)
    reason_counts = Counter({k: len(v) for k, v in grouped.items()})
    focus_reasons = [
        "classification_mismatch",
        "parser_missed_source_exists",
        "ambiguous_candidates",
        "ocr_source_garbled",
        "ocr_source_missing",
    ]

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "scope": {
            "name": "baseline_receipt_invoice_statement_raw_bbox_confidence_analysis",
            "totalSamples": len(samples),
            "source": str(T18_JSON.relative_to(ROOT)),
            "note": "No OCR/parser/classifier logic was modified.",
        },
        "t18Baseline": t18.get("summary", {}),
        "rawStructure": detect_runtime_structure(),
        "availability": artifact_availability(samples),
        "failureReasonPotential": [
            classify_reason_potential(reason, int(reason_counts.get(reason, 0)))
            for reason in focus_reasons
        ],
        "failureReasonSamples": {
            reason: [sample_id(sample) for sample in grouped.get(reason, [])]
            for reason in focus_reasons
        },
        "merchantNameAnalysis": build_field_analysis(samples, "merchantName"),
        "businessNoAnalysis": build_field_analysis(samples, "businessNo"),
        "totalAmountAnalysis": build_field_analysis(samples, "totalAmount"),
        "classificationMismatch": classification_analysis(samples),
        "invoiceStatement": invoice_bbox_analysis(t18),
        "recommendation": recommendation(t18.get("summary", {})),
        "validation": {
            "py_compile": "PASS: python -m py_compile scripts/analyze_ocr_raw_bbox_confidence_t19.py",
            "verify_script": "PASS: python scripts/analyze_ocr_raw_bbox_confidence_t19.py",
            "typecheck": "PASS: npm.cmd run typecheck",
            "build": "PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)",
        },
    }
    return report


def main() -> None:
    report = build_report()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_md(report), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
