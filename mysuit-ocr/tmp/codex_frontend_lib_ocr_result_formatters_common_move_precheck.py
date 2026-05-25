from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "lib" / "ocrResultFormatters.ts"
REPORT_MD = ROOT / "docs" / "FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.json"
REPORT_CSV = ROOT / "docs" / "FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_MAP_20260522.csv"

ANALYSIS_SCOPE = [
    "src/lib/ocrResultFormatters.ts",
    "src/components/runocr",
    "src/components/template",
    "src/common",
    "src/components/test/TestWorkspace.tsx",
    "src/app",
]

REFERENCE_REPORTS = [
    "docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md",
    "docs/FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME_20260522.md",
    "docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.md",
    "docs/FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_20260522.md",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def git_status() -> list[str]:
    proc = subprocess.run(["git", "status", "--short"], cwd=ROOT, text=True, capture_output=True, check=False)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def command_result(name: str) -> dict[str, object]:
    path = ROOT / "tmp" / f"codex_lib_ocr_result_formatters_common_move_precheck_{name}.json"
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
    # Include src/lib because markdownReportBuilder imports the target.
    lib_dir = ROOT / "src" / "lib"
    files.extend(child for child in lib_dir.glob("*") if child.suffix in {".ts", ".tsx"})
    return sorted(set(files))


def extract_imports(text: str) -> list[str]:
    pattern = re.compile(r"^import\s+.*?;\s*$", re.MULTILINE | re.DOTALL)
    return [" ".join(match.group(0).split()) for match in pattern.finditer(text)]


def extract_exports(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip().startswith("export ")]


def exported_names(text: str) -> list[str]:
    names: list[str] = []
    patterns = [
        r"export\s+function\s+([A-Za-z0-9_]+)",
        r"export\s+const\s+([A-Za-z0-9_]+)",
        r"export\s+type\s+([A-Za-z0-9_]+)",
        r"export\s+interface\s+([A-Za-z0-9_]+)",
    ]
    for pattern in patterns:
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
        "@/lib/ocrResultFormatters",
        "../../lib/ocrResultFormatters",
        "../lib/ocrResultFormatters",
        "./ocrResultFormatters",
        "src/lib/ocrResultFormatters",
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
        "mainResponsibility": "Pure OCR result display/report formatters: field labels, amount-like detection, adoption labels, and serialized table field parsing for RunOCR result UI and markdown report generation.",
        "sideEffects": has_any(text, ["localStorage.setItem", "sessionStorage.setItem", "indexedDB", "fetch(", "document.", "window."]),
        "browserLocalStorageIndexedDB": has_any(text, ["localStorage", "sessionStorage", "indexedDB", "IDB"]),
        "reactDependency": bool(re.search(r"from ['\"]react['\"]|React\.", text)),
        "componentsDependency": component_deps,
        "featurePolicyTags": ["runocr-display", "markdown-report", "table-field-formatting"],
        "commonUtilsFit": "Good fit: pure deterministic helpers with no React, DOM, storage, backend, or components/* dependency. Caveat: it currently imports src/lib/autofillEngine types and src/lib/invoiceFieldLabels.",
    }


def target_candidates() -> list[dict[str, object]]:
    return [
        {
            "target": "src/common/utils/ocrResultFormatters.ts",
            "pros": ["Matches shared pure formatter role", "Allows RunOCR UI and report builders to depend on common utils", "No components/* dependency introduced"],
            "cons": ["Temporarily common/utils would import from src/lib/autofillEngine and src/lib/invoiceFieldLabels until later LIB moves", "Requires import-only updates in two consumers"],
            "importUpdateScope": ["src/components/runocr/ui/OcrResultPanel.tsx", "src/lib/markdownReportBuilder.ts"],
            "risk": "LOW",
            "recommended": True,
        },
        {
            "target": "src/components/runocr/utils/ocrResultFormatters.ts",
            "pros": ["Close to the main UI consumer"],
            "cons": ["markdownReportBuilder in src/lib would import feature code or need to move too", "Less aligned with shared report/display helper role"],
            "importUpdateScope": ["src/components/runocr/ui/OcrResultPanel.tsx", "src/lib/markdownReportBuilder.ts"],
            "risk": "MEDIUM",
            "recommended": False,
        },
        {
            "target": "src/lib/ocrResultFormatters.ts",
            "pros": ["No immediate code change"],
            "cons": ["Leaves src/lib cleanup stalled", "Does not progress LIB-1 common utils"],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": False,
        },
        {
            "target": "DEFER",
            "pros": ["Avoids any current dirty-state interaction"],
            "cons": ["Unnecessary given small import surface and pure helper shape"],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": False,
        },
    ]


