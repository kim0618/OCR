# T-12c RunAll 결과 snapshot export 결과

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `mysuit-ocr/src/components/test/TestWorkspace.tsx` | `downloadFile` 유틸, `buildRunAllSnapshot` + `handleExportJson` + `handleExportMarkdown` (useCallback), export 버튼 JSX |

## 2. 핵심 요약

- 브라우저 다운로드 방식(Blob + anchor click)으로 JSON/MD export 구현
- RunAll 결과가 있으면 "JSON 저장" / "MD 저장" 버튼 표시
- snapshot JSON에 샘플별 상세 + documentType/qualityTag summary + missing/warning 집계 포함
- Markdown에 DocumentType 집계 표 + rowCount 집계 + Missing/Warning Top + 샘플별 표 포함
- typecheck ✓ / build ✓ (46.3 kB)

## 3. snapshot JSON 구조

```json
{
  "generatedAt": "2026-05-16T14:30:00.000Z",
  "testsetId": "invoice_statement",
  "testsetLabel": "거래명세서 1차 검증셋",
  "totalSamples": 7,
  "samplesRun": 7,
  "summary": {
    "documentTypeSummary": [
      {
        "documentType": "invoice_statement",
        "total": 7, "selected": 7, "suppressed": 0, "unknown": 0, "error": 0, "notRun": 0,
        "tableRowsWithData": 7,
        "tableRowsWarningCount": N,
        "rowExactCount": 7, "rowShortCount": 0, "rowOverCount": 0, "rowUnknownCount": 0,
        "missingFieldCounts": { "insuranceCode": 2, ... },
        "warningTypeCounts": { "insuranceCode:ocr_source_missing": 2, ... }
      }
    ],
    "qualityTagSummary": [...],
    "rowCountSummary": { "samplesWithExpected": 7, "exact": 7, "short": 0, "over": 0, "unknown": 0 },
    "missingFieldSummary": { "invoice_statement": { "insuranceCode": 2 } },
    "warningSummary": { "invoice_statement": { "insuranceCode:ocr_source_missing": 2 } }
  },
  "samples": [
    {
      "filename": "1.jpg",
      "documentType": "invoice_statement",
      "qualityTags": [],
      "difficulty": "easy",
      "expectedStatus": "selected",
      "run": true,
      "status": "selected",
      "docType": "invoice_statement",
      "extractionSource": "template_colguides_expected_columns",
      "tableBoundsUsed": true,
      "columnGuidesUsed": true,
      "columnGuidesCount": 5,
      "actualRowCount": 28,
      "expectedRowCount": 28,
      "rowCountStatus": "exact",
      "firstRowPreview": "...",
      "valueMappingWarnings": [],
      "missingFields": [],
      "notes": "..."
    }
  ]
}
```

## 4. UI 변경

### 버튼 위치

`qualityTagSummary` 표 다음, `Batch summary` 섹션 이전에 우측 정렬로 배치:

```
[결과 내보내기:] [JSON 저장] [MD 저장]
```

- **JSON 저장** (보라계열): `ocr_runall_{testsetId}_{yyyyMMdd_HHmm}.json` 다운로드
- **MD 저장** (회색): `ocr_runall_{testsetId}_{yyyyMMdd_HHmm}.md` 다운로드
- 버튼은 `batchRows.length > 0 || documentBatchRows.length > 0` 일 때만 표시

### 추가된 함수

| 함수 | 위치 | 역할 |
|---|---|---|
| `downloadFile(content, filename, mimeType)` | 모듈 레벨 | Blob 기반 파일 다운로드 |
| `buildRunAllSnapshot` | useCallback | 현재 실행 결과 → snapshot 객체 |
| `handleExportJson` | useCallback | snapshot → JSON 다운로드 |
| `handleExportMarkdown` | useCallback | snapshot → Markdown 다운로드 |

## 5. 포함 summary

### JSON snapshot

| 필드 | 설명 |
|---|---|
| `generatedAt` | ISO timestamp |
| `testsetId` / `testsetLabel` | 현재 testset |
| `totalSamples` / `samplesRun` | 전체/실행된 샘플 수 |
| `summary.documentTypeSummary` | T-11/T-12a/T-12b 집계 전체 |
| `summary.qualityTagSummary` | qualityTags별 집계 |
| `summary.rowCountSummary` | exact/short/over/unknown count |
| `summary.missingFieldSummary` | documentType별 field missing count |
| `summary.warningSummary` | documentType별 warning type count |
| `samples[].rowCountStatus` | exact/short/over/unknown 판정 |
| `samples[].missingFields` | 이 샘플에서 missing된 required columns |
| `samples[].valueMappingWarnings` | 이 샘플의 warning 문자열 배열 |

### Markdown export

1. DocumentType 집계 표 (total/selected/suppressed/not_run/rows有/exact/short/over)
2. rowCount 집계 요약
3. Missing Fields Top (documentType별)
4. Warning Types Top (documentType별)
5. 샘플별 결과 표 (filename/documentType/status/rowCount/expectedRow/rowCountStatus)

## 6. 검증 결과

- typecheck: **passed** (0 errors)
- build: **passed** (/test 46.3 kB)
- OCR 로직 미수정 → 기존 T-10~T-12b 회귀 없음

## 7. 한계 및 후속

- **Markdown export**: 구현 완료 (간결한 summary 형태)
- **서버 저장**: 구현하지 않음 (브라우저 다운로드로 충분; 서버 저장은 API endpoint 추가 필요)
- **before/after diff**: snapshot을 두 파일 로드하여 비교하는 diff 뷰어는 별도 UI 작업 필요
- **raw OCR 전체 포함 옵션**: 현재는 요약 중심; full raw는 optional로 분리 가능

## 8. 다음 작업 판단

**snapshot export 완료 → before/after diff 기능 가능**

현재 사용 가능한 워크플로우:
1. OCR 개선 전 RunAll → JSON 저장 → `ocr_runall_invoice_before.json`
2. OCR 개선 후 RunAll → JSON 저장 → `ocr_runall_invoice_after.json`
3. 두 파일 비교로 rowCount/missing/warning 변화량 파악 가능

후속 후보:
1. before/after JSON diff viewer (간단한 compare 페이지 또는 스크립트)
2. qualityTags × missing field 교차 집계
3. tax_invoice / transaction_statement 샘플 확장 및 parser 분기
