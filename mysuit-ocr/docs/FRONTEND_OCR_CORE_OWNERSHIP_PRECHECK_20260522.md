# FRONTEND OCR Core Ownership Precheck 2026-05-22

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `CODEX_FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- `src` 하위 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 파일: 허용된 `tmp/` 스크립트와 `docs/` 리포트만 생성

## 3. 생성 파일
- `tmp/codex_frontend_ocr_core_ownership_precheck.py`
- `docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CORE_OWNERSHIP_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/core/types.ts`
- `src/components/ocr/core/ops.ts`
- `src/components/ocr/core/table.ts`
- `src/components/ocr/core/export.ts`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/runocr/ui/*`
- `src/components/test/TestWorkspace.tsx` read-only

## 5. core 파일별 역할 요약
| file | lineCount | role | ownership | risk |
| --- | ---: | --- | --- | --- |
| `types.ts` | 110 | OCR canvas/template model types | `common/types` | MEDIUM |
| `ops.ts` | 99 | geometry/ratio/canvas helper functions | `common/utils` | MEDIUM |
| `table.ts` | 151 | OCR table row/column-guide helpers | `common/utils` with table-design caution | MEDIUM_HIGH |
| `export.ts` | 90 | template save/export payload builder | `components/template/utils` | LOW_MEDIUM |

## 6. importedBy 분석
| core file | importedBy |
| --- | --- |
| `types.ts` | `OcrCanvasPane`, `OcrAnnotator`, `OcrRightPanel`, `RunOcrWorkspace`, `runocr/utils/buildOcrFormData`, `ops/table/export` |
| `ops.ts` | `OcrCanvasPane`, `OcrRightPanel`, `table.ts`, `export.ts` |
| `table.ts` | `OcrCanvasPane`, `OcrRightPanel`, `export.ts` |
| `export.ts` | `OcrAnnotator` only |

`src/components/test/TestWorkspace.tsx`는 자체 `src/components/test/core/types.ts`를 쓰며, 이번 `src/components/ocr/core/*`의 직접 consumer는 아니다.

## 7. types.ts ownership
`FieldType`, `Rect`, `TableMeta`, `Region`, `LoadedImage`, `DragKind`, mapping metadata를 export한다. Template editor, RunOCR custom canvas, OcrCanvasPane, form-data util이 모두 쓰므로 Template 전용이 아니다.

추천 target: `src/common/types/ocr.ts` 또는 `src/common/types/ocrCanvas.ts`.

판정: **common/types 후보. 첫 micro-step으로 가장 적합**.

## 8. ops.ts ownership
`clamp`, `normalizeRect`, `uid`, `parseIndex`, `normalizeRatios`, `boxLabelStyle`, `calcMultiSubRegions`, `clampRectToArea`를 export한다. 대부분 pure geometry/ratio helper이고 OcrCanvasPane과 OcrRightPanel이 같이 쓴다. 단 `boxLabelStyle` 때문에 React `CSSProperties` type-only import가 있다.

추천 target: `src/common/utils/ocrCanvasOps.ts` 또는 `src/common/utils/ocrGeometry.ts`.

판정: **common/utils 후보. types 이동 후 이동**.

## 9. table.ts ownership
`normalizeColGuides`, `buildTableRows`, `normalizeStopKeywords`, `autoDetectRowBands`, `isStopRow`를 export한다. Table region geometry/guide 성격은 OcrCanvasPane과 공유되므로 common/utils 후보지만, table column definition 설계와 맞물릴 수 있다.

추천 target: `src/common/utils/ocrTableRegion.ts`. 다만 semantic mapper/column definition은 `components/template/utils` 설계와 분리 권장.

판정: **common/utils 후보이나 Template table column definition 전 주의**.

## 10. export.ts ownership
`buildExportPayload`만 export하며 `OcrAnnotator`의 Template 저장 payload 구성에만 직접 사용된다. RunOCR 직접 사용이 없다.

추천 target: `src/components/template/utils/buildTemplateExportPayload.ts` 또는 `src/components/template/utils/templateMapper.ts`.

판정: **common/utils 후보 아님. Template utils가 맞음**.

## 11. dependency graph / 이동 순서
```text
types.ts
ops.ts -> types.ts, React type-only CSSProperties
table.ts -> types.ts, ops.ts
export.ts -> types.ts, ops.ts, table.ts
OcrCanvasPane -> types.ts, ops.ts, table.ts
OcrAnnotator -> types.ts, export.ts
OcrRightPanel -> types.ts, ops.ts, table.ts
RunOcrWorkspace/buildOcrFormData -> types.ts
```

