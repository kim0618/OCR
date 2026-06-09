# Phase 1 — INGEST (DONE, 2026-06-09)

## Deliverables
| Artifact | Purpose |
|---|---|
| `eval/contract.py` | **Single source of truth** for contract constants + paths (phase0 now imports it too) |
| `eval/gt_loader.py` | `load_gt(path)` -> normalized shape (flatten `fields[]`, value-keys-only rows, split `excludedRows`, rich/thin profile) |
| `eval/build_manifest.py` | Auto-pair image<->GT by `sourceFile`, status per sample, writes `eval/manifest.json` |
| `eval/manifest.json` | Generated dataset definition (6 active + 2.pdf excluded) |
| `eval/phase1_check.py` | Gate checker |

## Gate result — GO
```
python eval/phase1_check.py  ->  GATE PASS - manifest 6 active + 2.pdf excluded, loader 6/6  (exit 0)
```
Both prior gates still green after the constant refactor: `phase0 EXIT=0`, `phase1 EXIT=0`.

## Manifest
```
active   : 1.jpg(28) 3.pdf(1) 4.pdf(1) 5.pdf(6) 6.pdf(6) 7.pdf(1)   [all rich]
excluded : 2.pdf  (no GT, no image — explicit, documented)
counts   : {active: 6, excluded: 1}
```
Statuses the manifest can emit: `active / pending_gt / gt_orphan / gt_invalid / excluded`.

## Loader output shape (what Phase 3 compare consumes)
```
{ sourceFile, sampleId, schemaVersion, profile: "rich"|"thin",
  documentFields: {labelEn: value} (13),  perSampleField: "totalAmount"|"totalQuantity",
  tableRows: [{value keys only, incl rowIndex}],  excludedRows: [...],
  _meta: {fieldCount, rowCount, excludedRowCount, gtPath} }
```
- Thin-graceful: rich-only keys (`bboxRefs/edited/confidence/fieldStatus`) detected for the
  profile flag but never required -> future ETL thin GT loads unchanged.
- Review-meta (`rowType` + 7 others) stripped from rows; checker asserts none leak.

## Refactor note
Constants that were inlined in `phase0_contract_check.py` now live only in `contract.py`;
phase0 imports them. Eliminates the drift the Phase 5 golden-regression checker guards against.

## Governance
New files under `ocr-server/eval/` only. `public/data` read-only (manifest reads, never writes).
`manifest.json` is a small generated dataset definition kept in `eval/` (not under `runs/`).

## Next — Phase 2 (RUNNER)
`run_batch.py`: POST each active image to live `:9099` `/ocr/extract` with `templateMode=unstructured`,
read `resp["document_fields"]` (page-0 + page-count assert), record `tableMeta.extractionSource`
(free vs fallback), resume + parallel + error isolation, write to `runs/<ts>/`.
**Needs the live server (already running per user).**
