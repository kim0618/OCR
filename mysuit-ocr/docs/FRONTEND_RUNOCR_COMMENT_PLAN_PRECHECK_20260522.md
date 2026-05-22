# FRONTEND RUNOCR COMMENT PLAN PRECHECK 20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_RUNOCR_COMMENT_PLAN_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 주석 추가: 없음
- 파일 이동/import 수정/리팩토링/fixture 수정: 없음

## 3. 생성 파일
- `tmp/codex_frontend_runocr_comment_plan_precheck.py`
- `docs/FRONTEND_RUNOCR_COMMENT_PLAN_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_COMMENT_PLAN_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_COMMENT_PLAN_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/runocr/ui/RunOcrResultLayout.tsx`
- `src/components/runocr/ui/OcrResultPanel.tsx`
- `src/components/runocr/ui/OcrDocViewer.tsx`
- `src/components/runocr/ui/CornerAdjust.tsx`
- `src/components/runocr/utils/buildOcrFormData.ts`
- `src/components/runocr/utils/runOcrRequest.ts`
- `src/components/runocr/utils/mapOcrResponse.ts`

## 5. RunOCR 파일별 역할 요약
| path | lines | role | responsibility |
| --- | ---: | --- | --- |
| `src/components/runocr/RunOcrWorkspace.tsx` | 1496 | RunOCR 탭 최상위 workspace | 파일/템플릿/모델 상태, OCR 실행 흐름, history/autofill orchestration, viewer/result 조립을 담당한다. |
| `src/components/runocr/ui/RunOcrResultLayout.tsx` | 40 | RunOCR 결과 화면 layout 전용 presentational component | viewer/resultPanel/scanOverlay/hiddenFileInput node를 배치한다. |
| `src/components/runocr/ui/OcrResultPanel.tsx` | 1660 | OCR 결과 표시 패널 | Preview, Custom, Validation, Clean JSON, Markdown, Raw JSON tab을 렌더링한다. |
| `src/components/runocr/ui/OcrDocViewer.tsx` | 224 | OCR 대상 문서 viewer | 이미지/PDF 렌더링 결과 위에 OCR field overlay를 표시하고 선택 상태를 연결한다. |
| `src/components/runocr/ui/CornerAdjust.tsx` | 174 | 문서 코너 보정 UI | 이미지 위 normalized corner point를 표시/드래그하여 코너 보정 입력을 만든다. |
| `src/components/runocr/utils/buildOcrFormData.ts` | 25 | OCR 요청 FormData 구성 helper | /ocr/extract 요청에 필요한 multipart FormData key를 만든다. |
| `src/components/runocr/utils/runOcrRequest.ts` | 25 | OCR API request helper | endpoint 결정, buildOcrFormData 호출, fetch, !ok 처리, json parsing을 담당한다. |
| `src/components/runocr/utils/mapOcrResponse.ts` | 120 | raw OCR response to OcrResult mapper | backend raw response를 OcrResultPanel이 소비하는 OcrResult 구조로 변환한다. |

## 6. 파일 최상단 주석 초안
### `src/components/runocr/RunOcrWorkspace.tsx`
```ts
/**
 * RunOCR 탭의 최상위 orchestration 컴포넌트입니다. 파일/템플릿/모델 상태와 OCR 실행 흐름을 관리하고, 요청 구성/API 호출/응답 매핑/결과 레이아웃의 세부 구현은 runocr utils/ui 파일에 위임합니다. 이 파일을 수정할 때는 history/autofill 저장 순서와 결과 state 반영 순서를 함께 확인해야 합니다.
 */
```

### `src/components/runocr/ui/RunOcrResultLayout.tsx`
```ts
/**
 * RunOCR 결과 화면의 배치만 담당하는 presentational layout입니다. viewer/resultPanel/scanOverlay/hiddenFileInput을 React node로 받아 배치하며, OCR 상태나 API 흐름을 직접 알지 않도록 유지합니다.
 */
```

### `src/components/runocr/ui/OcrResultPanel.tsx`
```ts
/**
 * OCR 결과 패널입니다. Preview/Custom/Validation/Clean JSON/Markdown/Raw JSON 표시를 담당하며, JSON/Markdown/table view model 생성은 전용 helper 계약을 통해 수행합니다. tab별 표시 정책을 바꿀 때는 관련 fixture runner를 함께 확인해야 합니다.
 */
```

