# FRONTEND CLEANUP OCR RESULT PANEL CYCLE 1 CLOSE-OUT 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `OcrResultPanel.tsx`, `TestWorkspace.tsx`, `src/lib/*`, backend/parser/templates/manifest/GT, fixture 수정 없음.
- 이번 작업은 close-out 문서화와 현재 typecheck/build 기준선 확인만 수행.

## 3. 생성 파일
- `tmp/codex_ocr_result_panel_cycle1_closeout.py`
- `docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md`
- `docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json`

## 4. Cycle 1 목적
OcrResultPanel의 비대해진 책임 중 Clean JSON, Markdown, formatter, structured table view model 책임을 순수 helper와 fixture runner로 분리하고, Preview structured table에만 helper를 적용한 뒤 다음 cycle 진입 조건을 정리한다.

## 5. Cycle 1 진행 타임라인
1. Clean JSON contract/fixture lock
2. Clean JSON builder extraction 및 JS-side runner
3. Markdown contract/fixture lock/coverage precheck
4. Markdown builder 및 formatter extraction
5. Preview/Custom/Validation table renderer precheck
6. table view model contract trim/output fixture/input fixture
7. `buildStructuredTableViewModel` helper + direct runner
8. Preview-only OcrResultPanel 적용
9. 프론트 파일 인벤토리/사용처 precheck

## 6. 완료된 작업 목록
| # | task | status | evidence |
| --- | --- | --- | --- |
| 1 | Clean JSON v1 contract 문서화 | DONE | docs/CLEAN_JSON_CONTRACT_20260521.md |
| 2 | Clean JSON v1 fixture lock | DONE | docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md |
| 3 | buildCleanJsonResult helper 분리 | DONE | src/lib/cleanJsonBuilder.ts |
| 4 | JS-side Clean JSON fixture runner 추가 | DONE | tmp/check_clean_json_v1_fixtures_js.mjs; 9/9 PASS |
| 5 | Markdown v1 contract 문서화 | DONE | docs/MARKDOWN_V1_CONTRACT_20260521.md |
| 6 | Markdown fixture lock | DONE | docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.md |
| 7 | Markdown LF/coverage precheck | DONE | docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md |
| 8 | buildMarkdownReport helper 분리 | DONE | src/lib/markdownReportBuilder.ts |
| 9 | ocrResultFormatters 분리 | DONE | src/lib/ocrResultFormatters.ts |
| 10 | Preview table builder precheck | DONE | docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md |
| 11 | Preview/Custom/Validation table renderer precheck | DONE | docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md |
| 12 | table view model contract/signature precheck | DONE | docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md |
| 13 | table view model contract trim | DONE | docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md |
| 14 | table_view_model_v1 output fixture lock | DONE | docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md |
| 15 | raw input fixture + synthetic_empty_rows fixture 보강 | DONE | docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md |
| 16 | buildStructuredTableViewModel helper 생성 | DONE | src/lib/structuredTableViewModel.ts |
| 17 | OcrResultPanel Preview structured table 적용 | DONE | docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md |
| 18 | 프론트 파일 인벤토리/사용처 precheck | DONE | docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md |

## 7. 생성/수정된 주요 파일
| path | role | lines | status |
| --- | --- | --- | --- |
| src/lib/cleanJsonBuilder.ts | Clean JSON builder | 171 | created in cycle |
| src/lib/markdownReportBuilder.ts | Markdown builder | 81 | created in cycle |
| src/lib/ocrResultFormatters.ts | OCR result formatter helpers | 120 | created in cycle |
| src/lib/structuredTableViewModel.ts | Structured table view model helper | 140 | created in cycle; do not delete |
| tmp/check_clean_json_v1_fixtures_js.mjs | Clean JSON JS fixture runner | 421 | created in cycle |
| tmp/check_table_view_model_v1_fixtures_js.mjs | Table view model JS fixture runner | 308 | created in cycle |
| src/components/upload/OcrResultPanel.tsx | Preview-only structured table helper adoption plus helper imports | 1660 | modified earlier in cycle; not modified by close-out |

## 8. OcrResultPanel 라인 수 변화
- Cycle 시작 기준: 1789 lines
- 3D3 리포트 기준: 1648 lines
- 현재 관측: 1660 lines
- 해석: Cycle 1 목표인 책임 분리와 Preview-only 적용은 완료. 현재 관측치는 이후 작업/dirty state를 포함할 수 있어 close-out은 3D3 리포트 기준 `~1648` 감소를 cycle 결과로 기록한다.

