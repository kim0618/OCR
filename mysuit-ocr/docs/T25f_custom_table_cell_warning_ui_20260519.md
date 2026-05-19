# T-25f: 거래명세서 Custom 탭 tableRows cell warning 표시 리포트

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**코드 수정**: 있음 — Custom 탭 전용, row value 불변

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| Custom 탭 전용 warning | **적용** |
| Preview 탭 미적용 | **확인** |
| Validation 탭 미적용 | **확인** |
| History 상세 미적용 | **확인** |
| row value 불변 | **확인** |
| spec 끝 글자 문제 | UI 표시 이슈 → title 속성으로 대응, 데이터 정상 |
| typecheck | **PASS** |
| build | **PASS** |

---

## 2. 백업 파일

| 백업 파일 | 원본 |
|---------|------|
| `backup/OcrResultPanel_20260519_1428_before_T25f_custom_cell_warning.tsx` | `src/components/upload/OcrResultPanel.tsx` |
| `backup/invoiceTableDisplay_20260519_1428_before_T25f_custom_cell_warning.ts` | `src/lib/invoiceTableDisplay.ts` |

---

## 3. 수정 파일

| 파일 | 변경 내용 |
|-----|---------|
| `src/lib/invoiceTableDisplay.ts` | `CustomCellWarning` 타입 + `getCustomTableCellWarning` helper 추가 |
| `src/components/upload/OcrResultPanel.tsx` | import 추가, Custom 탭 cell 렌더링에 warning 표시 로직 삽입 |

---

## 4. warning 탐지 규칙

| field | warning key | 조건 | 메시지 | 자동 보정 |
|-------|-------------|------|--------|----------|
| quantity | `quantity:handwritten_overlay_suspected` | T-25d valueMappingWarnings에 해당 row 경고 있음 | 수기 표시로 수량 OCR 원문이 불명확합니다 | 없음 |
| manufacturingNo | `manufacturingNo:handwritten_overlay_suspected` | T-25d valueMappingWarnings에 해당 row 경고 있음 | 수기 표시로 제조번호 OCR 원문이 불명확합니다 | 없음 |
| expiryDate | `expiryDate:handwritten_overlay_suspected` | manufacturingNo 경고가 있는 row → expiryDate에도 적용 | 수기 표시로 유효기간 OCR 원문이 불명확합니다 | 없음 |
| spec | `spec:numeric_alpha_ambiguous` | `\d[O][A-Z]` 패턴 또는 T-25d 경고 | 규격의 숫자/영문자 OCR 혼동 가능성. 자동 보정하지 않았습니다 | 없음 |
| itemName | `itemName:possible_ocr_char_confusion` | itemName이 "청" 또는 "징"으로 끝날 때 | 품목명 OCR 오인식 가능성이 있습니다 | 없음 |

**탐지 우선순위**:
1. `tableMeta.valueMappingWarnings` (T-25d 백엔드 row-specific 경고) 우선
2. 셀 값 패턴 독립 탐지 (valueMappingWarnings 없어도 동작)

---

## 5. Custom 탭 표시 방식

### 셀 아이콘
```
6OT ⚠
```
- `⚠` 기호 (U+26A0)
- 셀 우측 상단에 position: absolute 배치 (top: 2px, right: 3px)
- 기존 textarea와 독립 레이어

### title/tooltip
- `⚠` span에 `title={cellWarn.message}` — hover 시 이유 표시
- `<textarea>`에도 `title={row[col.key]}` — 전체값 hover 확인 가능 (spec 표시 문제 대응)

### 스타일 (warn severity)
- `<td>` border: `rgba(217,119,6,0.45)` 1px solid
- `<td>` background: `rgba(254,243,199,0.30)` (연한 노란색)
- ⚠ 색상: `#d97706` (amber)

### 스타일 (info severity)
- `<td>` border: `rgba(59,130,246,0.35)` 1px solid
- `<td>` background: `rgba(219,234,254,0.20)` (연한 파란색)
- ⚠ 색상: `#3b82f6` (blue)

### 편집 기능 유지
- `<textarea>` 기존 onChange/onFocus/onBlur 그대로 유지
- warning 표시는 textarea 편집을 방해하지 않음
- warning이 있을 때 `paddingRight: 18px` 추가 → ⚠ 밑에 텍스트 가리지 않음

---

## 6. 1.jpg Custom 탭 경고 표시 예시

