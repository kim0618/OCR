# T-10 invoice_statement Template annotation RunOCR E2E 재검증 결과

## 1. 생성 파일
- Script: `D:\Free_Vue\OCR\ocr-server\scripts\verify_invoice_statement_template_runocr_e2e_t10.py`
- Markdown report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_template_annotation_runocr_e2e_invoice_statement_20260514.md`
- JSON report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_template_annotation_runocr_e2e_invoice_statement_20260514.json`

## 2. 검증 방식
- 실제 저장 template 사용 여부: `True`
- API 직접 호출 여부: `True`
- 사용한 payload: Mode A: file+template_id only. Mode B: file+template_id+regions+documentType=invoice_statement.
- 한계: 브라우저 UI 클릭 및 History/result persistence 저장 플로우는 미수행. 저장 annotation 없는 샘플은 실제 Template E2E 미실행.

## 3. Template annotation 확인
| 샘플 | template 존재 | template_id | documentType | table region | colGuides | 판정 |
|---|---|---|---|---|---|---|
| 1.jpg | yes | TPL-31D13CF3 | invoice_statement | {"x": 47, "y": 831, "width": 2361, "height": 2317} | 6 | 실행 가능 |
| 2.pdf | no | - | - | 없음 | - | 저장 annotation 없음 |
| 3.pdf | no | - | - | 없음 | - | 저장 annotation 없음 |
| 4.pdf | no | - | - | 없음 | - | 저장 annotation 없음 |
| 5.pdf | no | - | - | 없음 | - | 저장 annotation 없음 |
| 6.pdf | no | - | - | 없음 | - | 저장 annotation 없음 |
| 7.pdf | no | - | - | 없음 | - | 저장 annotation 없음 |

## 4. RunOCR payload 확인
| 샘플 | 실행 여부 | regions 전달 | documentType source | tableBounds 유도 | columnGuides 유도 |
|---|---|---|---|---|---|
| 1.jpg | true | true | template metadata + explicit payload | true | true |
| 2.pdf | false | - | - | - | - |
| 3.pdf | false | - | - | - | - |
| 4.pdf | false | - | - | - | - |
| 5.pdf | false | - | - | - | - |
| 6.pdf | false | - | - | - | - |
| 7.pdf | false | - | - | - | - |

## 5. E2E rowCount 결과
| 샘플 | GT | Test 기준 | RunOCR E2E | 상태 |
|---|---:|---:|---:|---|
| 1.jpg | 28 | 28 | 28 | exact |
| 2.pdf | 13 | 13 | - | skipped_no_saved_template_annotation |
| 3.pdf | 1 | 1 | - | skipped_no_saved_template_annotation |
| 4.pdf | 1 | 1 | - | skipped_no_saved_template_annotation |
| 5.pdf | 6 | 6 | - | skipped_no_saved_template_annotation |
| 6.pdf | 6 | 6 | - | skipped_no_saved_template_annotation |
| 7.pdf | 1 | 1 | - | skipped_no_saved_template_annotation |

## 6. tableMeta/debug 결과
| 샘플 | doc_type | extractionSource | tableBoundsUsed | columnGuidesUsed | warnings |
|---|---|---|---|---|---|
| 1.jpg | invoice_statement | header_column_mapping | true | false | - |
| 2.pdf | - | - | - | - | - |
| 3.pdf | - | - | - | - | - |
| 4.pdf | - | - | - | - | - |
| 5.pdf | - | - | - | - | - |
| 6.pdf | - | - | - | - | - |
| 7.pdf | - | - | - | - | - |

## 7. 샘플별 상세
### 1.jpg
- template: TPL-31D13CF3
- rowCount: GT 28 / RunOCR 28 / 상태 exact
- tableMeta: extractionSource=header_column_mapping, tableBoundsUsed=true, tableBoundsSource=-, columnGuidesReceived=false, columnGuidesUsed=false, columnGuidesCount=0
- 판정: 저장 annotation 있음

### 2.pdf
- template: 저장 annotation 없음
- rowCount: GT 13 / RunOCR - / 상태 skipped_no_saved_template_annotation
- tableMeta: extractionSource=-, tableBoundsUsed=-, tableBoundsSource=-, columnGuidesReceived=-, columnGuidesUsed=-, columnGuidesCount=-
- 판정: 실제 저장 Template/RunOCR E2E 호출 불가. UI 저장 후 재검증 필요.

