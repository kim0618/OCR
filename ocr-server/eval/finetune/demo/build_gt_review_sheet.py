"""기준 모델 손실의 GT 검수 시트 생성.

왜 필요한가 (2026-08-10):
  기준셋 GT 는 사람이 친 게 아니라 <구글 Document AI OCR 출력>이다. base(PP-OCRv5)도 OCR 이라
  둘이 같은 글자에서 같이 틀리면 GT==base 가 되어 '정답'으로 채점된다. 그 상태에서 FT 가
  인쇄대로 제대로 읽으면 오히려 '잃어버림'으로 집계된다.
  실측 사례: 인쇄 `1000IU` → GT `10001U`, base `10001U`, FT `1000IU`(정답인데 손실로 계상).
  품명에는 산술 같은 교차검증 오라클이 없어 사람 눈이 유일한 검증 수단이다.

무엇을 담는가:
  기준 모델(BASELINE)의 ①잃어버림 중 <표기 정규화로 해소되지 않는 것>만.
  표기만 다른 건은 GT 문제가 아니므로 검수 대상에서 뺀다(건수는 헤더에 표기).

진행분 이어하기:
  GT_REVIEW_PROGRESS.json 에 이전 판정과 완료 분류를 적어두면 그대로 채워서 연다.
  (2026-08-10 사고: 작업 중인 HTML 을 경고 없이 덮어써 판정이 날아갈 뻔했다.
   이후 출력 파일은 항상 백업 후 쓰고, 진행분은 파일로 남긴다.)

사용:
  python eval/finetune/demo/build_gt_review_sheet.py
  python eval/finetune/demo/build_gt_review_sheet.py --progress GT_REVIEW_PROGRESS.json
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recount_reviewed_gt import (  # noqa: E402
    HERE, comparable, load_policy, load_scan, name_key,
)

BASELINE = "260807_1302"
COMPARE = "260810_1037"          # 참고용 두 번째 FT(겨냥 앵커)
CROPS = Path(os.environ.get(
    "LOSS_CROPS_DIR",
    r"C:\Users\jinsung\AppData\Local\Temp\claude\d--Free-Vue"
    r"\ce98f7eb-f95c-4472-9e47-0f5fb2157dd4\scratchpad\crops548"))

# ★표기 정규화 - 채점 규약 후보(2026-08-10 시뮬레이션). GT·예측에 동일 적용이라
#  이미 맞던 건을 깨뜨리지 않는다(f(a)==f(b) 보장). ㈜ 규칙은 시뮬레이션에서
#  오히려 ①을 늘려 제외했다 - 재설계 전까지 넣지 않는다.
# ★선두 행번호: 모델이 구분자를 끼워 넣은 형태(`10-A-135-경보)`, `10-A157_경보)`)까지
#  걷어내야 한다. 구분자를 안 보던 초판은 이 15건을 검수 대상으로 잘못 올렸다.
NORM_RULES = [
    ("꼬리 문장부호", lambda s: re.sub(r"[.\-_/·,]+$", "", s)),
    ("곱셈기호", lambda s: re.sub(r"[×xX*]", "*", s)),
    ("선두 행번호", lambda s: re.sub(r"^\d{1,4}[-–_]?[A-Z]?[-–_]?\d{0,4}[-–_]?", "", s)),
    ("괄호 미종결", lambda s: s + ")" * max(0, s.count("(") - s.count(")"))),
]
# ★2차 검수(2026-08-10)에서 보강. 1차 셋은 대문자 I↔L 이 빠져 `BLI→BLL` 을 놓쳤다.
HOMOGLYPH = {("O", "0"), ("0", "O"), ("I", "l"), ("l", "I"), ("I", "1"), ("1", "I"),
             ("I", "L"), ("L", "I"), ("l", "1"), ("1", "l"), ("l", "L"), ("L", "l"),
             ("ㄱ", "7"), ("7", "ㄱ"), ("B", "8"), ("8", "B"), ("S", "5"), ("5", "S"),
             ("n", "m"), ("m", "n"), ("q", "g"), ("g", "q"), ("D", "0"), ("0", "D"),
             ("U", "V"), ("V", "U"), ("C", "G"), ("G", "C"), ("E", "F"), ("F", "E"),
             ("c", "e"), ("e", "c"), ("rn", "m")}
TAILMARK = re.compile(r"[가-힣)\]]\s*([B3])\s*$")
# 수기 마크는 얇은 획이라 1차 임계(red>=8 & 0.0015)로도 놓친 게 있었다
# (`환인메만틴오디정 10밀리그램` 끝 마크를 FT 가 `0` 으로 읽음). 임계를 낮춘다.
RED_MIN_PX, RED_MIN_RATIO = 5, 0.0008


def norm(text: str) -> str:
    v = comparable(text)
    for _, fn in NORM_RULES:
        v = fn(v)
    return v


def red_ratio(path: Path) -> tuple[float, int]:
    try:
        from PIL import Image
    except ImportError:
        return 0.0, 0
    im = Image.open(path).convert("RGB")
    px = im.load()
    red = 0
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = px[x, y]
            if r > 90 and r - g > 35 and r - b > 30:
                red += 1
    return red / max(1, im.width * im.height), red


def classify(gt: str, ft_preds: list[str], red: float, red_px: int,
             freq: dict[str, int] | None = None,
             agree: int = 0, agree_of: int = 0) -> tuple[str, str]:
    """(자동 제안, 근거). 제안이지 판정이 아니다 - 사람이 확정한다.

    ft_preds 에 base 를 넣으면 안 된다 - ①의 정의가 'base 예측 == GT' 라
    길이·문자 비교 신호가 통째로 죽는다(2026-08-10 실측: 크롭잘림 0건).
    """
    g, p = comparable(gt), comparable(ft_preds[0])
    if (red > RED_MIN_RATIO and red_px >= RED_MIN_PX) or TAILMARK.search(gt.strip()):
        return "수기마크", (f"빨간 잉크 {red_px}px" if red_px else "꼬리 단독 B·3")
    if len(g) == len(p):
        diff = [(a, b) for a, b in zip(g, p) if a != b]
        if len(diff) == 1 and tuple(diff[0]) in HOMOGLYPH:
            return "GT오류의심", f"동형 문자 {diff[0][0]}↔{diff[0][1]}"
    # ★희귀 GT: GT 문자열은 기준셋에 드문데 FT 예측은 정답으로 흔하다
    #  → GT 쪽이 오타일 확률이 높다(`제이메트서방정`(1) vs `제미메트서방정`(다수)).
    if freq:
        fg, fp = freq.get(g, 0), freq.get(p, 0)
        if fp >= 3 and fp >= fg * 3:
            return "GT오류의심", f"GT는 {fg}회뿐인데 FT 예측은 정답으로 {fp}회 등장"
    # ★FT 다수 합의: 서로 다르게 학습된 FT 들이 한 문자열로 모였는데 GT만 다름.
    #  base 는 정의상 GT 와 같으므로 신호에서 뺀다.
    if agree_of >= 3 and agree >= agree_of - 0:
        return "합의불일치", f"FT {agree}/{agree_of} 이 같은 답, GT만 다름"
    ft = [len(comparable(x)) for x in ft_preds if x]
    if ft and len(g) - max(ft) >= 4:
        return "크롭잘림", f"GT가 FT 예측보다 {len(g) - max(ft)}자 김"
    return "모델오독", "인쇄·GT 일치 시 모델 책임"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--progress", default="GT_REVIEW_PROGRESS.json",
                    help="이전 판정·완료 분류. 없으면 무시")
    ap.add_argument("--out", default="GT_REVIEW_SHEET.html")
    ap.add_argument("--only", default="",
                    help="쉼표로 구분한 자동 제안 종류만 담는다(2차 검수용). "
                         "예: 수기마크,GT오류의심,합의불일치,크롭잘림")
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    prog_path = HERE / args.progress
    done_map, reviewed_kinds = {}, set()
    if prog_path.exists():
        prog = json.loads(prog_path.read_text(encoding="utf-8"))
        done_map = {j["path"]: j for j in prog.get("judgments", [])}
        reviewed_kinds = set(prog.get("reviewedKinds", []))
        print(f"[진행분] {prog_path.name}: 판정 {len(done_map)}건 · "
              f"완료 분류 {sorted(reviewed_kinds)}")

    keep = {line.strip() for line
            in (HERE / "basis_keep.txt").read_text(encoding="utf-8").splitlines()
            if line.strip()}
    overrides, excluded, _ = load_policy()
    base = load_scan("000_base.jsonl", keep)
    ref = load_scan(f"{BASELINE}.jsonl", keep)
    cmp_scan = load_scan(f"{COMPARE}.jsonl", keep) if (
        HERE / "scans" / f"{COMPARE}.jsonl").exists() else {}
    # ★FT 다수 합의 신호용 - 앵커 구성이 서로 다른 FT 들을 모은다(base 는 제외).
    agree_scans = []
    for tag in ("260807_1440", "260805_1341", "260804_1623", COMPARE):
        f = HERE / "scans" / f"{tag}.jsonl"
        if tag != BASELINE and f.exists():
            agree_scans.append(load_scan(f.name, keep))

    # ★기준셋 전체에서 <정답으로 확정된 GT 문자열>의 출현 빈도. 희귀 GT 신호의 모수다.
    freq: Counter = Counter()
    for path, brow in base.items():
        key = name_key(brow["gt"])
        if key not in excluded:
            freq[comparable(overrides.get(key, brow["gt"]))] += 1

    rows, notation_only = [], 0
    for path, brow in base.items():
        key = name_key(brow["gt"])
        if key in excluded or path not in ref:
            continue
        gt = overrides.get(key, brow["gt"])
        if comparable(gt) != comparable(brow["pred"]):
            continue                                   # base 가 못 읽음 = ①이 아님
        if comparable(gt) == comparable(ref[path]["pred"]):
            continue                                   # 손실 아님
        if norm(gt) == norm(ref[path]["pred"]):
            notation_only += 1                         # 표기 정규화로 해소 - 검수 불필요
            continue
        rows.append({"path": path, "gt": gt, "base": brow["pred"],
                     "ref": ref[path]["pred"],
                     "cmp": cmp_scan.get(path, {}).get("pred", "")})

    # ★크롭 실물은 임시 폴더에 두면 날아간다(2026-08-10: 시트를 다시 만들었더니 442건
    #  전부 '크롭 없음'). 아카이브를 레포에 두고 없으면 자동으로 푼다.
    if not any(CROPS.rglob("*.jpg")):
        arc = HERE / "verify" / f"loss548_crops_{BASELINE}.tgz"
        if not arc.exists():
            raise SystemExit(
                f"★크롭이 없습니다: {CROPS}\n  아카이브도 없습니다: {arc}\n"
                "  AWS 에서 해당 경로들을 tar 로 받아 그 위치에 둘 것.")
        import tarfile
        CROPS.mkdir(parents=True, exist_ok=True)
        with tarfile.open(arc) as t:
            t.extractall(CROPS)
        print(f"[크롭] {arc.name} → {CROPS} 자동 추출")
    missing = 0
    for r in rows:
        f = CROPS / r["path"].replace("/", os.sep)
        if f.exists():
            r["red"], r["redpx"] = red_ratio(f)
            r["img"] = "data:image/jpeg;base64," + base64.b64encode(
                f.read_bytes()).decode("ascii")
        else:
            r["red"], r["redpx"], r["img"] = 0.0, 0, ""
            missing += 1
        preds = [comparable(s[r["path"]]["pred"]) for s in agree_scans
                 if r["path"] in s]
        top = Counter(preds).most_common(1)
        agree = top[0][1] if (top and top[0][0] != comparable(r["gt"])) else 0
        r["kind"], r["why"] = classify(
            r["gt"], [r["ref"], r["cmp"]], r["red"], r["redpx"],
            freq=freq, agree=agree, agree_of=len(preds))
        # 이전 판정 반영: 고친 GT 를 채우고, 그 분류 전체를 끝냈으면 '완료'로 표시
        j = done_map.get(r["path"])
        r["fixed"] = j["final_gt"] if j else ""
        r["done"] = bool(j) or r["kind"] in reviewed_kinds

    order = {"수기마크": 0, "GT오류의심": 1, "합의불일치": 2, "크롭잘림": 3, "모델오독": 4}
    if only:
        dropped = len(rows) - sum(1 for r in rows if r["kind"] in only)
        rows = [r for r in rows if r["kind"] in only]
        print(f"[필터] --only {sorted(only)} → {len(rows)}건 (제외 {dropped}건)")
    rows.sort(key=lambda r: (order[r["kind"]], r["gt"]))
    counts = Counter(r["kind"] for r in rows)
    n_done = sum(1 for r in rows if r["done"])

    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    tr = []
    for i, r in enumerate(rows):
        img = (f'<img src="{r["img"]}">' if r["img"]
               else '<span class=no>크롭 없음</span>')
        val = r["fixed"] or r["gt"]
        checked = "fix" if r["fixed"] and r["fixed"] != r["gt"] else "keep"
        cls = ' class="done"' if r["done"] else ""
        tr.append(
            f'<tr data-kind="{r["kind"]}" data-done="{int(r["done"])}"{cls}>'
            f'<td class=n>{i + 1}</td>'
            f'<td class=k>{r["kind"]}<br><span class=why>{esc(r["why"])}</span></td>'
            f'<td class=c>{img}</td>'
            f'<td><input class=gt value="{esc(val)}" data-orig="{esc(r["gt"])}"'
            f' data-path="{esc(r["path"])}"></td>'
            f'<td class=p>{esc(r["base"])}</td><td class=p>{esc(r["ref"])}</td>'
            f'<td class=p>{esc(r["cmp"])}</td>'
            f'<td class=v>'
            f'<label><input type=radio name="v{i}" value="keep"'
            f'{" checked" if checked == "keep" else ""}>유지</label>'
            f'<label><input type=radio name="v{i}" value="fix"'
            f'{" checked" if checked == "fix" else ""}>GT수정</label>'
            f'<label><input type=radio name="v{i}" value="exclude">제외</label></td></tr>')

    html = f"""<!doctype html><meta charset="utf-8">
