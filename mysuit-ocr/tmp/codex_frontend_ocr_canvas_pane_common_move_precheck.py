from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
LOG_OUT = "ocr-server/logs/codex_CODEX_FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.out.log"
LOG_ERR = "ocr-server/logs/codex_CODEX_FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.err.log"


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def line_count(path: str) -> int:
    return len(read_text(path).splitlines())


def extract_import_blocks(path: str) -> list[str]:
    imports: list[str] = []
    lines = read_text(path).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip().startswith("import "):
            i += 1
            continue
        block = [line.strip()]
        while ";" not in lines[i] and i + 1 < len(lines):
            i += 1
            block.append(lines[i].strip())
        imports.append(" ".join(block))
        i += 1
    return imports


def extract_exports(path: str) -> list[str]:
    exports: list[str] = []
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if stripped.startswith("export "):
            exports.append(stripped.rstrip(" {"))
    return exports


def git_status() -> list[str]:
    result = subprocess.run(
        ["git", "-c", "core.excludesFile=", "status", "--porcelain=v1"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def parse_log_exit(command: str, marker: str) -> dict[str, object]:
    path = REPO_ROOT / LOG_OUT
    if not path.exists():
        return {"command": command, "status": "NOT_RUN", "exitCode": None, "stdoutLog": LOG_OUT, "stderrLog": LOG_ERR}
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"\[{re.escape(marker)}\]\s+(\d+)", text)
    code = int(match.group(1)) if match else None
    return {
        "command": command,
        "status": "PASS" if code == 0 else "FAIL" if code is not None else "UNKNOWN",
        "exitCode": code,
        "stdoutLog": LOG_OUT,
        "stderrLog": LOG_ERR,
        "knownStderrNoise": "ESLint: nextVitals is not iterable is non-blocking when exit code is 0.",
    }


CANVAS_PATH = "src/components/ocr/OcrCanvasPane.tsx"

props = [
    "imgRef",
    "fileInputRef?",
    "onPickFile?",
    "loaded",
    "regions",
    "setRegions",
    "selectedId",
    "setSelectedId",
    "rowTemplateTargetId",
    "setRowTemplateTargetId",
    "colGuideTargetId",
    "setColGuideTargetId",
    "drawMode",
    "setDrawMode",
    "zoomPct",
    "visibleRegionIds?",
    "emptySelectionHint?",
    "drawTargetRegionId?",
    "drawTargetName?",
    "drawTargetFieldType?",
    "onClearSelection?",
]

imported_by = [
    {
        "file": "src/components/template/ui/OcrAnnotator.tsx",
        "importPath": "../../ocr/OcrCanvasPane",
        "importKind": "static",
        "usagePurpose": "Template editor canvas: file pick/drop image display, region drawing/editing, table rowTemplate/colGuide editing, selection state.",
        "feature": "template",
        "moveImpact": "actual move must update import to ../../../common/ui/OcrCanvasPane or chosen target",
    },
    {
        "file": "src/components/runocr/RunOcrWorkspace.tsx",
        "importPath": "../ocr/OcrCanvasPane",
        "importKind": "dynamic next/dynamic ssr:false",
        "usagePurpose": "RunOCR custom tab canvas: edit/adopt OCR result regions, show selected OCR field region, preserve RunOCR request/result logic outside canvas.",
        "feature": "runocr",
        "moveImpact": "actual move must update dynamic import to ../../common/ui/OcrCanvasPane or chosen target",
    },
]

target_candidates = [
    {
        "path": "src/common/ui/OcrCanvasPane.tsx",
        "pros": [
            "Matches ownership: shared UI used by Template and RunOCR",
            "Simple path for a single shared canvas component",
            "Keeps feature folders from owning cross-feature canvas UI",
        ],
        "cons": [
            "Requires resolving FileDropzone dependency so common/ui does not import src/components/common",
        ],
        "roleAccuracy": "HIGH",
        "recommended": True,
        "condition": "Ready after FileDropzone is available from common/ui or another common-safe path.",
    },
    {
        "path": "src/common/ui/ocr/OcrCanvasPane.tsx",
        "pros": ["Creates a namespace if more OCR-specific common UI grows later"],
        "cons": ["Extra nesting for one file; does not by itself solve FileDropzone dependency"],
        "roleAccuracy": "MEDIUM_HIGH",
        "recommended": False,
        "condition": "Consider only if multiple OCR common UI files are moved together.",
    },
    {
        "path": "src/components/ocr/OcrCanvasPane.tsx",
        "pros": ["No import churn and no FileDropzone dependency problem"],
        "cons": ["Leaves a single-file feature folder owning shared UI"],
        "roleAccuracy": "MEDIUM",
        "recommended": False,
        "condition": "Temporary hold if FileDropzone cannot move yet.",
    },
    {
        "path": "src/components/shared/OcrCanvasPane.tsx",
        "pros": ["Names shared intent"],
        "cons": ["Does not match current target structure preference; creates another shared root beside common"],
        "roleAccuracy": "LOW",
        "recommended": False,
        "condition": "Not recommended.",
    },
]

usage_impact = {
    "template": {
        "file": "src/components/template/ui/OcrAnnotator.tsx",
        "importPath": "../../ocr/OcrCanvasPane",
        "props": [
            "imgRef",
            "fileInputRef",
            "onPickFile",
            "loaded",
            "regions/setRegions",
            "selectedId/setSelectedId",
            "drawMode/setDrawMode",
            "zoomPct",
            "rowTemplateTargetId/setRowTemplateTargetId",
            "colGuideTargetId/setColGuideTargetId",
        ],
        "boundary": "Template save/export, localStorage, IndexedDB image persistence, documentType detection, and backend save remain in OcrAnnotator; canvas only receives state/callback props.",
        "moveImpact": "import-only update expected after target exists.",
    },
    "runocr": {
        "file": "src/components/runocr/RunOcrWorkspace.tsx",
        "importPath": "../ocr/OcrCanvasPane via dynamic import",
        "props": [
            "imgRef",
            "loaded",
            "canvasRegions/setCanvasRegions",
            "canvasSelectedId/setCanvasSelectedId",
            "canvasDrawMode/setCanvasDrawMode",
            "canvasZoom",
            "rowTemplateTargetId/setRowTemplateTargetId",
            "colGuideTargetId/setColGuideTargetId",
            "visibleRegionIds",
            "emptySelectionHint",
            "drawTargetRegionId/name/type",
            "onClearSelection",
        ],
        "boundary": "RunOCR request/result/history/autofill/revalidate logic remains in RunOcrWorkspace and result panel; canvas is interactive region UI only.",
        "moveImpact": "dynamic import path update expected after target exists.",
    },
    "test": {
        "directImportFound": False,
        "notes": "No direct src/components/test/TestWorkspace.tsx import of OcrCanvasPane was found.",
    },
}

dependency_assessment = {
    "cleanCommonDependencies": [
        "src/common/types/ocr",
        "src/common/utils/ocrCanvasOps",
        "src/common/utils/ocrTableRegion",
        "React",
    ],
    "blockingDependency": {
        "path": "src/components/common/FileDropzone.tsx",
        "currentImport": "../common/FileDropzone",
        "reason": "Moving OcrCanvasPane to common/ui as-is would make common/ui import from src/components/common, violating the common -> components dependency rule.",
        "recommendedFixBeforeMove": "Move FileDropzone to src/common/ui/FileDropzone.tsx or otherwise expose it from a common-safe path, then move OcrCanvasPane.",
    },
    "templatePolicyFound": False,
    "runocrPolicyFound": False,
    "browserApiUse": ["ResizeObserver", "window keydown listener", "pointer events", "image getBoundingClientRect"],
    "browserApiAssessment": "Natural for an interactive UI component.",
}

static_check_plan = [
    "src/common/ui/OcrCanvasPane.tsx exists after actual move",
    "src/components/ocr/OcrCanvasPane.tsx is absent after actual move",
    "src/components/ocr folder is empty or removable after actual move",
    "common/ui/OcrCanvasPane.tsx does not import src/components/*",
    "FileDropzone dependency is common-safe before or during the actual move",
    "common/ui/OcrCanvasPane.tsx imports common/types/ocr, common/utils/ocrCanvasOps, common/utils/ocrTableRegion",
    "OcrAnnotator import points to common/ui target",
    "RunOcrWorkspace dynamic import points to common/ui target",
    "OcrRightPanel import impact is none",
    "TestWorkspace is not modified",
    "RunOCR request/result/history/autofill files are not modified except RunOcrWorkspace import path if needed",
    "npm run typecheck PASS",
    "npm run build PASS",
    "5A/5B/5C/5D checks PASS",
    "validation baseline repair check PASS",
]

validation_plan = [
    "node tmp/check_ocr_canvas_pane_common_move_5e.mjs",
    "npm run typecheck",
    "npm run build",
    "node tmp/check_ocr_core_types_common_move_5a.mjs",
    "node tmp/check_ocr_core_ops_common_move_5b.mjs",
    "node tmp/check_ocr_core_table_common_move_5c.mjs",
    "node tmp/check_template_export_payload_move_5d.mjs",
    "node tmp/check_validation_baseline_repair_1a.mjs",
    "node tmp/check_runocr_formdata_keys_2a.mjs",
    "node tmp/check_runocr_response_mapping_boundary_2c.mjs",
    "node tmp/check_template_workspace_move_4a.mjs",
    "node tmp/check_template_editor_ui_move_4b.mjs",
]

report = {
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "projectRoot": "mysuit-ocr",
    "codeModified": False,
    "dirtyStatus": git_status(),
    "ocrCanvasPane": {
        "currentPath": CANVAS_PATH,
        "lineCount": line_count(CANVAS_PATH),
        "imports": extract_import_blocks(CANVAS_PATH),
        "exports": extract_exports(CANVAS_PATH),
        "props": props,
        "importedBy": imported_by,
        "role": "Shared interactive OCR canvas UI for image display, file drop/pick surface, region draw/move/resize/delete/duplicate/undo, multi split editing, table rowTemplate/colGuide editing, zoom, and visible-region filtering.",
        "majorState": [
            "containerW",
            "drag",
            "loadedRef",
            "regionsRef",
            "dragRef",
            "rafRef",
            "pendingPointRef",
            "lastRectRef",
        ],
        "majorMemoEffects": [
            "visibleRegionSet/visibleRegions",
            "scale",
            "displaySize",
            "loaded and regions ref sync",
            "ResizeObserver container width tracking",
            "global keydown delete/backspace handler",
            "loaded src undo reset",
        ],
        "majorHandlers": [
            "onPointerDown",
            "applyDragFrame",
            "onPointerMove",
            "onPointerUp",
            "deleteRegionLocal",
            "duplicateSelected",
            "undoSelectedRect",
            "setMultiParts",
            "getImagePoint",
        ],
        "responsibilities": {
            "imageDisplay": True,
            "regionDrawMoveResizeDeleteDuplicateUndo": True,
            "tableRowTemplateColGuide": True,
            "zoomVisibleRegionFiltering": True,
            "templateOnlyPolicy": False,
            "runocrOnlyPolicy": False,
        },
        "commonUiReadiness": "DEFER_DUE_TO_FILEDROPZONE_COMPONENT_DEPENDENCY",
        "targetCandidates": target_candidates,
        "recommendation": "Do not move OcrCanvasPane alone yet. First make FileDropzone common-safe, then move OcrCanvasPane to src/common/ui/OcrCanvasPane.tsx with import-only updates in OcrAnnotator and RunOcrWorkspace.",
        "risk": "MEDIUM_HIGH until FileDropzone dependency is resolved; MEDIUM after that.",
    },
    "usageImpact": usage_impact,
    "dependencyAssessment": dependency_assessment,
    "moveRecommendation": {
        "choice": "A_AFTER_FILEDROPZONE_PRECONDITION",
        "target": "src/common/ui/OcrCanvasPane.tsx",
        "precondition": "FileDropzone must be moved or exposed from common/ui/common-safe path first.",
        "scopeAfterPrecondition": [
            "move OcrCanvasPane to src/common/ui/OcrCanvasPane.tsx",
            "update OcrAnnotator static import",
            "update RunOcrWorkspace dynamic import",
            "do not change OcrRightPanel",
            "do not change RunOCR request/result/history/autofill helpers",
            "do not touch TestWorkspace",
        ],
        "reason": "OcrCanvasPane is shared UI with clean common types/utils dependencies, but currently imports FileDropzone from src/components/common.",
        "risk": "MEDIUM_HIGH",
    },
    "staticCheckPlan": static_check_plan,
    "validationPlan": validation_plan,
    "typecheck": parse_log_exit("npm run typecheck", "typecheck_exit_code"),
    "build": parse_log_exit("npm run build", "build_exit_code"),
    "nextSteps": [
        "FileDropzone common/ui ownership precheck or micro-move",
        "FRONTEND-STRUCTURE-5E-OCR-CANVAS-PANE-COMMON-MOVE after FileDropzone is common-safe",
        "OcrCanvasPane common move static check",
        "Template table column definition design precheck",
        "TPL-95328E52 dirty impact precheck",
    ],
}


def write_json() -> None:
    path = ROOT / "docs" / "FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv() -> None:
    path = ROOT / "docs" / "FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_MAP_20260522.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "importPath", "importKind", "feature", "usagePurpose", "moveImpact"])
        writer.writeheader()
        for entry in imported_by:
            writer.writerow(entry)


def write_md() -> None:
    imports = "\n".join(f"- `{line}`" for line in report["ocrCanvasPane"]["imports"])
    exports = "\n".join(f"- `{line}`" for line in report["ocrCanvasPane"]["exports"])
    props_text = ", ".join(props)
    imported_table = "\n".join(
        f"| `{entry['file']}` | `{entry['importPath']}` | {entry['importKind']} | {entry['feature']} | {entry['usagePurpose']} |"
        for entry in imported_by
    )
    candidates = "\n".join(
        f"| `{item['path']}` | {item['roleAccuracy']} | {'YES' if item['recommended'] else 'NO'} | {item['condition']} | {'; '.join(item['pros'])} | {'; '.join(item['cons'])} |"
        for item in target_candidates
    )
    static_checks = "\n".join(f"- {item}" for item in static_check_plan)
    dirty = "\n".join(f" {line}" for line in report["dirtyStatus"]) or " clean"
    validation = "\n".join(f"- `{item}`" for item in validation_plan)

    md = f"""# FRONTEND OCR Canvas Pane Common Move Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 허용 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_ocr_canvas_pane_common_move_precheck.py`
- `docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/common/types/ocr.ts`
- `src/common/utils/ocrCanvasOps.ts`
- `src/common/utils/ocrTableRegion.ts`
- `src/components/template/utils/buildTemplateExportPayload.ts`
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. OcrCanvasPane 역할 요약
- currentPath: `src/components/ocr/OcrCanvasPane.tsx`
- lineCount: {report['ocrCanvasPane']['lineCount']}
- export: default `OcrCanvasPane(props: Props)`
- props: {props_text}
- 역할: shared interactive OCR canvas UI. 이미지 표시, drop/pick surface, region draw/move/resize/delete/duplicate/undo, multi split, table rowTemplate/colGuide, zoom, visible region filtering을 담당한다.
- Template-only persistence/save policy: 없음
- RunOCR request/result/history/autofill policy: 없음
- browser API: `ResizeObserver`, `window` keydown, pointer events, image rect 계산. UI component로 자연스러운 범위다.

Imports:
{imports}

Exports:
{exports}

## 6. importedBy 분석
| file | importPath | importKind | feature | usagePurpose |
|---|---|---|---|---|
{imported_table}

TestWorkspace 직접 import는 발견되지 않았다.

## 7. common/ui 적합성
- 판정: `DEFER_DUE_TO_FILEDROPZONE_COMPONENT_DEPENDENCY`
- common-ready 요소: types/ops/table 의존은 모두 `src/common/types`와 `src/common/utils`로 정리되어 있다.
- blocker: `OcrCanvasPane`가 `../common/FileDropzone`을 import한다. 이 상태로 `src/common/ui/OcrCanvasPane.tsx`로 이동하면 common/ui가 `src/components/common/FileDropzone.tsx`를 참조하게 된다.
- 결론: OcrCanvasPane 자체는 shared UI 후보가 맞지만, 단독 이동은 아직 권장하지 않는다. `FileDropzone`을 common-safe path로 먼저 옮기거나 같은 phase에서 함께 정리해야 한다.

## 8. Template 사용 영향
- 파일: `src/components/template/ui/OcrAnnotator.tsx`
- 현재 import: `../../ocr/OcrCanvasPane`
- 전달 props: image/file pick state, regions/selection state, draw mode, zoom, rowTemplate/colGuide target state.
- save/export, localStorage, IndexedDB image persistence, documentType detection, backend save는 OcrAnnotator에 남아 있고 canvas에는 props로만 전달된다.
- 이동 시 예상 수정: import path만 common/ui target으로 변경.

## 9. RunOCR 사용 영향
- 파일: `src/components/runocr/RunOcrWorkspace.tsx`
- 현재 import: dynamic `../ocr/OcrCanvasPane`, `ssr: false`
- 사용 위치: OCR 결과 화면의 custom tab.
- 전달 props: canvas image/regions/selection/draw/zoom state, visibleRegionIds, emptySelectionHint, OCR field 기반 draw target, clear selection callback.
- request/result/history/autofill/revalidate 로직은 RunOcrWorkspace와 result panel에 남아 있고 canvas 내부로 들어오지 않는다.
- 이동 시 예상 수정: dynamic import path만 common/ui target으로 변경.

## 10. TestWorkspace 영향
- 직접 import 없음.
- 사용자 확인 전 TestWorkspace 수정 금지 정책과 충돌하지 않는다.

## 11. target path 비교
| target | roleAccuracy | recommended | condition | pros | cons |
|---|---:|---:|---|---|---|
{candidates}

최종 target은 `src/common/ui/OcrCanvasPane.tsx`가 가장 자연스럽다. 단, `FileDropzone` dependency를 먼저 common-safe하게 만들어야 한다.

## 12. 실제 이동/보류 추천
- 추천: `A_AFTER_FILEDROPZONE_PRECONDITION`
- 지금 바로 OcrCanvasPane 단독 이동: 보류
- 선행 조건: `FileDropzone`을 `src/common/ui/FileDropzone.tsx` 등 common-safe path로 이동하거나, OcrCanvasPane 이동 phase에 포함한다.
- 선행 조건 충족 후 범위: OcrCanvasPane 이동 + OcrAnnotator import 수정 + RunOcrWorkspace dynamic import 수정.
- 변경하지 않을 범위: OcrRightPanel, RunOCR request/result/history/autofill helper, TestWorkspace.
- 위험도: 현재 MEDIUM_HIGH, FileDropzone 정리 후 MEDIUM.

## 13. static check 설계
{static_checks}

## 14. dirty 상태
```text
{dirty}
```

## 15. typecheck/build 결과
- `npm run typecheck`: {report['typecheck']['status']} (exit {report['typecheck']['exitCode']})
- `npm run build`: {report['build']['status']} (exit {report['build']['exitCode']})
- stdout log: `{LOG_OUT}`
- stderr log: `{LOG_ERR}`
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 non-blocking으로 기록.

## 16. 다음 작업 제안
{validation}

다음 실제 작업은 FileDropzone common/ui 선행 precheck 또는 micro-move를 먼저 수행하고, 그 다음 `FRONTEND-STRUCTURE-5E-OCR-CANVAS-PANE-COMMON-MOVE`로 OcrCanvasPane을 이동하는 순서가 안전하다.
"""
    path = ROOT / "docs" / "FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.md"
    path.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    write_json()
    write_csv()
    write_md()
    print("wrote FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522 reports")
