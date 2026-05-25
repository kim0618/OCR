# Frontend Validation Baseline Repair Precheck 2026-05-22

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `CODEX_FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- `src` 수정: 없음
- static check script 수정: 없음
- markdown runner/fixture 수정: 없음
- backup 생성/복원: 없음
- 파일 이동/import 수정/rename/refactor: 없음

## 3. 생성 파일
- `tmp/codex_frontend_validation_baseline_repair_precheck.py`
- `docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.md`
- `docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.json`
- `docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- 2A/2C/3B/4A/4B/5A static checks
- `tmp/codex_markdown_contract_fixture_lock.py`
- 5A closeout report
- `mysuit-ocr/backup` and expected `C:\OCR\OCR\backup`
- typecheck/build

## 5. 현재 실패 검증 목록
| command | status | root cause | 5A related |
| --- | --- | --- | --- |
| `node tmp/check_runocr_formdata_keys_2a.mjs` | FATAL exit 2 | `C:\OCR\OCR\backup` 2A snapshot missing | NO |
| `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | FAIL exit 1 | one backup-equivalence subcheck missing 2B snapshot | NO |
| `node tmp/check_runocr_doc_comments_3b.mjs` | FAIL exit 1 | 8 historical 3B backups missing | NO |
| `node tmp/check_template_workspace_move_4a.mjs` | FAIL exit 1 | structural checks pass; 4A backup equality missing | NO |
| `node tmp/check_template_editor_ui_move_4b.mjs` | FAIL exit 1 | structural/import checks pass; 3 backup equality checks missing | NO |
| `python tmp/codex_markdown_contract_fixture_lock.py --check ...` | FAIL exit 1 | actual LF vs expected fixture CRLF in all 6 cases | NO |
| `node tmp/check_ocr_core_types_common_move_5a.mjs` | PASS exit 0 | 5A baseline check passes | YES, PASS |

## 6. backup 경로 의존 분석
- Older static checks compute backup as `resolve(ROOT, "..", "backup")`, which maps to `C:\OCR\OCR\backup`.
- `C:\OCR\OCR\backup` does not exist in this workspace.
- Current backup exists at `C:\OCR\OCR\mysuit-ocr\backup\ocr_core_types_20260522_before_FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE`.
- That 5A backup contains 5A files only, not historical 2A/2B/3B/4A/4B snapshot filenames.
- 5A check uses `ROOT/backup/<phase>` and passes.

## 7. static check repair 방향
Recommended:
1. Replace stale sibling backup dependency with repo-relative phase backup discovery.
2. If a historical backup is missing, report `SKIP_WITH_REASON` for that one logic-equivalence check.
3. Keep current-state structural boundary checks strict.
4. Do not regenerate backup snapshots as part of this repair.

## 8. markdown LF/CRLF 분석
- Markdown runner already masks `processing_time`.
- Runner does not normalize CRLF/LF before equality.
- Current backend actual output: LF.
- Current expected fixtures: CRLF.
- All 6 failures show first diff at line 1: same text, different line ending.

Recommendation: normalize line endings in compare path only, e.g. CRLF/LF -> LF after processing_time masking. Do not rebake fixtures for EOL-only drift.

## 9. 5A 인과 여부
The reproduced failures are not 5A code regressions. 5A-specific validation passes, typecheck/build pass, and failing checks isolate to missing historical backup snapshots or EOL-only markdown comparison.

## 10. 다음 실제 repair 추천
Recommendation: **C. static check scripts repair + markdown runner line-ending normalize**.

Scope:
- validation scripts/runners only
- no `src`
- no backend
- no fixture changes
- no backup creation/restoration

## 11. dirty 상태
```text
 M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
 M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
 M mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
R  mysuit-ocr/src/components/ocr/core/types.ts -> mysuit-ocr/src/common/types/ocr.ts
 M mysuit-ocr/src/components/ocr/OcrCanvasPane.tsx
 M mysuit-ocr/src/components/ocr/core/export.ts
 M mysuit-ocr/src/components/ocr/core/ops.ts
 M mysuit-ocr/src/components/ocr/core/table.ts
 M mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx
 M mysuit-ocr/src/components/runocr/utils/buildOcrFormData.ts
 M mysuit-ocr/src/components/template/ui/OcrAnnotator.tsx
 M mysuit-ocr/src/components/template/ui/OcrRightPanel.tsx
 M mysuit-ocr/tmp/check_template_editor_ui_move_4b.mjs
 M ocr-server/data/review_log.jsonl
 M ocr-server/data/templates.json
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md
?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_MAP_20260522.csv
?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.json
?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.md
?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.json
?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.md
?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.json
?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.md
?? mysuit-ocr/tmp/check_ocr_core_types_common_move_5a.mjs
?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py
?? mysuit-ocr/tmp/codex_frontend_ocr_core_ownership_precheck.py
?? mysuit-ocr/tmp/codex_frontend_validation_baseline_repair_precheck.py
```

`templates.json` dirty state remains a TPL-95328E52 impact precheck candidate.

## 12. typecheck/build 결과
- `npm run typecheck`: exit 0, PASS
- `npm run build`: exit 0, PASS
- stdout log: `C:\OCR\OCR\ocr-server\logs\codex_CODEX_FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_NO_PROD_MODIFY.out.log`
- stderr log: `C:\OCR\OCR\ocr-server\logs\codex_CODEX_FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_NO_PROD_MODIFY.err.log`

## 13. 다음 작업 제안
1. Repair static check backup handling with explicit SKIP_WITH_REASON.
2. Repair markdown runner compare normalization for LF/CRLF only.
3. Rerun all affected validations plus 5A check/typecheck/build.
4. Continue 5B only after validation baseline noise is quiet.