### `src/components/runocr/ui/OcrDocViewer.tsx`
```ts
/**
 * RunOCR 문서 viewer입니다. OCR 대상 이미지/PDF 렌더링 결과와 field bbox overlay를 표시하고 선택 이벤트를 workspace로 전달합니다. 원본 이미지 크기와 화면 scale 계산이 overlay 정합성에 영향을 줍니다.
 */
```

### `src/components/runocr/ui/CornerAdjust.tsx`
```ts
/**
 * 문서 코너 보정용 UI입니다. 이미지 위의 normalized corner 좌표를 표시하고 드래그 결과를 상위 컴포넌트에 전달합니다. 좌표는 0~1 비율 기준이므로 pixel 좌표와 혼동하지 않도록 주의합니다.
 */
```

### `src/components/runocr/utils/buildOcrFormData.ts`
```ts
/**
 * /ocr/extract 요청의 FormData를 구성하는 helper입니다. backend가 기대하는 key와 append 순서를 보존하는 것이 목적이며, API 호출이나 response 처리는 runOcrRequest에서 담당합니다.
 */
```

### `src/components/runocr/utils/runOcrRequest.ts`
```ts
/**
 * RunOCR API 호출 helper입니다. endpoint 결정, FormData 구성, fetch, 응답 ok/json 처리까지만 담당하고 UI state나 history/autofill/mapping에는 관여하지 않습니다.
 */
```

### `src/components/runocr/utils/mapOcrResponse.ts`
```ts
/**
 * backend raw OCR response를 OcrResultPanel용 OcrResult로 변환하는 순수 mapper입니다. history/autofill/restore나 React state에 의존하지 않아야 하며, field key normalization은 options로 주입받습니다.
 */
```

## 7. JSDoc 필요 대상
| file | symbol | kind | line | reason |
| --- | --- | --- | ---: | --- |
| `src/components/runocr/RunOcrWorkspace.tsx` | `unionSourceBoxes` | function | 70 | 여러 OCR source box를 하나의 overlay box로 합치는 좌표 helper다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `RunOcrWorkspace` | component | 114 | RunOCR 화면 전체 흐름의 owner를 설명한다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `handlePersistEdits` | const/helper | 1078 | 편집 결과를 history run에 반영하는 경로다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `handleResultClose` | const/helper | 1099 | 결과 화면에서 초기 화면으로 돌아갈 때 초기화되는 state 범위를 설명한다. |
| `src/components/runocr/ui/RunOcrResultLayout.tsx` | `RunOcrResultLayoutProps` | type | 10 | exported public boundary라 파일을 여는 유지보수자에게 책임을 알려야 한다. |
| `src/components/runocr/ui/RunOcrResultLayout.tsx` | `RunOcrResultLayout` | component | 17 | node composition layout 원칙을 설명한다. |
| `src/components/runocr/ui/OcrResultPanel.tsx` | `OcrResultPanel` | component | 225 | tab별 결과 표시 패널의 책임과 fixture runner 영향 범위를 설명한다. |
| `src/components/runocr/ui/OcrDocViewer.tsx` | `OcrDocViewer` | component | 20 | scale/overlay 좌표 계산과 선택 이벤트 전달 역할을 설명한다. |
| `src/components/runocr/ui/OcrDocViewer.tsx` | `updateScale` | callback | 87 | viewer overlay 정합성에 영향을 주는 scale 측정 helper다. |
| `src/components/runocr/ui/CornerAdjust.tsx` | `CornerAdjust` | component | 17 | normalized corner coordinate interaction을 설명한다. |
| `src/components/runocr/ui/CornerAdjust.tsx` | `onImgClick` | callback | 44 | corner point 추가 방식과 normalized coordinate 변환을 설명한다. |
| `src/components/runocr/ui/CornerAdjust.tsx` | `onPointerMove` | callback | 61 | drag 중 normalized coordinate update를 설명한다. |
| `src/components/runocr/utils/buildOcrFormData.ts` | `BuildOcrFormDataInput` | type | 3 | exported public boundary라 파일을 여는 유지보수자에게 책임을 알려야 한다. |
| `src/components/runocr/utils/buildOcrFormData.ts` | `buildOcrFormData` | function | 13 | backend multipart key 계약과 FormData key parity 검증 대상이다. |
| `src/components/runocr/utils/runOcrRequest.ts` | `RunOcrRequestInput` | type | 3 | exported public boundary라 파일을 여는 유지보수자에게 책임을 알려야 한다. |
| `src/components/runocr/utils/runOcrRequest.ts` | `runOcrRequest` | function | 15 | request boundary와 UI state 비소유 원칙을 설명한다. |
| `src/components/runocr/utils/mapOcrResponse.ts` | `buildRunOcrResult` | function | 25 | raw response에서 OcrResult로 매핑하는 순수 contract다. |

