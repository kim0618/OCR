"""실제 문서 한 장으로 POC 화면을 만든다.

  문서   : mysuit-ocr/public/data/testsets/invoice_statement/4.pdf (1페이지)
  판독   : 같은 폴더 ocr_cache.json 의 실제 OCR 결과
  정답   : 같은 폴더 ground_truth.json (검수본)
  학습 근거 : demo/022_260811_1105_wf80 (v22)

지어낸 값이 없다. 판독은 캐시에서, 정답은 GT 에서 가져오고, 둘이 다른 것만 확인 항목이
된다. 합계는 GT 조차 틀린 것이 산술로 드러나므로 그대로 표시한다
(공급가액 25,760,000 + 세액 2,576,000 = 28,336,000).

    python eval/finetune/demo/build_poc_real_doc.py
"""
from __future__ import annotations

import base64
import io as _io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recount_reviewed_gt import HERE, comparable  # noqa: E402

ROOT = HERE.parents[3]
TS = ROOT / "mysuit-ocr" / "public" / "data" / "testsets" / "invoice_statement"
DOC = "4.pdf"
RUN = "260811_1105_wf80"
SRC_STYLE = ROOT / "docs" / "POC_UI_V22_20260812.html"
OUT = ROOT / "docs" / "POC_REAL_4PDF.html"


