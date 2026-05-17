# T-20a qualityTags 기반 preprocessing policy / guard 설계 결과

## 1. 생성 파일
- `mysuit-ocr/public/data/testsets/reports/T20a_preprocessing_policy_20260516.json`
- `mysuit-ocr/public/data/testsets/reports/T20a_preprocessing_policy_guard_design_20260516.json`
- `mysuit-ocr/public/data/testsets/reports/T20a_preprocessing_policy_guard_design_20260516.md`
- `ocr-server/scripts/design_preprocessing_policy_t20a.py`

## 2. 핵심 요약
- T-20 실험 결과(improved=5, unchanged=4, regressed=1) 기반 policy 설계
- policy simulation: conditional_accept 4건, reject_all 6건, unchanged 0건
- receipt 4건 conditional_accept: card_002(clahe), medical_001(clahe), pos_006(upscale_1_5x), medical_003(grayscale)
- invoice_statement/2.pdf: reject_all ✓ (rowCount mismatch 회귀)
- invoice_statement/3.pdf: reject_all — qualityTags=[] 이므로 policy_reject
  - T-20 실험에서는 render_dpi_200_grayscale이 rowCount exact 회복 (2→1). pdf_low_resolution 태그 보강 후 T-20c에서 재검토.
- small_text 단독 샘플: 모든 processing variant blocked
- upscale_1_5x: 가장 안전한 후보 (T-20 회귀 0건)
- 운영 연결 없음 — 정책 문서/JSON만 생성

## 3. policy simulation 결과
| sample | qualityTags | best accepted | final decision |
|---|---|---|---|
| receipt_generalization/card_001.jpg | ['small_text'] | - | reject_all |
| receipt_generalization/card_002.jpg | ['blurred'] | clahe | conditional_accept |
| receipt_generalization/medical_001.jpg | ['shadow'] | clahe | conditional_accept |
| receipt_generalization/pos_001.jpg | ['small_text'] | - | reject_all |
| receipt_generalization/pos_002.jpg | ['small_text'] | - | reject_all |
| receipt_generalization/pos_006.jpg | ['small_text'] | upscale_1_5x | conditional_accept |
| invoice_statement/2.pdf | [] | - | reject_all |
| invoice_statement/3.pdf | [] | - | reject_all |
| receipt_generalization/medical_002.jpg | ['small_text'] | - | reject_all |
| receipt_generalization/medical_003.jpg | ['long_receipt', 'small_text'] | grayscale | conditional_accept |

## 4. variant 정책 요약
| variant | risk | enabledFor | 판정 |
|---|---|---|---|
| upscale_1_5x | low | blurred, ocr_garbled_with_small | 조건부 허용 |
| clahe | medium | blurred, shadow, low_contrast | 조건부 허용 |
| clahe_plus_sharpen | medium | blurred, shadow, garbled_source | 조건부 허용 |
| grayscale | medium | long_receipt, dense_content | long_receipt 복합만 허용 |
| sharpen | medium | long_receipt | long_receipt 복합만 허용 |
| denoise | high | (없음) | 기본 차단 |
| threshold_adaptive | high | (없음) | 기본 차단 |
| render_dpi_200_grayscale | high | pdf_low_resolution | invoice 단순구조 + guard 필수 |

## 5. 운영 적용 전략
| Phase | 내용 | 상태 |
|---|---|---|
| Phase 1 | 실험/수동 비교 (T-20) | 완료 |
| Phase 2 | debug mode compare_then_select 구현 (T-20b) | 계획 |
| Phase 3 | qualityTags 기반 조건부 자동화 | 미래 |
| Phase 4 | 운영 기본값 적용 여부 재평가 | 미래 |

> Phase 2 이전에는 운영 경로에 전처리를 연결하지 않는다.

## 6. 다음 작업 판단
- T-20a policy/guard 설계 완료
- **다음 권장 T-20b**: debug mode compare_then_select 구현 (blurred/shadow 샘플 비교 로직 시험)
- 또는 **T-21**: qualityTags metadata 보강 우선 후 T-20b
- invoice/3.pdf render_dpi_200_grayscale: T-20c에서 별도 invoice precheck 권장

## 7. 검증 결과
- py_compile: PASS: `python -m py_compile scripts/design_preprocessing_policy_t20a.py`
- policy simulation: PASS (exit 0): `python scripts/design_preprocessing_policy_t20a.py`
- typecheck: PASS: `npm.cmd run typecheck`
- build: 미실행 (신규 스크립트/JSON만 생성, 운영 코드 무수정)
