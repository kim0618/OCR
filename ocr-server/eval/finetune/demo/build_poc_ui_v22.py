"""고객 POC 화면(5단계)을 v22 실측으로 채워 생성한다.

실측으로 채우는 것 - 품명 관련 전부:
  - 4개 품명의 base / 학습 모델 판독 문자열
  - 검증 위치 38개의 판독 결과 (base 9 -> 학습 38)
  - 실제 인식 크롭 이미지(리포트의 imgB64)

예시로 두는 것 - 문서 정보 필드(상호/대표/누계 등):
  고객 문서가 로컬에 없으므로 화면에 <예시>로 명시한다. 섞어 읽지 않도록
  표마다 기준을 적는다.

    python eval/finetune/demo/build_poc_ui_v22.py
"""
from __future__ import annotations

import argparse
import base64
import io as _io
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recount_reviewed_gt import HERE, comparable  # noqa: E402

RUN = "260811_1105_wf80"
SRC_STYLE = HERE.parents[3] / "docs" / "POC_UI_PRODUCT_20260812.html"
OUT = HERE.parents[3] / "docs" / "POC_UI_V22_20260812.html"



REAL_IMG = Path(r"D:\OCR학습자료\2606\471814\20260618135314_0008.jpg")
REAL_GT = HERE.parents[1] / "data" / "invoice_war" / "ground_truth_2606.json"
REAL_KEY = "471814/20260618135314_0008.jpg"
# 원본은 바탕화면 밖에 있어 옮겨지면 사라진다. 한 번 읽으면 여기에 남겨 두고 이후로는 이걸 쓴다.
SCAN_CACHE = HERE / "assets" / "scan_20260618135314_0008_1800.b64"


def scan_b64(path: Path, width: int = 1800, quality: int = 72) -> str:
    """스캔본을 화면 폭에 맞춰 줄인다. 원본 2490px 그대로 심으면 파일이 커진다."""
    if not path.exists():
        if SCAN_CACHE.exists():
            return SCAN_CACHE.read_text(encoding="ascii")
        raise SystemExit(f"스캔본도 캐시도 없습니다: {path}")
    from PIL import Image
    im = Image.open(path)
    if im.mode != "RGB":
        im = im.convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = _io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)
    out = base64.b64encode(buf.getvalue()).decode()
    SCAN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SCAN_CACHE.write_text(out, encoding="ascii")
    return out


