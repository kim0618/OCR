# T-20i receipt limited auto-apply 옵션 구현 결과

## 1. 수정 파일
- `ocr-server/main.py` — `autoApplyPreprocessing` Form 파라미터 + `_build_preprocessing_debug` auto-apply 확장
- `ocr-server/scripts/verify_receipt_limited_auto_apply_t20i.py` (신규)

## 2. 백업 파일
- `ocr-server/backup/main_20260517_before_T20i_receipt_limited_auto_apply.py`
- `ocr-server/backup/preprocessing_policy_20260517_before_T20i_receipt_limited_auto_apply.py`

## 3. 핵심 요약
- `autoApplyPreprocessing=false` (기본값): 기존 완전 동일
- `autoApplyPreprocessing=true`: receipt + guard 통과 시 productionApplied=True
- 자동 적용 대상: 4건 (card_002/medical_001/pos_006/medical_003)
- 정상군 차단: card_001, pos_005 (no_preprocessing_candidate_tag)
- invoice_statement: 항상 excluded (영구 제외)
- 검증 overall: PASS

## 4. 옵션 동작 정의
| debugPreprocessing | autoApplyPreprocessing | 동작 |
|---|---|---|
| false | false | 기존 완전 동일. preprocessingDebug 없음 |
| true | false | preprocessingDebug 추가. productionApplied=false (T-20d 동일) |
| true | true | debug compare + guard → receipt 통과 시 productionApplied=true |
| false | true | B案: 내부 debug compare 실행. preprocessingDebug 포함. 통과 시 productionApplied=true |

## 5. auto-apply 결과
| sample | expected | appliedVariant | productionApplied | reason |
|---|---|---|---|---|
| card_002.jpg | True | clahe | True | all_guards_passed |
| medical_001.jpg | True | clahe | True | all_guards_passed |
| pos_006.jpg | True | upscale_1_5x | True | all_guards_passed |
| medical_003.jpg | True | grayscale | True | all_guards_passed |
| card_001.jpg | False | upscale_1_5x | False | no_preprocessing_candidate_tag |
| pos_005.jpg | False | grayscale | False | no_preprocessing_candidate_tag |
| invoice/3.pdf | False | render_dpi_200_grayscale | False | invoice_excluded_from_auto_apply |

## 6. 차단 결과
| sample | reason | productionApplied |
|---|---|---|
| card_001.jpg | no_preprocessing_candidate_tag | False |
| pos_005.jpg | no_preprocessing_candidate_tag | False |
| invoice/3.pdf | invoice_excluded_from_auto_apply | False |

## 7. invoice_statement 제외 확인
| sample | debugCandidate | productionApplied | rowCount |
|---|---|---|---:|
| invoice/3.pdf | True | False | - |
| 1.jpg (baseline) | - | False | 28/28 exact |
| 2.pdf (baseline) | - | False | 13/13 exact |
| 3.pdf (baseline) | - | False | 1/1 exact |
| 4.pdf (baseline) | - | False | 1/1 exact |
| 5.pdf (baseline) | - | False | 6/6 exact |
| 6.pdf (baseline) | - | False | 6/6 exact |
| 7.pdf (baseline) | - | False | 1/1 exact |

## 8. 회귀 확인
| 영역 | 결과 |
|---|---|
| invoice_statement 7/7 exact | PASS |
| 정상군 receipt 회귀 | 0건 (card_001/pos_005 blocked) |
| autoApplyPreprocessing 기본값 false | OK (기존 결과 변경 없음) |
| invoice auto-apply 제외 | OK (invoice_excluded_from_auto_apply) |

## 9. 운영 적용 판단
| 항목 | 결과 |
|---|---|
| default (auto=false) | 기존 결과 100% 동일 |
| explicit auto=true | receipt 4건 auto-apply 가능 |
| invoice_statement | 영구 제외 (auto=true여도 무효) |
| next step | 프론트엔드에서 autoApplyPreprocessing=true 연결 또는 Phase 3 rollout |

## 10. 검증 결과
- py_compile main.py: PASS
- py_compile preprocessing_policy.py: PASS
- py_compile verify script: PASS
- verify script: PASS
  - PASS: autoApplyPreprocessing param added
  - PASS: debug/auto flag gates correct
  - PASS: productionApplied=True count == 4
  - PASS: card_002 autoApplyAllowed
  - PASS: medical_001 autoApplyAllowed
  - PASS: pos_006 autoApplyAllowed
  - PASS: medical_003 autoApplyAllowed
  - PASS: card_001 blocked
  - PASS: pos_005 blocked
  - PASS: invoice/3.pdf excluded
  - PASS: invoice baseline 7/7 exact
- typecheck: PASS (npm run typecheck)
- build: PASS
