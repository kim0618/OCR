# FRONTEND VALIDATION 1A BASELINE REPAIR 2026-05-22

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `FRONTEND-VALIDATION-1A-BASELINE-REPAIR`

## 2. 작업 목적
5A 이후 드러난 검증 baseline noise를 정리했다. 과거 static check의 historical backup 필수 의존을 안전하게 완화하고, markdown fixture runner의 LF/CRLF 비교 noise를 normalize로 해결했다.

## 3. 수정 파일
- `tmp/check_runocr_formdata_keys_2a.mjs`
- `tmp/check_runocr_response_mapping_boundary_2c.mjs`
- `tmp/check_runocr_doc_comments_3b.mjs`
- `tmp/check_template_workspace_move_4a.mjs`
- `tmp/check_template_editor_ui_move_4b.mjs`
- `tmp/codex_markdown_contract_fixture_lock.py`
- `tmp/check_validation_baseline_repair_1a.mjs`

## 4. 수정하지 않은 범위
- `src/**` 운영 코드 수정 없음
- backend 코드 수정 없음
- fixture 수정 없음
- `templates.json` 수정 없음
- backup 생성/복원 없음
- package/tsconfig/next config 수정 없음

## 5. backup handling 변경 내용
- Historical backup 비교는 backup이 있으면 기존처럼 strict 비교한다.
- Historical backup이 없으면 해당 logic-equivalence subcheck만 `SKIP_WITH_REASON: historical backup not found`로 기록한다.
- 파일 존재, 이동/미이동 정책, import boundary, forbidden leak, route policy, RunOCR/TestWorkspace presence 같은 structural boundary check는 계속 strict 실패 조건이다.
- repaired checks는 sibling `ROOT/../backup` 의존 대신 project-relative `ROOT/backup` 기준을 사용한다.

## 6. markdown EOL normalize 변경 내용
- `tmp/codex_markdown_contract_fixture_lock.py`에 `_normalize_eol()`을 추가했다.
- 비교 직전 `CRLF/LF/CR -> LF` normalize를 적용한다.
- 기존 `processing_time` masking은 유지된다.
- fixture 파일과 backend output은 수정하지 않는다.
- report에 `eolNormalizedForCompare: true`가 기록된다.

## 7. SKIP_WITH_REASON 동작
`PASS_WITH_SKIPPED_BACKUP`은 backup-only equality가 historical snapshot 부재로 skip되었고, 현재 구조/경계 검사는 모두 통과했다는 뜻이다. structural failure는 skip되지 않고 exit 1로 남는다.

## 8. 검증 결과
| command | result |
| --- | --- |
| `node tmp/check_validation_baseline_repair_1a.mjs` | PASS |
| `node tmp/check_runocr_formdata_keys_2a.mjs` | PASS_WITH_SKIPPED_BACKUP |
| `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | PASS_WITH_SKIPPED_BACKUP |
| `node tmp/check_runocr_doc_comments_3b.mjs` | PASS_WITH_SKIPPED_BACKUP |
| `node tmp/check_template_workspace_move_4a.mjs` | PASS_WITH_SKIPPED_BACKUP |
| `node tmp/check_template_editor_ui_move_4b.mjs` | PASS_WITH_SKIPPED_BACKUP |
| `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_VALIDATION_BASELINE_REPAIR_20260522` | PASS 6/6 |
| `npm run typecheck` | PASS |
| `npm run build` | PASS |
| `node tmp/check_ocr_core_types_common_move_5a.mjs` | PASS |
| `node tmp/check_table_view_model_v1_fixtures_js.mjs` | PASS 8/8 |
| `node tmp/check_clean_json_v1_fixtures_js.mjs` | PASS 9/9 |

Logs:
- `C:\OCR\OCR\ocr-server\logs\codex_FRONTEND_VALIDATION_1A_BASELINE_REPAIR.out.log`
- `C:\OCR\OCR\ocr-server\logs\codex_FRONTEND_VALIDATION_1A_BASELINE_REPAIR.err.log`

## 9. 남은 이슈
- 기존 5A 관련 `src` dirty 상태는 그대로 남아 있다. 이 작업은 원복하지 않았다.
- `ocr-server/data/templates.json` dirty 상태는 유지되며, `TPL-95328E52` 영향 precheck 후보로 남긴다.
- markdown runner는 backend OCR API를 호출하므로 `review_log.jsonl`에는 runtime append가 발생할 수 있다.

## 10. 다음 작업 제안
1. `FRONTEND-STRUCTURE-5B-OCR-CORE-OPS-COMMON-MOVE` precheck 또는 실제 이동
2. `table.ts` common/utils 이동 precheck
3. `export.ts` template/utils 이동 precheck
4. core 의존 정리 후 `OcrCanvasPane` common/ui 이동
5. Template table column definition 설계 precheck
6. `TPL-95328E52` dirty 영향 precheck
7. TestWorkspace는 사용자 확인 후 진행
