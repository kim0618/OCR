"""Compare two epoch/run scans with the same reviewed-GT policy as the official recount.

The important numbers for an epoch trajectory are paired transitions: crops that A still
read but B newly lost, and crops that A missed but B recovered.  Because both checkpoints
belong to one training trajectory, these counts show the effect of continuing that exact
trajectory without mixing in another run's training randomness.

    python eval/finetune/demo/demo_scan_transition.py TAG_EP08 TAG_EP12
    python eval/finetune/demo/demo_scan_transition.py TAG_EP12 TAG_EP20 --json out.json
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import recount_reviewed_gt as rr

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag_a")
    parser.add_argument("tag_b")
    parser.add_argument("--json", dest="json_path")
    args = parser.parse_args()

    keep = {
        line.strip()
        for line in (HERE / "basis_keep.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    overrides, excluded_names, _ = rr.load_policy()
    base = rr.load_scan("000_base.jsonl", keep)
    scan_a = rr.load_scan(f"{args.tag_a}.jsonl", keep)
    scan_b = rr.load_scan(f"{args.tag_b}.jsonl", keep)
    if not base or not scan_a or not scan_b:
        raise SystemExit("base/A/B 스캔 중 하나가 비어 있습니다")
    if set(base) != set(scan_a) or set(base) != set(scan_b):
        raise SystemExit(
            f"스캔 집합 불일치: base={len(base)} A={len(scan_a)} B={len(scan_b)}")

    policy: dict[str, tuple[str, bool]] = {}
    for path, row in base.items():
        old_gt = row["gt"]
        key = rr.name_key(old_gt)
        policy[path] = (overrides.get(key, old_gt), key in excluded_names)
    valid = [path for path, (_, excluded) in policy.items() if not excluded]

    def correct(scan: dict[str, dict], path: str) -> bool:
        return rr.comparable(policy[path][0]) == rr.comparable(scan[path]["pred"])

    base_ok = {path: correct(base, path) for path in valid}
    a_ok = {path: correct(scan_a, path) for path in valid}
    b_ok = {path: correct(scan_b, path) for path in valid}
    new_loss = sorted(path for path in valid if a_ok[path] and not b_ok[path])
    new_gain = sorted(path for path in valid if not a_ok[path] and b_ok[path])

    def totals(ok: dict[str, bool]) -> dict[str, int]:
        lost = sum(base_ok[path] and not ok[path] for path in valid)
        revived = sum(not base_ok[path] and ok[path] for path in valid)
        return {"lost": lost, "revived": revived, "net": revived - lost}

    causes = Counter(
        rr.lost_cause(policy[path][0], scan_b[path]["pred"])
        for path in new_loss
    )
    result = {
        "a": args.tag_a,
        "b": args.tag_b,
        "evaluatedCrops": len(valid),
        "aTotals": totals(a_ok),
        "bTotals": totals(b_ok),
        "newLoss": len(new_loss),
        "newGain": len(new_gain),
        "netTransition": len(new_gain) - len(new_loss),
        "newLossCauses": dict(causes),
        "newLossPaths": new_loss,
        "newGainPaths": new_gain,
    }
    print(f"{args.tag_a} → {args.tag_b}  (GT 보정 {len(valid):,}장)")
    print(f"  A 잃음 {result['aTotals']['lost']:,} / 소생 {result['aTotals']['revived']:,} / "
          f"순증 {result['aTotals']['net']:+,}")
    print(f"  B 잃음 {result['bTotals']['lost']:,} / 소생 {result['bTotals']['revived']:,} / "
          f"순증 {result['bTotals']['net']:+,}")
    print(f"  계속 학습하며 신규손실 {len(new_loss):,} / 신규회복 {len(new_gain):,} / "
          f"순 {len(new_gain) - len(new_loss):+,}")
    if causes:
        print("  신규손실 원인: " + ", ".join(f"{key} {value:,}" for key, value in causes.items()))

    if args.json_path:
        output = Path(args.json_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_name(output.name + ".tmp")
        temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(output)
        print(f"  JSON: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
