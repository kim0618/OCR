---
name: project_invoice_2h_custom_tab_gt_skeleton_table
description: "2H frontend patch DONE — Custom 탭 GT 후보 입력표(13행) for 2.pdf gtSkeletonCandidates, isolated edit state, no leak; next=2I GT Draft Builder source"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2H implemented (frontend patch, Claude Code @ `c:/OCR/OCR`). Builds on [[project_invoice_2g_gt_skeleton_ui_contract]].

Changes:
- NEW `mysuit-ocr/src/components/runocr/utils/gtSkeletonCandidateViewModel.ts` — `buildGtSkeletonCandidateViewModel(result)` reads `extract_debug.invoice_statement_free.gtSkeletonCandidates` (single `any` chokepoint), source=`gt_skeleton_candidate`, gate = `doc_type=invoice_statement && fallbackRequired===true && available===true && mode===debug_gt_skeleton_only && (releaseImpact===none||candidateRowsReleaseIsolated===true) && rows>0`. 8 std cols. tokenBboxDebug excluded.
- EDIT `OcrResultPanel.tsx` — `gtSkeletonVM` memo + reset effect, isolated `gtSkeletonEdits` state (row-index, separate from customTableEdits), `renderGtSkeletonCandidateTable` (amber-labeled "GT 후보 입력표 / 자동 추출 결과 아님 / 검토 필요"), rendered at Custom 탭 or-field-list 하단. NOT added to buildTableResultViewModels / representative priority.

Invariants held: skeleton NOT release tableRows; no Clean JSON/Markdown/History(onPersist)/DB leak (leakCount=0); release 2행 unchanged; 1.jpg/5.pdf fallbackRequired=false → 미표시. gtDraftBuilder.ts UNCHANGED (deferred).

Verified: py_compile/typecheck/build/checker all PASS (24/24). Next = FULL-UNSTRUCTURED-INVOICE-2I-GT-DRAFT-BUILDER-SKELETON-CANDIDATE-SOURCE-PATCH (wire edited 13 rows into GT Draft export base).
