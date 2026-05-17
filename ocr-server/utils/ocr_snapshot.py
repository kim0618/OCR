"""
OCR raw line normalize / snapshot helper.

용도:
  - PaddleOCR raw line (pts, text, conf) → 공통 JSON snapshot 구조로 변환
  - cache-only 모드: ocr_cache.json 텍스트에서 synthetic bbox/position 추정
  - live-OCR 모드: 실제 PaddleOCR 결과를 그대로 변환
  - T-19a/T-19b/T-19c bbox 기반 후보 선택 분석의 기반 데이터 구조 제공

snapshot line 구조:
  {
    "page": 1,
    "lineIndex": 0,
    "text": "...",
    "confidence": float | null,   # null = cache-only (synthetic)
    "pts": [[x,y], ...] | null,   # null = cache-only
    "bbox": {"x":0, "y":0, "width":0, "height":0},
    "center": {"x":0, "y":0},
    "yRatio": 0.05,               # 문서 내 상대적 세로 위치 (0=상단, 1=하단)
    "synthetic": true             # true=추정값, false=실제 OCR
  }
"""
from __future__ import annotations
import re
from typing import Any


# ============================================================
# 라인 카테고리 분류용 패턴
# ============================================================
_AMOUNT_LIKE_RE = re.compile(r'\d{1,3}(?:,\d{3})+|\d{4,}(?:원|₩)?')
_BIZ_NO_RE = re.compile(r'[1-9]\d{2}[-\s.]\d{2}[-\s.]\d{5}')
_PHONE_RE = re.compile(r'\(?0\d{1,2}\)?[-\s]?\d{3,4}[-\s]?\d{4}')
_ADDRESS_RE = re.compile(r'서울|경기|인천|부산|대구|광주|대전|울산|충북|충남|전북|전남|경북|경남|제주|강원')
_DATE_RE = re.compile(r'\d{4}[-./]\d{1,2}[-./]\d{1,2}|\d{2}[-./]\d{2}[-./]\d{2}')
_NOISE_RE = re.compile(r'승인번호|카드번호|거래일시|매출전표|영수증|가맹|합계|총계|부가세|공급가액', re.I)
_MERCHANT_HINT_RE = re.compile(
    r'상호|가맹점|회사명|업체명|점명|가맹점명|상점명|'
    r'카페|커피|마트|편의점|식당|약국|병원|의원|치킨|버거|피자|베이커리|'
    r'coffee|cafe|baguette|GS25|CU|이마트|홈플러스', re.I
)


def categorize_line(text: str) -> str:
    """OCR 라인 텍스트를 카테고리로 분류."""
    if not text:
        return "empty"
    t = text.strip()
    if _NOISE_RE.search(t):
        return "noise_label"
    if _BIZ_NO_RE.search(t):
        return "biz_number"
    if _PHONE_RE.search(t):
        return "phone"
    if _ADDRESS_RE.search(t):
        return "address"
    if _DATE_RE.search(t):
        return "date"
    if _AMOUNT_LIKE_RE.search(t):
        return "amount_like"
    if _MERCHANT_HINT_RE.search(t):
        return "merchant_hint"
    # 짧고 순수 텍스트 → 상호 후보
    compact = re.sub(r'\s+', '', t)
    if 2 <= len(compact) <= 20 and not re.search(r'\d', compact):
        return "text_candidate"
    return "other"


def normalize_raw_line(
    pts: list | None,
    text: str,
    conf: float | None,
    page: int = 1,
    line_index: int = 0,
    total_lines: int = 1,
    img_width: int = 0,
    img_height: int = 0,
) -> dict[str, Any]:
    """PaddleOCR raw line (pts, text, conf) → snapshot 구조로 변환.

    live OCR 모드에서 사용. pts는 4점 다각형 [[x0,y0],[x1,y1],[x2,y2],[x3,y3]].
    """
    if pts is not None:
        try:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x, y = min(xs), min(ys)
            w, h = max(xs) - x, max(ys) - y
            cx, cy = x + w / 2, y + h / 2
            y_ratio = cy / img_height if img_height > 0 else 0.5
            bbox = {"x": round(x), "y": round(y), "width": round(w), "height": round(h), "source": "paddleocr"}
            center = {"x": round(cx, 1), "y": round(cy, 1)}
            synthetic = False
        except Exception:
            pts = None

    if pts is None:
        # synthetic fallback
        estimated_y = int(10 + line_index * 20)
        estimated_h = 14
        estimated_w = max(20, min(800, len(text) * 8))
        cx = estimated_w / 2
        cy = estimated_y + estimated_h / 2
        y_ratio = cy / max(img_height, 1) if img_height > 0 else (line_index / max(total_lines, 1))
        bbox = {"x": 10, "y": estimated_y, "width": estimated_w, "height": estimated_h, "source": "synthetic"}
        center = {"x": round(cx, 1), "y": round(cy, 1)}
        synthetic = True

    return {
        "page": page,
        "lineIndex": line_index,
        "text": text,
        "confidence": round(conf, 4) if conf is not None else None,
        "pts": pts,
        "bbox": bbox,
        "center": center,
        "yRatio": round(y_ratio, 4),
        "synthetic": synthetic,
        "category": categorize_line(text),
    }