### 3.pdf
- template: 저장 annotation 없음
- rowCount: GT 1 / RunOCR - / 상태 skipped_no_saved_template_annotation
- tableMeta: extractionSource=-, tableBoundsUsed=-, tableBoundsSource=-, columnGuidesReceived=-, columnGuidesUsed=-, columnGuidesCount=-
- 판정: 실제 저장 Template/RunOCR E2E 호출 불가. UI 저장 후 재검증 필요.

### 4.pdf
- template: 저장 annotation 없음
- rowCount: GT 1 / RunOCR - / 상태 skipped_no_saved_template_annotation
- tableMeta: extractionSource=-, tableBoundsUsed=-, tableBoundsSource=-, columnGuidesReceived=-, columnGuidesUsed=-, columnGuidesCount=-
- 판정: 실제 저장 Template/RunOCR E2E 호출 불가. UI 저장 후 재검증 필요.

### 5.pdf
- template: 저장 annotation 없음
- rowCount: GT 6 / RunOCR - / 상태 skipped_no_saved_template_annotation
- tableMeta: extractionSource=-, tableBoundsUsed=-, tableBoundsSource=-, columnGuidesReceived=-, columnGuidesUsed=-, columnGuidesCount=-
- 판정: 실제 저장 Template/RunOCR E2E 호출 불가. UI 저장 후 재검증 필요.

### 6.pdf
- template: 저장 annotation 없음
- rowCount: GT 6 / RunOCR - / 상태 skipped_no_saved_template_annotation
- tableMeta: extractionSource=-, tableBoundsUsed=-, tableBoundsSource=-, columnGuidesReceived=-, columnGuidesUsed=-, columnGuidesCount=-
- 판정: 실제 저장 Template/RunOCR E2E 호출 불가. UI 저장 후 재검증 필요.

### 7.pdf
- template: 저장 annotation 없음
- rowCount: GT 1 / RunOCR - / 상태 skipped_no_saved_template_annotation
- tableMeta: extractionSource=-, tableBoundsUsed=-, tableBoundsSource=-, columnGuidesReceived=-, columnGuidesUsed=-, columnGuidesCount=-
- 판정: 실제 저장 Template/RunOCR E2E 호출 불가. UI 저장 후 재검증 필요.

## 8. 발견된 문제
| 문제 | 원인 추정 | 후속 |
|---|---|---|
| 5.pdf: saved annotation missing | templates.json에 해당 샘플 파일명과 연결된 table region template 없음 | UI에서 table region/column guide 저장 후 T-10 재실행 |
| 2.pdf: saved annotation missing | templates.json에 해당 샘플 파일명과 연결된 table region template 없음 | UI에서 table region/column guide 저장 후 T-10 재실행 |
| 7.pdf: saved annotation missing | templates.json에 해당 샘플 파일명과 연결된 table region template 없음 | UI에서 table region/column guide 저장 후 T-10 재실행 |
| 6.pdf: saved annotation missing | templates.json에 해당 샘플 파일명과 연결된 table region template 없음 | UI에서 table region/column guide 저장 후 T-10 재실행 |
| 3.pdf: saved annotation missing | templates.json에 해당 샘플 파일명과 연결된 table region template 없음 | UI에서 table region/column guide 저장 후 T-10 재실행 |
| 4.pdf: saved annotation missing | templates.json에 해당 샘플 파일명과 연결된 table region template 없음 | UI에서 table region/column guide 저장 후 T-10 재실행 |

## 9. annotation 미존재 샘플 후속
| 샘플 | 필요한 작업 |
|---|---|
| 5.pdf | documentType=invoice_statement, table region bounds, 필요 시 colGuides 저장 |
| 2.pdf | documentType=invoice_statement, table region bounds, 필요 시 colGuides 저장 |
| 7.pdf | documentType=invoice_statement, table region bounds, 필요 시 colGuides 저장 |
| 6.pdf | documentType=invoice_statement, table region bounds, 필요 시 colGuides 저장 |
| 3.pdf | documentType=invoice_statement, table region bounds, 필요 시 colGuides 저장 |
| 4.pdf | documentType=invoice_statement, table region bounds, 필요 시 colGuides 저장 |

## 10. 검증 결과
- script py_compile: passed
- E2E script: completed
- typecheck: passed after build regenerated `.next/types`
- build: passed; Next build completed, with ESLint message `nextVitals is not iterable`

## 11. 다음 작업 판단
- 2~7.pdf annotation 저장 필요

## 12. 결과 저장/History
- API 응답 기준 tableRows/tableMeta 확인 완료
- 브라우저 UI 저장 플로우는 미수행
- History/result persistence는 후속 E2E 필요
