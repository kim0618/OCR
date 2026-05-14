# T-6j-fix RunOCR regions doc_type 및 colGuides debug 보정 결과

## 1. 수정 파일
- `d:/Free_Vue/OCR/ocr-server/main.py`
- `d:/Free_Vue/OCR/ocr-server/extractors/invoice_statement.py`

## 2. 백업 파일
- `d:/Free_Vue/OCR/ocr-server/backup/main_20260512_before_T6j_fix_runocr_doc_type.py`
- `d:/Free_Vue/OCR/ocr-server/backup/invoice_statement_20260512_before_T6j_fix_debug_colguides.py`

## 3. 핵심 요약
- **HTTP 500 UnboundLocalError 해결**: `doc_type`, `ocr_lines_raw`, `ocr_w/h`, `extract_debug` 미초기화 문제 수정
- **regions 경로에서 invoice_statement extractor 정상 도달**: doc_type 분류 + 전체 이미지 OCR 실행
- **colGuides debug 전파 수정**: `columnGuidesReceived/Used/Count`, `tableBoundsSource` 이제 tableMeta에 노출
- **회귀 없음**: 기존 7/7 샘플 결과 유지

## 4. doc_type 오류 원인

### 발생 경로
`POST /ocr/extract` → regions JSON 제공 → `if region_list:` 분기 진입 → 분기 종료 → 2047행 `if doc_type == "invoice_statement":` → **UnboundLocalError**

### 기존 문제
`doc_type`은 `else:` (전체 이미지 OCR) 분기에서만 `doc_info["type"]`으로 세팅됨. `if region_list:` 분기에는 세팅 코드 없음. 마찬가지로 `ocr_lines_raw`, `ocr_w`, `ocr_h`, `extract_debug` 모두 미정의.

### 수정 내용 (main.py)

**1. 함수 진입부에 기본값 초기화 추가** (`if region_list:` 이전):
```python
doc_type: str = "unknown"
extract_debug: dict = {}
ocr_lines_raw: list = []
ocr_w: int = orig_w
ocr_h: int = orig_h
```

**2. `if region_list:` 블록 끝에 doc_type 분류 + invoice_statement OCR 추가**:
```python
# classify doc_type from template region text
if full_lines:
    _tmpl_doc_info = classify_document("\n".join(full_lines))
    doc_type = _tmpl_doc_info.get("type", "unknown")
    extract_debug = {"document_classification": _tmpl_doc_info, "doc_type": doc_type}

# For invoice_statement: run full-image OCR to get ocr_lines_raw
if doc_type == "invoice_statement":
    try:
        _tmpl_inv_result = ocr.ocr(img)
        ocr_lines_raw = _parse_ocr_lines(_tmpl_inv_result)
    except Exception as _tmpl_inv_e:
        ocr_lines_raw = []
```

**3. template 경로에서 extract_debug를 응답에 포함**:
```python
if region_list and extract_debug:
    extract_debug["template_path"] = True
    response["extract_debug"] = extract_debug
    response["doc_type"] = doc_type
```

## 5. regions → tableBounds/columnGuides 연결 확인
| 항목 | 결과 | 비고 |
|---|---|---|
| regions JSON 파싱 | ✓ | region_list에서 파싱 |
| table region 탐색 | ✓ | fieldType === "table" |
| tableBounds 유도 | ✓ | T-6i에서 구현됨, source="template_region" |
| columnGuides 유도 | ✓ | T-6j에서 구현됨, region.table.colX → OCR space |
| extractor 전달 | ✓ | table_bounds, column_guides 모두 전달됨 |

## 6. tableMeta/tableDebug 노출

### invoice_statement.py 수정: table_debug에 colGuides 정보 추가
`_detect_table`의 `table_debug` 딕셔너리에 `header_debug`로부터 propagate:
```python
"columnGuidesReceived": header_debug.get("columnGuidesReceived", False),
"columnGuidesCount": header_debug.get("columnGuidesCount", 0),
"columnGuidesOcrSpace": header_debug.get("columnGuideOcrSpace", []),
"columnGuideMode": header_debug.get("columnGuideMode", ""),
"columnGuideMismatch": header_debug.get("columnGuideMismatch"),
"tableBoundsSource": header_debug.get("tableBoundsSource", ""),
```

