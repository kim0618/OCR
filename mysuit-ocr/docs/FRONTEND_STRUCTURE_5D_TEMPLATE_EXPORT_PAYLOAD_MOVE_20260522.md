# FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
OCR core ownership 정리의 네 번째 micro-step.
`src/components/ocr/core/export.ts`만
`src/components/template/utils/buildTemplateExportPayload.ts`로 이동하여
Template 저장 payload 전용 helper(`buildExportPayload`)를 Template 도메인 안으로
이전한다. 파일명은 책임을 명확히 반영하도록 변경하지만 **export 함수명
(`buildExportPayload`)은 유지**한다.

- `OcrCanvasPane.tsx`는 이동하지 않는다.
- 함수 본문은 byte-identical 유지 (self-import path는 depth가 일치하여 변경 없음).
- 영향 받은 파일은 import path만 보정한다 (OcrAnnotator 1곳).
- Template table column definition 정책(canonical column mapping, 사용자 확인 상태,
  저장 payload 변환 추가 정책 등)은 이 step에서 구현하지 않는다.
- `templateMapper.ts` 생성 금지.
- 5A/5B/5C 완료 후 진행: types → common/types/ocr, ops → common/utils/ocrCanvasOps,
  table → common/utils/ocrTableRegion.

## 3. 백업 파일
경로: `mysuit-ocr/backup/template_export_payload_20260522_before_FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE/`

| 파일 | bytes |
| --- | --- |
| `export.ts` | 3,290 |
| `OcrAnnotator.tsx` | 16,746 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/ocr/core/export.ts` | `src/components/template/utils/buildTemplateExportPayload.ts` | `git mv` | 본문 byte-identical. self-import 3줄 모두 depth 동일(`../../../common/...`)이라 변경 불필요. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/template/ui/OcrAnnotator.tsx` | `../../ocr/core/export` | `../utils/buildTemplateExportPayload` |

빈 `src/components/ocr/core/` 폴더는 자연 제거 (의미 없는 placeholder 파일 생성하지 않음).

5A/5B/5C/4A/4B 검사가 post-5D 상태를 그대로 인정하도록 다음 tmp 스크립트 보완:
- `tmp/check_template_workspace_move_4a.mjs` — `ocr_core_dir_untouched_path`를
  always-true로 (5A~5D에서 core dir 비워짐).
- `tmp/check_template_editor_ui_move_4b.mjs` — `ocr_core_dir_untouched_path`
  always-true, `annotator_imports_core_via_ocr`에 새 export 경로 양쪽 허용.
- `tmp/check_ocr_core_types_common_move_5a.mjs` — `EXPORT` 경로 자동 탐지.
- `tmp/check_ocr_core_ops_common_move_5b.mjs` — `EXPORT` 경로 자동 탐지.
- `tmp/check_ocr_core_table_common_move_5c.mjs` — `EXPORT` 경로 자동 탐지,
  `template_utils_dir_not_introduced` 가드를 "buildTemplateExportPayload.ts만 있는
  경우 OK"로 완화.

## 6. 핵심 변경 내용
- `buildExportPayload` 함수 본문/시그니처/타입 그대로, 파일명만
  `buildTemplateExportPayload.ts`로 변경. export 식별자는 동일.
- 새 파일은 `common/types/ocr`, `common/utils/ocrCanvasOps`,
  `common/utils/ocrTableRegion`만 참조. `components/*` 의존 없음.
- `src/components/ocr/core/` 폴더는 모든 파일이 이동했으므로 제거.
  이제 `src/components/ocr/`에는 `OcrCanvasPane.tsx`만 남는다.
- `tmp/check_template_export_payload_move_5d.mjs` 신규 작성 — 31개 검증 항목,
  잔여 `./export`/`../export`/`ocr/core/export`/`ocr/core` 문자열 src 전역 스캔
  포함, Template policy 가드 포함.

## 7. 이동하지 않은 파일 (계약 유지)
- `src/components/ocr/OcrCanvasPane.tsx` — 완전 미수정 (export.ts를 사용하지 않음).
- `src/components/template/ui/OcrRightPanel.tsx` — 완전 미수정.
- `src/components/template/ui/OcrAnnotator.tsx` — import path 한 줄만 변경, 다른 모든 코드는 byte-identical.
- `src/components/runocr/*` — 완전 미수정.
- `src/components/test/TestWorkspace.tsx`, `src/components/test/core/*` — 완전 미수정.
- `src/common/types/ocr.ts` (5A), `src/common/utils/ocrCanvasOps.ts` (5B),
  `src/common/utils/ocrTableRegion.ts` (5C) — 유지.

