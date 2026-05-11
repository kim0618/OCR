# T-2 Test UI tableRows 컬럼 표시/검증 구조 정리 결과

작성일: 2026-05-11  
직전 작업: T-1 (T1_table_profile_column_policy_20260511.md)  
기준: T-1 확정 18개 canonical column + tableProfile별 컬럼 정책

---

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `src/lib/profiles.ts` | TableColumnKey 타입, TABLE_COLUMN_META 상수, getExpectedTableColumns 함수, TableRowsValidation 타입 추가 |
| `src/components/test/TestWorkspace.tsx` | import 추가, buildTableRowsValidation 함수, TABLE_ROWS_* 상수, tableStatusColor 함수, TableRowsValidationPanel 컴포넌트, batch table Table 컬럼, DocumentDetailPanel 내 TABLE ROWS PROFILE 섹션 추가 |

## 2. 백업 파일

| 원본 | 백업 |
|---|---|
| `src/lib/profiles.ts` | `/c/OCR/backup/profiles_20260511_2100_before_T2.ts` |
| `src/components/test/TestWorkspace.tsx` | `/c/OCR/backup/TestWorkspace_20260511_2100_before_T2.tsx` |

## 3. 구현 요약

T-1에서 정의한 tableProfile별 컬럼 정책을 Test UI에서 확인할 수 있도록 다음을 구현했다.

1. **profiles.ts 추가**: TableColumnKey(18개), TABLE_COLUMN_META, getExpectedTableColumns(), TableRowsValidation 타입
2. **batch 테이블 "Table" 컬럼**: tableProfile 배지 + 행/첫행 O/X 상태 표시 (Party 컬럼 다음)
3. **상세 패널 "TABLE ROWS PROFILE" 섹션**: 접이식. tableProfile/gridMode/extractionStatus 배지 + Required/Optional/Actual/Missing 컬럼 배지 목록

현재 extractionStatus = "parser_not_ready" (T-3 이후 실제 tableRows 컬럼 추출 구현 예정).

---

## 4. 추가 타입/상수

### profiles.ts에 추가된 항목

| 항목 | 종류 | 내용 |
|---|---|---|
| `TableColumnKey` | type | 18개 canonical column union |
| `GridModeRecommendation` | type | fixed / variable / either / single-row / manual-review |
| `TableColumnMeta` | type | key, labelKo, valueType |
| `TABLE_COLUMN_META` | const | 18개 컬럼 메타 (labelKo 포함) |
| `TableProfilePolicyResult` | type | getExpectedTableColumns 반환 타입 |
| `getExpectedTableColumns()` | function | tableProfile → required/optional/expectedColumns/recommendedGridMode |
| `TableRowsValidation` | type | T-2 검증 결과 전체 구조 |

### TestWorkspace.tsx에 추가된 항목

| 항목 | 종류 | 내용 |
|---|---|---|
| `TABLE_ROWS_GRID_LABEL/COLOR` | const | gridMode 표시용 |
| `TABLE_ROWS_EXTRACTION_BG/LABEL` | const | extractionStatus 표시용 |
| `tableStatusColor()` | function | O/△/X/— 색상 반환 |
| `buildTableRowsValidation()` | function | 검증 결과 계산 |
| `TableRowsValidationPanel` | component | 상세 패널용 접이식 섹션 |

---

## 5. tableProfile별 expectedColumns 반영

| tableProfile | required | optional | recommendedGridMode |
|---|---|---|---|
| multi_item_table | itemName, quantity | spec, lotNo, expiryDate, itemCode, unitPrice, amount, supplyAmount, manufacturer, taxAmount, insuranceCode, unit, rowIndex | either |
| single_item_table | itemName, quantity | lotNo, unitPrice, supplyAmount, taxAmount, amount, expiryDate, manufacturer, insuranceCode, unit, spec | single-row |
| item_quantity_table | itemCode, itemName, quantity | supplyAmount, unitPrice, insuranceCode, taxAmount, amount, remark | variable |
| lot_serial_quantity_table | itemName, quantity, lotNo | expiryDate, itemCode, serialNo, unit, rowIndex, remark | fixed |
| serial_quantity_table | itemName, serialNo, quantity | unit, lotNo, itemCode, spec, remark | variable |

---

## 6. UI 추가 내용

| 영역 | 추가 내용 | 판정 |
|---|---|---|
| batch 테이블 헤더 | "Table" 컬럼 (Party 다음, Norm 앞) | 추가 완료 |
| batch 테이블 본문 | tableProfile 배지 + 행/첫행 O/△/X | 추가 완료 |
| 상세 패널 (DocumentDetailPanel) | TABLE ROWS PROFILE 접이식 섹션 | 추가 완료 |
| TABLE ROWS PROFILE: 배지 줄 | tableProfile, gridMode, extractionStatus, 행/첫행 status | 구현 완료 |
| TABLE ROWS PROFILE: Required 컬럼 | 초록 배지 목록 | 구현 완료 |
| TABLE ROWS PROFILE: Optional 컬럼 | 회색 배지 목록 | 구현 완료 |
| TABLE ROWS PROFILE: Actual 컬럼 | 파란 배지 목록 (현재 빈값) | 구현 완료 (T-3 대기) |
| TABLE ROWS PROFILE: Missing 컬럼 | 빨간 배지 목록 | 구현 완료 (T-3 대기) |

---

## 7. sample별 확인 결과

