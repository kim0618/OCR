# FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS_20260522

## 1. 사용 도구 / 모델
- 도구: Claude Code (VSCode 확장)
- 모델: Claude Opus 4.7 (1M context)
- 작업명: FRONTEND-STRUCTURE-3B-RUNOCR-DOC-COMMENTS
- 실행 일자: 2026-05-22

## 2. 작업 목적
RunOCR Cycle 1 구조 정리(폴더 이동 → naming → utils 분리 → layout split) 직후, 신규 유지보수자가 파일을 열었을 때 "이 파일이 무슨 역할인지", "이 함수가 어떤 흐름을 담당하는지", "수정 시 무엇을 조심해야 하는지" 를 바로 파악할 수 있도록 8개 운영 파일에 **파일 헤더 JSDoc + 핵심 export JSDoc** 을 추가. **comments-only patch** — 로직/JSX/import/state/handler 일체 미변경.

## 3. 백업 파일 (`backup/` 하위 8개)
- `RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx`
- `RunOcrResultLayout_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx`
- `OcrResultPanel_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx`
- `OcrDocViewer_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx`
- `CornerAdjust_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx`
- `buildOcrFormData_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.ts`
- `runOcrRequest_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.ts`
- `mapOcrResponse_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.ts`

## 4. 수정 파일 (8 운영 + 3 검증 보정)
**운영 코드 (comments-only):**
1. `mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx`
2. `mysuit-ocr/src/components/runocr/ui/RunOcrResultLayout.tsx`
3. `mysuit-ocr/src/components/runocr/ui/OcrResultPanel.tsx`
4. `mysuit-ocr/src/components/runocr/ui/OcrDocViewer.tsx`
5. `mysuit-ocr/src/components/runocr/ui/CornerAdjust.tsx`
6. `mysuit-ocr/src/components/runocr/utils/buildOcrFormData.ts`
7. `mysuit-ocr/src/components/runocr/utils/runOcrRequest.ts`
8. `mysuit-ocr/src/components/runocr/utils/mapOcrResponse.ts`

**검증 스크립트 보정 (tmp/, 운영 코드 무관):**
- `tmp/check_runocr_request_boundary_2b.mjs` — keyword leak 검사 시 주석 strip 적용
- `tmp/check_runocr_response_mapping_boundary_2c.mjs` — forbidden import 검사 시 주석 strip + buildOcrFormData byte-equal 비교 시 주석 strip + whitespace 정규화
- `tmp/check_runocr_doc_comments_3b.mjs` — 신규 생성

**신규 산출물:**
- `tmp/check_runocr_doc_comments_3b.mjs` (헤더 / 앵커 JSDoc / comments-only diff 정적 검증 스크립트)

## 5. 추가한 파일 header 요약

| 파일 | header 핵심 메시지 |
|------|--------------------|
| RunOcrWorkspace.tsx | RunOCR 탭 최상위 Workspace. 상태/실행 흐름/autofill+history orchestration, viewer/result 조립. 책임 경계: FormData=utils/buildOcrFormData, API=utils/runOcrRequest, mapping=utils/mapOcrResponse, layout=ui/RunOcrResultLayout. history/autofill/restore 는 아직 Workspace 가 보유. |
| RunOcrResultLayout.tsx | 결과 화면 layout 전용 presentational. viewer/resultPanel/scanOverlay/hiddenFileInput 4 node 만 배치. OCR 상태/API/history/autofill 모름. 자식 컴포넌트 직접 import 금지. |
| OcrResultPanel.tsx | OCR 결과 패널 (Preview/Custom/Validation/Clean JSON/Markdown/Raw JSON). 표시용 변환은 `@/lib/cleanJsonBuilder`/`markdownReportBuilder`/`structuredTableViewModel`/`invoiceTableDisplay` 위임. API/viewer/history 책임 없음. 재검증/부분 OCR 은 부모 콜백. |
| OcrDocViewer.tsx | OCR 대상 문서 viewer. 이미지/bbox/overlay/스케일. API/매핑/history 책임 없음. Custom 탭 편집은 OcrCanvasPane 담당, viewer 는 read-only. |
| CornerAdjust.tsx | normalized corner 보정 UI. 4 모서리 click-to-place + 드래그 보정. 외부 API 는 0~1 normalized, 내부 렌더는 px (toPixel/toNorm). API/매핑/history 책임 없음. |
| buildOcrFormData.ts | `/ocr/extract` FormData 구성 helper. 유지 key: `file`/`template_id`/`regions`/`model_id`/`documentType` (append 순서/조건 명시). key 변경 시 backend contract + key parity check 동시 검증 필요. |
| runOcrRequest.ts | OCR API 호출 helper (endpoint + buildOcrFormData + fetch + ok + json). UI loading/error/mapping/history/autofill 책임 없음. response shape 변환 없이 raw 반환. 에러 메시지 `"OCR 요청 실패"` 변경 금지. |
| mapOcrResponse.ts | raw → OcrResult 순수 mapping. autofill/history/restore/localStorage/React 의존 금지. `normalizeFieldKey` 는 autofillEngine 직접 import 회피용 의존성 주입 지점. output shape 변경 시 Preview/Custom/Validation/Clean JSON/Markdown 전부 영향 가능. |

