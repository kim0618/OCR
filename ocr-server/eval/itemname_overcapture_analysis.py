"""Evaluate conservative itemName tail-cleanup rules on replay comparisons.

This is an offline scorer.  It never changes replay output or production code.
Each candidate only sees values available in the extracted row; GT is used
solely to score whether the transformed itemName fixes or breaks that row.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from extractors.master_match import strip_duplicate_item_pack_tail


_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^0-9a-z가-힣]+", re.I)
_PACK_TOKEN_RE = re.compile(
    r"(?i)^\d+(?:[.,]\d+)?\s*(?:t|tab|정|c|cap|캡슐|ea|포|병|v|a|amp|ml|mg|g)$"
)
_PACK_FIND_RE = re.compile(
    r"(?i)(\d+(?:[.,]\d+)?)\s*(t|tab|정|c|cap|캡슐|ea|포|병|v|a|amp)"
)


def _norm(value: Any) -> str:
    return _PUNCT_RE.sub("", str(value or "").lower())


def _cell(row: dict[str, Any], name: str) -> dict[str, Any]:
    return (row.get("cells") or {}).get(name) or {}


def _remove_suffix(text: str, suffix: str, *, require_boundary: bool) -> str | None:
    text = str(text or "").strip()
    suffix = str(suffix or "").strip()
    if not text or not suffix:
        return None
    text_norm = _norm(text)
    suffix_norm = _norm(suffix)
    if len(suffix_norm) < 1 or not text_norm.endswith(suffix_norm):
        return None
    # Locate against compact tokens so punctuation differences do not matter.
    tokens = list(re.finditer(r"[0-9A-Za-z가-힣]+", text))
    consumed = ""
    start = len(text)
    for token in reversed(tokens):
        consumed = token.group(0) + consumed
        start = token.start()
        if _norm(consumed) == suffix_norm:
            break
        if len(_norm(consumed)) > len(suffix_norm):
            return None
    if _norm(consumed) != suffix_norm or start <= 0:
        return None
    if require_boundary and not text[start - 1].isspace():
        return None
    base = text[:start].rstrip(" \t,;/|·")
    return base if len(_norm(base)) >= 3 else None


def _spec_boundary(row: dict[str, Any]) -> str | None:
    return _remove_suffix(
        _cell(row, "itemName").get("ext"),
        _cell(row, "spec").get("ext"),
        require_boundary=True,
    )


def _spec_glued(row: dict[str, Any]) -> str | None:
    return _remove_suffix(
        _cell(row, "itemName").get("ext"),
        _cell(row, "spec").get("ext"),
        require_boundary=False,
    )


def _pack_boundary(row: dict[str, Any]) -> str | None:
    name = str(_cell(row, "itemName").get("ext") or "").strip()
    match = re.search(r"(?P<base>.+\S)\s+(?P<tail>\S+)\s*$", name)
    if not match or not _PACK_TOKEN_RE.fullmatch(match.group("tail")):
        return None
    base = match.group("base").strip()
    return base if len(_norm(base)) >= 3 else None


def _spec_pack_boundary(row: dict[str, Any]) -> str | None:
    spec = str(_cell(row, "spec").get("ext") or "").strip()
    if not _PACK_TOKEN_RE.fullmatch(spec):
        return None
    return _remove_suffix(
        _cell(row, "itemName").get("ext"), spec, require_boundary=True
    )


def _pack_family(unit: str) -> str:
    unit = unit.lower()
    if unit in {"t", "tab", "정"}:
        return "tablet"
    if unit in {"c", "cap", "캡슐"}:
        return "capsule"
    if unit in {"v", "a", "amp"}:
        return "container"
    return unit


def _duplicate_pack_boundary(row: dict[str, Any]) -> str | None:
    """Remove only a second copy of a pack count at the name tail.

    Examples: ``약품(30T) 30정`` and ``약품/100C 100캡슐``.  The first pack
    signal stays in the name, so suppliers whose GT intentionally includes
    pack size are preserved.
    """
    name = str(_cell(row, "itemName").get("ext") or "").strip()
    match = re.search(r"(?P<base>.+\S)\s+(?P<tail>\S+)\s*$", name)
    if not match:
        return None
    tail_match = _PACK_FIND_RE.fullmatch(match.group("tail"))
    if not tail_match:
        return None
    number = tail_match.group(1).replace(",", "").lstrip("0") or "0"
    family = _pack_family(tail_match.group(2))
    base = match.group("base").strip()
    for base_number, base_unit in _PACK_FIND_RE.findall(base):
        normalized_number = base_number.replace(",", "").lstrip("0") or "0"
        if normalized_number == number and _pack_family(base_unit) == family:
            return base if len(_norm(base)) >= 3 else None
    return None


def _balanced_parens(value: str) -> bool:
    depth = 0
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _duplicate_pack_balanced(row: dict[str, Any]) -> str | None:
    base = _duplicate_pack_boundary(row)
    return base if base is not None and _balanced_parens(base) else None


def _duplicate_pack_structured(row: dict[str, Any]) -> str | None:
    """Stricter duplicate-pack rule requiring structural pack notation."""
    base = _duplicate_pack_balanced(row)
    if base is None:
        return None
    matches = list(_PACK_FIND_RE.finditer(base))
    if not matches:
        return None
    match = matches[-1]
    prefix = base[:match.start()]
    suffix = base[match.end():]
    inside_parens = prefix.count("(") > prefix.count(")")
    slash_prefixed = bool(re.search(r"/\s*$", prefix))
    annotation_follows = bool(re.match(r"\s*\([^)]*\)\s*$", suffix))
    return base if inside_parens or slash_prefixed or annotation_follows else None


def _duplicate_numeric_token_boundary(row: dict[str, Any]) -> str | None:
    """Remove an exact repeated trailing numeric/unit token."""
    name = str(_cell(row, "itemName").get("ext") or "").strip()
    match = re.search(r"(?P<base>.+\S)\s+(?P<tail>\S+)\s*$", name)
    if not match or not re.search(r"\d", match.group("tail")):
        return None
    tail_norm = _norm(match.group("tail"))
    if len(tail_norm) < 2:
        return None
    base = match.group("base").strip()
    base_tokens = {_norm(token) for token in re.findall(r"\S+", base)}
    return base if tail_norm in base_tokens and len(_norm(base)) >= 3 else None


def _runtime_duplicate_pack(row: dict[str, Any]) -> str | None:
    before = str(_cell(row, "itemName").get("ext") or "")
    runtime_rows = [{"itemName": before}]
    strip_duplicate_item_pack_tail(runtime_rows)
    after = runtime_rows[0]["itemName"]
    return after if after != before else None


RULES: dict[str, Callable[[dict[str, Any]], str | None]] = {
    "spec_boundary": _spec_boundary,
    "spec_pack_boundary": _spec_pack_boundary,
    "pack_boundary": _pack_boundary,
    "spec_glued": _spec_glued,
    "duplicate_pack_boundary": _duplicate_pack_boundary,
    "duplicate_pack_balanced": _duplicate_pack_balanced,
    "duplicate_pack_structured": _duplicate_pack_structured,
    "runtime_duplicate_pack": _runtime_duplicate_pack,
    "duplicate_numeric_token_boundary": _duplicate_numeric_token_boundary,
}


def analyze(compare_dir: str) -> dict[str, Any]:
    scores = {
        name: {
            "triggered": 0,
            "gain": 0,
            "regress": 0,
            "stillWrong": 0,
            "unchangedCorrect": 0,
            "samplesGain": [],
            "samplesRegress": [],
        }
        for name in RULES
    }
    target_sources: dict[str, set[str]] = {name: set() for name in RULES}
    oracle_suffixes: Counter[str] = Counter()
    oracle_overcapture = 0
    files = sorted(Path(compare_dir).glob("*.json"))
    rows_seen = 0
    for path in files:
        with path.open(encoding="utf-8") as fh:
            doc = json.load(fh)
        for row in (doc.get("table") or {}).get("rows") or []:
            cell = _cell(row, "itemName")
            gt = str(cell.get("gt") or "")
            ext = str(cell.get("ext") or "")
            gt_norm = _norm(gt)
            ext_norm = _norm(ext)
            if not gt_norm:
                continue
            rows_seen += 1
            before_ok = ext_norm == gt_norm
            if (
                not before_ok
                and ext_norm.startswith(gt_norm)
                and len(ext_norm) > len(gt_norm)
            ):
                oracle_overcapture += 1
                oracle_suffixes[ext_norm[len(gt_norm):]] += 1
            for name, rule in RULES.items():
                after = rule(row)
                if after is None or _norm(after) == ext_norm:
                    continue
                score = scores[name]
                score["triggered"] += 1
                if doc.get("sourceFile"):
                    target_sources[name].add(str(doc["sourceFile"]))
                after_ok = _norm(after) == gt_norm
                sample = {
                    "sourceFile": doc.get("sourceFile"),
                    "rowIndex": row.get("rowIndex"),
                    "gt": gt,
                    "before": ext,
                    "after": after,
                    "spec": _cell(row, "spec").get("ext"),
                }
                if not before_ok and after_ok:
                    score["gain"] += 1
                    if len(score["samplesGain"]) < 20:
                        score["samplesGain"].append(sample)
                elif before_ok and not after_ok:
                    score["regress"] += 1
                    if len(score["samplesRegress"]) < 20:
                        score["samplesRegress"].append(sample)
                elif not before_ok:
                    score["stillWrong"] += 1
                else:
                    score["unchangedCorrect"] += 1
    for score in scores.values():
        score["net"] = score["gain"] - score["regress"]
    for name, score in scores.items():
        score["targetSources"] = sorted(target_sources[name])
    return {
        "compareDir": os.path.abspath(compare_dir),
        "documents": len(files),
        "itemNameRows": rows_seen,
        "oracleOvercapture": oracle_overcapture,
        "topOracleSuffixes": oracle_suffixes.most_common(50),
        "rules": scores,
    }


def render(results: list[dict[str, Any]]) -> str:
    lines = [
        "# itemName overcapture rule analysis",
        "",
        "GT는 채점에만 사용했고 각 후보는 추출된 동일 행의 값만 사용했다.",
        "",
        "| run | rule | triggered | gain | regress | net | still wrong |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        run = Path(result["compareDir"]).parent.name
        for name, score in result["rules"].items():
            lines.append(
                f"| {run} | {name} | {score['triggered']:,} | "
                f"{score['gain']:,} | {score['regress']:,} | "
                f"{score['net']:+,} | {score['stillWrong']:,} |"
            )
    lines.append("")
    for result in results:
        run = Path(result["compareDir"]).parent.name
        lines += [
            f"## {run}",
            "",
            f"- oracle overcapture: {result['oracleOvercapture']:,}",
            f"- itemName rows: {result['itemNameRows']:,}",
            "",
            "Top normalized tails: "
            + ", ".join(f"`{tail}` {count:,}" for tail, count in result["topOracleSuffixes"][:20]),
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="append", required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--md-out", required=True)
    ap.add_argument("--targets-out")
    ap.add_argument("--target-rule", default="duplicate_pack_structured")
    args = ap.parse_args()
    results = [analyze(path) for path in args.compare]
    payload = {"schemaVersion": "itemname-overcapture.v1", "runs": results}
    os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(args.md_out, "w", encoding="utf-8") as fh:
        fh.write(render(results))
    if args.targets_out:
        targets = sorted({
            source
            for result in results
            for source in result["rules"][args.target_rule]["targetSources"]
        })
        with open(args.targets_out, "w", encoding="utf-8") as fh:
            for source in targets:
                fh.write(source + "\n")
    print(render(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
