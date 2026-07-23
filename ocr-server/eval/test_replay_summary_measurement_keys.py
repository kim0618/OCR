import json

import replay_summary


def test_kpi_excludes_learndata_measurement_columns():
    compare = {
        "table": {
            "rows": [{
                "cells": {
                    "itemName": {"gtNorm": "정답", "status": "match"},
                    "itemNameLearnA": {
                        "gtNorm": "정답", "status": "mismatch", "spurious": True,
                    },
                    "itemNameLearnB": {"gtNorm": "정답", "status": "match"},
                    "itemCodeLearnA": {"gtNorm": "001", "status": "match"},
                    "itemCodeLearnB": {"gtNorm": "001", "status": "mismatch"},
                }
            }]
        },
        "fields": {"perField": {}},
    }

    blobs = {"compare.json": json.dumps(compare)}
    kpi = replay_summary._kpi_from_blobs(
        blobs.get, ["compare.json"], "classify.json"
    )

    assert kpi is not None
    assert (kpi["cm"], kpi["cs"], kpi["spur"]) == (1, 1, 0)


def test_kpi_prefers_canonical_counts_including_missing_gt_rows():
    compare = {
        "table": {
            "cellCounts": {"scored": 3, "match": 2, "spurious": 1},
            # Deliberately incomplete row detail: a structurally missing row
            # is represented only in cellCounts.
            "rows": [{"cells": {"itemName": {
                "gtNorm": "정답", "status": "match", "spurious": False,
            }}}],
        },
        "fields": {
            "counts": {"scored": 2, "match": 1},
            "perField": {},
        },
    }
    blobs = {"compare.json": json.dumps(compare)}

    kpi = replay_summary._kpi_from_blobs(
        blobs.get, ["compare.json"], "classify.json"
    )

    assert kpi is not None
    assert (kpi["cm"], kpi["cs"], kpi["spur"]) == (2, 3, 1)
    assert (kpi["fm"], kpi["fs"]) == (1, 2)
