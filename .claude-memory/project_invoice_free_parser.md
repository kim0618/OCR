---
name: project-invoice-free-parser
description: "BACKEND-INVOICE-FREE series — unstructured 거래명세서 free parser, scalar-reuse fix, route-smoke method"
metadata: 
  node_type: memory
  type: project
  originSessionId: dc28e7c5-526c-4ef4-9b8c-c6961b6bba92
---

Initiative: an unstructured (비정형) 거래명세서 path via `ocr-server/extractors/invoice_statement_free.py`,
gated by env `USE_INVOICE_STATEMENT_FREE=1` (read at main.py import) and dispatched in `main.py`'s
`/ocr/extract` only when `not region_list and (not template_id or _is_unstructured_template)`. The free
parser succeeds only when its release threshold passes AND `doc_type == "invoice_statement"`; otherwise
main.py falls back to `extract_invoice_statement_fields` from `invoice_statement.py`.

Series state (as of 2026-05-28):
- 4B (frontend, committed): `mapOcrResponse.ts` maps `document_fields` scalar aliases (marker `INVOICE-PARITY-4B`).
- 4C (diagnosis): free success filled only `supplierBizNumber`; party/buyer/amount scalars empty.
- 4D (done): on free SUCCESS, reuse `extract_invoice_statement_fields(ocr_lines_raw)` to backfill empty
  party/summary scalars into `document_fields` (free value wins; table keys excluded). 1.jpg went 1→10/13
  scalars, kept 29 rows + `tableMeta.source=invoice_statement_free`. 2.pdf/3.pdf still fall back (release
  threshold unchanged). No circular import (invoice_statement.py never imports the free module).

**Why:** free parser owns the table contract (tableRows/tableMeta) but is weak at party/amount scalars;
the existing parser is strong at scalars. Reuse avoids duplicating extraction logic.

**How to apply:** Route smoke offline = in-process `fastapi.testclient.TestClient` + real PaddleOCR
(installed, v3.5.0 in `ocr-server/.venv`); POST samples in `mysuit-ocr/public/data/testsets/invoice_statement/`
(1.jpg/2.pdf/3.pdf) to `/ocr/extract` with `documentType=invoice_statement`. First OCR call ~90s (model load).
The route appends to `ocr-server/data/review_log.jsonl` as a normal side-effect — restore it with
`git checkout` after probing. See [[feedback-frontend-build-before-typecheck]] for the typecheck order.
