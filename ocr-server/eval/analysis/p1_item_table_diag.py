#!/usr/bin/env python3
"""
P1 품목표 병목 진단 — run 063 전수 재현 스크립트 (2026-07-07)
============================================================

목적: 이 조사의 모든 오프라인 시뮬 수치를 "정의 + 스크립트"로 재현 가능하게 고정.
      기본 063 산출물(compare/*.json)만으로 나오는 값과, snapshot replay가 필요한
      값을 함수별로 분리해 각각 독립 검증 가능하게 함.

실행:
    cd ocr-server && python eval/analysis/p1_item_table_diag.py [섹션]
    섹션: baseline | path | gtonly | free_ceiling | itemname | ha | all (기본 all)

정의(문서화):
  - ITEM 컬럼 = 10개 품목 테이블 컬럼(아래 ITEM).
  - scored = match+mismatch+ext_missing (GT 존재 셀). gt_empty/spurious 제외.
  - master_or_code(moc) 행 = itemNameMaster OR itemCode 중 하나라도 scored인 행;
    hit = 둘 중 하나라도 match. (compare rows 기준)
  - fallback 파일 = extractionPath=='fallback'. raw=1411 / GT행있는것만=1393.
  - collapse = fallback & moc_scored>0 & moc_hit==0 → 524(전 크기) / +rowCountGt>=3 → 278.
  - gtOnly 행 = compare table.gtOnlyRowIdx (ext 짝이 없어 안 만들어진 GT 행).
  - "OCR가 품명 읽음" = GT itemName(정규화)이 snapshot ocr_lines_raw 텍스트/토큰에
    포함되거나 SequenceMatcher>=0.7. 필요조건이지 위치보장 아님(상한 성격).

기대 산출(063 기준, 재현 목표값):
  baseline    : cell 37.892% (43661/115226), field 54.216%, moc 49.95%
  path        : free 591f/3551r moc58.6% | fallback 1411f/8904r moc46.5%
  gtonly      : ext_missing 49634, gtOnly귀속 26418(53.2%)
  free_ceiling: free후보+master가 fallback 대비 -22.7pp (11.2% vs 33.8%) → Direction A 기각
  itemname    : itemName 빈칸 3782 → matched+OCRhad 695 (+0.60pp)
  ha          : HA use=True 35% / gtOnly품명 HA재구성불가 74%
"""
import json
import glob
import os
import re
import sys
from collections import defaultdict, Counter
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))   # ocr-server/
RUN = os.path.join(ROOT, "eval", "runs", "063_20260707_121352", "thin")
CMP = os.path.join(RUN, "compare")
SNAP = os.path.join(RUN, "snapshots")
SCORED_TOTAL = 115226  # 063 전체 scored 셀 (impact pp 환산 분모)

ITEM = ["itemName", "itemNameMaster", "itemCode", "spec", "quantity",
        "unitPrice", "amount", "expiryDate", "manufacturingNo", "insuranceCode"]


def _st(c):
    return c.get("status") if c else None


def _norm(s):
    return re.sub(r"[^\w가-힣]", "", (s or "").lower())


def _emit(lines):
    sys.stdout.buffer.write(("\n".join(lines) + "\n").encode("utf-8"))


def _compare_files():
    return sorted(glob.glob(os.path.join(CMP, "*.json")))


