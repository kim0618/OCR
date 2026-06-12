"""report - render runs/<ts>/report.md from metrics.json + compare/*.json.

Human-facing: hypothesis banner (small sample), overall + free/fallback, per-field
table (weakest first), bucket totals, slices, and failing GT-vs-extraction examples
side by side.

CLI: python eval/report.py [--ts <run_ts>] [--examples N]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from typing import Any

import contract as C


def _pct(a: float | None) -> str:
    return "n/a" if a is None else f"{a * 100:.1f}%"


def _base_variant_split(compares: list[dict[str, Any]]) -> dict[str, Any] | None:
    """compares 를 base(정상문서)/변주(각도·회전 사진)로 갈라 셀 정확도를 가중 집계.

    전체 평균은 둘을 섞어 전처리 작업의 효과·회귀를 가린다(변주가 base를 끌어내림).
    변주가 하나도 없으면(예: thin) None → 블록 생략. 변주 식별 SSOT=contract._VARIANT_RE.
    """
    groups = {"base": {"n": 0, "match": 0, "scored": 0},
              "변주": {"n": 0, "match": 0, "scored": 0}}
    for d in compares:
        stem = os.path.splitext(d["sourceFile"])[0]
        g = "변주" if C._VARIANT_RE.match(stem) else "base"
        groups[g]["n"] += 1
        for row in d.get("table", {}).get("rows", []):
            for cell in row.get("cells", {}).values():
                st = cell.get("status")
                if st == "match":
                    groups[g]["match"] += 1
                    groups[g]["scored"] += 1
                elif st in ("mismatch", "ext_missing"):
                    groups[g]["scored"] += 1
    if groups["변주"]["n"] == 0:
        return None
    for v in groups.values():
        v["accuracy"] = (v["match"] / v["scored"]) if v["scored"] else None
    return groups


# 한글 표기 매핑 - 사람이 읽는 리포트용. 데이터 식별자(필드키 등)는 영문 유지.
_STATUS_KO = {"match": "일치", "mismatch": "불일치", "ext_missing": "추출누락", "gt_empty": "정답비움"}
_BUCKET_KO = {"recognition": "인식오류", "structure": "구조오류",
              "layout": "컬럼밀림", "preprocessing": "전처리"}
_SLICE_KO = {"extractionPath": "추출경로(free/fallback)", "supplier": "공급자별",
             "layout": "레이아웃(단일행/다행)", "qualityTag": "품질태그",
             "profile": "프로파일(rich/thin)"}

# 필드키 → 한글 이름 (필드별 정확도 표 + 실패 예시에 표시)
_FIELD_KO: dict[str, str] = {
    # 공급자
    "supplierCompany":        "공급자 상호",
    "supplierTaxId":          "공급자 사업자번호",
    "supplierBizNumber":      "공급자 사업자번호",
    "supplierRepresentative": "공급자 대표자",
    "supplierAddress":        "공급자 주소",
    # 공급받는자
    "buyerCompany":           "공급받는자 상호",
    "buyerTaxId":             "공급받는자 사업자번호",
    "buyerBizNumber":         "공급받는자 사업자번호",
    "buyerRepresentative":    "공급받는자 대표자",
    "buyerAddress":           "공급받는자 주소",
    # 문서 공통
    "issueDate":              "작성일자",
    "supplyAmount":           "공급가액",
    "taxAmount":              "세액",
    "totalAmount":            "합계금액",
    "cumulativeAmount":       "누계",
    "totalQuantity":          "총수량",
    # thin 추가
    "discountAmount":         "할인액",
    "documentNumber":         "문서번호",
    "taxType":                "과세유형",
    # 표 셀
    "itemName":               "품명",
    "spec":                   "규격",
    "productCode":            "품목코드",
    "lotNo":                  "LOT번호",
    "expiryDate":             "유효기간",
    "quantity":               "수량",
    "unitPrice":              "단가",
    "amount":                 "금액",
    "manufacturingNo":        "제조번호",
}


def _ko_field(key: str) -> str:
    """영문 필드키에 한글명 병기: 'supplierCompany (공급자 상호)'"""
    ko = _FIELD_KO.get(key)
    return f"{key} ({ko})" if ko else key


def _ko_status(s: str) -> str:
    return _STATUS_KO.get(s, s)


# 표준 컬럼 동의어 매핑 — "부가세/VAT 는 세액(taxAmount) 컬럼에 넣는다" 같은 규칙.
# SSOT는 추출기(invoice_statement._EXPECTED_COLUMN_ALIASES). 여기서 직접 읽어
# 표시만 하므로(리포트 read-only) 드리프트 없음. 표시 순서/한글명은 아래 고정.
_ALIAS_DISPLAY_ORDER = [
    ("supplyAmount", "공급가액"), ("taxAmount", "세액"),
    ("totalAmount", "합계금액"), ("amount", "금액"),
    ("itemName", "품명"), ("spec", "규격"), ("itemCode", "품목코드"),
    ("lotNo", "LOT번호"), ("expiryDate", "유효기간"),
    ("manufacturingNo", "제조번호"), ("quantity", "수량"), ("unitPrice", "단가"),
]


def _column_alias_rows() -> list[tuple[str, str, list[str]]]:
    """[(한글명, 표준키, [OCR 변형들])] — 추출기 SSOT에서 읽음. 실패 시 빈 리스트."""
    try:
        from extractors.invoice_statement import _EXPECTED_COLUMN_ALIASES as A
    except Exception:
        return []
    out = []
    for key, ko in _ALIAS_DISPLAY_ORDER:
        variants = A.get(key) or []
        if variants:
            out.append((ko, key, list(variants)))
    return out


def _load(run_dir: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metrics = json.load(open(os.path.join(run_dir, "metrics.json"), encoding="utf-8"))
    compares = [json.load(open(p, encoding="utf-8"))
                for p in sorted(glob.glob(os.path.join(run_dir, "compare", "*.json")))]
    return metrics, compares


def render_report(run_dir: str, examples: int = 12) -> str:
    m, compares = _load(run_dir)
    L: list[str] = []
    L.append(f"# 평가 리포트 - run {m['runTs']}  (testset={m.get('testset', '-')})")
    L.append("")
    L.append(f"> ⚠️ **가설이지 판정이 아님.** {m['sampleCount']}장 = 인프라가 도는지 검증용이지"
             f" 정확도 합격 판정이 아님(계획 §8). 숫자는 어느 룰을 보강할지 가리키는 신호일 뿐,"
             f" 릴리스 합격선으로 쓰지 말 것.")
    L.append("")

    of, oc = m["overall"]["field"], m["overall"]["cell"]
    ofm, ocm = m["overall"].get("fieldMacro") or {}, m["overall"].get("cellMacro") or {}
    L.append("## 전체 정확도 (Overall)")
    L.append("")
    L.append("| 항목 | 채점수 | 일치 | micro(항목가중) | macro(샘플평균) |")
    L.append("|---|---:|---:|---:|---:|")
    L.append(f"| 필드(스칼라 상단값) | {of['scored']} | {of['match']} | {_pct(of['accuracy'])} | {_pct(ofm.get('accuracy'))} |")
    L.append(f"| 셀(표 안 값) | {oc['scored']} | {oc['match']} | {_pct(oc['accuracy'])} | {_pct(ocm.get('accuracy'))} |")
    L.append("> 채점수 = 정답이 비어있지 않아 실제로 채점된 칸 수. **micro** = 일치÷채점수(전체 칸 가중,"
             " 큰 표가 지배). **macro** = 샘플당 정확도의 평균(샘플 동등 가중). 둘이 벌어지면"
             " 큰 표가 평균을 끌어올리는/내리는 것 → 수천장에선 macro 가 '핵심 샘플 다수 깨짐'을 더 정직히 드러냄.")
    L.append("")

    bv = _base_variant_split(compares)
    if bv:
        L.append("## base(정상문서) vs 변주(각도사진) 셀 정확도")
        L.append("")
        L.append("| 그룹 | 장수 | 셀 채점 | 일치 | 셀 정확도 |")
        L.append("|---|---:|---:|---:|---:|")
        for g in ("base", "변주"):
            v = bv[g]
            L.append(f"| {g} | {v['n']} | {v['scored']} | {v['match']} | {_pct(v['accuracy'])} |")
        L.append("> base = 정상 촬영(회귀 안전망) · 변주 = 각도/회전 사진. 전체 평균은 둘을 섞어"
                 " 전처리 작업의 효과·회귀를 가리므로 분리해서 본다.")
        L.append("")

    L.append("## 추출경로별 (free=우리 비정형룰 / fallback=보조 추출기)")
    L.append("")
    L.append("| 경로 | 필드 정확도 | 셀 정확도 |")
    L.append("|---|---:|---:|")
    for p, v in m["byPath"].items():
        L.append(f"| {p} | {_pct(v['field']['accuracy'])} | {_pct(v['cell']['accuracy'])} |")
    L.append("")

    # 이미지별 점수판 - 100장 규모에서 "어느 장이 약한지" 한눈에. 약한 순 정렬 = 고칠 우선순위.
    L.append(f"## 이미지별 결과 (약한 순, {len(compares)}장)")
    L.append("")
    L.append("| 이미지 | 경로 | 필드 | 셀 | 불일치 | 누락 | 행 GT/추출 | 인식 | 구조 |")
    L.append("|---|---|---:|---:|---:|---:|---|---:|---:|")

    def _weak_key(d: dict[str, Any]) -> float:
        a = d["fields"]["fieldAccuracy"]
        return a if a is not None else 1.0  # 채점필드 없는 장은 맨 아래로

    for d in sorted(compares, key=_weak_key):
        fc = d["fields"]["counts"]
        tt = d["table"]
        bt = d["buckets"]["bucketTally"]
        rowflag = "" if tt["rowCountMatch"] else " ⚠"
        L.append(
            f"| {d['sourceFile']} | {d.get('extractionPath')} | {_pct(d['fields']['fieldAccuracy'])} "
            f"| {_pct(tt['cellAccuracy'])} | {fc['mismatch']} | {fc['ext_missing']} "
            f"| {tt['rowCountGt']}/{tt['rowCountExt']}{rowflag} | {bt['recognition']} | {bt['structure']} |"
        )
    L.append("> 위에서부터 약한 장 = 먼저 열어볼 곳. `행 GT/추출`의 ⚠ = 행 수 불일치(추출기가 행을 놓침/지어냄).")
    L.append("")

    ds = m.get("difficultySplit") or {}
    if ds:
        L.append("## 난이도 분할 (difficultySplit, 프로파일별)")
        L.append("")
        L.append("| 그룹 | 채점수 | 일치 | 정확도 |")
        L.append("|---|---:|---:|---:|")
        _g_ko = {"difficult": "어려움(difficult)", "normal": "보통(normal)"}
        for g in ("difficult", "normal"):
            v = ds.get(g, {})
            L.append(f"| {_g_ko[g]} | {v.get('scored', 0)} | {v.get('match', 0)} | {_pct(v.get('accuracy'))} |")
        L.append("> `어려움` = rich는 사람이 손본(edited) 필드, thin은 war 저신뢰 필드"
                 "(supplierCompany/taxType). **룰 보강의 핵심 타깃.**")
        L.append("")

    cov = m.get("coverage") or {}
    if cov:
        L.append("## 커버리지 (분모 2개)")
        L.append("")
        L.append(f"- 정답 있는 필드(채점대상): **{cov.get('gtPresent', 0)}**  ·  맞힘: "
                 f"**{cov.get('matched', 0)}**  ·  채점 정확도: **{_pct(cov.get('gradedAccuracy'))}**")
        L.append(f"- 시도했지만 틀림: **{cov.get('extAttemptedMiss', 0)}**  ·  "
                 f"**아예 시도 안 함**(키 자체 없음 - 신규3 정직한 누락): **{cov.get('extNotAttempted', 0)}**"
                 f"  ·  시도율: **{_pct(cov.get('attemptRate'))}**")
        L.append("> *추출기가 시도했는데 틀린 것* 과 *애초에 그 필드를 안 뽑은 것*(discountAmount/"
                 "documentNumber/taxType - 데이터 오기 전까지)을 구분.")
        L.append("")

    es = m["editedSplit"]
    L.append("## 사람보정(edited) vs 원본 필드 (rich 전용)")
    L.append("")
    L.append("| 그룹 | 채점수 | 일치 | 정확도 |")
    L.append("|---|---:|---:|---:|")
    _e_ko = {"edited": "사람보정함(edited)", "nonEdited": "원본그대로(nonEdited)"}
    for g in ("edited", "nonEdited"):
        v = es[g]
        L.append(f"| {_e_ko[g]} | {v['scored']} | {v['match']} | {_pct(v['accuracy'])} |")
    L.append("> `edited=true` 필드의 불일치 = 사람이 교정한 정답과 추출값이 벌어진 곳"
             " → 예상된 지점이자 룰 보강 1순위.")
    L.append("")

    L.append("## 필드별 정확도 (약한 순)")
    L.append("")
    L.append("| 필드 | 채점수 | 일치 | 불일치 | 추출누락 | 정확도 |")
    L.append("|---|---:|---:|---:|---:|---:|")
    rows = sorted(
        m["perField"].items(),
        key=lambda kv: (kv[1]["accuracy"] if kv[1]["accuracy"] is not None else 1.0),
    )
    for label, v in rows:
        L.append(f"| {label} | {v['scored']} | {v['match']} | {v['mismatch']} "
                 f"| {v['ext_missing']} | {_pct(v['accuracy'])} |")
    L.append("> 필드명은 계약 식별자(영문)라 그대로 둠. 위에서부터 약한 필드 = 먼저 볼 곳.")
    L.append("")

    b = m["buckets"]
    L.append("## 결함 버킷 (heuristic - 문제의 *종류*)")
    L.append("")
    L.append(f"- 인식오류(recognition): **{b['recognition']}**  ·  구조오류(structure): **{b['structure']}**"
             f"  ·  컬럼밀림(layout): **{b['layout']}**  ·  전처리(preprocessing): **{b['preprocessing']}**")
    L.append("> 인식오류=OCR 글자 틀림(normalize/OCR) · 구조오류=값이 엉뚱한 필드/행(파서)"
             " · 컬럼밀림=표 안 열 어긋남 · 전처리=회전/기울기. **어느 종류가 많은지가 룰 보강 방향.**")
    L.append("")

    L.append("## 슬라이스 (부분집계)")
    L.append("")
    for sname, groups in m["slices"].items():
        L.append(f"### {_SLICE_KO.get(sname, sname)}")
        L.append("")
        L.append("| 그룹 | 채점수 | 일치 | 정확도 |")
        L.append("|---|---:|---:|---:|")
        for g, v in sorted(groups.items(), key=lambda kv: str(kv[0])):
            L.append(f"| {g} | {v['scored']} | {v['match']} | {_pct(v['accuracy'])} |")
        L.append("")

    L.append("## 실패 예시 (정답 GT vs 추출값)")
    L.append("")
    shown = 0
    for d in compares:
        src = d["sourceFile"]
        defects = []
        for label, info in d["fields"]["perField"].items():
            if info["status"] in ("mismatch", "ext_missing"):
                defects.append((f"field:{label}", info["status"], info["gt"], info["ext"]))
        for row in d["table"]["rows"]:
            for ck, cell in row["cells"].items():
                if cell["status"] in ("mismatch", "ext_missing"):
                    defects.append((f"row{row['rowIndex']}:{ck}", cell["status"], cell["gt"], cell["ext"]))
        if not defects:
            continue
        L.append(f"### {src} ({d.get('extractionPath')})")
        L.append("")
        L.append("| 위치 | 상태 | 정답(GT) | 추출값 |")
        L.append("|---|---|---|---|")
        for loc, st, gt, ext in defects:
            if shown >= examples:
                break
            gt_s = (gt or "").replace("|", "\\|")[:60]
            ext_s = (ext or "").replace("|", "\\|")[:60]
            L.append(f"| {loc} | {_ko_status(st)} | {gt_s} | {ext_s} |")
            shown += 1
        L.append("")
        if shown >= examples:
            L.append(f"_… {examples}개에서 잘림._")
            break

    text = "\n".join(L) + "\n"
    out_path = os.path.join(run_dir, "report.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return out_path


_SORT_JS = """<script>
function st(t,c,n){var b=t.tBodies[0],r=[].slice.call(b.rows);
 var d=(t.getAttribute('data-sc')==c&&t.getAttribute('data-sd')=='asc')?'desc':'asc';
 r.sort(function(a,e){var x=a.cells[c].getAttribute('data-v'),y=e.cells[c].getAttribute('data-v');
  if(x===null)x=a.cells[c].innerText; if(y===null)y=e.cells[c].innerText;
  if(n){x=parseFloat(x);y=parseFloat(y);x=isNaN(x)?-1:x;y=isNaN(y)?-1:y;}
  else{x=(''+x).toLowerCase();y=(''+y).toLowerCase();}
  return (x<y?-1:x>y?1:0)*(d=='asc'?1:-1);});
 r.forEach(function(x){b.appendChild(x);});t.setAttribute('data-sc',c);t.setAttribute('data-sd',d);}
