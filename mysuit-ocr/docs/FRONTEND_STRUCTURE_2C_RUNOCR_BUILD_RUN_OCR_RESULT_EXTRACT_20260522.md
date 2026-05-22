# FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522

## 1. 사용 도구 / 모델
- 도구: Claude Code (VSCode 확장)
- 모델: Claude Opus 4.7 (1M context)
- 작업명: FRONTEND-STRUCTURE-2C-RUNOCR-BUILD-RUN-OCR-RESULT-EXTRACT
- 실행 일자: 2026-05-22

## 2. 작업 목적
`RunOcrWorkspace.tsx` 의 `buildRunOcrResult` (raw OCR response → `OcrResult` 매핑) 순수 함수만 `src/components/runocr/utils/mapOcrResponse.ts` 로 분리. autofill/history/restore/setOcrResult/UI split 은 범위 밖.

## 3. 백업 파일
- `backup/RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT.tsx`
- (2B 백업 `backup/buildOcrFormData_20260522_before_FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT.ts` 는 boundary check 의 동일성 baseline 으로 재사용)

## 4. 생성 파일
- `mysuit-ocr/src/components/runocr/utils/mapOcrResponse.ts` (신규, 116줄)
- `mysuit-ocr/tmp/check_runocr_response_mapping_boundary_2c.mjs` (정적 boundary 검증, 운영 코드 미수정)

## 5. 수정 파일
- `mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx`
  - import 1줄 추가: `import { buildRunOcrResult } from "./utils/mapOcrResponse";`
  - 인라인 함수 정의 91줄 (line 436-527, `function buildRunOcrResult(raw: any, template?: TemplateItem): OcrResult { … }`) 제거 (이동 표시용 3줄 주석으로 대체)
  - 호출부(`buildRunOcrResult(json, activeTemplate)`) → `buildRunOcrResult(json, activeTemplate, { normalizeFieldKey: normalizeAutofillFieldKey })` 로 옵션 1개 추가
  - 그 외 본문 / JSX / state / hook / API / autofill / history / restore / setOcrResult 흐름 전부 미변경

## 6. 이동한 함수 / 헬퍼 목록
| 이름 | 종류 | 처리 |
|------|------|------|
| `buildRunOcrResult` | 함수 | 그대로 이동 (시그니처에 optional 3rd `options` 추가) |
| `RECEIPT_ALIAS` 상수 | 함수 내부 const | 그대로 이동 (mapOcrResponse 함수 내부 const 로 유지) |
| `pickValue` 헬퍼 | 함수 내부 const | 그대로 이동 (mapOcrResponse 함수 내부 const 로 유지) |
| `normalizeAutofillFieldKey` | autofillEngine 헬퍼 | **이동하지 않음** — caller (RunOcrWorkspace.tsx) 가 `options.normalizeFieldKey` 로 주입 |

## 7. mapOcrResponse boundary
- 위치: `src/components/runocr/utils/mapOcrResponse.ts`
- export:
  - `BuildRunOcrResultTemplate` (structural minimal 타입; `mode?`, `regions?`, `fields?` 만 사용)
  - `BuildRunOcrResultOptions` (`{ normalizeFieldKey?: (field: string) => string }`)
  - `buildRunOcrResult(raw, template?, options?)` 함수 (반환 `OcrResult`)
- 외부 import:
  - `OcrResult`, `OcrFieldResult` from `../ui/OcrResultPanel`
- 금지된 import (전부 없음 — boundary check 확인):
  - React, useState/useEffect/useMemo/useRef/useRouter
  - localStorage
  - `@/lib/autofillEngine`, `@/lib/historyStore`, `@/lib/restoreProfileStore`, `@/lib/imageStore`
  - setOcrResult/setCurrentJobId/setCurrentCreatedAt
  - appendHistoryRun/updateHistoryRun/syncHistoryIndexAndDetailOnCreate
- 의존성 방향: `RunOcrWorkspace.tsx` → `mapOcrResponse.ts` (단방향, 순환 없음)

## 8. RunOcrWorkspace 에 남긴 범위
- 인라인 `TemplateItem` 타입 정의 (광범위 필드 — runocr 전반에서 사용)
- 호출부: `buildRunOcrResult(json, activeTemplate, { normalizeFieldKey: normalizeAutofillFieldKey })`
- `normalizeAutofillFieldKey` import 및 호출 (autofillEngine 직접 참조는 workspace 에 유지)
- raw 응답 후속 처리:
  - `Array.isArray(json?.fields) ? ...` rawOcrFields 추출
  - `runResult.raw_ocr_fields = rawOcrFields` 부착
  - `originalRunFields` source-label 변환
- autofill 흐름: `extractBizNumber`, `collectInternalAutofillCandidates`, `buildAutofillSuggestionsFromCandidates`, `applyAutofillToOutputFields`, summary 구성
- history 흐름: `appendHistoryRun`, `updateHistoryRun`, `syncHistoryIndexAndDetailOnCreate`
- state 흐름: `setOcrResult`, `setCurrentJobId`, `setCurrentCreatedAt`, `setInitialOutputFields`, `setIsOcrRunning`
- `try / catch / finally` 전체 — 메시지/구조 모두 보존

## 9. 변경하지 않은 범위 (의도된 미수정)
- `src/components/runocr/utils/runOcrRequest.ts` (byte-for-byte 동일, boundary check 로 검증)
- `src/components/runocr/utils/buildOcrFormData.ts` (byte-for-byte 동일, 2B 백업과 SHA 매칭)
- `src/components/runocr/ui/OcrResultPanel.tsx`
- `src/components/runocr/ui/OcrDocViewer.tsx`
- `src/components/runocr/ui/CornerAdjust.tsx`
- `src/components/test/TestWorkspace.tsx`
- `src/lib/*` (autofillEngine 포함 — workspace 만 import 함)
- backend / parser / templates 변환 로직 / fixtures

