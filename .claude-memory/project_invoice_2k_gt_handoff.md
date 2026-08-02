---
name: project_invoice_2k_gt_handoff
description: "2K DONE — 2.pdf GT Draft user-review handoff docs (guide + column/promotion checklists + next-actions); 2.pdf GT-writable, next=2L final-GT-promotion-check"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2K DONE (Claude Code @ `c:/OCR/OCR`, docs-only handoff, no code). Closes the 2F→2K chain for 2.pdf. Builds on [[project_invoice_2j_gt_draft_export_smoke]].

Produced tmp/ docs for the user to author 2.pdf GT from the 13-row gt_skeleton_candidate Draft: user_review_guide, column_review_checklist, final_gt_promotion_checklist, next_actions, handoff report+summary, checker. No prod change (git before==final: only the 3 working-tree 2H/2I files). py_compile/typecheck/build/checker(25/0) PASS.

Key handoff facts: draft source=gt_skeleton_candidate, 13 rows; auto-filled = productCode+amount only; user must manually fill itemName/spec/lotNo/expiryDate/quantity/unitPrice. Rules: standard 8 keys (no Korean keys), no arithmetic generation (amount≠qty×unitPrice), no tokenBboxDebug/extract_debug/raw OCR/base64/full_text, rowConfidence=low first + reviewRequired=true all, user review BEFORE final promotion.

2.pdf = GT-writable, handed to user. Next = FULL-UNSTRUCTURED-INVOICE-2L-2PDF-FINAL-GT-PROMOTION-CHECK (after user fills draft) or 2L-6PDF-...-PRECHECK (parallel next sample).
