from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "lib" / "cleanJsonBuilder.ts"
FORMATTERS = ROOT / "src" / "common" / "utils" / "ocrResultFormatters.ts"
LABELS = ROOT / "src" / "common" / "utils" / "invoiceFieldLabels.ts"
MARKDOWN = ROOT / "src" / "common" / "utils" / "markdownReportBuilder.ts"
REPORT_MD = ROOT / "docs" / "FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_20260522.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_20260522.json"
REPORT_CSV = ROOT / "docs" / "FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_MAP_20260522.csv"

ANALYSIS_SCOPE = [
    "src/lib/cleanJsonBuilder.ts",
    "src/common/utils/ocrResultFormatters.ts",
    "src/common/utils/invoiceFieldLabels.ts",
    "src/common/utils/markdownReportBuilder.ts",
    "src/components/runocr",
    "src/components/template",
    "src/components/history",
    "src/common",
    "src/components/test/TestWorkspace.tsx",
    "src/app",
]

REFERENCE_REPORTS = [
    "docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md",
    "docs/FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522.md",
    "docs/FRONTEND_LIB_1B_INVOICE_FIELD_LABELS_COMMON_MOVE_20260522.md",
    "docs/FRONTEND_LIB_1C_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_20260522.md",
    "docs/FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME_20260522.md",
    "docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.md",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def git_status() -> list[str]:
    proc = subprocess.run(["git", "status", "--short"], cwd=ROOT, text=True, capture_output=True, check=False)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def command_result(name: str) -> dict[str, object]:
    path = ROOT / "tmp" / f"codex_lib_clean_json_builder_common_move_precheck_{name}.json"
    if not path.exists():
        return {"command": f"npm run {name}", "exitCode": None, "status": "NOT_RUN"}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def source_files() -> list[Path]:
    files: list[Path] = []
    for scope in ANALYSIS_SCOPE:
        path = ROOT / scope
        if path.is_file():
            files.append(path)
        elif path.exists():
            files.extend(
                child for child in path.rglob("*")
                if child.is_file() and child.suffix in {".ts", ".tsx", ".js", ".jsx"}
            )
    files.extend(child for child in (ROOT / "src" / "lib").glob("*") if child.suffix in {".ts", ".tsx"})
    files.extend(child for child in (ROOT / "tmp").glob("check_clean_json*.mjs") if child.is_file())
    return sorted(set(files))


def extract_imports(text: str) -> list[str]:
    pattern = re.compile(r"^import\s+.*?;\s*$", re.MULTILINE | re.DOTALL)
    return [" ".join(match.group(0).split()) for match in pattern.finditer(text)]


def extract_exports(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip().startswith("export ")]


def exported_names(text: str) -> list[str]:
    names: list[str] = []
    for pattern in [
        r"export\s+const\s+([A-Za-z0-9_]+)",
        r"export\s+function\s+([A-Za-z0-9_]+)",
        r"export\s+type\s+([A-Za-z0-9_]+)",
        r"export\s+interface\s+([A-Za-z0-9_]+)",
    ]:
        names.extend(re.findall(pattern, text))
    return names


IMPORT_RE = re.compile(
    r"import\s+(?P<body>[\s\S]*?)\s+from\s+['\"](?P<path>[^'\"]+)['\"]|"
    r"import\(\s*['\"](?P<dynamic>[^'\"]+)['\"]\s*\)"
)


def feature_for(path: Path) -> str:
    p = rel(path)
    if p.startswith("src/components/runocr") or p.startswith("src/app/runocr"):
        return "runocr"
    if p.startswith("src/components/template") or p.startswith("src/app/template") or p.startswith("src/app/ocr"):
        return "template"
    if p.startswith("src/components/history") or p.startswith("src/app/history"):
        return "history"
    if p.startswith("src/components/autorestore") or p.startswith("src/app/autorestore"):
        return "restore"
    if p.startswith("src/components/login") or p.startswith("src/app/login"):
        return "login"
    if p.startswith("src/components/layout") or p in {"src/app/layout.tsx", "src/app/page.tsx"}:
        return "layout"
    if p.startswith("src/components/test") or p.startswith("src/app/test"):
        return "test"
    if p.startswith("src/common"):
        return "common"
    if p.startswith("src/lib"):
        return "lib"
    if p.startswith("src/app"):
        return "app"
    if p.startswith("tmp"):
        return "fixture-runner"
    return "unknown"


def imported_symbols(body: str | None) -> str:
    return "*dynamic*" if not body else " ".join(body.split())


def find_imported_by(files: list[Path]) -> list[dict[str, object]]:
    module_paths = {
        "@/lib/cleanJsonBuilder",
        "../../lib/cleanJsonBuilder",
        "../lib/cleanJsonBuilder",
        "./cleanJsonBuilder",
        "src/lib/cleanJsonBuilder",
    }
    rows: list[dict[str, object]] = []
    for file in files:
        if file == TARGET:
            continue
        text = read(file)
        for match in IMPORT_RE.finditer(text):
            import_path = match.group("path") or match.group("dynamic")
            if import_path not in module_paths:
                continue
            rows.append({
                "file": rel(file),
                "importPath": import_path,
                "importKind": "dynamic" if match.group("dynamic") else "static",
                "importedSymbols": imported_symbols(match.group("body")),
                "feature": feature_for(file),
                "needsImportUpdateOnMove": True,
                "testWorkspaceImpact": feature_for(file) == "test",
            })
    return rows


def direct_string_consumers(files: list[Path]) -> list[dict[str, object]]:
    patterns = ["src/lib/cleanJsonBuilder.ts", "cleanJsonBuilder.ts", "@/lib/cleanJsonBuilder"]
    rows: list[dict[str, object]] = []
    for file in files:
        if file == TARGET:
            continue
        text = read(file)
        for pattern in patterns:
            if pattern in text:
                rows.append({"file": rel(file), "pattern": pattern, "feature": feature_for(file)})
    return rows


def symbol_hits(files: list[Path], names: list[str]) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    for file in files:
        if file == TARGET:
            continue
        text = read(file)
        for name in names:
            if re.search(rf"\b{re.escape(name)}\b", text):
                hits.append({"file": rel(file), "symbol": name, "feature": feature_for(file)})
    return hits


def has_any(text: str, tokens: list[str]) -> bool:
    return any(token in text for token in tokens)


def role(text: str, imports: list[str]) -> dict[str, object]:
    component_deps = [item for item in imports if "/components/" in item or "../components/" in item]
    return {
        "mainResponsibility": "Pure Clean JSON v1 output builder for RunOCR preview/copy/export paths and fixture contract checks.",
        "cleanJsonBuilder": "buildCleanJsonResult" in text,
        "sideEffects": has_any(text, ["localStorage.setItem", "sessionStorage.setItem", "indexedDB", "fetch(", "document.", "window."]),
        "browserLocalStorageIndexedDB": has_any(text, ["localStorage", "sessionStorage", "indexedDB", "IDB"]),
        "reactDependency": bool(re.search(r"from ['\"]react['\"]|React\.", text)),
        "componentsDependency": component_deps,
        "featurePolicyTags": ["clean-json-v1", "runocr-preview", "copy-export", "fixture-contract", "invoice-table-display"],
        "commonUtilsFit": "Good fit with a caveat: deterministic Clean JSON builder with no React/DOM/storage/backend/components dependency, but it currently imports invoiceTableDisplay from src/lib until that helper moves.",
    }


def dependency_impact() -> dict[str, object]:
    text = read(TARGET)
    return {
        "importsOcrResultFormatters": "@/common/utils/ocrResultFormatters" in text or "@/lib/ocrResultFormatters" in text,
        "importsInvoiceFieldLabels": "@/common/utils/invoiceFieldLabels" in text or "@/lib/invoiceFieldLabels" in text,
        "importsMarkdownReportBuilder": "@/common/utils/markdownReportBuilder" in text or "@/lib/markdownReportBuilder" in text,
        "importsInvoiceTableDisplay": "@/lib/invoiceTableDisplay" in text,
        "importsStructuredTableViewModel": "@/lib/structuredTableViewModel" in text,
        "temporarySrcLibDependencyAfterMove": "@/lib/invoiceTableDisplay" in text,
        "recommendedInvoiceTableDisplayFollowup": "Move invoiceTableDisplay.ts to common/utils in a later dedicated step, or update cleanJsonBuilder import after that move.",
        "commonUtilsFormatterExists": FORMATTERS.exists(),
        "commonUtilsLabelsExists": LABELS.exists(),
        "commonUtilsMarkdownExists": MARKDOWN.exists(),
        "circularDependencyRisk": "LOW",
        "reason": "cleanJsonBuilder is leaf-like except for invoiceTableDisplay helpers. No common/utils file imports cleanJsonBuilder today, so moving it does not introduce a cycle.",
    }


def clean_json_fixture_impact(files: list[Path]) -> dict[str, object]:
    runner = ROOT / "tmp" / "check_clean_json_v1_fixtures_js.mjs"
    runner_text = read(runner) if runner.exists() else ""
    direct_path = "src/lib/cleanJsonBuilder.ts" in runner_text
    return {
        "runnerPath": rel(runner) if runner.exists() else "MISSING",
        "runnerExists": runner.exists(),
        "runnerDirectlyReferencesSourcePath": direct_path,
        "impact": "The JS Clean JSON fixture runner directly references src/lib/cleanJsonBuilder.ts and must be updated or made path-aware in the actual move/static-check step. Fixture data itself should not be modified.",
        "fixtureRebakeNeeded": False,
        "recommendedCheck": "node tmp/check_clean_json_v1_fixtures_js.mjs",
        "expectedAfterImportOnlyMove": "PASS if runner source path/import is updated to src/common/utils/cleanJsonBuilder.ts and logic remains unchanged.",
    }


def target_candidates() -> list[dict[str, object]]:
    return [
        {
            "target": "src/common/utils/cleanJsonBuilder.ts",
            "pros": ["Matches pure Clean JSON output builder role", "Continues LIB-1 common formatter/display sequence", "Keeps RunOCR panel thin and delegates output building to common utilities"],
            "cons": ["Temporarily common/utils imports @/lib/invoiceTableDisplay until invoiceTableDisplay moves", "Clean JSON fixture runner path must be adjusted in the actual move/static-check step"],
            "importUpdateScope": ["src/components/runocr/ui/OcrResultPanel.tsx", "tmp/check_clean_json_v1_fixtures_js.mjs or move-specific checker"],
            "risk": "LOW_MEDIUM",
            "recommended": True,
        },
        {
            "target": "src/components/runocr/utils/cleanJsonBuilder.ts",
            "pros": ["Close to only production consumer"],
            "cons": ["Less reusable for output/fixture contract utilities", "Does not match LIB-1 common utils direction", "Still relies on shared invoice table policy"],
            "importUpdateScope": ["src/components/runocr/ui/OcrResultPanel.tsx", "tmp/check_clean_json_v1_fixtures_js.mjs or move-specific checker"],
            "risk": "MEDIUM",
            "recommended": False,
        },
        {
            "target": "src/lib/cleanJsonBuilder.ts",
            "pros": ["No immediate code change"],
            "cons": ["Leaves src/lib cleanup stalled", "Does not continue LIB-1 common utils sequence"],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": False,
        },
        {
            "target": "DEFER",
            "pros": ["Can wait until invoiceTableDisplay moves first"],
            "cons": ["Unnecessary if the temporary src/lib invoiceTableDisplay dependency is accepted and documented"],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": False,
        },
    ]


def static_check_plan() -> list[str]:
    return [
        "tmp/check_lib_clean_json_builder_common_move_1d.mjs",
        "src/common/utils/cleanJsonBuilder.ts exists",
        "src/lib/cleanJsonBuilder.ts absent",
        "src/common/utils/cleanJsonBuilder.ts does not import src/components/*",
        "React/localStorage/window/document/fetch/indexedDB dependency remains absent",
        "src/components/runocr/ui/OcrResultPanel.tsx imports @/common/utils/cleanJsonBuilder",
        "@/lib/cleanJsonBuilder string absent from src",
        "Clean JSON fixture runner points at src/common/utils/cleanJsonBuilder.ts or move-specific checker compiles the new path",
        "TestWorkspace unchanged",
        "clean JSON fixture lock PASS",
        "RunOCR boundary checks PASS",
        "Template checks PASS",
        "table_view_model/Markdown PASS",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]


def render_md(data: dict[str, object]) -> str:
    f = data["file"]
    imported_rows = "\n".join(
        f"| `{row['file']}` | `{row['importPath']}` | {row['importKind']} | `{row['importedSymbols']}` | {row['feature']} | {row['needsImportUpdateOnMove']} | {row['testWorkspaceImpact']} |"
        for row in f["importedBy"]
    )
    target_rows = "\n".join(
        f"| `{item['target']}` | {item['recommended']} | {'; '.join(item['pros'])} | {'; '.join(item['cons'])} | {'; '.join(item['importUpdateScope']) or 'none'} | {item['risk']} |"
        for item in f["targetCandidates"]
    )
    dirty = "\n".join(data["dirtyStatus"])
    checks = "\n".join(f"- {item}" for item in data["staticCheckPlan"])
    imports = "\n".join(f"- `{item}`" for item in f["imports"]) or "- 없음"
    exports = "\n".join(f"- `{item}`" for item in f["exports"])
    next_steps = "\n".join(f"- {item}" for item in data["nextSteps"])
    dep = data["dependencyImpact"]
    fixture = data["cleanJsonFixtureImpact"]
    return f"""# FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정 여부: false
- 파일 이동/import 수정/rename/fixture/templates/backend 수정: false
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_lib_clean_json_builder_common_move_precheck.py`
- `docs/FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
{chr(10).join(f"- `{item}`" for item in data['analysisScope'])}

참고 리포트:
{chr(10).join(f"- `{item}`" for item in data['referenceReports'])}

## 5. cleanJsonBuilder 역할 요약
- currentPath: `{f['currentPath']}`
- lineCount: {f['lineCount']}
- mainResponsibility: {f['role']['mainResponsibility']}
- Clean JSON builder: {f['role']['cleanJsonBuilder']}
- sideEffects: {f['role']['sideEffects']}
- browser/localStorage/IndexedDB: {f['role']['browserLocalStorageIndexedDB']}
- React 의존: {f['role']['reactDependency']}
- components/* 의존: {bool(f['role']['componentsDependency'])}
- common/utils 적합성: {f['role']['commonUtilsFit']}
- moveRisk: {f['risk']['level']}

imports:
{imports}

exports:
{exports}

exported names:
{', '.join(f['exportedNames'])}

## 6. importedBy 분석
| file | importPath | kind | imported symbols | feature | import 수정 필요 | TestWorkspace 영향 |
|---|---|---|---|---|---:|---:|
{imported_rows}

## 7. common/utils 적합성
- 판정: `{f['commonUtilReadiness']['verdict']}`
- 이유: {f['commonUtilReadiness']['reason']}
- common -> components 의존 발생 여부: false
- TestWorkspace 직접 import 영향: false

## 8. dependency 영향
- invoiceTableDisplay import 중: {dep['importsInvoiceTableDisplay']}
- structuredTableViewModel import 중: {dep['importsStructuredTableViewModel']}
- ocrResultFormatters import 중: {dep['importsOcrResultFormatters']}
- invoiceFieldLabels import 중: {dep['importsInvoiceFieldLabels']}
- markdownReportBuilder import 중: {dep['importsMarkdownReportBuilder']}
- 이동 후 src/lib 임시 의존 발생 여부: {dep['temporarySrcLibDependencyAfterMove']}
- 순환 의존 위험: {dep['circularDependencyRisk']}
- 판단: {dep['reason']}

## 9. Clean JSON fixture 영향
- runner: `{fixture['runnerPath']}`
- runner source path 직접 참조: {fixture['runnerDirectlyReferencesSourcePath']}
- fixture rebake 필요: {fixture['fixtureRebakeNeeded']}
- 영향: {fixture['impact']}
- 권장 검증: `{fixture['recommendedCheck']}`

## 10. target path 비교
| target | 추천 | 장점 | 단점 | import 수정 범위 | risk |
|---|---:|---|---|---|---|
{target_rows}

## 11. 실제 이동 추천
- 추천 선택지: A. `cleanJsonBuilder.ts`만 `src/common/utils/cleanJsonBuilder.ts`로 이동
- 이유: 순수 Clean JSON v1 output builder이고 production import 수정 범위는 `OcrResultPanel.tsx` 1곳이다.
- D(structuredTableViewModel과 묶음)는 비추천: diff와 table fixture 검증 표면이 커지므로 한 파일만 이동한다.
- 주의: `invoiceTableDisplay`가 아직 src/lib에 있어 이동 직후 common/utils -> src/lib 임시 의존이 남는다. 이는 후속 `invoiceTableDisplay` 이동에서 해소한다.

## 12. static check 설계
{checks}

## 13. dirty 상태
```text
{dirty}
```

- `../ocr-server/data/templates.json` dirty 상태가 있으면 실제 이동 전 영향 후보로 유지한다.
- TPL-95328E52 dirty 영향 precheck 후보를 유지한다.

## 14. typecheck/build 결과
- typecheck: `{data['typecheck'].get('status')}` exitCode={data['typecheck'].get('exitCode')}
- build: `{data['build'].get('status')}` exitCode={data['build'].get('exitCode')}
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 known issue로 기록한다.

## 15. 다음 작업 제안
{next_steps}
"""


def main() -> None:
    text = read(TARGET)
    imports = extract_imports(text)
    exports = extract_exports(text)
    names = exported_names(text)
    files = source_files()
    imported_by = find_imported_by(files)
    test_impact = any(row["testWorkspaceImpact"] for row in imported_by)
    file_data = {
        "currentPath": rel(TARGET),
        "lineCount": len(text.splitlines()),
        "imports": imports,
        "exports": exports,
        "exportedNames": names,
        "importedBy": imported_by,
        "symbolHits": symbol_hits(files, names),
        "stringConsumers": direct_string_consumers(files),
        "role": role(text, imports),
        "commonUtilReadiness": {
            "verdict": "COMMON_UTIL_READY_WITH_IMPORT_ONLY",
            "reason": "The file is a pure Clean JSON v1 builder with no React, DOM, storage, backend, or components/* dependency. Moving requires an OcrResultPanel import update and fixture runner path awareness.",
        },
        "targetCandidates": target_candidates(),
        "recommendation": {
            "choice": "A",
            "targetPath": "src/common/utils/cleanJsonBuilder.ts",
            "scope": "Move only this file and update direct import path in OcrResultPanel; no logic or fixture changes.",
            "requiredImportUpdates": ["src/components/runocr/ui/OcrResultPanel.tsx"],
            "validationSupportUpdates": ["tmp/check_clean_json_v1_fixtures_js.mjs or move-specific checker path should compile/check the new target"],
            "defer": [
                "Do not move structuredTableViewModel in the same step.",
                "Do not modify TestWorkspace.",
                "Do not modify Clean JSON fixtures.",
                "Defer invoiceTableDisplay move to a dedicated step.",
            ],
        },
        "risk": {
            "level": "LOW_MEDIUM",
            "reasons": [
                "Direct production import surface is one file.",
                "No components/* import inside cleanJsonBuilder.",
                "No React/browser storage/DOM/backend side effects.",
                "No direct TestWorkspace import.",
                "Clean JSON fixture runner directly references the current src/lib path.",
                "Temporary dependency on src/lib/invoiceTableDisplay remains until a later move.",
            ],
        },
        "testWorkspaceImpact": {
            "hasImpact": test_impact,
            "status": "NO_DIRECT_TEST_IMPORT_FOUND" if not test_impact else "DEFER_DUE_TO_TEST_IMPACT",
        },
    }
    data = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "projectRoot": "OCR/mysuit-ocr",
        "codeModified": False,
        "dirtyStatus": git_status(),
        "analysisScope": ANALYSIS_SCOPE,
        "referenceReports": REFERENCE_REPORTS,
        "file": file_data,
        "dependencyImpact": dependency_impact(),
        "cleanJsonFixtureImpact": clean_json_fixture_impact(files),
        "staticCheckPlan": static_check_plan(),
        "validationPlan": [
            "Run tmp/check_lib_clean_json_builder_common_move_1d.mjs after the actual move.",
            "Run Clean JSON fixture lock/check without rebaking fixtures.",
            "Run npm run typecheck and npm run build.",
            "Run RunOCR boundary checks and Markdown/table_view_model checks as applicable.",
            "Verify TestWorkspace remains unmodified.",
        ],
        "typecheck": command_result("typecheck"),
        "build": command_result("build"),
        "nextSteps": [
            "Proceed with option A as a move-only micro-step if temporary src/lib/invoiceTableDisplay dependency is acceptable.",
            "Create a move-specific static checker before or during the actual move step.",
            "Run Clean JSON fixture runner after move without modifying fixtures.",
            "Plan invoiceTableDisplay -> common/utils as a later dedicated precheck/move.",
        ],
    }
    REPORT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_md(data), encoding="utf-8")
    with REPORT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["file", "importPath", "importKind", "importedSymbols", "feature", "needsImportUpdateOnMove", "testWorkspaceImpact"],
        )
        writer.writeheader()
        writer.writerows(imported_by)


if __name__ == "__main__":
    main()