| rowIndex | field | currentValue | warning key | 표시 |
|---------|-------|-------------|------------|------|
| 4 | spec | `6OT` | spec:numeric_alpha_ambiguous | `6OT ⚠` |
| 4 | manufacturingNo | `""` | manufacturingNo:handwritten_overlay_suspected | `⚠` (빈 셀) |
| 4 | expiryDate | `""` | expiryDate:handwritten_overlay_suspected | `⚠` (빈 셀) |
| 12 | spec | `3OT` | spec:numeric_alpha_ambiguous | `3OT ⚠` |
| 12 | quantity | `""` | quantity:handwritten_overlay_suspected | `⚠` (빈 셀) |
| 11 (가상) | itemName | `아집린청` | itemName:possible_ocr_char_confusion | `아집린청 ⚠` |
| 1~3, 5~11, 13~28 | 모든 필드 | 정상값 | — | 경고 없음 |

**현재 1.jpg 데이터 기준**: itemName이 "청/징"으로 끝나는 행 없음 → `itemName:possible_ocr_char_confusion` 미발동  
(아집린청처럼 OCR이 잘못 읽는 경우 발동됨)

---

## 7. 규격 끝 글자 문제 확인 결과

### 진단
- **데이터 문제 아님**: 1.jpg tableRows spec 값들은 모두 정상 (`15m|*6포`, `30T`, `6OT` 등)
- **UI 표시 문제**: spec 컬럼 폭이 82px (고정), `<textarea>`는 `text-overflow: ellipsis`를 지원하지 않아 긴 값이 스크롤 처리됨

### 최장 spec 값 분석
| spec 값 | 길이 | 82px 대비 |
|--------|-----|---------|
| `15m|*6포` | 7자 | 이전에는 내용 보임 (ASCII+한글 혼재, 실제 너비 ≈ 55px) |
| `500T(B)` | 7자 | 안전 (≈ 49px) |
| `120DOSE` | 7자 | 안전 (≈ 49px) |

### 처리 방식
- **UI fix 적용**: `<textarea title={String(row[col.key] ?? "")}>` 추가
- hover 시 셀 전체값 표시 → 잘려 보이는 문제 해결
- 자동 보정 없음, spec 값 그대로 유지

---

## 8. 회귀 확인

| 항목 | 결과 |
|-----|------|
| Preview 탭 tableRows | **변경 없음** (getCustomTableCellWarning 호출 없음) |
| Custom 탭 tableRows | **경고 표시 추가** (row value 불변) |
| Validation 탭 tableRows | **변경 없음** |
| History 상세 tableRows | **변경 없음** |
| invoice rowCount (7/7 exact) | **유지** (parser 미변경) |
| T-25d cleanup 결과 | **유지** (amount comma-space, qty trailing symbol 정상 작동) |
| typecheck | **PASS** |
| build | **PASS** |

---

## 9. 남은 이슈

| 이슈 | 처리 방향 |
|-----|---------|
| itemName 자동 보정 (아집린청→아젭틴정) | 품목 마스터 DB 필요, 이번 작업 범위 밖 |
| spec 자동 보정 (6OT→60T) | 보류, 자동 치환 위험 |
| row 4 manufacturingNo/expiryDate 실제 값 복구 | T-25c red_pen_suppression debug variant |
| row 12 quantity 실제 값 복구 | T-25c 또는 수동 확인 |
| 사용자 수정값 저장 기반 item correction | 별도 작업 필요 |

---

## 10. 구현 위치 요약

### `invoiceTableDisplay.ts` 추가 코드
```typescript
// T-25f: Custom 탭 전용 cell-level warning helper

export interface CustomCellWarning {
  key: string;
  message: string;
  severity: "warn" | "info";
}

export function getCustomTableCellWarning(
  row: Record<string, unknown>,
  colKey: string,
  tableMeta: Record<string, unknown> | null | undefined,
): CustomCellWarning | null { ... }
```

### `OcrResultPanel.tsx` 변경점
- import: `getCustomTableCellWarning` 추가
- Custom 탭 `editRows.map` 내부: `map` → `({...})` 화살표 + `const cellWarn = getCustomTableCellWarning(...)`
- `<td>`: position: relative, cellWarn 시 border/background 추가
- `<textarea>`: title={전체값}, cellWarn 시 paddingRight: 18
- `cellWarn && <span>⚠</span>`: absolute 위치, title={message}