def esc(x: str) -> str:
    return x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_report(run: str) -> dict:
    d = next((p for p in HERE.glob(f"*_{run}") if p.is_dir()), None)
    if d is None:
        raise SystemExit(f"리포트 폴더가 없습니다: demo/*_{run}")
    return json.loads((d / f"DEMO_REPORT_{run}.json").read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=RUN)
    args = ap.parse_args()
    rep = load_report(args.run)

    # ---- 타깃별 실측 요약 ----
    T = []
    for t in rep["targets"]:
        rows = t["rows"]
        v = t["verdict"]
        wrong = next((r for r in rows if comparable(r["base"]) != comparable(r["gt"])), None)
        sample = wrong or rows[0]
        T.append({
            "name": t["name"], "role": t.get("role", ""), "isNew": bool(t.get("isNew")),
            "n": v["n"], "base": v["base"], "ft": v["ft"],
            "baseTxt": sample["base"], "gtTxt": sample["gt"], "ftTxt": sample["finetuned"],
            "img": sample["imgB64"], "path": sample["path"],
            "misread": wrong is not None,
        })
    # 타깃별 판독 분포 - 같은 품명을 몇 가지로 읽었는지
    for t, x in zip(rep["targets"], T):
        rows = t["rows"]
        bset, fset = {}, {}
        for r in rows:
            bset[r["base"]] = bset.get(r["base"], 0) + 1
            fset[r["finetuned"]] = fset.get(r["finetuned"], 0) + 1
        x["bKinds"] = sorted(bset.items(), key=lambda kv: -kv[1])
        x["fKinds"] = sorted(fset.items(), key=lambda kv: -kv[1])

    itp = rep.get("interpolation") or {}
    pool = rep.get("pool") or {}
    tot_n = sum(x["n"] for x in T)
    tot_b = sum(x["base"] for x in T)
    tot_f = sum(x["ft"] for x in T)
    misread = [x for x in T if x["misread"]]

    style = re.search(r"<style>.*?</style>", SRC_STYLE.read_text(encoding="utf-8"), re.S).group(0)
    # 카드 헤더 높이를 통일해 좌우 표의 시작 줄을 맞춘다
    style = style.replace(".card-h{display:flex;align-items:center;",
                          ".card-h{min-height:54px;display:flex;align-items:center;")
    style = style.replace("<style>", '<style>\n/* ── 시맨틱 색 : 제품 토큰(--accent 등) 위에 얹는다. 다크에서 각각 다시 정의 ── */\n:root{\n  --ok:#16a34a;   --okBg:rgba(22,163,74,.12);\n  --warn:#d97706; --warnBg:rgba(217,119,6,.13);\n  --err:#dc2626;  --errBg:rgba(220,38,38,.12);\n  --rule:#4f6ba8; --ruleBg:rgba(79,107,168,.12);\n  --r1:#0f9d8e; --r1Bg:rgba(15,157,142,.08);\n  --r2:#4f6ba8; --r2Bg:rgba(79,107,168,.08);\n  --r3:#7c8496; --r3Bg:rgba(124,132,150,.09);\n  --focus:0 0 0 3px rgba(8,145,178,.28);\n}\n[data-theme=dark]{\n  --ok:#4ade80;   --okBg:rgba(74,222,128,.14);\n  --warn:#fbbf24; --warnBg:rgba(251,191,36,.14);\n  --err:#f87171;  --errBg:rgba(248,113,113,.14);\n  --rule:#93b4f5; --ruleBg:rgba(147,180,245,.14);\n  --r1:#2dd4bf; --r1Bg:rgba(45,212,191,.10);\n  --r2:#93b4f5; --r2Bg:rgba(147,180,245,.10);\n  --r3:#9aa4b5; --r3Bg:rgba(154,164,181,.10);\n  --focus:0 0 0 3px rgba(6,182,212,.34);\n}\n', 1)
    style = style.replace("</style>", """
.scan{width:100%;max-width:640px;aspect-ratio:2490/3510;display:block;background:#fff;
 background-image:var(--scan);background-size:contain;background-repeat:no-repeat;
 background-position:top center;box-shadow:0 6px 26px rgba(0,0,0,.22);border-radius:2px}
.rawocr{border-top:1px solid var(--border);flex:none}
.rawocr summary{padding:10px 13px;cursor:pointer;font-size:11.5px;font-weight:800;
 color:var(--muted);list-style:none}
.rawocr summary::-webkit-details-marker{display:none}
.rawocr summary::before{content:"▶ ";font-size:9px}
.rawocr[open] summary::before{content:"▼ "}
.rawbody{max-height:190px;overflow:auto;padding:0 13px 12px;font-size:11px;line-height:1.7}
.rawline{display:flex;gap:9px;color:var(--text)}
.rawline i{font-style:normal;color:var(--muted);width:22px;text-align:right;flex:none;
 font-variant-numeric:tabular-nums}
.valflag{margin:-2px 0 8px 19px;font-size:10.5px;font-weight:700;color:var(--warn)}
.sig{font-size:10px;color:var(--muted);font-weight:700;margin-top:3px}
.nocrop{display:inline-flex;align-items:center;height:22px;padding:0 9px;border-radius:6px;
 border:1px dashed var(--border);background:var(--panel2);color:var(--muted);
 font-size:10.5px;font-weight:700}
.nocrop.err{border-style:solid;border-color:var(--err);color:var(--err);background:var(--errBg)}
.crop{height:22px;width:auto;max-width:190px;border-radius:3px;display:block;background:#fff}
.cropbig{height:34px;width:auto;max-width:100%;border-radius:4px;background:#fff}
/* 처리 경로 3구간 - 색으로 갈라 놓는다 */
.upstate{display:none;flex:1;min-height:0;flex-direction:column}
.upstate.on{display:flex}
.dropzone{flex:1;min-height:0;margin:13px;border:2px dashed var(--border);border-radius:12px;
 background:var(--panel2);display:flex;flex-direction:column;align-items:center;
 justify-content:center;text-align:center;padding:26px}
.dropzone:hover{border-color:var(--accent)}
.dz-ic{width:56px;height:56px;border-radius:50%;background:var(--accentBg);color:var(--accent);
 display:grid;place-items:center;font-size:24px;margin-bottom:14px}
.dz-t{font-size:15px;font-weight:800}
.dz-s{font-size:11.5px;color:var(--muted);margin-top:5px}
.runbtn:disabled{background:var(--panel2);border-color:var(--border);color:var(--muted);cursor:default}
.ltool{display:flex;align-items:center;gap:10px;padding:11px 13px;
 border-bottom:1px solid var(--border);flex:none;flex-wrap:wrap}
/* 필드 표 공통 툴바 - 필드가 수십 개로 늘어도 찾아갈 수 있게 */
.ftool{display:flex;align-items:center;gap:9px;padding:10px 13px;
 border-bottom:1px solid var(--border);flex:none;flex-wrap:wrap}
.ftool .fc{margin-left:auto;font-size:11.5px;color:var(--muted);font-weight:700}
.lpage{display:flex;align-items:center;justify-content:flex-end;gap:12px;padding:9px 13px;
 border-top:1px solid var(--border);flex:none}
.lpage .lcount{font-size:11.5px;color:var(--muted);font-weight:700}
.pager{display:inline-flex;align-items:stretch;border:1px solid var(--border);border-radius:9px;
 overflow:hidden;background:var(--panel);height:30px}
.pager button{border:0;background:transparent;color:var(--text);cursor:pointer;font:inherit;
 font-size:14px;width:32px;display:grid;place-items:center}
.pager button:hover:not(:disabled){background:var(--panel2);color:var(--accent)}
.pager button:disabled{color:var(--muted);opacity:.35;cursor:default}
.pager .pg{padding:0 12px;display:grid;place-items:center;font-size:11.5px;font-weight:800;
 color:var(--muted);border-left:1px solid var(--border);border-right:1px solid var(--border);
 min-width:56px}
.ltool .lcount{margin-left:auto;font-size:11.5px;color:var(--muted);font-weight:700}
.rtabs{display:flex;gap:8px;flex:none}
.rtab{flex:1;border:1px solid var(--border);border-top:4px solid var(--rc);border-radius:12px 12px 0 0;
 background:var(--panel);padding:12px 15px;cursor:pointer;font-family:inherit;text-align:left;
 display:flex;align-items:center;gap:11px;opacity:.55;transition:opacity .12s,background .12s}
.rtab:hover{opacity:.8}
.rtab.on{opacity:1;background:var(--rcbg);box-shadow:var(--shadowSoft)}
.rtab .rno{width:26px;height:26px;border-radius:50%;background:var(--rc);color:#fff;display:grid;
 place-items:center;font-size:11px;font-weight:900;flex:none}
.rtab .rt{font-size:14px;font-weight:900;color:var(--rc)}
.rtab .rd{font-size:10.5px;color:var(--muted);margin-top:1px}
.rtab .rbig{margin-left:auto;font-size:20px;font-weight:900;color:var(--rc);letter-spacing:-.03em}
.rpane{display:none;flex:1;min-height:0;flex-direction:column}
.rpane.on{display:flex}
.route{border-top:4px solid var(--rc);position:relative}
.route .rh{display:flex;align-items:center;gap:11px;padding:13px 15px;
 background:var(--rcbg);border-bottom:1px solid var(--border)}
.route .rno{width:28px;height:28px;border-radius:50%;background:var(--rc);color:#fff;
 display:grid;place-items:center;font-size:12px;font-weight:900;flex:none}
.route .rt{font-size:15px;font-weight:900;color:var(--rc)}
.route .rd{font-size:11.5px;color:var(--muted);margin-top:1px}
.route .rn{margin-left:auto;display:flex;align-items:center;gap:8px}
.route .rbig{font-size:22px;font-weight:900;color:var(--rc);letter-spacing:-.03em}
.route .sub{padding:9px 15px;background:var(--rcbg);font-size:11.5px;color:var(--muted);
 border-top:1px solid var(--border);border-bottom:1px solid var(--border);font-weight:600}
.r1{--rc:var(--r1);--rcbg:var(--r1Bg)}
.r2{--rc:var(--r2);--rcbg:var(--r2Bg)}
.r3{--rc:var(--r3);--rcbg:var(--r3Bg)}
.srcbar{display:flex;gap:6px;align-items:center;flex-wrap:wrap;padding:9px 13px;
 border-bottom:1px solid var(--border);flex:none;font-size:11px;color:var(--muted)}

/* ── 마감 ── */
*:focus-visible{outline:0;box-shadow:var(--focus);border-radius:8px}
.ms-btn,.ms-btn-sm,.ms-input,.ms-select{transition:border-color .12s,background .12s,color .12s}
.card{transition:box-shadow .15s}
th{letter-spacing:.01em}
td:first-child{font-weight:600}
tbody tr.tot td{border-top:1px solid var(--border)}
.kpi{transition:box-shadow .15s}
.kpi:hover{box-shadow:var(--shadow)}
.tag{line-height:1.35}
.crop{box-shadow:0 0 0 1px var(--border)}
.paper{border-radius:2px}
.doc{background:
  linear-gradient(0deg,var(--panel2),var(--panel2)),
  radial-gradient(circle at 50% 0,rgba(0,0,0,.05),transparent 60%)}
.ortab,.rtab,.seg button,.nav a{transition:background .12s,color .12s,opacity .12s}
.pager button{transition:background .12s,color .12s}
.dropzone{transition:border-color .15s,background .15s}
.dropzone:hover{background:var(--accentBg)}
.runbtn{transition:filter .12s}
.runbtn:not(:disabled):hover{filter:brightness(1.06)}
.side-foot,.lcount{font-variant-numeric:tabular-nums}
.tpbar{display:flex;gap:12px;align-items:center;background:var(--panel);
 border:1px solid var(--border);border-radius:12px;padding:6px 14px;flex-shrink:0}
.tpmode{display:flex;flex-direction:column;gap:8px;flex-shrink:0}
.mcard{width:120px;height:32px;border-radius:8px;border:1px solid var(--border);
 background:var(--panel2);color:var(--muted);cursor:pointer;display:flex;align-items:center;
 justify-content:center;gap:6px;font-size:11px;font-weight:700;letter-spacing:.3px;
 transition:border-color .15s,background .15s,color .15s}
.mcard:hover{border-color:var(--accent);color:var(--accent)}
.mcard.on{border-color:var(--accent);background:var(--accentBg);color:var(--accent)}
.tpdiv{width:1px;height:68px;background:var(--border);flex-shrink:0}
.tpsaved{flex:1;min-width:0;display:flex;align-items:center;gap:10px;overflow-x:auto}
.tmpane{display:none}
.tmpane.on{display:flex;flex-direction:column;flex:1;min-height:0}
.antb{display:flex;gap:6px;align-items:center;flex-wrap:wrap;padding:9px 12px;
 border-bottom:1px solid var(--border)}
.mbtn{height:26px;padding:0 10px;border-radius:6px;border:1px solid var(--border);
 background:var(--panel2);color:var(--text);font-size:11px;font-weight:600;cursor:pointer}
.mbtn:hover{border-color:var(--accent);color:var(--accent)}
.mbtn.on{border-color:var(--accent);background:var(--accentBg);color:var(--accent)}
#tm-reg .doc{flex:1;min-height:0;overflow:auto}
.cvs{position:relative;width:100%;max-width:940px;margin:0 auto}
.cvs .scan{max-width:100%}
.rgn{position:absolute;border:1.5px solid var(--accent);background:rgba(8,145,178,.10);
 border-radius:2px}
.rgn>i{position:absolute;top:-9px;left:-9px;width:17px;height:17px;border-radius:50%;
 display:flex;align-items:center;justify-content:center;font-style:normal;font-size:9px;
 font-weight:800;line-height:1;background:var(--accent);color:#fff;box-shadow:0 0 0 2px #fff}
.rgn.tb{border-color:#7c3aed;background:rgba(124,58,237,.07)}
.rgn.tb>i{background:#7c3aed}
.rgn.hi{background:rgba(8,145,178,.24);border-width:2px;
 box-shadow:0 0 0 3px rgba(8,145,178,.18)}
#runCvs .rgn{border-color:transparent;background:transparent}
#runCvs .rgn.hi{border-color:var(--accent)}
tr.pick td{background:var(--accentBg)}
#v-run tbody tr[data-fb]{cursor:pointer}
#v-detail tbody tr[data-fb]{cursor:pointer;user-select:none}
#v-detail tbody tr[data-fb] input{user-select:text}
/* 표 머리 행이 스크롤을 따라온다. 23행을 내려가도 어느 칸이 수량인지 안다. */
#v-detail .scroll thead th{position:sticky;top:0;z-index:3;background:var(--panel)}
.zexp{display:none}
.zexp.on{display:table-row}
.zexp>td{padding:0 !important;background:var(--accentBg)}
.zpair{display:flex;flex-direction:column;gap:1px;padding:8px 10px}
.zrow{position:relative;overflow:hidden;height:52px;border-radius:6px;
 background:var(--panel2);border:1px solid var(--border)}
.zimg{position:absolute;display:none;background-image:var(--scan);background-size:100% 100%;
 background-repeat:no-repeat;transform-origin:center}
.zlab{position:absolute;z-index:2;left:6px;top:5px;font-size:9px;font-weight:800;
 color:var(--muted);background:var(--panel);border:1px solid var(--border);
 border-radius:4px;padding:1px 5px}
.znone{display:none;padding:12px;font-size:11.5px;color:var(--muted);font-weight:600}
.loopbar{display:flex;flex-wrap:wrap;align-items:center;gap:7px;padding:10px 13px;
 border-bottom:1px solid var(--border)}
.lstep{height:24px;display:inline-flex;align-items:center;padding:0 10px;border-radius:7px;
 border:1px solid var(--border);background:var(--panel2);font-size:11px;font-weight:700;
 color:var(--text)}
.larr{color:var(--muted);font-size:11px}
.levi{margin-left:auto;display:flex;gap:16px;align-items:center;font-size:11px;
 color:var(--muted);font-weight:600}
.levi b{color:var(--ok)}
.declines{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:9px 13px;
 border-bottom:1px solid var(--border)}
.dc{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:700;
 color:var(--text);background:var(--panel2);border:1px solid var(--border);
 border-radius:7px;padding:4px 10px}
.dc b{color:var(--accent)}
.dc.mu{color:var(--muted)}
.dc.mu b{color:var(--muted)}
.tplcard .thumb{background-size:cover;background-position:center;background-repeat:no-repeat}
.tplcard.reg .thumb{background-image:var(--scan);background-position:top center}
.fnchip{font-size:11px;font-weight:700;color:var(--text);background:var(--panel2);
 border:1px solid var(--border);border-radius:7px;padding:4px 9px;max-width:60%;
 overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.frow2{display:flex;align-items:center;justify-content:space-between;gap:10px;
 padding:5px 0;font-size:11.5px;color:var(--muted)}
.frow2 b{color:var(--text);font-weight:700;overflow:hidden;text-overflow:ellipsis;
 white-space:nowrap}
.dmhelp{padding:7px 13px;font-size:11px;color:var(--muted);border-bottom:1px solid var(--border)}
.fclist{padding:10px 13px;display:flex;flex-direction:column;gap:8px}
.fcard{border:1px solid var(--border);border-radius:10px;background:var(--panel2);
 padding:9px 10px;cursor:pointer}
.fcard.bad{border-color:var(--warn);background:var(--warnBg)}
.fcard.pick{border-color:var(--accent);box-shadow:0 0 0 2px var(--accentBg)}
.fch{display:flex;align-items:center;gap:7px}
.fcn{flex:1;min-width:0;font-size:11px;font-weight:800;color:var(--text);
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fcn em{font-style:normal;font-size:9px;font-weight:400;color:var(--muted);margin-left:4px}
.fcsel{height:22px;border-radius:6px;border:1px solid var(--border);background:var(--panel);
 color:var(--text);font-size:10px;padding:0 4px}
.fcbar{width:54px;height:5px;border-radius:3px;background:var(--border);overflow:hidden;
 flex-shrink:0}
.fcbar i{display:block;height:100%}
.fcpct{font-size:10px;font-weight:800;font-variant-numeric:tabular-nums;min-width:52px;
 text-align:right}
.fcad{font-size:10px;font-weight:900;min-width:30px;text-align:center}
.fcx{width:20px;height:20px;border-radius:5px;border:1px solid var(--border);
 background:var(--panel);color:var(--muted);font-size:9px;cursor:pointer;flex-shrink:0}
.fcx:hover{border-color:var(--err);color:var(--err)}
.fcv{margin-top:7px}
.fcm{display:flex;gap:12px;font-size:10px;color:var(--muted);margin-bottom:5px}
.fcv label{display:block;font-size:10px;font-weight:800;color:var(--muted);margin-bottom:3px}
.fcin{width:100%;box-sizing:border-box;height:27px;border-radius:6px;
 border:1px solid var(--border);background:var(--panel);color:var(--text);
 font-size:11px;padding:0 8px}
.fcin.bad{border-color:var(--accent);background:var(--accentBg)}
.fcard table{margin-top:8px}
.rgn.tb.hi{background:rgba(124,58,237,.18)}
.cg{position:absolute;width:0;border-left:1.5px dashed #7c3aed;opacity:.8}
.tpcol{display:flex;flex-direction:column;gap:8px;min-height:0}
.savebar{flex-shrink:0;display:flex;gap:8px;justify-content:flex-end;align-items:center;
 background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:10px 12px;
 box-shadow:var(--shadow)}
.savebar .go{background:var(--accent);border-color:var(--accent);color:#fff}
.opanel{flex:1;min-height:0;overflow:auto;background:var(--panel);border:1px solid var(--border);
 border-radius:12px;padding:12px;box-shadow:var(--shadow)}
.oclab{font-size:11px;font-weight:800;color:var(--muted);letter-spacing:.3px;margin:0 0 5px}
.osec{margin-top:14px;padding-top:12px;border-top:1px solid var(--border)}
.sech{display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:8px}
.sect{font-size:13px;font-weight:800;color:var(--text);margin:0}
.g3,.g4{display:grid;gap:6px;align-items:center;padding:7px 8px;border-radius:10px;
 border:1px solid var(--border);background:var(--panel2);margin-bottom:6px}
.g3{grid-template-columns:28px 1fr 1fr}
.g4{grid-template-columns:28px 1.1fr 1fr 1fr;padding:6px 8px;border-radius:8px;background:var(--panel)}
.g3.hd,.g4.hd{background:var(--panel2)}
.g3.hd span,.g4.hd span{font-size:11px;font-weight:800;color:var(--muted);text-align:center}
.g3 .n0,.g4 .n0{text-align:center;font-size:12px;font-weight:800;color:var(--text)}
.g3.sel,.g4.sel{background:var(--accentBg);border-color:var(--accent)}
.g3.sel .n0,.g4.sel .n0{color:var(--accent)}
.g3 input,.g4 input,.g4 select,.tcard input{width:100%;min-width:0;box-sizing:border-box;
 height:26px;border-radius:6px;border:1px solid var(--border);background:var(--panel);
 color:var(--text);font-size:11px;padding:0 7px}
.tcard{background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:10px;
 display:flex;flex-direction:column;gap:8px;margin-bottom:8px}
.tcard .th{display:grid;grid-template-columns:28px 1fr 1fr auto;gap:6px;align-items:center}
.chip{height:22px;padding:0 8px;border-radius:999px;border:1px solid var(--border);
 background:var(--panel2);color:var(--text);font-size:10px;font-weight:700;cursor:pointer;
 font-variant-numeric:tabular-nums}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.info{font-size:11px;color:var(--muted);line-height:1.65;margin:8px 0 0}
.uzone{flex:1;min-height:0;margin:13px;border:2px dashed var(--border);border-radius:12px;
 display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;
 padding:32px 40px}
.uzone .em{font-size:40px;opacity:.25;line-height:1}
.uzone h4{font-size:17px;font-weight:800;color:var(--text);margin:0 0 10px}
.uzone p{font-size:13px;color:var(--muted);line-height:1.85;margin:0;max-width:460px;
 text-align:center}
.uzone p b{color:var(--text)}
.ucards{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.uc{width:152px;background:var(--panel2);border-radius:10px;border:1px solid var(--border);
 padding:16px 14px;display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center}
.uc .ic{font-size:22px;line-height:1}
.uc b{font-size:11px;font-weight:800;color:var(--text);white-space:nowrap}
.uc span{font-size:11px;color:var(--muted);line-height:1.6}
.frow[data-r]:hover,.g3[data-r]:hover{background:var(--accentBg);border-color:var(--accent)}

</style>""")

    # 신호 이름 칸이 62px 고정이라 「마스터 불일치」가 두 줄로 접혔다. 접지 않는다.
    style = style.replace(
        "grid-template-columns:10px minmax(140px,1.5fr) minmax(0,2.4fr) 62px",
        "grid-template-columns:10px minmax(140px,1.5fr) minmax(0,2.4fr) auto")
    style = style.replace(
        ".valrow .vl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
        ".valrow .vl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
        ".valrow .cf{white-space:nowrap;min-width:64px;text-align:right;font-variant-numeric:tabular-nums}.valrow .vl{display:flex;align-items:center;gap:7px;min-width:0}.valrow .vt{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ba{display:flex;align-items:baseline;gap:6px;white-space:nowrap}.ba i{font-style:normal;font-size:9px;font-weight:700;color:var(--muted);min-width:32px;flex:none}.vbadge{flex:none;font-size:10px;font-weight:700;color:var(--warn);background:var(--warnBg);border:1px solid var(--warn);border-radius:4px;padding:1px 6px;white-space:nowrap}")
    # 행 전체가 아니라 문제 있는 칸만 강조한다(상속 규칙 교체). 지우면 강조가 사라진다.
    style = style.replace("tr.flag .cellin{border-color:#d97706}",
                          ".cellin.bad{border-color:var(--accent);background:var(--accentBg)}")
    scan = scan_b64(REAL_IMG)
    # 스캔본은 :root 변수로 한 번만 심는다(여러 화면이 참조). 이 줄이 지워지면 문서가 안 보인다.
    style = style.replace("</style>", ":root{--scan:url(data:image/jpeg;base64," + scan + ")}</style>")
    rgt = json.loads(REAL_GT.read_text(encoding="utf-8"))["documents"][REAL_KEY]["normalizedResult"]
    rfields = {f["labelEn"]: f["value"] for f in rgt["fields"]}
    rrows = rgt["tableRows"]

    # 템플릿 카드 미리보기. 제품 public/images/*.svg 를 그대로 옮긴다.
    SVG_FREE = ("<svg width='192' height='128' viewBox='0 0 192 128' fill='none'"
                " xmlns='http://www.w3.org/2000/svg'>"
                "<rect width='192' height='128' rx='14' fill='#1a1230'/>"
                "<rect x='20' y='18' width='152' height='92' rx='10' fill='#241a3d'"
                " stroke='#5b46a0' stroke-width='2' stroke-dasharray='8 6'/>"
                "<path d='M40 42h78M40 56h96M40 70h60M40 84h84' stroke='#8b78c4'"
                " stroke-width='5' stroke-linecap='round'/>"
                "<path d='M130 26l4.8 13.2L148 44l-13.2 4.8L130 62l-4.8-13.2L112 44"
                "l13.2-4.8L130 26Z' fill='#c084fc'/>"
                "<path d='M155 54l2.8 7.6L165 64l-7.2 2.4L155 74l-2.8-7.6L145 64"
                "l7.2-2.4L155 54Z' fill='#a855f7'/></svg>")
    SVG_UNS = ("<svg width='192' height='128' viewBox='0 0 192 128' fill='none'"
               " xmlns='http://www.w3.org/2000/svg'>"
               "<rect width='192' height='128' rx='14' fill='#0f1724'/>"
               "<rect x='20' y='18' width='152' height='92' rx='10' fill='#151e2c'"
               " stroke='#263449'/>"
               "<path d='M42 38h64M42 51h84M42 64h48' stroke='#38506c' stroke-width='5'"
               " stroke-linecap='round'/>"
               "<rect x='42' y='78' width='44' height='14' rx='4' fill='#1f3348'/>"
               "<rect x='94' y='78' width='56' height='14' rx='4' fill='#183449'/>"
               "<path d='M132 32l10 10-26 26-12 2 2-12 26-26Z' fill='#22d3ee'/>"
               "<path d='M132 32l10 10' stroke='#e8edf5' stroke-width='3'"
               " stroke-linecap='round'/>"
               "<circle cx='145' cy='87' r='14' fill='#0891b2'/>"
               "<path d='M138 87h14M145 80v14' stroke='white' stroke-width='3'"
               " stroke-linecap='round'/></svg>")

    def svg_url(x):
        # style="..." 안에 들어가므로 홑따옴표로 감싼다. quote 가 홑따옴표는 %27 로 바꾼다.
        return "url('data:image/svg+xml;utf8," + urllib.parse.quote(x) + "')"

    # (이름, 종류) - reg 는 좌표 템플릿이라 저장해 둔 문서가 썸네일이 된다
    TPLS = [("거래명세서", "reg"), ("거래_1", "reg"), ("거래_2", "uns"),
            ("영수증", "reg"), ("세금계산서", "uns")]

    def tpl_cards(active="거래명세서", free=False):
        out = []
        def th(kind):
            u = {"free": svg_url(SVG_FREE), "uns": svg_url(SVG_UNS)}.get(kind)
            return f'<div class="thumb" style="background-image:{u}"></div>' if u                 else '<div class="thumb"></div>'

        if free:
            out.append('<div class="tplcard free' + (" on" if active == "비정형" else "")
                       + '">' + th("free") + '<div class="nm">비정형</div></div>')
        for nm, kind in TPLS:
            out.append(f'<div class="tplcard {kind}{" on" if nm == active else ""}">'
                       + th(kind) + f'<div class="nm">{nm}</div></div>')
        return "\n          ".join(out)

    def paper(pid="", tilt=False, mark=True):
        """실제 스캔본. tilt 는 전처리 전 이미지를 흉내내기 위한 기울기."""
        st = ' style="transform:rotate(-0.8deg)"' if tilt else ""
        idp = f' id="{pid}"' if pid else ""
        return f'              <div class="scan"{idp}{st} role="img" aria-label="{REAL_KEY}"></div>'

    # 문서 정보 필드 - 정답은 실측 GT, OCR값은 예시 오류.
    def _biz(v):
        return f"{v[:3]}-{v[3:5]}-{v[5:]}" if v and len(v) == 10 and v.isdigit() else v

    def _date(v):
        return f"{v[:4]}-{v[4:6]}-{v[6:]}" if v and len(v) == 8 and v.isdigit() else v

    _g = rfields.get
    # (한글명, 영문키, OCR값, 정답(다를 때만), 원인, 해결태그, 해결라벨, 확인필요, 정확도, 등급)
    DOC = [
        ("공급자 등록번호", "supplierBizNumber", _biz(_g("supplierBizNumber", "")),
         "", "", "", "", 0, "99.8%", "h", ""),
        ("공급자 상호", "supplierCompany", "한국휴텍스제약(주)이상일,김성겸",
         _g("supplierCompany", ""), "블록 결합<div class=\"sig\">상호 칸과 성명 칸이 붙음</div>", "mu", "규칙", 1, "66.3%", "m",
         "신뢰도 74%"),
        ("공급자 주소", "supplierAddress", "경기 화성시 향남읍 제약공단3길 99한국휴텍스제",
         _g("supplierAddress", ""), "마스터 불일치<div class=\"sig\">문서 주소 &ne; 거래처 마스터</div>",
         "ac", "매칭", 1, "68.2%", "l", "마스터 불일치"),
        ("공급받는자 등록번호", "buyerBizNumber", _g("buyerBizNumber", ""),
         "", "", "", "", 0, "99.9%", "h", ""),
        ("공급받는자 상호", "buyerCompany", "백제약품(주)영등포지점",
         "", "", "", "", 0, "96.4%", "h", ""),
        ("공급받는자 주소", "buyerAddress", _g("buyerAddress", ""), "", "", "", "", 0, "97.1%", "h", ""),
        ("작성일자", "issueDate", _date(_g("issueDate", "")), "", "", "", "", 0, "100.0%", "h", ""),
        ("과세 구분", "taxType", _g("taxType", ""), "", "", "", "", 0, "98.2%", "h", ""),
        ("공급가액", "supplyAmount", "", _g("supplyAmount", ""),
         "컬럼 미매핑<div class=\"sig\">TOTAL 칸을 못 잡음</div>", "mu", "규칙", 1, "0.0%", "l", "값 없음"),
        ("세액", "taxAmount", "", _g("taxAmount", ""),
         "컬럼 미매핑<div class=\"sig\">TOTAL 칸을 못 잡음</div>", "mu", "규칙", 1, "0.0%", "l", "값 없음"),
        ("합계금액", "totalAmount", "", _g("totalAmount", ""),
         "컬럼 미매핑<div class=\"sig\">TOTAL 칸을 못 잡음</div>", "mu", "규칙", 1, "0.0%", "l", "값 없음"),
    ]

    # 품목 판독 오류 예시 - 행 번호(1-based) -> (OCR값, 정확도, 등급, 원인)
    ITEM_ERR = {
        1: ("넥시메졸캡술20mg", "88.6%", "m", "동형 글자<div class=\"sig\">슐 / 술</div>", "신뢰도 89%"),
        12: ("로오딜슈프라정16Omg", "85.3%", "m", "동형 글자<div class=\"sig\">0 / O</div>", "신뢰도 85%"),
        18: ("세파록스캡슬", "88.4%", "m", "글자 오독<div class=\"sig\">슐 / 슬</div>", "대장에 없음"),
    }
    # 품명 외 칸의 오류. {행: {칸키: OCR값}} - 정답은 GT 값이다.
    ITEM_CELL_ERR = {
        1: {"spec": "1O0C"},
        4: {"quantity": "1O"},
    }

    # 03 문서 위 영역 좌표. 01 템플릿에 찍은 것과 같은 문서라 값을 공유한다.
    # 값이 없는 필드(buyerAddress·taxType 은 마스터/규칙에서, 금액 3종은 미검출)는
    # 문서에 자리가 없다. 그것도 화면이 말해 줘야 한다.
    FBOX = {
        "issueDate": (89.2, 8.2, 9.2, 1.5),
        "supplierBizNumber": (15.4, 10.5, 38.2, 1.9),
        "supplierCompany": (15.4, 12.7, 19.0, 1.9),
        "supplierAddress": (15.4, 14.8, 38.2, 1.9),
        "buyerBizNumber": (64.8, 10.5, 33.4, 1.9),
        "buyerCompany": (64.8, 12.7, 33.4, 1.9),
    }
    TB_TOP, TB_BOT, TB_L, TB_W = 26.95, 94.30, 2.2, 96.2
    ROW_H = (TB_BOT - TB_TOP) / len(rrows)

    def zexp(cols):
        """행 바로 아래 접혀 있는 확대 칸. 누른 행에서만 펼쳐진다."""
        return (f'<tr class="zexp"><td colspan="{cols}">'
                '<div class="zpair">'
                '<div class="zrow"><span class="zlab">전처리 전</span>'
                '<div class="zimg" style="transform:rotate(-0.8deg)"></div></div>'
                '<div class="zrow"><span class="zlab">전처리 후</span>'
                '<div class="zimg"></div></div></div>'
                '<div class="znone">이 값은 문서에 위치가 없습니다</div>'
                '</td></tr>')

    def zbox_js():
        """확대에 쓸 좌표. 품목은 품명이 보이도록 왼쪽 구간만."""
        d = {k: list(v) for k, v in FBOX.items()}
        for i in range(1, len(rrows) + 1):
            d[f"row-{i}"] = [TB_L, round(TB_TOP + (i - 1) * ROW_H, 2), TB_W, round(ROW_H, 2)]
        return json.dumps(d, ensure_ascii=False)

    def boxes():
        out = [f'<div class="rgn" data-fb="{k}" '
               f'style="left:{v[0]}%;top:{v[1]}%;width:{v[2]}%;height:{v[3]}%"></div>'
               for k, v in FBOX.items()]
        out += [f'<div class="rgn" data-fb="row-{i}" style="left:{TB_L}%;'
                f'top:{TB_TOP + (i - 1) * ROW_H:.2f}%;width:{TB_W}%;height:{ROW_H:.2f}%"></div>'
                for i in range(1, len(rrows) + 1)]
        return "\n                ".join(out)

    def doc_rows(edit=False, only_need=False, no_start=1):
        out = []
        for i, (ko, en, got, want, why, tg, tl, need, cf, cls, sig) in enumerate(DOC, no_start):
            if only_need and not need:
                continue
            cell = '<span class="none">미검출</span>' if not got else (
                f'<span class="was">{esc(got)}</span>' if need else esc(got))
            ed = (f'<td><input class="cellin{" bad" if need else ""}" '
                  f'value="{esc(got)}"></td>' if edit else "")
            mark = ('<span class="tag wa">확인 필요</span>' if need
                    else '<span style="color:var(--muted)">-</span>')
            out.append(f'<tr class="{"flag" if need else ""}" data-need="{need}" '
                       f'data-fb="{en}" data-k="{esc(ko)} {esc(en)} {esc(got)}"><td>{i}</td>'
                       f'<td>{ko}</td><td class="fkey">{en}</td><td>{cell}</td>{ed}'
                       f'<td style="text-align:center">{mark}</td></tr>')
        return "\n                  ".join(out)

    def item_rows(model="base"):
        """실제 GT 23행 + 판독 오류 예시 3건."""
        out = []
        for i, r in enumerate(rrows, 1):
            nm = r.get("itemName", "")
            err = ITEM_ERR.get(i)
            # 품명뿐 아니라 규격·수량 같은 칸의 오독도 같이 보여야 한다.
            # 이게 빠져 있어서 KPI(9건)와 표(8건)가 어긋났다.
            cerr = ITEM_CELL_ERR.get(i, {})
            bad = bool(err) or bool(cerr)
            read = err[0] if err else nm
            spec = cerr.get("spec", r.get("spec", ""))
            qty = cerr.get("quantity", r.get("quantity", ""))
            unit = cerr.get("unitPrice", f'{int(r.get("unitPrice") or 0):,}')
            amt = cerr.get("amount", f'{int(r.get("amount") or 0):,}')
            mark = ('<span class="tag wa">확인 필요</span>' if bad
                    else '<span style="color:var(--muted)">-</span>')
            out.append(
                f'<tr class="{"flag" if bad else ""}" data-need="{1 if bad else 0}" '
                f'data-fb="row-{i}" data-k="품목 {i:02d} {esc(read)} {esc(spec)}"><td>{i}</td>'
                f'<td class="{"was" if err else ""}">{esc(read)}</td>'
                f'<td class="{"was" if "spec" in cerr else ""}">{esc(spec)}</td>'
                f'<td class="n {"was" if "quantity" in cerr else ""}">{esc(qty)}</td>'
                f'<td class="n {"was" if "unitPrice" in cerr else ""}">{esc(unit)}</td>'
                f'<td class="n {"was" if "amount" in cerr else ""}">{esc(amt)}</td>'
                f'<td style="text-align:center">{mark}</td></tr>')
        return "\n                  ".join(out)

    def field_cards():
        """제품 Custom 탭의 필드 카드. 표가 아니라 카드 하나씩이다."""
        def conf(pct):
            v = float(pct.rstrip("%"))
            if v >= 70:
                return v, "#16a34a", "&#10003;"
            if v >= 40:
                return v, "#d97706", "&#9651;"
            return v, "#dc2626", "&#10005;"

        out = []
        for i, (ko, en, got, want, why, tg, tl, need, cf, cls, sig) in enumerate(DOC, 1):
            v, col, ico = conf(cf)
            # 문서에 자리가 없는 값은 OCR 이 아니라 다른 경로로 채워졌다
            adopt = ("복원" if en in ("buyerAddress", "taxType")
                     else "-" if not got else "OCR")
            acol = {"복원": "#4f46e5", "OCR": "#2563eb"}.get(adopt, "var(--muted)")
            types = "".join(
                f'<option{" selected" if k == "필드" else ""}>{k}</option>'
                for k in ("필드", "멀티필드", "체크필드", "테이블필드"))
            out.append(
                f'<div class="fcard{" bad" if need else ""}" data-fb="{en}" '
                f'data-need="{need}" data-k="{esc(ko)} {esc(en)} {esc(got)}">'
                f'<div class="fch"><span class="fcn">{esc(ko)}'
                f'<em>{esc(en)}</em></span>'
                f'<select class="fcsel">{types}</select>'
                f'<span class="fcbar"><i style="width:{v:.0f}%;background:{col}"></i></span>'
                f'<span class="fcpct" style="color:{col}">{ico} {cf}</span>'
                f'<span class="fcad" style="color:{acol}">{adopt}</span>'
                f'<button class="fcx">&#10005;</button></div>'
                f'<div class="fcv"><div class="fcm">'
                f'<span>OCR 원본: {esc(got) if got else "-"}</span>'
                f'<span>채택: {adopt}</span></div>'
                f'<label>최종값</label>'
                f'<input class="fcin{" bad" if need else ""}" value="{esc(got)}" '
                f'placeholder="최종값 입력"></div></div>')
        return "\n                  ".join(out)

    fcards = field_cards()

    def item_rw_rows():
        """Custom 은 편집 화면이라 품목의 모든 값을 고칠 수 있어야 한다."""
        out = []
        for i, r in enumerate(rrows, 1):
            nm = r.get("itemName", "")
            err = ITEM_ERR.get(i)
            read = err[0] if err else nm
            mark = ('<span class="tag wa">확인 필요</span>' if err
                    else '<span style="color:var(--muted)">-</span>')
            cells = "".join(
                f'<td><input class="cellin{" n" if right else ""}{" bad" if bad else ""}" '
                f'value="{esc(v)}"></td>'
                for v, right, bad in (
                    (read, False, bool(err)), (r.get("spec", ""), False, False),
                    (r.get("quantity", ""), True, False),
                    (f'{int(r.get("unitPrice") or 0):,}', True, False),
                    (f'{int(r.get("amount") or 0):,}', True, False)))
            out.append(f'<tr class="{"flag" if err else ""}" data-need="{1 if err else 0}" '
                       f'data-fb="row-{i}" '
                       f'data-k="품목 {i:02d} {esc(read)} {esc(r.get("spec",""))}">'
                       f'<td>{i}</td>{cells}'
                       f'<td style="text-align:center">{mark}</td></tr>')
        return "\n                  ".join(out)

    item_rw = item_rw_rows()

    # 제품 Preview 우측의 <전체 OCR 텍스트>. 값이 어느 줄에서 왔는지 보여 주는 자리다.
    raw_src = [rfields.get("supplierBizNumber", ""), "한국휴텍스제약(주)", "이상일, 김성겸",
               "경기 화성시 향남읍 제약공단3길 99한국휴텍스제", "제조업,도매업,", "양약,자양강장제",
               rfields.get("buyerBizNumber", ""), "백제약품(주)영등포지점", "김승관", "도매",
               "02-869-0211", "거래명세서", "(공급받는자용)", "20260617", "박스개수 6",
               "총 매수 3장", "A1P000120260617001639TS001"]
    raw_src += [f'{r.get("itemName","")}  {r.get("spec","")}  {r.get("quantity","")}  '
                f'{int(r.get("unitPrice") or 0):,}  {int(r.get("amount") or 0):,}'
                for r in rrows]
    raw_lines = "".join(f'<div class="rawline"><i>{i}</i>{esc(t)}</div>'
                        for i, t in enumerate(raw_src, 1))

    def _valrow(kind, ko, en, val, cf, badge="", flag=""):
        """제품 Validation 행과 같은 구성 - 값 + (신호 배지) + 신뢰도.

        신뢰도로 설명되는 건 오른쪽 숫자가 이미 말한다. 배지는 숫자로는
        알 수 없는 신호(대조 실패 · 검산)에만 붙인다.
        """
        b = f'<span class="vbadge">{badge}</span>' if badge else ""
        return (f'                    <div class="valrow"><span class="dt d-{kind}"></span>'
                f'<span class="nm">{esc(ko)}<em>({esc(en)})</em></span>'
                f'<span class="vl"><span class="vt">{val}</span>{b}</span>'
                f'<span class="cf {"l" if kind == "er" else "m"}">{cf}</span></div>'
                + (f'\n                    <div class="valflag">{flag}</div>' if flag else ""))

    _NONE = '<span class="none">미검출</span>'
    val_er = "\n".join([
        _valrow("er", "공급가액", "supplyAmount", _NONE, "0.0%", "",
                "검산 불가 - 공급가액+세액=합계 를 확인할 수 없음"),
        _valrow("er", "세액", "taxAmount", _NONE, "0.0%"),
        _valrow("er", "합계금액", "totalAmount", _NONE, "0.0%"),
    ])
    val_wa = "\n".join([
        _valrow("wa", "공급자 상호", "supplierCompany", "한국휴텍스제약(주)이상일,김성겸", "66.3%"),
        _valrow("wa", "공급자 주소", "supplierAddress",
                "경기 화성시 향남읍 제약공단3길 99한국휴텍스제", "68.2%", "마스터 불일치"),
        _valrow("wa", "품목 01 품명", "itemName", "넥시메졸캡술20mg", "88.6%", "대장에 없음"),
        _valrow("wa", "품목 12 품명", "itemName", "로오딜슈프라정16Omg", "85.3%", "대장에 없음"),
        _valrow("wa", "품목 18 품명", "itemName", "세파록스캡슬", "88.4%", "대장에 없음"),
    ])

    # 04 확인 항목 - 02 실행 결과의 오류 8건을 그대로 쓴다.
    learned_img = {x["gtTxt"]: x["img"] for x in T}
    issue = []
    for ko, en, got, want, why, tg, tl, need, cf, cls, sig in DOC:
        if not need:
            continue
        issue.append((ko, en, got, want, why, tg, tl, "", cf))

    issue_rows = "\n                  ".join(
        f'<tr data-need="1" data-fb="{en}" data-k="{esc(ko)} {esc(en)} {esc(got)} {esc(want)}">'
        f'<td>{esc(ko)}<br><span class="fkey">{esc(en)}</span></td>'
        + (f'<td class="was">{esc(got)}</td>' if got
           else '<td><span class="none">미검출</span></td>')
        + f'<td><input class="cellin bad" value="{esc(want)}"></td>'
        f'<td style="text-align:center"><span class="tag wa">확인 필요</span></td>'
        f'<td class="cf {"m" if got else "l"}">{cf}</td></tr>' + zexp(5)
        for ko, en, got, want, why, tg, tl, img, cf in issue)

    # 확인 필요가 아닌 필드도 함께 - 「전체」 로 보면 나머지가 다 맞았음이 보인다
    ok_rows = "\n                  ".join(
        f'<tr data-need="0" data-fb="{en}" data-k="{esc(ko)} {esc(en)} {esc(got)}">'
        f'<td>{esc(ko)}<br><span class="fkey">{esc(en)}</span></td>'
        f'<td>{esc(got)}</td>'
        f'<td><input class="cellin" value="{esc(got)}"></td>'
        f'<td style="text-align:center"><span class="tag ok">정상</span></td>'
        f'<td class="cf h">{cf}</td></tr>' + zexp(5)
        for ko, en, got, want, why, tg, tl, need, cf, cls, sig in DOC if not need)

    def detail_item_rows():
        """04 품목 표 - 02 Custom 과 같은 방식. 모든 칸이 입력칸이고 문제 칸만 강조."""
        def cell(val, bad, right=False):
            return (f'<td><input class="cellin{" n" if right else ""}{" bad" if bad else ""}" '
                    f'value="{esc(val)}"></td>')

        out = []
        for i, r in enumerate(rrows, 1):
            nm = r.get("itemName", "")
            err = ITEM_ERR.get(i)
            cerr = ITEM_CELL_ERR.get(i, {})
            bad = bool(err) or bool(cerr)
            mark = ('<span class="tag wa">확인 필요</span>' if bad
                    else '<span class="tag ok">정상</span>')
            cells = (cell(err[0] if err else nm, bool(err))
                     + cell(cerr.get("spec", r.get("spec", "")), "spec" in cerr)
                     + cell(cerr.get("quantity", r.get("quantity", "")), "quantity" in cerr, True)
                     + cell(cerr.get("unitPrice", f'{int(r.get("unitPrice") or 0):,}'),
                            "unitPrice" in cerr, True)
                     + cell(cerr.get("amount", f'{int(r.get("amount") or 0):,}'),
                            "amount" in cerr, True))
            out.append(f'<tr data-need="{1 if bad else 0}" data-fb="row-{i}" '
                       f'data-k="품목 {i:02d} {esc(nm)}">'
                       f'<td>{i}</td>{cells}'
                       f'<td style="text-align:center">{mark}</td></tr>' + zexp(7))
        return "\n                  ".join(out)

    ditem_rows = detail_item_rows()

    # OCR 데이터 - 제품 상세보기의 원문 표
    raw_rows = "\n                  ".join(
        f'<tr><td>{i}</td><td class="fkey">field_{i}</td><td>{esc(t)}</td>'
        f'<td class="cf {"h" if i % 4 else "m"}">{95 + i % 5}.{i % 10}%</td></tr>'
        for i, t in enumerate(raw_src, 1))

    REAL_FILES = [
        ("471814/20260618135314_0008.jpg", "299 KB", 23),
        ("455158/20260604092610_0008.jpg", "312 KB", 23),
        ("459910/20260608132151_0009.jpg", "287 KB", 23),
        ("453931/20260602120005_0002.jpg", "341 KB", 24),
        ("457719/img20260605_0001.jpg", "1.1 MB", 23),
        ("452796/20260601131502_0008.jpg", "268 KB", 23),
    ]

    # 03 필드별 결과 - 고객이 준 문서 전체 기준. 기본 / 학습 / 비교 세 벌.
    NDOC = len(REAL_FILES)
    NITEM = sum(n for _, _, n in REAL_FILES)          # 품명 등장 횟수
    # 필드별 (기본 정상, 학습 정상). 규칙·매칭 대상은 학습으로 안 바뀐다.
    AGG_BASE = {"supplierCompany": 2, "supplierAddress": 3,
                "supplyAmount": 0, "taxAmount": 0, "totalAmount": 0}

    def agg_rows(mode):
        out, sb, sl, tot = [], 0, 0, 0
        for ko, en, got, want, why, tg, tl, need, cf, cls, sig in DOC:
            b = AGG_BASE.get(en, NDOC)
            l = b                                       # 학습이 건드리지 않는 필드
            sb += b
            sl += l
            tot += NDOC
            sol = f'<span class="tag {tg}">{tl}</span>' if tl else '<span style="color:var(--muted)">-</span>'
            out.append(_agg_tr(ko, en, b, l, NDOC, mode, why, sol))
        # 품명 - 학습이 바꾸는 유일한 필드
        b, l = NITEM - 20, NITEM - 6
        sb += b
        sl += l
        tot += NITEM
        out.append(_agg_tr("품명", "itemName", b, l, NITEM, mode,
                           "글자 오독", '<span class="tag ac">학습</span>'))
        out.append(_agg_tot(sb, sl, tot, mode))
        return "\n                  ".join(out)

    def _bar(ok, n):
        pct = round(ok * 100 / n) if n else 0
        col = "var(--ok)" if ok == n else ("var(--warn)" if pct >= 50 else "var(--err)")
        return (f'<div class="barwrap"><div class="mini">'
                f'<i style="width:{pct}%;background:{col}"></i></div>'
                f'<span class="pct" style="color:{col}">{pct}%</span></div>')

    def _agg_tr(ko, en, b, l, n, mode, why, sol):
        name = f'<td>{esc(ko)}<br><span class="fkey">{esc(en)}</span></td>'
        cause = f'<td>{why or "<span style=color:var(--muted)>-</span>"}</td><td>{sol}</td>'
        if mode == "diff":
            d = l - b
            cls = "chg" if d else "dim"
            delta = (f'<span class="now">+{d}</span>' if d
                     else '<span style="color:var(--muted)">0</span>')
            return (f'<tr class="{cls}">{name}<td class="n">{b} / {n}</td>'
                    f'<td class="n">{l} / {n}</td><td class="n">{delta}</td>'
                    f'<td>{_bar(l, n)}</td>{cause}</tr>')
        v = b if mode == "base" else l
        ng = n - v
        return (f'<tr class="{"flag" if ng else ""}">{name}<td class="n">{v} / {n}</td>'
                f'<td class="n">{f"<span class=was>{ng}</span>" if ng else "0"}</td>'
                f'<td>{_bar(v, n)}</td>{cause}</tr>')

    def _agg_tot(sb, sl, tot, mode):
        if mode == "diff":
            return (f'<tr class="tot"><td>합계</td><td class="n">{sb} / {tot}</td>'
                    f'<td class="n">{sl} / {tot}</td>'
                    f'<td class="n"><span class="now">+{sl - sb}</span></td>'
                    f'<td>{_bar(sl, tot)}</td><td></td><td></td></tr>')
        v = sb if mode == "base" else sl
        return (f'<tr class="tot"><td>합계</td><td class="n">{v} / {tot}</td>'
                f'<td class="n">{tot - v}</td><td>{_bar(v, tot)}</td><td></td><td></td></tr>')

    agg_base = agg_rows("base")
    agg_tuned = agg_rows("tuned")
    agg_diff = agg_rows("diff")
    _tb = sum(AGG_BASE.get(d[1], NDOC) for d in DOC) + NITEM - 20
    _tl = sum(AGG_BASE.get(d[1], NDOC) for d in DOC) + NITEM - 6
    _tt = len(DOC) * NDOC + NITEM

    # 06 비교 - 같은 문서를 두 모델로. 학습이 바꾼 것은 세파록스캡슐 하나뿐이다.
    # 학습은 인식 모델을 바꾸므로 품명 밖의 필드도 값이 달라질 수 있다.
    # 주소 꼬리 한 글자를 더 읽은 예 - 마스터 불일치는 그대로라 확인 필요는 남는다.
    CMP_TUNED = {"supplierAddress": "경기 화성시 향남읍 제약공단3길 99한국휴텍스제약"}

    def _cmpcell(v, c):
        return f'<td class="{c}">{esc(v)}</td>' if v else '<td><span class="none">미검출</span></td>'

    cmp_rows, n_dchg = [], 0
    for ko, en, got, want, why, tg, tl, need, cf, cls, sig in DOC:
        aft = CMP_TUNED.get(en, got)
        chg = aft != got
        if chg:
            n_dchg += 1
        cmp_rows.append(
            f'<tr class="{"chg" if chg else "dim"}" data-chg="{1 if chg else 0}" '
            f'data-k="{esc(ko)} {esc(en)} {esc(got)} {esc(aft)}">'
            f'<td>{esc(ko)}<br><span class="fkey">{esc(en)}</span></td>'
            + _cmpcell(got, "was" if chg else "")
            + _cmpcell(aft, "now" if chg else "")
            + f'<td><span class="tag {"ac" if chg else "mu"}">'
            f'{"변경" if chg else "동일"}</span></td></tr>')
    cmp_rows = "\n                  ".join(cmp_rows)

    # 07 품목표 비교 - 업체가 보는 단위는 품명이 아니라 품목표 한 줄이다.
    # 학습이 바꾼 칸만 학습 전/후를 위아래로 보이고 나머지는 값 하나로 둔다.
    def item_cmp_rows():
        def cell(val, before=None, right=False):
            cls = ' class="n"' if right else ""
            if before is None:
                return f"<td{cls}>{esc(val)}</td>"
            return (f'<td{cls}><span class="ba"><i>학습 전</i>'
                    f'<span class="was">{esc(before)}</span></span>'
                    f'<span class="ba"><i>학습 후</i>'
                    f'<span class="now">{esc(val)}</span></span></td>')

        out, chg_n = [], 0
        for i, r in enumerate(rrows, 1):
            nm = r.get("itemName", "")
            err = ITEM_ERR.get(i)
            cerr = ITEM_CELL_ERR.get(i, {})
            read = err[0] if err else nm
            # 학습이 고친 것은 대장에 있는 품명뿐. 나머지 오독은 두 모델 다 그대로다.
            chg = bool(learned_img.get(nm)) and read != nm
            if chg:
                chg_n += 1
            out.append(
                f'<tr class="{"chg" if chg else "dim"}" data-chg="{1 if chg else 0}" '
                f'data-k="품목 {i:02d} {esc(read)} {esc(nm)}">'
                f'<td>{i}</td>'
                + cell(nm if chg else read, read if chg else None)
                + cell(cerr.get("spec", r.get("spec", "")))
                + cell(cerr.get("quantity", r.get("quantity", "")), right=True)
                + cell(cerr.get("unitPrice", f'{int(r.get("unitPrice") or 0):,}'), right=True)
                + cell(cerr.get("amount", f'{int(r.get("amount") or 0):,}'), right=True)
                + f'<td style="text-align:center"><span class="tag {"ac" if chg else "mu"}">'
                f'{"변경" if chg else "동일"}</span></td></tr>')
        return "\n                  ".join(out), chg_n

    icmp_rows, n_ichg = item_cmp_rows()
    n_cmp = len(DOC) + len(rrows)

    # 04 하단 - 타깃별 실측
    tgt_rows = "\n                  ".join(
        f'<tr><td>{esc(x["name"])}</td>'
        f'<td><span class="tag {"ac" if x["isNew"] else "mu"}">'
        f'{"신규" if x["isNew"] else "유지 확인"}</span></td>'
        f'<td class="n {"was" if x["base"] < x["n"] else ""}">{x["base"]} / {x["n"]}</td>'
        f'<td class="n {"now" if x["ft"] == x["n"] else ""}">{x["ft"]} / {x["n"]}</td>'
        f'<td><span class="tag ok">{"개선" if x["base"] < x["ft"] else "유지"}</span></td></tr>'
        for x in T)

    tgt_rows_s = "\n                ".join(
        f'<tr><td>{esc(x["name"])}</td>'
        f'<td><span class="tag {"ac" if x["isNew"] else "mu"}">'
        f'{"신규" if x["isNew"] else "유지"}</span></td>'
        f'<td class="n {"was" if x["base"] < x["n"] else ""}">{x["base"]}/{x["n"]}</td>'
        f'<td class="n {"now" if x["ft"] == x["n"] else ""}">{x["ft"]}/{x["n"]}</td></tr>'
        for x in T)

    def char_diff(a, b):
        """base 와 학습 모델 판독에서 서로 다른 글자만 뽑는다(길이 같을 때만)."""
        if a == b:
            return ""
        if len(a) == len(b):
            pairs = [(x, y) for x, y in zip(a, b) if x != y]
            if 0 < len(pairs) <= 3:
                return " · ".join(f"{x} &rarr; {y}" for x, y in pairs)
        return "표기"

    # 컬럼(필드)은 리포트에서 나온 것만 넣는다. 종류가 늘면 셀렉트가 알아서 길어진다.
    COL_LABEL = {"itemName": "품명", "quantity": "수량", "unitPrice": "단가",
                 "amount": "금액", "supplyAmount": "공급가액", "taxAmount": "세액",
                 "spec": "규격", "unit": "단위"}
    col_key = rep.get("column") or "itemName"

    CHAR_LABEL = {"ko": "한글", "en": "영문", "num": "숫자", "sym": "기호"}

    def char_class(ch):
        """바뀐 글자 하나가 어느 종류인지. 학습이 무엇을 건드렸는지의 축이다."""
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF:
            return "ko"
        if ch.isdigit():
            return "num"
        if ("a" <= ch.lower() <= "z"):
            return "en"
        return "sym"

    def diff_class(a, b):
        """판독이 바뀐 글자들의 종류. 안 바뀌었으면 빈 값."""
        if a == b or len(a) != len(b):
            return ""
        ks = {char_class(y) for x, y in zip(a, b) if x != y}
        return ks.pop() if len(ks) == 1 else ("mix" if ks else "")

    char_count = {}
    col_count = {}

    learn_rows = []
    n_up = n_keep = n_down = 0
    for x in T:
        d = char_diff(x["baseTxt"], x["ftTxt"])
        chg = x["ft"] > x["base"]
        res = "up" if x["ft"] > x["base"] else ("down" if x["ft"] < x["base"] else "keep")
        n_up += res == "up"
        n_keep += res == "keep"
        n_down += res == "down"
        col_count[col_key] = col_count.get(col_key, 0) + 1
        cc = diff_class(x["baseTxt"], x["ftTxt"])
        if cc:
            char_count[cc] = char_count.get(cc, 0) + 1
        learn_rows.append(
            f'<tr class="{"chg" if chg else "dim"}" data-res="{res}" data-col="{col_key}" '
            f'data-gain="{x["ft"] - x["base"]}" data-n="{x["n"]}" data-nm="{esc(x["name"])}" '
            f'data-cc="{cc or "none"}" '
            f'data-name="{esc(x["name"])} {esc(x["baseTxt"])} {esc(x["ftTxt"])}">'
            f'<td><img class="crop" src="data:image/jpeg;base64,{x["img"]}"></td>'
            f'<td class="{"was" if chg else ""}">{esc(x["baseTxt"])}</td>'
            f'<td class="{"now" if chg else ""}">{esc(x["ftTxt"])}</td>'
            f'<td>{d + (f" <span class=tag mu>{CHAR_LABEL.get(cc, cc)}</span>" if cc and cc != "mix" else "") if d else "<span style=color:var(--muted)>변화 없음</span>"}</td>'
            f'<td class="n">{x["base"]}/{x["n"]} &rarr; '
            f'<b class="{"now" if chg else ""}">{x["ft"]}/{x["n"]}</b></td>'
            f'<td><span class="tag {"ok" if chg else "mu"}">'
            f'{"개선" if chg else "유지"}</span></td></tr>')
    learn_rows = "\n                  ".join(learn_rows)
    n_chg = sum(char_count.values())
    char_opts = ('<option value="all">전체 글자 ({})</option>'.format(n_chg)
                 + "".join(f'<option value="{k}">{CHAR_LABEL[k]} ({char_count.get(k, 0)})</option>'
                           for k in ("ko", "en", "num", "sym"))
                 + (f'<option value="mix">복합 ({char_count["mix"]})</option>'
                    if char_count.get("mix") else ""))
    col_opts = '<option value="all">전체 컬럼 ({})</option>'.format(len(T)) + ''.join(
        f'<option value="{k}">{COL_LABEL.get(k, k)} ({v})</option>'
        for k, v in sorted(col_count.items(), key=lambda kv: -kv[1]))

    kind_rows = []
    for x in T:
        b = "<br>".join(
            f'<span class="{"was" if k != x["gtTxt"] else ""}">{esc(k)}</span> '
            f'<span class="fkey">{c}회</span>' for k, c in x["bKinds"])
        f = "<br>".join(
            f'<span class="{"now" if x["ft"] == x["n"] else ""}">{esc(k)}</span> '
            f'<span class="fkey">{c}회</span>' for k, c in x["fKinds"])
        kind_rows.append(
            f'<tr><td>{esc(x["name"])}</td><td class="n">{x["n"]}</td>'
            f'<td class="n">{len(x["bKinds"])}종</td><td>{b}</td>'
            f'<td class="n">{len(x["fKinds"])}종</td><td>{f}</td></tr>')
    kind_rows = "\n                  ".join(kind_rows)

    spec_rows = "\n                  ".join([
        f'<tr><td>학습 방식</td><td>인식 모델 재학습 + 가중치 보간 (WiSE-FT)</td></tr>',
        f'<tr><td>보간 비율</td><td>학습 모델 {itp.get("alphaFt", 0):.1f} + 기본 모델 '
        f'{1 - itp.get("alphaFt", 0):.1f}</td></tr>',
        f'<tr><td>재료 모델</td><td class="fkey">{esc(itp.get("ftRun", "-"))}</td></tr>',
        f'<tr><td>결과 모델 체크섬</td><td class="fkey">{esc((itp.get("outSha256") or "-")[:32])}…</td></tr>',
        f'<tr><td>생성 시각</td><td>{esc(rep.get("generatedAt", "-"))}</td></tr>',
        f'<tr><td>교체 범위</td><td>인식 모델만 - 검출·전처리·필드 추출은 그대로</td></tr>',
        f'<tr><td>학습 후보 풀</td><td>품명 크롭 {pool.get("trainItem", 0):,}개 '
        f'<span class="fkey">문서 {pool.get("trainDocs", 0):,}건</span></td></tr>',
        f'<tr><td>검사 기준</td><td>품명 셀 {pool.get("judgeItem", 0):,}개 '
        f'<span class="fkey">문서 {pool.get("judgeDocs", 0):,}건 - 학습에 쓰지 않음</span></td></tr>',
    ])

    files = "\n                ".join(
        f'<button class="fchip{" on" if i == 0 else ""}"><b>{f.split("/")[-1]}</b>'
        f'<s>{z} · 품목 {n}행</s></button>'
        for i, (f, z, n) in enumerate(REAL_FILES))

    hist = []
    for i, (f, z, n) in enumerate(REAL_FILES, 1):
        hist.append((i, f.split("/")[-1], "학습", f"10:{40 - i:02d}", 8 - (i % 3) - 2, "성공"))
    for i, (f, z, n) in enumerate(REAL_FILES, 7):
        # 5번째 문서는 전처리에서 걸러진 실패 건 - 실패가 어떻게 보이는지도 화면에 남긴다
        fail = i == 11
        hist.append((i, f.split("/")[-1], "기본", f"09:{20 - i:02d}",
                     0 if fail else 8 - (i % 3), "실패" if fail else "성공"))
    hist_rows = "\n                  ".join(
        f'<tr data-model="{md}" data-need="{1 if n else 0}"'
        f'{" class=flag" if n else ""}><td>{i}</td><td>비정형</td>'
        f'<td><span class="tag {"ac" if md == "학습" else "mu"}">{md}</span></td>'
        f'<td>2026-08-12 {tm}</td>'
        f'<td><span class="tag {"er" if st == "실패" else "ok"}">{st}</span></td>'
        f'<td class="fkey">{fn}</td>'
        f'<td>{"<span style=color:var(--muted)>-</span>" if st == "실패"
              else f"<span class=" + chr(34) + "tag " + ("wa" if n else "ok") + chr(34) + ">확인 " + str(n) + "</span>"}</td>'
        f'<td style="text-align:center"><button class="ms-btn-sm" data-view-go="detail">보기</button></td>'
        f'<td style="text-align:center"><button class="ms-btn-sm">삭제</button></td></tr>'
        for i, fn, md, tm, n, st in hist)

    html = TPL.format(
        style=style, run=esc(rep["runTag"]), files=files,
        paper01=paper(), paper02=paper("pR"), paper03b=paper("pB", True), paper03a=paper("pA"),
        paper04=paper("pC"), paper04r=paper(),
        doc_ro=doc_rows(), doc_rw=doc_rows(edit=True), item_rw=item_rw, boxes=boxes(),
        tpl_tpl=tpl_cards(), tpl_run=tpl_cards('비정형', free=True), zbox=zbox_js(),
        fcards=fcards, n_fc=len(DOC) + 1,
        raw_lines=raw_lines, n_raw=len(raw_src), ok_rows=ok_rows, raw_rows=raw_rows,
        ditem_rows=ditem_rows, val_er=val_er, val_wa=val_wa,
        items_base=item_rows("base"), issue_rows=issue_rows,
        agg_base=agg_base, agg_tuned=agg_tuned, agg_diff=agg_diff,
        ndoc=len(REAL_FILES), ntot=_tt, pbase=round(_tb * 100 / _tt),
        ptuned=round(_tl * 100 / _tt), gain=_tl - _tb, hist_rows=hist_rows,
        cmp_rows=cmp_rows, tgt_rows=tgt_rows, tgt_rows_s=tgt_rows_s,
        learn_rows=learn_rows, n_up=n_up, n_keep=n_keep, n_down=n_down,
        docid=REAL_KEY.split("/")[-1], n_doc=len(DOC), n_item=len(rrows),
        n_need=sum(1 for d in DOC if d[7]) + len(set(ITEM_ERR) | set(ITEM_CELL_ERR)),
        n_docneed=sum(1 for d in DOC if d[7]), n_tot=len(DOC) + len(rrows),
        n_field=len(DOC) + len(rrows),
        n_learned=sum(1 for r in rrows if r.get("itemName") in {x["gtTxt"] for x in T}),
        n_cmp=n_cmp, n_ichg=n_ichg, icmp_rows=icmp_rows,
        n_dchg=n_dchg, n_allchg=n_ichg + n_dchg,
        tag_dchg='ac' if n_dchg else 'mu',
        n_isame=len(rrows) - n_ichg, n_chg=n_chg,
        n_all=len(T), col_opts=col_opts, char_opts=char_opts, n_same=10 + len(T) - len(misread), kind_rows=kind_rows, spec_rows=spec_rows,
        tot_n=tot_n, tot_b=tot_b, tot_f=tot_f, lost=tot_n - tot_b,
        basis=f'{rep["pool"]["judgeItem"]:,}', docs=f'{rep["basisDocs"]:,}',
        n_mis=len(misread))
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"  타깃 {len(T)}종 · 검증 위치 {tot_n} · base {tot_b} → 학습 {tot_f}")
    for x in T:
        print(f"     {x['name'][:40]:<40} {x['base']:>2}/{x['n']:<2} → {x['ft']:>2}/{x['n']:<2}"
              f"  {'오독' if x['misread'] else '동일'}")


