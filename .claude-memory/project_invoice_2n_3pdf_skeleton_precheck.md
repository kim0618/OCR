---
name: project_invoice_2n_3pdf_skeleton_precheck
description: "2N DONE — 3.pdf precheck; original is genuine 1-item invoice (rowCount=1 correct, not a miss), GT_WRITABLE_WITH_MINOR_REVIEW via representative_table; next=2O-3PDF handoff"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2N precheck DONE (Claude Code @ `c:/OCR/OCR`, no code change). Builds on [[project_invoice_2l_6pdf_gt_workflow_precheck]] / [[project_invoice_2m_6pdf_gt_handoff]].

Decisive evidence: **read original 3.pdf directly** (Read tool on the PDF) — table has 10 slots but only **1 genuine item row** filled (보험코드 669700020 / 에스피씨세파클러캡슐250mg / 30캡슐 / 수량30 / 단가10,044 / 금액301,320 / 제조 (주)에스피 / 제조번호23004A / 유효기간20261204). Row2 = "이하여백" filler (not an item); rows 3-10 blank. So rowCount=1 is the TRUE content, NOT a route miss. (Prior 1X "free rowCount=1" confirmed correct; 3A no-template free path failed but irrelevant.)

거래_3 template (TPL-E4B15A22, invoice_statement): 10 regions, table region[9] box=[54,358,1553,85] = **THIN** (height 85), 0 columns → TEMPLATE_THIN_TABLE (THIN is normal for 1 row).

Headless real-builder smoke (Node TS strip, 2J harness): gtSkeletonVM=null → representative=backend_document_fields(1 row) → buildDraftGtDocument(useSkeletonCandidateRows=false) → draft tableRowsSource=representative_table, 1 row, raw/debug guard PASS, leak 0.

Decision: **GT_WRITABLE_WITH_MINOR_REVIEW**. 2.pdf skeleton reuse = NO_NEED_REPRESENTATIVE_OK (1 genuine row, no anchor builder needed). minor review = exclude '이하여백' filler + map 보험코드↔productCode / 제조번호↔lotNo / 유효기간↔expiryDate.

Verified: py_compile/typecheck/build/checker(31/0) PASS. Single next = FULL-UNSTRUCTURED-INVOICE-2O-3PDF-GT-DRAFT-USER-REVIEW-HANDOFF.

Sample GT status: 1.jpg/2.pdf(2K)/6.pdf(2M)/3.pdf(2N) all GT-writable; 4.pdf=blocker候補; 5.pdf needs review; 7.pdf pending.
