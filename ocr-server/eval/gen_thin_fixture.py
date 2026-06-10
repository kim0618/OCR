"""gen_thin_fixture — down-project the rich invoice_study GT into a thin fixture.

Builds the §6.6 thin fixture WITHOUT guessing any values: it keeps only the
SSOT war columns (contract.THIN_SCALAR_FIELDS / THIN_ROW_KEYS) from the real
rich GT, drops every rich-only key (bbox/edited/confidence/fieldStatus, rowIndex,
review-meta), and emits a proper thin envelope (⓮'). The recorded OCR results
from a real run are copied verbatim as canned rec envelopes (⓱) so the thin
testset runs with no live server and no images.

This is the oracle generator for the bidirectional acceptance check: thin =
rich ∩ war-columns, so rich-path and thin-path must agree on shared fields.

    python eval/gen_thin_fixture.py --from-run <run_ts>   # default: latest run

Writes ONLY under eval/fixtures/invoice_thin/. Reads public/data + runs/ (no
writes there). Not part of the live pipeline; a fixture builder.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil

import contract as C

THIN = C.get_testset("invoice_thin")
RICH = C.get_testset("invoice_study")
THIN_SCALAR = set(C.THIN_SCALAR_FIELDS)
THIN_ROWS = list(C.THIN_ROW_KEYS)


def downproject_gt(rich_raw: dict) -> dict:
    """rich GT envelope -> thin GT envelope (SSOT-filtered, no guessed values)."""
    src = rich_raw.get("sourceFile")
    nr = rich_raw.get("normalizedResult") or {}

    thin_fields = []
    for f in nr.get("fields") or []:
        label = f.get("labelEn")
        if label in THIN_SCALAR:
            # value ONLY — no bbox/edited/confidence/fieldStatus (rich-only, §5).
            thin_fields.append({"labelEn": label, "value": f.get("value", "")})

    thin_rows = []
    for r in nr.get("tableRows") or []:
        # keep ONLY war row columns; NO rowIndex, no rich-only keys, no review-meta.
        row = {k: r[k] for k in THIN_ROWS if k in r}
        thin_rows.append(row)

    return {
        "schemaVersion": C.SCHEMA_VERSION,
        "sourceFile": src,
        "sampleId": rich_raw.get("sampleId"),
        "normalizedResult": {"fields": thin_fields, "tableRows": thin_rows},
        "excludedRows": [],
        "_provenance": {
            "downProjectedFrom": "invoice_study",
            "ssot": "contract.THIN_SCALAR_FIELDS + THIN_ROW_KEYS",
            "note": "no guessed values; real rich values filtered to war columns; "
                    "rich-only keys (bbox/edited/rowIndex/meta) and new-3 (absent in rich) dropped",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-run", default=None, help="run_ts whose recorded results become canned rec (default: latest)")
    args = ap.parse_args()

    run_dir = (os.path.join(C.RUNS_DIR, args.from_run) if args.from_run
               else sorted(p for p in glob.glob(os.path.join(C.RUNS_DIR, "*")) if os.path.isdir(p))[-1])
    samples_dir = os.path.join(run_dir, "samples")

    gt_out = THIN["gtDir"]
    rec_out = THIN["recDir"]
    os.makedirs(gt_out, exist_ok=True)
    os.makedirs(rec_out, exist_ok=True)

    rich_gt_paths = sorted(glob.glob(os.path.join(RICH["gtDir"], "*.json")))
    written = []
    for path in rich_gt_paths:
        with open(path, encoding="utf-8") as fh:
            rich_raw = json.load(fh)
        thin = downproject_gt(rich_raw)
        src = thin["sourceFile"]
        if not src:
            continue
        # thin GT
        with open(os.path.join(gt_out, src + ".json"), "w", encoding="utf-8") as fh:
            json.dump(thin, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        # canned rec = recorded run result, copied verbatim (녹화 rec봉투)
        rec_src = os.path.join(samples_dir, src + ".json")
        if os.path.isfile(rec_src):
            shutil.copyfile(rec_src, os.path.join(rec_out, src + ".json"))
        n_scalar = len(thin["normalizedResult"]["fields"])
        n_rows = len(thin["normalizedResult"]["tableRows"])
        written.append((src, n_scalar, n_rows, os.path.isfile(rec_src)))

    print(f"down-projected from run: {os.path.basename(run_dir)}")
    print(f"thin GT  -> {os.path.relpath(gt_out, C.HERE)}")
    print(f"thin rec -> {os.path.relpath(rec_out, C.HERE)}")
    for src, ns, nr, has_rec in written:
        print(f"  {src:<8} scalars={ns:<2} rows={nr:<3} rec={'Y' if has_rec else 'MISSING'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