# --- baseline: compare/*.json 만으로 재현 -----------------------------------
def baseline():
    cc = Counter()
    col = defaultdict(lambda: Counter())
    moc_hit = moc_scored = 0
    for f in _compare_files():
        d = json.load(open(f, encoding="utf-8"))
        t = d.get("table", {})
        for k, v in t.get("cellCounts", {}).items():
            cc[k] += v
        for row in t.get("rows", []):
            cs = row.get("cells", {})
            nm, co = cs.get("itemNameMaster", {}), cs.get("itemCode", {})
            rs = _st(nm) in ("match", "mismatch", "ext_missing") or _st(co) in ("match", "mismatch", "ext_missing")
            rh = _st(nm) == "match" or _st(co) == "match"
            if rs:
                moc_scored += 1
                moc_hit += 1 if rh else 0
            for c, cell in cs.items():
                col[c][_st(cell)] += 1
    scored = cc["scored"]
    out = ["=== baseline (compare only) ==="]
    out.append("cell  %d/%d = %.4f%%  (mismatch %d, ext_missing %d, spurious %d)"
               % (cc["match"], scored, 100 * cc["match"] / scored, cc["mismatch"], cc["ext_missing"], cc["spurious"]))
    out.append("moc   %d/%d = %.2f%%" % (moc_hit, moc_scored, 100 * moc_hit / moc_scored))
    for c in ITEM:
        s = col[c]
        sc = s["match"] + s["mismatch"] + s["ext_missing"]
        out.append("  %-16s %5d/%5d = %4.1f%%" % (c, s["match"], sc, 100 * s["match"] / sc if sc else 0))
    _emit(out)


# --- path split + collapse: compare only ------------------------------------
def path():
    P = defaultdict(lambda: dict(files=0, rows=0, gt=0, gtonly=0, extonly=0, mh=0, ms=0,
                                 **{c + "_m": 0 for c in ITEM}, **{c + "_s": 0 for c in ITEM}))
    collapse_524 = collapse_278 = 0
    for f in _compare_files():
        d = json.load(open(f, encoding="utf-8"))
        ep = d.get("extractionPath")
        t = d.get("table", {})
        p = P[ep]
        p["files"] += 1
        p["gt"] += t.get("rowCountGt", 0)
        p["gtonly"] += len(t.get("gtOnlyRowIdx", []))
        p["extonly"] += len(t.get("extOnlyRowIdx", []))
        fh = fs = 0
        for row in t.get("rows", []):
            cs = row.get("cells", {})
            p["rows"] += 1
            nm, co = cs.get("itemNameMaster", {}), cs.get("itemCode", {})
            rs = _st(nm) in ("match", "mismatch", "ext_missing") or _st(co) in ("match", "mismatch", "ext_missing")
            rh = _st(nm) == "match" or _st(co) == "match"
            if rs:
                p["ms"] += 1; fs += 1
                if rh:
                    p["mh"] += 1; fh += 1
            for c in ITEM:
                cell = cs.get(c, {})
                if _st(cell) in ("match", "mismatch", "ext_missing"):
                    p[c + "_s"] += 1
                    if _st(cell) == "match":
                        p[c + "_m"] += 1
        if ep == "fallback" and fs > 0 and fh == 0:
            collapse_524 += 1
            if t.get("rowCountGt", 0) >= 3:
                collapse_278 += 1
    out = ["=== path split ==="]
    for ep in ("free", "fallback"):
        p = P[ep]
        out.append("%-9s files=%d rows=%d moc=%.1f%% gtOnly=%d extOnly=%d"
                   % (ep, p["files"], p["rows"], 100 * p["mh"] / p["ms"], p["gtonly"], p["extonly"]))
        for c in ("itemName", "itemNameMaster", "itemCode", "quantity", "unitPrice", "amount"):
            out.append("    %-14s %4.1f%%" % (c, 100 * p[c + "_m"] / p[c + "_s"] if p[c + "_s"] else 0))
    out.append("collapse(moc0): 524-def=%d  278-def(gtRows>=3)=%d" % (collapse_524, collapse_278))
    _emit(out)


