from __future__ import annotations

import base64
import html
import json
import re
import tarfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
AUDIT_DIR = HERE / "verify" / "lost_v5_full_audit_20260805"
LOST_META = HERE / "lost_meta.json"
ARCHIVE = AUDIT_DIR / "lost_crops.tgz"
OUTPUT = HERE / "GT_REVIEW_220.html"
REVIEW_RESULT = HERE / "GT_REVIEW_220_result.json"


# B means both the old GT and v5 output were wrong. These values were transcribed
# from the crop itself. Low-confidence rows are deliberately marked for review.
B_REVIEW: dict[str, tuple[str, str, str]] = {
    "crops/2417fd783498e193.jpg": ("글리아티연질캡슐", "medium", "작은 글자: 제품명 철자 재확인 권장"),
    "crops/2e30cc808c53b7c5.jpg": ("세로프건조시럽[15", "medium", "오른쪽이 잘린 크롭: [15 이후 범위 확인 필요"),
    "crops/35ffe67757973d74.jpg": ("중외제약)피나스타5mg(78ea)p", "high", "마지막 p는 인쇄 문자로 판독"),
    "crops/68c38141c8d57062.jpg": ("페스틴정(향정신성의약품)", "high", "빨간 손글씨 B 제외"),
    "crops/a0e47b5925af820a.jpg": ("트리마셋세미정", "high", "빨간 손글씨 B 제외"),
    "crops/be1aa794f4c383ed.jpg": ("부스핀정", "high", "인쇄 문자열 기준"),
    "crops_correct/0adf8ba09c53a71e.jpg": ("리피엔정10mg / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/0f40cc59b865a994.jpg": ("베넬리탁듀오서방정10/500mg/30T", "high", "인쇄 문자열 기준"),
    "crops_correct/1ab0d831f67cae27.jpg": ("동화쿠에티아핀정 200mg 30T", "high", "빨간 손글씨 B 제외"),
    "crops_correct/2e42bee8d876ff20.jpg": ("2284 메시마캅셀", "high", "인쇄된 행번호 2284 포함"),
    "crops_correct/36ca17feac6714f5.jpg": ("10-서 112 한화)아토산정", "medium", "10-서 부분 작은 글자 재확인 권장"),
    "crops_correct/3d9c11809123f19a.jpg": ("다글립정10/100mg / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/7ca0d825f992d905.jpg": ("다글립정10/100mg / ㈜이든파마", "high", "동일 품명 두 번째 크롭"),
    "crops_correct/4087f801345ca120.jpg": ("스피드구급함+셋트", "high", "+ 기호 포함"),
    "crops_correct/a951ab725d28082e.jpg": ("스피드구급함+셋트", "high", "동일 품명 두 번째 크롭"),
    "crops_correct/45467df818f0ddeb.jpg": ("리큅피디정 4밀리그램", "high", "리컵/리쉽이 아니라 리큅으로 판독"),
    "crops_correct/525a1c5fb580c188.jpg": ("바이제타정10/20mg / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/54ef4f4bb6656f75.jpg": ("타리마겐정", "high", "빨간 손글씨 B 제외"),
    "crops_correct/5a4a333c39ec67db.jpg": ("10-서 141 현대)바로스크정(B)", "medium", "10-서 부분 작은 글자 재확인 권장"),
    "crops_correct/5d459c2584606fe8.jpg": ("레바드정 / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/674aea9e55e0653b.jpg": ("디핀스정80/5mg / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/6989e726c25688ec.jpg": ("시글립듀오정50/500mg / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/69c84b8387a28cae.jpg": ("크레바젯정10/5mg/30T(P)", "high", "단위 mg로 판독"),
    "crops_correct/7e9a47b6553a492d.jpg": ("에소프라정40mg / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/8c1ade41060b7485.jpg": ("리큅피디정 8밀리그램", "high", "리컵/리쉽이 아니라 리큅으로 판독"),
    "crops_correct/9f8f5011548ffcfe.jpg": ("10-B 154 글로벌)피나스칸정", "high", "오른쪽 빨간 손글씨 10 제외"),
    "crops_correct/a37abe8437f446ae.jpg": ("암로텔미정40/5밀리그램", "high", "오른쪽 빨간 손글씨 숫자 제외"),
    "crops_correct/aa4d78d8062d0c7c.jpg": ("엠피디정", "high", "인쇄 문자열 기준"),
    "crops_correct/b68f9db4fde2af15.jpg": ("시글립정100mg / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/bb0172a0deee3a95.jpg": ("세푸록심악세틸정", "medium", "왼쪽 첫 글자가 경계에 가까워 재확인 권장"),
    "crops_correct/bc182aec9e7a19c6.jpg": ("1650700930 휴듀오서방정10/1000mg(PTP) 28T", "medium", "휴듀오 첫 글자와 공백 재확인 권장"),
    "crops_correct/d2ff1897470f395f.jpg": ("이든알마게이트정 / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/d9a05ad779879ebc.jpg": ("글루피드정", "high", "빨간 손글씨 B 제외"),
    "crops_correct/eabab43ef4baeb08.jpg": ("리프스톤정 / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/eb29dbed2c147491.jpg": ("그로모정5mg", "high", "오른쪽 빨간 손글씨 제외"),
    "crops_correct/f145ecdd939ea144.jpg": ("리셀론정150mg / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/fb28e6bafc8c0b05.jpg": ("인티진정 / ㈜이든파마", "high", "인쇄 문자열 기준"),
    "crops_correct/fb8622e44c098f95.jpg": ("에큐민정25mg / ㈜이든파마", "high", "인쇄 문자열 기준"),
}

VERIFICATION_ISSUES: dict[str, str] = {
    "crops/7582a0b828169f87.jpg": "넥스팜)암로텔",
    "crops_correct/1d35de833981ef6e.jpg": "티로프란정",
    "crops_correct/aa4d78d8062d0c7c.jpg": "엠피디정",
    "crops_correct/d9eb1217a8a2048c.jpg": "피글리정",
    "crops_correct/db2a1480972fc7d7.jpg": "피나베린정 5mg",
    "crops_correct/dfcf788b67d50986.jpg": "이바레탄정160mg",
    "crops_correct/e7fe0bebd0865937.jpg": "애스펜정",
    "crops_correct/fdac07ac0f781a0b.jpg": "티로프란정",
    "crops_correct/2a5ebe6374d3aa9a.jpg": "아베린엠정2/500밀리그램(글리메피리드,",
    "crops_correct/2bb6ee5bc9384c55.jpg": "우황청심원현탁액(영묘향)-",
    "crops_correct/46f53c854379e3a8.jpg": "유로가드정0.5/5밀리그램(두타스테리드,",
}


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text)


def load_verdicts() -> dict[int, str]:
    result: dict[int, str] = {}
    for line in (AUDIT_DIR / "verdicts.txt").read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(\d+)\s+([MGBXOCP])", line.strip())
        if match:
            result[int(match.group(1))] = match.group(2)
    return result


def build_rows() -> list[dict[str, object]]:
    groups = json.loads((AUDIT_DIR / "meta.json").read_text(encoding="utf-8"))
    lost = json.loads(LOST_META.read_text(encoding="utf-8"))
    reviewed = {}
    if REVIEW_RESULT.exists():
        reviewed = {
            item["path"]: item
            for item in json.loads(REVIEW_RESULT.read_text(encoding="utf-8"))
        }
    verdicts = load_verdicts()
    group_by_name = {
        normalized(group["name"]): {
            "idx": int(group["idx"]),
            "verdict": verdicts[int(group["idx"])],
        }
        for group in groups
    }

    selected: list[dict[str, object]] = []
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        for item in lost:
            group = group_by_name[normalized(item["gt"])]
            code = group["verdict"]
            if code not in {"G", "B"}:
                continue

            path = item["path"]
            image_bytes = archive.extractfile(path).read()
            image_data = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
            if code == "B":
                ai_gt, confidence, note = B_REVIEW[path]
            else:
                ai_gt = item["pred"]
                confidence = "high"
                note = "G 판독: v5 출력이 인쇄 내용과 일치한다고 판단한 초안"

            reviewed_item = reviewed.get(path, {})
            default_gt = VERIFICATION_ISSUES.get(
                path, reviewed_item.get("final_gt", ai_gt)
            )
            default_status = reviewed_item.get("status", "pending")

            selected.append(
                {
                    "row": len(selected) + 1,
                    "audit_idx": group["idx"],
                    "code": code,
                    "path": path,
                    "image": image_data,
                    "old_gt": item["gt"],
                    "prediction": item["pred"],
                    "ai_gt": ai_gt,
                    "confidence": confidence,
                    "verification_issue": path in VERIFICATION_ISSUES,
                    "recommended_gt": VERIFICATION_ISSUES.get(path, ""),
                    "default_gt": default_gt,
                    "default_status": default_status,
                    "note": (
                        f"재검증 이상: 이미지 기준 권장 GT = {VERIFICATION_ISSUES[path]}"
                        if path in VERIFICATION_ISSUES
                        else note
                    ),
                }
            )

    counts = {code: sum(row["code"] == code for row in selected) for code in ("G", "B")}
    if len(selected) != 220 or counts != {"G": 182, "B": 38}:
        raise RuntimeError(f"unexpected selection: total={len(selected)}, counts={counts}")
    missing_b = {row["path"] for row in selected if row["code"] == "B"} - B_REVIEW.keys()
    if missing_b:
        raise RuntimeError(f"missing B review entries: {sorted(missing_b)}")
    return selected


def render(rows: list[dict[str, object]]) -> str:
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang=\"ko\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>GT 재검수 220장</title>
<style>
:root {{--bg:#f4f6f8;--panel:#fff;--line:#d8dee5;--text:#18212b;--muted:#65717e;--g:#16784a;--b:#b54708;--blue:#1769aa}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Segoe UI","Malgun Gothic",sans-serif}}
header{{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.97);border-bottom:1px solid var(--line);padding:14px 18px;box-shadow:0 2px 10px #0001}}
h1{{font-size:20px;margin:0 0 6px}} .sub{{font-size:13px;color:var(--muted);margin-bottom:10px}}
.toolbar{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}} button,select,input{{font:inherit}}
button{{border:1px solid #aeb8c2;background:#fff;border-radius:7px;padding:7px 10px;cursor:pointer}} button.primary{{background:var(--blue);color:#fff;border-color:var(--blue)}}
input[type=search]{{width:300px;max-width:100%;border:1px solid #aeb8c2;border-radius:7px;padding:8px}}
.stats{{font-size:13px;font-weight:700;margin-left:auto}} main{{padding:14px}}
.notice{{background:#fff7e8;border:1px solid #f2cb84;border-radius:8px;padding:10px 12px;margin-bottom:12px;font-size:13px}}
.table-wrap{{overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:9px}}
table{{border-collapse:collapse;width:100%;min-width:1550px}} th,td{{border-bottom:1px solid var(--line);border-right:1px solid #edf0f2;padding:8px;vertical-align:top;text-align:left}}
th{{position:sticky;top:0;background:#eef2f5;z-index:2;font-size:12px;white-space:nowrap}} td{{font-size:13px}}
tr.done{{background:#f3fbf6}} tr.review{{background:#fff7ed}} tr.flagged{{background:#fff0f0;box-shadow:inset 4px 0 #d92d20}} .idx{{color:var(--muted);white-space:nowrap}}
.badge{{display:inline-block;padding:2px 7px;border-radius:999px;color:#fff;font-weight:800}} .badge.G{{background:var(--g)}} .badge.B{{background:var(--b)}}
.crop{{width:360px;max-width:360px;min-height:46px;display:flex;align-items:center;justify-content:center;background:#f8fafb;border:1px solid var(--line);border-radius:5px;overflow:hidden;cursor:zoom-in}}
.crop img{{max-width:100%;max-height:95px;image-rendering:auto}} .text{{white-space:pre-wrap;word-break:break-all;min-width:180px}}
.ai{{font-weight:700;color:#123f64}} .confidence{{font-size:11px;margin-top:5px;color:var(--muted)}}
textarea{{width:250px;min-height:64px;resize:vertical;border:1px solid #9da9b5;border-radius:6px;padding:7px;font:inherit}}
.mini{{padding:3px 6px;font-size:11px;margin-top:5px}} .note{{max-width:210px;color:#53606d;font-size:12px}}
#modal{{display:none;position:fixed;inset:0;z-index:50;background:#000c;padding:28px;align-items:center;justify-content:center;cursor:zoom-out}}
#modal.open{{display:flex}} #modal img{{max-width:96vw;max-height:88vh;transform:scale(2);image-rendering:auto;background:#fff;padding:10px}}
@media(max-width:800px){{header{{position:relative}}.stats{{width:100%;margin-left:0}}main{{padding:8px}}}}
</style>
</head>
<body>
<header>
  <h1>GT 재검수 — G 182장 + B 38장</h1>
  <div class=\"sub\">이미지를 클릭하면 확대됩니다. ‘최종 GT’ 수정과 상태는 이 브라우저에 자동 저장됩니다.</div>
  <div class=\"toolbar\">
    <input id=\"q\" type=\"search\" placeholder=\"GT·예측·파일명 검색\">
    <select id=\"codeFilter\"><option value=\"flagged\" selected>재검증 이상 8개</option><option value=\"all\">G+B 전체 220개</option><option value=\"G\">G 182장</option><option value=\"B\">B 38장</option></select>
    <select id=\"statusFilter\"><option value=\"all\">모든 상태</option><option value=\"pending\">미검수</option><option value=\"approved\">확정</option><option value=\"needs_review\">재확인</option><option value=\"exclude\">제외</option></select>
    <button class=\"primary\" id=\"exportJson\">JSON 내보내기</button>
    <button id=\"exportTsv\">TSV 내보내기</button>
    <button id=\"importBtn\">JSON 불러오기</button><input id=\"importFile\" type=\"file\" accept=\"application/json\" hidden>
    <button id=\"resetBtn\">저장값 초기화</button>
    <span class=\"stats\" id=\"stats\"></span>
  </div>
</header>
<main>
  <div class=\"notice\"><b>판독 기준:</b> 검은 인쇄 문자열을 우선하고 빨간 손글씨 B·P·숫자는 제외했습니다. B의 ‘확인 필요’ 표시는 작은 글자나 잘린 경계 때문에 사용자가 한 번 더 봐야 하는 항목입니다. G의 AI GT는 전수 판독에서 이미지와 일치한다고 판단한 v5 출력을 초안으로 넣었습니다.</div>
  <div class=\"table-wrap\"><table><thead><tr><th># / 판정</th><th>크롭</th><th>기존 GT</th><th>v5 출력</th><th>AI 판단 GT</th><th>최종 GT (수정 가능)</th><th>상태</th><th>판독 메모</th></tr></thead><tbody id=\"rows\"></tbody></table></div>
</main>
<div id=\"modal\"><img alt=\"확대 크롭\"></div>
<script>
const DATA={data};
const STORE='gt-review-220-v2';
let saved=JSON.parse(localStorage.getItem(STORE)||'{{}}');
const esc=s=>String(s).replace(/[&<>\"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c]));
function stateFor(r){{return saved[r.path]||{{final_gt:r.default_gt,status:r.default_status}}}}
function persist(){{localStorage.setItem(STORE,JSON.stringify(saved));updateStats()}}
function visible(r){{const q=document.querySelector('#q').value.trim().toLowerCase();const cf=document.querySelector('#codeFilter').value;const sf=document.querySelector('#statusFilter').value;const s=stateFor(r);const codeOk=cf==='all'||(cf==='flagged'&&r.verification_issue)||r.code===cf;return codeOk&&(sf==='all'||s.status===sf)&&(!q||[r.old_gt,r.prediction,r.ai_gt,r.recommended_gt,r.path].join(' ').toLowerCase().includes(q))}}
function render(){{const body=document.querySelector('#rows');body.innerHTML=DATA.filter(visible).map(r=>{{const s=stateFor(r);const rowClass=r.verification_issue?'flagged':s.status==='approved'?'done':s.status==='needs_review'?'review':'';return `<tr data-path="${{esc(r.path)}}" class="${{rowClass}}"><td class="idx">${{r.row}}<br><span class="badge ${{r.code}}">${{r.code}}</span><br>품명 #${{r.audit_idx}}<br><small>${{esc(r.path.split('/').pop())}}</small></td><td><div class="crop"><img src="${{r.image}}" data-zoom alt="crop"></div></td><td class="text">${{esc(r.old_gt)}}</td><td class="text">${{esc(r.prediction)}}</td><td class="text ai">${{esc(r.ai_gt)}}<div class="confidence">신뢰도: ${{r.confidence}}</div></td><td><textarea data-final>${{esc(s.final_gt)}}</textarea><br><button class="mini" data-copy-ai>AI GT로 복원</button>${{r.verification_issue?`<br><button class="mini" data-copy-recommended>권장 GT 적용</button>`:''}}</td><td><select data-status><option value="pending" ${{s.status==='pending'?'selected':''}}>미검수</option><option value="approved" ${{s.status==='approved'?'selected':''}}>확정</option><option value="needs_review" ${{s.status==='needs_review'?'selected':''}}>재확인</option><option value="exclude" ${{s.status==='exclude'?'selected':''}}>제외</option></select></td><td class="note">${{esc(r.note)}}</td></tr>`}}).join('');bindRows();updateStats()}}
function bindRows(){{document.querySelectorAll('tr[data-path]').forEach(tr=>{{const path=tr.dataset.path;const r=DATA.find(x=>x.path===path);const ta=tr.querySelector('[data-final]');const st=tr.querySelector('[data-status]');ta.oninput=()=>{{saved[path]={{final_gt:ta.value,status:st.value}};persist()}};st.onchange=()=>{{saved[path]={{final_gt:ta.value,status:st.value}};persist();render()}};tr.querySelector('[data-copy-ai]').onclick=()=>{{ta.value=r.ai_gt;ta.dispatchEvent(new Event('input'))}};const recommended=tr.querySelector('[data-copy-recommended]');if(recommended)recommended.onclick=()=>{{ta.value=r.recommended_gt;ta.dispatchEvent(new Event('input'))}};tr.querySelector('[data-zoom]').onclick=e=>{{const m=document.querySelector('#modal');m.querySelector('img').src=e.target.src;m.classList.add('open')}}}})}}
function updateStats(){{const states=DATA.map(stateFor);const done=states.filter(s=>s.status==='approved').length;const review=states.filter(s=>s.status==='needs_review').length;document.querySelector('#stats').textContent=`표시 ${{DATA.filter(visible).length}} / 220 · 확정 ${{done}} · 재확인 ${{review}}`}}
function exportData(format){{const out=DATA.map(r=>({{row:r.row,audit_idx:r.audit_idx,code:r.code,path:r.path,old_gt:r.old_gt,prediction:r.prediction,ai_gt:r.ai_gt,...stateFor(r),note:r.note}}));let blob,name;if(format==='json'){{blob=new Blob([JSON.stringify(out,null,2)],{{type:'application/json;charset=utf-8'}});name='GT_REVIEW_220_result.json'}}else{{const cols=['row','audit_idx','code','path','old_gt','prediction','ai_gt','final_gt','status','note'];const clean=v=>String(v??'').replace(/\\t/g,' ').replace(/\\r?\\n/g,' ');blob=new Blob(['\\ufeff'+cols.join('\\t')+'\\n'+out.map(x=>cols.map(c=>clean(x[c])).join('\\t')).join('\\n')],{{type:'text/tab-separated-values;charset=utf-8'}});name='GT_REVIEW_220_result.tsv'}}const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}}
document.querySelectorAll('#q,#codeFilter,#statusFilter').forEach(el=>el.addEventListener(el.id==='q'?'input':'change',render));
document.querySelector('#exportJson').onclick=()=>exportData('json');document.querySelector('#exportTsv').onclick=()=>exportData('tsv');
document.querySelector('#importBtn').onclick=()=>document.querySelector('#importFile').click();document.querySelector('#importFile').onchange=async e=>{{const arr=JSON.parse(await e.target.files[0].text());for(const x of arr)if(x.path)saved[x.path]={{final_gt:x.final_gt??x.ai_gt??'',status:x.status??'pending'}};persist();render()}};
document.querySelector('#resetBtn').onclick=()=>{{if(confirm('이 HTML에 저장된 모든 수정값을 초기화할까요?')){{saved={{}};persist();render()}}}};
document.querySelector('#modal').onclick=e=>e.currentTarget.classList.remove('open');document.addEventListener('keydown',e=>{{if(e.key==='Escape')document.querySelector('#modal').classList.remove('open')}});
render();
</script>
</body></html>"""


def main() -> None:
    rows = build_rows()
    OUTPUT.write_text(render(rows), encoding="utf-8")
    print(f"wrote {OUTPUT}")
    print(f"rows={len(rows)} G={sum(r['code'] == 'G' for r in rows)} B={sum(r['code'] == 'B' for r in rows)}")


if __name__ == "__main__":
    main()
