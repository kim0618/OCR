# TPL-12F Row Override Manual UI Verify

> **Verification mode**: agent automation + human handoff.
> A CLI agent ran the dev server boot probe, the source-marker runner, and the
> full automatic pipeline. Pure-browser scenarios that require manual mouse
> interaction (drag, visual handle inspection, save-then-reload) are marked
> `BLOCKED-NEEDS-HUMAN` with handoff steps. A human verifier should re-run
> those scenarios and update this file in place.

## 1. Summary

- **dev server**: PASS — `next dev -p 8089 -H 0.0.0.0` booted in 1845 ms. `Ready` signal observed.
- **browser/UI verify 가능 여부**: partial. Agent reached `/template` over HTTP (200 OK, shell rendered, Korean labels visible). The TemplateAnnotator is `next/dynamic` → server bails to CSR as expected; client-side React + canvas drag cannot be driven without a browser MCP. Manual drag-driven scenarios are deferred to a human verifier.
- **overall status**: **CONDITIONAL PASS**. Source markers + compatibility sweep + automatic pipeline all PASS. Visual confirmation of handle visibility / hit-area / drag UX / save-reload round-trip in localStorage is `BLOCKED-NEEDS-HUMAN`.
- **manual scenarios**: 2/9 PASS via HTTP probe, 7/9 BLOCKED-NEEDS-HUMAN.
- **automatic checks**: typecheck PASS / build PASS / TPL-12D compat PASS / TPL-12F source-marker PASS / existing 65 runners PASS / markdown contract PASS / FAIL 0건.
- **must-fix**: 없음.
- **nice-to-have**: 없음 (TPL-12C에서 보류된 `선택 행 reset`은 별도 phase 후보로 이미 기록됨).
- **recommendation**: `rowOverrides` MVP는 contract-level close-out 가능. 사용자 시각 검증 한 번만 마치면 full close-out 처리. `TPL-12G/H/I-FIX`는 현재 트리거 없음.

## 2. Environment

- **OS**: Windows 10 Pro 10.0.19045 (per harness header)
- **node**: v24.14.0
- **npm**: bundled with node 24
- **dev command**: `npm run dev` → `next dev -p 8089 -H 0.0.0.0`
- **URL**: `http://localhost:8089/template` (agent HTTP probe), browser checklist also uses the same URL
- **browser/tool**: agent — `curl` only. human — Chromium-based browser (Chrome/Edge) recommended
- **sample/template used**: agent — none (no saved templates were present when probed; "아직 저장된 템플릿이 없습니다." rendered). human — pick any PDF/image with a table; e.g. `mysuit-ocr/public/data/testsets/invoice_statement/` 샘플 1장

## 3. Manual Checklist

| scenario | status | notes |
|---|---|---|
| Template tab access | PASS | `GET /template` → 200 OK, 33 KB, layout shell rendered, Korean menu "템플릿 생성 / 비정형 생성 / 저장된 템플릿" visible. TemplateAnnotator dynamically imported (`next/dynamic`) — CSR bailout is the expected and documented Next.js behavior, not an error. |
| table region select | BLOCKED-NEEDS-HUMAN | Requires file upload + canvas drag → cannot drive from CLI. Source markers confirm TemplateRightPanel still wires `selected.fieldType === "table"` block (테이블필드 mode + selected.id 표시). |
| rowTemplate create | BLOCKED-NEEDS-HUMAN | Requires canvas drag. Source markers confirm `drawRowTemplate` drag type, `rowTemplateTargetId` plumbing, `buildTableRows` regeneration remain wired. |
| row adjust toggle | BLOCKED-NEEDS-HUMAN | Requires button click. Source markers confirm: "행 개별 조정 시작/종료" label present in TemplateRightPanel, `rowAdjustTargetId` state + setter forwarded to children, mutually-exclusive `setRowTemplateTargetId(null)` / `setColGuideTargetId(null)` calls on toggle. |
| boundary handles visible | BLOCKED-NEEDS-HUMAN | Requires visual rendering. Source markers confirm: `data-role="row-boundary-handle"` element with `height: 12px`, yellow band (`rgba(250,204,21,0.18)`) + dashed amber border, ns-resize cursor, zIndex 36. Rendered only when `isRowAdjustActive === true`. |
| drag row height | BLOCKED-NEEDS-HUMAN | Requires pointer drag. Source markers confirm: `setRowBoundaryDragBoth({tableId, rowIndex, startY, startHeight})` on pointerDown, `applyRowBoundaryDragFrame` math (`newHeight = max(MIN_ROW_HEIGHT, startHeight + dy)`), `rowOverrides` upsert (preserves existing y/locked), `setRegions` commit of materialized rows + merged overrides. |
| reset all overrides | BLOCKED-NEEDS-HUMAN | Requires button click. Source markers confirm: "모든 행 조정 초기화" button (`clearRowOverrides` handler), disabled when `overrides.length === 0`, "조정된 행 N개" count label updates from `selected.table?.rowOverrides`. |
| save/reload | BLOCKED-NEEDS-HUMAN | Requires manual save + page reload. TPL-12B byte-level round-trip is already locked by `tmp/check_row_override_save_load_tpl12b.mjs` (9 smoke cases PASS) and TPL-12D compatibility sweep (idempotent export, columns + overrides coexist). Human verifier should open the saved template again and confirm visible row heights reflect the override. |
| existing features regression | PASS (markers) / BLOCKED-NEEDS-HUMAN (visual) | Source markers confirm `drawRowTemplate` / `colGuideTargetId` / "컬럼 정의" / "세로 가이드 찍기" / "행 템플릿 해제" all still wired. `clearTableMeta` clears rowOverrides alongside rowTemplate/rows. Visual confirmation deferred to human. |

