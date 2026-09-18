"""llm_parser_cases — 파서 실물: Base 와 VLM 이 같은 셀을 두고 갈린 곳을 FT 보고서 모양으로 보인다.

모양은 finetune/demo/DEMO_SUMMARY·DEMO_REPORT 와 같다(사용자 지정 2026-09-15):
    탭 = 행(품목표 7칸) 살린 것·망친 것 / 헤더(문서당 10필드) 살린 것·망친 것 / 전체 현황
    하위 탭 = 유형(틀린 쪽이 어떻게 틀렸나: 행을 통째로 못 잡음 / 칸을 비움 / 값을 틀리게 읽음 × 칸), 쪽마다 많은 5개
    묶음 = 행이면 품목(GT 품명), 헤더면 공급자(GT 상호). **기준셋 안의 그 묶음 전부**를 모아
           "N행(문서) 중 Base a → Qwen b 정답 (살림 r · 잃음 l)" - FT 의 "세파록스캡슐 26크롭 중 몇 개 살렸나" 와 같은 단위.
           묶음을 펼치면 행·문서마다 크롭.

크롭 = 그 칸 GT 값이 적힌 Base OCR 상자(071 스냅샷 · 좌표계 = 072 처리본과 동일). 모델은 좌표를 주지 않으므로
같은 문서의 Base 좌표를 쓴다. 긴 값은 문서 전체에서 유일하게 잡힐 때만, 짧은 값(수량 10 등)은 먼저 행 위치를
금액·제조번호·품명으로 잡은 뒤 그 행 안에서만 찾는다.

    python eval/llm_parser_cases.py --base 072_20260802_182127_post --model vlm_qwen_500r_post
"""
from __future__ import annotations

import argparse
import base64
import collections
import difflib
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "LLM", "LLM_CASES_PARSER.html")
SNAP = os.path.join(HERE, "runs", "071_20260731_143206", "snapshots")      # 071 == 072 문서별 동일(검증됨)
PROC = os.path.join(HERE, "runs", "072_20260802_182127", "processed")
ALIGN = os.path.join(HERE, "runs", "vlm_qwen_500", "compare")               # 계획서와 같은 문서 기준
EXCL = {"itemCode", "itemNameMaster", "itemNameLearnA", "itemNameLearnB", "itemCodeLearnA", "itemCodeLearnB",
        "insuranceCode"}
SCORED = {"match", "mismatch", "ext_missing"}
ORDER = ["itemName", "spec", "quantity", "unitPrice", "amount", "manufacturingNo", "expiryDate"]
KO = {"itemName": "품명", "spec": "규격", "quantity": "수량", "unitPrice": "단가", "amount": "금액",
      "manufacturingNo": "제조번호", "expiryDate": "유효기간"}
HEADER = ["issueDate", "supplierCompany", "supplierBizNumber", "supplierAddress",
          "buyerCompany", "buyerBizNumber", "buyerAddress", "supplyAmount", "taxAmount", "totalAmount"]
KOH = {"issueDate": "작성일자", "supplierCompany": "공급자 상호", "supplierBizNumber": "공급자 사업자번호",
       "supplierAddress": "공급자 주소", "buyerCompany": "공급받는자 상호", "buyerBizNumber": "공급받는자 사업자번호",
       "buyerAddress": "공급받는자 주소", "supplyAmount": "공급가액", "taxAmount": "세액", "totalAmount": "합계"}
ANCHORS = ["amount", "manufacturingNo", "unitPrice", "itemName", "expiryDate"]   # 행 위치를 잡을 칸(구분되는 순)
ROWMISS = "행을 통째로 못 잡음"
PER_SIDE = 5
PER_TYPE_ITEMS = 10              # 유형마다 품목 몇 개
SHOW_ROWS = 12                   # 품목마다 펼쳐 보일 행 수(나머지는 숫자로만)
MISSING = "__missingGtRow"       # 행 dict 안에 넣어 두는 표시(칸 이름과 겹치지 않게)

norm = lambda v: re.sub(r"[\s,.\-/()\[\]]", "", str(v or "")).upper()
esc = lambda v: (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if v not in (None, "") else "")
fmt = lambda n: "{:,}".format(n)

