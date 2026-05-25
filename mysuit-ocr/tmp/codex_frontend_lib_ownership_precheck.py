from __future__ import annotations

import csv
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "docs" / "FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.json"
REPORT_CSV = ROOT / "docs" / "FRONTEND_LIB_OWNERSHIP_MAP_20260522.csv"

LIB_DIR = ROOT / "src" / "lib"
ANALYSIS_ROOTS = [
    "src/lib",
    "src/components/runocr",
    "src/components/template",
    "src/components/history",
    "src/components/autorestore",
    "src/components/login",
    "src/components/layout",
    "src/components/common",
    "src/components/test",
    "src/common",
    "src/app",
]

OWNERSHIP_CANDIDATES = [
    "common/utils",
    "common/types",
    "components/history/utils",
    "components/restore/utils",
    "components/runocr/utils",
    "components/template/utils",
    "components/login/utils",
    "components/layout/utils",
    "components/test/utils",
    "src/lib 유지",
    "보류/추가 precheck 필요",
]

ROLE_OVERRIDES = {
    "autofillEngine.ts": "Autofill candidate collection, suggestion ranking, auto-apply policy, and output-field autofill helpers used around RunOCR/history/restore flows.",
    "axios.ts": "Axios API client factory/interceptors and auth token/header handling.",
    "bizNumber.ts": "Business registration number extraction/normalization/validation helpers.",
    "cleanJsonBuilder.ts": "Clean JSON report/output builder for OCR result fixtures and display contracts.",
    "groundTruthStore.ts": "Ground-truth browser storage helpers for TestWorkspace validation data.",
    "historyStore.ts": "History run index/detail persistence, synchronization, migration, and update helpers.",
    "imageStore.ts": "Template image IndexedDB persistence helpers used by Template and RunOCR template cards.",
    "invoiceFieldLabels.ts": "Invoice field label and display metadata dictionaries.",
    "invoiceTableDisplay.ts": "Invoice table row/column display policy and row-index visibility helpers.",
    "login.ts": "Login/auth token storage and auth request helpers.",
    "markdownReportBuilder.ts": "Markdown report builder for OCR clean/structured outputs.",
    "ocrResultFormatters.ts": "OCR result formatting helpers for text, confidence, and display values.",
    "profiles.ts": "Document/profile definitions and table-column policy metadata for RunOCR/Test validation.",
    "restoreProfileStore.ts": "Restore/autofill profile persistence in browser storage.",
    "structuredTableViewModel.ts": "Structured table view-model builder for invoice table rendering and fixtures.",
    "testsets.ts": "Test dataset manifest/profile loading helpers for TestWorkspace.",
    "theme.ts": "Theme metadata/constants used by application shell/theme setup.",
}

