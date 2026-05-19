# T-25: 거래명세서 1.jpg 수기/빨간펜 오염 tableRows 분석 리포트

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**분석 대상**: `invoice_statement/1.jpg`  
**코드 수정**: 없음 (분석 리포트 전용)

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 분석 대상 | 거래명세서 1.jpg (28행 품목표) |
| rowCount 유지 | **28/28 유지** (변경 없음) |
| 수기 오염 의심 cell 수 | **8개** (엄격 기준) |
| 부차적 OCR 아티팩트 | 2개 (no_action) |
| source_garbled_hold (복구 불가) | 3개 (row4 mfg/exp, row12 qty) |
| numeric_ambiguous (O/0 혼동) | 2개 (row4 spec, row12 spec) |
| safe_numeric_cleanup_candidate | 4개 (row19/20/21/26 amount 공백) |
| red_pen_suppression 후보 | row4, row12 (debug-only, 운영 미적용) |
| 코드 수정 여부 | **없음** |
| 회귀 위험 | **없음** (코드 미변경) |

---

## 2. 1.jpg tableRows 현황 (전체 28행)

OCR 원문 출처: `ocr_cache.json → 1.jpg.ocr_text` (2026-05-18 스캔)  
파서 결과 출처: `T10_fix_template_colguides_header_skip_20260516.json` + `T6m_value_mapping_after_20260514.json`

### 문제 있는 행

| rowIndex | field | currentValue | issueType | recommendation | 수학 검증 |
|---------|-------|-------------|-----------|---------------|----------|
| 4 | spec | `6OT` | numeric_ambiguous | warning_only | — |
| 4 | manufacturingNo | `""` (empty) | source_garbled_hold | hold | — |
| 4 | expiryDate | `""` (empty) | source_garbled_hold | hold | — |
| 12 | spec | `3OT` | numeric_ambiguous | warning_only | — |
| 12 | quantity | `""` (empty) | source_garbled_hold | hold | 27,900 ÷ 2,790 = **10** (추정 가능, 자동 삽입 금지) |
| 19 | amount | `301, 100` | printed_value_plus_markup | safe_numeric_cleanup_candidate | 10 × 30,110 = **301,100** ✓ |
| 20 | amount | `782, 160` | printed_value_plus_markup | safe_numeric_cleanup_candidate | 240 × 3,259 = **782,160** ✓ |
| 21 | amount | `163, 100` | printed_value_plus_markup | safe_numeric_cleanup_candidate | 10 × 16,310 = **163,100** ✓ |
| 26 | amount | `220, 890` | printed_value_plus_markup | safe_numeric_cleanup_candidate | 30 × 7,363 = **220,890** ✓ |

### 부차적 아티팩트 (no_action)

| rowIndex | field | currentValue | issueType | recommendation |
|---------|-------|-------------|-----------|---------------|
| 1 | spec | `15m\|*6포` | itemName_trailing_noise | no_action (`\|` = l OCR 혼동, 비수기 원인) |
| 23 | spec | `150mI` | numeric_ambiguous | no_action (I = l OCR 혼동, 비수기 원인) |

### 정상 행 (27개 필드 모두 clean)

Rows 2, 3, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 22, 24, 25, 27, 28 — 모든 필드 정상.

Row 27 (`씬지로이드정0.025mg`): OCR 원문에 `0.025ng`로 읽히는 경우가 있으나,  
T10 파서 결과는 `0.025mg`로 표시 — 현재 파서 출력 기준 정상.

---

## 3. 수기 오염 유형 분류

| 유형 | 건수 | 설명 | 처리 방향 |
|------|------|------|----------|
| `source_garbled_hold` | 3 | OCR 원문에서 해당 컬럼 토큰이 완전히 소실. 수기/빨간펜이 인쇄값 위에 겹쳐 인식 불가능. | hold — 자동 복구 금지. 이미지 전처리 후 재OCR 검토 (T-25c) |
| `numeric_ambiguous` | 2 | spec 필드에서 문자 'O'가 숫자 '0'으로 인식되어야 할 위치에 존재. `6OT`→`60T`, `3OT`→`30T` 추정. | warning_only — 자동 수정 금지. T-25b에서 warning 추가. |
| `printed_value_plus_markup` | 4 | amount 필드의 천 단위 쉼표 뒤에 공백이 삽입됨. 패턴: `301, 100`. 수기 체크/동그라미가 쉼표 영역에 겹쳐 OCR이 공백을 삽입. 수학 검증으로 올바른 값 확인됨. | safe_numeric_cleanup_candidate — T-25b/d에서 regex 정리 가능. |
| `itemName_trailing_noise` | 1 | spec `\|` 문자가 l(소문자) 대신 파이프(`\|`)로 읽힘. 비수기 원인. | no_action |
| `no_action_minor` | 1 | spec `I` 문자가 l(소문자) 대신 대문자 I로 읽힘. 비수기 원인. | no_action |