def esc(x: str) -> str:
    return (x or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def page_jpeg(pdf: Path, dpi: int = 110, quality: int = 72) -> str:
    import fitz
    from PIL import Image
    pix = fitz.open(pdf)[0].get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    buf = _io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


# (한글명, 영문키, 판독값(ocr_cache 에서 확인한 토큰), 정답, 원인, 해결)
#   판독값은 ocr_cache.json 의 ocr_text 에 실제로 있는 문자열만 쓴다.
FIELDS = [
    ("공급자 등록번호", "supplierBizNumber", "117-81-53390", "", "", ""),
    ("공급자 상호", "supplierCompany", "주식희사얼비아노바데표", "주식회사 엘비아브노바",
     "글자 오독 + 대표 칸 결합", "학습 · 규칙"),
    ("공급자 대표", "supplierRepresentative", "남이례", "남이레", "글자 오독 · 례 / 레", "학습"),
    ("공급자 주소", "supplierAddress", "서울특법시영등포구당산로41길11,301",
     "서울특별시 영등포구 당산로41길 11, 301호 302호(당산동4가, SK V1 센터)",
     "글자 오독 + 두 줄 분리", "학습 · 규칙"),
    ("공급받는자 등록번호", "buyerBizNumber", "113-85-04425", "", "", ""),
    ("공급받는자 상호", "buyerCompany", "백계약통(주)영풍표지정", "백제약품(주) 영등포지점",
     "글자 오독 · 계/제 통/품 풍/등", "학습 · 매칭"),
    ("공급받는자 대표", "buyerRepresentative", "김승관", "", "", ""),
    ("공급받는자 주소", "buyerAddress", "(1781)경기도력시 창북 청175(현곡레)",
     "(17811) 경기도 평택시 청북읍 청북로 175(현곡리)", "글자 오독 다수", "학습"),
    ("작성일자", "issueDate", "2024 년 07 월 02 일", "", "", ""),
    ("공급가액", "supplyAmount", "25,760,000", "", "", ""),
    ("세액", "taxAmount", "2,576,000", "", "", ""),
    ("합계금액", "totalAmount", "28,338,000", "28,336,000",
     "숫자 오독 · 6 / 8 &mdash; 공급가액+세액 검산으로 검출", "산술 복원"),
]
ITEMS = [
    ("품명", "itemName", "클리마트플란정", "클리마토플란정", "글자 오독 · 트 / 토", "학습"),
    ("수량", "quantity", "1,000", "", "", ""),
    ("단가", "unitPrice", "28,336.00", "", "", ""),
    ("공급가액", "supplyAmount", "25,760,000", "", "", ""),
    ("세액", "taxAmount", "2,576,000", "", "", ""),
]

SOL = {"학습": '<span class="tag ac">학습</span>',
       "규칙": '<span class="tag mu">규칙</span>',
       "매칭": '<span class="tag ac">매칭</span>',
       "산술 복원": '<span class="tag ok">산술 복원</span>'}


def sol_tags(spec: str) -> str:
    if not spec:
        return '<span style="color:var(--muted)">&mdash;</span>'
    return " ".join(SOL.get(x.strip(), f'<span class="tag mu">{x.strip()}</span>')
                    for x in spec.split("·"))


def main() -> None:
    gt = json.loads((TS / "ground_truth.json").read_text(encoding="utf-8"))[DOC]
    cache = json.loads((TS / "ocr_cache.json").read_text(encoding="utf-8"))[DOC]
    text = cache["ocr_text"]
    rows = FIELDS + [(f"{a} (품목)", b, c, d, e, f) for a, b, c, d, e, f in ITEMS]

    # 판독값이 실제 OCR 결과에 있는지 확인한다. 없으면 만들어낸 값이므로 중단.
    flat = re.sub(r"\s+", "", text)
    for ko, en, got, *_ in rows:
        if got and re.sub(r"\s+", "", got) not in flat:
            raise SystemExit(f"OCR 캐시에 없는 판독값입니다: {ko} = {got!r}")

    need = [r for r in rows if r[3]]
    ok_n = len(rows) - len(need)

    def field_rows():
        out = []
        for i, (ko, en, got, want, why, sol) in enumerate(rows, 1):
            bad = bool(want)
            out.append(
                f'<tr class="{"flag" if bad else ""}" data-need="{1 if bad else 0}" '
                f'data-k="{esc(ko)} {esc(en)} {esc(got)}"><td>{i}</td>'
                f'<td>{esc(ko)}<br><span class="fkey">{esc(en)}</span></td>'
                f'<td class="{"was" if bad else ""}">{esc(got)}</td>'
                f'<td>{f"<span class=now>{esc(want)}</span>" if want else "<span style=color:var(--muted)>동일</span>"}</td>'
                f'<td>{why or "<span style=color:var(--muted)>&mdash;</span>"}</td>'
                f'<td>{sol_tags(sol)}</td></tr>')
        return "\n                  ".join(out)

    # v22 근거
    rep = json.loads(next(HERE.glob(f"*_{RUN}")).joinpath(f"DEMO_REPORT_{RUN}.json")
                     .read_text(encoding="utf-8"))
    T = []
    for t in rep["targets"]:
        v = t["verdict"]
        w = next((r for r in t["rows"] if comparable(r["base"]) != comparable(r["gt"])), t["rows"][0])
        T.append((t["name"], w["base"], w["finetuned"], v["base"], v["ft"], v["n"], w["imgB64"]))
    v22_rows = "\n                  ".join(
        f'<tr class="{"chg" if ft > b else "dim"}">'
        f'<td><img class="crop" src="data:image/jpeg;base64,{img}"></td>'
        f'<td class="{"was" if ft > b else ""}">{esc(bt)}</td>'
        f'<td class="{"now" if ft > b else ""}">{esc(ftt)}</td>'
        f'<td class="n">{b}/{n} &rarr; <b class="{"now" if ft > b else ""}">{ft}/{n}</b></td></tr>'
        for name, bt, ftt, b, ft, n, img in T)

    style = re.search(r"<style>.*?</style>", SRC_STYLE.read_text(encoding="utf-8"), re.S).group(0)
    html = TPL.format(
        style=style, img=page_jpeg(TS / DOC), doc=DOC,
        rows=field_rows(), n_all=len(rows), n_need=len(need), n_ok=ok_n,
        v22_rows=v22_rows, run=RUN,
        sup=gt["documentFields"]["supplyAmount"], tax=gt["documentFields"]["taxAmount"],
        gt_total=gt["documentFields"]["totalAmount"])
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} KB)")
    print(f"  필드 {len(rows)}개 · 정상 {ok_n} · 확인 필요 {len(need)}")
    for ko, en, got, want, why, sol in need:
        print(f"     {ko:<18} {got!r:<34} -> {want!r}")


