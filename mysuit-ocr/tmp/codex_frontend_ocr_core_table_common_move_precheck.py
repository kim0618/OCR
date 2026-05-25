from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
LOG_OUT = "ocr-server/logs/codex_CODEX_FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.out.log"
LOG_ERR = "ocr-server/logs/codex_CODEX_FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.err.log"


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def line_count(path: str) -> int:
    return len(read_text(path).splitlines())


def extract_imports(path: str) -> list[str]:
    return [line.strip() for line in read_text(path).splitlines() if line.strip().startswith("import ")]


def extract_exports(path: str) -> list[str]:
    out: list[str] = []
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if stripped.startswith("export "):
            out.append(stripped.rstrip(" {"))
    return out


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


TABLE_PATH = "src/components/ocr/core/table.ts"

imported_by = [
    {
        "file": "src/components/ocr/OcrCanvasPane.tsx",
        "importPath": "./core/table",
        "importedSymbols": ["buildTableRows", "normalizeColGuides"],
        "usagePurpose": "interactive table region editing: add/normalize column guides and build repeat rows from rowTemplate",
        "feature": "shared",
        "moveImpact": "actual move must update import to the selected common utils target",
    },
    {
        "file": "src/components/template/ui/OcrRightPanel.tsx",
        "importPath": "../../ocr/core/table",
        "importedSymbols": ["normalizeColGuides"],
        "usagePurpose": "right panel table metadata display, guide count, guide removal, and guide list rendering",
        "feature": "template",
        "moveImpact": "actual move must update import to the selected common utils target",
    },
    {
        "file": "src/components/ocr/core/export.ts",
        "importPath": "./table",
        "importedSymbols": ["normalizeColGuides"],
        "usagePurpose": "template export payload normalizes colGuides and derives colX",
        "feature": "template",
        "moveImpact": "actual move must update import while export.ts remains in template/core path until separate decision",
    },
]

target_candidates = [
    {
        "path": "src/common/utils/ocrTableRegion.ts",
        "pros": [
            "Covers rowTemplate, row rectangles, table area clamping, OCR row bands, stop-row helpers, and guide normalization",
            "Broad enough for future OcrCanvasPane common/ui dependency",
            "Keeps primitive table-region helpers separate from Template save payload policy",
        ],
        "cons": ["Less explicit about column guides than ocrTableGuides.ts"],
        "roleAccuracy": "HIGH",
        "recommended": True,
    },
    {
        "path": "src/common/utils/ocrTableGuides.ts",
        "pros": ["Very clear for normalizeColGuides and future column guide editor helpers"],
        "cons": ["Too narrow for buildTableRows, autoDetectRowBands, normalizeStopKeywords, and isStopRow"],
        "roleAccuracy": "MEDIUM",
        "recommended": False,
    },
    {
        "path": "src/common/utils/ocrCanvasTable.ts",
        "pros": ["Aligns with OcrCanvasPane interactive table editing"],
        "cons": ["Sounds UI/canvas-specific even though helpers are pure table region utilities"],
        "roleAccuracy": "MEDIUM_HIGH",
        "recommended": False,
    },
    {
        "path": "src/components/template/utils/templateTableRegion.ts",
        "pros": ["Keeps future Template table column policy close to Template feature"],
        "cons": ["Unnatural for OcrCanvasPane/RunOCR shared canvas path and would make Template own shared helpers"],
        "roleAccuracy": "MEDIUM",
        "recommended": False,
    },
    {
        "path": "defer",
        "pros": ["Avoids churn before Template table column definition design"],
        "cons": ["Leaves OcrCanvasPane common/ui blocked by feature-local table helper dependency"],
        "roleAccuracy": "LOW",
        "recommended": False,
    },
]

