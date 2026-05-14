# T-6i Template table bounds 기반 expectedColumns 추출 경로 연결 결과

## 1. 수정 파일
- `d:/Free_Vue/OCR/ocr-server/main.py`
- `d:/Free_Vue/OCR/ocr-server/extractors/invoice_statement.py`

## 2. 백업 파일
- `d:/Free_Vue/OCR/ocr-server/backup/main_20260512_before_T6i_template_bounds.py`
- `d:/Free_Vue/OCR/ocr-server/backup/invoice_statement_20260512_before_T6i_template_bounds.py`

## 3. 핵심 요약
- **tableBounds 경로 완전 연결**: backend↔extractor 경로 이미 존재 + Template region 자동 유도 추가
- **table_bounds 제공 시 header threshold 완화**: score=1도 허용 (전체 완화는 5.pdf 회귀 확인됨)
- **5.pdf/2.pdf 한계 확인**: OCR garble로 expected_columns header 인식 자체 불가 — tableBounds만으로 해결 불가
- **회귀 없음**: 모든 기존 샘플 결과 유지

## 4. 현재 Template table 구조 조사

### table bounds 저장 구조
- `Region.x, y, width, height` — image pixel 좌표
- `Region.fieldType === "table"` 로 표/필드 구분
- `Region.table.colGuides: number[]` — 정규화(0-1) 컬럼 가이드 위치

### TableMeta 구조
```typescript
type TableMeta = {
  mode?: "repeat" | "auto";
  rowTemplate?: Rect;     // 단일 행 템플릿
  rows?: Rect[];          // 명시적 행 배열
  colGuides?: number[];   // 컬럼 가이드 (0-1 정규화)
  stopKeywords?: string[];
  tableName?: string;
  columns?: TableColumnDef[];
}
```

### Frontend → Backend 전달
- `UploadWorkspace.tsx`가 `regions` JSON만 전송 (tableBounds 별도 전송 없음)
- `regions`에 table region (`fieldType: "table"`) 포함 시 자동 tableBounds 유도 가능

## 5. backend tableBounds 수신/전달 구조

### 수신/전달 (T-6f부터 이미 구현)
```
Frontend (regions JSON)
  → main.py: tableBounds Form param 수신
  → json.loads(tableBounds) → _tbn dict
  → extract_invoice_statement_fields(table_bounds=_tbn)
  → _table_items_with_expected_columns(table_bounds=...)
  → _find_expected_header_band(table_bounds=...)
```

### T-6i 추가: Template region → tableBounds 자동 유도 (main.py)
```python
if not _tbn and region_list:
    for _r in region_list:
        if _r.get("fieldType") == "table":
            _sx = float(ocr_w) / max(float(orig_w), 1)
            _sy = float(ocr_h) / max(float(orig_h), 1)
            _tbn = {
                "xMin": max(0.0, _rx * _sx),
                "yMin": max(0.0, _ry * _sy),
                "xMax": min(float(ocr_w), (_rx + _rw) * _sx),
                "yMax": min(float(ocr_h), (_ry + _rh) * _sy),
                "source": "template_region",
            }
```
좌표 변환: img space → ocr_img space (단순 scale 근사, perspective/orientation 보정 미포함)

## 6. invoice_statement.py table_bounds 적용 결과

### 변경된 동작 (table_bounds 있을 때만)
| 항목 | 기존 | T-6i 추가 |
|---|---|---|
| header score threshold | 항상 >= 2 | table_bounds 있으면 >= 1 |
| boundary 최소 매칭 | 항상 >= 2 | allow_single_match=True 가능 |
| row 추출 y_max | page_h * 0.96 | table_bounds.get("yMax") 우선 |
| debug.tableBoundsUsed | 부분 | 명시적으로 추가 |
| debug.tableBoundsSource | 없음 | "explicit", "template_region", "none" |

### 기존 동작 (table_bounds 없을 때)
모든 기존 로직 그대로 유지. 회귀 없음.

## 7. 검증 결과
- main.py py_compile: 통과 ✓
- invoice_statement.py py_compile: 통과 ✓
- typecheck: 통과 ✓
- build: 통과 ✓
- verify script (tableBounds 없는 기존 경로): 7/7 성공, 기존 결과 동일 ✓

### tableBounds 주입 테스트
| 샘플 | tableBoundsUsed | extractionSource | headerBandFound | 결과 |
|---|---|---|---|---|
| 5.pdf (broad bounds) | True | legacy_text_items | None | OCR garble 한계 — 헤더 인식 불가 |
| 2.pdf (broad bounds) | True | legacy_text_items | None | OCR garble 한계 — 헤더 인식 불가 |

**tableBoundsUsed=True** 확인됨 — 경로 자체는 정상 동작.

## 8. 기존 RunAll 회귀 확인
| 샘플 | 기존 주요 결과 | T-6i 후 결과 | 회귀 여부 |
|---|---|---|---|
| 1.jpg | rowCount=29, value mapping OK | 동일 | 없음 ✓ |
| 5.pdf | rowCount=6 | rowCount=6 | 없음 ✓ |
| 6.pdf | rowCount=5 | rowCount=5 | 없음 ✓ |
| 7.pdf | rowCount=1, serialNo/unit 채워짐 | 동일 | 없음 ✓ |

## 9. 5.pdf/2.pdf 한계 분석
### 5.pdf
- OCR이 "품명", "품목코드", "수량", "단가", "금액" 헤더를 인식 불가
- auto-detection: "3,000", "C" 등 데이터 행을 헤더로 오인식
- tableBounds 있어도 `_find_expected_header_band`에서 score=0 (no candidates)
- **근본 해결**: column guides 또는 manual column positions 제공 필요 (T-6j)

### 2.pdf
- OCR garble + footer/summary 혼재로 header detection 실패
- tableBounds 있어도 헤더 텍스트 자체가 인식 불가
- **근본 해결**: T-6j column guides 또는 T-6h-fix-2pdf 별도 처리

## 10. 남은 문제
1. **5.pdf**: tableBounds만으로는 header detection 불가 → column guides (colX) 기반 경계 직접 지정 필요
2. **2.pdf**: 동일 구조적 한계
3. **Frontend 연결**: UploadWorkspace.tsx가 tableBounds를 아직 별도로 보내지 않음 (regions로만 전달)
4. **column guides 통합**: template colGuides → extractor column boundaries 연결 미구현

## 11. 다음 작업 판단

**T-6j: column guides 기반 경계 직접 지정 (5.pdf/2.pdf 해결 경로)**
- Template colGuides (정규화 컬럼 가이드) → tableBounds에 colGuides 포함 전달
- extractor에서 colGuides 있으면 header detection 없이 직접 boundary 구성
- 이렇게 하면 OCR garbled header 있어도 column 구분 가능

**OR**: 5.pdf/2.pdf 문제를 받아들이고 T-7 금액 계열로 진행
- 1.jpg value mapping 완료, 7.pdf composite 완료, 6.pdf 5/6
- 남은 5.pdf/2.pdf는 OCR quality 한계로 분리 처리