## 8. template/utils boundary 확인
`src/components/template/utils/buildTemplateExportPayload.ts` 검증 (5D 스크립트):

| 항목 | 결과 |
| --- | --- |
| `from "components/*"` import | 없음 (다른 components 도메인 미참조) |
| `from "components/runocr/*"` / `from "components/test/*"` | 없음 |
| `from "react"` | 없음 |
| `window` / `document` / `localStorage` | 없음 |
| `common/types/ocr` import | 있음 |
| `common/utils/ocrCanvasOps` import | 있음 |
| `common/utils/ocrTableRegion` import | 있음 |
| 백업 대비 logic equivalence (path 제외) | 동일 |
| `export function buildExportPayload` | 보존 |

또한 `common/types/ocr.ts`, `common/utils/ocrCanvasOps.ts`,
`common/utils/ocrTableRegion.ts` 모두 `components/*` 미참조 invariant 재확인됨.

## 9. src/components/ocr/core 상태
- 폴더 자체가 제거됨 (의미 없는 placeholder 파일 생성 없음).
- `src/components/ocr/` 디렉터리에는 `OcrCanvasPane.tsx`만 남아 있다.
- src 전역에 `./export` / `../export` / `ocr/core/export` / `ocr/core` 문자열 잔존 0건.

## 10. Template table column definition 미구현 확인
- `src/components/template/utils/templateMapper.ts` — 미생성.
- `src/components/template/ui/TemplateTableColumnEditor.tsx` — 미생성.
- `buildTemplateExportPayload.ts` 본문 스캔 결과 다음 신규 정책 식별자 모두 0건:
  `canonicalColumn`, `userConfirmed`, `columnMappingStatus`, `columnCandidates`.
- 기존부터 존재하던 passthrough field(`canonicalField`, `mappingStatus`)는
  Region 타입의 forwarding이라 신규 정책이 아니며, 본 작업은 이들에 손대지
  않았다.

## 11. static check 결과 (5D 신규 스크립트)
- 파일: `tmp/check_template_export_payload_move_5d.mjs`
- 명령: `node tmp/check_template_export_payload_move_5d.mjs`
- 결과: **PASS** (31/31 checks, skippedBackupChecks=0, residuals=0)

## 12. runner 결과 (17개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522` | **PASS** (6/6) | overall PASS, exit 0 |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2A backup absent |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | exit 0 |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2B backup absent |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | exit 0 |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 3B backups absent |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | post-5D core dir 부재 허용 패치 적용 |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | post-5D core dir 부재 + export 경로 양쪽 허용 패치 적용 |
| 13 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | EXPORT 경로 fallback 패치 적용 |
| 14 | `node tmp/check_ocr_core_ops_common_move_5b.mjs` | **PASS** | EXPORT 경로 fallback 패치 적용 |
| 15 | `node tmp/check_ocr_core_table_common_move_5c.mjs` | **PASS** | EXPORT 경로 fallback + template/utils 가드 완화 |
| 16 | `node tmp/check_template_export_payload_move_5d.mjs` | **PASS** | 31/31 |
| 17 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 14개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS 또는
PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 13. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE.err.log`

## 14. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 15. 남은 이슈
- 과거 phase(2A/2B/3B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`으로 처리되고 있다. 5D와 무관한 사전 상태.
- 5D 시점에서 4A/4B 검사도 backup 부재가 그대로 남아 있다 (PASS_WITH_SKIPPED_BACKUP).
- `src/components/ocr/` 디렉터리에는 이제 `OcrCanvasPane.tsx`만 남아 있다.
  다음 phase로 `OcrCanvasPane → common/ui` 이동을 고려할 수 있다.
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존 (실제 import 아님, 동작 무영향, 후속 cleanup 후보).

## 16. 다음 작업 제안 (소단위 micro-step 권장)
- `OcrCanvasPane → common/ui` 이동 precheck (이제 OCR 도메인 의존이 모두
  common 으로 분리되었으므로 가장 자연스러운 다음 단계).
- Template table column definition 설계 precheck (canonical column mapping,
  사용자 확인 상태, 저장 payload 변환 등의 신규 정책 — 별도
  `components/template/utils/` 또는 store layer로 분리).
- TPL-95328E52 dirty 영향 precheck.
- `src/lib/profiles.ts` doc-comment 잔존 정리.
- TestWorkspace 정리는 사용자 확인 후 진행.
