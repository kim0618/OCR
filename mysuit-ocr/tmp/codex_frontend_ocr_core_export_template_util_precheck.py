from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
LOG_OUT = "ocr-server/logs/codex_CODEX_FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_NO_PROD_MODIFY.out.log"
LOG_ERR = "ocr-server/logs/codex_CODEX_FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_NO_PROD_MODIFY.err.log"


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def exists(path: str) -> bool:
    return (ROOT / path).exists()


def line_count(path: str) -> int:
    return len(read_text(path).splitlines())


def extract_imports(path: str) -> list[str]:
    return [line.strip() for line in read_text(path).splitlines() if line.strip().startswith("import ")]


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


EXPORT_PATH = "src/components/ocr/core/export.ts"

imported_by = [
    {
        "file": "src/components/template/ui/OcrAnnotator.tsx",
        "importPath": "../../ocr/core/export",
        "importedSymbols": ["buildExportPayload"],
        "usagePurpose": "Template editor save/export payload is memoized from templateName, loaded image, regions, and documentType before save.",
        "feature": "template",
        "moveImpact": "actual 5D must update this single import to ../utils/buildTemplateExportPayload or equivalent",
    }
]

target_candidates = [
    {
        "path": "src/components/template/utils/buildTemplateExportPayload.ts",
        "pros": [
            "Names the only exported function's responsibility directly",
            "Clearly scoped to Template persistence payload rather than generic mapping",
            "Leaves future TemplateTableColumnEditor policy free to live in separate files",
        ],
        "cons": ["Longer filename"],
        "roleAccuracy": "HIGH",
        "recommended": True,
    },
    {
        "path": "src/components/template/utils/templateMapper.ts",
        "pros": ["Good umbrella name if multiple template import/export mappers are added later"],
        "cons": ["Too broad for the current single export and could attract canonical mapping/column policy too early"],
        "roleAccuracy": "MEDIUM",
        "recommended": False,
    },
    {
        "path": "src/components/template/utils/templateExport.ts",
        "pros": ["Short and template-specific"],
        "cons": ["Less explicit than buildTemplateExportPayload; could be confused with UI/export command code"],
        "roleAccuracy": "MEDIUM_HIGH",
        "recommended": False,
    },
    {
        "path": "src/components/template/utils/exportTemplatePayload.ts",
        "pros": ["Describes output shape and avoids generic mapper naming"],
        "cons": ["Verb-object order is less aligned with current buildExportPayload function name"],
        "roleAccuracy": "MEDIUM_HIGH",
        "recommended": False,
    },
    {
        "path": "defer",
        "pros": ["Avoids one import update until Template table column design"],
        "cons": ["Leaves src/components/ocr/core containing a Template-only file and delays OcrCanvasPane common/ui cleanup"],
        "roleAccuracy": "LOW",
        "recommended": False,
    },
]

dependency_graph = {
    "src/components/ocr/core/export.ts": {
        "imports": [
            "src/common/types/ocr",
            "src/common/utils/ocrCanvasOps",
            "src/common/utils/ocrTableRegion",
        ],
        "runtimeDependencies": [],
        "importedBy": [entry["file"] for entry in imported_by],
        "doesNotImport": ["src/components/*", "React", "browser APIs", "RunOCR", "TestWorkspace"],
    },
    "src/components/template/ui/OcrAnnotator.tsx": {
        "imports": ["src/components/ocr/core/export.ts"],
        "relationship": "only direct production consumer; owns template save flow",
    },
    "src/components/ocr/OcrCanvasPane.tsx": {
        "imports": [],
        "relationship": "does not import export.ts; export cleanup is a structural prerequisite, not a direct canvas dependency",
    },
    "src/components/template/ui/OcrRightPanel.tsx": {
        "imports": [],
        "relationship": "does not import export.ts",
    },
    "src/components/runocr/RunOcrWorkspace.tsx": {
        "imports": [],
        "relationship": "does not import export.ts",
    },
    "src/components/test/TestWorkspace.tsx": {
        "imports": [],
        "relationship": "does not import export.ts",
    },
}