# --- gtOnly attribution of ext_missing: compare only ------------------------
def gtonly():
    tot = gto = mat = 0
    for f in _compare_files():
        d = json.load(open(f, encoding="utf-8"))
        t = d.get("table", {})
        gset = set(str(x) for x in t.get("gtOnlyRowIdx", []))
        for row in t.get("rows", []):
            ridx = str(row.get("rowIndex", ""))
            for c, cell in row.get("cells", {}).items():
                if _st(cell) == "ext_missing":
                    tot += 1
                    if ridx in gset:
                        gto += 1
                    else:
                        mat += 1
    _emit(["=== ext_missing attribution ===",
           "total ext_missing = %d" % tot,
           "  in gtOnly rows   = %d (%.1f%%)" % (gto, 100 * gto / tot),
           "  in matched rows  = %d (%.1f%%)" % (mat, 100 * mat / tot)])


# --- snapshot-replay measurements (free extractor 필요) ----------------------
def _load_free():
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "eval"))
    import extractors.invoice_statement_free as F
    return F


def free_ceiling():
    """Direction A 기각 근거: fallback 파일에 free 후보+master fill 채점 vs 현재 fallback."""
    F = _load_free()
    from extractors.master_match import fill_master_match, get_matcher
    import contract as C
    from compare_table import compare_table
    from gt_loader import load_gt_aggregate
    from build_manifest import build_manifest
    man = build_manifest("invoice_thin")
    agg = load_gt_aggregate(os.path.normpath(os.path.join(C.HERE, man["gtAggregate"])), profile=man["kind"])
    gtkey = {s["sourceFile"]: s.get("gtKey") for s in man["samples"]}
    matcher = get_matcher()
    cur = [0, 0]; new = [0, 0]; nfree = 0
    for f in _compare_files():
        d = json.load(open(f, encoding="utf-8"))
        if d["extractionPath"] != "fallback":
            continue
        src = d["sourceFile"]
        gt = agg.get(gtkey.get(src))
        if not gt:
            continue
        tcur = d["table"]
        cur[0] += tcur["cellCounts"]["match"]; cur[1] += tcur["cellCounts"]["scored"]
        snap = json.load(open(os.path.join(SNAP, src + ".json"), encoding="utf-8"))
        lines = [(r[0], r[1], r[2]) for r in (snap.get("ocr_lines_raw") or [])]
        img = snap.get("image_size") or [0, 0]
        res = F.extract_invoice_statement_free(ocr_lines_raw=lines, full_text=snap.get("full_text", ""),
                                               image_size=(int(img[0]), int(img[1])),
                                               doc_type=snap.get("doc_type", "invoice_statement"),
                                               context=snap.get("context") or {})
        fd = (res.get("extract_debug", {}) or {}).get("invoice_statement_free", {}) or {}
        frows = [dict(r) for r in ((fd.get("tableCandidates", {}) or {}).get("rows") or []) if isinstance(r, dict)]
        nfree += len(frows)
        if frows:
            try:
                fill_master_match(frows, matcher)
            except Exception:
                pass
        tnew = compare_table(gt["tableRows"], frows)
        new[0] += tnew["cellCounts"]["match"]; new[1] += tnew["cellCounts"]["scored"]
    _emit(["=== free-candidate ceiling on fallback files (Direction A) ===",
           "free candidate rows total = %d" % nfree,
           "current fallback : %d/%d = %.2f%%" % (cur[0], cur[1], 100 * cur[0] / cur[1]),
           "free-cand+master : %d/%d = %.2f%%" % (new[0], new[1], 100 * new[0] / new[1]),
           "Δ = %+.2fpp  (음수면 Direction A 기각)" % (100 * new[0] / new[1] - 100 * cur[0] / cur[1])])


