from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT_ROOT / "src" / "components" / "runocr" / "RunOcrWorkspace.tsx"
DOCS = PROJECT_ROOT / "docs"
MD_PATH = DOCS / "FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.md"
JSON_PATH = DOCS / "FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.json"
CSV_PATH = DOCS / "FRONTEND_RUNOCR_UI_SPLIT_MAP_20260522.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def run_command(args: list[str]) -> dict:
    print(f"$ {' '.join(args)}")
    proc = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        shell=False,
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    return {
        "command": " ".join(args),
        "exitCode": proc.returncode,
        "stdoutTail": proc.stdout[-4000:],
        "stderrTail": proc.stderr[-4000:],
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "knownStderrNoise": "ESLint: nextVitals is not iterable" if "nextVitals is not iterable" in proc.stderr else None,
    }


def git_status(path: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=path,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        shell=False,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def find_line(lines: list[str], needle: str, start: int = 1) -> int | None:
    for idx, line in enumerate(lines[start - 1 :], start=start):
        if needle in line:
            return idx
    return None


def count_uses(lines: list[str], start: int, end: int, names: list[str]) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for name in names:
        hits = [idx for idx in range(start, min(end, len(lines)) + 1) if name in lines[idx - 1]]
        if hits:
            result[name] = hits
    return result


def make_prop(name: str, category: str, source: str, line_usage: list[int], risk: str, notes: str = "") -> dict:
    return {
        "propName": name,
        "category": category,
        "source": source,
        "lineUsage": line_usage,
        "required": True,
        "risk": risk,
        "notes": notes,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    DOCS.mkdir(parents=True, exist_ok=True)
    lines = read_lines(WORKSPACE)
    line_count = len(lines)

    result_branch_start = find_line(lines, "if (ocrResult && selectedFile)") or 1114
    result_branch_return = find_line(lines, "return (", result_branch_start) or result_branch_start
    main_return = find_line(lines, "return (", result_branch_return + 1) or 1228
    result_branch_end = main_return - 3
    file_dropzone_line = find_line(lines, "<FileDropzone") or 1309
    run_button_line = find_line(lines, "className={`uw-run-btn") or 1446
    topbar_start = find_line(lines, "Top: Template bar") or 1230
    upload_start = find_line(lines, "Left: upload panel") or 1306
    guide_start = find_line(lines, "Right: guide or file info") or 1338
    tooltip_start = find_line(lines, "{cardTooltip &&") or 1464

    controls_names = [
        "isRunOcr",
        "templates",
        "activeTemplateId",
        "setRunOcrTemplateMode",
        "setActiveTemplateId",
        "cardTooltip",
        "setCardTooltip",
        "router.push",
        "FileDropzone",
        "pickFile",
        "fileInputRef",
        "previewUrl",
        "selectedFile",
        "isRendering",
        "displayUrl",
        "isTiff",
        "isOcrRunning",
        "openFilePicker",
        "selectedModelId",
        "setSelectedModelId",
        "MODEL_OPTIONS",
        "formatFileType",
        "uploadDuration",
        "hintSections",
        "canRunOcr",
        "runOcr",
        "window.innerWidth",
    ]
    controls_uses = count_uses(lines, topbar_start, len(lines), controls_names)

    controls_props = [
        make_prop("isRunOcr", "value", "route/workspace mode", controls_uses.get("isRunOcr", []), "LOW"),
        make_prop("templates", "derived option list", "template state", controls_uses.get("templates", []), "MEDIUM"),
        make_prop("activeTemplateId", "value", "template state", controls_uses.get("activeTemplateId", []), "LOW"),
        make_prop("onTemplateModeChange", "handler/setter", "setRunOcrTemplateMode", controls_uses.get("setRunOcrTemplateMode", []), "MEDIUM"),
        make_prop("onActiveTemplateChange", "handler/setter", "setActiveTemplateId", controls_uses.get("setActiveTemplateId", []), "MEDIUM"),
        make_prop("cardTooltip", "value", "tooltip state", controls_uses.get("cardTooltip", []), "LOW"),
        make_prop("onCardTooltipChange", "handler/setter", "setCardTooltip", controls_uses.get("setCardTooltip", []), "MEDIUM"),
        make_prop("onNewTemplate", "handler", "router.push('/ocr?mode=new')", controls_uses.get("router.push", []), "LOW"),
        make_prop("fileInputRef", "ref", "file input ref", controls_uses.get("fileInputRef", []), "MEDIUM"),
        make_prop("onPickFile", "handler", "pickFile", controls_uses.get("pickFile", []), "MEDIUM"),
        make_prop("previewUrl", "value", "preview state", controls_uses.get("previewUrl", []), "LOW"),
        make_prop("selectedFile", "value", "file state", controls_uses.get("selectedFile", []), "MEDIUM"),
        make_prop("isRendering", "value", "viewer/render state", controls_uses.get("isRendering", []), "LOW"),
        make_prop("displayUrl", "value", "preview/render state", controls_uses.get("displayUrl", []), "LOW"),
        make_prop("isTiff", "utility", "local helper", controls_uses.get("isTiff", []), "LOW"),
        make_prop("isOcrRunning", "value", "request state", controls_uses.get("isOcrRunning", []), "LOW"),
        make_prop("onOpenFilePicker", "handler", "openFilePicker", controls_uses.get("openFilePicker", []), "LOW"),
        make_prop("selectedModelId", "value", "model state", controls_uses.get("selectedModelId", []), "LOW"),
        make_prop("onSelectedModelChange", "handler/setter", "setSelectedModelId", controls_uses.get("setSelectedModelId", []), "MEDIUM"),
        make_prop("modelOptions", "derived option list", "MODEL_OPTIONS", controls_uses.get("MODEL_OPTIONS", []), "LOW"),
        make_prop("formatFileType", "utility", "local helper", controls_uses.get("formatFileType", []), "LOW"),
        make_prop("uploadDuration", "value", "file/render state", controls_uses.get("uploadDuration", []), "LOW"),
        make_prop("hintSections", "derived data", "workspace memo/static data", controls_uses.get("hintSections", []), "LOW"),
        make_prop("canRunOcr", "value", "derived state", controls_uses.get("canRunOcr", []), "LOW"),
        make_prop("onRunOcr", "handler", "runOcr", controls_uses.get("runOcr", []), "MEDIUM"),
        make_prop("viewportWidthGuard", "browser dependency", "window.innerWidth tooltip clamp", controls_uses.get("window.innerWidth", []), "MEDIUM"),
    ]

    layout_names = [
        "ocrDisplayUrl",
        "resultTab",
        "canvasLoaded",
        "canvasImgRef",
        "canvasRegions",
        "setCanvasRegions",
        "canvasSelectedId",
        "setCanvasSelectedId",
        "canvasDrawMode",
        "setCanvasDrawMode",
        "canvasZoom",
        "rowTemplateTargetId",
        "setRowTemplateTargetId",
        "colGuideTargetId",
        "setColGuideTargetId",
        "customVisibleRegionIds",
        "customEmptySelectionHint",
        "customDrawTargetRegionId",
        "customDrawTargetField",
        "ocrResult",
        "selectedFieldIndex",
        "setSelectedFieldIndex",
        "activeTemplateForPanel",
        "isOcrRunning",
        "runOcr",
        "processedImageUrl",
        "selectedFile",
        "setResultTab",
        "setIsOcrRunning",
        "currentJobId",
        "currentCreatedAt",
        "handleResultClose",
        "handlePersistEdits",
        "fileInputRef",
        "pickFile",
    ]
    layout_uses = count_uses(lines, result_branch_start, result_branch_end, layout_names)

    direct_layout_props = [
        make_prop(name, "direct prop/state", "RunOcrWorkspace", hits, "HIGH" if name.startswith("set") else "MEDIUM")
        for name, hits in layout_uses.items()
    ]
    node_layout_props = [
        make_prop("viewer", "React node", "OcrCanvasPane/OcrDocViewer/placeholder composed in workspace", [1120, 1145], "LOW"),
        make_prop("resultPanel", "React node", "OcrResultPanel composed in workspace", [1162], "LOW"),
        make_prop("scanOverlay", "React node/boolean", "isOcrRunning overlay, optionally composed in workspace", [1157], "LOW"),
        make_prop("hiddenFileInput", "React node", "existing hidden input composed in workspace", [1214], "LOW"),
    ]

    controls_handler_count = sum(1 for p in controls_props if "handler" in p["category"] or "setter" in p["category"])
    controls_setter_count = sum(1 for p in controls_props if "setter" in p["category"])
    controls_risk = "HIGH" if len(controls_props) >= 16 or controls_handler_count >= 8 else "MEDIUM"
    direct_layout_risk = "HIGH" if len(direct_layout_props) >= 16 else "MEDIUM"
    node_layout_risk = "LOW"

    jsx_structure = {
        "returnRange": {"resultBranch": [result_branch_start, result_branch_end], "main": [main_return, line_count]},
        "sections": [
            {
                "name": "resultBranch",
                "lineRange": [result_branch_start, result_branch_end],
                "role": "OCR 결과 화면. 문서 뷰어 또는 canvas pane과 결과 패널을 좌우 배치한다.",
                "keyElements": ["OcrCanvasPane", "OcrDocViewer", "OcrResultPanel", "hidden file input", "scan overlay"],
            },
            {
                "name": "templateTopbar",
                "lineRange": [topbar_start, upload_start - 1],
                "role": "RunOCR 템플릿 카드 선택 또는 일반 템플릿 select/new-template 진입.",
                "keyElements": ["template cards", "template select", "new template button", "hover tooltip source"],
            },
            {
                "name": "uploadPanel",
                "lineRange": [upload_start, guide_start - 1],
                "role": "파일 선택, preview image, rendering/running overlay, 파일 변경 버튼.",
                "keyElements": ["FileDropzone", "preview image", "scan overlay", "change file button"],
            },
            {
                "name": "guidePanel",
                "lineRange": [guide_start, tooltip_start - 1],
                "role": "모델 선택, 파일 정보, 힌트/가이드, Run OCR 실행 버튼.",
                "keyElements": ["model select", "file metadata", "hint sections", "Run OCR button"],
            },
            {
                "name": "templateHoverTooltip",
                "lineRange": [tooltip_start, line_count],
                "role": "템플릿 카드 hover preview tooltip. window width clamp에 의존한다.",
                "keyElements": ["fixed tooltip", "preview image", "window.innerWidth"],
            },
        ],
    }

    controls_candidate = {
        "lineRange": [topbar_start, tooltip_start - 1],
        "includes": ["templateTopbar", "uploadPanel", "guidePanel"],
        "props": controls_props,
        "estimatedPropsCount": len(controls_props),
        "handlerCount": controls_handler_count,
        "setterCount": controls_setter_count,
        "derivedDataCount": sum(1 for p in controls_props if p["category"] in {"derived data", "derived option list"}),
        "risk": controls_risk,
        "recommendation": "DO_LATER_SPLIT_SMALLER",
        "reason": "한 번에 RunOcrControls로 빼면 템플릿, 파일, 모델, 실행 버튼, tooltip, ref까지 넘어가 props가 16개를 크게 넘는다.",
        "recommendedPropShape": "나중에 templateControls/fileControls/runButton처럼 더 작은 presentational component 또는 grouped props로 분리한다.",
    }

    layout_candidate = {
        "lineRange": [result_branch_start, result_branch_end],
        "directProps": {
            "props": direct_layout_props,
            "estimatedPropsCount": len(direct_layout_props),
            "risk": direct_layout_risk,
            "recommendation": "AVOID_DIRECT_PROP_PASSING",
        },
        "nodeComposition": {
            "props": node_layout_props,
            "estimatedPropsCount": len(node_layout_props),
            "risk": node_layout_risk,
            "recommendation": "DO_FIRST",
        },
        "recommendation": "Extract RunOcrResultLayout with node composition only.",
        "reason": "OcrDocViewer/OcrResultPanel props를 layout 컴포넌트로 직접 넘기면 위험하지만, viewer/result/hidden input을 node로 넘기면 layout 책임만 분리된다.",
    }

    extraction_options = [
        {
            "option": "RunOcrControls only",
            "risk": controls_risk,
            "pros": ["조작 UI 위치가 명확해진다."],
            "cons": ["예상 props 26개, handler/setter 다수.", "tooltip과 file input ref까지 같이 얽힌다."],
            "recommendation": "DO_LATER",
        },
        {
            "option": "RunOcrResultLayout direct props",
            "risk": direct_layout_risk,
            "pros": ["결과 레이아웃 이름은 생긴다."],
            "cons": ["OcrDocViewer/OcrResultPanel의 방대한 props를 중계하게 되어 중복 인터페이스가 된다."],
            "recommendation": "DO_NOT_USE",
        },
        {
            "option": "RunOcrControls + RunOcrResultLayout together",
            "risk": "HIGH",
            "pros": ["한 번에 파일 구조 목표에 가까워진다."],
            "cons": ["UI와 layout 변경을 동시에 하므로 회귀 지점이 넓다."],
            "recommendation": "DO_NOT_DO_IN_PHASE_3A",
        },
        {
            "option": "RunOcrResultLayout node composition only",
            "risk": node_layout_risk,
            "pros": ["state/handler 이동 없음.", "props 4개 수준.", "layout 책임만 분리 가능."],
            "cons": ["라인 수 감소는 제한적이고, 조작 UI는 그대로 남는다."],
            "recommendation": "DO_FIRST",
        },
        {
            "option": "Hold UI split",
            "risk": "LOW",
            "pros": ["리스크 없음."],
            "cons": ["RunOCR 화면 배치 위치를 찾기 쉬운 구조로 만드는 진척이 없다."],
            "recommendation": "ACCEPTABLE_BUT_NOT_PRIMARY",
        },
    ]

    phase3a = {
        "recommendation": "A. RunOcrResultLayout만 node composition 방식으로 분리",
        "scope": [
            "Create src/components/runocr/ui/RunOcrResultLayout.tsx",
            "Keep OcrDocViewer/OcrResultPanel/CornerAdjust composition in RunOcrWorkspace",
            "Pass viewer/resultPanel/hiddenFileInput/scanOverlay nodes",
            "Do not move state, handlers, request, mapping, history, or autofill",
            "Defer RunOcrControls until smaller control groups are designed",
        ],
        "why": "첫 UI split은 layout 책임만 떼어내면 props 폭발을 피하고, RunOcrWorkspace의 orchestration 책임을 유지할 수 있다.",
        "risk": "LOW",
    }

    expected_files = [
        {
            "path": "src/components/runocr/ui/RunOcrResultLayout.tsx",
            "role": "Presentational result screen layout using node composition.",
            "expectedProps": ["viewer", "resultPanel", "hiddenFileInput", "scanOverlay"],
            "risk": "LOW",
        },
        {
            "path": "src/components/runocr/ui/RunOcrControls.tsx",
            "role": "Future control panel candidate, not recommended for Phase 3A all-at-once.",
            "expectedProps": [p["propName"] for p in controls_props],
            "risk": "HIGH",
        },
        {
            "path": "src/components/runocr/RunOcrWorkspace.tsx",
            "role": "Would import/use RunOcrResultLayout in actual split. Not modified in this precheck.",
            "expectedProps": [],
            "risk": "MEDIUM",
        },
        {
            "path": "tmp/check_runocr_ui_split_boundary_3a.mjs",
            "role": "Optional static check after actual split.",
            "expectedProps": [],
            "risk": "LOW",
        },
    ]

    validation_plan = [
        "npm run typecheck",
        "npm run build",
        "node tmp/check_table_view_model_v1_fixtures_js.mjs",
        "node tmp/check_clean_json_v1_fixtures_js.mjs",
        "python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_UI_SPLIT_3A_20260522",
        "FormData key parity check",
        "request boundary static check",
        "response mapping boundary static check",
        "UI split boundary static check",
        "/runocr manual smoke: file selection, OCR run, Preview tab, Clean JSON copy/export",
    ]

    dirty_status = git_status(PROJECT_ROOT)

    typecheck = run_command(["npm.cmd", "run", "typecheck"])
    build = run_command(["npm.cmd", "run", "build"])

    report = {
        "generatedAt": now_iso(),
        "projectRoot": str(PROJECT_ROOT),
        "dirtyStatus": dirty_status,
        "codeModified": False,
        "createdFiles": [
            "tmp/codex_frontend_runocr_ui_split_precheck.py",
            "docs/FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.md",
            "docs/FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.json",
            "docs/FRONTEND_RUNOCR_UI_SPLIT_MAP_20260522.csv",
        ],
        "jsxStructure": jsx_structure,
        "controlsCandidate": controls_candidate,
        "layoutCandidate": layout_candidate,
        "extractionOptions": extraction_options,
        "phase3ARecommendation": phase3a,
        "expectedFiles": expected_files,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "Phase 3A에서는 RunOcrResultLayout node composition만 실제 적용한다.",
            "RunOcrControls는 props grouping 또는 더 작은 control 컴포넌트 precheck 후 진행한다.",
            "실제 split 후 runner 3종, typecheck/build, /runocr manual smoke를 실행한다.",
        ],
    }

    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["candidate", "lineRange", "estimatedPropsCount", "handlerCount", "setterCount", "risk", "recommendation", "notes"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "candidate": "RunOcrControls",
                "lineRange": f"{controls_candidate['lineRange'][0]}-{controls_candidate['lineRange'][1]}",
                "estimatedPropsCount": controls_candidate["estimatedPropsCount"],
                "handlerCount": controls_candidate["handlerCount"],
                "setterCount": controls_candidate["setterCount"],
                "risk": controls_candidate["risk"],
                "recommendation": controls_candidate["recommendation"],
                "notes": controls_candidate["reason"],
            }
        )
        writer.writerow(
            {
                "candidate": "RunOcrResultLayout direct props",
                "lineRange": f"{layout_candidate['lineRange'][0]}-{layout_candidate['lineRange'][1]}",
                "estimatedPropsCount": layout_candidate["directProps"]["estimatedPropsCount"],
                "handlerCount": "",
                "setterCount": "",
                "risk": layout_candidate["directProps"]["risk"],
                "recommendation": layout_candidate["directProps"]["recommendation"],
                "notes": "Direct prop passing would mirror OcrDocViewer/OcrResultPanel props.",
            }
        )
        writer.writerow(
            {
                "candidate": "RunOcrResultLayout node composition",
                "lineRange": f"{layout_candidate['lineRange'][0]}-{layout_candidate['lineRange'][1]}",
                "estimatedPropsCount": layout_candidate["nodeComposition"]["estimatedPropsCount"],
                "handlerCount": 0,
                "setterCount": 0,
                "risk": layout_candidate["nodeComposition"]["risk"],
                "recommendation": layout_candidate["nodeComposition"]["recommendation"],
                "notes": layout_candidate["reason"],
            }
        )

    md = f"""# FRONTEND RUNOCR UI SPLIT PRECHECK 20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- UI 파일 생성: 없음
- import 수정/파일 이동/fixture 수정: 없음
- 생성한 파일은 precheck 스크립트와 문서 리포트뿐이다.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_ui_split_precheck.py`
- `docs/FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_UI_SPLIT_MAP_20260522.csv`

## 4. 분석 범위
- 필수: `src/components/runocr/RunOcrWorkspace.tsx`
- 참고: `src/components/runocr/ui/*`, `src/components/runocr/utils/*`

## 5. RunOcrWorkspace JSX 구조 요약
- 전체 라인 수: {line_count}
- 결과 화면 branch: {result_branch_start}-{result_branch_end}
  - `OcrCanvasPane` 또는 `OcrDocViewer`를 문서 영역에 표시한다.
  - `OcrResultPanel`을 오른쪽 결과 패널에 표시한다.
  - scan overlay와 hidden file input이 같은 branch 안에 있다.
- 기본 화면 main return: {main_return}-{line_count}
  - template topbar: {topbar_start}-{upload_start - 1}
  - upload panel: {upload_start}-{guide_start - 1}
  - guide/model/run button panel: {guide_start}-{tooltip_start - 1}
  - template hover tooltip: {tooltip_start}-{line_count}

## 6. RunOcrControls 후보 분석
- 후보 범위: {controls_candidate['lineRange'][0]}-{controls_candidate['lineRange'][1]}
- 포함 후보: template topbar, file dropzone/preview, model select, file info, guide, run button
- 예상 props 수: {controls_candidate['estimatedPropsCount']}
- handler 수: {controls_candidate['handlerCount']}
- setter 수: {controls_candidate['setterCount']}
- 위험도: {controls_candidate['risk']}
- 판정: `{controls_candidate['recommendation']}`
- 이유: {controls_candidate['reason']}

## 7. RunOcrResultLayout 후보 분석
- 후보 범위: {layout_candidate['lineRange'][0]}-{layout_candidate['lineRange'][1]}
- direct props 방식 예상 props 수: {layout_candidate['directProps']['estimatedPropsCount']} / 위험도 {layout_candidate['directProps']['risk']}
- node composition 방식 예상 props 수: {layout_candidate['nodeComposition']['estimatedPropsCount']} / 위험도 {layout_candidate['nodeComposition']['risk']}
- 판정: {layout_candidate['recommendation']}
- 이유: {layout_candidate['reason']}

## 8. props 폭발 위험
- `RunOcrControls`를 한 번에 분리하면 템플릿 선택, 파일 선택, preview/render 상태, model select, run button, tooltip, ref, router handler가 모두 props로 넘어간다.
- `RunOcrResultLayout`을 direct props 방식으로 만들면 `OcrDocViewer`와 `OcrResultPanel` props를 그대로 중계하는 컴포넌트가 되어 책임이 흐려진다.
- `RunOcrResultLayout`을 node composition 방식으로 만들면 props를 `viewer`, `resultPanel`, `scanOverlay`, `hiddenFileInput` 수준으로 낮출 수 있다.

## 9. extraction options 비교
| option | risk | recommendation |
| --- | --- | --- |
| RunOcrControls only | {extraction_options[0]['risk']} | {extraction_options[0]['recommendation']} |
| RunOcrResultLayout direct props | {extraction_options[1]['risk']} | {extraction_options[1]['recommendation']} |
| RunOcrControls + RunOcrResultLayout together | {extraction_options[2]['risk']} | {extraction_options[2]['recommendation']} |
| RunOcrResultLayout node composition only | {extraction_options[3]['risk']} | {extraction_options[3]['recommendation']} |
| Hold UI split | {extraction_options[4]['risk']} | {extraction_options[4]['recommendation']} |

## 10. Phase 3A 추천 범위
- 추천: {phase3a['recommendation']}
- 범위:
  - `RunOcrResultLayout.tsx`만 생성
  - `viewer`, `resultPanel`, `scanOverlay`, `hiddenFileInput`을 node로 전달
  - state/handler/request/mapping/history/autofill 이동 없음
  - `RunOcrControls`는 보류
- 위험도: {phase3a['risk']}
- 이유: {phase3a['why']}

## 11. 예상 파일/변경
- 신규 후보: `src/components/runocr/ui/RunOcrResultLayout.tsx`
- 수정 후보: `src/components/runocr/RunOcrWorkspace.tsx`
- 보류 후보: `src/components/runocr/ui/RunOcrControls.tsx`
- optional check 후보: `tmp/check_runocr_ui_split_boundary_3a.mjs`

## 12. 검증 전략
{chr(10).join(f'- {item}' for item in validation_plan)}

## 13. dirty 상태
현재 dirty 상태는 되돌리지 않았다.

```text
{chr(10).join(dirty_status)}
```

## 14. typecheck/build 결과
- `npm run typecheck`: {typecheck['status']} (exit {typecheck['exitCode']})
- `npm run build`: {build['status']} (exit {build['exitCode']})
- known stderr noise: {build['knownStderrNoise'] or '없음'}

## 15. 다음 작업 제안
1. Phase 3A로 `RunOcrResultLayout` node composition split만 진행한다.
2. 실제 split 후 runner 3종, typecheck/build, `/runocr` manual smoke를 실행한다.
3. `RunOcrControls`는 props grouping 또는 더 작은 control 단위 precheck 이후 별도 작업으로 진행한다.
"""
    MD_PATH.write_text(md, encoding="utf-8")

    print(json.dumps({"md": str(MD_PATH), "json": str(JSON_PATH), "csv": str(CSV_PATH)}, ensure_ascii=False, indent=2))
    return 0 if typecheck["exitCode"] == 0 and build["exitCode"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
