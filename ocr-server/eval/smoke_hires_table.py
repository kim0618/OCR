"""smoke_hires_table - G2 검증(standalone): 표크롭 고해상 재OCR이 품명을 개선하나?

running 서버를 안 건드리고 main.py의 R002 로직을 그대로 재현해서,
pass1(950px) tableRows vs pass2(표크롭 고해상) tableRows 의 품명 정확도를 비교한다.

  python eval/smoke_hires_table.py   (OCR 엔진 필요, 느림)
"""
import difflib
import json
import os
import sys

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
sys.path.insert(0, SERVER)

IMG = os.path.normpath(os.path.join(
    SERVER, "..", "mysuit-ocr", "public", "data", "testsets", "invoice_study", "1.jpg"))
CMP = os.path.join(HERE, "runs", "002_20260610_163020", "study", "compare", "1.jpg.json")


def _gt_names():
    d = json.load(open(CMP, encoding="utf-8"))
    out = []
    for row in d.get("table", {}).get("rows", []):
        gt = (row.get("cells", {}).get("itemName", {}).get("gt") or "").strip()
        if gt:
            out.append(gt)
    return out


def _free_like(img):
    h, w = img.shape[:2]
    if w > 950:
        s = 950 / w
        img = cv2.resize(img, (950, int(h * s)), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(l)
    img = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    blur = cv2.GaussianBlur(img, (0, 0), 1.5)
    return cv2.addWeighted(img, 1.5, blur, -0.5, 0)


def _names_from_rows(rows):
    return [(_r.get("itemName") or "").strip() for _r in (rows or []) if (_r.get("itemName") or "").strip()]


def _count_match(gt_names, got_names):
    """GT 품명 중 got에 그대로(공백무시) 있는 개수."""
    got_compact = ["".join(g.split()) for g in got_names]
    joined = " ".join(got_compact)
    n = 0
    for name in gt_names:
        if "".join(name.split()) in joined:
            n += 1
    return n


def main():
    from main import get_ocr_engine, _parse_ocr_lines
    from extractors.invoice_statement_free import extract_invoice_statement_free
    from extractors.table_region import derive_table_bbox

    img = cv2.imread(IMG)
    H, W = img.shape[:2]
    gt = _gt_names()
    ocr = get_ocr_engine()

    print(f"이미지 {W}x{H}, GT 품명 {len(gt)}개\n")

    # pass1: 950px (free 1차)
    ocr_img = _free_like(img)
    ow, oh = ocr_img.shape[1], ocr_img.shape[0]
    p1_lines = _parse_ocr_lines(ocr.ocr(ocr_img))
    p1 = extract_invoice_statement_free(
        ocr_lines_raw=p1_lines, full_text="\n".join(t for _, t, _ in p1_lines),
        image_size=(ow, oh), doc_type="invoice_statement",
        context={"templateMode": False, "isUnstructuredTemplate": True})
    p1_rows = p1.get("tableRows") if isinstance(p1, dict) else None
    p1_names = _names_from_rows(p1_rows)
    print(f"pass1(950px): tableRows {len(p1_names)}행")

    # bbox 도출 → 풀해상 크롭 → pass2
    bb = derive_table_bbox(p1_lines, image_size=(ow, oh)) if p1_names else None
    print(f"표 bbox(950px): {bb}")
    p2_names = []
    if bb:
        sx, sy = W / float(ow), H / float(oh)
        x1, y1 = max(0, int(bb["x"] * sx)), max(0, int(bb["y"] * sy))
        x2 = min(W, int((bb["x"] + bb["width"]) * sx))
        y2 = min(H, int((bb["y"] + bb["height"]) * sy))
        crop = img[y1:y2, x1:x2]
        print(f"풀해상 크롭: {crop.shape[1]}x{crop.shape[0]}")
        hi_lines = _parse_ocr_lines(ocr.ocr(crop))
        p2 = extract_invoice_statement_free(
            ocr_lines_raw=hi_lines, full_text="\n".join(t for _, t, _ in hi_lines),
            image_size=(crop.shape[1], crop.shape[0]), doc_type="invoice_statement",
            context={"templateMode": False, "isUnstructuredTemplate": True, "hiResTableReocr": True})
        p2_rows = p2.get("tableRows") if isinstance(p2, dict) else None
        p2_names = _names_from_rows(p2_rows)
        print(f"pass2(표크롭 고해상): tableRows {len(p2_names)}행")

    m1 = _count_match(gt, p1_names)
    m2 = _count_match(gt, p2_names) if p2_names else 0
    print("\n" + "=" * 60)
    print(f"품명 정확(GT 대조):  pass1(950px) {m1}/{len(gt)}  →  pass2(고해상) {m2}/{len(gt)}")
    print("=" * 60)

    # 어느 품명이 pass2에서 새로 맞았나
    g1 = " ".join("".join(n.split()) for n in p1_names)
    g2 = " ".join("".join(n.split()) for n in p2_names)
    fixed = [n for n in gt if "".join(n.split()) not in g1 and "".join(n.split()) in g2]
    broke = [n for n in gt if "".join(n.split()) in g1 and "".join(n.split()) not in g2]
    if fixed:
        print(f"★ pass2에서 새로 맞은 품명({len(fixed)}): {fixed}")
    if broke:
        print(f"⚠ pass2에서 깨진 품명({len(broke)}): {broke}")
    if p2_names and m2 > m1:
        print("\n결론: 표크롭 고해상 재OCR이 품명 인식 개선 → G2 유효.")
    elif not p2_names:
        print("\n결론: pass2 행 없음 — bbox/크롭 점검 필요.")
    else:
        print("\n결론: 개선 없음/혼재 — 표 참고.")


if __name__ == "__main__":
    main()
