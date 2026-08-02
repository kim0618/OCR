---
name: project_invoice_2t_1jpg_5pdf_gap_check
description: 2T DONE — 1.jpg handoff created (28 rows); 5.pdf is a 22-PAGE multi-transaction bundle (release 6 rows = page1 only) → needs draft recreate; next=2U-5PDF-DRAFT-RECREATE-AND-HANDOFF
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2T DONE (Claude Code @ `c:/OCR/OCR`, docs-only gap check, no code). Builds on [[project_invoice_2s_original7_closeout]].

Closed the 1.jpg/5.pdf handoff gap from 2S — by READING both originals directly:

- **1.jpg**: single-page readable 28-row 거래명세서 (품목명/규격/제조번호/유효기간/수량/단가/금액; 소계 18,098,750; no productCode col). Free path, freeValid, representative_table 28 rows. Headless smoke: 28-row export OK, raw/debug guard PASS, leak 0. → **1JPG_HANDOFF_NEEDED → HANDOFF_CREATED** (guide written). Review point: past row11 quantity issue → user verify (no auto-fix).

- **5.pdf**: ⚠ CRITICAL — original is a **22-PAGE multi-transaction bundle** (주문번호 471/470/466/465/469/467/464/463/468...). Each main page = 6 items + a 세부내역 detail page (제품코드/제품명/수량/Lot No/유효일자). The "6-row" release captured **page1 ONLY** (두피나액30ML...노루모에프내복액75ML). So 6 rows ≠ full doc → page2~22 missing. → **5PDF_DRAFT_RECREATE_NEEDED** (NOT a simple handoff). Resolves the 1W "5.pdf draft missing / 1.jpg duplicate" concern: 5.pdf needs GT-scope decision (per-page vs whole) + multi-page draft recreate + detail-page productCode/lotNo/expiryDate join.

original-7 handoff completeness: DONE 6/7 (1.jpg added; 2/3/4/6/7 prior); GAP=5.pdf (draft recreate). unreadable blocker 0. all final-promotion USER_INPUT_PENDING.

2H/2I frontend changes STILL UNCOMMITTED (3 files); 2T added no code change. py_compile/typecheck/build/checker(29/0) PASS.

Recommended next = FULL-UNSTRUCTURED-INVOICE-2U-5PDF-DRAFT-RECREATE-AND-HANDOFF. (Note: live route never run to confirm how the OCR pipeline actually segments 5.pdf's 22 pages — flag for 2U.)
