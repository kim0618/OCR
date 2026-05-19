# T-25 최종 checkpoint: invoice_statement cleanup 안정화 기준선

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**작업 유형**: 코드 수정 없는 체크포인트 문서화

> **이 기준선의 의미**: "더 이상 수정하지 않겠다"가 아니라 **"다음 작업의 회귀 감지 기준"**이다.

---

## 1. T-25 계열 작업 요약

### T-25 — 수기/빨간펜 오염 분석 (코드 수정 없음)

1.jpg에서 수기/빨간펜 마킹이 OCR 인식에 미치는 영향을 분석했다.

| 분류 | 대상 | 처리 방향 |
|-----|------|---------|
| `source_garbled_hold` | row4 mfg/exp, row12 qty | 보류 — OCR 원문 부재 |
| `numeric_ambiguous` | row4 spec(6OT), row12 spec(3OT) | warning-only (자동 보정 금지) |
| `printed_value_plus_markup` | row19/20/21/26 amount | safe cleanup 후보 |

rowCount: **28/28 exact**, 7개 샘플 7/7 all exact 재확인.

---

### T-25d — cell-level safe cleanup

**수정 파일**: `ocr-server/extractors/invoice_statement.py`

#### 적용된 cleanup

| 규칙 | 예시 |
|-----|------|
| amount comma-space | `301, 100` → `301,100` (row19/20/21/26) |
| quantity trailing symbol | `360 ^` → `360` (row5) |

#### 자동 보정하지 않은 항목

| 항목 | 이유 |
|-----|------|
| itemName | 자동 보정 근거 없음 |
| spec O/0 혼동 | 6OT→60T 불확실 |
| quantity 빈 값 | 수학 추정으로 자동 삽입 금지 |
| manufacturingNo/expiryDate 빈 값 | OCR 원문 부재, 복구 불가 |

---

### T-25f — Custom 탭 cell warning UI 시도 → RESET

#### 시도한 것
Custom 탭 품목표 셀에 OCR 오인식 가능성 ⚠ 아이콘 + amber border/background 표시.

#### RESET 이유
regex 기반 자동 탐지는 **과탐지/미탐지 위험**이 있고, 품목코드/과거 수정 이력/GT/마스터 데이터가 없는 현재 단계에서는 정확한 판단이 어렵다.

#### RESET 결과
**수정 파일**: `src/lib/invoiceTableDisplay.ts`, `src/components/upload/OcrResultPanel.tsx`

| 제거 | 유지 |
|-----|------|
| `CustomCellWarning` 타입 | Custom 탭 품목표 렌더링 |
| `getCustomTableCellWarning` 함수 | textarea 편집 UX |
| itemName/spec warning 탐지 로직 | `textarea title={전체값}` |
| ⚠ 아이콘 + amber border | table-level `missingExpectedWarning` 배지 |
| `cellWarn` 계산 | T-25d backend cleanup |

typecheck PASS, build PASS.

---

### T-25g — spec trailing character safe cleanup

**수정 파일**: `ocr-server/extractors/invoice_statement.py`

#### 적용된 규칙

| Rule | 조건 | 예시 |
|------|------|------|
| A: 닫힘 괄호 누락 | `(` 있음 + `)` 없음 + 길이 ≤20 | `500T(B` → `500T(B)` |
| B: ml suffix 누락 | `^\d{1,4}[mM]$` fullmatch | `150m` → `150ml`, `500m` → `500ml` |

#### 1.jpg 개선 결과

| rowIndex | before | after |
|---------|--------|-------|
| 8 | `500T(B` | `500T(B)` |
| 23 | `150m` | `150ml` |
| 26 | `500m` | `500ml` |

변경하지 않은 spec: `15m|*6포`, `150mI`, `500n1`, `30T`, `500C`, `100T` 등 모두 정상 유지.

py_compile OK, 단위 테스트 17/17 PASS, typecheck PASS, build PASS.

---

## 2. 현재 invoice_statement 기준선

### rowCount exact (전체 7개 샘플)

| 파일 | rowCount | 상태 |
|-----|---------|------|
| 1.jpg | 28 | exact ✓ |
| 2.pdf | 13 | exact ✓ |
| 3.pdf | 1 | exact ✓ |
| 4.pdf | 1 | exact ✓ |
| 5.pdf | 6 | exact ✓ |
| 6.pdf | 6 | exact ✓ |
| 7.pdf | 1 | exact ✓ |

마지막 확인: T10_fix_template_colguides_header_skip_20260516.json

### 활성화된 backend cleanup

