"""Read-only 066 thin analysis for large amount-column parser levers.

Uses frozen samples/snapshots only.  It classifies the baseline amount errors,
then simulates geometry/raw-row based amount remapping in memory.  It does not
call or modify the production parser.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path


SERVER = Path(__file__).resolve().parents[1]
EVAL = SERVER / "eval"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(EVAL))

import normalize as N  # noqa: E402
from build_manifest import build_manifest  # noqa: E402
from compare_table import compare_table  # noqa: E402
from extractors.invoice_statement import _group_rows, _line_from_raw  # noqa: E402
from gt_loader import load_gt_aggregate  # noqa: E402


RUN_DIR = EVAL / "runs" / "066_20260709_122046" / "thin"
OUT = SERVER / "tmp" / "analyze_amount_big_levers_066.result.json"
NUMERIC_RE = re.compile(r"^[\s()\-+\u20a9]*\d[\d,.\s]*$")
TOKEN_RE = re.compile(r"[0-9A-Za-z\uac00-\ud7a3]{2,}")
FOOTER_RE = re.compile(
    r"(?:\ud569\s*\uacc4|\ucd1d\s*\uacc4|\uacf5\s*\uae09\s*\uac00|"
    r"\ubd80\s*\uac00\s*\uc138|\uccad\s*\uad6c\s*\uae08\s*\uc561|VAT)", re.I
)


def compact(value: object) -> str:
    return re.sub(r"[^0-9A-Za-z\uac00-\ud7a3]", "", str(value or "")).lower()


def norm_money(value: object) -> str:
    return N.norm_amount(str(value or ""))


def row_text(group: list) -> str:
    return " ".join(str(line.text or "").strip() for line in sorted(group, key=lambda x: x.x))


def numeric_value(text: object) -> str:
    value = str(text or "").strip()
    if not NUMERIC_RE.fullmatch(value):
        return ""
    digits = re.sub(r"\D", "", value)
    if not digits or len(digits) > 12:
        return ""
    # Exclude dates, phone/business numbers, and tiny ordinal-like values.
    if re.fullmatch(r"(?:19|20)\d{6}", digits) or len(digits) < 3:
        return ""
    return value.replace(".", ",")


def raw_tokens(value: object) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(str(value or "")) if len(token) >= 2}


def match_score(raw_text: str, group_text: str) -> float:
    raw_c, group_c = compact(raw_text), compact(group_text)
    if not raw_c or not group_c:
        return 0.0
    seq = SequenceMatcher(None, raw_c, group_c).ratio()
    rt, gt = raw_tokens(raw_text), raw_tokens(group_text)
    overlap = len(rt & gt) / max(1, len(rt))
    containment = min(len(raw_c), len(group_c)) / max(len(raw_c), len(group_c)) if raw_c in group_c or group_c in raw_c else 0.0
    return 0.45 * seq + 0.45 * overlap + 0.10 * containment


def build_geometry(raw: list) -> tuple[list, float]:
    lines = [line for item in raw if (line := _line_from_raw(item))]
    groups = _group_rows(lines, tolerance_factor=0.62) if lines else []
    page_w = max((line.x + line.w for line in lines), default=0.0)
    return groups, page_w


def map_rows(rows: list[dict], groups: list) -> list[dict | None]:
    """One-to-one monotonic-ish rawText -> OCR visual-row mapping."""
    candidates = []
    for ri, row in enumerate(rows):
        raw = str(row.get("_rawText") or "")
        for gi, group in enumerate(groups):
            text = row_text(group)
            score = match_score(raw, text)
            if score >= 0.48:
                candidates.append((score, ri, gi, text))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    used_rows, used_groups = set(), set()
    accepted_pairs: list[tuple[int, int]] = []
    mapped: list[dict | None] = [None] * len(rows)
    for score, ri, gi, text in candidates:
        if ri in used_rows or gi in used_groups:
            continue
        # A row map must be locally consistent with already accepted row order.
        if any((rj < ri and gj > gi) or (rj > ri and gj < gi) for rj, gj in accepted_pairs):
            continue
        group = groups[gi]
        mapped[ri] = {"group": group, "groupIndex": gi, "score": score, "text": text}
        used_rows.add(ri)
        used_groups.add(gi)
        accepted_pairs.append((ri, gi))
    return mapped


def amount_from_group(group: list, page_w: float, x_floor: float | None) -> tuple[str, dict] | None:
    candidates = []
    for line in group:
        value = numeric_value(line.text)
        if not value:
            continue
        right = line.x + line.w
        if x_floor is not None and line.cx < x_floor:
            continue
        candidates.append((right, line.cx, value, line.text))
    if not candidates:
        return None
    right, cx, value, raw = max(candidates)
    # Without a learned amount band, require the candidate to be in the right 28%.
    if x_floor is None and page_w and cx < page_w * 0.72:
        return None
    return value, {"right": right, "cx": cx, "raw": raw}


def learn_amount_x(rows: list[dict], mapped: list[dict | None], page_w: float) -> float | None:
    """Learn the amount column from already correct row amounts in this document."""
    xs = []
    for row, item in zip(rows, mapped):
        current = norm_money(row.get("amount"))
        if not current or not item:
            continue
        for line in item["group"]:
            if norm_money(line.text) == current:
                xs.append(line.cx)
    if not xs:
        return None
    xs.sort()
    med = xs[len(xs) // 2]
    if page_w and med < page_w * 0.64:
        return None
    return med - page_w * 0.075


def apply_variant(rows: list[dict], raw: list, variant: str) -> tuple[list[dict], list[dict], dict]:
    groups, page_w = build_geometry(raw)
    mapped = map_rows(rows, groups)
    x_floor = learn_amount_x(rows, mapped, page_w)
    out = copy.deepcopy(rows)
    changes = []
    for index, (row, item) in enumerate(zip(out, mapped)):
        if not item or item["score"] < (0.66 if variant == "strict" else 0.54):
            continue
        learned = x_floor is not None
        found = amount_from_group(item["group"], page_w, x_floor)
        if not found:
            continue
        value, meta = found
        current = str(row.get("amount") or "").strip()
        if norm_money(current) == norm_money(value):
            continue
        blank_only = variant in {"strict", "blank"}
        if blank_only and current:
            continue
        if variant == "strict" and not learned:
            continue
        row["amount"] = value
        changes.append({
            "row": index + 1, "before": current, "after": value,
            "score": round(item["score"], 4), "learnedX": learned,
            "source": str(row.get("_source") or ""), **meta,
        })
    return out, changes, {
        "mappedRows": sum(item is not None for item in mapped),
        "learnedAmountX": x_floor is not None,
    }


def amount_status(table: dict) -> dict[str, dict]:
    out = {}
    for row in table.get("rows") or []:
        cell = (row.get("cells") or {}).get("amount")
        if cell:
            out[str(row.get("rowIndex"))] = cell
    return out


def delta(before: dict, after: dict) -> dict:
    bs, ass = amount_status(before), amount_status(after)
    keys = set(bs) | set(ass)
    gain = sum(bs.get(k, {}).get("status") != "match" and ass.get(k, {}).get("status") == "match" for k in keys)
    regression = sum(bs.get(k, {}).get("status") == "match" and ass.get(k, {}).get("status") != "match" for k in keys)
    b_sp = sum(bool(cell.get("spurious")) for cell in bs.values())
    a_sp = sum(bool(cell.get("spurious")) for cell in ass.values())
    return {"gain": gain, "regression": regression, "spuriousDelta": a_sp - b_sp}


def classify_failures(table: dict, full_text: str, ext_rows: list[dict], counters: dict) -> None:
    statuses = amount_status(table)
    doc_ext_amounts = [norm_money(row.get("amount")) for row in ext_rows]
    full_digits = re.sub(r"\D", "", full_text or "")
    for key, cell in statuses.items():
        status = cell.get("status")
        if status not in {"ext_missing", "mismatch"}:
            continue
        gt = str(cell.get("gt") or "")
        gt_norm = norm_money(gt)
        digits = re.sub(r"\D", "", gt)
        readable = bool(gt_norm and (gt_norm in {norm_money(x) for x in re.findall(r"\d[\d,.]+", full_text or "")} or (len(digits) >= 3 and digits in full_digits)))
        counters["ocr"]["readable" if readable else "garbled_or_absent"] += 1
        if status == "ext_missing":
            kind = "missing"
        else:
            row_pos = int(key) - 1 if key.isdigit() else -1
            ext_row = ext_rows[row_pos] if 0 <= row_pos < len(ext_rows) else {}
            other_cells = [norm_money(ext_row.get(name)) for name in ("quantity", "unitPrice", "spec", "manufacturingNo")]
            if gt_norm and gt_norm in other_cells:
                kind = "column_misplacement"
            elif gt_norm and gt_norm in doc_ext_amounts and norm_money(cell.get("ext")) != gt_norm:
                kind = "row_shift"
            else:
                kind = "wrongpick"
        counters["type"][kind] += 1
        counters["readable_type"][kind if readable else "not_readable"] += 1


def main() -> None:
    manifest = build_manifest("invoice_thin")
    sample_by_source = {item["sourceFile"]: item for item in manifest["samples"]}
    gt = load_gt_aggregate(str(EVAL / manifest["gtAggregate"]), profile="thin")
    result = {
        "basis": "066 thin frozen samples + snapshots",
        "documents": 0,
        "baseline": {"amount": Counter(), "failureTaxonomy": {}},
        "variants": {},
        "examples": defaultdict(list),
    }
    taxonomy = {"ocr": Counter(), "type": Counter(), "readable_type": Counter()}
    variants = {
        name: {"docsChanged": 0, "cellsChanged": 0, "gain": 0, "regression": 0, "spuriousDelta": 0,
               "learnedXDocs": 0, "mappedRows": 0, "bySource": Counter()}
        for name in ("strict", "blank", "overwrite")
    }
    for snap_path in sorted((RUN_DIR / "snapshots").glob("*.json")):
        source = snap_path.name[:-5]
        sample_meta = sample_by_source.get(source)
        sample_path = RUN_DIR / "samples" / snap_path.name
        if not sample_meta or not sample_path.exists():
            continue
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        rows = (sample.get("documentFields") or {}).get("tableRows") or []
        gt_rows = gt[sample_meta["gtKey"]]["tableRows"]
        before = compare_table(gt_rows, rows)
        result["documents"] += 1
        for status in amount_status(before).values():
            result["baseline"]["amount"][str(status.get("status"))] += 1
        classify_failures(before, str(snap.get("full_text") or ""), rows, taxonomy)

        raw = snap.get("ocr_lines_raw") or []
        for name, metrics in variants.items():
            new_rows, changes, debug = apply_variant(rows, raw, name)
            metrics["mappedRows"] += debug["mappedRows"]
            metrics["learnedXDocs"] += int(debug["learnedAmountX"])
            if not changes:
                continue
            after = compare_table(gt_rows, new_rows)
            d = delta(before, after)
            metrics["docsChanged"] += 1
            metrics["cellsChanged"] += len(changes)
            for key in ("gain", "regression", "spuriousDelta"):
                metrics[key] += d[key]
            for change in changes:
                metrics["bySource"][change["source"]] += 1
            if len(result["examples"][name]) < 25 and (d["gain"] or d["regression"] or d["spuriousDelta"]):
                result["examples"][name].append({"sourceFile": source, **d, "changes": changes[:8]})

    result["baseline"]["amount"] = dict(result["baseline"]["amount"])
    result["baseline"]["failureTaxonomy"] = {key: dict(value) for key, value in taxonomy.items()}
    for name, metrics in variants.items():
        metrics["bySource"] = dict(metrics["bySource"])
        metrics["net"] = metrics["gain"] - metrics["regression"]
        result["variants"][name] = metrics
    result["examples"] = dict(result["examples"])
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"documents": result["documents"], "baseline": result["baseline"], "variants": result["variants"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
