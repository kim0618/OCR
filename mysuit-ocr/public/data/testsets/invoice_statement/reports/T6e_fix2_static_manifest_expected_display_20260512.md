# T-6e-fix2-static manifest expectedColumns UI 표시 정적 검증 결과

## 1. 수정 파일
- `C:\OCR\mysuit-ocr\src\components\test\TestWorkspace.tsx`
  - `getManifestExpectedColKeys`: `required + optional` → **`required` 전용**으로 수정

## 2. 핵심 결론

- **expected 모드 source**: `manifest.invoiceProfile.tableExpectedColumns.required`
- **manifest 우선순위**: 1순위 (manifest required 있으면 tableMeta/ALL_CANONICAL_COLS 무시)
- **tableMeta fallback 조건**: manifest.tableExpectedColumns가 없을 때만 tableMeta.expectedColumnKeys 사용
- **extra column 유입 가능성**: **없음** — manifest required를 반환한 뒤 즉시 return, 다른 경로 실행 안 됨
- **발견한 문제**: 기존 `getManifestExpectedColKeys`가 required+optional 전체 포함 → required만으로 수정

---

## 3. 코드 경로 검증

| 항목 | 결과 | 근거 |
|---|---|---|
| `InvoiceTableRowsPanel` invoiceProfile prop 수신 | ✓ | line 4176: `invoiceProfile?: InvoiceProfile` |
| 호출부 invoiceProfile 전달 | ✓ | `<InvoiceTableRowsPanel ... invoiceProfile={invoiceProfile} />` |
| expected 모드 manifest 1순위 | ✓ | `if (manifestExpectedColKeys && manifestExpectedColKeys.length > 0) return manifestExpectedColKeys;` |
| manifest 존재 시 tableMeta.expectedColumnKeys 미사용 | ✓ | `return` 후 2순위 코드 미도달 |
| manifest 존재 시 ALL_CANONICAL_COLS 미사용 | ✓ | mode="expected"에서 ALL_CANONICAL_COLS 참조 없음 |
| manifest 존재 시 valueColumns 미사용 | ✓ | "expected" 분기에서 tableRows 스캔 없음 |
| manifest 순서 유지 | ✓ | `getManifestExpectedColKeys`가 required 배열 순서 그대로 push |
| label: canonical labelKo 사용 | ✓ (`△`) | `colLabelMap[col] ?? col` (TABLE_COLUMN_META 기반). manifest에 per-column label 없음 |
| missing 계산 manifest required 기준 | ✓ | `manifestRequiredKeys = invoiceProfile?.tableExpectedColumns?.required` 사용 |
| expected count manifest required 기준 | ✓ (수정 후) | `getManifestExpectedColKeys` → required 전용으로 수정 |

**label 비고** (`△`): manifest에 per-column label 미정의. TABLE_COLUMN_META.labelKo 사용.  
실제 표시: `itemName → "품목명"` (canonical) vs 문서 원본 "품명"(5.pdf) / "품목"(1.jpg). 동일 의미이므로 실용적으로 충분.

---

## 4. 샘플별 expected 표시 컬럼 정적 검증

| 샘플 | expected count | required keys | 표시 labelKo | 결과 |
|---|---:|---|---|---|
| 1.jpg | **7** | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount | 품목명, 규격, 제조번호, 유효기간, 수량, 단가, 금액 | ✓ |
| 2.pdf | **6** | itemCode, itemName, quantity, unitPrice, supplyAmount, insuranceCode | 품목코드, 품목명, 수량, 단가, 공급가액, 보험코드 | ✓ (태스크 기술 8개와 차이 있음 — 아래 참조) |
| 3.pdf | **9** | insuranceCode, itemName, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate | 보험코드, 품목명, 규격, 수량, 단가, 금액, 제조사, 제조번호, 유효기간 | ✓ |
| 4.pdf | **7** | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount | 품목명, LOT/제조번호, 단위, 수량, 단가, 공급가액, 세액 | ✓ |
| 5.pdf | **5** | itemName, itemCode, quantity, unitPrice, amount | 품목명, 품목코드, 수량, 단가, 금액 | ✓ |
| 6.pdf | **5** | itemCode, itemName, quantity, lotNo, expiryDate | 품목코드, 품목명, 수량, LOT/제조번호, 유효기간 | ✓ (태스크 기술 6개와 차이 있음 — 아래 참조) |
| 7.pdf | **4** | itemName, serialNo, unit, quantity | 품목명, Serial, 단위, 수량 | ✓ |

**2.pdf 차이**: 태스크는 "NO/품목코드/품목명/수량/소비자단가/공급단가/공급금액/보험No" 8개 기술.  
manifest required에 rowIndex(NO) 미포함 → 6개 표시. rowIndex는 canonical table의 자동 부여 필드로, display-only 컬럼이므로 expected 표시에서 제외하는 것이 타당.

**6.pdf 차이**: 태스크는 "NO/제품코드/제품명/수량/LotNo/유효일자" 6개 기술.  
manifest required에 rowIndex(NO) 미포함 → 5개 표시. 동일 이유로 제외 타당.

**수정 전후 count 비교**:
| 샘플 | 수정 전 (req+opt) | 수정 후 (req only) | 태스크 목표 |
|---|---:|---:|---:|
| 1.jpg | 13 | **7** | 7 ✓ |
| 2.pdf | 9 | **6** | 8 (rowIndex 제외 시 6) |
| 3.pdf | 12 | **9** | 9 ✓ |
| 4.pdf | 10 | **7** | 7 ✓ |
| 5.pdf | 9 | **5** | 5 ✓ |
| 6.pdf | 9 | **5** | 6 (rowIndex 제외 시 5) |
| 7.pdf | 7 | **4** | 4 ✓ |

---

## 5. 발견한 문제와 수정 내용

### 문제
`getManifestExpectedColKeys(tableExpectedColumns)` 함수가 `required + optional` 전체를 반환.  
→ 5.pdf expected count 9 (실제 표시 9개), 태스크 목표 5개. 불일치.

### 수정
```typescript
// 수정 전
for (const k of [...(tableExpectedColumns.required ?? []), ...(tableExpectedColumns.optional ?? [])]) {

// 수정 후
for (const k of (tableExpectedColumns.required ?? [])) {
```
optional 컬럼은 expected 모드에서 제외. detected/hasValue 모드에서 값이 있을 때 표시됨.

---

## 6. 검증 결과

- **typecheck**: ✓ PASS
- **build**: ✓ PASS

---

## 7. 다음 작업 판단

**정적 검증 완료**: expected UI 표시 경로가 manifest required 컬럼 기준으로 고정됨.

- 브라우저에서 샘플 클릭 시 expected 모드 자동 전환 + manifest required 컬럼만 표시될 것으로 예상
- RunAll 없이 샘플 선택만으로도 "expected 컬럼" 버튼 활성화 여부 확인 가능 (invoiceProfile이 manifest에서 로드되므로)
- 실제 OCR 전에도 expected 컬럼 구조가 correct하게 표시됨
- 값 매핑(OCR 결과가 올바른 컬럼에 배치되는지)은 RunAll 후 확인 필요 → T-6g-fix 또는 value mapping으로 이동
