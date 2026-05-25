from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
LOG_OUT = "ocr-server/logs/codex_CODEX_FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_NO_PROD_MODIFY.out.log"
LOG_ERR = "ocr-server/logs/codex_CODEX_FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_NO_PROD_MODIFY.err.log"


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def line_count(path: str) -> int:
    return len(read_text(path).splitlines())


def extract_imports(path: str) -> list[str]:
    return [line.strip() for line in read_text(path).splitlines() if line.strip().startswith("import ")]


def extract_exports(path: str) -> list[str]:
    return [line.strip() for line in read_text(path).splitlines() if line.strip().startswith("export ")]


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


FILEDROPZONE_PATH = "src/components/common/FileDropzone.tsx"

props = [
    "onPickFile",
    "accept?",
    "hasFile?",
    "children?",
    "fileInputRef?",
    "className?",
    "style?",
]

imported_by = [
    {
        "file": "src/components/ocr/OcrCanvasPane.tsx",
        "importPath": "../common/FileDropzone",
        "usagePurpose": "OCR canvas empty/upload surface; delegates picked or dropped file to parent via onPickFile.",
        "feature": "ocr/shared",
        "moveImpact": "actual move must update import to ../../common/ui/FileDropzone while OcrCanvasPane remains in components/ocr.",
    },
    {
        "file": "src/components/runocr/RunOcrWorkspace.tsx",
        "importPath": "../common/FileDropzone",
        "usagePurpose": "RunOCR upload panel dropzone with preview children when a file is selected.",
        "feature": "runocr",
        "moveImpact": "actual move must update import to ../../common/ui/FileDropzone.",
    },
]

target_candidates = [
    {
        "path": "src/common/ui/FileDropzone.tsx",
        "pros": [
            "Matches shared UI ownership",
            "Simple path for a single reusable UI primitive",
            "Removes OcrCanvasPane common/ui blocker",
        ],
        "cons": ["Requires creating src/common/ui because it does not exist yet"],
        "roleAccuracy": "HIGH",
        "recommended": True,
    },
    {
        "path": "src/common/ui/file/FileDropzone.tsx",
        "pros": ["Creates a namespace if multiple file input UI pieces appear later"],
        "cons": ["Extra nesting for one file and not needed for the immediate blocker"],
        "roleAccuracy": "MEDIUM",
        "recommended": False,
    },
    {
        "path": "src/components/common/FileDropzone.tsx",
        "pros": ["No import churn"],
        "cons": ["Keeps OcrCanvasPane common/ui blocked by common -> components dependency risk"],
        "roleAccuracy": "LOW",
        "recommended": False,
    },
    {
        "path": "bundle with OcrCanvasPane move",
        "pros": ["One phase can finish both blockers"],
        "cons": ["Larger diff and harder to isolate FileDropzone regression from OcrCanvasPane move"],
        "roleAccuracy": "MEDIUM",
        "recommended": False,
    },
]

ocr_canvas_pane_blocker_resolution = {
    "currentBlocker": "OcrCanvasPane imports FileDropzone from src/components/common/FileDropzone.tsx.",
    "resolvedByFileDropzoneMove": True,
    "afterMoveOcrCanvasPaneImport": "from ../../common/ui/FileDropzone while OcrCanvasPane remains in src/components/ocr; later from ./FileDropzone after OcrCanvasPane moves to src/common/ui.",
    "remainingOcrCanvasPaneComponentsDependencies": [],
    "notes": "After FileDropzone is in common/ui, OcrCanvasPane can move to common/ui without importing src/components/*.",
}

move_recommendation = {
    "choice": "A",
    "target": "src/common/ui/FileDropzone.tsx",
    "scope": [
        "create src/common/ui if absent",
        "move src/components/common/FileDropzone.tsx to src/common/ui/FileDropzone.tsx",
        "update imports in OcrCanvasPane and RunOcrWorkspace",
        "do not move OcrCanvasPane in the same micro-step",
        "do not touch Template files or TestWorkspace",
    ],
    "reason": "Small safe precondition for OcrCanvasPane common/ui move; FileDropzone is already shared by OCR canvas and RunOCR upload flow and has no feature-specific imports.",
    "risk": "LOW_MEDIUM",
}

