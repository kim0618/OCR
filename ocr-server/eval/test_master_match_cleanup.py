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
    strip_master_annotations,
    strip_trailing_item_classification,
    strip_trailing_item_page_fraction,
)
from eval.normalize import normalize_cell  # noqa: E402


class MasterAnnotationOutputTests(unittest.TestCase):
    def test_strips_parenthetical_annotations_only_from_emitted_name(self):
        matcher = MasterMatcher(
            {
                "plain": {"nm": "로카탄플러스정", "bp1": 100},
                "bottle": {"nm": "로카탄플러스정(병)", "bp1": 100},
            }
        )

        matched = matcher.match("로카탄플러스정(병)")

        self.assertEqual(matched["itemCode"], "bottle")
        self.assertEqual(matched["itemNameMaster"], "로카탄플러스정")
        self.assertEqual(matcher._nms[matcher._cd2i["bottle"]], "로카탄플러스정(병)")

    def test_strips_multiple_annotations_and_keeps_non_parenthetical_text(self):
        self.assertEqual(
            strip_master_annotations("휴티렌정 (제약사품절) 10mg (병)"),
            "휴티렌정 10mg",
        )

    def test_keeps_original_when_name_contains_only_parenthetical_text(self):
        self.assertEqual(strip_master_annotations("(병)"), "(병)")

    def test_master_annotation_normalization_is_symmetric_and_scoped(self):
        self.assertEqual(
            normalize_cell("itemNameMaster", "로카탄플러스정(병)"),
            normalize_cell("itemNameMaster", "로카탄플러스정"),
        )
        self.assertNotEqual(
            normalize_cell("itemName", "로카탄플러스정(병)"),
            normalize_cell("itemName", "로카탄플러스정"),
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


class TrailingItemPageFractionTests(unittest.TestCase):
    def test_strips_only_whitespace_delimited_explicit_one_of_n(self):
        rows = [
            {"itemName": "약품정 10mg 1/2"},
            {"itemName": "약품정 10mg 1 / 12"},
            {"itemName": "복합정5/20mg"},
            {"itemName": "약품정 // 2"},
            {"itemName": "1/2"},
            {"itemName": "약품정 10mg 116"},
            {"itemName": "약품정 // 111"},
            {"itemName": "약품정 300"},
        ]

        output, debug = strip_trailing_item_page_fraction(rows)

        self.assertEqual(output[0]["itemName"], "약품정 10mg")
        self.assertEqual(output[1]["itemName"], "약품정 10mg")
        self.assertEqual(output[2]["itemName"], "복합정5/20mg")
        self.assertEqual(output[3]["itemName"], "약품정 // 2")
        self.assertEqual(output[4]["itemName"], "1/2")
        self.assertEqual(output[5]["itemName"], "약품정 10mg")
        self.assertEqual(output[6]["itemName"], "약품정 // 111")
        self.assertEqual(output[7]["itemName"], "약품정 300")
        self.assertEqual(debug["stripped"], 3)

    def test_runtime_learndata_can_use_cleaned_page_fraction_key(self):
        matcher = MasterMatcher(
            {"code-a": {"nm": "약품정 10mg", "bp1": 100}},
            learndata={"readings": {"약품정 10mg": [["code-a", 3]]}},
        )
        self.assertEqual(
            matcher.resolve_learndata_code("약품정 10mg 1/2"), "code-a"
        )
        self.assertEqual(
            matcher.resolve_learndata_code("약품정 10mg 116"), "code-a"
        )


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

    def test_accepts_lower_similarity_only_with_learndata_agreement(self):
        matcher = MasterMatcher(
            {
                "wrong": {"nm": "WrongDrug", "bp1": 100},
                "right": {"nm": "CorrectDrug", "bp1": 100},
            },
            {self.BIZNO: ["right"]},
            {"readings": {"CorrectDrug 10mg": [["right", 3]]}},
        )
        wrong_i = matcher._cd2i["wrong"]
        right_i = matcher._cd2i["right"]
        current = {"itemCode": "wrong", "itemNameMaster": "WrongDrug", "sim": 0.70}
        with patch.object(
            matcher, "top_candidates", return_value=[(0.70, wrong_i), (0.65, right_i)]
        ):
            reranked = matcher.itembuycust_strict_rerank(
                "CorrectDrug 10mg", self.BIZNO, current
            )

        self.assertIsNotNone(reranked)
        self.assertEqual(reranked["itemCode"], "right")
        self.assertTrue(reranked["learnAgreement"])

    def test_rejects_lower_similarity_without_learndata_agreement(self):
        matcher, wrong_i, right_i = self._matcher()
        current = {"itemCode": "wrong", "itemNameMaster": "WrongDrug", "sim": 0.70}
        with patch.object(
            matcher, "top_candidates", return_value=[(0.70, wrong_i), (0.65, right_i)]
        ):
            reranked = matcher.itembuycust_strict_rerank(
                "CorrectDrug 10mg", self.BIZNO, current
            )

        self.assertIsNone(reranked)

    def test_runtime_learndata_uses_count_then_exact_unit(self):
        matcher = MasterMatcher(
            {
                "major": {"nm": "Drug Major", "unit": "30T", "bp1": 100},
                "unit": {"nm": "Drug Unit", "unit": "100T", "bp1": 100},
            },
            None,
            {"readings": {"Printed Drug": [["major", 5], ["unit", 2]]}},
        )

        self.assertEqual(
            matcher.resolve_learndata_code("Printed Drug", spec=""), "major"
        )
        self.assertEqual(
            matcher.resolve_learndata_code("Printed Drug", spec="100T"), "unit"
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

    def test_preserves_stockout_guard_after_display_annotation_is_stripped(self):
        matcher = MasterMatcher(
            {
                "stockout": {"nm": "StatusDrug(제약사품절)", "bp1": 100},
                "history": {"nm": "StatusDrug", "bp1": 100},
            },
            {self.BIZNO: ["history"]},
        )
        stockout_i = matcher._cd2i["stockout"]
        history_i = matcher._cd2i["history"]
        current = matcher.match("StatusDrug(제약사품절)")
        self.assertEqual(current["itemNameMaster"], "StatusDrug")
        with patch.object(
            matcher, "top_candidates", return_value=[(1.0, history_i), (1.0, stockout_i)]
        ):
            self.assertIsNone(
                matcher.itembuycust_strict_rerank("StatusDrug", self.BIZNO, current)
            )


if __name__ == "__main__":
    unittest.main()
