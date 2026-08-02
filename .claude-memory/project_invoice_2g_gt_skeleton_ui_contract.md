---
name: project_invoice_2g_gt_skeleton_ui_contract
description: "2G precheck — 2.pdf gtSkeletonCandidates(13행) GT Draft/UI contract; mapper already preserves extract_debug, table VM pipeline does not"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2G precheck closeout (no_prod_modify). Real repo root = `c:/OCR/OCR` (지시서 D:/Free_Vue/OCR 미존재).

Findings:
- `extract_debug.invoice_statement_free.gtSkeletonCandidates`(2.pdf, 13행, available) reaches frontend: mapOcrResponse `buildRunOcrResult` does `{...raw}` → extract_debug preserved → **mapper patch unnecessary**.
- BUT `buildTableResultViewModels` (tableResultViewModel.ts) reads only document_fields.tableRows / unstructuredTables / template.regions — NOT extract_debug. So 13-row skeleton needs a **dedicated `gt_skeleton_candidate` VM**, kept OUT of the shared pipeline (cleanJson/markdown share that array → leak risk).
- gtDraftBuilder consumes `tableResultViewModels → selectRepresentative(backend_document_fields=2 rows)`; FIELD_KEYS fully match skeleton row keys; `customTableEdits` is row-index matched → base table must be 13 rows for full edit. `_gtSkeleton` fits sourceRowMeta. RAW_OCR_POLICY_MARKER: skeleton ok, tokenBboxDebug must NOT export.

Recommendation: UI option A(Custom 탭 별도 편집표)+C(GT Draft export); reject B(대표표 승격)/D(전면연결). Gate = `available && fallbackRequired && doc_type===invoice_statement` (no filename hardcode; 1.jpg/5.pdf freeValid→미표시). Invariants: gtSkeletonCandidates NOT release tableRows; no Clean JSON/Markdown/History/DB wiring.

Next: 2H-CUSTOM-TAB-GT-SKELETON-CANDIDATE-TABLE-PATCH (1순위, 편집 surface) + 2H-GT-DRAFT-BUILDER-SKELETON-CANDIDATE-SOURCE-PATCH (묶음). Verified: py_compile/typecheck/build/checker all PASS. Builds on [[project_invoice_4b_2pdf_overlay]].