static_check_plan = [
    "src/common/ui/FileDropzone.tsx exists",
    "src/components/common/FileDropzone.tsx is absent",
    "common/ui/FileDropzone.tsx does not import src/components/*",
    "FileDropzone importedBy uses new common/ui path",
    "OcrCanvasPane import points to common/ui/FileDropzone",
    "RunOcrWorkspace import points to common/ui/FileDropzone",
    "OcrCanvasPane remains at src/components/ocr/OcrCanvasPane.tsx",
    "TestWorkspace is not modified",
    "npm run typecheck PASS",
    "npm run build PASS",
    "5A/5B/5C/5D checks PASS",
    "validation baseline repair check PASS",
]

validation_plan = [
    "node tmp/check_filedropzone_common_ui_move.mjs",
    "npm run typecheck",
    "npm run build",
    "node tmp/check_ocr_core_types_common_move_5a.mjs",
    "node tmp/check_ocr_core_ops_common_move_5b.mjs",
    "node tmp/check_ocr_core_table_common_move_5c.mjs",
    "node tmp/check_template_export_payload_move_5d.mjs",
    "node tmp/check_validation_baseline_repair_1a.mjs",
    "node tmp/check_runocr_formdata_keys_2a.mjs",
    "node tmp/check_runocr_response_mapping_boundary_2c.mjs",
]

report = {
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "projectRoot": "mysuit-ocr",
    "codeModified": False,
    "dirtyStatus": git_status(),
    "fileDropzone": {
        "currentPath": FILEDROPZONE_PATH,
        "lineCount": line_count(FILEDROPZONE_PATH),
        "imports": extract_imports(FILEDROPZONE_PATH),
        "exports": extract_exports(FILEDROPZONE_PATH),
        "props": props,
        "importedBy": imported_by,
        "role": "Shared drag/drop and file picker UI. It provides drag visual state, default image/pdf/tiff accept list, optional external input ref, filled-state children rendering, and delegates selected files through onPickFile.",
        "dragDropHandling": True,
        "filePickerHandling": True,
        "featureSpecificPolicy": False,
        "ocrSpecificTextStyleLogic": {
            "text": "Empty-state copy is document/upload oriented and uses uw-* classes, but file type defaults are generic for OCR upload flows and no OCR business logic exists.",
            "risk": "LOW_MEDIUM",
        },
        "browserApiUse": ["DragEvent dataTransfer", "hidden file input click", "input change reset"],
        "componentsDependency": "None.",
        "commonUiReadiness": "COMMON_UI_READY_WITH_IMPORT_ONLY",
        "targetCandidates": target_candidates,
        "recommendation": "Move FileDropzone alone to src/common/ui/FileDropzone.tsx before OcrCanvasPane common/ui move.",
        "risk": "LOW_MEDIUM",
        "commonUiDirectoryExists": exists("src/common/ui"),
    },
    "ocrCanvasPaneBlockerResolution": ocr_canvas_pane_blocker_resolution,
    "moveRecommendation": move_recommendation,
    "staticCheckPlan": static_check_plan,
    "validationPlan": validation_plan,
    "typecheck": parse_log_exit("npm run typecheck", "typecheck_exit_code"),
    "build": parse_log_exit("npm run build", "build_exit_code"),
    "nextSteps": [
        "FRONTEND-STRUCTURE-5E-FILEDROPZONE-COMMON-UI-MOVE micro-step",
        "OcrCanvasPane common/ui move after FileDropzone is common-safe",
        "OcrCanvasPane common move static check",
        "Template table column definition design precheck",
        "TPL-95328E52 dirty impact precheck",
    ],
}


def write_json() -> None:
    path = ROOT / "docs" / "FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv() -> None:
    path = ROOT / "docs" / "FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_MAP_20260522.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "importPath", "feature", "usagePurpose", "moveImpact"])
        writer.writeheader()
        for entry in imported_by:
            writer.writerow(entry)


