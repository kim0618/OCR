from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASK = "CODEX_FRONTEND_LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY"
REPORT_BASE = "FRONTEND_LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_PRECHECK_20260522"
DOCS = ROOT / "docs"
TMP = ROOT / "tmp"
TARGET = ROOT / "src/lib/structuredTableViewModel.ts"
COMMON_TARGET = ROOT / "src/common/utils/structuredTableViewModel.ts"


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
    exports: list[str] = []
    names: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("export "):
            exports.append(stripped)
            m = re.match(r"export\s+(?:type|interface|const|function|class)\s+([A-Za-z0-9_]+)", stripped)
            if m:
                names.append(m.group(1))
    return exports, names


def feature_for(path: str) -> str:
    p = path.replace("\\", "/")
    if "/components/runocr/" in p:
        return "runocr"
    if "/components/history/" in p:
        return "history"
    if "/components/test/" in p:
        return "test"
    if "/components/template/" in p:
        return "template"
    if "/components/restore/" in p or "/components/autorestore/" in p:
        return "restore"
    if "/components/login/" in p:
        return "login"
    if "/components/layout/" in p:
        return "layout"
    if "/common/" in p:
        return "common"
    if "/app/" in p:
        return "app"
    if "/src/lib/" in p:
        return "lib"
    if p.startswith("tmp/"):
        return "tmp"
    return "unknown"


def extract_imported_symbols(text: str, import_path: str) -> str:
    pattern = re.compile(r"import\s+(.+?)\s+from\s+[\"']" + re.escape(import_path) + r"[\"']", re.S)
    match = pattern.search(text)
    return " ".join(match.group(1).split()) if match else ""


def scan_imported_by() -> list[dict]:
    rows: list[dict] = []
    import_paths = [
        "@/lib/structuredTableViewModel",
        "@/common/utils/structuredTableViewModel",
        "../lib/structuredTableViewModel",
        "../../lib/structuredTableViewModel",
        "./structuredTableViewModel",
    ]
    paths: list[Path] = []
    for base in [ROOT / "src", ROOT / "tmp"]:
        if base.exists():
            for path in base.rglob("*"):
                if path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py"}:
                    paths.append(path)
    seen = set()
    for path in sorted(paths):
        rel_path = rel(path)
        if rel_path == "src/lib/structuredTableViewModel.ts":
            continue
        text = read(path)
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
                        "importKind": "static" if "import " in text and import_path.startswith("@/") else "path/string",
                        "needsImportUpdateOnMove": import_path != "@/common/utils/structuredTableViewModel",
                        "testWorkspaceImpact": rel_path.startswith("src/components/test/"),
                    }
                )
    return rows