# finetune/demo/DEMO_REPORT.html 과 같은 스타일
CSS = r"""
*{box-sizing:border-box}
body{font-family:'Segoe UI',Malgun Gothic,sans-serif;margin:0;padding:20px 28px;max-width:none;color:#1a2733}
h1{font-size:22px} h2{font-size:17px;margin-top:30px;border-bottom:2px solid #dde5ec;padding-bottom:6px}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;margin:10px 0;min-width:640px}
th,td{border:1px solid #d7dee5;padding:6px 10px;font-size:13.5px;text-align:left;vertical-align:middle}
th{background:#f2f6fa}
@media (max-width:820px){body{padding:14px 12px} th,td{padding:5px 7px;font-size:12.5px}}
.box{background:#f6f9fc;border:1px solid #d7dee5;border-radius:8px;padding:14px 18px;margin:14px 0;font-size:14px;line-height:1.65}
.ok{color:#0a7a3d;font-weight:700} .bad{color:#c0392b;font-weight:700}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12.5px;font-weight:700}
.badge.pass{background:#e3f6ea;color:#0a7a3d} .badge.fail{background:#fdeceb;color:#c0392b}
.muted{color:#5b6b7b;font-size:12.5px} .big{font-size:16px}
mark{background:#ffd9d9;color:inherit;font-weight:700;padding:0 1px;border-radius:2px}
a{color:#0b63ce;text-decoration:none}
h3{font-size:15px;margin-top:22px} .nw{white-space:nowrap}
details{margin:6px 0}
details>summary{cursor:pointer;list-style:none}
details>summary::-webkit-details-marker{display:none}
details>summary.big{padding:7px 10px;background:#f7fafd;border:1px solid #e3eaf1;border-radius:7px;user-select:none}
details>summary.big:hover{background:#eef4fa}
details>summary.big::before{content:"\25B8 ";color:#5b6b7b;font-weight:700}
details[open]>summary.big::before{content:"\25BE "}
.tabs{display:flex;flex-wrap:wrap;gap:4px;border-bottom:2px solid #dde5ec;margin:18px 0 4px}
.tabs button{border:1px solid #dde5ec;border-bottom:none;background:#f2f6fa;color:#37485a;
 padding:8px 20px;font-size:14px;font-weight:600;cursor:pointer;border-radius:8px 8px 0 0}
.tabs button.on{background:#fff;color:#0b63ce;border-color:#b9d3ef;box-shadow:0 2px 0 #fff}
.tabs.sub{margin:14px 0 2px;border-bottom-width:1px}
.tabs.sub button{padding:6px 14px;font-size:13px}
.pane{display:none} .pane.on{display:block}
"""


def load_rows(path: str) -> dict:
    """GT 행 → 칸들. 키 = 그 행의 GT 값 묶음 + 같은 묶음 안의 순번.

    ★ compare/ 의 rowIndex 는 GT 행 번호가 아니라 **짝지어진 추출 행의 번호**이고(compare_table:107),
    짝 없는 GT 행은 맨 뒤에 붙는다(:174). 그래서 rowIndex 로도 목록 위치로도 두 run 의 같은 GT 행을
    짝지을 수 없다(2026-09-15 실측: rowIndex 키는 37%, 위치 키는 28% 가 다른 GT 행). GT 값 묶음은
    두 run 이 같은 GT 에서 나왔으므로 100% 짝지어진다(묶음이 완전히 같은 행은 순번으로).
    """
    out, seen = {}, collections.Counter()
    for r in json.load(io.open(path, encoding="utf-8"))["table"]["rows"]:
        g = tuple(sorted((c, str(v.get("gt"))) for c, v in (r.get("cells") or {}).items()))
        seen[g] += 1
        cs = {c: v for c, v in (r.get("cells") or {}).items() if c not in EXCL and v.get("status") in SCORED}
        cs[MISSING] = bool(r.get("missingGtRow"))
        out[(g, seen[g])] = cs
    return out


def kind_of(cell: dict, rowmiss: bool) -> str:
    if rowmiss:
        return ROWMISS
    return "칸을 비움" if cell["status"] == "ext_missing" else "값을 틀리게 읽음"