TARGET_OVERRIDES = {
    "autofillEngine.ts": {
        "ownership": "보류/추가 precheck 필요",
        "target": "DEFER: split/confirm between src/common/utils/autofillEngine.ts and components/restore/utils/autofillEngine.ts",
        "recommendation": "별도 precheck. RunOCR, history, restore 영향이 얽혀 한 번에 이동 금지.",
    },
    "axios.ts": {
        "ownership": "보류/추가 precheck 필요",
        "target": "src/common/utils/axios.ts or src/common/api/axios.ts",
        "recommendation": "login/common API ownership precheck 후 이동.",
    },
    "bizNumber.ts": {
        "ownership": "common/utils",
        "target": "src/common/utils/bizNumber.ts",
        "recommendation": "LOW/MEDIUM common helper 후보. Test 영향 확인 후 별도 micro-step.",
    },
    "cleanJsonBuilder.ts": {
        "ownership": "common/utils",
        "target": "src/common/utils/cleanJsonBuilder.ts",
        "recommendation": "LOW risk common report builder 후보.",
    },
    "groundTruthStore.ts": {
        "ownership": "components/test/utils",
        "target": "src/components/test/utils/groundTruthStore.ts",
        "recommendation": "TestWorkspace 관련. 사용자 확인 전 이동 보류.",
    },
    "historyStore.ts": {
        "ownership": "components/history/utils",
        "target": "src/components/history/utils/historyStore.ts",
        "recommendation": "별도 history store precheck 후 이동.",
    },
    "imageStore.ts": {
        "ownership": "보류/추가 precheck 필요",
        "target": "src/common/utils/imageStore.ts or src/components/template/utils/imageStore.ts",
        "recommendation": "Template/RunOCR가 공유하므로 history utils 단독 이동은 비추천. 별도 image persistence ownership precheck.",
    },
    "invoiceFieldLabels.ts": {
        "ownership": "common/utils",
        "target": "src/common/utils/invoiceFieldLabels.ts",
        "recommendation": "LOW risk label dictionary 후보.",
    },
    "invoiceTableDisplay.ts": {
        "ownership": "common/utils",
        "target": "src/common/utils/invoiceTableDisplay.ts",
        "recommendation": "LOW/MEDIUM display policy helper 후보.",
    },
    "login.ts": {
        "ownership": "components/login/utils",
        "target": "src/components/login/utils/login.ts",
        "recommendation": "login/auth precheck 후 이동.",
    },
    "markdownReportBuilder.ts": {
        "ownership": "common/utils",
        "target": "src/common/utils/markdownReportBuilder.ts",
        "recommendation": "LOW risk common report builder 후보.",
    },
    "ocrResultFormatters.ts": {
        "ownership": "common/utils",
        "target": "src/common/utils/ocrResultFormatters.ts",
        "recommendation": "LOW risk formatter 후보.",
    },
    "profiles.ts": {
        "ownership": "보류/추가 precheck 필요",
        "target": "src/common/utils/profiles.ts or src/components/restore/utils/profiles.ts",
        "recommendation": "RunOCR/Test/restore policy 영향. 별도 profile ownership precheck.",
    },
    "restoreProfileStore.ts": {
        "ownership": "components/restore/utils",
        "target": "src/components/restore/utils/restoreProfileStore.ts",
        "recommendation": "restore/autofill profile precheck 후 이동.",
    },
    "structuredTableViewModel.ts": {
        "ownership": "common/utils",
        "target": "src/common/utils/structuredTableViewModel.ts",
        "recommendation": "Clean JSON/Markdown/table fixtures 영향 확인 후 common micro-step.",
    },
    "testsets.ts": {
        "ownership": "components/test/utils",
        "target": "src/components/test/utils/testsets.ts",
        "recommendation": "TestWorkspace 관련. 사용자 확인 전 이동 보류.",
    },
    "theme.ts": {
        "ownership": "components/layout/utils",
        "target": "src/components/layout/utils/theme.ts or src/common/utils/theme.ts",
        "recommendation": "layout/theme ownership precheck 후 이동.",
    },
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def run_git_status() -> list[str]:
    proc = subprocess.run(["git", "status", "--short"], cwd=ROOT, text=True, capture_output=True, check=False)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def command_result(name: str) -> dict[str, object]:
    path = ROOT / "tmp" / f"codex_lib_ownership_precheck_{name}.json"
    if not path.exists():
        return {"command": f"npm run {name}", "exitCode": None, "status": "NOT_RUN"}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def source_files() -> list[Path]:
    roots = [ROOT / root for root in ANALYSIS_ROOTS if (ROOT / root).exists()]
    files: list[Path] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".jsx"}:
                files.append(path)
    return sorted(set(files))


def extract_imports(text: str) -> list[str]:
    imports: list[str] = []
    pattern = re.compile(r"^import\s+.*?;\s*$", re.MULTILINE | re.DOTALL)
    for match in pattern.finditer(text):
        imports.append(" ".join(match.group(0).split()))
    return imports


def extract_exports(text: str) -> list[str]:
    exports: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("export "):
            exports.append(stripped)
    return exports


def module_paths_for(lib_file: Path) -> set[str]:
    stem = lib_file.stem
    return {
        f"@/lib/{stem}",
        f"../../lib/{stem}",
        f"../lib/{stem}",
        f"./lib/{stem}",
        f"src/lib/{stem}",
    }


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
    if p.startswith("src/components/login") or p.startswith("src/app/login") or p.startswith("src/components/common/RequireLogin"):
        return "login"
    if p.startswith("src/components/layout") or p in {"src/app/layout.tsx", "src/app/page.tsx"}:
        return "layout"
    if p.startswith("src/components/test") or p.startswith("src/app/test"):
        return "test"
    if p.startswith("src/common") or p.startswith("src/components/common"):
        return "common"
    if p.startswith("src/app/api"):
        return "app"
    if p.startswith("src/app"):
        return "app"
    return "unknown"


def imported_symbols(import_body: str | None) -> str:
    if not import_body:
        return "*dynamic*"
    body = " ".join(import_body.split())
    return body


