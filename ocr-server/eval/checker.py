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


def manifest_run_crosscheck(run_dir: str, testset: str = C.DEFAULT_TESTSET) -> list[str]:
    problems: list[str] = []
    from build_manifest import build_manifest
    actives = {s["sourceFile"] for s in build_manifest(testset)["samples"]
               if s["status"] in ("active", "canned")}
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


def thin_self_consistency(run_dir: str, testset: str) -> list[str]:
    """Generic gate for a non-rich testset: metrics cross-foot + report, with no
    rich-specific constants. Used by the one-command thin path (run_all)."""
    from metrics import compute_metrics
    from report import render_report
    p: list[str] = []
    m = compute_metrics(run_dir)
    rp = render_report(run_dir)
    of = m["overall"]["field"]
    pf_scored = sum(v["scored"] for v in m["perField"].values())
    pf_match = sum(v["match"] for v in m["perField"].values())
    if (pf_scored, pf_match) != (of["scored"], of["match"]):
        p.append(f"perField sum {pf_scored}/{pf_match} != overall {of['scored']}/{of['match']}")
    bp_scored = sum(v["field"]["scored"] for v in m["byPath"].values())
    if bp_scored != of["scored"]:
        p.append(f"byPath scored {bp_scored} != overall {of['scored']}")
    ds_scored = sum(v["scored"] for v in m["difficultySplit"].values())
    if ds_scored != of["scored"]:
        p.append(f"difficultySplit scored {ds_scored} != overall {of['scored']}")
    cov = m["coverage"]
    if cov["gtPresent"] != of["scored"] or cov["matched"] != of["match"]:
        p.append(f"coverage {cov['gtPresent']}/{cov['matched']} != overall {of['scored']}/{of['match']}")
    if cov["gtPresent"] != cov["matched"] + cov["extAttemptedMiss"] + cov["extNotAttempted"] + of["mismatch"]:
        p.append("coverage denominators do not partition gtPresent")
    if not os.path.isfile(rp) or "가설" not in open(rp, encoding="utf-8").read():
        p.append("report.md missing / no hypothesis banner")
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    args = ap.parse_args()
    # testset-aware: never let a rich checker grab a thin run (or vice versa).
    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else C.latest_run(args.testset)

    results: list[tuple[str, bool, str]] = []

    # --- non-rich testset: generic self-consistency gate (no rich constants) ---
    if args.testset != C.DEFAULT_TESTSET:
        if not run_dir or not os.path.isdir(run_dir):
            results.append(("run-dir", False, f"no run dir ({run_dir})"))
        else:
            xc = manifest_run_crosscheck(run_dir, args.testset)
            results.append(("manifest<->run", not xc, xc[0] if xc else "all canned samples present, parse ok"))
            sc = thin_self_consistency(run_dir, args.testset)
            results.append(("metrics-self-consistency", not sc, sc[0] if sc else "cross-foot + coverage + report OK"))
        print(f"checker over {args.testset} run: {os.path.basename(run_dir) if run_dir else '(none)'}\n")
        width = max(len(r[0]) for r in results)
        all_ok = all(ok for _, ok, _ in results)
        for name, ok, last in results:
            print(f"  {'PASS' if ok else 'FAIL'}  {name:<{width}}  {last}")
        print()
        print("CHECKER PASS" if all_ok else "CHECKER FAIL", f"({args.testset})")
        return 0 if all_ok else 1

    gp = golden_regression()
    results.append(("normalization-golden", not gp, gp[0] if gp else "all golden cases hold"))

    for name, argv in [("phase0_contract_check.py", []), ("phase1_check.py", [])]:
        ok, last = run_check(name, argv)
        results.append((name, ok, last))

    if not run_dir or not os.path.isdir(run_dir):
        results.append(("run-dir", False, f"no run dir ({run_dir})"))
    else:
        # pass the path RELATIVE to runs/ (not just the basename) so nested batch
        # runs (runs/<batch>/study) resolve correctly in the phase sub-checks.
        rel_ts = os.path.relpath(run_dir, C.RUNS_DIR).replace(os.sep, "/")
        ts_argv = ["--ts", rel_ts]
        for name in ("phase2_check.py", "phase3_check.py", "phase4_check.py"):
            ok, last = run_check(name, ts_argv)
            results.append((name, ok, last))
        xc = manifest_run_crosscheck(run_dir)
        results.append(("manifest<->run", not xc, xc[0] if xc else "all active samples present, parse 6/6"))

    _disp = os.path.relpath(run_dir, C.RUNS_DIR).replace(os.sep, "/") if run_dir else "(none)"
    print(f"checker over run: {_disp}\n")
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
