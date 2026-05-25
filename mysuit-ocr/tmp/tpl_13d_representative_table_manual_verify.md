# TPL-13D Representative Table Manual Verify

> **Verification mode**: agent automation + human handoff.
> The agent confirmed the dev server is live, both `/template` and `/runocr`
> respond 200, the source-marker runner verifies TPL-13B/13C wiring is intact,
> and the full automatic pipeline (typecheck/build/runners/markdown contract)
> passes. The 9 visual scenarios require a human verifier — agent has no
> browser MCP. After running each, fill the table below in place.

## 1. Summary

- **dev server**: PASS — port 8089 already listening (user-managed), `GET /template` → 200 (33 KB shell, Korean labels rendered: "MySuit OCR", "템플릿 생성", "비정형 생성", "저장된 템플릿"), `GET /runocr` → 200 (21 KB shell).
- **manual UI verify 가능 여부**: partial — agent reached the routes over HTTP but cannot drive the actual RunOCR flow (file upload + OCR exec + result modal inspection). Visual scenarios are `BLOCKED-NEEDS-HUMAN`.
- **overall status**: **CONDITIONAL PASS** at contract-level. Automatic pipeline + source markers + HTTP probe all PASS. Visual confirmation in Preview/Custom/JSON deferred to the human verifier.
- **must-fix**: 없음 (source markers + automatic pipeline have no FAIL).
- **recommendation**: human runs the 9 scenarios below. If all PASS, Template table editing close-out. If any FAIL, do NOT patch in this task — create the appropriate `TPL-13E-*` follow-up.

## 2. Manual Checklist

> Run from a Chromium-based browser at `http://localhost:8089/runocr`.
> Pick (a) an `invoice_statement` template that defines `table.columns` for the
> Template-representative case, (b) a template with `unstructuredTables` for
> the Unstructured-representative case, (c) a template without either for the
> Backend-only case.

| scenario | status | notes |
|---|---|---|
| Template representative Preview | BLOCKED-NEEDS-HUMAN | Expect exactly **1 표**. Field-row block renders representative VM (user-defined columns). No separate "템플릿 테이블" section below. Markdown preview shows only the field summary table (no duplicate "## 템플릿 테이블" — Preview uses `toMarkdownForPreview` which omits `tableResultViewModels`). |
| Template representative Custom | BLOCKED-NEEDS-HUMAN | Expect exactly **1 표**. `customRepVM` = template VM → field-row table edit area shows user-defined columns. No separate "템플릿 테이블" Custom section below the field list. |
| Template representative JSON | BLOCKED-NEEDS-HUMAN | `tables[]` length === 1, `tables[0].columns` carries user-defined columns. `templateTables` key absent. `unstructuredTables` key absent. |
| Unstructured representative Preview | BLOCKED-NEEDS-HUMAN | Expect exactly **1 표** using unstructured columns. No separate "비정형 테이블" section when a table field row exists. |
| Unstructured representative Custom | BLOCKED-NEEDS-HUMAN | Expect exactly **1 표** using unstructured columns. No duplicate Custom section. |
| Unstructured representative JSON | BLOCKED-NEEDS-HUMAN | `tables[]` length === 1, `tables[0].key` matches the unstructured `tableKey`. `unstructuredTables` key absent. |
| Backend-only Preview | BLOCKED-NEEDS-HUMAN | Expect existing backend invoice table (canonical columns). Markdown stays identical to pre-TPL-13B. No extra "템플릿 테이블"/"비정형 테이블" section. |
| Backend-only Custom | BLOCKED-NEEDS-HUMAN | Existing backend table in field-row edit area. No standalone section. |
| Backend-only JSON | BLOCKED-NEEDS-HUMAN | Legacy `tables[]` (built from `docTableRows`) byte-identical to Clean JSON v1 contract. No `columns` metadata on entries (preserved fixture shape). No `templateTables` / `unstructuredTables`. |

### Handoff steps for the human verifier

