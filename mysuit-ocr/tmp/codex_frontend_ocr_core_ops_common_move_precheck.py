from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
LOG_OUT = REPO_ROOT / "ocr-server" / "logs" / "codex_CODEX_FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.out.log"
LOG_ERR = REPO_ROOT / "ocr-server" / "logs" / "codex_CODEX_FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.err.log"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def line_count(path: str) -> int:
    return len(read_text(path).splitlines())


def extract_imports(path: str) -> list[str]:
    text = read_text(path)
    return [line.strip() for line in text.splitlines() if line.strip().startswith("import ")]


def extract_exports(path: str) -> list[str]:
    text = read_text(path)
    exports: list[str] = []
    for line in text.splitlines():
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


def parse_log_exit(label: str) -> dict[str, object]:
    if not LOG_OUT.exists():
        return {"command": label, "status": "NOT_RUN", "exitCode": None, "log": rel(LOG_OUT) if LOG_OUT.is_relative_to(ROOT) else str(LOG_OUT)}
    text = LOG_OUT.read_text(encoding="utf-8", errors="replace")
    pattern = "typecheck_exit_code" if "typecheck" in label else "build_exit_code"
    match = re.search(rf"\[{pattern}\]\s+(\d+)", text)
    code = int(match.group(1)) if match else None
    return {
        "command": label,
        "status": "PASS" if code == 0 else "FAIL" if code is not None else "UNKNOWN",
        "exitCode": code,
        "stdoutLog": str(LOG_OUT),
        "stderrLog": str(LOG_ERR),
        "knownStderrNoise": "ESLint: nextVitals is not iterable is non-blocking when exit code is 0.",
    }


OPS_PATH = "src/components/ocr/core/ops.ts"

imported_by = [
    {
        "file": "src/components/ocr/OcrCanvasPane.tsx",
        "importPath": "./core/ops",
        "importedSymbols": [
            "boxLabelStyle",
            "clamp",
            "clampRectToArea",
            "normalizeRatios",
            "normalizeRect",
            "parseIndex",
            "uid",
        ],
        "usagePurpose": "interactive OCR canvas drawing, drag, resize, clamp, duplicate, label positioning, split ratio handling",
        "feature": "shared",
        "moveImpact": "actual 5B must update this import to src/common/utils/ocrCanvasOps",
    },
    {
        "file": "src/components/template/ui/OcrRightPanel.tsx",
        "importPath": "../../ocr/core/ops",
        "importedSymbols": ["normalizeRatios", "calcMultiSubRegions"],
        "usagePurpose": "right panel split/sub-region preview for selected OCR region",
        "feature": "template",
        "moveImpact": "actual 5B must update this import to common utils",
    },
    {
        "file": "src/components/ocr/core/table.ts",
        "importPath": "./ops",
        "importedSymbols": ["clampRectToArea"],
        "usagePurpose": "table row template and row band rectangles are clamped to table area",
        "feature": "shared-internal",
        "moveImpact": "actual 5B must update this import while leaving table.ts in components/ocr/core",
    },
    {
        "file": "src/components/ocr/core/export.ts",
        "importPath": "./ops",
        "importedSymbols": ["calcMultiSubRegions", "normalizeRatios"],
        "usagePurpose": "template export payload normalizes split region ratios and materializes subRegions",
        "feature": "template",
        "moveImpact": "actual 5B must update this import while leaving export.ts in components/ocr/core",
    },
]

target_candidates = [
    {
        "path": "src/common/utils/ocrCanvasOps.ts",
        "pros": ["Matches current canvas editing operations", "Broad enough for geometry, ratio, id parsing, and label style helpers", "Fits future OcrCanvasPane common/ui move"],
        "cons": ["Name is broader than pure geometry helpers"],
        "accuracy": "HIGH",
        "recommended": True,
    },
    {
        "path": "src/common/utils/ocrGeometry.ts",
        "pros": ["Clear for clamp and rectangle normalization helpers"],
        "cons": ["Too narrow for uid, parseIndex, normalizeRatios, and boxLabelStyle"],
        "accuracy": "MEDIUM",
        "recommended": False,
    },
    {
        "path": "src/common/utils/ocrRegionOps.ts",
        "pros": ["Captures region-oriented helpers and split sub-region logic"],
        "cons": ["Less direct for OcrCanvasPane ownership and table clamp reuse"],
        "accuracy": "MEDIUM_HIGH",
        "recommended": False,
    },
    {
        "path": "src/common/utils/ocrCanvasGeometry.ts",
        "pros": ["Good if helpers are split down to geometry-only functions later"],
        "cons": ["Current file contains non-geometry operations"],
        "accuracy": "MEDIUM",
        "recommended": False,
    },
    {
        "path": "defer",
        "pros": ["Avoids import churn until table/export decisions are done"],
        "cons": ["Keeps OcrCanvasPane blocked by feature-local ops dependency"],
        "accuracy": "LOW",
        "recommended": False,
    },
]