def find_imported_by(lib_file: Path, files: list[Path]) -> list[dict[str, object]]:
    wanted = module_paths_for(lib_file)
    rows: list[dict[str, object]] = []
    for file in files:
        if file == lib_file:
            continue
        text = read(file)
        for match in IMPORT_RE.finditer(text):
            import_path = match.group("path") or match.group("dynamic")
            if import_path not in wanted:
                continue
            rows.append({
                "file": rel(file),
                "importPath": import_path,
                "importKind": "dynamic" if match.group("dynamic") else "static",
                "importedSymbols": imported_symbols(match.group("body")),
                "feature": feature_for(file),
                "moveImpact": "import path update required",
            })
    return rows


def has_browser_storage(text: str) -> bool:
    return any(token in text for token in ["localStorage", "sessionStorage", "indexedDB", "IDB", "window."])


def has_backend_api(text: str) -> bool:
    return any(token in text for token in ["fetch(", "axios", "/api/", "NEXT_PUBLIC", "XMLHttpRequest"])


def has_react(text: str) -> bool:
    return bool(re.search(r"from ['\"]react['\"]|React\.", text))


def has_side_effects(text: str) -> bool:
    side_effect_tokens = ["localStorage.setItem", "sessionStorage.setItem", "indexedDB", "fetch(", "axios.", "document.", "window.", "URL.createObjectURL"]
    return any(token in text for token in side_effect_tokens)


def policy_tags(name: str, text: str) -> list[str]:
    tags: list[str] = []
    checks = {
        "history": ["history", "History"],
        "restore": ["restore", "Restore", "autofill", "Autofill"],
        "template": ["template", "Template"],
        "runocr": ["RunOCR", "ocrResult", "OcrResult"],
        "test": ["groundTruth", "testset", "Dataset", "GT"],
        "login": ["login", "token", "auth"],
        "invoice": ["invoice", "Invoice", "tableRows"],
    }
    hay = name + "\n" + text[:4000]
    for tag, needles in checks.items():
        if any(needle in hay for needle in needles):
            tags.append(tag)
    return tags


def infer_risk(name: str, imported_by: list[dict[str, object]], text: str, ownership: str) -> str:
    features = {row["feature"] for row in imported_by}
    if name in {"autofillEngine.ts", "historyStore.ts", "profiles.ts"}:
        return "HIGH"
    if any(row["feature"] == "test" for row in imported_by) and name in {"groundTruthStore.ts", "testsets.ts", "profiles.ts", "invoiceTableDisplay.ts", "bizNumber.ts"}:
        return "HIGH"
    if has_browser_storage(text) or has_backend_api(text) or len(features) >= 3 or ownership == "보류/추가 precheck 필요":
        return "MEDIUM" if name not in {"imageStore.ts"} else "HIGH"
    return "LOW"


def summarize_ownership(lib_files: list[dict[str, object]]) -> dict[str, object]:
    counts = Counter(str(item["ownership"]["candidate"]) for item in lib_files)
    return {
        "counts": dict(counts),
        "highRisk": [item["currentPath"] for item in lib_files if item["risk"]["level"] == "HIGH"],
        "deferred": [item["currentPath"] for item in lib_files if item["ownership"]["candidate"] in {"components/test/utils", "보류/추가 precheck 필요"}],
    }


def build_lib_record(lib_file: Path, files: list[Path]) -> dict[str, object]:
    text = read(lib_file)
    name = lib_file.name
    imports = extract_imports(text)
    exports = extract_exports(text)
    imported_by = find_imported_by(lib_file, files)
    override = TARGET_OVERRIDES[name]
    ownership = override["ownership"]
    risk_level = infer_risk(name, imported_by, text, ownership)
    test_impact = any(row["feature"] == "test" for row in imported_by) or ownership == "components/test/utils"
    return {
        "currentPath": rel(lib_file),
        "lineCount": len(text.splitlines()),
        "imports": imports,
        "exports": exports,
        "importedBy": imported_by,
        "role": {
            "mainResponsibility": ROLE_OVERRIDES[name],
            "sideEffects": has_side_effects(text),
            "browserLocalStorageIndexedDB": has_browser_storage(text),
            "backendApiCalls": has_backend_api(text),
            "reactDependency": has_react(text),
            "featurePolicyTags": policy_tags(name, text),
        },
        "ownership": {
            "candidate": ownership,
            "allowedCandidates": OWNERSHIP_CANDIDATES,
            "reason": ownership_reason(name, imported_by, ownership),
        },
        "targetCandidates": [override["target"]],
        "recommendation": override["recommendation"],
        "risk": {
            "level": risk_level,
            "reason": risk_reason(name, imported_by, text, ownership, test_impact),
        },
        "testWorkspaceImpact": {
            "hasImpact": test_impact,
            "status": "DEFER_UNTIL_USER_CONFIRMATION" if test_impact else "NO_DIRECT_TEST_IMPORT_FOUND",
        },
    }