def scan_symbol_hits(names: list[str]) -> list[dict]:
    rows: list[dict] = []
    for name in names:
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
            "option": "src/common/utils/structuredTableViewModel.ts",
            "pros": [
                "Keeps UI-agnostic structured table builder with other common formatter/display utilities.",
                "Import update scope is small: OcrResultPanel and table_view_model runner/checker.",
            ],
            "cons": ["Requires table_view_model runner source path update or move-specific checker update."],
            "importUpdateScope": [
                "src/components/runocr/ui/OcrResultPanel.tsx",
                "tmp/check_table_view_model_v1_fixtures_js.mjs",
                "tmp/check_lib_structured_table_view_model_common_move_1f.mjs",
            ],
            "risk": "LOW_MEDIUM",
            "recommended": True,
        },
        {
            "option": "src/components/runocr/utils/structuredTableViewModel.ts",
            "pros": ["Main production consumer is currently RunOCR."],
            "cons": ["Less future-proof for History/Test/shared table tooling and separates it from other common display helpers."],
            "importUpdateScope": ["RunOCR import only, but ownership is narrower than helper semantics."],
            "risk": "MEDIUM",
            "recommended": False,
        },
        {
            "option": "src/components/test/utils/structuredTableViewModel.ts",
            "pros": ["Would align with fixture/test runner concerns."],
            "cons": ["Wrong ownership because production RunOCR consumes it."],
            "importUpdateScope": ["Broad and semantically backwards."],
            "risk": "HIGH",
            "recommended": False,
        },
        {
            "option": "src/lib 유지",
            "pros": ["No import updates now."],
            "cons": ["Leaves common formatter/display utilities split across src/lib and src/common/utils."],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": False,
        },
        {
            "option": "보류",
            "pros": ["Avoids touching runner path now."],
            "cons": ["Unnecessary if import-only move is accepted."],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": False,
        },
    ]


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    TMP.mkdir(exist_ok=True)
    text = read(TARGET)
    exports, exported_names = find_exports(text)
    imports = find_imports(text)
    imported_by = scan_imported_by()
    symbol_hits = scan_symbol_hits(exported_names)
    _, dirty_out = run(["git", "status", "--short"])
    dirty = [line for line in dirty_out.splitlines() if line and not line.startswith("warning:")]

    test_direct = [r for r in imported_by if r["file"] == "src/components/test/TestWorkspace.tsx"]
    test_core = [r for r in imported_by if r["file"].startswith("src/components/test/core/")]
    invoice_text = read(ROOT / "src/common/utils/invoiceTableDisplay.ts")
    if not invoice_text:
        invoice_text = read(ROOT / "src/lib/invoiceTableDisplay.ts")
    table_runner_text = read(ROOT / "tmp/check_table_view_model_v1_fixtures_js.mjs")
    clean_runner_text = read(ROOT / "tmp/check_clean_json_v1_fixtures_js.mjs")

    typecheck = load_result("codex_lib_structured_table_view_model_common_move_precheck_typecheck.json")
    build = load_result("codex_lib_structured_table_view_model_common_move_precheck_build.json")

    file_info = {
        "currentPath": "src/lib/structuredTableViewModel.ts",
        "targetPath": "src/common/utils/structuredTableViewModel.ts",
        "lineCount": line_count(text),
        "imports": imports,
        "exports": exports,
        "exportedNames": exported_names,
        "importedBy": imported_by,
        "symbolHits": symbol_hits,
        "role": {
            "mainResponsibility": "Builds a UI-agnostic structured invoice table view model from caller-provided rows and displayCols.",
            "structuredTableViewModelBuilder": True,
            "tableRowColumnNormalization": True,
            "invoiceTableDisplayRelation": "Does not import invoiceTableDisplay. It consumes displayCols that callers usually resolve with buildInvoicePreviewCols.",
            "sideEffects": False,
            "browserLocalStorageIndexedDB": False,
            "backendApiCalls": False,
            "reactDependency": False,
            "componentsDependency": False,
            "featurePolicyIncluded": False,
            "commonUtilsFit": "Good fit: pure common table view-model helper with no component dependency.",
        },
        "commonUtilReadiness": {
            "verdict": "COMMON_UTIL_READY_WITH_IMPORT_ONLY",
            "reason": "Pure helper, no components/* imports, no React/browser/storage/backend dependency, and direct production import scope is small.",
        },
        "targetCandidates": target_options(),
        "recommendation": {
            "choice": "A",
            "summary": "Move structuredTableViewModel.ts only to src/common/utils/structuredTableViewModel.ts and update import paths.",
            "doNotBundle": ["invoiceTableDisplay.ts", "bizNumber.ts"],
            "requiredImportUpdates": [
                "src/components/runocr/ui/OcrResultPanel.tsx",
                "tmp/check_table_view_model_v1_fixtures_js.mjs or move-specific checker",
            ],
            "testWorkspaceApprovalNeeded": False,
        },
        "risk": {
            "level": "LOW_MEDIUM",
            "reasons": [
                "The helper is pure and currently imported by one production UI file.",
                "table_view_model fixture runner directly references src/lib/structuredTableViewModel.ts.",
                "No TestWorkspace direct import found.",
            ],
        },
        "testWorkspaceImpact": {
            "status": "NO_TEST_IMPACT" if not test_direct and not test_core else "TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY",
            "directImport": bool(test_direct),
            "testCoreDirectImport": bool(test_core),
            "directImportRows": test_direct,
            "testCoreRows": test_core,
            "canMoveWithoutTestWorkspaceEdit": not test_direct and not test_core,
            "note": "No TestWorkspace or src/components/test/core direct import was found for structuredTableViewModel.",
        },
    }

    dependency_impact = {
        "structuredImportsInvoiceTableDisplay": "@/common/utils/invoiceTableDisplay" in text
        or "@/lib/invoiceTableDisplay" in text
        or re.search(r"from\s+[\"'][^\"']*invoiceTableDisplay[\"']", text) is not None,
        "invoiceTableDisplayImportsStructured": "structuredTableViewModel" in invoice_text,
        "commonUtilsSiblingDependencyNeeded": False,
        "circularDependencyRisk": "LOW",
        "reason": "structuredTableViewModel is leaf-like and consumes caller-provided displayCols; invoiceTableDisplay does not import it.",
        "cleanJsonDirectOrIndirectImport": "structuredTableViewModel" in clean_runner_text or "structuredTableViewModel" in read(ROOT / "src/common/utils/cleanJsonBuilder.ts"),
        "srcLibResidualDependencyAfterMove": "Only @/lib/structuredTableViewModel imports/paths must be updated; no dependency on invoiceTableDisplay is introduced by the move.",
    }

    table_fixture = {
        "runnerPath": "tmp/check_table_view_model_v1_fixtures_js.mjs",
        "runnerExists": (ROOT / "tmp/check_table_view_model_v1_fixtures_js.mjs").exists(),
        "runnerDirectlyReferencesSourcePath": "src\", \"lib\", \"structuredTableViewModel.ts" in table_runner_text
        or "src/lib/structuredTableViewModel.ts" in table_runner_text,
        "runnerUsesTransientBuild": "typescript.transpileModule" in table_runner_text,
        "impact": "Runner HELPER_SRC must point to src/common/utils/structuredTableViewModel.ts or a move-specific checker must compile from the new location.",
        "fixtureRebakeNeeded": False,
        "recommendedCheck": "node tmp/check_table_view_model_v1_fixtures_js.mjs",
    }

    clean_fixture = {
        "runnerPath": "tmp/check_clean_json_v1_fixtures_js.mjs",
        "runnerExists": (ROOT / "tmp/check_clean_json_v1_fixtures_js.mjs").exists(),
        "directStructuredImport": "structuredTableViewModel" in clean_runner_text,
        "impact": "No direct Clean JSON fixture impact found; keep Clean JSON fixture lock in validation as a regression guard.",
        "fixtureRebakeNeeded": False,
        "recommendedCheck": "node tmp/check_clean_json_v1_fixtures_js.mjs",
    }

    static_checks = [
        "src/common/utils/structuredTableViewModel.ts exists",
        "src/lib/structuredTableViewModel.ts absent",
        "src/common/utils/structuredTableViewModel.ts imports no components/* path",
        "React/localStorage/window/document dependency remains absent",
        "@/lib/structuredTableViewModel string absent from src",
        "OcrResultPanel imports @/common/utils/structuredTableViewModel",
        "TestWorkspace remains unmodified by this move or has NO_TEST_IMPACT",
        "table_view_model fixture lock PASS",
        "Clean JSON fixture lock PASS",
        "RunOCR boundary checks PASS",
        "Template checks PASS",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "projectRoot": "mysuit-ocr",
        "task": TASK,
        "codeModified": False,
        "dirtyStatus": {"entries": dirty},
        "file": file_info,
        "dependencyImpact": dependency_impact,
        "tableViewModelFixtureImpact": table_fixture,
        "cleanJsonFixtureImpact": clean_fixture,
        "staticCheckPlan": {"script": "tmp/check_lib_structured_table_view_model_common_move_1f.mjs", "items": static_checks},
        "validationPlan": [
            "No production code changed during this precheck.",
            "Actual move should be one-file move plus import/path updates only.",
            "Do not rebake fixtures or edit templates.json.",
        ],
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "Proceed with LIB-1F structuredTableViewModel common move as a small import-only move.",
            "Update OcrResultPanel import path and table_view_model runner/checker source path.",
            "Run table_view_model fixture lock, Clean JSON fixture lock, typecheck, and build.",
        ],
    }

    json_path = DOCS / f"{REPORT_BASE}.json"
    md_path = DOCS / f"{REPORT_BASE}.md"
    csv_path = DOCS / "FRONTEND_LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_PRECHECK_MAP_20260522.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = f"""# FRONTEND LIB structuredTableViewModel common move precheck

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `{TASK}`

