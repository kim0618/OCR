## BACKEND-STRUCTURE-2A Main Route Ownership Precheck

### 1. Summary
- Production code modified: NO. This report is read-only analysis plus a tmp checker.
- Scope: `ocr-server/main.py` line-level route/function ownership, with read-only context from `preprocess.py`, `preprocessing_policy.py`, `extractors/invoice_statement.py`, `extractors/ocr_lines.py`, backend-facing Next API guard state, and public testset links.
- Route count: 14 FastAPI routes plus 1 startup event.
- Biggest high-risk route: `POST /ocr/extract` (`ocr_extract`, lines 1894-2883). It owns upload decode, OCR engine calls, template branch, full OCR branch, invoice_statement extraction, `document_fields`, `tableRows`, image payloads, debug metadata, and review log side effects.
- Low-risk split candidates: constants/storage path mapping, JSON stores for templates/history/review log, `GET /health`, and `GET /templates`.
- Recommended first actual work: `BACKEND-STRUCTURE-2B-MAIN-CONSTANTS-STORAGE-PRECHECK`.
- Next phase: storage/precheck first, then template storage extraction, then review-log storage extraction. Keep OCR extraction as a final high-risk phase.

### 2. main.py Route Map
| method | path | function | line range | role | downstream deps | side effects | risk | recommended owner |
|---|---|---|---|---|---|---|---|---|
| startup | app startup | `_warmup_ocr` | 558-573 | Background OCR engine warmup. | `get_ocr_engine`, PaddleOCR | Creates background thread, initializes global engine. | HIGH | `app/main.py` startup + `core/ocr_engine.py` |
| GET | `/health` | `health` | 702-704 | Liveness check. | none | none | LOW | `api/health_routes.py` |
| POST | `/login` | `login` | 710-739 | Local JSON user login compatibility response. | `_load_json`, `USERS_FILE`, uuid | Reads `data/users.json`. | MEDIUM | `api/auth_routes.py`, `storage/user_store.py` |
| GET | `/templates` | `template_list` | 750-753 | List saved templates. | `_load_json`, `TEMPLATES_FILE` | Reads `data/templates.json`. | MEDIUM | `api/template_routes.py`, `storage/template_store.py` |
| POST | `/templates` | `template_save` | 756-783 | Upsert template by id/name. | `_load_json`, `_save_json`, uuid | Writes `data/templates.json`; stores request body under `template_json`. | MEDIUM | `api/template_routes.py`, `services/template_service.py`, `storage/template_store.py` |
| DELETE | `/templates/{template_id}` | `template_delete` | 786-791 | Delete template by id. | `_load_json`, `_save_json` | Writes `data/templates.json`. | MEDIUM | `api/template_routes.py`, `storage/template_store.py` |
| POST | `/ocrSelect` | `ocr_select` | 797-800 | Legacy history list. | `_load_json`, `HISTORY_FILE` | Reads `data/history.json`. | MEDIUM | `api/history_routes.py`, `storage/history_store.py` |
| POST | `/ocrInsert` | `ocr_insert` | 803-819 | Legacy history insert. | `_load_json`, `_save_json`, uuid | Writes `data/history.json`. | MEDIUM | `api/history_routes.py`, `storage/history_store.py` |
| POST | `/ocrUpdate` | `ocr_update` | 822-837 | Legacy history update. | `_load_json`, `_save_json` | Writes `data/history.json`. | MEDIUM | `api/history_routes.py`, `storage/history_store.py` |
| POST | `/ocrDelete` | `ocr_delete` | 839-848 | Legacy history delete. | `_load_json`, `_save_json` | Writes `data/history.json`. | MEDIUM | `api/history_routes.py`, `storage/history_store.py` |
| POST | `/ocr/feedback` | `ocr_feedback` | 855-884 | Store human correction event. | `_append_review_log` | Appends `data/review_log.jsonl`. | MEDIUM | `api/review_routes.py`, `storage/review_log_store.py` |
| GET | `/ocr/review-log` | `ocr_review_log` | 888-920 | Read/filter operational review log. | `REVIEW_LOG_FILE`, json | Reads `data/review_log.jsonl`. | MEDIUM | `api/review_routes.py`, `storage/review_log_store.py` |
| POST | `/preprocess` | `preprocess_image` | 957-976 | Return preprocessed PNG stream and headers. | `read_image`, `preprocess`, `encode_image` | CPU image work; no file write. | HIGH | `api/preprocess_routes.py`, `services/preprocess_service.py`, `core/image.py` |
| POST | `/preprocess/info` | `preprocess_info` | 978-984 | Return preprocess metadata. | `read_image`, `preprocess` | CPU image work; no file write. | HIGH | `api/preprocess_routes.py`, `services/preprocess_service.py` |
| POST | `/preprocess/corners` | `preprocess_corners` | 1593-1636 | Detect normalized document corners. | `read_image`, OpenCV contour logic | CPU image work; no file write. | HIGH | `api/preprocess_routes.py`, `core/image.py` |
| POST | `/ocr/extract` | `ocr_extract` | 1894-2883 | Main OCR execution and response mapping. | `read_image`, `get_ocr_engine`, template store, OCR parser, document classifier, receipt/invoice/finance extractors, preprocessing policy, review log | OCR CPU work, reads templates/manifests, appends review log in full OCR path. | HIGH | final phase: `api/ocr_routes.py` + `services/ocr_service.py` |
| POST | `/ocr/revalidate` | `ocr_revalidate` | 2884-2952 | Re-OCR user-specified bbox regions. | `read_image`, `get_ocr_engine`, `_parse_ocr_lines`, OpenCV crop/enhance | OCR CPU work; no file write. | HIGH | `api/ocr_routes.py`, `services/revalidate_service.py`, `core/ocr_engine.py` |