static_check_plan = [
    "target template utils file exists at src/components/template/utils/buildTemplateExportPayload.ts",
    "src/components/ocr/core/export.ts is absent after actual move",
    "src/components/ocr/core folder is empty or removable after actual move",
    "template utils file may import src/common/types/ocr and src/common/utils/*",
    "template utils file does not import RunOCR or TestWorkspace",
    "OcrAnnotator import points to template utils target",
    "OcrCanvasPane remains at src/components/ocr/OcrCanvasPane.tsx for this phase",
    "common/utils files do not import src/components/*",
    "TestWorkspace is not modified",
    "npm run typecheck PASS",
    "npm run build PASS",
    "5A, 5B, and 5C static checks PASS",
    "validation 1A checks PASS or PASS_WITH_SKIPPED_BACKUP",
]

validation_plan = [
    "node tmp/check_template_export_payload_move_5d.mjs",
    "npm run typecheck",
    "npm run build",
    "node tmp/check_ocr_core_types_common_move_5a.mjs",
    "node tmp/check_ocr_core_ops_common_move_5b.mjs",
    "node tmp/check_ocr_core_table_common_move_5c.mjs",
    "node tmp/check_validation_baseline_repair_1a.mjs",
    "node tmp/check_table_view_model_v1_fixtures_js.mjs",
    "node tmp/check_clean_json_v1_fixtures_js.mjs",
    "python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522",
]

report = {
    "generatedAt": datetime.now(timezone.utc).isoformat(),
    "projectRoot": "mysuit-ocr",
    "codeModified": False,
    "dirtyStatus": git_status(),
    "export": {
        "currentPath": EXPORT_PATH,
        "lineCount": line_count(EXPORT_PATH),
        "imports": extract_imports(EXPORT_PATH),
        "exports": extract_exports(EXPORT_PATH),
        "exportedFunctionsTypesConstants": ["buildExportPayload"],
        "importedBy": imported_by,
        "role": "Template save/export payload builder: serializes template metadata, source image info, regions, multi subRegions, check mode, and table payload fields.",
        "sideEffects": "No module-load side effects.",
        "reactBrowserDependency": "No React/browser/window/document/localStorage dependency.",
        "commonTypesDependency": "Uses LoadedImage, Rect, and Region from src/common/types/ocr.",
        "commonUtilsDependency": "Uses calcMultiSubRegions/normalizeRatios from ocrCanvasOps and normalizeColGuides from ocrTableRegion.",
        "componentsDependency": "None.",
        "templateUtilReadiness": "TEMPLATE_UTIL_READY_WITH_RENAME",
        "commonUtilsRecommendation": "COMMON_UTIL_NOT_RECOMMENDED because the output is Template persistence/save payload policy, not a shared primitive.",
        "targetCandidates": target_candidates,
        "recommendation": "Move export.ts to src/components/template/utils/buildTemplateExportPayload.ts in actual 5D.",
        "risk": "LOW_MEDIUM",
        "templateUtilsDirectoryExists": exists("src/components/template/utils"),
    },
    "dependencyGraph": dependency_graph,
    "moveRecommendation": {
        "choice": "A",
        "target": "src/components/template/utils/buildTemplateExportPayload.ts",
        "scope": [
            "create src/components/template/utils if absent",
            "move src/components/ocr/core/export.ts to the target filename",
            "update OcrAnnotator import only",
            "do not move OcrCanvasPane in the same phase",
            "do not implement Template table column definition in the same phase",
            "do not touch TestWorkspace",
        ],
        "reason": "Only OcrAnnotator imports buildExportPayload, and the file now depends only on common primitives. Moving it removes the last Template-only file from src/components/ocr/core before OcrCanvasPane common/ui work.",
        "risk": "LOW_MEDIUM",
    },
    "staticCheckPlan": static_check_plan,
    "validationPlan": validation_plan,
    "typecheck": parse_log_exit("npm run typecheck", "typecheck_exit_code"),
    "build": parse_log_exit("npm run build", "build_exit_code"),
    "nextSteps": [
        "FRONTEND-STRUCTURE-5D-TEMPLATE-EXPORT-PAYLOAD-MOVE actual move",
        "OcrCanvasPane common/ui move precheck after core folder is empty",
        "Template table column definition design precheck",
        "TPL-95328E52 dirty impact precheck",
    ],
}


