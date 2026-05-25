# FRONTEND OCR Canvas Pane Shared Precheck 2026-05-22

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `CODEX_FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- `src` 하위 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 파일: 이 precheck 스크립트와 docs 리포트만 생성

## 3. 생성 파일
- `tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py`
- `docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/runocr/ui/OcrDocViewer.tsx`
- `src/components/ocr/core/*`
- `src/components/test/TestWorkspace.tsx` read-only

## 5. OcrCanvasPane 역할 요약
- Path: `src/components/ocr/OcrCanvasPane.tsx`
- lineCount: 1527
- Export: default `OcrCanvasPane(props: Props)`
- 역할: 이미지 기반 OCR region canvas. draw/move/resize/delete/duplicate/undo, multi split, table rowTemplate/colGuide, zoom, drag/drop handoff, visible region filtering을 담당한다.
- 주요 imports: `React`, `./core/types`, `./core/ops`, `./core/table`, `../common/FileDropzone`

## 6. importedBy 분석
| consumer | import path |
| --- | --- |
| `src/components/template/ui/OcrAnnotator.tsx` | `../../ocr/OcrCanvasPane` |
| `src/components/runocr/RunOcrWorkspace.tsx` | dynamic `../ocr/OcrCanvasPane` |

`TestWorkspace.tsx` 직접 import는 발견되지 않았다.

## 7. Template 사용 분석
`OcrAnnotator`는 `imgRef`, `onPickFile`, `loaded`, `regions/setRegions`, selection, table target 상태, drawMode, zoom을 전달한다. Template에서는 field/multi/check/table region 작성과 편집, `OcrRightPanel`의 metadata/table controls, `buildExportPayload` 저장 흐름과 직접 연결된다.

## 8. RunOCR 사용 분석
`RunOcrWorkspace`는 result `custom` tab에서만 `OcrCanvasPane`를 렌더링한다. preview에서는 `OcrDocViewer`가 read-only overlay를 담당하고, custom tab에서는 `visibleRegionIds`, `emptySelectionHint`, `drawTargetRegionId/name/type`, `onClearSelection`으로 OCR 결과 field 선택과 canvas region 편집을 연결한다.

## 9. props 차이 분석
- 공통 props: imgRef, loaded, regions, setRegions, selectedId, setSelectedId, rowTemplateTargetId, setRowTemplateTargetId, colGuideTargetId, setColGuideTargetId, drawMode, setDrawMode, zoomPct
- Template-only: onPickFile
- RunOCR-only: visibleRegionIds, emptySelectionHint, drawTargetRegionId, drawTargetName, drawTargetFieldType, onClearSelection
- 판단: props 이름 자체는 feature-neutral에 가깝다. 다만 `setRegions` 등 상태 setter를 직접 받는 큰 shared editor이고, `ocr/core` 상대 의존이 남아 있어 common/ui 단독 이동은 아직 거칠다.

## 10. ocr/core 의존 분석
`OcrCanvasPane`는 `types`, `ops`, `table`에 직접 의존한다. `types`는 Template/RunOCR/formData가 공유하고, `ops/table`은 Canvas/RightPanel/export helper가 공유한다. `export.ts`는 현재 Template 저장 payload 중심이다.

| core file | lineCount | current role | candidate |
| --- | ---: | --- | --- |
| `src/components/ocr/core/types.ts` | 110 | Region/FieldType/LoadedImage/DragKind | common types |
| `src/components/ocr/core/ops.ts` | 99 | geometry/ratio/id helpers | common utils |
| `src/components/ocr/core/table.ts` | 151 | table row/column guide helpers | common utils or template table utils |
| `src/components/ocr/core/export.ts` | 90 | template export payload | template utils |

## 11. 이동 후보 비교
| 후보 | 판단 | 위험도 | 메모 |
| --- | --- | --- | --- |
| `src/common/ui/OcrCanvasPane.tsx` | 가능하지만 core precheck 후 | MEDIUM_HIGH | cross-feature 위치는 맞지만 core 상대 의존 정리가 선행되면 자연스럽다. |
| 현 위치 유지 | 현재 추천 | LOW | 운영 diff 없이 shared holding area로 임시 유지. |
| `src/components/template/ui/OcrCanvasPane.tsx` | 비추천 | HIGH | RunOCR 직접 사용과 충돌. |
| `src/components/runocr/ui/OcrCanvasPane.tsx` | 비추천 | HIGH | Template 직접 사용과 충돌. |

## 12. Phase 추천
추천: **B. ocr/core utils 이동 precheck를 먼저 진행**.

이유:
- OcrCanvasPane는 Template/RunOCR 모두 쓰므로 feature-private 폴더로 보내면 안 된다.
- common/ui 후보는 맞지만 `types/ops/table` 의존이 같이 정리되어야 common 계층이 어색하지 않다.
- 지금 이동하면 import 변경 범위는 작아 보여도 RunOCR dynamic import와 Template editor 저장/편집 흐름을 동시에 건드린다.

## 13. static check 설계
후속 이동 시 `tmp/check_ocr_canvas_pane_common_move.mjs` 후보:
1. `common/ui/OcrCanvasPane.tsx` 존재
2. `components/ocr/OcrCanvasPane.tsx` 부재 또는 shim 정책 일치
3. `OcrAnnotator` import 정상
4. `RunOcrWorkspace` dynamic import 정상
5. `TestWorkspace` 미수정
6. `ocr/core` 이동 정책 일치
7. `npm run typecheck` PASS
8. `npm run build` PASS
9. RunOCR boundary checks PASS
10. Template 4A/4B checks PASS

## 14. dirty 상태
Pre-existing dirty before report generation:

```text
 M ocr-server/data/review_log.jsonl
 M ocr-server/data/templates.json
```

Dirty after generating allowed precheck artifacts:

```text
 M ocr-server/data/review_log.jsonl
 M ocr-server/data/templates.json
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md
?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py
```

`templates.json` dirty 상태는 원복하지 않았고, TPL-95328E52 영향 precheck 후보로 유지한다.

## 15. typecheck/build 결과
- `npm run typecheck`: exit 0, PASS
- `npm run build`: exit 0, PASS
- known stderr noise: `ESLint: nextVitals is not iterable`
- 요청 로그 경로: `D:/Free_Vue/OCR/ocr-server/logs/codex_CODEX_FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_NO_PROD_MODIFY.out.log` / `D:/Free_Vue/OCR/ocr-server/logs/codex_CODEX_FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_NO_PROD_MODIFY.err.log`
- 요청 로그 저장 결과: 실패. 현재 실행 환경에 `D:` 드라이브가 없음.
- 대체 로그: `C:\OCR\OCR\mysuit-ocr\tmp\codex_CODEX_FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_NO_PROD_MODIFY.out.log` / `C:\OCR\OCR\mysuit-ocr\tmp\codex_CODEX_FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_NO_PROD_MODIFY.err.log`

## 16. 다음 작업 제안
1. `ocr/core/types/ops/table/export` ownership precheck
2. `types/ops/table` common 이동 여부 확정
3. 이후 `OcrCanvasPane` common/ui 이동 + static check
4. 별도 phase에서 `OcrRightPanel` rename 또는 Template table column definition 설계 진행
