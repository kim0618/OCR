from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASK = "CODEX_FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY"
REPORT_BASE = "FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_20260522"
DOCS = ROOT / "docs"
TMP = ROOT / "tmp"
TARGET = ROOT / "src/lib/invoiceTableDisplay.ts"
COMMON_TARGET = ROOT / "src/common/utils/invoiceTableDisplay.ts"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def line_count(text: str) -> int:
    return 0 if text == "" else len(text.splitlines())


def find_imports(text: str) -> list[str]:
    imports: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("import "):
            block = [line.rstrip()]
            while ";" not in lines[i] and i + 1 < len(lines):
                i += 1
                block.append(lines[i].rstrip())
            imports.append(" ".join(s.strip() for s in block))
        i += 1
    return imports


def find_exports(text: str) -> tuple[list[str], list[str]]:
    exports = []
    names = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("export "):
            exports.append(stripped)
            match = re.match(
                r"export\s+(?:type|interface|const|function|class)\s+([A-Za-z0-9_]+)",
                stripped,
            )
            if match:
                names.append(match.group(1))
    return exports, names


def feature_for(path: str) -> str:
    normalized = path.replace("\\", "/")
    if "/components/runocr/" in normalized:
        return "runocr"
    if "/components/history/" in normalized:
        return "history"
    if "/components/test/" in normalized:
        return "test"
    if "/components/template/" in normalized:
        return "template"
    if "/components/restore/" in normalized or "/components/autorestore/" in normalized:
        return "restore"
    if "/components/login/" in normalized:
        return "login"
    if "/components/layout/" in normalized:
        return "layout"
    if "/common/" in normalized:
        return "common"
    if "/app/" in normalized:
        return "app"
    if "/src/lib/" in normalized:
        return "lib"
    if normalized.startswith("tmp/"):
        return "tmp"
    return "unknown"


def extract_imported_symbols(text: str, import_path: str) -> str:
    pattern = re.compile(r"import\s+(.+?)\s+from\s+[\"']" + re.escape(import_path) + r"[\"']", re.S)
    match = pattern.search(text)
    if not match:
        return ""
    return " ".join(match.group(1).split())


def scan_imported_by() -> list[dict]:
    roots = [ROOT / "src", ROOT / "tmp"]
    rows: list[dict] = []
    paths = []
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py"}:
                paths.append(path)
    seen = set()
    import_paths = [
        "@/lib/invoiceTableDisplay",
        "@/common/utils/invoiceTableDisplay",
        "../lib/invoiceTableDisplay",
        "../../lib/invoiceTableDisplay",
        "./invoiceTableDisplay",
    ]
    for path in sorted(paths):
        text = read(path)
        rel_path = rel(path)
        if rel_path == "src/lib/invoiceTableDisplay.ts":
            continue
        for import_path in import_paths:
            if import_path in text:
                key = (rel_path, import_path)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "file": rel_path,
                        "importPath": import_path,
                        "importedSymbols": extract_imported_symbols(text, import_path),
                        "feature": feature_for("/" + rel_path),
                        "importKind": "static" if "import " in text else "path/string",
                        "needsImportUpdateOnMove": import_path != "@/common/utils/invoiceTableDisplay",
                        "testWorkspaceImpact": rel_path.startswith("src/components/test/"),
                    }
                )
    return rows


def scan_symbol_hits(names: list[str]) -> list[dict]:
    rows: list[dict] = []
    for name in names:
        if not name:
            continue
        code, out = run(["rg", "-n", name, "src", "tmp"])
        if code not in (0, 1):
            continue
        files = sorted({line.split(":", 1)[0].replace("\\", "/") for line in out.splitlines() if ":" in line})
        rows.append({"symbol": name, "files": files[:80], "count": len(files)})
    return rows


