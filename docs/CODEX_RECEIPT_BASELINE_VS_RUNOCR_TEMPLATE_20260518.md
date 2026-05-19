# CODEX receipt baseline vs RunOCR 영수증 template verification

## 1. 요약
- 전체 판정: **INCONCLUSIVE**
- 실행 방식: `static_analysis`
- 비교 샘플 수: 17
- 일치: 0
- 불일치: 0
- 미확정: 17

## 2. 검증 기준
- baseline: receipt_generalization selected samples with documentType in pos_receipt, food_cafe_receipt, card_receipt, medical_receipt; finance_slip suppressed samples excluded
- baseline source: `receipt_generalization/ocr_cache.json + current parser`
- baseline sample count: 17
- RunOCR template: `TPL-003` / `영수증`
- template documentType: `(empty)`
- template regions: 0
- template fields: 5

## 3. 샘플별 비교표
| 샘플 | baseline docType | RunOCR docType | 핵심 필드 일치 | row/table 여부 | 상태 | 원인 |
|---|---|---|---:|---|---|---|
| pos_001.jpg | receipt_pos | receipt_pos | 2/2 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| pos_002.jpg | receipt_pos | receipt_pos | 2/2 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| pos_003.jpg | medical_receipt | medical_receipt | 4/4 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| pos_004.jpg | receipt_pos | receipt_pos | 5/5 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| pos_005.jpg | receipt_pos | receipt_pos | 4/4 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| pos_006.jpg | receipt_pos | receipt_pos | 1/1 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| food_001.jpg | unknown | unknown | 0/0 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| food_002.jpg | receipt_pos | receipt_pos | 4/4 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| food_003.jpg | receipt_pos | receipt_pos | 5/5 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| food_004.jpg | receipt_pos | receipt_pos | 4/4 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| food_005.jpg | receipt_pos | receipt_pos | 4/4 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| medical_001.jpg | medical_receipt | medical_receipt | 1/1 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| medical_002.jpg | medical_receipt | medical_receipt | 2/2 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| medical_003.jpg | medical_receipt | medical_receipt | 2/2 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| medical_004.jpg | medical_receipt | medical_receipt | 6/6 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| card_001.jpg | receipt_card | receipt_card | 3/3 | no | inconclusive | api_not_executed_static_equivalent_path_expected |
| card_002.jpg | receipt_card | receipt_card | 4/4 | no | inconclusive | api_not_executed_static_equivalent_path_expected |

## 4. 필드별 비교 상세
### pos_001.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | 문정수정점 | 문정수정점 | yes | - |
| businessNo | - | - | yes | - |
| totalAmount | 18,308 | 18,308 | yes | - |
| transactionDate | - | - | yes | - |
| phone | - | - | yes | - |
| address | - | - | yes | - |
| representative | - | - | yes | - |

### pos_002.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | - | - | yes | - |
| businessNo | - | - | yes | - |
| totalAmount | 45,590 | 45,590 | yes | - |
| transactionDate | - | - | yes | - |
| phone | - | - | yes | - |
| address | - | - | yes | - |
| representative | 박스 | 박스 | yes | - |

### pos_003.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | 미금프라자약국 | 미금프라자약국 | yes | - |
| businessNo | 129-21-65920 | 129-21-65920 | yes | - |
| totalAmount | 10,360 | 10,360 | yes | - |
| transactionDate | - | - | yes | - |
| phone | - | - | yes | - |
| address | 경기 성남시 분당구 금곡동154 번 지 미금프라자 1층 105호 | 경기 성남시 분당구 금곡동154 번 지 미금프라자 1층 105호 | yes | - |
| representative | - | - | yes | - |

### pos_004.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | CUl파주시청점 | CUl파주시청점 | yes | - |
| businessNo | 141-01-16722 | 141-01-16722 | yes | - |
| totalAmount | 5,000 | 5,000 | yes | - |
| transactionDate | - | - | yes | - |
| phone | 031-949-5587 | 031-949-5587 | yes | - |
| address | 경기로 파주시 중앙로263,(금촌동) | 경기로 파주시 중앙로263,(금촌동) | yes | - |
| representative | - | - | yes | - |

### pos_005.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | 이마트 | 이마트 | yes | - |
| businessNo | 208-86-50913 | 208-86-50913 | yes | - |
| totalAmount | 59,480 | 59,480 | yes | - |
| transactionDate | - | - | yes | - |
| phone | 043-841-1234 | 043-841-1234 | yes | - |
| address | - | - | yes | - |
| representative | - | - | yes | - |

### pos_006.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | GS25 | GS25 | yes | - |
| businessNo | - | - | yes | - |
| totalAmount | - | - | yes | - |
| transactionDate | - | - | yes | - |
| phone | - | - | yes | - |
| address | - | - | yes | - |
| representative | - | - | yes | - |

### food_001.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | - | - | yes | - |
| businessNo | - | - | yes | - |
| totalAmount | - | - | yes | - |
| transactionDate | - | - | yes | - |
| phone | - | - | yes | - |
| address | - | - | yes | - |
| representative | - | - | yes | - |

### food_002.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | 경기장애인생산품판매시설 | 경기장애인생산품판매시설 | yes | - |
| businessNo | - | - | yes | - |
| totalAmount | 5,000 | 5,000 | yes | - |
| transactionDate | - | - | yes | - |
| phone | 031-256-9844 | 031-256-9844 | yes | - |
| address | 경기 수원시 장안구 영화동443-13 | 경기 수원시 장안구 영화동443-13 | yes | - |
| representative | - | - | yes | - |

