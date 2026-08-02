---
name: project_invoice_2x_approval_handoff
description: 2X DONE — main.py multi-page OCR patch APPROVAL handoff (decision form ready); blocked on user approval to edit protected main.py; next=USER_APPROVAL_REQUIRED_FOR_2Y_MAIN_PY_PATCH
metadata: 
  node_type: memory
  type: project
  originSessionId: 131608a2-fe23-41eb-a4d0-6429d6f81591
---

FULL-UNSTRUCTURED-INVOICE-2X DONE (Claude Code @ `c:/OCR/OCR`, approval/decision handoff docs-only, no code, main.py untouched). Builds on [[project_invoice_2w_multipage_patch_precheck]].

Produced approval package for the multi-page OCR patch (2W design Option B): approval_target_summary, multi_page_application_policy (recommend **정책 C debug-only** — release unchanged so all rowCount fixtures + 4.pdf preserved), 2xb_patch_scope_approval, risk_and_rollback_plan, validation_checklist, **approval_decision_form (6 items, 승인/보류)**, report+summary, checker. py_compile/typecheck/build/checker(31/0) PASS. git before==final (main.py + backend untouched; 2H/2I 3 files still UNCOMMITTED).

Decision form (recommended): 1 main.py 수정 승인 / 2 read_image 유지+신규 read_images_for_ocr helper 승인 / 3 적용정책 = debug-only/gated / 4 2X-B scope 승인 / 5 collector·main-detail join 후속 분리 승인 / 6 final GT·variant 미생성 승인.

**Recommended next = USER_APPROVAL_REQUIRED_FOR_2Y_MAIN_PY_PATCH** — agent must NOT self-approve editing main.py (CLAUDE.md do-not-modify) nor decide the multi-page apply policy (affects 4.pdf). Awaiting user's explicit approval; on approval → FULL-UNSTRUCTURED-INVOICE-2Y-MAIN-PY-MULTI-PAGE-OCR-INPUT-PATCH; safer alt = 2Y-PROBE-NO-PROD.

Full-unstructured-invoice arc status: original-7 GT handoff done 6/7 (1.jpg/2/3/4/6/7); 5.pdf blocked on multi-page OCR (needs main.py change → user approval). 2H/2I frontend (skeleton + GT-draft) remain uncommitted across whole arc.
