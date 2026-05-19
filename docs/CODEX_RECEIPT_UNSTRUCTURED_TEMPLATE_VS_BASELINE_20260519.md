# CODEX receipt unstructured template vs baseline verification

## 1. 요약
- 전체 판정: **INCONCLUSIVE**
- 이전 검증 재해석: regions 0개는 비정형 템플릿에서는 실패 근거가 아님.
- 비교 샘플 수: 17
- 일치: 0
- 불일치: 0
- 미확정: 17
- 비정형 receipt_fields 직접 출력 가정 필드 일치: 53/53
- 주요 결론: 접근 가능한 TPL-003 저장값에는 비정형 output field definitions가 없어 실제 RunOCR 출력 컬럼 동일성은 정적 분석만으로 확정 불가.

## 2. 영수증 템플릿 구조
- templateId: `TPL-003`
- templateName: `영수증`
- documentType: `(empty)`
- mode: `(empty)`
- regions: 0
- field_count: 5
- output field definitions found: False
- output field definition source: `not_found_in_accessible_sources`

RunOCR frontend logic indicates that unstructured templates rebuild output fields from `receipt_fields` / `finance_fields`. That path requires `template.mode === "unstructured"`; otherwise raw OCR `fields` are passed through.

## 3. baseline 기준
- 대상: `receipt_generalization` selected 17개
- 포함: pos_receipt, food_cafe_receipt, card_receipt, medical_receipt
- 제외: finance_slip suppressed 샘플
- 수집: `ocr_cache.json` 텍스트에 current parser read-only 적용

## 4. 비교 결과
| 샘플 | baseline docType | RunOCR/template docType | output fields 일치 | 상태 | 원인 |
|---|---|---|---:|---|---|
| pos_001.jpg | receipt_pos | receipt_pos | 2/2 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| pos_002.jpg | receipt_pos | receipt_pos | 2/2 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| pos_003.jpg | medical_receipt | medical_receipt | 4/4 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| pos_004.jpg | receipt_pos | receipt_pos | 5/5 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| pos_005.jpg | receipt_pos | receipt_pos | 4/4 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| pos_006.jpg | receipt_pos | receipt_pos | 1/1 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| food_001.jpg | unknown | unknown | 0/0 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| food_002.jpg | receipt_pos | receipt_pos | 4/4 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| food_003.jpg | receipt_pos | receipt_pos | 5/5 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| food_004.jpg | receipt_pos | receipt_pos | 4/4 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| food_005.jpg | receipt_pos | receipt_pos | 4/4 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| medical_001.jpg | medical_receipt | medical_receipt | 1/1 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| medical_002.jpg | medical_receipt | medical_receipt | 2/2 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| medical_003.jpg | medical_receipt | medical_receipt | 2/2 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| medical_004.jpg | medical_receipt | medical_receipt | 6/6 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| card_001.jpg | receipt_card | receipt_card | 3/3 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |
| card_002.jpg | receipt_card | receipt_card | 4/4 | inconclusive | unstructured_template_mapping_missing, no_live_api_static_only |

## 5. 필드별 비교 상세
### pos_001.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | 문정수정점 | 문정수정점 | yes | match |
| businessNo | - | - | yes | match |
| representative | - | - | yes | match |
| phone | - | - | yes | match |
| address | - | - | yes | match |
| totalAmount | 18,308 | 18,308 | yes | match |

### pos_002.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | - | - | yes | match |
| businessNo | - | - | yes | match |
| representative | 박스 | 박스 | yes | match |
| phone | - | - | yes | match |
| address | - | - | yes | match |
| totalAmount | 45,590 | 45,590 | yes | match |

### pos_003.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | 미금프라자약국 | 미금프라자약국 | yes | match |
| businessNo | 129-21-65920 | 129-21-65920 | yes | match |
| representative | - | - | yes | match |
| phone | - | - | yes | match |
| address | 경기 성남시 분당구 금곡동154 번 지 미금프라자 1층 105호 | 경기 성남시 분당구 금곡동154 번 지 미금프라자 1층 105호 | yes | match |
| totalAmount | 10,360 | 10,360 | yes | match |

### pos_004.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | CUl파주시청점 | CUl파주시청점 | yes | match |
| businessNo | 141-01-16722 | 141-01-16722 | yes | match |
| representative | - | - | yes | match |
| phone | 031-949-5587 | 031-949-5587 | yes | match |
| address | 경기로 파주시 중앙로263,(금촌동) | 경기로 파주시 중앙로263,(금촌동) | yes | match |
| totalAmount | 5,000 | 5,000 | yes | match |

### pos_005.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | 이마트 | 이마트 | yes | match |
| businessNo | 208-86-50913 | 208-86-50913 | yes | match |
| representative | - | - | yes | match |
| phone | 043-841-1234 | 043-841-1234 | yes | match |
| address | - | - | yes | match |
| totalAmount | 59,480 | 59,480 | yes | match |

### pos_006.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | GS25 | GS25 | yes | match |
| businessNo | - | - | yes | match |
| representative | - | - | yes | match |
| phone | - | - | yes | match |
| address | - | - | yes | match |
| totalAmount | - | - | yes | match |

### food_001.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | - | - | yes | match |
| businessNo | - | - | yes | match |
| representative | - | - | yes | match |
| phone | - | - | yes | match |
| address | - | - | yes | match |
| totalAmount | - | - | yes | match |

### food_002.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | 경기장애인생산품판매시설 | 경기장애인생산품판매시설 | yes | match |
| businessNo | - | - | yes | match |
| representative | - | - | yes | match |
| phone | 031-256-9844 | 031-256-9844 | yes | match |
| address | 경기 수원시 장안구 영화동443-13 | 경기 수원시 장안구 영화동443-13 | yes | match |
| totalAmount | 5,000 | 5,000 | yes | match |

