"""
T-Template-Grid-1 가변 그리드 동작 검증 스크립트.

검증 항목:
1. 1.jpg (이미 mode=auto, stopKeywords=['소계','누계'], h=85 작은 박스)에 대해
   - variableGridExpanded == True
   - variableGridStopKeywordHit == True
   - variableGridStopKeyword 문자열 출력
   - variableGridScanYMax > variableGridOriginalYMax (확장됨)
   - rowCount == 28 (예상값과 일치)
   - tableRows에 '소계'/'누계' 행이 포함되지 않는지 검사
2. 같은 1.jpg를 mode='repeat'로 강제 변경한 비교 호출:
   - variableGridExpanded == False
   - rowCount < 28 (기존 동작 - 박스 안 1행만)
3. 같은 1.jpg에서 stopKeywords만 빈 배열로 만들고 mode='auto' 유지:
   - variableGridExpanded == True (mode='auto' 단독으로도 확장)
   - stopKeywordHit == False
   - rowCount 결과 기록 (참고용)
"""

from __future__ import annotations

import io
import json
import sys

# Windows cp949 console에서 UTF-8 출력 강제
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)
except Exception:
    pass
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any
from copy import deepcopy


BASE_URL = "http://127.0.0.1:9099"
ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "ocr-server"
FRONTEND_DIR = ROOT_DIR / "mysuit-ocr"
TESTSET_DIR = FRONTEND_DIR / "public/data/testsets/invoice_statement"
REPORT_DIR = TESTSET_DIR / "reports"
TEMPLATES_PATH = BACKEND_DIR / "data/templates.json"
MANIFEST_PATH = TESTSET_DIR / "manifest.json"

OUT_JSON = REPORT_DIR / "T_Template_Grid_1_variable_grid_20260517.json"
OUT_MD = REPORT_DIR / "T_Template_Grid_1_variable_grid_20260517.md"

SAMPLE = "1.jpg"
SAMPLE_MIME = "image/jpeg"
EXPECTED_ROW_COUNT = 28


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


def find_target_template(templates: list[dict[str, Any]], sample: str) -> dict[str, Any] | None:
    target = sample.lower()
    best = None
    best_updated = ""
    for t in templates:
        tj = t.get("template_json") or {}
        fn = (tj.get("file") or {}).get("name", "")
        if fn == target or target in (t.get("template_name") or "").lower():
            up = str(t.get("updated_at") or "")
            if up > best_updated:
                best_updated = up
                best = t
    return best


