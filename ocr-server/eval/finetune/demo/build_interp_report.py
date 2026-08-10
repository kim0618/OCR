"""보간(WiSE-FT) 모델을 demo_summary 가 읽는 DEMO_REPORT 로 등록한다.

보간 모델은 학습 run 이 아니라 demo/NNN_<태그>/ 폴더가 없어 실행 이력에 안 잡힌다.
학습 run 리포트(demo-report.v1)와 같은 스키마로 합성하되, <학습이 없었다>는 사실이
그대로 보이게 한다:
  - counts 를 비워 학습 크롭 칸이 '미측정'이 아니라 학습 자체가 없음을 모델명에 명시
  - 판정 rows 는 원본(v16) 리포트의 크롭 이미지를 재사용하고 예측만 TARGET_EVAL 로 교체
  - interpolation 블록에 α·재료 모델·sha256(manifest)을 그대로 박아 재현 근거를 남긴다

    python eval/finetune/demo/build_interp_report.py --alpha 80
    python eval/finetune/demo/build_interp_report.py --alpha 90   # wf90 도 등록 가능
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recount_reviewed_gt import HERE  # noqa: E402

FT_RUN = "260807_1302"          # 보간의 FT 쪽 재료 = v16
TEMPLATE = HERE / f"016_{FT_RUN}" / f"DEMO_REPORT_{FT_RUN}.json"
VERSIONS = HERE.parent / "versions" / f"run_{FT_RUN}" / "interp"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", required=True, help="보간 α×100 (예: 80)")
    ap.add_argument("--seq", type=int, default=0,
                    help="demo/NNN 폴더 번호. 0=기존 최대+1")
    args = ap.parse_args()
    a = int(args.alpha)
    tag = f"260810_wf{a:02d}"

    adir = VERSIONS / f"a{a:02d}"
    target_eval = json.loads((adir / "TARGET_EVAL.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (adir / f"interp_a{a:02d}.pdparams.manifest.json").read_text(encoding="utf-8"))
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    preds = target_eval["predictions"]
    rows = template["targets"][0]["rows"]
    if len(preds) != len(rows):
        raise SystemExit(f"판정 크롭 수 불일치: template {len(rows)} vs eval {len(preds)}")
    new_rows = [dict(row, finetuned=p["pred"], ok=bool(p["ok"]))
                for row, p in zip(rows, preds)]
    ok_n = sum(1 for p in preds if p["ok"])

    tgt = dict(template["targets"][0])
    tgt["rows"] = new_rows
    tgt["verdict"] = {"n": len(preds), "ft": ok_n,
                      "base": template["targets"][0]["verdict"]["base"],
                      "pass": bool(target_eval["summary"]["allPass"])}

    report = {
        "schemaVersion": "demo-report.v1",
        "runTag": tag,
        "generatedAt": manifest["generatedAt"],
        "cycle": template["cycle"], "roundNo": template["roundNo"],
        "step": template["step"], "stepIndex": template["stepIndex"],
        "modelName": f"1차 1단계 모델 · 가중치 보간 wf{a:02d} "
                     f"(= {a / 100:.1f}×v16 + {1 - a / 100:.1f}×base, 학습 없음)",
        "baseModel": template["baseModel"],
        "compareLabel": "base",
        "compareStep": None, "compareDir": None,
        "basisDocs": template["basisDocs"], "column": template["column"],
        # 학습이 없었으므로 학습 크롭 수치를 만들지 않는다(표에는 '미측정'으로 나옴).
        "counts": {"test": len(preds)},
        "pool": template["pool"],
        "targets": [tgt],
        "summary": {"pass": int(tgt["verdict"]["pass"]), "total": 1,
                    "allPass": bool(tgt["verdict"]["pass"])},
        "interpolation": {
            "method": "wise-ft", "alphaFt": a / 100.0,
            "ftRun": FT_RUN, "baseSha256": manifest["base"]["sha256"],
            "ftSha256": manifest["ft"]["sha256"],
            "outSha256": manifest["out"]["sha256"],
            "tool": "eval/finetune/demo/interpolate_weights.py",
        },
    }

    seq = args.seq
    if not seq:
        seq = 1 + max((int(p.name.split("_", 1)[0])
                       for p in HERE.glob("[0-9]*_*") if p.is_dir()), default=0)
    out_dir = HERE / f"{seq:03d}_{tag}"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"DEMO_REPORT_{tag}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    # ★demo_summary 의 ① 잃어버림 블록은 NEXT_TARGETS.json 이 있어야 렌더된다
    #  (v14 에폭사다리 폴더도 이 파일이 없어 블록이 빠졌던 전례). 후보 표는
    #  GT_REVIEW_RECOUNT 의 candidates[tag] 가 대체하므로 빈 목록이면 충분하다.
    nt = out_dir / "NEXT_TARGETS.json"
    nt.write_text(json.dumps({
        "schemaVersion": "demo-next-targets.v1", "runTag": tag,
        "basisCrops": 45617, "prevScan": "000_base.jsonl",
        "lost": [], "unread": [],
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"wrote {nt}")
    print(f"  판정 {ok_n}/{len(preds)} · α={a / 100:.2f} · v{seq} 로 등록됨")
    print("  demo_summary 갱신: .venv\\Scripts\\python.exe eval\\demo_summary.py")


if __name__ == "__main__":
    main()
