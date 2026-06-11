"""probe_invoice_resolution - 거래명세서 전용 해상도 스윕 (판단용·standalone).

질문: 비정형(free) 단일 OCR 패스를 950px 대신 더 높은 해상도로 하면
      free 파서 표 정확도가 순증하나? (R002 크롭방식과 달리 크롭·2차재구성 없음)

같은 1.jpg를 폭 [950, 1400, 1900, full] 로 OCR → free 파서 → 컬럼별 GT 대조 + 시간.
main.py 안 건드림. 영수증 무관(거래명세서만 보는 실험).

  python eval/probe_invoice_resolution.py
"""
import json
import os
import sys
import time

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
sys.path.insert(0, SERVER)

IMG = os.path.normpath(os.path.join(
    SERVER, "..", "mysuit-ocr", "public", "data", "testsets", "invoice_study", "1.jpg"))
CMP = os.path.join(HERE, "runs", "002_20260610_163020", "study", "compare", "1.jpg.json")
COLS = ["itemName", "spec", "quantity", "unitPrice", "amount"]


def _prep(img, target_w):
    """main.py free 전처리(CLAHE+언샤프) 동일, 단 폭만 가변. target_w=None이면 풀사이즈."""
    h, w = img.shape[:2]
    if target_w and w > target_w:
        s = target_w / w
        img = cv2.resize(img, (target_w, int(h * s)), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(l)
    img = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    blur = cv2.GaussianBlur(img, (0, 0), 1.5)
    return cv2.addWeighted(img, 1.5, blur, -0.5, 0)


def _norm(v):
    return "".join(str(v or "").split()).replace(",", "")


def _gt_rows():
    d = json.load(open(CMP, encoding="utf-8"))
    out = []
    for row in d.get("table", {}).get("rows", []):
        c = row.get("cells", {})
        out.append({k: (c.get(k, {}).get("gt") or "") for k in COLS})
    return out


def _score(rows, gt):
    per = {k: 0 for k in COLS}
    for i in range(min(len(rows), len(gt))):
        for k in COLS:
            gv = _norm(gt[i].get(k))
            if gv and _norm(rows[i].get(k)) == gv:
                per[k] += 1
    return per


def main():
    from main import get_ocr_engine, _parse_ocr_lines
    from extractors.invoice_statement_free import extract_invoice_statement_free

    img = cv2.imread(IMG)
    H, W = img.shape[:2]
    gt = _gt_rows()
    ocr = get_ocr_engine()
    print(f"원본 {W}x{H}, GT 품명 {len(gt)}\n")

    widths = [("950(현재)", 950), ("1400", 1400), ("1900", 1900), ("full", None)]
    results = []
    for label, tw in widths:
        prepped = _prep(img, tw)
        ow, oh = prepped.shape[1], prepped.shape[0]
        t0 = time.time()
        lines = _parse_ocr_lines(ocr.ocr(prepped))
        ocr_ms = (time.time() - t0) * 1000
        f = extract_invoice_statement_free(
            ocr_lines_raw=lines, full_text="\n".join(t for _, t, _ in lines),
            image_size=(ow, oh), doc_type="invoice_statement",
            context={"templateMode": False, "isUnstructuredTemplate": True})
        rows = (f.get("tableRows") if isinstance(f, dict) else None) or []
        sc = _score(rows, gt)
        results.append((label, ow, oh, ocr_ms, len(rows), sc))
        print(f"[{label:10}] {ow}x{oh}  OCR {ocr_ms:6.0f}ms  행수 {len(rows)}")

    print()
    hdr = f"{'해상도':12} {'OCRms':>7} {'행':>4}  " + " ".join(f"{c[:6]:>7}" for c in COLS) + f"  {'합계':>6}"
    print(hdr); print("-" * len(hdr))
    base = None
    for label, ow, oh, ms, nr, sc in results:
        tot = sum(sc.values())
        if base is None:
            base = tot
        cells = " ".join(f"{sc[c]:>7}" for c in COLS)
        delta = f" ({tot-base:+d})" if tot != base else ""
        print(f"{label:12} {ms:>7.0f} {nr:>4}  {cells}  {tot:>6}{delta}")
    print("-" * len(hdr))
    print(f"(컬럼 합계 만점 = {len(gt)*len(COLS)})\n")

    best = max(results, key=lambda r: sum(r[5].values()))
    cur = results[0]
    bt, ct = sum(best[5].values()), sum(cur[5].values())
    if best[0] != "950(현재)" and bt > ct:
        print(f"★ {best[0]}이 950px보다 컬럼 +{bt-ct} (OCR {best[3]:.0f}ms vs {cur[3]:.0f}ms).")
        print("  → 거래명세서 전용 해상도 상향 = net-positive 후보. 6장 전체로 확정 필요.")
    else:
        print(f"★ 950px가 최고이거나 동률 → 해상도 상향 효과 없음(1.jpg). 재검토.")


if __name__ == "__main__":
    main()