TPL = """<!doctype html>
<html lang="ko" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MySuit OCR · POC ({run})</title>
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
      <select class="side-sel"><option>한빛약품</option></select>
    </div>
    <div class="side-menu"><span class="side-lab">MENU</span></div>
    <nav class="nav">
      <a><svg width="16" height="16" viewBox="0 0 20 20" fill="none"><rect x="3" y="2" width="14" height="16" rx="2" stroke="currentColor" stroke-width="1.8"/><line x1="6" y1="6" x2="14" y2="6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="6" y1="10" x2="14" y2="10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="6" y1="14" x2="10" y2="14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>Template</a>
      <a><svg width="16" height="16" viewBox="0 0 20 20" fill="none"><path d="M10 14V4M10 4L6 8M10 4L14 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M4 16h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>RunOCR</a>
      <a><svg width="16" height="16" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7.5" stroke="currentColor" stroke-width="1.8"/><path d="M10 6V10.5L13 12.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>History</a>
      <a><svg width="16" height="16" viewBox="0 0 20 20" fill="none"><path d="M3.5 10a6.5 6.5 0 1 0 1.3-3.9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M3.5 4.5V8H7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>Restore</a>
    </nav>
    <div class="side-menu" style="margin-top:2px"><span class="side-lab">POC</span></div>
    <nav class="nav">
      <a class="on" data-view="tpl"><span class="no">01</span>템플릿</a>
      <a data-view="ocr"><span class="no">02</span>OCR 실행</a>
      <a data-view="run"><span class="no">03</span>실행 결과</a>
      <a data-view="missed"><span class="no">04</span>실행 이력</a>
      <a data-view="detail"><span class="no">05</span>확인 항목</a>
      <a data-view="compare"><span class="no">06</span>모델 비교</a>
      <a data-view="cmpresult"><span class="no">07</span>비교 결과</a>
      <a data-view="remaining"><span class="no">08</span>처리 경로</a>
    </nav>
  </aside>

  <div class="main">
    <header class="hd">
      <h1 id="hdTitle">템플릿</h1>
      <div class="hd-r">
        <button class="ms-btn" id="themeBtn">◐</button>
        <button class="ms-btn">로그아웃</button>
      </div>
    </header>

    <div class="body">

      <!-- ================= 01 템플릿 ================= -->
      <section class="view on" id="v-tpl">
        <div class="tpbar">
          <div class="tpmode">
            <button class="mcard on" data-tm="reg"><span>&#65291;</span>템플릿 생성</button>
            <button class="mcard" data-tm="uns"><span>&#8801;</span>비정형 생성</button>
          </div>
          <div class="tpdiv"></div>
          <div class="tpsaved">
            <div class="tpl" style="margin:0">
          {tpl_tpl}
            </div>
          </div>
        </div>

        <!-- 템플릿 생성 -->
        <div class="tmpane on" id="tm-reg">
          <div class="cols" style="grid-template-columns:1fr 420px">
            <div class="card">
              <div class="antb">
                <button class="mbtn">문서 변경</button>
                <button class="mbtn on">필드</button>
                <button class="mbtn">멀티필드</button>
                <button class="mbtn">체크필드</button>
                <button class="mbtn">테이블필드</button>
                <span class="fl" style="margin-left:8px">줌</span>
                <input type="range" min="10" max="200" value="100" style="width:96px">
                <span class="fkey">100%</span>
                <button class="mbtn">초기화</button>
              </div>
              <div class="doc">
                <div class="cvs">
                  <div class="scan" role="img" aria-label="{docid}"></div>
                  <div class="rgn" id="rgn1" style="left:41.8%;top:3.1%;width:17.4%;height:2.7%"><i>1</i></div>
                  <div class="rgn" id="rgn2" style="left:89.2%;top:8.2%;width:9.2%;height:1.5%"><i>2</i></div>
                  <div class="rgn" id="rgn3" style="left:15.4%;top:10.5%;width:38.2%;height:1.9%"><i>3</i></div>
                  <div class="rgn" id="rgn4" style="left:15.4%;top:12.7%;width:19.0%;height:1.9%"><i>4</i></div>
                  <div class="rgn" id="rgn5" style="left:15.4%;top:14.8%;width:38.2%;height:1.9%"><i>5</i></div>
                  <div class="rgn" id="rgn6" style="left:64.8%;top:10.5%;width:33.4%;height:1.9%"><i>6</i></div>
                  <div class="rgn" id="rgn7" style="left:64.8%;top:12.7%;width:33.4%;height:1.9%"><i>7</i></div>
                  <div class="rgn tb" id="rgn8" style="left:2.2%;top:24.0%;width:96.2%;height:70.3%"><i>8</i></div>
                  <div class="cg" style="left:5.7%;top:24.0%;height:70.3%"></div><div class="cg" style="left:35.0%;top:24.0%;height:70.3%"></div><div class="cg" style="left:41.7%;top:24.0%;height:70.3%"></div><div class="cg" style="left:46.7%;top:24.0%;height:70.3%"></div><div class="cg" style="left:56.7%;top:24.0%;height:70.3%"></div><div class="cg" style="left:67.9%;top:24.0%;height:70.3%"></div><div class="cg" style="left:77.0%;top:24.0%;height:70.3%"></div><div class="cg" style="left:89.3%;top:24.0%;height:70.3%"></div>
                </div>
              </div>
              <div class="bar"><span class="tag mu">{docid}</span><span class="tag mu">2490 &times; 3510</span>
                <span class="tag ac">필드 7</span>
                <span class="tag" style="background:rgba(124,58,237,.12);color:#7c3aed">테이블 1</span>
                <span class="tag ac" style="margin-left:auto">좌표 고정</span></div>
            </div>

            <div class="tpcol">
              <div class="savebar">
                <button class="ms-btn">삭제</button>
                <button class="ms-btn go" data-toast="템플릿을 저장했습니다.">저장</button>
              </div>
              <div class="opanel">
                <h2 class="oclab">템플릿 명</h2>
                <input class="ms-input" value="거래명세서_한국휴텍스" style="width:100%">
                <h2 class="oclab" style="margin-top:8px">문서 유형</h2>
                <select class="ms-input" style="width:100%"><option>선택 안 함</option><option>영수증</option><option selected>거래명세서</option><option>세금계산서</option></select>

                <div class="osec">
                  <div class="sech"><h3 class="sect">출력 필드 정의</h3>
                    <button class="ms-btn-sm">삭제</button></div>
                  <div class="g3 hd"><span>No</span><span>영문 필드명</span><span>한글 필드명</span></div>
                  <div class="g3 " data-r="1"><span class="n0">1</span><input value="documentTitle"><input value="문서 제목"></div>
                  <div class="g3 " data-r="2"><span class="n0">2</span><input value="issueDate"><input value="거래일자"></div>
                  <div class="g3 " data-r="3"><span class="n0">3</span><input value="supplierBizNumber"><input value="공급자 등록번호"></div>
                  <div class="g3 " data-r="4"><span class="n0">4</span><input value="supplierCompany"><input value="공급자 상호"></div>
                  <div class="g3 " data-r="5"><span class="n0">5</span><input value="supplierAddress"><input value="공급자 주소"></div>
                  <div class="g3 " data-r="6"><span class="n0">6</span><input value="buyerBizNumber"><input value="공급받는자 등록번호"></div>
                  <div class="g3 " data-r="7"><span class="n0">7</span><input value="buyerCompany"><input value="공급받는자 상호"></div>
                  <div class="g3 sel" data-r="8"><span class="n0">8</span>
                    <input value="items"><input value="품목"></div>
                </div>

                <div class="osec">
                  <div class="sech"><h3 class="sect">선택 영역 <span class="fkey">(items)</span></h3></div>
                  <h2 class="oclab">그리드 모드</h2>
                  <div style="display:flex;gap:8px;margin-bottom:10px">
                    <button class="mbtn on">가변 그리드</button>
                    <button class="mbtn">고정 그리드</button></div>
                  <h2 class="oclab">종료 키워드 (쉼표로 구분)</h2>
                  <input class="ms-input" value="합계, 총액, 이월" style="width:100%">
                  <div style="display:flex;gap:8px;margin:10px 0">
                    <button class="mbtn on">세로 가이드</button>
                    <button class="mbtn">행 개별 조정</button></div>
                  <h2 class="oclab" style="margin-top:10px">세로 가이드선</h2>
                  <div style="display:flex;gap:5px;flex-wrap:wrap"><button class="chip">5.7% &times;</button><button class="chip">35.0% &times;</button><button class="chip">41.7% &times;</button><button class="chip">46.7% &times;</button><button class="chip">56.7% &times;</button><button class="chip">67.9% &times;</button><button class="chip">77.0% &times;</button><button class="chip">89.3% &times;</button></div>
                  <div class="info">가변 그리드: <b>세로 가이드(컬럼)</b>와 <b>종료 키워드</b> 기반으로
                    OCR 단계에서 행을 자동 감지합니다.</div>

                  <div style="margin-top:14px;padding-top:10px;border-top:1px solid var(--border)">
                    <div class="sech"><h3 class="sect" style="font-size:13px">컬럼 정의</h3>
                      <span class="fkey">세로 가이드 8개 &rarr; 컬럼 9개</span></div>
                    <div class="g4 hd"><span>No</span><span>영문 컬럼명</span>
                      <span>한글 컬럼명</span><span>표준 컬럼</span></div>
                    <div class="g4"><span class="n0">1</span><input value="no"><input value="번호"><select><option selected>선택 안 함</option><option>itemName (품목명)</option><option>spec (규격)</option><option>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                    <div class="g4"><span class="n0">2</span><input value="itemName"><input value="제품명"><select><option>선택 안 함</option><option selected>itemName (품목명)</option><option>spec (규격)</option><option>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                    <div class="g4"><span class="n0">3</span><input value="spec"><input value="규격"><select><option>선택 안 함</option><option>itemName (품목명)</option><option selected>spec (규격)</option><option>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                    <div class="g4"><span class="n0">4</span><input value="quantity"><input value="수량"><select><option>선택 안 함</option><option>itemName (품목명)</option><option>spec (규격)</option><option selected>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                    <div class="g4"><span class="n0">5</span><input value="unitPrice"><input value="단가"><select><option>선택 안 함</option><option>itemName (품목명)</option><option>spec (규격)</option><option>quantity (수량)</option><option selected>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                    <div class="g4"><span class="n0">6</span><input value="amount"><input value="금액"><select><option>선택 안 함</option><option>itemName (품목명)</option><option>spec (규격)</option><option>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option selected>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                    <div class="g4"><span class="n0">7</span><input value="discount"><input value="에누리"><select><option selected>선택 안 함</option><option>itemName (품목명)</option><option>spec (규격)</option><option>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                    <div class="g4"><span class="n0">8</span><input value="salePrice"><input value="판매가"><select><option selected>선택 안 함</option><option>itemName (품목명)</option><option>spec (규격)</option><option>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                    <div class="g4"><span class="n0">9</span><input value="remark"><input value="비고"><select><option>선택 안 함</option><option>itemName (품목명)</option><option>spec (규격)</option><option>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option selected>remark (비고)</option></select></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 비정형 생성 -->
        <div class="tmpane" id="tm-uns">
          <div class="cols" style="grid-template-columns:1fr 420px">
            <div class="card">
              <div class="uzone">
                <div class="em">&#128203;</div>
                <div>
                  <h4 style="text-align:center">비정형 생성이란?</h4>
                  <p>고정된 양식이 없는 문서에서 원하는 정보를 자유롭게 추출하는 방식입니다.<br>
                    우측에서 <b>출력 필드</b>를 정의하면 문서 내 해당 정보를 자동으로 찾아 반환합니다.</p>
                </div>
                <div class="ucards">
                  <div class="uc"><span class="ic">&#128196;</span><b>다양한 문서 지원</b>
                    <span>계약서&middot;이메일&middot;보고서 등 형식이 달라도 적용 가능</span></div>
                  <div class="uc"><span class="ic">&#127991;&#65039;</span><b>필드 자유 정의</b>
                    <span>추출할 항목을 영문&middot;한글로 직접 입력해 커스터마이징</span></div>
                  <div class="uc"><span class="ic">&#128269;</span><b>위치 무관 인식</b>
                    <span>고정 위치 없이 문서 어디서든 원하는 정보를 찾아냄</span></div>
                </div>
              </div>
            </div>

            <div class="tpcol">
              <div class="savebar">
                <button class="ms-btn">삭제</button>
                <button class="ms-btn go" data-toast="템플릿을 저장했습니다.">저장</button>
              </div>
              <div class="opanel">
                <h2 class="oclab">템플릿 명</h2>
                <input class="ms-input" value="거래명세서_공통" style="width:100%">
                <h2 class="oclab" style="margin-top:8px">문서 유형</h2>
                <select class="ms-input" style="width:100%"><option>선택 안 함</option><option>영수증</option><option selected>거래명세서</option><option>세금계산서</option></select>

                <div class="osec">
                  <div class="sech"><h3 class="sect">출력 정의</h3>
                    <div style="display:flex;gap:5px">
                      <button class="ms-btn-sm">영역 정의</button>
                      <button class="ms-btn-sm">테이블 정의</button>
                      <button class="ms-btn-sm">삭제</button></div></div>

                  <h2 class="oclab" style="margin-top:10px">일반 영역</h2>
                  <div class="g3 hd"><span>No</span><span>영문 필드명</span><span>한글 필드명</span></div>
                  <div class="g3 "><span class="n0">1</span><input value="issueDate"><input value="거래일자"></div>
                  <div class="g3 "><span class="n0">2</span><input value="supplierBizNumber"><input value="공급자 등록번호"></div>
                  <div class="g3 "><span class="n0">3</span><input value="supplierCompany"><input value="공급자 상호"></div>
                  <div class="g3 "><span class="n0">4</span><input value="supplierAddress"><input value="공급자 주소"></div>
                  <div class="g3 "><span class="n0">5</span><input value="buyerBizNumber"><input value="공급받는자 등록번호"></div>
                  <div class="g3 "><span class="n0">6</span><input value="buyerCompany"><input value="공급받는자 상호"></div>
                  <div class="g3 "><span class="n0">7</span><input value="totalAmount"><input value="합계금액"></div>

                  <h2 class="oclab" style="margin-top:16px">테이블 정의</h2>
                  <div class="tcard">
                    <div class="th"><span class="n0">8</span>
                      <input value="items"><input value="품목">
                      <button class="ms-btn-sm">+ 컬럼</button></div>
                    <div>
                      <div class="g4 hd"><span>No</span><span>영문 컬럼명</span>
                        <span>한글 컬럼명</span><span>표준 컬럼</span></div>
                      <div class="g4"><span class="n0">1</span><input value="itemName"><input value="품명"><select><option>선택 안 함</option><option selected>itemName (품목명)</option><option>spec (규격)</option><option>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                      <div class="g4"><span class="n0">2</span><input value="spec"><input value="규격"><select><option>선택 안 함</option><option>itemName (품목명)</option><option selected>spec (규격)</option><option>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                      <div class="g4"><span class="n0">3</span><input value="quantity"><input value="수량"><select><option>선택 안 함</option><option>itemName (품목명)</option><option>spec (규격)</option><option selected>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                      <div class="g4"><span class="n0">4</span><input value="unitPrice"><input value="단가"><select><option>선택 안 함</option><option>itemName (품목명)</option><option>spec (규격)</option><option>quantity (수량)</option><option selected>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                      <div class="g4"><span class="n0">5</span><input value="amount"><input value="금액"><select><option>선택 안 함</option><option>itemName (품목명)</option><option>spec (규격)</option><option>quantity (수량)</option><option>unitPrice (단가)</option><option>supplyAmount (공급가액)</option><option>taxAmount (세액)</option><option selected>amount (금액)</option><option>lotNo (제조번호)</option><option>expiryDate (유효기간)</option><option>itemCode (품목코드)</option><option>unit (단위)</option><option>remark (비고)</option></select></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ================= 02 OCR 실행 ================= -->
      <section class="view" id="v-ocr">
        <div class="tpl">
          {tpl_run}
        </div>
        <div class="cols" style="grid-template-columns:1fr 280px">
          <div class="card">
            <div class="card-h"><span class="t">업로드 문서</span>
              <button class="ms-btn-sm" data-up="filled">파일 선택</button></div>

            <div class="upstate on" id="up-empty">
              <div class="dropzone">
                <div class="dz-ic">&uarr;</div>
                <div class="dz-t">문서를 드래그하거나 업로드하세요</div>
                <div class="dz-s">이미지(.jpeg .jpg .png .tif .tiff) 및 PDF 지원</div>
                <button class="ms-btn" data-up="filled"
                  style="margin-top:14px;background:var(--accent);border-color:var(--accent);color:#fff">파일 선택</button>
              </div>
            </div>

            <div class="upstate" id="up-filled">
              <div class="doc">
{paper01}
              </div>
              <div class="bar"><span class="fnchip">{docid}</span>
                <button class="ms-btn-sm" data-up="empty" style="margin-left:auto">파일 변경</button></div>
            </div>
          </div>
          <div class="card">
            <div class="guide" style="border-bottom:1px solid var(--border)">
              <div class="gs" style="margin-bottom:0"><h5>모델 선택</h5>
                <select class="mdsel" style="margin-top:6px">
                  <option>기본 모델</option><option>학습 모델</option></select></div>
            </div>
            <div class="guide scroll fill" id="gFile" style="display:none">
              <div class="gs"><h5>업로드 파일</h5>
                <div class="frow2"><span>파일명</span><b>{docid}</b></div>
                <div class="frow2"><span>파일타입</span><b>JPEG 이미지</b></div>
                <div class="frow2"><span>소요 시간</span><b>0.4초</b></div></div>
            </div>
            <div class="guide scroll fill" id="gEmpty">
              <div class="gs"><h5>지원 형식</h5><div class="gd">업로드 / 내보내기 가능한 파일 형식</div>
                <ul><li>업로드: jpeg, jpg, png, tif, tiff, pdf</li>
                  <li>내보내기: JSON, Markdown</li></ul></div>
              <div class="gs"><h5>자동 처리</h5><div class="gd">실행 시 순서대로 수행됩니다</div>
                <ul><li>문서 영역 검출 - 배경 잘라내기</li>
                  <li>회전 보정 - 90&deg; / 270&deg; 뒤집힘</li>
                  <li>해상도 보정 - 세로 1500px 미만이면 확대</li>
                  <li>기울기 보정 - 5&deg; 이내 자동 교정</li>
                  <li>대비 강화</li></ul></div>
              <div class="gs"><h5>업로드 가이드</h5><div class="gd">정확도를 높이기 위한 권장 조건</div>
                <ul><li>150~300dpi &middot; 세로 1500px 이상</li>
                  <li>글자 번짐 &middot; 흔들림 없음</li>
                  <li>표 테두리가 잘리지 않게</li>
                  <li>기울기 5&deg; 이내</li></ul></div>
            </div>
            <div style="padding:12px 13px;border-top:1px solid var(--border)">
              <button class="runbtn" id="runBtn" data-view-go="run" disabled>Run OCR</button></div>
          </div>
        </div>
      </section>

      <!-- ================= 03 실행 결과 ================= -->
      <section class="view" id="v-run">
        <div class="kpis">
          <div class="kpi"><span>문서</span><b style="font-size:13px">{docid}</b></div>
          <div class="kpi"><span>모델</span><b>기본</b></div>
          <div class="kpi"><span>문서 정보 필드</span><b>{n_doc}</b></div>
          <div class="kpi"><span>표</span><b>{n_item}행</b></div>
          <div class="kpi"><span>확인 필요</span><b class="was">{n_need}</b></div>
        </div>
        <div class="cols c-46">
          <div class="card">
            <div class="card-h"><span class="t">업로드 문서</span>
              <div style="display:flex;gap:6px;align-items:center">
                <span class="tag mu" id="fbHint">행을 누르면 문서에서 표시됩니다</span>
                <span class="tag mu">{docid}</span></div></div>
            <div class="doc">
              <div class="cvs" id="runCvs">
                <div class="scan" id="pR" role="img" aria-label="{docid}"></div>
                {boxes}
              </div>
            </div>
          </div>
          <div class="card">
            <div class="ortabs" id="orTabs">
              <button class="ortab on" data-tab="preview">Preview</button>
              <button class="ortab" data-tab="custom">Custom</button>
              <button class="ortab" data-tab="validation">Validation<span class="bdg">3</span></button>
            </div>
            <div class="orbody">
              <div class="orpane on" id="pane-preview">
                <div class="modes">
                  <button class="ms-btn-sm" style="border-color:var(--accent);color:var(--accent)">Markdown</button>
                  <button class="ms-btn-sm">JSON</button>
                </div>
                <div class="scroll fill">
                  <div class="ftool" data-ftool="#tbPrev,#tbPrevItem">
                    <input class="ms-input" data-q placeholder="필드명 · 값 검색" style="width:220px">
                    <div class="seg" data-seg>
                      <button class="on" data-f="all">전체 {n_tot}</button>
                      <button data-f="need">확인 필요 {n_need}</button>
                    </div>
                    <span class="fc" data-cnt></span>
                  </div>
                  <div class="srcbar">문서 정보 {n_doc}개</div>
                  <table id="tbPrev">
                    <thead><tr><th style="width:28px">No</th><th style="width:126px">한글 필드명</th>
                      <th style="width:146px">영문 필드명</th><th>원본 데이터</th>
                      <th style="width:82px;text-align:center">상태</th></tr></thead>
                    <tbody>
                  {doc_ro}
                    </tbody>
                  </table>
                  <div class="srcbar" style="border-top:1px solid var(--border)">
                    표 {n_item}행</div>
                  <table id="tbPrevItem">
                    <thead><tr><th style="width:28px">No</th><th>품명</th>
                      <th style="width:56px">규격</th><th class="n" style="width:52px">수량</th>
                      <th class="n" style="width:76px">단가</th><th class="n" style="width:86px">금액</th>
                      <th style="width:82px;text-align:center">상태</th></tr></thead>
                    <tbody>
                  {items_base}
                    </tbody>
                  </table>
                </div>
                <details class="rawocr">
                  <summary>전체 OCR 텍스트 ({n_raw}줄)</summary>
                  <div class="rawbody">{raw_lines}</div>
                </details>
                <div class="bar"><span class="lab">내보내기</span>
                  <button class="ms-btn-sm" data-toast="JSON 파일을 내려받습니다.">JSON</button>
                  <button class="ms-btn-sm" data-toast="Markdown 파일을 내려받습니다.">Markdown</button>
                </div>
              </div>
              <div class="orpane" id="pane-custom">
                <div class="modes">
                  <button class="mbtn on" data-dm="필드">필드</button>
                  <button class="mbtn" data-dm="멀티필드">멀티필드</button>
                  <button class="mbtn" data-dm="체크필드">체크필드</button>
                  <button class="mbtn" data-dm="테이블필드">테이블필드</button>
                  <div class="sp">
                    <button class="ms-btn-sm" id="reRun"
                      style="background:var(--accent);border-color:var(--accent);color:#fff">OCR 재실행</button>
                  </div>
                </div>
                <div class="dmhelp" id="dmHelp">단일 영역에서 하나의 값을 읽습니다.</div>
                <div class="scroll fill">
                  <div class="ftool" data-ftool="#fcList">
                    <input class="ms-input" data-q placeholder="필드명 · 값 검색" style="width:220px">
                    <div class="seg" data-seg>
                      <button class="on" data-f="all">전체 {n_tot}</button>
                      <button data-f="need">확인 필요 {n_need}</button>
                    </div>
                    <span class="fc" data-cnt></span>
                  </div>
                  <div class="srcbar">필드 목록 <b>{n_fc}</b>건</div>
                  <div class="fclist" id="fcList">
                  {fcards}
                    <div class="fcard" id="itemCard">
                      <div class="fch"><span class="fcn">{n_fc}. 품목<em>items</em></span>
                        <select class="fcsel"><option>필드</option><option>멀티필드</option>
                          <option>체크필드</option><option selected>테이블필드</option></select>
                        <span class="fcad" style="color:#2563eb">OCR</span>
                        <button class="fcx">&#10005;</button></div>
                      <table id="tbCustomItem">
                        <thead><tr><th style="width:28px">No</th><th>품명</th>
                          <th style="width:72px">규격</th><th style="width:66px">수량</th>
                          <th style="width:92px">단가</th><th style="width:102px">금액</th>
                          <th style="width:82px;text-align:center">상태</th></tr></thead>
                        <tbody>
                      {item_rw}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
              <div class="orpane" id="pane-validation">
                <div class="valsum"><span class="h">검수 결과</span>
                  <span class="tag er">확인 필요</span>
                  <span style="font-size:12px;color:var(--muted)">오류 <b>3</b>건 / 경고 <b>5</b>건 / 성공 <b>26</b>건</span>
                  <div style="margin-left:auto;display:flex;gap:6px">
                    <span class="tag wa">검산 불가 - 금액 미검출</span></div>
                </div>
                <div class="scroll fill" style="padding-bottom:12px">
                  <div class="valsec"><div class="st"><span>오류 내역: 3건</span>
                    <button class="ms-btn-sm" data-gotab="custom" data-jump="supplyAmount">오류 수정</button></div>
{val_er}
                  </div>
                  <div class="valsec"><div class="st"><span>경고 내역: 5건</span>
                    <button class="ms-btn-sm" data-gotab="custom" data-jump="supplierCompany">경고 확인</button></div>
{val_wa}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ================= 03 확인 항목 ================= -->
      <section class="view" id="v-missed">
          <div class="card" style="flex:none">
            <div class="filt">
              <span class="fl">요청일시</span>
              <input class="ms-input" type="date" style="width:150px">
              <span class="fl">~</span>
              <input class="ms-input" type="date" value="2026-08-12" style="width:150px">
              <span class="fl" style="margin-left:6px">상태</span>
              <select class="ms-select" style="width:100px"><option>전체</option></select>
              <span class="fl" style="margin-left:6px">모델</span>
              <select class="ms-select" id="mdFilter" style="width:100px">
                <option>전체</option><option>기본</option><option>학습</option></select>
              <span class="fl" style="margin-left:6px">확인 필요</span>
              <select class="ms-select" id="needFilter" style="width:100px">
                <option>전체</option><option>있음</option><option>없음</option></select>
              <button class="ms-btn" style="background:var(--accent);border-color:var(--accent);color:#fff">조회</button>
              <button class="ms-btn" style="border-color:var(--err);color:var(--err)">전체 삭제</button>
            </div>
          </div>
          <div class="cols" style="grid-template-columns:1fr 1.05fr">
            <div class="card fill">
              <div class="card-h"><span class="t">실행 이력</span>
                <div style="display:flex;gap:6px;align-items:center">
                  <span class="tag mu">총 12건</span></div></div>
              <div class="scroll fill">
                <table>
                  <thead><tr><th style="width:40px">No</th><th style="width:88px">템플릿명</th>
                    <th style="width:70px">모델</th><th style="width:150px">요청일시</th>
                    <th style="width:70px">상태</th><th>파일명</th><th style="width:90px">확인 필요</th>
                    <th style="width:64px;text-align:center">보기</th>
                    <th style="width:64px;text-align:center">삭제</th></tr></thead>
                  <tbody>
                  {hist_rows}
                  <tr class="hempty2" style="display:none"><td colspan="9"
                    style="text-align:center;color:var(--muted);padding:26px 10px">
                    해당하는 실행이 없습니다</td></tr>
                  </tbody>
                </table>
              </div>
              <div class="lpage" id="hstpage">
                <span class="lcount" id="hstrange"></span>
                <div class="pager" id="hstpager">
                  <button id="hstprev" aria-label="이전">&lsaquo;</button>
                  <span class="pg" id="hstpg"></span>
                  <button id="hstnext" aria-label="다음">&rsaquo;</button>
                </div>
              </div>
            </div>
            <div class="card fill">
              <div class="card-h"><span class="t">필드별 결과</span>
                <div style="display:flex;gap:8px;align-items:center">
                <span class="tag mu">문서 {ndoc}장 기준</span>
                <div class="seg" id="aggSeg">
                  <button class="on" data-agg="base">기본</button>
                  <button data-agg="tuned">학습</button>
                  <button data-agg="diff">비교</button></div></div></div>
              <div class="scroll fill">
                <table class="aggt on" data-agg="base">
                  <thead><tr><th style="width:140px">필드</th><th class="n" style="width:78px">정상</th><th class="n" style="width:54px">확인</th><th style="width:124px">정상률</th><th style="width:150px">원인</th><th style="width:64px">해결</th></tr></thead>
                  <tbody>
                  {agg_base}
                  </tbody>
                </table>
                <table class="aggt" data-agg="tuned">
                  <thead><tr><th style="width:140px">필드</th><th class="n" style="width:78px">정상</th><th class="n" style="width:54px">확인</th><th style="width:124px">정상률</th><th style="width:150px">원인</th><th style="width:64px">해결</th></tr></thead>
                  <tbody>
                  {agg_tuned}
                  </tbody>
                </table>
                <table class="aggt" data-agg="diff">
                  <thead><tr><th style="width:140px">필드</th><th class="n" style="width:84px">기본</th><th class="n" style="width:84px">학습</th><th class="n" style="width:62px">변화</th><th style="width:124px">정상률</th><th style="width:150px">원인</th><th style="width:64px">해결</th></tr></thead>
                  <tbody>
                  {agg_diff}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
      </section>

      <!-- ================= 04 상세보기 ================= -->
      <section class="view" id="v-detail">
          <div class="card" style="flex:none">
            <div class="card-h">
              <div style="display:flex;align-items:center;gap:9px">
                <span class="t">확인 항목</span><span class="tag mu">비정형</span>
                <span style="font-size:12px;color:var(--muted)">{docid} &middot; 2026-08-12 09:12</span></div>
              <div style="display:flex;gap:6px;align-items:center">
                <span class="tag wa">확인 필요 {n_need}</span>
                <button class="ms-btn-sm" data-toast="수정한 값을 정답 기준값으로 저장합니다."
                  style="background:var(--accent);border-color:var(--accent);color:#fff">저장</button>
                <button class="ms-btn-sm" data-view-go="missed">목록</button></div>
            </div>
          </div>
          <div class="cols" style="grid-template-columns:.72fr 1.28fr">
            <div class="stack">
              <div class="card fill">
                <div class="card-h"><span class="t">전처리 전 이미지</span>
                  <span class="tag mu">기울기 -0.8&deg;</span></div>
                <div class="doc">
{paper03b}
                </div>
              </div>
              <div class="card fill">
                <div class="card-h"><span class="t">전처리 후 이미지</span>
                  <span class="tag mu">보정 적용</span></div>
                <div class="doc">
{paper03a}
                </div>
              </div>
            </div>
            <div class="card">
              <div class="card-h"><span class="t">인식 결과</span>
                <div style="display:flex;gap:8px;align-items:center">
                  <div class="seg" id="issueSeg">
                    <button class="on" data-f="all">전체 {n_field}</button>
                    <button data-f="need">확인 필요 {n_need}</button>
                  </div></div></div>
              <div class="scroll fill">
                <div class="srcbar">문서 정보 {n_doc}개</div>
                <table>
                  <thead><tr><th style="width:150px">필드</th>
                    <th>OCR값</th><th style="width:230px">정답 · 수정</th>
                    <th style="width:82px;text-align:center">상태</th>
                    <th style="width:62px;text-align:right">신뢰도</th></tr></thead>
                  <tbody>
                  {issue_rows}
                  {ok_rows}
                  </tbody>
                </table>
                <div class="card-h" style="border-top:1px solid var(--border)">
                  <span class="t">표</span><span class="tag mu">{n_item}행</span></div>
                <table>
                  <thead><tr><th style="width:34px">No</th>
                    <th>품명</th><th style="width:88px">규격</th><th class="n" style="width:76px">수량</th>
                    <th class="n" style="width:96px">단가</th><th class="n" style="width:104px">금액</th>
                    <th style="width:78px;text-align:center">상태</th></tr></thead>
                  <tbody>
                  {ditem_rows}
                  </tbody>
                </table>
                <div class="card-h" style="border-top:1px solid var(--border)">
                  <span class="t">OCR 데이터</span><span class="tag mu">{n_raw}줄</span></div>
                <table>
                  <thead><tr><th style="width:34px">No</th><th style="width:104px">필드</th>
                    <th>원본 데이터</th><th style="width:70px;text-align:right">정확도</th></tr></thead>
                  <tbody>
                  {raw_rows}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
      </section>

      <!-- ================= 06 모델 비교 ================= -->
      <section class="view" id="v-compare">
          <div class="cols" style="grid-template-columns:1fr 300px">
            <div class="card">
              <div class="card-h"><span class="t">비교할 문서</span>
                <div style="display:flex;gap:6px;align-items:center">
                  <span class="tag mu" id="cmpCount" style="display:none">6건 중 1건 선택</span>
                  <button class="ms-btn-sm" id="cmpAdd" style="display:none">파일 추가</button>
                  <button class="ms-btn-sm" data-cup="filled">파일 선택</button></div></div>

              <div class="upstate on" id="cup-empty">
                <div class="dropzone">
                  <div class="dz-ic">&uarr;</div>
                  <div class="dz-t">비교할 문서를 올려주세요</div>
                  <div class="dz-s">02 에서 실행한 문서를 그대로 쓰면 앞뒤가 이어집니다</div>
                  <button class="ms-btn" data-cup="filled"
                    style="margin-top:14px;background:var(--accent);border-color:var(--accent);color:#fff">파일 선택</button>
                </div>
              </div>

              <div class="upstate" id="cup-filled">
                <div class="fbar">
                  {files}
                </div>
                <div class="doc">
{paper04r}
                </div>
                <div class="bar"><span class="tag mu">4.pdf</span><span class="tag mu">1.2 MB</span>
                  <span class="tag mu">2480 &times; 3508</span>
                  <span class="tag mu" style="margin-left:auto">평가셋 미포함</span></div>
              </div>
            </div>
            <div class="card">
              <div class="guide" style="border-bottom:1px solid var(--border)">
                <div class="gs"><h5>모델 A</h5>
                  <select class="mdsel" style="margin-top:6px">
                    <option>기본 모델</option><option>학습 모델</option></select></div>
                <div class="gs" style="margin-bottom:0"><h5>모델 B</h5>
                  <select class="mdsel" style="margin-top:6px">
                    <option>학습 모델 &middot; {run}</option><option>기본 모델</option></select></div>
              </div>
              <div class="guide scroll fill">
                <div class="gs"><h5>학습 모델</h5><div class="gd">05 에서 전달한 항목이 반영된 모델</div>
                  <ul><li>전달 항목 {n_mis}건</li><li>검증 위치 {tot_n}개</li>
                    <li>인식 모델만 교체</li></ul></div>
                <div class="gs"><h5>실행 방식</h5><div class="gd">같은 문서를 두 모델에 각각 1회</div>
                  <ul><li>전처리 결과 공유</li><li>필드 추출 규칙 동일</li>
                    <li>인식 모델만 다름</li></ul></div>
                <div class="gs"><h5>표시 항목</h5><div class="gd">실행 후 보이는 내용</div>
                  <ul><li>필드별 학습 전 / 후</li><li>달라진 필드 강조</li>
                    <li>품명별 검증 결과</li></ul></div>
                <div class="gs"><h5>소요 예상</h5><div class="gd">문서 1건 기준</div>
                  <ul><li>약 7초 (두 모델 합계)</li></ul></div>
              </div>
              <div style="padding:12px 13px;border-top:1px solid var(--border)">
                <button class="runbtn" id="cmpRunBtn" data-view-go="cmpresult" disabled>두 모델로 실행</button></div>
            </div>
          </div>
      </section>

      <!-- ================= 07 비교 결과 ================= -->
      <section class="view" id="v-cmpresult">
        <div style="display:flex;align-items:center;gap:11px;flex:none">
          <span class="tag ac">학습 모델 &middot; 05 전달 항목 {n_mis}건 반영</span>
          <div style="margin-left:auto;display:flex;gap:7px">
            <button class="ms-btn" data-view-go="compare">새 문서</button>
            <button class="ms-btn" data-view-go="compare"
              style="background:var(--accent);border-color:var(--accent);color:#fff">다시 실행</button>
          </div>
        </div>
        <div class="kpis">
          <div class="kpi"><span>비교 항목</span><b>{n_cmp}</b></div>
          <div class="kpi"><span>달라진 항목</span><b style="color:var(--accent)">{n_allchg}</b></div>
          <div class="kpi"><span>문서 정보 필드</span><b>{n_doc}</b></div>
          <div class="kpi"><span>표</span><b>{n_item}행</b></div>
        </div>
        <div class="cols c-46">
          <div class="card">
            <div class="card-h"><span class="t">업로드 문서</span></div>
            <div class="doc">
{paper04}
            </div>
          </div>
          <div class="stack" id="cmpCard">
            <div class="card fill">
              <div class="card-h"><span class="t">문서 정보 필드 비교</span>
                <span class="tag {tag_dchg}">{n_doc}개 &middot; 변경 {n_dchg}</span></div>
              <div class="ftool" data-ftool="#tbCmp">
                <input class="ms-input" data-q placeholder="필드명 · OCR값 검색" style="width:230px">
                <span class="fc" data-cnt></span>
              </div>
              <div class="scroll fill">
                <table id="tbCmp">
                  <thead><tr><th style="width:150px">필드</th>
                    <th>학습 전</th><th>학습 후</th>
                    <th style="width:66px">판정</th></tr></thead>
                  <tbody>
                  {cmp_rows}
                  </tbody>
                </table>
              </div>
            </div>
            <div class="card fill">
              <div class="card-h"><span class="t">표 비교</span>
                <span class="tag ac">{n_ichg}개 변경</span></div>
              <div class="ftool" data-ftool="#tbICmp">
                <input class="ms-input" data-q placeholder="품명 · 값 검색" style="width:200px">
                <div class="seg" data-seg>
                  <button class="on" data-f="all">전체 {n_item}</button>
                  <button data-f="chg">변경 {n_ichg}</button>
                  <button data-f="same">동일 {n_isame}</button>
                </div>
                <span class="fc" data-cnt></span>
              </div>
              <div class="scroll fill">
                <table id="tbICmp">
                  <thead><tr><th style="width:34px">No</th><th>품명</th>
                    <th style="width:60px">규격</th><th class="n" style="width:52px">수량</th>
                    <th class="n" style="width:76px">단가</th><th class="n" style="width:86px">금액</th>
                    <th style="width:62px;text-align:center">판정</th></tr></thead>
                  <tbody>
                  {icmp_rows}
                  </tbody>
                </table>
              </div>
            </div>

        <div class="card fill" style="margin-top:8px">
          <div class="card-h"><span class="t">정답 대조 - 학습이 실제로 GT와 맞아졌는가</span>
            <span class="tag ac">v22 실측 &middot; 라이브 비교와 별개</span></div>
          <div class="scroll fill">
            <table>
              <thead><tr><th>품명</th><th style="width:100px">대상</th>
                <th class="n" style="width:76px">학습 전</th><th class="n" style="width:76px">학습 후</th>
                <th style="width:58px">결과</th></tr></thead>
              <tbody>
              {tgt_rows}
              </tbody>
            </table>
          </div>
          <div class="bar"><span class="lab">기준 데이터</span>
            <span class="tag mu">품명 셀 {basis}개 &middot; 문서 {docs}건</span>
            <span class="tag wa">유지 검사 257 잃음</span></div>
        </div>
          </div>
        </div>
      </section>

      <!-- ================= 08 처리 경로 ================= -->
      <section class="view" id="v-remaining">
        <div class="kpis" style="grid-template-columns:repeat(4,1fr)">
          <div class="kpi"><span>학습으로 해결</span><b class="now">{lost}</b></div>
          <div class="kpi"><span>다음 작업 대상 · 후처리 · 매칭</span><b style="color:var(--rule)">71</b></div>
          <div class="kpi"><span>사람 확인</span><b>9</b></div>
          <div class="kpi"><span>품명 검증 위치</span><b>{tot_b} &rarr; {tot_f} / {tot_n}</b></div>
        </div>

        <div class="rtabs" id="rTabs">
          <button class="rtab r1 on" data-route="learn"><span class="rno">1</span>
            <span><span class="rt">학습 현황</span>
              <span class="rd" style="display:block">글자를 잘못 읽은 것 - 재학습</span></span>
            <span class="rbig">{lost}</span></button>
          <button class="rtab r2" data-route="rule"><span class="rno">2</span>
            <span><span class="rt">남은 현황</span>
              <span class="rd" style="display:block">값이 제자리에 없는 것 - 후처리·매칭</span></span>
            <span class="rbig">71</span></button>
          <button class="rtab r3" data-route="human"><span class="rno">3</span>
            <span><span class="rt">사람 확인 현황</span>
              <span class="rd" style="display:block">자동으로 못 가리는 것 - 검수</span></span>
            <span class="rbig">9</span></button>
        </div>

        <div class="rpane on" id="rp-learn">
          <div class="card route r1" style="border-top:0;flex:1;min-height:0;overflow:auto">
            <div class="ltool">
              <input class="ms-input" id="lq" placeholder="품명 · OCR값 검색" style="width:260px">
              <select class="ms-select" id="lcol" style="width:150px">
                {col_opts}
              </select>
              <select class="ms-select" id="lchar" style="width:140px">
                {char_opts}
              </select>
              <div class="seg" id="lseg">
                <button class="on" data-res="all">전체 {n_all}</button>
                <button data-res="up">개선 {n_up}</button>
                <button data-res="keep">유지 {n_keep}</button>
                <button data-res="down">실패 {n_down}</button>
              </div>
              <span class="lcount" id="lcnt"></span>
            </div>
            <table id="learnTb">
              <thead><tr><th style="width:210px">인식 이미지</th><th>학습 전 OCR</th><th>학습 후 OCR</th>
                <th style="width:126px">바뀐 글자</th><th class="n" style="width:150px">검증 위치</th>
                <th style="width:60px">결과</th></tr></thead>
              <tbody>
                  {learn_rows}
                <tr class="tot"><td>합계</td><td></td><td></td><td></td>
                  <td class="n">{tot_b}/{tot_n} &rarr; {tot_f}/{tot_n}</td><td></td></tr>
                <tr class="lempty" style="display:none"><td colspan="6"
                  style="text-align:center;color:var(--muted);padding:26px 10px">
                  이 컬럼은 이번 학습 대상이 아닙니다</td></tr>
              </tbody>
            </table>
            <div class="bar"><span class="lab">기준 데이터</span>
              <span class="tag mu">품명 셀 {basis}개 &middot; 문서 {docs}건</span>
              <span class="tag wa">유지 검사 257 잃음</span></div>
            <div class="lpage">
              <span class="lcount" id="lrange"></span>
              <div class="pager" id="lpager">
                <button id="lprev" aria-label="이전">&lsaquo;</button>
                <span class="pg" id="lpg"></span>
                <button id="lnext" aria-label="다음">&rsaquo;</button>
              </div>
            </div>
          </div>
        </div>

        <div class="rpane" id="rp-rule">
          <div class="card route r2" style="border-top:0;flex:1;min-height:0;overflow:auto">
            <div class="ltool">
              <input class="ms-input" id="rq" placeholder="유형 · 값 · 처리 방법 검색" style="width:230px">
              <div class="seg" id="rseg">
                <button class="on" data-f="all">전체 5</button>
              </div>
              <span class="lcount" id="rcnt"></span>
            </div>
            <table id="ruleTb">
              <thead><tr><th style="width:132px">유형</th><th class="n" style="width:48px">건수</th>
                <th style="width:180px">현재 값</th><th style="width:180px">처리 후</th>
                <th>해결 방법</th><th style="width:150px">필요한 것</th></tr></thead>
              <tbody>
                <tr data-f="post" data-k="상호 성명 결합 후처리 한국휴텍스제약">
                  <td>상호·성명 결합</td><td class="n">1</td>
                  <td class="was">한국휴텍스제약(주)이상일,김성겸</td>
                  <td class="now">한국휴텍스제약</td>
                  <td><span class="tag" style="background:var(--ruleBg);color:var(--rule)">규칙</span>
                    상호 칸과 성명 칸 분리</td>
                  <td><span class="tag" style="background:var(--ruleBg);color:var(--rule)">규칙</span></td></tr>
                <tr data-f="post" data-k="품명 박스번호 결합 넥시메졸캡슐20mg 후처리 규칙">
                  <td>품명 &middot; 박스번호 결합</td><td class="n">23</td>
                  <td class="was">넥시메졸캡슐20mg // 1</td>
                  <td class="now">넥시메졸캡슐20mg</td>
                  <td><span class="tag" style="background:var(--ruleBg);color:var(--rule)">규칙</span>
                    품명 칸의 &laquo;// 박스번호&raquo; 꼬리 분리</td>
                  <td><span class="tag" style="background:var(--ruleBg);color:var(--rule)">규칙</span></td></tr>
                <tr data-f="post" data-k="규격 단위 표기 30T 30C 1EA 정규화 규칙">
                  <td>규격 단위 표기</td><td class="n">23</td>
                  <td class="was">30T &middot; 30C &middot; 1EA</td>
                  <td class="now">30정 &middot; 30캡슐 &middot; 1개</td>
                  <td><span class="tag" style="background:var(--ruleBg);color:var(--rule)">규칙</span>
                    단위 약어 &rarr; 표준 단위 변환</td>
                  <td><span class="tag" style="background:var(--ruleBg);color:var(--rule)">단위 사전</span></td></tr>
                <tr data-f="match" data-k="품목코드 미부여 품명 품목 마스터 매칭 itemCode">
                  <td>품목코드 미부여</td><td class="n">23</td>
                  <td class="none">없음</td>
                  <td class="now">품명 &rarr; 품목코드 자동 부여</td>
                  <td><span class="tag ac">매칭</span> <span class="tag mu">품목</span>
                    품명으로 품목 마스터 조회</td>
                  <td><span class="tag wa">품목 마스터</span></td></tr>
                <tr data-f="match" data-k="주소 마스터 불일치 매칭 거래처">
                  <td>주소 출처 불일치</td><td class="n">1</td>
                  <td class="was">경기 화성시 향남읍 제약공단3길 99한국휴텍스제</td>
                  <td class="now">경기 화성시 삼성1로 344-2 (반월동 101-1)</td>
                  <td><span class="tag ac">매칭</span> <span class="tag mu">거래처</span>
                    사업자번호로 거래처 마스터 조회</td>
                  <td><span class="tag wa">거래처 마스터</span></td></tr>
                <tr class="tot"><td>합계</td><td class="n">71</td><td></td><td></td>
                  <td>모델 교체 없이 처리</td><td></td></tr>
                <tr class="rempty" style="display:none"><td colspan="6"
                  style="text-align:center;color:var(--muted);padding:26px 10px">
                  해당하는 항목이 없습니다</td></tr>
              </tbody>
            </table>
            <div class="lpage" id="rpage">
              <span class="lcount" id="rrange"></span>
              <div class="pager" id="rpager">
                <button id="rprev" aria-label="이전">&lsaquo;</button>
                <span class="pg" id="rpg"></span>
                <button id="rnext" aria-label="다음">&rsaquo;</button>
              </div>
            </div>
          </div>
        </div>

        <div class="rpane" id="rp-human">
          <div class="card route r3" style="border-top:0;flex:1;min-height:0;overflow:auto">
            <div class="ltool">
              <input class="ms-input" id="hq" placeholder="조건 · 예 · 판정 방법 검색" style="width:230px">
              <div class="seg" id="hseg">
                <button class="on" data-f="hit">발생 4</button><button data-f="all">전체 13</button>
              </div>
              <span class="lcount" id="hcnt"></span>
            </div>
            <table id="humanTb">
              <thead><tr><th style="width:132px">조건</th><th class="n" style="width:56px">건수</th><th style="width:220px">예</th>
                <th>자동 판정 방법</th></tr></thead>
              <tbody>
                <tr data-f="warn" data-k="해상도 부족 150dpi 미만 &middot; 글자 높이 10px 미만 업로드 시 이미지 메타 검사 업로드 경고"><td>해상도 부족</td><td class="n">0</td><td>150dpi 미만 &middot; 글자 높이 10px 미만</td><td>업로드 시 이미지 메타 검사</td></tr>
                <tr data-f="warn" data-k="지원 안 하는 형식 jpeg / jpg / png / pdf / tif 외 확장자 &middot; MIME 검사 업로드 경고"><td>지원 안 하는 형식</td><td class="n">0</td><td>jpeg / jpg / png / pdf / tif 외</td><td>확장자 &middot; MIME 검사</td></tr>
                <tr data-f="warn" data-k="파일 손상 열 수 없는 파일 디코딩 실패 업로드 경고"><td>파일 손상</td><td class="n">0</td><td>열 수 없는 파일</td><td>디코딩 실패</td></tr>
                <tr data-f="rescan" data-k="인쇄 상태 불량 번짐 &middot; 흐림 &middot; 저해상 인식 신뢰도 40% 미만 재스캔"><td>인쇄 상태 불량</td><td class="n">0</td><td>번짐 &middot; 흐림 &middot; 저해상</td><td>인식 신뢰도 40% 미만</td></tr>
                <tr data-f="rescan" data-k="페이지 회전 실패 90&deg; / 270&deg; 뒤집힘 orientation 판정 재스캔"><td>페이지 회전 실패</td><td class="n">0</td><td>90&deg; / 270&deg; 뒤집힘</td><td>orientation 판정</td></tr>
                <tr data-f="rescan" data-k="표 미검출 품목표를 찾지 못함 표 영역 검출 실패 재스캔"><td>표 미검출</td><td class="n">0</td><td>표를 찾지 못함</td><td>표 영역 검출 실패</td></tr>
                <tr data-f="review" data-hit="1" data-k="모양이 같은 글자 O / 0 &middot; l / 1 &middot; 다 / 디 후보가 둘 이상인데 산술·대조로도 하나로 안 좁혀짐 검수"><td>모양이 같은 글자</td><td class="n">1</td><td>O / 0 &middot; l / 1 &middot; 다 / 디</td><td>후보가 둘 이상인데 산술·대조로도 하나로 안 좁혀짐</td></tr>
                <tr data-f="review" data-k="복합 오류 한 셀에 두 가지 이상 어느 규칙도 단독으로 적용되지 않음 검수"><td>복합 오류</td><td class="n">0</td><td>한 셀에 두 가지 이상</td><td>어느 규칙도 단독으로 적용되지 않음</td></tr>
                <tr data-f="review" data-hit="1" data-k="인식 신뢰도 낮음 필드 신뢰도 70% 미만 필드별 신뢰도 임계값 검수"><td>인식 신뢰도 낮음</td><td class="n">2</td><td>필드 신뢰도 70% 미만</td><td>필드별 신뢰도 임계값</td></tr>
                <tr data-f="review" data-k="산술 불일치 수량 &times; 단가 &ne; 공급가 행 검산 &middot; 열 합계 &middot; 세액 10% &middot; 공급가+세액=합계 검수"><td>산술 불일치</td><td class="n">0</td><td>수량 &times; 단가 &ne; 공급가</td><td>행 검산 &middot; 열 합계 &middot; 세액 10% &middot; 공급가+세액=합계</td></tr>
                <tr data-f="review" data-k="사업자번호 이상 폐업 &middot; 없는 번호 국세청 사업자 상태 조회 검수"><td>사업자번호 이상</td><td class="n">0</td><td>폐업 &middot; 없는 번호</td><td>국세청 사업자 상태 조회</td></tr>
                <tr data-f="review" data-hit="1" data-k="필수 필드 누락 누계 미검출 고객이 지정한 필수 필드가 비어 있음 검수"><td>필수 필드 누락</td><td class="n">3</td><td>공급가액 &middot; 세액 &middot; 합계 미검출</td><td>고객이 지정한 필수 필드가 비어 있음</td></tr>
                <tr data-f="review" data-hit="1" data-k="미등록 품명 품명 대장에 없는 품명 품명 대장 대조 실패 검수"><td>미등록 품명</td><td class="n">3</td><td>품명 대장에 없는 품명</td><td>품명 대장 대조 실패</td></tr>
                <tr class="tot"><td>합계</td><td class="n">9</td><td></td><td></td></tr>
                <tr class="hempty" style="display:none"><td colspan="4"
                  style="text-align:center;color:var(--muted);padding:26px 10px">
                  해당하는 항목이 없습니다</td></tr>
              </tbody>
            </table>
            <div class="lpage" id="hpage">
              <span class="lcount" id="hrange"></span>
              <div class="pager" id="hpager">
                <button id="hprev" aria-label="이전">&lsaquo;</button>
                <span class="pg" id="hpg"></span>
                <button id="hnext" aria-label="다음">&rsaquo;</button>
              </div>
            </div>
          </div>
        </div>
        </div>
      </section>

    </div>
  </div>
</div>
<div class="toast" id="toast"></div>

<script>
const T={{tpl:'템플릿',ocr:'OCR 실행',run:'실행 결과',missed:'실행 이력',detail:'확인 항목',compare:'모델 비교',cmpresult:'비교 결과',remaining:'처리 경로'}};
function openView(n){{
  document.querySelectorAll('.view').forEach(v=>v.classList.toggle('on',v.id==='v-'+n));
  document.querySelectorAll('.nav a[data-view]').forEach(a=>a.classList.toggle('on',a.dataset.view===n));
  document.querySelector('#hdTitle').textContent=T[n];
  if(location.hash.slice(1)!==n)history.replaceState(null,'','#'+n);
}}
document.querySelectorAll('.nav a[data-view]').forEach(a=>
  a.addEventListener('click',()=>openView(a.dataset.view)));
function upState(n){{
  document.querySelectorAll('.upstate').forEach(x=>x.classList.toggle('on',x.id==='up-'+n));
  const on=n==='filled';
  // 제품은 파일이 있으면 가이드 대신 업로드 파일 정보를 보여준다
  document.querySelector('#gFile').style.display=on?'':'none';
  document.querySelector('#gEmpty').style.display=on?'none':'';
  document.querySelector('#runBtn').disabled=!on;
}}
const DMH={{'필드':'단일 영역에서 하나의 값을 읽습니다.',
 '멀티필드':'여러 영역 또는 여러 줄을 합쳐 하나의 값으로 사용합니다.',
 '체크필드':'체크 여부나 선택 상태를 판정합니다.',
 '테이블필드':'반복되는 표 영역을 읽습니다.'}};
document.querySelectorAll('[data-dm]').forEach(b=>b.addEventListener('click',()=>{{
  // 제품과 같이 같은 버튼을 다시 누르면 해제된다
  const on=b.classList.contains('on');
  document.querySelectorAll('[data-dm]').forEach(x=>x.classList.remove('on'));
  if(!on)b.classList.add('on');
  document.querySelector('#dmHelp').textContent=on?'그릴 영역 종류를 고르세요.':DMH[b.dataset.dm];
}}));
const rr=document.querySelector('#reRun');
if(rr)rr.addEventListener('click',()=>{{
  // 전체가 아니라 신뢰도 0.7 미만이거나 값이 빈 필드만 다시 돌린다
  const t=[...document.querySelectorAll('#fcList .fcard.bad')];
  toast(t.length?('재실행 대상 '+t.length+'건 · 신뢰도 70% 미만 또는 값 없음')
               :'재실행할 대상이 없습니다. (모두 100%)');
}});
(()=>{{
  const ZB={zbox};
  // 한 조각을 한 줄에 앉힌다. 배율은 심어 둔 화소의 1.5배가 상한이다.
  // 넘기면 없는 화소를 만들어내서 글자가 뭉개진다.
  const put=(row,b)=>{{
    const im=row.querySelector('.zimg');
    const bw=row.clientWidth, bh=row.clientHeight;
    // 가로만 맞추면 좁은 필드(공급받는자 상호 33%)가 세로로 칸을 넘어 잘린다.
    // 가로·세로·화소 상한 셋 중 가장 작은 배율을 쓴다.
    const iw=Math.min(bw/(b[2]/100),
                      bh*0.88/((b[3]/100)*1410/1000),
                      1800*1.5);
    const ih=iw*1410/1000;
    im.style.display='block';
    im.style.width=iw+'px'; im.style.height=ih+'px';
    const rw=(b[2]/100)*iw;
    im.style.left=(-(b[0]/100)*iw+(bw-rw)/2)+'px';
    im.style.top=(-(b[1]/100)*ih+(bh-(b[3]/100)*ih)/2)+'px';
  }};
  const rows=[...document.querySelectorAll('#v-detail tbody tr[data-fb]')];
  rows.forEach(r=>r.addEventListener('click',()=>{{
    const exp=r.nextElementSibling, open=exp&&exp.classList.contains('on');
    document.querySelectorAll('#v-detail .zexp.on').forEach(x=>x.classList.remove('on'));
    rows.forEach(x=>x.classList.remove('pick'));
    // 같은 행을 다시 누르면 접는다
    if(open||!exp||!exp.classList.contains('zexp'))return;
    r.classList.add('pick'); exp.classList.add('on');
    const b=ZB[r.dataset.fb];
    exp.querySelector('.zpair').style.display=b?'flex':'none';
    exp.querySelector('.znone').style.display=b?'none':'block';
    if(b)exp.querySelectorAll('.zrow').forEach(z=>put(z,b));
  }}));
}})();
(()=>{{
  const cvs=document.querySelector('#runCvs'); if(!cvs)return;
  const hint=document.querySelector('#fbHint');
  const rows=[...document.querySelectorAll('#v-run tbody tr[data-fb],#v-run .fcard[data-fb]')];
  const clear=()=>cvs.querySelectorAll('.rgn.hi').forEach(b=>b.classList.remove('hi'));
  rows.forEach(r=>r.addEventListener('click',()=>{{
    clear();
    rows.forEach(x=>x.classList.remove('pick'));
    if(r.tagName!=='TR')r.classList.add('pick');
    r.classList.add('pick');
    const box=cvs.querySelector('.rgn[data-fb="'+r.dataset.fb+'"]');
    if(box){{
      box.classList.add('hi');
      box.scrollIntoView({{block:'center',behavior:'smooth'}});
      hint.textContent='문서에서 표시했습니다';
      hint.className='tag ac';
    }}else{{
      // 마스터 매칭으로 채웠거나 아예 못 찾은 값은 문서에 자리가 없다
      hint.textContent='이 값은 문서에 위치가 없습니다';
      hint.className='tag wa';
    }}
  }}));
}})();
document.querySelectorAll('[data-r]').forEach(el=>{{
  const box=document.querySelector('#rgn'+el.dataset.r);
  if(!box)return;
  el.addEventListener('mouseenter',()=>box.classList.add('hi'));
  el.addEventListener('mouseleave',()=>box.classList.remove('hi'));
}});
document.querySelectorAll('[data-tm]').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelectorAll('[data-tm]').forEach(x=>x.classList.toggle('on',x===b));
  document.querySelectorAll('.tmpane').forEach(p=>
    p.classList.toggle('on',p.id==='tm-'+b.dataset.tm));
}}));
document.querySelectorAll('[data-up]').forEach(b=>
  b.addEventListener('click',()=>upState(b.dataset.up)));
function cupState(n){{
  document.querySelectorAll('#cup-empty,#cup-filled').forEach(x=>
    x.classList.toggle('on',x.id==='cup-'+n));
  const on=n==='filled';
  document.querySelector('#cmpCount').style.display=on?'':'none';
  document.querySelector('#cmpAdd').style.display=on?'':'none';
  document.querySelector('#cmpRunBtn').disabled=!on;
}}
document.querySelectorAll('[data-cup]').forEach(b=>
  b.addEventListener('click',()=>cupState(b.dataset.cup)));
document.querySelectorAll('[data-view-go]').forEach(b=>
  b.addEventListener('click',()=>openView(b.dataset.viewGo)));

document.querySelectorAll('#orTabs .ortab').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelectorAll('#orTabs .ortab').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  document.querySelectorAll('.orpane').forEach(p=>p.classList.toggle('on',p.id==='pane-'+b.dataset.tab));
}}));
document.querySelectorAll('[data-gotab]').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelector('#orTabs .ortab[data-tab="'+b.dataset.gotab+'"]').click();
  const k=b.dataset.jump; if(!k)return;
  const card=document.querySelector('#fcList .fcard[data-fb="'+k+'"]');
  if(card){{card.click();setTimeout(()=>card.scrollIntoView({{block:'center',behavior:'smooth'}}),80);}}
}}));

document.querySelectorAll('[data-ftool]').forEach(tool=>{{
  const tbs=tool.dataset.ftool.split(',').map(x=>document.querySelector(x.trim()))
    .filter(Boolean);
  if(!tbs.length)return;
  // 표 행과 필드 카드를 함께 본다. 카드 안에 표가 들어 있는 경우
  // (Custom 탭) 그 표 행은 표대로, 카드는 카드대로 한 번씩만 센다.
  const rows=tbs.flatMap(t=>[
    ...t.querySelectorAll(':scope > .fcard[data-need]'),
    ...t.querySelectorAll('tbody tr')]);
  const q=tool.querySelector('[data-q]'), cnt=tool.querySelector('[data-cnt]');
  const apply=()=>{{
    const t=(q.value||'').trim().toLowerCase();
    const seg=tool.querySelector('[data-seg] button.on');
    const f=seg?seg.dataset.f:'all';
    let n=0;
    rows.forEach(r=>{{
      const okF=f==='all'
        ? true
        : f==='need' ? r.dataset.need==='1'
        : f==='chg'  ? r.dataset.chg==='1'
        : f==='same' ? r.dataset.chg==='0' : true;
      const okQ=!t||(r.dataset.k||'').toLowerCase().includes(t);
      const show=okF&&okQ; r.style.display=show?'':'none'; if(show)n++;
    }});
    cnt.textContent=(n!==rows.length)?(n+' / '+rows.length+' 항목'):'';
    // 품목 카드는 안에 보이는 행이 없으면 통째로 숨긴다
    const ic=document.querySelector('#itemCard');
    if(ic&&tbs.includes(ic.parentElement)){{
      const live=[...ic.querySelectorAll('tbody tr')].some(r=>r.style.display!=='none');
      ic.style.display=live?'':'none';
    }}
  }};
  q.addEventListener('input',apply);
  tool.querySelectorAll('[data-seg] button').forEach(b=>b.addEventListener('click',()=>{{
    tool.querySelectorAll('[data-seg] button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on'); apply();}}));
  apply();
}});
const lTb=document.querySelector('#learnTb');
if(lTb){{
  const lrs=[...lTb.querySelectorAll('tbody tr:not(.tot):not(.lempty)')];
  const lq=document.querySelector('#lq');
  const tb=lTb.querySelector('tbody');
  const totRow=tb.querySelector('tr.tot'), emptyRow=tb.querySelector('tr.lempty');
  let page=1; const PER=50;   // 한 페이지 행 수 고정
  const applyL=()=>{{
    const q=(lq.value||'').trim().toLowerCase();
    const r=document.querySelector('#lseg button.on').dataset.res;
    const c=document.querySelector('#lcol').value;
    const cc=document.querySelector('#lchar').value;
    const size=PER;
    const hit=lrs.filter(x=>
      (r==='all'||x.dataset.res===r)&&(c==='all'||x.dataset.col===c)&&
      (cc==='all'||x.dataset.cc===cc)&&
      (!q||(x.dataset.name||'').toLowerCase().includes(q)));
    const per=size||hit.length||1;
    const pages=Math.max(1,Math.ceil(hit.length/per));
    if(page>pages)page=pages;
    const from=(page-1)*per, to=Math.min(hit.length,from+per);
    lrs.forEach(x=>x.style.display='none');
    hit.slice(from,to).forEach(x=>x.style.display='');
    totRow.style.display=(r==='all'&&c==='all'&&cc==='all'&&!q&&pages===1)?'':'none';
    emptyRow.style.display=hit.length?'none':'';
    const filtered=hit.length!==lrs.length;
    document.querySelector('#lcnt').textContent=filtered
      ? hit.length+' / '+lrs.length+' 항목' : '';
    document.querySelector('.lpage').style.display=pages>1?'':'none';
    document.querySelector('#lrange').textContent=(from+1)+'-'+to+' / '+hit.length;
    document.querySelector('#lpg').textContent=page+' / '+pages;
    document.querySelector('#lprev').disabled=page<=1;
    document.querySelector('#lnext').disabled=page>=pages;
    document.querySelector('#lpager').style.display=pages>1?'':'none';
  }};
  document.querySelector('#lprev').addEventListener('click',()=>{{if(page>1){{page--;applyL();}}}});
  document.querySelector('#lnext').addEventListener('click',()=>{{page++;applyL();}});

  lq.addEventListener('input',()=>{{page=1;applyL();}});
  document.querySelectorAll('#lseg button').forEach(b=>b.addEventListener('click',()=>{{
    document.querySelectorAll('#lseg button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on'); page=1; applyL();}}));
  ['#lcol','#lchar'].forEach(id=>document.querySelector(id)
    .addEventListener('change',()=>{{page=1;applyL();}}));
  applyL();
}}
const hTb=document.querySelector('#humanTb');
if(hTb){{
  const hrs=[...hTb.querySelectorAll('tbody tr:not(.tot):not(.hempty)')];
  const hq=document.querySelector('#hq');
  const hTot=hTb.querySelector('tbody tr.tot'), hEmpty=hTb.querySelector('tbody tr.hempty');
  let hpage=1; const HPER=50;
  const applyH=()=>{{
    const t=(hq.value||'').trim().toLowerCase();
    const f=document.querySelector('#hseg button.on').dataset.f;
    const hit=hrs.filter(x=>(f==='all'||(f==='hit'?x.dataset.hit==='1':x.dataset.f===f))&&
      (!t||(x.dataset.k||'').toLowerCase().includes(t)));
    const pages=Math.max(1,Math.ceil(hit.length/HPER));
    if(hpage>pages)hpage=pages;
    const from=(hpage-1)*HPER, to=Math.min(hit.length,from+HPER);
    hrs.forEach(x=>x.style.display='none');
    hit.slice(from,to).forEach(x=>x.style.display='');
    hTot.style.display=((f==='all'||f==='hit')&&!t&&pages===1)?'':'none';
    hEmpty.style.display=hit.length?'none':'';
    document.querySelector('#hcnt').textContent=
      (hit.length!==hrs.length)?(hit.length+' / '+hrs.length+' 유형'):'';
    document.querySelector('#hpage').style.display=pages>1?'':'none';
    document.querySelector('#hrange').textContent=(from+1)+'-'+to+' / '+hit.length;
    document.querySelector('#hpg').textContent=hpage+' / '+pages;
    document.querySelector('#hprev').disabled=hpage<=1;
    document.querySelector('#hnext').disabled=hpage>=pages;
  }};
  hq.addEventListener('input',()=>{{hpage=1;applyH();}});
  document.querySelectorAll('#hseg button').forEach(b=>b.addEventListener('click',()=>{{
    document.querySelectorAll('#hseg button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on'); hpage=1; applyH();}}));
  document.querySelector('#hprev').addEventListener('click',()=>{{if(hpage>1){{hpage--;applyH();}}}});
  document.querySelector('#hnext').addEventListener('click',()=>{{hpage++;applyH();}});
  applyH();
}}
const rTb=document.querySelector('#ruleTb');
if(rTb){{
  const rrs=[...rTb.querySelectorAll('tbody tr:not(.tot):not(.rempty)')];
  const rq=document.querySelector('#rq');
  const rTot=rTb.querySelector('tbody tr.tot'), rEmpty=rTb.querySelector('tbody tr.rempty');
  let rpage=1; const RPER=50;
  const applyR=()=>{{
    const t=(rq.value||'').trim().toLowerCase();
    const f=document.querySelector('#rseg button.on').dataset.f;
    const hit=rrs.filter(x=>(f==='all'||x.dataset.f===f)&&
      (!t||(x.dataset.k||'').toLowerCase().includes(t)));
    const pages=Math.max(1,Math.ceil(hit.length/RPER));
    if(rpage>pages)rpage=pages;
    const from=(rpage-1)*RPER, to=Math.min(hit.length,from+RPER);
    rrs.forEach(x=>x.style.display='none');
    hit.slice(from,to).forEach(x=>x.style.display='');
    rTot.style.display=(f==='all'&&!t&&pages===1)?'':'none';
    rEmpty.style.display=hit.length?'none':'';
    document.querySelector('#rcnt').textContent=
      (hit.length!==rrs.length)?(hit.length+' / '+rrs.length+' 유형'):'';
    document.querySelector('#rpage').style.display=pages>1?'':'none';
    document.querySelector('#rrange').textContent=(from+1)+'-'+to+' / '+hit.length;
    document.querySelector('#rpg').textContent=rpage+' / '+pages;
    document.querySelector('#rprev').disabled=rpage<=1;
    document.querySelector('#rnext').disabled=rpage>=pages;
  }};
  rq.addEventListener('input',()=>{{rpage=1;applyR();}});
  document.querySelectorAll('#rseg button').forEach(b=>b.addEventListener('click',()=>{{
    document.querySelectorAll('#rseg button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on'); rpage=1; applyR();}}));
  document.querySelector('#rprev').addEventListener('click',()=>{{if(rpage>1){{rpage--;applyR();}}}});
  document.querySelector('#rnext').addEventListener('click',()=>{{rpage++;applyR();}});
  applyR();
}}
document.querySelectorAll('#rTabs .rtab').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelectorAll('#rTabs .rtab').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  document.querySelectorAll('.rpane').forEach(p=>p.classList.toggle('on',p.id==='rp-'+b.dataset.route));
}}));
document.querySelectorAll('#issueSeg button').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelectorAll('#issueSeg button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  const all=b.dataset.f==='all';
  document.querySelectorAll('#v-detail tbody tr[data-need]').forEach(r=>{{
    r.style.display=(all||r.dataset.need==='1')?'':'none';}});
}}));
document.querySelectorAll('#aggSeg button').forEach(b=>b.addEventListener('click',()=>{{
  document.querySelectorAll('#aggSeg button').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  document.querySelectorAll('.aggt').forEach(t=>t.classList.toggle('on',t.dataset.agg===b.dataset.agg));
}}));
const mdF=document.querySelector('#mdFilter');
if(mdF){{
  const hrows=[...document.querySelectorAll('#v-missed tbody tr[data-model]')];
  const needF=document.querySelector('#needFilter');
  const empty=document.querySelector('.hempty2');
  let hp=1; const HP=20;
  const applyH=()=>{{
    const m=mdF.value, nd=needF.value;
    const hit=hrows.filter(r=>
      (m==='전체'||r.dataset.model===m)&&
      (nd==='전체'||(nd==='있음')===(r.dataset.need==='1')));
    const pages=Math.max(1,Math.ceil(hit.length/HP));
    if(hp>pages)hp=pages;
    const from=(hp-1)*HP, to=Math.min(hit.length,from+HP);
    hrows.forEach(r=>r.style.display='none');
    hit.slice(from,to).forEach(r=>r.style.display='');
    empty.style.display=hit.length?'none':'';
    document.querySelector('#hstpage').style.display=pages>1?'':'none';
    document.querySelector('#hstrange').textContent=(from+1)+'-'+to+' / '+hit.length;
    document.querySelector('#hstpg').textContent=hp+' / '+pages;
    document.querySelector('#hstprev').disabled=hp<=1;
    document.querySelector('#hstnext').disabled=hp>=pages;
  }};
  [mdF,needF].forEach(el=>el.addEventListener('change',()=>{{hp=1;applyH();}}));
  document.querySelector('#hstprev').addEventListener('click',()=>{{if(hp>1){{hp--;applyH();}}}});
  document.querySelector('#hstnext').addEventListener('click',()=>{{hp++;applyH();}});
  applyH();
}}

document.querySelector('#themeBtn').addEventListener('click',()=>{{
  const r=document.documentElement;r.dataset.theme=r.dataset.theme==='dark'?'light':'dark';}});
const tw=document.querySelector('#toast');let tm;
document.querySelectorAll('[data-toast]').forEach(b=>b.addEventListener('click',()=>{{
  tw.textContent=b.dataset.toast;tw.classList.add('show');
  clearTimeout(tm);tm=setTimeout(()=>tw.classList.remove('show'),1500);}}));

const q=new URLSearchParams(location.search);
if(q.get('up')==='filled')upState('filled');
if(q.get('cup')==='filled')cupState('filled');
const w=location.hash.slice(1)||q.get('view');
if(T[w])openView(w);
const tb=q.get('tab');
if(tb)document.querySelector('#orTabs .ortab[data-tab="'+tb+'"]')?.click();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
