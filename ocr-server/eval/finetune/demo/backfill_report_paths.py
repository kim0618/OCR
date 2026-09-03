"""과거 DEMO_REPORT 의 판정 행에 크롭 경로(path)를 채워 넣는다.

demo_report 가 한동안 rows 에 path 를 안 남겨서, 판독 불가 크롭(basis_bad_paths)을
행 단위로 제외할 수 없었다. 같은 run 의 보간 TARGET_EVAL 은 같은 test.txt 순서로
path 를 갖고 있으므로, 타깃별 순서로 짝지어 채운다.

    python eval/finetune/demo/backfill_report_paths.py --run 260811_1105

안전장치: 타깃별 행 수가 다르면 건드리지 않고 중단한다(순서 가정이 깨졌다는 뜻).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recount_reviewed_gt import HERE, comparable  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run 태그 (예: 260811_1105)")
    ap.add_argument("--from-alpha", default="80",
                    help="경로를 가져올 보간 TARGET_EVAL 의 α×100")
    args = ap.parse_args()

    rep_dir = next((p for p in HERE.glob(f"*_{args.run}") if p.is_dir()), None)
    if rep_dir is None:
        raise SystemExit(f"리포트 폴더가 없습니다: demo/*_{args.run}")
    rep_path = rep_dir / f"DEMO_REPORT_{args.run}.json"
    src = (HERE.parent / "versions" / f"run_{args.run}" / "interp"
           / f"a{int(args.from_alpha):02d}" / "TARGET_EVAL.json")
    if not src.exists():
        raise SystemExit(f"경로 원본이 없습니다: {src}")

    report = json.loads(rep_path.read_text(encoding="utf-8"))
    evald = json.loads(src.read_text(encoding="utf-8"))
    by_target: dict[str, list] = {}
    for p in evald["predictions"]:
        by_target.setdefault(p.get("target") or "?", []).append(p)

    filled = 0
    for t in report.get("targets") or []:
        rows = t.get("rows") or []
        preds = by_target.get(t["name"], [])
        if len(rows) != len(preds):
            raise SystemExit(f"행 수 불일치 [{t['name']}]: 리포트 {len(rows)} vs "
                             f"판정 {len(preds)} — 같은 dataset 이 아닙니다")
        for row, p in zip(rows, preds):
            # GT 가 다르면 순서 가정이 깨진 것이다 - 조용히 잘못 채우지 않는다.
            if comparable(row.get("gt")) != comparable(p.get("gt")):
                raise SystemExit(f"GT 불일치 [{t['name']}]: {row.get('gt')!r} vs "
                                 f"{p.get('gt')!r}")
            row["path"] = p["path"]
            filled += 1

    rep_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                        encoding="utf-8")
    print(f"wrote {rep_path}")
    print(f"  {filled} 행에 path 채움 (원본: {src.name})")


if __name__ == "__main__":
    main()