### food_003.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | BAGUETTE | BAGUETTE | yes | - |
| businessNo | 448-20-01024 | 448-20-01024 | yes | - |
| totalAmount | 6,800 | 6,800 | yes | - |
| transactionDate | - | - | yes | - |
| phone | 031-719-1886 | 031-719-1886 | yes | - |
| address | 경기 성남시 분당위 청자일로 240 월드프라자 1층 [정상 | 경기 성남시 분당위 청자일로 240 월드프라자 1층 [정상 | yes | - |
| representative | - | - | yes | - |

### food_004.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | 쭈꾸미낙지볶음전문점 | 쭈꾸미낙지볶음전문점 | yes | - |
| businessNo | 502-30-94239 | 502-30-94239 | yes | - |
| totalAmount | 155,200 | 155,200 | yes | - |
| transactionDate | - | - | yes | - |
| phone | - | - | yes | - |
| address | - | - | yes | - |
| representative | 박준영 | 박준영 | yes | - |

### food_005.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | 이티야커피 | 이티야커피 | yes | - |
| businessNo | - | - | yes | - |
| totalAmount | 2,545 | 2,545 | yes | - |
| transactionDate | - | - | yes | - |
| phone | 032-890-2636 | 032-890-2636 | yes | - |
| address | 인천중구 신흥동3가 7-206 1층 | 인천중구 신흥동3가 7-206 1층 | yes | - |
| representative | - | - | yes | - |

### medical_001.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | - | - | yes | - |
| businessNo | - | - | yes | - |
| totalAmount | 205,000 | 205,000 | yes | - |
| transactionDate | - | - | yes | - |
| phone | - | - | yes | - |
| address | - | - | yes | - |
| representative | - | - | yes | - |

### medical_002.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | 하나동물병원 | 하나동물병원 | yes | - |
| businessNo | - | - | yes | - |
| totalAmount | 88,000 | 88,000 | yes | - |
| transactionDate | - | - | yes | - |
| phone | - | - | yes | - |
| address | - | - | yes | - |
| representative | - | - | yes | - |

### medical_003.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | 귀약점 | 귀약점 | yes | - |
| businessNo | - | - | yes | - |
| totalAmount | 122,850 | 122,850 | yes | - |
| transactionDate | - | - | yes | - |
| phone | - | - | yes | - |
| address | - | - | yes | - |
| representative | - | - | yes | - |

### medical_004.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | (주)크레소티 | (주)크레소티 | yes | - |
| businessNo | 201-81-82695 | 201-81-82695 | yes | - |
| totalAmount | 1,000 | 1,000 | yes | - |
| transactionDate | - | - | yes | - |
| phone | 02-2011-0777 | 02-2011-0777 | yes | - |
| address | 서울 영등포구 양평동3가우림e | 서울 영등포구 양평동3가우림e | yes | - |
| representative | 황윤홍 | 황윤홍 | yes | - |

### card_001.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | - | - | yes | - |
| businessNo | 140-09-20255 | 140-09-20255 | yes | - |
| totalAmount | 90,000 | 90,000 | yes | - |
| transactionDate | - | - | yes | - |
| phone | - | - | yes | - |
| address | 경기 시용시 시정도번길 31 (장인동, 대상센담 | 경기 시용시 시정도번길 31 (장인동, 대상센담 | yes | - |
| representative | - | - | yes | - |

### card_002.jpg
| field | baseline | RunOCR template | normalized match | reason |
|---|---|---|---|---|
| merchantName | 당신만식부께 | 당신만식부께 | yes | - |
| businessNo | 306-13-63556 | 306-13-63556 | yes | - |
| totalAmount | 29,000 | 29,000 | yes | - |
| transactionDate | - | - | yes | - |
| phone | 041-359-7955 | 041-359-7955 | yes | - |
| address | - | - | yes | - |
| representative | - | - | yes | - |

## 5. mismatch 원인 분류
- api_not_executed_static_equivalent_path_expected: 17

## 6. 영수증 템플릿 구조 분석
- template_id: `TPL-003`
- templateName: `영수증`
- documentType: `(empty)`
- regions: 0
- field mapping: 5

현재 저장된 `영수증` 템플릿은 region mapping이 비어 있다. 따라서 `template_id=TPL-003`만 RunOCR API에 전달하면 backend는 template crop OCR 경로가 아니라 full-image OCR/parser 경로로 처리한다. documentType도 비어 있어 template metadata가 documentType을 강제하지 않는다.

## 7. 자동복원 영향 여부
- 자동복원 개입 감지: no
- 이 검증 스크립트는 frontend localStorage, History, restoreProfile 저장소를 읽거나 쓰지 않는다.
- TestWorkspace baseline snapshot과 backend API response 또는 정적 projection만 비교하므로 자동복원 값은 비교 대상에서 제외된다.

## 8. 결론
API live 실행 없이 정적 분석 기준으로는 최종 값 동일성 PASS/FAIL을 확정할 수 없다. 다만 저장된 `영수증` 템플릿은 regions/documentType이 비어 있어, 현재 구조상 template region/field mapping 차이로 결과가 달라질 근거는 없다.

## 9. 다음 작업 제안
- Live API execution is intentionally guarded because /ocr/extract can append ocr-server/data/review_log.jsonl.
- If that side effect is acceptable, rerun with --api-base http://127.0.0.1:<port> --allow-api-side-effects.
- If 영수증 is intended to be a region template, save real regions and documentType in a separate template update task.
- Keep autofill/history restore disabled or excluded when doing value equality checks.

## 10. 이슈
- template_region_mapping_empty: 영수증 template has no regions; backend will not execute template crop/field mapping path from this stored template.
- template_document_type_empty: 영수증 template has no template_json.documentType; /ocr/extract will classify from OCR text unless explicit documentType is sent.