def write_md() -> None:
    imports = "\n".join(f"- `{line}`" for line in report["fileDropzone"]["imports"])
    exports = "\n".join(f"- `{line}`" for line in report["fileDropzone"]["exports"])
    imported_table = "\n".join(
        f"| `{entry['file']}` | `{entry['importPath']}` | {entry['feature']} | {entry['usagePurpose']} |"
        for entry in imported_by
    )
    candidates = "\n".join(
        f"| `{item['path']}` | {item['roleAccuracy']} | {'YES' if item['recommended'] else 'NO'} | {'; '.join(item['pros'])} | {'; '.join(item['cons'])} |"
        for item in target_candidates
    )
    static_checks = "\n".join(f"- {item}" for item in static_check_plan)
    dirty = "\n".join(f" {line}" for line in report["dirtyStatus"]) or " clean"
    validation = "\n".join(f"- `{item}`" for item in validation_plan)

    md = f"""# FRONTEND FileDropzone Common UI Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 허용 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_filedropzone_common_ui_precheck.py`
- `docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.md`
- `docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.json`
- `docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/common/FileDropzone.tsx`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/common/ui` 폴더 존재 여부
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. FileDropzone 역할 요약
- currentPath: `src/components/common/FileDropzone.tsx`
- lineCount: {report['fileDropzone']['lineCount']}
- export: default `FileDropzone`
- props: {', '.join(props)}
- 역할: drag/drop + hidden file picker UI. 선택된 파일을 `onPickFile`로 위임하고, 파일이 있을 때는 children preview UI를 렌더링한다.
- drag/drop 처리: 있음
- file picker 처리: 있음
- feature-specific policy: 없음
- OCR 전용 business logic: 없음. 단 empty-state 문구와 `uw-*` class는 문서 업로드 UI 색채가 있다.
- browser API: drag event `dataTransfer`, hidden input click/change.
- `src/common/ui` 현재 존재 여부: {report['fileDropzone']['commonUiDirectoryExists']}

Imports:
{imports}

Exports:
{exports}

## 6. importedBy 분석
| file | importPath | feature | usagePurpose |
|---|---|---|---|
{imported_table}

TestWorkspace 직접 import는 발견되지 않았다.

## 7. common/ui 적합성
- 판정: `COMMON_UI_READY_WITH_IMPORT_ONLY`
- 내부 import는 React뿐이며 components/*, feature utils, backend, template/runocr policy 의존이 없다.
- props는 `onPickFile`, `accept`, `hasFile`, `children`, `fileInputRef`, `className`, `style`로 일반적인 dropzone 형태다.
- 현재 RunOCR upload panel과 OcrCanvasPane에서 함께 쓰므로 feature 전용 UI가 아니다.

## 8. OcrCanvasPane blocker 해소 여부
- 현재 blocker: `OcrCanvasPane`이 `src/components/common/FileDropzone.tsx`를 import한다.
- `FileDropzone`을 `src/common/ui/FileDropzone.tsx`로 이동하면 `OcrCanvasPane`은 common-safe path를 참조할 수 있다.
- 이후 `OcrCanvasPane`을 `src/common/ui/OcrCanvasPane.tsx`로 옮길 때는 같은 common/ui 내부 import로 정리 가능하다.
- OcrCanvasPane의 다른 components/* 의존은 현재 발견되지 않았다.

## 9. target path 비교
| target | roleAccuracy | recommended | pros | cons |
|---|---:|---:|---|---|
{candidates}

추천 target은 `src/common/ui/FileDropzone.tsx`다. 단일 공통 UI 파일이므로 `src/common/ui/file/` 하위 폴더는 아직 과하다.

## 10. 실제 이동/보류 추천
- 추천: A. FileDropzone만 `src/common/ui/FileDropzone.tsx`로 이동
- 실제 이동 범위: `src/common/ui` 생성, FileDropzone 이동, `OcrCanvasPane`/`RunOcrWorkspace` import 수정
- 이번 micro-step에서 하지 않을 것: OcrCanvasPane 이동, Template/TestWorkspace 수정, RunOCR 로직 수정
- 위험도: LOW_MEDIUM

## 11. static check 설계
{static_checks}

## 12. dirty 상태
```text
{dirty}
```

## 13. typecheck/build 결과
- `npm run typecheck`: {report['typecheck']['status']} (exit {report['typecheck']['exitCode']})
- `npm run build`: {report['build']['status']} (exit {report['build']['exitCode']})
- stdout log: `{LOG_OUT}`
- stderr log: `{LOG_ERR}`
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 non-blocking으로 기록.

## 14. 다음 작업 제안
{validation}

다음 실제 작업은 `FRONTEND-STRUCTURE-5E-FILEDROPZONE-COMMON-UI-MOVE` micro-step으로 FileDropzone만 먼저 옮기고, 그 다음 `OcrCanvasPane` common/ui 이동을 진행하는 순서가 안전하다.
"""
    path = ROOT / "docs" / "FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.md"
    path.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    write_json()
    write_csv()
    write_md()
    print("wrote FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522 reports")
