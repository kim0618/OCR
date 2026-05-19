# CODEX_RECEIPT_ACTUAL_RESULTS_COMPARE_20260519

## 1. 요약
- 전체 판정: **INCONCLUSIVE**
- 실제 baseline 결과 존재: True / actual=True
- 실제 RunOCR 결과 존재: False / actual=False
- 비교 샘플 수: 0
- sample match/mismatch: 0 / 0
- field match/mismatch/both_empty/missing: 0 / 0 / 0 / 0
- 핵심 결론: 저장된 실제 RunOCR 영수증 템플릿 output_fields가 없어 실제 결과끼리 같다고 판정할 수 없다.

## 2. 실제 결과 source
- baseline: `mysuit-ocr\public\data\testsets\reports\T22_current_ocr_baseline_snapshot_20260517.json`
- baseline actual 근거: existing Test baseline snapshot/report JSON
- baseline warnings: cache_based_parser:no_live_runall_export, doc_type_mismatch:medical_receipt!=manifest:pos_receipt, doc_type_mismatch:unknown!=manifest:food_cafe_receipt, metadata_issue:manifest=pos_receipt, OCR/source indicates medical receipt, taxAmount=doc_level_pushdown, totalAmount=doc_level_pushdown
- RunOCR: `-`
- RunOCR actual 근거: -
- projection/static 리포트 제외: docs\CODEX_RECEIPT_RUNTIME_TEMPLATE_E2E_20260519.json, docs\CODEX_RECEIPT_BASELINE_VS_RUNOCR_TEMPLATE_20260518.json, docs\CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_VS_BASELINE_20260519.json

## 3. 영수증 템플릿 필드 기준
| 템플릿 필드 | 한글명 | baseline 후보 key | RunOCR 후보 key |
|---|---|---|---|
| no_1 | 회사명 | merchantName, companyName, 회사명, 상호 | no_1, 회사명, 상호 |
| no_2 | 사업자번호 | businessNo, businessNumber, 사업자번호 | no_2, 사업자번호 |
| no_3 | 대표자 | representative, 대표자 | no_3, 대표자 |
| no_4 | 전화번호 | tel, phone, telephone, 전화번호 | no_4, 전화번호, tel, phone |
| no_5 | 주소 | address, 주소 | no_5, 주소 |
| no_6 | 총합계금액 | totalAmount, amount, total, 총합계금액, 합계금액, 결제금액 | no_6, 총합계금액, 합계금액, 결제금액, totalAmount, amount, total |

## 4. 샘플별 비교 결과
- 비교 가능한 실제 RunOCR 샘플이 없다.

## 5. 필드별 상세 비교
- 상세 비교 없음.

## 6. 불일치 원인 분석
- actual_runocr_result_missing: No stored RunOCR receipt-template result with output_fields was found for receipt_generalization samples.
- sample_not_matched: No common sample could be matched between baseline and actual RunOCR result data.
- projection_only_not_actual: Projection/static CODEX receipt reports were explicitly excluded from PASS evidence.

## 7. 자동복원 영향
- 자동복원 개입 확인: None
- 사유: actual RunOCR output_fields were not found, so autofill metadata could not be inspected

## 8. 결론
- 현재 저장된 실제 결과 기준으로는 RunOCR 영수증 템플릿 실제 output_fields가 없어서 동일 여부를 판단할 수 없다.
- 이전 projection/static 리포트는 실제 RunOCR 결과로 인정하지 않았다.

## 9. 다음 작업
- 브라우저 localStorage의 `mysuit_ocr_history`, `mysuit_ocr_history_details`, `mysuit_ocr_templates` export 확보
- RunOCR 영수증 템플릿으로 receipt_generalization 샘플을 실행한 실제 결과 JSON/export 제공
- side-effect 없는 RunOCR 결과 export 기능 마련