### 3. OCR Extract Flow
1. Request enters `POST /ocr/extract` with multipart `file` and controls: `template_id`, `regions`, `corners`, `model_id`, `tableExpectedColumns`, `tableBounds`, `columnGuides`, `documentType`, `debugPreprocessing`, `qualityTagsJson`, `autoApplyPreprocessing`.
2. The route reads bytes, calls `read_image`; PDF input is rendered through PyMuPDF first page, image input is decoded with OpenCV.
3. It builds `original_image` base64 preview, lazily acquires PaddleOCR through `get_ocr_engine`, parses inline `regions`, or loads template metadata/regions from `data/templates.json`.
4. Template branch (`region_list` present): crop OCR is run per field via `_ocr_crop_region`; table regions go through `_ocr_table_region`, except `invoice_statement` table regions are deferred.
5. Template branch classifies document type from region text unless explicit `documentType` or template metadata wins. For `invoice_statement`, it also runs full image OCR to populate `ocr_lines_raw` for parser input.
6. Full OCR branch (`region_list` absent): document corners are supplied or auto-detected, orientation is corrected, display/OCR images are prepared, PaddleOCR runs on the OCR image, `_parse_ocr_lines` converts OCR output, and raw fields/full text are assembled.
7. Full OCR branch classifies document type, runs receipt/bank/form field extraction through `extract_receipt_fields`, conditional upper/amount/handwritten-total re-OCR helpers, then repairs top fields from text lines.
8. Response skeleton is built: `fields`, `full_text`, `receipt_fields`, `processing_time`. Optional `processed_image`, `original_image`, `extract_debug`, `doc_type`, `ocr_lines`, `total_amount_review_*`, `finance_fields`, `preprocessingDebug`, and `templateOrientationDebug` are added depending on branch/doc type.
9. For `doc_type == "invoice_statement"`, the route parses table controls, derives template table bounds/column guides, optionally reads `public/data/testsets/invoice_statement/manifest.json`, calls `extract_invoice_statement_fields`, and writes `document_fields` including parser-provided `tableRows` and `tableMeta`.
10. Deferred template table fields are resolved from `document_fields.tableRows`; if missing, `_ocr_table_region` fallback runs.
11. Full OCR path appends an `auto_extract` review event through `_build_auto_extract_log` and `_append_review_log` on a best-effort basis.
12. Debug/auto-apply preprocessing path calls `_build_preprocessing_debug`, which imports `preprocessing_policy` and can read public testset manifests. It may replace `receipt_fields` only under limited receipt auto-apply rules.