def load_result(name: str) -> dict:
    path = TMP / name
    if not path.exists():
        return {
            "command": "unknown",
            "status": "NOT_RUN",
            "exitCode": None,
            "outLog": f"ocr-server/logs/codex_{TASK}.out.log",
            "errLog": f"ocr-server/logs/codex_{TASK}.err.log",
        }
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def target_options() -> list[dict]:
    return [
        {
            "option": "src/common/utils/invoiceTableDisplay.ts",
            "pros": [
                "Shared display policy can be consumed by RunOCR, History, Clean JSON, and TestWorkspace from one common location.",
                "Resolves the current common/utils/cleanJsonBuilder.ts runtime dependency on @/lib/invoiceTableDisplay.",
            ],
            "cons": [
                "Requires import path updates in TestWorkspace, which is currently under no-modify policy unless approved for the actual move.",
                "Fixture runner path mappings must be updated for move validation.",
            ],
            "importUpdateScope": [
                "src/components/runocr/ui/OcrResultPanel.tsx",
                "src/components/history/DetailHistoryView.tsx",
                "src/components/test/TestWorkspace.tsx",
                "src/common/utils/cleanJsonBuilder.ts",
                "tmp/check_clean_json_v1_fixtures_js.mjs",
            ],
            "risk": "MEDIUM_HIGH",
            "recommended": False,
            "recommendationNote": "Correct target, but actual move should wait for explicit TestWorkspace import-path approval or be scoped to an approved TestWorkspace path-only update.",
        },
        {
            "option": "src/components/runocr/utils/invoiceTableDisplay.ts",
            "pros": ["Keeps RunOCR preview policy near its main UI consumer."],
            "cons": ["Wrong ownership because History, Clean JSON, and TestWorkspace also consume it."],
            "importUpdateScope": ["RunOCR plus cross-feature imports would still need updates."],
            "risk": "HIGH",
            "recommended": False,
        },
        {
            "option": "src/components/test/utils/invoiceTableDisplay.ts",
            "pros": ["Would isolate the TestWorkspace direct import."],
            "cons": ["Wrong ownership for RunOCR/History/Clean JSON shared display policy."],
            "importUpdateScope": ["Broad and semantically backwards."],
            "risk": "HIGH",
            "recommended": False,
        },
        {
            "option": "src/lib 유지",
            "pros": ["No TestWorkspace modification needed now."],
            "cons": ["Leaves common/utils/cleanJsonBuilder.ts importing @/lib/invoiceTableDisplay."],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": True,
            "recommendationNote": "Recommended until TestWorkspace path-only update is approved.",
        },
        {
            "option": "보류",
            "pros": ["Avoids violating the current TestWorkspace no-modify policy."],
            "cons": ["Defers cleanup of the temporary runtime dependency."],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": True,
        },
    ]


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    TMP.mkdir(exist_ok=True)
    text = read(TARGET)
    clean_text = read(ROOT / "src/common/utils/cleanJsonBuilder.ts")
    exports, exported_names = find_exports(text)
    imports = find_imports(text)
    imported_by = scan_imported_by()
    symbol_hits = scan_symbol_hits(exported_names)
    code, dirty_out = run(["git", "status", "--short"])
    dirty = dirty_out.splitlines()

    test_direct = [row for row in imported_by if row["file"] == "src/components/test/TestWorkspace.tsx"]
    test_core_hits = [
        hit for hit in symbol_hits
        for file in hit["files"]
        if file.startswith("src/components/test/core/")
    ]
    tmp_runner_direct = any(row["file"] == "tmp/check_clean_json_v1_fixtures_js.mjs" for row in imported_by)

    typecheck = load_result("codex_lib_invoice_table_display_common_move_precheck_typecheck.json")
    build = load_result("codex_lib_invoice_table_display_common_move_precheck_build.json")

    file_info = {
        "currentPath": "src/lib/invoiceTableDisplay.ts",
        "targetPath": "src/common/utils/invoiceTableDisplay.ts",
        "lineCount": line_count(text),
        "imports": imports,
        "exports": exports,
        "exportedNames": exported_names,
        "importedBy": imported_by,
        "symbolHits": symbol_hits,
        "role": {
            "mainResponsibility": "Invoice table row/column display policy, label map, cell normalization, meaningful-value filtering, rowIndex visibility, and preview column selection.",
            "invoiceTableDisplayPolicy": True,
            "tableColumnFieldDisplayPolicy": True,
            "sideEffects": False,
            "browserLocalStorageIndexedDB": False,
            "backendApiCalls": False,
            "reactDependency": False,
            "componentsDependency": False,
            "featurePolicyIncluded": True,
            "commonUtilsFit": "Shared display policy used by RunOCR, History, Clean JSON, and TestWorkspace. Good common/utils fit, but TestWorkspace direct import requires explicit handling.",
        },
        "commonUtilReadiness": {
            "verdict": "DEFER_DUE_TO_TEST_IMPACT",
            "alternateVerdictIfTestWorkspacePathUpdateApproved": "COMMON_UTIL_READY_WITH_IMPORT_ONLY",
            "reason": "The helper is pure and shared, but src/components/test/TestWorkspace.tsx directly imports it. Current policy forbids TestWorkspace modification without user confirmation.",
        },
        "targetCandidates": target_options(),
        "recommendation": {
            "choice": "C",
            "summary": "Defer the actual move until a path-only TestWorkspace import update is explicitly allowed, then move only invoiceTableDisplay.ts to src/common/utils/invoiceTableDisplay.ts.",
            "actualMoveIfApproved": "A",
            "doNotBundle": ["structuredTableViewModel.ts", "bizNumber.ts"],
            "requiredImportUpdatesIfApproved": [
                "src/components/runocr/ui/OcrResultPanel.tsx",
                "src/components/history/DetailHistoryView.tsx",
                "src/components/test/TestWorkspace.tsx",
                "src/common/utils/cleanJsonBuilder.ts",
                "tmp/check_clean_json_v1_fixtures_js.mjs or dedicated move checker",
            ],
        },
        "risk": {
            "level": "MEDIUM_HIGH",
            "reasons": [
                "Direct TestWorkspace import is present.",
                "RunOCR preview and History detail both use buildInvoicePreviewCols/normalizeTableCell.",
                "Clean JSON fixture runner directly transpiles src/lib/invoiceTableDisplay.ts.",
            ],
        },
        "testWorkspaceImpact": {
            "status": "DEFER_DUE_TO_TEST_WORKSPACE_POLICY" if test_direct else "NO_TEST_IMPACT",
            "directImport": bool(test_direct),
            "directImportRows": test_direct,
            "testCoreDirectImport": bool(test_core_hits),
            "testCoreHits": test_core_hits,
            "canMoveWithoutTestWorkspaceEdit": False if test_direct else True,
            "note": "Actual move needs a TestWorkspace import-path update from @/lib/invoiceTableDisplay to @/common/utils/invoiceTableDisplay unless a compatibility shim is intentionally kept, which is not recommended for this cleanup.",
        },
    }

    dependency_impact = {
        "cleanJsonBuilderImportsLibInvoiceTableDisplay": "@/lib/invoiceTableDisplay" in clean_text,
        "canResolveCleanJsonTempDependency": True,
        "targetCleanJsonImportAfterMove": "@/common/utils/invoiceTableDisplay",
        "commonUtilsSiblingImportNatural": True,
        "circularDependencyRisk": "LOW",
        "structuredTableViewModelDependency": {
            "directImportOfInvoiceTableDisplay": "invoiceTableDisplay" in read(ROOT / "src/lib/structuredTableViewModel.ts"),
            "recommendation": "Do not bundle structuredTableViewModel with this move.",
        },
        "bizNumberDependency": {
            "directImportOfInvoiceTableDisplay": "invoiceTableDisplay" in read(ROOT / "src/lib/bizNumber.ts"),
            "recommendation": "No bizNumber dependency coupling found; do not bundle bizNumber with this move.",
        },
        "srcLibResidualDependencyAfterMove": "Only if imports are not updated. With approved import-only updates, @/lib/invoiceTableDisplay can be eliminated.",
    }

    clean_json_fixture = {
        "runnerPath": "tmp/check_clean_json_v1_fixtures_js.mjs",
        "runnerExists": (ROOT / "tmp/check_clean_json_v1_fixtures_js.mjs").exists(),
        "runnerDirectlyReferencesSourcePath": "src\", \"lib\", \"invoiceTableDisplay.ts" in read(ROOT / "tmp/check_clean_json_v1_fixtures_js.mjs")
        or "src/lib/invoiceTableDisplay.ts" in read(ROOT / "tmp/check_clean_json_v1_fixtures_js.mjs"),
        "runnerUsesAliasMapping": "@/lib/invoiceTableDisplay" in read(ROOT / "tmp/check_clean_json_v1_fixtures_js.mjs"),
        "impact": "Runner path/mapping must be updated or the move-specific static checker must compile from src/common/utils/invoiceTableDisplay.ts. Fixture data should not be modified.",
        "fixtureRebakeNeeded": False,
    }

    table_view_model_fixture = {
        "pythonFixtureScriptsMirrorPolicy": True,
        "directRuntimeImportFound": False,
        "impact": "Existing table view model fixture scripts mirror invoiceTableDisplay policy in Python rather than importing the TS file. Moving the TS file should be import-path/static-check impact only.",
        "fixtureRebakeNeeded": False,
        "recommendedChecks": [
            "table_view_model fixture lock PASS",
            "Clean JSON fixture lock PASS",
        ],
    }

    static_checks = [
        "src/common/utils/invoiceTableDisplay.ts exists",
        "src/lib/invoiceTableDisplay.ts absent",
        "src/common/utils/invoiceTableDisplay.ts imports no components/* path",
        "React/localStorage/window/document dependency remains absent",
        "@/lib/invoiceTableDisplay string absent from src",
        "src/common/utils/cleanJsonBuilder.ts imports @/common/utils/invoiceTableDisplay",
        "TestWorkspace import path is either explicitly approved and updated, or move is deferred",
        "tmp/check_clean_json_v1_fixtures_js.mjs path/mapping updated or dedicated move checker passes",
        "clean JSON fixture lock PASS",
        "table_view_model fixture lock PASS",
        "RunOCR boundary checks PASS",
        "Template checks PASS",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]

    validation = [
        "No production code changed during this precheck.",
        "Do not edit fixture outputs or templates.json.",
        "If actual move is approved, keep it as one-file move plus import-path updates only.",
    ]

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "projectRoot": "mysuit-ocr",
        "task": TASK,
        "codeModified": False,
        "dirtyStatus": {"exitCode": code, "entries": dirty},
        "file": file_info,
        "dependencyImpact": dependency_impact,
        "cleanJsonFixtureImpact": clean_json_fixture,
        "tableViewModelFixtureImpact": table_view_model_fixture,
        "staticCheckPlan": {"script": "tmp/check_lib_invoice_table_display_common_move_1e.mjs", "items": static_checks},
        "validationPlan": validation,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "Ask for explicit approval to include a TestWorkspace import-path-only update in the actual move.",
            "If approved, move invoiceTableDisplay.ts to common/utils and update import paths only.",
            "Run clean JSON and table view model fixture locks plus typecheck/build.",
        ],
    }

    json_path = DOCS / f"{REPORT_BASE}.json"
    md_path = DOCS / f"{REPORT_BASE}.md"
    csv_path = DOCS / "FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_MAP_20260522.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = f"""# FRONTEND LIB invoiceTableDisplay common move precheck

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `{TASK}`

