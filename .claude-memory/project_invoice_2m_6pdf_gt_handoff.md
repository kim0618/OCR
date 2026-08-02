---
name: project_invoice_2m_6pdf_gt_handoff
description: 2M DONE — 6.pdf GT Draft user-review handoff docs; 6.pdf GT-writable via representative_table 6 rows (no skeleton); recommended next=2N-3PDF precheck
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2M DONE (Claude Code @ `c:/OCR/OCR`, docs-only handoff, no code). Builds on [[project_invoice_2l_6pdf_gt_workflow_precheck]]; parallels [[project_invoice_2k_gt_handoff]] (2.pdf).

Produced tmp/ docs for user to author 6.pdf GT from the 거래_6 template release table: user_review_guide, column_review_checklist, final_gt_promotion_checklist, next_actions, handoff report+summary, checker. No prod change (git before==final: only the 3 working-tree 2H/2I files). py_compile/typecheck/build/checker(29/0) PASS.

Key handoff facts (differ from 2.pdf): 6.pdf draft source=representative_table, 6 rows (NOT skeleton). Auto-filled = itemName/spec/quantity/unitPrice/amount (5); user fills productCode/lotNo/expiryDate. Extra canonical cols supplyAmount/taxAmount/totalAmount/itemCode → handle per §3 (row-col vs footer; itemCode→productCode naming only, no value gen). Rules: standard 8 keys, no Korean keys, no arithmetic, no tokenBboxDebug/extract_debug/raw/base64/full_text, user review before promotion.

Status: 2.pdf (2K) + 6.pdf (2M) both GT-writable, in user-review. Recommended next = FULL-UNSTRUCTURED-INVOICE-2N-3PDF-TEMPLATE-BASED-SKELETON-PRECHECK (advance to next sample; final-promotion-check waits on user-filled drafts).