High-risk response keys: `fields`, `full_text`, `receipt_fields`, `document_fields`, `document_fields.tableRows`, `processed_image`, `original_image`, `extract_debug`, `doc_type`, `ocr_lines`, `preprocessingDebug`, `templateOrientationDebug`, `total_amount_review_required`.

### 4. Template Route Flow
- `GET /templates`: loads `ocr-server/data/templates.json` and returns `{"resultMap":{"templateList": rows}}`.
- `POST /templates`: reads JSON body, requires `templateName` or `template_name`, generates `TPL-XXXXXXXX` when absent, stores complete body as `template_json`, upserts by `template_id` or `template_name`, writes the full list.
- `DELETE /templates/{template_id}`: filters `templates.json` by `template_id`, writes the list, returns success.
- Ownership note: storage and CRUD can be split before OCR route splitting, but `template_json` must remain pass-through because RunOCR template metadata, regions, table `colX`, `rowOverrides`, document type, and frontend editor state depend on it.

### 5. Preprocess Route Flow
- `read_image`: shared helper for `/preprocess`, `/preprocess/info`, `/preprocess/corners`, `/ocr/extract`, `/ocr/revalidate`. It accepts PDF or image bytes and returns BGR numpy image.
- `POST /preprocess`: `read_image` -> `preprocess(img)` -> `encode_image` -> `StreamingResponse(image/png)` with preprocess headers.
- `POST /preprocess/info`: `read_image` -> `preprocess(img)` -> metadata JSON.
- `POST /preprocess/corners`: `read_image` -> grayscale/threshold/morphology/contour corner detection -> normalized corner list fallback to 5%-95% rectangle.
- `_build_preprocessing_debug`: not a route, but route-adjacent. It calls `preprocessing_policy`, reads quality tags/expected rows/table expected columns from public testsets manifests, compares variants, and can drive limited auto-apply in `/ocr/extract`.

### 6. Review / Feedback Flow
- `POST /ocr/feedback`: accepts human correction JSON and appends a `human_correction` event into `ocr-server/data/review_log.jsonl`. It does not write ground truth.
- `GET /ocr/review-log`: reads `review_log.jsonl`, filters by `status` and `image_id`, returns latest `limit` entries.
- `/ocr/extract`: full OCR path appends `auto_extract` events through `_build_auto_extract_log`; failures are swallowed to avoid breaking OCR responses.
- Recommended ownership: keep as operational/review feature, separate from Test tab and ground-truth API removal. Candidate split: `api/review_routes.py`, `services/review_service.py`, `storage/review_log_store.py`.