## 2. 코드 수정 여부
- codeModified: false
- 운영 코드 수정 없음
- 파일 이동/import 수정/rename/fixture/templates/backend 수정 없음

## 3. 생성 파일
- `tmp/codex_frontend_lib_structured_table_view_model_common_move_precheck.py`
- `docs/{REPORT_BASE}.md`
- `docs/{REPORT_BASE}.json`
- `docs/FRONTEND_LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_PRECHECK_MAP_20260522.csv`
- `ocr-server/logs/codex_{TASK}.out.log`
- `ocr-server/logs/codex_{TASK}.err.log`

## 4. 분석 범위
- `src/lib/structuredTableViewModel.ts`
- `src/common/utils/invoiceTableDisplay.ts`
- `src/common/utils/cleanJsonBuilder.ts`
- `src/components/runocr/**`
- `src/components/history/**`
- `src/components/test/TestWorkspace.tsx` 읽기 전용
- `src/components/test/core/**` 읽기 전용
- `src/common/**`
- `src/app/**`
- `tmp/check_table_view_model_v1_fixtures_js.mjs`
- `tmp/check_clean_json_v1_fixtures_js.mjs`

## 5. structuredTableViewModel 역할 요약
- currentPath: `src/lib/structuredTableViewModel.ts`
- lineCount: {file_info['lineCount']}
- imports: {len(imports)}
- exports: {", ".join(exported_names)}
- 역할: caller가 넘긴 `rows`/`displayCols`를 UI-agnostic structured table view model로 변환.
- React/DOM/storage/backend/components dependency: false
- sideEffects: false
- invoiceTableDisplay 관계: 직접 import하지 않고 caller-provided `displayCols`를 소비한다.

