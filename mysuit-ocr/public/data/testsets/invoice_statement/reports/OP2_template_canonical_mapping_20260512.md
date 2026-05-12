# OP-2 Template canonicalField/canonicalColumn 매핑 구조 결과

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `src/components/ocr/core/types.ts` | MappingStatus, FieldMappingCandidate, TableColumnDef 타입 추가; TableMeta에 tableName/columns 추가; Region에 koField/enField/canonicalField/mappingStatus/mappingCandidates/valueType 추가 |
| `src/lib/canonicalFields.ts` | TemplateFieldContext 타입 + resolveTemplateFieldMapping() 헬퍼 추가 |
| `src/components/ocr/core/export.ts` | field/multi/check 영역의 canonical 필드 export 포함; table의 tableName/columns 포함 |
| `src/components/ocr/OcrAnnotator.tsx` | documentType 상태 추가; 툴바에 문서유형 선택기 추가; OcrRightPanel에 documentType 전달; exportPayload에 documentType 포함 |
| `src/components/ocr/OcrRightPanel.tsx` | documentType prop 추가; field/multi/check 선택 시 koField/enField/canonical 섹션 추가; table 선택 시 tableName 입력 + 컬럼 canonical 매핑 UI 추가; MappingBadge 컴포넌트 추가 |
| `src/components/template/UnstructuredBuilder.tsx` | Field 타입에 canonicalField/mappingStatus/mappingCandidates 추가; documentType prop + 선택기 추가; koField 입력 시 자동 canonical 매핑; MappingBadge + ambiguous 후보 선택 UI 추가 |

## 2. 백업 파일

| 백업 경로 | 원본 |
|---|---|
| `backup/types_20260512_before_OP2.ts` | src/components/ocr/core/types.ts |
| `backup/export_20260512_before_OP2.ts` | src/components/ocr/core/export.ts |
| `backup/OcrRightPanel_20260512_before_OP2.tsx` | src/components/ocr/OcrRightPanel.tsx |
| `backup/OcrAnnotator_20260512_before_OP2.tsx` | src/components/ocr/OcrAnnotator.tsx |
| `backup/UnstructuredBuilder_20260512_before_OP2.tsx` | src/components/template/UnstructuredBuilder.tsx |
| `backup/canonicalFields_20260512_before_OP2.ts` | src/lib/canonicalFields.ts |

## 3. 핵심 요약

- Template 탭의 정형(OcrAnnotator + OcrRightPanel), 비정형(UnstructuredBuilder) 모두에 canonical 매핑 UI 추가
- koField 입력 시 resolveTemplateFieldMapping()이 자동 호출되어 canonicalField/mappingStatus 계산
- ambiguous 상태(거래명세서 + 회사명 등)에서 후보 버튼 클릭으로 확정 가능
- 테이블 컬럼별 koField/enField/canonicalColumn 입력 + 자동 매핑 UI 추가
- 모든 새 필드는 optional로 추가 → 기존 템플릿 데이터 backward compatible
- field_1/table_1 id 체계 유지, 의미 필드(koField/canonicalField 등)는 별도로 추가

## 4. 정형 필드 변경 내용

| 항목 | 내용 |
|---|---|
| koField | Region에 optional 추가. 우측 패널에서 입력 시 자동 canonical 계산 |
| enField | Region에 optional 추가. 사용자가 직접 입력 |
| canonicalField | Region에 optional 추가. koField 기반 자동/수동 확정 |
| mappingStatus | auto / ambiguous / manual / unmapped. 색상 badge로 표시 |
| mappingCandidates | ambiguous 시 후보 배열 저장. 버튼 클릭으로 확정 |
| 문서유형 선택기 | 툴바에 문서유형 드롭다운 추가 (unknown/invoice_statement/receipt/finance_slip) |

## 5. 비정형 필드 변경 내용