### 7. main.py Internal Helper Ownership
| helper/function | line range | role | callers | side effects | target owner | risk |
|---|---|---|---|---|---|---|
| `_parse_amounts` | 76-111 | Amount token parsing. | receipt extraction helpers in `main.py` | none | `services/ocr/receipt_amounts.py` or existing extractor module | MEDIUM |
| `_repair_remaining_top_fields_from_text_lines` | 113-205 | Repairs top receipt/business fields from OCR text lines. | `ocr_extract` | mutates target dict | `services/ocr/receipt_service.py` | HIGH |
| `_extract_fields_from_rows` | 207-320 | Extracts structured fields from grouped rows. | `extract_receipt_fields` | mutates target dict | `services/ocr/receipt_service.py` | HIGH |
| `_apply_doc_type_amount_policy` | 322-419 | Applies doc-type amount suppression/review policy. | `extract_receipt_fields` | mutates fields/debug | `services/ocr/amount_policy.py` | HIGH |
| `extract_receipt_fields` | 420-557 | Main receipt/bank/form field extraction wrapper. | `ocr_extract` | mutates debug | `services/ocr/receipt_service.py` | HIGH |
| `_warmup_ocr` | 559-573 | Startup background OCR engine warmup. | FastAPI startup | initializes global OCR engine | `core/ocr_engine.py` + app startup | HIGH |
| `_append_review_log` | 612-619 | JSONL append helper. | `/ocr/feedback`, `/ocr/extract` | writes `review_log.jsonl` | `storage/review_log_store.py` | MEDIUM |
| `_build_auto_extract_log` | 621-687 | Builds operational auto_extract event. | `/ocr/extract` | none | `services/review_service.py` | MEDIUM |
| `read_image` | 925-948 | Decode image/PDF upload bytes. | preprocess routes, OCR routes | CPU/PDF decode | `core/image.py`, `core/pdf.py` | HIGH |
| `encode_image` | 950-955 | BGR numpy to PNG/JPEG bytes. | `/preprocess` | none | `core/image.py` | LOW |
| `get_ocr_engine` | 989-1013 | Lazy PaddleOCR singleton. | OCR routes/helpers/startup | global singleton allocation | `core/ocr_engine.py` | HIGH |
| `_ocr_crop_region` | 1015-1044 | OCR one rectangular region. | `/ocr/extract` template path | OCR CPU work | `core/ocr_engine.py`, `services/template_ocr.py` | HIGH |
| `_detect_upper_block_bbox` | 1046-1168 | Heuristic upper block bbox detection. | `/ocr/extract` full path | none | `services/ocr/receipt_blocks.py` | HIGH |
| `_detect_amount_block_bbox` | 1170-1265 | Heuristic amount block bbox detection. | `/ocr/extract` full path | none | `services/ocr/receipt_blocks.py` | HIGH |
| `_detect_handwritten_total_bbox` | 1267-1341 | Heuristic handwritten total bbox. | `/ocr/extract` full path | none | `services/ocr/receipt_blocks.py` | HIGH |
| `_extract_handwritten_total_from_lines` | 1343-1398 | Parse handwritten total re-OCR lines. | `/ocr/extract` full path | none | `services/ocr/amount_policy.py` | HIGH |
| `_reocr_block` | 1400-1500 | Crop/enhance/re-OCR selected block. | `/ocr/extract` full path | OCR CPU work | `core/ocr_engine.py`, `services/ocr/reocr_service.py` | HIGH |
| `_ocr_table_region` | 1502-1591 | Table crop OCR and row/cell grouping. | `/ocr/extract` template path/fallback | OCR CPU work | `core/table.py`, `services/template/table_ocr.py` | HIGH |
| `_build_preprocessing_debug` | 1639-1888 | Debug/auto-apply preprocessing comparison. | `/ocr/extract` | reads public testset manifests through `preprocessing_policy`; may pass raw applied fields to caller | `services/preprocess_debug_service.py` | HIGH |

### 8. Current Coupling / Risk Notes
- `main.py` mixes API routes, storage constants, JSON file stores, OCR engine lifecycle, PDF/image decoding, receipt extraction, invoice extraction orchestration, table crop OCR, preprocessing policy, and review log writes.
- `POST /ocr/extract` is not only a controller; it owns response schema assembly and many production policies.
- `templates.json` is a pass-through contract with frontend template editor. Restructuring storage is safer than normalizing template JSON now.
- `preprocessing_policy.py` reads `public/data/testsets` manifests; public testsets are still backend policy inputs, not just removed Test tab assets.
- `review_log.jsonl` is operational telemetry/correction storage. It is separate from ground truth and should not be removed as part of Test cleanup.
- Invoice coupling is especially sensitive: `ocr_extract` passes `table_expected_columns`, `table_bounds`, and `column_guides` into `extract_invoice_statement_fields`; parser output becomes `document_fields.tableRows`.