## 9. 분리된 책임
- Clean JSON: `src/lib/cleanJsonBuilder.ts`
- Markdown: `src/lib/markdownReportBuilder.ts`
- formatter/table parser labels: `src/lib/ocrResultFormatters.ts`
- structured table view model: `src/lib/structuredTableViewModel.ts`
- invoice table column/rowIndex policy: `src/lib/invoiceTableDisplay.ts`

## 10. Fixture/Check Runner 현황
| runner | command | status | pass/total | diffs | sourceReport |
| --- | --- | --- | --- | --- | --- |
| Clean JSON fixture runner | node tmp/check_clean_json_v1_fixtures_js.mjs | PASS | 9/9 | 0 | docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json |
| Markdown fixture check | python tmp/codex_markdown_contract_fixture_lock.py --check ... | PASS | 6/6 | 0 | docs\MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.json |
| table_view_model fixture runner | node tmp/check_table_view_model_v1_fixtures_js.mjs | PASS | 8/8 | 0 | docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.json |

## 11. 최종 검증 결과
| check | status | exit | seconds | notes |
| --- | --- | ---: | ---: | --- |
| npm.cmd run typecheck | PASS | 0 | 1.841 | current close-out run |
| npm.cmd run build | PASS | 0 | 15.2 | known stderr noise tracked separately |

## 12. 적용된 범위
- Preview structured table 렌더링만 `buildStructuredTableViewModel` 기반으로 연결.
- Clean JSON / Markdown / formatter helper extraction 완료.
- JS-side/direct fixture runner 기반 회귀 검증 체계 확보.

## 13. 의도적으로 미적용한 범위
- Custom table view model 적용 보류.
- Validation table view model 적용 보류.
- legacy `parseTableField(field.value)` fallback 보류.
- TestWorkspace cleanup 보류.

## 14. 남은 이슈
| id | status | description | nextAction |
| --- | --- | --- | --- |
| ISSUE-FRONTEND-BUILD-LOG-1 | OPEN_NON_BLOCKING | build stderr: ESLint: nextVitals is not iterable | 원인 확인 및 별도 정리 |
| MANUAL-SMOKE-1 | OPEN | /runocr Preview table browser smoke 미실시 | 다음 최우선 작업 |

## 15. 다음 작업 후보
| priority | candidate | description |
| --- | --- | --- |
| 1 | Manual smoke 1회 | npm run dev, /runocr, 거래명세서 업로드, Preview 탭 표 시각 확인 |
| 2 | ISSUE-FRONTEND-BUILD-LOG-1 정리 | nextVitals is not iterable 원인 확인 |
| 3 | Custom / Validation table view model 적용 precheck | Cycle 2 후보 |
| 4 | legacy fallback view model precheck | buildLegacyTableViewModel 후보 |
| 5 | components/ocr/core 위치 조정 precheck | 순수 로직 위치 재검토 |
| 6 | TestWorkspace 분리 precheck | 사용자에게 먼저 확인 후 진행 |

## 16. Reopen Trigger
| # | trigger |
| --- | --- |
| 1 | OcrResultPanel Preview 표 시각 이상 발견 |
| 2 | 거래_3 컬럼 정책 변경 결정 |
| 3 | Custom/Validation table 중복 제거 필요 |
| 4 | legacy table fallback 정리 필요 |
| 5 | v2 info/tables 구조 개편 시작 |
| 6 | TestWorkspace 분리 작업 시작 전 컨텍스트 복원 필요 |

## 17. TestWorkspace 진입 전 조건
- 사용자에게 먼저 TestWorkspace 분리/정리 착수 여부를 확인한다.
- summary/export/tableRows/UI 섹션 중 어느 경계부터 나눌지 별도 precheck를 둔다.
- fixture/typecheck/build 기준선을 먼저 고정한다.

## 18. 최종 결론
Cycle 1은 close-out 가능. 다만 manual smoke는 아직 미실시이므로 `/runocr` Preview 표 시각 확인 1회를 다음 최우선 작업으로 둔다. Custom/Validation/legacy fallback은 Cycle 2 후보로 넘긴다.

## 19. Known Stderr Noise
- `ISSUE-FRONTEND-BUILD-LOG-1`: `ESLint: nextVitals is not iterable`
- 현재 build exit code 0이라 blocking 아님.