## 8. JSDoc 불필요 대상
아래 대상은 이름과 코드 구조로 의미가 충분하거나, 파일 header와 중복될 가능성이 커서 실제 주석 작업에서 제외하는 편이 좋다.

| file | symbol | reason |
| --- | --- | --- |
| `src/components/runocr/RunOcrWorkspace.tsx` | `OcrCanvasPane` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `LOCAL_TEMPLATES_KEY` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `OCR_REGION_ID_PREFIX` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `ocrRegionIdForField` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `fieldIndexFromOcrRegionId` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `index` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `left` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `top` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `right` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `bottom` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `MODEL_OPTIONS` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `isTiff` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `router` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `ui` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `fileInputRef` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `uploadStartRef` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `isRunOcr` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `canvasImgRef` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `loadLocalTemplates` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `list` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `imgMeta` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `imgW` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `imgH` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `inlineSrc` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `mergeTemplates` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `seen` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `key` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `useEffect` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `fieldIndex` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `useEffect` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `regionId` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `region` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `src` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `useEffect` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `localTemplates` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `hydrated` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `res` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `json` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `list` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `mapped` | 이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다. |

## 9. RunOcrWorkspace 핵심 주석 대상
- `RunOcrWorkspace`: 전체 RunOCR orchestration owner.
- `runOcr`: `runOcrRequest` 호출, `buildRunOcrResult` 변환, autofill 적용, history 저장, result state 반영 순서를 설명.
- `handlePersistEdits`: 수정 결과를 history run에 반영하는 경계.
- `handleResultClose`: 결과 화면 close 시 초기화되는 state 범위.
- `unionSourceBoxes`: field source box를 overlay box로 합치는 좌표 helper.

## 10. utils 파일 주석 대상
- `src/components/runocr/utils/buildOcrFormData.ts`: FormData key parity와 연결되어 함수 JSDoc에 검증 기준을 적는 것이 좋다.
- `src/components/runocr/utils/runOcrRequest.ts`: Error 메시지와 endpoint fallback은 request boundary 검증 대상이다.
- `src/components/runocr/utils/mapOcrResponse.ts`: raw response shape와 OcrResult contract 사이 경계라 JSDoc이 필요하다.

## 11. ui 파일 주석 대상
- `src/components/runocr/ui/RunOcrResultLayout.tsx`: node composition 경계를 유지해야 props 중계 컴포넌트로 비대해지지 않는다.
- `src/components/runocr/ui/OcrResultPanel.tsx`: 파일이 크고 tab별 책임이 많으므로 실제 주석 추가는 header와 핵심 helper 경계 중심으로 제한하는 편이 안전하다.
- `src/components/runocr/ui/OcrDocViewer.tsx`: scale/overlay 좌표 계산은 시각 회귀가 나기 쉬워 주석 가치가 있다.
- `src/components/runocr/ui/CornerAdjust.tsx`: pointer event와 normalized 좌표 변환은 짧은 주석이 있으면 유지보수성이 좋아진다.

## 12. 과주석 금지 목록
- 단순 setState wrapper
- 단순 toggle handler
- JSX node 변수 또는 JSX wrapper
- 명확한 상수 import/export
- props type 내부 모든 field
- 1~3줄짜리 명확한 local helper
- 파일 header와 같은 내용을 반복하는 함수 주석

