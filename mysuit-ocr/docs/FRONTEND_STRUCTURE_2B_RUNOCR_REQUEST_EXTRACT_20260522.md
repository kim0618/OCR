# FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522

## 1. 사용 도구 / 모델
- 도구: Claude Code (VSCode 확장)
- 모델: Claude Opus 4.7 (1M context)
- 작업명: FRONTEND-STRUCTURE-2B-RUNOCR-REQUEST-EXTRACT
- 실행 일자: 2026-05-22

## 2. 작업 목적
`RunOcrWorkspace.tsx` 의 `runOcr()` 내부 OCR `/ocr/extract` API 요청 경계(endpoint 결정 + `fetch` + `!res.ok` + `res.json()`)만 `src/components/runocr/utils/runOcrRequest.ts` 로 분리. 2A 에서 만든 `buildOcrFormData` 를 `runOcrRequest` 내부에서 호출. loading/error UI state, response mapping, history/restore/autofill, UI split 은 범위 밖.

## 3. 백업 파일
- `backup/RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT.tsx`
- `backup/buildOcrFormData_20260522_before_FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT.ts`

## 4. 생성 파일
- `mysuit-ocr/src/components/runocr/utils/runOcrRequest.ts` (신규, 21줄)
- `mysuit-ocr/tmp/check_runocr_request_boundary_2b.mjs` (정적 boundary 검증 스크립트, 운영 코드 미수정)

## 5. 수정 파일
- `mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx`
  - import 교체: `buildOcrFormData` → `runOcrRequest` (이 컴포넌트는 더 이상 `buildOcrFormData` 를 직접 호출하지 않음)
  - `runOcr()` 안의 `buildOcrFormData(...)` → `ocrEndpoint` 계산 → `fetch` → `!res.ok` → `res.json()` 18줄 블록을 `await runOcrRequest({...})` 단일 호출 9줄로 치환
  - 비활성화된 corner 페이로드 주석은 그대로 유지
  - 그 외 본문 / JSX / state / hook / API 흐름 / mapping / autofill / history / catch / finally 모두 미변경
- `mysuit-ocr/tmp/check_runocr_formdata_keys_2a.mjs`
  - 2A 검증 스크립트의 `callsBuilder` 조건을 "workspace 가 buildOcrFormData 를 **직접** 호출" → "직접 호출 OR runOcrRequest 호출 중 하나" 로 완화. 운영 코드 무관, tmp 검증 스크립트만 minor 보정 (PASS 회복용)

## 6. runOcrRequest boundary
| 항목 | 위치 |
|------|------|
| endpoint 결정 | `runOcrRequest.ts` — `input.endpoint ?? (backendBase ? \`${backendBase}/ocr/extract\` : "/api/ocr-extract")` |
| FormData 생성 | `runOcrRequest.ts` — `buildOcrFormData(input)` |
| `fetch(POST, body=formData)` | `runOcrRequest.ts` |
| `!res.ok` → `throw new Error("OCR 요청 실패")` | `runOcrRequest.ts` (메시지 동일) |
| `await res.json()` | `runOcrRequest.ts` — raw JSON 그대로 반환 |
| try/catch/finally, loading state, mapping, history, autofill, restore | **그대로 RunOcrWorkspace.tsx 에 유지** |

## 7. input / output 타입
```ts
import { buildOcrFormData, type BuildOcrFormDataInput } from "./buildOcrFormData";

export type RunOcrRequestInput = BuildOcrFormDataInput & {
  endpoint?: string;
};

export type RunOcrRawResponse = Record<string, unknown>;

// 반환 타입은 의도적으로 `any`. 사유: 이전 인라인 `await res.json()` 동작과
// 1:1 parity 를 유지해야 downstream(`json?.full_text`, `json?.receipt_fields?.["사업자번호"]`,
// `buildRunOcrResult(json, ...)`)의 매핑/타입 흐름을 전혀 건드리지 않을 수 있음.
// `RunOcrRawResponse` 는 narrow 하고 싶은 호출자가 선택적으로 사용할 수 있는 별칭.
export async function runOcrRequest(input: RunOcrRequestInput): Promise<any> { ... }
```

`endpoint` 는 optional override 만 추가 — 미지정 시 기존 정책(`NEXT_PUBLIC_BACKEND_URL` 유무에 따른 `/ocr/extract` vs `/api/ocr-extract`)을 그대로 유지.

## 8. RunOcrWorkspace 에 남긴 범위 (mapping/state/history)
- `runOcr()` 함수 자체 (validation guards, `setIsOcrRunning(true)`, `activeTemplate` 선택, `useRegionTemplate` 계산)
- `runOcrRequest(...)` 호출 결과 `json` 변수
- `Array.isArray(json?.fields) ? ... : []` → `rawOcrFields` 추출
- `buildRunOcrResult(json, activeTemplate)` → `runResult` 매핑
- `originalRunFields` 가공 (source 라벨 변환)
- 사업자번호 추출 및 internal autofill candidate 수집/적용 (`extractBizNumber`, `collectInternalAutofillCandidates`, `buildAutofillSuggestionsFromCandidates`, `applyAutofillToOutputFields`)
- `appendHistoryRun`, `updateHistoryRun`, `syncHistoryIndexAndDetailOnCreate`
- `setOcrResult`, `setCurrentJobId`, `setCurrentCreatedAt`, `setInitialOutputFields`
- `try / catch (await ui.alert("OCR 처리 중 오류가 발생했습니다.")) / finally (setIsOcrRunning(false))` 전체 — 메시지/구조 모두 보존