## 6. 추가한 JSDoc 대상
| 파일 | JSDoc 추가 대상 |
|------|----------------|
| RunOcrWorkspace.tsx | `export default function RunOcrWorkspace`, `async function runOcr`, `const handlePersistEdits`, `const handleResultClose` |
| RunOcrResultLayout.tsx | `export type RunOcrResultLayoutProps`, `export default function RunOcrResultLayout` |
| OcrResultPanel.tsx | `export default function OcrResultPanel` (props 그룹 설명 포함) |
| OcrDocViewer.tsx | `export default function OcrDocViewer`, `const updateScale` |
| CornerAdjust.tsx | `export default function CornerAdjust` |
| buildOcrFormData.ts | `export type BuildOcrFormDataInput`, `export function buildOcrFormData` |
| runOcrRequest.ts | `export type RunOcrRequestInput`, `export async function runOcrRequest` |
| mapOcrResponse.ts | `export type BuildRunOcrResultTemplate`, `export type BuildRunOcrResultOptions`, `export function buildRunOcrResult` |

## 7. 과주석 방지 기준 준수 여부
- 단순 setter/toggle handler 에 주석 추가하지 않음
- JSX node 변수 / useMemo derived variable 에 주석 추가하지 않음
- props type 각 필드별 한 줄 주석 추가하지 않음 (OcrResultPanel 은 props 그룹 단위 요약만)
- 명확한 import/export 설명 반복 추가하지 않음
- 1~3줄짜리 자명한 local helper 에 주석 추가하지 않음
- 동일 설명을 여러 파일에 복붙하지 않음 (책임 경계만 cross-link 형식으로 짧게)

## 8. comments-only diff 확인
`tmp/check_runocr_doc_comments_3b.mjs` 가 8개 파일 각각에 대해:
- (a) 블록/라인 주석을 모두 strip
- (b) 모든 whitespace 시퀀스를 단일 공백으로 정규화
- (c) backup 본과 normalize-equal 비교

→ 8/8 모두 `commentsOnly: true` 확인. 실질적 로직/JSX/타입/import/export 변경 0건.

## 9. doc comments static check 결과
| 항목 | 결과 |
|------|------|
| 8개 파일 모두 file-top JSDoc 존재 (`/** ... */`) | ✓ (headerOk: true × 8) |
| 핵심 export 앵커 직전에 JSDoc 블록 존재 | ✓ (anchorOk: true × 8) |
| comments-only diff 무결성 | ✓ (commentsOnly: true × 8) |
| `RunOcrControls.tsx` 미생성 | ✓ |
| `src/components/test/TestWorkspace.tsx` 존재(sanity) | ✓ |
| **[RUNOCR_DOC_COMMENTS]** | **PASS** |

## 10. 기존 runner 결과 (재실행)
| Runner | 결과 |
|--------|------|
| `node tmp/check_runocr_doc_comments_3b.mjs` | PASS |
| `node tmp/check_runocr_formdata_keys_2a.mjs` | PASS |
| `node tmp/check_runocr_request_boundary_2b.mjs` | PASS (주석 strip 적용 후) |
| `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | PASS (주석 strip + buildOcrFormData byte-equal 완화 후) |
| `node tmp/check_runocr_result_layout_boundary_3a.mjs` | PASS |
| `node tmp/check_table_view_model_v1_fixtures_js.mjs` | PASS 8/8 |
| `node tmp/check_clean_json_v1_fixtures_js.mjs` | PASS 9/9 (내부 typecheck=PASS, build=PASS) |
| `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_DOC_COMMENTS_20260522` | PASS 6/6 (`.venv` python) |

**2B / 2C 검증 스크립트 보정 메모**:
- 두 스크립트는 원래 naive substring 매칭으로 키워드 leak / forbidden import 를 검사했다. 3B 가 JSDoc 으로 같은 키워드들을 *경계 설명용으로* 언급하면서 false-positive 가 발생.
- 운영 코드(`runOcrRequest.ts`, `mapOcrResponse.ts`) 는 그대로 두고, **검증 스크립트만** 주석 strip 후 검사하도록 보정. 검증 강도 (실제 코드 의존성/import 검사) 는 그대로 유지.
- `buildOcrFormData_unchanged_vs_2B_backup` 항목은 byte-equal → 주석 strip + whitespace 정규화 후 equal 로 완화. logic 동일성 invariant 는 유지하면서 doc comment 추가를 허용.

## 11. typecheck / build 결과
- `npm run typecheck` → PASS (exit 0)
- `npm run build` → PASS (exit 0, Next.js 15.5.4, 18/18 static pages, `/runocr` 65.7 kB / 184 kB — 3A 와 동일, 사이즈 변화 없음)

## 12. known stderr noise
- `⨯ ESLint: nextVitals is not iterable` — `npm run build` 시 stderr 에 등장, exit code 0 (non-blocking)
- 시스템 python 의 `requests` 미설치는 `.venv/Scripts/python.exe` 로 우회

## 13. 남은 이슈
- 이번 작업은 **doc comments only** 라 RunOCR 의 추가 분리/리팩토링은 진행되지 않음
- `runOcr()` 본문은 여전히 autofill/history/restore mapping 응집 (500+ 줄)
- 기본 화면 main return + `RunOcrControls` 분리는 별도 phase (props 폭발, HIGH risk)
- 2B/2C 검증 스크립트는 이제 주석 strip 기반이므로 향후 doc comments 추가 시 false-positive 없음. 새 검증 스크립트 작성 시 동일 패턴 적용 권장
- `ocr-server/data/templates.json` 은 여전히 dirty — 사용자 의도에 따른 별도 정리 필요

## 14. 다음 작업 제안
- **RunOCR Cycle 1 close-out 리포트** — 1 / 1B / 2A / 2B / 2C / 3A / 3B 통합 마무리
- Template 폴더 ownership precheck
- TPL-95328E52 등 dirty templates 영향 precheck
- `RunOcrControls` 분리는 작은 control group(template topbar / model card / run button bar) 단위로 precheck 후 진행
- `common/utils` 이동은 feature 폴더 안정화 후
- TestWorkspace 폴더 정비는 사용자 확인 후
