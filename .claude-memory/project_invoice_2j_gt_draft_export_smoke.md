---
name: project_invoice_2j_gt_draft_export_smoke
description: "2J smoke DONE — 2.pdf GT Draft export headless smoke (real pipeline) PASS; 13-row gt_skeleton_candidate, edits reflected, no raw/debug leak; next=2K user-review handoff"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2J smoke/review DONE (Claude Code @ `c:/OCR/OCR`). Builds on [[project_invoice_2h_custom_tab_gt_skeleton_table]].

NOTE: 2I (GT Draft Builder skeleton-candidate source) was implemented in the working tree by a prior run — `gtDraftBuilder.ts` has `useSkeletonCandidateRows`/`tableRowsFromSkeletonCandidateRows`/`mergeSkeletonCandidateEdits` + `tableRowsSource:"gt_skeleton_candidate"`; `OcrResultPanel.handleExportDraftGt` passes `skeletonCandidateRows`/`skeletonCandidateEdits`. So 2H+2I are uncommitted working-tree changes (3 files: OcrResultPanel.tsx, gtDraftBuilder.ts, gtSkeletonCandidateViewModel.ts).

Smoke method: NO live browser/PaddleOCR in this env → ran the REAL export pipeline HEADLESS via Node 24 TS type-stripping + a resolve hook (`tmp/_2j_loader.mjs`+`_2j_register.mjs` maps `@/`→mysuit-ocr/src, appends .ts). Harness `tmp/_2j_smoke.mjs` feeds a synthetic 2.pdf response (release 2 rows + 13 skeleton rows + tokenBboxDebug + full_text) through real buildGtSkeletonCandidateViewModel/buildDraftGtDocument/buildCandidateFields/buildCleanJsonResult/buildMarkdownReport/buildTableResultViewModels.

Results (all PASS): draft tableRows=13, source=gt_skeleton_candidate, smoke edits reflected (row0 itemName, row1 amount), release unchanged=2, sourceRowMeta sanitized to scalars only [source,sourceRowIndex,reviewRequired,rowConfidence] (gtDraftBuilder.sanitizeSourceRowMeta strips debug/ocr/coordinate/raw + non-scalar). Guard: no tokenBboxDebug/extract_debug/raw_ocr/full_text/base64 in downloaded doc. Clean JSON/Markdown leak=0 (skeleton markers absent, release present). Regression: freeValid (fallbackRequired=false) → VM null → 미표시. py_compile/typecheck/build/checker(35/0) PASS.

GT 작성 가능. Skeleton fills only productCode+amount → user fills itemName/spec/lotNo/expiryDate/quantity/unitPrice manually. Next = FULL-UNSTRUCTURED-INVOICE-2K-2PDF-GT-DRAFT-USER-REVIEW-HANDOFF. (Live browser E2E recommended once on an OCR-backend env.)
