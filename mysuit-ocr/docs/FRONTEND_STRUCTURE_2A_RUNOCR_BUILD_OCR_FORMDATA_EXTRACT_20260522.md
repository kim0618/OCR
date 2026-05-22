# FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522

## 1. 사용 도구 / 모델
- 도구: Claude Code (VSCode 확장)
- 모델: Claude Opus 4.7 (1M context)
- 작업명: FRONTEND-STRUCTURE-2A-RUNOCR-BUILD-OCR-FORMDATA-EXTRACT
- 실행 일자: 2026-05-22

## 2. 작업 목적
`RunOcrWorkspace.tsx` 의 `runOcr()` 안에 인라인으로 작성돼 있던 OCR 추출 요청용 FormData 구성 로직만 `src/components/runocr/utils/buildOcrFormData.ts` 로 분리. 기능 변경 없이 위치만 옮기는 RunOCR utils 분리 Phase 2A. API fetch / response mapping / history / restore / autofill / UI 분리는 범위 밖.

## 3. 백업 파일
- `backup/RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT.tsx`

## 4. 생성 파일
- `mysuit-ocr/src/components/runocr/utils/buildOcrFormData.ts` (신규, 25줄)
- `mysuit-ocr/tmp/check_runocr_formdata_keys_2a.mjs` (정적 key parity 검증용 스크립트, 운영 코드 미수정)

## 5. 수정 파일
- `mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx`
  - import 1줄 추가: `import { buildOcrFormData } from "./utils/buildOcrFormData";`
  - `runOcr()` 내 인라인 FormData 구성 블록(약 13줄) → `buildOcrFormData({...})` 단일 호출(약 9줄)로 치환
  - 그 외 본문/JSX/state/hook/import 구조 변화 없음

## 6. 추출한 FormData append key 목록 (변경 없음, 순서 보존)
| 순서 | key | 조건 | 값 |
|------|-----|------|----|
| 1 | `file` | 항상 | `selectedFile` (`File`) |
| 2 | `template_id` | `activeTemplateId` truthy | `activeTemplateId` (`string`) |
| 3 | `regions` | `useRegionTemplate && activeTemplate?.regions?.length` | `JSON.stringify(activeTemplate.regions)` |
| 4 | `model_id` | `isRunOcr` | `selectedModelId` (`string`) |
| 5 | `documentType` | `activeTemplate?.documentType` truthy | `activeTemplate.documentType` (`string`) |

코너 페이로드는 기존과 동일하게 주석으로 비활성화 상태 유지(`if (corners.length === 4) ...` 주석).

## 7. `buildOcrFormData` input 타입 요약
```ts
export type BuildOcrFormDataInput = {
  file: File;
  templateId?: string | null;
  useRegionTemplate: boolean;
  regions?: Region[];          // ../../ocr/core/types 재사용
  isRunOcr: boolean;
  modelId: string;
  documentType?: string | null;
};
```
- 순수 함수: React 의존성 없음 (`useState`/`useEffect`/`useRef` 등 import 없음, 컴포넌트 외부에서 단독 호출 가능)
- 외부 부수효과 없음 — 입력에서 `FormData` 인스턴스만 생성해 반환
- append 순서/조건/값/JSON.stringify 정책은 추출 전과 1:1 동일

## 8. 기존 `RunOcrWorkspace.tsx` 에 남긴 범위
- `runOcr()` 함수 자체 (validation guards, `setIsOcrRunning(true)`, `activeTemplate` 선택, `useRegionTemplate` 계산)
- `fetch(ocrEndpoint, ...)` 호출 및 backendBase 결정 로직
- response → `runResult` 매핑 (`buildRunOcrResult`, `raw_ocr_fields` 주입, `originalRunFields` 변환)
- autofill candidate/business number 매칭 로직 전체
- history append/update (`appendHistoryRun`, `updateHistoryRun`, `syncHistoryIndexAndDetailOnCreate`)
- restore/autofill summary 처리
- corner detect, preprocess info, revalidate/partial OCR FormData 블록 4종은 **별개 엔드포인트**라 이번 작업 범위 밖, 변경 없음

