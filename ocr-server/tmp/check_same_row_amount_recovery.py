"""Focused non-replay checks for post-join same-row amount recovery."""

from copy import deepcopy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractors.invoice_statement import recover_postjoin_same_row_amounts


def parser_row(**values):
    return {"_source": "invoice_statement_table_parser", **values}


original = [
    parser_row(amount="", supplyAmount="27,000 2,430.000", quantity="90"),
    parser_row(amount="495,000", supplyAmount="24,750 495,000", quantity="20"),
    parser_row(amount="", supplyAmount="12", quantity="1"),
]
rows = deepcopy(original)
result, debug = recover_postjoin_same_row_amounts(rows)
assert result[0]["amount"] == "2,430.000"
assert result[1]["amount"] == "495,000"
assert result[2]["amount"] == ""
assert result[0]["supplyAmount"] == original[0]["supplyAmount"]
assert result[0]["quantity"] == original[0]["quantity"]
assert debug["applied"] is True and debug["filledRows"] == [1]

mixed = [
    parser_row(amount="", supplyAmount="10,000 20,000"),
    {"_source": "invoice_statement_free_ha_appended", "amount": "", "supplyAmount": "30,000"},
]
mixed_before = deepcopy(mixed)
mixed_after, mixed_debug = recover_postjoin_same_row_amounts(mixed)
assert mixed_after == mixed_before
assert mixed_debug["applied"] is False
assert mixed_debug["reason"] == "mixed_or_non_table_parser_rows"

separate_columns = [
    parser_row(amount="2,359", supplyAmount="23,691"),
    parser_row(amount="", supplyAmount="208,245"),
]
separate_before = deepcopy(separate_columns)
separate_after, separate_debug = recover_postjoin_same_row_amounts(separate_columns)
assert separate_after == separate_before
assert separate_debug["reason"] == "existing_amount_proves_separate_supply_column"

too_many = [parser_row(amount="", supplyAmount="10,000") for _ in range(14)]
too_many_before = deepcopy(too_many)
too_many_after, too_many_debug = recover_postjoin_same_row_amounts(too_many)
assert too_many_after == too_many_before
assert too_many_debug["reason"] == "too_many_rows_for_stable_content_alignment"

print("same-row amount recovery focused checks: PASS")
