# T-10-fix template_colguides header row 자동 제외 결과

## 1. 수정 파일
- `ocr-server/extractors/invoice_statement.py`

## 2. 백업 파일
- `ocr-server/backup/invoice_statement_20260516_before_T10_fix_template_header_skip.py`

## 3. 핵심 요약
- 전체 E2E 7/7 exact 달성 → Template/RunOCR E2E 1차 마감
- exact: 7/7
- 생성: 2026-05-17T19:38:35

## 4. 기존 문제
- 6.pdf E2E rowCount: **7/6 (over)**
- extra row text: `NO 제품코드 5 24001 270305`
- 원인: tableBounds가 헤더를 포함하고 colGuides 경로가 헤더 행을 데이터 row로 오인

## 5. header row skip 로직
- 적용 경로: `template_colguides_expected_columns` (`skip_contact_filter=True`)
- 판정 기준: `_is_colguides_header_like_row()` — 확장 header keyword(NO, 제품코드 포함) 2개 이상 AND strong item signal 없음
- 위치 기반: tableBounds 상단 20% 이내 + keyword 1개 이상 → header
- strong item signal 예외: mixed-case 제품코드(ANDC300C 패턴), Korean 4자+ (품목명 내용)

## 6. 6.pdf 결과
| 항목 | 결과 |
|---|---|
| doc_type | invoice_statement |
| extractionSource | template_colguides_expected_columns |
| tableBoundsUsed | true |
| columnGuidesUsed | true |
| rowCount | 6/6 |
| headerRowsSkipped | 1 |
| headerRowsSkippedSamples | ["NO 제품코드 5 24001 270305"] |
| ANDC300C 유지 | true |
| quantity 0 유지 | true |

## 7. 전체 E2E rowCount 결과
| 샘플 | 기대 | 결과 | 상태 |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | exact |
| 2.pdf | 13 | 13 | exact |
| 3.pdf | 1 | 1 | exact |
| 4.pdf | 1 | 1 | exact |
| 5.pdf | 6 | 6 | exact |
| 6.pdf | 6 | 6 | exact |
| 7.pdf | 1 | 1 | exact |

## 8. 회귀 확인
| 항목 | 결과 |
|---|---|
| 2.pdf OP-anchor 유지 | rowCount=13 |
| 5.pdf multiline 유지 | rowCount=6 |
| 7.pdf quantity=1,000 유지 | true |
| Test 기준 rowCount 7/7 유지 | true |

## 9. 검증 결과
- py_compile: not_run_in_script
- E2E script: completed
- typecheck: not_run_in_script
- build: not_run_in_script

## 10. 다음 작업 판단
- 전체 E2E 7/7 exact 달성 → Template/RunOCR E2E 1차 마감
