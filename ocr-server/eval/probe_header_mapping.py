"""probe_header_mapping - 이식 가치 실측: 같은 토큰으로 free(위치추측) vs template(헤더매핑) 표 비교.

이식 전 판단: 템플릿의 헤더-기반 컬럼매핑 표가 free의 위치-추측 표보다 실제로 나은가?
같은 1.jpg 950px 토큰을 두 파서에 먹여 tableRows를 뽑고, GT와 컬럼별로 대조한다.

  python eval/probe_header_mapping.py
"""
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

COLS = ["itemName", "spec", "quantity", "unitPrice", "amount"]


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
    """행 index 정렬로 컬럼별 일치 수 (정규화 후)."""
    per = {k: 0 for k in COLS}
    n = min(len(rows), len(gt))
    for i in range(n):
        r, g = rows[i], gt[i]
        for k in COLS:
            gv = _norm(g.get(k))
            if gv and _norm(r.get(k)) == gv:
                per[k] += 1
    return per, n


def main():
    from main import get_ocr_engine, _parse_ocr_lines
    from extractors.invoice_statement_free import extract_invoice_statement_free
    from extractors.invoice_statement import extract_invoice_statement_fields

    img = cv2.imread(IMG)
    ocr = get_ocr_engine()
    ocr_img = _free_like(img)
    ow, oh = ocr_img.shape[1], ocr_img.shape[0]
    lines = _parse_ocr_lines(ocr.ocr(ocr_img))
    print(f"1.jpg 950px 토큰 {len(lines)}개\n")

    # free (위치 추측)
    f = extract_invoice_statement_free(
        ocr_lines_raw=lines, full_text="\n".join(t for _, t, _ in lines),
        image_size=(ow, oh), doc_type="invoice_statement",
        context={"templateMode": False, "isUnstructuredTemplate": True})
    f_rows = (f.get("tableRows") if isinstance(f, dict) else None) or []

    # template (헤더 매핑, 힌트 없음) — 같은 토큰
    t = extract_invoice_statement_fields(list(lines), debug={})
    t_rows = (t.get("tableRows") if isinstance(t, dict) else None) or []

    # template + expected_columns 힌트 — 같은 토큰
    _ec = {"required": ["itemName", "quantity", "unitPrice", "amount"],
           "optional": ["spec", "lotNo", "expiryDate", "productCode", "manufacturingNo"]}
    th = extract_invoice_statement_fields(list(lines), debug={}, table_expected_columns=_ec)
    th_rows = (th.get("tableRows") if isinstance(th, dict) else None) or []

    gt = _gt_rows()
    print(f"행수: GT {len(gt)} · free {len(f_rows)} · tmpl {len(t_rows)} · tmpl+힌트 {len(th_rows)}\n")

    fs, _ = _score(f_rows, gt)
    ts, _ = _score(t_rows, gt)
    hs, _ = _score(th_rows, gt)
    print(f"{'컬럼':12} {'free(위치)':>11} {'tmpl(헤더)':>11} {'tmpl+힌트':>11}")
    print("-" * 48)
    for k in COLS:
        print(f"{k:12} {fs[k]:>7}/{len(gt):<3} {ts[k]:>7}/{len(gt):<3} {hs[k]:>7}/{len(gt):<3}")
    ftot, ttot, htot = sum(fs.values()), sum(ts.values()), sum(hs.values())
    print("-" * 48)
    print(f"{'합계':12} {ftot:>9}   {ttot:>9}   {htot:>9}")
    print()
    # 샘플 3행 나란히 (눈으로 컬럼배치 확인)
    print("샘플 비교 (행0~2, 수량|단가|금액):")
    for i in range(min(3, len(gt))):
        g = gt[i]
        fr = f_rows[i] if i < len(f_rows) else {}
        tr = t_rows[i] if i < len(t_rows) else {}
        print(f"  GT  : {g['itemName'][:14]:14} q={g['quantity']:>8} u={g['unitPrice']:>8} a={g['amount']:>10}")
        print(f"  free: {str(fr.get('itemName',''))[:14]:14} q={str(fr.get('quantity','')):>8} u={str(fr.get('unitPrice','')):>8} a={str(fr.get('amount','')):>10}")
        print(f"  tmpl: {str(tr.get('itemName',''))[:14]:14} q={str(tr.get('quantity','')):>8} u={str(tr.get('unitPrice','')):>8} a={str(tr.get('amount','')):>10}")
        print()
    print("=" * 48)
    best = max(ttot, htot)
    if best > ftot:
        which = "tmpl+힌트" if htot >= ttot else "tmpl"
        print(f"★ 결론: {which}이 free보다 +{best-ftot} 우세 → 이식 가치 있음.")
    else:
        print(f"★ 결론: free가 최고({ftot} vs tmpl {ttot} vs tmpl+힌트 {htot}) → 파서 이식 불필요.")
        print("  인식률 차이는 파서가 아니라 OCR 입력(해상도/per-form 좌표)에서 옴.")


if __name__ == "__main__":
    main()