| 파일 | tableProfile | required | optional count | gridMode | rowCountStatus | firstRowPreviewStatus | extractionStatus |
|---|---|---|---|---|---|---|---|
| 1.jpg | multi_item_table | itemName, quantity | 12 | either | O (GT=28, OCR=28) | O | parser_not_ready |
| 2.pdf | item_quantity_table | itemCode, itemName, quantity | 6 | variable | O (GT=13, OCR=13) | O | parser_not_ready |
| 3.pdf | single_item_table | itemName, quantity | 10 | single-row | O (GT=1, OCR=1) | O | parser_not_ready |
| 4.pdf | single_item_table | itemName, quantity | 10 | single-row | O (GT=1, OCR=1) | X (ocr_garbled) | parser_not_ready |
| 5.pdf | multi_item_table | itemName, quantity | 12 | either | O (GT=6, OCR=6) | O | parser_not_ready |
| 6.pdf | lot_serial_quantity_table | itemName, quantity, lotNo | 6 | fixed | O (GT=6, OCR=6) | O | parser_not_ready |
| 7.pdf | serial_quantity_table | itemName, serialNo, quantity | 5 | variable | O (GT=1, OCR=1) | O | parser_not_ready |

비고:
- 4.pdf firstRowPreviewStatus=X: OCR "클리마트플란정" vs GT "클리마토플란정" (1자 OCR 오독, ocr_garbled)
- extractionStatus 전체 "parser_not_ready": 현재 documentFields에 rowCount/firstRowPreview만 있고 tableRows 배열 미구현 (T-3 범위)
- missingColumns 전체 = required columns (actual이 없으므로): T-3 이후 실제 추출 시 해소 예정

---

## 8. 기존 기능 영향 확인

| 항목 | 결과 |
|---|---|
| Run OCR 버튼 | **영향 없음** — OCR 호출 로직 미수정 |
| Run All 버튼 | **영향 없음** — batch 실행 로직 미수정 |
| party/address/amount 판정 O/△/X | **영향 없음** — computeFieldFinalStatus 로직 미수정 |
| documentType 집계 | **영향 없음** |
| Profile 집계 (Amount/Party/Table) | **영향 없음** |
| Norm KPI | **영향 없음** — collectEntryNormalizationSummary 미수정 |
| 기존 tableDetected/rowCount/firstRowPreview | **유지** — DOCUMENT_FIELD_META 그대로 표시. Table 컬럼은 별도 추가 |
| invoice_statement.py | **수정 없음** |

---

## 9. JSON/typecheck/build 검증

| 검증 | 결과 |
|---|---|
| manifest.json parse | ✅ ok |
| ground_truth.json parse | ✅ ok |
| `npm run typecheck` | ✅ pass (에러 0) |
| `npm run build` | ✅ pass (`/test` 번들 40.3 kB → 정상) |

---

## 10. 주요 diff 요약

**profiles.ts**: 파일 끝에 100줄 추가. 기존 코드 변경 없음.

**TestWorkspace.tsx**:
- import 라인 1줄 추가 (profiles.ts 신규 export 추가)
- `buildTableRowsValidation()` 함수 40줄 추가 (line ~240 영역)
- `TABLE_ROWS_*` 상수 + `tableStatusColor()` + `TableRowsValidationPanel` 컴포넌트 약 100줄 추가 (DocumentDetailPanel 바로 앞)
- batch 테이블 thead: `<th>Table</th>` 1줄 추가
- batch 테이블 tbody: Table 셀 30줄 추가 (Party td 다음)
- DocumentDetailPanel: `<TableRowsValidationPanel .../>` 4줄 추가 (PROFILE 배지 블록 다음)
- 기존 로직 삭제/변경: **없음**

---

## 11. 남은 문제

| # | 항목 | 원인 | 조치 |
|---|---|---|---|
| 1 | extractionStatus = "parser_not_ready" 전체 | invoice_statement.py가 tableRows 배열을 미출력 | T-3에서 parser tableRows column extraction 구현 |
| 2 | actualColumns = [] 전체 | 위와 동일 | T-3 이후 해소 |
| 3 | missingColumns = requiredColumns 전체 | actual이 없으므로 required가 전부 missing으로 표시 | T-3 이후 해소. 현재 UI에서는 "T-3 대기" 안내 메시지로 처리 |
| 4 | 4.pdf firstRowPreview X | ocr_garbled qualityTag 정상 실패 | 유지 (expected_failure) |
| 5 | multi_item_table recommendedGridMode = "either" | 1.jpg(fixed)와 5.pdf(variable) 두 패턴 존재 | T-2에서 현행 유지. 추후 subProfile 분기 검토 |

---

## 12. 다음 추천 작업

| 후보 | 설명 | 선행 조건 | 위험도 |
|---|---|---|---|
| **OP-1** | canonicalField registry 설계 (table column 포함) | T-1, T-2 완료 | 낮음 |
| **T-3** | parser tableRows column extraction | T-1, T-2 완료 | 중간 |
| Template-Table-1 | Template 고정/가변 그리드와 table column 매핑 | T-1, OP-1 완료 | 중간 |
| RunOCR-Table-1 | RunOCR tableRows 출력 연결 | T-3, OP-3 완료 | 중간 |

### 추천: **OP-1** (canonicalField registry 설계)

추천 이유:
1. T-1/T-2에서 table column canonical 목록이 확정됨 → OP-1 registry에 `isTableColumn=true` 항목으로 반영 가능
2. OP-1은 코드 타입 추가 수준이므로 회귀 위험 없음
3. OP-1 완료 후 Template-Table-1(Template UI table column 매핑)과 OP-2(비정형 필드명 canonical 후보 매핑)로 진입 가능

병행 가능: **T-3** — Test 탭 영역 내 parser 개선. OP-1과 독립적으로 진행 가능.
