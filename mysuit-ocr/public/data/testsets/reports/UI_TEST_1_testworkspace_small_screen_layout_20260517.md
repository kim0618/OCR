# UI-TEST-1 완료 보고

## 1. 수정 파일

- `mysuit-ocr/src/components/test/TestWorkspace.tsx`

백업:
- `mysuit-ocr/src/components/test/TestWorkspace_20260517_before_UI1.tsx`

## 2. 핵심 요약

TestWorkspace UI 레이아웃을 작은 화면에서도 가독성이 좋도록 개선했다.
총 6가지 변경 지점에서 OCR/parser/classifier 로직은 일절 수정하지 않았다.

## 3. 개선 내용

### 작업 1: 상단 샘플 썸네일 영역 접기/펼치기

- `showThumbnails` state 추가 (기본값: `false` — 기본 접힘)
- topBar에 "▶ 샘플 (N)" / "▼ 접기" 토글 버튼 추가
- 썸네일 strip은 펼침 상태에서만 표시
- Run OCR / Run All / 모드 스위처 / 체크박스는 항상 표시
- topBar style: `overflow: "hidden"` → `flexWrap: "wrap"` 변경

### 작업 2: 요약 카드 반응형 grid

- `KpiSection` 컴포넌트 wrapper의 `flex: "1 1 0"`, `minWidth: 0` →
  `flex: "1 1 240px"`, `minWidth: "min(100%, 240px)"` 로 변경
- 화면 폭에 따라 4열 → 2열 → 1열로 자연스럽게 wrapping 됨
- `kpiWrapper`의 `flexWrap: "wrap"` 기존 설정과 함께 동작

### 작업 3: documentType/qualityTags 집계 기본 접힘

- `DocTypeSummarySection`과 `QualityTagSummarySection` 모두 기존에 `<details>` 를 사용하고 있어 `open` 속성 없이 기본 접힘 상태로 동작 중
- 별도 수정 불필요 (이미 올바른 동작)

### 작업 4/5: 이미지 패널 토글 (상세 패널 compact화)

- `showImagePanel` state 추가 (기본값: `true`)
- 결과 테이블과 상세 패널 사이에 "이미지 숨기기 / 이미지 보이기" 토글 버튼 추가
- 이미지 패널을 숨기면 비교 패널이 전체 너비를 차지함
- 선택된 샘플이 있을 때만 버튼 표시

### 작업 6: 결과 테이블 높이/스크롤 정리

- `batchBox.maxHeight`: 220 → 320 으로 증가 (더 많은 행 표시)
- `th` 스타일에 `position: "sticky"`, `top: 0`, `background: "var(--panel)"`, `zIndex: 1` 추가
- 테이블 스크롤 시 헤더가 고정되어 가독성 향상

## 4. 작은 화면 개선 포인트

| 문제 | 해결 방법 |
|------|-----------|
| 썸네일 strip이 화면 높이를 과점 | 기본 접힘, 토글로 선택적 표시 |
| KPI 카드가 가로로 압축됨 | minWidth: 240px 설정으로 자연스러운 줄바꿈 |
| 이미지 + 필드 패널이 동시에 눌림 | 이미지 패널 토글로 선택적 숨김 |
| 테이블 헤더가 스크롤 시 사라짐 | sticky header 적용 |
| 테이블이 너무 작게 잘림 | maxHeight 220 → 320 증가 |

## 5. 유지된 기능

- Run OCR / Run All 버튼 — 항상 접근 가능
- 전처리 Debug / 자동 보정 체크박스 — 항상 표시
- 모드 스위처 (compare/ocr_only/autofill/gt_edit) — 항상 표시
- documentType 집계 / qualityTags 집계 — `<details>` 기본 접힘 유지
- 결과 테이블 배치 요약 접기/펼치기 — 유지
- 자동복원 배지 / commitBtn — 유지
- FieldCard / FinanceDetailPanel / DocumentDetailPanel — 유지
- PreprocessingDebugPanel / DebugPanel / OCR text — 유지
- 전체 채택값 기준값 확정 버튼 — 유지
- Export JSON / MD — 유지

## 6. 검증 결과

```
npm run typecheck → 통과 (에러 없음)
npm run build     → 통과 (빌드 성공, /test 페이지 47.6 kB)
```

## 7. 다음 작업 판단

UI-TEST-1 완료. 다음 작업은 추가 요구사항에 따라 판단:

- 작업 5 심화: 필드/OCR·디버그 탭 분리가 필요하면 별도 UI-TEST-2로 진행
- 현재 구조에서 이미지 숨기기 + 디버그 `<details>` 접힘으로 충분히 compact함
- OCR 로직 / manifest 데이터 미수정 확인