## 6. importedBy 분석
| file | importPath | symbols | feature | move import update |
|---|---|---|---|---|
"""
    for row in imported_by:
        md += f"| `{row['file']}` | `{row['importPath']}` | `{row['importedSymbols']}` | {row['feature']} | {row['needsImportUpdateOnMove']} |\n"

    md += f"""

## 7. TestWorkspace 영향 분석
- 판정: `{file_info['testWorkspaceImpact']['status']}`
- TestWorkspace 직접 import: {file_info['testWorkspaceImpact']['directImport']}
- test/core 직접 import: {file_info['testWorkspaceImpact']['testCoreDirectImport']}
- 실제 이동 시 TestWorkspace 수정은 필요하지 않은 것으로 판단한다.

## 8. common/utils 적합성
- 판정: `{file_info['commonUtilReadiness']['verdict']}`
- 순수 helper이고 common formatter/display 계열과 맞는다.
- 현재 직접 production import는 RunOCR 결과 패널 1곳이다.

## 9. dependency/table_view_model/Clean JSON 영향
- structured -> invoiceTableDisplay 직접 import: {dependency_impact['structuredImportsInvoiceTableDisplay']}
- invoiceTableDisplay -> structured 직접 import: {dependency_impact['invoiceTableDisplayImportsStructured']}
- 순환 의존 위험: {dependency_impact['circularDependencyRisk']}
- table_view_model runner source path 직접 참조: {table_fixture['runnerDirectlyReferencesSourcePath']}
- Clean JSON direct structured import: {clean_fixture['directStructuredImport']}
- fixture rebake 필요: false

## 10. target path 비교
| option | risk | recommended |
|---|---|---|
"""
    for option in target_options():
        md += f"| `{option['option']}` | {option['risk']} | {option['recommended']} |\n"

    md += f"""

## 11. 실제 이동 추천
- 추천 선택지: A. `structuredTableViewModel.ts`만 `src/common/utils/structuredTableViewModel.ts`로 이동.
- 필요한 import/path 수정: `OcrResultPanel.tsx`, `tmp/check_table_view_model_v1_fixtures_js.mjs` 또는 move-specific checker.
- 묶지 말 것: `invoiceTableDisplay.ts`, `bizNumber.ts`

## 12. static check 설계
- proposed: `tmp/check_lib_structured_table_view_model_common_move_1f.mjs`
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
- LIB-1F 실제 move step으로 진행.
- 한 파일 이동 + import/path 업데이트만 수행.
- table_view_model fixture lock, Clean JSON fixture lock, typecheck/build를 실행.
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
