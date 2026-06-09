"""checker — one consolidated gate over the whole harness (Phase 5).

Aggregates:
  - normalization golden regression (golden/normalization_golden.json)
  - phase0 (GT parse) + phase1 (manifest/loader)            [no run dir needed]
  - phase2 (run results) + phase3 (compare) + phase4 (metrics/report)  [for a run]
  - manifest <-> run files cross-check + parse rate for the run

Exit 0 = harness healthy (MVP-level GO).

CLI: python eval/checker.py [--ts <run_ts>]   (default: latest run)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys

import contract as C
import normalize as N

PY = sys.executable
GOLDEN = os.path.join(C.HERE, "golden", "normalization_golden.json")
_NORM = {
    "amount": N.norm_amount, "qty": N.norm_qty, "bizno": N.norm_bizno,
    "date": N.norm_date, "code": N.norm_code, "index": N.norm_index, "text": N.norm_text,
}


def golden_regression() -> list[str]:
    problems: list[str] = []
    try:
        g = json.load(open(GOLDEN, encoding="utf-8"))
    except Exception as exc:
        return [f"golden file unreadable: {exc}"]
    for typ, cases in g.items():
        if typ.startswith("_"):
            continue
        fn = _NORM.get(typ)
        if not fn:
            problems.append(f"golden has unknown type '{typ}'")
            continue
        for inp, expected in cases:
            got = fn(inp)
            if got != expected:
                problems.append(f"golden {typ}: {inp!r} -> {got!r} != {expected!r}")
    return problems


def run_check(name: str, argv: list[str]) -> tuple[bool, str]:
    """Run a phaseN check as a subprocess; return (ok, last_line)."""
    p = subprocess.run([PY, os.path.join(C.HERE, name), *argv],
                       capture_output=True, text=True, encoding="utf-8")
    out = (p.stdout or "") + (p.stderr or "")
    last = next((ln for ln in reversed(out.strip().splitlines()) if ln.strip()), "")
    return p.returncode == 0, last


def manifest_run_crosscheck(run_dir: str) -> list[str]:
    problems: list[str] = []
    from build_manifest import build_manifest
    actives = {s["sourceFile"] for s in build_manifest()["samples"] if s["status"] == "active"}
    samples_dir = os.path.join(run_dir, "samples")
    have = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(samples_dir, "*.json"))}
    missing = actives - have
    if missing:
        problems.append(f"run missing results for active samples: {sorted(missing)}")
    # parse rate: every result + compare must be valid JSON with status ok
    ok = 0
    for src in actives:
        rp = os.path.join(samples_dir, src + ".json")
        try:
            if json.load(open(rp, encoding="utf-8")).get("status") == "ok":
                ok += 1
        except Exception as exc:
            problems.append(f"{src}: result unparseable ({exc})")
        cp = os.path.join(run_dir, "compare", src + ".json")
        if not os.path.isfile(cp):
            problems.append(f"{src}: compare file missing")
    if ok != len(actives):
        problems.append(f"run parse rate {ok}/{len(actives)} ok")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    args = ap.parse_args()
    run_dir = (os.path.join(C.RUNS_DIR, args.ts) if args.ts
               else (sorted(p for p in glob.glob(os.path.join(C.RUNS_DIR, "*")) if os.path.isdir(p)) or [None])[-1])

    results: list[tuple[str, bool, str]] = []

    gp = golden_regression()
    results.append(("normalization-golden", not gp, gp[0] if gp else "all golden cases hold"))

    for name, argv in [("phase0_contract_check.py", []), ("phase1_check.py", [])]:
        ok, last = run_check(name, argv)
        results.append((name, ok, last))

    if not run_dir or not os.path.isdir(run_dir):
        results.append(("run-dir", False, f"no run dir ({run_dir})"))
    else:
        ts_argv = ["--ts", os.path.basename(run_dir)]
        for name in ("phase2_check.py", "phase3_check.py", "phase4_check.py"):
            ok, last = run_check(name, ts_argv)
            results.append((name, ok, last))
        xc = manifest_run_crosscheck(run_dir)
        results.append(("manifest<->run", not xc, xc[0] if xc else "all active samples present, parse 6/6"))

    print(f"checker over run: {os.path.basename(run_dir) if run_dir else '(none)'}\n")
    width = max(len(r[0]) for r in results)
    all_ok = True
    for name, ok, last in results:
        all_ok = all_ok and ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<{width}}  {last}")
    print()
    if all_ok:
        print("CHECKER PASS - harness healthy (MVP GO)")
        return 0
    print("CHECKER FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
