"""066 thin read-only probe: relocate same-row money fields into amount."""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
EVAL = SERVER / "eval"
RUN = EVAL / "runs" / "066_20260709_122046" / "thin"
OUT = SERVER / "tmp" / "probe_amount_same_row_relocation_066.result.json"
sys.path.insert(0, str(EVAL))

from build_manifest import build_manifest  # noqa: E402
from compare_table import compare_table  # noqa: E402
from gt_loader import load_gt_aggregate  # noqa: E402

MONEY = re.compile(r"\d[\d,.]*")
CONFIGS = (
    "pure_total", "pure_supply_last", "pure_total_else_supply", "all_total_else_supply",
    "pure_supply_anchor1", "pure_supply_anchor2", "pure_supply_anchor1_two_tokens",
)


def candidate(row, config):
    if str(row.get("amount") or "").strip():
        return ""
    if str(row.get("_source") or "") != "invoice_statement_table_parser":
        return ""
    total = str(row.get("totalAmount") or "").strip()
    supply = str(row.get("supplyAmount") or "").strip()
    if config.endswith("total"):
        raw = total
    elif config.endswith("supply_last") or "supply_anchor" in config:
        raw = supply
    else:
        raw = total or supply
    values = MONEY.findall(raw)
    value = values[-1] if values else ""
    return value if len(re.sub(r"\D", "", value)) >= 3 else ""


def norm(value):
    return re.sub(r"\D", "", str(value or "")).lstrip("0") or "0"


def supply_values(row):
    return MONEY.findall(str(row.get("supplyAmount") or ""))


def statuses(table):
    return {
        str(row.get("rowIndex")): (row.get("cells") or {}).get("amount", {})
        for row in table.get("rows") or [] if (row.get("cells") or {}).get("amount")
    }


def measure(before, after):
    b, a = statuses(before), statuses(after)
    keys = set(b) | set(a)
    gain = sum(b.get(k, {}).get("status") != "match" and a.get(k, {}).get("status") == "match" for k in keys)
    regression = sum(b.get(k, {}).get("status") == "match" and a.get(k, {}).get("status") != "match" for k in keys)
    sp_b = sum(bool(x.get("spurious")) for x in b.values())
    sp_a = sum(bool(x.get("spurious")) for x in a.values())
    return gain, regression, sp_a - sp_b


def main():
    manifest = build_manifest("invoice_thin")
    by_source = {x["sourceFile"]: x for x in manifest["samples"]}
    aggregate = load_gt_aggregate(str(EVAL / manifest["gtAggregate"]), profile="thin")
    result = {name: {"docsChanged": 0, "cellsChanged": 0, "gain": 0, "regression": 0, "spuriousDelta": 0} for name in CONFIGS}
    documents = 0
    for path in sorted((RUN / "samples").glob("*.json")):
        source = path.name[:-5]
        meta = by_source.get(source)
        if not meta:
            continue
        sample = json.loads(path.read_text(encoding="utf-8"))
        rows = (sample.get("documentFields") or {}).get("tableRows") or []
        before = compare_table(aggregate[meta["gtKey"]]["tableRows"], rows)
        pure = bool(rows) and all(str(r.get("_source") or "") == "invoice_statement_table_parser" for r in rows)
        supply_anchor_count = sum(
            bool(str(row.get("amount") or "").strip())
            and bool(supply_values(row))
            and norm(row.get("amount")) == norm(supply_values(row)[-1])
            for row in rows
        )
        supply_disagree_count = sum(
            bool(str(row.get("amount") or "").strip())
            and bool(supply_values(row))
            and norm(row.get("amount")) != norm(supply_values(row)[-1])
            for row in rows
        )
        for config in CONFIGS:
            if config.startswith("pure_") and not pure:
                continue
            if "anchor1" in config and (supply_anchor_count < 1 or supply_disagree_count):
                continue
            if "anchor2" in config and (supply_anchor_count < 2 or supply_disagree_count):
                continue
            new_rows = copy.deepcopy(rows)
            changed = 0
            for row in new_rows:
                if config.endswith("two_tokens") and len(supply_values(row)) != 2:
                    continue
                value = candidate(row, config)
                if value:
                    row["amount"] = value
                    changed += 1
            if not changed:
                continue
            after = compare_table(aggregate[meta["gtKey"]]["tableRows"], new_rows)
            gain, regression, spurious = measure(before, after)
            m = result[config]
            m["docsChanged"] += 1
            m["cellsChanged"] += changed
            m["gain"] += gain
            m["regression"] += regression
            m["spuriousDelta"] += spurious
        documents += 1
    for m in result.values():
        m["net"] = m["gain"] - m["regression"]
        m["gainPerChange"] = round(m["gain"] / m["cellsChanged"], 4) if m["cellsChanged"] else 0
    payload = {"basis": "066 thin", "documents": documents, "variants": result}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
