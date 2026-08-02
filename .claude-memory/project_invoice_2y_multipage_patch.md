---
name: project_invoice_2y_multipage_patch
description: "2Y DONE — REAL main.py patch (user-approved): added read_images_for_ocr helper + gated multi-page OCR debug; read_image untouched, gate OFF default; 5.pdf pageCount=22 confirmed; next=2Z-table-row-collector-precheck"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2Y DONE (Claude Code @ `c:/OCR/OCR`, **REAL backend patch, user-approved**). First code edit of the 2F→2Y arc that touches backend. Builds on [[project_invoice_2x_approval_handoff]].

Modified ONLY `ocr-server/main.py` (backup: `ocr-server/backup/main_before_FULL_UNSTRUCTURED_INVOICE_2Y_MAIN_PY_MULTI_PAGE_OCR_INPUT_PATCH.py`). Added (additive, after read_image ~line 951):
- `class PageImage` (pageNo/pageIndex/totalPages/width/height/image/source).
- `_render_pdf_page_to_bgr(page)` — same dpi=200 + RGBA/RGB→BGR as read_image.
- `read_images_for_ocr(data,filename)->list[PageImage]` — image→1 (reuses read_image), single-PDF→1 (page0 동치), multi-PDF→N.
- `_build_multi_page_ocr_debug(data,filename,ocr_engine)` — PDF: always record pageCount (fitz, cheap); env gate `INVOICE_MULTIPAGE_OCR_DEBUG` **OFF by default** → no OCR; ON → per-page ocr.ocr probe, compact evidence (lineCount + 60-char snippet) + evidenceTermsFound + hasPage2PlusEvidence, page_cap=30.
- route: after `ocr=get_ocr_engine()` compute `_mp_ocr_debug`; before `return response` attach `extract_debug.multiPageOcr` (additive).

**read_image UNCHANGED** (5 callers safe). release/tableRows/extractors/preprocess/ocr_lines/frontend UNTOUCHED. page-local bbox, no global y offset.

Validation: fitz rasterization probe (no PaddleOCR/main.py import) confirmed pageCounts: 1.jpg=1, 2.pdf=1, 3.pdf=1, **4.pdf=2, 5.pdf=22**, 6.pdf=1, 7.pdf=1 → 5.pdf pageCount=22 CONFIRMED; helper feeds all 22 pages to ocr.ocr when gate ON. page2~22 OCR **text** evidence = DEFERRED_LIVE_RUN (22-page PaddleOCR not run; gate OFF default → zero regression by construction; 4.pdf rowCount=1 preserved). raw/debug guard pass (60-char snippet only; no full_text/raw/base64/tokenBboxDebug). py_compile/typecheck/build/checker(37/0) PASS.

git status now: ocr-server/main.py (M) + 2H/2I 3 frontend files (still uncommitted) + new gtSkeletonCandidateViewModel.ts. Recommended next = FULL-UNSTRUCTURED-INVOICE-2Z-5PDF-MULTI-PAGE-TABLE-ROW-COLLECTOR-PRECHECK (accumulate per-page tableRows → ~70 rows; do gate-ON live OCR check there).