## 10. response mapping static check 결과
`tmp/check_runocr_response_mapping_boundary_2c.mjs`:

| 항목 | 결과 |
|------|------|
| `mapOcrResponse.ts` 존재 | ✓ |
| `export function buildRunOcrResult` | ✓ |
| `RunOcrWorkspace.tsx` 가 `./utils/mapOcrResponse` 에서 import | ✓ |
| `RunOcrWorkspace.tsx` 에 `function buildRunOcrResult(` 정의 잔존 없음 | ✓ |
| `RunOcrWorkspace.tsx` 가 여전히 `buildRunOcrResult(` 호출 | ✓ |
| `mapOcrResponse.ts` 에 forbidden import 없음 (offenders: `[]`) | ✓ |
| `RunOcrWorkspace.tsx` 가 여전히 autofill/history 키워드 보유 (`appendHistoryRun`, `updateHistoryRun`, `syncHistoryIndexAndDetailOnCreate`, `AutofillSuggestion`, `AutofillRunSummary`, `setOcrResult`) | ✓ |
| `buildOcrFormData.ts` 가 2B 백업과 byte-for-byte 동일 | ✓ |
| `runOcrRequest.ts` 가 여전히 `buildOcrFormData` import | ✓ |
| `mapOcrResponse.ts` 가 `runOcrRequest` import 안 함 (순환 방지) | ✓ |
| `mapOcrResponse.ts` 가 `RunOcrWorkspace` import 안 함 (순환 방지) | ✓ |
| **[RUNOCR_RESPONSE_MAPPING_BOUNDARY]** | **PASS** |

## 11. 기존 runner 결과
| Runner | 결과 |
|--------|------|
| `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | PASS |
| `node tmp/check_runocr_formdata_keys_2a.mjs` | PASS (2B-aware) |
| `node tmp/check_runocr_request_boundary_2b.mjs` | PASS |
| `node tmp/check_table_view_model_v1_fixtures_js.mjs` | PASS 8/8 |
| `node tmp/check_clean_json_v1_fixtures_js.mjs` | PASS 9/9 (내부 typecheck=PASS, build=PASS) |
| `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_RESPONSE_MAPPING_2C_20260522` | **FAIL 5/6** (단일 case `trade_7_7pdf`) |

### markdown FAIL 원인 분석
`trade_7_7pdf` 의 line 9 diff:
- actual: `| 2 | 공급받는자 사업자 번호 (field_2) | 113-85-04425 | 100.0% | OCR |`
- expected: `| 2 | 공급받는자 사업자 번호 (field_2) | (113-85-04425) | 97.1% | OCR |`

이 차이는 **2C 와 무관**:
- 2C 변경은 frontend(`RunOcrWorkspace.tsx`)의 `buildRunOcrResult` 함수 위치만 옮긴 것
- markdown fixture runner 는 백엔드 `http://127.0.0.1:9099/ocr/extract` 를 Python 으로 직접 호출 — React frontend 흐름을 전혀 거치지 않음
- 현재 working tree 에 `M ocr-server/data/templates.json` 가 별도로 dirty 상태 (TPL-3AFD383E 의 region field_3/4/5 bbox 가 픽셀 단위로 이동 — `x: 937→945`, `y: 280→` 등). 이 템플릿 좌표 수정이 backend OCR 결과 값/confidence 를 미세하게 바꿨고, 이로 인해 fixture 가 drift 됨
- 2B 직전 markdown 은 6/6 PASS 였고, 본 2C 가 frontend 만 건드렸으므로 trade_7_7pdf 의 drift 는 templates.json 사전 변경에 기인

조치: 본 작업 범위 밖. 별도 manifest/GT 또는 fixture rebake 단계에서 처리해야 함.

## 12. typecheck / build 결과
- `npm run typecheck` → PASS (exit 0)
- `npm run build` → PASS (exit 0, Next.js 15.5.4, 18/18 static pages, `/runocr` 65.7 kB / 184 kB — 2B 대비 +0.1 KB 미세 증가)

## 13. known stderr noise
- `⨯ ESLint: nextVitals is not iterable` — `npm run build` 시 stderr 에 등장, exit 0 (non-blocking)
- 시스템 python 의 `requests` 미설치는 `.venv/Scripts/python.exe` 로 우회. extract 와 무관

## 14. 남은 이슈
- **markdown fixture `trade_7_7pdf` drift** — 별도 dirty `templates.json` 의 region 좌표 변경 영향. 2C 와 인과 없음. fixture rebake 또는 template rollback 필요
- `runOcr()` 본문은 여전히 autofill/history/restore mapping 으로 600+ 줄. UI split, history adapter, restore adapter 분리는 별도 phase
- `buildRunOcrResult` 반환 타입 `OcrResult` 는 보존되었으나 input `raw` 는 `any` 유지 (downstream 사용 패턴 보존). 추후 backend response 타입이 좁아지면 narrow 가능

## 15. 다음 작업 제안
- UI split precheck — `RunOcrControls.tsx` / `RunOcrResultLayout.tsx`
- `history` adapter (appendHistoryRun/updateHistoryRun 호출 묶음) 분리 precheck
- `restore` / autofill orchestration adapter 분리 precheck (가장 마지막 — state 결합도 높음)
- Template 폴더 ownership precheck
- `common/utils` 이동은 feature 폴더 안정화 후
- TestWorkspace 폴더 정비는 사용자 확인 후 진행
- 별도: 현재 dirty `templates.json` 정리 또는 fixture rebake (drift 해결)
