# T-20b debug mode compare_then_select preprocessing 결과

## 1. 생성/수정 파일
- `ocr-server/preprocessing_policy.py` (신규)
- `ocr-server/scripts/verify_preprocessing_compare_then_select_t20b.py` (신규)
- `mysuit-ocr/public/data/testsets/reports/T20b_preprocessing_compare_then_select_20260516.json`
- `mysuit-ocr/public/data/testsets/reports/T20b_preprocessing_compare_then_select_20260516.md`

## 2. 핵심 요약
- compare_then_select 검증: 9/9 PASS, overall=PASS
- 운영 OCR 기본 경로 수정 없음 (debug_preprocessing=True 시뮬레이션만)
- T-20 캐시 결과 활용 (OCR 재실행 없음)
- receipt 4건 candidate_accept: card_002(clahe), medical_001(clahe), pos_006(upscale_1_5x), medical_003(grayscale)
- invoice/3.pdf: render_dpi_200_grayscale candidate_accept (rowCount guard 통과)
- invoice/2.pdf: preprocessing_blocked + rowCount mismatch → reject
- threshold/denoise: always_blocked

## 3. 지원 variant
| variant | 대상 | 상태 |
|---|---|---|
| clahe | blurred/shadow/low_contrast/long_receipt+small_text | 지원 |
| upscale_1_5x | blurred/garbled_source | 지원 |
| clahe_plus_sharpen | blurred/shadow/garbled_source/long_receipt+small_text | 지원 |
| grayscale | long_receipt+small_text | 지원 |
| render_dpi_200_grayscale | invoice pdf_low_resolution | 지원 |
| threshold_adaptive | - | always_blocked |
| denoise | - | always_blocked |
| render_dpi_150/200/300 | - | always_blocked |

## 4. policy 적용 결과
| sample | qualityTags | candidates | 비고 |
|---|---|---|---|
| card_002.jpg | blurred | clahe, upscale_1_5x, clahe_plus_sharpen | selected=clahe |
| medical_001.jpg | shadow | clahe, clahe_plus_sharpen | selected=clahe |
| pos_006.jpg | small_text, garbled_source, preprocessing_candidate | upscale_1_5x, clahe_plus_sharpen | selected=upscale_1_5x |
| medical_003.jpg | long_receipt, small_text | grayscale, clahe, clahe_plus_sharpen | selected=grayscale |
| invoice/3.pdf | pdf_low_resolution, preprocessing_candidate, rowcount_guard_required | render_dpi_200_grayscale | selected=render_dpi_200_grayscale |
| invoice/2.pdf | dense_table, rowcount_guard_required, preprocessing_blocked | (없음) | selected=- |
| card_001.jpg | small_text, garbled_source | upscale_1_5x, clahe_plus_sharpen | selected=- |
| pos_001.jpg | small_text, garbled_source | upscale_1_5x, clahe_plus_sharpen | selected=- |
| medical_002.jpg | small_text | (없음) | selected=- |

## 5. compare_then_select 결과
| sample | original core fill / rowCount | best variant | decision | guard reason |
|---|---|---|---|---|
| card_002.jpg | fill=2/4 | clahe | candidate_accept | core field fill increased |
| medical_001.jpg | fill=1/2 | clahe | candidate_accept | core field fill increased |
| pos_006.jpg | fill=1/3 | upscale_1_5x | candidate_accept | businessNo source appeared, totalAmount source appeared |
| medical_003.jpg | fill=1/2 | grayscale | candidate_accept | core field fill increased |
| invoice/3.pdf | rowCount=2/1 | render_dpi_200_grayscale | candidate_accept | rowCount exact recovered |
| invoice/2.pdf | rowCount=18/13 | - | no_candidate | - |
| card_001.jpg | fill=2/4 | - | no_improvement | - |
| pos_001.jpg | fill=3/3 | - | no_improvement | - |
| medical_002.jpg | fill=2/2 | - | no_candidate | - |

## 6. invoice_statement guard 결과
| sample | variant | original rowCount | after rowCount | decision | reason |
|---|---|---:|---:|---|---|
| invoice/3.pdf | render_dpi_150 | 2/1 | 2/1 | always_blocked |  |
| invoice/3.pdf | render_dpi_200 | 2/1 | 2/1 | always_blocked |  |
| invoice/3.pdf | render_dpi_300 | 2/1 | 2/1 | always_blocked |  |
| invoice/3.pdf | render_dpi_200_grayscale | 2/1 | 1/1 | candidate_accept | rowCount exact recovered |
| invoice/2.pdf | render_dpi_150 | 18/13 | 17/13 | always_blocked |  |
| invoice/2.pdf | render_dpi_200 | 18/13 | 18/13 | always_blocked |  |
| invoice/2.pdf | render_dpi_300 | 18/13 | 17/13 | always_blocked |  |

## 7. 운영 적용 여부
- **production default**: False (운영 기본 결과 변경 없음)
- **debug mode**: wouldApplyInDebug=True 시 전처리 결과를 debug 출력으로만 표시
- **next step**: T-20b module 검증 완료. 운영 적용은 T-20d 이후 결정.
  - 적용 후보: card_002(clahe), medical_001(clahe), pos_006(upscale_1_5x), medical_003(grayscale), invoice/3.pdf(render_dpi_200_grayscale)
  - 차단: invoice/2.pdf, card_001, pos_001, pos_002, medical_002

## 8. 검증 결과
- py_compile preprocessing_policy.py: PASS
- py_compile verify_preprocessing_compare_then_select_t20b.py: PASS
- verify script: PASS (9/9)
- typecheck: PASS (npm run typecheck)
- build: 미실행 (신규 Python 파일만 생성, JS 코드 무수정)
