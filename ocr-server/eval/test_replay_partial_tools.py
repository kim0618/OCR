import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import replay_compare
import replay_partial_diff


def _sidecar(source: str, field_status: str, cell_status: str) -> dict:
    return {
        "sourceFile": source,
        "fields": {"perField": {"supplierBizNumber": {"status": field_status}}},
        "table": {"rows": [{"cells": {
            "itemName": {"status": cell_status},
            "itemNameLearnA": {"status": "match"},
        }}]},
    }


class ReplayPartialToolsTest(unittest.TestCase):
    def test_load_only_sources_accepts_comments_bom_and_sidecar_names(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "targets.txt"
            path.write_text(
                "\ufeff# target set\na.jpg\na.jpg.json\n\n", encoding="utf-8"
            )
            self.assertEqual(
                replay_compare._load_only_sources(str(path)), {"a.jpg"}
            )

    def test_default_testset_is_inferred_from_run_meta(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "run_meta.json"
            path.write_text(
                json.dumps({"testset": "invoice_replay"}), encoding="utf-8"
            )
            self.assertEqual(
                replay_compare._resolve_testset(temp, None), "invoice_replay"
            )
            self.assertEqual(
                replay_compare._resolve_testset(temp, "invoice_thin"),
                "invoice_thin",
            )

    def test_partial_diff_compares_only_candidate_documents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / "baseline"
            candidate = root / "candidate"
            baseline.mkdir()
            candidate.mkdir()
            (baseline / "a.jpg.json").write_text(
                json.dumps(_sidecar("a.jpg", "match", "mismatch")),
                encoding="utf-8",
            )
            (baseline / "unselected.jpg.json").write_text(
                json.dumps(_sidecar("unselected.jpg", "mismatch", "mismatch")),
                encoding="utf-8",
            )
            (candidate / "a.jpg.json").write_text(
                json.dumps(_sidecar("a.jpg", "match", "match")), encoding="utf-8"
            )

            output = io.StringIO()
            with redirect_stdout(output):
                result = replay_partial_diff.compare(
                    str(baseline), str(candidate)
                )
            self.assertEqual(result, 0)
            text = output.getvalue()
            self.assertIn("1 same documents", text)
            self.assertIn("cell:itemName", text)
            self.assertIn("+100.000pp", text)
            # Measurement columns are displayed but excluded from CELL TOTAL.
            self.assertIn("CELL TOTAL", text)
            self.assertIn("0.000% (0/1)", text)


if __name__ == "__main__":
    unittest.main()
