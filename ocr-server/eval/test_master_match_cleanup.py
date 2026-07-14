from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

SERVER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SERVER)

from extractors.master_match import (  # noqa: E402
    MasterMatcher,
    fill_master_match,
    strip_trailing_item_classification,
)


class TrailingItemClassificationTests(unittest.TestCase):
    def test_strips_only_whitespace_delimited_final_marker(self):
        rows = [
            {"itemName": "삼진디아제팜정2mg-P100T/갑 전문", "amount": "1"},
            {"itemName": "시푸로겔3%-50g/1Tube/갑 일반", "amount": "2"},
            {"itemName": "전문", "amount": "3"},
            {"itemName": "Mago 250mg(일반)", "amount": "4"},
        ]

        output, debug = strip_trailing_item_classification(rows)

        self.assertIs(output, rows)
        self.assertEqual(output[0]["itemName"], "삼진디아제팜정2mg-P100T/갑")
        self.assertEqual(output[1]["itemName"], "시푸로겔3%-50g/1Tube/갑")
        self.assertEqual(output[2]["itemName"], "전문")
        self.assertEqual(output[3]["itemName"], "Mago 250mg(일반)")
        self.assertEqual(output[0]["amount"], "1")
        self.assertEqual(debug["stripped"], 2)


class StrictPurchaseHistoryRerankTests(unittest.TestCase):
    BIZNO = "1234567890"

    @staticmethod
    def _matcher(include_current: bool = False):
        history = ["right", "wrong"] if include_current else ["right"]
        matcher = MasterMatcher(
            {
                "wrong": {"nm": "WrongDrug", "bp1": 100},
                "right": {"nm": "CorrectDrug", "bp1": 100},
            },
            {StrictPurchaseHistoryRerankTests.BIZNO: history},
        )
        return matcher, matcher._cd2i["wrong"], matcher._cd2i["right"]

    def test_fill_replaces_only_with_strict_in_history_contained_candidate(self):
        matcher, wrong_i, right_i = self._matcher()
        rows = [{"itemName": "CorrectDrug 10mg", "unitPrice": "100"}]
        current = {"itemCode": "wrong", "itemNameMaster": "WrongDrug", "sim": 0.85}
        ranked = [(0.90, right_i), (0.85, wrong_i)]

        with patch.object(matcher, "match", return_value=current), patch.object(
            matcher, "top_candidates", return_value=ranked
        ):
            output, debug = fill_master_match(rows, matcher, self.BIZNO)

        self.assertEqual(output[0]["itemNameMaster"], "CorrectDrug")
        self.assertEqual(output[0]["itemCode"], "right")
        self.assertEqual(debug["ibcStrictReranked"], 1)

    def test_rejects_low_similarity_and_current_history_candidates(self):
        matcher, wrong_i, right_i = self._matcher()
        current = {"itemCode": "wrong", "itemNameMaster": "WrongDrug", "sim": 0.85}
        with patch.object(
            matcher, "top_candidates", return_value=[(0.85, wrong_i), (0.79, right_i)]
        ):
            self.assertIsNone(
                matcher.itembuycust_strict_rerank(
                    "CorrectDrug 10mg", self.BIZNO, current
                )
            )

        matcher, wrong_i, right_i = self._matcher(include_current=True)
        with patch.object(
            matcher, "top_candidates", return_value=[(0.90, right_i), (0.85, wrong_i)]
        ):
            self.assertIsNone(
                matcher.itembuycust_strict_rerank(
                    "CorrectDrug 10mg", self.BIZNO, current
                )
            )

    def test_rejects_candidate_not_explicitly_present_in_raw_name(self):
        matcher, wrong_i, right_i = self._matcher()
        current = {"itemCode": "wrong", "itemNameMaster": "WrongDrug", "sim": 0.85}
        with patch.object(
            matcher, "top_candidates", return_value=[(0.90, right_i), (0.85, wrong_i)]
        ):
            self.assertIsNone(
                matcher.itembuycust_strict_rerank(
                    "Unrelated OCR text", self.BIZNO, current
                )
            )

    def test_rejects_same_master_name_with_a_different_sku_code(self):
        matcher = MasterMatcher(
            {
                "outside": {"nm": "SameDrug", "bp1": 100},
                "history": {"nm": "SameDrug", "bp1": 100},
            },
            {self.BIZNO: ["history"]},
        )
        outside_i = matcher._cd2i["outside"]
        history_i = matcher._cd2i["history"]
        current = {"itemCode": "outside", "itemNameMaster": "SameDrug", "sim": 0.85}
        with patch.object(
            matcher, "top_candidates", return_value=[(0.90, history_i), (0.85, outside_i)]
        ):
            self.assertIsNone(
                matcher.itembuycust_strict_rerank("SameDrug", self.BIZNO, current)
            )

    def test_preserves_stockout_qualified_master_without_raw_replacement_evidence(self):
        matcher = MasterMatcher(
            {
                "stockout": {"nm": "StatusDrug(제약사품절)", "bp1": 100},
                "history": {"nm": "StatusDrug", "bp1": 100},
            },
            {self.BIZNO: ["history"]},
        )
        stockout_i = matcher._cd2i["stockout"]
        history_i = matcher._cd2i["history"]
        current = {
            "itemCode": "stockout",
            "itemNameMaster": "StatusDrug(제약사품절)",
            "sim": 1.0,
        }
        with patch.object(
            matcher, "top_candidates", return_value=[(1.0, history_i), (1.0, stockout_i)]
        ):
            self.assertIsNone(
                matcher.itembuycust_strict_rerank("StatusDrug", self.BIZNO, current)
            )


if __name__ == "__main__":
    unittest.main()