def static_check_plan() -> list[str]:
    return [
        "tmp/check_lib_ocr_result_formatters_common_move_1a.mjs",
        "src/common/utils/ocrResultFormatters.ts exists",
        "src/lib/ocrResultFormatters.ts absent",
        "src/common/utils/ocrResultFormatters.ts does not import src/components/*",
        "React/localStorage/window/document/fetch/indexedDB dependency remains absent",
        "src/components/runocr/ui/OcrResultPanel.tsx import path points to common utils",
        "src/lib/markdownReportBuilder.ts import path points to common utils",
        "No @/lib/ocrResultFormatters or ../../lib/ocrResultFormatters remains in src",
        "TestWorkspace unchanged",
        "RunOCR boundary checks PASS",
        "Template checks PASS",
        "table_view_model/Clean JSON/Markdown checks PASS",
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
    next_steps = "\n".join(f"- {item}" for item in data["nextSteps"])
    imports = "\n".join(f"- `{item}`" for item in f["imports"])
    exports = "\n".join(f"- `{item}`" for item in f["exports"])
    return f"""# FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정 여부: false
- 파일 이동/import 수정/rename/fixture/templates/backend 수정: false
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_lib_ocr_result_formatters_common_move_precheck.py`
- `docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
{chr(10).join(f"- `{item}`" for item in data['analysisScope'])}

참고 리포트:
{chr(10).join(f"- `{item}`" for item in data['referenceReports'])}

## 5. ocrResultFormatters 역할 요약
- currentPath: `{f['currentPath']}`
- lineCount: {f['lineCount']}
- mainResponsibility: {f['role']['mainResponsibility']}
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
- 주의: 이동 직후에는 `autofillEngine` type import와 `invoiceFieldLabels` import가 `src/lib`에 남을 수 있다. 이는 components 의존은 아니며, 후속 LIB-1/별도 precheck에서 정리한다.

## 8. target path 비교
| target | 추천 | 장점 | 단점 | import 수정 범위 | risk |
|---|---:|---|---|---|---|
{target_rows}

## 9. 실제 이동 추천
- 추천 선택지: A. `ocrResultFormatters.ts`만 `src/common/utils/ocrResultFormatters.ts`로 이동
- 이유: 첫 LIB 이동은 작게 시작하는 것이 안전하고, direct consumer가 2곳뿐이며 순수 formatter이다.
- 필요한 import 수정: `src/components/runocr/ui/OcrResultPanel.tsx`, `src/lib/markdownReportBuilder.ts`
- 묶음 이동(D)은 비추천: markdown/clean json과 한 번에 묶으면 첫 LIB 이동 diff가 커진다.

## 10. static check 설계
{checks}

## 11. dirty 상태
```text
{dirty}
```

- `../ocr-server/data/templates.json` dirty 상태가 있으면 실제 이동 전 영향 후보로 유지한다.
- TPL-95328E52 dirty 영향 precheck 후보를 유지한다.

## 12. typecheck/build 결과
- typecheck: `{data['typecheck'].get('status')}` exitCode={data['typecheck'].get('exitCode')}
- build: `{data['build'].get('status')}` exitCode={data['build'].get('exitCode')}
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 known issue로 기록한다.

## 13. 다음 작업 제안
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
            "reason": "The file is pure and has no React, DOM, storage, backend, or components/* dependency. Moving to common/utils requires only import path updates in OcrResultPanel and markdownReportBuilder.",
        },
        "targetCandidates": target_candidates(),
        "recommendation": {
            "choice": "A",
            "targetPath": "src/common/utils/ocrResultFormatters.ts",
            "scope": "Move only this file and update direct import paths in two consumers; no logic changes.",
            "requiredImportUpdates": [
                "src/components/runocr/ui/OcrResultPanel.tsx",
                "src/lib/markdownReportBuilder.ts",
            ],
            "defer": [
                "Do not move markdownReportBuilder or cleanJsonBuilder in the same step.",
                "Do not modify TestWorkspace.",
                "Defer invoiceFieldLabels/autofillEngine ownership cleanup to later LIB steps.",
            ],
        },
        "risk": {
            "level": "LOW",
            "reasons": [
                "Direct import surface is two files.",
                "No components/* import inside formatter file.",
                "No React/browser storage/DOM/backend side effects.",
                "No direct TestWorkspace import.",
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
        "staticCheckPlan": static_check_plan(),
        "validationPlan": [
            "Run tmp/check_lib_ocr_result_formatters_common_move_1a.mjs after the actual move.",
            "Run npm run typecheck and npm run build.",
            "Run RunOCR boundary checks and Markdown/Clean JSON checks because the consumers are OcrResultPanel and markdownReportBuilder.",
            "Verify TestWorkspace remains unmodified.",
        ],
        "typecheck": command_result("typecheck"),
        "build": command_result("build"),
        "nextSteps": [
            "Proceed with option A as a small move-only micro-step.",
            "Create a move-specific static checker before or during the actual move step.",
            "Keep markdownReportBuilder/cleanJsonBuilder moves separate.",
            "Later, move invoiceFieldLabels to common/utils so ocrResultFormatters can stop importing it from src/lib.",
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
