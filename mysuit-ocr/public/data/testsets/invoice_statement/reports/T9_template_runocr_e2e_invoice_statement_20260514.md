# T-9 Template/RunOCR E2E invoice_statement 검증 결과

## 1. 생성 파일
- JSON: `c:\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T9_template_runocr_e2e_invoice_statement_20260514.json`
- Markdown: `c:\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T9_template_runocr_e2e_invoice_statement_20260514.md`
- Script: `C:\OCR\ocr-server\scripts\verify_invoice_statement_template_runocr_e2e_t9.py`

## 2. 검증 방식
- 실제 UI 저장 template 사용 여부: `templates.json`에 저장된 annotation을 사용
- API 직접 호출 여부: 저장 table template이 있는 샘플만 `/ocr/extract` 직접 호출
- 사용한 payload: RunOCR와 동일하게 `file`, `template_id`, `regions`, `model_id` 전달
- 한계: 실제 브라우저 UI 클릭 및 History persistence 저장은 수행하지 않음

## 3. Template annotation 확인
| 샘플 | template 존재 | table region | colGuides | 비고 |
|---|---|---|---|---|
| 1.jpg | yes | yes | 6 | TPL-31D13CF3 |
| 2.pdf | no | no | - | 저장된 table region template annotation이 없어 실제 RunOCR E2E 호출을 생략함 |
| 3.pdf | no | no | - | 저장된 table region template annotation이 없어 실제 RunOCR E2E 호출을 생략함 |
| 4.pdf | no | no | - | 저장된 table region template annotation이 없어 실제 RunOCR E2E 호출을 생략함 |
| 5.pdf | no | no | - | 저장된 table region template annotation이 없어 실제 RunOCR E2E 호출을 생략함 |
| 6.pdf | no | no | - | 저장된 table region template annotation이 없어 실제 RunOCR E2E 호출을 생략함 |
| 7.pdf | no | no | - | 저장된 table region template annotation이 없어 실제 RunOCR E2E 호출을 생략함 |

## 4. RunOCR payload 확인
| 샘플 | regions 전달 | tableBounds 유도 | columnGuides 유도 | doc_type |
|---|---|---|---|---|
| 1.jpg | True | True | True | receipt_pos |
| 2.pdf | False | False | False | - |
| 3.pdf | False | False | False | - |
| 4.pdf | False | False | False | - |
| 5.pdf | False | False | False | - |
| 6.pdf | False | False | False | - |
| 7.pdf | False | False | False | - |

## 5. E2E rowCount 결과
| 샘플 | GT | RunOCR OCR | Test 기준 | 상태 |
|---|---:|---:|---:|---|
| 1.jpg | 28 | 0 | 28 | mismatch |
| 2.pdf | 13 | - | 13 | skipped_no_saved_table_template |
| 3.pdf | 1 | - | 1 | skipped_no_saved_table_template |
| 4.pdf | 1 | - | 1 | skipped_no_saved_table_template |
| 5.pdf | 6 | - | 6 | skipped_no_saved_table_template |
| 6.pdf | 6 | - | 6 | skipped_no_saved_table_template |
| 7.pdf | 1 | - | 1 | skipped_no_saved_table_template |

## 6. tableMeta/debug 결과
| 샘플 | extractionSource | tableBoundsUsed | columnGuidesUsed | warnings |
|---|---|---|---|---|
| 1.jpg | - | - | - | - |
| 2.pdf | - | - | - | - |
| 3.pdf | - | - | - | - |
| 4.pdf | - | - | - | - |
| 5.pdf | - | - | - | - |
| 6.pdf | - | - | - | - |
| 7.pdf | - | - | - | - |

## 7. 샘플별 상세
### 1.jpg
- template: TPL-31D13CF3
- rowCount: GT 28 / RunOCR 0 / 상태 mismatch
- tableMeta: extractionSource=-, templatePath=True
- 비고: RunOCR payload(template_id + regions) 직접 호출 완료

### 2.pdf
- template: missing
- rowCount: GT 13 / RunOCR - / 상태 skipped_no_saved_table_template
- tableMeta: extractionSource=-, templatePath=None
- 비고: 저장된 table region template annotation이 없어 실제 RunOCR E2E 호출을 생략함

### 5.pdf
- template: missing
- rowCount: GT 6 / RunOCR - / 상태 skipped_no_saved_table_template
- tableMeta: extractionSource=-, templatePath=None
- 비고: 저장된 table region template annotation이 없어 실제 RunOCR E2E 호출을 생략함

### 7.pdf
- template: missing
- rowCount: GT 1 / RunOCR - / 상태 skipped_no_saved_table_template
- tableMeta: extractionSource=-, templatePath=None
- 비고: 저장된 table region template annotation이 없어 실제 RunOCR E2E 호출을 생략함

## 8. 발견된 문제
| 문제 | 원인 추정 | 후속 |
|---|---|---|
| 1.jpg: rowCount mismatch | RunOCR=0, GT=28 | Template bounds/column guide 좌표와 extractor template path 확인 |
| 1.jpg: doc_type not invoice_statement | template region OCR classification returned receipt_pos | Template field regions에 문서 분류에 충분한 텍스트가 포함되는지 확인 |
| 2.pdf: saved table template missing | templates.json에 해당 샘플 파일명과 연결된 table region annotation이 없음 | UI에서 해당 샘플용 table region/column guide 저장 후 재검증 |
| 3.pdf: saved table template missing | templates.json에 해당 샘플 파일명과 연결된 table region annotation이 없음 | UI에서 해당 샘플용 table region/column guide 저장 후 재검증 |
| 4.pdf: saved table template missing | templates.json에 해당 샘플 파일명과 연결된 table region annotation이 없음 | UI에서 해당 샘플용 table region/column guide 저장 후 재검증 |
| 5.pdf: saved table template missing | templates.json에 해당 샘플 파일명과 연결된 table region annotation이 없음 | UI에서 해당 샘플용 table region/column guide 저장 후 재검증 |
| 6.pdf: saved table template missing | templates.json에 해당 샘플 파일명과 연결된 table region annotation이 없음 | UI에서 해당 샘플용 table region/column guide 저장 후 재검증 |
| 7.pdf: saved table template missing | templates.json에 해당 샘플 파일명과 연결된 table region annotation이 없음 | UI에서 해당 샘플용 table region/column guide 저장 후 재검증 |

## 9. 다음 작업 판단
- Template 저장/전달 문제 있음 -> template path 문서분류/table annotation 보정 후 재검증
