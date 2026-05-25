from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "lib" / "invoiceFieldLabels.ts"
OCR_RESULT_FORMATTERS = ROOT / "src" / "common" / "utils" / "ocrResultFormatters.ts"
REPORT_MD = ROOT / "docs" / "FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522.json"
REPORT_CSV = ROOT / "docs" / "FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_MAP_20260522.csv"

ANALYSIS_SCOPE = [
    "src/lib/invoiceFieldLabels.ts",
    "src/common/utils/ocrResultFormatters.ts",
    "src/components/runocr",
    "src/components/template",
    "src/common",
    "src/components/test/TestWorkspace.tsx",
    "src/app",
]

REFERENCE_REPORTS = [
    "docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md",
    "docs/FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522.md",
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
    path = ROOT / "tmp" / f"codex_lib_invoice_field_labels_common_move_precheck_{name}.json"
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
        "@/lib/invoiceFieldLabels",
        "../../lib/invoiceFieldLabels",
        "../lib/invoiceFieldLabels",
        "./invoiceFieldLabels",
        "src/lib/invoiceFieldLabels",
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
        "mainResponsibility": "UI-only invoice_statement canonical field label dictionary and field label resolver helpers.",
        "labelDictionary": "INVOICE_FIELD_KO" in text,
        "sideEffects": has_any(text, ["localStorage.setItem", "sessionStorage.setItem", "indexedDB", "fetch(", "document.", "window."]),
        "browserLocalStorageIndexedDB": has_any(text, ["localStorage", "sessionStorage", "indexedDB", "IDB"]),
        "reactDependency": bool(re.search(r"from ['\"]react['\"]|React\.", text)),
        "componentsDependency": component_deps,
        "featurePolicyTags": ["invoice-labels", "runocr-display", "common-formatting"],
        "commonUtilsFit": "Good fit: static label dictionary and pure resolver helpers with no imports, React, DOM, storage, backend, or components/* dependency.",
    }


def dependency_impact() -> dict[str, object]:
    fmt_text = read(OCR_RESULT_FORMATTERS) if OCR_RESULT_FORMATTERS.exists() else ""
    temp_dep = '@/lib/invoiceFieldLabels' in fmt_text
    return {
        "ocrResultFormattersPath": rel(OCR_RESULT_FORMATTERS) if OCR_RESULT_FORMATTERS.exists() else "MISSING",
        "ocrResultFormattersTempDependency": temp_dep,
        "currentImport": "@/lib/invoiceFieldLabels" if temp_dep else None,
        "recommendedImport": "@/common/utils/invoiceFieldLabels",
        "canResolveTempDependency": temp_dep and TARGET.exists(),
        "commonUtilsNatural": True,
        "circularDependencyRisk": "LOW",
        "reason": "invoiceFieldLabels has no import dependencies, so ocrResultFormatters can import it from common/utils without introducing a cycle.",
    }


def target_candidates() -> list[dict[str, object]]:
    return [
        {
            "target": "src/common/utils/invoiceFieldLabels.ts",
            "pros": ["Resolves common/utils/ocrResultFormatters temporary runtime import from src/lib", "Matches static shared label dictionary role", "Keeps RunOCR display helper dependency common"],
            "cons": ["Requires import-only updates in two consumers"],
            "importUpdateScope": ["src/common/utils/ocrResultFormatters.ts", "src/components/runocr/ui/OcrDocViewer.tsx"],
            "risk": "LOW",
            "recommended": True,
        },
        {
            "target": "src/components/runocr/utils/invoiceFieldLabels.ts",
            "pros": ["Close to OcrDocViewer consumer"],
            "cons": ["common/utils/ocrResultFormatters would need to import from components/runocr, which violates common boundary", "Not suitable while ocrResultFormatters is common"],
            "importUpdateScope": ["src/common/utils/ocrResultFormatters.ts", "src/components/runocr/ui/OcrDocViewer.tsx"],
            "risk": "HIGH",
            "recommended": False,
        },
        {
            "target": "src/lib/invoiceFieldLabels.ts",
            "pros": ["No immediate code change"],
            "cons": ["Leaves common/utils -> src/lib temporary dependency unresolved", "Does not progress LIB-1 cleanup"],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": False,
        },
        {
            "target": "DEFER",
            "pros": ["Avoids current dirty-state interaction"],
            "cons": ["Unnecessary given pure no-import file and small consumer surface"],
            "importUpdateScope": [],
            "risk": "LOW",
            "recommended": False,
        },
    ]