---

## 4. 안전 개선 후보

### A. safe_numeric_cleanup_candidate
**대상**: row 19, 20, 21, 26 — amount 필드

```
현재 값 → 정리 후 값
"301, 100" → "301,100"   (10 × 30,110 = 301,100 ✓)
"782, 160" → "782,160"   (240 × 3,259 = 782,160 ✓)
"163, 100" → "163,100"   (10 × 16,310 = 163,100 ✓)
"220, 890" → "220,890"   (30 × 7,363 = 220,890 ✓)
```

**제안 regex**: `re.sub(r'(\d{1,3}),\s+(\d{3})', r'\1,\2', value)`

- 패턴이 명확 (쉼표 + 공백 + 정확히 3자리 숫자)
- 수학 검증으로 4건 모두 확인됨
- 다른 6개 샘플에 동일 패턴 없는지 T-25b에서 확인 후 적용
- **이번 작업에서 구현 안 함** → T-25b/d로 분리

### B. warning_only_candidate
**대상**: row 4 spec (`6OT`), row 12 spec (`3OT`)

- `6OT` → `60T`, `3OT` → `30T` 가능성이 높으나 자동 수정은 부정확할 수 있음
- 제안 warning: `spec:O_zero_ambiguity_detected`
- **이번 작업에서 구현 안 함** → T-25b로 분리

### C. red_pen_preprocess_candidate
**대상**: row 4 (mfg/exp 소실 영역), row 12 (qty 소실 영역)

- HSV 기반 빨간 계열 픽셀 마스킹 → 인페인트 → 재OCR
- debug compare만, 운영 자동 적용 금지
- **이번 작업에서 구현 안 함** → T-25c로 분리

### D. source_garbled_hold (복구 불가)
**대상**: row 4 manufacturingNo, row 4 expiryDate, row 12 quantity

- OCR 원문에 토큰 자체가 없음 → 파서가 빈 값을 올바르게 유지 중
- row 12 quantity: 수학적으로 qty=10 추정 가능 (27,900 ÷ 2,790 = 10)이지만 자동 삽입 금지
- 수동 확인 또는 red_pen_suppression 후 재OCR 필요

---

## 5. red_pen_suppression 검토

### 가능성
- HSV 기반 빨간색 계열(H: 0-15 또는 160-180, S>100, V>50) 픽셀 마스킹 후 재OCR
- row 4의 제조번호/유효기간 컬럼 영역, row 12의 수량 컬럼 영역에 효과 기대

### 위험
| 위험 항목 | 설명 |
|---------|------|
| 빨간 도장/인감 소실 | 문서에 빨간 인감 또는 도장이 있는 경우 함께 제거됨 |
| 인쇄 잉크 간섭 | 수기 빨간 잉크와 인쇄 값이 같은 픽셀에 겹쳐 있으면 인쇄값도 손상 |
| 회귀 위험 | 현재 정상 추출 중인 다른 행에 영향 줄 수 있음 |
| 처리 지연 | 재OCR 호출 추가 → 응답 시간 증가 |

### auto-apply 금지 사유
`preprocessing_policy.py` Rule 1: invoice_statement는 자동 전처리 적용 영구 제외.  
`decide_auto_apply_preprocessing()` 함수에서 `invoice_excluded_from_auto_apply` 반환.

### debug-only 판단
T-25c 작업에서 별도 debug variant로만 구현하고, 결과를 비교 리포트로 공유.  
운영 OCR 경로에 절대 삽입하지 않음.

---

## 6. parser 동작 확인

### value mapping 경로
```
template colGuides → _table_items_with_expected_columns() (colGuides path)
  → _extract_items_using_boundaries()
  → _build_canonical_table_rows()
  → tableMeta.valueMappingWarnings
```

### 오염값 채택 여부
- 파서는 **빈 값을 그대로 유지** (row 4 mfg/exp, row 12 qty) — 임의 추정 없음 ✓
- amount 공백 값(`301, 100`)은 OCR 원문 그대로 채택 — 파서가 공백을 제거하지 않음
- 현재 `tableMeta.valueMappingWarnings`에 이들 케이스에 대한 warning 없음

