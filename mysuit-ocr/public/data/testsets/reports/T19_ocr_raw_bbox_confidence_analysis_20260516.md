# T-19 OCR raw confidence/bbox 활용 가능성 분석

## 1. 생성 파일
- `C:/OCR/mysuit-ocr/public/data/testsets/reports/T19_ocr_raw_bbox_confidence_analysis_20260516.md`
- `C:/OCR/mysuit-ocr/public/data/testsets/reports/T19_ocr_raw_bbox_confidence_analysis_20260516.json`
- `C:/OCR/ocr-server/scripts/analyze_ocr_raw_bbox_confidence_t19.py`

## 2. 핵심 요약
- backend 런타임에는 PaddleOCR line 단위 `pts/text/conf` 구조가 존재한다.
- 현재 T-18/RunAll 저장 산출물에는 57개 샘플의 full raw OCR line/token bbox/confidence가 보존되어 있지 않다.
- 따라서 후속 구현 전에는 live API/debug 또는 별도 진단 실행으로 raw line snapshot을 남기는 단계가 필요하다.
- T-18 기준 최다 실패 원인은 classification_mismatch 9건이므로, 위치 가중치 기반 분류 진단/구현이 1순위다.

## 3. raw OCR 구조
| 필드 | 존재 여부 | 설명 |
|---|---|---|
| lineTuple | yes | PaddleOCR output is normalized to (pts, text, conf). pts is a polygon; conf is line recognition score. |
| apiFieldsBBoxConfidence | yes | Generic non-template OCR path can expose fields[] entries with confidence and display-scaled bbox. |
| extractDebugBboxes | yes | extract_debug can expose upper/amount/handwritten total block bboxes, but not the full raw line list in RunAll reports. |
| invoiceSourceBboxes | yes | invoice_statement internally attaches sourceBboxes to several table item paths. |
| fullRawLinesPersisted | no | Current T18/RunAll-style report artifacts do not persist complete raw OCR line/token coordinates for the 57-sample audit set. |

## 4. bbox/confidence 존재율
| 항목 | count |
|---|---|
| executed samples | 57 |
| persisted bbox available samples | 0 |
| persisted confidence available samples | 0 |
| line-level bbox count in T18 artifacts | 0 |
| token-level bbox count in T18 artifacts | 0 |
| missing bbox samples | 57 |
| missing confidence samples | 57 |

## 5. 실패 원인별 bbox 활용 가능성
| reason | samples | bbox 활용 가능성 | 비고 |
|---|---|---|---|
| classification_mismatch | 9 | high | keyword position weighting can distinguish top facility/store signals from lower payment blocks |
| parser_missed_source_exists | 4 | high | source text exists, so line position, label proximity, and confidence can improve candidate selection |
| ambiguous_candidates | 1 | high | bbox y-band/column proximity can choose between competing numeric candidates |
| ocr_source_garbled | 3 | medium | confidence can mark low-quality OCR; bbox alone will not repair garbled text |
| ocr_source_missing | 2 | low | missing OCR source usually needs preprocessing/re-OCR rather than candidate scoring |

## 6. merchantName 후보 분석
| sample | current | bbox 후보 | confidence | 판정 |
|---|---|---|---|---|
| baseline/8.jpg | 효성온누리약국 | requires live raw lines; not present in persisted T18 artifact | N/A | high: top-line/businessNo/address proximity can rank name candidates |
| baseline/9.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium |
| baseline/a1.jpg | 정공구 | requires live raw lines; not present in persisted T18 artifact | N/A | high: top-line/businessNo/address proximity can rank name candidates |
| baseline_fast/9.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium |
| google/5.jpg | GS25역상효성점 | requires live raw lines; not present in persisted T18 artifact | N/A | high: top-line/businessNo/address proximity can rank name candidates |
| google/8.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium |
| google/9.jpg | 미화약국 | requires live raw lines; not present in persisted T18 artifact | N/A | high: top-line/businessNo/address proximity can rank name candidates |
| google_fast/5.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | high: top-line/businessNo/address proximity can rank name candidates |

## 7. businessNo 후보 분석
| sample | current | bbox 후보 | confidence | 판정 |
|---|---|---|---|---|
| baseline/8.jpg | 134-04-13602 | requires live raw lines; not present in persisted T18 artifact | N/A | medium |
| baseline/9.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium |
| baseline/a1.jpg | 123-23-94265 | requires live raw lines; not present in persisted T18 artifact | N/A | high: label proximity can separate businessNo from phone/card numbers |
| baseline_fast/9.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium |
| google/1.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium |
| google/5.jpg | 220-09-99115 | requires live raw lines; not present in persisted T18 artifact | N/A | high: label proximity can separate businessNo from phone/card numbers |
| google/6.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium |
| google/8.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium |

