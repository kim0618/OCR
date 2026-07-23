"""Verify compact runtime LearnData against replay measurement columns."""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, SERVER)

from extractors.master_match import MasterMatcher  # noqa: E402
from extractors.master_match import (  # noqa: E402
    _runtime_char_sim, _runtime_spec,
)
import learndata_apply as LDA  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="067_20260720_175949")
    args = ap.parse_args()

    master = json.load(open(os.path.join(SERVER, "master_dict.json"), encoding="utf-8"))
    learned = json.load(
        open(os.path.join(SERVER, "learndata_runtime.json"), encoding="utf-8")
    )
    matcher = MasterMatcher(
        master.get("item") or {}, master.get("itembuycust"), learned
    )

    scored = matched = missing_master = 0
    mismatches = []
    pattern = os.path.join(HERE, "runs", args.run, "replay_compare", "*.json")
    for path in sorted(glob.glob(pattern)):
        comp = json.load(open(path, encoding="utf-8"))
        for row in (comp.get("table") or {}).get("rows", []):
            cells = row.get("cells") or {}
            expected = str(
                (cells.get("itemCodeLearnA") or {}).get("ext") or ""
            )
            reading = str((cells.get("itemName") or {}).get("ext") or "")
            if not expected or not reading:
                continue
            # Measurement columns fall back to the existing Master result when
            # LearnData does not fire. Parity covers only actual lookup hits.
            if reading not in matcher._learn:
                continue
            if expected not in matcher._cd2i:
                missing_master += 1
                continue
            actual = matcher.resolve_learndata_code(
                reading,
                spec=(cells.get("spec") or {}).get("ext"),
                price=(cells.get("unitPrice") or {}).get("ext"),
                quantity=(cells.get("quantity") or {}).get("ext"),
                amount=(cells.get("amount") or {}).get("ext"),
            )
            scored += 1
            matched += int(actual == expected)
            if actual != expected and len(mismatches) < 20:
                mismatches.append({
                    "file": os.path.basename(path),
                    "rowIndex": row.get("rowIndex"),
                    "reading": reading,
                    "expected": expected,
                    "actual": actual,
                    "spec": (cells.get("spec") or {}).get("ext"),
                    "unitPrice": (cells.get("unitPrice") or {}).get("ext"),
                    "quantity": (cells.get("quantity") or {}).get("ext"),
                    "amount": (cells.get("amount") or {}).get("ext"),
                    "counts": matcher._learn.get(reading),
                    "expectedUnit": (
                        matcher._units[matcher._cd2i[expected]]
                        if expected in matcher._cd2i else None
                    ),
                    "actualUnit": (
                        matcher._units[matcher._cd2i[actual]]
                        if actual in matcher._cd2i else None
                    ),
                    "normSpecEval": LDA._normspec(
                        (cells.get("spec") or {}).get("ext")
                    ),
                    "normSpecRuntime": _runtime_spec(
                        (cells.get("spec") or {}).get("ext")
                    ),
                    "candidateScores": {
                        code: {
                            "eval": LDA._sim(
                                reading, matcher._nms[matcher._cd2i[code]]
                            ),
                            "runtime": _runtime_char_sim(
                                reading, matcher._nms[matcher._cd2i[code]]
                            ),
                        }
                        for code in (matcher._learn.get(reading) or {})
                        if code in matcher._cd2i
                    },
                })

    result = {
        "scored": scored,
        "matched": matched,
        "pct": 100.0 * matched / scored if scored else None,
        "expectedCodeMissingMaster": missing_master,
        "mismatches": mismatches,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if matched == scored else 1


if __name__ == "__main__":
    raise SystemExit(main())