def make_multipart(fields: dict[str, str], file_bytes: bytes, filename: str, mime: str) -> tuple[bytes, str]:
    boundary = f"----codex-tgrid1-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        chunks.append(value.encode("utf-8"))
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}\r\n".encode("utf-8"))
    chunks.append((
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8"))
    chunks.append(file_bytes)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def expected_columns_from_manifest(sample: str, manifest: dict[str, Any]) -> dict[str, Any] | None:
    for item in manifest.get("items", []):
        if item.get("filename") == sample:
            return (item.get("invoiceProfile") or {}).get("tableExpectedColumns") or None
    return None


def call_extract(regions: list[dict[str, Any]], template_id: str, sample: str, manifest: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "template_id": template_id,
        "regions": json.dumps(regions, ensure_ascii=False),
        "model_id": "",
        "documentType": "invoice_statement",
    }
    cols = expected_columns_from_manifest(sample, manifest)
    if cols:
        fields["tableExpectedColumns"] = json.dumps(cols, ensure_ascii=False)
    file_bytes = (TESTSET_DIR / sample).read_bytes()
    body, boundary = make_multipart(fields, file_bytes, sample, SAMPLE_MIME)
    request = urllib.request.Request(
        f"{BASE_URL}/ocr/extract",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=420) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
        text = exc.read().decode("utf-8", errors="replace")
    elapsed = round(time.time() - started, 1)
    try:
        payload = json.loads(text)
    except Exception:
        payload = {"raw": text[:1000]}
    return {"http_status": status, "elapsed_sec": elapsed, "response": payload}


def row_text(row: Any) -> str:
    if isinstance(row, dict):
        return " ".join(str(v) for v in row.values() if v is not None)
    return str(row)


def has_stop_keyword_row(rows: list[Any], stop_keywords: list[str]) -> bool:
    norm = ["".join(str(k).split()) for k in stop_keywords if str(k).strip()]
    for r in rows:
        compact = "".join(row_text(r).split())
        for k in norm:
            if k and k in compact:
                return True
    return False


def summarize(call_result: dict[str, Any], stop_keywords: list[str]) -> dict[str, Any]:
    resp = call_result.get("response") or {}
    fields = resp.get("document_fields") or {}
    meta = fields.get("tableMeta") or {}
    rows = fields.get("tableRows") or []
    if not isinstance(rows, list):
        rows = []
    row_count = fields.get("rowCount")
    try:
        row_count_int = int(row_count) if row_count is not None and str(row_count).strip() else len(rows)
    except Exception:
        row_count_int = len(rows)
    return {
        "http_status": call_result.get("http_status"),
        "elapsed_sec": call_result.get("elapsed_sec"),
        "rowCount": row_count_int,
        "tableRowsCount": len(rows),
        "variableGridExpanded": meta.get("variableGridExpanded"),
        "variableGridStopKeywordHit": meta.get("variableGridStopKeywordHit"),
        "variableGridStopKeyword": meta.get("variableGridStopKeyword"),
        "variableGridScanYMax": meta.get("variableGridScanYMax"),
        "variableGridOriginalYMax": meta.get("variableGridOriginalYMax"),
        "extractionSource": meta.get("extractionSource"),
        "stopKeywordRowMixed": has_stop_keyword_row(rows, stop_keywords),
        "rowPreviewFirst": rows[:2],
        "rowPreviewLast": rows[-2:],
    }


def build_modified_regions(base_regions: list[dict[str, Any]], **overrides: Any) -> list[dict[str, Any]]:
    """table region에 대해 mode/stopKeywords를 덮어쓴 새 region 리스트 반환."""
    new_regions = deepcopy(base_regions)
    for r in new_regions:
        if r.get("fieldType") == "table":
            tm = r.setdefault("table", {})
            if "mode" in overrides:
                tm["mode"] = overrides["mode"]
            if "stopKeywords" in overrides:
                tm["stopKeywords"] = overrides["stopKeywords"]
            if "height" in overrides:
                r["height"] = overrides["height"]
            if "y" in overrides:
                r["y"] = overrides["y"]
    return new_regions


def main() -> int:
    templates = load_json(TEMPLATES_PATH, [])
    manifest = load_json(MANIFEST_PATH, {})
    target = find_target_template(templates, SAMPLE)
    if not target:
        print(f"[ERROR] {SAMPLE} 템플릿을 templates.json에서 찾을 수 없습니다.")
        return 1

    template_id = str(target.get("template_id") or "")
    tj = target.get("template_json") or {}
    base_regions = tj.get("regions") or []
    table_region_orig = next((r for r in base_regions if r.get("fieldType") == "table"), None)
    if not table_region_orig:
        print("[ERROR] 1.jpg 템플릿에 table region이 없습니다.")
        return 1
    orig_table_meta = table_region_orig.get("table") or {}
    orig_stop = orig_table_meta.get("stopKeywords") or []
    orig_height = table_region_orig.get("height")
    orig_y = table_region_orig.get("y")
    orig_mode = orig_table_meta.get("mode")

    print(f"[INFO] target template: {target.get('template_name')} | template_id={template_id}")
    print(f"  base region: y={orig_y}, height={orig_height}, mode={orig_mode}, stop={orig_stop}")

    # === CASE 1: 그대로 (mode=auto, stopKeywords 유지) - 가변 확장 + stopKeyword hit 기대 ===
    print("\n[CASE 1] mode=auto + stopKeywords 그대로 (가변 확장 + stop 기대)")
    r1 = call_extract(base_regions, template_id, SAMPLE, manifest)
    s1 = summarize(r1, orig_stop)
    print(f"  rowCount={s1['rowCount']} (expected {EXPECTED_ROW_COUNT})")
    print(f"  variableGridExpanded={s1['variableGridExpanded']}")
    print(f"  variableGridStopKeywordHit={s1['variableGridStopKeywordHit']}")
    print(f"  variableGridStopKeyword={s1['variableGridStopKeyword']}")
    print(f"  scanYMax={s1['variableGridScanYMax']} vs originalYMax={s1['variableGridOriginalYMax']}")
    print(f"  stopKeywordRowMixed={s1['stopKeywordRowMixed']} (False 기대)")

    # === CASE 2: mode=repeat 강제 (고정 그리드 회귀 확인) ===
    print("\n[CASE 2] mode=repeat 강제 (고정 그리드 - 기존 동작: 박스 안만 추출)")
    regions_repeat = build_modified_regions(base_regions, mode="repeat", stopKeywords=[])
    r2 = call_extract(regions_repeat, template_id, SAMPLE, manifest)
    s2 = summarize(r2, [])
    print(f"  rowCount={s2['rowCount']} (확장 비활성 → 작은 수 기대)")
    print(f"  variableGridExpanded={s2['variableGridExpanded']} (False 기대)")

    # === CASE 3: mode=auto + stopKeywords 비움 (mode 단독으로 확장) ===
    print("\n[CASE 3] mode=auto + stopKeywords=[] (mode 단독 확장)")
    regions_no_stop = build_modified_regions(base_regions, mode="auto", stopKeywords=[])
    r3 = call_extract(regions_no_stop, template_id, SAMPLE, manifest)
    s3 = summarize(r3, [])
    print(f"  rowCount={s3['rowCount']} (page_h * 0.98까지 확장, footer guard로 잡음 제거)")
    print(f"  variableGridExpanded={s3['variableGridExpanded']} (True 기대)")
    print(f"  variableGridStopKeywordHit={s3['variableGridStopKeywordHit']} (False 기대)")

    # 결과 평가
    verdict = {
        "case1_pass": (
            s1["variableGridExpanded"] is True
            and s1["variableGridStopKeywordHit"] is True
            and s1["rowCount"] == EXPECTED_ROW_COUNT
            and not s1["stopKeywordRowMixed"]
        ),
        "case2_pass": (
            s2["variableGridExpanded"] is False
            and (s2["rowCount"] is None or s2["rowCount"] < EXPECTED_ROW_COUNT)
        ),
        "case3_pass": (
            s3["variableGridExpanded"] is True
            and s3["variableGridStopKeywordHit"] is False
        ),
    }
    all_pass = all(verdict.values())

    report = {
        "task": "T-Template-Grid-1 verification",
        "sample": SAMPLE,
        "expectedRowCount": EXPECTED_ROW_COUNT,
        "case1_variable_grid_with_stop": s1,
        "case2_fixed_grid_repeat": s2,
        "case3_variable_grid_no_stop": s3,
        "verdict": verdict,
        "allPass": all_pass,
        "baseRegion": {"y": orig_y, "height": orig_height, "mode": orig_mode, "stopKeywords": orig_stop},
    }
    write_json(OUT_JSON, report)

    md = []
    md.append("# T-Template-Grid-1 가변 그리드 검증\n")
    md.append(f"- sample: `{SAMPLE}` | expected rowCount: **{EXPECTED_ROW_COUNT}**")
    md.append(f"- base region: y={orig_y}, height={orig_height}, mode={orig_mode}, stopKeywords={orig_stop}\n")
    md.append("## CASE 1: mode=auto + stopKeywords 그대로 (사용자 시나리오)\n")
    for k, v in s1.items():
        md.append(f"- {k}: `{json.dumps(v, ensure_ascii=False)}`")
    md.append("\n## CASE 2: mode=repeat 강제 (고정 그리드 회귀)\n")
    for k, v in s2.items():
        md.append(f"- {k}: `{json.dumps(v, ensure_ascii=False)}`")
    md.append("\n## CASE 3: mode=auto + stopKeywords=[] (mode 단독 확장)\n")
    for k, v in s3.items():
        md.append(f"- {k}: `{json.dumps(v, ensure_ascii=False)}`")
    md.append("\n## Verdict\n")
    for k, v in verdict.items():
        md.append(f"- {k}: **{'PASS' if v else 'FAIL'}**")
    md.append(f"\n**ALL PASS: {all_pass}**")
    write_text(OUT_MD, "\n".join(md))

    print("\n" + "=" * 60)
    print(f"verdict: {verdict}")
    print(f"ALL PASS: {all_pass}")
    print(f"\nWrote: {OUT_JSON}")
    print(f"Wrote: {OUT_MD}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    sys.exit(main())