<title>GT 검수 - {BASELINE} 손실 {len(rows)}건</title>
<style>
body{{font-family:'Malgun Gothic',sans-serif;margin:20px;color:#111;background:#fff}}
h1{{font-size:19px;margin:0 0 6px}} .sum{{color:#555;font-size:13px;line-height:1.7;margin-bottom:14px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border:1px solid #ddd;padding:5px 7px;vertical-align:middle}}
th{{background:#f4f4f4;position:sticky;top:0;z-index:2}}
img{{max-height:40px;image-rendering:crisp-edges}}
.n{{color:#999;width:38px}} .k{{width:120px;font-size:12px}} .why{{color:#888;font-size:11px}}
.c{{width:330px}} .p{{font-family:Consolas,monospace;font-size:12px;color:#444}}
.gt{{width:100%;font-size:13px;padding:3px;border:1px solid #ccc}}
.v label{{display:block;font-size:12px;white-space:nowrap}} .v{{width:92px}}
.no{{color:#c60;font-size:12px}}
tr.done{{opacity:.45}} tr.done td.n:after{{content:" ✓";color:#0a7}}
#bar{{position:sticky;bottom:0;background:#fff;border-top:2px solid #333;padding:10px 0;margin-top:12px}}
button{{font-size:14px;padding:7px 16px;cursor:pointer;margin-right:8px}}
textarea{{width:100%;height:130px;font-family:Consolas,monospace;font-size:11px;margin-top:8px}}
tr[data-kind="수기마크"]{{background:#fff7e6}} tr[data-kind="GT오류의심"]{{background:#eef7ff}}
tr[data-kind="크롭잘림"]{{background:#f6f0ff}}
</style>
<h1>GT 검수 — 기준 모델 <code>{BASELINE}</code> 잃어버림 {len(rows)}건
<span style="font-size:14px;color:#0a7">(검토 완료 {n_done} · 남은 {len(rows) - n_done})</span></h1>
<div class=sum>
GT 는 구글 Document AI OCR 출력이고 base 도 OCR 이라, 둘이 같이 틀리면 GT==base 가 되어
'정답'으로 채점됩니다. 그 상태에서 FT 가 인쇄대로 읽으면 오히려 손실로 집계됩니다
(실측: 인쇄 <code>1000IU</code> → GT <code>10001U</code>, base <code>10001U</code>, FT <code>1000IU</code>).
<b>크롭에 인쇄된 글자만 보고 판정</b>하세요.<br>
· <b>유지</b> = GT 가 인쇄와 맞음 → 모델이 틀린 것(진짜 잃어버림)<br>
· <b>GT수정</b> = GT 가 인쇄와 다름 → 왼쪽 칸을 인쇄대로 고침 (<b>글자를 고치면 자동으로 선택됨</b>)<br>
· <b>제외</b> = 크롭이 잘렸거나 판독 불가 → 평가에서 뺌<br>
자동 제안: {' · '.join(f'{k} {v}' for k, v in counts.most_common())}
&nbsp;|&nbsp; 표기 정규화로 해소되어 검수에서 뺀 건 {notation_only}건
{f'&nbsp;|&nbsp; <b>크롭 없음 {missing}건</b>' if missing else ''}<br>
✓ 표시(흐린 행)는 이전에 판정하신 건입니다. <b>다음 미판정으로</b> 버튼으로 이어서 하세요.
</div>
<table><tr><th>#</th><th>자동 제안</th><th>크롭 실물</th><th>GT(수정 가능)</th>
<th>base</th><th>{BASELINE}</th><th>{COMPARE}</th><th>판정</th></tr>
{chr(10).join(tr)}
</table>
<div id=bar>
<button onclick="jump()">다음 미판정으로</button>
<button onclick="dump()">판정 JSON 복사</button>
<span id=stat style="color:#555"></span>
<textarea id=out placeholder="여기에 결과가 나옵니다"></textarea></div>
<script>
const trs=[...document.querySelectorAll('table tr')].filter(r=>r.querySelector('.gt'));
// ★GT 칸을 고치면 라디오를 자동으로 'GT수정'으로 옮긴다.
//  안 그러면 글자만 고치고 라디오를 안 눌러 판정이 통째로 누락된다(2026-08-10 실제 사고).
trs.forEach(r=>{{
  const inp=r.querySelector('.gt');
  inp.addEventListener('input',()=>{{
    const changed=inp.value.trim()!==inp.dataset.orig.trim();
    const t=r.querySelector('input[type=radio][value="'+(changed?'fix':'keep')+'"]');
    if(t) t.checked=true;
    r.dataset.done='1'; r.classList.remove('done');
    r.style.boxShadow=changed?'inset 4px 0 0 #0a7':'';
  }});
  r.querySelectorAll('input[type=radio]').forEach(rd=>rd.addEventListener('change',()=>{{
    r.dataset.done='1'; r.classList.remove('done');
  }}));
}});
function jump(){{
  const t=trs.find(r=>r.dataset.done!=='1');
  if(!t){{ alert('남은 미판정 행이 없습니다.'); return; }}
  t.scrollIntoView({{block:'center'}});
  t.style.outline='3px solid #f60';
  setTimeout(()=>t.style.outline='',1500);
}}
function dump(){{
  const out=[]; let fix=0, exc=0, warn=0;
  trs.forEach(r=>{{
    const inp=r.querySelector('.gt');
    const orig=inp.dataset.orig;
    const changed=inp.value.trim()!==orig.trim();
    let v=r.querySelector('input[type=radio]:checked').value;
    if(changed && v==='keep') v='fix';       // 글자를 고쳤으면 라디오와 무관하게 수정으로 본다
    if(v==='fix' && !changed) {{ warn++; return; }}
    if(v==='keep') return;
    if(v==='fix') fix++; else exc++;
    out.push({{path:inp.dataset.path, status:(v==='fix'?'approved':'exclude'),
               old_gt:orig, final_gt:inp.value.trim()}});
  }});
  document.getElementById('out').value=JSON.stringify(out,null,1);
  document.getElementById('stat').textContent=
    'GT수정 '+fix+' / 제외 '+exc+' / 유지 '+(trs.length-fix-exc-warn)
    + (warn? '   ★GT수정인데 글자 안 고친 '+warn+'건 제외':'');
  document.getElementById('out').select();
}}
</script>"""

    out_path = HERE / args.out
    if out_path.exists():                 # ★작업 중 파일을 말없이 덮지 않는다
        bak = out_path.with_suffix(f".{time.strftime('%y%m%d_%H%M%S')}.bak.html")
        shutil.copy2(out_path, bak)
        print(f"[백업] 기존 시트 → {bak.name}")
    out_path.write_text(html, encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"  검수 대상 {len(rows)}건 (완료 {n_done} / 남은 {len(rows) - n_done}) "
          f"· 표기 정규화로 제외 {notation_only}건"
          + (f" · 크롭 없음 {missing}건" if missing else ""))
    for k, v in counts.most_common():
        d = sum(1 for r in rows if r["kind"] == k and r["done"])
        print(f"    {k:<12} {v:>4}  (완료 {d})")


if __name__ == "__main__":
    main()
