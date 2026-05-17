# T-20 OCR preprocessing experiment 결과

## 1. 생성 파일
- `mysuit-ocr/public/data/testsets/reports/T20_ocr_preprocessing_experiment_20260516.md`
- `mysuit-ocr/public/data/testsets/reports/T20_ocr_preprocessing_experiment_20260516.json`
- `mysuit-ocr/public/data/testsets/reports/preprocess_t20/`
- `ocr-server/scripts/experiment_ocr_preprocessing_t20.py`

## 2. 핵심 요약
- 후보 10개 샘플에 대해 전처리 실험을 실행했다.
- 총 OCR 실행 결과: 72건.
- 개선 판정 샘플: 5건, mixed: 0건, 회귀: 1건.
- 결론: 일부 샘플만 효과 - qualityTags 기반 조건부 적용 필요

## 3. 실험 대상 샘플
| sample | reason | type | baseline issue |
|---|---|---|---|
| receipt_generalization/card_001.jpg | ocr_source_garbled | jpg | OCR source recovery / garbled text reduction |
| receipt_generalization/card_002.jpg | ocr_source_garbled | jpg | OCR source recovery / garbled text reduction |
| receipt_generalization/medical_001.jpg | ocr_source_missing | jpg | OCR source recovery / garbled text reduction |
| receipt_generalization/pos_001.jpg | ocr_source_garbled | jpg | OCR source recovery / garbled text reduction |
| receipt_generalization/pos_002.jpg | ocr_source_missing | jpg | OCR source recovery / garbled text reduction |
| receipt_generalization/pos_006.jpg | ocr_source_garbled | jpg | OCR source recovery / garbled text reduction |
| invoice_statement/2.pdf | ocr_source_missing | pdf | OCR source recovery / garbled text reduction |
| invoice_statement/3.pdf | ocr_source_missing | pdf | OCR source recovery / garbled text reduction |
| receipt_generalization/medical_002.jpg | OCR에 사업자번호 없음 (동물병원 영수증) | jpg | businessNo/source text visibility check |
| receipt_generalization/medical_003.jpg | OCR에 사업자번호 없음 (수의원 처방영수증) | jpg | businessNo/source text visibility check |

## 4. 전처리 variant
| variant | 설명 |
|---|---|
| original | 원본 이미지 baseline |
| grayscale | BGR -> grayscale |
| clahe | local contrast enhancement |
| sharpen | 3x3 sharpening kernel |
| denoise | fastNlMeansDenoisingColored |
| threshold_adaptive | adaptive Gaussian threshold |
| upscale_1_5x | bicubic 1.5x upscale |
| clahe_plus_sharpen | CLAHE 후 sharpening |
| render_dpi_150 | PDF page 1 render at 150 DPI |
| render_dpi_200 | PDF page 1 render at 200 DPI baseline |
| render_dpi_300 | PDF page 1 render at 300 DPI |
| render_dpi_200_grayscale | PDF 200 DPI grayscale render |

## 5. 전체 결과 요약
| variant | improved | regressed | mixed | unchanged | 판정 |
|---|---|---|---|---|---|
| clahe | 3 | 1 | 0 | 4 | guarded_only |
| clahe_plus_sharpen | 3 | 1 | 0 | 4 | guarded_only |
| denoise | 1 | 3 | 0 | 4 | guarded_only |
| grayscale | 1 | 1 | 0 | 6 | guarded_only |
| original | 0 | 0 | 0 | 8 | no_effect |
| render_dpi_150 | 0 | 1 | 1 | 0 | guarded_only |
| render_dpi_200 | 0 | 2 | 0 | 0 | guarded_only |
| render_dpi_200_grayscale | 1 | 1 | 0 | 0 | guarded_only |
| render_dpi_300 | 0 | 2 | 0 | 0 | guarded_only |
| sharpen | 1 | 1 | 0 | 6 | guarded_only |
| threshold_adaptive | 1 | 2 | 0 | 5 | guarded_only |
| upscale_1_5x | 2 | 0 | 0 | 6 | candidate |

## 6. 샘플별 상세
| sample | best variant | baseline issue | improvement | regression | 판정 |
|---|---|---|---|---|---|
| receipt_generalization/card_001.jpg | original | ocr_source_garbled | [] | [] | unchanged |
| receipt_generalization/card_002.jpg | clahe | ocr_source_garbled | ["core field fill increased"] | [] | improved |
| receipt_generalization/medical_001.jpg | clahe | ocr_source_missing | ["core field fill increased"] | [] | improved |
| receipt_generalization/pos_001.jpg | original | ocr_source_garbled | [] | [] | unchanged |
| receipt_generalization/pos_002.jpg | original | ocr_source_missing | [] | [] | unchanged |
| receipt_generalization/pos_006.jpg | clahe_plus_sharpen | ocr_source_garbled | ["core field fill increased", "totalAmount source appeared"] | [] | improved |
| invoice_statement/2.pdf | render_dpi_150 | ocr_source_missing | [] | ["rowCount mismatch expected 13"] | regressed |
| invoice_statement/3.pdf | render_dpi_200_grayscale | ocr_source_missing | ["rowCount exact recovered"] | [] | improved |
| receipt_generalization/medical_002.jpg | original | OCR에 사업자번호 없음 (동물병원 영수증) | [] | [] | unchanged |
| receipt_generalization/medical_003.jpg | grayscale | OCR에 사업자번호 없음 (수의원 처방영수증) | ["core field fill increased"] | [] | improved |

## 7. invoice_statement 영향
| sample | original rowCount | best variant rowCount | warning 변화 | 판정 |
|---|---|---|---|---|
| invoice_statement/2.pdf | 18 | 17 | 0->0 | regressed |
| invoice_statement/3.pdf | 2 | 1 | 1->1 | improved |

## 8. 전처리 적용 전략
- 적용 가능: 회귀 없이 source presence/core fill이 개선된 variant를 해당 qualityTag 샘플에만 제한 적용.
- 조건부 적용: sharpen/CLAHE 계열은 small_text, low_contrast, shadow 후보에만 A/B guard와 함께 사용.
- 적용 금지: threshold 계열은 line count 급감 또는 docType/table rowCount 회귀가 있으면 운영 기본값 금지.
- 추가 실험 필요: PDF는 rowCount exact guard를 통과한 DPI/render 조합만 별도 후보로 둔다.

## 9. 다음 작업 판단
- 일부 샘플만 효과 - qualityTags 기반 조건부 적용 필요

## 10. 검증 결과
- py_compile: PASS: python -m py_compile scripts/experiment_ocr_preprocessing_t20.py
- experiment script: PASS: python scripts/experiment_ocr_preprocessing_t20.py
- typecheck: PASS: npm.cmd run typecheck
- build: PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)