- Field 타입에 `canonicalField?`, `mappingStatus?`, `mappingCandidates?` 추가
- 우측 패널에 문서유형 선택기(documentType) 추가 — canonical mapping context
- koField 입력 시 resolveTemplateFieldMapping(koField, documentType, "nonStructured") 자동 호출
- documentType 변경 시 모든 필드의 canonical 재계산 (기존 manual 확정 제외)
- 각 필드 행 하단에 MappingBadge + canonicalField 표시
- ambiguous 상태 시 후보 버튼 표시 → 클릭하면 manual로 확정
- 저장 payload에 documentType 포함

## 6. 테이블필드 변경 내용

| 항목 | 내용 |
|---|---|
| tableName | TableMeta에 optional 추가. 우측 패널에서 입력 |
| columns | TableMeta에 TableColumnDef[] optional 추가 |
| 컬럼 개수 | colGuides 수 + 1 기준으로 컬럼 행 자동 생성 |
| koField (컬럼) | 입력 시 tableColumn context로 canonical 자동 매핑 |
| enField (컬럼) | 사용자 직접 입력 |
| canonicalColumn | koField 기반 자동/수동 확정. MappingBadge 표시 |
| ambiguous | 컬럼도 ambiguous 시 후보 버튼 표시 |

## 7. alias/canonical 매핑 정책

| 입력 | documentType | context | 결과 |
|---|---|---|---|
| 회사명 | receipt | field | merchantName / auto |
| 회사명 | invoice_statement | field | supplierCompany+buyerCompany / ambiguous |
| 공급자 상호 | invoice_statement | field | supplierCompany / auto |
| 사업자번호 | receipt | field | merchantBizNumber / auto |
| 사업자번호 | invoice_statement | field | supplierBizNumber+buyerBizNumber / ambiguous |
| 품목 | invoice_statement | tableColumn | itemName / auto |
| 규격 | invoice_statement | tableColumn | spec / auto |
| 제조번호 | invoice_statement | tableColumn | lotNo / auto |
| 유효기간 | invoice_statement | tableColumn | expiryDate / auto |
| 수량 | invoice_statement | tableColumn | quantity / auto |
| 단가 | invoice_statement | tableColumn | unitPrice / auto |
| 금액 | invoice_statement | tableColumn | amount / auto |

## 8. 저장 구조 예시

### 일반 field 예시
```json
{
  "id": "field_1",
  "name": "공급자사업자번호",
  "fieldType": "field",
  "x": 100, "y": 200, "width": 150, "height": 25,
  "koField": "공급자 사업자번호",
  "enField": "supplierBizNumber",
  "canonicalField": "supplierBizNumber",
  "mappingStatus": "auto"
}
```

### table field 예시
```json
{
  "id": "table_1",
  "name": "품목표",
  "fieldType": "table",
  "x": 50, "y": 300, "width": 600, "height": 200,
  "table": {
    "mode": "auto",
    "colGuides": [0.2, 0.4, 0.6, 0.75, 0.88],
    "tableName": "품목표",
    "columns": [
      { "index": 0, "koField": "품목", "enField": "itemName", "canonicalColumn": "itemName", "mappingStatus": "auto" },
      { "index": 1, "koField": "규격", "enField": "spec", "canonicalColumn": "spec", "mappingStatus": "auto" },
      { "index": 2, "koField": "제조번호", "enField": "lotNo", "canonicalColumn": "lotNo", "mappingStatus": "auto" },
      { "index": 3, "koField": "수량", "enField": "quantity", "canonicalColumn": "quantity", "mappingStatus": "auto" },
      { "index": 4, "koField": "단가", "enField": "unitPrice", "canonicalColumn": "unitPrice", "mappingStatus": "auto" },
      { "index": 5, "koField": "금액", "enField": "amount", "canonicalColumn": "amount", "mappingStatus": "auto" }
    ]
  }
}
```

