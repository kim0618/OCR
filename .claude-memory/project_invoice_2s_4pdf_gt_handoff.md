---
name: project_invoice_2s_4pdf_gt_handoff
description: "2S DONE — 4.pdf GT Draft user-review handoff docs (page1 priced GT source, page2=7.pdf no-duplicate); original-7 all GT-writable; next=2S-ORIGINAL-7-GT-STATUS-CLOSEOUT"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2S DONE (Claude Code @ `c:/OCR/OCR`, docs-only handoff, no code). Builds on [[project_invoice_2r_4pdf_blocker_confirmation]]; completes the original-7 handoff set (parallels 2K/2M/2O/2Q).

Produced tmp/ docs for user to author 4.pdf GT from 거래_4 template release table (1 row, page1 priced): user_review_guide, column_review_checklist, final_gt_promotion_checklist, next_actions, handoff report+summary, checker. No prod change (git before==final: only the 3 working-tree 2H/2I files). py_compile/typecheck/build/checker(37/0) PASS.

4.pdf-specific handoff facts: draft source=representative_table, **1 row**, NOT a blocker. **2-page doc: page1=priced 거래명세표 (GT SOURCE), page2=7.pdf-identical quantity-only (DO NOT duplicate)**. Item: 클리마토플란정 / Lot 0350623-231024-260811 / BOX / 1,000 / 단가 28,336.00 / 공급가액 25,760,000 / 세액 2,576,000 / TOTAL footer 28,336,000 (footer, NOT a row). Auto-filled = itemName/quantity/lotNo/unitPrice/amount. Rules: page1 빈 grid 행 + TOTAL/footer 행 제외; Lot/시리얼→lotNo (260811 expiry split review); 단위 BOX → spec/note; unitPrice 28,336.00 decimal preserved; supplyAmount/taxAmount keep if row-col; NO arithmetic (amount/supply/tax/total); standard 8 keys, no Korean keys, no raw/debug; user review before promotion.

**Original-7 ALL GT-writable, 0 blockers.** Handoff done: 2.pdf(2K)/3.pdf(2O)/4.pdf(2S)/6.pdf(2M)/7.pdf(2Q); 1.jpg writable; 5.pdf needs review. Recommended next = FULL-UNSTRUCTURED-INVOICE-2S-ORIGINAL-7-GT-STATUS-CLOSEOUT (close out census; per-sample 2T-*-FINAL-GT-PROMOTION-CHECK after user fills drafts).
