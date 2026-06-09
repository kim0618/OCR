# Phase 4 — METRICS-REPORT (DONE, 2026-06-09)

## Deliverables
| Artifact | Purpose |
|---|---|
| `eval/metrics.py` | Aggregate compares -> overall/per-field/bucket + slices + free/fallback + edited split; appends time series |
| `eval/report.py` | Render `runs/<ts>/report.md` (hypothesis banner, per-field table, side-by-side failures) |
| `eval/phase4_check.py` | Gate checker (cross-foot self-consistency + report + time series) |
| `runs/<ts>/metrics.json` | Machine metrics |
| `runs/<ts>/report.md` | Human report |
| `eval/metrics_timeseries.sqlite` | Per-run trend (gitignored, regression tracking) |

## Gate result — GO
```
python eval/phase4_check.py -> GATE PASS - metrics self-consistent, report rendered, time-series appended
```
All earlier gates still green.

## Headline signal (6 samples — HYPOTHESIS, not a verdict)
- Overall field **62.3%** (38/61), cell **88.7%** (236/266).
- **The diagnostic that matters — edited split:**
  - `edited=false` GT fields: **97.4%** (37/38) — where raw OCR was already right, extraction nails it.
  - `edited=true` GT fields: **4.3%** (1/23) — where a human corrected the GT, extraction (raw-ish) misses.
  - => The 62% is dragged down entirely by human-corrected fields. The harness is correctly
    pointing at the exact OCR-error locations. **This is the rule-boost worklist.**
- free vs fallback: free cell **94.6%** vs fallback cell **57.1%**.
- Weakest fields: `buyerAddress` / `supplierAddress` **0%** (extraction appends noise e.g. "자상으로"),
  `supplierRepresentative` 40%.
- Buckets: recognition **39**, structure **14**, layout 0, preprocessing 0. Failing examples are
  real OCR misreads (헥사메딘->헥사메던, 켈론정->헬론정, 30T->3OT O/0 confusion).

## Slices (code path fired on 6 samples)
- `extractionPath` (== byPath), `supplier`, `layout` (single_row 54.5% vs multi_row 71.4%),
  `qualityTag` (all `untagged` — manifest carries no tags yet; populates at Phase 6 / real tags).
- **Fix folded in:** supplier slice groups by whitespace-stripped name, so the same supplier with
  different GT spacing ("주식회사 엘비..." vs "주식회사엘비...") merges into one group (21 scored, was split 9+12).

## Notes
- All metrics cross-foot: overall == sum(per-sample) == sum(per-field) == sum(byPath) == sum(editedSplit).
- Time series keyed by runTs (INSERT OR REPLACE) — re-running a run updates its row, no dupes.
- Numbers are signal to direct rule work, NOT an accuracy gate (plan §8).

## Next — Phase 5 (CHECKER-RUNALL) = MVP GO
`checker.py` (manifest<->files, metric cross-foot, parse rate, normalization golden regression)
+ `run_all` (one command: manifest -> run_batch -> compare -> metrics -> report -> checker).
Gate: checker PASS + one-command reproduce.