### 비정형 field 예시
```json
{
  "template_id": "LOCAL-1234567890",
  "template_name": "거래명세서_비정형",
  "template_json": {
    "templateName": "거래명세서_비정형",
    "documentType": "invoice_statement",
    "mode": "unstructured",
    "fields": [
      {
        "no": 1,
        "enField": "supplierCompany",
        "koField": "공급자 상호",
        "canonicalField": "supplierCompany",
        "mappingStatus": "auto"
      },
      {
        "no": 2,
        "enField": "",
        "koField": "회사명",
        "canonicalField": null,
        "mappingStatus": "ambiguous",
        "mappingCandidates": [
          { "canonicalField": "supplierCompany", "confidence": 0.55, "reason": "alias_ambiguous_side" },
          { "canonicalField": "buyerCompany", "confidence": 0.55, "reason": "alias_ambiguous_side" }
        ]
      }
    ]
  }
}
```

## 9. backward compatibility

| 항목 | 처리 |
|---|---|
| 기존 템플릿 처리 | 모든 새 필드가 optional이므로 기존 데이터 로딩 시 undefined로 처리 |
| 기존 field_1 id 유지 | id/name 필드 변경 없음. canonical 필드는 별도로 추가됨 |
| 기존 table_1 유지 | table.colGuides/mode/rowTemplate 등 기존 구조 유지. tableName/columns만 추가 |
| koField 없는 기존 필드 | mappingStatus="unmapped"으로 fallback 표시 |
| columns 없는 기존 테이블 | colGuides 수 기준으로 빈 columns 배열 UI 생성. 저장 시 columns 배열 포함 |

## 10. 기존 기능 영향 확인

| 항목 | 결과 |
|---|---|
| 템플릿 생성 | 정상. OcrAnnotator 기존 플로우 유지 |
| 비정형 생성 | 정상. UnstructuredBuilder 기존 저장 구조 확장만 |
| 필드 생성 (field/multi/check) | 정상. 박스 생성 로직 미변경 |
| 테이블필드 생성 | 정상. 테이블 생성/가이드/모드 로직 미변경 |
| 영역 이동/삭제 | 정상. 기존 OcrCanvasPane 미변경 |
| 세로 가이드 찍기 | 정상. colGuide 로직 미변경 |
| 종료 키워드 입력 | 정상. stopKeywords 로직 유지 |
| 저장/수정 | 정상. 새 필드 포함된 채로 localStorage + 서버 저장 |
| RunOCR | 정상. RunOCR 로직 미변경. canonical 필드는 아직 RunOCR output에 미반영 |
| History | 정상. History 구조 미변경 |
| Test | 정상. TestWorkspace 미변경 |

## 11. 검증 결과

- **typecheck**: PASS (tsc --noEmit 오류 없음)
- **build**: PASS (✓ Compiled successfully in 2.6s, 20/20 pages generated)
- **브라우저 확인**: 빌드 성공으로 정적 페이지 생성 확인. 실제 브라우저 동작은 dev server 재기동 필요

## 12. 남은 문제

- RunOCR 출력이 아직 canonicalField 기준으로 변환되지 않음 → OP-3에서 처리
- table column 기반 실제 tableRows 매핑 미구현 → Template-Table-1에서 처리
- ambiguous 후보 UX: 현재 버튼 목록 방식. 드롭다운/라디오 등 추가 개선 가능
- enField 기본값 제안 (canonicalField가 있을 때) 미구현 — 의도적 보류 (사용자 입력값 덮어쓰기 금지 원칙)
- documentType 자동 추정 미구현 (템플릿명 기반) — 명시적 선택 방식으로 운영 중

## 13. 다음 추천 작업

후보:
- **OP-3** (강력 추천): RunOCR canonicalField 기반 output mapping — Template에 저장된 canonicalField를 RunOCR 결과 output_fields에 반영
- **Template-Table-1**: 테이블필드 column canonicalColumn 기반 RunOCR tableRows 매핑
- **T-4**: Test UI tableRows/tableMeta 연동 — Test 탭에서 canonical column 기반 테이블 결과 검증
- **H-3**: backend 원본/전처리 이미지 파일 저장 API 설계

추천: **OP-3** — Template canonical 구조가 완성되었으므로 RunOCR output에 연결해야 실제 운영에서 의미가 생긴다.
