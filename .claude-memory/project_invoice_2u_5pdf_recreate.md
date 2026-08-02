---
name: project_invoice_2u_5pdf_recreate
description: 2U DONE — 5.pdf mapped as 22pg/10-transaction bundle (~70 rows); current 6-row release=page1 only; scope=A+C recommended; handoff blocked → next=2V-5PDF-MULTI-PAGE-EXTRACTION-PRECHECK
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2U DONE (Claude Code @ `c:/OCR/OCR`, docs-only, no code). Builds on [[project_invoice_2t_1jpg_5pdf_gap_check]].

5.pdf structure mapped page-by-page (from 2T's full read): **22 pages = 12 main + 10 detail; 10 transactions (orders 462–471); ~70 main item rows.** Orders 471 & 470 each span 2 main pages. Detail pages give NO/제품코드(productCode)/제품명/수량/Lot No(lotNo)/유효일자(expiryDate); main pages give 품명/품목코드/수량/단가/금액. Current free→columnar release **6 rows = page1 (order 471) only**; page2~22 entirely missing.

Invariants restated: current 6-row release NOT promoted as whole 5.pdf GT; no final promotion while pages missing; no arithmetic; no raw/debug export.

GT scope recommended = **A+C** (file-unit single GT ~70 rows + orderNo as row metadata + detail-page productCode/lotNo/expiryDate joined to main rows). B (per-transaction split) deferred (needs manifest/schema policy); D (page1-only) rejected. userScopeDecisionNeeded=true (A vs B is a product call). main/detail join = **DETAIL_JOIN_FEASIBLE_WITH_REVIEW** (anchor = productCode 품목코드==제품코드; risks: lot-split 1:N e.g. FRT250T 20/100, detail NO order ≠ main order, qty-0 rows).

handoff judgment = **NEEDS_MULTI_PAGE_EXTRACTION_PRECHECK** (handoff NOT written — recreate plan only). Binding blocker: does the live OCR pipeline ingest all 22 pages or just page1? (release=6=page1 is strong circumstantial but live route NOT run.)

original-7 handoff: DONE 6/7; 5.pdf pending (multi-page precheck). unreadable blocker 0. all final-promotion USER_INPUT_PENDING. 2H/2I 3 files still UNCOMMITTED; 2U added no code. py_compile/typecheck/build/checker(36/0) PASS.

Recommended next = FULL-UNSTRUCTURED-INVOICE-2V-5PDF-MULTI-PAGE-EXTRACTION-PRECHECK.
