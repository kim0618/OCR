"""P0 thin-ready gate — the §6.6 redesign checker (grows step 0 → step 6).

Each step appends assertions; every prior step must stay green. The final gate
(step 6) is: thin fixture passes the full pipeline AND the 6 rich samples stay
green AND down-projecting rich→thin agrees on shared fields (bidirectional).

Run:  python eval/p0_thin_check.py            exit 0 = PASS
"""

from __future__ import annotations

import os
import sys

import contract as C
from gt_loader import load_gt


def check_ssot() -> list[str]:
    """Step 0: SSOT thin column contract invariants (§6.6 war column contract)."""
    p: list[str] = []
    if len(C.THIN_SCALAR_FIELDS) != 10:
        p.append(f"THIN_SCALAR_FIELDS = {len(C.THIN_SCALAR_FIELDS)} != 10")
    if len(C.THIN_ROW_KEYS) != 6:
        p.append(f"THIN_ROW_KEYS = {len(C.THIN_ROW_KEYS)} != 6")
    if C.ROW_ALIGN_KEY in C.THIN_ROW_KEYS:
        p.append("THIN_ROW_KEYS must not contain rowIndex (thin has none)")
    if len(C.NEW_3_FIELDS) != 3:
        p.append(f"NEW_3_FIELDS = {len(C.NEW_3_FIELDS)} != 3")
    if len(C.RICH_ONLY_FIELDS) != 7:
        p.append(f"RICH_ONLY_FIELDS = {len(C.RICH_ONLY_FIELDS)} != 7")

    new3 = set(C.NEW_3_FIELDS)
    thin = set(C.THIN_SCALAR_FIELDS)
    richonly = set(C.RICH_ONLY_FIELDS)
    allscalar = set(C.ALL_SCALAR_LABELS)

    if not new3 <= thin:
        p.append(f"NEW_3_FIELDS not ⊆ THIN_SCALAR_FIELDS: {sorted(new3 - thin)}")
    if thin & richonly:
        p.append(f"THIN_SCALAR ∩ RICH_ONLY must be ∅: {sorted(thin & richonly)}")
    # the new-3 are exactly the thin scalars rich does NOT have.
    shared = thin - new3
    if not shared <= allscalar:
        p.append(f"shared thin scalars escape rich universe: {sorted(shared - allscalar)}")
    if not richonly <= allscalar:
        p.append(f"RICH_ONLY escapes rich universe: {sorted(richonly - allscalar)}")
    # COVERAGE ORACLE: (thin shared) ∪ (rich-only) == full rich scalar universe.
    if (shared | richonly) != allscalar:
        missing = allscalar - (shared | richonly)
        extra = (shared | richonly) - allscalar
        p.append(f"partition != rich universe (missing={sorted(missing)} extra={sorted(extra)})")
    return p


def check_profile_helpers() -> list[str]:
    p: list[str] = []
    if tuple(C.required_scalar_fields("rich")) != C.COMMON_12:
        p.append("required_scalar_fields('rich') != COMMON_12")
    if C.required_scalar_fields("thin") != ():
        p.append("required_scalar_fields('thin') must be empty (scores gt.keys())")
    if not C.enforce_per_sample("rich") or C.enforce_per_sample("thin"):
        p.append("enforce_per_sample must be rich-only")
    return p


def check_registry() -> list[str]:
    p: list[str] = []
    try:
        rich = C.get_testset("invoice_study")
        thin = C.get_testset("invoice_thin")
    except KeyError as exc:
        return [f"registry: {exc}"]
    if rich["kind"] != "rich" or rich["runMode"] != "live":
        p.append("invoice_study must be rich/live")
    if thin["kind"] != "thin" or thin["runMode"] != "canned":
        p.append("invoice_thin must be thin/canned")
    if not os.path.isdir(rich["gtDir"]):
        p.append(f"invoice_study GT dir missing: {rich['gtDir']}")
    return p


def check_injection() -> list[str]:
    """Profile is injected (⓳'), not inferred; rich GT carries the rich signal."""
    p: list[str] = []
    import glob
    gt = C.get_testset("invoice_study")["gtDir"]
    paths = sorted(glob.glob(os.path.join(gt, "*.json")))
    if not paths:
        return ["no rich GT to test injection"]
    g = load_gt(paths[0], profile="rich")
    if g["profile"] != "rich":
        p.append("injected profile 'rich' not honored")
    if not g["_meta"]["profileInjected"]:
        p.append("profileInjected flag not set when profile passed")
    if g["_meta"]["richSignal"] is not True:
        p.append("rich fixture should carry richSignal=True (bbox/edited present)")
    return p


