---
name: project_invoice_2v_5pdf_multipage_precheck
description: "2V DONE — code-confirmed the OCR pipeline reads PDF FIRST PAGE ONLY (read_image doc[0]); 5.pdf page2~22 never OCR'd; next=2W-5PDF-MULTI-PAGE-OCR-PIPELINE-PATCH-PRECHECK"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2V DONE (Claude Code @ `c:/OCR/OCR`, docs-only precheck, no code). Builds on [[project_invoice_2u_5pdf_recreate]].

DEFINITIVE code-path finding (read-only): **`read_image` (ocr-server/main.py:929-945) rasterizes only `doc[0]` (PDF first page).** Code: `doc = fitz.open(stream=data, filetype='pdf'); page = doc[0]; pix = page.get_pixmap(dpi=200); return single image`. Docstring: "PDF인 경우 첫 페이지를 이미지로 변환". So the WHOLE `/ocr/extract` pipeline (OCR → extractors → tableRows) only ever sees page 1. No multi-page loop. Corroboration: `get_expected_row_count(5.pdf)=6` (verify_t28k_live.py) — the page1-only behavior is baked into the project baseline. This is GENERAL (affects all PDFs: 2/3/4/6/7 also page1-only — but those happen to be 1-page-of-interest docs, while 5.pdf and 4.pdf are multi-page).

Judgments: pipeline=PIPELINE_FIRST_PAGE_ONLY; page text=ONLY_PAGE_1_TEXT_PRESENT; release 6 rows=RELEASE_ROWS_PAGE1_ONLY; multi-page draft=MULTI_PAGE_DRAFT_NOT_FEASIBLE_CURRENT_PIPELINE (page2~22 OCR 입력 자산 전무); main/detail join=DETAIL_JOIN_NOT_FEASIBLE_CURRENT_PIPELINE (detail pages not even read; after patch → FEASIBLE_WITH_REVIEW); scope A+C=SCOPE_A_C_NEEDS_PAGE_EXTRACTION_PATCH. Live PaddleOCR route NOT run (code-path definitive → unnecessary).

So 5.pdf's ~70-row reality requires a backend multi-page OCR change (rasterize all pages → per-page OCR → merge) BEFORE any draft recreate. This is the binding upstream boundary, more upstream than a table-row-collector or draft-skeleton step.

Invariants restated: 6-row release NOT promoted as whole 5.pdf GT; no final promotion while pages missing. original-7 handoff DONE 6/7; 5.pdf pending multi-page OCR. 2H/2I 3 files still UNCOMMITTED; 2V added no code. py_compile/typecheck/build/checker(32/0) PASS.

Recommended next = FULL-UNSTRUCTURED-INVOICE-2W-5PDF-MULTI-PAGE-OCR-PIPELINE-PATCH-PRECHECK. (Caveat: any multi-page change to read_image is a CORE OCR-input change — CLAUDE.md flags main.py as do-not-modify-unless-asked; treat as precheck/design only.)