dependency_graph = {
    "src/components/ocr/core/table.ts": {
        "imports": ["src/common/types/ocr", "src/common/utils/ocrCanvasOps"],
        "runtimeDependencies": [],
        "importedBy": [entry["file"] for entry in imported_by],
        "doesNotImport": ["src/components/*", "src/components/ocr/core/export.ts", "React", "browser APIs"],
    },
    "src/components/ocr/core/export.ts": {
        "imports": ["src/common/types/ocr", "src/common/utils/ocrCanvasOps", "src/components/ocr/core/table.ts"],
        "relationship": "template save/export mapper uses normalizeColGuides only; can remain after table helper moves",
    },
    "src/components/ocr/OcrCanvasPane.tsx": {
        "imports": ["src/common/utils/ocrCanvasOps", "src/components/ocr/core/table.ts"],
        "relationship": "shared interactive canvas consumer; table helper move reduces blocker for future common/ui move",
    },
    "src/components/template/ui/OcrRightPanel.tsx": {
        "imports": ["src/common/utils/ocrCanvasOps", "src/components/ocr/core/table.ts"],
        "relationship": "template panel consumer; only needs normalizeColGuides",
    },
    "src/components/template/ui/OcrAnnotator.tsx": {
        "imports": ["src/components/ocr/core/export.ts"],
        "relationship": "does not directly import table.ts",
    },
}

static_check_plan = [
    "target common utils file exists at src/common/utils/ocrTableRegion.ts",
    "src/components/ocr/core/table.ts is absent after actual move",
    "common utils file does not import src/components/*",
    "common utils file does not use React/browser/window/document/localStorage APIs",
    "common utils file imports OCR shape types from src/common/types/ocr",
    "common utils file imports clampRectToArea from src/common/utils/ocrCanvasOps",
    "src contains no src/components/ocr/core/table import string after move",
    "OcrCanvasPane remains at src/components/ocr/OcrCanvasPane.tsx for this phase",
    "export.ts remains at src/components/ocr/core/export.ts for this phase",
    "TestWorkspace is not modified",
    "npm run typecheck PASS",
    "npm run build PASS",
    "5A and 5B static checks PASS",
    "validation 1A checks PASS or PASS_WITH_SKIPPED_BACKUP",
]

validation_plan = [
    "node tmp/check_ocr_core_table_common_move_5c.mjs",
    "npm run typecheck",
    "npm run build",
    "node tmp/check_ocr_core_types_common_move_5a.mjs",
    "node tmp/check_ocr_core_ops_common_move_5b.mjs",
    "node tmp/check_validation_baseline_repair_1a.mjs",
    "node tmp/check_table_view_model_v1_fixtures_js.mjs",
    "node tmp/check_clean_json_v1_fixtures_js.mjs",
    "python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_OCR_CORE_TABLE_COMMON_MOVE_20260522",
]

