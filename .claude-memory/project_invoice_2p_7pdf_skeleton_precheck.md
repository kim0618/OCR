---
name: project_invoice_2p_7pdf_skeleton_precheck
description: "2P DONE — 7.pdf precheck; original is genuine 1-item quantity-only delivery statement (rowCount=1 correct), GT_WRITABLE_WITH_MINOR_REVIEW via representative_table; next=2Q-7PDF handoff"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2P precheck DONE (Claude Code @ `c:/OCR/OCR`, no code change). Mirrors [[project_invoice_2n_3pdf_skeleton_precheck]].

Decisive evidence: **read original 7.pdf directly** — LB/엘비아브노바 거래명세서, **1 genuine item row**: 품명 클리마토플란정 / 시리얼·로트No 0350623-231024-260811 / 단위 BOX / 수량 1,000. **Quantity-only delivery statement — table has NO 단가/금액 columns** (only 품명/시리얼·로트/단위/수량). No filler, no blank rows. So rowCount=1 is TRUE content, not a route miss.

거래_7 template (TPL-3AFD383E, invoice_statement): 10 regions, table region[9] box=[70,961,1513,72] = **THIN** (height 72, thinner than 3.pdf's 85), 0 columns → TEMPLATE_THIN_TABLE.

Headless real-builder smoke (Node TS strip, 2J harness): gtSkeletonVM=null → representative=backend_document_fields(1 row) → buildDraftGtDocument(useSkeletonCandidateRows=false) → draft tableRowsSource=representative_table, 1 row, raw/debug guard PASS, leak 0. draftStandardKeys=[itemName,lotNo,quantity].

Key structure: STANDARD_KEYS_PARTIAL — itemName/lotNo/quantity present; spec/productCode/expiryDate/unitPrice/amount GENUINELY ABSENT in source (quantity-only doc), not a mapping failure. Decision: GT_WRITABLE_WITH_MINOR_REVIEW. 2.pdf reuse=NO_NEED_REPRESENTATIVE_OK. minor review: 시리얼/로트No→lotNo (260811 expiry split?), 단위(BOX) handling, unitPrice/amount empty (source-absent), 총수량 header vs row qty.

Verified: py_compile/typecheck/build/checker(34/0) PASS. Single next = FULL-UNSTRUCTURED-INVOICE-2Q-7PDF-GT-DRAFT-USER-REVIEW-HANDOFF.

Sample GT status: 1.jpg/2.pdf(2K)/3.pdf(2O)/6.pdf(2M)/7.pdf(2P) GT-writable; 5.pdf needs review; **4.pdf = remaining blocker候補** (only unchecked sample left).
