"""table_region - OCR 토큰에서 거래명세서 '표 영역' bbox를 도출한다 (순수 함수).

용도: free(완전비정형) 경로가 950px 저해상으로 표를 읽어 글자가 뭉개질 때,
이 함수로 표 영역만 찾아 풀해상 이미지에서 크롭→고해상 재OCR 하기 위함.

설계 원칙:
  - 순수 함수. OCR/이미지/전역 상태 접근 없음. 토큰 좌표만 본다.
  - 값(특정 품명) 기반이 아니라 **헤더/합계 키워드 패턴** 기반 = 일반화.
  - 헤더행(품명/규격/수량/단가/금액…)과 합계행(합계/소계/공급가액…) 사이의
    품목행 토큰들의 min/max 로 표 bbox 산출.
  - 못 찾으면 None (호출측은 재OCR 생략, 기존 동작 유지 = 안전).

입력 ocr_lines_raw: [(pts, text, conf), ...]  pts=[[x,y],...] (이미지 좌표계)
반환: {"x","y","width","height"}  (입력과 같은 좌표계) 또는 None
"""

from __future__ import annotations

import re
from typing import Any

# 표 컬럼 헤더에 나오는 토큰들 (한 행에 2개 이상이면 헤더행으로 판단)
_HEADER_KW = ("품명", "품목", "규격", "수량", "단가", "금액", "단위",
              "유효", "제조", "로트", "lot", "코드", "제품", "no")
# 표 아래 합계/요약행을 가리키는 토큰들 (헤더 아래 첫 등장 = 표 끝)
_FOOTER_KW = ("합계", "소계", "총합", "총금액", "청구금액", "인수자",
              "공급받는자", "받는자", "누계", "공급가액")


def _box(pts: Any) -> tuple[float, float, float, float] | None:
    """pts(폴리곤 or [x,y,w,h])에서 (x1,y1,x2,y2)."""
    try:
        if not pts:
            return None
        # 폴리곤 [[x,y],...]
        if isinstance(pts[0], (list, tuple)) and len(pts[0]) >= 2:
            xs = [float(p[0]) for p in pts]
            ys = [float(p[1]) for p in pts]
            return min(xs), min(ys), max(xs), max(ys)
        # [x,y,w,h]
        if len(pts) == 4:
            x, y, w, h = (float(v) for v in pts)
            return x, y, x + w, y + h
    except (TypeError, ValueError, IndexError):
        return None
    return None


def _rows_by_y(items: list[dict], tol_factor: float = 0.6) -> list[list[dict]]:
    """토큰을 y 근접도로 행 단위 묶음 (단순 밴드 클러스터)."""
    rows: list[list[dict]] = []
    for it in sorted(items, key=lambda d: (d["cy"], d["x1"])):
        if rows:
            cur = rows[-1]
            avg_cy = sum(d["cy"] for d in cur) / len(cur)
            avg_h = sum(d["h"] for d in cur) / len(cur)
            if abs(it["cy"] - avg_cy) <= max(avg_h, it["h"]) * tol_factor:
                cur.append(it)
                continue
        rows.append([it])
    return rows


def _kw_hits(text_compact: str, kws: tuple[str, ...]) -> int:
    t = text_compact.lower()
    return sum(1 for k in kws if k in t)


def derive_table_bbox(ocr_lines_raw: list, image_size: tuple[int, int] | None = None,
                      pad_ratio: float = 0.012) -> dict | None:
    """표 영역 bbox 도출. 못 찾으면 None.

    pad_ratio: 이미지 폭 기준 여백 비율(상하좌우 약간 넓혀 글자 잘림 방지).
    """
    items: list[dict] = []
    for line in ocr_lines_raw or []:
        try:
            pts, text, _conf = line[0], line[1], line[2]
        except (TypeError, IndexError):
            continue
        if not text:
            continue
        b = _box(pts)
        if not b:
            continue
        x1, y1, x2, y2 = b
        items.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2,
                      "cy": (y1 + y2) / 2.0, "h": max(1.0, y2 - y1),
                      "t": re.sub(r"\s+", "", str(text))})
    if not items:
        return None

    rows = _rows_by_y(items)
    if not rows:
        return None

    # 행별 텍스트 합쳐 헤더/합계 점수
    row_info = []
    for r in rows:
        joined = "".join(d["t"] for d in r)
        cy = sum(d["cy"] for d in r) / len(r)
        row_info.append({"row": r, "cy": cy,
                         "header": _kw_hits(joined, _HEADER_KW),
                         "footer": _kw_hits(joined, _FOOTER_KW)})
    row_info.sort(key=lambda d: d["cy"])

    # 헤더행 = header 키워드 2개 이상인 최상단 행
    header_idx = next((i for i, ri in enumerate(row_info) if ri["header"] >= 2), None)
    if header_idx is None:
        return None
    header_cy = row_info[header_idx]["cy"]

    # 합계행 = 헤더 아래에서 footer 키워드 등장하는 첫 행 (없으면 맨 끝)
    footer_cy = None
    for ri in row_info[header_idx + 1:]:
        if ri["footer"] >= 1:
            footer_cy = ri["cy"]
            break

    # 품목행 토큰 = 헤더 아래 ~ 합계 위
    body = [d for d in items if d["cy"] > header_cy and
            (footer_cy is None or d["cy"] < footer_cy)]
    if not body:
        return None

    # bbox = 헤더행 상단 ~ 품목행 하단, 좌우는 헤더+품목 토큰 min/max
    header_tokens = row_info[header_idx]["row"]
    span = header_tokens + body
    x1 = min(d["x1"] for d in span)
    x2 = max(d["x2"] for d in span)
    y1 = min(d["y1"] for d in header_tokens)   # 헤더 포함
    y2 = max(d["y2"] for d in body)

    # 여백
    if image_size:
        pad = max(4.0, image_size[0] * pad_ratio)
        x1 -= pad; y1 -= pad; x2 += pad; y2 += pad
        x1 = max(0.0, x1); y1 = max(0.0, y1)
        x2 = min(float(image_size[0]), x2); y2 = min(float(image_size[1]), y2)

    w = x2 - x1
    h = y2 - y1
    if w < 20 or h < 20:
        return None
    return {"x": int(round(x1)), "y": int(round(y1)),
            "width": int(round(w)), "height": int(round(h))}