## 2. 코드 수정 여부
- codeModified: false
- 운영 코드 수정 없음
- 파일 이동/import 수정/rename/fixture/templates/backend 수정 없음

## 3. 생성 파일
- `tmp/codex_frontend_lib_invoice_table_display_common_move_precheck.py`
- `docs/{REPORT_BASE}.md`
- `docs/{REPORT_BASE}.json`
- `docs/FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_MAP_20260522.csv`
- `ocr-server/logs/codex_{TASK}.out.log`
- `ocr-server/logs/codex_{TASK}.err.log`

## 4. 분석 범위
- `src/lib/invoiceTableDisplay.ts`
- `src/common/utils/cleanJsonBuilder.ts`
- `src/common/utils/ocrResultFormatters.ts`
- `src/common/utils/invoiceFieldLabels.ts`
- `src/components/runocr/**`
- `src/components/history/**`
- `src/components/test/TestWorkspace.tsx` 읽기 전용
- `src/components/test/core/**` 읽기 전용
- `src/common/**`
- `src/app/**`

## 5. invoiceTableDisplay 역할 요약
- currentPath: `src/lib/invoiceTableDisplay.ts`
- lineCount: {file_info['lineCount']}
- imports: {len(imports)}
- exports: {", ".join(exported_names)}
- 역할: invoice table row/column display policy, label map, cell normalization, meaningful-value filtering, rowIndex visibility, preview column selection.
- sideEffects: false
- React/DOM/storage/backend/components dependency: false
- feature policy 포함: true