def check_thin_fixture_loads() -> list[str]:
    """Step 1/2: thin fixture exists, manifests as 6 canned, loads 6/6 (thin profile).

    RED at step 1 (loader rich-strict: requires rowIndex, enforces per-sample).
    GREEN at step 2 (loader relaxed: rowIndex optional, per-sample rich-gated).
    """
    from build_manifest import build_manifest
    from gt_loader import GTLoadError
    p: list[str] = []
    m = build_manifest("invoice_thin")
    if m["kind"] != "thin":
        p.append(f"thin manifest kind {m['kind']} != thin")
    statuses = {}
    for s in m["samples"]:
        statuses[s["status"]] = statuses.get(s["status"], 0) + 1
    canned = [s for s in m["samples"] if s["status"] == "canned"]
    if len(canned) != 6:
        p.append(f"expected 6 canned thin samples, got {statuses}")
    # load each thin GT under the injected thin profile
    loaded = 0
    for s in m["samples"]:
        if not s.get("gt"):
            continue
        gt_path = os.path.join(C.HERE, s["gt"])
        try:
            g = load_gt(gt_path, profile="thin")
        except GTLoadError as exc:
            p.append(f"thin load {s['sourceFile']}: {exc}")
            continue
        if g["profile"] != "thin":
            p.append(f"{s['sourceFile']}: profile {g['profile']} != thin")
        if g["_meta"]["richSignal"]:
            p.append(f"{s['sourceFile']}: thin GT must not carry rich signal")
        loaded += 1
    if loaded != 6:
        p.append(f"thin loader {loaded}/6")
    return p


def check_normalize_types() -> list[str]:
    """Step 3: new-3 field types + name-heuristic fallback (➍)."""
    import normalize as N
    p: list[str] = []
    # explicit new-3 mappings
    if N.FIELD_TYPE.get("discountAmount") != "amount":
        p.append("discountAmount must map to amount")
    if N.FIELD_TYPE.get("documentNumber") != "code":
        p.append("documentNumber must map to code")
    if N.FIELD_TYPE.get("taxType") != "text":
        p.append("taxType must map to text")
    if N.ROW_KEY_TYPE.get("manufacturingNo") != "code":
        p.append("manufacturingNo must map to code")
    # behavior: amount collapses separators, code uppercases alnum, text NFC/casefold
    cases = [
        ("discountAmount", "1,000", "1000"),
        ("documentNumber", "2024-0702-0013", "202407020013"),
        ("totalAmount", "18,098,750", "18098750"),
    ]
    for label, a, b in cases:
        if N.normalize_field(label, a) != b:
            p.append(f"normalize_field({label},{a!r}) != {b!r} (got {N.normalize_field(label, a)!r})")
    if N.normalize_cell("manufacturingNo", "abc-123") != "ABC123":
        p.append("manufacturingNo cell normalize wrong")
    # name-heuristic fallback for unknown keys (future ETL columns)
    heur = [
        (N.normalize_field, "rebateAmount", "2,000", "2000"),   # *Amount -> amount
        (N.normalize_field, "deliveryDate", "2024-01-02", "20240102"),  # *Date -> date
        (N.normalize_cell, "batchNo", "lot-9", "LOT9"),         # *No -> code
    ]
    for fn, key, a, b in heur:
        if fn(key, a) != b:
            p.append(f"heuristic {fn.__name__}({key},{a!r}) != {b!r} (got {fn(key, a)!r})")
    # heuristic must NOT fire for mapped rich keys (no behavior shift)
    if N._infer_type("supplierCompany") != "text" or N.FIELD_TYPE["supplierBizNumber"] != "bizno":
        p.append("rich mapped keys must keep explicit types")
    return p


# Measured on the 6-sample rich set (run 20260609_143048): content alignment
# reproduces the rowIndex truth 43/43 = 100%. A drop is a real regression to
# investigate (small-sample baseline = hypothesis per plan §8, not a universal law).
ORACLE_MIN_AGREEMENT = 1.0