_BOX = {}


def _boxes(src: str) -> list:
    if src not in _BOX:
        _BOX[src] = _boxes_load(src)
    return _BOX[src]


def _boxes_load(src: str) -> list:
    try:
        lines = json.load(io.open(os.path.join(SNAP, src + ".json"), encoding="utf-8"))["ocr_lines_raw"]
    except Exception:                                            # noqa: BLE001
        return []
    out = []
    for ln in lines:
        try:
            xs = [p[0] for p in ln[0]]; ys = [p[1] for p in ln[0]]
            out.append((min(xs), min(ys), max(xs), max(ys), norm(ln[1])))
        except Exception:                                        # noqa: BLE001
            continue
    return out


def _row_band(boxes: list, row: dict):
    """행 위치(y1, y2). 구분되는 칸의 GT 값이 문서에서 유일하게 잡힐 때만."""
    for c in ANCHORS:
        g = norm((row.get(c) or {}).get("gt"))
        if c == "itemName":
            g = g[:6]
        if len(g) < 4:
            continue
        hits = [b for b in boxes if g in b[4]]
        if len(hits) == 1:
            h = hits[0]; cy, hh = (h[1] + h[3]) / 2, max(8.0, h[3] - h[1])
            return cy - hh * 0.8, cy + hh * 0.8
    return None


def _fuzzy(cands: list, g: str):
    """GT 와 가장 비슷한 상자 하나 - 0.6 이상이고 2등과 0.15 이상 벌어질 때만.

    Base 가 틀리게 읽은 칸은 OCR 글자도 GT 와 달라(2mg/30T → '2ng/3T') 정확 일치로는 못 찾는다.
    """
    sc = sorted(((difflib.SequenceMatcher(None, g, b[4]).ratio(), b) for b in cands if b[4]), key=lambda t: -t[0])
    if sc and sc[0][0] >= 0.6 and (len(sc) == 1 or sc[0][0] - sc[1][0] >= 0.15):
        return sc[0][1]
    return None


def cell_box(src: str, row: dict, col: str, occ: int = 1):
    """그 칸 GT 값이 적힌 OCR 상자 (x1, y1, x2, y2) 또는 None.

    순서: 행 안 정확 → 행 안 유사 → 문서 전체 정확(유일) → 문서 전체 유사(유일, 4자 이상)
          → 같은 글자가 여러 번이면 GT 행 순번(occ)번째(위에서부터).
    """
    boxes = _boxes(src)
    g = norm((row.get(col) or {}).get("gt"))
    if not g or not boxes:
        return None
    exact = lambda cs: [b for b in cs if b[4] == g or (len(g) >= 4 and g in b[4])]
    band = _row_band(boxes, row)
    if band:
        inb = [b for b in boxes if b[1] < band[1] and b[3] > band[0]]
        hits = exact(inb)
        if len(hits) == 1:
            return hits[0][:4]
        f = _fuzzy(inb, g) if not hits else None
        if f:
            return f[:4]
    if len(g) >= 4:
        hits = exact(boxes)
        if len(hits) == 1:
            return hits[0][:4]
        if not hits:
            f = _fuzzy(boxes, g)
            return f[:4] if f else None
        if len({b[4] for b in hits}) == 1 and occ <= len(hits):   # 같은 품목이 한 문서에 여러 행
            return sorted(hits, key=lambda b: b[1])[occ - 1][:4]
    return None


def crop_b64(src: str, box) -> str | None:
    try:
        from PIL import Image
        with Image.open(os.path.join(PROC, src + ".jpg")) as im:
            im = im.convert("RGB")
            x1, y1, x2, y2 = box
            c = im.crop((max(0, int(x1) - 4), max(0, int(y1) - 4), min(im.width, int(x2) + 4), min(im.height, int(y2) + 4)))
            c = c.resize((c.width * 2, c.height * 2))            # 950px 처리본이라 두 배로 키워 읽기 쉽게
            buf = io.BytesIO(); c.save(buf, format="JPEG", quality=88)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:                                            # noqa: BLE001
        return None


def josa(word: str, with_final: str, without: str) -> str:
    last = word[-1] if word else ""
    return with_final if ("가" <= last <= "힣" and (ord(last) - 0xAC00) % 28) else without


