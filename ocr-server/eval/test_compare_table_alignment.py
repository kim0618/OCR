from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from compare_table import compare_table  # noqa: E402


class ContentAlignmentTests(unittest.TestCase):
    def test_named_row_wins_over_blank_row_with_matching_numbers(self) -> None:
        gt = [{
            "itemName": "몬카스트정 10mg 28TBL(ALU)",
            "quantity": "1",
            "amount": "87515",
        }]
        extracted = [
            {
                "rowIndex": "7",
                "itemName": "몬카스트정10mg 28TBL(ALU)",
                "quantity": "1",
                "amount": "37620",
            },
            {
                "rowIndex": "8",
                "itemName": "",
                "quantity": "1",
                "amount": "87515",
            },
        ]

        result = compare_table(gt, extracted, align="content")

        self.assertEqual(result["rows"][0]["cells"]["itemName"]["status"], "match")
        self.assertEqual(result["rows"][0]["cells"]["itemName"]["ext"],
                         "몬카스트정10mg 28TBL(ALU)")
        self.assertEqual(result["extOnlyRowIdx"], ["8"])

    def test_blank_name_can_still_align_by_exact_amount_and_quantity(self) -> None:
        gt = [{"itemName": "품명", "quantity": "2", "amount": "10000"}]
        extracted = [{"rowIndex": "1", "itemName": "", "quantity": "2", "amount": "10000"}]

        result = compare_table(gt, extracted, align="content")

        self.assertEqual(result["gtOnlyRowIdx"], [])
        self.assertEqual(result["rows"][0]["cells"]["itemName"]["status"], "ext_missing")


if __name__ == "__main__":
    unittest.main()
