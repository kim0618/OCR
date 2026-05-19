# T-25f REV1: Custom 탭 tableRows warning 로직 수정 리포트

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**코드 수정**: `src/lib/invoiceTableDisplay.ts` 1개

---

## 1. 수정 배경

T-25f 구현에서 `valueMappingWarnings` 기반 탐지가 **빈칸 셀**에도 warning을 표시하는 문제가 있었다.  
빈칸은 원래부터 비어 있을 수 있으므로 warning 표시 금지.  
REV1에서는 **비어 있지 않은 셀 값 기반 자동 탐지**로 전면 전환한다.

---

## 2. 백업 파일

| 파일 | 원본 |
|-----|------|
| `backup/invoiceTableDisplay_20260519_1439_before_T25f_REV1_warning_refine.ts` | `src/lib/invoiceTableDisplay.ts` |
| `backup/OcrResultPanel_20260519_1439_before_T25f_REV1_warning_refine.tsx` | `src/components/upload/OcrResultPanel.tsx` |

---

## 3. 수정 파일

| 파일 | 변경 내용 |
|-----|---------|
| `src/lib/invoiceTableDisplay.ts` | `getCustomTableCellWarning` 함수 전면 재작성 |
| `src/components/upload/OcrResultPanel.tsx` | **변경 없음** (함수 호출 구조 그대로) |

---

## 4. 제거한 warning 조건

| 제거된 warning | 제거 이유 |
|--------------|---------|
| `quantity:handwritten_overlay_suspected` | 빈칸에 표시됨 — valueMappingWarnings row 고정 기반, 제거 |
| `manufacturingNo:handwritten_overlay_suspected` | 동일 이유 |
| `expiryDate:handwritten_overlay_suspected` | 동일 이유 |
| `valueMappingWarnings` 파싱 로직 전체 | 빈칸 문제의 근본 원인, 전면 제거 |

---

## 5. 유지한 warning 조건 (값 기반 자동 탐지)

| warning key | field | 조건 | 메시지 | severity |
|------------|-------|------|--------|---------|
| `itemName:possible_ocr_char_confusion` | itemName | 한글 포함 + 3자 이상 + "청" 또는 "징"으로 끝남 | 품목명 OCR 오인식 가능성이 있습니다. 원문 이미지와 대조 후 확인하세요. | warn |
| `spec:numeric_alpha_ambiguous` | spec | ≤6자 + 숫자 + O + T 포함 (예: 6OT, 3OT) | 규격의 숫자/영문자 OCR 혼동 가능성이 있습니다. 자동 보정하지 않았습니다. | warn |
| `spec:possible_unit_suffix_missing` | spec | 순수 숫자만으로 구성 (예: 400) | 규격 단위가 누락되었을 가능성이 있습니다. 원문 이미지와 대조 후 확인하세요. | info |

**모든 warning**: 자동 보정 없음, 표시만.

---

## 6. 빈칸 warning 제거 확인

`getCustomTableCellWarning` 함수 시작부에 방어 로직 추가:

```typescript
const rawValue = row?.[colKey];
const value = String(rawValue ?? "").trim();
if (!value) return null;  // 빈칸이면 어떤 field라도 null 반환
```

| 케이스 | 결과 |
|-------|------|
| `quantity = ""` | **null** (경고 없음) ✓ |
| `manufacturingNo = ""` | **null** (경고 없음) ✓ |
| `expiryDate = ""` | **null** (경고 없음) ✓ |
| `spec = "  "` (공백만) | **null** (경고 없음) ✓ |

---

## 7. itemName 자동 탐지 확인

```typescript
colKey === "itemName"
  && value.length >= 3
  && /[가-힣]/.test(value)          // 한글 포함
  && /(?:청|징)$/.test(value)       // "청" 또는 "징"으로 끝남
```

| itemName 값 | 결과 |
|-----------|------|
| `아집린청` | `itemName:possible_ocr_char_confusion` ✓ |
| `아젭틴청` | `itemName:possible_ocr_char_confusion` ✓ |
| `메티마졸정` | null (정상, "정" 끝) ✓ |
| `헥사메딘액0.12%` | null (정상) ✓ |

---

## 8. spec 자동 탐지 확인

### O/0/T 혼동 탐지
```typescript
colKey === "spec"
  && value.length <= 6              // 짧은 규격값
  && /\d/.test(value)              // 숫자 포함
  && /O/.test(value)               // 대문자 O 포함
  && /T/i.test(value)              // T 포함 (대소문자 무관)
```

| spec 값 | 결과 |
|--------|------|
| `6OT` | `spec:numeric_alpha_ambiguous` ✓ |
| `3OT` | `spec:numeric_alpha_ambiguous` ✓ |
| `30T` | null (O 없음) ✓ |
| `500C` | null (O 없음, T 없음) ✓ |
| `120DOSE` | null (길이 7 > 6) ✓ |

### 단위 누락 탐지 (info)
```typescript
colKey === "spec" && /^\d+$/.test(value)
```

| spec 값 | 결과 |
|--------|------|
| `400` | `spec:possible_unit_suffix_missing` (info) ✓ |
| `30T` | null (숫자만 아님) ✓ |

---

## 9. Preview/Validation/History 미표시 확인

`getCustomTableCellWarning`은 **Custom 탭 `editRows.map` 렌더링 내부에서만 호출**.  
Preview / Validation / History 렌더링 경로에는 호출 없음 — `OcrResultPanel.tsx` 미변경.

---

## 10. row value 불변 확인

`getCustomTableCellWarning`은 `row` 객체를 읽기만 하고 수정하지 않음.  
T-25d cleanup 결과(amount comma-space, qty trailing symbol)는 그대로 유지.

---

## 11. typecheck / build 결과

| 항목 | 결과 |
|-----|------|
| `npm run typecheck` | **PASS** |
| `npm run build` | **PASS** |
| 로직 검증 (15 케이스) | **15/15 PASS** |