### normalizeTableCell/display layer 문제인지 여부
- 오염 원인: OCR 원문 레이어 (파서 이전 단계)
- displayLayer 문제 아님: `OcrResultPanel.tsx`는 파서 출력을 그대로 표시
- 파서 value 문제: amount 공백은 파서가 정리하지 않아 노출됨 (T-25b/d에서 정리 예정)

### 현재 valueMappingWarnings
- 현재 구현된 warning: `insuranceCode:ocr_source_missing` 단건 (T-8b)
- 1.jpg 기준 `insuranceCode`는 required 아님 → 현재 warning 없음

---

## 7. warning 정책 제안

T-25b에서 `tableMeta.valueMappingWarnings`에 추가할 후보:

| warning key | trigger 조건 | 대상 행 | 구현 우선순위 |
|------------|-------------|--------|------------|
| `tableRows:partial_field_contamination_suspected` | 필수 컬럼 fill rate < 100% | row 4, 12 | T-25b |
| `quantity:handwritten_overlay_suspected` | itemName/mfg/exp/unitPrice/amount 있는데 quantity 빈 행 | row 12 | T-25b |
| `manufacturingNo:handwritten_overlay_suspected` | itemName/qty/unitPrice/amount 있는데 mfg+exp 모두 빈 행 | row 4 | T-25b |
| `amount:comma_space_formatting_noise` | amount 패턴 `\d{1,3},\s+\d{3}` 매칭 | row 19, 20, 21, 26 | T-25b |

**원칙**: warning 추가는 row value를 바꾸지 않음. rowCount에 영향 없음. rowCount 7/7 exact 유지.

---

## 8. 회귀 검증 계획

### rowCount exact 검증 (기준)

| 파일 | GT rowCount | 현재 rowCount | 상태 |
|-----|------------|--------------|------|
| 1.jpg | 28 | 28 | exact ✓ |
| 2.pdf | 13 | 13 | exact ✓ |
| 3.pdf | 1 | 1 | exact ✓ |
| 4.pdf | 1 | 1 | exact ✓ |
| 5.pdf | 6 | 6 | exact ✓ |
| 6.pdf | 6 | 6 | exact ✓ |
| 7.pdf | 1 | 1 | exact ✓ |

출처: T10_fix_template_colguides_header_skip_20260516.json (모두 exact 확인됨)

### T-25b 코드 변경 시 추가 검증 항목
1. 7개 샘플 RunOCR rowCount 전수 확인
2. Preview/Custom/Validation tableRows 표시 확인
3. History 상세 tableRows 렌더링 확인
4. warning 추가 후 영수증 관련 파서에 영향 없음 확인
5. `npm run typecheck` + `npm run build` (TypeScript 변경 시)
6. `py_compile` + `python scripts/verify_invoice_statement_full_quality_t8_final_precheck.py` (Python 변경 시)

---

## 9. 다음 작업 제안

### T-25b: warning-only 구현 (권장 우선순위 1)
- `_build_canonical_table_rows()`에 4개 warning 조건 추가
- row value 변경 없음
- 7개 rowCount exact 검증 포함
- 위험: low

### T-25c: red_pen_suppression debug variant
- HSV 마스킹 → 재OCR 결과 비교
- debug compare 리포트 생성
- 운영 적용 없음
- 위험: medium (격리 필요)

### T-25d: safe numeric cleanup (amount 공백 정리)
- amount 필드 comma-space regex 정리 구현
- 수학 검증 포함
- 7개 샘플 회귀 검증
- 위험: low

---

## 10. 최종 확인

| 확인 항목 | 결과 |
|---------|------|
| 사용 도구 | Claude Sonnet 4.6 (Claude Code) |
| 생성 리포트 | `docs/T25_invoice_1jpg_handwritten_overlay_tableRows_analysis_20260519.md` + `.json` |
| 코드 수정 여부 | **없음** |
| 1.jpg rowCount | **28/28 exact 유지** |
| 수기 오염 의심 cell | **8개** (엄격) + 2개 minor |
| 자동 보정 가능 여부 | **불가** (이번 작업에서) |
| warning-only 후보 | 4개 warning 키 (T-25b 구현 예정) |
| red_pen_suppression | debug-only 후보 (T-25c, 운영 미적용) |
| 기존 7개 거래명세서 회귀 위험 | **없음** (코드 미변경) |