## 9. 변경하지 않은 범위 (의도된 미수정)
- `src/components/runocr/ui/OcrResultPanel.tsx`
- `src/components/runocr/ui/OcrDocViewer.tsx`
- `src/components/runocr/ui/CornerAdjust.tsx`
- `src/components/test/TestWorkspace.tsx`
- `src/lib/*` 전체
- backend / parser / templates.json / manifest / GT / fixtures
- `buildOcrFormData.ts` 운영 동작 (시그니처/로직 모두 변경 없음, 백업과 byte-for-byte 동일)
- `mapOcrResponse.ts`, `useRunOcr.ts`, `RunOcrControls.tsx`, `RunOcrResultLayout.tsx` 신규 생성 없음

## 10. FormData key parity 결과
`tmp/check_runocr_formdata_keys_2a.mjs` (2B 적용 후 `callsBuilder` 조건만 살짝 완화):

```
beforeKeys (2A backup):   ["file","template_id","regions","model_id","documentType"]
afterUtilKeys (util):     ["file","template_id","regions","model_id","documentType"]
sameOrder:      true
sameSet:        true
inlineRemoved:  true
callsBuilder:   true  (workspace 가 runOcrRequest 를 호출 → 내부에서 buildOcrFormData 호출 — 간접 경로 인정)
[FORMDATA_KEY_PARITY] PASS
```

키 / 순서 / 조건 / 값 정책은 2A 결과 그대로 보존.

## 11. request boundary static check 결과
`tmp/check_runocr_request_boundary_2b.mjs`:

| 항목 | 결과 |
|------|------|
| runOcrRequest.ts imports buildOcrFormData | true |
| runOcrRequest.ts has `fetch(` | true |
| runOcrRequest.ts has `!res.ok` | true |
| runOcrRequest.ts has error message `"OCR 요청 실패"` | true |
| runOcrRequest.ts exports `runOcrRequest` | true |
| RunOcrWorkspace.tsx no direct `fetch(ocrEndpoint…)` / `/ocr/extract` / `/api/ocr-extract` | true |
| RunOcrWorkspace.tsx calls `runOcrRequest(` | true |
| RunOcrWorkspace.tsx no local `const ocrEndpoint =` | true |
| runOcrRequest.ts 안에 mapping/history/autofill leak 없음 (`buildRunOcrResult`/`appendHistoryRun`/`setOcrResult`/`raw_ocr_fields` 등) | true (leaked keywords: `[]`) |
| RunOcrWorkspace.tsx 가 여전히 `buildRunOcrResult(` 호출 | true |
| buildOcrFormData.ts 가 runOcrRequest 를 import 하지 않음 (순환 방지) | true |
| error message parity | true |
| **[RUNOCR_REQUEST_BOUNDARY]** | **PASS** |

## 12. runner 결과
| Runner | 결과 |
|--------|------|
| `node tmp/check_runocr_request_boundary_2b.mjs` | PASS |
| `node tmp/check_runocr_formdata_keys_2a.mjs` | PASS (2B-aware) |
| `node tmp/check_table_view_model_v1_fixtures_js.mjs` | PASS 8/8 |
| `node tmp/check_clean_json_v1_fixtures_js.mjs` | PASS 9/9 (내부 typecheck=PASS, build=PASS) |
| `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_REQUEST_EXTRACT_20260522` | PASS 6/6 (`.venv` python) |

## 13. typecheck / build 결과
- `npm run typecheck` → PASS (exit 0)
- `npm run build` → PASS (exit 0, Next.js 15.5.4, 18/18 static pages, `/runocr` 65.6 kB / 184 kB — 사이즈 변화 없음)

## 14. known stderr noise
- `⨯ ESLint: nextVitals is not iterable` — `npm run build` 시 stderr 에 등장, exit code 0 (non-blocking)
- 시스템 python 의 `requests` 미설치는 `.venv/Scripts/python.exe` 로 우회. boundary extract 와 무관

## 15. 남은 이슈
- `runOcr()` 본문은 여전히 mapping/autofill/history 가 응집된 상태. 다음 단계(`mapOcrResponse` 분리, UI split)에서 다룰 필요
- `runOcrRequest` 반환 타입을 `any` 로 둔 이유는 downstream `json?.full_text`, `json?.receipt_fields?.["사업자번호"]`, `buildRunOcrResult(json, …)` 호출 흐름을 무손실 보존하기 위함. 나중에 `mapOcrResponse` 가 분리될 때 명시 타입(`RunOcrRawResponse` 등)으로 좁힐 수 있음
- 다른 4개 FormData 사용처(corner / preprocess / revalidate / partial OCR)는 별 엔드포인트라 본 작업에서 통합하지 않음

## 16. 다음 작업 제안
- `mapOcrResponse` 분리 precheck — history/restore/autofill 얽힘 분석부터
- `RunOcrControls.tsx` / `RunOcrResultLayout.tsx` UI split (request boundary 안정화 후)
- Template 폴더 ownership precheck
- `common/utils` 이동은 feature 폴더 안정화 후
- TestWorkspace 폴더 정비는 사용자 확인 후 진행
- 선택: `runOcrRequest` 반환 타입을 단계적으로 `RunOcrRawResponse` 로 narrow 후 호출부에서 명시 cast