dependency_graph = {
    "src/components/ocr/core/ops.ts": {
        "imports": ["react type CSSProperties", "src/common/types/ocr"],
        "runtimeDependencies": [],
        "importedBy": [entry["file"] for entry in imported_by],
    },
    "src/components/ocr/core/table.ts": {
        "imports": ["src/common/types/ocr", "src/components/ocr/core/ops.ts"],
        "relationship": "depends on clampRectToArea only; can remain after ops moves",
    },
    "src/components/ocr/core/export.ts": {
        "imports": ["src/common/types/ocr", "src/components/ocr/core/ops.ts", "src/components/ocr/core/table.ts"],
        "relationship": "template export mapper uses ops for split region payload normalization",
    },
    "src/components/ocr/OcrCanvasPane.tsx": {
        "imports": ["src/components/ocr/core/ops.ts", "src/components/ocr/core/table.ts", "src/common/types/ocr"],
        "relationship": "direct shared UI consumer; still stays in components/ocr for 5B",
    },
    "src/components/template/ui/OcrRightPanel.tsx": {
        "imports": ["src/components/ocr/core/ops.ts", "src/components/ocr/core/table.ts", "src/common/types/ocr"],
        "relationship": "template panel consumer of ratio/sub-region helpers",
    },
}

static_check_plan = [
    "target common utils file exists at src/common/utils/ocrCanvasOps.ts",
    "src/components/ocr/core/ops.ts is absent after actual move",
    "common utils file does not import src/components/*",
    "common utils file does not use runtime React/browser/window/document/localStorage APIs",
    "common utils file imports OCR shape types from src/common/types/ocr",
    "src contains no src/components/ocr/core/ops import string after move",
    "OcrCanvasPane remains at src/components/ocr/OcrCanvasPane.tsx for 5B",
    "table.ts/export.ts remain at src/components/ocr/core for 5B",
    "TestWorkspace is not modified",
    "npm run typecheck PASS",
    "npm run build PASS",
    "tmp/check_ocr_core_types_common_move_5a.mjs PASS",
    "validation 1A checks PASS or PASS_WITH_SKIPPED_BACKUP",
]

validation_plan = [
    "node tmp/check_ocr_core_ops_common_move_5b.mjs",
    "npm run typecheck",
    "npm run build",
    "node tmp/check_ocr_core_types_common_move_5a.mjs",
    "node tmp/check_validation_baseline_repair_1a.mjs",
    "node tmp/check_runocr_formdata_keys_2a.mjs",
    "node tmp/check_runocr_response_mapping_boundary_2c.mjs",
    "node tmp/check_runocr_doc_comments_3b.mjs",
    "node tmp/check_template_workspace_move_4a.mjs",
    "node tmp/check_template_editor_ui_move_4b.mjs",
]

report = {
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "projectRoot": str(ROOT),
    "codeModified": False,
    "dirtyStatus": git_status(),
    "ops": {
        "currentPath": OPS_PATH,
        "lineCount": line_count(OPS_PATH),
        "imports": extract_imports(OPS_PATH),
        "exports": extract_exports(OPS_PATH),
        "exportedFunctionsTypesConstants": [
            "clamp",
            "normalizeRect",
            "uid",
            "parseIndex",
            "normalizeRatios",
            "boxLabelStyle",
            "calcMultiSubRegions",
            "clampRectToArea",
        ],
        "importedBy": imported_by,
        "role": "Pure OCR canvas and region operation helpers: numeric clamping, rectangle normalization, region id parsing, split ratio normalization, label style sizing, sub-region calculation, and area clamping.",
        "sideEffects": "No module-load side effects. uid uses Math.random and Date.now only when called.",
        "reactBrowserDependency": "Type-only React CSSProperties import; no runtime React/browser/window/document/localStorage dependency.",
        "commonTypesDependency": "Depends on src/common/types/ocr via Rect and Region type-only imports.",
        "componentsDependency": "None.",
        "commonUtilsReadiness": "COMMON_UTIL_READY_WITH_RENAME",
        "targetCandidates": target_candidates,
        "recommendation": "Move ops.ts alone to src/common/utils/ocrCanvasOps.ts in the actual 5B step.",
        "risk": "LOW_MEDIUM",
    },
    "dependencyGraph": dependency_graph,
    "phase5BRecommendation": {
        "choice": "A",
        "target": "src/common/utils/ocrCanvasOps.ts",
        "scope": [
            "move src/components/ocr/core/ops.ts to src/common/utils/ocrCanvasOps.ts",
            "update imports in OcrCanvasPane, OcrRightPanel, table.ts, export.ts",
            "do not move table.ts, export.ts, or OcrCanvasPane in 5B",
            "do not touch TestWorkspace",
        ],
        "reason": "Smallest safe step; ops already depends only on common OCR types plus type-only CSSProperties and is shared by Template and OcrCanvasPane/RunOCR path.",
        "risk": "LOW_MEDIUM",
    },
    "staticCheckPlan": static_check_plan,
    "validationPlan": validation_plan,
    "typecheck": parse_log_exit("npm run typecheck"),
    "build": parse_log_exit("npm run build"),
    "nextSteps": [
        "FRONTEND-STRUCTURE-5B-OCR-CORE-OPS-COMMON-MOVE actual move",
        "table.ts common/utils move precheck after 5B",
        "export.ts template/utils move precheck",
        "OcrCanvasPane common/ui move after ops/table/export dependencies are settled",
        "Template table column definition design precheck",
        "TPL-95328E52 dirty impact precheck",
    ],
}


