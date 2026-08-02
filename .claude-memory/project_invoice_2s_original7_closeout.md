---
name: project_invoice_2s_original7_closeout
description: "2S closeout DONE — original-7 GT status census; all 7 GT-writable, 0 unreadable blockers; handoff gap=1.jpg/5.pdf; next=2T-1JPG-5PDF-GT-HANDOFF-GAP-CHECK"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2S-ORIGINAL-7-GT-STATUS-CLOSEOUT DONE (Claude Code @ `c:/OCR/OCR`, docs-only, no code). Caps the 2F→2S full-unstructured-invoice GT arc. Builds on [[project_invoice_2s_4pdf_gt_handoff]].

**Original-7 GT status census (closeout):**
- ALL 7 GT-writable (or with review). **unreadable blocker = 0.**
- dedicated handoff DONE (5): 2.pdf(2K, skeleton 13)/3.pdf(2O, repr 1)/4.pdf(2R+2S, repr 1 page1-priced)/6.pdf(2M, repr 6)/7.pdf(2Q, repr 1 qty-only).
- **handoff GAP (2): 1.jpg (free 28 rows, GT_WRITABLE) + 5.pdf (columnar 6 rows, GT_WRITABLE_WITH_REVIEW)** — never got a dedicated handoff task. 1.jpg row11 issue / 5.pdf draft-recreate status = "확인 필요" (not assumed).
- ALL final promotion = USER_INPUT_PENDING (no final GT created).

Policies set: **final GT promotion = after user fills draft, per-sample 2T-*-FINAL-GT-PROMOTION-CHECK** (no final GT/manifest/data-gt now). **variant 28 = only after original-7 draft/final secured + schema unified + rowCount/key fixed + 0 leak** (no variant now).

Artifacts: tmp/full_unstructured_invoice_2s_original_7_{status_matrix.json, gt_status_closeout_{summary.json,report.md}, user_review_workqueue.md}, final_gt_promotion_policy.md, variant_28_generation_policy.md, next_actions.md, checker. py_compile/typecheck/build/checker(28/0) PASS. git before==final (only 3 working-tree 2H/2I files).

NOTE on uncommitted working tree: 2H+2I frontend changes (OcrResultPanel.tsx, gtDraftBuilder.ts, gtSkeletonCandidateViewModel.ts) remain UNCOMMITTED across this whole arc — never committed.

Recommended next = FULL-UNSTRUCTURED-INVOICE-2T-1JPG-5PDF-GT-HANDOFF-GAP-CHECK (close the 2 handoff gaps to bring all 7 to equal handoff level).
