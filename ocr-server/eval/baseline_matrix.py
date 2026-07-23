"""baseline_matrix — war GT 필드 × 단계(구글/룰/마스터/파인튜닝) 정확도.

baseline(구글) = 구글이 읽은 값 vs GT 일치율. 값 없으면 0%. **6000 샘플 기준(2606⊂6000).**
라벨은 report._FIELD_KO 그대로. 스타일은 trend._CSS. 출력: runs/BASELINE_MATRIX.html
usage: python eval/baseline_matrix.py
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict

from report import _FIELD_KO
from trend import _CSS

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "invoice_war")
GT_PATH = os.path.join(DATA, "ground_truth_2606.json")
MASTER_PATH = os.path.join(DATA, "master_dict.json")
SAMPLE_PATH = os.path.join(DATA, "sample_6000.txt")
OUT = os.path.join(HERE, "runs", "BASELINE_MATRIX.html")
SAMPLE_LABEL = "지점 분산, 2606⊂6000"        # HTML 캡션(프리셋별 갱신)
PADDLE_FILTER = None                          # Paddle 채점 제한용 safe-id 집합(9000 프리셋)

# ocr.xml selectMasterItemLearnData: learn_count >= #{learn_count} 게이트.
# war 실제값=3 (2606 item_match_type 최솟값이 L_3, L_1/L_2 부재) → 충실 재현.
LEARN_COUNT_MIN = 3

ITEM = "ITEM"  # 품명만 GT로 라이브 계산

# (labelEn, group, baseline%)  group: head=헤더(위) / row=품목행(아래)
#   100.0 = 구글 값 = GT (같은 컬럼) / 67.5 = 공급자 사업자번호(샘플 raw vs 검증)
#   0.0   = 구글 값이 war에 없음(빈칸) → 일치 0
FIELDS = [
    ("supplierCompany",   "head", 0.0),
    ("supplierBizNumber", "head", 67.5),
    ("supplierAddress",   "head", 0.0),
    ("buyerCompany",      "head", 0.0),
    ("buyerBizNumber",    "head", 100.0),
    ("buyerAddress",      "head", 0.0),
    ("issueDate",         "head", 100.0),
    ("supplyAmount",      "head", 100.0),
    ("taxAmount",         "head", 100.0),
    ("totalAmount",       "head", 100.0),
    ("discountAmount",    "head", 100.0),
    ("taxType",           "head", 100.0),
    ("itemName",          "row",  ITEM),
    ("spec",              "row",  100.0),
    ("quantity",          "row",  100.0),
    ("unitPrice",         "row",  100.0),
    ("amount",            "row",  100.0),
    ("expiryDate",        "row",  100.0),
    ("manufacturingNo",   "row",  100.0),
    ("itemCode",          "row",  0.0),
    ("insuranceCode",     "row",  100.0), # 보험코드: OCR로 읽는 인쇄 컬럼(pass-through) → war 순환, Paddle이 읽음
]

_LOCAL_KO = {"insuranceCode": "보험코드"}   # report._FIELD_KO에 없는 라벨 보강

# Google의 순환 제외 판정을 Paddle의 정확히 같은 GT 행에 적용하기 위한 안정 서명.
# replay GT는 rowIndex가 없는 thin 데이터라 compare_table이 내용 정렬을 사용한다.
# 따라서 화면상의 행번호가 아니라 GT 값 전체로 연결한다.
_ROW_SIG_FIELDS = (
    "itemName", "itemNameMaster", "spec", "quantity",
    "unitPrice", "amount", "itemCode",
)


def _row_signature(row):
    return tuple(str((row or {}).get(k) or "") for k in _ROW_SIG_FIELDS)


def _cell_gt_signature(cells):
    return tuple(str(((cells or {}).get(k) or {}).get("gt") or "")
                 for k in _ROW_SIG_FIELDS)


def _safe_sample_id(key):
    return str(key).replace("\\", "/").replace("/", "__")


def _clean_nm(s) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", "", re.sub(r"\(.*?\)", "", str(s))).lower()


def load_sample_keys():
    if not os.path.isfile(SAMPLE_PATH):
        return None
    return {ln.strip() for ln in open(SAMPLE_PATH, encoding="utf-8") if ln.strip()}


def compute_item_baseline(keys):
    d = json.load(open(GT_PATH, encoding="utf-8"))
    docs = d.get("documents", {})
    if keys is not None:
        docs = {k: v for k, v in docs.items() if k in keys}
    ok = tot = 0
    for doc in docs.values():
        for r in doc.get("normalizedResult", {}).get("tableRows", []):
            gold = r.get("itemNameMaster")
            if not gold:
                continue
            tot += 1
            if _clean_nm(r.get("itemName")) == _clean_nm(gold):
                ok += 1
    return len(docs), (100.0 * ok / tot if tot else 0.0), ok, tot


def compute_google_rule(keys):
    """ocr.xml `selectMasterItemLearnData` 룰 레이어 적용 → 1차 샘플 채점.
    learndata를 원본대로(similarity+가격 tiebreak, learn_count>=3) 재현한 캐시의
    ld_cd/ld_nm 사용 (master_match_google.json). head 필드는 learndata 무관 → base 유지."""
    if not os.path.isfile(MMATCH_PATH):
        return {}, {}
    mm = json.load(open(MMATCH_PATH, encoding="utf-8")) or {}
    d = json.load(open(GT_PATH, encoding="utf-8"))
    docs = d.get("documents", {})
    if keys is not None:
        docs = {k: v for k, v in docs.items() if k in keys}

    nm_ok = nm_tot = cd_ok = cd_tot = fired = 0
    for doc in docs.values():
        for r in doc.get("normalizedResult", {}).get("tableRows", []):
            raw = r.get("itemName")
            if not raw:
                continue
            mc = mm.get(_price_key(raw, r.get("unitPrice"))) or {}
            cd = mc.get("ld_cd")          # learndata 단독 결과(충실 재현)
            if cd:
                fired += 1
            gold_master = r.get("itemNameMaster")
            if gold_master:
                nm_tot += 1
                resolved = mc.get("ld_nm") or raw
                if _clean_nm(resolved) == _clean_nm(gold_master):
                    nm_ok += 1
            gold_code = r.get("itemCode")
            if gold_code:
                cd_tot += 1
                if cd and str(cd) == str(gold_code):
                    cd_ok += 1
    out = {}
    if nm_tot:
        out["itemName"] = 100.0 * nm_ok / nm_tot
    if cd_tot:
        out["itemCode"] = 100.0 * cd_ok / cd_tot
    det = {"fired": fired, "nm_ok": nm_ok, "nm_tot": nm_tot,
           "cd_ok": cd_ok, "cd_tot": cd_tot, "learn_min": LEARN_COUNT_MIN}
    return out, det


MMATCH_PATH = os.path.join(DATA, "master_match_google.json")
CUST_PATH = os.path.join(DATA, "cust_match_google.json")   # ocr.xml 거래처매칭 재현(지점+사업자번호)


def _price_key(raw, price):
    p = re.sub(r"[^0-9]", "", str(price or ""))
    return f"{raw}\x01{p}"


def compute_google_master(keys):
    """ocr.xml 마스터 캐스케이드(LIKE→trigram) 적용 → 1차 샘플 채점.
    단계 정의 = rule(learndata) 우선, 없으면 master 캐시(LIKE/trigram). = war 전체 캐스케이드.
    순환분리: item_match_type로 war가 같은 방식으로 맞춘 행(=GT가 그 출력) 제외한 '독립' 수치도 계산.
    반환: ({'itemName':pct,'itemCode':pct}, 상세)."""
    if not (os.path.isfile(MMATCH_PATH) and os.path.isfile(MASTER_PATH)):
        return {}, {}
    mm = json.load(open(MMATCH_PATH, encoding="utf-8")) or {}   # 캐스케이드 최종 cd/nm/method
    md = json.load(open(MASTER_PATH, encoding="utf-8"))
    brch = md.get("brch", {})  # brch_cd -> {nm,addr}
    custm = json.load(open(CUST_PATH, encoding="utf-8")) if os.path.isfile(CUST_PATH) else {}
    d = json.load(open(GT_PATH, encoding="utf-8"))
    docs = d.get("documents", {})
    if keys is not None:
        docs = {k: v for k, v in docs.items() if k in keys}

    # 통계: 전체 + 독립(순환제외). 순환 = war match_type이 우리가 쓴 방식과 같은 행.
    nm_ok = nm_tot = cd_ok = cd_tot = 0
    icd_ok = icd_tot = 0        # itemCode 독립(순환제외)
    inm_ok = inm_tot = 0        # itemName 최종 독립(순환제외)
    inm_base_ok = 0             # 같은 독립행의 Google raw 품명 정답
    n_like = n_trg = n_rule = n_miss = 0
    # target별 독립 행 selector. 품명/itemCode는 GT 존재 행이 달라 분리한다.
    # Counter를 쓰므로 같은 문서 안에 완전히 같은 품목행이 반복돼도 분모가 보존된다.
    independent = {
        "itemName": defaultdict(Counter),
        "itemCode": defaultdict(Counter),
    }
    # 거래처(공급자)/지점(공급받는자) 매칭 카운터: labelEn -> [ok, tot]
    party = {k: [0, 0] for k in ("supplierCompany", "supplierAddress",
                                 "buyerCompany", "buyerAddress")}
    for img_key, doc in docs.items():
        nr = doc.get("normalizedResult", {})
        fld = {f.get("labelEn"): f.get("value") for f in nr.get("fields", [])}
        # 공급자: ocr.xml 거래처매칭 재현(지점+사업자번호) 캐시 → 상호/주소
        cinfo = custm.get(img_key) or {}
        # 공급받는자: brch_cd → 상호/주소
        bcd = str((doc.get("_source") or {}).get("brch_cd") or "")
        binfo = brch.get(bcd, {}) if bcd else {}
        for lab, resolved in (("supplierCompany", cinfo.get("nm")),
                              ("supplierAddress", cinfo.get("addr")),
                              ("buyerCompany", binfo.get("nm")),
                              ("buyerAddress", binfo.get("addr"))):
            gold = fld.get(lab)
            if not gold:
                continue
            party[lab][1] += 1
            if resolved and _clean_nm(resolved) == _clean_nm(gold):
                party[lab][0] += 1
        for r in nr.get("tableRows", []):
            raw = r.get("itemName")
            if not raw:
                continue
            mtype = r.get("item_match_type") or ""
            # 캐스케이드 최종(learndata→LIKE→trigram) 캐시에서 직접
            mc = mm.get(_price_key(raw, r.get("unitPrice"))) or {}
            cd = mc.get("cd")
            used = mc.get("method")   # 'L'(learndata) | 'NM_L' | 'SIMILAR' | None
            if used == "L":
                n_rule += 1
            elif used == "NM_L":
                n_like += 1
            elif used == "SIMILAR":
                n_trg += 1
            else:
                n_miss += 1
            # 순환 여부: war가 우리와 같은 부류로 맞췄으면 GT가 그 출력 → 순환
            circ = (used == "SIMILAR" and mtype.startswith("SIMI")) or \
                   (used == "NM_L" and mtype == "NM_L") or \
                   (used == "L" and mtype.startswith("L_"))
            gold_master = r.get("itemNameMaster")
            if gold_master:
                nm_tot += 1
                resolved = mc.get("nm") or raw
                nm_match = _clean_nm(resolved) == _clean_nm(gold_master)
                if nm_match:
                    nm_ok += 1
                if not circ:                 # 독립(순환제외) 집계
                    inm_tot += 1
                    independent["itemName"][_safe_sample_id(img_key)][
                        _row_signature(r)
                    ] += 1
                    if _clean_nm(raw) == _clean_nm(gold_master):
                        inm_base_ok += 1
                    if nm_match:
                        inm_ok += 1
            gold_code = r.get("itemCode")
            if gold_code:
                cd_tot += 1
                ok = bool(cd and str(cd) == str(gold_code))
                if ok:
                    cd_ok += 1
                if not circ:                 # 독립(순환제외) 집계
                    icd_tot += 1
                    independent["itemCode"][_safe_sample_id(img_key)][
                        _row_signature(r)
                    ] += 1
                    if ok:
                        icd_ok += 1
    out = {}
    if nm_tot:
        out["itemName"] = 100.0 * nm_ok / nm_tot
    if cd_tot:
        out["itemCode"] = 100.0 * cd_ok / cd_tot
    for lab, (ok, tot) in party.items():        # 거래처/지점 매칭 결과
        if tot:
            out[lab] = 100.0 * ok / tot
    det = {"nm_ok": nm_ok, "nm_tot": nm_tot, "cd_ok": cd_ok, "cd_tot": cd_tot,
           "icd_ok": icd_ok, "icd_tot": icd_tot,
           "icd_pct": (100.0 * icd_ok / icd_tot if icd_tot else None),
           "inm_ok": inm_ok, "inm_tot": inm_tot,
           "inm_pct": (100.0 * inm_ok / inm_tot if inm_tot else None),
           "inm_base_ok": inm_base_ok,
           "inm_base_pct": (100.0 * inm_base_ok / inm_tot if inm_tot else None),
           "n_rule": n_rule, "n_like": n_like, "n_trg": n_trg, "n_miss": n_miss,
           "party": {k: tuple(v) for k, v in party.items()},
           "cache_entries": len(mm),
           # 런타임 렌더링 전용. HTML에는 selector 원문을 쓰지 않는다.
           "independentSelectors": {
               target: dict(by_file) for target, by_file in independent.items()
           }}
    return out, det


def _ko(label):
    ko = _FIELD_KO.get(label) or _LOCAL_KO.get(label, label)
    return f'{ko} <span class="muted">({label})</span>'


def _val(b, item_pct):
    return item_pct if b == ITEM else b


STAGES = [
    ("base", "OCR 읽기"),
    ("master", "최종 매칭"),   # 합본: Google=learndata→LIKE→trigram, Paddle=전체 파이프라인
]

_TAB_CSS = """
.tabbar{display:flex;gap:6px;max-width:1600px;margin:16px auto 0;border-bottom:1px solid var(--line)}
.tab{padding:8px 18px;border:1px solid var(--line);border-bottom:none;border-radius:8px 8px 0 0;
cursor:pointer;background:#eef1f4;color:var(--muted);font-weight:600;font-size:13.5px}
.tab.active{background:var(--card);color:var(--fg)}
.panel{display:none}.panel.active{display:block}
table.matrix{table-layout:fixed}
.v-noc{display:none}
body.hidecirc .v-full{display:none}
body.hidecirc .v-noc{display:inline}
body.hidecirc tr.circ,body.hidecirc tr.partcirc{display:none}
.toggle{display:inline-flex;align-items:center;gap:6px;cursor:pointer;font-size:13px;color:var(--fg);
user-select:none;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 12px}
.cardgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;max-width:1600px;margin:16px auto 0}
.cardbox{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px}
.cardv{font-size:26px;font-weight:700}.cardl{color:var(--muted);font-size:12.5px}
"""


def _score_compare_dir(cdir):
    """한 compare 디렉토리의 필드·셀별 정확도 집계 → {labelEn: pct}.
    PADDLE_FILTER(safe-id 집합)가 있으면 그 샘플만 채점(9000: 대량 run에서 9,001만 추림)."""
    import glob
    fcnt = {}  # labelEn -> [match, scored]
    files = [f for f in glob.glob(os.path.join(cdir, "*.json"))
             if not f.endswith("compare_summary.json")]
    if PADDLE_FILTER is not None:
        files = [f for f in files
                 if os.path.basename(f)[:-5] in PADDLE_FILTER]  # <id>.json
    for f in files:
        try:
            c = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for lab, info in c.get("fields", {}).get("perField", {}).items():
            st = info.get("status")
            if st == "gt_empty":
                continue
            fcnt.setdefault(lab, [0, 0])
            fcnt[lab][1] += 1
            fcnt[lab][0] += 1 if st == "match" else 0
        for row in c.get("table", {}).get("rows", []):
            for ck, ci in row.get("cells", {}).items():
                st = ci.get("status")
                if st == "gt_empty":
                    continue
                fcnt.setdefault(ck, [0, 0])
                fcnt[ck][1] += 1
                fcnt[ck][0] += 1 if st == "match" else 0
    return {lab: (100.0 * m / s if s else None) for lab, (m, s) in fcnt.items()}, len(files)


def _score_compare_dir_subset(cdir, selectors):
    """Google 독립 selector와 정확히 같은 GT 행만 Paddle 채점.

    분모는 selector의 행 수로 먼저 고정한다. compare 파일/행/측정 셀이 없으면
    numerator에만 들어가지 않으므로 자동으로 누락 오답이 된다.
    """
    outputs = {
        "itemName": ("itemName", "itemNameMaster", "itemNameLearnA", "itemNameLearnB"),
        "itemCode": ("itemCode", "itemCodeLearnA", "itemCodeLearnB"),
    }
    counts = {}
    for target, by_file in (selectors or {}).items():
        if target not in outputs:
            continue
        total = sum(sum(counter.values()) for counter in by_file.values())
        for lab in outputs[target]:
            counts[lab] = [0, total]
        for safe_id, selected in by_file.items():
            path = os.path.join(cdir, safe_id + ".json")
            try:
                comp = json.load(open(path, encoding="utf-8"))
            except Exception:
                continue
            remaining = Counter(selected)
            for row in comp.get("table", {}).get("rows", []):
                cells = row.get("cells", {})
                sig = _cell_gt_signature(cells)
                if remaining[sig] <= 0:
                    continue
                remaining[sig] -= 1
                for lab in outputs[target]:
                    if (cells.get(lab) or {}).get("status") == "match":
                        counts[lab][0] += 1
    pct = {lab: (100.0 * ok / total if total else None)
           for lab, (ok, total) in counts.items()}
    detail = {lab: {"ok": ok, "total": total, "pct": pct.get(lab)}
              for lab, (ok, total) in counts.items()}
    return pct, detail


def load_paddle(independent_selectors=None):
    """최신 run에서 우리 파이프라인 정확도를 **단계별로** 집계.
      - Base   = thin/compare/              (AWS run, 파서룰 적용 전 기준선)
      - Rule   = thin/replay_compare_rule/  (파서룰 적용, ②마스터 매칭 제외 —
                 replay_compare.py --no-master-match --out-subdir replay_compare_rule)
      - Master = thin/replay_compare/       (파서룰 + ②G4 마스터 매칭 배선)
    반환: ({'base':{lab:pct}, 'rule':{...}, 'master':{...}}, run_ts). Finetune=Master 이어받음.
    replay_compare_rule 없으면 rule=master 폴백, compare 없으면 base=rule 폴백.
    ★flat 리플레이 런(runs/<ts>/replay_compare, thin 하위폴더 없음 — invoice_replay
    스냅샷만 반입한 067류)은 PADDLE_FILTER(9000 프리셋)일 때만 sub=런폴더로 대체."""
    import glob
    flat_ok = PADDLE_FILTER is not None   # 9000: 리플레이 런은 flat 구조
    for d in sorted(glob.glob(os.path.join(HERE, "runs", "*")), reverse=True):
        sub = os.path.join(d, "thin")
        if not glob.glob(os.path.join(sub, "replay_compare", "*.json")):
            if flat_ok and glob.glob(os.path.join(d, "replay_compare", "*.json")):
                sub = d                    # flat 리플레이 런(예: 067)
            else:
                continue
        mdir = os.path.join(sub, "replay_compare")
        master, _ = _score_compare_dir(mdir)
        master_nocirc, master_nocirc_detail = _score_compare_dir_subset(
            mdir, independent_selectors or {}
        )
        rdir = os.path.join(sub, "replay_compare_rule")
        if glob.glob(os.path.join(rdir, "*.json")):
            rule, _ = _score_compare_dir(rdir)
        else:
            rule = master  # 매칭-제외 사이드카 없으면 단계 구분 불가 → 동일값
        bdir = os.path.join(sub, "compare")
        if glob.glob(os.path.join(bdir, "*.json")):
            base, _ = _score_compare_dir(bdir)
        else:
            base = rule  # AWS compare 없으면 룰전 기준선 없음 → 동일값
        # Master 단계 품명 = 매칭된 정식명(itemNameMaster). 구글 Master 99.4%도 매칭
        # 교체값이므로 raw 읽기(itemName)를 그대로 두면 불공정 비교가 된다.
        if master.get("itemNameMaster") is not None:
            master = dict(master, itemName=master["itemNameMaster"])
        return {
            "base": base,
            "rule": rule,
            "master": master,
            "master_nocirc": master_nocirc,
            "master_nocirc_detail": master_nocirc_detail,
        }, os.path.basename(d)
    return {
        "base": {}, "rule": {}, "master": {},
        "master_nocirc": {}, "master_nocirc_detail": {},
    }, None


def _stage_value(stage, side, lab, b, item_pct, paddle, grule, gmaster):
    """side: 'google'(war) | 'paddle'(우리 PP-OCR, run 결과 자동).
    paddle = {'base','rule','master'} — Base=룰전(compare), Rule=룰후(매칭전),
    Master/Finetune=룰+②마스터매칭(replay_compare)."""
    if side == "paddle":
        pkey = {"base": "base", "rule": "rule"}.get(stage, "master")
        return (paddle.get(pkey) or {}).get(lab)  # run 결과 있으면 자동, 없으면 None
    base_val = item_pct if b == ITEM else b
    if stage == "base":
        return base_val
    if stage == "rule":     # ocr.xml learndata EXACT 매칭
        return grule.get(lab, base_val)
    if stage == "master":   # rule + LIKE/trigram 캐스케이드
        return gmaster.get(lab, base_val)
    if stage == "finetune":
        # 경쟁사(Google DocAI)는 별도 파인튜닝 단계 없음 → master 천장을 기준선으로 이어줌
        return gmaster.get(lab, base_val)
    return None


def _pctcell(v):
    return '<span class="muted">-</span>' if v is None else f"{v:.1f}%"


def _delta(g, p):
    """paddle - google 차이. paddle 우위=초록▲."""
    if g is None or p is None:
        return '<span class="muted">-</span>'
    d = p - g
    if abs(d) < 0.05:
        return '<span class="muted">=</span>'
    cls, arrow = ("up", "▲") if d > 0 else ("down", "▼")
    return f'<span class="{cls}">{arrow}&nbsp;{abs(d):.1f}</span>'


def _pcttxt(v):
    return "-" if v is None else f"{v:.1f}%"


def _dual(full, noc):
    """토글용 듀얼 값: 순환포함(v-full) / 순환제외(v-noc). CSS로 전환."""
    return f'<span class="v-full">{_pcttxt(full)}</span><span class="v-noc">{_pcttxt(noc)}</span>'


def _dual_html(full_html, noc_html):
    return f'<span class="v-full">{full_html}</span><span class="v-noc">{noc_html}</span>'


def _render_panel(stage, active, item_pct, item_ok, item_tot, paddle, grule, gmaster, mdet=None) -> str:
    grp_ko = {"head": "문서 헤더 (필드)", "row": "표 셀 (품목 행)"}

    def _noc_item(lab):
        """동일 독립행의 Google 값. 해당 stage/컬럼 selector가 없으면 None."""
        if not mdet:
            return None
        if stage == "base" and lab == "itemName":
            return mdet.get("inm_base_pct")
        if stage != "master":
            return None
        if lab == "itemName":
            return mdet.get("inm_pct")
        if lab == "itemCode":
            return mdet.get("icd_pct")
        return None

    def _paddle_value(lab, mode):
        """Paddle 값. itemCode 는 learndata 적용값으로 대체 —
        full=전체행 LearnB(순환상한) / nocirc=Google과 동일 독립행 LearnA(held-out).
        구글의 full/독립 토글과 동일 행·동일 분모로 대응한다.
        base/rule 단계는 learndata 전이라 그대로."""
        pkey = {"base": "base", "rule": "rule"}.get(stage, "master")
        same_rows = (
            (stage == "base" and lab == "itemName")
            or (stage == "master" and lab in {"itemName", "itemCode"})
        )
        if mode == "nocirc" and same_rows:
            m = paddle.get("master_nocirc") or {}
        else:
            m = paddle.get(pkey) or {}
        if stage not in ("base", "rule"):
            learn = {"itemCode": ("itemCodeLearnB", "itemCodeLearnA"),
                     "itemName": ("itemNameLearnB", "itemNameLearnA")}.get(lab)
            if learn:
                v = m.get(learn[0] if mode == "full" else learn[1])
                if v is not None:
                    return v
        return m.get(lab)

    def _agg(side, g, mode):
        pool = FIELDS if g == "all" else [t for t in FIELDS if t[1] == g]
        if mode == "nocirc":                       # 순환 pass-through(b==100.0) 제외
            pool = [t for t in pool if t[2] != 100.0]
            # 거래처/지점 최종값(⚑)은 부분순환인데 동일 독립행 selector가 없다.
            # 공정 모드 평균과 표에서 제외하고, 전체 참고 모드에서만 보여준다.
            if stage == "master":
                pool = [t for t in pool if t[0] not in
                        {"supplierCompany", "supplierAddress",
                         "buyerCompany", "buyerAddress"}]
            elif stage == "base":
                # 067 itemCode는 OCR 원문이 아니라 후단 Master가 채운 값이다.
                pool = [t for t in pool if t[0] != "itemCode"]
        vals = []
        for lab, gg, b in pool:
            if side == "paddle":
                v = _paddle_value(lab, mode)
            else:
                v = _stage_value(stage, side, lab, b, item_pct, paddle, grule, gmaster)
                if mode == "nocirc" and _noc_item(lab) is not None:  # 품명/itemCode 독립값
                    v = _noc_item(lab)
            if v is None:
                continue
            vals.append(v)
        return (sum(vals) / len(vals)) if vals else None

    def _c(side, g, ko):
        bg = ' style="background:#f1f3f5"' if side == "google" else ''  # Google만 회색 바탕
        if stage == "master":
            if side == "google":
                ko += (' <span class="v-full">(순환 포함)</span>'
                       '<span class="v-noc">(독립 동일행)</span>')
            else:
                ko += (' <span class="v-full">(Learn B 상한)</span>'
                       '<span class="v-noc">(Learn A·동일행)</span>')
        elif stage == "base":
            ko += (' <span class="v-full">(전체행)</span>'
                   '<span class="v-noc">(독립 동일행)</span>')
        return (f'<div class="cardbox"{bg}><div class="cardv">'
                f'{_dual(_agg(side, g, "full"), _agg(side, g, "nocirc"))}</div>'
                f'<div class="cardl">{ko}</div></div>')
    cards = (
        '<div class="cardgrid">'
        + _c("google", "all", "Google · 전체") + _c("google", "head", "Google · 필드") + _c("google", "row", "Google · 셀")
        + _c("paddle", "all", "Paddle · 전체") + _c("paddle", "head", "Paddle · 필드") + _c("paddle", "row", "Paddle · 셀")
        + '</div>')
    rows, last = [], None
    for i, (lab, grp, b) in enumerate(FIELDS):
        if grp != last:
            rows.append(f'<tr><td colspan="4" style="background:#eef1f4;font-weight:700;'
                        f'font-size:12.5px;color:var(--muted)">{grp_ko[grp]}</td></tr>')
            last = grp
        gv = _stage_value(stage, "google", lab, b, item_pct, paddle, grule, gmaster)
        pv_full = _paddle_value(lab, "full")
        pv_noc = _paddle_value(lab, "nocirc")
        pv = pv_full
        circular = (b == 100.0 and gv is not None)  # GT=구글값 → 자기비교(pass-through)
        _circ_labs = {"itemName", "itemCode", "supplierCompany", "supplierAddress",
                      "buyerCompany", "buyerAddress"}
        circ_item = (stage in ("rule", "master") and lab in _circ_labs and gv is not None)
        partial_without_independent = (
            stage == "master"
            and lab in {"supplierCompany", "supplierAddress",
                        "buyerCompany", "buyerAddress"}
            and gv is not None
        )
        base_not_raw = stage == "base" and lab == "itemCode"
        if b == ITEM and gv is not None and stage == "base":
            full_html = f'<b>{_pctcell(gv)}</b> <span class="muted">({item_ok:,}/{item_tot:,})</span>'
            nv = _noc_item(lab)
            noc_html = (
                f'<b>{_pctcell(nv)}</b> '
                f'<span class="muted" title="최종 탭과 같은 독립행">'
                f'({mdet.get("inm_base_ok",0):,}/{mdet.get("inm_tot",0):,}) ◆</span>'
            )
            gcell = _dual_html(full_html, noc_html)
        elif circ_item:
            tip = "war 최종값과 일치율 — war가 같은 방식(learndata/LIKE/trigram)으로 맞춘 행은 부분순환"
            full_html = f'<b>{_pctcell(gv)}</b> <span class="muted" title="{tip}">⚑</span>'
            nv = _noc_item(lab)                     # 순환제외(독립) 값
            if nv is not None:
                noc_tip = "순환 제외 — war가 우리와 다른 방식으로 맞춘 독립 행만"
                noc_html = f'<b>{_pctcell(nv)}</b> <span class="muted" title="{noc_tip}">◆</span>'
                gcell = _dual_html(full_html, noc_html)
            else:
                gcell = full_html
        elif circular:  # 흐리게 (실제 점수 아님)
            gcell = f'<span class="muted" title="GT가 구글값이라 자기비교(=GT)">{_pctcell(gv)}</span>'
        else:
            gcell = f'<b>{_pctcell(gv)}</b>'
        if b == 100.0:
            trcls = ' class="circ"'                     # 완전 순환
        elif partial_without_independent or base_not_raw:
            trcls = ' class="partcirc"'                 # 독립 selector 없는 부분순환
        else:
            trcls = ''
        # Paddle 셀·Δ: itemCode는 full(LearnB)/nocirc(LearnA) 듀얼, 그 외는 단일.
        # Δ의 nocirc 는 구글 독립값(_noc_item)과 대조 → 토글 시 공정 비교로 전환.
        g_noc = _noc_item(lab)
        gv_noc = g_noc if g_noc is not None else gv
        ndetail = paddle.get("master_nocirc_detail", {}) if stage in {"base", "master"} else {}
        learn_noc = (
            {"itemName": "itemNameLearnA", "itemCode": "itemCodeLearnA"}.get(lab, lab)
            if stage == "master" else lab
        )
        pd = ndetail.get(learn_noc) or {}
        noc_count = (f' <span class="muted" title="Google과 동일 독립행 · 누락 오답 포함">'
                     f'({pd.get("ok",0):,}/{pd.get("total",0):,}) ◆</span>') if pd else ""
        if pv_noc is not None and abs((pv_noc or 0) - (pv_full or 0)) > 0.05:
            pcell = _dual_html(
                f"<b>{_pctcell(pv_full)}</b>",
                f"<b>{_pctcell(pv_noc)}</b>{noc_count}",
            )
        else:
            pcell = _dual_html(
                f"<b>{_pctcell(pv_full)}</b>",
                f"<b>{_pctcell(pv_noc)}</b>{noc_count}",
            ) if pd else f"<b>{_pctcell(pv_full)}</b>"
        if g_noc is not None or (pv_noc is not None and pv_noc != pv_full):
            dcell = _dual_html(_delta(gv, pv_full), _delta(gv_noc, pv_noc))
        else:
            dcell = _delta(gv, pv_full)
        rows.append(f"<tr{trcls}><td>{_ko(lab)}</td><td>{gcell}</td>"
                    f"<td>{pcell}</td><td>{dcell}</td></tr>")
        if (i + 1 == len(FIELDS)) or FIELDS[i + 1][1] != grp:
            label = "셀 전체" if grp == "row" else "필드 전체"
            gf, gn = _agg("google", grp, "full"), _agg("google", grp, "nocirc")
            pf, pn = _agg("paddle", grp, "full"), _agg("paddle", grp, "nocirc")
            rows.append(f'<tr style="background:#f0f6ff;font-weight:700">'
                        f'<td>{label} <span class="muted" style="font-weight:400">(컬럼 평균)</span></td>'
                        f'<td>{_dual(gf, gn)}</td><td>{_dual(pf, pn)}</td>'
                        f'<td>{_dual_html(_delta(gf, pf), _delta(gn, pn))}</td></tr>')
    body = (f'<section><table class="matrix">'
            f'<colgroup><col style="width:46%"><col style="width:18%">'
            f'<col style="width:18%"><col style="width:18%"></colgroup>'
            f'<thead><tr><th>컬럼</th><th>Google</th><th>Paddle (우리)</th>'
            f'<th>비교 Δ</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>')
    return f'<div class="panel{" active" if active else ""}">{cards}{body}</div>'


def build_html(ndocs, item_pct, item_ok, item_tot, paddle, paddle_run, grule, gdet, gmaster, mdet) -> str:
    tabs = "".join(
        f'<div class="tab{" active" if i == 0 else ""}" onclick="showTab({i})">{ko}</div>'
        for i, (st, ko) in enumerate(STAGES))
    panels = "".join(
        _render_panel(st, i == 0, item_pct, item_ok, item_tot, paddle, grule, gmaster, mdet)
        for i, (st, ko) in enumerate(STAGES))
    js = ("function showTab(i){"
          "document.querySelectorAll('.tab').forEach((t,j)=>t.classList.toggle('active',j===i));"
          "document.querySelectorAll('.panel').forEach((p,j)=>p.classList.toggle('active',j===i));}")
    return (
        f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
        f'<title>필드 × 단계 정확도</title><style>{_CSS}{_TAB_CSS}</style></head><body class="hidecirc">'
        f'<div class="head"><h1>필드 × 단계 정확도</h1>'
        f'<label class="toggle"><input type="checkbox" checked '
        f'onchange="document.body.classList.toggle(\'hidecirc\',this.checked)"> '
        f'공정 비교 <span class="muted">(순환 제외·Google/Paddle 동일 행)</span></label></div>'
        f'<div class="gen" style="max-width:1600px;margin:0 auto 6px">샘플 {ndocs:,}장 ({SAMPLE_LABEL}) · 구글 vs GT</div>'
        f'<p class="note" style="border-left:4px solid #d97706;padding-left:10px">'
        f'<b>두 탭의 정답 목표는 다릅니다.</b> '
        f'OCR 읽기 = <code>itemName</code> raw 기준값과 비교 · '
        f'최종 매칭 = <code>itemNameMaster/itemCode</code> 정식 마스터 기준값과 비교. '
        f'따라서 OCR 읽기 우위가 최종 품목 식별 우위를 뜻하지 않습니다.</p>'
        f'<p class="note">탭 2단계 · <b>OCR 읽기</b> = 읽은 값 vs GT(값 없으면 0%) · '
        f'<b>최종 매칭</b> = 룰+파서+마스터 합본: '
        f'Google = ocr.xml 캐스케이드(learndata→LIKE→trigram) + 거래처(지점+사업자번호) + 지점(brch_cd) 충실재현, '
        f'Paddle {("run " + paddle_run) if paddle_run else "(run 없음)"} = 전체 파이프라인(replay_compare, 품명=매칭 정식명 itemNameMaster)</p>'
        f'<div class="tabbar">{tabs}</div>{panels}'
        f'<p class="note">· <b>⚑</b> = war 최종값과 일치율(품명·코드) — war가 같은 방식으로 맞춘 행은 부분순환. '
        f'<b>◆</b> = 순환 제외(독립 행): 품명 <b>{("%.1f%%" % mdet["inm_pct"]) if mdet.get("inm_pct") is not None else "-"}</b> '
        f'({mdet.get("inm_ok",0):,}/{mdet.get("inm_tot",0):,}), '
        f'itemCode <b>{("%.1f%%" % mdet["icd_pct"]) if mdet.get("icd_pct") is not None else "-"}</b> '
        f'({mdet.get("icd_ok",0):,}/{mdet.get("icd_tot",0):,}) · '
        f'<b>체크 상태</b>는 OCR/최종 탭 모두 같은 독립 행을 사용하고, '
        f'최종 Paddle은 LearnData A(held-out)로 채점하며 '
        f'행·값 누락을 오답으로 포함 · <b>체크 해제</b>는 LearnData B 순환상한 참고 · '
        f'<span class="muted">회색 100%</span> = GT가 구글값(순환) · 0% = war에 없음 → Paddle 돌리면 채워짐</p>'
        f'<script>{js}</script></body></html>')


def _apply_preset(args):
    """프리셋/오버라이드로 경로 글로벌 재지정. 6000=기존(2606), 9000=리플레이 기준셋(18개월)."""
    global GT_PATH, SAMPLE_PATH, MMATCH_PATH, CUST_PATH, OUT, SAMPLE_LABEL, PADDLE_FILTER
    if args.preset == "9000":
        SAMPLE_PATH = os.path.join(DATA, "replay_set_v1.txt")
        GT_PATH = os.path.join(DATA, "ground_truth_replay.json")
        MMATCH_PATH = os.path.join(DATA, "master_match_google_9000.json")
        CUST_PATH = os.path.join(DATA, "cust_match_google_9000.json")
        OUT = os.path.join(HERE, "runs", "BASELINE_MATRIX_9000.html")
        SAMPLE_LABEL = "리플레이 기준셋, 18개월 월비례 held-out"
    # 개별 오버라이드
    if args.sample: SAMPLE_PATH = os.path.abspath(args.sample)
    if args.gt:     GT_PATH = os.path.abspath(args.gt)
    if args.mmatch: MMATCH_PATH = os.path.abspath(args.mmatch)
    if args.cust:   CUST_PATH = os.path.abspath(args.cust)
    if args.out:    OUT = os.path.abspath(args.out)
    # Paddle 채점 제한(대량 run에서 이 샘플만 추림). 파일명 = safe_sample_id = 키의 '/'→'__'
    keys = load_sample_keys()
    if keys and args.preset == "9000":
        PADDLE_FILTER = {k.replace("\\", "/").replace("/", "__") for k in keys}


def main():
    import argparse
    ap = argparse.ArgumentParser(description="war GT 필드×단계 정확도 매트릭스 (구글 vs Paddle)")
    ap.add_argument("--preset", choices=["6000", "9000"], default="6000",
                    help="6000=2606 6천샘플(기존) / 9000=리플레이 기준셋 18개월")
    ap.add_argument("--sample"); ap.add_argument("--gt"); ap.add_argument("--out")
    ap.add_argument("--mmatch"); ap.add_argument("--cust")
    args = ap.parse_args()
    _apply_preset(args)

    keys = load_sample_keys()
    ndocs, item_pct, ok, tot = compute_item_baseline(keys)
    grule, gdet = compute_google_rule(keys)
    gmaster, mdet = compute_google_master(keys)
    paddle, paddle_run = load_paddle(mdet.get("independentSelectors"))
    open(OUT, "w", encoding="utf-8").write(
        build_html(ndocs, item_pct, ok, tot, paddle, paddle_run, grule, gdet, gmaster, mdet))
    print("wrote", OUT, f"(sample docs={ndocs:,})")
    if grule:
        print(f"  Google Rule (learndata EXACT, min={gdet['learn_min']}): "
              f"itemName {grule.get('itemName', 0):.1f}% (base {item_pct:.1f}%), "
              f"itemCode {grule.get('itemCode', 0):.1f}% "
              f"[발화 {gdet['fired']:,}행 / cd채점 {gdet['cd_tot']:,}]")
    if gmaster:
        print(f"  Google Master (+LIKE→trigram): "
              f"itemName {gmaster.get('itemName', 0):.1f}%, itemCode {gmaster.get('itemCode', 0):.1f}% "
              f"| itemCode 독립(순환제외) {('%.1f%%' % mdet['icd_pct']) if mdet.get('icd_pct') is not None else '-'} "
              f"({mdet['icd_ok']:,}/{mdet['icd_tot']:,}) "
              f"[룰{mdet['n_rule']:,}/LIKE{mdet['n_like']:,}/trg{mdet['n_trg']:,}/miss{mdet['n_miss']:,}]")
        p = mdet.get("party", {})
        print(f"  Google Master 거래처/지점: "
              + ", ".join(f"{k} {gmaster.get(k,0):.1f}%({p[k][0]:,}/{p[k][1]:,})"
                          for k in ("supplierCompany","supplierAddress","buyerCompany","buyerAddress")))
    elif not os.path.isfile(MMATCH_PATH):
        print("  Google Master: 캐시 없음 → master_match_google.sql 먼저 실행")
    if paddle_run:
        print(f"  Paddle 자동채움: run {paddle_run} ({len(paddle)} fields)")
    else:
        print("  Paddle: run 없음 → '-' (이미지 돌리면 자동 채움)")


if __name__ == "__main__":
    main()
