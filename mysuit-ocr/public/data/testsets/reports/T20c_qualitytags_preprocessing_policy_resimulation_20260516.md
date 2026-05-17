# T-20c qualityTags 보강 및 preprocessing policy 재시뮬레이션 결과

## 1. 수정 파일
- `mysuit-ocr/public/data/testsets/invoice_statement/manifest.json`
- `mysuit-ocr/public/data/testsets/receipt_generalization/manifest.json`
- `ocr-server/scripts/resimulate_preprocessing_policy_t20c.py`

## 2. 백업 파일
- `mysuit-ocr/backup/manifest_invoice_statement_20260516_before_T20c_qualitytags.json`
- `mysuit-ocr/backup/manifest_receipt_generalization_20260516_before_T20c_qualitytags.json`

## 3. 핵심 요약
- T-20a → T-20c: conditional_accept 4→5건, reject_all 6→5건
- decision 변화: 1건
- invoice/3.pdf: reject_all → conditional_accept (pdf_low_resolution 태그 추가)
  - T-20 결과 근거: render_dpi_200_grayscale이 rowCount exact 회복 (원본 2→expected 1)
- invoice/2.pdf: reject_all 유지 (preprocessing_blocked 태그 추가, rowCount 회귀 확인)
- receipt 4건 conditional_accept 유지 (card_002/medical_001/pos_006/medical_003)
- 운영 OCR 코드 수정 없음. 정책 문서/simulation만 업데이트.

## 4. qualityTags 변경 목록
| sample | before tags | after tags | 근거 |
|---|---|---|---|
| card_001.jpg | small_text | small_text, garbled_source | T-20: ocr_source_garbled 확인 (모든 variant unchanged) |
| pos_001.jpg | small_text | small_text, garbled_source | T-20: ocr_source_garbled 확인 (모든 variant unchanged) |
| pos_006.jpg | small_text | small_text, garbled_source, preprocessing_candidate | T-20: upscale_1_5x/clahe_plus_sharpen 개선 |
| invoice/2.pdf | (없음) | dense_table, rowcount_guard_required, preprocessing_blocked | T-20: 모든 DPI variant rowCount mismatch 회귀 |
| invoice/3.pdf | (없음) | pdf_low_resolution, preprocessing_candidate, rowcount_guard_required | T-20: render_dpi_200_grayscale rowCount exact 회복 |

## 5. policy simulation before/after
| sample | before decision | after decision | best variant | 변화 |
|---|---|---|---|---|
| card_001.jpg | reject_all | reject_all | - | - |
| card_002.jpg | conditional_accept | conditional_accept | clahe | - |
| medical_001.jpg | conditional_accept | conditional_accept | clahe | - |
| pos_001.jpg | reject_all | reject_all | - | - |
| pos_002.jpg | reject_all | reject_all | - | - |
| pos_006.jpg | conditional_accept | conditional_accept | upscale_1_5x | - |
| invoice/2.pdf | reject_all | reject_all | - | - |
| invoice/3.pdf | reject_all | conditional_accept | render_dpi_200_grayscale | **변경** |
| medical_002.jpg | reject_all | reject_all | - | - |
| medical_003.jpg | conditional_accept | conditional_accept | grayscale | - |

## 6. invoice_statement 정책 확인
| sample | decision | rowCount guard | preprocessing 방침 | 비고 |
|---|---|---|---|---|
| invoice/2.pdf | reject_all | rowcount_guard_required | preprocessing_blocked | T-20 rowCount 회귀 (13→17). dense_table 구조. |
| invoice/3.pdf | conditional_accept | rowcount_guard_required | render_dpi_200_grayscale 조건부 | T-20 exact 회복. 단순 single item table. |

## 7. 운영 적용 판단
- **자동 적용 가능**: 없음 (Phase 2 이전 미연결)
- **debug mode 후보**: card_002(clahe), medical_001(clahe), pos_006(upscale_1_5x), medical_003(grayscale)
- **invoice debug 후보**: invoice/3.pdf (render_dpi_200_grayscale, rowcount_guard 통과 조건)
- **blocked**: invoice/2.pdf, card_001, pos_001, pos_002, medical_002
- **manual review 불필요**: 모든 샘플 T-20 실험 결과 근거 확인 완료

## 8. 검증 결과
- JSON validation: PASS
- policy simulation: PASS
  - invoice/2.pdf reject_all: OK
  - invoice/3.pdf conditional_accept: OK
  - receipt 4건 maintained: OK
- typecheck: PASS (npm run typecheck)
- build: 미실행 (manifest JSON + script만 수정, 운영 코드 무수정)

## 9. 다음 작업 판단
- T-20c qualityTags 보강 및 policy 재시뮬레이션 완료
- **다음 권장: T-20b debug mode compare_then_select 구현**
  - blurred/shadow 샘플(card_002, medical_001)에서 compare 로직 시험
  - invoice/3.pdf render_dpi_200_grayscale compare 별도 T-20c 후속 또는 T-20b 포함
- 또는 추가 qualityTags 보강 후 T-20b 진행
