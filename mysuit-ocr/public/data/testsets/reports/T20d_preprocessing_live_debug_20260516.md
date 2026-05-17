# T-20d preprocessing live debug 연결 결과

## 1. 수정 파일
- `ocr-server/main.py` — debugPreprocessing Form 파라미터 + `_build_preprocessing_debug` 헬퍼 추가
- `ocr-server/preprocessing_policy.py` — manifest lookup + live variant 헬퍼 추가
- `ocr-server/scripts/verify_preprocessing_live_debug_t20d.py` (신규)

## 2. 백업 파일
- `ocr-server/backup/main_20260516_before_T20d_debug_preprocessing.py`
- `ocr-server/backup/preprocessing_policy_20260516_before_T20d_live_debug.py`

## 3. 핵심 요약
- 검증 overall: PASS
- main.py: debugPreprocessing=false (기본값), true 시 preprocessingDebug 응답 추가
- debug=false: 기존 응답 완전 동일, preprocessingDebug 없음
- debug=true: 후보 샘플에서 wouldApplyInDebug=True, productionApplied=False
- invoice_statement 7/7 exact 기존 경로 유지
- 운영 OCR 결과 변경 없음

## 4. API flag
| flag | default | effect |
|---|---|---|
| debugPreprocessing | false | false: 기존 응답 유지 / true: preprocessingDebug 블록 추가 |
| qualityTagsJson | (없음) | qualityTags 직접 전달 (선택). 없으면 manifest 자동 조회 |
| productionApplied | - | 항상 false (운영 결과 변경 불가) |

## 5. debug=false 회귀 확인
| 항목 | 결과 |
|---|---|
| debugPreprocessing 기본값 false | OK |
| 조건부 gate (_debug_preprocessing) | OK |
| preprocessingDebug 없음 (debug=false) | OK (conditional gate 확인) |
| 기존 응답 구조 변경 없음 | OK (기존 코드 무수정) |

## 6. debug=true 결과
| sample | candidates | selectedCandidate | wouldApplyInDebug | productionApplied |
|---|---|---|---|---|
| card_002.jpg | clahe, upscale_1_5x, clahe_plus_sharpen | clahe | True | False |
| medical_001.jpg | clahe, clahe_plus_sharpen | clahe | True | False |
| pos_006.jpg | upscale_1_5x, clahe_plus_sharpen | upscale_1_5x | True | False |
| medical_003.jpg | grayscale, clahe, clahe_plus_sharpen | grayscale | True | False |
| invoice/3.pdf | render_dpi_200_grayscale | render_dpi_200_grayscale | True | False |
| invoice/2.pdf | (없음) | - | False | False |
| card_001.jpg | upscale_1_5x, clahe_plus_sharpen | upscale_1_5x | True | False |

## 7. invoice guard 결과
| sample | expectedRowCount | original rowCount | candidate | decision |
|---|---:|---:|---|---|
| invoice/3.pdf | see manifest | see T-20 | render_dpi_200_grayscale | candidate_accept |
| invoice/2.pdf | see manifest | see T-20 | blocked | blocked/no_candidate |
| 1.jpg (baseline) | 28 | 28 | - | exact |
| 2.pdf (baseline) | 13 | 13 | - | exact |
| 3.pdf (baseline) | 1 | 1 | - | exact |
| 4.pdf (baseline) | 1 | 1 | - | exact |
| 5.pdf (baseline) | 6 | 6 | - | exact |
| 6.pdf (baseline) | 6 | 6 | - | exact |
| 7.pdf (baseline) | 1 | 1 | - | exact |

## 8. 운영 적용 판단
- **production default**: debugPreprocessing=false → 기존 응답 100% 동일
- **debug mode**: debugPreprocessing=true → preprocessingDebug 추가 (productionApplied=false)
- **선택 적용 후보**: card_002(clahe), medical_001(clahe), pos_006(upscale_1_5x), medical_003(grayscale), invoice/3.pdf(render_dpi_200_grayscale)
- **next step**: T-20d debug 연결 완료. 운영 auto-apply는 추가 실사용 검증 후 결정.

## 9. 검증 결과
- py_compile main.py: PASS
- py_compile preprocessing_policy.py: PASS
- py_compile verify script: PASS
- verify script: PASS
  - main.py flag: PASS
  - policy functions: PASS
  - debug=false gate: PASS
  - debug=true compare: PASS
  - invoice baseline: PASS
- typecheck: PASS (npm run typecheck)
- build: 미실행 (Python 파일만 수정, JS 코드 무수정)
