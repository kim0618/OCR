# T-7b-check 거래명세서 tableRows 현재 품질 최종 점검

## 1. 사용한 데이터/검증 방식
- 데이터: `c:\OCR\mysuit-ocr\public\data\testsets\invoice_statement`의 7개 거래명세서 샘플
- API: `http://127.0.0.1:9100/ocr/extract`
- 기준: manifest `tableExpectedColumns`의 required+optional expected columns로 T-7a 동일 fill rate 산출, display columns는 별도 기록
- 수정 범위: 추출 로직 수정 없음, 검증 스크립트와 최종 리포트만 생성

## 2. rowCount 최종 확인
| 샘플 | GT | OCR | 상태 |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | OK |
| 2.pdf | 13 | 13 | OK |
| 3.pdf | 1 | 1 | OK |
| 4.pdf | 1 | 1 | OK |
| 5.pdf | 6 | 6 | OK |
| 6.pdf | 6 | 6 | OK |
| 7.pdf | 1 | 1 | OK |

## 3. expected fill rate
| 샘플 | fill rate | 주요 filled | 주요 missing | 판정 |
|---|---:|---|---|---|
| 1.jpg | 60.4% (220/364) | itemName, spec, manufacturingNo, expiryDate, quantity 외 3 | unit, supplyAmount, taxAmount, totalAmount, remark | pass/current quality fixed |
| 2.pdf | 44.8% (64/143) | rowIndex, itemCode, itemName, quantity, consumerUnitPrice 외 2 | insuranceCode, amount, totalAmount, remark | T-8b candidate: OCR source missing policy |
| 3.pdf | 16.7% (2/12) | rowIndex, itemName | insuranceCode, spec, quantity, unitPrice, amount 외 5 | pass with known OCR/layout limitation |
| 4.pdf | 80.0% (8/10) | itemName, lotNo, unit, quantity, unitPrice 외 3 | amount, remark | pass/current quality fixed |
| 5.pdf | 14.8% (8/54) | itemName, quantity | itemCode, unitPrice, amount, supplyAmount, taxAmount 외 2 | T-8a candidate: multi-line OCR layout |
| 6.pdf | 50.0% (30/60) | rowIndex, itemCode, itemName, quantity, lotNo 외 1 | serialNo, manufacturingNo, unit, remark | pass/current quality fixed |
| 7.pdf | 66.7% (4/6) | itemName, serialLotComposite, unit, quantity | manufacturingNo, remark | pass/current quality fixed |

## 4. valueMappingWarnings
| 샘플 | warning | 의미 | 후속 필요 |
|---|---|---|---|
| 1.jpg | - | 실제 valueMappingWarnings 없음 | 없음 |
| 2.pdf | insuranceCode: OCR source missing (all rows empty; source text has no reliable insurance code pattern) | 품질 판정용 warning | T-8b |
| 3.pdf | - | 실제 valueMappingWarnings 없음 | 없음 |
| 4.pdf | taxAmount: doc_level_pushdown inferred | 품질 판정용 warning | 현 상태 유지/표시 확인 |
| 4.pdf | totalAmount: doc_level_pushdown inferred | 품질 판정용 warning | 현 상태 유지/표시 확인 |
| 5.pdf | - | 실제 valueMappingWarnings 없음 | 없음 |
| 6.pdf | - | 실제 valueMappingWarnings 없음 | 없음 |
| 7.pdf | - | 실제 valueMappingWarnings 없음 | 없음 |

## 5. 금액 계열 점검
| 샘플 | unitPrice | supplyAmount | taxAmount | amount | totalAmount | 판정 |
|---|---|---|---|---|---|---|
| 1.jpg | 1,050, 4,490 외 6 | - | - | 420,000, 449,000 외 6 | - | 오배치 없음 |
| 2.pdf | - | 9,064, 3,300 | - | - | - | 오배치 없음 |
| 3.pdf | - | - | - | - | - | 오배치 없음 |
| 4.pdf | 28,338.00 | 25,760,000 | 2,576,000 | - | 28,338,000 | row[0] quantity=1,000 (quantity comma value; false-positive amount-like) |
| 5.pdf | - | - | - | - | - | 오배치 없음 |
| 6.pdf | - | - | - | - | - | 오배치 없음 |
| 7.pdf | - | - | - | - | - | row[0] quantity=1,000 (quantity comma value; false-positive amount-like) |

## 6. 샘플별 최종 판정
| 샘플 | 상태 | 남은 문제 | 후속 |
|---|---|---|---|
| 1.jpg | 통과 | optional column source missing 정상 | 현 품질 고정 |
| 2.pdf | 통과/정책 이슈 | insuranceCode OCR source missing 표시 없음 | T-8b |
| 3.pdf | 통과/한계 | OCR garbled 및 구조 추출 한계, garbage quantity 제거 유지 | 현 품질 고정 |
| 4.pdf | 통과 | taxAmount=2,576,000, totalAmount=28,338,000 doc-level pushdown 추론 | 현 품질 고정 |
| 5.pdf | 통과/구조 한계 | itemCode/unitPrice/amount 다단 OCR layout 연결 한계 | T-8a |
| 6.pdf | 통과 | optional missing 정상 | 현 품질 고정 |
| 7.pdf | 통과 | quantity=1,000 유지, quantity amount-like false positive | 현 품질 고정 |

## 7. T-8 후보 정리
### T-8a. 5.pdf 다단 OCR layout 처리
- 대상: 5.pdf의 itemCode, unitPrice, amount, supplyAmount, taxAmount, totalAmount
- 이유: OCR에는 코드/금액 데이터가 존재하나 항목명과 서로 다른 OCR row로 분리되어 legacy path에서 연결되지 않음
- 예상 수정 범위: 다단 row stitching 또는 column-wise association 보강, 5.pdf 전용 회귀 검증 추가

### T-8b. 2.pdf insuranceCode OCR source missing 표시 정책
- 대상: 2.pdf insuranceCode
- 이유: OP-anchor reconstruction은 유지되지만 보험코드 원천 OCR이 불명확해 전 row missing이며 사용자에게 source missing으로 명시할 정책 필요
- 예상 수정 범위: valueMappingWarnings/qualityWarnings 표기 정책, UI 표시 여부, 테스트 기대값 정리

## 8. 다음 작업 판단
- 현재 품질 기준 통과 -> T-8 범위 선택
- 우선순위 제안: 5.pdf 다단 layout을 먼저 처리(T-8a), 이후 2.pdf warning 표시 정책(T-8b)