### Handoff steps for the human verifier

Run from `mysuit-ocr/`:

```
npm run dev
# wait for "Ready in ...ms" — port 8089 unless overridden
```

Open `http://localhost:8089/template` and walk the 7 BLOCKED scenarios above. After each, update the `status` cell to `PASS`, `FAIL`, or `BLOCKED` with a note. If you find a regression, do NOT patch in this task — create one of:

- `TPL-12G-ROW-OVERRIDE-UI-FIX` — handle visibility / cursor / overlap bug
- `TPL-12H-ROW-OVERRIDE-SAVE-RELOAD-FIX` — save/load drift
- `TPL-12I-ROW-OVERRIDE-HIT-AREA-TUNE` — drag hit-area too small / too large

## 4. Findings

- **must-fix**: 없음.
- **nice-to-have**: 없음 (선택 행 reset 부재는 이미 TPL-12C 보고서에 follow-up 후보로 기록).
- **blocked**: 7 manual visual scenarios pending human verifier (see §3).
- **screenshots**: screenshot unavailable — CLI agent has no browser. `tmp/screenshots/` directory is created and ready for the human verifier to drop:
  - `tpl_12f_row_adjust_toggle.png`
  - `tpl_12f_row_boundary_handles.png`
  - `tpl_12f_row_drag_after.png`
  - `tpl_12f_reset_after.png`

## 5. Automatic Verification

- **typecheck**: PASS
- **build**: PASS (Next.js compiled successfully, 16.7s)
- **TPL-12D compatibility**: PASS (`[ROW_OVERRIDE_COMPATIBILITY_SWEEP_TPL12D] PASS`, 9 simulation cases + source-marker + backend + lib + git sweep)
- **existing node runners**: 65/65 PASS (58 tagged PASS, 7 `PASS_WITH_SKIPPED_BACKUP` — all phase-aware skips intact)
- **markdown contract**: PASS (Clean JSON v1 fixture 9건 + table_view_model_v1 fixture 9건, diffs=0 forbidden=0)
- **TPL-12F source-marker**: PASS (`[ROW_OVERRIDE_MANUAL_UI_VERIFY_TPL12F] PASS`)
- **FAIL count**: 0

## 6. Final Decision

- **close-out 가능 여부**: **CONDITIONAL — contract-level CLOSED, visual confirmation OPEN**. 자동 검증과 source-marker로 코드 wiring은 잠금. 사용자 한 번의 시각 검증 후 full close-out.
- **follow-up 필요 여부**: 시각 검증 후 사항 발견 시에만. 현재 트리거 0건.
- **추천 다음 작업**:
  - **Path A (recommended)**: 사람이 위의 핸드오프 단계를 한 번 돌리고 §3 표를 PASS로 갱신 → TPL-12 series full close-out.
  - **Path B**: 시각 검증 없이 다른 phase로 진행 — contract는 이미 잠겨 있어 functional regression 위험은 매우 낮음. UX 발견 사항은 별도 TPL-12G/H/I로 분리.