## 6. importedBy 분석
| file | importPath | symbols | feature | move import update |
|---|---|---|---|---|
"""
    for row in imported_by:
        md += f"| `{row['file']}` | `{row['importPath']}` | `{row['importedSymbols']}` | {row['feature']} | {row['needsImportUpdateOnMove']} |\n"

    md += f"""

## 7. TestWorkspace 영향 분석
- 판정: `{file_info['testWorkspaceImpact']['status']}`
- `src/components/test/TestWorkspace.tsx` 직접 import: {file_info['testWorkspaceImpact']['directImport']}
- `src/components/test/core/**` 직접 import: {file_info['testWorkspaceImpact']['testCoreDirectImport']}
- 현재 정책상 TestWorkspace 수정 금지이므로 실제 이동은 보류하거나, 별도 승인으로 import path-only 변경을 허용해야 한다.

## 8. common/utils 적합성
- 판정: `{file_info['commonUtilReadiness']['verdict']}`
- TestWorkspace path-only update 승인 시 대체 판정: `{file_info['commonUtilReadiness']['alternateVerdictIfTestWorkspacePathUpdateApproved']}`
- 순수 helper이고 여러 feature가 공유하므로 common/utils 자체는 적합하다.

## 9. dependency/Clean JSON/table_view_model 영향
- `src/common/utils/cleanJsonBuilder.ts`의 `@/lib/invoiceTableDisplay` 임시 의존 해소 가능: {dependency_impact['canResolveCleanJsonTempDependency']}
- 이동 후 권장 import: `{dependency_impact['targetCleanJsonImportAfterMove']}`
- 순환 의존 위험: {dependency_impact['circularDependencyRisk']}
- Clean JSON runner 직접 source path 참조: {clean_json_fixture['runnerDirectlyReferencesSourcePath']}
- table_view_model fixture rebake 필요: {table_view_model_fixture['fixtureRebakeNeeded']}

