from __future__ import annotations

import difflib
import html
import json
import unicodedata
from collections import Counter
from pathlib import Path

import recount_reviewed_gt as R


HERE = Path(__file__).resolve().parent
SCANS = HERE / "scans"
OUTPUT = HERE / "TARGET_EFFECT_REVIEW.html"
PATHS = HERE / "TARGET_EFFECT_PATHS.txt"
IMAGE_ROOT = HERE / "verify" / "target_effect_crops_20260805"
TARGET_NAME = "세파록스캡슐"
SL_MISSING_PATHS = HERE / "SL_GT_MISSING_CROPS.txt"

# Confirmed against the crop and the registered product name.  These two old
# labels made genuine `슐` examples look like `슬 -> 슐` regressions.
KNOWN_GT_FIXES = {
    "비스칸엔캡슬(바실루스리케니포르미": "비스칸엔캡슐(바실루스리케니포르미",
    "클라넥신듀오캡슬": "클라빅신듀오캡슐",
}


def compact(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).split())


def load_scan(name: str, keep: set[str]) -> dict[str, dict]:
    rows = {}
    with (SCANS / name).open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["path"] in keep:
                rows[row["path"]] = row
    return rows


def state(base_ok: bool, model_ok: bool) -> str:
    if not base_ok and model_ok:
        return "revived"
    if base_ok and not model_ok:
        return "lost"
    if base_ok and model_ok:
        return "kept_correct"
    return "still_wrong"


def marked_diff(old: str, new: str) -> tuple[str, str, str]:
    base_parts: list[str] = []
    new_parts: list[str] = []
    changes: list[str] = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new).get_opcodes():
        before, after = old[i1:i2], new[j1:j2]
        if op == "equal":
            base_parts.append(html.escape(before))
            new_parts.append(html.escape(after))
        elif op == "replace":
            base_parts.append(f'<span class="removed">{html.escape(before)}</span>')
            new_parts.append(f'<span class="changed">{html.escape(after)}</span>')
            if before.strip() or after.strip():
                changes.append(f'“{before}”→“{after}” 치환')
        elif op == "delete":
            base_parts.append(f'<span class="removed">{html.escape(before)}</span>')
            if before.strip():
                changes.append(f'“{before}” 삭제')
        elif op == "insert":
            new_parts.append(f'<span class="changed">{html.escape(after)}</span>')
            if after.strip():
                changes.append(f'“{after}” 추가')
    return "".join(base_parts), "".join(new_parts), ", ".join(changes) or "공백 위치 변경"


def has_sl_to_shul(old: str, new: str) -> bool:
    """True only when the actual diff replaces 슬 with 슐."""
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new).get_opcodes():
        if op == "replace" and "슬" in old[i1:i2] and "슐" in new[j1:j2]:
            return True
    return False


def only_sl_to_shul(old: str, new: str) -> bool:
    """True when every real base->12x change is exactly `슬` -> `슐`."""
    old, new = compact(old), compact(new)
    saw_change = False
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new).get_opcodes():
        if op == "equal":
            continue
        if op != "replace" or old[i1:i2] != "슬" or new[j1:j2] != "슐":
            return False
        saw_change = True
    return saw_change


def effect_label(value: str) -> str:
    return {
        "revived": "오독 교정: base 오답을 12배가 정답으로 바꿈",
        "lost": "회귀 발생: base 정답을 12배가 오답으로 바꿈",
        "still_wrong": "오답 형태 변경: 둘 다 오답이지만 판독 문자열이 바뀜",
        "kept_correct": "정답 표기 변경: 둘 다 정답 범위지만 출력 표기가 바뀜",
    }[value]


