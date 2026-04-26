# SESSION SUMMARY

## Current Status

### Baseline Lock — 완료

- Lock document: docs/BASELINE_LOCK_20260425.md
- Baseline OCR score: 43/57
- Baseline final selected value score: 52/57
- Business number: 9/9
- Total amount: 8/10
- selected: 8
- suppression: 2
- unknown: 0

Core regression criteria (변경 시 반드시 확인):

- 1.jpg total amount = 10,560
- 4.jpg total amount = 17,600
- 10.jpg status = selected / total amount = 19,250
- 9.jpg = suppressed_bank_slip
- a2.jpg = suppressed_handwritten

### Google Lock — 완료

- Lock document: docs/GOOGLE_LOCK_20260425.md
- Google total: 11
- selected: 10
- suppression: 1
- unknown: 0
- error: 0

Key locked results:

- 7.jpg = receipt_pos / selected
- 7.jpg company: GS25성신로데오점
- 7.jpg amount: 7,650
- 7.jpg phone: 02-927-2369
- 6.jpg = suppressed_bank_slip
- 11.jpg phone/address improvement retained
- 8.jpg company false positive removed
- 10.jpg address remains blank due to raw absence

---

## Testset Management Stage 1 — 완료

### manifest.json 추가

- mysuit-ocr/public/data/testsets/baseline/manifest.json
- mysuit-ocr/public/data/testsets/baseline_fast/manifest.json
- mysuit-ocr/public/data/testsets/google/manifest.json
- mysuit-ocr/public/data/testsets/google_fast/manifest.json

각 manifest에 포함된 항목:

- datasetId / datasetRole / status / lockDoc / description
- items[]: filename / documentType / qualityTags / difficulty / expectedStatus / notes

### TypeScript 타입 추가

- src/lib/testsets.ts: DocumentType, QualityTag, Difficulty, DatasetRole, DatasetStatus, ManifestItem, DatasetManifest

### TestWorkspace UI — 전체 완료

**1차 UI (manifest 연동):**

- manifest metadata non-blocking fetch / fallback 처리
- 썸네일 documentType 배지 (한글 짧은 라벨: 카드/POS/음식/금융/약국/거래/기타)
- 썸네일 documentType 기준 그룹화 (manifest 있을 때)
- ManifestMetaBadges 우측 패널 "문서 정보" 영역
- documentType별 summary 집계 뷰 (details 접이식)
- qualityTags 필터 UI (OR 조건, 썸네일 전용, 한글 라벨)
- qualityTags별 summary 집계 뷰 (details 접이식)
- dataset 탭에 datasetRole / status 배지 (한글)

**2차 UI (한글화 + 레이아웃 개선):**

- documentType / qualityTags / difficulty / expectedStatus / datasetRole / datasetStatus 전체 한글 표시
- 썸네일 배지 한글 짧은 라벨 (C→카드, P→POS, F→음식 등)
- 썸네일 그룹 헤더 한글 전체명 + 영문 코드 tooltip
- 우측 META 영역 "문서 정보" 한글화 (정상 선택 / 정상 억제 / 미분류)
- documentType summary / qualityTags summary 표 첫 열 한글 표시
- 문서 유형/태그 안내 범례 (details 접이식)
- KPI 3카드 레이아웃 조밀화
- 전체 결과 요약 접기/펼치기 (기본 펼침, 헤더 클릭 토글)

**검증:**

- npm run typecheck 통과
- npm run build 통과
- Run OCR / Run All / dataset 전환 / qualityTags filter 동작 영향 없음

---

## main.py Refactoring Stage 1 (R1 + R2 최소) — 완료

계획 문서: docs/REFACTOR_PLAN_20260426.md
완료 선언 문서: docs/REFACTOR_MINIMAL_COMMON_READY_20260426.md

### 완료된 Phase

| Phase | 모듈 | 이동 내용 |
|---|---|---|
| R1-a | utils/text_normalize.py | _clean_number, _clean_inline_field_value |
| R1-b | utils/regex_patterns.py | 19개 정규식 상수 |
| R1-c | utils/rows.py | _group_rows, _row_text, _single_line_rows, _is_merchant_notice_row |
| R1-d | utils/io_json.py | _load_json, _save_json |
| R2-a | extractors/common.py | _bad_top_text_candidate, _extract_until_next_label |
| R2-b | extractors/business_number.py | _validate_biz_number, _extract_biz_number |
| R2-c | extractors/phone.py | _normalize_phone_digits, _format_phone_digits, _valid_phone_digits, _valid_labeled_phone_digits, _extract_phone_candidate |

main.py 라인 수: 2450 → 2234 (-216줄)

회귀 검증: baseline_fast / google / baseline ALL PASS (사업자번호 9/9, 전화번호 8/8, google lock 전체 유지)

### 보류된 Refactoring Phase

거래명세서 진입 및 향후 일정과 독립적으로 진행 가능:

- R2-d: extractors/representative.py
- R2-e: extractors/address.py
- R2-f: extractors/company.py
- R2-g: extractors/fields_pipeline.py
- R3: pipeline/ (image/OCR/bbox)
- R4: policies/ (amount/suppression)
- R5: pipeline/response_builder.py
- R6: routes/

---

## Current Next Stage

**다음 작업: 영수증 신규 일반화셋 계획 문서 작성**

거래명세서로 넘어가기 전, 영수증 계열 일반화셋을 먼저 보강한다.

작성할 문서: `docs/RECEIPT_GENERALIZATION_TESTSET_PLAN_20260426.md`

목표:
1. receipt_generalization dataset 계획
2. 15~30장 신규 샘플 수집 기준 정의
3. documentType / qualityTags / expectedStatus 기준 정의
4. 최초 실행은 코드 수정 없이 initial validation만 수행

이후 순서:
- 신규 일반화셋 준비 완료 → initial validation
- 거래명세서 schema/field profile 문서 작성
- 거래명세서 샘플셋 준비 + manifest 작성
- parser 구현 (스키마/샘플 확정 후)

## Not Started / Frozen

- OCR 인식 로직 개선: 구조 정리 완료 후까지 중단
- 거래명세서 parser 구현: 스키마/샘플 확정 전 금지
- main.py R2-d~R6 리팩토링: 독립적으로 진행 예정
- validation 결과 JSON: 수정하지 않음
- baseline/google lock 문서: 유지. 변경 금지

## Important Direction

This OCR project should not overfit to a single vendor or sample set.

Goal:

- Compare with other OCR products
- Improve recognition as samples accumulate
- Support multiple document types
- Use baseline as regression safety
- Use google as real-world generalization validation