report = {
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "projectRoot": "mysuit-ocr",
    "codeModified": False,
    "dirtyStatus": git_status(),
    "table": {
        "currentPath": TABLE_PATH,
        "lineCount": line_count(TABLE_PATH),
        "imports": extract_imports(TABLE_PATH),
        "exports": extract_exports(TABLE_PATH),
        "exportedFunctionsTypesConstants": [
            "OcrBox",
            "normalizeColGuides",
            "buildTableRows",
            "normalizeStopKeywords",
            "autoDetectRowBands",
            "isStopRow",
        ],
        "importedBy": imported_by,
        "role": "Pure OCR table-region helper: column guide normalization, repeat row construction from rowTemplate, stop keyword normalization, OCR box row band detection, and stop-row matching.",
        "sideEffects": "No module-load side effects.",
        "reactBrowserDependency": "No React/browser/window/document/localStorage dependency.",
        "commonTypesDependency": "Uses Rect from src/common/types/ocr.",
        "commonUtilsDependency": "Uses clampRectToArea from src/common/utils/ocrCanvasOps.",
        "componentsDependency": "None.",
        "commonUtilsReadiness": "COMMON_UTIL_READY_WITH_RENAME",
        "templateColumnDefinitionImpact": {
            "summary": "Current table.ts contains common primitive helpers, not Template table column policy.",
            "canMoveNow": True,
            "risk": "Future TemplateTableColumnEditor should add policy/mapping in template/utils and reuse these primitives instead of extending common with template-specific decisions.",
            "splitNeededNow": False,
        },
        "targetCandidates": target_candidates,
        "recommendation": "Move table.ts alone to src/common/utils/ocrTableRegion.ts in the actual next step.",
        "risk": "MEDIUM",
    },
    "dependencyGraph": dependency_graph,
    "moveRecommendation": {
        "choice": "A",
        "target": "src/common/utils/ocrTableRegion.ts",
        "scope": [
            "move src/components/ocr/core/table.ts to src/common/utils/ocrTableRegion.ts",
            "update imports in OcrCanvasPane, OcrRightPanel, and export.ts",
            "do not move export.ts in the same phase",
            "do not move OcrCanvasPane in the same phase",
            "do not touch TestWorkspace",
        ],
        "reason": "Smallest safe move; table.ts now imports only common types and common canvas ops and is already consumed by shared OcrCanvasPane plus Template export/panel paths.",
        "risk": "MEDIUM",
    },
    "staticCheckPlan": static_check_plan,
    "validationPlan": validation_plan,
    "typecheck": parse_log_exit("npm run typecheck", "typecheck_exit_code"),
    "build": parse_log_exit("npm run build", "build_exit_code"),
    "nextSteps": [
        "FRONTEND-STRUCTURE-5C-OCR-CORE-TABLE-COMMON-MOVE actual move",
        "export.ts template/utils move precheck or actual move after 5C",
        "Template table column definition design precheck",
        "OcrCanvasPane common/ui move after table/export dependencies are settled",
        "TPL-95328E52 dirty impact precheck",
    ],
}


def write_json() -> None:
    path = ROOT / "docs" / "FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv() -> None:
    path = ROOT / "docs" / "FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_MAP_20260522.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "importPath", "importedSymbols", "feature", "usagePurpose", "moveImpact"])
        writer.writeheader()
        for entry in imported_by:
            writer.writerow({
                "file": entry["file"],
                "importPath": entry["importPath"],
                "importedSymbols": "; ".join(entry["importedSymbols"]),
                "feature": entry["feature"],
                "usagePurpose": entry["usagePurpose"],
                "moveImpact": entry["moveImpact"],
            })


