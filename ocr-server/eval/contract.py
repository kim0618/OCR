"""Frozen GT contract constants + per-testset profiles (single source of truth).

Imported by every phase (phase0 check, gt_loader, build_manifest, comparators,
checker) so the contract lives in exactly one place. See GT_CONTRACT.md for the
human-readable spec this encodes.

P0 thin-ready (§6.6): this module now carries TWO profiles —
  rich  the human-reviewed draft GT (invoice_study, today): COMMON_12 + rich keys.
  thin  the future ETL/DB GT (war columns): a strict subset, no bbox/edited/rowIndex.
The thin column set is the SSOT shared by the fixture down-projector (step 1) and
the Phase-7 ETL, so a passing fixture proves the harness accepts production shape.
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys

# Windows consoles default to cp949; force UTF-8 so report text never crashes.
try:  # pragma: no cover - environment dependent
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# --- paths (resolved relative to this file, so scripts run from anywhere) ----
HERE = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.path.join(HERE, "runs")
MANIFEST_PATH = os.path.join(HERE, "manifest.json")
FIXTURES_DIR = os.path.join(HERE, "fixtures")  # harness-owned thin fixtures (not public/data)

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".pdf", ".tif", ".tiff")

# --- contract (GT_CONTRACT.md) ----------------------------------------------
SCHEMA_VERSION = "draft-gt-document.v1"

# rich profile: human-reviewed draft GT (invoice_study).
COMMON_12 = (
    "supplierCompany", "supplierBizNumber", "supplierRepresentative", "supplierAddress",
    "buyerCompany", "buyerBizNumber", "buyerRepresentative", "buyerAddress",
    "issueDate", "supplyAmount", "taxAmount", "cumulativeAmount",
)
PER_SAMPLE = ("totalAmount", "totalQuantity")  # exactly one per rich sample
ALL_SCALAR_LABELS = COMMON_12 + PER_SAMPLE  # union = 14

# --- SSOT thin column contract (war-verified, §6.6 P0) ----------------------
# ONE constant shared by the thin fixture down-projector (step 1) and the future
# Phase-7 ETL. Equal sets here == the oracle that the fixture matches production.
THIN_SCALAR_FIELDS = (
    "totalAmount", "taxAmount", "discountAmount", "issueDate", "documentNumber",
    "supplierBizNumber", "buyerBizNumber", "supplierCompany", "taxType",
    "supplierAddress",
)  # 10 war scalar columns
THIN_ROW_KEYS = (
    "itemName", "quantity", "unitPrice", "amount", "expiryDate", "manufacturingNo",
)  # 6 war row columns — note: NO rowIndex (thin has none → content-aligned, step 4)
NEW_3_FIELDS = ("discountAmount", "documentNumber", "taxType")  # extractor not-yet-emitted → honest 100% miss
# war low-confidence thin fields (§6.6): the "difficult" subset for thin's
# difficultySplit (➐), mirroring rich's `edited` subset.
THIN_LOW_CONFIDENCE_FIELDS = ("supplierCompany", "taxType")  # brcd_name / 저신뢰
RICH_ONLY_FIELDS = (
    "supplyAmount", "supplierRepresentative", "buyerCompany", "buyerRepresentative",
    "buyerAddress", "cumulativeAmount", "totalQuantity",
)  # 7 thin-absent → rich (invoice_study) covers


def required_scalar_fields(kind: str) -> tuple[str, ...]:
    """Hard-required scalar keys for a profile (loader gate, §6.6 A).

    rich enforces the COMMON_12 presence; thin enforces nothing — thin scores
    exactly the keys the GT provides (➊⓭), so missing keys are absent-by-design.
    """
    return COMMON_12 if kind == "rich" else ()


def enforce_per_sample(kind: str) -> bool:
    """Per-sample exactly-one invariant (➋) is rich-gated; thin opts out."""
    return kind == "rich"


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

# --- testset profiles (⓬ per-testset, replaces a single hardcoded dir) -------
# Each profile: where the GT/images live, the comparison profile (rich|thin),
# how the runner produces results (live POST vs canned recorded rec), and the
# verified per-sample row counts. EXPECTED_ROWS/dir are no longer global facts.


def _testset(dir_path: str, kind: str, run_mode: str,
             expected: dict[str, int], excluded: dict[str, str] | None = None) -> dict:
    return {
        "dir": dir_path,
        "gtDir": os.path.join(dir_path, "GT"),
        "recDir": os.path.join(dir_path, "rec"),  # canned recorded rec envelopes (⓲)
        "kind": kind,                              # "rich" | "thin"
        "runMode": run_mode,                       # "live" | "canned"
        "expected": dict(expected),                # sourceFile -> verified row count
        "excluded": dict(excluded or {}),          # sourceFile -> reason
    }


TESTSETS: dict[str, dict] = {
    "invoice_study": _testset(
        os.path.normpath(os.path.join(
            HERE, "..", "..", "mysuit-ocr", "public", "data", "testsets",
            "invoice_study",
        )),
        kind="rich",
        run_mode="live",
        expected={"1.jpg": 28, "3.pdf": 1, "4.pdf": 1, "5.pdf": 6, "6.pdf": 6, "7.pdf": 1},
        excluded={"2.pdf": "temporary exclusion (no GT, no image) — pending re-add"},
    ),
    "invoice_thin": _testset(
        os.path.join(FIXTURES_DIR, "invoice_thin"),
        kind="thin",
        run_mode="canned",
        # Down-projection preserves row count, so the thin fixture's expected row
        # counts equal the rich source's (derived fact, not a guess).
        expected={"1.jpg": 28, "3.pdf": 1, "4.pdf": 1, "5.pdf": 6, "6.pdf": 6, "7.pdf": 1},
    ),
}
DEFAULT_TESTSET = "invoice_study"


def get_testset(name: str = DEFAULT_TESTSET) -> dict:
    if name not in TESTSETS:
        raise KeyError(f"unknown testset {name!r}; known={sorted(TESTSETS)}")
    return TESTSETS[name]


def latest_run(testset: str | None = None) -> str | None:
    """Latest run dir, FILTERED by run_meta.testset when given.

    A run dir = any directory holding a run_meta.json. They live either FLAT
    (runs/<ts>/) or nested under a batch folder (runs/<batch>/<study|thin>/,
    written by `run_all --all`). We search both depths and pick the most recent
    by mtime, filtered to the requested testset so a rich checker never grabs a
    thin run (or vice versa).
    """
    metas = (glob.glob(os.path.join(RUNS_DIR, "*", "run_meta.json"))
             + glob.glob(os.path.join(RUNS_DIR, "*", "*", "run_meta.json")))
    best: str | None = None
    best_mtime = -1.0
    for mp in metas:
        if testset is not None:
            try:
                mt = json.load(open(mp, encoding="utf-8")).get("testset")
            except (OSError, json.JSONDecodeError):
                mt = None
            if (mt or DEFAULT_TESTSET) != testset:
                continue
        mtime = os.path.getmtime(mp)
        if mtime > best_mtime:
            best_mtime, best = mtime, os.path.dirname(mp)
    return best


# --- legacy aliases: default testset = invoice_study (keeps rich callers green)
_DEFAULT = TESTSETS[DEFAULT_TESTSET]
TESTSET_DIR = _DEFAULT["dir"]
IMG_DIR = _DEFAULT["dir"]
GT_DIR = _DEFAULT["gtDir"]
EXPECTED_ROWS = _DEFAULT["expected"]            # verified per-sample row counts
EXCLUDED_SOURCES = _DEFAULT["excluded"]         # deliberately dropped (no image, no GT)
EXPECTED_ACTIVE_SOURCES = set(EXPECTED_ROWS)    # the verified BASE documents (regression anchor)

# --- angle/condition variants ------------------------------------------------
# A base document reshot at angles produces "<base>-<N>.<ext>" images (1-1.jpg,
# 3-2.jpg). Same document => same answers, so a variant inherits its base GT.
# SSOT for the variant pattern (build_manifest + checkers share this).
_VARIANT_RE = re.compile(r"^(?P<base>.+)-\d+$")


def base_source(source_file: str, testset: str = DEFAULT_TESTSET) -> str:
    """Resolve a variant image ('1-1.jpg', '3-2.jpg') to its base document
    ('1.jpg', '3.pdf'). Non-variants, and variants of an unknown base, return
    unchanged. Matches by stem so the variant ext may differ from the base."""
    stem_to_base = {os.path.splitext(s)[0]: s for s in get_testset(testset)["expected"]}
    m = _VARIANT_RE.match(os.path.splitext(source_file)[0])
    if m:
        base = stem_to_base.get(m.group("base"))
        if base:
            return base
    return source_file


def expected_active_sources(testset: str = DEFAULT_TESTSET) -> set[str]:
    """The full active set the harness should run: the verified base documents
    PLUS their on-disk variants. Bases are the fixed regression anchor; variants
    are discovered from the testset image dir so reshooting samples at new angles
    does not trip the gate. A missing base still fails (bases are always in the
    set); a stray image with no base GT is never added (=> caught as pending_gt)."""
    ts = get_testset(testset)
    bases = set(ts["expected"])
    out = set(bases)
    img_dir = ts["dir"]
    if os.path.isdir(img_dir):
        for name in os.listdir(img_dir):
            if (name.lower().endswith(IMAGE_EXTS) and name not in bases
                    and base_source(name, testset) in bases):
                out.add(name)
    return out
