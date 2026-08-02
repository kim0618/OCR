---
name: project_invoice_2o_3pdf_gt_handoff
description: "2O DONE — 3.pdf GT Draft user-review handoff docs; 1-row representative_table, exclude 이하여백 filler/blank rows; next=2P-7PDF precheck"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2O DONE (Claude Code @ `c:/OCR/OCR`, docs-only handoff, no code). Builds on [[project_invoice_2n_3pdf_skeleton_precheck]]; parallels 2K(2.pdf)/2M(6.pdf).

Produced tmp/ docs for user to author 3.pdf GT from the 거래_3 template release table (1 row): user_review_guide, column_review_checklist, final_gt_promotion_checklist, next_actions, handoff report+summary, checker. No prod change (git before==final: only the 3 working-tree 2H/2I files). py_compile/typecheck/build/checker(32/0) PASS.

Key 3.pdf-specific handoff facts: draft source=representative_table, **1 row** (single-item invoice). Exclude "이하여백" filler row + 8 blank rows from tableRows. Auto-filled = itemName/spec/quantity/unitPrice/amount; map 보험코드/itemCode→productCode, 제조번호→lotNo, 유효기간→expiryDate; 제조회사(manufacturer) = extra col → schema decision (keep vs extra/notes). Rules: standard 8 keys, no Korean keys, no arithmetic, no tokenBboxDebug/extract_debug/raw/base64/full_text, user review before promotion.

Sample GT status: 1.jpg + 2.pdf(2K) + 6.pdf(2M) + 3.pdf(2O) all GT-writable & handed to user-review; 4.pdf=blocker候補; 5.pdf needs review; 7.pdf pending. Recommended next = FULL-UNSTRUCTURED-INVOICE-2P-7PDF-TEMPLATE-BASED-SKELETON-PRECHECK (last unchecked sample; final-promotion-checks wait on user-filled drafts).