def ownership_reason(name: str, imported_by: list[dict[str, object]], ownership: str) -> str:
    features = sorted({str(row["feature"]) for row in imported_by})
    if ownership == "common/utils":
        return f"Pure/shared helper or display policy used across {features or ['no direct src consumer found']}."
    if ownership == "components/test/utils":
        return "TestWorkspace/test route ownership; user confirmation required before any move."
    if ownership == "보류/추가 precheck 필요":
        return f"Ambiguous or cross-feature ownership across {features}; needs narrower precheck."
    return f"Primary consumer feature set: {features}."


def risk_reason(name: str, imported_by: list[dict[str, object]], text: str, ownership: str, test_impact: bool) -> str:
    bits: list[str] = []
    features = sorted({str(row["feature"]) for row in imported_by})
    if features:
        bits.append(f"features={','.join(features)}")
    if has_browser_storage(text):
        bits.append("browser storage")
    if has_backend_api(text):
        bits.append("API/backend access")
    if test_impact:
        bits.append("TestWorkspace impact")
    if ownership == "보류/추가 precheck 필요":
        bits.append("ownership deferred")
    return "; ".join(bits) or "small pure helper surface"


def move_phases() -> list[dict[str, object]]:
    return [
        {
            "phase": "LIB-1",
            "title": "common formatter/display utils",
            "files": [
                "src/lib/invoiceFieldLabels.ts",
                "src/lib/ocrResultFormatters.ts",
                "src/lib/markdownReportBuilder.ts",
                "src/lib/cleanJsonBuilder.ts",
                "src/lib/invoiceTableDisplay.ts",
                "src/lib/structuredTableViewModel.ts",
                "src/lib/bizNumber.ts",
            ],
            "notes": "Start with low-risk pure helpers. Include table/clean-json checks when table view-model files move.",
        },
        {
            "phase": "LIB-2",
            "title": "history store",
            "files": ["src/lib/historyStore.ts"],
            "notes": "Separate history persistence precheck; verify HistoryWorkspace and RunOCR history writes.",
        },
        {
            "phase": "LIB-3",
            "title": "restore profile/autofill/image persistence",
            "files": ["src/lib/restoreProfileStore.ts", "src/lib/autofillEngine.ts", "src/lib/profiles.ts", "src/lib/imageStore.ts"],
            "notes": "Do not batch blindly. Autofill/profile/imageStore need separate boundary decisions.",
        },
        {
            "phase": "LIB-4",
            "title": "login/api/theme",
            "files": ["src/lib/login.ts", "src/lib/axios.ts", "src/lib/theme.ts"],
            "notes": "Confirm login/common API/layout ownership before moving.",
        },
        {
            "phase": "LIB-5",
            "title": "test-related",
            "files": ["src/lib/groundTruthStore.ts", "src/lib/testsets.ts"],
            "notes": "Blocked until user explicitly approves TestWorkspace-related work.",
        },
    ]


def static_check_plan() -> list[str]:
    return [
        "tmp/check_lib_common_utils_move_xxx.mjs",
        "tmp/check_history_utils_move_xxx.mjs",
        "tmp/check_restore_utils_move_xxx.mjs",
        "target files exist and source files are absent for the active micro-step",
        "all import paths point at the new target paths",
        "src/common/utils does not import from src/components/*",
        "TestWorkspace remains unchanged unless explicitly approved",
        "RunOCR boundary checks PASS",
        "Template checks PASS",
        "table_view_model/Clean JSON/Markdown checks PASS",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]


