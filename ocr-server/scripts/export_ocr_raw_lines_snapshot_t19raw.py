"""
T-19raw OCR raw line bbox/confidence snapshot export 스크립트.

목적:
  - 각 샘플의 OCR 텍스트에서 라인별 snapshot JSON을 생성
  - T-18 failure samples와 연결하여 각 실패 유형별 OCR 구조 분석
  - T-19a/T-19b/T-19c bbox 기반 개선 분석의 기반 데이터 제공

동작 모드:
  cache-only (기본):
    - ocr_cache.json의 ocr_text를 줄 단위로 분할
    - 라인 인덱스 기반으로 y_ratio(세로 위치) 추정
    - bbox/confidence: null (synthetic=true)
  live-ocr (미래):
    - 실제 OCR 엔진으로 이미지 처리 → 실제 pts/confidence 확보
    - --live-ocr 플래그로 활성화 (OCR 서버 실행 필요)

사용법:
  python scripts/export_ocr_raw_lines_snapshot_t19raw.py
  python scripts/export_ocr_raw_lines_snapshot_t19raw.py --all
  python scripts/export_ocr_raw_lines_snapshot_t19raw.py --testset receipt_generalization
  python scripts/export_ocr_raw_lines_snapshot_t19raw.py --failures-from ../mysuit-ocr/public/data/testsets/reports/T18_precheck_current_baseline_gt_ocr_alignment_20260516.json
  python scripts/export_ocr_raw_lines_snapshot_t19raw.py --sample receipt_generalization food_003.jpg
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public/data/testsets"
REPORTS = TESTSETS / "reports"
RAW_LINES_DIR = REPORTS / "ocr_raw_lines"

sys.path.insert(0, str(BACKEND))

from utils.ocr_snapshot import (  # type: ignore
    synthetic_lines_from_text,
    summarize_snapshot,
    categorize_line,
)

RECEIPT_TESTSETS = [
    "baseline", "baseline_fast", "google", "google_fast",
    "receipt_generalization", "invoice_statement",
]

# T-18 failure reason 설명
FAILURE_REASON_DESC = {
    "ok": "정상 추출",
    "classification_mismatch": "doc_type 오분류",
    "ocr_source_garbled": "OCR 원문 손상/garbled",
    "ocr_source_missing": "OCR 원문 없음",
    "parser_missed_source_exists": "OCR 원문 있으나 parser 미추출",
    "suppressed_policy": "suppressed 정책 (정상)",
    "metadata_mismatch": "manifest 오기입",
    "ambiguous_candidates": "후보 모호성",
}


def load_json(path: Path, default: Any = {}) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_ocr_text(testset_id: str, filename: str) -> str | None:
    """ocr_cache.json에서 OCR 텍스트를 읽는다. 없으면 None."""
    cache_path = TESTSETS / testset_id / "ocr_cache.json"
    if not cache_path.exists():
        return None
    cache = load_json(cache_path, {})
    entry = cache.get(filename)
    if not entry:
        return None
    return entry.get("ocr_text", "")


def get_manifest_item(testset_id: str, filename: str) -> dict:
    manifest = load_json(TESTSETS / testset_id / "manifest.json", {})
    for item in manifest.get("items", []):
        if item.get("filename") == filename:
            return item
    return {}


def build_sample_snapshot(
    testset_id: str,
    filename: str,
    failure_reason: str = "",
    missing_fields: list[str] | None = None,
    failure_details: str = "",
) -> dict[str, Any]:
    """단일 샘플의 snapshot 딕셔너리 생성."""
    manifest_item = get_manifest_item(testset_id, filename)
    ocr_text = get_ocr_text(testset_id, filename)

    if ocr_text is None:
        # invoice_statement 또는 ocr_cache 없는 testset
        return {
            "testsetId": testset_id,
            "filename": filename,
            "documentType": manifest_item.get("documentType", "unknown"),
            "qualityTags": manifest_item.get("qualityTags", []),
            "difficulty": manifest_item.get("difficulty", "unknown"),
            "failureReason": failure_reason,
            "failureDetails": failure_details,
            "missingFields": missing_fields or [],
            "cacheAvailable": False,
            "rawLineCount": 0,
            "bboxAvailable": False,
            "confidenceAvailable": False,
            "syntheticLines": True,
            "lines": [],
            "summary": {},
            "note": "ocr_cache.json 없음 (live RunAll 결과 또는 PDF OCR 필요)",
        }

    lines = synthetic_lines_from_text(ocr_text, page=1)
    summary = summarize_snapshot(lines)

    return {
        "testsetId": testset_id,
        "filename": filename,
        "documentType": manifest_item.get("documentType", "unknown"),
        "qualityTags": manifest_item.get("qualityTags", []),
        "difficulty": manifest_item.get("difficulty", "unknown"),
        "failureReason": failure_reason,
        "failureDetails": failure_details,
        "failureReasonDesc": FAILURE_REASON_DESC.get(failure_reason, failure_reason),
        "missingFields": missing_fields or [],
        "cacheAvailable": True,
        "rawLineCount": summary["totalLines"],
        "bboxAvailable": False,
        "confidenceAvailable": False,
        "syntheticLines": True,
        "lines": lines,
        "summary": summary,
    }


def load_failure_samples(t18_json: Path) -> list[dict]:
    """T-18 JSON에서 failure_reason != 'ok' 인 샘플을 반환."""
    data = load_json(t18_json, {})
    samples = data.get("samples", [])
    # all samples for completeness, sorted by failure_reason
    out = []
    for s in samples:
        out.append({
            "testsetId": s.get("testsetId", ""),
            "filename": s.get("filename", ""),
            "failureReason": s.get("failureReason", ""),
            "missingFields": s.get("missingFields", []),
            "ocrDocType": s.get("ocrDocType", ""),
            "documentType": s.get("documentType", s.get("manifestDocumentType", "")),
        })
    return out


def run_export(
    samples_to_process: list[dict],
    save_per_sample: bool = True,
    verbose: bool = True,
) -> dict[str, Any]:
    """지정된 샘플 목록에 대해 snapshot을 생성하고 결과를 반환."""
    all_snapshots = []
    total_lines = 0
    bbox_count = 0
    conf_count = 0
    failure_counts: dict[str, int] = {}

    for s in samples_to_process:
        ts = s.get("testsetId", "")
        fn = s.get("filename", "")
        reason = s.get("failureReason", "")
        missing = s.get("missingFields", [])

        if verbose:
            print(f"  Processing {ts}/{fn} (failureReason={reason or 'N/A'}, missing={missing})")

        snapshot = build_sample_snapshot(
            testset_id=ts,
            filename=fn,
            failure_reason=reason,
            missing_fields=missing,
        )

        all_snapshots.append(snapshot)
        total_lines += snapshot.get("rawLineCount", 0)
        if snapshot.get("bboxAvailable"):
            bbox_count += 1
        if snapshot.get("confidenceAvailable"):
            conf_count += 1
        failure_counts[reason] = failure_counts.get(reason, 0) + 1

        # 샘플별 JSON 저장
        if save_per_sample and snapshot.get("cacheAvailable"):
            safe_fn = fn.replace(".", "_")
            per_sample_path = RAW_LINES_DIR / f"{ts}_{safe_fn}.json"
            write_json(per_sample_path, snapshot)

    return {
        "totalSamples": len(all_snapshots),
        "totalLines": total_lines,
        "bboxAvailable": bbox_count,
        "confidenceAvailable": conf_count,
        "failureCounts": failure_counts,
        "samples": all_snapshots,
    }


def build_failure_linkage(snapshots: list[dict]) -> list[dict]:
    """T-18 failure 샘플과 snapshot 연결 분석."""
    linkage = []
    for s in snapshots:
        reason = s.get("failureReason", "")
        if reason in ("", "ok", "suppressed_policy"):
            continue
        summary = s.get("summary", {})
        linkage.append({
            "filename": s.get("filename"),
            "testsetId": s.get("testsetId"),
            "failureReason": reason,
            "failureReasonDesc": s.get("failureReasonDesc", ""),
            "missingFields": s.get("missingFields", []),
            "rawLineCount": s.get("rawLineCount", 0),
            "bboxAvailable": s.get("bboxAvailable", False),
            "confidenceAvailable": s.get("confidenceAvailable", False),
            "topAreaLines": summary.get("topAreaLines", []),
            "merchantCandidates": summary.get("merchantCandidates", []),
            "amountLikeLines": summary.get("amountLikeLines", []),
            "bizNumberLines": summary.get("bizNumberLines", []),
            "categoryDistribution": summary.get("categoryDistribution", {}),
            "analysisNote": _failure_analysis_note(reason, s),
        })
    return linkage


def _failure_analysis_note(reason: str, snapshot: dict) -> str:
    """failure reason별 T-19 활용 가능성 노트."""
    summary = snapshot.get("summary", {})
    merchant = summary.get("merchantCandidates", [])
    amount = summary.get("amountLikeLines", [])
    biz = summary.get("bizNumberLines", [])

    if reason == "parser_missed_source_exists":
        notes = []
        if merchant:
            notes.append(f"상단 상호 후보: {merchant[:2]}")
        if biz:
            notes.append(f"사업자번호 후보: {biz[:1]}")
        return " | ".join(notes) or "OCR text에서 후보 라인 추출 필요"
    elif reason == "ocr_source_garbled":
        return "OCR source 손상 → bbox 기반 재처리 또는 preprocessing 개선 후 재실행"
    elif reason == "classification_mismatch":
        return "doc_type 오분류 → position 기반 signal 가중치 개선 후보 (T-19c)"
    elif reason == "ocr_source_missing":
        return "PDF/이미지에서 OCR 원문 없음 → live OCR 재실행 필요"
    elif reason == "metadata_mismatch":
        return "manifest 오기입 → T-15e에서 확인됨, manifest 수정 필요"
    elif reason == "ambiguous_candidates":
        return "amount 후보 모호성 → bbox score 기반 선택 개선 후보 (T-19b)"
    return "분석 필요"


def main():
    parser = argparse.ArgumentParser(description="T-19raw OCR raw line snapshot export")
    parser.add_argument("--all", action="store_true", help="전체 57개 샘플 처리")
    parser.add_argument("--testset", type=str, help="특정 testset만 처리")
    parser.add_argument("--sample", nargs=2, metavar=("TESTSET", "FILENAME"),
                        help="특정 샘플 1개 처리")
    parser.add_argument("--failures-from", type=str,
                        help="T-18 JSON에서 failure 샘플만 처리")
    parser.add_argument("--no-per-sample", action="store_true",
                        help="샘플별 JSON 저장 안 함")
    args = parser.parse_args()

    OUT_JSON = REPORTS / "T19raw_ocr_raw_lines_snapshot_20260516.json"
    OUT_MD = REPORTS / "T19raw_ocr_raw_line_snapshot_export_20260516.md"
    RAW_LINES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"=== T-19raw OCR raw line snapshot export ===")
    print(f"generatedAt: {datetime.now().isoformat()}")

    # --- 대상 샘플 결정 ---
    t18_json = Path(args.failures_from) if args.failures_from else (
        REPORTS / "T18_precheck_current_baseline_gt_ocr_alignment_20260516.json"
    )

    if args.sample:
        ts_id, fn = args.sample
        samples_to_process = [{"testsetId": ts_id, "filename": fn, "failureReason": "", "missingFields": []}]
        scope = f"single:{ts_id}/{fn}"
    elif args.testset:
        # 특정 testset의 모든 샘플 (manifest에서)
        manifest = load_json(TESTSETS / args.testset / "manifest.json", {})
        samples_to_process = [
            {"testsetId": args.testset, "filename": item["filename"],
             "failureReason": "", "missingFields": []}
            for item in manifest.get("items", []) if item.get("filename")
        ]
        scope = f"testset:{args.testset}"
    elif args.all or args.failures_from:
        samples_to_process = load_failure_samples(t18_json)
        scope = f"t18_all_57"
    else:
        # 기본: T-18 failure 샘플만 (ok/suppressed_policy 제외)
        all_samples = load_failure_samples(t18_json)
        samples_to_process = [
            s for s in all_samples
            if s.get("failureReason", "") not in ("", "ok", "suppressed_policy")
        ]
        scope = f"t18_failures_only"

    print(f"scope: {scope}")
    print(f"처리 대상: {len(samples_to_process)}개 샘플\n")

    # --- Export 실행 ---
    save_per = not args.no_per_sample
    result = run_export(samples_to_process, save_per_sample=save_per, verbose=True)

    failure_linkage = build_failure_linkage(result["samples"])

    # --- 요약 출력 ---
    print(f"\n=== 결과 요약 ===")
    print(f"처리 샘플: {result['totalSamples']}")
    print(f"총 OCR 라인: {result['totalLines']}")
    print(f"bbox 보존: {result['bboxAvailable']}/{result['totalSamples']} (cache-only mode = 0)")
    print(f"confidence 보존: {result['confidenceAvailable']}/{result['totalSamples']} (cache-only mode = 0)")
    print(f"\nfailure reason 분포:")
    for reason, count in sorted(result["failureCounts"].items(), key=lambda x: -x[1]):
        desc = FAILURE_REASON_DESC.get(reason, reason)
        print(f"  {reason}({count}): {desc}")

    print(f"\n=== T-18 failure 연결 분석 ({len(failure_linkage)}건) ===")
    for link in failure_linkage:
        print(f"  {link['testsetId']}/{link['filename']}: [{link['failureReason']}] missing={link['missingFields']}")
        if link["merchantCandidates"]:
            print(f"    상호후보: {link['merchantCandidates'][:3]}")
        if link["bizNumberLines"]:
            print(f"    사업자: {link['bizNumberLines']}")
        if link["analysisNote"]:
            print(f"    분석: {link['analysisNote']}")

    # --- JSON 저장 ---
    out_data = {
        "task": "T-19raw",
        "generatedAt": datetime.now().isoformat(),
        "scope": scope,
        "mode": "cache_only",
        "bboxAvailableGlobal": False,
        "confidenceAvailableGlobal": False,
        "note": (
            "cache-only 모드: ocr_cache.json 텍스트에서 synthetic 라인 생성. "
            "실제 bbox/confidence는 live-OCR 모드(OCR 서버 + GPU 필요) 시에만 확보 가능. "
            "live 모드: /ocr/extract?debugRawLines=true 또는 --live-ocr 플래그 사용."
        ),
        "t19_readiness": {
            "T-19a_merchantName_bbox_scoring": "가능 (synthetic y_ratio 기반 위치 분석)",
            "T-19b_amount_bbox_selection": "가능 (synthetic y_ratio 기반 하단 필터)",
            "T-19c_classification_position": "가능 (synthetic position signal 분석)",
            "live_bbox_confidence": "미가능 (live OCR 엔진 필요)",
        },
        "totalSamples": result["totalSamples"],
        "totalLines": result["totalLines"],
        "bboxAvailable": result["bboxAvailable"],
        "confidenceAvailable": result["confidenceAvailable"],
        "failureCounts": result["failureCounts"],
        "t18FailureLinkage": failure_linkage,
        "samples": result["samples"],
    }
    write_json(OUT_JSON, out_data)
    print(f"\n결과 저장: {OUT_JSON}")

    # --- MD 리포트 ---
    _write_md_report(out_data, failure_linkage, result, OUT_MD, OUT_JSON)
    print(f"리포트 저장: {OUT_MD}")

    if save_per:
        per_sample_count = sum(1 for s in result["samples"] if s.get("cacheAvailable"))
        print(f"샘플별 JSON: {per_sample_count}건 → {RAW_LINES_DIR}/")


def _write_md_report(out_data: dict, failure_linkage: list[dict], result: dict, out_path: Path, json_path: Path | None = None) -> None:
    lines = [
        "# T-19raw OCR raw line bbox/confidence snapshot export 결과",
        "",
        "## 1. 수정 파일",
        "- `ocr-server/utils/ocr_snapshot.py` (신규) — normalize helper",
        "- `ocr-server/scripts/export_ocr_raw_lines_snapshot_t19raw.py` (신규) — export script",
        "",
        "## 2. 백업 파일",
        "- 코드 수정 없음 (신규 파일만 추가)",
        "",
        "## 3. 핵심 요약",
        f"- 처리 샘플: {result['totalSamples']}개",
        f"- 총 OCR 라인 (synthetic): {result['totalLines']}개",
        f"- bbox 실제 보존: 0/{result['totalSamples']} (cache-only 모드, live OCR 필요)",
        f"- confidence 실제 보존: 0/{result['totalSamples']} (cache-only 모드)",
        f"- T-18 failure 연결 분석: {len(failure_linkage)}건",
        "",
        "## 4. raw line normalize 구조",
        "| field | 설명 |",
        "|---|---|",
        "| page | PDF 페이지 번호 (이미지=1) |",
        "| lineIndex | 라인 인덱스 (0부터) |",
        "| text | OCR 텍스트 |",
        "| confidence | OCR 신뢰도 (0~1), cache-only 시 null |",
        "| pts | 4점 다각형 [[x,y]×4], cache-only 시 null |",
        "| bbox | {x,y,width,height,source}, synthetic or paddleocr |",
        "| center | {x,y} 중심점 |",
        "| yRatio | 문서 내 세로 위치 비율 (0=상단, 1=하단) |",
        "| synthetic | true=추정값, false=실제 OCR |",
        "| category | 라인 카테고리 (text_candidate/amount_like/biz_number/phone/address/date/noise_label/other) |",
        "",
        "## 5. snapshot 생성 결과",
        "| 항목 | 결과 |",
        "|---|---:|",
        f"| total samples | {result['totalSamples']} |",
        f"| bbox available (real) | {result['bboxAvailable']}/{result['totalSamples']} |",
        f"| confidence available (real) | {result['confidenceAvailable']}/{result['totalSamples']} |",
        f"| total synthetic raw lines | {result['totalLines']} |",
        "",
        "### failure reason 분포",
        "| reason | count | 설명 |",
        "|---|---:|---|",
    ]
    for reason, count in sorted(result["failureCounts"].items(), key=lambda x: -x[1]):
        desc = FAILURE_REASON_DESC.get(reason, reason)
        lines.append(f"| {reason} | {count} | {desc} |")

    lines += [
        "",
        "## 6. 실패 샘플 연결 결과",
        "| sample | reason | rawLineCount | merchant 후보 | biz 후보 | 활용 가능성 |",
        "|---|---|---:|---|---|---|",
    ]
    for link in failure_linkage:
        fn = f"{link['testsetId']}/{link['filename']}"
        mc = ", ".join(link["merchantCandidates"][:2]) or "-"
        bc = ", ".join(link["bizNumberLines"][:1]) or "-"
        note = link["analysisNote"][:50] if link["analysisNote"] else "-"
        lines.append(f"| {fn} | {link['failureReason']} | {link['rawLineCount']} | {mc} | {bc} | {note} |")

    lines += [
        "",
        "## 7. 저장 파일",
        f"- `{json_path.relative_to(FRONTEND.parent)}`" if json_path else "- (JSON 경로 미지정)",
        f"- `{out_path.relative_to(FRONTEND.parent)}`",
        f"- `mysuit-ocr/public/data/testsets/reports/ocr_raw_lines/{{testsetId}}_{{filename}}.json` (샘플별)",
        "",
        "## 8. 한계",
        "- **bbox/confidence 없음**: cache-only 모드에서는 실제 bbox/confidence 불가. live OCR 엔진 필요.",
        "- **synthetic y_ratio**: 줄 인덱스 기반 위치 추정, 실제 픽셀 위치와 다를 수 있음.",
        "- **multi-page**: PDF 다중 페이지 지원은 live OCR 모드에서만 가능.",
        "- **기본 응답 미포함**: 운영 /ocr/extract 응답에는 rawLines 미포함. debug 목적으로만 사용.",
        "",
        "### live OCR 모드 사용법 (미래, GPU 환경 필요)",
        "```python",
        "# main.py /ocr/extract 에 debugRawLines=true 추가 예시 (architecture hook)",
        "# POST /ocr/extract?debugRawLines=true",
        "# → response.extract_debug.rawLines = normalize된 raw line 목록",
        "```",
        "",
        "## 9. 다음 작업 판단",
        "",
        "### T-19 readiness",
        "| 작업 | 가능 여부 | 근거 |",
        "|---|---|---|",
        "| T-19a merchantName bbox scoring | **가능 (synthetic)** | y_ratio 기반 상단 라인 필터링 가능 |",
        "| T-19b amount bbox selection | **가능 (synthetic)** | y_ratio 기반 하단 영역 필터링 가능 |",
        "| T-19c classification position weighting | **가능 (synthetic)** | 라인 카테고리 + 위치 조합 분석 가능 |",
        "| live bbox/confidence 기반 개선 | **미가능** | 실제 OCR 엔진 실행 필요 (GPU 환경) |",
        "",
        "**결론: synthetic y_ratio 기반 T-19a/T-19b/T-19c 실험은 현재 가능. 실제 bbox precision 개선은 live OCR 환경 구축 후.**",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
