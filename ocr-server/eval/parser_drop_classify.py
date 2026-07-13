"""parser_drop_classify — exhaustive "OCR read it, parser dropped it" taxonomy.

READ-ONLY analysis sidecar. Cross-references, per sample, the run's
  compare/<src>.json   (per-field + per-cell GT vs ext status)
with the run's
  snapshots/<src>.json (the EXACT OCR output the parser was fed: full_text + lines)

For every defective cell/field (status mismatch | ext_missing) it asks the one
question that splits parser-work from OCR-work (feedback_systematic_report_analysis):

    Is the GT value actually present in the OCR output?
      exact/strong present -> PARSER-DROP (recoverable: OCR read it, parser lost it)
      fuzzy-only present   -> AMBIGUOUS-FUZZY (do not claim parser recovery)
      absent               -> RECOGNITION (OCR-bound, NOT a parser target)

Parser-drops are then split into PATTERNS so we fix by CLASS, not per-case
(feedback_class_not_per_case):
    drop        ext_missing  + value present in OCR        -> parser omitted a readable cell
    mislocate   value present in OCR AND in ext elsewhere  -> landed in wrong column/field
    wrongpick   value present in OCR, ext has other/garbled-> parser picked the wrong line

Output: a column x pattern count table, split clean-original vs angle-variant
(clean = the 6 source files; variants overfit-prone per 24-base memory). Sorted
biggest-class-first so we know where to aim.

Touches NOTHING the checker reads (samples/, compare/, metrics/, trend). Writes
only its own sidecars: PARSER_DROP_CLASSIFY.{md,json} under the run's study dir.

    ../.venv/Scripts/python.exe eval/parser_drop_classify.py
    ../.venv/Scripts/python.exe eval/parser_drop_classify.py --ts 053_20260617_142725/study
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402
import normalize as N  # noqa: E402

# clean source originals; everything else (1-1.jpg ...) is an angle/deskew variant.
CLEAN = {"1.jpg", "3.pdf", "4.pdf", "5.pdf", "6.pdf", "7.pdf"}

DIGIT_TYPES = {"amount", "qty", "bizno", "date", "index"}
_NON_ALNUM = re.compile(r"[^0-9A-Za-z가-힣]+")
_DIGITS = re.compile(r"\D+")


def _field_type(label: str) -> str:
    return N.FIELD_TYPE.get(label) or N._infer_type(label)


def _cell_type(key: str) -> str:
    return N.ROW_KEY_TYPE.get(key) or N._infer_type(key)


def _pp_features(pp: dict | None) -> dict | None:
    """Extract the actionable preprocessing risk signals from a sample's
    `preprocess` telemetry (run_batch captured extract_debug.preprocess).

    These are all knowable BEFORE GT — so a bucket that's systematically worse
    points at a preprocessing DECISION to fix server-side, not a parser rule.
    orientMargin = gap between the top-2 orientation scores (low = the 90/180/270
    pick was a coin-flip = the catastrophic 'whole page rotated wrong' risk)."""
    if not isinstance(pp, dict):
        return None
    o = pp.get("orientation") or {}
    d = pp.get("deskew") or {}
    doc = pp.get("document") or {}
    margin = None
    try:
        vals = sorted((float(v) for v in (o.get("allScores") or {}).values()), reverse=True)
        if len(vals) >= 2:
            margin = round(vals[0] - vals[1], 1)
    except (TypeError, ValueError):
        pass
    applied = o.get("finalAppliedAfterPolicy")
    if applied is None:
        applied = o.get("applied")
    def _num(x):
        return x if isinstance(x, (int, float)) else None
    return {
        "orientApplied": bool(applied),
        "orientAngle": o.get("angle"),
        "orientMargin": margin,
        "deskewApplied": bool(d.get("applied")),
        "deskewAbs": _num(d.get("absAngle")),
        "deskewReverted": bool((d.get("overApplyGuard") or {}).get("reverted")),
        "areaPct": _num(doc.get("areaPct")),
        "forcedWarp": bool(doc.get("forcedWarpOnSkip")),
    }


def _orient_bucket(f: dict) -> list[str]:
    if not f["orientApplied"] or f["orientAngle"] in (0, None):
        return ["미적용(0°)"]
    return [f"{f['orientAngle']}° 적용"]


def _deskew_bucket(f: dict) -> list[str]:
    if f["deskewReverted"]:
        return ["guard-revert"]
    if not f["deskewApplied"]:
        return ["미적용"]
    a = f["deskewAbs"]
    return ["≤2°" if (a is not None and a <= 2.0) else ">2°"]


def _warp_bucket(f: dict) -> list[str]:
    out = []
    a = f["areaPct"]
    if a is not None:
        out.append("영역≥90%" if a >= 90 else ("영역50–90%" if a >= 50 else "영역<50%"))
    if f["forcedWarp"]:
        out.append("forcedWarpOnSkip")
    return out or ["영역미상"]


def _preprocess_buckets(scores: list[dict], recog: list[dict], samples_dir: str) -> dict | None:
    """Cross-tab: for each preprocessing condition bucket, the cell accuracy +
    recognition rate (recognition defects / scored cells). Scale-invariant
    (O(buckets), not O(samples)) and micro-aggregated. Δ vs baseline = the cost.

    Returns None if no sample carries preprocess telemetry (older runs)."""
    from collections import Counter
    recog_by_src: Counter = Counter(d["src"] for d in recog)
    feats: dict[str, dict] = {}
    for s in scores:
        try:
            pp = json.load(open(os.path.join(samples_dir, s["src"] + ".json"),
                                encoding="utf-8")).get("preprocess")
        except (OSError, json.JSONDecodeError):
            pp = None
        f = _pp_features(pp)
        if f is not None:
            feats[s["src"]] = f
    if not feats:
        return None

    def agg_by(keyfn) -> list[dict]:
        bk: dict[str, dict] = {}
        for s in scores:
            f = feats.get(s["src"])
            if f is None:
                continue
            for k in keyfn(f):
                a = bk.setdefault(k, {"bucket": k, "n": 0, "cM": 0, "cS": 0, "recog": 0,
                                      "mSum": 0.0, "mN": 0})
                a["n"] += 1
                a["cM"] += s["cScored"] and s["cMatch"]
                a["cS"] += s["cScored"]
                a["recog"] += recog_by_src.get(s["src"], 0)
                if f["orientMargin"] is not None:
                    a["mSum"] += f["orientMargin"]; a["mN"] += 1
        rows = list(bk.values())
        for a in rows:
            a["cellAcc"] = (a["cM"] / a["cS"]) if a["cS"] else None
            a["recogRate"] = (a["recog"] / a["cS"]) if a["cS"] else None
            a["avgMargin"] = round(a["mSum"] / a["mN"], 1) if a["mN"] else None
        return rows

    return {
        "orientation": agg_by(_orient_bucket),
        "deskew": agg_by(_deskew_bucket),
        "warp": agg_by(_warp_bucket),
        "coverage": {"withTelemetry": len(feats), "total": len(scores)},
    }


def _collapse_alnum(s: str) -> str:
    return _NON_ALNUM.sub("", unicodedata.normalize("NFC", s or "")).casefold()


def _collapse_digits(s: str) -> str:
    return _DIGITS.sub("", s or "")


def _ocr_haystacks(snap: dict):
    """Return (alnum_full, digits_full, lines_alnum, lines_digits) from a snapshot."""
    full = snap.get("full_text") or ""
    lines = []
    for item in snap.get("ocr_lines_raw") or []:
        # ocr_lines_raw row = [box, text, score]
        try:
            lines.append(str(item[1]))
        except (IndexError, TypeError):
            continue
    return (
        _collapse_alnum(full),
        _collapse_digits(full),
        [_collapse_alnum(t) for t in lines],
        [_collapse_digits(t) for t in lines],
    )


def _present_in_ocr(gt_norm: str, vtype: str, hay) -> tuple[bool, str]:
    """Is the (already type-normalized) GT value present in the OCR output?

    Returns (present, how). Digit values: contiguous substring of some line's
    digits (strong) or of full_text digits (weak). Text/code/address: collapsed
    substring, or best per-line fuzzy ratio >= 0.90 (tolerates spacing splits).
    Empty / too-short GT is treated as not-a-target (returns False, "trivial").
    """
    alnum_full, digits_full, lines_alnum, lines_digits = hay
    if not gt_norm:
        return False, "trivial"
    if vtype in DIGIT_TYPES:
        g = _collapse_digits(gt_norm)
        if len(g) < 2:
            return False, "trivial"
        if any(g in ld for ld in lines_digits):
            return True, "line_digits"
        if g in digits_full:
            return True, "full_digits"
        return False, "absent"
    # text-like
    g = _collapse_alnum(gt_norm)
    if len(g) < 2:
        return False, "trivial"
    if g in alnum_full:
        return True, "full_alnum"
    best = max((SequenceMatcher(None, g, la).ratio() for la in lines_alnum), default=0.0)
    if best >= 0.90:
        return True, f"line_fuzzy({best:.2f})"
    return False, f"absent(best={best:.2f})"


# bbox-locality: a fuzzy/exact GT match SOMEWHERE on the page is not proof the
# OCR read this cell's value AT this row. We locate the row's Y-band from its
# matched cells, then check whether a clean GT token sits within that band.
LOCAL_TOL = 15.0     # px around the row's median Y to count as "this row"
LOCAL_CLEAN = 0.97   # local token must match GT this well to confirm parser


def _load_run_meta(run_dir: str) -> dict:
    try:
        value = json.load(open(os.path.join(run_dir, "run_meta.json"), encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _recorded_scope(run_meta: dict) -> set[str] | None:
    ran = run_meta.get("ran")
    if not isinstance(ran, list) or not all(isinstance(src, str) and src for src in ran):
        return None
    return set(ran)


def _clean_classification(src: str, run_meta: dict) -> bool | None:
    """Return legacy study clean/angle classification, or None if unavailable.

    The old six-name CLEAN set belongs only to invoice_study. Applying it to a
    thin run labels every production filename as an angle variant, which is
    false metadata. Thin stays explicitly unclassified until manifest/GT carries
    original/variant provenance.
    """
    if run_meta.get("kind") == "thin" or run_meta.get("testset") == "invoice_thin":
        return None
    return src in CLEAN


def _raw_master_cross_add(cross: dict, src: str, cmp: dict) -> None:
    """Accumulate row-level itemName -> itemNameMaster transition metrics."""
    counts = cross["counts"]
    protected = cross["protectedRows"]
    for row in (cmp.get("table") or {}).get("rows") or []:
        cells = row.get("cells") or {}
        raw_status = (cells.get("itemName") or {}).get("status", "none")
        master_status = (cells.get("itemNameMaster") or {}).get("status", "none")
        row_id = f"{src}#row{row.get('rowIndex', '')}"
        raw_bad = raw_status in {"mismatch", "ext_missing"}
        master_bad = master_status in {"mismatch", "ext_missing"}
        if raw_bad and master_status == "match":
            key = "rawWrong_masterCorrect"
            protected[key].append(row_id)
        elif raw_bad and master_bad:
            key = "rawWrong_masterWrongOrMissing"
        elif raw_status == "match" and master_status == "match":
            key = "rawCorrect_masterCorrect"
        elif raw_status == "match" and master_status == "mismatch":
            key = "rawCorrect_masterWrong"
            protected[key].append(row_id)
        elif raw_status == "match" and master_status == "ext_missing":
            key = "rawCorrect_masterMissing"
            protected[key].append(row_id)
        else:
            continue
        counts[key] += 1


def _ocr_tokens_xy(snap: dict):
    """[(alnum, digits, y_center), ...] from snapshot bboxes (ocr_lines_raw row = [box, text, score])."""
    out = []
    for item in snap.get("ocr_lines_raw") or []:
        try:
            box, text = item[0], str(item[1])
            yc = sum(p[1] for p in box) / len(box)
        except (IndexError, TypeError, ZeroDivisionError):
            continue
        out.append((_collapse_alnum(text), _collapse_digits(text), yc))
    return out


def _row_yband(row: dict, tokens) -> float | None:
    """Median Y of the row's matched-cell ext values located in OCR. None if unlocatable."""
    ys = []
    for _ck, cell in row["cells"].items():
        if cell.get("status") != "match":
            continue
        ev = _collapse_alnum(cell.get("extNorm") or "")
        if len(ev) < 4:   # need a distinctive anchor (skip short numerics)
            continue
        for a, _d, yc in tokens:
            if ev in a:
                ys.append(yc)
                break
    if not ys:
        return None
    ys.sort()
    return ys[len(ys) // 2]


def _local_ratio(gt: str, vtype: str, tokens, yband: float | None) -> float | None:
    """Best GT-match ratio among OCR tokens within the row's Y-band.
    None = band unknown or no token in band (can't judge locally)."""
    if yband is None:
        return None
    g = _collapse_digits(gt) if vtype in DIGIT_TYPES else _collapse_alnum(gt)
    if len(g) < 2:
        return None
    best = 0.0
    seen = False
    for a, d, yc in tokens:
        if abs(yc - yband) > LOCAL_TOL:
            continue
        hay = d if vtype in DIGIT_TYPES else a
        if not hay:
            continue
        seen = True
        if g in hay:
            return 1.0
        r = SequenceMatcher(None, g, hay).ratio()
        if r > best:
            best = r
    return best if seen else None


def _ext_value_locations(fields: dict, table: dict) -> dict[str, set[str]]:
    """normalized ext value -> set of locations it appears at on the EXTRACTED side."""
    idx: dict[str, set[str]] = defaultdict(set)
    for label, info in fields["perField"].items():
        v = info.get("extNorm")
        if v:
            idx[v].add(f"field:{label}")
    for row in table["rows"]:
        for ck, cell in row["cells"].items():
            v = cell.get("extNorm")
            if v:
                idx[v].add(f"row{row['rowIndex']}:{ck}")
    return idx


def classify_sample(src: str, cmp: dict, snap: dict | None) -> list[dict]:
    fields, table = cmp["fields"], cmp["table"]
    hay = _ocr_haystacks(snap) if snap else (None,) * 4
    tokens_xy = _ocr_tokens_xy(snap) if snap else []
    ext_idx = _ext_value_locations(fields, table)
    out: list[dict] = []

    def emit(loc, col, vtype, status, gtn, extn, yband=None, gtr=None):
        present = how = None
        if snap is not None:
            present, how = _present_in_ocr(gtn, vtype, hay)
        if present and str(how).startswith("line_fuzzy"):
            # A near string somewhere on the page is not proof that OCR read
            # the exact GT value at this field/row. Keep it out of both the
            # confirmed parser and confirmed OCR backlogs until row/bbox-local
            # evidence can resolve it.
            cls, pattern = "ambiguous_fuzzy", "fuzzy_only"
        elif not present:
            cls, pattern = "recognition", "ocr_absent" if snap is not None else "no_snapshot"
        else:
            elsewhere = {l for l in ext_idx.get(gtn, set()) if l != loc}
            if status == "ext_missing" and not elsewhere:
                cls, pattern = "parser_drop", "drop"
            elif elsewhere:
                cls, pattern = "parser_drop", "mislocate"
            else:
                cls, pattern = "parser_drop", "wrongpick"
        # bbox-locality override (table cells only — fields have no row band).
        # Resolve parser_drop/ambiguous by the OCR token AT this cell's row:
        #   clean GT token local (>=LOCAL_CLEAN) -> confirmed parser (promote ambiguous)
        #   only a garbled token local           -> recognition (OCR misread THIS cell)
        # The page-elsewhere duplicate (e.g. same drug name on another row) no
        # longer counts as proof.
        if yband is not None and cls in ("parser_drop", "ambiguous_fuzzy"):
            lr = _local_ratio(gtn, vtype, tokens_xy, yband)
            if lr is not None:
                if lr >= LOCAL_CLEAN:
                    if cls == "ambiguous_fuzzy":
                        cls, pattern = "parser_drop", "wrongpick"
                else:
                    cls, pattern = "recognition", "ocr_local_garbled"
                how = f"{how};local({lr:.2f})"
        # Fields (no row band) / cells the band couldn't place: if the parser's
        # OWN ext is a char-garbled version of GT (GT is NOT a clean substring of
        # ext), the parser DID extract this value and the OCR misread it ->
        # recognition. (A clean GT-substring-of-ext means parser noise -> parser.)
        if cls == "ambiguous_fuzzy" and extn:
            ge, ee = _collapse_alnum(gtn), _collapse_alnum(extn)
            if ge and ge not in ee:
                cls, pattern = "recognition", "ocr_garbled_ext"
                how = f"{how};ext_garble"
        out.append({
            "src": src, "clean": src in CLEAN, "location": loc, "column": col,
            "vtype": vtype, "status": status, "gtNorm": gtn, "extNorm": extn,
            "gtRaw": gtr,   # 원문 GT(정규화 전) — 파인튜닝 라벨용(인쇄형 보존)
            "class": cls, "pattern": pattern, "ocrHow": how,
        })

    for label, info in fields["perField"].items():
        if info["status"] in ("mismatch", "ext_missing"):
            emit(f"field:{label}", label, _field_type(label), info["status"],
                 info["gtNorm"], info["extNorm"], gtr=info.get("gt"))
    for row in table["rows"]:
        yband = _row_yband(row, tokens_xy) if tokens_xy else None
        for ck, cell in row["cells"].items():
            if cell["status"] in ("mismatch", "ext_missing"):
                emit(f"row{row['rowIndex']}:{ck}", ck, _cell_type(ck),
                     cell["status"], cell["gtNorm"], cell["extNorm"], yband=yband,
                     gtr=cell.get("gt"))
    return out


def _pct(match: int, scored: int) -> str:
    return "n/a" if not scored else f"{100*match/scored:.1f}%"


_SORT_JS = """<script>
document.querySelectorAll('table.sortable').forEach(t=>{
 t.querySelectorAll('th').forEach((th,i)=>{th.style.cursor='pointer';th.title='클릭=정렬';
  th.addEventListener('click',()=>{const tb=t.tBodies[0];const rows=[...tb.rows];
   const num=th.dataset.num==='1';const asc=th.dataset.asc!=='1';
   t.querySelectorAll('th').forEach(o=>o.dataset.asc='');th.dataset.asc=asc?'1':'0';
   rows.sort((a,b)=>{let x=a.cells[i].dataset.v??a.cells[i].textContent,
     y=b.cells[i].dataset.v??b.cells[i].textContent;
    if(num){x=parseFloat(x)||0;y=parseFloat(y)||0;return asc?x-y:y-x;}
    return asc?(''+x).localeCompare(y):(''+y).localeCompare(x);});
   rows.forEach(r=>tb.appendChild(r));});});});
</script>"""


def _render_preprocess_section(pp_buckets, _esc) -> str:
    """전처리 진단 섹션 — 조건 버킷별 셀정확도 + recognition율(+baseline 대비 Δ).
    수천장에서 '전처리가 어느 조건에서 체계적으로 깎는가'를 한 표로."""
    if not pp_buckets:
        return ""
    cov = pp_buckets.get("coverage", {})
    H = ["<section><h2>전처리 진단 "
         "<span class='muted'>(recognition = OCR 바운드 결함; 전처리 실패가 여기로 나타남)</span></h2>",
         f"<div class='note'><div class='row'>각 표 = 전처리 조건 버킷별 <b>셀 정확도</b>·"
         f"<b>recognition율</b>(결함/채점셀). <b>Δ</b> = baseline 대비 recognition율 차이"
         f"(<b>+면 그 조건이 깎는 중</b> → 서버 전처리에서 고칠 후보). "
         f"<span class='muted'>텔레메트리 보유 {cov.get('withTelemetry','?')}/{cov.get('total','?')} 샘플</span>"
         f"</div></div>"]

    def table(title, hint, rows, baseline_key, extra_col=None):
        if not rows:
            return ""
        base = next((r for r in rows if r["bucket"] == baseline_key), None)
        base_rr = base["recogRate"] if base else None
        rows = sorted(rows, key=lambda r: -(r["recogRate"] or 0))
        h = [f"<h3 style='margin:14px 0 6px'>{_esc(title)} "
             f"<span class='muted' style='font-size:12px;font-weight:400'>{_esc(hint)}</span></h3>",
             "<table class='sortable'><thead><tr><th>조건</th><th data-num='1'>샘플수</th>"
             "<th data-num='1'>셀 정확도</th><th data-num='1'>recognition율</th>"
             "<th data-num='1'>Δ vs baseline</th>"
             + ("<th data-num='1'>평균 orient margin</th>" if extra_col else "")
             + "</tr></thead><tbody>"]
        for r in rows:
            ca = r["cellAcc"]; rr = r["recogRate"]
            ca_s = "n/a" if ca is None else f"{ca*100:.1f}%"
            rr_s = "n/a" if rr is None else f"{rr*100:.1f}%"
            d = (rr - base_rr) if (rr is not None and base_rr is not None) else None
            d_s = "—" if r["bucket"] == baseline_key else ("n/a" if d is None
                  else f"<b style='color:{'#cf222e' if d>0.005 else '#1a7f37' if d<-0.005 else 'inherit'}'>"
                       f"{'+' if d>=0 else ''}{d*100:.1f}pp</b>")
            cacls = "acc-lo" if (ca is not None and ca<0.5) else ("acc-mid" if (ca is not None and ca<0.8) else "acc-ok" if ca is not None else "")
            mg = ""
            if extra_col:
                m = r.get("avgMargin")
                mg = f"<td data-v='{m if m is not None else -1}'>{'n/a' if m is None else m}</td>"
            h.append(f"<tr><td><b>{_esc(r['bucket'])}</b></td>"
                     f"<td data-v='{r['n']}'>{r['n']}</td>"
                     f"<td data-v='{ca or 0:.4f}' class='{cacls}'>{ca_s}</td>"
                     f"<td data-v='{rr or 0:.4f}'>{rr_s}</td>"
                     f"<td data-v='{d if d is not None else 0:.4f}'>{d_s}</td>{mg}</tr>")
        h.append("</tbody></table>")
        return "".join(h)

    H.append(table("방향(orientation)", "margin 낮음+적용=오회전 위험(페이지 통째 깨짐)",
                   pp_buckets.get("orientation"), "미적용(0°)", extra_col=True))
    H.append(table("기울기(deskew)", "guard-revert=과적용 가드 작동",
                   pp_buckets.get("deskew"), "미적용"))
    H.append(table("문서검출(warp)", "영역% 낮음/강제warp=크롭 위험",
                   pp_buckets.get("warp"), "영역≥90%"))
    H.append("</section>")
    return "".join(H)


def _render_html(run_label, compare_dir, scores, pdrops, ambiguous, recog, n_def, col_pattern_table,
                 pp_buckets=None):
    import datetime as _dt
    from trend import _CSS, _esc  # shared look with report.html / SUMMARY.html
    try:
        from report import _FIELD_KO  # bilingual column labels (SSOT in report.py)
    except Exception:
        _FIELD_KO = {}

    def ko(col):  # 한글 우선(잘 보이게) + 영문 식별자 보조: "품명 (itemName)"
        k = _FIELD_KO.get(col)
        return (f"<b>{_esc(k)}</b> <span class='muted' style='font-size:12px'>({_esc(col)})</span>"
                if k else _esc(col))

    gen = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    fS = sum(s["fScored"] for s in scores); fM = sum(s["fMatch"] for s in scores)
    cS = sum(s["cScored"] for s in scores); cM = sum(s["cMatch"] for s in scores)
    n_pd, n_af, n_rc = len(pdrops), len(ambiguous), len(recog)
    rec_pct = (100 * n_pd / n_def) if n_def else 0
    is_replay = compare_dir != "compare"
    src_label = "수정 후 (로컬 replay)" if is_replay else "AWS run 기준 (수정 전)"

    extra = ("table.sortable th:hover{color:var(--fg)}"
             ".acc-lo{background:#ffeef0}.acc-mid{background:#fff8e6}.acc-ok{background:#e9f7ec}"
             ".free{color:var(--link);font-weight:600}.fallback{color:var(--warn);font-weight:600}"
             ".kpis{display:flex;flex-wrap:wrap;gap:10px;max-width:1600px;margin:0 auto}"
             ".kpi{flex:1;min-width:130px;background:var(--card);border:1px solid var(--line);"
             "border-radius:10px;padding:12px 16px;box-shadow:0 1px 2px rgba(27,31,36,.04)}"
             ".kpi .lab{color:var(--muted);font-size:12px}.kpi b{font-size:24px;display:block;margin:2px 0}"
             ".kpi .sub{color:var(--muted);font-size:11.5px}")

    P = ["drop", "mislocate", "wrongpick"]
    PAT_KO = {"drop": "누락(drop)", "mislocate": "오배치(mislocate)", "wrongpick": "오선택(wrongpick)"}
    pat_th = "".join(f"<th data-num='1'>{PAT_KO[p]}</th>" for p in P)

    def acc_cls(a):
        if a is None: return ""
        return "acc-lo" if a < 0.5 else ("acc-mid" if a < 0.8 else "acc-ok")

    def acc_td(match, scored, a):
        v = "" if a is None else f"{a:.4f}"
        return f"<td data-v='{v}' class='{acc_cls(a)}'>{_pct(match, scored)}</td>"

    H = ["<!doctype html><html lang='ko'><head><meta charset='utf-8'>",
         "<meta name='viewport' content='width=device-width,initial-scale=1'>",
         f"<title>Parser-drop 요약 - {_esc(run_label)}</title><style>", _CSS, extra,
         "</style></head><body>",
         f"<div class='head'><h1>Parser-drop 요약 "
         f"<span class='muted' style='font-size:14px'>({_esc(run_label)})</span></h1>"
         f"<div class='gen'>생성 {gen} · {_esc(src_label)}</div></div>",
         "<div class='note'>"
         "<div class='row'><b>parser-drop</b> = GT 값이 OCR 출력엔 있는데 파서가 떨군 것 "
         "<b>(회수 가능)</b> · <b>recognition</b> = OCR이 글자 자체를 못 읽음(OCR 바운드, 파서 대상 아님)</div>"
         "<div class='row'><b>패턴</b> — <b>누락(drop)</b>: 칸 통째 누락 · "
         "<b>오배치(mislocate)</b>: 값이 엉뚱한 컬럼에 배치 · "
         "<b>오선택(wrongpick)</b>: 정답 라인 있는데 다른 걸 선택</div>"
         "<div class='row'><b>추출경로</b> — <b class='free'>free</b>(비정형 룰 파서) / "
         "<b class='fallback'>fallback</b>(레퍼런스 보조, free 게이트 탈락 시)</div></div>"]

    # KPI cards
    H.append("<div class='kpis'>"
             f"<div class='kpi'><div class='lab'>전체 필드</div><b>{_pct(fM,fS)}</b>"
             f"<div class='sub'>{fM}/{fS}</div></div>"
             f"<div class='kpi'><div class='lab'>전체 셀</div><b>{_pct(cM,cS)}</b>"
             f"<div class='sub'>{cM}/{cS}</div></div>"
             f"<div class='kpi'><div class='lab'>결함</div><b>{n_def}</b>"
             f"<div class='sub'>불일치+누락</div></div>"
             f"<div class='kpi'><div class='lab'>parser-drop</div><b>{n_pd}</b>"
             f"<div class='sub'>OCR 읽음 · 회수가능 {rec_pct:.0f}%</div></div>"
             f"<div class='kpi'><div class='lab'>ambiguous_fuzzy</div><b>{n_af}</b>"
             f"<div class='sub'>fuzzy-only · pending</div></div>"
             f"<div class='kpi'><div class='lab'>recognition</div><b>{n_rc}</b>"
             f"<div class='sub'>OCR 바운드</div></div></div>")

    # parser-drop by extraction path (the prioritization axis)
    path_agg = defaultdict(lambda: defaultdict(int))
    path_by_src = {s["src"]: (s["path"] or "?") for s in scores}
    for d in pdrops:
        path_agg[path_by_src.get(d["src"], "?")][d["pattern"]] += 1
    H.append("<section><h2>추출경로별 parser-drop <span class='muted'>(우선순위 축)</span></h2>"
             "<table class='sortable'><thead><tr><th>경로</th>" + pat_th
             + "<th data-num='1'>합계</th></tr></thead><tbody>")
    for path in ("fallback", "free"):
        pats = path_agg.get(path, {})
        tot = sum(pats.values())
        cls = "fallback" if path == "fallback" else "free"
        H.append(f"<tr><td><b class='{cls}'>{path}</b></td>"
                 + "".join(f"<td data-v='{pats.get(p,0)}'>{pats.get(p,0)}</td>" for p in P)
                 + f"<td data-v='{tot}'><b>{tot}</b></td></tr>")
    H.append("</tbody></table></section>")

    # per-sample scores (sortable)
    H.append("<section><h2>샘플별 점수 <span class='muted'>(약한 순 · 컬럼 클릭=정렬)</span></h2>"
             "<table class='sortable'><thead><tr><th>이미지</th><th>구분</th><th>추출경로</th>"
             "<th data-num='1'>필드 정확도</th><th data-num='1'>셀 정확도</th></tr></thead><tbody>")
    for s in sorted(scores, key=lambda s: (s["fieldAcc"] is None, s["fieldAcc"] or 0)):
        pth = s["path"] or ""
        clean_label = "미분류" if s["clean"] is None else ("정상" if s["clean"] else "변주")
        H.append(f"<tr><td>{_esc(s['src'])}</td>"
                 f"<td>{clean_label}</td>"
                 f"<td><span class='{pth}'>{_esc(pth)}</span></td>"
                 + acc_td(s['fMatch'], s['fScored'], s['fieldAcc'])
                 + acc_td(s['cMatch'], s['cScored'], s['cellAcc']) + "</tr>")
    H.append("</tbody></table></section>")

    # parser-drop class tables (ALL + clean/variant split)
    html_scopes = [("전체", pdrops)]
    if any(d["clean"] is not None for d in pdrops):
        html_scopes.extend((("정상 원본", [d for d in pdrops if d["clean"] is True]),
                            ("변주(각도)", [d for d in pdrops if d["clean"] is False])))
    for scope, rows in html_scopes:
        agg = col_pattern_table(rows)
        ordered = sorted(agg.items(), key=lambda kv: -sum(kv[1].values()))
        H.append(f"<section><h2>컬럼 × 패턴 — {scope} <span class='muted'>(n={len(rows)} · 클릭=정렬)</span></h2>"
                 "<table class='sortable'><thead><tr><th>컬럼</th>" + pat_th
                 + "<th data-num='1'>합계</th></tr></thead><tbody>")
        for col, pats in ordered:
            tot = sum(pats.values())
            H.append(f"<tr><td>{ko(col)}</td>"
                     + "".join(f"<td data-v='{pats.get(p,0)}'>{pats.get(p,0)}</td>" for p in P)
                     + f"<td data-v='{tot}'><b>{tot}</b></td></tr>")
        H.append("</tbody></table></section>")

    # Fuzzy-only evidence is intentionally not mixed into either actionable
    # parser work or confirmed OCR work.
    aagg = defaultdict(int)
    for d in ambiguous:
        aagg[d["column"]] += 1
    H.append("<section><h2>ambiguous_fuzzy <span class='muted'>(fuzzy-only · pending row/bbox proof)</span></h2>"
             "<table class='sortable'><thead><tr><th>column</th><th data-num='1'>count</th>"
             "</tr></thead><tbody>")
    for col, n in sorted(aagg.items(), key=lambda kv: -kv[1]):
        H.append(f"<tr><td>{ko(col)}</td><td data-v='{n}'>{n}</td></tr>")
    H.append("</tbody></table></section>")

    # recognition by column
    ragg = defaultdict(int)
    for d in recog:
        ragg[d["column"]] += 1
    H.append("<section><h2>recognition <span class='muted'>(OCR 바운드 · 파서 대상 아님)</span></h2>"
             "<table class='sortable'><thead><tr><th>컬럼</th><th data-num='1'>건수</th>"
             "</tr></thead><tbody>")
    for col, n in sorted(ragg.items(), key=lambda kv: -kv[1]):
        H.append(f"<tr><td>{ko(col)}</td><td data-v='{n}'>{n}</td></tr>")
    H.append("</tbody></table></section>")
    H.append(_render_preprocess_section(pp_buckets, _esc))
    H.append(_SORT_JS)
    H.append("</body></html>")
    return "\n".join(H)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None, help="run dir under runs/ (default: latest study run)")
    ap.add_argument("--testset", default="invoice_study")
    ap.add_argument("--compare-dir", default="compare",
                    help="which scorecard dir to read: 'compare' (the run's) or "
                         "'replay_compare' (a local parser-edit re-score)")
    args = ap.parse_args()

    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else C.latest_run(args.testset)
    if not run_dir or not os.path.isdir(run_dir):
        print(f"no run dir ({run_dir})"); return 2
    cmp_dir, snap_dir = os.path.join(run_dir, args.compare_dir), os.path.join(run_dir, "snapshots")
    if not os.path.isdir(cmp_dir):
        print(f"no {args.compare_dir}/ in {run_dir}"); return 2
    has_snap = os.path.isdir(snap_dir)
    run_meta = _load_run_meta(run_dir)
    recorded_scope = _recorded_scope(run_meta)

    defects: list[dict] = []
    scores: list[dict] = []   # per-sample field/cell accuracy for the HTML score table
    raw_master_cross = {
        "counts": defaultdict(int),
        "protectedRows": defaultdict(list),
    }
    excluded_out_of_scope = 0
    for f in sorted(os.listdir(cmp_dir)):
        if not f.endswith(".json"):
            continue
        src = f[:-5]
        if recorded_scope is not None and src not in recorded_scope:
            excluded_out_of_scope += 1
            continue
        cmp = json.load(open(os.path.join(cmp_dir, f), encoding="utf-8"))
        snap = None
        sp = os.path.join(snap_dir, f)
        if has_snap and os.path.exists(sp):
            snap = json.load(open(sp, encoding="utf-8"))
        clean = _clean_classification(src, run_meta)
        sample_defects = classify_sample(src, cmp, snap)
        for defect in sample_defects:
            defect["clean"] = clean
        defects += sample_defects
        _raw_master_cross_add(raw_master_cross, src, cmp)
        fc, tc = cmp["fields"]["counts"], cmp["table"]["cellCounts"]
        scores.append({
            "src": src, "clean": clean, "path": cmp.get("extractionPath"),
            "fScored": fc["scored"], "fMatch": fc["match"],
            "cScored": tc["scored"], "cMatch": tc["match"],
            "fieldAcc": cmp["fields"].get("fieldAccuracy"),
            "cellAcc": cmp["table"].get("cellAccuracy"),
        })

    # --- aggregate ---
    pdrops = [d for d in defects if d["class"] == "parser_drop"]
    ambiguous = [d for d in defects if d["class"] == "ambiguous_fuzzy"]
    recog = [d for d in defects if d["class"] == "recognition"]
    n_def = len(defects)
    if len(pdrops) + len(ambiguous) + len(recog) != n_def:
        raise RuntimeError("defect taxonomy does not partition all defects")

    def col_pattern_table(rows):
        agg: dict = defaultdict(lambda: defaultdict(int))
        for d in rows:
            agg[d["column"]][d["pattern"]] += 1
        return agg

    lines = []
    lines.append(f"# Parser-drop classification — {os.path.relpath(run_dir, C.RUNS_DIR)}")
    lines.append("")
    lines.append(f"Defects scored (mismatch|ext_missing): **{n_def}**  "
                 f"|  parser-drop (OCR read it, recoverable): **{len(pdrops)}**  "
                 f"|  ambiguous_fuzzy (fuzzy-only, pending): **{len(ambiguous)}**  "
                 f"|  recognition (OCR-bound): **{len(recog)}**"
                 + ("" if has_snap else "  _(NO SNAPSHOTS — class=no_snapshot)_"))
    pct = (100 * len(pdrops) / n_def) if n_def else 0
    lines.append(f"Parser-recoverable share of defects: **{pct:.1f}%**")
    lines.append("")
    if recorded_scope is not None:
        lines.append(f"Evaluation scope: **run_meta.ran {len(recorded_scope)} sources**; "
                     f"out-of-scope compare files excluded: **{excluded_out_of_scope}**")
        lines.append("")

    cross_counts = raw_master_cross["counts"]
    lines.append("## Raw itemName × master itemNameMaster transitions")
    lines.append("")
    lines.append("| transition | rows |")
    lines.append("|---|--:|")
    for key in ("rawWrong_masterCorrect", "rawWrong_masterWrongOrMissing",
                "rawCorrect_masterCorrect", "rawCorrect_masterWrong",
                "rawCorrect_masterMissing"):
        lines.append(f"| {key} | **{cross_counts.get(key, 0)}** |")
    lines.append("")
    lines.append("Regression gates use the persisted row identities, not fixed bin counts: "
                 "a successful raw fix may legitimately move a protected row between bins.")
    lines.append("")

    classified_clean_angle = any(d["clean"] is not None for d in pdrops)
    scope_rows = []
    if classified_clean_angle:
        scope_rows.extend((("CLEAN originals", [d for d in pdrops if d["clean"] is True]),
                           ("ANGLE variants", [d for d in pdrops if d["clean"] is False])))
    else:
        lines.append("Clean/angle split: **unavailable for this run**. The legacy six-file "
                     "study filename list is not applied to thin data.")
        lines.append("")
    scope_rows.append(("ALL", pdrops))
    for scope_name, rows in scope_rows:
        agg = col_pattern_table(rows)
        ordered = sorted(agg.items(), key=lambda kv: -sum(kv[1].values()))
        lines.append(f"## Parser-drops by column × pattern — {scope_name}  (n={len(rows)})")
        lines.append("")
        lines.append("| column | drop | mislocate | wrongpick | total |")
        lines.append("|---|--:|--:|--:|--:|")
        for col, pats in ordered:
            tot = sum(pats.values())
            lines.append(f"| {col} | {pats.get('drop',0)} | {pats.get('mislocate',0)} "
                         f"| {pats.get('wrongpick',0)} | **{tot}** |")
        lines.append("")

    # recognition (OCR-bound) by column — so we don't mistake it for parser work
    aagg: dict = defaultdict(int)
    for d in ambiguous:
        aagg[d["column"]] += 1
    lines.append("## Ambiguous fuzzy-only evidence by column")
    lines.append("")
    lines.append("| column | count |")
    lines.append("|---|--:|")
    for col, n in sorted(aagg.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {col} | {n} |")
    lines.append("")

    ragg: dict = defaultdict(int)
    for d in recog:
        ragg[d["column"]] += 1
    lines.append("## Recognition (OCR-bound, NOT parser) by column")
    lines.append("")
    lines.append("| column | count |")
    lines.append("|---|--:|")
    for col, n in sorted(ragg.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {col} | {n} |")
    lines.append("")

    # --- preprocessing diagnosis (scale-actionable buckets) ---
    pp_buckets = _preprocess_buckets(scores, recog, os.path.join(run_dir, "samples"))
    if pp_buckets:
        cov = pp_buckets["coverage"]
        lines.append(f"## Preprocessing diagnosis  (telemetry {cov['withTelemetry']}/{cov['total']} samples)")
        lines.append("")
        lines.append("recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).")
        lines.append("")
        for title, key, base in (("Orientation", "orientation", "미적용(0°)"),
                                 ("Deskew", "deskew", "미적용"),
                                 ("Warp", "warp", "영역≥90%")):
            rows = sorted(pp_buckets[key], key=lambda r: -(r["recogRate"] or 0))
            if not rows:
                continue
            base_rr = next((r["recogRate"] for r in rows if r["bucket"] == base), None)
            lines.append(f"### {title}")
            lines.append("")
            lines.append("| condition | n | cellAcc | recognition% | Δ vs base |")
            lines.append("|---|--:|--:|--:|--:|")
            for r in rows:
                ca = "n/a" if r["cellAcc"] is None else f"{r['cellAcc']*100:.1f}%"
                rr = "n/a" if r["recogRate"] is None else f"{r['recogRate']*100:.1f}%"
                if r["bucket"] == base or base_rr is None or r["recogRate"] is None:
                    dlt = "—"
                else:
                    d = r["recogRate"] - base_rr
                    dlt = f"{'+' if d>=0 else ''}{d*100:.1f}pp"
                lines.append(f"| {r['bucket']} | {r['n']} | {ca} | {rr} | {dlt} |")
            lines.append("")

    md = "\n".join(lines)
    suffix = "" if args.compare_dir == "compare" else "_" + args.compare_dir
    run_label = os.path.relpath(run_dir, C.RUNS_DIR)
    out_md = os.path.join(run_dir, f"PARSER_DROP_CLASSIFY{suffix}.md")
    out_json = os.path.join(run_dir, f"PARSER_DROP_CLASSIFY{suffix}.json")
    out_html = os.path.join(run_dir, f"PARSER_DROP_CLASSIFY{suffix}.html")
    open(out_md, "w", encoding="utf-8").write(md)
    json.dump({
        "schemaVersion": "parser-drop-classification.v2",
        "runDir": run_dir,
        "hasSnapshots": has_snap,
        "summary": {
            "defects": n_def,
            "parserDropConfirmed": len(pdrops),
            "ambiguousFuzzy": len(ambiguous),
            "recognitionConfirmed": len(recog),
            "scopeSourceCount": len(recorded_scope) if recorded_scope is not None else len(scores),
            "outOfScopeCompareFilesExcluded": excluded_out_of_scope,
        },
        "rawMasterCross": {
            "counts": dict(raw_master_cross["counts"]),
            "protectedRows": dict(raw_master_cross["protectedRows"]),
        },
        # per-sample field/cell accuracy — persisted so a batch-level combiner
        # (local_summary.py) can compute KPIs without re-reading every compare/.
        "scores": scores,
        "preprocess": pp_buckets,   # scale-actionable preprocessing diagnosis buckets
        "defects": defects,
    }, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(out_html, "w", encoding="utf-8").write(
        _render_html(run_label, args.compare_dir, scores, pdrops, ambiguous, recog,
                     n_def, col_pattern_table, pp_buckets=pp_buckets))

    # Auto-embed the replay progress history (git-reconstructed) at the top of the
    # HTML, so running just replay_compare + parser_drop_classify shows the trend
    # too — no separate command. Best-effort: never break the classifier.
    if args.compare_dir == "replay_compare":
        try:
            from replay_summary import append_history, inject_html
            _hist = append_history(run_label)   # appends a row (only if KPIs changed)
            if _hist:
                inject_html(out_html, _hist)
        except Exception as _e:
            print(f"[replay_summary skipped] {_e}")

    # Batch-level combined view: if this run sits inside a run_all --all batch
    # (runs/<batch>/<sub>/), regenerate LOCAL_SUMMARY so the existing loop
    # (replay_compare -> parser_drop_classify) auto-produces the combined
    # study+thin page with NO extra command. Merge-only (refresh=False) reads the
    # per-testset JSONs already on disk and never re-invokes this classifier
    # (no recursion). Flat single runs (parent == runs/) are not batches -> skip.
    # Best-effort: never break the classifier.
    try:
        batch_dir = os.path.dirname(run_dir)
        if os.path.abspath(batch_dir) != os.path.abspath(C.RUNS_DIR):
            from local_summary import build as _ls_build
            _out = _ls_build(batch_dir, args.compare_dir, refresh=False)
            if _out:
                print(f"[written] {_out}  <- 로컬 합산뷰")
    except Exception as _e:
        print(f"[local_summary skipped] {_e}")

    # console: ascii-safe summary (cp949 consoles mangle hangul; full table in .md/.html)
    sys.stdout.reconfigure(errors="replace")
    print(md)
    print(f"\n[written] {out_md}\n[written] {out_json}\n[written] {out_html}  <- 브라우저로 열기")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
