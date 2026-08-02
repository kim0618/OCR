---
name: project_invoice_2l_6pdf_gt_workflow_precheck
description: "2L DONE — 6.pdf GT-draft workflow precheck; GT_WRITABLE_WITH_MINOR_REVIEW via existing representative-table path (no skeleton needed), next=2M-6PDF user-review handoff"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2L precheck DONE (Claude Code @ `c:/OCR/OCR`, no code change). Builds on [[project_invoice_2k_gt_handoff]] and [[project_t10_header_skip]].

Question: is 6.pdf GT-writable? Answer: **GT_WRITABLE_WITH_MINOR_REVIEW** — and crucially it does NOT need the 2.pdf skeleton machinery.

Findings:
- 거래_6 template (TPL-95328E52, invoice_statement): 6 regions, region[5]=table box [66,621,1515,277] (height 277 = MEDIUM), **0 column defs → TEMPLATE_REGION_ONLY_OK** (backend colGuides decides columns).
- 6.pdf via template path → release tableRows **6 rows** (T-10 evidence: 7/6→6/6 exact). NO extract_debug.gtSkeletonCandidates (skeleton is only the free-fallback/2.pdf case). 3A no-template free path was fallback/fail — irrelevant here.
- Row keys = canonical invoice_statement schema (itemName, spec, quantity, unitPrice, supplyAmount, taxAmount, totalAmount, amount...). Standard-8 populated: itemName/spec/quantity/unitPrice/amount (5/8); productCode/lotNo/expiryDate absent→user fills. productCode↔itemCode naming differs from skeleton schema → STANDARD_KEYS_PARTIAL.
- Headless real-builder smoke (Node TS strip, 2J harness): gtSkeletonVM=null → buildTableResultViewModels → representative=backend_document_fields(6 rows) → buildDraftGtDocument(useSkeletonCandidateRows=false) → draft tableRowsSource=representative_table, **6 rows**, raw/debug guard PASS (no tokenBboxDebug/extract_debug/raw/base64/full_text), clean/md leak 0.

Live OCR route NOT executed (45s + template payload wiring); headless substitute disclosed; paddleocr importable if live run wanted later.

Verified: py_compile/typecheck/build/checker(28/0) PASS. Next (single) = FULL-UNSTRUCTURED-INVOICE-2M-6PDF-GT-DRAFT-USER-REVIEW-HANDOFF.
