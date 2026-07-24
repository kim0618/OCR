from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import Mock, patch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from extractors.invoice_statement_free import (
    _synth_relaxed_name_line_ok,
    adopt_missing_item_names,
    synthesize_missing_rows,
)


def _line(x1: float, x2: float, text: str) -> tuple[list[list[float]], str, float]:
    return (
        [[x1, 100.0], [x2, 100.0], [x2, 120.0], [x1, 120.0]],
        text,
        0.99,
    )


class ItemNameSynthesisTests(unittest.TestCase):
    def test_relaxed_master_line_can_fill_existing_empty_name_row(self) -> None:
        matcher = Mock()
        matcher.top_candidates.return_value = [(0.71, 1)]
        rows = [{"itemName": "", "amount": "12,345"}]
        ocr = [
            _line(100, 350, "AKLIEF CREAM 30 G"),
            _line(700, 820, "12,345"),
        ]

        with patch("extractors.master_match.get_matcher", return_value=matcher):
            result, debug = adopt_missing_item_names(
                rows, ocr, allow_relaxed_master=True
            )

        self.assertEqual(debug["adopted"], 1)
        self.assertEqual(result[0]["itemName"], "AKLIEF CREAM 30 G")

    def test_master_confirmed_english_name_can_synthesize(self) -> None:
        matcher = Mock()
        matcher.top_candidates.return_value = [(0.71, 1)]
        rows = [{"itemName": "기존품목정", "amount": "9,999"}]
        ocr = [
            _line(100, 350, "AKLIEF CREAM 30 G (1)"),
            _line(700, 820, "12,345"),
        ]

        with patch("extractors.master_match.get_matcher", return_value=matcher):
            result, debug = synthesize_missing_rows(rows, ocr)

        self.assertEqual(debug["synthesized"], 1)
        self.assertEqual(result[-1]["itemName"], "AKLIEF CREAM 30 G (1)")
        self.assertEqual(result[-1]["amount"], "12,345")

    def test_relaxed_name_requires_strong_master_score(self) -> None:
        matcher = Mock()
        matcher.top_candidates.return_value = [(0.69, 1)]
        rows = [{"itemName": "기존품목정", "amount": "9,999"}]
        ocr = [
            _line(100, 350, "AKLIEF CREAM 30 G (1)"),
            _line(700, 820, "12,345"),
        ]

        with patch("extractors.master_match.get_matcher", return_value=matcher):
            result, debug = synthesize_missing_rows(rows, ocr)

        self.assertEqual(debug["synthesized"], 0)
        self.assertEqual(len(result), 1)

    def test_relaxed_gate_rejects_non_name_numeric_text(self) -> None:
        self.assertFalse(_synth_relaxed_name_line_ok("12345 67890"))

    def test_rightmost_money_candidate_can_be_selected(self) -> None:
        matcher = Mock()
        matcher.top_candidates.return_value = [(0.71, 1)]
        rows = [{"itemName": "기존품명", "amount": "9,999"}]
        ocr = [
            _line(100, 350, "AKLIEF CREAM 30 G (1)"),
            _line(550, 650, "12,345"),
            _line(700, 820, "246,900"),
        ]

        with patch("extractors.master_match.get_matcher", return_value=matcher):
            result, debug = synthesize_missing_rows(
                rows, ocr, prefer_rightmost_money=True
            )

        self.assertEqual(debug["synthesized"], 1)
        self.assertEqual(result[-1]["amount"], "246,900")

    def test_unique_arithmetic_triple_fills_the_whole_synthesized_row(self) -> None:
        matcher = Mock()
        matcher.top_candidates.return_value = [(0.71, 1)]
        rows = [{"itemName": "湲곗〈?덈챸", "amount": "9,999"}]
        ocr = [
            _line(100, 350, "AKLIEF CREAM 30 G (1)"),
            _line(450, 500, "5"),
            _line(550, 650, "1,000"),
            _line(700, 820, "5,000"),
        ]

        with patch("extractors.master_match.get_matcher", return_value=matcher):
            result, debug = synthesize_missing_rows(
                rows, ocr, prefer_arithmetic_triple=True
            )

        self.assertEqual(debug["synthesized"], 1)
        self.assertEqual(result[-1]["quantity"], "5")
        self.assertEqual(result[-1]["unitPrice"], "1000")
        self.assertEqual(result[-1]["amount"], "5000")

    def test_arithmetic_triple_merges_into_unique_empty_name_row(self) -> None:
        matcher = Mock()
        matcher.top_candidates.return_value = [(0.71, 1)]
        rows = [{
            "itemName": "",
            "spec": "30T",
            "quantity": "",
            "unitPrice": "23,355",
            "amount": "467,100",
            "manufacturingNo": "23003",
            "expiryDate": "2026.08.20",
        }]
        ocr = [
            _line(100, 350, "CLAYCIN TABLET 30 T"),
            _line(450, 500, "20"),
            _line(550, 650, "23,355"),
            _line(700, 820, "467,100"),
        ]

        with patch("extractors.master_match.get_matcher", return_value=matcher):
            result, debug = synthesize_missing_rows(
                rows, ocr, prefer_arithmetic_triple=True
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(debug["merged"], 1)
        self.assertEqual(result[0]["itemName"], "CLAYCIN TABLET 30 T")
        self.assertEqual(result[0]["manufacturingNo"], "23003")
        self.assertEqual(result[0]["expiryDate"], "2026.08.20")


if __name__ == "__main__":
    unittest.main()
