---
name: project_invoice_2q_7pdf_gt_handoff
description: 2Q DONE — 7.pdf GT Draft user-review handoff docs; 1-row quantity-only representative_table; next=2R-4PDF blocker confirmation (last unchecked sample)
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2Q DONE (Claude Code @ `c:/OCR/OCR`, docs-only handoff, no code). Builds on [[project_invoice_2p_7pdf_skeleton_precheck]]; parallels 2K(2.pdf)/2M(6.pdf)/2O(3.pdf).

Produced tmp/ docs for user to author 7.pdf GT from the 거래_7 template release table (1 row): user_review_guide, column_review_checklist, final_gt_promotion_checklist, next_actions, handoff report+summary, checker. No prod change (git before==final: only the 3 working-tree 2H/2I files). py_compile/typecheck/build/checker(32/0) PASS.

7.pdf-specific handoff facts: draft source=representative_table, **1 row, quantity-only delivery statement** (클리마토플란정 / 시리얼·로트No 0350623-231024-260811 / 단위 BOX / 수량 1,000; NO 단가·금액 cols). Auto-filled = itemName/quantity/lotNo. unitPrice/amount = source-absent → keep empty (no arithmetic). 시리얼/로트No→lotNo; 260811→expiryDate split review (original-confirm); 단위 BOX → spec/note; header 총수량(1,000) vs row quantity(1,000) — don't confuse/duplicate. Rules: standard 8 keys, no Korean keys, no arithmetic, no tokenBboxDebug/extract_debug/raw/base64/full_text, user review before promotion.

Original 7-sample GT status: 1.jpg + 2.pdf(2K) + 3.pdf(2O) + 6.pdf(2M) + 7.pdf(2Q) GT-writable & handed to user-review; 5.pdf needs review; **4.pdf = ONLY unchecked sample (blocker候補)**. Recommended next = FULL-UNSTRUCTURED-INVOICE-2R-4PDF-UNREADABLE-BLOCKER-CONFIRMATION (close out original-7 census; final-promotion-checks wait on user-filled drafts).