## 9. 변경하지 않은 범위 (의도된 미수정)
- `src/components/runocr/ui/OcrResultPanel.tsx`
- `src/components/runocr/ui/OcrDocViewer.tsx`
- `src/components/runocr/ui/CornerAdjust.tsx`
- `src/components/test/TestWorkspace.tsx`
- `src/lib/*` (invoiceTableDisplay, structuredTableViewModel, cleanJsonBuilder, markdownReportBuilder, ocrResultFormatters)
- backend / parser / templates.json / manifest / GT / fixtures
- `runOcrRequest.ts`, `mapOcrResponse.ts`, `useRunOcr.ts`, `RunOcrControls.tsx`, `RunOcrResultLayout.tsx` 신규 생성 없음 (별도 phase)

## 10. FormData key 동일성 확인
정적 분석 스크립트 `tmp/check_runocr_formdata_keys_2a.mjs` 가 backup tsx 와 신규 util 의 `formData.append("KEY", ...)` 키를 추출해 비교:

```
beforeKeys (backup runOcr inline block):  ["file","template_id","regions","model_id","documentType"]
afterUtilKeys (buildOcrFormData.ts):       ["file","template_id","regions","model_id","documentType"]
sameOrder:      true
sameSet:        true
inlineRemoved:  true  (post-extract RunOcrWorkspace.tsx 의 runOcr() 구간에 해당 key 들 append 잔존 없음)
callsBuilder:   true  (RunOcrWorkspace.tsx 에 buildOcrFormData(...) 호출 존재)
[FORMDATA_KEY_PARITY] PASS
```

## 11. runner 결과
| Runner | 결과 |
|--------|------|
| `node tmp/check_runocr_formdata_keys_2a.mjs` | PASS (key parity, order, inline removal, builder call) |
| `node tmp/check_table_view_model_v1_fixtures_js.mjs` | PASS 8/8 |
| `node tmp/check_clean_json_v1_fixtures_js.mjs` | PASS 9/9 (내부 typecheck=PASS, build=PASS) |
| `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_FORMDATA_EXTRACT_20260522` | PASS 6/6 (.venv python 사용) |

## 12. typecheck / build 결과
- `npm run typecheck` → PASS (exit 0)
- `npm run build` → PASS (exit 0, Next.js 15.5.4, 18/18 static pages, `/runocr` 65.6 kB / 184 kB — 사이즈 변화 미미 0.1KB 감소)

## 13. known stderr noise
- `⨯ ESLint: nextVitals is not iterable` — `npm run build` 시 stderr 에 등장, exit 0 (non-blocking)
- 시스템 python 의 `requests` 미설치 이슈는 `.venv/Scripts/python.exe` 사용으로 우회 — rename/extract 와 무관

## 14. 남은 이슈
- `runOcr()` 함수 본문은 여전히 600+ 줄(autofill/history/restore 매핑이 응집). 다음 phase 에서 단계적 분리 필요
- 다른 4종 FormData 사용처(corner / preprocess / revalidate / partial OCR)는 본 작업 범위 밖이라 인라인 유지

## 15. 다음 작업 제안
- RunOCR `runOcrRequest.ts` 분리 precheck 또는 추출 (fetch + 엔드포인트 결정 분리)
- `mapOcrResponse` 분리는 history/restore 얽힘 때문에 후순위
- `RunOcrControls.tsx` / `RunOcrResultLayout.tsx` UI split 은 request boundary 안정화 이후
- Template 폴더 ownership precheck
- `common/utils` 이동은 feature 폴더 안정화 후
- TestWorkspace 폴더 정비는 사용자 확인 후 진행
- 선택: revalidate/partial OCR 의 FormData 도 공통화 가능하지만 엔드포인트/파일 처리(blob vs file) 차이로 별 helper 권장
