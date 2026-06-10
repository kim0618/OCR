"""REVIEW-SIGNAL Phase A: post-hoc per-field confidence reconstruction.

document_fields carries plain strings, so per-character OCR confidence is lost
during extraction. This module matches final field values back against
ocr_lines_raw (text + confidence) to recover a per-field confidence without
modifying the extractor itself (additive-only).

Confidence semantics in the output:
- float 0~1 : best OCR-line confidence supporting this exact value
- None      : value not traceable to any OCR line (derived/reconstructed,
              e.g. checksum-based reconstruction) — "no signal", not "bad"
"""
from __future__ import annotations

from typing import Any

# document_fields keys that are extractor metadata, not OCR-derived values.
_META_KEYS = {
    "tableDetected", "rowCount", "firstRowPreview",
    "tableMeta", "tableRows", "items", "extract_debug",
}

# Below this normalized length a substring match is too ambiguous
# (e.g. quantity "1" appears in almost every line) — require token-exact.
_MIN_SUBSTRING_LEN = 4


def _norm(text: str) -> str:
    return "".join(ch for ch in (text or "") if ch not in " ,\t ").lower()


def _index_lines(ocr_lines_raw: list[tuple]) -> list[tuple[str, set[str], float]]:
    indexed = []
    for raw in ocr_lines_raw:
        try:
            _, text, confidence = raw
        except (TypeError, ValueError):
            continue
        text = (text or "").strip()
        if not text:
            continue
        norm_text = _norm(text)
        tokens = {_norm(t) for t in text.split()} - {""}
        indexed.append((norm_text, tokens, float(confidence)))
    return indexed


def _digit_bounded_in(needle: str, haystack: str) -> bool:
    """True if needle occurs in haystack NOT flanked by extra digits.

    Prevents numeric false positives after comma-stripping: "1,809,875" must
    not match inside "18,098,750" ("1809875" is a prefix of "18098750").
    """
    start = haystack.find(needle)
    while start != -1:
        before = haystack[start - 1] if start > 0 else ""
        after_idx = start + len(needle)
        after = haystack[after_idx] if after_idx < len(haystack) else ""
        if not before.isdigit() and not after.isdigit():
            return True
        start = haystack.find(needle, start + 1)
    return False


def _substring_hit(needle: str, norm_text: str) -> bool:
    if needle.isdigit():
        return _digit_bounded_in(needle, norm_text)
    return needle in norm_text


def _match_value(value: str, lines: list[tuple[str, set[str], float]]) -> float | None:
    n = _norm(value)
    if not n:
        return None
    # 1) token-exact: the value is a whole OCR token somewhere.
    #    Multiple hits with the same text corroborate the value → take max.
    token_hits = [conf for _, tokens, conf in lines if n in tokens]
    if token_hits:
        return max(token_hits)
    # 2) substring of a single line (long values only, to avoid noise hits).
    if len(n) >= _MIN_SUBSTRING_LEN:
        sub_hits = [conf for norm_text, _, conf in lines if _substring_hit(n, norm_text)]
        if sub_hits:
            return max(sub_hits)
    # 3) value assembled from multiple lines (addresses, company names):
    #    weakest-link min over per-token best confidences, with coverage gate.
    value_tokens = [_norm(t) for t in (value or "").split()]
    value_tokens = [t for t in value_tokens if len(t) >= 2]
    if len(value_tokens) >= 2:
        per_token = []
        for tok in value_tokens:
            hits = [
                conf for norm_text, tokens, conf in lines
                if tok in tokens or (len(tok) >= _MIN_SUBSTRING_LEN and _substring_hit(tok, norm_text))
            ]
            if hits:
                per_token.append(max(hits))
        if per_token and len(per_token) / len(value_tokens) >= 0.6:
            return min(per_token)
    return None


def build_field_confidence(
    document_fields: dict[str, Any],
    ocr_lines_raw: list[tuple],
) -> dict[str, Any]:
    """Return {"fields": {name: conf|None}, "tableRows": [{col: conf|None}], "method": ...}."""
    lines = _index_lines(ocr_lines_raw)
    fields: dict[str, float | None] = {}
    for key, value in (document_fields or {}).items():
        if key in _META_KEYS or not isinstance(value, str) or not value.strip():
            continue
        conf = _match_value(value, lines)
        fields[key] = round(conf, 4) if conf is not None else None

    table_rows: list[dict[str, float | None]] = []
    raw_rows = (document_fields or {}).get("tableRows")
    if isinstance(raw_rows, list):
        for row in raw_rows:
            row_conf: dict[str, float | None] = {}
            if isinstance(row, dict):
                for col, cell in row.items():
                    if not isinstance(cell, str) or not cell.strip():
                        continue
                    conf = _match_value(cell, lines)
                    row_conf[col] = round(conf, 4) if conf is not None else None
            table_rows.append(row_conf)

    return {
        "fields": fields,
        "tableRows": table_rows,
        "method": "posthoc_line_match.v1",
    }
