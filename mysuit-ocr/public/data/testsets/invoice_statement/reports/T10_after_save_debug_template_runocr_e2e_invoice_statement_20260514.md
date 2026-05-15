# T-10 after save-debug Template/RunOCR E2E 재검증 결과

## 1. 생성 파일
- Script: `D:\Free_Vue\OCR\ocr-server\scripts\verify_invoice_statement_template_runocr_e2e_t10_after_save_debug.py`
- Markdown report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_after_save_debug_template_runocr_e2e_invoice_statement_20260514.md`
- JSON report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_after_save_debug_template_runocr_e2e_invoice_statement_20260514.json`

## 2. 핵심 요약
- templates.json 재확인: `D:\Free_Vue\OCR\ocr-server\data\templates.json`
- API 기준: `http://127.0.0.1:9099`
- API 직접 호출 여부: `True`
- 요약: {'samplesTotal': 7, 'apiExecuted': 3, 'rowCountExactAmongExecuted': '1/3', 'missingSavedAnnotations': 4, 'issues': 6}
- 한계: 브라우저 UI 클릭 및 History/result persistence 저장 플로우는 미수행. 저장 annotation 없는 샘플은 실제 Template E2E 미실행.

## 3. 새로 저장된 Template annotation 확인
| 샘플 | template 존재 | template_id | documentType | table region | colGuides | 실행 여부 |
|---|---|---|---|---|---|---|
| 1.jpg | yes | TPL-31D13CF3 | invoice_statement | {"x": 47, "y": 831, "width": 2361, "height": 2317} | 6 | true |
| 2.pdf | yes | TPL-A4585BC7 | invoice_statement | {"x": 111, "y": 136, "width": 1486, "height": 2112} | 9 | true |
| 3.pdf | no | - | - | 없음 | - | false |
| 4.pdf | no | - | - | 없음 | - | false |
| 5.pdf | yes | TPL-A6B12CED | invoice_statement | {"x": 68, "y": 39, "width": 1504, "height": 843} | 9 | true |
| 6.pdf | no | - | - | 없음 | - | false |
| 7.pdf | no | - | - | 없음 | - | false |

## 4. RunOCR E2E rowCount 결과
| 샘플 | GT | Test 기준 | RunOCR E2E | 상태 |
|---|---:|---:|---:|---|
| 1.jpg | 28 | 28 | 28 | exact |
| 2.pdf | 13 | 13 | 17 | mismatch |
| 3.pdf | 1 | 1 | - | skipped_no_saved_template_annotation |
| 4.pdf | 1 | 1 | - | skipped_no_saved_template_annotation |
| 5.pdf | 6 | 6 | 9 | mismatch |
| 6.pdf | 6 | 6 | - | skipped_no_saved_template_annotation |
| 7.pdf | 1 | 1 | - | skipped_no_saved_template_annotation |

## 5. tableMeta/debug 결과
| 샘플 | doc_type | extractionSource | tableBoundsUsed | columnGuidesUsed | warnings |
|---|---|---|---|---|---|
| 1.jpg | invoice_statement | header_column_mapping | true | false | - |
| 2.pdf | invoice_statement | header_column_mapping | true | false | - |
| 3.pdf | - | - | - | - | - |
| 4.pdf | - | - | - | - | - |
| 5.pdf | invoice_statement | header_column_mapping | true | false | - |
| 6.pdf | - | - | - | - | - |
| 7.pdf | - | - | - | - | - |

## 6. 샘플별 상세
### 5.pdf
- template: TPL-A6B12CED
- rowCount: GT 6 / RunOCR 9 / 상태 mismatch
- tableMeta: extractionSource=header_column_mapping, tableBoundsUsed=true, tableBoundsSource=-, columnGuidesReceived=false, columnGuidesUsed=false, columnGuidesCount=0
- 판정: 저장 annotation 있음

### 2.pdf
- template: TPL-A4585BC7
- rowCount: GT 13 / RunOCR 17 / 상태 mismatch
- tableMeta: extractionSource=header_column_mapping, tableBoundsUsed=true, tableBoundsSource=-, columnGuidesReceived=false, columnGuidesUsed=false, columnGuidesCount=0
- 판정: 저장 annotation 있음

### 7.pdf
- template: 저장 annotation 없음
- rowCount: GT 1 / RunOCR - / 상태 skipped_no_saved_template_annotation
- tableMeta: extractionSource=-, tableBoundsUsed=-, tableBoundsSource=-, columnGuidesReceived=-, columnGuidesUsed=-, columnGuidesCount=-
- 판정: 실제 저장 Template/RunOCR E2E 호출 불가. UI 저장 후 재검증 필요.

### 6.pdf
- template: 저장 annotation 없음
- rowCount: GT 6 / RunOCR - / 상태 skipped_no_saved_template_annotation
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

### 1.jpg
- template: TPL-31D13CF3
- rowCount: GT 28 / RunOCR 28 / 상태 exact
- tableMeta: extractionSource=header_column_mapping, tableBoundsUsed=true, tableBoundsSource=-, columnGuidesReceived=false, columnGuidesUsed=false, columnGuidesCount=0
- 판정: 저장 annotation 있음

## 7. 발견 문제
| 문제 | 원인 | 후속 |
|---|---|---|
| 5.pdf: rowCount mismatch | RunOCR E2E=9, expected=6 | 새 추출 로직 수정 없이 template bounds/colGuides 저장 좌표 후속 검증 |
| 2.pdf: rowCount mismatch | RunOCR E2E=17, expected=13 | 새 추출 로직 수정 없이 template bounds/colGuides 저장 좌표 후속 검증 |
| 7.pdf: saved annotation missing | templates.json에 해당 샘플 파일명과 연결된 table region template 없음 | UI에서 table region/column guide 저장 후 T-10 재실행 |
| 6.pdf: saved annotation missing | templates.json에 해당 샘플 파일명과 연결된 table region template 없음 | UI에서 table region/column guide 저장 후 T-10 재실행 |
| 3.pdf: saved annotation missing | templates.json에 해당 샘플 파일명과 연결된 table region template 없음 | UI에서 table region/column guide 저장 후 T-10 재실행 |
| 4.pdf: saved annotation missing | templates.json에 해당 샘플 파일명과 연결된 table region template 없음 | UI에서 table region/column guide 저장 후 T-10 재실행 |

## 8. 검증 결과
- script py_compile: not_run_in_script
- E2E script: completed
- typecheck: not_run_in_script
- build: not_run_in_script

## 9. 다음 작업 판단
- documentType 누락 재발 → T-10-save-debug-fix

## 10. 결과 저장/History
- API 응답 기준 tableRows/tableMeta 확인 완료
- 브라우저 UI 저장 플로우는 미수행
- History/result persistence는 후속 E2E 필요
