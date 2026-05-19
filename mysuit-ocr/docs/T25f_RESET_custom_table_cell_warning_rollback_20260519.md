# T-25f RESET: Custom 탭 tableRows warning 표시 제거 리포트

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**코드 수정**: 2개 파일, warning 코드 제거만

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| Custom 탭 ⚠ 아이콘 제거 | **완료** |
| Custom 탭 warning border/background 제거 | **완료** |
| Custom 탭 cellWarn 계산 제거 | **완료** |
| `getCustomTableCellWarning` 함수 제거 | **완료** |
| `CustomCellWarning` 타입 제거 | **완료** |
| textarea title 유지 (전체값 hover) | **유지** |
| Preview / Validation / History 영향 | **없음** |
| T-25d cleanup 결과 | **유지** |
| typecheck | **PASS** |
| build | **PASS** |

---

## 2. 백업 파일

| 파일 | 설명 |
|-----|------|
| `backup/invoiceTableDisplay_20260519_1449_before_T25f_RESET_warning_rollback.ts` | RESET 직전 invoiceTableDisplay.ts |
| `backup/OcrResultPanel_20260519_1449_before_T25f_RESET_warning_rollback.tsx` | RESET 직전 OcrResultPanel.tsx |

---

## 3. 수정 파일

| 파일 | 변경 내용 |
|-----|---------|
| `src/lib/invoiceTableDisplay.ts` | T-25f/REV1 섹션 전체 제거 |
| `src/components/upload/OcrResultPanel.tsx` | import 제거, Custom 탭 셀 렌더링 warning 코드 제거 |

---

## 4. 제거한 warning 관련 코드

### `invoiceTableDisplay.ts`
- `CustomCellWarning` interface
- `getCustomTableCellWarning()` export 함수
- `_ITEM_NAME_CHAR_CONFUSION_RE` regex 상수
- T-25f/REV1 섹션 주석 블록

### `OcrResultPanel.tsx`
- `getCustomTableCellWarning` import
- `const cellWarn = getCustomTableCellWarning(row, col.key, docTableMeta)`
- T-25f comment
- `<td>` warning border/background styles
- `<td>` `position: "relative"` (warning icon용)
- `<textarea>` `paddingRight: cellWarn ? 18 : undefined`
- `{cellWarn && (<span>⚠</span>)}` 블록 (title, aria-label, color, zIndex 포함)
- `docTableDisplayCols.map((col) => { ... return (...); })` 래퍼 → `.map((col) => (...))` 원래 형태로 복원

---

## 5. 유지한 기능

| 기능 | 파일 | 상태 |
|-----|------|------|
| Custom 탭 품목표 렌더링 | OcrResultPanel.tsx | **유지** |
| textarea 편집 기능 (onChange/onFocus/onBlur) | OcrResultPanel.tsx | **유지** |
| `title={String(row[col.key] ?? "")}` on textarea | OcrResultPanel.tsx | **유지** (전체값 hover — 독립적으로 유용) |
| `missingExpectedWarning` table-level 배지 | OcrResultPanel.tsx | **유지** (T-25f 이전부터 존재, 관계 없음) |
| `buildInvoicePreviewCols` 공통 helper | invoiceTableDisplay.ts | **유지** |
| `normalizeTableCell`, `hasMeaningfulTableValue` 등 | invoiceTableDisplay.ts | **유지** |
| T-25d backend cleanup 결과 (amount space, qty symbol) | invoice_statement.py | **유지** (미변경) |

---

## 6. Custom 탭 warning 제거 확인

| 체크 항목 | 결과 |
|---------|------|
| `getCustomTableCellWarning` 코드 없음 | ✓ |
| `cellWarn` 변수 없음 | ✓ |
| `⚠` 아이콘 코드 없음 | ✓ |
| amber warning border 코드 없음 (T-25f 것만, 기존 배지 코드는 남아 있음) | ✓ |
| warning background 코드 없음 | ✓ |
| `cursor: "help"` 없음 | ✓ |
| 아집린청, 6OT, 3OT에도 warning 없음 (코드 자체 제거) | ✓ |
| 빈칸 warning 없음 (코드 자체 제거) | ✓ |

---

## 7. row value 불변 확인

이번 RESET은 UI 렌더링 코드만 수정.  
`invoice_statement.py` 미변경 → tableRows 값 불변 ✓  
T-25d cleanup (amount comma-space, qty trailing symbol) 그대로 유지 ✓

---

## 8. Preview / Validation / History 영향 없음 확인

제거된 `getCustomTableCellWarning`은 Custom 탭 렌더링에서만 호출됐음.  
Preview / Validation / History 렌더링 경로는 이 함수를 사용하지 않았으므로 영향 없음 ✓

---

## 9. typecheck / build 결과

| 항목 | 결과 |
|-----|------|
| `npm run typecheck` | **PASS** |
| `npm run build` | **PASS** |

---

## 10. 후속 작업 제안

나중에 데이터가 충분히 쌓였을 때 다음 구조로 재구현한다:

| 단계 | 내용 |
|-----|------|
| 1 | 사용자가 Custom 탭에서 수정한 tableRows 값을 **correction profile**로 저장 |
| 2 | 저장 키: 품목코드 + 거래처(사업자번호) + 규격 3중 키 |
| 3 | 다음 OCR에서 같은 품목코드/유사 품목명 발견 시 "과거 수정 후보 있음" 표시 |
| 4 | 자동 치환 아닌 Custom 탭에서 **후보 표시 → 사용자가 선택** 방식 |
| 5 | 신뢰도 기준: 품목코드 완전 일치 > 품목명 유사도 > 규격 일치 순 |