### food_003.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | BAGUETTE | BAGUETTE | yes | match |
| businessNo | 448-20-01024 | 448-20-01024 | yes | match |
| representative | - | - | yes | match |
| phone | 031-719-1886 | 031-719-1886 | yes | match |
| address | 경기 성남시 분당위 청자일로 240 월드프라자 1층 [정상 | 경기 성남시 분당위 청자일로 240 월드프라자 1층 [정상 | yes | match |
| totalAmount | 6,800 | 6,800 | yes | match |

### food_004.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | 쭈꾸미낙지볶음전문점 | 쭈꾸미낙지볶음전문점 | yes | match |
| businessNo | 502-30-94239 | 502-30-94239 | yes | match |
| representative | 박준영 | 박준영 | yes | match |
| phone | - | - | yes | match |
| address | - | - | yes | match |
| totalAmount | 155,200 | 155,200 | yes | match |

### food_005.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | 이티야커피 | 이티야커피 | yes | match |
| businessNo | - | - | yes | match |
| representative | - | - | yes | match |
| phone | 032-890-2636 | 032-890-2636 | yes | match |
| address | 인천중구 신흥동3가 7-206 1층 | 인천중구 신흥동3가 7-206 1층 | yes | match |
| totalAmount | 2,545 | 2,545 | yes | match |

### medical_001.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | - | - | yes | match |
| businessNo | - | - | yes | match |
| representative | - | - | yes | match |
| phone | - | - | yes | match |
| address | - | - | yes | match |
| totalAmount | 205,000 | 205,000 | yes | match |

### medical_002.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | 하나동물병원 | 하나동물병원 | yes | match |
| businessNo | - | - | yes | match |
| representative | - | - | yes | match |
| phone | - | - | yes | match |
| address | - | - | yes | match |
| totalAmount | 88,000 | 88,000 | yes | match |

### medical_003.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | 귀약점 | 귀약점 | yes | match |
| businessNo | - | - | yes | match |
| representative | - | - | yes | match |
| phone | - | - | yes | match |
| address | - | - | yes | match |
| totalAmount | 122,850 | 122,850 | yes | match |

### medical_004.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | (주)크레소티 | (주)크레소티 | yes | match |
| businessNo | 201-81-82695 | 201-81-82695 | yes | match |
| representative | 황윤홍 | 황윤홍 | yes | match |
| phone | 02-2011-0777 | 02-2011-0777 | yes | match |
| address | 서울 영등포구 양평동3가우림e | 서울 영등포구 양평동3가우림e | yes | match |
| totalAmount | 1,000 | 1,000 | yes | match |

### card_001.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | - | - | yes | match |
| businessNo | 140-09-20255 | 140-09-20255 | yes | match |
| representative | - | - | yes | match |
| phone | - | - | yes | match |
| address | 경기 시용시 시정도번길 31 (장인동, 대상센담 | 경기 시용시 시정도번길 31 (장인동, 대상센담 | yes | match |
| totalAmount | 90,000 | 90,000 | yes | match |

### card_002.jpg
| field | baseline value | template output value | normalized match | reason |
|---|---|---|---|---|
| merchantName | 당신만식부께 | 당신만식부께 | yes | match |
| businessNo | 306-13-63556 | 306-13-63556 | yes | match |
| representative | - | - | yes | match |
| phone | 041-359-7955 | 041-359-7955 | yes | match |
| address | - | - | yes | match |
| totalAmount | 29,000 | 29,000 | yes | match |

## 6. 핵심 원인 분석
- regions_zero_not_failure: 비정형 템플릿에서는 regions 0개가 정상일 수 있으므로 실패 근거로 보지 않음.
- unstructured_template_mapping_missing: 접근 가능한 TPL-003 저장값에는 template_json.fields/output field definitions가 없음.
- unstructured_mode_not_persisted: 접근 가능한 TPL-003 저장값에는 mode='unstructured'가 없음. 실제 RunOCR localStorage 템플릿과 다를 수 있음.
- document_type_missing_or_mismatch: TPL-003 documentType이 없어 API payload에서 documentType을 강제하지 않음. backend classify_document 결과에 의존.

## 7. 결론
비정형 템플릿 관점에서 regions 0개는 문제가 아니다. 하지만 현재 접근 가능한 `TPL-003 / 영수증` 저장값에는 `mode: unstructured`와 `fields` 정의가 없어, RunOCR가 어떤 output_fields를 생성해야 하는지 확정할 수 없다. parser 결과 자체는 baseline 방식으로 수집됐고, 비정형 템플릿이 receipt_fields 전체를 출력한다는 가정에서는 값은 baseline과 동일해야 한다.

## 8. 다음 작업 제안
- RunOCR localStorage의 mysuit_ocr_templates에서 TPL-003의 mode와 fields를 확인한다.
- 비정형 영수증 템플릿에 mode='unstructured'와 fields(회사명/사업자번호/대표자/tel/주소/총합계금액 등)를 저장한다.
- side effect 허용 환경에서 --api-base ... --allow-api-side-effects로 E2E 응답을 검증한다.
- documentType을 receipt 계열로 강제할지, backend classify_document에 맡길지 정책을 정한다.

## 9. 자동복원 영향 여부
- 자동복원 개입: 없음
- History/restore/localStorage/DB 쓰기 없음
- API 호출은 기본 guard로 차단하며, 명시 옵션이 있을 때만 실행
