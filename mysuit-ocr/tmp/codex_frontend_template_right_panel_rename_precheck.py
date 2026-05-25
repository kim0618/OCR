from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
LOG_OUT = "ocr-server/logs/codex_CODEX_FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_NO_PROD_MODIFY.out.log"
LOG_ERR = "ocr-server/logs/codex_CODEX_FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_NO_PROD_MODIFY.err.log"


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


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


RIGHT_PANEL_PATH = "src/components/template/ui/OcrRightPanel.tsx"

props = [
    "imgRef",
    "templateName",
    "setTemplateName",
    "documentType",
    "setDocumentType",
    "loaded",
    "regions",
    "setRegions",
    "selectedId",
    "setSelectedId",
    "rowTemplateTargetId",
    "setRowTemplateTargetId",
    "colGuideTargetId",
    "setColGuideTargetId",
    "updateName",
    "deleteRegion",
]

imported_by = [
    {
        "file": "src/components/template/ui/OcrAnnotator.tsx",
        "importPath": "./OcrRightPanel",
        "usagePurpose": "Template annotator right panel for template metadata, output field definitions, selected region preview, table controls, and table column metadata.",
        "feature": "template",
        "renameImpact": "actual rename must update this import path and optionally imported local identifier",
    }
]

rename_options = [
    {
        "option": "A",
        "title": "file only rename",
        "scope": ["OcrRightPanel.tsx -> TemplateRightPanel.tsx", "OcrAnnotator import path update only"],
        "pros": ["Smallest diff", "No internal symbol churn", "Lowest logic risk"],
        "cons": ["File name and default function name diverge", "OcrRightPanel string remains in source"],
        "staticCheckDifficulty": "LOW",
        "recommended": False,
    },
    {
        "option": "B",
        "title": "file + component symbol rename",
        "scope": [
            "OcrRightPanel.tsx -> TemplateRightPanel.tsx",
            "export default function OcrRightPanel -> TemplateRightPanel",
            "OcrAnnotator local import identifier -> TemplateRightPanel",
        ],
        "pros": ["File and component naming align", "Template ownership is clear to maintainers", "Still a narrow single-consumer rename"],
        "cons": ["Slightly more text churn than file-only rename"],
        "staticCheckDifficulty": "MEDIUM_LOW",
        "recommended": True,
    },
    {
        "option": "C",
        "title": "defer rename",
        "scope": ["No source changes"],
        "pros": ["No immediate churn"],
        "cons": ["Leaves Template-only UI with OCR-prefixed name after structure cleanup"],
        "staticCheckDifficulty": "LOW",
        "recommended": False,
    },
]

static_check_plan = [
    "src/components/template/ui/TemplateRightPanel.tsx exists",
    "src/components/template/ui/OcrRightPanel.tsx is absent",
    "OcrAnnotator imports ./TemplateRightPanel",
    "OcrAnnotator renders <TemplateRightPanel",
    "components/ocr/OcrRightPanel string is absent",
    "components/template/ui/OcrRightPanel import path string is absent",
    "RunOCR files are not modified",
    "TestWorkspace is not modified",
    "common/ui/OcrCanvasPane.tsx is not modified",
    "npm run typecheck PASS",
    "npm run build PASS",
    "4A/4B/5A/5B/5C/5D/5E/5F checks PASS where applicable",
    "validation baseline repair check PASS",
]

validation_plan = [
    "node tmp/check_template_right_panel_rename_6a.mjs",
    "npm run typecheck",
    "npm run build",
    "node tmp/check_template_workspace_move_4a.mjs",
    "node tmp/check_template_editor_ui_move_4b.mjs",
    "node tmp/check_ocr_core_types_common_move_5a.mjs",
    "node tmp/check_ocr_core_ops_common_move_5b.mjs",
    "node tmp/check_ocr_core_table_common_move_5c.mjs",
    "node tmp/check_template_export_payload_move_5d.mjs",
    "node tmp/check_filedropzone_common_ui_move_5e.mjs",
    "node tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs",
    "node tmp/check_validation_baseline_repair_1a.mjs",
]

report = {
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "projectRoot": "mysuit-ocr",
    "codeModified": False,
    "dirtyStatus": git_status(),
    "rightPanel": {
        "currentPath": RIGHT_PANEL_PATH,
        "lineCount": line_count(RIGHT_PANEL_PATH),
        "imports": extract_imports(RIGHT_PANEL_PATH),
        "exports": extract_exports(RIGHT_PANEL_PATH),
        "props": props,
        "importedBy": imported_by,
        "role": "Template editor right panel for template name/document type, output field definition, selected region preview, table row/column guide controls, stop keywords, and table column metadata.",
        "templateOnly": True,
        "ocrCanvasPaneRelationship": "Receives selection/region/table state coordinated with OcrCanvasPane through OcrAnnotator props; does not import OcrCanvasPane directly.",
        "ocrAnnotatorRelationship": "Only direct production consumer is OcrAnnotator, which passes all state/callback props.",
        "runocrTestDependency": "No direct RunOCR or TestWorkspace import found.",
        "renameReadiness": "RENAME_READY_FILE_AND_SYMBOLS",
        "renameOptions": rename_options,
        "recommendation": "Rename file and default component/local import symbol to TemplateRightPanel in a narrow micro-step.",
        "risk": "LOW_MEDIUM",
    },
    "staticCheckPlan": static_check_plan,
    "validationPlan": validation_plan,
    "typecheck": parse_log_exit("npm run typecheck", "typecheck_exit_code"),
    "build": parse_log_exit("npm run build", "build_exit_code"),
    "nextSteps": [
        "FRONTEND-STRUCTURE-6A-TEMPLATE-RIGHT-PANEL-RENAME micro-step",
        "Template table column definition design precheck",
        "TPL-95328E52 dirty impact precheck",
    ],
}


