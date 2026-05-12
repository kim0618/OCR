"""T-6d-fix 자동 검증 스크립트 — invoice_statement 1~7 tableRows 추출 결과 검증

실행 방법:
  cd d:/Free_Vue/OCR/ocr-server
  python scripts/verify_invoice_table_rows_t6d.py

동작:
1. ocr_cache.json의 OCR 텍스트를 파싱해 합성 OcrLine 좌표를 생성
2. extract_invoice_statement_fields 실행
3. tableRows / tableMeta / tableDebug 수집
4. 샘플별 expected vs actual 컬럼 비교
5. markdown 리포트 생성 (T6d_fix_runall_based_row_column_report_20260512.md)

⚠️ 합성 좌표 한계:
- ocr_cache.json은 plain text만 저장 (좌표 없음)
- 각 OCR 토큰을 별도 y-위치에 배치하므로, 실제 OCR에서 같은 row에 있는 토큰들이
  synthetic 모드에서는 서로 다른 "row"로 분리됨
- 헤더 행의 여러 컬럼 레이블(품목, 규격, 수량 등)이 같은 y에 있어야 하지만
  synthetic에서는 각각 별도 y-행으로 처리됨 → header score 1~2로 낮아짐
- 실제 RunAll에서는 OCR이 실제 pixel 좌표로 제공하므로 header detection 정확도가 훨씬 높음
- rowCount 결과도 실제와 다를 수 있음 (synthetic row grouping ≠ real row grouping)
- 이 스크립트의 주 목적: 코드 로직 정확성 검증 + rejectedRows 분석 + 리포트 생성

실제 RunAll 결과 (기준값):
  1.jpg: rowCount=27 (실제 28, 1개 누락)
  2.pdf: rowCount=2 (실제 훨씬 많음, 대량 누락)
  3.pdf: rowCount=1, 4.pdf: rowCount=1, 5.pdf: rowCount=6, 6.pdf: rowCount=6, 7.pdf: rowCount=1
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from extractors.invoice_statement import (
    extract_invoice_statement_fields,
    _TABLE_ROW_COLUMNS,
    _match_header_to_canonical,
    _tr_extract_expiry_date,
    _HEADER_CANONICAL_MAP,
    _score_row_for_expected_columns,
    _find_expected_header_band,
)

# ── 샘플별 expected ────────────────────────────────────────────────────────────
EXPECTED: dict[str, dict] = {
    "1.jpg": {
        "required": ["itemName", "spec", "manufacturingNo", "expiryDate", "quantity", "unitPrice", "amount"],
        "optional": ["lotNo", "unit", "supplyAmount", "taxAmount", "totalAmount", "remark"],
        "actual_row_count": 28,
        "real_columns": ["품목", "규격", "제조번호", "유효기간", "수량", "단가", "금액"],
    },
    "2.pdf": {
        "required": ["itemCode", "itemName", "quantity", "unitPrice", "supplyAmount", "insuranceCode"],
        "optional": ["amount", "totalAmount", "remark"],
        "actual_row_count": None,
        "real_columns": ["NO", "품목코드", "품목명", "수량", "소비자단가", "공급단가", "공급금액", "보험No"],
    },
    "3.pdf": {
        "required": ["insuranceCode", "itemName", "spec", "quantity", "unitPrice", "amount",
                     "manufacturer", "manufacturingNo", "expiryDate"],
        "optional": ["lotNo", "serialNo", "remark"],
        "actual_row_count": None,
        "real_columns": ["순번", "보험코드", "품명", "규격", "수량", "단가", "금액", "제조회사", "제조번호/유효기간"],
    },
    "4.pdf": {
        "required": ["itemName", "lotNo", "unit", "quantity", "unitPrice", "supplyAmount", "taxAmount"],
        "optional": ["amount", "totalAmount", "remark"],
        "actual_row_count": None,
        "real_columns": ["품목명", "LotNo.", "단위", "수량", "단가", "공급가액", "세액"],
    },
    "5.pdf": {
        "required": ["itemName", "itemCode", "quantity", "unitPrice", "amount"],
        "optional": ["supplyAmount", "taxAmount", "totalAmount", "remark"],
        "actual_row_count": 6,
        "real_columns": ["품명", "품목코드", "수량", "단가", "금액"],
    },
    "6.pdf": {
        "required": ["itemCode", "itemName", "quantity", "lotNo", "expiryDate"],
        "optional": ["serialNo", "manufacturingNo", "unit", "remark"],
        "actual_row_count": 6,
        "real_columns": ["NO", "제품코드", "제품명", "수량", "LotNo", "유효일자"],
    },
    "7.pdf": {
        "required": ["itemName", "serialNo", "unit", "quantity"],
        "optional": ["lotNo", "manufacturingNo", "remark"],
        "actual_row_count": 1,
        "real_columns": ["품명", "시리얼/로트No.", "단위", "수량"],
    },
}


def _classify_token(text: str) -> str:
    """Classify an OCR token for rough x-position assignment."""
    t = text.strip()
    # header keyword → header position
    if _match_header_to_canonical(t) is not None:
        return "header"
    digits = re.sub(r"\D", "", t)
    # Date-like (YYYYMMDD or YYMMDD)
    if re.fullmatch(r"(?:20)?\d{6}", digits) and len(t) <= 12:
        return "date"
    # Amount (1,000+ with comma or large int)
    if re.search(r"\d{1,3}(?:,\d{3})+", t):
        return "amount"
    # Short integer ≤ 4 digits → possible quantity or lot fragment
    if re.fullmatch(r"\d{1,4}", digits) and len(t) <= 6:
        return "small_int"
    # Alphanumeric code (lot / manufacturing number)
    if re.search(r"[A-Za-z0-9]{3,}[-/][A-Za-z0-9]{3,}", t) or re.fullmatch(r"[A-Z]\d{4,}", t):
        return "code"
    if digits and len(digits) >= 4 and not re.search(r"[가-힣]", t):
        return "code"
    # Spec-like (e.g., 30T, 500mg, 150mI)
    if re.search(r"\d+(?:mg|ml|mI|T|C|G|g|p|포|정|캡|박)\b", t, re.I):
        return "spec"
    # Korean text → item name candidate
    if re.search(r"[가-힣]{2,}", t):
        return "name"
    return "other"


def make_synthetic_lines(ocr_text: str, page_w: float = 1000.0, page_h: float = 1400.0) -> list[tuple]:
    """Convert plain OCR text to synthetic (pts, text, confidence) tuples.

    Assigns approximate x positions based on token type to enable basic
    header detection and rough column testing.

    Column x positions (approximate):
      name:     80   (itemName)
      spec:     240  (spec)
      code:     370  (lotNo / itemCode)
      date:     470  (expiryDate)
      small_int:560  (quantity / unit)
      amount:   680  (unitPrice / amount)
      header:   depends on canonical key
      other:    150
    """
    X_MAP: dict[str, float] = {
        "name": 80.0,
        "spec": 240.0,
        "code": 370.0,
        "date": 470.0,
        "small_int": 560.0,
        "amount": 680.0,
        "other": 150.0,
    }
    # For header tokens, map canonical key to x
    HEADER_X_MAP: dict[str, float] = {
        "itemCode": 60.0, "itemName": 120.0, "spec": 230.0,
        "lotNo": 340.0, "serialNo": 340.0, "manufacturingNo": 380.0,
        "expiryDate": 460.0, "quantity": 540.0, "unit": 510.0,
        "unitPrice": 620.0, "supplyAmount": 700.0, "taxAmount": 760.0,
        "amount": 700.0, "totalAmount": 780.0,
        "manufacturer": 730.0, "insuranceCode": 50.0, "remark": 870.0,
    }

    tokens = [t.strip() for t in ocr_text.split("\n") if t.strip()]
    n = len(tokens)
    result: list[tuple] = []
    for i, text in enumerate(tokens):
        y = page_h * 0.05 + (page_h * 0.88) * i / max(n, 1)
        tok_class = _classify_token(text)
        if tok_class == "header":
            canon = _match_header_to_canonical(text)
            x = HEADER_X_MAP.get(canon or "", 300.0) if canon else 300.0
        else:
            x = X_MAP.get(tok_class, 150.0)
        w = max(20.0, min(len(text) * 9, page_w * 0.5))
        h = 22.0
        cx = x + w / 2
        pts = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
        result.append((pts, text, 0.9))
    return result


def run_sample(filename: str, ocr_text: str, table_expected_columns: dict | None = None) -> dict:
    """Run extraction on one sample and return structured result.

    T-6e: accepts table_expected_columns to test the expectedColumns-based header matching path.
    """
    synth_lines = make_synthetic_lines(ocr_text)
    debug: dict = {}
    try:
        fields = extract_invoice_statement_fields(
            synth_lines,
            debug=debug,
            table_expected_columns=table_expected_columns,
        )
    except Exception as e:
        return {"error": str(e), "fields": {}, "debug": {}}

    inv_debug = debug.get("invoice_statement", {})
    table_raw = inv_debug.get("table", {})
    table_debug_raw = fields.get("tableDebug") or table_raw.get("tableDebug") or {}

    table_rows = fields.get("tableRows") or []
    if isinstance(table_rows, str):
        table_rows = []
    table_meta = fields.get("tableMeta") or {}
    if isinstance(table_meta, str):
        table_meta = {}

    actual_cols: list[str] = []
    if isinstance(table_meta, dict):
        actual_cols = list(table_meta.get("columns") or [])
    if not actual_cols and table_rows:
        actual_cols = [
            k for k in _TABLE_ROW_COLUMNS
            if k != "rowIndex" and any(r.get(k) for r in table_rows if isinstance(r, dict))
        ]

    # T-6e: expected columns header matching results from tableDebug
    t6e_matched = table_debug_raw.get("matchedHeaders", [])
    t6e_missing = table_debug_raw.get("missingExpectedHeaders", [])
    t6e_interp = table_debug_raw.get("interpolatedColumns", [])
    t6e_fallback = table_debug_raw.get("fallbackReason", "")
    t6e_used = bool(isinstance(table_meta, dict) and table_meta.get("expectedColumnsUsed"))
    t6e_source = table_debug_raw.get("extractionSource", table_debug_raw.get("fallbackSource", "unknown"))

    return {
        "filename": filename,
        "rowCount": len(table_rows),
        "fields_rowCount": fields.get("rowCount", ""),
        "tableDetected": fields.get("tableDetected", "N"),
        "firstRowPreview": fields.get("firstRowPreview", "") or (isinstance(table_meta, dict) and table_meta.get("firstRowPreview", "")) or "",
        "extractionStatus": isinstance(table_meta, dict) and table_meta.get("extractionStatus") or "",
        "actualColumns": actual_cols,
        "tableRows": table_rows[:3],  # first 3 rows only for report
        "tableRows_all": table_rows,
        "tableDebug": table_debug_raw,
        "headerUsed": table_debug_raw.get("headerUsed", False),
        "headerFound": table_debug_raw.get("headerRowFound", False),
        "headerLines": table_debug_raw.get("headerLines", []),
        "boundaries": table_debug_raw.get("boundaries", []),
        "rejectedRows": table_debug_raw.get("rejectedRows", []),
        "fallbackSource": t6e_source,
        # T-6e
        "t6e_used": t6e_used,
        "t6e_matched": t6e_matched,
        "t6e_missing": t6e_missing,
        "t6e_interpolated": t6e_interp,
        "t6e_fallback": t6e_fallback,
        "t6e_source": t6e_source,
    }


def format_list(lst: list, max_items: int = 8) -> str:
    if not lst:
        return "—"
    items = [str(x) for x in lst[:max_items]]
    suffix = f" ...+{len(lst) - max_items}" if len(lst) > max_items else ""
    return ", ".join(items) + suffix


RUNALL_BEFORE: dict[str, int | None] = {
    "1.jpg": 27, "2.pdf": 2, "3.pdf": 1, "4.pdf": 1,
    "5.pdf": 6, "6.pdf": 6, "7.pdf": 1,
}


def generate_report(results: dict[str, dict]) -> str:
    lines: list[str] = []
    lines.append("# T-6e expectedColumns 기반 표 헤더 위치 매칭 추출 결과\n")
    lines.append(f"검증 방식: synthetic OCR (ocr_cache.json 텍스트 기반, 좌표 없음)\n")
    lines.append("⚠️ **합성 좌표 한계**: 실제 RunAll과 rowCount/column이 다를 수 있음. "
                 "실제 성능은 backend 재시작 후 브라우저 RunAll로 확인 필요.\n")
    lines.append("T-6e 핵심: OCR이 컬럼을 자동 발견하는 것이 아니라, "
                 "이미 정의된 expectedColumns 헤더를 OCR 결과에서 찾아 boundary를 구성하는 구조.\n")

    # Section 1: before/after rowCount
    lines.append("## 1. 수정 전/후 rowCount 비교\n")
    lines.append("| 샘플 | 실제 row 수 | 수정 전(RunAll) | 수정 후(synthetic) | 결과 | 비고 |")
    lines.append("|---|---:|---:|---:|---|---|")
    for fname, exp in EXPECTED.items():
        r = results.get(fname, {})
        actual_rc = exp.get("actual_row_count")
        before_rc = RUNALL_BEFORE.get(fname, "?")
        after_rc = r.get("rowCount", 0)
        actual_str = str(actual_rc) if actual_rc is not None else "?"
        if actual_rc is not None:
            match = "✓" if after_rc == actual_rc else f"✗ ({after_rc - actual_rc:+d})"
        else:
            match = "확인필요"
        note = r.get("error", "")[:40] if r.get("error") else "synthetic 제한"
        lines.append(f"| {fname} | {actual_str} | {before_rc} | {after_rc} | {match} | {note} |")
    lines.append("")

    # Section 6: rowCount (keep for compatibility)
    lines.append("## 6. 샘플별 rowCount 비교\n")
    lines.append("| 샘플 | 실제 row 수 | 추출 rowCount | 일치 여부 | 비고 |")
    lines.append("|---|---:|---:|---|---|")
    for fname, exp in EXPECTED.items():
        r = results.get(fname, {})
        actual_rc = exp.get("actual_row_count")
        extracted_rc = r.get("rowCount", 0)
        if actual_rc is None:
            match = "확인필요"
            actual_str = "?"
        else:
            actual_str = str(actual_rc)
            match = "✓" if extracted_rc == actual_rc else f"✗ (차이 {extracted_rc - actual_rc:+d})"
        err = r.get("error", "")
        note = err[:40] if err else ""
        lines.append(f"| {fname} | {actual_str} | {extracted_rc} | {match} | {note} |")
    lines.append("")

    # Section 7: expected vs actual columns
    lines.append("## 7. 샘플별 expected vs actual columns\n")
    lines.append("| 샘플 | expected required | actual columns | missing | hit rate |")
    lines.append("|---|---|---|---|---|")
    for fname, exp in EXPECTED.items():
        r = results.get(fname, {})
        required = exp["required"]
        actual = r.get("actualColumns", [])
        missing = [c for c in required if c not in actual]
        hit = len(required) - len(missing)
        rate = f"{hit}/{len(required)}"
        lines.append(
            f"| {fname} | {format_list(required, 9)} | {format_list(actual, 9)} "
            f"| {format_list(missing, 9)} | {rate} |"
        )
    lines.append("")

    # Section 8: tableDebug
    lines.append("## 8. tableDebug 요약\n")
    lines.append("| 샘플 | headerFound | headerLines | boundaries | fallback | rejectedRows | notes |")
    lines.append("|---|---|---|---|---|---|---|")
    for fname in EXPECTED:
        r = results.get(fname, {})
        hf = "✓" if r.get("headerFound") else "✗"
        hlines = format_list(r.get("headerLines", []), 5)
        bds = format_list([b.get("canonical_key", "?") for b in r.get("boundaries", [])], 8)
        fb = r.get("fallbackSource", "?")
        rej = len(r.get("rejectedRows", []))
        err = r.get("error", "")
        note = err[:30] if err else ""
        lines.append(f"| {fname} | {hf} | {hlines} | {bds} | {fb} | {rej}건 | {note} |")
    lines.append("")

    # Section 9: firstRowPreview
    lines.append("## 9. firstRowPreview 확인\n")
    lines.append("| 샘플 | firstRowPreview | extractionStatus | 비고 |")
    lines.append("|---|---|---|---|")
    for fname in EXPECTED:
        r = results.get(fname, {})
        preview = (r.get("firstRowPreview") or "")[:60]
        status = r.get("extractionStatus", "")
        note = "OK" if preview else "비어 있음"
        lines.append(f"| {fname} | {preview} | {status} | {note} |")
    lines.append("")

    # Section 10: row samples
    lines.append("## 10. 샘플별 tableRows 요약\n")
    for fname in EXPECTED:
        r = results.get(fname, {})
        rows = r.get("tableRows_all", [])
        lines.append(f"### {fname} (rowCount={r.get('rowCount', 0)})\n")
        if not rows:
            lines.append("- 추출된 row 없음\n")
            continue
        sample_rows = rows[:3]
        if fname == "1.jpg" and len(rows) >= 3:
            last3 = rows[-3:]
        else:
            last3 = []
        for i, row in enumerate(sample_rows):
            if not isinstance(row, dict):
                continue
            name = row.get("itemName", "—")
            qty = row.get("quantity", "—")
            lot = row.get("lotNo") or row.get("manufacturingNo") or row.get("serialNo") or "—"
            exp_d = row.get("expiryDate", "—")
            amt = row.get("amount") or row.get("supplyAmount") or "—"
            lines.append(f"- row{i+1}: itemName={name} / quantity={qty} / lot={lot} / expiry={exp_d} / amount={amt}")
        if last3:
            lines.append("- ...(중략)...")
            for i, row in enumerate(last3):
                if not isinstance(row, dict):
                    continue
                name = row.get("itemName", "—")
                qty = row.get("quantity", "—")
                amt = row.get("amount") or row.get("supplyAmount") or "—"
                lines.append(f"- row{len(rows)-2+i}: itemName={name} / quantity={qty} / amount={amt}")
        lines.append("")

    # Section 2: expected vs actual columns
    lines.append("## 2. 샘플별 컬럼 감지 비교\n")
    lines.append("| 샘플 | expected required | 수정 후 actual | missing 후 | 결과 |")
    lines.append("|---|---|---|---|---|")
    for fname, exp in EXPECTED.items():
        r = results.get(fname, {})
        required = exp["required"]
        actual = r.get("actualColumns", [])
        missing = [c for c in required if c not in actual]
        hit = len(required) - len(missing)
        rate = f"{hit}/{len(required)}"
        ok = "✓" if not missing else f"✗ {rate}"
        lines.append(
            f"| {fname} | {format_list(required, 9)} | {format_list(actual, 9)} "
            f"| {format_list(missing, 9)} | {ok} |"
        )
    lines.append("")
    lines.append("> ⚠️ synthetic 좌표로 인해 column 감지 결과는 실제 OCR과 다름. "
                 "실제 성능은 backend RunAll 기준으로 확인 필요.\n")

    # Section 3: rejectedRows analysis
    lines.append("## 3. rejectedRows 분석\n")
    lines.append("| 샘플 | rejected count | reason별 분포 | 비고 |")
    lines.append("|---|---:|---|---|")
    for fname in EXPECTED:
        r = results.get(fname, {})
        rejected = r.get("rejectedRows", [])
        reason_counts: dict[str, int] = {}
        for rr in rejected:
            reason = rr.get("reason", "unknown")
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        reason_str = ", ".join(f"{k}:{v}" for k, v in sorted(reason_counts.items()))
        note = r.get("fallbackSource", "?")
        lines.append(f"| {fname} | {len(rejected)} | {reason_str or '—'} | fallback={note} |")
    lines.append("")

    # Section 4: 1.jpg row 누락 원인 분석
    lines.append("## 4. 1.jpg rowCount 27 누락 원인 분석\n")
    lines.append("**실제 RunAll 결과**: rowCount=27 (실제 28, 1개 누락)\n")
    lines.append("**분석 (synthetic 기반, 실제 OCR 좌표 없음)**:\n")
    lines.append("- 1.jpg 헤더 토큰 '품' '목'이 synthetic 모드에서 각각 별도 y-행으로 분리됨")
    lines.append("  → '품목'을 한 토큰으로 인식 못해 itemName 컬럼 boundary 미생성")
    lines.append("- 실제 OCR에서는 '품목', '규격', '제조번호', '유효기간', '수량', '단가', '금액'이")
    lines.append("  같은 y-좌표에 위치 → header_score ≥ 6 → boundary 7개 정상 생성")
    lines.append("- **28번째 행 누락 추정 원인**:")
    lines.append("  1) 하드칼씨플러스정(item4): 제조번호/유효기간 없는 5-필드 행 → itemName 컬럼 배정 정상이어야 함")
    lines.append("  2) 영업소(팀)/도매관리팀 행이 item 영역에서 처리될 때 _is_business_contact_line 판정 불일치 가능")
    lines.append("  3) 마지막 item 행 직후 '소계' 행 → _is_summary_row_for_items=True → break")
    lines.append("  4) 27번 카운트가 맞다면 '이누스정5mg'(line119-124) 같은 6-필드 행이 하나 누락 가능성")
    lines.append("- **T-6d-fix 적용**: summary break를 items>0 AND y≥72% 조건으로 완화")
    lines.append("  → 실제 OCR에서 28번째 행이 소계 이전에 정상 처리될 것으로 예상\n")

    # Section 5: 2.pdf 대량 누락 원인 분석
    lines.append("## 5. 2.pdf row 대량 누락 원인 분석\n")
    lines.append("**실제 RunAll 결과**: rowCount=2 (실제 13개 이상 예상)\n")
    lines.append("**분석**:\n")
    lines.append("- 2.pdf는 landscape 이미지 (950×672): page_h=672")
    lines.append("- OCR 텍스트 line 2: '공급금액합계' = 헤더 영역 총액 → _is_summary_row_for_items 판정 위험")
    lines.append("- OCR 텍스트 line 41: '18,295,140소비자금액합계' → _TABLE_SUMMARY_STRONG_RE='합계' 매치 + amount=1 + name_chars<=14")
    lines.append("  → _is_summary_row_for_items=True → 기존 코드에서 **즉시 break** 발생")
    lines.append("- 실제 OCR에서: '18,295,140소비자금액합계'가 헤더 상단(y≈50)에 위치하여")
    lines.append("  아이템 행(y≈200~600) 이전에 처리됨 → break로 인해 나머지 13개 행 누락")
    lines.append("- **T-6d-fix 적용**:")
    lines.append("  ```")
    lines.append("  if items and row_y >= page_h * 0.72:  # 0.72*672=484")
    lines.append("      break  # 하단 summary → 테이블 끝")
    lines.append("  continue   # 상단 summary 또는 items없을 때 → 스킵하고 계속")
    lines.append("  ```")
    lines.append("  → y<484에서 등장하는 '18,295,140소비자금액합계'는 skip, 아이템 행 정상 추출 예상")
    lines.append("- 추가 fix: no_item_name 완화 → itemCode+quantity or quantity+price 조합으로 허용\n")

    # Section 11: header match check from OCR text
    lines.append("## 11. 헤더 패턴 매치 확인 (OCR 텍스트 기준)\n")
    lines.append("각 샘플의 실제 컬럼 헤더가 `_HEADER_CANONICAL_MAP`에서 어떻게 매핑되는지 정적 확인:\n")
    lines.append("| 샘플 | 실제 헤더 | canonical key | 매핑 여부 |")
    lines.append("|---|---|---|---|")
    for fname, exp in EXPECTED.items():
        for col in exp.get("real_columns", []):
            canon = _match_header_to_canonical(col)
            match = f"→ {canon}" if canon else "❌ 매핑 없음"
            lines.append(f"| {fname} | {col} | {match} | {'✓' if canon else '✗'} |")
    lines.append("")

    # Summary
    lines.append("## 12. 분석 요약\n")

    # rowCount issues
    rowcount_issues: list[str] = []
    for fname, exp in EXPECTED.items():
        r = results.get(fname, {})
        actual_rc = exp.get("actual_row_count")
        extracted_rc = r.get("rowCount", 0)
        if actual_rc is not None and extracted_rc != actual_rc:
            rowcount_issues.append(f"{fname}: expected {actual_rc}, got {extracted_rc} (diff={extracted_rc - actual_rc:+d})")
    if rowcount_issues:
        lines.append("### rowCount 불일치 (synthetic 기준):")
        for issue in rowcount_issues:
            lines.append(f"- {issue}")
    else:
        lines.append("### rowCount: 모두 일치 또는 확인 필요 없음")
    lines.append("")

    # Column issues
    col_issues: list[str] = []
    for fname, exp in EXPECTED.items():
        r = results.get(fname, {})
        required = exp["required"]
        actual = r.get("actualColumns", [])
        missing = [c for c in required if c not in actual]
        if missing:
            col_issues.append(f"{fname} missing: {', '.join(missing)}")
    if col_issues:
        lines.append("### Missing columns (synthetic, 참고용):")
        for issue in col_issues:
            lines.append(f"- {issue}")
    lines.append("")

    lines.append("### 검증 한계 (중요):")
    lines.append("- **ocr_cache.json은 plain text만 저장 (좌표 없음)** → synthetic 좌표는 실제와 근본적으로 다름")
    lines.append("- 실제 OCR에서는 헤더 행의 모든 토큰이 같은 y-좌표에 있어 header detection 정확도 높음")
    lines.append("- 이 스크립트로 검증된 것: _HEADER_CANONICAL_MAP 매핑 정확도, 코드 로직 오류 여부")
    lines.append("- 이 스크립트로 검증 불가: 실제 rowCount, 실제 column 배치 정확도")
    lines.append("- **실제 성능 확인**: backend 재시작 후 Test UI RunAll 실행 필요")
    lines.append("")

    # T-6e Section: expected header matching results
    lines.append("## 9. T-6e expected header matching 결과 (synthetic 좌표 기준)\n")
    lines.append("| 샘플 | expectedColumns 사용 | matched headers | missing required | interpolated | fallback 이유 | extractionSource |")
    lines.append("|---|---|---|---|---|---|---|")
    for fname, exp in EXPECTED.items():
        r = results.get(fname, {})
        used = "✓" if r.get("t6e_used") else "✗"
        matched = format_list(r.get("t6e_matched", []), 8)
        missing = format_list(r.get("t6e_missing", []), 8)
        interp = format_list(r.get("t6e_interpolated", []), 8)
        fb = r.get("t6e_fallback", "") or "—"
        src = r.get("t6e_source", "?")
        lines.append(f"| {fname} | {used} | {matched} | {missing} | {interp} | {fb} | {src} |")
    lines.append("")
    lines.append("> ⚠️ synthetic 좌표 한계: 헤더 토큰들이 서로 다른 y-행에 배치됨 → "
                 "같은 row로 묶이지 않아 score가 낮게 나옴. 실제 OCR에서는 정상 동작 예상.\n")

    # T-6e Section: header alias check
    lines.append("## 10. T-6e expected header alias 매핑 확인\n")
    lines.append("| 샘플 | 실제 헤더 텍스트 | canonical key | 매핑 여부 |")
    lines.append("|---|---|---|---|")
    for fname, exp in EXPECTED.items():
        for col in exp.get("real_columns", []):
            canon = _match_header_to_canonical(col)
            match_str = f"→ {canon}" if canon else "❌ 매핑 없음"
            ok = "✓" if canon else "✗"
            exp_keys = set(exp.get("required", []) + exp.get("optional", []))
            in_expected = "(expected)" if canon and canon in exp_keys else ""
            lines.append(f"| {fname} | {col} | {match_str} {in_expected} | {ok} |")
    lines.append("")

    lines.append("## 13. 다음 작업 판단\n")
    lines.append("**T-6e 적용 내용 요약**:")
    lines.append("1. `_score_row_for_expected_columns`: expected key 집합 기준 row scoring")
    lines.append("2. `_find_expected_header_band`: expected headers가 가장 많이 모인 y-band 탐색")
    lines.append("3. `_build_boundaries_from_expected_columns`: matched/interpolated boundary 생성")
    lines.append("4. `_table_items_with_expected_columns`: expectedColumns 기반 전체 추출 경로")
    lines.append("5. `_detect_table`: T-6e 경로 우선, T-6 auto-detect fallback")
    lines.append("6. `extract_invoice_statement_fields`: `table_expected_columns`, `table_bounds` 파라미터 추가")
    lines.append("")
    lines.append("**synthetic 검증 한계**:")
    lines.append("- ocr_cache.json에 좌표 없음 → 헤더 토큰들이 각각 별도 y-행으로 분리됨")
    lines.append("- 실제 OCR에서는 같은 row의 헤더 토큰들이 동일 y-좌표에 있어 score ≥ 3 이상 달성 예상")
    lines.append("- expectedColumns header matching 로직 자체는 alias 매핑 테이블로 검증 가능")
    lines.append("")
    lines.append("**판단**:")
    lines.append("- expectedColumns 기반 추출 구조 완성 → 실제 RunAll에서 성능 확인 필요")
    lines.append("- tableExpectedColumns가 backend에 전달되려면 frontend→backend API 파라미터 추가 필요")
    lines.append("  (현재 main.py 수정 금지로 미전달 → verify script에서 직접 파라미터 주입으로 검증)")
    lines.append("- 실제 RunAll 결과 확인 후:")
    lines.append("  - expected header matching 성공 → T-7 금액 계열 보정 가능")
    lines.append("  - expected header matching 실패 → table bounds/Template 연동 선행 필요")

    return "\n".join(lines)


def main():
    cache_path = ROOT / "mysuit-ocr" / "public" / "data" / "testsets" / "invoice_statement" / "ocr_cache.json"
    if not cache_path.exists():
        # Alternative path
        cache_path = ROOT.parent / "mysuit-ocr" / "public" / "data" / "testsets" / "invoice_statement" / "ocr_cache.json"
    if not cache_path.exists():
        print(f"ERROR: ocr_cache.json not found at {cache_path}")
        sys.exit(1)

    with open(cache_path, encoding="utf-8") as f:
        cache = json.load(f)

    print(f"Loaded ocr_cache.json with {len(cache)} samples")
    results: dict[str, dict] = {}
    for fname in EXPECTED:
        entry = cache.get(fname)
        if not entry:
            print(f"  SKIP: {fname} not in cache")
            results[fname] = {
                "error": "not in cache", "rowCount": 0, "actualColumns": [],
                "tableRows_all": [], "t6e_used": False, "t6e_matched": [],
                "t6e_missing": [], "t6e_interpolated": [], "t6e_fallback": "not_in_cache",
                "t6e_source": "not_in_cache",
            }
            continue
        ocr_text = entry.get("ocr_text", "")
        # T-6e: pass tableExpectedColumns from EXPECTED dict
        exp = EXPECTED[fname]
        tec = {"required": exp["required"], "optional": exp.get("optional", [])}
        print(f"  Processing {fname} ({len(ocr_text)} chars) with expectedColumns={exp['required'][:3]}...")
        r = run_sample(fname, ocr_text, table_expected_columns=tec)
        results[fname] = r
        t6e_info = f"t6e={'used' if r.get('t6e_used') else 'fallback'}({r.get('t6e_source','?')})"
        print(f"    rowCount={r['rowCount']}, actualCols={r['actualColumns'][:5]}, {t6e_info}")
        print(f"    matched={r.get('t6e_matched', [])[:5]}, missing={r.get('t6e_missing', [])[:3]}")

    report = generate_report(results)

    # T-6e: write to new report path (try sibling mysuit-ocr first, then parent)
    _candidates = [
        ROOT.parent / "mysuit-ocr" / "public" / "data" / "testsets" / "invoice_statement" / "reports",
        ROOT / "mysuit-ocr" / "public" / "data" / "testsets" / "invoice_statement" / "reports",
    ]
    report_dir = next((p for p in _candidates if p.parent.exists()), _candidates[0])
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "T6e_expected_columns_header_match_20260512.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    # Also update the T-6d report file for backward compatibility
    old_path = report_dir / "T6d_fix_runall_based_row_column_report_20260512.md"
    with open(old_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nReport written to: {out_path}")

    print(f"\nReport written to: {out_path}")

    # Also print summary to stdout
    print("\n=== T-6e SUMMARY ===")
    for fname, r in results.items():
        exp = EXPECTED[fname]
        required = exp["required"]
        actual = r.get("actualColumns", [])
        missing = [c for c in required if c not in actual]
        match_rc = ""
        if exp.get("actual_row_count") is not None:
            ok = r['rowCount'] == exp['actual_row_count']
            match_rc = f"rowCount={r['rowCount']}/{exp['actual_row_count']} {'OK' if ok else 'FAIL'}"
        t6e_info = f"t6e={'YES' if r.get('t6e_used') else 'fallback'} matched={r.get('t6e_matched',[])[:4]}"
        print(f"  {fname}: {match_rc}, missing_cols={missing[:4]}, {t6e_info}")


if __name__ == "__main__":
    main()
