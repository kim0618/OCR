# T-23 OCR 전체 안정화 최종 마감 리포트

## 1. 생성 파일
- `mysuit-ocr/public/data/testsets/reports/T23_ocr_full_stabilization_final_summary_20260517.md`
- `mysuit-ocr/public/data/testsets/reports/T23_ocr_full_stabilization_final_summary_20260517.json`

## 2. 전체 결론
- `invoice_statement` 안정화 완료
- baseline receipt 개선 완료
- synthetic position 기반 개선 완료
- preprocessing debug / limited auto-apply 준비 완료
- TestWorkspace 검증 UI 연결 완료
- RunOCR 자동 적용은 보류
- OCR 기준선은 T-22 snapshot으로 고정
- DB 작업으로 이동 가능

## 3. invoice_statement 최종 상태
| sample | expected | actual | status |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | exact |
| 2.pdf | 13 | 13 | exact |
| 3.pdf | 1 | 1 | exact |
| 4.pdf | 1 | 1 | exact |
| 5.pdf | 6 | 6 | exact |
| 6.pdf | 6 | 6 | exact |
| 7.pdf | 1 | 1 | exact |

- Test rowCount: 7/7 exact
- Template/RunOCR E2E: 7/7 exact
- OP-anchor reconstruction 적용
- multiline layout mapping 적용
- colGuides header skip 적용
- warning 정책 유지

## 4. baseline receipt 최종 상태
- T-15/T-16 기준으로 pos/card/food/medical 주요 missing 및 분류 개선 완료
- finance_slip은 selected 1건에서 0건으로 정리하고 suppression 정책을 정합화
- OCR source missing/garbled 케이스는 parser 문제가 아니라 입력 OCR 품질 한계로 분리
- metadata mismatch는 기준선 이슈로 기록하고 별도 정리 대상으로 유지

## 5. T-19 개선 요약
| metric | before | after | delta |
|---|---:|---:|---:|
| docType match rate | 77.2% | 87.7% | +10.5%p |
| core field fill rate | 87.6% | 94.6% | +7.0%p |
| classification_mismatch | 9 | 3 | -6 |
| parser_missed_source_exists | 4 | 0 | -4 |
| invoice_statement rowCount exact | 7/7 | 7/7 | 0 |

T-19 final snapshot 기준:
- totalSamples: 57
- selected: 48
- suppressed: 7
- unknown: 0
- error: 0
- coreFieldGtMatchRate: 99.1%
- rowCountExactRate: 100.0%

## 6. T-20 preprocessing 최종 정책
| 항목 | 정책 |
|---|---|
| `debugPreprocessing` | 기본값 `false`, 전처리 후보 비교/debug 전용 |
| `autoApplyPreprocessing` | 기본값 `false`, receipt limited opt-in |
| `invoice_statement` | auto-apply 영구 제외 |
| receipt | `preprocessing_candidate` + guard 통과 샘플만 적용 |
| 서버 기본값 | `autoApplyPreprocessing=false` 유지 |

- 전체 전처리 기본 적용은 위험하므로 금지
- `qualityTags` 기반 조건부 적용이 최종 정책
- original / variant / debug 정보 보존
- `preprocessing_blocked`는 차단
- 핵심 필드 손실, docType 악화, false positive 금액은 차단

## 7. productionApplied 대상
| sample | variant | reason |
|---|---|---|
| `card_002` | `clahe` | core field fill 개선, guard 통과 |
| `medical_001` | `clahe` | merchantName 개선, guard 통과 |
| `pos_006` | `upscale_1_5x` | totalAmount 개선, guard 통과 |
| `medical_003` | `grayscale` | merchantName 개선, guard 통과 |

제한 유지:
- `card_001`, `pos_005`는 정상군 방어로 차단
- `invoice_statement`는 후보가 있어도 `productionApplied=false`

## 8. T-21/T-22 UI 연결 및 검증 상태
- TestWorkspace: 전처리 Debug / 자동 보정 체크박스 연결 완료, 기본값 `false`
- RunOCR: preprocessing 옵션 미전달, 기존 동작 유지
- UploadWorkspace: preprocessing 옵션 미전달, 기존 동작 유지
- T22 snapshot: `T22_current_ocr_baseline_snapshot_20260517.json`
- T22 검증 대상: 26개 샘플
- T22 `regressionCount`: 0
- T22 `productionAppliedCount`: 4
- T22 `invoiceProductionAppliedCount`: 0
- T22 `invoiceRowCountExact`: 7/7

## 9. 현재 기준선 파일
- T17 summary: `T17_ocr_current_baseline_stabilization_summary_20260516.md`
- T17 summary JSON: `T17_ocr_current_baseline_stabilization_summary_20260516.json`
- T19 final snapshot: `T19_final_runall_snapshot_20260516.json`
- T19 improvement audit: `T19_final_synthetic_position_improvement_audit_20260516.md`
- T20 final summary: `T20_final_preprocessing_series_summary_20260517.md`
- T22 validation: `T22_testworkspace_preprocessing_options_validation_20260517.md`
- T22 current baseline snapshot: `T22_current_ocr_baseline_snapshot_20260517.json`

## 10. 남은 이슈
- `pos_003` metadata mismatch
- `google/6` locked mismatch
- OCR source missing/garbled 케이스
- finance_slip extractor 장기 후보
- tax_invoice sample 없음
- transaction_statement 예비 타입
- `invoice_statement` template path preprocessingDebug wiring 장기 후보
- RunOCR Phase 3 자동 적용 보류

## 11. 앞으로 건드리면 안 되는 안정화 기준
- `invoice_statement` rowCount 7/7 exact
- `invoice_statement` autoApplyPreprocessing 제외
- receipt `productionApplied` 대상 4건 제한
- TestWorkspace 옵션 기본값 `false`
- RunOCR 기존 동작 유지
- UploadWorkspace 기존 동작 유지
- 서버 `autoApplyPreprocessing` 기본값 `false`
- `preprocessing_candidate` 태그 필수 guard 유지
- `preprocessing_blocked` 차단 유지

## 12. 다음 작업 후보
1. DB-2 PostgreSQL `schema.sql` 작성
2. RunOCR Phase 3 자동 preprocessing 적용 설계
3. 추가 receipt 샘플 확보 후 guard 재평가
4. tax_invoice 샘플 확보 후 parser 분기
5. finance_slip extractor 장기 작업
6. metadata mismatch 정리

## 13. 검증 결과
기존 최신 검증 결과 요약:
- T22 validation: PASS
- T22 overall: PASS
- T22 regressionCount: 0
- T22 productionAppliedCount: 4
- T22 invoiceProductionAppliedCount: 0
- T22 invoiceRowCountExact: 7/7
- typecheck: PASS (`npm.cmd run typecheck`)
- build: PASS (`npm.cmd run build`)
- known message: `nextVitals is not iterable`, exit code 0

## 14. 최종 마감 판단
- OCR/parser/classifier/preprocessing 안정화는 현재 기준선에서 마감한다.
- 내일 DB 작업 중 OCR 안정화 파일을 수정하지 않는다.
- OCR 관련 변경이 필요한 경우 T22 snapshot을 기준으로 회귀 검증 후 별도 작업으로 분리한다.