def write_json() -> None:
    path = ROOT / "docs" / "FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv() -> None:
    path = ROOT / "docs" / "FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_MAP_20260522.csv"
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
    imports = "\n".join(f"- `{line}`" for line in report["export"]["imports"])
    exports = "\n".join(f"- `{line}`" for line in report["export"]["exports"])
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

    md = f"""# FRONTEND OCR Core Export Template Util Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 허용 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_ocr_core_export_template_util_precheck.py`
- `docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/core/export.ts`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/common/types/ocr.ts`
- `src/common/utils/ocrCanvasOps.ts`
- `src/common/utils/ocrTableRegion.ts`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. export.ts 역할 요약
- currentPath: `src/components/ocr/core/export.ts`
- lineCount: {report['export']['lineCount']}
- 역할: Template save/export payload builder. template metadata, image info, regions, multi subRegions, check mode, table payload를 저장용 구조로 직렬화한다.
- sideEffects: 모듈 로드 시 side effect 없음.
- React/browser 의존: 없음.
- common/types 의존: `LoadedImage`, `Rect`, `Region`.
- common/utils 의존: `calcMultiSubRegions`, `normalizeRatios`, `normalizeColGuides`.
- components 의존: 없음.
- `src/components/template/utils` 현재 존재 여부: {report['export']['templateUtilsDirectoryExists']}

Imports:
{imports}

Exports:
{exports}

## 6. importedBy 분석
| file | importPath | symbols | feature | usagePurpose |
|---|---|---|---|---|
{imported_table}

RunOCR, OcrCanvasPane, OcrRightPanel, TestWorkspace는 `export.ts`를 직접 import하지 않는다.

## 7. Template 전용 여부
- 판정: `TEMPLATE_UTIL_READY_WITH_RENAME`
- common/utils 판정: `COMMON_UTIL_NOT_RECOMMENDED`
- 이유: output은 Template 저장/persistence payload 정책이다. 좌표/캔버스/table primitive가 아니라 save contract를 구성한다.
- 직접 production consumer는 `OcrAnnotator.tsx` 하나뿐이며, 저장 직전 `exportPayload` memo와 save body 구성에 연결된다.

## 8. target 파일명 비교
| target | roleAccuracy | recommended | pros | cons |
|---|---:|---:|---|---|
{candidates}

추천 target은 `src/components/template/utils/buildTemplateExportPayload.ts`다. `templateMapper.ts`는 이후 import/load mapper나 column canonical mapping까지 끌어들일 수 있어 지금 이름으로는 너무 넓다.

## 9. dependency graph
- `export.ts` -> `src/common/types/ocr`, `src/common/utils/ocrCanvasOps`, `src/common/utils/ocrTableRegion`
- `OcrAnnotator.tsx` -> `../../ocr/core/export`
- `OcrCanvasPane.tsx` -> export.ts 직접 import 없음
- `OcrRightPanel.tsx` -> export.ts 직접 import 없음
- `RunOcrWorkspace.tsx` -> export.ts 직접 import 없음
- `TestWorkspace.tsx` -> export.ts 직접 import 없음

export.ts만 먼저 이동 가능하다. 이 이동은 OcrCanvasPane의 직접 의존을 줄이는 작업은 아니지만, `src/components/ocr/core`의 마지막 Template-only 파일을 제거해 OcrCanvasPane common/ui 이동 전 구조를 정리한다.

## 10. 실제 이동/보류 추천
- 추천: A. `export.ts`만 `src/components/template/utils/buildTemplateExportPayload.ts`로 이동
- import 수정 범위: `src/components/template/ui/OcrAnnotator.tsx` 1곳
- 실제 5D에서 필요: `src/components/template/utils` 디렉터리가 없으면 생성
- 이번 phase에서 하지 않을 것: `OcrCanvasPane` 이동, Template table column definition 구현, TestWorkspace 수정
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

다음 실제 구조 작업은 `FRONTEND-STRUCTURE-5D-TEMPLATE-EXPORT-PAYLOAD-MOVE`로 잡고, 그 뒤에 OcrCanvasPane common/ui 이동 precheck를 진행하는 것이 자연스럽다.
"""
    path = ROOT / "docs" / "FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.md"
    path.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    write_json()
    write_csv()
    write_md()
    print("wrote FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522 reports")