### 9. Proposed Target Backend Structure
```text
ocr-server/
  app/
    main.py
    api/
      health_routes.py
      auth_routes.py
      history_routes.py
      ocr_routes.py
      preprocess_routes.py
      review_routes.py
      template_routes.py
    schemas/
      auth.py
      history.py
      ocr.py
      preprocess.py
      review.py
      template.py
      response.py
    services/
      ocr/
        extract_service.py
        receipt_service.py
        invoice_service.py
        reocr_service.py
        revalidate_service.py
      preprocess/
        preprocess_service.py
        debug_service.py
      review/
        review_service.py
      template/
        template_service.py
    core/
      image.py
      pdf.py
      ocr_engine.py
      table.py
    storage/
      json_store.py
      history_store.py
      review_log_store.py
      template_store.py
      user_store.py
    config/
      paths.py
    utils/
      text_normalize.py
      regex_patterns.py
```
Reason: split route ownership from storage and CPU-heavy OCR services while preserving the current response contract until dedicated fixture smoke tests exist.

### 10. Refactor Candidate Matrix
| candidate | current location | target owner | risk | blocker | recommended phase |
|---|---|---|---|---|---|
| DATA path constants | `main.py` 578-583, 745 | `config/paths.py` | LOW | Need import smoke and no cwd assumptions. | 2B |
| Template JSON read/write wrapper | `main.py` 750-791 | `storage/template_store.py` | MEDIUM | Must preserve pass-through `template_json`. | 2C |
| Review log append/read wrapper | `main.py` 612-687, 855-920 | `storage/review_log_store.py` | MEDIUM | Must preserve best-effort append semantics. | 2D |
| Health route | `main.py` 702-704 | `api/health_routes.py` | LOW | Need app router include smoke. | 3A |
| History CRUD routes | `main.py` 797-848 | `api/history_routes.py`, `storage/history_store.py` | MEDIUM | Legacy response names must remain. | 3B |
| Login route/storage | `main.py` 710-739 | `api/auth_routes.py`, `storage/user_store.py` | MEDIUM | Local JSON auth compatibility. | 3C |
| Preprocess routes | `main.py` 957-984, 1593-1636 | `api/preprocess_routes.py`, `services/preprocess_service.py` | HIGH | Shared `read_image` and OpenCV/PDF path. | 5A |
| OCR engine singleton | `main.py` 989-1013 | `core/ocr_engine.py` | HIGH | Startup warmup and lazy import behavior. | 5B |
| Template crop/table OCR helpers | `main.py` 1015-1044, 1502-1591 | `services/template/table_ocr.py`, `core/table.py` | HIGH | Template RunOCR and invoice deferred table logic. | 6A |
| Receipt helpers | `main.py` 76-557, 1046-1500 | `services/ocr/receipt_service.py` | HIGH | Field names, review codes, debug schema. | 6B |
| Invoice orchestration in `ocr_extract` | `main.py` 2550-2740 approx | `services/ocr/invoice_service.py` | HIGH | `document_fields.tableRows` exact shape. | 7A precheck only |
| `ocr_extract` route thin controller | `main.py` 1894-2883 | `api/ocr_routes.py`, `services/ocr/extract_service.py` | HIGH | Requires fixture rowCount/shape smoke. | 8A/8B |

### 11. Do Not Move Yet
- `POST /ocr/extract`: too much response-shape and parser coupling. Move only after route smoke, fixture smoke, `document_fields/tableRows` contract, and frontend RunOCR smoke exist.
- `extract_receipt_fields` and amount policy helpers: field names and review flags are fragile and encoded in frontend display.
- `extract_invoice_statement_fields` call site and table-bound/column-guide preparation: table row mapping and invoice fixtures depend on exact behavior.
- `_build_preprocessing_debug` and `preprocessing_policy.py` linkage: public testset manifest reads need a separate policy/storage precheck.
- OCR engine singleton/startup warmup: PaddleOCR initialization side effects and CPU flags are production-sensitive.
- `templates.json` schema transformation: do not normalize or migrate in a route split phase.

### 12. Verification Strategy
- Python import smoke: import new modules without initializing PaddleOCR where possible.
- FastAPI route smoke: ensure `/health`, `/templates`, `/preprocess/info`, `/ocr/revalidate`, `/ocr/extract` are still registered.
- `/templates` CRUD smoke: list, save a temporary template, delete it, restore data file or use isolated temp store in later phase.
- `/preprocess` smoke: representative image/PDF decode and response headers.
- `/ocr/extract` fixture smoke: representative receipt, bank slip, and invoice_statement samples.
- Invoice statement rowCount smoke: existing seven fixture row counts exact where available.
- `document_fields/tableRows` shape smoke: assert keys, row arrays, `tableMeta`, and canonical columns.
- RunOCR frontend smoke: typecheck/build and manual route invocation through `src/app/api/ocr-extract`.
- Existing node runners and markdown contract checks.
- `src/lib` absent and `@/lib` import 0 guard.

