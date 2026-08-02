---
name: project_invoice_3bm_4pdf_promotion_check
description: "4.pdf Draft GT promotion check — decision NEEDS_MINOR_USER_FIX (lotNo + itemName), next = user lot fix"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0a3460cd-7501-467d-ae35-2c01aa7078ad
---

FULL-UNSTRUCTURED-INVOICE-3BM done (read-only review, no operational code change). Reviewed `RUN-468C3F55__draft_gt.json` (in user's Downloads) vs original `4.pdf`.

Decision: **NEEDS_MINOR_USER_FIX**. Structure/schema/금액/`tableExtraColumns`(unit=BOX, taxAmount=2,576,000) all正常; 금액 reconcile 25,760,000+2,576,000=28,336,000 OK; no hard leak (candidates carry short raw_ocr fragments only, draft-allowed).

Key finding: 4.pdf page2 (거래명세서) is **clean digital text** (page1 거래명세표 is degraded scan). Authoritative LOT from page2 = `0350623-231024-260811`. Draft JSON lotNo `0360623-231024-280811` is wrong in 2 segments (036→035, 280811→260811). Also page2 itemName = `클리마토플란정` (likely Climatoplan) vs JSON `클리마로플란정` (로→토 — verify).

**Why:** OCR LOT wandered (036/280811/200811 variants); only page2 clean text resolves it. **How to apply:** for any 4.pdf GT, trust page2 digital detail table over page1 scan.

Next = `USER_ACTION_REQUIRED_FIX_4PDF_LOT_NO_AND_REEXPORT_DRAFT_GT` (lotNo→`0350623-231024-260811`, optional itemName→클리마토플란정), then 3BN final precheck (strip candidates 51+18 on promotion). Artifacts in tmp/full_unstructured_invoice_3bm_*. Builds on [[project_invoice_2s_4pdf_gt_handoff]].
