# T-20g receipt limited auto-apply 설계 결과

## 1. 생성/수정 파일
- `ocr-server/preprocessing_policy.py` — `decide_auto_apply_preprocessing()` 헬퍼 추가
- `ocr-server/scripts/design_receipt_preprocessing_auto_apply_t20g.py` (신규)
- `mysuit-ocr/public/data/testsets/reports/T20g_receipt_limited_auto_apply_design_20260516.json`
- `mysuit-ocr/public/data/testsets/reports/T20g_receipt_limited_auto_apply_design_20260516.md`

## 2. 핵심 요약
- T-20f 15개 샘플 auto-apply simulation 완료
- 현재 태그 기준 autoApplyAllowed: 4건 (pos_006만)
- 추천 태그 추가 후: 4건 (candidate 4건)
- 정상군 candidate_accept 방어 guard: `preprocessing_candidate` 태그 필수 조건
- invoice_statement: 항상 excluded
- productionApplied=false 유지 (실제 적용 없음)

## 3. T-20f 결과 요약
| group | count | candidate_accept | issue |
|---|---:|---:|---|
| candidate | 4 | 4 | none |
| normal_receipt | 8 | 2 | normal_candidate_accept_debug_only |
| blocked_edge | 3 | 2 (invoice/3.pdf, pos_001) | invoice_debug_only / edge |

## 4. auto-apply 허용 조건
| 조건 | 내용 |
|---|---|
| documentType | receipt 계열만 (invoice_statement 영구 제외) |
| preprocessing_candidate | qualityTags에 반드시 포함 |
| preprocessing_blocked | 없어야 함 |
| debug_decision | candidate_accept여야 함 |
| 핵심 필드 보존 | merchantName / businessNo / totalAmount 기존 값 유지 |
| improvement delta | coreFieldFillCount 증가 또는 명시적 improvement |
| false positive | 10M원 이상 bare 금액 없어야 함 |
| docType | 기존 대비 악화 없어야 함 |

## 5. auto-apply 차단 조건
- invoice_statement → 영구 차단
- `preprocessing_blocked` 태그 → 차단
- `preprocessing_candidate` 태그 없음 → 차단 (정상군 false positive 방어)
- 핵심 필드(merchantName/businessNo/totalAmount) 손실 → 차단
- 개선 delta 없음 (no positive improvement) → 차단
- false positive 금액(≥10M bare) → 차단
- docType 악화 → 차단

## 6. 정상군 candidate_accept 방어
| sample | issue | guard | autoApplyAllowed |
|---|---|---|---|
| card_001.jpg | normal_candidate_accept_debug_only | no_preprocessing_candidate_tag | False |
| pos_005.jpg | normal_candidate_accept_debug_only | no_preprocessing_candidate_tag | False |

## 7. simulation 결과 (현재 태그 기준)
| sample | group | selectedCandidate | debugDecision | autoApplyAllowed | reason |
|---|---|---|---|---|---|
| card_002.jpg | candidate | clahe | candidate_accept | True | all_guards_passed |
| medical_001.jpg | candidate | clahe | candidate_accept | True | all_guards_passed |
| pos_006.jpg | candidate | upscale_1_5x | candidate_accept | True | all_guards_passed |
| medical_003.jpg | candidate | grayscale | candidate_accept | True | all_guards_passed |
| card_001.jpg | normal | upscale_1_5x | candidate_accept | False | no_preprocessing_candidate_tag |
| baseline/2.jpg | normal | - | preprocessing_blocked | False | debug_decision_not_accept: preprocessing_blocked |
| pos_002.jpg | normal | - | preprocessing_blocked | False | debug_decision_not_accept: preprocessing_blocked |
| pos_005.jpg | normal | grayscale | candidate_accept | False | no_preprocessing_candidate_tag |
| food_003.jpg | normal | - | preprocessing_blocked | False | debug_decision_not_accept: preprocessing_blocked |
| food_005.jpg | normal | - | preprocessing_blocked | False | debug_decision_not_accept: preprocessing_blocked |
| medical_002.jpg | normal | - | preprocessing_blocked | False | debug_decision_not_accept: preprocessing_blocked |
| medical_004.jpg | normal | - | preprocessing_blocked | False | debug_decision_not_accept: preprocessing_blocked |
| invoice/2.pdf | blocked | - | preprocessing_blocked | False | invoice_excluded_from_auto_apply |
| invoice/3.pdf | blocked | render_dpi_200_grayscale | candidate_accept | False | invoice_excluded_from_auto_apply |
| pos_001.jpg | blocked | upscale_1_5x | candidate_accept | False | no_preprocessing_candidate_tag, no_positive_improvement_delta |

## 7b. simulation 결과 (추천 태그 추가 후: card_002, medical_001, medical_003에 preprocessing_candidate 추가)
| sample | autoApplyAllowed (현재) | autoApplyAllowed (추천) | 변화 |
|---|---|---|---|
| card_002.jpg | True | True | - |
| medical_001.jpg | True | True | - |
| pos_006.jpg | True | True | - |
| medical_003.jpg | True | True | - |
| card_001.jpg | False | False | - |
| baseline/2.jpg | False | False | - |
| pos_002.jpg | False | False | - |
| pos_005.jpg | False | False | - |
| food_003.jpg | False | False | - |
| food_005.jpg | False | False | - |
| medical_002.jpg | False | False | - |
| medical_004.jpg | False | False | - |
| invoice/2.pdf | False | False | - |
| invoice/3.pdf | False | False | - |
| pos_001.jpg | False | False | - |

## 8. invoice_statement 정책
| 항목 | 정책 |
|---|---|
| auto-apply | **영구 제외** (`invoice_excluded_from_auto_apply`) |
| debug mode | candidate_accept 표시 가능 (wouldApplyInDebug=True) |
| template path | debug-only 유지, production 결과 변경 없음 |

## 9. rollout 전략
| Phase | 내용 | 상태 |
|---|---|---|
| Phase 0 | debug-only 유지 (현재) | 완료 |
| Phase 1 | UI: preprocessing_candidate 샘플 '전처리 후보' 표시 | 설계 완료 |
| Phase 2 | 사용자 수동 채택 UI | 미구현 |
| Phase 3 | Limited auto-apply (preprocessing_candidate + guard passed + receipt only) | 설계 완료 |
| Phase 4 | 더 많은 샘플 검증 후 기본 정책 재평가 | 미래 |

**Phase 3 진입 조건:**
- preprocessing_candidate 태그 보강 (card_002, medical_001, medical_003)
- T-20g guard 검증 PASS
- 정상군 false positive 0건 확인
- invoice_statement 7/7 exact 유지

## 10. 다음 작업 판단
- **즉시 가능**: Phase 1 UI 설계 (preprocessing_candidate 샘플 강조 표시)
- **권장 선행 작업**: card_002/medical_001/medical_003 manifest에 `preprocessing_candidate` 태그 추가 (T-20h)
- **Phase 3 준비**: 추천 태그 추가 후 T-20g simulation 재실행 → autoAllowed=4건 확인
- **Phase 4 전**: 더 많은 정상 샘플에서 false positive 0건 유지 확인
- **invoice**: debug-only 유지, auto-apply 논의 제외

## 11. 검증 결과
- py_compile preprocessing_policy.py: PASS
- py_compile design script: PASS
- simulation script: PASS
- typecheck: PASS (npm run typecheck)
- build: 미실행 (Python 파일만 수정, JS 무수정)