## 10. target path 비교
| option | risk | recommended | note |
|---|---|---|---|
"""
    for option in target_options():
        md += f"| `{option['option']}` | {option['risk']} | {option['recommended']} | {option.get('recommendationNote', '')} |\n"

    md += f"""

## 11. 실제 이동 추천
- 추천 선택지: C. 이동 보류
- 이유: `TestWorkspace.tsx`가 직접 import하고 있고, 현재 사용자 정책상 TestWorkspace 수정은 사용자 확인 전 금지다.
- 승인 시 실제 범위: A. `invoiceTableDisplay.ts`만 `src/common/utils/invoiceTableDisplay.ts`로 이동하고 import path만 수정.
- 묶지 말 것: `structuredTableViewModel.ts`, `bizNumber.ts`

## 12. static check 설계
- proposed: `tmp/check_lib_invoice_table_display_common_move_1e.mjs`
"""
    for item in static_checks:
        md += f"- {item}\n"

    md += f"""

## 13. dirty 상태
```text
{chr(10).join(dirty)}
```

## 14. typecheck/build 결과
- typecheck: {typecheck.get('status')} / exitCode {typecheck.get('exitCode')}
- build: {build.get('status')} / exitCode {build.get('exitCode')}
- known stderr noise: ESLint `nextVitals is not iterable`는 exit code 0이면 known issue로 기록

## 15. 다음 작업 제안
- TestWorkspace import-path-only update를 실제 이동 범위에 포함할지 사용자 확인.
- 승인되면 LIB-1E move step으로 한 파일 이동 + import path 업데이트만 수행.
- 이후 Clean JSON fixture lock, table_view_model fixture lock, typecheck/build를 실행.
"""
    md_path.write_text(md, encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "importPath",
                "importedSymbols",
                "feature",
                "needsImportUpdateOnMove",
                "testWorkspaceImpact",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in imported_by:
            writer.writerow(row)

    print(json.dumps({
        "status": "ok",
        "json": rel(json_path),
        "md": rel(md_path),
        "csv": rel(csv_path),
        "verdict": file_info["commonUtilReadiness"]["verdict"],
        "recommendation": file_info["recommendation"]["choice"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