document.querySelectorAll('table.sortable').forEach(function(t){
 [].slice.call(t.tHead.rows[0].cells).forEach(function(h,i){h.onclick=function(){st(t,i,h.dataset.num=='1');};});});
</script>"""


def render_report_html(run_dir: str, examples: int = 40) -> str:
    """report.html - browser report with a CLICK-TO-SORT per-image table.

    At 100s of images you sort by 필드/셀/불일치/버킷 to triage. Self-contained
    (inline CSS+JS, no external deps).
    """
    import datetime as _dt
    from trend import _CSS, _esc
    m, compares = _load(run_dir)
    gen = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    of, oc = m["overall"]["field"], m["overall"]["cell"]

    def acc_td(a) -> str:
        v = "" if a is None else f"{a:.4f}"
        return f"<td data-v='{v}'>{_pct(a)}</td>"

    def num_td(n) -> str:
        return f"<td data-v='{n}'>{n}</td>"

    testset = m.get("testset", "")
    is_thin = "thin" in testset
    _role_title = "학습데이터" if is_thin else "회귀 기준값"
    thin_field_suffix = (" <span class='muted'>(thin 추가: 할인액·문서번호·과세유형)</span>"
                         if is_thin else " <span class='muted'>(thin에서 할인액·문서번호·과세유형 추가됨)</span>")
    thin_cell_suffix = (" <span class='muted'>(thin 추가: 제조번호)</span>"
                        if is_thin else " <span class='muted'>(thin에서 제조번호 추가됨)</span>")

    H = ["<!doctype html><html lang='ko'><head><meta charset='utf-8'>",
         "<meta name='viewport' content='width=device-width,initial-scale=1'>",
         f"<title>평가 리포트 - {_role_title}</title><style>", _CSS,
         "table.sortable th{cursor:pointer;user-select:none}",
         "table.sortable th:hover{color:var(--fg)}",
         "details.aliasbox{max-width:1600px;margin:4px auto 0;background:var(--card);"
         "border:1px solid var(--line);border-radius:10px;padding:10px 16px}",
         "details.aliasbox summary{cursor:pointer;font-weight:600;font-size:13px}",
         "details.aliasbox summary:hover{color:var(--link)}",
         "details.aliasbox[open] summary{margin-bottom:8px}",
         "details.aliasbox td code{margin-right:4px}",
         "</style></head><body>",
         f"<div class='head'><h1>평가 리포트 - {_role_title}"
         f" <span class='muted' style='font-size:14px'>({_esc(m['runTs'])})</span></h1>"
         f"<div class='gen'>생성 {gen}</div></div>",
         f"<p class='note warn'>⚠️ 가설이지 판정 아님 · {m['sampleCount']}장 = 인프라 검증용,"
         " 릴리스 합격선 아님(계획 §8).</p>",
         "<div class='note'>"
         "<div class='row'><b>필드 정확도</b> = "
         "공급자 상호·사업자번호·대표자·주소 / "
         "공급받는자 상호·사업자번호·대표자·주소 / "
         "작성일자·공급가액·세액·합계금액·누계·총수량"
         + thin_field_suffix + "</div>"
         "<div class='row'><b>셀 정확도</b> = "
         "표 내부 행별 값 - 품명·규격·품목코드·LOT번호·유효기간·수량·단가·금액"
         + thin_cell_suffix + "</div>"
         "<div class='row'><b>추출경로</b> = "
         "<b>free</b>(비정형 룰 파서 - 표 구조를 스스로 추론) / "
         "<b>fallback</b>(레퍼런스 기반 보조 추출기 - free 게이트 탈락 시 사용)</div>"
         "<div class='row'><b>결함 버킷</b> = "
         "인식오류(OCR 글자 틀림) · "
         "구조오류(값이 엉뚱한 필드/행에 배치됨) · "
         "컬럼밀림(표 열 어긋남) · "
         "전처리(회전·기울기 보정 실패)</div>"
         "</div>"]

    # 표준 컬럼 동의어 매핑 (접이식) — 어떤 OCR 표기가 어느 표준컬럼으로 들어가나
    alias_rows = _column_alias_rows()
    if alias_rows:
        H.append("<details class='aliasbox'><summary>표준 컬럼 동의어 매핑 "
                 "<span class='muted'>(이 OCR 표기들은 같은 표준컬럼으로 들어감 — "
                 "예: 부가세·VAT → 세액)</span></summary>")
        H.append("<table><thead><tr><th>표준 컬럼</th><th>키</th>"
                 "<th>인식되는 OCR 표기</th></tr></thead><tbody>")
        for ko, key, variants in alias_rows:
            chips = " ".join(f"<code>{_esc(v)}</code>" for v in variants)
            H.append(f"<tr><td>{_esc(ko)}</td>"
                     f"<td><span class='muted' style='font-size:11.5px'>{_esc(key)}</span></td>"
                     f"<td>{chips}</td></tr>")
        H.append("</tbody></table>"
                 "<div class='legend'>출처: 추출기 <code>invoice_statement."
                 "_EXPECTED_COLUMN_ALIASES</code> (리포트가 직접 읽어 표시 — 규칙 바뀌면 자동 반영)</div>"
                 "</details>")

    # 전체 — micro(항목가중) / macro(샘플평균) 병기 (#5)
    ofm, ocm = m["overall"].get("fieldMacro") or {}, m["overall"].get("cellMacro") or {}
    H.append("<section><h2>전체 정확도</h2><table><thead><tr><th>항목</th><th>채점수</th>"
             "<th>일치</th><th>micro<br><span class='muted' style='font-weight:400'>항목가중</span></th>"
             "<th>macro<br><span class='muted' style='font-weight:400'>샘플평균</span></th></tr></thead><tbody>")
    H.append(f"<tr><td>필드(스칼라 상단값)</td><td>{of['scored']}</td><td>{of['match']}</td>"
             f"<td>{_pct(of['accuracy'])}</td><td>{_pct(ofm.get('accuracy'))}</td></tr>")
    H.append(f"<tr><td>셀(표 안 값)</td><td>{oc['scored']}</td><td>{oc['match']}</td>"
             f"<td>{_pct(oc['accuracy'])}</td><td>{_pct(ocm.get('accuracy'))}</td></tr>")
    H.append("</tbody></table>"
             "<div class='legend'><b>micro</b>=일치÷채점수(전체 칸 가중, 큰 표가 지배) · "
             "<b>macro</b>=샘플당 정확도의 평균(샘플 동등 가중). 둘이 벌어지면 큰 표가 평균을 좌우하는 것 — "
             "수천장에선 macro 가 '핵심 샘플 다수 깨짐'을 더 정직히 드러냄.</div></section>")

    # base vs 변주 분리 — 전체 평균이 가리는 전처리 효과/회귀를 드러냄
    bv = _base_variant_split(compares)
    if bv:
        H.append("<section><h2>base(정상문서) vs 변주(각도사진) 셀 정확도</h2>"
                 "<table><thead><tr><th>그룹</th><th>장수</th><th>셀 채점</th>"
                 "<th>일치</th><th>셀 정확도</th></tr></thead><tbody>")
        for g in ("base", "변주"):
            v = bv[g]
            H.append(f"<tr><td>{g}</td><td>{v['n']}</td><td>{v['scored']}</td>"
                     f"<td>{v['match']}</td><td>{_pct(v['accuracy'])}</td></tr>")
        H.append("</tbody></table>"
                 "<div class='legend'>base = 정상 촬영(회귀 안전망) · 변주 = 각도/회전 사진. "
                 "전체 평균은 둘을 섞어 전처리 작업의 효과·회귀를 가리므로 분리해서 본다.</div></section>")

    # 이미지별 점수판 (정렬) - 핵심
    H.append(f"<section><h2>이미지별 결과 <span class='muted'>({len(compares)}장 · 컬럼 클릭=정렬)</span></h2>")
    H.append("<table class='sortable'><thead><tr>"
             "<th title='파일명'>이미지</th>"
             "<th title='free=비정형룰파서 / fallback=레퍼런스기반보조'>추출경로</th>"
             "<th data-num='1' title='스칼라 필드(상단 헤더 영역) 정확도'>필드 정확도</th>"
             "<th data-num='1' title='표 내부 셀(품명·수량·단가·금액 등) 정확도'>셀 정확도</th>"
             "<th data-num='1' title='GT와 추출값이 다른 건수(추출했으나 틀림)'>불일치</th>"
             "<th data-num='1' title='추출 자체가 없는 건수(키가 아예 없음)'>추출누락</th>"
             "<th title='정답 행 수 / 추출된 행 수 (⚠=불일치)'>행 GT/추출</th>"
             "<th data-num='1' title='OCR 글자 오인식으로 인한 오류 수'>인식오류</th>"
             "<th data-num='1' title='값이 엉뚱한 필드·행에 배치된 오류 수'>구조오류</th>"
             "</tr></thead><tbody>")

    def _wk(d):
        a = d["fields"]["fieldAccuracy"]
        return a if a is not None else 1.0

    for d in sorted(compares, key=_wk):
        fc, tt, bt = d["fields"]["counts"], d["table"], d["buckets"]["bucketTally"]
        flag = "" if tt["rowCountMatch"] else " ⚠"
        H.append("<tr>"
                 f"<td>{_esc(d['sourceFile'])}</td><td>{_esc(d.get('extractionPath'))}</td>"
                 f"{acc_td(d['fields']['fieldAccuracy'])}{acc_td(tt['cellAccuracy'])}"
                 f"{num_td(fc['mismatch'])}{num_td(fc['ext_missing'])}"
                 f"<td data-v='{tt['rowCountGt']}'>{tt['rowCountGt']}/{tt['rowCountExt']}{flag}</td>"
                 f"{num_td(bt['recognition'])}{num_td(bt['structure'])}</tr>")
    H.append("</tbody></table><div class='legend'>위에서부터 약한 장 = 먼저 고칠 곳 · "
             "⚠=행 수 불일치 · 컬럼 머리글 클릭으로 정렬</div></section>")

    # 추출경로별
    H.append("<section><h2>추출경로별 (free / fallback)</h2><table><thead><tr><th>경로</th>"
             "<th>필드</th><th>셀</th></tr></thead><tbody>")
    for p, v in m["byPath"].items():
        H.append(f"<tr><td>{_esc(p)}</td><td>{_pct(v['field']['accuracy'])}</td><td>{_pct(v['cell']['accuracy'])}</td></tr>")
    H.append("</tbody></table></section>")

    # 커버리지
    cov = m.get("coverage") or {}
    if cov:
        H.append("<section><h2>커버리지 (분모 2개)</h2>"
                 f"<p class='note'>정답 있는 필드 <b>{cov.get('gtPresent', 0)}</b> · 맞힘 <b>{cov.get('matched', 0)}</b>"
                 f" · 시도했지만 틀림 <b>{cov.get('extAttemptedMiss', 0)}</b>"
                 f" · <b>아예 시도 안 함</b>(신규3 정직한 누락) <b>{cov.get('extNotAttempted', 0)}</b>"
                 f" · 시도율 <b>{_pct(cov.get('attemptRate'))}</b></p></section>")

    # 필드별 (정렬)
    H.append("<section><h2>필드별 정확도 <span class='muted'>(컬럼 클릭=정렬 · 위에서부터 약한 필드)</span></h2>")
    H.append("<table class='sortable'><thead><tr>"
             "<th title='필드 식별자(영문 계약키)'>필드명</th>"
             "<th data-num='1' title='GT가 비어있지 않아 실제로 채점된 건수'>채점수</th>"
             "<th data-num='1' title='GT와 추출값이 정확히 일치한 건수'>일치</th>"
             "<th data-num='1' title='추출했으나 GT와 다른 건수'>불일치</th>"
             "<th data-num='1' title='추출 자체가 없는 건수(키 없음)'>추출누락</th>"
             "<th data-num='1' title='일치 ÷ 채점수'>정확도</th>"
             "</tr></thead><tbody>")
    for label, v in sorted(m["perField"].items(), key=lambda kv: (kv[1]["accuracy"] if kv[1]["accuracy"] is not None else 1.0)):
        ko = _FIELD_KO.get(label, "")
        label_cell = (f"<td><span title='{_esc(label)}'>{_esc(ko)}</span>"
                      f" <span class='muted' style='font-size:11.5px'>({_esc(label)})</span></td>"
                      if ko else f"<td>{_esc(label)}</td>")
        H.append(f"<tr>{label_cell}{num_td(v['scored'])}{num_td(v['match'])}"
                 f"{num_td(v['mismatch'])}{num_td(v['ext_missing'])}{acc_td(v['accuracy'])}</tr>")
    H.append("</tbody></table></section>")

    # 결함 버킷
    b = m["buckets"]
    H.append(f"<section><h2>결함 버킷</h2><p class='note'>인식오류 <b>{b['recognition']}</b> · "
             f"구조오류 <b>{b['structure']}</b> · 컬럼밀림 <b>{b['layout']}</b> · 전처리 <b>{b['preprocessing']}</b>"
             "<br>인식=OCR글자 · 구조=필드/행배치 · 컬럼=표 열밀림 · 전처리=회전/기울기</p></section>")

    # 실패 예시
    H.append("<section><h2>실패 예시 (정답 GT vs 추출값)</h2>")
    shown = 0
    for d in compares:
        if shown >= examples:
            break
        defects = []
        for label, info in d["fields"]["perField"].items():
            if info["status"] in ("mismatch", "ext_missing"):
                ko = _FIELD_KO.get(label, "")
                loc_label = f"{ko} ({label})" if ko else label
                defects.append((f"필드:{loc_label}", info["status"], info["gt"], info["ext"]))
        for row in d["table"]["rows"]:
            for ck, cell in row["cells"].items():
                if cell["status"] in ("mismatch", "ext_missing"):
                    ko = _FIELD_KO.get(ck, "")
                    loc_label = f"{ko} ({ck})" if ko else ck
                    defects.append((f"행{row['rowIndex']}:{loc_label}", cell["status"], cell["gt"], cell["ext"]))
        if not defects:
            continue
        H.append(f"<h3>{_esc(d['sourceFile'])} <span class='muted'>({_esc(d.get('extractionPath'))})</span></h3>")
        H.append("<table><thead><tr><th>위치</th><th>상태</th><th>정답(GT)</th><th>추출값</th></tr></thead><tbody>")
        for loc, st, gt, ext in defects:
            if shown >= examples:
                break
            H.append(f"<tr><td>{_esc(loc)}</td><td>{_ko_status(st)}</td>"
                     f"<td>{_esc((gt or '')[:80])}</td><td>{_esc((ext or '')[:80])}</td></tr>")
            shown += 1
        H.append("</tbody></table>")
    H.append("</section>")

    H.append(_SORT_JS)
    H.append("</body></html>")
    out = os.path.join(run_dir, "report.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(H))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    ap.add_argument("--examples", type=int, default=12)
    args = ap.parse_args()
    run_dir = (os.path.join(C.RUNS_DIR, args.ts) if args.ts
               else sorted(p for p in glob.glob(os.path.join(C.RUNS_DIR, "*")) if os.path.isdir(p))[-1])
    path = render_report(run_dir, args.examples)
    html = render_report_html(run_dir)
    print(f"wrote {path}")
    print(f"wrote {html}")