def load_fields(path: str) -> dict:
    """헤더 필드(문서당 하나) - 채점 대상만."""
    pf = ((json.load(io.open(path, encoding="utf-8")).get("fields") or {}).get("perField") or {})
    return {c: v for c, v in pf.items() if c in HEADER and v.get("status") in SCORED}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="Base 파생 run(runs/ 아래)")
    ap.add_argument("--model", required=True, help="모델 파생 run(runs/ 아래)")
    ap.add_argument("--label", default="Qwen3-VL 4B · 리사이즈 제거")
    a = ap.parse_args()
    B = os.path.join(HERE, "runs", a.base, "compare"); M = os.path.join(HERE, "runs", a.model, "compare")
    docs = sorted({f[:-5] for f in os.listdir(M)} & {f[:-5] for f in os.listdir(ALIGN)})

    ALL = []          # 행: (문서, 행키, Base 칸들, 모델 칸들, Base 행 못 잡음, 모델 행 못 잡음)
    HALL = []         # 헤더: (문서, Base 필드들, 모델 필드들)
    col = collections.defaultdict(lambda: [0, 0, 0, 0])      # 칸/필드 → Base틀림 · 모델살림 · Base맞음 · 모델잃음
    types = collections.Counter()
    for d in docs:
        pb, pm = os.path.join(B, d + ".json"), os.path.join(M, d + ".json")
        b, m = load_rows(pb), load_rows(pm)
        for rk in b.keys() & m.keys():
            bc, mc = b[rk], m[rk]
            # 행을 통째로 못 잡음 = 짝 없는 GT 행(missingGtRow) 또는 짝은 지었지만 칸이 전부 빈 행
            b_miss = bc.get(MISSING) or all(v["status"] == "ext_missing" for c, v in bc.items() if c != MISSING)
            m_miss = mc.get(MISSING) or all(v["status"] == "ext_missing" for c, v in mc.items() if c != MISSING)
            ALL.append((d, rk, bc, mc, b_miss, m_miss))
            for c in ORDER:
                if c not in bc or c not in mc:
                    continue
                bo, mo = bc[c]["status"] == "match", mc[c]["status"] == "match"
                a4 = col[c]
                if not bo:
                    a4[0] += 1; a4[1] += mo
                else:
                    a4[2] += 1; a4[3] += (not mo)
                if not bo and not mo:                         # 둘 다 틀림
                    types[("행", "둘다", kind_of(bc[c], b_miss), "" if b_miss else c)] += 1
                    continue
                if bo == mo:
                    continue
                k = ("행", "살림", kind_of(bc[c], b_miss), "" if b_miss else c) if mo else \
                    ("행", "망침", kind_of(mc[c], m_miss), "" if m_miss else c)
                types[k] += 1
        bf, mf = load_fields(pb), load_fields(pm)
        HALL.append((d, bf, mf))
        for c in HEADER:
            if c not in bf or c not in mf:
                continue
            bo, mo = bf[c]["status"] == "match", mf[c]["status"] == "match"
            a4 = col[c]
            if not bo:
                a4[0] += 1; a4[1] += mo
            else:
                a4[2] += 1; a4[3] += (not mo)
            if bo != mo:
                types[("헤더", "살림", kind_of(bf[c], False), c) if mo else
                      ("헤더", "망침", kind_of(mf[c], False), c)] += 1

    TR = [sum(col[c][i] for c in ORDER) for i in range(4)]       # 행 칸 합계
    TH = [sum(col[c][i] for c in HEADER) for i in range(4)]      # 헤더 필드 합계

    def top(dom, side):
        return sorted([k for k in types if k[0] == dom and k[1] == side], key=lambda k: -types[k])[:PER_SIDE]

    def name_of(c):
        return KO.get(c) or KOH.get(c) or c

    def tlabel(k, short=False):
        dom, side, how, c = k
        nm = name_of(c)
        what = how if how == ROWMISS else "%s%s %s" % (nm, josa(nm, "을", "를"), "비움" if how == "칸을 비움" else "틀리게 읽음")
        who = {"살림": "Base가", "망침": "Qwen 이", "둘다": "둘 다"}[side]
        return what if short else "%s %s" % (who, what)

    # ── 판정·묶기: 행은 (품목, 행), 헤더는 (공급자, 문서) ──
    def cells_of(k, R):
        """(Base 쪽, 모델 쪽) 칸 묶음."""
        return (R[2], R[3]) if k[0] == "행" else (R[1], R[2])

    def judge(k, R):
        """(Base 맞음, 모델 맞음) 또는 None(이 문서/행에서 채점 대상이 아님)."""
        dom, side, how, c = k
        bc, mc = cells_of(k, R)
        if how == ROWMISS:
            return (not R[4], not R[5])
        if c not in bc or c not in mc:
            return None
        return (bc[c]["status"] == "match", mc[c]["status"] == "match")

    def is_event(k, R, j):
        """이 행/문서가 유형 k 에 해당하나(살린 쪽이면 Base 가 그 방식으로 틀리고 모델이 맞힘)."""
        dom, side, how, c = k
        bc, mc = cells_of(k, R)
        okb, okm = j
        miss_b, miss_m = (R[4], R[5]) if dom == "행" else (False, False)
        if side == "살림":
            return (not okb) and okm and (how == ROWMISS or (not miss_b and kind_of(bc[c], False) == how))
        if side == "둘다":
            return (not okb) and (not okm) and (how == ROWMISS or (not miss_b and kind_of(bc[c], False) == how))
        return okb and (not okm) and (how == ROWMISS or (not miss_m and kind_of(mc[c], False) == how))

    def group_key(k, R):
        """묶는 단위 - 행은 GT 품명, 헤더는 GT 공급자."""
        bc, mc = cells_of(k, R)
        g = "itemName" if k[0] == "행" else "supplierCompany"
        cell = bc.get(g) or mc.get(g)
        return (norm(cell.get("gt")), str(cell.get("gt")).strip()) if cell and cell.get("gt") else (None, None)

    def shot(k, R):
        dom, side, how, c = k
        cc = "itemName" if how == ROWMISS else c
        if dom == "행":
            return crop_of(R[0], {**R[3], **R[2]}, cc, R[1][1])
        return crop_of(R[0], {**R[2], **R[1]}, cc, 1)

    def crop_of(src, row, cc, occ):
        box = cell_box(src, row, cc, occ)
        return crop_b64(src, box) if box else None

    def mark_diff(gt, val):
        """GT 와 다른 글자만 <mark> 로 싼다. 한 글자 오독(향정→항정)은 안 그러면 안 보인다."""
        out = []
        for tag, _i1, _i2, j1, j2 in difflib.SequenceMatcher(None, gt, val, autojunk=False).get_opcodes():
            seg = val[j1:j2]
            if not seg:
                continue
            out.append(esc(seg) if tag == "equal" else "<mark>%s</mark>" % esc(seg))
        return "".join(out)

    def read_cell(k, cells, miss, gt=""):
        if k[2] == ROWMISS and miss:
            return "(행 없음)"
        c = cells.get("itemName" if k[2] == ROWMISS else k[3]) or {}
        v = c.get("ext")
        if not v:
            return "(빈칸)"
        if c.get("status") == "match" or not gt:
            return esc(v)                      # 맞힌 칸은 표기 차이(띄어쓰기 등)까지 칠하지 않는다
        return mark_diff(str(gt), str(v))

    def tone(ok, cells, rowmiss):
        # 행 통째로 탭: 판정은 "행을 잡았나"지만 보이는 글자는 품명이므로, 색은 품명이 맞았는지로
        if rowmiss and ok and (cells.get("itemName") or {}).get("status") != "match":
            return "bad"
        return "ok" if ok else "bad"

    def group(k):
        src = ALL if k[0] == "행" else HALL
        g = collections.defaultdict(lambda: {"rows": [], "ev": 0, "names": collections.Counter()})
        for R in src:
            j = judge(k, R)
            key, raw = group_key(k, R)
            if j is None or not key:
                continue
            ev = is_event(k, R, j)
            e = g[key]; e["rows"].append((R, j, ev)); e["ev"] += ev; e["names"][raw] += 1
        hit = [x for x in g.items() if x[1]["ev"]]
        # 여러 문서에 걸친 품목/거래처 먼저
        hit.sort(key=lambda x: (-x[1]["ev"], -len({R[0] for R, _, _ in x[1]["rows"]}), -len(x[1]["rows"]), x[0]))
        return hit, len(hit)

    # ── 한 탭(행/헤더 × 살림/망침) 그리기 ──
    def board(g, dom, side):
        ks = top(dom, side)
        unit = "행" if dom == "행" else "문서"
        gname = "품목" if dom == "행" else "공급자"
        buttons, panes = [], []
        for i, k in enumerate(ks):
            n = types[k]
            rowmiss = k[2] == ROWMISS
            colname = "행" if rowmiss else name_of(k[3])
            what_ok = "행 잡음" if rowmiss else "정답"
            buttons.append("<button id='t%d_%d' class='%s' onclick='sub(%d,%d,%d)'>%s <span class=muted>%s</span></button>" % (
                g, i, "on" if i == 0 else "", g, i, len(ks), esc(tlabel(k, short=True)), fmt(n)))
            items, _ = group(k)
            # 크롭 없는 행은 보여 줄 게 없다 - 보일 행 전부 크롭을 찾은 것만 싣는다(숫자는 전체 기준 그대로)
            shots, picked = {}, []
            for key, e in items:
                order = sorted(e["rows"], key=lambda t: (0 if t[2] else 1 if t[1][0] != t[1][1] else 2 if t[1][0] else 3, t[0][0]))
                imgs = [shot(k, R) for R, j, ev in order[:SHOW_ROWS]]
                if all(imgs):
                    picked.append((key, e)); shots[key] = (order, imgs)
                if len(picked) >= PER_TYPE_ITEMS:
                    break
            items = picked
            srows, details = [], []
            for rank, (key, e) in enumerate(items, 1):
                rows = e["rows"]; nm = e["names"].most_common(1)[0][0]
                N = len(rows); nd = len({R[0] for R, j, ev in rows})
                okb = sum(j[0] for R, j, ev in rows); okm = sum(j[1] for R, j, ev in rows)
                rv = sum((not j[0]) and j[1] for R, j, ev in rows); ls = sum(j[0] and (not j[1]) for R, j, ev in rows)
                mis = collections.Counter()
                for R, j, ev in rows:
                    if ev and not rowmiss:
                        v = (cells_of(k, R)[0 if side == "살림" else 1].get(k[3]) or {})
                        if v.get("status") == "mismatch":
                            mis[str(v.get("ext"))] += 1
                mis_s = " · ".join("“%s” %d" % (esc(v), c) for v, c in mis.most_common(2))
                order, imgs = shots[key]
                trs = []
                thumbs = [img for (R, j, ev), img in zip(order[:SHOW_ROWS], imgs) if ev][:3]
                for (R, j, ev), img in zip(order[:SHOW_ROWS], imgs):
                    bc, mc = cells_of(k, R)
                    cc = "itemName" if rowmiss else k[3]
                    gt_raw = (bc.get(cc) or mc.get(cc) or {}).get("gt") or ""
                    gt = esc(gt_raw)
                    miss_b, miss_m = (R[4], R[5]) if dom == "행" else (False, False)
                    if j[1] and not j[0]:
                        vd = "<span class='ok'>%s</span>" % ("Qwen 행 잡음" if rowmiss else "Qwen 살림")
                    elif j[0] and not j[1]:
                        vd = "<span class='bad'>%s</span>" % ("Qwen 행 놓침" if rowmiss else "Qwen 잃음")
                    else:
                        vd = "<span class='muted'>%s</span>" % ("둘 다 맞음" if j[0] else "둘 다 틀림")
                    trs.append("<tr><td><img src='data:image/jpeg;base64,%s' style='max-height:34px'></td>"
                               "<td><b>%s</b><div class='muted'>%s</div></td><td class='%s'>%s</td>"
                               "<td class='%s'>%s</td><td>%s</td></tr>" % (
                                   img, gt, esc(R[0][:34]), tone(j[0], bc, rowmiss), read_cell(k, bc, miss_b, gt_raw),
                                   tone(j[1], mc, rowmiss), read_cell(k, mc, miss_m, gt_raw), vd))
                rest = N - min(N, SHOW_ROWS)
                more = "<p class='muted'>외 %d%s 생략 - 위 표는 Qwen 이 바꾼 것부터 보인다(숫자는 전체 %d%s 기준)</p>" % (
                    rest, unit, N, unit) if rest else ""
                thumb_html = "".join("<img src='data:image/jpeg;base64,%s' style='max-height:28px;margin:1px 4px 1px 0'>" % t for t in thumbs)
                srows.append("<tr><td>%d</td><td><b>%s</b></td><td>%s</td><td class='nw'>%d%s <span class='muted'>(%d개 문서)</span></td>"
                             "<td class='nw'>%d / %d</td><td class='nw'>%d / %d</td>"
                             "<td class='nw'><span class='ok'>%d</span> · <span class='bad'>%d</span></td><td>%s</td></tr>" % (
                                 rank, esc(nm), thumb_html, N, unit, nd, okb, N, okm, N, rv, ls, mis_s))
                details.append(
                    "<details><summary class='big'><b>[%d] %s</b>%s - %d%s 중 Base <b class='%s'>%d</b> → Qwen <b class='%s'>%d</b> %s "
                    "<span class='muted'>(Qwen 살림 %d · Qwen 잃음 %d)</span></summary>"
                    "<div class='tw'><table><tr><th style='width:260px'>크롭</th><th>정답</th><th>Base 읽음</th><th>Qwen 읽음</th>"
                    "<th style='width:90px'>판정</th></tr>%s</table></div>%s</details>" % (
                        rank, esc(nm), "" if rowmiss else " <span class='muted'>· %s 칸</span>" % colname, N, unit,
                        "ok" if okb >= okm else "bad", okb, "ok" if okm >= okb else "bad", okm, what_ok, rv, ls, "".join(trs), more))
            panes.append(
                "<div id='p%d_%d' class='%s'><div class='tw'><table><tr><th>#</th><th>%s</th><th>크롭 실물</th><th>%s</th>"
                "<th>Base %s</th><th>Qwen %s</th><th>Qwen 살림 · 잃음</th><th>대표 오독 (%s)</th></tr>%s</table></div>"
                "<h3>%s별 전체 %s <span class='muted'>(눌러서 펼침)</span></h3>%s</div>" % (
                    g, i, "pane on" if i == 0 else "pane", gname, unit, what_ok, what_ok,
                    "Base" if side == "살림" else "Qwen", "".join(srows), gname, unit, "".join(details)))
        return "<div class='tabs sub'>%s</div>%s" % ("".join(buttons), "".join(panes))

    # 헤더 탭은 뺐다(2026-09-17) - 이 페이지는 품목표만 다룬다. 헤더 순증은 +88 뿐이라 계획서 숫자로 충분하다.
    boards = [board(0, "행", "살림"), board(1, "행", "망침"), board(2, "행", "둘다")]

    def stat_rows(cols):
        return "".join(
            "<tr><td><b>%s</b></td><td>%s 중 <span class='ok'>%s</span> <span class='muted'>(%.1f%%)</span></td>"
            "<td>%s 중 <span class='bad'>%s</span> <span class='muted'>(%.1f%%)</span></td><td class='%s'>%+d</td></tr>" % (
                name_of(c), fmt(col[c][0]), fmt(col[c][1]), 100 * col[c][1] / max(1, col[c][0]),
                fmt(col[c][2]), fmt(col[c][3]), 100 * col[c][3] / max(1, col[c][2]),
                "ok" if col[c][1] >= col[c][3] else "bad", col[c][1] - col[c][3])
            for c in cols)

    html = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>파서 실물 · LLM 비교</title><style>{CSS}</style>
