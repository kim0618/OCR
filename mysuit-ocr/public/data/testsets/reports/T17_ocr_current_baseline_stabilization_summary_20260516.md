# T-17 OCR 현재 보유 샘플 기준 1차 안정화 최종 요약

## 1. 전체 결론
- invoice_statement 1차 안정화 완료.
- baseline receipt 1차 개선 완료.
- testset management/export/diff 기반 완료.
- DB 전환 계획은 PostgreSQL 14개 테이블 기준으로 보류 저장.

이번 작업은 마감 리포트 생성만 수행했으며 OCR 추출 로직, parser/classifier, manifest, TestWorkspace, DB 구현, `invoice_statement.py`, `main.py`는 수정하지 않았다.

## 2. invoice_statement 최종 상태
- Test 기준 rowCount: 7/7 exact.
- Template/RunOCR E2E: 7/7 exact.
- 1.jpg: 28/28.
- 2.pdf: 13/13.
- 3.pdf: 1/1.
- 4.pdf: 1/1.
- 5.pdf: 6/6.
- 6.pdf: 6/6.
- 7.pdf: 1/1.
- OP-anchor reconstruction 적용 상태 유지.
- multiline layout mapping 적용 상태 유지.
- colGuides header skip 적용 상태 유지.
- valueMappingWarnings/warning 정책 유지.

근거 리포트:
- `T16_baseline_receipt_invoice_final_audit_20260516.json`
- `invoice_statement/reports/T10_fix_template_colguides_header_skip_20260516.json`

## 3. baseline receipt T-15/T-16 최종 상태
| 항목 | Before | After | 개선 |
|---|---:|---:|---:|
| pos_receipt businessNo missing | 4 | 3 | -1 |
| pos_receipt merchantName missing | 2 | 1 | -1 |
| food_cafe merchantName missing | 4 | 2 | -2 |
| card_receipt businessNo missing | 2 | 0 | -2 |
| card_receipt merchantName missing | 2 | 1 | -1 |
| medical_receipt 정분류 | 2/4 | 4/4 | +2 |
| finance_slip selected | 1 | 0 | 정책 정합화 |

T-16 aggregate:
- total samples: 57
- selected: 48
- suppressed: 7
- unknown: 2
- error: 0

## 4. testset management/export/diff 도구
- T-11 documentType/qualityTags summary 완료.
- T-12a expectedRowCount summary 완료.
- T-12b missing/warning field summary 완료.
- T-12c RunAll JSON/MD export 완료.
- T-12d before/after diff tool 완료.

관련 산출물:
- `T11_testset_management_summary_20260516.*`
- `T12a_expected_rowcount_summary_20260516.*`
- `T12b_field_missing_warning_summary_20260516.*`
- `T12c_runall_snapshot_export_20260516.*`
- `T12d_runall_snapshot_diff_20260516.*`

## 5. DB 전환 계획
- 기준 DB: PostgreSQL.
- 운영형 테이블 수: 14개.
- 다음 단계: DB-2 schema.sql 작성.

대상 테이블:
- users
- sites
- site_members
- ocr_templates
- ocr_template_regions
- ocr_template_table_guides
- ocr_runs
- ocr_run_files
- ocr_run_results
- ocr_run_table_rows
- ocr_run_warnings
- ocr_ground_truth
- user_preferences
- audit_logs

근거 문서:
- `mysuit-ocr/docs/db_migration_analysis_ocr_project_20260516.md`
- `mysuit-ocr/docs/db_migration_analysis_ocr_project_20260516.json`

## 6. 남은 이슈
- pos_003.jpg metadata mismatch.
- google/6.jpg locked mismatch.
- OCR source missing/garbled 케이스.
- finance_slip extractor 장기 후보.
- tax_invoice sample 없음.
- transaction_statement 예비 타입.

## 7. 다음 우선순위 후보
1. 현재 상태 마감 후 새 샘플 확보.
2. metadata 정리.
3. finance_slip extractor 장기 작업.
4. DB-2 PostgreSQL schema.sql.
5. tax_invoice / transaction_statement 실제 샘플 확보 후 parser 분기.

## 8. 검증 결과
- T-16 py_compile: PASS.
- T-16 verify script: PASS.
- typecheck: PASS (`npm run typecheck`).
- build: T-16에서는 코드 수정이 없어 미실행.

