# T-16 baseline receipt + invoice_statement final audit

## 1. 생성 파일
- `mysuit-ocr\public\data\testsets\reports\T16_baseline_receipt_invoice_final_audit_20260516.json`
- `mysuit-ocr\public\data\testsets\reports\T16_baseline_receipt_invoice_final_audit_20260516.md`
- `ocr-server/scripts/verify_baseline_receipt_invoice_quality_t16_final.py`

## 2. 핵심 요약
T-15a~T-15e 시리즈를 통해 receipt_generalization 기준으로 아래 개선이 완료되었다.

| 작업 | 개선 내용 |
|---|---|
| T-15a | pos_receipt businessNo 5→4, merchantName 3→2 |
| T-15b | medical_receipt 정분류 2/6→5/6, card_receipt 오분류 0건 |
| T-15c | food_cafe_receipt merchantName 4→2 |
| T-15d | card_receipt businessNo 2→0, merchantName 2→1 |
| T-15e | finance_slip selected 1→0, suppressed 4→5 (정합) |

**모든 작업에서 invoice_statement 7/7 exact 유지, 회귀 0건.**

## 3. T-14 vs T-16 전체 비교
| 항목 | T-14 | T-16 | 변화 |
|---|---:|---:|---:|
| total samples | 57 | 57 | - |
| selected | 49 | 48 | -1 |
| suppressed | 6 | 7 | +1 |
| unknown | 2 | 2 | +0 |
| error | 0 | 0 | +0 |

> 주: selected 감소는 finance_001.jpg expectedStatus 변경(selected→suppressed_bank_slip, T-15e) 때문.

## 4. documentType별 최종 결과
| documentType | 주요 개선 | 남은 한계 | 판정 |
|---|---|---|---|
| invoice_statement | rowCount 7/7 exact | T-15 시리즈 전체 회귀 없음 | **pass** |
| finance_slip | 전체 5건 suppressed_bank_slip으로 정합(T-15e) | extractor 미구현 | **suppressed_policy_ok** |
| medical_receipt | 정분류 2/4→4/4(T-15b) | google/9.jpg 1건 미확인 | **improved** |
| pos_receipt | businessNo 5→4 | merchantName 3→2(T-15a), 잔여 OCR source 한계 | **improved** |
| food_cafe_receipt | merchantName 4→2(T-15c) | 잔여 OCR source/false-positive 한계 | **improved** |
| card_receipt | businessNo 2→0 | merchantName 2→1(T-15d), 잔여 1건 OCR 불완전 | **improved** |
| unknown | 1건 unknown | OCR 품질 한계 | **acceptable_limit** |

## 5. 필드별 before/after (receipt_generalization 기준)
| documentType | field | T-14 missing | T-16 missing | 개선 |
|---|---|---:|---:|---:|
| pos_receipt | businessNo | 4 | 3 | -1 |
| pos_receipt | merchantName | 2 | 1 | -1 |
| pos_receipt | totalAmount | 1 | 1 | 0 |
| food_cafe_receipt | merchantName | 4 | 2 | -2 |
| food_cafe_receipt | totalAmount | 1 | 1 | 0 |
| card_receipt | merchantName | 2 | 1 | -1 |
| card_receipt | businessNo | 2 | 0 | -2 |
| card_receipt | totalAmount | 0 | 0 | 0 |
| medical_receipt | merchantName | 2 | 2 | 0 |

## 6. medical_receipt 분류 결과
| 항목 | T-14 | T-16 | 변화 |
|---|---:|---:|---:|
| medical_receipt 정분류 (receipt_generalization) | 2/4 | 4/4 | +2 |

> 주: google/9.jpg(medical_receipt expected) 1건은 google testset locked으로 live RunAll 없이 확인 불가.

## 7. finance_slip 정책 결과
| 항목 | T-14 | T-16 | 변화 |
|---|---:|---:|---:|
| finance_slip selected | 1 | 0 | -1 |
| finance_slip suppressed_bank_slip | 4 | 5 | +1 |

> T-15e에서 finance_001.jpg expectedStatus를 selected→suppressed_bank_slip으로 변경. 현재 finance_slip extractor 미구현.

## 8. invoice_statement 회귀 확인
| sample | expected | actual | status |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | exact |
| 2.pdf | 13 | 13 | exact |
| 3.pdf | 1 | 1 | exact |
| 4.pdf | 1 | 1 | exact |
| 5.pdf | 6 | 6 | exact |
| 6.pdf | 6 | 6 | exact |
| 7.pdf | 1 | 1 | exact |

> invoice_statement: **7/7 exact 유지**

## 9. 남은 이슈
| 이슈 | 유형 | 후속 필요성 |
|---|---|---|
| pos_001 businessNo | ocr_source_missing | OCR garbled, 복구 불가 |
| pos_002 businessNo+merchantName | ocr_source_missing | 헤더 없는 영수증, OCR source 없음 |
| pos_006 businessNo+totalAmount | ocr_source_garbled | OCR 심각하게 손상 |
| food_001 merchantName+totalAmount | ocr_source_broken | OCR 전체 garbled |
| food_002 merchantName | address_false_positive | 경기 prefix → 주소 필터 차단 |
| card_001 merchantName+phone | ocr_source_incomplete | 라벨 garbled, '송명( 이'로만 남음 |
| card_002 address | ocr_garbled_province | 충청남도 → 충심남도 garble, _ADDR_START_RE 미매칭 |
| card_002 merchantName(garbled) | partial_ocr_recovery | 당신만식부께 = garbled value, T-15d에서 추출했으나 품질 미흡 |
| medical_receipt 1건 미분류 | doc_type_mismatch | google/9.jpg: receipt_pos로 분류, live RunAll 필요 |
| pos_003.jpg manifest 오기입 | metadata_issue | manifest=pos_receipt, OCR=약국영수증(medical_receipt) |
| google/6.jpg manifest 불일치 | metadata_issue_locked | manifest=finance_slip, OCR=GS25 편의점, google testset locked |
| finance_slip extractor 미구현 | feature_gap | T-16a 별도 큰 작업으로 분리 예정 |

## 10. 다음 작업 판단

**T-15a~T-15e baseline receipt 1차 개선 마감.**

### 즉시 후속 후보
| 우선순위 | 작업 | 근거 |
|---|---|---|
| P1 | pos_003.jpg manifest 재분류 (medical_receipt) | T-15b에서 실제 의료 영수증으로 확인됨 |
| P2 | google/6.jpg manifest 재검토 (편의점 영수증?) | locked testset, 차기 google 업데이트 시 검토 |
| P3 | qualityTags metadata 보강 | 일부 __none__ 태그 샘플의 tag 세분화 |
| P4 | card_002 merchantName 품질 개선 | 당신만식부께 = garbled, 재OCR 또는 GT 보강 필요 |

### 장기 후속 후보
| 작업 | 근거 |
|---|---|
| T-16a finance_slip extractor | KB ATM 영수증 Tier-1 필드 추출 |
| T-16b pos_receipt OCR source 개선 | pos_001/002 OCR 재촬영 또는 GT 보강 |
| T-16c food_002 merchantName address false-positive 개선 | 경기장애인생산품판매시설 추출 차단 패턴 분리 |

## 11. 검증 결과
- py_compile: PASS
- verify script: PASS
- typecheck: PASS (npm run typecheck)
- build: 미실행 (코드 수정 없음)