## 13. 실제 주석 추가 작업 추천 범위
- 추천: RunOCR 8개 파일 전체에 파일 header를 추가하되, 함수 JSDoc은 utils 3개와 RunOcrWorkspace 핵심 흐름, RunOcrResultLayout boundary에 우선 적용한다.
- 옵션: `A_LIGHTWEIGHT_HEADER_ALL_PLUS_CORE_JSDOC`
- 위험도: MEDIUM
- 포함:
  - 8개 RunOCR 파일 file header
  - buildOcrFormData / runOcrRequest / buildRunOcrResult JSDoc
  - RunOcrWorkspace / runOcr / handlePersistEdits / handleResultClose JSDoc
  - RunOcrResultLayout JSDoc
  - OcrDocViewer scale helper, CornerAdjust coordinate helpers는 짧게만
- 보류:
  - OcrResultPanel 내부 모든 helper 주석화
  - props type field-by-field 주석
  - 단순 setter/toggle 주석

## 14. 검증 전략
- npm run typecheck
- npm run build
- node tmp/check_table_view_model_v1_fixtures_js.mjs
- node tmp/check_clean_json_v1_fixtures_js.mjs
- python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_DOC_COMMENTS_20260522
- FormData key parity check
- request boundary static check
- response mapping boundary static check
- result layout boundary static check
- diff review: comments-only change인지 확인
- no excessive comments static/manual review

## 15. dirty 상태
이번 precheck에서 dirty 상태는 되돌리지 않았다.

```text
 M src/app/runocr/page.tsx
RM src/components/upload/UploadWorkspace.tsx -> src/components/runocr/RunOcrWorkspace.tsx
R  src/components/upload/CornerAdjust.tsx -> src/components/runocr/ui/CornerAdjust.tsx
R  src/components/upload/OcrDocViewer.tsx -> src/components/runocr/ui/OcrDocViewer.tsx
RM src/components/upload/OcrResultPanel.tsx -> src/components/runocr/ui/OcrResultPanel.tsx
 M src/lib/invoiceTableDisplay.ts
 M ../ocr-server/data/review_log.jsonl
 M ../ocr-server/data/templates.json
 M ../ocr-server/requirements.txt
?? docs/CLEAN_JSON_CONTRACT_20260521.json
?? docs/CLEAN_JSON_CONTRACT_20260521.md
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md
?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.json
?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md
?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.json
?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.md
?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.json
?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.md
?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.json
?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md
?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json
?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md
?? docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.json
?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.md
?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.json
?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md
?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json
?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md
?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.json
?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md
?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_TABLE_20260521.csv
?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.json
?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.md
?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.json
?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.md
?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.md
?? docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.md
?? docs/FRONTEND_RUNOCR_UI_SPLIT_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.md
?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.md
?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.json
?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.md
?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.json
?? docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.md
?? docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.json
?? docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.md
?? docs/FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.json
?? docs/FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.md
?? docs/FRONTEND_STRUCTURE_3A_RUNOCR_RESULT_LAYOUT_SPLIT_20260522.json
?? docs/FRONTEND_STRUCTURE_3A_RUNOCR_RESULT_LAYOUT_SPLIT_20260522.md
?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md
?? docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.json
?? docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.md
?? docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_DIFF_20260522.csv
?? docs/MARKDOWN_V1_CONTRACT_20260521.json
?? docs/MARKDOWN_V1_CONTRACT_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FORMDATA_EXTRACT_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FORMDATA_EXTRACT_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_REQUEST_EXTRACT_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_REQUEST_EXTRACT_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESULT_LAYOUT_SPLIT_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESULT_LAYOUT_SPLIT_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TRADE7_REBAKE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TRADE7_REBAKE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.md
?? docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.json
?? docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.md
?? src/components/runocr/ui/RunOcrResultLayout.tsx
?? src/components/runocr/utils/
?? src/lib/cleanJsonBuilder.ts
?? src/lib/markdownReportBuilder.ts
?? src/lib/ocrResultFormatters.ts
?? src/lib/structuredTableViewModel.ts
?? tmp/
?? ../ocr-server/requirements-aws.txt
```

## 16. typecheck/build 결과
- `npm run typecheck`: PASS (exit 0)
- `npm run build`: PASS (exit 0)
- known stderr noise: ESLint: nextVitals is not iterable

## 17. 다음 작업 제안
1. `FRONTEND-STRUCTURE-3B-RUNOCR-DOC-COMMENTS`로 comments-only patch를 진행한다.
2. 8개 파일 header + core JSDoc만 먼저 적용한다.
3. `OcrResultPanel` 내부 helper 전체 주석화는 별도 cycle로 미룬다.