def check_rowindex_oracle() -> list[str]:
    """Step 4: content alignment scores thin tables AND reproduces the rich
    rowIndex truth (➏ numeric oracle)."""
    import glob, json
    import normalize as N
    import compare_table as T
    p: list[str] = []

    # (a) thin tables now score via content alignment (rowsGt>0, mode=content).
    thin = C.get_testset("invoice_thin")
    for gp in sorted(glob.glob(os.path.join(thin["gtDir"], "*.json"))):
        src = os.path.basename(gp)[:-5]
        g = load_gt(gp, profile="thin")
        rec = json.load(open(os.path.join(thin["recDir"], src + ".json"), encoding="utf-8"))
        ext = (rec.get("documentFields") or {}).get("tableRows") or []
        tc = T.compare_table(g["tableRows"], ext)
        if tc["alignMode"] != "content":
            p.append(f"thin {src}: alignMode {tc['alignMode']} != content")
        if tc["rowCountGt"] != C.get_testset('invoice_thin')['expected'].get(src):
            p.append(f"thin {src}: rowCountGt {tc['rowCountGt']} != expected")
        if len(tc["matchedRowIdx"]) != tc["rowCountGt"]:
            p.append(f"thin {src}: matched {len(tc['matchedRowIdx'])} != rowsGt {tc['rowCountGt']}")

    # (b) rich rowIndex oracle: content alignment must reproduce positional truth.
    rich = C.get_testset("invoice_study")
    run = C.latest_run("invoice_study")  # flat or nested batch run, testset-aware
    if not run:
        return p + ["no rich run dir for rowIndex oracle"]
    truth_total = agree_total = 0
    for gp in sorted(glob.glob(os.path.join(rich["gtDir"], "*.json"))):
        g = load_gt(gp, profile="rich")
        src = g["sourceFile"]
        rec = json.load(open(os.path.join(run, "samples", src + ".json"), encoding="utf-8"))
        ext = (rec.get("documentFields") or {}).get("tableRows") or []
        ri_pairs, *_ = T._align_by_rowindex(g["tableRows"], ext)
        truth = {k: k for k, _, _ in ri_pairs}
        co_pairs, *_ = T._align_by_content(g["tableRows"], ext)
        for _, grow, erow in co_pairs:
            gidx, eidx = N.norm_index(grow.get("rowIndex")), N.norm_index(erow.get("rowIndex"))
            if gidx in truth and truth[gidx] == eidx:
                agree_total += 1
        truth_total += len(truth)
    ratio = (agree_total / truth_total) if truth_total else 1.0
    if ratio < ORACLE_MIN_AGREEMENT:
        p.append(f"rowIndex oracle: content agreement {agree_total}/{truth_total} "
                 f"= {ratio:.3f} < {ORACLE_MIN_AGREEMENT}")
    return p


def check_profile_consistency() -> list[str]:
    """Step 6: injected profile ⇔ content rich-signal (⓳' demotion / bboxRefs).

    rich GT must carry the rich signal (bbox/edited present); thin GT must not.
    This is the consistency check that replaces content-inference.
    """
    import glob
    p: list[str] = []
    for name, want_rich in (("invoice_study", True), ("invoice_thin", False)):
        ts = C.get_testset(name)
        for gp in sorted(glob.glob(os.path.join(ts["gtDir"], "*.json"))):
            g = load_gt(gp, profile=ts["kind"])
            sig = g["_meta"]["richSignal"]
            if g["profile"] != ts["kind"]:
                p.append(f"{name}/{g['sourceFile']}: profile {g['profile']} != injected {ts['kind']}")
            if sig != want_rich:
                p.append(f"{name}/{g['sourceFile']}: richSignal {sig} inconsistent with {ts['kind']} profile")
    return p


