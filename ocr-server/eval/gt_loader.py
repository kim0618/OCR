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
) -> tuple[dict[str, str], list[str], bool, dict[str, dict[str, Any]]]:
    """fields[] -> ({labelEn: value}, presentPerSample[], richSignal, fieldMeta).

    Scores nothing here; just normalizes. Raises only on a duplicate labelEn
    collision. The per-sample exactly-one invariant is NOT enforced here — it is
    rich-gated by load_gt (➋). fieldMeta carries rich-only signal
    (edited/fieldStatus/confidence) per label; empty for thin GT.
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
    return flat, present_per_sample, is_rich, meta


def _value_rows(rows: list[dict[str, Any]], src: str) -> list[dict[str, Any]]:
    """Keep the GT-provided value keys per row; drop review-meta. Preserve order.

    rowIndex is OPTIONAL (⓫): rich GT carries it (kept for the oracle alignment),
    thin GT has none (content-aligned in step 4). Value keys = whatever the GT
    provides minus review-meta (⓰), so thin war columns like manufacturingNo are
    not dropped while rich keeps exactly its 9 value keys.
    """
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            raise GTLoadError(f"{src}: tableRows[{i}] not an object")
        out.append({k: v for k, v in r.items() if k not in C.ROW_META_KEYS})
    return out


def load_gt(path: str, profile: str | None = None) -> dict[str, Any]:
    """Load + normalize one GT file. Raises GTLoadError on contract breach.

    `profile` ("rich"|"thin") is INJECTED by the caller from the testset profile
    (⓳'); content-inference is retired. When omitted (legacy call), the profile
    is inferred from rich-key presence and the checker flags the inconsistency.
    The bbox-derived rich signal is always exposed for that consistency check.
    """
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
    document_fields, present_per_sample, rich_signal, field_meta = _flatten_fields(fields, source_file)

    # Profile is injected from the testset (⓳'); fall back to the content signal
    # only for legacy calls. The two are cross-checked by the checker.
    resolved_profile = profile if profile in ("rich", "thin") else ("rich" if rich_signal else "thin")

    # COMMON_12 is hard-required for rich; thin opts out (A — scores gt.keys()).
    required = C.required_scalar_fields(resolved_profile)
    missing_common = [k for k in required if k not in document_fields]
    if missing_common:
        raise GTLoadError(f"{source_file}: missing required fields ({resolved_profile}): {missing_common}")

    # Per-sample exactly-one (➋) is rich-gated. thin may have 0 (e.g. totalQuantity
    # is rich-only) or 1; it is never an error there.
    if C.enforce_per_sample(resolved_profile) and len(present_per_sample) != 1:
        raise GTLoadError(
            f"{source_file}: per-sample field must be exactly one of "
            f"{list(C.PER_SAMPLE)}, found {present_per_sample}"
        )
    per_sample_label = present_per_sample[0] if present_per_sample else None

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
        "profile": resolved_profile,             # INJECTED (⓳'), not inferred
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
            "richSignal": rich_signal,           # bbox/edited present? → checker cross-checks vs injected profile
            "profileInjected": profile in ("rich", "thin"),
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
