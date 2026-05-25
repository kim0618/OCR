# TPL-11 Template Table Row Overrides Precheck

## 1. Summary

- **현재 rowTemplate 구조:** 단일 `Rect`. 사용자가 캔버스에서 한 줄을 드래그하면 그 Rect가 `region.table.rowTemplate`에 저장되고, `buildTableRows(area, rowTemplate)`가 이를 동일 height로 아래로 반복하여 `rows: Rect[]`을 즉시 materialize 한다.
- **현재 rows 구조:** `Rect[]`. rowTemplate 드래그 시점 / region resize 시점에 `buildTableRows`로 전부 재생성된다. 사용자가 직접 편집할 UI는 없다. region move 시에는 동일 dy만큼 일괄 shift 된다.
- **backend rows 사용 여부:** **사용 안 함.** `ocr-server/main.py`는 region에서 `colGuides` / `colX` / `mode` / `stopKeywords` + `x,y,width,height`로부터 만든 `tableBounds`만 소비한다. `rows` / `rowTemplate`은 페이로드에 저장되지만 백엔드는 읽지 않는다. 백엔드는 OCR 텍스트 라인을 표 영역 내에서 직접 군집화한다.
- **rowOverrides 필요 여부:** 프론트엔드 시각 보정 / 사용자 편의용으로만 의미가 있다. 백엔드 추출 정확도와는 무관. 사용자가 “이 한 행만 두 줄짜리야”라고 시각적으로 표시·저장하려는 요구는 정당하지만, OCR 추출 결과를 바꾸지는 않는다.
- **추천 schema:** **Option A — sparse `rowOverrides: TableRowOverride[]`**. 기존 rowTemplate 자동 반복은 유지하고, 사용자가 손댄 row만 sparse override로 보관한다.
- **추천 UI interaction:** **C + D — "행 개별 조정" 토글 모드 + reset 버튼**. 토글 켜진 동안 캔버스에 row boundary handle을 표시, 드래그로 인접 row 경계 조정. 각 row에 reset 단축, 전체 reset 버튼.
- **backend contract 변경 필요 여부:** **없음.** rowOverrides는 frontend 메타로 저장하되, `buildTemplateExportPayload`는 기존처럼 `rowTemplate` + materialized `rows`를 그대로 내보낸다 (rows에 override가 이미 합쳐진 상태).
- **추천 다음 구현 작업:** TPL-12A → TPL-12B → TPL-12C → TPL-12D (아래 §9).
- **이번 precheck에서 운영 코드 수정 여부:** 없음. 산출물 두 파일과 로그만 생성.

## 2. Current Row Flow