def check_thin_full_pipeline() -> list[str]:
    """Step 5/6: drive the thin canned pipeline + the generic checker; PASS."""
    import subprocess
    import sys as _sys
    from run_batch import run_batch
    from compare_run import compare_run
    p: list[str] = []
    # stable run id so the gate is idempotent (no run-dir accumulation).
    ts = "p0_thin_canned"
    out = run_batch(testset="invoice_thin", resume_ts=ts, workers=4)
    if out["meta"]["summary"]["error"]:
        p.append(f"thin run errors: {out['meta']['summary']}")
    compare_run(ts, testset="invoice_thin")
    r = subprocess.run([_sys.executable, os.path.join(C.HERE, "checker.py"),
                        "--ts", ts, "--testset", "invoice_thin"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        tail = (r.stdout or "") + (r.stderr or "")
        p.append("thin checker FAIL: " + tail.strip().splitlines()[-1] if tail.strip() else "thin checker FAIL")
    return p


def check_bidirectional_oracle() -> list[str]:
    """Acceptance (양방향): down-project each rich sample → thin and prove the
    thin path agrees with the rich path on the SHARED columns (SSOT-based oracle).

    Same GT values (down-projected), same extraction (canned == rich run), same
    normalization ⇒ identical per-field and per-cell verdicts. A divergence means
    the thin path silently changed scoring.
    """
    import glob, json
    from gt_loader import load_gt as _load
    from compare_fields import compare_fields
    from compare_table import compare_table
    p: list[str] = []

    rich = C.get_testset("invoice_study")
    thin = C.get_testset("invoice_thin")
    # use the latest rich run (flat or nested); canned rec is a copy of it.
    rich_run = C.latest_run("invoice_study")
    if not rich_run or not os.path.isdir(os.path.join(rich_run, "samples")):
        return ["no rich run dir for oracle"]

    shared_scalars = set(C.THIN_SCALAR_FIELDS) - set(C.NEW_3_FIELDS)
    shared_cells = set(C.THIN_ROW_KEYS) & set(k for k in C.ROW_VALUE_KEYS)
    checked_fields = checked_cells = 0

    for gp in sorted(glob.glob(os.path.join(rich["gtDir"], "*.json"))):
        rg = _load(gp, profile="rich")
        src = rg["sourceFile"]
        tp = os.path.join(thin["gtDir"], src + ".json")
        if not os.path.isfile(tp):
            p.append(f"{src}: no thin counterpart")
            continue
        tg = _load(tp, profile="thin")
        rec = json.load(open(os.path.join(rich_run, "samples", src + ".json"), encoding="utf-8"))
        ext = rec.get("documentFields") or {}

        rf = compare_fields(rg, ext)["perField"]
        tf = compare_fields(tg, ext)["perField"]
        for label in sorted(shared_scalars):
            if label in rf and label in tf:
                if rf[label]["status"] != tf[label]["status"] or rf[label]["gtNorm"] != tf[label]["gtNorm"]:
                    p.append(f"{src}/{label}: rich={rf[label]['status']}({rf[label]['gtNorm']!r}) "
                             f"!= thin={tf[label]['status']}({tf[label]['gtNorm']!r})")
                checked_fields += 1

        # table: rich rowIndex-aligned vs thin content-aligned, shared cell keys.
        rt = {r["rowIndex"]: r for r in compare_table(rg["tableRows"], ext.get("tableRows") or [])["rows"]}
        tt = {r["rowIndex"]: r for r in compare_table(tg["tableRows"], ext.get("tableRows") or [])["rows"]}
        for ridx in sorted(set(rt) & set(tt), key=lambda s: int(s) if s.isdigit() else 0):
            rc, tc = rt[ridx]["cells"], tt[ridx]["cells"]
            for key in sorted(shared_cells):
                if key in rc and key in tc:
                    if rc[key]["status"] != tc[key]["status"] or rc[key]["gtNorm"] != tc[key]["gtNorm"]:
                        p.append(f"{src}/row{ridx}:{key}: rich={rc[key]['status']} != thin={tc[key]['status']}")
                    checked_cells += 1

    if checked_fields == 0 or checked_cells == 0:
        p.append(f"oracle covered too little (fields={checked_fields}, cells={checked_cells})")
    return p


def check_rich_six_green() -> list[str]:
    """Step 6: the rich 6-sample harness must stay fully green (the live checker)."""
    import subprocess
    import sys as _sys
    r = subprocess.run([_sys.executable, os.path.join(C.HERE, "checker.py")],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        out = (r.stdout or "") + (r.stderr or "")
        fails = [ln.strip() for ln in out.splitlines() if "FAIL" in ln]
        return ["rich checker FAIL: " + (fails[0] if fails else "see checker output")]
    return []


STEPS = [
    ("step0:ssot-column-contract", check_ssot),
    ("step0:profile-helpers", check_profile_helpers),
    ("step0:testset-registry", check_registry),
    ("step0:profile-injection", check_injection),
    ("step1-2:thin-fixture-loads", check_thin_fixture_loads),
    ("step3:normalize-types", check_normalize_types),
    ("step4:rowindex-oracle+content", check_rowindex_oracle),
    ("step6:profile-consistency", check_profile_consistency),
    ("step6:thin-full-pipeline", check_thin_full_pipeline),
    ("step6:bidirectional-oracle", check_bidirectional_oracle),
    ("step6:rich-6-green", check_rich_six_green),
]


def main() -> int:
    results = [(name, fn()) for name, fn in STEPS]
    width = max(len(n) for n, _ in results)
    all_ok = True
    for name, problems in results:
        ok = not problems
        all_ok = all_ok and ok
        msg = "OK" if ok else problems[0]
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<{width}}  {msg}")
        for extra in problems[1:]:
            print(f"          - {extra}")
    print()
    if all_ok:
        print("P0 THIN-READY CHECK PASS")
        return 0
    print("P0 THIN-READY CHECK FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
