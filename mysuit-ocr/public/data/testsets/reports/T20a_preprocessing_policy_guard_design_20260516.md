# T-20a qualityTags 기반 preprocessing policy / guard 설계 결과

## 1. 생성 파일
- `mysuit-ocr\public\data\testsets\reports\T20a_preprocessing_policy_20260516.json`
- `mysuit-ocr\public\data\testsets\reports\T20a_preprocessing_policy_guard_design_20260516.json`
- `mysuit-ocr\public\data\testsets\reports\T20a_preprocessing_policy_guard_design_20260516.md`
- `ocr-server/scripts/design_preprocessing_policy_t20a.py`

## 2. 핵심 요약
- T-20 실험 결과 분석: improved=5, unchanged=4, regressed=1
- policy simulation: conditional_accept 4건, reject_all 6건, unchanged 0건
- invoice_statement/2.pdf: 모든 variant reject (rowCount mismatch) ✓
- invoice_statement/3.pdf: reject_all — qualityTags=[] 이므로 policy_reject (pdf_low_resolution 태그 필요)
  - T-20 실험에서는 render_dpi_200_grayscale이 rowCount exact 회복. 태그 보강 후 T-20c에서 재검토.
- small_text 단독: 모든 processing variant blocked (T-20에서 card_001/pos_001/002/medical_002 회귀 또는 unchanged)
- upscale_1_5x: 가장 안전한 후보 (회귀 0건)

## 3. T-20 variant 분석
| variant | improved | regressed | risk | 정책 |
|---|---:|---:|---|---|
| upscale_1_5x | 2 | 0 | low | blurred/garbled 조건부 허용 |
| clahe | 3 | 1 | medium | shadow/blurred/low_contrast 조건부 |
| clahe_plus_sharpen | 3 | 1 | medium | shadow/blurred/garbled 조건부 |
| grayscale | 1 | 1 | medium | long_receipt 복합만 조건부 |
| sharpen | 1 | 1 | medium | long_receipt 복합만 조건부 |
| denoise | 1 | 3 | high | 기본 차단 |
| threshold_adaptive | 1 | 2 | high | 기본 차단 |
| render_dpi_200_grayscale | 1 | 1 | high | invoice 단순 구조만 조건부 |
| render_dpi_150/200/300 | 0 | 1~2 | high | 기본 차단 |

## 4. qualityTags → preprocessing 매핑
| qualityTag/reason | 후보 variant | guard | 비고 |
|---|---|---|---|
| blurred | clahe, upscale_1_5x | core_fields_not_regressed | card_002 개선 확인 |
| shadow | clahe | core_fields_not_regressed | medical_001 개선 확인 |
| low_contrast | clahe | core_fields_not_regressed | 간접 추정 |
| small_text 단독 | **blocked** | - | card_001/pos_001/002/medical_002 모두 회귀 또는 미개선 |
| long_receipt + small_text | grayscale, clahe | core_fields_not_regressed | medical_003 모든 variant 개선 |
| ocr_garbled | upscale_1_5x | core_fields_not_regressed | pos_006 개선, 회귀 0 |
| pdf_low_resolution | render_dpi_200_grayscale | rowcount_exact + warnings | invoice/3.pdf 개선 |

## 5. documentType별 정책
| documentType | 기본 적용 | 허용 조건 | reject 조건 |
|---|---|---|---|
| invoice_statement | 기본 차단 | render_dpi_200_grayscale + rowCount guard + 단순구조 | rowCount mismatch, warning 증가 |
| receipt 계열 | compare_then_select | core field fill 증가 + 기존 필드 유지 | 기존 필드 손실, false positive |
| finance_slip | 기본 차단 | extractor 미구현 | - |

## 6. 채택 guard
### 공통 guard
- `core_fields_not_regressed`: merchantName/businessNo/totalAmount 기존 값 유지
- `doctype_not_regressed`: 분류 결과가 expected와 더 멀어지지 않음
- `no_new_false_positive`: 새로운 false positive 금액/사업자번호 없음

### receipt guard
- core field fill count 증가 → accept 후보
- source_missing 필드가 새로 채워짐 → accept 후보
- 기존 채워진 핵심 필드 유지 필수

### invoice_statement guard
- rowCount == expectedRowCount 유지 필수
- expectedValueFillRate >= 원본
- critical warning count 증가 없음
- invoice anchor structure (OP-anchor, header-skip 결과) 유지

## 7. policy simulation 결과
| sample | qualityTags | best accepted | final decision | reason |
|---|---|---|---|---|
| receipt_generalization/card_001.jpg | ['small_text'] | None | reject_all | T-20 judgement: unchanged |
| receipt_generalization/card_002.jpg | ['blurred'] | clahe | conditional_accept | T-20 judgement: improved |
| receipt_generalization/medical_001.jpg | ['shadow'] | clahe | conditional_accept | T-20 judgement: improved |
| receipt_generalization/pos_001.jpg | ['small_text'] | None | reject_all | T-20 judgement: unchanged |
| receipt_generalization/pos_002.jpg | ['small_text'] | None | reject_all | T-20 judgement: unchanged |
| receipt_generalization/pos_006.jpg | ['small_text'] | upscale_1_5x | conditional_accept | T-20 judgement: improved |
| invoice_statement/2.pdf | [] | None | reject_all | T-20 judgement: regressed |
| invoice_statement/3.pdf | [] | None | reject_all | T-20 judgement: improved |
| receipt_generalization/medical_002.jpg | ['small_text'] | None | reject_all | T-20 judgement: unchanged |
| receipt_generalization/medical_003.jpg | ['long_receipt', 'small_text'] | grayscale | conditional_accept | T-20 judgement: improved |

## 8. 운영 적용 전략
| Phase | 내용 | 상태 |
|---|---|---|
| Phase 1 | 실험/수동 비교 (T-20) | 완료 |
| Phase 2 | debug mode compare_then_select 구현 (T-20b) | 계획 |
| Phase 3 | qualityTags 기반 조건부 자동화 | 미래 |
| Phase 4 | 운영 기본 적용 여부 재평가 | 미래 |

> Phase 2 이전에는 운영 경로에 전처리를 연결하지 않는다.
> qualityTags metadata가 충분히 보강된 후에 Phase 3 진행 권장.

## 9. 다음 작업 판단
- T-20a policy/guard 설계 완료
- **다음 권장: T-20b debug mode compare_then_select 구현** (blurred/shadow 샘플에서 compare 로직 시험)
- 또는: qualityTags metadata 보강 (T-21) 우선 후 T-20b
- invoice/3.pdf render_dpi_200_grayscale: 별도 invoice precheck T20c로 분리 권장

## 10. 검증 결과
- py_compile: PASS
- policy simulation: PASS (invoice/2.pdf reject_all ✓, invoice/3.pdf reject_all — pdf_low_resolution 태그 미설정)
- typecheck: PASS (npm run typecheck)
- build: 미실행 (신규 스크립트/JSON만 생성, 운영 코드 무수정)