- **TemplateAnnotator state:** [TemplateAnnotator.tsx:34-35](../src/components/template/ui/TemplateAnnotator.tsx#L34-L35)에서 `rowTemplateTargetId` / `colGuideTargetId`를 `useState`로 관리. OcrCanvasPane / TemplateRightPanel에 prop으로 전달.
- **OcrCanvasPane draw flow:**
  1. [OcrCanvasPane.tsx:345-362](../src/common/ui/OcrCanvasPane.tsx#L345-L362) — pointerDown 시 `rowTemplateTargetId`가 있으면 `drawRowTemplate` 드래그 타입으로 진입.
  2. [OcrCanvasPane.tsx:402-435](../src/common/ui/OcrCanvasPane.tsx#L402-L435) — 드래그 중 매 프레임 `normalizeRect → clampRectToArea → buildTableRows`로 `rowTemplate` + `rows`를 동시에 갱신.
  3. [OcrCanvasPane.tsx:735-755](../src/common/ui/OcrCanvasPane.tsx#L735-L755) — pointerUp 시 너무 작은 rowTemplate은 정리.
  4. [OcrCanvasPane.tsx:1363-1398](../src/common/ui/OcrCanvasPane.tsx#L1363-L1398) — rowTemplate은 2px dashed 진녹색 박스, rows는 최대 80개까지 1px dashed 옅은 녹색으로 표시.
- **buildTableRows:** [ocrTableRegion.ts:34-50](../src/common/utils/ocrTableRegion.ts#L34-L50). 순수 함수. rowTemplate height만큼 area 하단까지 반복. 5000행 안전상한.
- **region move/resize behavior:**
  - **move:** [OcrCanvasPane.tsx:515-522](../src/common/ui/OcrCanvasPane.tsx#L515-L522) — `rowTemplate`과 모든 `rows`를 동일 dx/dy로 shift. 행별 정렬 유지.
  - **resize:** [OcrCanvasPane.tsx:594-610](../src/common/ui/OcrCanvasPane.tsx#L594-L610) — rowTemplate을 새 area에 clamp 후 `buildTableRows`로 **rows 전체 재생성**. rowTemplate이 없으면 rows도 undefined로 정리. → **resize는 현재 사용자가 손댄 어떤 row 편집도 파괴할 수 있는 지점.**
- **TemplateRightPanel display:** [TemplateRightPanel.tsx:419-465](../src/components/template/ui/TemplateRightPanel.tsx#L419-L465) — `행 템플릿 지정` 버튼이 `rowTemplateTargetId`를 켠다. `행 템플릿 해제`가 rowTemplate + rows를 모두 비운다. 개별 row를 표시하는 UI는 **없음.**
- **buildTemplateExportPayload:** [buildTemplateExportPayload.ts:61-85](../src/components/template/utils/buildTemplateExportPayload.ts#L61-L85) — `rowTemplate` (또는 null) + `rows: Rect[]` + `colGuides` + `colX` + `stopKeywords` + 선택적 `tableName` / `columns`를 그대로 라운딩하여 저장.
- **backend payload:** [main.py:2590-2626](../../ocr-server/main.py#L2590-L2626) — region 순회 중 `fieldType==="table"`이면 region x/y/w/h로 `tableBounds`(OCR 좌표계 스케일)를 만들고, `region.table.colX` / `mode` / `stopKeywords`만 추출. `rows` / `rowTemplate`은 읽지 않음.
- **current limitations:**
  - resize 한 번에 사용자 편집 손실
  - row별 다른 height 표현 불가
  - 표 끝부분이 area에 안 맞아 마지막 행이 짤리거나 누락 (height가 area에 정확히 나누어떨어지지 않으면)
  - 같은 region 내 “헤더 row가 더 두꺼움 + 본문 row는 작음” 패턴 표현 불가

## 3. Current Schema

- **Region.table** ([ocr.ts:35-43](../src/common/types/ocr.ts#L35-L43)):
  ```ts
  export type TableMeta = {
    mode?: "repeat" | "auto";
    rowTemplate?: Rect;
    rows?: Rect[];
    colGuides?: number[];
    stopKeywords?: string[];
    tableName?: string;
    columns?: TableColumnDef[];
  };
  ```
- **rowTemplate:** 단일 Rect, 사용자 드래그 결과를 그대로 보관.
- **rows:** materialized Rect 배열. 항상 rowTemplate에서 파생.
- **colGuides:** 정규화된 비율(0~1) 배열.
- **saved payload (templates.json 발췌):**
  ```jsonc
  "table": {
    "mode": "repeat",
    "rowTemplate": { "x": 68, "y": 433, "width": 1503, "height": 68 },
    "rows": [ { "x": 68, "y": 433, "width": 1503, "height": 68 }, ... ],
    "colGuides": [...],
    "colX": [...],
    "stopKeywords": []
  }
  ```
- **backend expected shape:** `colX` (혹은 `colGuides`), `mode`, `stopKeywords`만. `rows` / `rowTemplate`은 무시.

## 4. Row Override Options

| option | description | pros | cons | recommendation |
|---|---|---|---|---|
| **A. rowOverrides (sparse)** | `rowOverrides: { rowIndex; y?; height? }[]`. 기본 rowTemplate 반복 + 손댄 행만 patch | • 기존 자동 반복 정책 그대로 • payload diff 작음 • backward compat 자연스러움 • 사용자 의도(어디를 손댔는지) 보존 | • merge/clamp/insertion 정책 필요 • resize 시 rowIndex 의미 보존 어렵 (개수가 바뀌면) | **Recommended** |
| **B. editable rows (direct)** | `rows`를 사용자 편집 가능한 source of truth로 격상 | • 데이터 흐름 직관적 • backend가 rows를 쓴다면 즉시 반영 | • rowTemplate과 충돌 (어느 쪽이 진실?) • resize 보정 정책이 row 개수만큼 복잡 • 자동 반복으로 “복귀” 표현 어렵 • 백엔드는 rows를 안 쓰므로 보너스 없음 | 비추천 |
| **C. hybrid (rowTemplate + rows + rowOverrides 동시)** | A+B 모두 보유 | • 최대 유연성 | • 진실의 출처 3개로 늘어남 • 디버깅 비용 폭증 • 지금 단계 과설계 | 비추천 |

## 5. Recommended Schema

```ts
/**
 * Sparse override for a single repeated row. rowIndex는 buildTableRows가
 * rowTemplate으로 만드는 base rows 배열의 0-based index. height만 있고 y는
 * 없으면 base y는 유지하고 본인 + 후속 rows를 자동으로 shift. y/height 둘 다
 * 있으면 절대 위치 + 높이 강제.
 */
export type TableRowOverride = {
  rowIndex: number;
  /** Optional absolute y (override of rowTemplate-derived y). Float allowed. */
  y?: number;
  /** Optional absolute height. Must be > 0. */
  height?: number;
  /**
   * 사용자가 명시적으로 “이 행은 자동 재계산에서 보호” 표시.
   * locked === true 면 region resize 시에도 height/y 보존.
   */
  locked?: boolean;
};

export type TableMeta = {
  mode?: "repeat" | "auto";
  rowTemplate?: Rect;
  rows?: Rect[];
  colGuides?: number[];
  stopKeywords?: string[];
  tableName?: string;
  columns?: TableColumnDef[];
  /**
   * TPL-12: sparse per-row 보정. 없으면 기존 동작 그대로.
   */
  rowOverrides?: TableRowOverride[];
};
```

- `rowOverrides`가 없으면 schema는 기존과 동일 (backward compat OK).
- `rowOverrides`가 있어도 export 시 buildTemplateExportPayload는 base rows에 override를 merge한 결과를 `rows`로 내보낸다 → 백엔드 contract 무변경.
- `rowOverrides` 자체도 함께 저장하여 다음 편집에서 사용자 의도(어디를 손댔는지) 복원.

## 6. Merge / Materialization Strategy

- **base rows 생성:** `const baseRows = buildTableRows(area, rowTemplate)`. 기존 helper 그대로 재사용.
- **override 적용:** 새 helper `materializeTableRowsWithOverrides(baseRows, overrides, area)`:
  1. baseRows를 copy.
  2. overrides를 `rowIndex` 오름차순 정렬.
  3. 각 override에 대해 `rows[rowIndex]`의 height/y를 patch.
  4. 한 행의 height가 변경되면 그 뒤 행들의 y를 `prev.y + prev.height`로 cascade 재계산 (locked row는 보존).
  5. area 하단을 벗어나는 trailing rows는 잘라낸다.
  6. min height = 4 (rowTemplate min과 동일).
- **bounds clamp:** 결과 rect 각각 `clampRectToArea(rect, area)` 적용. min/max는 area 경계.
- **min height:** `MIN_ROW_HEIGHT = 4` (canvas drag clamp와 동일).
- **adjacent row policy:** cascade shift — 한 행 height 늘리면 그 아래 모든 행이 그만큼 내려간다 (혹은 area 끝에서 잘림). drag UX는 “경계 라인 위/아래로 끌어 인접 두 행의 height를 zero-sum으로 조정” vs “한 행만 늘리고 아래쪽 모두 cascade”의 두 모드 가능. 권장은 **단순 cascade**.
- **export rows:** `buildTemplateExportPayload`에서 `materializeTableRowsWithOverrides`로 만든 rows를 기존처럼 `rows`로 직렬화. **payload key는 추가하지 않음** (rowOverrides 자체는 별도 key로 보존 — 다음 항목 참조).
- **reset policy:**
  - row-level reset: `rowOverrides`에서 해당 `rowIndex` 항목 제거.
  - global reset: `rowOverrides = []` (또는 undefined).
  - `행 템플릿 해제` 누르면 rowTemplate/rows/rowOverrides 모두 비움.

## 7. UI Interaction Plan

- **canvas mode:** 새 모드 토글 `rowAdjustTargetId: string | null`. `행 개별 조정` 버튼이 켜면 진입. 켜진 동안 row boundary handle 표시.
- **row boundary handles:**
  - 각 row 상/하 경계에 작은 노란색 핸들 라인 (height 6px 정도).
  - 드래그 → 위/아래 두 인접 행의 height를 cascade 갱신.
  - 클릭 → 해당 row 선택 (오른쪽 패널에 해당 rowIndex 표시).
- **selected row:** 선택된 row는 약간 더 진한 색 + “이 행 reset” 버튼 노출. 키보드 Esc로 선택 해제.
- **reset row:** TemplateRightPanel에 “선택 행 reset” 버튼 (해당 rowIndex의 override만 제거).
- **reset all:** “모든 행 조정 초기화” 버튼 (rowOverrides 전체 제거).
- **right panel summary:** rowOverrides 개수 / 마지막 수정 시간 / 잠긴 행 수.
- **keyboard/mouse conflict:**
  - drawRowTemplate 모드와 rowAdjust 모드는 **상호 배타** (둘 중 하나만 active).
  - rowAdjust 활성 중 region resize 핸들 드래그는 비활성 (사용자 실수 방지) 또는 confirm 다이얼로그.
- **mobile/desktop consideration:** mobile에서 row handle은 hit-area 12px 이상 필요. 데스크탑은 6px로도 OK.

## 8. Backend / Payload Impact

- **backend contract change 필요 여부:** **없음.** [main.py:2590-2626](../../ocr-server/main.py#L2590-L2626)이 `region.table.rows`를 읽지 않음을 확인.
- **buildTemplateExportPayload 변경 여부:** 두 가지 옵션:
  - **(권장) export 시 materialize-then-spread**: `rows`는 override 합쳐진 최종 Rect 배열로 그대로 저장. `rowOverrides` 자체도 별도 key로 저장 (다음 편집 복원용). 백엔드는 기존처럼 rows를 무시.
  - **(대안) base rows + rowOverrides만 저장**: 저장 시 rows를 생성하지 않고, 로드 시 materialize. 페이로드는 작아지지만 다른 도구가 rows를 가정할 수 있어 위험 (templates.json의 기존 rows 형태와 호환성 깨짐). 비추천.
- **rows materialization 방식:** 위 권장안 — export 시점 materialize.
- **template save metadata:** `rowOverrides`는 `region.table.rowOverrides`에 보존. 없으면 key 생략 (기존 templates.json과 byte-compat).
- **legacy compatibility:**
  - 기존 template 로드 → `rowOverrides` 없음 → 기존 동작 100% 보존.
  - rowOverrides가 있는 새 template을 옛 코드로 로드 → 옛 코드는 모르고 무시 → rowTemplate + rows만 사용 (성능/추출 영향 없음).

## 9. Implementation Plan (TPL-12A → TPL-12D)

### TPL-12A — Row Override Types and Helpers

- **목표:** schema 도입과 순수 helper 추가. UI/payload 미변경.
- **수정 파일 후보:**
  - `src/common/types/ocr.ts` — `TableRowOverride` 타입 + `TableMeta.rowOverrides?: TableRowOverride[]` 추가.
  - `src/common/utils/ocrTableRegion.ts` — `materializeTableRowsWithOverrides(baseRows, overrides, area)` 순수 helper 추가.
  - **OcrCanvasPane / TemplateRightPanel / buildTemplateExportPayload 미수정.**
- **금지:** UI 추가, payload 변경, backend 변경.
- **검증 기준:**
  - typecheck/build PASS
  - new helper 6+ smoke (no overrides=base, single override y/height, cascade, locked, out-of-bounds clamp, min height, mutation guard)
  - 기존 runner all PASS
  - rowOverrides 사용처 0 (helper 정의/타입만)

### TPL-12B — Row Override Save / Load Round-Trip

- **목표:** rowOverrides save/load가 buildTemplateExportPayload를 거쳐도 보존되는지 fixture로 검증. UI 미변경.
- **수정 파일 후보:**
  - `src/components/template/utils/buildTemplateExportPayload.ts` — `rowOverrides`가 있으면 그대로 spread 보존 + `rows`는 `materializeTableRowsWithOverrides` 결과로 저장 (있을 때만 다른 동작, 없으면 기존 동작 byte-identical).
  - 새 fixture `tmp/fixtures/template_table_row_overrides/` (legacy/empty-overrides/single-override/cascade/locked).
- **금지:** UI, backend, rowOverrides 핸들러.
- **검증 기준:**
  - 기존 templates.json fixture (rowOverrides 없는 case) byte-identical 결과
  - rowOverrides가 있는 경우 `rows`가 materialized 결과로 저장 + `rowOverrides`도 함께 저장
  - typecheck/build PASS

### TPL-12C — Row Boundary Drag Canvas UI

- **목표:** OcrCanvasPane에 row boundary handle + 드래그 UI 추가, “행 개별 조정” 모드 토글, TemplateRightPanel에 토글 + reset 버튼 추가.
- **수정 파일 후보:**
  - `src/common/ui/OcrCanvasPane.tsx` — `rowAdjustTargetId` prop / drag handler / 핸들 렌더.
  - `src/components/template/ui/TemplateAnnotator.tsx` — `rowAdjustTargetId` state + OcrCanvasPane에 전달.
  - `src/components/template/ui/TemplateRightPanel.tsx` — `행 개별 조정` 버튼 / row reset 버튼 / summary.
- **금지:** payload schema 변경, backend, 키보드 단축 (기본 mouse만).
- **검증 기준:**
  - region move 시 rowOverrides 보존 (cascade dy shift)
  - region resize 시 locked row의 height 보존, 비locked는 cascade
  - 기존 rowTemplate 드래그 미회귀
  - `행 템플릿 해제`는 rowOverrides도 함께 초기화

### TPL-12D — Payload Integration + Compatibility Sweep

- **목표:** 전체 흐름 (canvas → template → payload → 로드 복원) 통합 회귀 테스트. rowOverrides가 있는 신규 template을 load → save → load 했을 때 byte-identical 보장.
- **수정 파일 후보:**
  - 기존 파일 미수정. fixture/runner 추가.
  - tmp/check_template_table_row_overrides_round_trip_tpl12d.mjs
- **금지:** 추가 schema 변경, backend.
- **검증 기준:**
  - 모든 기존 runner PASS
  - markdown contract PASS
  - 신규 fixture 8+ pass
  - rowOverrides가 backend payload에 영향 없음 확인 (main.py 비활성 — read 안 함)

## 10. Risk Assessment

| 항목 | 리스크 | 비고 |
|---|---|---|
| OcrCanvasPane complexity | **MEDIUM** | drag 타입 한 종류 추가, 기존 drawRowTemplate / resize / move와 상호 배타 처리 필요 |
| resize/move regression | **MEDIUM** | TPL-12C에서 cascade dy shift + clamp 정책을 명확히 해야 함 |
| backend contract risk | **LOW** | main.py가 rows/rowTemplate 모두 무시함을 확인 |
| existing template compatibility | **LOW** | rowOverrides 없으면 기존 동작 그대로, 새 key는 optional |
| row/col guide interaction | **LOW** | colGuides는 가로/세로 비율 기반이라 rowOverrides와 차원이 다름 |
| user confusion risk | **MEDIUM** | “행 템플릿 지정 / 행 개별 조정”의 mode 두 개가 생김 → UI에서 분명히 구분 필요 |
| test coverage risk | **MEDIUM** | row cascade 정책 / locked / area boundary clamp의 unit test 필요 |

## 11. Do Not Start Yet

- rowOverrides 구현 (TPL-12A-D는 별도 phase)
- OcrCanvasPane 수정
- TemplateRightPanel 수정
- buildTemplateExportPayload 수정
- types/ocr.ts 수정
- backend 수정 (절대)
- TestWorkspace / public/data/testsets / templates.json 수정
- row drag UI prototype

## 12. Verification Results

- **production code modified:** 없음
- **src/lib absent:** 유지
- **@/lib import 0:** 유지
- **typecheck:** PASS
- **build:** PASS
- **static precheck:** PASS
- **FAIL count:** 0
