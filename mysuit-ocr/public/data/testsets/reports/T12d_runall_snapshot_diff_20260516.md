# T-12d RunAll snapshot before/after diff tool 결과

## 1. 생성/수정 파일

| 파일 | 내용 |
|---|---|
| `mysuit-ocr/scripts/diff-runall-snapshots.mjs` | 신규 생성 — diff tool 본체 |
| `mysuit-ocr/package.json` | `"diff:runall": "node scripts/diff-runall-snapshots.mjs"` 추가 |
| `mysuit-ocr/scripts/test-before.json` | 테스트용 임시 before snapshot |
| `mysuit-ocr/scripts/test-after.json` | 테스트용 임시 after snapshot |

## 2. 핵심 기능

- before/after 두 snapshot JSON을 로드하고 sample별/documentType별 변화량 집계
- 판정: `improved / regressed / mixed / unchanged / new / removed`
- regression 감지 시 exit code 1 반환 (CI/CD 연동 가능)
- 출력: JSON diff 파일 + Markdown diff 리포트

## 3. diff 입력/출력 구조

### 입력
T-12c에서 export한 snapshot JSON 2개 (구조 검증 포함)

### 출력 파일명
```
runall_diff_{testsetId}_{yyyyMMdd_HHmm}.json
runall_diff_{testsetId}_{yyyyMMdd_HHmm}.md
```

### JSON diff 구조
```json
{
  "generatedAt": "...",
  "before": { "file", "generatedAt", "testsetId" },
  "after":  { "file", "generatedAt", "testsetId" },
  "summary": {
    "totalSamplesBefore", "totalSamplesAfter",
    "samplesRunBefore", "samplesRunAfter",
    "improvedCount", "regressedCount", "mixedCount", "unchangedCount",
    "improvedSamples": [...],
    "regressedSamples": [...],
    "rowCountSummaryDelta": { "exact", "short", "over", "unknown" }
  },
  "documentTypeDiffs": [{ "documentType", "before", "after", "deltas", "missingFieldDiffs", "warningTypeDiffs", "verdict" }],
  "sampleDiffs":       [{ "filename", "verdict", "improvements", "regressions", "before", "after", "deltas", "changed" }],
  "missingFieldDiffs": { "documentType": [{ "key", "before", "after", "delta" }] },
  "warningDiffs":      { "documentType": [{ "key", "before", "after", "delta" }] }
}
```

### Markdown 리포트 섹션
1. 입력 파일 정보
2. 전체 요약 (totalSamples, samplesRun, improved/regressed/unchanged)
3. rowCount 집계 변화 (exact/short/over/unknown Δ, 방향 아이콘)
4. 개선 샘플 (improved) 목록 + 변화 항목
5. 회귀 샘플 (regressed) 목록 + 변화 항목
6. 혼재 샘플 (mixed) — 개선+회귀 동시
7. documentType별 변화 (rowExact Δ, rowShort Δ, warn Δ, missing Δ, 판정)
8. missing field 변화 (field별 before/after/delta)
9. warning 변화 (key:type별 before/after/delta)
10. sample별 상세 표 (변화 있는 샘플만)

## 4. 검증 결과 (샘플 데이터)

```
[diff-runall-snapshots]
  before : scripts/test-before.json
  after  : scripts/test-after.json
  output : C:\OCR\mysuit-ocr\scripts

=== Diff Summary ===
  Samples: 7 before / 7 after
  Improved : 2 (3.pdf, 5.pdf)
  Regressed: 0
  Unchanged: 5
  rowCount.exact  : +1
  rowCount.short  : -1

✓ JSON : ...runall_diff_invoice_statement_20260516_1425.json
✓ MD   : ...runall_diff_invoice_statement_20260516_1425.md
```

- `3.pdf` → missing 2→0 (개선)
- `5.pdf` → rowCount short→exact (개선)
- `invoice_statement` → rowExact +1, missing Δ합 -2, warning -1 (✓ 개선)

- typecheck: **passed**
- build: **passed** (46.3 kB 유지, 스크립트는 브라우저 번들 외)

## 5. 사용 방법

### 기본 사용
```bash
# RunAll 전 → JSON 저장 (UI 버튼)
# → ocr_runall_invoice_statement_20260516_0900.json

# OCR 로직 수정 후 RunAll → JSON 저장
# → ocr_runall_invoice_statement_20260516_1400.json

# diff 실행
node scripts/diff-runall-snapshots.mjs \
  ocr_runall_invoice_statement_before.json \
  ocr_runall_invoice_statement_after.json
```

### npm script
```bash
npm run diff:runall -- before.json after.json

# 출력 디렉터리 지정
npm run diff:runall -- before.json after.json public/data/testsets/reports/
```

### exit code
- `0`: 회귀 없음 (regressed = 0)
- `1`: 회귀 감지 (regressed > 0) → CI 파이프라인 연동 가능

### 오류 처리
- 파일 없음 → `[ERROR] Cannot read file: ...`
- JSON 파싱 실패 → `[ERROR] JSON parse failed: ...`
- samples 필드 없음 → `[ERROR] ... is missing 'samples' array. Is this a T-12c snapshot?`

## 6. 다음 작업 판단

**snapshot export + diff tool 완료 → before/after diff 워크플로우 가능**

실제 사용 시나리오:
1. 현재 7/7 exact 상태에서 "JSON 저장" → `before.json`
2. OCR 로직 수정 후 RunAll → "JSON 저장" → `after.json`
3. `npm run diff:runall -- before.json after.json` 실행
4. Markdown 리포트에서 개선/회귀 즉시 확인

후속 후보:
1. qualityTags × missing field 교차 집계 추가
2. diff 리포트를 `public/data/testsets/reports/`에 자동 저장하는 npm script wrapper
3. tax_invoice / transaction_statement 샘플 확장 + parser 분기