def synthetic_lines_from_text(
    ocr_text: str,
    page: int = 1,
    img_height: int = 0,
) -> list[dict[str, Any]]:
    """cache-only 모드: ocr_cache.json 텍스트 → synthetic snapshot 라인 목록.

    bbox/confidence는 없으며, line index 기반으로 y_ratio를 추정한다.
    synthetic=True로 표시된다.
    """
    raw_lines = [ln.strip() for ln in (ocr_text or "").splitlines()]
    non_empty = [ln for ln in raw_lines if ln]
    total = len(non_empty)
    result = []
    for i, text in enumerate(non_empty):
        entry = normalize_raw_line(
            pts=None,
            text=text,
            conf=None,
            page=page,
            line_index=i,
            total_lines=total,
            img_height=img_height,
        )
        result.append(entry)
    return result


def extract_lines_from_paddleocr(
    ocr_result: Any,
    page: int = 1,
    img_width: int = 0,
    img_height: int = 0,
) -> list[dict[str, Any]]:
    """live OCR 모드: PaddleOCR 결과 → snapshot 라인 목록.

    _parse_ocr_lines 대신 snapshot 구조로 변환한다.
    """
    lines = []
    if not ocr_result or not ocr_result[0]:
        return lines
    r0 = ocr_result[0]
    if isinstance(r0, dict):
        items = zip(r0.get("rec_texts", []), r0.get("rec_scores", []), r0.get("rec_polys", []))
        for i, (text, score, poly) in enumerate(items):
            pts = poly.tolist() if hasattr(poly, "tolist") else poly
            entry = normalize_raw_line(pts, str(text).strip(), float(score), page, i, 0, img_width, img_height)
            lines.append(entry)
    else:
        for i, line in enumerate(r0):
            pts = line[0]
            text, conf = str(line[1][0]).strip(), float(line[1][1])
            entry = normalize_raw_line(pts, text, conf, page, i, 0, img_width, img_height)
            lines.append(entry)
    return lines


def summarize_snapshot(lines: list[dict[str, Any]]) -> dict[str, Any]:
    """라인 목록 요약: 카테고리 분포, bbox/confidence 가용성, 구역별 분포."""
    total = len(lines)
    has_conf = any(ln.get("confidence") is not None for ln in lines)
    has_bbox = any(not ln.get("synthetic", True) for ln in lines)
    avg_conf = None
    if has_conf:
        confs = [ln["confidence"] for ln in lines if ln.get("confidence") is not None]
        avg_conf = round(sum(confs) / len(confs), 4) if confs else None

    cat_counts: dict[str, int] = {}
    for ln in lines:
        c = ln.get("category", "other")
        cat_counts[c] = cat_counts.get(c, 0) + 1

    # 구역별 분포 (상단 30%, 중간 40%, 하단 30%)
    top_lines = [ln["text"] for ln in lines if ln.get("yRatio", 0) < 0.3]
    mid_lines = [ln["text"] for ln in lines if 0.3 <= ln.get("yRatio", 0) < 0.7]
    bot_lines = [ln["text"] for ln in lines if ln.get("yRatio", 0) >= 0.7]

    merchant_candidates = [ln["text"] for ln in lines if ln.get("category") == "text_candidate" and ln.get("yRatio", 1) < 0.4]
    amount_lines = [ln["text"] for ln in lines if ln.get("category") == "amount_like"]
    biz_lines = [ln["text"] for ln in lines if ln.get("category") == "biz_number"]

    return {
        "totalLines": total,
        "confidenceAvailable": has_conf,
        "bboxAvailable": has_bbox,
        "avgConfidence": avg_conf,
        "categoryDistribution": cat_counts,
        "topAreaLines": top_lines[:5],
        "merchantCandidates": merchant_candidates[:5],
        "amountLikeLines": amount_lines[:5],
        "bizNumberLines": biz_lines[:3],
        "zoneDistribution": {
            "top_30pct": len(top_lines),
            "mid_40pct": len(mid_lines),
            "bot_30pct": len(bot_lines),
        },
    }