1. With dev server already running on `http://localhost:8089`, open `/runocr`.
2. **Template case**: pick a saved template that has `table.columns` defined (template editor: 컬럼 정의 with non-empty columnKey/labelKo). Upload a corresponding image/PDF. Run OCR. Verify Preview/Custom/JSON.
3. **Unstructured case**: pick or create a template via 비정형 생성 with a defined table (UnstructuredBuilder). Upload + Run OCR.
4. **Backend-only case**: pick a template that has NO `table.columns` and NO unstructured tables (e.g., the original test templates pre-TPL-9B). Upload + Run OCR.
5. For each row above, replace `BLOCKED-NEEDS-HUMAN` with `PASS` / `FAIL` and add a note.
6. If you find a regression, do NOT patch here — open one of:
   - `TPL-13E-REPRESENTATIVE-TABLE-PREVIEW-FIX`
   - `TPL-13F-REPRESENTATIVE-TABLE-JSON-FIX`
   - `TPL-13G-REPRESENTATIVE-TABLE-CUSTOM-FIX`

## 3. Expected Result

- **representative priority**: `template_region_canonical` > `unstructured_definition` > `backend_document_fields` > `field_value_legacy`
- **tables[] count**: 1 per physical table (representative VM only)
- **templateTables**: omitted (TPL-13B dropped emission; type declaration retained for legacy shape compat)
- **unstructuredTables**: omitted (same reason)
- **Markdown Preview**: shows the field/value summary table only (TPL-13C `toMarkdownForPreview`). No `## 템플릿 테이블` / `## 비정형 테이블` section in the on-screen Markdown.
- **Export Markdown**: download (`내보내기`) and Copy (`복사`) emit the full Markdown including the representative `## 템플릿 테이블` or `## 비정형 테이블` section. (TPL-13C kept `toMarkdown()` for handlers.)

## 4. Findings

- **must-fix**: 없음.
- **nice-to-have**: 없음.
- **blocked**: 9 visual scenarios pending human verifier.
- **screenshots**: screenshot unavailable — `tmp/screenshots/` is created and ready for the human verifier to drop:
  - `tpl_13d_template_preview.png`
  - `tpl_13d_template_custom.png`
  - `tpl_13d_template_json.png`
  - `tpl_13d_unstructured_preview.png`
  - `tpl_13d_unstructured_json.png`
  - `tpl_13d_backend_preview.png`

## 5. Automatic Verification

- **typecheck**: PASS
- **build**: PASS (Next.js compiled successfully)
- **TPL-13C**: PASS (`[PREVIEW_REPRESENTATIVE_TABLE_DEDUP_FIX_TPL13C] PASS`)
- **TPL-13B**: PASS (`[TABLE_RESULT_REPRESENTATIVE_DEDUP_TPL13B] PASS`)
- **TPL-13D source-marker**: PASS (`[REPRESENTATIVE_TABLE_MANUAL_VERIFY_TPL13D] PASS`)
- **existing node runners**: 70/70 PASS (63 tagged PASS, 7 `PASS_WITH_SKIPPED_BACKUP`)
- **markdown contract**: PASS (Clean JSON v1 fixture 9건 + table_view_model_v1 fixture 9건, diffs=0 forbidden=0)
- **FAIL count**: 0

## 6. Final Decision

- **Template table editing close-out 가능 여부**: **CONDITIONAL — contract-level CLOSED, visual confirmation OPEN**. Source markers + automatic pipeline + HTTP probe confirm wiring is intact. Pending human visual verification of the 9 scenarios.
- **follow-up 필요 여부**: only if a visual scenario fails. Currently zero triggers.
- **추천 다음 작업**:
  - **Path A (recommended)**: human walks the 9 scenarios → updates §2 in place → if all PASS, **Template table editing FULL CLOSE-OUT**.
  - **Path B**: if a scenario reports a regression, open the matching `TPL-13E/F/G-FIX` phase.
  - **Path C**: skip visual verification (contract-level already locked) and move on to the next domain (RunOCR result UX polish, autofill expansion, etc.).