def write_md() -> None:
    imports = "\n".join(f"- `{line}`" for line in report["table"]["imports"])
    exports = "\n".join(f"- `{line}`" for line in report["table"]["exports"])
    imported_table = "\n".join(
        f"| `{entry['file']}` | `{entry['importPath']}` | {', '.join(entry['importedSymbols'])} | {entry['feature']} | {entry['usagePurpose']} |"
        for entry in imported_by
    )
    candidates = "\n".join(
        f"| `{item['path']}` | {item['roleAccuracy']} | {'YES' if item['recommended'] else 'NO'} | {'; '.join(item['pros'])} | {'; '.join(item['cons'])} |"
        for item in target_candidates
    )
    dirty = "\n".join(f" {line}" for line in report["dirtyStatus"]) or " clean"
    static_checks = "\n".join(f"- {item}" for item in static_check_plan)
    validation = "\n".join(f"- `{item}`" for item in validation_plan)

    md = f"""# FRONTEND OCR Core Table Common Move Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 허용 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_ocr_core_table_common_move_precheck.py`
- `docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/core/table.ts`
- `src/components/ocr/core/export.ts`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/common/types/ocr.ts`
- `src/common/utils/ocrCanvasOps.ts`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. table.ts 역할 요약
- currentPath: `src/components/ocr/core/table.ts`
- lineCount: {report['table']['lineCount']}
- 역할: OCR table-region helper. column guide 정규화, rowTemplate 기반 repeat row 생성, stop keyword 정규화, OCR box row band 자동 감지, stop row 판정을 담당한다.
- sideEffects: 모듈 로드 시 side effect 없음.
- React/browser 의존: 없음.
- common/types 의존: `Rect` type.
- common/utils 의존: `clampRectToArea`.
- components 의존: 없음.

Imports:
{imports}

Exports:
{exports}

## 6. importedBy 분석
| file | importPath | symbols | feature | usagePurpose |
|---|---|---|---|---|
{imported_table}

RunOCR는 `table.ts`를 직접 import하지 않지만 `RunOcrWorkspace`가 사용하는 `OcrCanvasPane` 경로를 통해 간접 영향을 받는다.

## 7. common/utils 적합성
- 판정: `COMMON_UTIL_READY_WITH_RENAME`
- 이유: 현재 `table.ts`는 Template 저장 payload 자체가 아니라 OCR table region primitive helper다.
- common 이동 시 components 의존은 생기지 않는다. 필요한 의존은 `src/common/types/ocr`와 `src/common/utils/ocrCanvasOps`로 이미 common 쪽에 있다.
- `export.ts`와 결합은 `normalizeColGuides` 단일 helper 재사용 수준이므로 export.ts와 동시 이동할 필요는 낮다.

## 8. Template table column definition 영향
- 현재 파일은 `rowTemplate`, `colGuides`, `rows`, `stopKeywords` 같은 primitive를 다룬다.
- 향후 `TemplateTableColumnEditor`의 자동 추천 + 사용자 확인 흐름에서 재사용 가능성이 높다.
- 다만 column canonical mapping, 사용자 확인 상태, 저장 payload 변환 같은 Template policy는 common에 넣지 말고 `components/template/utils`에 둬야 한다.
- 따라서 지금은 common primitive로 이동 가능하되, 이후 Template table column definition은 이 common helper 위에 Template 전용 policy layer를 얹는 방식이 적합하다.

## 9. target 파일명 비교
| target | roleAccuracy | recommended | pros | cons |
|---|---:|---:|---|---|
{candidates}

추천 target은 `src/common/utils/ocrTableRegion.ts`다. `ocrTableGuides.ts`는 column guide만 표현해서 현재 row band/stop row/helper 범위를 담기에는 좁다.

## 10. dependency graph
- `table.ts` -> `src/common/types/ocr`, `src/common/utils/ocrCanvasOps`
- `export.ts` -> `src/common/types/ocr`, `src/common/utils/ocrCanvasOps`, `./table`
- `OcrCanvasPane.tsx` -> `src/common/utils/ocrCanvasOps`, `./core/table`
- `OcrRightPanel.tsx` -> `src/common/utils/ocrCanvasOps`, `../../ocr/core/table`
- `OcrAnnotator.tsx` -> `./export` 경유, table.ts 직접 import 없음

`table.ts`는 `export.ts`를 역참조하지 않으므로 table만 먼저 이동 가능하다.

## 11. 실제 이동/보류 추천
- 추천: A. `table.ts`만 `src/common/utils/ocrTableRegion.ts`로 이동
- import 수정 범위: `OcrCanvasPane.tsx`, `OcrRightPanel.tsx`, `export.ts`
- 이번 phase에서 하지 않을 것: `export.ts` 이동, `OcrCanvasPane` 이동, `TestWorkspace` 수정
- 위험도: MEDIUM

## 12. static check 설계
{static_checks}

## 13. dirty 상태
```text
{dirty}
```

## 14. typecheck/build 결과
- `npm run typecheck`: {report['typecheck']['status']} (exit {report['typecheck']['exitCode']})
- `npm run build`: {report['build']['status']} (exit {report['build']['exitCode']})
- stdout log: `{LOG_OUT}`
- stderr log: `{LOG_ERR}`
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 non-blocking으로 기록.

## 15. 다음 작업 제안
{validation}

다음 실제 구조 작업은 `FRONTEND-STRUCTURE-5C-OCR-CORE-TABLE-COMMON-MOVE`로 잡고, 그 뒤에 `export.ts` template/utils 이동과 Template table column definition 설계를 분리하는 것이 안전하다.
"""
    path = ROOT / "docs" / "FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.md"
    path.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    write_json()
    write_csv()
    write_md()
    print("wrote FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522 reports")
