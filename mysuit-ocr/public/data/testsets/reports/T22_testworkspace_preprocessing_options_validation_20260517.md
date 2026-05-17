# T-22 TestWorkspace preprocessing 옵션 RunAll 검증 결과

## 1. 생성 파일
- `mysuit-ocr/public/data/testsets/reports/T22_testworkspace_preprocessing_options_validation_20260517.md`
- `mysuit-ocr/public/data/testsets/reports/T22_testworkspace_preprocessing_options_validation_20260517.json`
- `mysuit-ocr/public/data/testsets/reports/T22_current_ocr_baseline_snapshot_20260517.json`
- `ocr-server/scripts/verify_testworkspace_preprocessing_options_t22.py`

## 2. 핵심 요약
- overall: PASS
- 기본 모드는 preprocessingDebug 없이 기존 기준선을 유지한다.
- debug only 모드는 preprocessingDebug를 생성하지만 final result는 기본 모드와 동일하다.
- debug + auto 모드는 receipt limited 4건만 productionApplied=true다.
- invoice_statement는 모든 옵션 조합에서 productionApplied=false다.
- invoice_statement rowCount exact: 7/7

## 3. 검증 모드
| mode | debugPreprocessing | autoApplyPreprocessing | 목적 |
|---|---|---|---|
| default | False | False | baseline compatibility |
| debugOnly | True | False | emit preprocessingDebug without changing final result |
| debugAuto | True | True | receipt limited opt-in auto apply |

## 4. 기본 모드 결과
| 항목 | 결과 |
|---|---|
| preprocessingDebug | 없음 또는 false |
| productionApplied | 0건 |
| invoice_statement rowCount | 7/7 |
| regressionCount | 0 |

## 5. debug only 결과
| sample | selectedCandidate | productionApplied | finalSame |
|---|---|---|---|
| pos_005.jpg | grayscale | False | PASS |
| pos_006.jpg | upscale_1_5x | False | PASS |
| medical_001.jpg | clahe | False | PASS |
| medical_003.jpg | grayscale | False | PASS |
| card_001.jpg | upscale_1_5x | False | PASS |
| card_002.jpg | clahe | False | PASS |
| 2.pdf | - | False | PASS |
| 3.pdf | render_dpi_200_grayscale | False | PASS |

## 6. debug + auto 결과
| sample | appliedVariant | productionApplied | 판정 |
|---|---|---|---|
| card_002.jpg | clahe | True | PASS |
| medical_001.jpg | clahe | True | PASS |
| pos_006.jpg | upscale_1_5x | True | PASS |
| medical_003.jpg | grayscale | True | PASS |

## 7. invoice_statement 제외 확인
| sample | rowCount | productionApplied | status |
|---|---|---|---|
| 1.jpg | 28/28 | False | exact |
| 2.pdf | 13/13 | False | exact |
| 3.pdf | 1/1 | False | exact |
| 4.pdf | 1/1 | False | exact |
| 5.pdf | 6/6 | False | exact |
| 6.pdf | 6/6 | False | exact |
| 7.pdf | 1/1 | False | exact |

## 8. 차단/정상군 방어 확인
| sample | reason | productionApplied |
|---|---|---|
| receipt_generalization/card_001.jpg | no_preprocessing_candidate_tag | False |
| receipt_generalization/pos_005.jpg | no_preprocessing_candidate_tag | False |
| invoice_statement/3.pdf | invoice_excluded_from_auto_apply | False |

## 9. TestWorkspace UI 연결 확인
| check | status |
|---|---|
| debugCheckboxDefaultFalse | PASS |
| autoCheckboxDefaultFalse | PASS |
| fetchOcrSendsDebug | PASS |
| fetchOcrSendsAuto | PASS |
| fetchOcrSendsQualityTags | PASS |
| runOnePassesOptions | PASS |
| runAllPassesOptions | PASS |
| preprocessingDebugPanelRendered | PASS |
| preprocessingDebugPanelBranches | PASS |
| uploadWorkspaceNoPreprocessingOptions | PASS |
| runocrNoPreprocessingOptions | PASS |

## 10. 현재 기준선 snapshot
- `mysuit-ocr/public/data/testsets/reports/T22_current_ocr_baseline_snapshot_20260517.json`
- scope: `T22_current_ocr_baseline_after_preprocessing_ui`
- samples: 78 mode rows

## 11. 검증 결과
- py_compile: PASS: python -m py_compile scripts/verify_testworkspace_preprocessing_options_t22.py
- validation script: PASS: python scripts/verify_testworkspace_preprocessing_options_t22.py
- typecheck: PASS: npm.cmd run typecheck
- build: PASS: npm.cmd run build (exit 0; existing ESLint setting message: nextVitals is not iterable)

## 12. 다음 작업 판단
- preprocessing UI 연결까지 최종 마감
- RunOCR Phase 3 자동 적용은 보류
- 추가 receipt 샘플 확보 후 guard 재평가
- DB-2 PostgreSQL schema 작업으로 이동 가능
