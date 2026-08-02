---
name: project_invoice_2w_multipage_patch_precheck
description: "2W DONE — multi-page PDF OCR patch DESIGN (Option B: read_image kept + new read_images_for_ocr helper, page-local bbox merge); main.py untouched; next=2X-MAIN-PY-...-APPROVAL-HANDOFF"
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2W DONE (Claude Code @ `c:/OCR/OCR`, no_prod_modify patch DESIGN, no code). Builds on [[project_invoice_2v_5pdf_multipage_precheck]].

Designed the multi-page PDF OCR pipeline patch (NO main.py edit — it's CLAUDE.md do-not-modify):

- Current contract: `read_image(data,filename)->np.ndarray` (single image; PDF doc[0]); **5 callers** all expect single np.ndarray (preprocess ×3, /ocr/extract @1925, @2970). OCR = `ocr.ocr(ocr_img)` single image → `_parse_ocr_lines` → ocr_lines_raw (page-local bbox) → extractors (page-unaware, y-grouping).
- **Recommended design = Option B**: keep `read_image` unchanged + add `read_images_for_ocr(data,filename)->list[PageImage]`; only ocr_extract's multi-page-PDF path uses it; single-page returns [page0] = read_image-equivalent. Page metadata ADDITIVE (pageNo/pageIndex/totalPages/width/height/image/source). Rejected A (read_image→list; breaks 5 callers).
- Merge contract: **page-local bbox (NO global y offset — would collide with extractor y-grouping)** + page tags; page-grouped extraction.
- Downstream: MULTI_PAGE_OCR_PATCH_ONLY_NOT_ENOUGH_FOR_5PDF + TABLE_ROW_COLLECTOR_FOLLOWUP_REQUIRED + MAIN_DETAIL_JOIN_FOLLOWUP_REQUIRED (OCR input alone ≠ ~70-row draft).
- Regression matrix: 1.jpg/2/3/6/7 LOW; **4.pdf MEDIUM (it's a 2-page PDF — multi-page would change its result; needs gating)**; 5.pdf intentional. patch scope = 2X-B (helper + pageNo metadata + page-count route debug). validation plan keeps fixtures (1.jpg=28,2.pdf=13,3=1,4=1,6=6,7=1).

Invariants: 6-row release NOT promoted as whole 5.pdf GT; no final promotion while pages missing. main.py untouched; 2H/2I 3 files still UNCOMMITTED; 2W added no code. py_compile/typecheck/build/checker(34/0) PASS.

Recommended next = FULL-UNSTRUCTURED-INVOICE-2X-MAIN-PY-MULTI-PAGE-OCR-PATCH-APPROVAL-HANDOFF (design ready; remaining gate = human approval to edit protected main.py + decide multi-page apply policy/4.pdf regression).