| cleanup | 상태 |
|--------|------|
| amount comma-space | ✓ 활성 |
| quantity trailing symbol | ✓ 활성 |
| spec trailing 닫힘 괄호 | ✓ 활성 |
| spec trailing ml suffix | ✓ 활성 |

### 비활성화된 frontend warning

| 항목 | 상태 |
|-----|------|
| Custom 탭 cell-level ⚠ warning | ✗ 비활성 (RESET) |
| table-level missingExpectedWarning 배지 | ✓ 유지 (기존) |
| textarea title={전체값} | ✓ 유지 |

---

## 3. 유지해야 할 조건

| 조건 | 설명 |
|-----|------|
| Custom 탭 cell warning 미표시 | 근거 데이터 없이 재도입 금지 |
| itemName 자동 보정 금지 | correction profile 완성 후 처리 |
| spec O/0 자동 수정 금지 | 확실한 근거 없이 변경 금지 |
| quantity 빈 값 자동 삽입 금지 | 수학 추정으로도 금지 |
| manufacturingNo/expiryDate 자동 복구 금지 | OCR 원문 부재 |
| rowCount 7/7 exact 유지 | invoice_statement 핵심 품질 기준 |
| T-25d cleanup 유지 | amount/qty cleanup 회귀 금지 |
| T-25g spec cleanup 유지 | spec 끝 글자 복구 회귀 금지 |

---

## 4. 다음 작업에서 깨지면 회귀로 간주하는 조건

```
[ ] Custom 탭에서 ⚠ 아이콘 또는 amber warning border 다시 표시됨
[ ] spec '500T(B)'가 다시 '500T(B'로 깨짐
[ ] spec '150ml'이 다시 '150m'으로 깨짐
[ ] spec '500ml'이 다시 '500m'으로 깨짐
[ ] amount '301,100'이 다시 '301, 100'으로 깨짐
[ ] amount '782,160'이 다시 '782, 160'으로 깨짐
[ ] amount '163,100'이 다시 '163, 100'으로 깨짐
[ ] amount '220,890'이 다시 '220, 890'으로 깨짐
[ ] quantity '360'이 다시 '360 ^'로 깨짐
[ ] invoice_statement 7개 중 하나라도 rowCount 불일치
[ ] itemName이 자동으로 변경됨
[ ] quantity 빈 값에 자동 삽입됨
```

---

## 5. 남은 이슈

### 이슈 1: 품목명 OCR 오인식

| 항목 | 내용 |
|-----|------|
| 예시 | OCR: `아집린청` / 사용자 확인: `아젭틴정` |
| 현재 상태 | 자동 보정 없음, warning 없음 (RESET 상태) |
| 처리 방향 | correction profile 구조 완성 후 |

### 이슈 2: row 4 — manufacturingNo/expiryDate 소실

| 항목 | 내용 |
|-----|------|
| 원인 | 수기/빨간펜이 해당 컬럼 인쇄값 위에 겹쳐 OCR 인식 불가 |
| 현재 상태 | 빈 값 유지, `manufacturingNo:handwritten_overlay_suspected:row4` warning만 |
| 처리 방향 | T-25c red_pen_suppression debug variant (미구현) |

### 이슈 3: row 12 — quantity 소실

| 항목 | 내용 |
|-----|------|
| 수학 힌트 | 27,900 ÷ 2,790 = **10** (자동 삽입 금지) |
| 현재 상태 | 빈 값 유지, `quantity:handwritten_overlay_suspected:row12` warning만 |
| 처리 방향 | T-25c 또는 수동 확인 |

---

## 6. 후속 작업 제안

### correction-profile-v1 (우선순위 높음)

사용자가 Custom 탭에서 수정한 tableRows 값을 저장하고, 다음 OCR에서 동일 조건 품목이 발견되면 Custom 탭에 "과거 수정 후보 있음"으로 표시.

**저장 키 (권장)**:
- 공급자 사업자번호
- 공급받는자 사업자번호
- 품목코드
- 규격

**원칙**: 자동 치환 없음. 사용자가 Custom 탭에서 후보를 선택해야 반영.

### T-25c — red_pen_suppression debug variant

HSV 기반 빨간 마스킹 → 재OCR. row4 mfg/exp, row12 qty 복구 가능성 확인.  
**운영 자동 적용 금지**. debug compare 전용.

---

## 7. 검증 상태 요약

| 항목 | 결과 |
|-----|------|
| py_compile | OK (T-25d+T-25g 기준) |
| 단위 테스트 | 17/17 PASS (T-25g) |
| 통합 테스트 | ALL PASS |
| npm run typecheck | PASS |
| npm run build | PASS |
| rowCount 7/7 exact | 전체 확인됨 |
