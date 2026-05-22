# FRONTEND_STRUCTURE_3A_RUNOCR_RESULT_LAYOUT_SPLIT_20260522

## 1. 사용 도구 / 모델
- 도구: Claude Code (VSCode 확장)
- 모델: Claude Opus 4.7 (1M context)
- 작업명: FRONTEND-STRUCTURE-3A-RUNOCR-RESULT-LAYOUT-SPLIT
- 실행 일자: 2026-05-22

## 2. 작업 목적
`RunOcrWorkspace.tsx` 의 OCR 결과 화면 branch(line 1114-1226) 의 layout wrapper 만 `src/components/runocr/ui/RunOcrResultLayout.tsx` 로 node composition 방식으로 분리. state / handler / request / mapping / history / autofill 은 절대 이동하지 않음. `RunOcrControls` 는 이번 phase 범위 밖 (생성 금지).

## 3. 백업 파일
- `backup/RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_3A_RUNOCR_RESULT_LAYOUT_SPLIT.tsx`

## 4. 생성 파일
- `mysuit-ocr/src/components/runocr/ui/RunOcrResultLayout.tsx` (신규, 35줄)
- `mysuit-ocr/tmp/check_runocr_result_layout_boundary_3a.mjs` (정적 boundary 검증, 운영 코드 미수정)

## 5. 수정 파일
- `mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx`
  - import 1줄 추가: `import RunOcrResultLayout from "./ui/RunOcrResultLayout";`
  - 결과 branch 내부에서 4개 JSX node 변수(`resultViewerNode`, `resultScanOverlayNode`, `resultPanelNode`, `resultHiddenFileInputNode`) 구성
  - 기존 `<div className="uw-result-root">…</div>` 직접 렌더링을 `<RunOcrResultLayout viewer={…} resultPanel={…} scanOverlay={…} hiddenFileInput={…} />` 로 치환
  - **모든 JSX, prop, 조건부 렌더링, inline handler(`onRevalidate`, `onPartialOcr`, `onChange`), className, style 은 그대로 보존**
  - 기본 화면 main return (line 1228 이후) 미수정

## 6. RunOcrResultLayout props
```tsx
export type RunOcrResultLayoutProps = {
  viewer: React.ReactNode;
  resultPanel: React.ReactNode;
  scanOverlay?: React.ReactNode;
  hiddenFileInput?: React.ReactNode;
};
```
- 4개 props 전부 `React.ReactNode` — node composition 원칙 100% 준수
- state/handler/concrete component 타입 의존 0개
- `OcrResult` / `OcrFieldResult` / `FieldType` / `Corner` / `Region` 등 도메인 타입 의존 없음

## 7. node composition 적용 내용
호출 측(워크스페이스) 흐름:
```tsx
if (ocrResult && selectedFile) {
  const resultViewerNode = /* OcrCanvasPane | OcrDocViewer | <span> 3-way 조건부 */;
  const resultScanOverlayNode = isOcrRunning ? <div className="uw-scan-overlay">…</div> : null;
  const resultPanelNode       = <OcrResultPanel … />;
  const resultHiddenFileInputNode = <input ref={fileInputRef} … />;

  return (
    <RunOcrResultLayout
      viewer={resultViewerNode}
      resultPanel={resultPanelNode}
      scanOverlay={resultScanOverlayNode}
      hiddenFileInput={resultHiddenFileInputNode}
    />
  );
}
```

Layout 내부:
```tsx
<div className="uw-result-root">
  <div className="uw-result-doc" style={{ position: "relative" }}>
    {viewer}
    {scanOverlay}
  </div>
  <div className="uw-result-panel">{resultPanel}</div>
  {hiddenFileInput}
</div>
```
- DOM 구조(`uw-result-root` / `uw-result-doc` / `uw-result-panel`) 완벽 보존
- `position: relative` 인라인 스타일 보존
- `uw-scan-overlay` 위치 / 조건(`isOcrRunning`) 모두 그대로 — workspace 가 `isOcrRunning ? … : null` 분기로 외부에서 결정

## 8. 변경하지 않은 범위 (의도된 미수정)
- `src/components/runocr/ui/OcrResultPanel.tsx` (export default function 정상, boundary check 통과)
- `src/components/runocr/ui/OcrDocViewer.tsx` (export default function 정상, boundary check 통과)
- `src/components/runocr/ui/CornerAdjust.tsx` (export default function 정상, boundary check 통과)
- `src/components/runocr/utils/buildOcrFormData.ts`
- `src/components/runocr/utils/runOcrRequest.ts`
- `src/components/runocr/utils/mapOcrResponse.ts`
- `src/components/test/TestWorkspace.tsx`
- `src/lib/*`
- backend / parser / templates / fixtures
- `RunOcrControls.tsx` 미생성 — boundary check 로 확인
- `RunOcrWorkspace.tsx` 의 기본 화면 main return, state/hook/handler/`runOcr()`/autofill/history/restore 흐름 100% 미변경

