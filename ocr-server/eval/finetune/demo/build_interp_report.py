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
from recount_reviewed_gt import HERE, bad_paths  # noqa: E402

DEFAULT_FT_RUN = "260807_1302"          # 보간의 FT 쪽 재료(기본 = v16)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", required=True, help="보간 α×100 (예: 80)")
    ap.add_argument("--ft-run", default=DEFAULT_FT_RUN,
                    help="보간의 FT 쪽 재료 run 태그")
    ap.add_argument("--scan-tag", default="",
                    help="이 보간의 전수 스캔 태그. 비우면 <ft-run>_wf<α> 규칙")
    ap.add_argument("--seq", type=int, default=0,
                    help="demo/NNN 폴더 번호. 0=기존 최대+1")
    args = ap.parse_args()
    a = int(args.alpha)
    ft_run = args.ft_run
    # 1단계 스윕은 260810_wf80 같은 태그를 썼고, 이후 스윕은 <ft-run>_wf<α> 규칙이다.
    tag = args.scan_tag or f"{ft_run}_wf{a:02d}"

    template_dir = next((p for p in HERE.glob(f"*_{ft_run}") if p.is_dir()), None)
    if template_dir is None:
        raise SystemExit(f"원본 run 리포트 폴더가 없습니다: demo/*_{ft_run}")
    TEMPLATE = template_dir / f"DEMO_REPORT_{ft_run}.json"
    adir = HERE.parent / "versions" / f"run_{ft_run}" / "interp" / f"a{a:02d}"
    target_eval = json.loads((adir / "TARGET_EVAL.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (adir / f"interp_a{a:02d}.pdparams.manifest.json").read_text(encoding="utf-8"))
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    # ★타깃별로 예측을 갈라 넣는다(다타깃 지원). 원본 리포트의 rows 에는 path 가 없고
    #  크롭 이미지(imgB64)만 있으므로, <같은 test.txt 순서>라는 사실을 이용해 타깃별로
    #  순서대로 짝짓는다. 판독 불가 크롭(basis_bad_paths)은 여기서 빼서 게이트와
    #  리포트가 같은 모수를 보게 한다.
    bad = bad_paths()
    preds_by_target: dict[str, list] = {}
    for p in target_eval["predictions"]:
        preds_by_target.setdefault(p.get("target") or "?", []).append(p)
    targets_out = []
    for t in template["targets"]:
        src = preds_by_target.get(t["name"], [])
        tmpl_rows = t.get("rows") or []
        if len(src) != len(tmpl_rows):
            raise SystemExit(
                f"판정 크롭 수 불일치 [{t['name']}]: 원본 {len(tmpl_rows)} vs "
                f"보간 {len(src)} — 같은 dataset 에서 나온 판정인지 확인할 것")
        rows = []
        for row, p in zip(tmpl_rows, src):
            if p["path"] in bad:
                continue              # 판독 불가로 확정 - 게이트·리포트 모두에서 제외
            rows.append(dict(row, path=p["path"], finetuned=p["pred"],
                             ok=bool(p["ok"])))
        ok_n = sum(1 for r in rows if r["ok"])
        t2 = dict(t)
        t2["rows"] = rows
        t2["verdict"] = {"n": len(rows), "ft": ok_n,
                         "base": (t.get("verdict") or {}).get("base", 0),
                         "pass": bool(rows) and ok_n == len(rows)}
        targets_out.append(t2)
    all_pass = all(t["verdict"]["pass"] for t in targets_out)
    n_pass = sum(1 for t in targets_out if t["verdict"]["pass"])

    report = {
        "schemaVersion": "demo-report.v1",
        "runTag": tag,
        "generatedAt": manifest["generatedAt"],
        "cycle": template["cycle"], "roundNo": template["roundNo"],
        "step": template["step"], "stepIndex": template["stepIndex"],
        "modelName": f"가중치 보간 wf{a:02d} "
                     f"(= {a / 100:.1f}×{ft_run} + {1 - a / 100:.1f}×base, 학습 없음)",
        "baseModel": template["baseModel"],
        "compareLabel": "base",
        "compareStep": None, "compareDir": None,
        "basisDocs": template["basisDocs"], "column": template["column"],
        # 학습이 없었으므로 학습 크롭 수치를 만들지 않는다(표에는 보간 재료가 표시된다).
        "counts": {"test": sum(len(t["rows"]) for t in targets_out)},
        "pool": template["pool"],
        "targets": targets_out,
        "summary": {"pass": n_pass, "total": len(targets_out),
                    "allPass": all_pass},
        "interpolation": {
            "method": "wise-ft", "alphaFt": a / 100.0,
            "ftRun": ft_run, "baseSha256": manifest["base"]["sha256"],
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
    print(f"  α={a / 100:.2f} · FT 재료 {ft_run} · v{seq} 로 등록 "
          f"({n_pass}/{len(targets_out)} 타깃 통과)")
    for t in targets_out:
        v = t["verdict"]
        print(f"     {t['name'][:44]:<44} {v['ft']}/{v['n']} "
              f"{'PASS' if v['pass'] else 'FAIL'}")
    print("  demo_summary 갱신: .venv\\Scripts\\python.exe eval\\demo_summary.py")


if __name__ == "__main__":
    main()