## 8. totalAmount 후보 분석
| sample | current | bbox 후보 | confidence | 판정 |
|---|---|---|---|---|
| baseline/8.jpg | 11,000 | requires live raw lines; not present in persisted T18 artifact | N/A | medium: useful for label/right-side amount selection |
| baseline/9.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium: useful for label/right-side amount selection |
| baseline/a1.jpg | 110,000 | requires live raw lines; not present in persisted T18 artifact | N/A | medium: useful for label/right-side amount selection |
| baseline/a2.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium: useful for label/right-side amount selection |
| baseline_fast/9.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium: useful for label/right-side amount selection |
| baseline_fast/a2.jpg | (missing) | requires live raw lines; not present in persisted T18 artifact | N/A | medium: useful for label/right-side amount selection |
| google/5.jpg | 53,200 | requires live raw lines; not present in persisted T18 artifact | N/A | medium: useful for label/right-side amount selection |
| google/8.jpg | 5,500 | requires live raw lines; not present in persisted T18 artifact | N/A | medium: useful for label/right-side amount selection |

## 9. classification_mismatch 분석
| sample | before/actual | keyword 위치 | bbox 근거 | 후속 |
|---|---|---|---|---|
| baseline/8.jpg | medical_receipt / receipt_card | not persisted; requires live raw line y/x positions | runtime ocr_lines_raw supports pts/conf; T18 artifact has only summary fields | position-weighted classifier candidate |
| baseline/a1.jpg | card_receipt / receipt_pos | not persisted; requires live raw line y/x positions | runtime ocr_lines_raw supports pts/conf; T18 artifact has only summary fields | position-weighted classifier candidate |
| google/5.jpg | pos_receipt / receipt_card | not persisted; requires live raw line y/x positions | runtime ocr_lines_raw supports pts/conf; T18 artifact has only summary fields | position-weighted classifier candidate |
| google/8.jpg | unknown / receipt_pos | not persisted; requires live raw line y/x positions | runtime ocr_lines_raw supports pts/conf; T18 artifact has only summary fields | position-weighted classifier candidate |
| google/9.jpg | medical_receipt / receipt_pos | not persisted; requires live raw line y/x positions | runtime ocr_lines_raw supports pts/conf; T18 artifact has only summary fields | position-weighted classifier candidate |
| google_fast/5.jpg | pos_receipt / receipt_card | not persisted; requires live raw line y/x positions | runtime ocr_lines_raw supports pts/conf; T18 artifact has only summary fields | position-weighted classifier candidate |
| receipt_generalization/food_001.jpg | food_cafe_receipt / unknown | not persisted; requires live raw line y/x positions | runtime ocr_lines_raw supports pts/conf; T18 artifact has only summary fields | position-weighted classifier candidate |
| receipt_generalization/food_004.jpg | food_cafe_receipt / invoice_statement | not persisted; requires live raw line y/x positions | runtime ocr_lines_raw supports pts/conf; T18 artifact has only summary fields | position-weighted classifier candidate |
| receipt_generalization/pos_006.jpg | pos_receipt / unknown | not persisted; requires live raw line y/x positions | runtime ocr_lines_raw supports pts/conf; T18 artifact has only summary fields | position-weighted classifier candidate |

## 10. invoice_statement bbox 활용 가능성
- rowCount exact rate: 100.0%
- expected value fill average: 52.4%
- 판단: Maintain invoice_statement behavior for now; rowCount is 7/7 exact and bbox-based changes are lower priority.
- 2.pdf OP-anchor, 5.pdf multiline, 6.pdf header skip, 7.pdf quantity 병합은 현재 회귀 없이 유지된다.
- extractor 내부에는 `sourceBboxes` 경로가 있으나 현재 보고서 preview에는 full bbox가 보존되지 않는다.

## 11. 후속 후보 우선순위
| 후보 | 기대 효과 | 위험도 | 추천 |
|---|---|---|---|
| T-19c classification position weighting | high | medium | #1 - classification_mismatch=9, highest remaining failure reason |
| T-19a bbox-based merchantName candidate scoring | medium-high | low-medium | #2 - parser_missed_source_exists=4; merchantName missing remains in receipt groups |
| T-19b bbox-based businessNo/totalAmount selection | medium | low-medium | #3 - ambiguous_candidates=1; pos businessNo and amount misses remain |
| T-20 OCR preprocessing experiment | limited for current top failures | medium | #4 - ocr_source_garbled+ocr_source_missing=5, lower than bbox/classification-related reasons |
| invoice_statement bbox generalization | low now | medium | #5 - invoice rowCount remains 7/7 exact |

## 12. 다음 작업 판단
- 추천: T-19c classification position weighting, with known metadata/suppression cases guarded before changing behavior
- T-20 전처리 실험은 source missing/garbled 5건 중심이라 현재 최다 실패 원인 대비 후순위다.
- invoice_statement는 7/7 exact 상태이므로 기능 변경보다 raw snapshot 보강만 후순위로 둔다.

## 13. 검증 결과
- py_compile: PASS: python -m py_compile scripts/analyze_ocr_raw_bbox_confidence_t19.py
- verify script: PASS: python scripts/analyze_ocr_raw_bbox_confidence_t19.py
- typecheck: PASS: npm.cmd run typecheck
- build: PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)
