from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "lib" / "markdownReportBuilder.ts"
FORMATTERS = ROOT / "src" / "common" / "utils" / "ocrResultFormatters.ts"
LABELS = ROOT / "src" / "common" / "utils" / "invoiceFieldLabels.ts"
REPORT_MD = ROOT / "docs" / "FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_20260522.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_20260522.json"
REPORT_CSV = ROOT / "docs" / "FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_MAP_20260522.csv"

ANALYSIS_SCOPE = [
    "src/lib/markdownReportBuilder.ts",
    "src/common/utils/ocrResultFormatters.ts",
    "src/common/utils/invoiceFieldLabels.ts",
    "src/components/runocr",
    "src/components/template",
    "src/common",
    "src/components/test/TestWorkspace.tsx",
    "src/app",
]

REFERENCE_REPORTS = [
    "docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md",
    "docs/FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522.md",
    "docs/FRONTEND_LIB_1B_INVOICE_FIELD_LABELS_COMMON_MOVE_20260522.md",
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
    path = ROOT / "tmp" / f"codex_lib_markdown_report_builder_common_move_precheck_{name}.json"
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
    return "unknown"


def imported_symbols(body: str | None) -> str:
    return "*dynamic*" if not body else " ".join(body.split())


def find_imported_by(files: list[Path]) -> list[dict[str, object]]:
    module_paths = {
        "@/lib/markdownReportBuilder",
        "../../lib/markdownReportBuilder",
        "../lib/markdownReportBuilder",
        "./markdownReportBuilder",
        "src/lib/markdownReportBuilder",
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
        "mainResponsibility": "Pure Markdown v1 OCR report builder for RunOCR preview/copy/export paths.",
        "markdownReportBuilder": "buildMarkdownReport" in text,
        "sideEffects": has_any(text, ["localStorage.setItem", "sessionStorage.setItem", "indexedDB", "fetch(", "document.", "window."]),
        "browserLocalStorageIndexedDB": has_any(text, ["localStorage", "sessionStorage", "indexedDB", "IDB"]),
        "reactDependency": bool(re.search(r"from ['\"]react['\"]|React\.", text)),
        "componentsDependency": component_deps,
        "featurePolicyTags": ["markdown-v1", "runocr-preview", "copy-export", "fixture-contract"],
        "commonUtilsFit": "Good fit: deterministic output builder with no React, DOM, storage, backend, or components/* dependency; it already imports common/utils/ocrResultFormatters.",
    }


def dependency_impact() -> dict[str, object]:
    text = read(TARGET)
    fmt_text = read(FORMATTERS) if FORMATTERS.exists() else ""
    labels_text = read(LABELS) if LABELS.exists() else ""
    return {
        "importsCommonOcrResultFormatters": "@/common/utils/ocrResultFormatters" in text,
        "importsCommonInvoiceFieldLabelsDirectly": "@/common/utils/invoiceFieldLabels" in text,
        "recommendedFormatterImportAfterMove": "@/common/utils/ocrResultFormatters or ./ocrResultFormatters",
        "temporarySrcLibDependencyAfterMove": False,
        "commonUtilsFormatterExists": FORMATTERS.exists(),
        "commonUtilsLabelsExists": LABELS.exists(),
        "formatterImportsMarkdownBuilder": "markdownReportBuilder" in fmt_text,
        "labelsImportsMarkdownBuilder": "markdownReportBuilder" in labels_text,
        "circularDependencyRisk": "LOW",
        "markdownFixtureRunnerImpact": {
            "hasDirectRuntimeImport": False,
            "impact": "Fixture runner is a contract/regression check target, not a direct runtime importer. Move should be import-path only in OcrResultPanel; markdown fixture lock should remain PASS.",
            "recommendedCheck": "python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_20260522",
        },
    }


def target_candidates() -> list[dict[str, object]]:
    return [
        {
            "target": "src/common/utils/markdownReportBuilder.ts",
            "pros": ["Matches pure Markdown output builder role", "Keeps dependency on common/utils/ocrResultFormatters natural", "Avoids RunOCR feature dependency from common helpers"],
            "cons": ["Requires import-only update in OcrResultPanel", "Markdown fixture checks should be rerun because output contract is sensitive"],
            "importUpdateScope": ["src/components/runocr/ui/OcrResultPanel.tsx"],
            "risk": "LOW",
            "recommended": True,
        },
        {
            "target": "src/components/runocr/utils/markdownReportBuilder.ts",
            "pros": ["Close to only production consumer"],
            "cons": ["Less reusable for report/fixture utilities", "Breaks LIB-1 common formatter/display direction", "Would leave a common output builder outside common"],
            "importUpdateScope": ["src/components/runocr/ui/OcrResultPanel.tsx"],
            "risk": "MEDIUM",
            "recommended": False,
        },
        {
            "target": "src/lib/markdownReportBuilder.ts",
            "pros": ["No immediate code change"],
            "cons": ["Leaves src/lib cleanup stalled", "Does not continue LIB-1 common utils sequence"],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": False,
        },
        {
            "target": "DEFER",
            "pros": ["Avoids current dirty-state interaction"],
            "cons": ["Unnecessary given pure file and single production consumer"],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": False,
        },
    ]


def static_check_plan() -> list[str]:
    return [
        "tmp/check_lib_markdown_report_builder_common_move_1c.mjs",
        "src/common/utils/markdownReportBuilder.ts exists",
        "src/lib/markdownReportBuilder.ts absent",
        "src/common/utils/markdownReportBuilder.ts does not import src/components/*",
        "React/localStorage/window/document/fetch/indexedDB dependency remains absent",
        "src/common/utils/markdownReportBuilder.ts imports common/utils/ocrResultFormatters",
        "src/components/runocr/ui/OcrResultPanel.tsx imports @/common/utils/markdownReportBuilder",
        "@/lib/markdownReportBuilder string absent from src",
        "TestWorkspace unchanged",
        "markdown fixture lock PASS",
        "RunOCR boundary checks PASS",
        "Template checks PASS",
        "table_view_model/Clean JSON PASS",
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
    return f"""# FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정 여부: false
- 파일 이동/import 수정/rename/fixture/templates/backend 수정: false
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_lib_markdown_report_builder_common_move_precheck.py`
- `docs/FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
{chr(10).join(f"- `{item}`" for item in data['analysisScope'])}

참고 리포트:
{chr(10).join(f"- `{item}`" for item in data['referenceReports'])}

## 5. markdownReportBuilder 역할 요약
- currentPath: `{f['currentPath']}`
- lineCount: {f['lineCount']}
- mainResponsibility: {f['role']['mainResponsibility']}
- markdown report builder: {f['role']['markdownReportBuilder']}
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
- common/utils/ocrResultFormatters import 중: {dep['importsCommonOcrResultFormatters']}
- common/utils/invoiceFieldLabels 직접 import 중: {dep['importsCommonInvoiceFieldLabelsDirectly']}
- 이동 후 권장 formatter import: `{dep['recommendedFormatterImportAfterMove']}`
- src/lib 임시 의존 발생 여부: {dep['temporarySrcLibDependencyAfterMove']}
- 순환 의존 위험: {dep['circularDependencyRisk']}
- markdown fixture runner 직접 runtime import: {dep['markdownFixtureRunnerImpact']['hasDirectRuntimeImport']}
- fixture 영향: {dep['markdownFixtureRunnerImpact']['impact']}

## 9. target path 비교
| target | 추천 | 장점 | 단점 | import 수정 범위 | risk |
|---|---:|---|---|---|---|
{target_rows}

## 10. 실제 이동 추천
- 추천 선택지: A. `markdownReportBuilder.ts`만 `src/common/utils/markdownReportBuilder.ts`로 이동
- 이유: 순수 Markdown v1 output builder이고 이미 common formatter에만 의존한다. production import 수정 범위는 `OcrResultPanel.tsx` 1곳이다.
- D(cleanJsonBuilder와 묶음)는 비추천: 첫 Markdown builder 이동에서 fixture 계약 검증 범위가 커지므로 한 파일만 이동한다.

## 11. static check 설계
{checks}

## 12. dirty 상태
```text
{dirty}
```

- `../ocr-server/data/templates.json` dirty 상태가 있으면 실제 이동 전 영향 후보로 유지한다.
- TPL-95328E52 dirty 영향 precheck 후보를 유지한다.

## 13. typecheck/build 결과
- typecheck: `{data['typecheck'].get('status')}` exitCode={data['typecheck'].get('exitCode')}
- build: `{data['build'].get('status')}` exitCode={data['build'].get('exitCode')}
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 known issue로 기록한다.

## 14. 다음 작업 제안
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
        "role": role(text, imports),
        "commonUtilReadiness": {
            "verdict": "COMMON_UTIL_READY_WITH_IMPORT_ONLY",
            "reason": "The file is a pure Markdown v1 builder with no React, DOM, storage, backend, or components/* dependency. It already depends on common/utils/ocrResultFormatters, so moving requires only an OcrResultPanel import update.",
        },
        "targetCandidates": target_candidates(),
        "recommendation": {
            "choice": "A",
            "targetPath": "src/common/utils/markdownReportBuilder.ts",
            "scope": "Move only this file and update direct import path in OcrResultPanel; no logic changes.",
            "requiredImportUpdates": ["src/components/runocr/ui/OcrResultPanel.tsx"],
            "defer": [
                "Do not move cleanJsonBuilder in the same step.",
                "Do not modify TestWorkspace.",
                "Do not modify markdown fixtures.",
            ],
        },
        "risk": {
            "level": "LOW",
            "reasons": [
                "Direct production import surface is one file.",
                "No components/* import inside markdownReportBuilder.",
                "No React/browser storage/DOM/backend side effects.",
                "No direct TestWorkspace import.",
                "Markdown fixture runner can validate output contract after import-only move.",
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
        "staticCheckPlan": static_check_plan(),
        "validationPlan": [
            "Run tmp/check_lib_markdown_report_builder_common_move_1c.mjs after the actual move.",
            "Run markdown fixture lock because Markdown v1 output is contract-sensitive.",
            "Run npm run typecheck and npm run build.",
            "Run RunOCR boundary checks and Clean JSON/table_view_model checks as applicable.",
            "Verify TestWorkspace remains unmodified.",
        ],
        "typecheck": command_result("typecheck"),
        "build": command_result("build"),
        "nextSteps": [
            "Proceed with option A as a move-only micro-step.",
            "Create a move-specific static checker before or during the actual move step.",
            "Run markdown fixture lock after move without modifying fixtures.",
            "Continue LIB-1 with cleanJsonBuilder only after checks pass.",
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
