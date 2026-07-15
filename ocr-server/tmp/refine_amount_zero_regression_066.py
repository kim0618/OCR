"""Find the largest zero-regression guard for 066 amount blank recovery."""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path


SERVER = Path(__file__).resolve().parents[1]
EVAL = SERVER / "eval"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(EVAL))
sys.path.insert(0, str(SERVER / "tmp"))

from analyze_amount_big_levers_066 import (  # noqa: E402
    RUN_DIR, amount_from_group, build_geometry, delta, map_rows, norm_money,
)
from build_manifest import build_manifest  # noqa: E402
from compare_table import compare_table  # noqa: E402
from gt_loader import load_gt_aggregate  # noqa: E402


OUT = SERVER / "tmp" / "refine_amount_zero_regression_066.result.json"
CONFIGS = [
    (f"pure_a{anchors}_s{str(score).replace('.', '')}_x15", anchors, score, 0.015)
    for anchors in (1, 2, 3)
    for score in (0.70, 0.75, 0.80, 0.85, 0.90)
]


def anchors(rows: list[dict], mapped: list[dict | None]) -> list[float]:
    xs = []
    for row, item in zip(rows, mapped):
        current = norm_money(row.get("amount"))
        if not current or not item:
            continue
        hits = [line.cx for line in item["group"] if norm_money(line.text) == current]
        if hits:
            xs.append(max(hits))
    return xs


def changes_for(rows, mapped, page_w, anchor_xs, min_anchors, min_score, x_tol):
    if any(str(row.get("_source") or "") != "invoice_statement_table_parser" for row in rows):
        return [], []
    if len(anchor_xs) < min_anchors:
        return [], []
    ordered = sorted(anchor_xs)
    med_x = ordered[len(ordered) // 2]
    out = copy.deepcopy(rows)
    changes = []
    for idx, (row, item) in enumerate(zip(out, mapped)):
        if str(row.get("_source") or "") != "invoice_statement_table_parser":
            continue
        if str(row.get("amount") or "").strip() or not item or item["score"] < min_score:
            continue
        found = amount_from_group(item["group"], page_w, med_x - page_w * x_tol)
        if not found:
            continue
        value, meta = found
        if abs(meta["cx"] - med_x) > page_w * x_tol:
            continue
        row["amount"] = value
        changes.append({"row": idx + 1, "value": value, "score": item["score"], "xDelta": abs(meta["cx"] - med_x) / page_w})
    return out, changes


def main():
    manifest = build_manifest("invoice_thin")
    sample_by_source = {item["sourceFile"]: item for item in manifest["samples"]}
    aggregate = load_gt_aggregate(str(EVAL / manifest["gtAggregate"]), profile="thin")
    metrics = {
        name: {"docsChanged": 0, "cellsChanged": 0, "gain": 0, "regression": 0,
               "spuriousDelta": 0, "net": 0, "regressionDocs": []}
        for name, *_ in CONFIGS
    }
    documents = 0
    for snap_path in sorted((RUN_DIR / "snapshots").glob("*.json")):
        source = snap_path.name[:-5]
        meta = sample_by_source.get(source)
        sample_path = RUN_DIR / "samples" / snap_path.name
        if not meta or not sample_path.exists():
            continue
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        rows = (sample.get("documentFields") or {}).get("tableRows") or []
        if not rows or not any(not str(r.get("amount") or "").strip() for r in rows):
            documents += 1
            continue
        gt_rows = aggregate[meta["gtKey"]]["tableRows"]
        before = compare_table(gt_rows, rows)
        groups, page_w = build_geometry(snap.get("ocr_lines_raw") or [])
        mapped = map_rows(rows, groups)
        anchor_xs = anchors(rows, mapped)
        for name, min_anchors, min_score, x_tol in CONFIGS:
            new_rows, changed = changes_for(rows, mapped, page_w, anchor_xs, min_anchors, min_score, x_tol)
            if not changed:
                continue
            d = delta(before, compare_table(gt_rows, new_rows))
            m = metrics[name]
            m["docsChanged"] += 1
            m["cellsChanged"] += len(changed)
            for key in ("gain", "regression", "spuriousDelta"):
                m[key] += d[key]
            if d["regression"]:
                m["regressionDocs"].append({"sourceFile": source, **d, "changes": changed})
        documents += 1
    for m in metrics.values():
        m["net"] = m["gain"] - m["regression"]
    ranked = sorted(
        ({"config": name, **m} for name, m in metrics.items()),
        key=lambda x: (x["regression"] != 0, x["spuriousDelta"] != 0, -x["gain"], -x["net"]),
    )
    result = {"basis": "066 thin", "documents": documents, "ranked": ranked}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"documents": documents, "top": [{k: x[k] for k in ("config", "docsChanged", "cellsChanged", "gain", "regression", "spuriousDelta", "net")} for x in ranked[:15]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
