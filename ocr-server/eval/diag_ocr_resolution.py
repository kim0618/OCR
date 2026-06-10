"""diag_ocr_resolution - P1 실측: free(950px) vs template(풀사이즈) OCR 글자 인식 차이.

질문: 품명 글자오류(헥사메딘→헥사메던)가 'OCR 모델 한계'인가, 아니면
      free 경로가 950px 다운스케일 이미지를 OCR에 넣어서인가?

방법: 같은 이미지를 두 조건으로 OCR해서 GT 품명이 그대로 읽히는지 비교.
  A) free-like   : 폭 950px 리사이즈(INTER_AREA) + CLAHE + 언샤프  (main.py 2549~2569 복제)
  B) template-like: 원본 풀사이즈 그대로                          (main.py 2341 복제)
해상도 변수만 격리하려고 둘 다 deskew는 적용 안 함(1.jpg는 정상 방향).
엔진은 production과 동일(get_ocr_engine).

실행(서버 venv): python eval/diag_ocr_resolution.py
         또는   python eval/diag_ocr_resolution.py --img <경로>
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)          # ocr-server
sys.path.insert(0, SERVER)

DEFAULT_IMG = os.path.normpath(os.path.join(
    SERVER, "..", "mysuit-ocr", "public", "data", "testsets", "invoice_study", "1.jpg"))
DEFAULT_COMPARE = os.path.join(
    HERE, "runs", "002_20260610_163020", "study", "compare", "1.jpg.json")


def _gt_item_names(compare_path: str) -> list[str]:
    """compare/1.jpg.json 에서 GT 품명들(정답) 추출."""
    if not os.path.isfile(compare_path):
        return []
    d = json.load(open(compare_path, encoding="utf-8"))
    names = []
    for row in d.get("table", {}).get("rows", []):
        cell = row.get("cells", {}).get("itemName", {})
        gt = (cell.get("gt") or "").strip()
        if gt:
            names.append(gt)
    return names


def _free_like(img):
    """main.py free 경로 전처리 복제: 950px + CLAHE + 언샤프."""
    h, w = img.shape[:2]
    ocr_max_w = 950
    if w > ocr_max_w:
        s = ocr_max_w / w
        img = cv2.resize(img, (ocr_max_w, int(h * s)), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(l)
    img = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    blur = cv2.GaussianBlur(img, (0, 0), 1.5)
    return cv2.addWeighted(img, 1.5, blur, -0.5, 0)


def _tokens(ocr, img) -> list[str]:
    from main import _parse_ocr_lines
    res = ocr.ocr(img)
    return [t for _, t, _ in _parse_ocr_lines(res) if t]


def _norm(s: str) -> str:
    return "".join(s.split())


def _present(name: str, tokens: list[str]) -> tuple[bool, str]:
    """name 이 토큰들 안에 그대로 있나? 없으면 가장 비슷한 토큰 반환."""
    nn = _norm(name)
    joined = _norm(" ".join(tokens))
    if nn in joined:
        return True, name
    near = difflib.get_close_matches(name, tokens, n=1, cutoff=0.3)
    return False, (near[0] if near else "—")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--img", default=DEFAULT_IMG)
    ap.add_argument("--compare", default=DEFAULT_COMPARE)
    a = ap.parse_args()

    if not os.path.isfile(a.img):
        print(f"이미지 없음: {a.img}")
        return 1
    img = cv2.imread(a.img)
    if img is None:
        print(f"이미지 로드 실패: {a.img}")
        return 1
    h, w = img.shape[:2]

    gt_names = _gt_item_names(a.compare)
    if not gt_names:
        print(f"(GT 품명 못 읽음: {a.compare} — 그래도 토큰 덤프는 진행)")

    print(f"이미지: {a.img}")
    print(f"원본 크기: {w}x{h}  ·  free 경로는 폭 950px로 다운스케일(축소율 {950/w:.2f})\n")

    from main import get_ocr_engine
    ocr = get_ocr_engine()

    print("== OCR 실행 중 (A: 950px free-like / B: 풀사이즈 template-like) ==")
    free_tokens = _tokens(ocr, _free_like(img))
    full_tokens = _tokens(ocr, img)
    print(f"   토큰 수: free(950px)={len(free_tokens)}  ·  full(풀사이즈)={len(full_tokens)}\n")

    if gt_names:
        print("=" * 78)
        print(f"{'GT 품명':30} {'950px':>7} {'풀사이즈':>8}   비고(틀리게 읽힌 토큰)")
        print("-" * 78)
        free_ok = full_ok = 0
        only_full = 0
        for name in gt_names:
            f_ok, f_near = _present(name, free_tokens)
            u_ok, u_near = _present(name, full_tokens)
            free_ok += f_ok
            full_ok += u_ok
            if u_ok and not f_ok:
                only_full += 1
            note = ""
            if not f_ok:
                note = f"950px→ {f_near}"
            if not u_ok:
                note += f"  | full→ {u_near}"
            print(f"{name:30} {'O' if f_ok else 'X':>7} {'O' if u_ok else 'X':>8}   {note}")
        print("-" * 78)
        n = len(gt_names)
        print(f"정확 인식:  950px {free_ok}/{n}  ·  풀사이즈 {full_ok}/{n}")
        print(f"풀사이즈에서만 맞은 품명(해상도 덕분): {only_full}건")
        print("=" * 78)
        print()
        if only_full > 0:
            print(f"★ 결론: 해상도 영향 확인 — 풀사이즈로 읽으면 {only_full}건이 추가로 정확해짐.")
            print("  → 인식오류는 'OCR 모델 한계'가 아니라 free의 950px 다운스케일 탓.")
            print("  → free에 고해상(표-크롭) 재OCR 배선 = 유효한 개선.")
        elif full_ok == free_ok:
            print("★ 결론: 해상도 영향 없음 — 950px와 풀사이즈 인식 동일.")
            print("  → 글자오류는 해상도가 아니라 다른 원인(엔진/전처리). 다른 접근 필요.")
        else:
            print("★ 결론: 혼재 — 표 보고 케이스별 판단 필요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