권장 순서:
1. `types.ts` common/types micro-step
2. `ops.ts` common/utils 이동
3. `table.ts` common/utils 이동 또는 table design 후 확정
4. `export.ts` template/utils 이동
5. `OcrCanvasPane` common/ui 이동

## 12. 이동 후보 비교
| option | 판단 | risk | 메모 |
| --- | --- | --- | --- |
| A. types만 common/types | RECOMMENDED_FIRST | MEDIUM | 가장 작은 유효 추출. RunOCR/Template 양쪽 import 변경 필요. |
| B. types+ops+table common | GOOD_SECOND_PHASE | MEDIUM_HIGH | OcrCanvasPane common/ui 전 구조가 자연스러워짐. |
| C. export만 template/utils | DO_AFTER_TYPES_OR_WITH_TEMPLATE_MAPPER | LOW_MEDIUM | Template 전용이라 방향은 명확. |
| D. 전체 보류 후 table design | SAFE_BUT_SLOW | LOW | OcrCanvasPane common/ui는 계속 막힘. |
| E. OcrCanvasPane 이동과 묶기 | DO_NOT_DO_FIRST | HIGH | 한 번에 건드리는 표면이 큼. |
| F. precheck 후 rename micro-step | SECONDARY | LOW | core dependency shape 해결은 아님. |

## 13. Phase 추천
추천: **A를 먼저 진행한 뒤 B/C를 나누고, 마지막에 OcrCanvasPane common/ui 이동**.

이유:
- common이 feature 내부를 참조하지 않게 하려면 shared type이 먼저 common에 있어야 한다.
- `types.ts`는 side effect와 React/browser 의존이 없어 가장 안전한 첫 이동이다.
- `ops/table`은 OcrCanvasPane common/ui 이동 전에 common/utils로 정리하는 편이 자연스럽다.
- `export.ts`는 Template 저장 payload라 common으로 보내지 않는다.

## 14. static check 설계
후속 후보:
- `tmp/check_ocr_core_types_move.mjs`
- `tmp/check_ocr_core_shared_utils_move.mjs`
- `tmp/check_template_export_mapper_move.mjs`

검증 항목:
1. target 파일 존재
2. source 파일 부재 또는 보류/shim 정책 일치
3. common 파일이 `components/*`를 import하지 않음
4. template utils 파일은 common/types/common/utils 또는 template-local만 참조
5. RunOCR import 정상
6. Template import 정상
7. TestWorkspace 미수정
8. typecheck/build PASS
9. RunOCR boundary checks PASS
10. Template 4A/4B checks PASS

## 15. dirty 상태
Precheck 시작 시점 dirty:
```text
 M ocr-server/data/review_log.jsonl
 M ocr-server/data/templates.json
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md
?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py
```

리포트 생성 후 dirty:
```text
 M ocr-server/data/review_log.jsonl
 M ocr-server/data/templates.json
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json
?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md
?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_MAP_20260522.csv
?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.json
?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.md
?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py
?? mysuit-ocr/tmp/codex_frontend_ocr_core_ownership_precheck.py
```

`templates.json` dirty 상태는 원복하지 않았고, TPL-95328E52 영향 precheck 후보로 유지한다.

## 16. typecheck/build 결과
- `npm run typecheck`: exit 0, PASS
- `npm run build`: exit 0, PASS
- stdout log: `C:\OCR\OCR\ocr-server\logs\codex_CODEX_FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_NO_PROD_MODIFY.out.log`
- stderr log: `C:\OCR\OCR\ocr-server\logs\codex_CODEX_FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_NO_PROD_MODIFY.err.log`
- known stderr noise: `ESLint: nextVitals is not iterable` if present with exit 0

## 17. 다음 작업 제안
1. `types.ts` -> `src/common/types/ocr.ts` micro-step
2. `ops.ts` -> `src/common/utils/ocrCanvasOps.ts` 또는 `ocrGeometry.ts`
3. `table.ts` -> `src/common/utils/ocrTableRegion.ts`, 단 column definition 설계와 분리
4. `export.ts` -> `components/template/utils/buildTemplateExportPayload.ts` 또는 `templateMapper.ts`
5. 이후 `OcrCanvasPane` -> `src/common/ui/OcrCanvasPane.tsx`