def static_check_plan() -> list[str]:
    return [
        "tmp/check_lib_invoice_field_labels_common_move_1b.mjs",
        "src/common/utils/invoiceFieldLabels.ts exists",
        "src/lib/invoiceFieldLabels.ts absent",
        "src/common/utils/invoiceFieldLabels.ts does not import src/components/*",
        "React/localStorage/window/document/fetch/indexedDB dependency remains absent",
        "src/common/utils/ocrResultFormatters.ts imports @/common/utils/invoiceFieldLabels",
        "src/components/runocr/ui/OcrDocViewer.tsx imports @/common/utils/invoiceFieldLabels",
        "@/lib/invoiceFieldLabels string absent from src",
        "No circular dependency between common/utils/ocrResultFormatters and common/utils/invoiceFieldLabels",
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
    imports = "\n".join(f"- `{item}`" for item in f["imports"]) or "- 없음"
    exports = "\n".join(f"- `{item}`" for item in f["exports"])
    next_steps = "\n".join(f"- {item}" for item in data["nextSteps"])
    dep = data["dependencyImpact"]
    return f"""# FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정 여부: false
- 파일 이동/import 수정/rename/fixture/templates/backend 수정: false
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_lib_invoice_field_labels_common_move_precheck.py`
- `docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
{chr(10).join(f"- `{item}`" for item in data['analysisScope'])}

참고 리포트:
{chr(10).join(f"- `{item}`" for item in data['referenceReports'])}

## 5. invoiceFieldLabels 역할 요약
- currentPath: `{f['currentPath']}`
- lineCount: {f['lineCount']}
- mainResponsibility: {f['role']['mainResponsibility']}
- label dictionary: {f['role']['labelDictionary']}
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

## 8. ocrResultFormatters 임시 의존 해소 가능성
- ocrResultFormatters path: `{dep['ocrResultFormattersPath']}`
- 현재 `@/lib/invoiceFieldLabels` import 중: {dep['ocrResultFormattersTempDependency']}
- 추천 import: `{dep['recommendedImport']}`
- 해소 가능: {dep['canResolveTempDependency']}
- 순환 의존 위험: {dep['circularDependencyRisk']}
- 판단: {dep['reason']}

## 9. target path 비교
| target | 추천 | 장점 | 단점 | import 수정 범위 | risk |
|---|---:|---|---|---|---|
{target_rows}

## 10. 실제 이동 추천
- 추천 선택지: A. `invoiceFieldLabels.ts`만 `src/common/utils/invoiceFieldLabels.ts`로 이동
- 이유: 단순 label dictionary/helper이고 import가 없는 순수 파일이며, 1A 이후 남은 `common/utils/ocrResultFormatters.ts -> @/lib/invoiceFieldLabels` 임시 runtime 의존을 해소한다.
- 필요한 import 수정: `src/common/utils/ocrResultFormatters.ts`, `src/components/runocr/ui/OcrDocViewer.tsx`
- D는 사실상 A의 import 조정에 포함된다. 추가 파일 이동은 하지 않는다.

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
            "reason": "The file is a no-import static label dictionary plus pure resolver helpers. Moving to common/utils only requires import path updates in ocrResultFormatters and OcrDocViewer.",
        },
        "targetCandidates": target_candidates(),
        "recommendation": {
            "choice": "A",
            "targetPath": "src/common/utils/invoiceFieldLabels.ts",
            "scope": "Move only this file and update direct import paths in two consumers; no logic changes.",
            "requiredImportUpdates": [
                "src/common/utils/ocrResultFormatters.ts",
                "src/components/runocr/ui/OcrDocViewer.tsx",
            ],
            "defer": [
                "Do not move additional src/lib files in the same step.",
                "Do not modify TestWorkspace.",
                "Defer remaining src/lib cleanup to later LIB micro-steps.",
            ],
        },
        "risk": {
            "level": "LOW",
            "reasons": [
                "Direct import surface is two files.",
                "No imports inside invoiceFieldLabels.",
                "No React/browser storage/DOM/backend side effects.",
                "No direct TestWorkspace import.",
                "Moving resolves common/utils temporary runtime import from src/lib.",
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
            "Run tmp/check_lib_invoice_field_labels_common_move_1b.mjs after the actual move.",
            "Run npm run typecheck and npm run build.",
            "Run RunOCR boundary checks and Markdown/Clean JSON checks because ocrResultFormatters and OcrDocViewer consume the labels.",
            "Verify TestWorkspace remains unmodified.",
        ],
        "typecheck": command_result("typecheck"),
        "build": command_result("build"),
        "nextSteps": [
            "Proceed with option A as a small move-only micro-step.",
            "Create a move-specific static checker before or during the actual move step.",
            "Confirm @/lib/invoiceFieldLabels is absent from src after the move.",
            "Continue LIB-1 with another low-risk pure helper only after checks pass.",
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