<script>
function sel(i){{for(var k=0;k<4;k++){{
 document.getElementById('t'+k).className=(k==i?'on':'');
 document.getElementById('p'+k).className=(k==i?'pane on':'pane');}}}}
function sub(g,i,n){{for(var k=0;k<n;k++){{
 document.getElementById('t'+g+'_'+k).className=(k==i?'on':'');
 document.getElementById('p'+g+'_'+k).className=(k==i?'pane on':'pane');}}}}
</script></head><body>
<h1>파서 비교 <span class="muted">- 품목표 7칸 · {esc(a.label)} vs Base · {len(docs)}장</span></h1>
<p class="muted"><a href="LLM_REVIEW_PLAN.html">← LLM 비교</a></p>

<div class="tabs">
<button id="t0" class="on" onclick="sel(0)">Qwen 이 살린 것 <span class=muted>{fmt(TR[1])}</span></button>
<button id="t1" class="" onclick="sel(1)">Qwen 이 망친 것 <span class=muted>{fmt(TR[3])}</span></button>
<button id="t2" class="" onclick="sel(2)">둘 다 틀린 것 <span class=muted>{fmt(TR[0] - TR[1])}</span></button>
<button id="t3" class="" onclick="sel(3)">전체 현황</button>
</div>
<div id="p0" class="pane on">{boards[0]}</div>
<div id="p1" class="pane">{boards[1]}</div>
<div id="p2" class="pane">{boards[2]}</div>
<div id="p3" class="pane">
<div class="tw"><table><tr><th>구분</th><th>칸</th><th>비중</th></tr>
<tr><td>둘 다 맞음</td><td>{fmt(TR[2] - TR[3])}</td><td class="muted">{100*(TR[2]-TR[3])/(TR[0]+TR[2]):.1f}%</td></tr>
<tr><td><b>Qwen 이 살린 것</b></td><td class="ok"><b>{fmt(TR[1])}</b></td><td class="muted">{100*TR[1]/(TR[0]+TR[2]):.1f}%</td></tr>
<tr class="hi"><td><b>둘 다 틀림</b> <span class="muted">Qwen 으로 바꿔도 안 풀린 몫</span></td><td><b>{fmt(TR[0] - TR[1])}</b></td><td class="muted">{100*(TR[0]-TR[1])/(TR[0]+TR[2]):.1f}%</td></tr>
<tr><td><b>Qwen 이 잃은 것</b></td><td class="bad"><b>{fmt(TR[3])}</b></td><td class="muted">{100*TR[3]/(TR[0]+TR[2]):.1f}%</td></tr>
<tr><td>합계</td><td>{fmt(TR[0] + TR[2])}</td><td class="muted">100%</td></tr></table></div>
<h3>칸별</h3>
<div class="tw"><table><tr><th>칸</th><th>Base 가 틀림 → Qwen 이 살림</th><th>Base 가 맞음 → Qwen 이 잃음</th><th>순증</th></tr>{stat_rows(ORDER)}</table></div>
</div>
<p class="muted">묶음 = GT 품명(띄어쓰기·기호 무시). 크롭은 Base 처리본(950px)에서 그 값이 적힌 글자 상자를 자른 것 -
Qwen 은 원본 해상도로 봤으므로 실제로 본 화질은 이보다 높다.</p>
</body></html>"""
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("→ %s (%.0fKB) · 문서 %d" % (os.path.basename(OUT), os.path.getsize(OUT) / 1024, len(docs)))
    for nm, T in (("행 7칸", TR), ("헤더 10필드", TH)):
        print("%s: Base 틀림 %s 중 살림 %s (%.1f%%) · Base 맞음 %s 중 잃음 %s (%.1f%%) · 순증 %+d" % (
            nm, fmt(T[0]), fmt(T[1]), 100 * T[1] / T[0], fmt(T[2]), fmt(T[3]), 100 * T[3] / T[2], T[1] - T[3]))
    for dom in ("행", "헤더"):
        for side in ("살림", "망침"):
            for k in top(dom, side):
                items, n_items = group(k)
                print("  %s %s %-22s %5s · 묶음 %4d개 · 1위 %s" % (dom, side, tlabel(k), fmt(types[k]), n_items,
                      "%s %d개 B%d→M%d" % (items[0][1]["names"].most_common(1)[0][0][:16], len(items[0][1]["rows"]),
                                           sum(j[0] for _, j, _ in items[0][1]["rows"]),
                                           sum(j[1] for _, j, _ in items[0][1]["rows"])) if items else "-"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