def itemname():
    """itemName 빈칸 3782 분해: gtOnly vs matched, matched&OCR-had(직접 레버)."""
    F = None  # OCR-had 판정은 PARSER_DROP class 사용(스냅샷 불요)
    pdc = json.load(open(os.path.join(RUN, "PARSER_DROP_CLASSIFY.json"), encoding="utf-8"))["defects"]
    cls_by = defaultdict(list)
    for x in pdc:
        if x["column"] == "itemName" and x["status"] == "ext_missing":
            cls_by[(x["src"], x["gtNorm"])].append(x["class"])
    tot = gto = mat = mat_pd = 0
    for f in _compare_files():
        d = json.load(open(f, encoding="utf-8"))
        src = d["sourceFile"]
        t = d.get("table", {})
        gset = set(str(x) for x in t.get("gtOnlyRowIdx", []))
        for row in t.get("rows", []):
            cell = row.get("cells", {}).get("itemName")
            if not cell or _st(cell) != "ext_missing":
                continue
            tot += 1
            if str(row.get("rowIndex", "")) in gset:
                gto += 1
            else:
                mat += 1
                lst = cls_by.get((src, cell.get("gtNorm", "")))
                if lst and "parser_drop" in lst:
                    mat_pd += 1
    _emit(["=== itemName blank lever ===",
           "itemName ext_missing total = %d" % tot,
           "  gtOnly(행없음)           = %d (%.0f%%)" % (gto, 100 * gto / tot),
           "  matched(행있음)          = %d" % mat,
           "     matched & OCR-had(parser_drop, 직접레버) = %d  -> +%.2fpp"
           % (mat_pd, 100 * mat_pd / SCORED_TOTAL)])


def ha():
    """gtOnly 품명을 HA가 재구성하는가 / HA use 여부."""
    F = _load_free()
    files_g = {}
    for f in _compare_files():
        d = json.load(open(f, encoding="utf-8"))
        if d["extractionPath"] != "fallback":
            continue
        gset = set(str(x) for x in d["table"].get("gtOnlyRowIdx", []))
        names = [row.get("cells", {}).get("itemName", {}).get("gt", "")
                 for row in d["table"].get("rows", []) if str(row.get("rowIndex", "")) in gset]
        names = [n for n in names if len(_norm(n)) >= 3]
        if names:
            files_g[d["sourceFile"]] = names
    use = norun = 0
    norun_r = Counter()
    gtot = gin = gout = 0
    for src, gnames in files_g.items():
        snap = json.load(open(os.path.join(SNAP, src + ".json"), encoding="utf-8"))
        lines = [(r[0], r[1], r[2]) for r in (snap.get("ocr_lines_raw") or []) if len(r) >= 2]
        ocr_items = F._extract_ocr_line_items(lines)
        ha_rows, ha_dbg = F._extract_header_anchored_table(ocr_items, append_mode=True)
        if not ha_dbg.get("use") or not ha_rows:
            norun += 1
            norun_r[ha_dbg.get("reason", "?")] += 1
            gtot += len(gnames); gout += len(gnames)
            continue
        use += 1
        hnames = [_norm(r.get("itemName")) for r in ha_rows if r.get("itemName")]
        for gn in gnames:
            gtot += 1
            g = _norm(gn)
            if any(g in h or (len(h) >= 4 and h in g) or SequenceMatcher(None, g, h).ratio() >= 0.7 for h in hnames if h):
                gin += 1
            else:
                gout += 1
    proc = use + norun
    _emit(["=== HA-append coverage of gtOnly ===",
           "files processed = %d  HA use=True %d (%.0f%%)  norun %d (%.0f%%)"
           % (proc, use, 100 * use / proc, norun, 100 * norun / proc),
           "  norun reasons: %s" % dict(norun_r.most_common(8)),
           "gtOnly names = %d  HA재구성함 %d (%.0f%%)  HA불가 %d (%.0f%%)"
           % (gtot, gin, 100 * gin / gtot, gout, 100 * gout / gtot)])


SECTIONS = {"baseline": baseline, "path": path, "gtonly": gtonly,
            "free_ceiling": free_ceiling, "itemname": itemname, "ha": ha}

if __name__ == "__main__":
    sel = sys.argv[1] if len(sys.argv) > 1 else "all"
    order = ["baseline", "path", "gtonly", "itemname", "free_ceiling", "ha"]
    for name in (order if sel == "all" else [sel]):
        SECTIONS[name]()
        print()
