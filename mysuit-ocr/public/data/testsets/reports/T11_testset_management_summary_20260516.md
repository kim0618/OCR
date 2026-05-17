# T-11 testset management / documentType grouping / qualityTags / summary aggregation 결과

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `mysuit-ocr/src/lib/testsets.ts` | Difficulty "extreme" 추가, DocumentType "tax_invoice"/"transaction_statement" 추가, ExpectedStatus 유니온 타입 추가 |
| `mysuit-ocr/src/lib/profiles.ts` | DOCUMENT_TYPE_PROFILE_MAP에 tax_invoice/transaction_statement 항목 추가 |
| `mysuit-ocr/src/lib/profiles_20260511_before_GT5.ts` | 동일 (백업 파일 정합성 유지) |
| `mysuit-ocr/src/lib/profiles_20260511_before_P2.ts` | 동일 (백업 파일 정합성 유지) |
| `mysuit-ocr/src/components/test/TestWorkspace.tsx` | receipt_generalization testset 추가, QualityTagSummarySection 렌더링, DocTypeSummaryRow tableRows 메트릭 필드 추가, 거래명세서 sub-table 개선 |
| `mysuit-ocr/public/data/testsets/new_samples/manifest.json` | 신규 생성 (9개 샘플) |

## 2. 백업 파일

- `mysuit-ocr/src/lib/testsets_20260516_before_T11.ts`
- `mysuit-ocr/src/components/test/TestWorkspace_20260516_before_T11.tsx`

## 3. 핵심 요약

- testsets.ts 타입 정리: Difficulty "extreme" 추가, DocumentType 2종 추가, ExpectedStatus 명시적 유니온 추가
- new_samples manifest.json 생성: 9개 샘플 (CORD×4, SROIE×3, express×1, funsd×1)
- TestWorkspace: receipt_generalization testset UI 노출, qualityTags 집계 렌더링 추가
- invoice_statement (거래명세서) 집계 표에 tableRows 메트릭 (rows有, warn) 컬럼 추가
- typecheck ✓ / build ✓

## 4. metadata 타입 정리

### testsets.ts 변경

| 타입 | 변경 전 | 변경 후 |
|---|---|---|
| `Difficulty` | `"easy" \| "medium" \| "hard"` | + `"extreme"` |
| `DocumentType` | 7종 | 9종 (`tax_invoice`, `transaction_statement` 추가) |
| `ExpectedStatus` | 없음 (string 직접 사용) | 명시적 유니온 타입 추가 |

### profiles.ts 변경

- `DOCUMENT_TYPE_PROFILE_MAP`에 `tax_invoice: { base: "document" }`, `transaction_statement: { base: "document" }` 추가
- 두 타입 모두 `document` profile base로 처리 (향후 parser 분기 기반)

## 5. documentType / qualityTags 정책

### 현재 사용 중인 documentType

| documentType | profile base | 현황 |
|---|---|---|
| card_receipt | receipt | baseline, baseline_fast, google, google_fast, receipt_generalization |
| pos_receipt | receipt | google, receipt_generalization, new_samples |
| food_cafe_receipt | receipt | google, google_fast, receipt_generalization |
| medical_receipt | receipt | baseline, google, receipt_generalization |
| finance_slip | finance | baseline, baseline_fast, google, receipt_generalization |
| invoice_statement | document | invoice_statement |
| unknown | none | google, new_samples |

### 신규 추가 documentType (테스트셋 샘플 없음, 향후 분기용)

- `tax_invoice`: 세금계산서 — invoice_statement와 유사하나 별도 parser 예정
- `transaction_statement`: 거래명세서 변형 — invoice_statement의 sub-type 후보

### qualityTags 현황 (전체 testset 기준)

| 태그 | 사용 testset |
|---|---|
| ocr_noise | baseline, baseline_fast, google |
| handwritten | baseline, baseline_fast, new_samples |
| small_text | google, receipt_generalization |
| long_receipt | receipt_generalization |
| skewed | receipt_generalization |
| shadow | receipt_generalization |
| low_contrast | receipt_generalization |
| blurred | receipt_generalization |
| rotated | receipt_generalization |
| ocr_garbled | invoice_statement |
| party_block_garbled | invoice_statement |
| address_garbled | invoice_statement |
| no_amount_summary | invoice_statement |
| lot_serial_table | invoice_statement |
| buyer_only_document | invoice_statement |
| optional_supplier | invoice_statement |
| address_tail_missing | invoice_statement |

## 6. UI grouping 변경

### TestWorkspace.tsx 변경 사항

1. **receipt_generalization testset 추가**
   - DEFAULT_TESTSETS에 추가 → UI 상단 testset 선택 버튼에 "영수증 신규 일반화셋" 노출

2. **QualityTagSummarySection 렌더링 추가**
   - 기존: 컴포넌트 정의만 있고 JSX에서 렌더링 안 됨
   - 변경 후: DocTypeSummarySection 다음에 qualityTags 집계 표 노출

3. **거래명세서 sub-table 개선 (T-11)**
   - 기존: documentType / total / selected / suppressed / not_run / 선택률 / [필드별 채움]
   - 변경 후: 위 + **rows有** (tableRows 반환 샘플 수) + **warn** (valueMappingWarnings 샘플 수)

## 7. summary aggregation 변경

### DocTypeSummaryRow 타입 확장

```typescript
type DocTypeSummaryRow = {
  // ... 기존 필드 유지 ...
  tableRowsWithData: number;     // T-11: tableRows를 반환한 샘플 수
  tableRowsWarningCount: number; // T-11: valueMappingWarnings가 있는 샘플 수
};
```

### 집계 로직 추가 (docTypeSummary useMemo)

- document profile 샘플에 대해 `tableMeta.rowCount > 0` 이면 `tableRowsWithData++`
- document profile 샘플에 대해 `tableMeta.valueMappingWarnings.length > 0` 이면 `tableRowsWarningCount++`

## 8. invoice_statement 영향 확인

- OCR 로직 수정 없음 (invoice_statement.py 미수정)
- 거래명세서 testset E2E 결과 7/7 exact 유지 (T-10-fix에서 이미 확인)
- tableMeta.rowCount, tableMeta.valueMappingWarnings 필드 읽기만 추가 (기존 응답 구조 변경 없음)

## 9. 검증 결과

- npm run typecheck: **passed** (0 errors)
- npm run build: **성공** (/test 43.8 kB)
- invoice_statement E2E 회귀: 없음 (OCR 로직 미수정)

## 10. 다음 작업 판단

**testset management 기반 완료 → 다른 문서 유형 확장 가능**

현재 상태:
- 6개 testset 모두 manifest.json 완비 (documentType / qualityTags / difficulty / expectedStatus)
- new_samples manifest.json 신규 생성
- UI: documentType 그룹 썸네일 / DocTypeSummary / QualityTagSummary 전체 렌더링
- 거래명세서: tableRows 메트릭 집계 추가

후속 작업 후보:
1. ground_truth.json에 expectedRowCount 추가 → rowCount exact 비교 집계 가능
2. tax_invoice / transaction_statement 실제 샘플 추가 및 parser 분기 구현
3. receipt_generalization ground_truth.json 보강
4. 필드별 실패율 집계 (fieldFilled 기반) UI 상세화
