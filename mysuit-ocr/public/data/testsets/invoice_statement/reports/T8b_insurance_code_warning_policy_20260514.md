# T-8b 2.pdf insuranceCode OCR source missing 표시 정책 결과

**작업일**: 2026-05-14  
**모델**: Claude Code Sonnet

---

## 1. 수정 파일

| 파일 | 수정 내용 |
|---|---|
| `ocr-server/extractors/invoice_statement.py` | `_build_canonical_table_rows` T-8b warning 로직 추가 |
| `mysuit-ocr/src/components/test/TestWorkspace.tsx` | `CanonicalTableMeta` 타입에 `valueMappingWarnings` 추가 + 패널 UI 표시 |

---

## 2. 백업 파일

| 백업 파일 |
|---|
| `backup/invoice_statement_20260514_before_T8b_insurance_warning.py` |
| `backup/TestWorkspace_20260514_before_T8b_insurance_warning.tsx` |

---

## 3. 핵심 요약

2.pdf (및 3.pdf)의 insuranceCode가 "추출 실패"가 아닌 "OCR source missing"임을 tableMeta.valueMappingWarnings에 명시했다.

- insuranceCode 값은 계속 빈 값 유지 (억지로 생성/추정 안 함)
- `tableMeta.valueMappingWarnings`에 `"insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지"` 추가
- Test UI에 Warning 뱃지로 표시 (노란색, 조건부 표시)
- `CanonicalTableMeta` TypeScript 타입에 `valueMappingWarnings?: string[]` 추가

---

## 4. 정책 결정

### insuranceCode를 추정하지 않는 이유
OCR 원문에서 보험코드 패턴으로 확인 가능한 값이 없다. 2.pdf OCR 텍스트의 "보험NO □ 14 □ S O"는 불명확한 마크로, 신뢰 가능한 6자리+ 보험코드를 추출할 수 없다. 잘못된 값을 채우면 의약품 보험청구 오류로 이어질 수 있으므로 빈 값 유지가 안전하다.

### OCR source missing 기준
- `insuranceCode`가 `expected_columns.required`에 포함됨
- AND 모든 행에서 insuranceCode가 비어 있음 (`expectedMissingKeys`에 포함)
- → 특정 샘플 하드코딩 없이 조건 기반으로 적용

### missing과 warning의 관계
- `expectedMissingKeys: ["insuranceCode"]` → 컬럼이 비어 있다는 사실
- `valueMappingWarnings: ["insuranceCode:ocr_source_missing:..."]` → 비어 있는 이유 (OCR source 없음)
- 두 필드가 함께 있으면 사용자/시스템이 이유를 구분할 수 있다

---

## 5. 2.pdf 결과

| 항목 | 결과 |
|---|---|
| rowCount | 13/13 (OK) |
| insuranceCode filled rows | 0/13 (all empty - 빈 값 유지) |
| expectedMissingKeys 포함 여부 | True (insuranceCode 포함) |
| valueMappingWarnings | `insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지` |

---

## 6. 전체 rowCount 회귀 확인

| 샘플 | GT | OCR | 상태 |
|---:|---:|---:|---|
| 1.jpg | 28 | 28 | OK |
| 2.pdf | 13 | 13 | OK |
| 3.pdf | 1 | 1 | OK |
| 4.pdf | 1 | 1 | OK |
| 5.pdf | 6 | 6 | OK |
| 6.pdf | 6 | 6 | OK |
| 7.pdf | 1 | 1 | OK |

---

## 7. UI 표시 여부

- raw JSON: `tableMeta.valueMappingWarnings` 배열로 포함 (기존에도 조회 가능)
- Test UI warning 표시: **추가됨** — `InvoiceTableRowsPanel` 헤더 아래 노란색 Warning 뱃지 (값이 있을 때만 표시)
- 추가 수정 여부: `CanonicalTableMeta` 타입에 `valueMappingWarnings?: string[]` 필드 추가

---

## 8. insuranceCode warning 전체 점검

| 샘플 | required | allEmpty | expectsWarn | hasWarn | 판정 |
|---|---|---|---|---|---|
| 1.jpg | No | Yes | No | No | OK (불필요 warning 없음) |
| 2.pdf | Yes | Yes | Yes | Yes | OK (warning 정상 표시) |
| 3.pdf | Yes | Yes | Yes | Yes | OK (warning 정상 표시) |
| 4.pdf | No | Yes | No | No | OK (불필요 warning 없음) |
| 5.pdf | No | Yes | No | No | OK |
| 6.pdf | No | Yes | No | No | OK |
| 7.pdf | No | Yes | No | No | OK |

---

## 9. 검증 결과

| 검증 항목 | 결과 |
|---|---|
| `python -m py_compile extractors/invoice_statement.py` | PASS |
| `python scripts/verify_invoice_table_rows_t8b.py` | PASS (rowCount 7/7, all checks OK) |
| `npm run typecheck` | PASS |
| `npm run build` | PASS |

---

## 10. 다음 작업 판단

T-8b 완료.

- T-8a 5.pdf 다단 OCR layout 처리로 이동 가능:
  5.pdf의 itemCode/unitPrice/amount는 별도 OCR row로 분리된 다단 layout이 원인. legacy_text_items 경로에서 column-wise association 보강 필요. 2.pdf/3.pdf warning 정책과 별개로 독립 작업.

- 추가 warning 정책 필요 여부:
  현재는 insuranceCode만 명시. 다른 required 컬럼도 유사 패턴이 있으면 동일 방식으로 확장 가능 (`_t8b_required_set` 루프 내에 항목 추가).
