---
name: project_invoice_2r_4pdf_blocker_confirmation
description: "2R DONE — 4.pdf is NOT an unreadable blocker (readable 2-page doc, page1 priced 1-item row); original-7 all GT-writable, 0 blockers; next=2S-4PDF handoff"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2R DONE (Claude Code @ `c:/OCR/OCR`, no code change). Closes the original-7 census.

DECISIVE finding (overturns prior hypothesis): **4.pdf is NOT an unreadable blocker.** Read original 4.pdf directly — it's a readable **2-page** document:
- page1 = full priced 거래명세표, 1 genuine item row: 클리마토플란정 / LotNo 0350623-231024-260811 / BOX / 수량 1,000 / **단가 28,336.00 / 공급가액 25,760,000 / 세액 2,576,000**, TOTAL footer 합계 28,336,000.
- page2 = LB quantity-only delivery statement == **7.pdf** (same transaction No.202407020013).

거래_4 template (TPL-FD07531C): table region[9] box=[276,806,1090,42] = **VERY_THIN** (height 42, thinnest of all), 0 columns → TEMPLATE_THIN_TABLE. rowCount=1 is correct (1 genuine readable row), not unreadable.

Headless real-builder smoke (2J harness): gtSkeletonVM=null → representative=backend_document_fields(1 row) → draft tableRowsSource=representative_table, 1 row, raw/debug guard PASS, leak 0. draftStandardKeys=[itemName,lotNo,quantity,unitPrice,amount] (5/8; spec/productCode/expiryDate empty). Decision: **GT_WRITABLE_WITH_MINOR_REVIEW**, isUnreadableBlocker=false. 2.pdf reuse=NO_NEED_REPRESENTATIVE_OK.

**Original-7 status: ALL 7 GT-writable, 0 unreadable blockers.** Handoff done: 2.pdf(2K)/3.pdf(2O)/6.pdf(2M)/7.pdf(2Q). 4.pdf handoff pending (→2S). 5.pdf needs review. 1.jpg writable.

Verified: py_compile/typecheck/build/checker(37/0) PASS. Single next = FULL-UNSTRUCTURED-INVOICE-2S-4PDF-GT-DRAFT-USER-REVIEW-HANDOFF. 4.pdf handoff minor review: pick page1(priced) as GT source over page2(=7.pdf qty-only); 시리얼/로트No→lotNo (260811 expiry split); 단위 BOX; TOTAL footer not a row; 단가 28,336.00 decimal (no arithmetic).
