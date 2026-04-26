import re


def _group_rows(ocr_lines: list):
    """OCR 라인들을 행 기준으로 그룹핑.

    PaddleOCR v5 에서는 세로형 영수증에서 polygon 이 '세로로 긴 박스'로 들어오는 경우가 있어
    단순 y-span 기준 그룹핑이 전표 전체를 한 행으로 합쳐버릴 수 있다. 그런 경우에는 x축을
    읽기 진행축으로 간주해 행을 복구한다.
    """
    if not ocr_lines:
        return []

    def cy(line): ys = [p[1] for p in line[0]]; return (min(ys) + max(ys)) / 2
    def cx(line): xs = [p[0] for p in line[0]]; return (min(xs) + max(xs)) / 2
    def width(line): xs = [p[0] for p in line[0]]; return max(xs) - min(xs)
    def height(line): ys = [p[1] for p in line[0]]; return max(ys) - min(ys)

    widths = sorted(width(line) for line in ocr_lines)
    heights = sorted(height(line) for line in ocr_lines)
    median_w = widths[len(widths) // 2] if widths else 20
    median_h = heights[len(heights) // 2] if heights else 20
    vertical_layout = median_h > max(median_w * 1.8, 80)

    primary_center = cx if vertical_layout else cy
    secondary_center = cy if vertical_layout else cx
    primary_size = width if vertical_layout else height

    sorted_lines = sorted(ocr_lines, key=primary_center)
    primary_sizes = [primary_size(line) for line in sorted_lines]
    median_primary = sorted(primary_sizes)[len(primary_sizes) // 2] if primary_sizes else 20
    row_thr_scale = 0.45 if vertical_layout else 0.75
    row_thr = max(median_primary * row_thr_scale, 8)

    rows = []
    cur = [sorted_lines[0]]
    for line in sorted_lines[1:]:
        if abs(primary_center(line) - primary_center(cur[-1])) <= row_thr:
            cur.append(line)
        else:
            rows.append(sorted(cur, key=secondary_center))
            cur = [line]
    rows.append(sorted(cur, key=secondary_center))
    return rows


def _row_text(row):
    return ' '.join(t for _, t, _ in row)


def _single_line_rows(ocr_lines: list):
    return [[line] for line in (ocr_lines or []) if line and line[1]]


def _is_merchant_notice_row(text: str) -> bool:
    norm = re.sub(r'\s+', '', text or '')
    if re.search(r'다른경우|실제와|가맹점주소가|전기작업|작업지시|직원|식지|재발행|안내문|설명문구|예시문구|작성문구', norm, re.I):
        return True
    return bool(re.search(
        r'신고안내|여신금융|협회|고객센터|가맹점주소.*다른경우|crefia|'
        r'승인번호|카드번호|거래일시|매출전표|공급가액|부가세|합계|총계|품목|수량|단가|금액',
        norm,
        re.I,
    ))
