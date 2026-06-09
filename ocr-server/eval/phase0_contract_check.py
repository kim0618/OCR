"""Phase 0 gate — GT_CONTRACT conformance check.

Validates that every GT file in the invoice_study fixture parses 100% and
conforms to GT_CONTRACT.md. Measurement-only: reads GT, writes nothing.

Gate (GO): all 6 GT files PASS (2.pdf is excluded by design, not present in GT/).

Run:
    python eval/phase0_contract_check.py
Exit code 0 = gate PASS, 1 = FAIL.
"""

from __future__ import annotations

import glob
import json
import os
import sys

import contract as C

# Use the single source of truth (contract.py) so this gate can never drift.
GT_DIR = C.GT_DIR
SCHEMA_VERSION = C.SCHEMA_VERSION
COMMON_12 = set(C.COMMON_12)
PER_SAMPLE = set(C.PER_SAMPLE)
ROW_VALUE_KEYS = set(C.ROW_VALUE_KEYS)
EXPECTED_ROWS = C.EXPECTED_ROWS


def check_file(path: str) -> tuple[bool, list[str]]:
    """Return (ok, problems) for one GT file."""
    problems: list[str] = []
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"unreadable / invalid JSON: {exc}"]

    if d.get("schemaVersion") != SCHEMA_VERSION:
        problems.append(f"schemaVersion={d.get('schemaVersion')!r} != {SCHEMA_VERSION!r}")

    source_file = d.get("sourceFile")
    if not source_file:
        problems.append("missing top-level sourceFile")

    nr = d.get("normalizedResult")
    if not isinstance(nr, dict):
        return False, problems + ["normalizedResult missing or not an object"]

    # --- scalar fields ---
    fields = nr.get("fields")
    if not isinstance(fields, list):
        problems.append("normalizedResult.fields missing or not a list")
        fields = []

    labels: list[str] = []
    for i, f in enumerate(fields):
        if not isinstance(f, dict):
            problems.append(f"fields[{i}] not an object")
            continue
        if "labelEn" not in f:
            problems.append(f"fields[{i}] missing labelEn")
            continue
        if "value" not in f:
            problems.append(f"fields[{i}] ({f.get('labelEn')}) missing value key")
        labels.append(f["labelEn"])

    label_set = set(labels)
    if len(labels) != len(label_set):
        dupes = sorted({l for l in labels if labels.count(l) > 1})
        problems.append(f"duplicate labelEn (flatten collision): {dupes}")

    missing_common = COMMON_12 - label_set
    if missing_common:
        problems.append(f"missing common-12 fields: {sorted(missing_common)}")

    present_per_sample = label_set & PER_SAMPLE
    if len(present_per_sample) != 1:
        problems.append(
            f"per-sample field must be exactly ONE of {sorted(PER_SAMPLE)}, "
            f"found {sorted(present_per_sample)}"
        )

    unknown = label_set - COMMON_12 - PER_SAMPLE
    if unknown:
        problems.append(f"unexpected labelEn not in contract: {sorted(unknown)}")

    # --- table rows ---
    rows = nr.get("tableRows")
    if not isinstance(rows, list):
        problems.append("normalizedResult.tableRows missing or not a list")
        rows = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            problems.append(f"tableRows[{i}] not an object")
            continue
        if "rowIndex" not in r:
            problems.append(f"tableRows[{i}] missing rowIndex (alignment key)")
        present_value_keys = set(r.keys()) & ROW_VALUE_KEYS
        if not present_value_keys:
            problems.append(f"tableRows[{i}] has no contract value keys")

    if source_file in EXPECTED_ROWS and len(rows) != EXPECTED_ROWS[source_file]:
        problems.append(
            f"row count {len(rows)} != expected {EXPECTED_ROWS[source_file]} "
            f"for {source_file}"
        )

    # --- excluded rows ---
    excl = d.get("excludedRows", [])
    if not isinstance(excl, list):
        problems.append("excludedRows present but not a list")

    return len(problems) == 0, problems


def main() -> int:
    if not os.path.isdir(GT_DIR):
        print(f"FAIL: GT dir not found: {GT_DIR}")
        return 1

    paths = sorted(glob.glob(os.path.join(GT_DIR, "*.json")))
    if not paths:
        print(f"FAIL: no GT files under {GT_DIR}")
        return 1

    print(f"GT dir: {GT_DIR}")
    print(f"Found {len(paths)} GT file(s)\n")

    all_ok = True
    seen_sources: list[str] = []
    for path in paths:
        name = os.path.basename(path)
        ok, problems = check_file(path)
        # capture sourceFile for the excluded-2.pdf assertion
        try:
            src = json.load(open(path, encoding="utf-8")).get("sourceFile")
            if src:
                seen_sources.append(src)
        except Exception:
            pass
        if ok:
            print(f"  PASS  {name}")
        else:
            all_ok = False
            print(f"  FAIL  {name}")
            for p in problems:
                print(f"          - {p}")

    # 2.pdf must be absent by design.
    if "2.pdf" in seen_sources:
        all_ok = False
        print("\n  FAIL  2.pdf is present but should be excluded (temporary).")

    expected_sources = set(EXPECTED_ROWS)  # 6 expected
    missing_sources = expected_sources - set(seen_sources)
    if missing_sources:
        all_ok = False
        print(f"\n  FAIL  missing expected sources: {sorted(missing_sources)}")

    print()
    if all_ok and len(paths) == 6:
        print("GATE PASS - 6/6 GT files conform to GT_CONTRACT.md")
        return 0
    print("GATE FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
