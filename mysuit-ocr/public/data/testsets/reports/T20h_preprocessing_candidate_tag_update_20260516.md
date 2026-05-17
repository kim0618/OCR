# T-20h preprocessing_candidate 태그 보강 및 auto-apply simulation 결과

## 1. 수정 파일
- `mysuit-ocr/public/data/testsets/receipt_generalization/manifest.json` — card_002, medical_001, medical_003에 `preprocessing_candidate` 추가
- `ocr-server/scripts/verify_preprocessing_candidate_tag_update_t20h.py` (신규)

## 2. 백업 파일
- `mysuit-ocr/backup/receipt_generalization_manifest_20260516_before_T20h_preprocessing_candidate.json`

## 3. 핵심 요약
- preprocessing_candidate 추가: card_002, medical_001, medical_003 (3건)
- auto-apply simulation: autoApplyAllowed=4건 (PASS)
- 허용 대상: card_002(clahe), medical_001(clahe), pos_006(upscale_1_5x), medical_003(grayscale)
- 정상군 card_001/pos_005: `no_preprocessing_candidate_tag`로 계속 차단
- invoice_statement: 0건 (영구 제외)
- productionApplied=false 유지
- 전체 검증: PASS

## 4. qualityTags 변경 목록
| sample | before tags | after tags | 근거 |
|---|---|---|---|
| card_002.jpg | blurred | blurred, **preprocessing_candidate** | T-20: clahe로 merchantName+businessNo 출현 (fill 2→4) |
| medical_001.jpg | shadow | shadow, **preprocessing_candidate** | T-20: clahe로 merchantName 출현 (fill 1→2) |
| medical_003.jpg | long_receipt, small_text | long_receipt, small_text, **preprocessing_candidate** | T-20: grayscale로 merchantName 출현 (fill 1→2) |
| card_001.jpg | small_text, garbled_source | (변경 없음) | T-20: 모든 variant unchanged — 추가 안 함 |
| pos_005.jpg | long_receipt, small_text | (변경 없음) | T-20 candidate 아님 — 추가 안 함 |

## 5. auto-apply simulation 결과
| sample | candidate | qualityTags | autoApplyAllowed | reason |
|---|---|---|---|---|
| card_002.jpg | clahe | blurred, preprocessing_candidate | True | all_guards_passed |
| medical_001.jpg | clahe | shadow, preprocessing_candidate | True | all_guards_passed |
| pos_006.jpg | upscale_1_5x | small_text, garbled_source, preprocessing_candidate | True | all_guards_passed |
| medical_003.jpg | grayscale | long_receipt, small_text, preprocessing_candidate | True | all_guards_passed |
| card_001.jpg | upscale_1_5x | small_text, garbled_source | False | no_preprocessing_candidate_tag |
| pos_005.jpg | grayscale | long_receipt, small_text | False | no_preprocessing_candidate_tag |
| pos_002.jpg | - | small_text | False | debug_decision_not_accept: preprocessing_blocked |
| invoice/2.pdf | - | dense_table, rowcount_guard_required, preprocessing_blocked | False | invoice_excluded_from_auto_apply |
| invoice/3.pdf | render_dpi_200_grayscale | pdf_low_resolution, preprocessing_candidate, rowcount_guard_required | False | invoice_excluded_from_auto_apply |

## 6. 정상군 방어 확인
| sample | expected block reason | result |
|---|---|---|
| card_001.jpg | no_preprocessing_candidate_tag | [GUARD_OK] no_preprocessing_candidate_tag |
| pos_005.jpg | no_preprocessing_candidate_tag | [GUARD_OK] no_preprocessing_candidate_tag |

## 7. invoice_statement 제외 확인
| 항목 | 결과 |
|---|---|
| invoice_statement 샘플 수 | 2건 |
| autoApplyAllowed | 0건 (모두 invoice_excluded) |
| productionApplied | False (모두) |
| 검증 | PASS |

## 8. 운영 적용 판단
| 항목 | 결과 |
|---|---|
| productionApplied | **False** (변경 없음) |
| receipt autoApplyAllowed | 4건 (candidate 4개 모두) |
| invoice_statement | 영구 제외 유지 |
| next step | Phase 3 limited auto-apply 구현 준비 완료 |

## 9. 검증 결과
- manifest qualityTags 확인: PASS
- auto-apply simulation: PASS (4건)
- Key assertions:
  - PASS: autoApplyAllowed == 4
  - PASS: card_002 allowed
  - PASS: medical_001 allowed
  - PASS: pos_006 allowed
  - PASS: medical_003 allowed
  - PASS: card_001 blocked
  - PASS: pos_005 blocked
  - PASS: invoice excluded (0)
  - PASS: productionApplied=false
- typecheck: PASS (npm run typecheck)
- build: PASS
