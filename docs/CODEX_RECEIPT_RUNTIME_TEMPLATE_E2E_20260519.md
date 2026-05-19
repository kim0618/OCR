# CODEX_RECEIPT_RUNTIME_TEMPLATE_E2E_20260519

## 1. 요약
- 전체 판정: **PASS**
- 이전 검증과 다른 점: repo의 TPL-003만 보지 않고, 화면에서 확인된 영수증 비정형 템플릿 출력 필드(no_1~no_6)를 런타임 정의로 고정해 비교했다.
- regions 0개는 비정형 템플릿에서는 실패 근거가 아니다.
- baseline 샘플: 17개
- 샘플 projection 일치: 17/17
- 필드 projection 일치: 53 match, 49 both_empty, 0 mismatch
- Live API: 미실행 (api_base_not_provided)

## 2. 실제 영수증 템플릿 정의 확인
- UI에서 확인된 출력 필드 정의:
  - no_1 -> 회사명
  - no_2 -> 사업자번호
  - no_3 -> 대표자
  - no_4 -> 전화번호
  - no_5 -> 주소
  - no_6 -> 총합계금액
- repo 템플릿 파일 내 no_1~no_6 정의 발견: False
- localStorage key: `mysuit_ocr_templates`
- Template 탭 localStorage 읽기: True
- UnstructuredBuilder localStorage 저장: True
- UnstructuredBuilder `mode: unstructured` 저장: True
- UnstructuredBuilder `template_json.fields` 저장: True
- UnstructuredBuilder `regions: []` 저장: True
- RunOCR 템플릿 목록 localStorage 사용: True
- localStorage template_json.fields 읽기: True
- RunOCR payload에 fields 포함: False
- 해석: fields는 backend payload로 전달되지 않고, frontend의 activeTemplate.fields로 output_fields/history output을 구성한다.

## 3. baseline 기준
- source: `receipt_generalization`
- selected 영수증 documentType 17개
- finance_slip suppressed 제외
- 수집 방식: `ocr_cache.json` OCR text + 현재 backend receipt parser read-only 실행

## 4. no_1~no_6 매핑 기준
| 템플릿 필드 | 한글명 | baseline 후보 key | 비고 |
|---|---|---|---|
| no_1 | 회사명 | merchantName, companyName, 상호, 회사명 | 런타임 UI 정의 기준 |
| no_2 | 사업자번호 | businessNo, businessNumber, 사업자번호 | 런타임 UI 정의 기준 |
| no_3 | 대표자 | representative, 대표자 | 런타임 UI 정의 기준 |
| no_4 | 전화번호 | tel, phone, 전화번호 | 런타임 UI 정의 기준 |
| no_5 | 주소 | address, 주소 | 런타임 UI 정의 기준 |
| no_6 | 총합계금액 | totalAmount, amount, 총합계금액, 합계금액 | 런타임 UI 정의 기준 |

## 5. 샘플별 비교 결과
| 샘플 | docType | no_1 회사명 | no_2 사업자번호 | no_3 대표자 | no_4 전화번호 | no_5 주소 | no_6 총합계금액 | 상태 |
|---|---|---|---|---|---|---|---|---|
| pos_001.jpg | receipt_pos | 문정수정점 |  |  |  |  | 18,308 | match |
| pos_002.jpg | receipt_pos |  |  | 박스 |  |  | 45,590 | match |
| pos_003.jpg | medical_receipt | 미금프라자약국 | 129-21-65920 |  |  | 경기 성남시 분당구 금곡동154 번 지 미금프라자 1층 105호 | 10,360 | match |
| pos_004.jpg | receipt_pos | CUl파주시청점 | 141-01-16722 |  | 031-949-5587 | 경기로 파주시 중앙로263,(금촌동) | 5,000 | match |
| pos_005.jpg | receipt_pos | 이마트 | 208-86-50913 |  | 043-841-1234 |  | 59,480 | match |
| pos_006.jpg | receipt_pos | GS25 |  |  |  |  |  | match |
| food_001.jpg | unknown |  |  |  |  |  |  | match |
| food_002.jpg | receipt_pos | 경기장애인생산품판매시설 |  |  | 031-256-9844 | 경기 수원시 장안구 영화동443-13 | 5,000 | match |
| food_003.jpg | receipt_pos | BAGUETTE | 448-20-01024 |  | 031-719-1886 | 경기 성남시 분당위 청자일로 240 월드프라자 1층 [정상 | 6,800 | match |
| food_004.jpg | receipt_pos | 쭈꾸미낙지볶음전문점 | 502-30-94239 | 박준영 |  |  | 155,200 | match |
| food_005.jpg | receipt_pos | 이티야커피 |  |  | 032-890-2636 | 인천중구 신흥동3가 7-206 1층 | 2,545 | match |
| medical_001.jpg | medical_receipt |  |  |  |  |  | 205,000 | match |
| medical_002.jpg | medical_receipt | 하나동물병원 |  |  |  |  | 88,000 | match |
| medical_003.jpg | medical_receipt | 귀약점 |  |  |  |  | 122,850 | match |
| medical_004.jpg | medical_receipt | (주)크레소티 | 201-81-82695 | 황윤홍 | 02-2011-0777 | 서울 영등포구 양평동3가우림e | 1,000 | match |
| card_001.jpg | receipt_card |  | 140-09-20255 |  |  | 경기 시용시 시정도번길 31 (장인동, 대상센담 | 90,000 | match |
| card_002.jpg | receipt_card | 당신만식부께 | 306-13-63556 |  | 041-359-7955 |  | 29,000 | match |

## 6. 차이 원인
- runtime_template_definition_missing: no_1~no_6 field definitions were not found in repository template files; runtime UI likely stores them in browser localStorage.
- runocr_payload_missing_fields: RunOCR does not send template field definitions to the backend; frontend activeTemplate.fields generates output fields client-side.
- api_not_run_static_only: read-only 원칙 때문에 `/ocr/extract` live 호출은 기본 미실행.
- autofill_interference: 이번 스크립트는 frontend autofill/history/restore/localStorage write 경로를 실행하지 않아 자동복원 개입 없음.

## 7. 결론
- 화면 기준 영수증 비정형 템플릿 no_1~no_6 정의와 frontend RunOCR projection 흐름 기준으로는 `PASS`.
- RunOCR payload에는 필드 정의가 포함되지 않지만, 이는 현재 구조상 실패가 아니라 frontend activeTemplate.fields가 output_fields를 만드는 구조로 확인된다.
- 실제 브라우저 localStorage export와 네트워크 payload 캡처가 있으면 runtime 저장값까지 완전한 E2E 증거로 고정할 수 있다.

## 8. 다음 권장 작업
- 브라우저 localStorage의 실제 `mysuit_ocr_templates` export 확보
- RunOCR 요청 payload/response/output_fields 저장용 read-only debug snapshot 추가
- 비정형 템플릿 output field definitions를 서버 저장소 또는 repo fixture에 명시 저장
- Test baseline vs RunOCR template E2E 자동화
