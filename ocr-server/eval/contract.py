"""Frozen GT contract constants + path resolution (single source of truth).

Imported by every phase (phase0 check, gt_loader, build_manifest, comparators,
checker) so the contract lives in exactly one place. See GT_CONTRACT.md for the
human-readable spec this encodes.
"""

from __future__ import annotations

import os
import sys

# Windows consoles default to cp949; force UTF-8 so report text never crashes.
try:  # pragma: no cover - environment dependent
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# --- paths (resolved relative to this file, so scripts run from anywhere) ----
HERE = os.path.dirname(os.path.abspath(__file__))
TESTSET_DIR = os.path.normpath(
    os.path.join(
        HERE, "..", "..", "mysuit-ocr", "public", "data", "testsets",
        "invoice_study",
    )
)
IMG_DIR = TESTSET_DIR
GT_DIR = os.path.join(TESTSET_DIR, "GT")
RUNS_DIR = os.path.join(HERE, "runs")
MANIFEST_PATH = os.path.join(HERE, "manifest.json")

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".pdf", ".tif", ".tiff")

# --- contract (GT_CONTRACT.md) ----------------------------------------------
SCHEMA_VERSION = "draft-gt-document.v1"

COMMON_12 = (
    "supplierCompany", "supplierBizNumber", "supplierRepresentative", "supplierAddress",
    "buyerCompany", "buyerBizNumber", "buyerRepresentative", "buyerAddress",
    "issueDate", "supplyAmount", "taxAmount", "cumulativeAmount",
)
PER_SAMPLE = ("totalAmount", "totalQuantity")  # exactly one per sample
ALL_SCALAR_LABELS = COMMON_12 + PER_SAMPLE  # union = 14

# Row keys that are real extracted values (compared).
ROW_VALUE_KEYS = (
    "rowIndex", "itemName", "spec", "productCode", "lotNo",
    "expiryDate", "quantity", "unitPrice", "amount",
)
# Row keys that are GT review-meta — never extractor output, excluded from compare.
ROW_META_KEYS = (
    "rowType", "amountOnly", "missingFields", "fieldStatus", "reviewStatus",
    "excludeReason", "sourceRowMeta", "tableExtraColumns",
)
ROW_ALIGN_KEY = "rowIndex"

# Optional rich-only scalar/field keys (bonus; thin GT omits them).
RICH_FIELD_KEYS = ("bboxRefs", "edited", "confidence", "fieldStatus")

# Verified per-sample row counts (contract §3.3).
EXPECTED_ROWS = {
    "1.jpg": 28, "3.pdf": 1, "4.pdf": 1, "5.pdf": 6, "6.pdf": 6, "7.pdf": 1,
}
# Samples deliberately excluded (no image, no GT). Documented in the manifest.
EXCLUDED_SOURCES = {
    "2.pdf": "temporary exclusion (no GT, no image) — pending re-add",
}
EXPECTED_ACTIVE_SOURCES = set(EXPECTED_ROWS)  # the 6 active samples