### 13. Recommended Next Phases
1. `BACKEND-STRUCTURE-2B-MAIN-CONSTANTS-STORAGE-PRECHECK`
   - Tool: Codex.
   - Goal: identify path constants and JSON store boundaries only.
   - Modify candidates: none in precheck; later `config/paths.py`, `storage/json_store.py`.
   - Forbidden: `/ocr/extract`, invoice parser, template data migration.
   - Verification: import smoke, no route behavior change, typecheck/build.
   - Risk: LOW.
   - Rollback: remove new storage/config modules if extraction later fails.
2. `BACKEND-STRUCTURE-2C-TEMPLATE-STORAGE-EXTRACT`
   - Tool: Codex.
   - Goal: move template read/write helpers behind storage wrapper while route response stays identical.
   - Modify candidates: `main.py` template route call sites plus new `storage/template_store.py`.
   - Forbidden: `templates.json` content/schema migration.
   - Verification: `/templates` list/save/delete smoke, template RunOCR smoke, typecheck/build.
   - Risk: MEDIUM.
   - Rollback: restore direct `_load_json/_save_json` call sites.
3. `BACKEND-STRUCTURE-2D-REVIEW-LOG-STORAGE-EXTRACT`
   - Tool: Codex.
   - Goal: isolate `_append_review_log` and review-log read/filter.
   - Modify candidates: review storage module and route call sites.
   - Forbidden: ground-truth route/data changes.
   - Verification: feedback append smoke against disposable log or backed-up log, review-log query smoke.
   - Risk: MEDIUM.
   - Rollback: restore helper functions in `main.py`.
4. `BACKEND-STRUCTURE-5A-PREPROCESS-ROUTES-SPLIT-PRECHECK`
   - Tool: Codex or Claude Code.
   - Goal: precheck `read_image`, preprocess, corners, and preprocessing policy dependencies.
   - Modify candidates: none until precheck passes.
   - Forbidden: public testsets archive/removal.
   - Verification: image/PDF preprocess smoke and manifest policy smoke.
   - Risk: HIGH.
5. `BACKEND-STRUCTURE-6A-OCR-EXTRACT-ROUTE-PRECHECK`
   - Tool: Codex.
   - Goal: freeze `/ocr/extract` request/response contract and fixture matrix before any split.
   - Modify candidates: none.
   - Forbidden: direct code movement.
   - Verification: full RunOCR/invoice/receipt smoke baseline.
   - Risk: HIGH.
6. `BACKEND-STRUCTURE-6B-OCR-EXTRACT-THIN-CONTROLLER`
   - Tool: Claude Code or Codex after 6A.
   - Goal: only after baseline fixtures, move orchestration behind service with zero response delta.
   - Modify candidates: `main.py`, new `api/ocr_routes.py`, `services/ocr/extract_service.py`.
   - Forbidden: parser/extractor behavior changes.
   - Verification: all fixture, route, frontend, and shape checks.
   - Risk: HIGH.

### 14. Zero-touch Verification
- Production modified: NO. Only `tmp/backend_structure_2a_main_route_ownership_precheck.md`, `tmp/check_backend_main_route_ownership_2a.py`, and the requested log files were created for this task.
- Files moved: NO.
- Typecheck: PASS (`npm run typecheck` / `tsc --noEmit`).
- Build: PASS (`npm run build`; route list excludes `/test` and `/api/test-images`).
- Static check: PASS (`[BACKEND_MAIN_ROUTE_OWNERSHIP_2A] PASS`).
- FAIL count: 0.
- Known warning: build stderr emitted `ESLint: nextVitals is not iterable`, while `next build` completed successfully and exited 0.