def render_md(data: dict[str, object]) -> str:
    lib_files = data["libFiles"]
    rows = "\n".join(
        f"| `{item['currentPath']}` | {item['lineCount']} | {item['ownership']['candidate']} | `{item['targetCandidates'][0]}` | {item['risk']['level']} | {item['testWorkspaceImpact']['status']} | {item['role']['mainResponsibility']} |"
        for item in lib_files
    )
    imported_summary = "\n".join(
        f"- `{item['currentPath']}`: "
        + (", ".join(f"`{row['file']}`({row['feature']})" for row in item["importedBy"]) or "direct src import 없음")
        for item in lib_files
    )
    phases = "\n".join(
        f"- {phase['phase']} {phase['title']}: {', '.join(phase['files'])}. {phase['notes']}"
        for phase in data["movePhases"]
    )
    dirty = "\n".join(data["dirtyStatus"])
    checks = "\n".join(f"- {item}" for item in data["staticCheckPlan"])
    next_steps = "\n".join(f"- {item}" for item in data["nextSteps"])

    return f"""# FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_LIB_OWNERSHIP_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정 여부: false
- 파일 이동/import 수정/rename/fixture/templates/backend 수정: false
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_lib_ownership_precheck.py`
- `docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_LIB_OWNERSHIP_MAP_20260522.csv`

## 4. 분석 범위
{chr(10).join(f"- `{root}`" for root in ANALYSIS_ROOTS)}

## 5. src/lib 파일별 역할 요약
| file | lines | ownership 후보 | targetPath 후보 | risk | TestWorkspace | mainResponsibility |
|---|---:|---|---|---|---|---|
{rows}

## 6. importedBy 분석 요약
{imported_summary}

## 7. ownership 분류표
```json
{json.dumps(data['ownershipSummary']['counts'], ensure_ascii=False, indent=2)}
```

## 8. target path 제안
세부 target path 후보는 위 표와 JSON/CSV에 기록했다. `imageStore`, `autofillEngine`, `profiles`, `axios`는 단일 feature로 확정하지 않고 별도 precheck 후보로 둔다.

## 9. 위험도 분류
- HIGH: {', '.join(data['ownershipSummary']['highRisk']) or '없음'}
- 보류: {', '.join(data['ownershipSummary']['deferred']) or '없음'}

## 10. 이동 순서 추천
{phases}

## 11. TestWorkspace 관련 보류 항목
- `src/lib/groundTruthStore.ts` -> `src/components/test/utils/groundTruthStore.ts` 후보, 사용자 확인 전 이동 금지
- `src/lib/testsets.ts` -> `src/components/test/utils/testsets.ts` 후보, 사용자 확인 전 이동 금지
- `profiles.ts`, `invoiceTableDisplay.ts`, `bizNumber.ts` 등 TestWorkspace import가 있는 common 후보도 실제 이동 시 TestWorkspace 미수정 검증 필요

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
    files = source_files()
    lib_paths = sorted(path for path in LIB_DIR.glob("*") if path.suffix in {".ts", ".tsx"})
    lib_records = [build_lib_record(path, files) for path in lib_paths]
    data: dict[str, object] = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "projectRoot": "OCR/mysuit-ocr",
        "codeModified": False,
        "dirtyStatus": run_git_status(),
        "analysisScope": ANALYSIS_ROOTS,
        "libFiles": lib_records,
        "ownershipSummary": summarize_ownership(lib_records),
        "movePhases": move_phases(),
        "staticCheckPlan": static_check_plan(),
        "validationPlan": [
            "Run the phase-specific static checker for each micro-step.",
            "Run npm run typecheck and npm run build after each move.",
            "Run RunOCR/Template/table_view_model/Clean JSON/Markdown checks as applicable.",
            "Do not modify TestWorkspace until explicitly approved.",
        ],
        "typecheck": command_result("typecheck"),
        "build": command_result("build"),
        "nextSteps": [
            "Start with LIB-1 low-risk common formatter/display helpers, one small batch at a time.",
            "Run a dedicated precheck before moving historyStore.",
            "Run separate ownership prechecks for autofillEngine/profiles/imageStore.",
            "Keep TestWorkspace-related files deferred until user confirmation.",
        ],
    }

    REPORT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_md(data), encoding="utf-8")
    with REPORT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "currentPath",
                "lineCount",
                "ownership",
                "targetPath",
                "risk",
                "testWorkspaceImpact",
                "importedByCount",
                "importedByFeatures",
                "recommendation",
            ],
        )
        writer.writeheader()
        for item in lib_records:
            writer.writerow({
                "currentPath": item["currentPath"],
                "lineCount": item["lineCount"],
                "ownership": item["ownership"]["candidate"],
                "targetPath": item["targetCandidates"][0],
                "risk": item["risk"]["level"],
                "testWorkspaceImpact": item["testWorkspaceImpact"]["status"],
                "importedByCount": len(item["importedBy"]),
                "importedByFeatures": ";".join(sorted({str(row["feature"]) for row in item["importedBy"]})),
                "recommendation": item["recommendation"],
            })


if __name__ == "__main__":
    main()