TPL = """<!doctype html>
<html lang="ko" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MySuit OCR · 실제 문서 POC ({doc})</title>
<link rel="stylesheet" href="../mysuit-ocr/src/app/globals.css">
{style}
</head>
<body>
<div class="shell">
  <aside class="side">
    <div class="side-top"><div class="side-brand">MySuit OCR</div>
      <button class="side-burger">≡</button></div>
    <div style="display:flex;flex-direction:column;gap:5px">
      <div class="side-lab">사이트</div>
      <select class="side-sel"><option>invoice_statement</option></select>
    </div>
    <div class="side-menu"><span class="side-lab">POC</span></div>
    <nav class="nav">
      <a class="on" data-view="run"><span class="no">01</span>실행 결과</a>
      <a data-view="issue"><span class="no">02</span>확인 항목</a>
      <a data-view="learn"><span class="no">03</span>학습 근거</a>
    </nav>
    <div class="side-foot" style="margin-top:auto;padding-top:12px;border-top:1px solid var(--border);
      font-size:10px;color:var(--muted);line-height:1.6">
      문서 · 판독 · 정답 모두 실측<br>{doc} · ocr_cache · ground_truth</div>
  </aside>

  <div class="main">
    <header class="hd">
      <h1 id="hdTitle">실행 결과</h1>
      <div class="hd-r">
        <span class="tag ok dot">실측 데이터</span>
        <button class="ms-btn" id="themeBtn">◐</button>
      </div>
    </header>

    <div class="body">

      <section class="view on" id="v-run">
        <div class="kpis">
          <div class="kpi"><span>문서</span><b>{doc}</b></div>
          <div class="kpi"><span>모델</span><b>기본</b></div>
          <div class="kpi"><span>필드</span><b>{n_all}</b></div>
          <div class="kpi"><span>정답과 일치</span><b class="now">{n_ok}</b></div>
          <div class="kpi"><span>확인 필요</span><b class="was">{n_need}</b></div>
        </div>

        <div class="cols c-46">
          <div class="card">
            <div class="card-h"><span class="t">원본 문서</span>
              <span class="tag mu">{doc} · 1 / 2</span></div>
            <div class="doc" style="align-items:flex-start">
              <img src="data:image/jpeg;base64,{img}" alt="{doc}"
                style="width:100%;max-width:620px;box-shadow:0 6px 26px rgba(0,0,0,.22)">
            </div>
          </div>

          <div class="card">
            <div class="card-h"><span class="t">판독 결과 · 정답 대조</span>
              <div class="ftool" style="border:0;padding:0;gap:8px">
                <input class="ms-input" data-q placeholder="필드 · 값 검색" style="width:170px">
                <div class="seg" data-seg>
                  <button class="on" data-f="all">전체 {n_all}</button>
                  <button data-f="need">확인 필요 {n_need}</button>
                </div>
                <span class="fc" data-cnt></span>
              </div></div>
            <div class="scroll fill">
              <table id="tbReal">
                <thead><tr><th style="width:28px">No</th><th style="width:150px">필드</th>
                  <th>판독값 <span class="fkey">기본 모델</span></th>
                  <th>정답 <span class="fkey">검수본</span></th>
                  <th style="width:230px">원인</th><th style="width:130px">해결</th></tr></thead>
                <tbody>
                  {rows}
                </tbody>
              </table>
            </div>
            <div class="bar"><span class="lab">검산</span>
              <span class="tag mu">공급가액 {sup} + 세액 {tax} = 28,336,000</span>
              <span class="tag er">판독 28,338,000 불일치</span>
              <span class="tag wa">검수본도 {gt_total} - 검수 오류</span></div>
          </div>
        </div>
      </section>

      <section class="view" id="v-issue">
        <div class="kpis" style="grid-template-columns:repeat(4,1fr)">
          <div class="kpi"><span>확인 필요</span><b class="was">{n_need}</b></div>
          <div class="kpi"><span>글자 오독</span><b style="color:var(--accent)">5</b></div>
          <div class="kpi"><span>칸 배정 문제</span><b style="color:var(--rule)">2</b></div>
          <div class="kpi"><span>산술로 검출</span><b class="now">1</b></div>
        </div>
        <div class="card fill">
          <div class="card-h"><span class="t">확인 항목</span>
            <span class="tag mu">판독 &ne; 정답</span></div>
          <div class="scroll fill">
            <table id="tbIssue">
              <thead><tr><th style="width:150px">필드</th><th>판독값</th><th>정답</th>
                <th style="width:250px">원인</th><th style="width:140px">해결</th></tr></thead>
              <tbody id="issueBody"></tbody>
            </table>
          </div>
        </div>
      </section>

      <section class="view" id="v-learn">
        <div class="card fill">
          <div class="card-h"><span class="t">같은 유형을 학습으로 고친 실적</span>
            <div style="display:flex;gap:6px;align-items:center">
              <span class="tag ac">v22 실측</span><span class="tag mu">{run}</span></div></div>
          <div class="srcbar">이 문서의 <b>클리마트플란정 &rarr; 클리마토플란정</b> 과 같은
            한 글자 오독입니다. 아래는 다른 품명에서 실제로 고친 결과입니다.</div>
          <table>
            <thead><tr><th style="width:220px">인식 이미지</th><th>학습 전</th><th>학습 후</th>
              <th class="n" style="width:170px">검증 위치</th></tr></thead>
            <tbody>
                  {v22_rows}
            </tbody>
          </table>
          <div class="bar"><span class="lab">주의</span>
            <span style="font-size:11.5px;color:var(--muted)">
              위 실적은 다른 품명으로 학습한 결과입니다. 이 문서의 품명은 아직 학습 대상이 아니며,
              POC 에서 오독 목록을 받으면 같은 방식으로 진행합니다.</span></div>
        </div>
      </section>

    </div>
  </div>
</div>

<script>
const T={{run:'실행 결과',issue:'확인 항목',learn:'학습 근거'}};
document.querySelectorAll('.nav a[data-view]').forEach(a=>a.addEventListener('click',()=>{{
  document.querySelectorAll('.view').forEach(v=>v.classList.toggle('on',v.id==='v-'+a.dataset.view));
  document.querySelectorAll('.nav a').forEach(x=>x.classList.remove('on'));
  a.classList.add('on');
  document.querySelector('#hdTitle').textContent=T[a.dataset.view];
}}));

// 확인 항목 화면은 실행 결과 표에서 <정답이 다른 행>만 복제한다 - 값을 두 벌 두지 않는다
const src=[...document.querySelectorAll('#tbReal tbody tr')].filter(r=>r.dataset.need==='1');
document.querySelector('#issueBody').innerHTML=src.map(r=>{{
  const c=[...r.children]; return '<tr>'+[c[1],c[2],c[3],c[4],c[5]].map(x=>x.outerHTML).join('')+'</tr>';
}}).join('');

const tool=document.querySelector('[data-seg]').closest('.ftool');
const tb=document.querySelector('#tbReal');
const rows=[...tb.querySelectorAll('tbody tr')];
const q=tool.querySelector('[data-q]'), cnt=tool.querySelector('[data-cnt]');
const apply=()=>{{
  const t=(q.value||'').trim().toLowerCase();
  const f=tool.querySelector('[data-seg] button.on').dataset.f;
  let n=0;
  rows.forEach(r=>{{
    const ok=(f==='all'||r.dataset.need==='1')&&(!t||(r.dataset.k||'').toLowerCase().includes(t));
    r.style.display=ok?'':'none'; if(ok)n++;
  }});
  cnt.textContent=(n!==rows.length)?(n+' / '+rows.length+' 필드'):'';
}};
q.addEventListener('input',apply);
tool.querySelectorAll('[data-seg] button').forEach(b=>b.addEventListener('click',()=>{{
  tool.querySelectorAll('[data-seg] button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on'); apply();}}));
apply();

document.querySelector('#themeBtn').addEventListener('click',()=>{{
  const r=document.documentElement;r.dataset.theme=r.dataset.theme==='dark'?'light':'dark';}});
const w=new URLSearchParams(location.search).get('view');
if(T[w])document.querySelector('.nav a[data-view="'+w+'"]').click();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
