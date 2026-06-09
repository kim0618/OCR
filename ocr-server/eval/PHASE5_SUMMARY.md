# Phase 5 — CHECKER-RUNALL = MVP GO (DONE, 2026-06-09)

## Deliverables
| Artifact | Purpose |
|---|---|
| `eval/checker.py` | One consolidated gate: golden regression + phase0-4 checks + manifest<->run cross-check + parse rate |
| `eval/run_all.py` | One command: manifest -> run_batch -> compare -> metrics -> report -> checker |
| `eval/golden/normalization_golden.json` | Hand-authored expected normalizer outputs (drift guard) |

## Gate result — MVP GO
```
python eval/run_all.py --reuse 20260609_143048
  ...
  PASS  normalization-golden      all golden cases hold
  PASS  phase0_contract_check.py  6/6 GT conform
  PASS  phase1_check.py           manifest 6 active + 2.pdf excluded, loader 6/6
  PASS  phase2_check.py           6/6 ok, 0 errors, UTF-8 intact
  PASS  phase3_check.py           6/6 compared, counts consistent, freeze anchors hold
  PASS  phase4_check.py           metrics self-consistent, report rendered, time-series appended
  PASS  manifest<->run            all active samples present, parse 6/6
  CHECKER PASS - harness healthy (MVP GO)
MVP GO - one-command pipeline reproduced run 20260609_143048, checker PASS   (exit 0)
```

## One-command reproduce
- Fast (reuse existing OCR results, no server): `python eval/run_all.py --reuse <run_ts>`
- Full (fresh re-OCR all 6, needs live :9099, ~10 min): `python eval/run_all.py`
Same command, same checker — the only difference is whether step [2/6] re-runs the live OCR.

## Normalization golden regression
`golden/normalization_golden.json` pins expected outputs for every normalizer type
(amount/qty/bizno/date/code/index/text). The checker asserts `normalize.py` reproduces them
exactly — so any accidental change to the frozen normalization (over- or under-normalizing)
fails the gate. Hand-authored, never auto-regenerated.

## What "MVP" means here (plan §8)
The MACHINE runs end to end and every stage is self-consistent and reproducible from one command.
This is an **infrastructure** milestone, NOT an accuracy pass — 6 samples = hypothesis. Accuracy
judgement is the thousands-of-images job (Phase 7 data).

## Next — Phase 6 (SCALE-DRYRUN-30)
Absorb 24-30 user-provided GT (same `draft-gt-document.v1` contract), exercise holdout / slice
code paths for real (qualityTag slice stops being all-`untagged`, supplier/layout slices get
populated). Gate: trustworthy buckets & slices at 30 images = **infrastructure verified** (still
not an accuracy verdict). **Blocked on user providing the additional GT** (see memory:
GT work resumes only on explicit user GT input / approval).
