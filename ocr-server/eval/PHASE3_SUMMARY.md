# Phase 3 — COMPARE (DONE, 2026-06-09)

## Deliverables
| Artifact | Purpose |
|---|---|
| `eval/normalize.py` | **Frozen** value normalization (per field/cell type) — neutralizes representation only |
| `eval/compare_fields.py` | Scalar compare by labelEn, per-sample required set, GT-empty skip, edited tracking |
| `eval/compare_table.py` | Row align by normalized rowIndex, value-cell compare, excludedRows already split out |
| `eval/buckets.py` | 4-bucket defect tagging (recognition / structure / layout / preprocessing), explainable |
| `eval/compare_run.py` | Driver: GT x run -> `runs/<ts>/compare/<src>.json` + `compare_summary.json` |
| `eval/phase3_check.py` | Gate checker (self-consistency + freeze anchors) |
| `gt_loader.py` | (extended, additive) now also returns `fieldMeta` = edited/fieldStatus/confidence |

## Gate result — GO
```
python eval/phase3_check.py -> GATE PASS - 6/6 compared, counts self-consistent, buckets valid, freeze anchors hold
```
phase0/phase1/phase2 all still green after the additive loader change.

## Human spot-check (the gate) — PASS
Verified the comparison matches reality on `1.jpg` (free) and `4.pdf` (fallback):
- `118-81-00450` ~ `1188100450` -> **match** (hyphen neutralized); `18,098,750` ~ `18098750`
  -> match (comma); `2024-03-07` ~ `20240307` -> match (date sep). Freeze works.
- `LEE WOO HYUN` vs `UIO J`, address `...상도로7` vs `...상도로7 자상으로` -> **mismatch**
  (real OCR errors preserved, NOT normalized away).
- GT-empty `supplyAmount`/`taxAmount` -> **gt_empty, not scored** (extracted noise `합` ignored,
  per contract).
- Counts add up: `1.jpg` scored 11 = 13 - 2 gt_empty; 7 match + 3 mismatch + 1 miss = 11.

## Snapshot (6 samples) — HYPOTHESIS, not a verdict (plan §8: small sample)
```
sample  path      fieldAcc  cellAcc  rows(g/e)  buckets
1.jpg   free       63.6%    94.3%    28/28      reco=13 stru=2
3.pdf   fallback   41.7%    75.0%     1/1       reco=2  stru=7
4.pdf   fallback   50.0%    60.0%     1/1       reco=7  stru=1
5.pdf   free       75.0%    96.7%     6/6       reco=3  stru=1
6.pdf   fallback   80.0%    50.0%     6/6       reco=12 stru=2
7.pdf   fallback   77.8%    66.7%     1/1       reco=2  stru=1
```
fieldAcc = match / scored (gt_empty excluded). Free-path tables (1.jpg, 5.pdf) score highest
on cells (94-97%). Many scalar text mismatches sit on `edited=true` GT fields (human-corrected
GT vs raw-ish extraction) — Phase 4 will slice edited separately.

## Decisions folded in
- `rowIndex` type-normalized (`"1"` == `1`) for row alignment.
- 4-bucket tags are heuristic + carry a `reason`; preprocessing is a sample-level suspicion
  (>=70% field miss), advisory only. **No accuracy claims from 6 samples.**
- normalization is the single freeze point (`normalize.py`); the checker pins anchors so it
  cannot silently over- or under-normalize.

## Next — Phase 4 (METRICS-REPORT)
`metrics.py` (field/overall/bucket + slices: supplier, layout, qualityTag; edited separate;
free vs fallback separate) and `report.py` (Markdown: hypothesis banner + field table + failing
GT/extraction side-by-side) + time series (sqlite/parquet). Gate: 6-sample e2e -> report.md,
metrics self-consistent.
