from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch

import finetune_run_summary
import finetune_report_by_type
import metrics
import run_history


class RunHistoryExtendedTest(unittest.TestCase):
    def test_cost_snapshot_and_unknown_duration_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "history.jsonl")
            out = os.path.join(tmp, "history.html")
            with patch.object(run_history, "LOG", log), patch.object(run_history, "OUT", out), \
                    patch.dict(os.environ, {"AWS_EC2_HOURLY_USD": "2.0"}, clear=False):
                run_history.record("eval", ts="timed", images=100, elapsedSec=1800,
                                   itemName=75.0, itemNameMatch=75, itemNameScored=100,
                                   itemNameMaster=80.0, itemNameMasterMatch=80,
                                   itemNameMasterScored=100)
                run_history.record("eval", ts="legacy", images=900)
                run_history.record("eval", ts="replay", runType="snapshot-replay",
                                   images=500, itemName=70.0, itemNameMaster=80.0,
                                   learnA=70.9, learnAMatch=71, learnAScored=100,
                                   learnB=71.7, learnBMatch=72, learnBScored=100)
                rows = run_history._load()
                self.assertEqual(rows[0]["estimatedCostUsd"], 1.0)
                with open(out, encoding="utf-8") as fh:
                    rendered = fh.read()
                self.assertIn("Base", rendered)
                self.assertIn("Master", rendered)
                self.assertIn("80.0%", rendered)
                self.assertIn("스냅샷 재평가", rendered)
                self.assertIn("AWS OCR 누계 (2 run)", rendered)
                self.assertIn("Learn A 품명", rendered)
                self.assertIn("Learn B 품명", rendered)
                self.assertIn("71.7%", rendered)
                self.assertIn("기록 없음", rendered)
                self.assertIn("시간 기록 100장 기준", rendered)
                self.assertNotIn("2,000 장/시간", rendered)  # must not mix untimed 900 images
                self.assertIn("200장/h", rendered)
                self.assertNotIn("<th>학습 기준</th>", rendered)
                self.assertNotIn("<th>기준 대비</th>", rendered)

    def test_training_log_extracts_completed_and_best_epoch(self):
        text = """
epoch: [1/4], global_step: 10
best metric, acc: 0.51
epoch: [2/4], global_step: 20
best metric, acc: 0.638
epoch: [3/4], global_step: 30
"""
        parsed = finetune_run_summary.parse_training_log(text)
        self.assertEqual(parsed["epochsCompleted"], 3)
        self.assertEqual(parsed["bestEpoch"], 2)
        self.assertEqual(parsed["bestAcc"], 0.638)

    def test_criteria_describes_columns_and_numeric_anchor(self):
        criteria = finetune_run_summary.describe_criteria({"policy": {
            "columns": ["itemName"], "hangulMin": 2,
            "minMatch": 0.7, "numberAnchorRatio": 0.3, "rawOnly": True,
        }})
        self.assertIn("품명 중심", criteria)
        self.assertIn("GT 일치도 0.7+", criteria)
        self.assertIn("숫자 보존 앵커 0.3", criteria)

    def test_best_acc_is_rendered_to_three_decimal_places(self):
        self.assertEqual(run_history._best_acc("0.532193910694478"), "0.532")
        self.assertEqual(run_history._best_acc(0.638), "0.638")
        self.assertEqual(run_history._best_acc(None), "-")

    def test_type_uses_column_metadata_not_every_hangul_as_item_name(self):
        self.assertEqual(finetune_report_by_type._type("가나다", {"column": "itemName"}), "품명")
        self.assertEqual(finetune_report_by_type._type("주식회사", {"column": "supplierCompany"}),
                         "한글(기타)")
        self.assertEqual(finetune_report_by_type._type("1,234", {"column": "amount"}), "숫자")


class MetricsPerCellFieldTest(unittest.TestCase):
    def test_item_name_is_aggregated_by_column(self):
        sample = {
            "sourceFile": "a.jpg", "extractionPath": "free", "profile": "thin",
            "fields": {
                "counts": {"scored": 0, "match": 0, "mismatch": 0,
                           "ext_missing": 0, "gt_empty": 0, "spurious": 0},
                "fieldAccuracy": None, "coverage": {}, "perField": {},
            },
            "table": {
                "cellCounts": {"scored": 2, "match": 1, "mismatch": 1,
                               "ext_missing": 0, "gt_empty": 0, "spurious": 0},
                "cellAccuracy": 0.5, "rowCountGt": 1,
                "rows": [{"cells": {
                    "itemName": {"status": "match", "spurious": False},
                    "amount": {"status": "mismatch", "spurious": False},
                }}],
            },
            "buckets": {"bucketTally": {"recognition": 0, "structure": 0,
                                           "layout": 0, "preprocessing": 0}},
        }
        with tempfile.TemporaryDirectory() as tmp:
            compare = os.path.join(tmp, "compare")
            os.makedirs(compare)
            with open(os.path.join(compare, "a.json"), "w", encoding="utf-8") as fh:
                json.dump(sample, fh)
            with open(os.path.join(tmp, "run_meta.json"), "w", encoding="utf-8") as fh:
                json.dump({"testset": "invoice_thin"}, fh)
            with patch("build_manifest.build_manifest", return_value={"samples": []}), \
                    patch.object(metrics, "_append_timeseries"), \
                    patch.object(metrics.C, "RUNS_DIR", tmp):
                result = metrics.compute_metrics(tmp)
            item = result["perCellField"]["itemName"]
            self.assertEqual(item["scored"], 1)
            self.assertEqual(item["match"], 1)
            self.assertEqual(item["accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