def main() -> None:
    keep = {
        line.strip()
        for line in (HERE / "basis_keep.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    overrides, excluded_names, _ = R.load_policy()
    base = load_scan("000_base.jsonl", keep)
    v12 = load_scan("260804_1623.jsonl", keep)
    common = set(base) & set(v12)

    rows = []
    for path in sorted(common):
        old_gt = base[path]["gt"]
        key = R.name_key(old_gt)
        if key in excluded_names:
            continue
        gt = overrides.get(key, old_gt)
        gt = KNOWN_GT_FIXES.get(R.name_key(gt), gt)
        # The target itself is already proven separately (0/26 -> 26/26).
        # This view is only for collateral improvements/regressions on all
        # *other* product names caused by the target fine-tune run as a whole.
        if R.comparable(gt) == R.comparable(TARGET_NAME):
            continue
        bp, p12 = base[path]["pred"], v12[path]["pred"]
        bok = R.comparable(gt) == R.comparable(bp)
        ok12 = R.comparable(gt) == R.comparable(p12)
        s12 = state(bok, ok12)
        tabs: list[str] = []
        reason = ""
        strict_sl_to_shul = only_sl_to_shul(bp, p12)
        if strict_sl_to_shul and ok12:
            tabs.append("sl_to_shul_correct")
            reason = "base→12배의 유일한 변화가 ‘슬→슐’이며 12배 전체 품명이 정답"
        elif strict_sl_to_shul and "슬" in gt and "슐" in p12 and not ok12:
            tabs.append("sl_to_shul_wrong")
            reason = "정답은 실제 ‘슬’인데 base→12배가 ‘슬→슐’만 바꿔 오답이 됨"
        elif "슬" in gt and compact(bp) == compact(p12) and ok12:
            tabs.append("sl_unchanged_correct")
            reason = "정답의 ‘슬’을 base와 12배가 변환 없이 그대로 정확히 읽음"

        if not tabs:
            continue
        base_html, p12_html, change = marked_diff(bp, p12)
        change_note = change if compact(bp) != compact(p12) else "base와 12배 출력 동일"
        image_path = IMAGE_ROOT / path
        rows.append({
            "path": path,
            "base": bp,
            "p12": p12,
            "base_html": base_html,
            "p12_html": p12_html,
            "base_ok": bok,
            "ok12": ok12,
            "state12": s12,
            "tabs": tabs,
            "reason": f"{reason} · {change_note}",
            "has_image": image_path.exists(),
            "image": image_path.relative_to(HERE).as_posix(),
        })

    PATHS.write_text("\n".join(row["path"] for row in rows) + "\n", encoding="utf-8", newline="\n")
    missing_sl = [row["path"] for row in rows if not row["has_image"]]
    SL_MISSING_PATHS.write_text("\n".join(missing_sl) + ("\n" if missing_sl else ""), encoding="utf-8", newline="\n")
    counts12 = Counter(row["state12"] for row in rows)
    impacts = Counter(tab for row in rows for tab in row["tabs"])
    view_rows = [
        {key: row[key] for key in (
            "base", "p12", "base_html", "p12_html", "base_ok", "ok12",
            "state12", "tabs", "reason", "has_image", "image"
        )}
        for row in rows
    ]
    data = json.dumps(view_rows, ensure_ascii=False).replace("</", "<\\/")
    summary = {
        "rows": len(rows),
        "images": sum(row["has_image"] for row in rows),
        "state12": counts12,
    }
    body = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>세파록스캡슐 FT 영향 전수 비교</title>
<style>
body{{font-family:Arial,'Malgun Gothic',sans-serif;margin:0;background:#f5f7fa;color:#172033}}
header{{position:sticky;top:0;background:white;padding:14px 18px;border-bottom:1px solid #ccd5e0;z-index:5}}
h1{{font-size:20px;margin:0 0 8px}} .summary{{font-size:13px;color:#46566b;margin-bottom:9px}}
.tools{{display:flex;gap:8px;flex-wrap:wrap}} input,select,button{{font-size:14px;padding:7px;border:1px solid #aeb9c7;border-radius:5px;background:white}}
.tabs{{display:flex;gap:6px;margin-bottom:9px}} .tab.active{{background:#1269b0;color:white;border-color:#1269b0;font-weight:bold}}
.pager{{display:flex;align-items:center;gap:8px;padding:8px 18px;background:white;border-bottom:1px solid #d6dee8}}
.pager button:disabled{{opacity:.4}}
#status{{padding:10px 18px;font-weight:bold}} table{{width:100%;border-collapse:collapse;background:white;font-size:13px}}
th{{position:sticky;top:112px;background:#eaf0f6;z-index:3}} th,td{{border:1px solid #d6dee8;padding:7px;vertical-align:top}}
td.crop{{width:330px}} td.crop img{{max-width:320px;max-height:95px;image-rendering:auto}}
.ok{{background:#e8f7ec}} .bad{{background:#fff0f0}} .tag{{display:inline-block;padding:2px 6px;border-radius:10px;font-size:11px;font-weight:bold}}
.revived{{background:#d8f3df;color:#087329}} .lost{{background:#ffdada;color:#b00020}} .still_wrong{{background:#fff2cc;color:#765800}}
.kept_correct{{background:#e7eef7;color:#33506f}} .muted{{color:#78889b}}
.changed{{color:#d00000;font-weight:800;background:#fff0a8}} .removed{{color:#d00000;font-weight:700;text-decoration:line-through;background:#ffe0e0}}
.reason{{line-height:1.55;min-width:320px}}
</style></head><body>
<header><h1>세파록스캡슐 학습의 `슬→슐` 교정과 과잉 적용</h1>
<div class="summary">세파록스캡슐 자체 26장은 제외 · 한 페이지 최대 50개 · <b>슬→슐만 바뀌고 틀림 {impacts['sl_to_shul_wrong']:,}개</b> · <b>슬→슐만 바뀌고 맞음 {impacts['sl_to_shul_correct']:,}개</b> · <b>슬을 그대로 잘 읽음 {impacts['sl_unchanged_correct']:,}개</b> · 다른 문자 변화가 섞인 사례는 제외</div>
<div class="tabs"><button class="tab active" data-tab="sl_to_shul_wrong">슐로 고쳤지만 틀림 ({impacts['sl_to_shul_wrong']:,})</button><button class="tab" data-tab="sl_to_shul_correct">슐로 고쳐서 맞음 ({impacts['sl_to_shul_correct']:,})</button><button class="tab" data-tab="sl_unchanged_correct">변환 없이 슬 그대로 정답 ({impacts['sl_unchanged_correct']:,})</button></div>
<div class="tools"><input id="q" placeholder="base·12배 출력 검색" size="28">
<button id="reset">초기화</button></div></header>
<div class="pager"><button id="prev">이전 50개</button><span id="status"></span><button id="next">다음 50개</button></div>
<table><thead><tr><th># / 영향</th><th>크롭 실물</th><th>base 출력</th><th>12배 출력</th><th>판정 설명</th></tr></thead><tbody id="rows"></tbody></table>
<script>const DATA={data};
const esc=s=>String(s).replace(/[&<>\"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[c]));
const PAGE_SIZE=50;let activeTab='sl_to_shul_wrong',page=0;
function render(){{let q=document.querySelector('#q').value.trim().toLowerCase();
 let all=DATA.filter(r=>r.tabs.includes(activeTab)&&(!q||[r.base,r.p12].join(' ').toLowerCase().includes(q)));let pages=Math.max(1,Math.ceil(all.length/PAGE_SIZE));page=Math.min(page,pages-1);
 let start=page*PAGE_SIZE,out=all.slice(start,start+PAGE_SIZE);
 const names={{sl_to_shul_wrong:'슐로 고쳤지만 틀림',sl_to_shul_correct:'슐로 고쳐서 맞음',sl_unchanged_correct:'변환 없이 슬 그대로 정답'}};
 document.querySelector('#status').textContent=`${{names[activeTab]}} · ${{all.length.toLocaleString()}}개 · ${{page+1}}/${{pages}}페이지`;
 document.querySelector('#prev').disabled=page===0;document.querySelector('#next').disabled=page>=pages-1;
 document.querySelector('#rows').innerHTML=out.map((r,i)=>`<tr><td><b>${{start+i+1}}</b><br><span class="tag ${{r.state12}}">${{r.state12}}</span></td><td class="crop">${{r.has_image?`<img loading="lazy" src="${{esc(r.image)}}">`:'<span class="muted">이미지 미연결</span>'}}</td><td class="${{r.base_ok?'ok':'bad'}}">${{r.base_html}}</td><td class="${{r.ok12?'ok':'bad'}}">${{r.p12_html}}</td><td class="reason">${{esc(r.reason)}}</td></tr>`).join('');}}
document.querySelectorAll('.tab').forEach(x=>x.onclick=()=>{{document.querySelectorAll('.tab').forEach(y=>y.classList.remove('active'));x.classList.add('active');activeTab=x.dataset.tab;page=0;render();}});
document.querySelector('#q').addEventListener('input',()=>{{page=0;render();}});document.querySelector('#prev').onclick=()=>{{page--;render();scrollTo(0,0);}};document.querySelector('#next').onclick=()=>{{page++;render();scrollTo(0,0);}};
document.querySelector('#reset').onclick=()=>{{document.querySelector('#q').value='';page=0;render();}};render();</script>
</body></html>"""
    OUTPUT.write_text(body, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, default=dict, indent=2))
    print(f"wrote {OUTPUT}")
    print(f"wrote {PATHS}")


if __name__ == "__main__":
    main()