## 9. layout boundary static check 결과
`tmp/check_runocr_result_layout_boundary_3a.mjs`:

| 항목 | 결과 |
|------|------|
| `RunOcrResultLayout.tsx` 존재 | ✓ |
| `RunOcrControls.tsx` 생성되지 않음 | ✓ |
| props 4종(`viewer`, `resultPanel`, `scanOverlay`, `hiddenFileInput`) 모두 정의 | ✓ |
| Layout 에 heavy domain type(`OcrResult`/`OcrFieldResult`/`FieldType`/`Corner`/`Region`) 부재 (단어 경계 + 주석 strip 후 검사) | ✓ |
| Layout 이 `OcrDocViewer`/`OcrResultPanel`/`CornerAdjust` 를 import 하지 않음 | ✓ |
| Layout 에 `fetch(`/history/autofill/runOcrRequest/buildOcrFormData/mapOcrResponse/buildRunOcrResult/useState/useEffect/useMemo/useRef/useRouter/localStorage/setOcrResult 키워드 없음 | ✓ (forbidden: `[]`) |
| Workspace 가 `RunOcrResultLayout` import | ✓ |
| Workspace 가 `<RunOcrResultLayout …>` 렌더 | ✓ |
| Workspace 가 여전히 `async function runOcr`/autofill/history/`setOcrResult`/`useState`/`useEffect` 보유 | ✓ |
| Workspace 에 `<div className="uw-result-root">` 인라인 잔존 없음 | ✓ |
| `OcrResultPanel`/`OcrDocViewer`/`CornerAdjust` export default function 정상 | ✓ |
| **[RUNOCR_RESULT_LAYOUT_BOUNDARY]** | **PASS** |

(첫 실행에서 단어 경계 미사용 substring 매칭이 `OcrResultPanel` 안의 `OcrResult` 등을 false-positive 로 잡아 FAIL 1회. 검증 스크립트 regex 를 단어 경계 + 주석 strip 으로 보정 후 PASS — tmp 스크립트만 보정, 운영 코드 무관)

## 10. 기존 runner 결과
| Runner | 결과 |
|--------|------|
| `node tmp/check_runocr_result_layout_boundary_3a.mjs` | PASS |
| `node tmp/check_runocr_formdata_keys_2a.mjs` | PASS |
| `node tmp/check_runocr_request_boundary_2b.mjs` | PASS |
| `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | PASS |
| `node tmp/check_table_view_model_v1_fixtures_js.mjs` | PASS 8/8 |
| `node tmp/check_clean_json_v1_fixtures_js.mjs` | PASS 9/9 (내부 typecheck=PASS, build=PASS) |
| `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_RESULT_LAYOUT_SPLIT_20260522` | PASS 6/6 (`.venv` python) — 2C 의 trade_7_7pdf drift 가 이번 실행에서는 발생하지 않음 (backend OCR 결과 재안정화 또는 fixture 재정렬 추정) |

## 11. typecheck / build 결과
- `npm run typecheck` → PASS (exit 0)
- `npm run build` → PASS (exit 0, Next.js 15.5.4, 18/18 static pages, `/runocr` 65.7 kB / 184 kB — 2C 와 동일, 사이즈 변화 없음)

## 12. known stderr noise
- `⨯ ESLint: nextVitals is not iterable` — `npm run build` 시 stderr 에 등장, exit code 0 (non-blocking)
- 시스템 python `requests` 미설치는 `.venv/Scripts/python.exe` 로 우회

## 13. 남은 이슈
- 워크스페이스 `runOcr()` 본문은 여전히 autofill/history/restore mapping 응집 (500+ 줄). 추가 분리는 별도 phase
- 기본 화면 main return (line 1228 이후, 약 260줄) 은 이번 작업 범위 밖 — `RunOcrControls` precheck 가 별도로 필요 (HIGH risk, prop 26개)
- `RunOcrResultLayout` 의 `scanOverlay` 는 optional 이지만 워크스페이스에서 `isOcrRunning ? … : null` 로 condition 결정 — 의미 차이 없음
- `templates.json` 은 여전히 dirty 상태이나 이번 markdown 6/6 PASS — 별도 정리는 필요할 수 있음

## 14. 다음 작업 제안
- `RunOcrControls` 분리는 props 폭발(26개+)이 커서 더 작은 control group(예: template topbar, run button bar, model/file info card) 별로 precheck 후 단계적 진행
- Template 폴더 ownership precheck
- history / restore adapter 분리 precheck (state 결합 가장 큼 — 마지막)
- `common/utils` 이동은 feature 폴더 안정화 후 진행
- TPL-95328E52 등 dirty templates 영향 precheck (markdown drift 재발 방지)
- TestWorkspace 폴더 정비는 사용자 확인 후
