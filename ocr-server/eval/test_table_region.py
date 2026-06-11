"""test_table_region - G1 검증: derive_table_bbox 순수 함수.

  python eval/test_table_region.py          # 합성 토큰 단위테스트 (빠름)
  python eval/test_table_region.py --real    # 실제 1.jpg 950px OCR로 bbox 확인 (느림, 엔진 필요)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
sys.path.insert(0, SERVER)

from extractors.table_region import derive_table_bbox


def _poly(x, y, w, h):
    return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]


def _synth():
    """헤더행 + 품목 3행 + 합계행 합성. 표는 y≈100~250 영역."""
    lines = []
    # 상단 헤더영역(party) — 표 아님
    lines.append((_poly(40, 20, 200, 20), "공급자 일양약품", 0.9))
    lines.append((_poly(40, 50, 200, 20), "대표자 김동연", 0.9))
    # 표 헤더행 (y=100)
    for x, t in [(50, "품명"), (300, "규격"), (420, "수량"), (520, "단가"), (640, "금액")]:
        lines.append((_poly(x, 100, 60, 18), t, 0.9))
    # 품목행 3개
    for i, yy in enumerate((140, 180, 220)):
        lines.append((_poly(50, yy, 180, 18), f"품목{i}", 0.9))
        lines.append((_poly(420, yy, 40, 18), "100", 0.9))
        lines.append((_poly(520, yy, 60, 18), "2,730", 0.9))
        lines.append((_poly(640, yy, 70, 18), "273,000", 0.9))
    # 합계행 (y=270) — 표 끝
    lines.append((_poly(420, 270, 200, 18), "합계 819,000", 0.9))
    # 하단 푸터
    lines.append((_poly(40, 320, 200, 18), "인수자 확인", 0.9))
    return lines


def test_synth():
    lines = _synth()
    bb = derive_table_bbox(lines, image_size=(760, 400))
    assert bb is not None, "표 bbox를 못 찾음"
    # 헤더(y100)~품목하단(y238) 포함, 합계행(270)·party(20~70) 제외
    print(f"  합성 bbox: {bb}")
    assert bb["y"] <= 100, f"헤더(y=100) 미포함: y={bb['y']}"
    assert bb["y"] + bb["height"] < 270, f"합계행(y=270) 잘못 포함: bottom={bb['y']+bb['height']}"
    assert bb["y"] > 70, f"상단 party(y<=70) 잘못 포함: y={bb['y']}"
    assert bb["x"] <= 50 and bb["x"] + bb["width"] >= 710, f"좌우 범위 부족: {bb}"
    print("  [OK] 합성 테스트 통과")


def test_empty():
    assert derive_table_bbox([], (760, 400)) is None
    assert derive_table_bbox(None, (760, 400)) is None
    # 헤더 없음 → None (안전)
    no_header = [(_poly(40, 20, 200, 20), "공급자 일양약품", 0.9)]
    assert derive_table_bbox(no_header, (760, 400)) is None
    print("  [OK] 빈/헤더없음 → None (안전)")


def test_real():
    """실제 1.jpg를 950px로 OCR → bbox 도출 후 크롭 미리보기 저장."""
    import cv2
    img_path = os.path.normpath(os.path.join(
        SERVER, "..", "mysuit-ocr", "public", "data", "testsets", "invoice_study", "1.jpg"))
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    s = 950 / w
    ocr_img = cv2.resize(img, (950, int(h * s)), interpolation=cv2.INTER_AREA)
    from main import get_ocr_engine, _parse_ocr_lines
    ocr = get_ocr_engine()
    lines = _parse_ocr_lines(ocr.ocr(ocr_img))
    print(f"  1.jpg 950px 토큰 수: {len(lines)}")
    bb = derive_table_bbox(lines, image_size=(950, int(h * s)))
    print(f"  도출된 표 bbox(950px 공간): {bb}")
    assert bb is not None, "실제 이미지에서 표 bbox 못 찾음"
    # 크롭 미리보기 저장 (사람이 눈으로 확인용)
    crop = ocr_img[bb["y"]:bb["y"]+bb["height"], bb["x"]:bb["x"]+bb["width"]]
    out = os.path.join(HERE, "runs", "_table_region_preview.jpg")
    cv2.imwrite(out, crop)
    print(f"  크롭 미리보기 저장: {out}  (크기 {crop.shape[1]}x{crop.shape[0]})")
    # 표가 이미지의 상당부분(세로 20%+)을 차지해야 정상
    assert bb["height"] > int(h * s) * 0.15, "표 영역이 비정상적으로 작음"
    print("  [OK] 실제 1.jpg 표 영역 도출 성공")


if __name__ == "__main__":
    real = "--real" in sys.argv
    print("== G1: derive_table_bbox 단위테스트 ==")
    test_synth()
    test_empty()
    if real:
        print("== 실제 이미지 검증 (--real) ==")
        test_real()
    else:
        print("  (실제 이미지 검증은 --real 로)")
    print("ALL PASS")