def write_json() -> None:
    path = ROOT / "docs" / "FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv() -> None:
    path = ROOT / "docs" / "FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_MAP_20260522.csv"
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
    dirty = "\n".join(f" {line}" for line in report["dirtyStatus"]) or " clean"
    imports = "\n".join(f"- `{line}`" for line in report["ops"]["imports"])
    exports = "\n".join(f"- `{line}`" for line in report["ops"]["exports"])
    imported_table = "\n".join(
        f"| `{entry['file']}` | `{entry['importPath']}` | {', '.join(entry['importedSymbols'])} | {entry['feature']} | {entry['usagePurpose']} |"
        for entry in imported_by
    )
    candidates = "\n".join(
        f"| `{item['path']}` | {item['accuracy']} | {'YES' if item['recommended'] else 'NO'} | {'; '.join(item['pros'])} | {'; '.join(item['cons'])} |"
        for item in target_candidates
    )
    static_checks = "\n".join(f"- {item}" for item in static_check_plan)
    validation = "\n".join(f"- `{item}`" for item in validation_plan)

    md = f"""# FRONTEND OCR Core Ops Common Move Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_ocr_core_ops_common_move_precheck.py`
- `docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/core/ops.ts`
- `src/components/ocr/core/table.ts`
- `src/components/ocr/core/export.ts`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/common/types/ocr.ts`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. ops.ts 역할 요약
- currentPath: `src/components/ocr/core/ops.ts`
- lineCount: {report['ops']['lineCount']}
- 역할: OCR canvas/region operation helper. clamp, rect normalization, uid/id parsing, split ratio normalization, label style sizing, sub-region calculation, area clamp를 담당한다.
- sideEffects: 모듈 로드 시 side effect 없음. `uid`는 호출 시에만 `Math.random`/`Date.now`를 사용한다.
- React/browser 의존: React는 `CSSProperties` type-only import뿐이며 runtime React/window/document/localStorage 의존은 없다.
- components 의존: 없음.
- common types 의존: `src/common/types/ocr`의 `Rect`, `Region` type-only import.

Imports:
{imports}

Exports:
{exports}

## 6. importedBy 분석
| file | importPath | symbols | feature | usagePurpose |
|---|---|---|---|---|
{imported_table}

RunOCR는 `ops.ts`를 직접 import하지 않지만 `RunOcrWorkspace`가 사용하는 `OcrCanvasPane` 경로를 통해 간접 영향을 받는다.

## 7. common/utils 적합성
- 판정: `COMMON_UTIL_READY_WITH_RENAME`
- 이유: Template panel, OcrCanvasPane, table/export helper가 같이 쓰는 OCR canvas/region pure helper이며 common에서 components를 참조할 필요가 없다.
- 주의: `boxLabelStyle` 때문에 React `CSSProperties` type-only import가 남는다. 이는 runtime React dependency가 아니므로 허용 가능하지만, 5B static check에서 type-only 여부를 확인하는 것이 좋다.

## 8. target 파일명 비교
| target | roleAccuracy | recommended | pros | cons |
|---|---:|---:|---|---|
{candidates}

추천 target은 `src/common/utils/ocrCanvasOps.ts`다. `ocrGeometry.ts`는 현재 파일의 id/ratio/label style 책임까지 담기에는 좁다.

## 9. dependency graph
- `ops.ts` -> `src/common/types/ocr`, React `CSSProperties` type-only
- `table.ts` -> `src/common/types/ocr`, `./ops`
- `export.ts` -> `src/common/types/ocr`, `./ops`, `./table`
- `OcrCanvasPane.tsx` -> `./core/ops`, `./core/table`, `src/common/types/ocr`
- `OcrRightPanel.tsx` -> `../../ocr/core/ops`, `../../ocr/core/table`, `src/common/types/ocr`

`table.ts`와 `export.ts`가 `ops.ts`를 의존하지만, `ops.ts`는 table/export를 역참조하지 않는다. 따라서 ops만 먼저 common으로 이동 가능하다.

## 10. 5B 실제 이동 추천
- 추천: A. `ops.ts`만 `src/common/utils/ocrCanvasOps.ts`로 이동
- import 수정 범위: `OcrCanvasPane.tsx`, `OcrRightPanel.tsx`, `table.ts`, `export.ts`
- 5B에서 하지 않을 것: `table.ts` 이동, `export.ts` 이동, `OcrCanvasPane` 이동, `TestWorkspace` 수정
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

다음 실제 구조 작업은 `FRONTEND-STRUCTURE-5B-OCR-CORE-OPS-COMMON-MOVE`로 잡고, 그 뒤에 `table.ts` common/utils 이동 precheck와 `export.ts` template/utils 이동 precheck를 분리하는 것이 안전하다.
"""
    path = ROOT / "docs" / "FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.md"
    path.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    write_json()
    write_csv()
    write_md()
    print("wrote FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522 reports")
