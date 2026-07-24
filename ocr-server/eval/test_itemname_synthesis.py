from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import Mock, patch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from extractors.invoice_statement_free import (
    _synth_relaxed_name_line_ok,
    synthesize_missing_rows,
)


def _line(x1: float, x2: float, text: str) -> tuple[list[list[float]], str, float]:
    return (
        [[x1, 100.0], [x2, 100.0], [x2, 120.0], [x1, 120.0]],
        text,
        0.99,
    )


class ItemNameSynthesisTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
