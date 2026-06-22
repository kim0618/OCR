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

    def emit(loc, col, vtype, status, gtn, extn, yband=None):
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
            "class": cls, "pattern": pattern, "ocrHow": how,
        })

    for label, info in fields["perField"].items():
        if info["status"] in ("mismatch", "ext_missing"):
            emit(f"field:{label}", label, _field_type(label), info["status"],
                 info["gtNorm"], info["extNorm"])
    for row in table["rows"]:
        yband = _row_yband(row, tokens_xy) if tokens_xy else None
        for ck, cell in row["cells"].items():
            if cell["status"] in ("mismatch", "ext_missing"):
                emit(f"row{row['rowIndex']}:{ck}", ck, _cell_type(ck),
                     cell["status"], cell["gtNorm"], cell["extNorm"], yband=yband)
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


def _render_html(run_label, compare_dir, scores, pdrops, ambiguous, recog, n_def, col_pattern_table):
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
        H.append(f"<tr><td>{_esc(s['src'])}</td>"
                 f"<td>{'정상' if s['clean'] else '변주'}</td>"
                 f"<td><span class='{pth}'>{_esc(pth)}</span></td>"
                 + acc_td(s['fMatch'], s['fScored'], s['fieldAcc'])
                 + acc_td(s['cMatch'], s['cScored'], s['cellAcc']) + "</tr>")
    H.append("</tbody></table></section>")

    # parser-drop class tables (ALL + clean/variant split)
    for scope, rows in (("전체", pdrops),
                        ("정상 원본", [d for d in pdrops if d["clean"]]),
                        ("변주(각도)", [d for d in pdrops if not d["clean"]])):
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

    defects: list[dict] = []
    scores: list[dict] = []   # per-sample field/cell accuracy for the HTML score table
    for f in sorted(os.listdir(cmp_dir)):
        if not f.endswith(".json"):
            continue
        src = f[:-5]
        cmp = json.load(open(os.path.join(cmp_dir, f), encoding="utf-8"))
        snap = None
        sp = os.path.join(snap_dir, f)
        if has_snap and os.path.exists(sp):
            snap = json.load(open(sp, encoding="utf-8"))
        defects += classify_sample(src, cmp, snap)
        fc, tc = cmp["fields"]["counts"], cmp["table"]["cellCounts"]
        scores.append({
            "src": src, "clean": src in CLEAN, "path": cmp.get("extractionPath"),
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

    for scope, rows in (("CLEAN originals", [d for d in pdrops if d["clean"]]),
                        ("ANGLE variants", [d for d in pdrops if not d["clean"]]),
                        ("ALL", pdrops)):
        agg = col_pattern_table(rows)
        ordered = sorted(agg.items(), key=lambda kv: -sum(kv[1].values()))
        lines.append(f"## Parser-drops by column × pattern — {scope}  (n={len(rows)})")
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
        },
        "defects": defects,
    }, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(out_html, "w", encoding="utf-8").write(
        _render_html(run_label, args.compare_dir, scores, pdrops, ambiguous, recog,
                     n_def, col_pattern_table))

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

    # console: ascii-safe summary (cp949 consoles mangle hangul; full table in .md/.html)
    sys.stdout.reconfigure(errors="replace")
    print(md)
    print(f"\n[written] {out_md}\n[written] {out_json}\n[written] {out_html}  <- 브라우저로 열기")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
