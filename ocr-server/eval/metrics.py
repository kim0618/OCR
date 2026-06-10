"""metrics — aggregate a run's per-sample comparisons into metrics + time series.

Reads runs/<ts>/compare/*.json, produces:
  - overall field & cell accuracy
  - per-field (labelEn) accuracy   -> which fields are weak
  - per-bucket defect totals
  - free vs fallback split
  - edited vs non-edited split
  - slices: extractionPath, supplier, layout, qualityTag (code path fires now,
    fills out when 30-image set / real tags arrive)
and appends one row to eval/metrics_timeseries.sqlite for regression tracking.

Writes runs/<ts>/metrics.json. Measurement-only.

CLI: python eval/metrics.py [--ts <run_ts>]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
from typing import Any

import contract as C

TIMESERIES_DB = os.path.join(C.HERE, "metrics_timeseries.sqlite")


def _acc(scored: int, match: int) -> float | None:
    return (match / scored) if scored else None


def _new_counts() -> dict[str, int]:
    return {"scored": 0, "match": 0, "mismatch": 0, "ext_missing": 0, "gt_empty": 0}


def _add(dst: dict[str, int], src: dict[str, int]) -> None:
    for k in dst:
        dst[k] += src.get(k, 0)


def _load_compares(run_dir: str) -> list[dict[str, Any]]:
    out = []
    for p in sorted(glob.glob(os.path.join(run_dir, "compare", "*.json"))):
        out.append(json.load(open(p, encoding="utf-8")))
    return out


def _read_testset(run_dir: str) -> str:
    try:
        meta = json.load(open(os.path.join(run_dir, "run_meta.json"), encoding="utf-8"))
        return meta.get("testset") or C.DEFAULT_TESTSET
    except Exception:
        return C.DEFAULT_TESTSET


def compute_metrics(run_dir: str) -> dict[str, Any]:
    compares = _load_compares(run_dir)
    if not compares:
        raise FileNotFoundError(f"no compare/*.json in {run_dir}")

    testset = _read_testset(run_dir)
    overall_field = _new_counts()
    overall_cell = _new_counts()
    per_field: dict[str, dict[str, int]] = {}
    buckets_total = {"recognition": 0, "structure": 0, "layout": 0, "preprocessing": 0}
    by_path: dict[str, dict[str, dict[str, int]]] = {}   # path -> {field, cell}
    edited_split = {"edited": _new_counts(), "nonEdited": _new_counts()}
    # ➐ profile-aware difficulty split (rich=edited, thin=low-confidence).
    difficulty_split = {"difficult": _new_counts(), "normal": _new_counts()}
    # ➌E coverage two denominators (graded vs extractor-never-attempted).
    coverage = {"gtPresent": 0, "matched": 0, "extNotAttempted": 0, "extAttemptedMiss": 0}
    slices: dict[str, dict[str, dict[str, int]]] = {
        "extractionPath": {}, "supplier": {}, "layout": {}, "qualityTag": {}, "profile": {},
    }

    # manifest for qualityTags (may be absent today)
    from build_manifest import build_manifest
    qtags = {}
    for s in build_manifest(testset)["samples"]:
        qtags[s["sourceFile"]] = s.get("qualityTags") or []

    def slice_add(slice_name: str, group: str, fcounts: dict[str, int]) -> None:
        g = slices[slice_name].setdefault(group, _new_counts())
        _add(g, fcounts)

    for d in compares:
        src = d["sourceFile"]
        path = d.get("extractionPath") or "unknown"
        profile = d.get("profile") or d["fields"].get("profile") or "rich"
        fc = d["fields"]["counts"]
        cc = d["table"]["cellCounts"]
        _add(overall_field, fc)
        _add(overall_cell, cc)

        # coverage two denominators (➌E)
        for k in coverage:
            coverage[k] += d["fields"].get("coverage", {}).get(k, 0)

        # per-field
        for label, info in d["fields"]["perField"].items():
            pf = per_field.setdefault(label, _new_counts())
            st = info["status"]
            if st != "gt_empty":
                pf["scored"] += 1
            pf[st] = pf.get(st, 0) + 1
            # edited split (field-level, rich)
            bucket = "edited" if info.get("edited") else "nonEdited"
            if st != "gt_empty":
                edited_split[bucket]["scored"] += 1
            edited_split[bucket][st] = edited_split[bucket].get(st, 0) + 1
            # difficulty split (➐, profile-aware): info["difficult"] already branched
            dbucket = "difficult" if info.get("difficult") else "normal"
            if st != "gt_empty":
                difficulty_split[dbucket]["scored"] += 1
            difficulty_split[dbucket][st] = difficulty_split[dbucket].get(st, 0) + 1

        # buckets
        for b, n in d["buckets"]["bucketTally"].items():
            buckets_total[b] = buckets_total.get(b, 0) + n

        # by path
        bp = by_path.setdefault(path, {"field": _new_counts(), "cell": _new_counts()})
        _add(bp["field"], fc)
        _add(bp["cell"], cc)

        # slices (on field counts)
        # group suppliers by whitespace-stripped name so the same supplier with
        # different GT spacing (e.g. "주식회사 엘비..." vs "주식회사엘비...") merges.
        _sup_raw = d["fields"]["perField"].get("supplierCompany", {}).get("gt", "")
        supplier = "".join(str(_sup_raw).split()) or "(empty)"
        layout = "single_row" if d["table"]["rowCountGt"] <= 1 else "multi_row"
        slice_add("extractionPath", path, fc)
        slice_add("supplier", supplier, fc)
        slice_add("layout", layout, fc)
        slice_add("profile", profile, fc)
        for t in (qtags.get(src) or ["untagged"]):
            slice_add("qualityTag", t, fc)

    def finalize(counts: dict[str, int]) -> dict[str, Any]:
        return {**counts, "accuracy": _acc(counts["scored"], counts["match"])}

    cov_graded = coverage["gtPresent"]
    # runTs = path relative to runs/ so a nested batch run (batch/study) is unique
    # in the time-series instead of colliding on the basename "study"/"thin".
    run_ts = os.path.relpath(run_dir, C.RUNS_DIR).replace(os.sep, "/")
    metrics = {
        "schemaVersion": "eval-metrics.v1",
        "runTs": run_ts,
        "testset": testset,
        "sampleCount": len(compares),
        "overall": {
            "field": finalize(overall_field),
            "cell": finalize(overall_cell),
        },
        "perField": {k: finalize(v) for k, v in sorted(per_field.items())},
        "buckets": buckets_total,
        "byPath": {p: {"field": finalize(v["field"]), "cell": finalize(v["cell"])}
                   for p, v in sorted(by_path.items())},
        "editedSplit": {k: finalize(v) for k, v in edited_split.items()},
        "difficultySplit": {k: finalize(v) for k, v in difficulty_split.items()},
        # ➌E two coverage denominators: of GT-present fields, what the extractor
        # matched vs missed-having-tried vs never-attempted (new-3 honest-miss).
        "coverage": {
            **coverage,
            "gradedAccuracy": _acc(cov_graded, coverage["matched"]),
            "attemptRate": _acc(cov_graded, cov_graded - coverage["extNotAttempted"]),
        },
        "slices": {
            sname: {g: finalize(c) for g, c in groups.items()}
            for sname, groups in slices.items()
        },
    }

    with open(os.path.join(run_dir, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    _append_timeseries(metrics)
    return metrics


_TS_DDL = """CREATE TABLE IF NOT EXISTS runs (
    testset TEXT, runTs TEXT, sampleCount INT,
    fieldScored INT, fieldMatch INT, fieldAcc REAL,
    cellScored INT, cellMatch INT, cellAcc REAL,
    freeFieldAcc REAL, fallbackFieldAcc REAL,
    bRecognition INT, bStructure INT, bLayout INT, bPreprocessing INT,
    PRIMARY KEY (testset, runTs)
)"""
_TS_COLS = ("testset", "runTs", "sampleCount", "fieldScored", "fieldMatch", "fieldAcc",
            "cellScored", "cellMatch", "cellAcc", "freeFieldAcc", "fallbackFieldAcc",
            "bRecognition", "bStructure", "bLayout", "bPreprocessing")


def _append_timeseries(m: dict[str, Any]) -> None:
    con = sqlite3.connect(TIMESERIES_DB)
    try:
        # Migrate the pre-P0 schema (runTs PK, no testset) in place so existing
        # history is preserved and tagged invoice_study (it was rich-only then).
        existing = [r[1] for r in con.execute("PRAGMA table_info(runs)").fetchall()]
        if existing and "testset" not in existing:
            con.execute("ALTER TABLE runs RENAME TO runs_legacy")
            con.execute(_TS_DDL)
            con.execute(
                "INSERT OR IGNORE INTO runs (" + ",".join(_TS_COLS) + ") "
                "SELECT 'invoice_study', runTs, sampleCount, fieldScored, fieldMatch, fieldAcc, "
                "cellScored, cellMatch, cellAcc, freeFieldAcc, fallbackFieldAcc, "
                "bRecognition, bStructure, bLayout, bPreprocessing FROM runs_legacy"
            )
            con.execute("DROP TABLE runs_legacy")
        else:
            con.execute(_TS_DDL)

        of = m["overall"]["field"]
        oc = m["overall"]["cell"]
        bp = m["byPath"]
        b = m["buckets"]
        con.execute(
            "INSERT OR REPLACE INTO runs (" + ",".join(_TS_COLS) + ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                m.get("testset", C.DEFAULT_TESTSET), m["runTs"], m["sampleCount"],
                of["scored"], of["match"], of["accuracy"],
                oc["scored"], oc["match"], oc["accuracy"],
                bp.get("free", {}).get("field", {}).get("accuracy"),
                bp.get("fallback", {}).get("field", {}).get("accuracy"),
                b["recognition"], b["structure"], b["layout"], b["preprocessing"],
            ),
        )
        con.commit()
    finally:
        con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    args = ap.parse_args()
    run_dir = (os.path.join(C.RUNS_DIR, args.ts) if args.ts
               else sorted(p for p in glob.glob(os.path.join(C.RUNS_DIR, "*")) if os.path.isdir(p))[-1])
    m = compute_metrics(run_dir)
    print(f"run: {m['runTs']}  samples={m['sampleCount']}")
    print(f"overall field acc: {m['overall']['field']['accuracy']}")
    print(f"overall cell  acc: {m['overall']['cell']['accuracy']}")
    print(f"byPath: " + ", ".join(
        f"{p}={v['field']['accuracy']}" for p, v in m["byPath"].items()))
    print(f"buckets: {m['buckets']}")
    print(f"timeseries -> {TIMESERIES_DB}")