def write_json() -> None:
    path = ROOT / "docs" / "FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv() -> None:
    path = ROOT / "docs" / "FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_MAP_20260522.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "importPath", "feature", "usagePurpose", "renameImpact"])
        writer.writeheader()
        for entry in imported_by:
            writer.writerow(entry)


def write_md() -> None:
    imports = "\n".join(f"- `{line}`" for line in report["rightPanel"]["imports"])
    exports = "\n".join(f"- `{line}`" for line in report["rightPanel"]["exports"])
    imported_table = "\n".join(
        f"| `{entry['file']}` | `{entry['importPath']}` | {entry['feature']} | {entry['usagePurpose']} |"
        for entry in imported_by
    )
    options = "\n".join(
        f"| {item['option']} | {item['title']} | {'YES' if item['recommended'] else 'NO'} | {item['staticCheckDifficulty']} | {'; '.join(item['pros'])} | {'; '.join(item['cons'])} |"
        for item in rename_options
    )
    static_checks = "\n".join(f"- {item}" for item in static_check_plan)
    validation = "\n".join(f"- `{item}`" for item in validation_plan)
    dirty = "\n".join(f" {line}" for line in report["dirtyStatus"]) or " clean"

    md = f"""# FRONTEND Template Right Panel Rename Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 허용 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_template_right_panel_rename_precheck.py`
- `docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522.md`
- `docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522.json`
- `docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/common/ui/OcrCanvasPane.tsx`
- `src/components/template/TemplateWorkspace.tsx`
- `src/app/ocr/page.tsx`
- `src/app/template/page.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. OcrRightPanel 역할 요약
- currentPath: `src/components/template/ui/OcrRightPanel.tsx`
- lineCount: {report['rightPanel']['lineCount']}
- export: default `OcrRightPanel`
- props: {', '.join(props)}
- 역할: Template editor right panel. 템플릿명/문서유형, 출력 필드 정의, 선택 region preview, table row/col guide, stop keywords, table column metadata를 다룬다.
- Template 전용 여부: YES
- OcrCanvasPane 관계: 직접 import하지 않고 OcrAnnotator가 selection/region/table state를 중재한다.
- OcrAnnotator 관계: 유일한 production consumer.
- RunOCR/Test 의존: 직접 import 없음.

Imports:
{imports}

Exports:
{exports}

## 6. importedBy 분석
| file | importPath | feature | usagePurpose |
|---|---|---|---|
{imported_table}

`components/ocr/OcrRightPanel` 런타임 import는 남아 있지 않다. 검색 결과의 다수는 과거 docs/tmp static check 기록이다.

## 7. rename 적합성
- 판정: `RENAME_READY_FILE_AND_SYMBOLS`
- 이유: 현재 파일은 Template 전용 UI이고 direct consumer가 `OcrAnnotator` 하나뿐이다.
- 파일명만 바꾸면 내부 default function 이름 `OcrRightPanel`이 남아 파일명과 심볼명이 어긋난다.
- 따라서 실제 rename micro-step에서는 파일명과 default component/local import symbol을 함께 `TemplateRightPanel`로 맞추는 것이 유지보수성 측면에서 낫다.
- `Props` type은 로컬 비-export 타입이므로 `TemplateRightPanelProps`로 바꾸는 것은 선택 사항이다. 이번 추천은 component symbol까지이며, props type rename은 static check 난이도를 조금 올리므로 필요 시 포함한다.

## 8. rename 범위 후보 비교
| option | title | recommended | staticCheck | pros | cons |
|---|---|---:|---|---|---|
{options}

## 9. 실제 rename 추천
- 추천: B. 파일명 + default component/local import symbol rename
- 실제 범위:
  - `src/components/template/ui/OcrRightPanel.tsx` -> `src/components/template/ui/TemplateRightPanel.tsx`
  - `export default function OcrRightPanel` -> `TemplateRightPanel`
  - `OcrAnnotator` import path/local identifier/render tag 수정
- 수정하지 않을 범위: RunOCR, TestWorkspace, common/ui/OcrCanvasPane, TemplateWorkspace, app routes.
- 위험도: LOW_MEDIUM

## 10. static check 설계
{static_checks}

## 11. dirty 상태
```text
{dirty}
```

## 12. typecheck/build 결과
- `npm run typecheck`: {report['typecheck']['status']} (exit {report['typecheck']['exitCode']})
- `npm run build`: {report['build']['status']} (exit {report['build']['exitCode']})
- stdout log: `{LOG_OUT}`
- stderr log: `{LOG_ERR}`
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 non-blocking으로 기록.

## 13. 다음 작업 제안
{validation}

다음 실제 작업은 `FRONTEND-STRUCTURE-6A-TEMPLATE-RIGHT-PANEL-RENAME`으로 작게 진행하고, 이후 Template table column definition 설계 precheck로 이어가는 것이 자연스럽다.
"""
    path = ROOT / "docs" / "FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522.md"
    path.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    write_json()
    write_csv()
    write_md()
    print("wrote FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522 reports")
