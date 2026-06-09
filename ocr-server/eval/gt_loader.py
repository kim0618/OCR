"""gt_loader — load a GT file into the harness's normalized comparison shape.

Knows ONLY the contract (contract.py / GT_CONTRACT.md). Works for rich draft GT
(today) and thin ETL GT (future, Phase 7) alike: optional rich keys are dropped,
never required.

load_gt(path) -> LoadedGT (dict-like), or raises GTLoadError on contract breach.
"""

from __future__ import annotations

import json
from typing import Any

import contract as C


class GTLoadError(ValueError):
    """Raised when a GT file cannot be loaded under the contract."""


def _flatten_fields(
    fields: list[dict[str, Any]], src: str
) -> tuple[dict[str, str], str, bool, dict[str, dict[str, Any]]]:
    """fields[] -> ({labelEn: value}, perSampleLabel, isRich, fieldMeta).

    Scores nothing here; just normalizes. Raises on duplicate labelEn collision
    or a missing per-sample field (exactly one of totalAmount/totalQuantity).
    fieldMeta carries rich-only signal (edited/fieldStatus/confidence) per label;
    empty for thin GT.
    """
    flat: dict[str, str] = {}
    meta: dict[str, dict[str, Any]] = {}
    is_rich = False
    for i, f in enumerate(fields):
        if not isinstance(f, dict) or "labelEn" not in f:
            raise GTLoadError(f"{src}: fields[{i}] missing labelEn / not an object")
        label = f["labelEn"]
        if label in flat:
            raise GTLoadError(f"{src}: duplicate labelEn '{label}' (flatten collision)")
        flat[label] = f.get("value", "")
        meta[label] = {
            k: f[k] for k in ("edited", "fieldStatus", "confidence") if k in f
        }
        if any(k in f for k in C.RICH_FIELD_KEYS):
            is_rich = True

    present_per_sample = [l for l in C.PER_SAMPLE if l in flat]
    if len(present_per_sample) != 1:
        raise GTLoadError(
            f"{src}: per-sample field must be exactly one of {list(C.PER_SAMPLE)}, "
            f"found {present_per_sample}"
        )
    return flat, present_per_sample[0], is_rich, meta


def _value_rows(rows: list[dict[str, Any]], src: str) -> list[dict[str, Any]]:
    """Keep only contract value keys per row; drop review-meta. Preserve order."""
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            raise GTLoadError(f"{src}: tableRows[{i}] not an object")
        if C.ROW_ALIGN_KEY not in r:
            raise GTLoadError(f"{src}: tableRows[{i}] missing '{C.ROW_ALIGN_KEY}'")
        out.append({k: r[k] for k in C.ROW_VALUE_KEYS if k in r})
    return out


def load_gt(path: str) -> dict[str, Any]:
    """Load + normalize one GT file. Raises GTLoadError on contract breach."""
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise GTLoadError(f"{path}: unreadable / invalid JSON: {exc}") from exc

    if d.get("schemaVersion") != C.SCHEMA_VERSION:
        raise GTLoadError(
            f"{path}: schemaVersion {d.get('schemaVersion')!r} != {C.SCHEMA_VERSION!r}"
        )

    source_file = d.get("sourceFile")
    if not source_file:
        raise GTLoadError(f"{path}: missing top-level sourceFile")

    nr = d.get("normalizedResult")
    if not isinstance(nr, dict):
        raise GTLoadError(f"{path}: normalizedResult missing / not an object")

    fields = nr.get("fields")
    if not isinstance(fields, list):
        raise GTLoadError(f"{path}: normalizedResult.fields missing / not a list")
    document_fields, per_sample_label, is_rich, field_meta = _flatten_fields(fields, source_file)

    missing_common = [k for k in C.COMMON_12 if k not in document_fields]
    if missing_common:
        raise GTLoadError(f"{source_file}: missing common-12 fields: {missing_common}")

    rows_raw = nr.get("tableRows")
    if not isinstance(rows_raw, list):
        raise GTLoadError(f"{source_file}: normalizedResult.tableRows missing / not a list")
    table_rows = _value_rows(rows_raw, source_file)

    excluded = d.get("excludedRows", [])
    if not isinstance(excluded, list):
        raise GTLoadError(f"{source_file}: excludedRows present but not a list")

    return {
        "sourceFile": source_file,
        "sampleId": d.get("sampleId"),
        "schemaVersion": d.get("schemaVersion"),
        "profile": "rich" if is_rich else "thin",
        "documentFields": document_fields,      # {labelEn: value}, 13 entries
        "fieldMeta": field_meta,                 # {labelEn: {edited, fieldStatus, confidence}}
        "perSampleField": per_sample_label,      # "totalAmount" | "totalQuantity"
        "tableRows": table_rows,                 # value keys only, order preserved
        "excludedRows": excluded,                # split out: never a "missing row"
        "_meta": {
            "fieldCount": len(document_fields),
            "rowCount": len(table_rows),
            "excludedRowCount": len(excluded),
            "gtPath": path,
        },
    }


if __name__ == "__main__":  # quick manual smoke
    import glob
    import os

    for p in sorted(glob.glob(os.path.join(C.GT_DIR, "*.json"))):
        try:
            g = load_gt(p)
            print(
                f"OK  {g['sourceFile']:<8} profile={g['profile']:<4} "
                f"fields={g['_meta']['fieldCount']} rows={g['_meta']['rowCount']} "
                f"perSample={g['perSampleField']}"
            )
        except GTLoadError as e:
            print(f"ERR {os.path.basename(p)}: {e}")