`extract_invoice_statement_fields`에서 tableMeta로 전파:
```python
canonical["tableMeta"]["columnGuidesReceived"] = tdbg.get("columnGuidesReceived", False)
canonical["tableMeta"]["columnGuidesUsed"] = bool(...)
canonical["tableMeta"]["columnGuidesCount"] = tdbg.get("columnGuidesCount", 0)
canonical["tableMeta"]["tableBoundsSource"] = tdbg.get("tableBoundsSource", "")
```

| 필드 | 노출 여부 | 값 예시 |
|---|---|---|
| tableBoundsUsed | ✓ | True |
| columnGuidesReceived | ✓ | True |
| columnGuidesUsed | ✓ | True |
| columnGuidesCount | ✓ | 4 (5.pdf), 7 (2.pdf) |
| extractionSource | ✓ | template_colguides_expected_columns |
| tableBoundsSource | ✓ | template_region |

## 7. 검증 결과

### 5.pdf regions payload (HTTP 상태 + debug)
- HTTP status: **200** (기존 500 → 수정됨)
- doc_type: invoice_statement ✓
- extractionSource: template_colguides_expected_columns ✓
- tableBoundsUsed: True ✓
- columnGuidesReceived: True ✓
- columnGuidesUsed: True ✓
- columnGuidesCount: 4 ✓
- tableBoundsSource: template_region ✓
- rowCount: 11 (테스트 좌표가 원본 이미지 해상도와 불일치 → 실제 template annotation 필요)

### 2.pdf regions payload
- HTTP status: **200** (기존 500 → 수정됨)
- doc_type: invoice_statement ✓
- extractionSource: template_colguides_expected_columns ✓
- tableBoundsUsed: True ✓
- columnGuidesReceived: True ✓
- columnGuidesUsed: True ✓
- columnGuidesCount: 7 ✓
- rowCount: 14 (같은 이유 — 테스트 좌표 불일치)

### direct-control (tableBounds + columnGuides Form param)
- 5.pdf: HTTP 200, extractionSource=template_colguides_expected_columns, rowCount=4 ✓
- 2.pdf: HTTP 200, extractionSource=template_colguides_expected_columns, rowCount=1 ✓

### 기존 표준 경로 (tableBounds 미제공)
- verify script 7/7 성공, 기존 결과 모두 유지 ✓

## 8. py_compile 결과
- main.py: 통과 ✓
- invoice_statement.py: 통과 ✓

## 9. 남은 문제

### rowCount/value 좌표 불일치
테스트에서 colX=[190, 350, 490, 650]는 950px OCR 공간 기준으로 설계됐지만, regions 경로에서 full OCR은 원본 이미지 (PDF → 200DPI → 2480px+) 해상도로 실행됨. 따라서 colX 좌표가 실제 컬럼 위치와 불일치하여 rowCount가 과다/오분류.

**실제 Template 저장 annotation이 있으면**: 사용자가 실제 이미지에서 그린 colX 좌표가 원본 이미지 픽셀 공간에 저장되므로, regions 경로에서 정확한 컬럼 경계가 만들어짐.

### 전처리 미적용 이슈
regions 경로에서 invoice_statement 추출을 위한 OCR은 원본 `img`에 직접 실행 (perspective correction, deskew, resize 없음). 문서가 기울어지거나 왜곡된 경우 OCR 품질이 저하될 수 있음.

## 10. 다음 작업 판단
- **regions 경로 정상화 완료** → 실제 UI 저장 Template 기반 좌표 검증 가능
- **colGuides debug 노출 완료** → extractionSource, columnGuidesReceived/Used/Count, tableBoundsSource 모두 확인 가능
- **T-6 시리즈 안정화** → T-7 금액 계열 검토 가능
- 실제 Template annotation으로 5.pdf/2.pdf 정확도 검증은 후속 작업
