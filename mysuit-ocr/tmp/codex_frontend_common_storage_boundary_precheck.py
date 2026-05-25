import csv
import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

MD_PATH = DOCS_DIR / "FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_20260522.md"
JSON_PATH = DOCS_DIR / "FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_20260522.json"
CSV_PATH = DOCS_DIR / "FRONTEND_COMMON_STORAGE_BOUNDARY_MAP_20260522.csv"

TYPECHECK_RESULT = PROJECT_ROOT / "tmp" / "codex_common_storage_boundary_precheck_typecheck.json"
BUILD_RESULT = PROJECT_ROOT / "tmp" / "codex_common_storage_boundary_precheck_build.json"

TARGET_FILES = [
    "src/lib/historyStore.ts",
    "src/lib/imageStore.ts",
    "src/lib/autofillEngine.ts",
    "src/lib/groundTruthStore.ts",
    "src/lib/restoreProfileStore.ts",
    "src/lib/profiles.ts",
    "src/lib/bizNumber.ts",
    "src/lib/testsets.ts",
]

STORAGE_FILES = [
    "src/lib/historyStore.ts",
    "src/lib/imageStore.ts",
    "src/lib/groundTruthStore.ts",
    "src/lib/restoreProfileStore.ts",
    "src/lib/profiles.ts",
    "src/lib/testsets.ts",
]

SEARCH_KEYWORDS = [
    "historyStore",
    "imageStore",
    "autofillEngine",
    "groundTruthStore",
    "restoreProfileStore",
    "profiles",
    "testsets",
    "bizNumber",
    "appendHistoryRun",
    "updateHistoryRun",
    "readHistoryRuns",
    "saveImage",
    "loadImage",
    "restoreProfile",
    "AutofillSuggestion",
    "normalizeAutofillFieldKey",
]


def path(rel: str) -> Path:
    return PROJECT_ROOT / rel


def read_text(rel: str) -> str:
    p = path(rel)
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def line_count(rel: str) -> int:
    text = read_text(rel)
    return len(text.splitlines()) if text else 0


def parse_imports(text: str) -> list[dict]:
    imports = []
    for match in re.finditer(r"import\s+([\s\S]*?)\s+from\s+['\"]([^'\"]+)['\"]", text):
        symbols = " ".join(match.group(1).split())
        imports.append(
            {
                "symbols": symbols,
                "source": match.group(2),
                "typeOnly": symbols.startswith("type ") or symbols == "type",
            }
        )
    for match in re.finditer(r"import\s+['\"]([^'\"]+)['\"]", text):
        imports.append({"symbols": "(side-effect)", "source": match.group(1), "typeOnly": False})
    return imports


def parse_exports(text: str) -> list[dict]:
    exports = []
    pattern = r"export\s+(?:(type|interface|function|const|class)\s+([A-Za-z0-9_]+)|default\s+function\s+([A-Za-z0-9_]+))"
    for match in re.finditer(pattern, text):
        exports.append({"kind": match.group(1) or "default function", "name": match.group(2) or match.group(3)})
    return exports


def rg(pattern: str, roots: list[str]) -> list[dict]:
    proc = subprocess.run(
        ["rg", "-n", "--hidden", "--glob", "!node_modules", pattern, *roots],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    rows = []
    if proc.returncode not in (0, 1):
        return [{"pattern": pattern, "error": proc.stderr.strip()}]
    for line in proc.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            rows.append({"file": parts[0].replace("\\", "/"), "line": int(parts[1]), "text": parts[2].strip()})
    return rows


def feature_for(file: str) -> str:
    p = file.replace("\\", "/")
    if p.startswith("src/components/runocr/") or p.startswith("src/app/runocr/") or p == "src/app/ocr/page.tsx":
        return "runocr"
    if p.startswith("src/components/history/") or p.startswith("src/app/history/"):
        return "history"
    if p.startswith("src/components/autorestore/") or p.startswith("src/components/restore/") or p.startswith("src/app/autorestore/"):
        return "restore"
    if p.startswith("src/components/template/") or p.startswith("src/app/template/"):
        return "template"
    if p.startswith("src/components/test/"):
        return "test"
    if p.startswith("src/common/"):
        return "common"
    if p.startswith("src/lib/"):
        return "lib"
    if p.startswith("src/app/"):
        return "app"
    if p.startswith("tmp/"):
        return "tmp"
    return "unknown"


def import_symbols(line: str) -> str:
    match = re.search(r"import\s+(.+?)\s+from\s+['\"]", line)
    return " ".join(match.group(1).split()) if match else ""


def runtime_or_type(line: str) -> str:
    if "import type" in line or re.search(r"import\s+\{[^}]*\btype\b", line):
        return "type-only"
    if "import" in line:
        return "runtime"
    return "reference"


def imported_by_for(file_rel: str, exports: list[dict]) -> list[dict]:
    stem = Path(file_rel).stem
    keys = [
        stem,
        f"@/lib/{stem}",
        f"./{stem}",
        f"../lib/{stem}",
        f"../../lib/{stem}",
    ] + [e["name"] for e in exports]
    rows = []
    seen = set()
    for key in keys:
        for hit in rg(key, ["src", "tmp"]):
            item = (hit.get("file"), hit.get("line"), hit.get("text"))
            if item in seen:
                continue
            seen.add(item)
            if hit.get("file") == file_rel:
                continue
            text = hit.get("text", "")
            rows.append(
                {
                    "file": hit.get("file"),
                    "line": hit.get("line"),
                    "importPath": text if "import" in text else "(reference)",
                    "importedSymbols": import_symbols(text),
                    "feature": feature_for(hit.get("file", "")),
                    "runtimeOrTypeOnly": runtime_or_type(text),
                    "needsImportUpdateOnMove": f"@/lib/{stem}" in text
                    or f"./{stem}" in text
                    or f"../lib/{stem}" in text
                    or f"../../lib/{stem}" in text,
                    "testWorkspaceImpact": hit.get("file", "").startswith("src/components/test/"),
                    "tmpReference": hit.get("file", "").startswith("tmp/"),
                }
            )
    return rows


def classify_file(file_rel: str, text: str, imported_by: list[dict]) -> dict:
    consumers = {row["feature"] for row in imported_by if row["runtimeOrTypeOnly"] != "reference" and row["feature"] != "tmp"}
    uses_local = "localStorage" in text or "sessionStorage" in text
    uses_idb = "indexedDB" in text or "IDBDatabase" in text
    uses_browser = "window" in text or "document" in text or "crypto" in text or uses_local or uses_idb
    uses_react = "from \"react\"" in text or "from 'react'" in text
    components_dep = "@/components/" in text or "../components/" in text or "../../components/" in text
    backend_api = "fetch(" in text or "axios" in text or "@/lib/axios" in text

    if file_rel.endswith("historyStore.ts"):
        recommendation = ("common/storage", "src/common/storage/historyStore.ts", "HIGH", "shared OCR history persistence used by RunOCR, History, autofillEngine")
    elif file_rel.endswith("imageStore.ts"):
        recommendation = ("common/storage", "src/common/storage/imageStore.ts", "MEDIUM_HIGH", "IndexedDB image persistence shared by history and template image helpers")
    elif file_rel.endswith("groundTruthStore.ts"):
        recommendation = ("defer/test-aware", "DEFER_UNTIL_TEST_WORKSPACE_APPROVAL or src/common/storage/groundTruthStore.ts", "HIGH", "localStorage ground truth store with TestWorkspace policy sensitivity")
    elif file_rel.endswith("restoreProfileStore.ts"):
        recommendation = ("restore/utils or common/storage", "src/components/restore/utils/restoreProfileStore.ts after restore boundary OR src/common/storage/restoreProfileStore.ts", "MEDIUM_HIGH", "restore profile localStorage store consumed by autofillEngine and history detail")
    elif file_rel.endswith("profiles.ts"):
        recommendation = ("restore/data or defer", "src/components/restore/utils/profiles.ts or src/common/data/profiles.ts", "MEDIUM", "profile definitions/helper data, ownership depends on restore/Test usage")
    elif file_rel.endswith("testsets.ts"):
        recommendation = ("test/utils defer", "src/components/test/utils/testsets.ts after user approval", "HIGH", "TestWorkspace/testset related")
    elif file_rel.endswith("bizNumber.ts"):
        recommendation = ("common/utils", "src/common/utils/bizNumber.ts", "MEDIUM", "pure business number parser/normalizer likely common utility")
    elif file_rel.endswith("autofillEngine.ts"):
        recommendation = ("defer separate precheck", "DEFER_UNTIL_STORAGE_BOUNDARY", "HIGH", "shared domain engine depends on historyStore, restoreProfileStore, bizNumber")
    else:
        recommendation = ("review", "REVIEW_NEEDED", "MEDIUM", "unknown")

    return {
        "mainConsumers": sorted(consumers),
        "localStorageUse": uses_local,
        "indexedDBUse": uses_idb,
        "browserApiUse": uses_browser,
        "backendApiUse": backend_api,
        "reactDependency": uses_react,
        "componentsDependency": components_dep,
        "runocrDependency": "runocr" in consumers,
        "historyDependency": "history" in consumers,
        "restoreDependency": "restore" in consumers,
        "templateDependency": "template" in consumers,
        "testWorkspaceDependency": any(row["testWorkspaceImpact"] for row in imported_by),
        "commonStorageReadiness": recommendation[0] == "common/storage",
        "commonDataReadiness": recommendation[0] in {"restore/data or defer"},
        "featureUtilsReadiness": recommendation[0] in {"restore/utils or common/storage", "test/utils defer"},
        "recommendedOwner": recommendation[0],
        "recommendedTarget": recommendation[1],
        "risk": recommendation[2],
        "recommendationReason": recommendation[3],
    }


def resolve_import(from_file: str, source: str) -> str | None:
    if source.startswith("@/"):
        return f"src/{source[2:]}.ts"
    if source.startswith("."):
        base = Path(from_file).parent
        candidate = (base / source).as_posix()
        for suffix in [".ts", ".tsx", "/index.ts", "/index.tsx"]:
            rel = f"{candidate}{suffix}"
            if (PROJECT_ROOT / rel).exists():
                return rel
    return None


def dependency_graph(files: list[dict]) -> dict:
    target_set = {item["currentPath"] for item in files}
    edges = []
    for item in files:
        for imp in item["imports"]:
            resolved = resolve_import(item["currentPath"], imp["source"])
            if resolved in target_set:
                edges.append(
                    {
                        "from": item["currentPath"],
                        "to": resolved,
                        "source": imp["source"],
                        "typeOnly": imp["typeOnly"],
                    }
                )
    incoming = defaultdict(list)
    outgoing = defaultdict(list)
    for edge in edges:
        outgoing[edge["from"]].append(edge["to"])
        incoming[edge["to"]].append(edge["from"])
    return {
        "edges": edges,
        "reverseEdges": {k: v for k, v in incoming.items()},
        "outgoingEdges": {k: v for k, v in outgoing.items()},
        "cycleRisk": "MEDIUM: autofillEngine depends on historyStore/restoreProfileStore; moving stores into feature folders would create cross-feature imports.",
        "sharedBoundaryRisk": "HIGH without common/storage; LOW_MEDIUM if browser persistence files move into common/storage.",
        "featureDependencyRisk": "historyStore in components/history/utils would force RunOCR and autofillEngine to import history feature code.",
    }


def command_result(path_obj: Path, command: str) -> dict:
    if not path_obj.exists():
        return {"command": command, "status": "NOT_RUN", "exitCode": None}
    try:
        return json.loads(path_obj.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"command": command, "status": "UNKNOWN", "exitCode": None}


def git_status() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return [f"git status failed: {proc.stderr.strip()}"]
    return proc.stdout.splitlines()


def test_impact_for(file_rel: str, imported_by: list[dict]) -> str:
    if any(row["file"] == "src/components/test/TestWorkspace.tsx" and row["runtimeOrTypeOnly"] != "reference" for row in imported_by):
        return "TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY"
    if any(row["file"].startswith("src/components/test/core/") and row["runtimeOrTypeOnly"] != "reference" for row in imported_by):
        return "TEST_CORE_DIRECT_IMPORT"
    if file_rel.endswith(("groundTruthStore.ts", "testsets.ts")):
        return "DEFER_DUE_TO_TEST_WORKSPACE_POLICY"
    return "NO_TEST_IMPACT"


def main() -> int:
    files = []
    for rel in TARGET_FILES:
        text = read_text(rel)
        imports = parse_imports(text)
        exports = parse_exports(text)
        imported_by = imported_by_for(rel, exports)
        role = classify_file(rel, text, imported_by)
        files.append(
            {
                "currentPath": rel,
                "lineCount": line_count(rel),
                "role": role["recommendationReason"],
                "imports": imports,
                "exports": exports,
                "importedBy": imported_by,
                "storageReadiness": {
                    "commonStorage": role["commonStorageReadiness"],
                    "commonData": role["commonDataReadiness"],
                    "featureUtils": role["featureUtilsReadiness"],
                },
                "targetCandidates": [
                    role["recommendedTarget"],
                    "src/lib 유지",
                    "보류",
                ],
                "recommendation": {
                    "owner": role["recommendedOwner"],
                    "target": role["recommendedTarget"],
                    "reason": role["recommendationReason"],
                },
                "risk": role["risk"],
                "testWorkspaceImpact": test_impact_for(rel, imported_by),
                "signals": role,
            }
        )

    graph = dependency_graph(files)

    autofill = next(item for item in files if item["currentPath"].endswith("autofillEngine.ts"))
    autofill_text = read_text("src/lib/autofillEngine.ts")
    autofill_analysis = {
        "lineCount": autofill["lineCount"],
        "imports": autofill["imports"],
        "exports": autofill["exports"],
        "runtimeConsumers": sorted(
            {
                row["feature"]
                for row in autofill["importedBy"]
                if row["runtimeOrTypeOnly"] == "runtime" and row["feature"] != "tmp"
            }
        ),
        "typeOnlyConsumers": sorted(
            {
                row["feature"]
                for row in autofill["importedBy"]
                if row["runtimeOrTypeOnly"] == "type-only" and row["feature"] != "tmp"
            }
        ),
        "historyStoreDependency": "historyStore" in autofill_text,
        "restoreProfileStoreDependency": "restoreProfileStore" in autofill_text,
        "bizNumberDependency": "bizNumber" in autofill_text,
        "profilesDependency": "profiles" in autofill_text,
        "runocrDependency": "runocr" in autofill["signals"]["mainConsumers"],
        "historyDependency": "history" in autofill["signals"]["mainConsumers"],
        "restoreDependency": "restore" in autofill["signals"]["mainConsumers"],
        "commonUtilsOcrResultFormattersTypeOnlyImportCanResolve": "Move autofillEngine only after historyStore/restoreProfileStore/bizNumber paths settle.",
        "commonUtilsReadiness": "Not yet",
        "commonStorageReadiness": "No: domain engine, not persistence store",
        "restoreUtilsReadiness": "No: consumed by RunOCR and History",
        "runocrUtilsReadiness": "No: consumed by History/detail and restore profile flow",
        "judgement": "DEFER_UNTIL_STORAGE_BOUNDARY",
        "moveRisk": "HIGH",
    }

    boundary_recommendation = {
        "recommendedBoundary": "src/common/storage/",
        "secondaryBoundary": "src/common/data/ only for pure data/profile definitions if needed",
        "notRecommended": ["src/common/persistence/ (longer name, less aligned with current simple tree)", "src/common/utils/ for browser persistence stores"],
        "reason": "historyStore, imageStore, groundTruthStore and restoreProfileStore are browser persistence modules using localStorage/IndexedDB. storage is clearer than utils/data and avoids feature-to-feature imports.",
        "decision": "INTRODUCE_COMMON_STORAGE_BOUNDARY",
    }

    boundary_options = [
        {
            "path": "src/common/storage/",
            "recommended": True,
            "meaning": "browser persistence: localStorage, IndexedDB, storage-backed stores",
            "risk": "MEDIUM",
            "notes": "Best fit for historyStore/imageStore and possible groundTruth/restoreProfileStore.",
        },
        {
            "path": "src/common/data/",
            "recommended": False,
            "meaning": "shared data models/static data, less explicit for browser storage",
            "risk": "MEDIUM",
            "notes": "Useful later for pure profile definitions, not primary store target.",
        },
        {
            "path": "src/common/persistence/",
            "recommended": False,
            "meaning": "technically accurate but heavier naming than current structure",
            "risk": "MEDIUM",
            "notes": "Could work, but storage is simpler and clearer.",
        },
        {
            "path": "src/common/utils/",
            "recommended": False,
            "meaning": "pure helpers/formatters",
            "risk": "MEDIUM_HIGH",
            "notes": "Already used for pure formatter/display utils; stores would muddy boundary.",
        },
        {
            "path": "src/lib 유지",
            "recommended": "temporary",
            "meaning": "defer while boundary is introduced",
            "risk": "CURRENT",
            "notes": "Safe short-term but does not complete cleanup.",
        },
    ]

    move_phases = [
        {"phase": "CS-0", "name": "common/storage boundary decision", "items": ["src/common/storage/"], "risk": "LOW", "notes": "precheck only in this task"},
        {"phase": "CS-1", "name": "imageStore common/storage move", "items": ["src/lib/imageStore.ts"], "risk": "MEDIUM_HIGH", "notes": "leaf-ish IndexedDB store, history/template consumers"},
        {"phase": "CS-2", "name": "historyStore common/storage move", "items": ["src/lib/historyStore.ts"], "risk": "HIGH", "notes": "after imageStore so sibling storage import is natural"},
        {"phase": "RS-1", "name": "restore/autorestore folder boundary", "items": ["src/components/autorestore/**"], "risk": "MEDIUM", "notes": "separate route/feature precheck"},
        {"phase": "RS-2", "name": "restoreProfileStore ownership", "items": ["src/lib/restoreProfileStore.ts"], "risk": "MEDIUM_HIGH", "notes": "restore/utils vs common/storage after restore boundary"},
        {"phase": "AF-1", "name": "autofillEngine separate precheck", "items": ["src/lib/autofillEngine.ts"], "risk": "HIGH", "notes": "after storage paths settle"},
        {"phase": "BZ-1", "name": "bizNumber common/utils precheck", "items": ["src/lib/bizNumber.ts"], "risk": "MEDIUM", "notes": "pure util candidate, check Test impact"},
        {"phase": "TEST-1", "name": "TestWorkspace-approved moves", "items": ["src/lib/groundTruthStore.ts", "src/lib/testsets.ts", "src/lib/profiles.ts"], "risk": "HIGH", "notes": "user approval before TestWorkspace structure changes"},
    ]

    static_check_plan = [
        "tmp/check_common_storage_boundary_cs0.mjs",
        "tmp/check_image_store_common_storage_move_cs1.mjs",
        "tmp/check_history_store_common_storage_move_cs2.mjs",
        "tmp/check_restore_profile_store_move_rs2.mjs",
        "tmp/check_autofill_engine_ownership_af1.mjs",
        "target 파일 존재/source 파일 부재/import path 정상",
        "common/storage가 components/*를 import하지 않음",
        "storage 파일과 common/utils 간 순환 없음",
        "TestWorkspace 미수정 또는 import-only 확인",
        "RunOCR/History/Template import path 정상",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]

    validation_plan = [
        "이번 precheck는 운영 코드 변경 없이 boundary 판단만 수행한다.",
        "실제 이동은 imageStore, historyStore 순서로 한 파일씩 진행한다.",
        "autofillEngine과 TestWorkspace 관련 store는 별도 precheck/승인 후 진행한다.",
    ]

    typecheck = command_result(TYPECHECK_RESULT, "npm run typecheck")
    build = command_result(BUILD_RESULT, "npm run build")
    dirty = git_status()

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "projectRoot": ".",
        "codeModified": False,
        "dirtyStatus": dirty,
        "files": files,
        "autofillEngineAnalysis": autofill_analysis,
        "dependencyGraph": graph,
        "boundaryRecommendation": boundary_recommendation,
        "boundaryOptions": boundary_options,
        "movePhases": move_phases,
        "staticCheckPlan": static_check_plan,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "Confirm src/common/storage as the shared browser persistence boundary.",
            "Run CS-1 imageStore common/storage move precheck/move.",
            "Run CS-2 historyStore common/storage move precheck/move.",
            "Defer autofillEngine until storage imports settle.",
            "Keep TestWorkspace-related files deferred until explicit approval.",
        ],
    }

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "currentPath",
                "role",
                "importedByCount",
                "mainConsumers",
                "dependencyOut",
                "dependencyIn",
                "recommendedOwner",
                "recommendedTarget",
                "risk",
                "testWorkspaceImpact",
                "movePhase",
                "notes",
            ],
        )
        writer.writeheader()
        for item in files:
            current = item["currentPath"]
            phase = next((p["phase"] for p in move_phases if current in p["items"]), "TBD")
            if current.endswith("imageStore.ts"):
                phase = "CS-1"
            elif current.endswith("historyStore.ts"):
                phase = "CS-2"
            elif current.endswith("restoreProfileStore.ts"):
                phase = "RS-2"
            elif current.endswith("autofillEngine.ts"):
                phase = "AF-1"
            elif current.endswith("bizNumber.ts"):
                phase = "BZ-1"
            elif current.endswith(("groundTruthStore.ts", "testsets.ts", "profiles.ts")):
                phase = "TEST-1"
            writer.writerow(
                {
                    "currentPath": current,
                    "role": item["role"],
                    "importedByCount": len([r for r in item["importedBy"] if r["runtimeOrTypeOnly"] != "reference"]),
                    "mainConsumers": ",".join(item["signals"]["mainConsumers"]),
                    "dependencyOut": ",".join(graph["outgoingEdges"].get(current, [])),
                    "dependencyIn": ",".join(graph["reverseEdges"].get(current, [])),
                    "recommendedOwner": item["recommendation"]["owner"],
                    "recommendedTarget": item["recommendation"]["target"],
                    "risk": item["risk"],
                    "testWorkspaceImpact": item["testWorkspaceImpact"],
                    "movePhase": phase,
                    "notes": item["recommendation"]["reason"],
                }
            )

    file_rows = "\n".join(
        f"| {item['currentPath']} | {item['recommendation']['owner']} | {item['recommendation']['target']} | {item['risk']} | {item['testWorkspaceImpact']} |"
        for item in files
    )
    graph_rows = "\n".join(
        f"- {edge['from']} -> {edge['to']} ({'type-only' if edge['typeOnly'] else 'runtime'}, {edge['source']})"
        for edge in graph["edges"]
    ) or "- 내부 대상 파일 간 edge 없음"
    dirty_text = "\n".join(dirty) if dirty else "(clean)"

    md = f"""# FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/rename/import 수정: 없음
- fixture/templates/backend 수정: 없음
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- tmp/codex_frontend_common_storage_boundary_precheck.py
- docs/FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_20260522.md
- docs/FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_20260522.json
- docs/FRONTEND_COMMON_STORAGE_BOUNDARY_MAP_20260522.csv

## 4. 분석 범위
- src/lib/historyStore.ts
- src/lib/imageStore.ts
- src/lib/autofillEngine.ts
- src/lib/groundTruthStore.ts
- src/lib/restoreProfileStore.ts
- src/lib/profiles.ts
- src/lib/bizNumber.ts
- src/lib/testsets.ts
- src/components/runocr/**
- src/components/history/**
- src/components/autorestore/**
- src/components/restore/**
- src/components/template/**
- src/components/test/TestWorkspace.tsx
- src/components/test/core/**
- src/common/**
- src/app/**

## 5. storage/data 후보 파일 역할 분석
| 파일 | 추천 owner | 추천 target | 위험 | TestWorkspace 영향 |
| --- | --- | --- | --- | --- |
{file_rows}

## 6. autofillEngine 특별 분석
- 판정: {autofill_analysis['judgement']}
- moveRisk: {autofill_analysis['moveRisk']}
- historyStore 의존: {autofill_analysis['historyStoreDependency']}
- restoreProfileStore 의존: {autofill_analysis['restoreProfileStoreDependency']}
- bizNumber 의존: {autofill_analysis['bizNumberDependency']}
- common/storage 적합성: {autofill_analysis['commonStorageReadiness']}
- common/utils 적합성: {autofill_analysis['commonUtilsReadiness']}
- restore/utils 적합성: {autofill_analysis['restoreUtilsReadiness']}
- runocr/utils 적합성: {autofill_analysis['runocrUtilsReadiness']}
- 결론: storage boundary가 먼저 정리된 뒤 별도 precheck로 이동 여부를 판단한다.

## 7. importedBy/dependency graph
### dependency edges
{graph_rows}

### graph risk
- cycleRisk: {graph['cycleRisk']}
- sharedBoundaryRisk: {graph['sharedBoundaryRisk']}
- featureDependencyRisk: {graph['featureDependencyRisk']}

## 8. common/storage vs common/data 판단
- 추천 boundary: src/common/storage/
- 이유: localStorage/IndexedDB/browser persistence 책임이 있는 파일을 common/utils와 분리하면서 feature 간 의존을 줄인다.
- src/common/data/는 순수 data/model 정의에는 가능하지만 historyStore/imageStore 같은 persistence store에는 덜 명확하다.
- src/common/utils/는 formatter/display/pure helper 중심으로 유지하는 것이 좋다.

## 9. 파일별 target 추천
- historyStore.ts -> src/common/storage/historyStore.ts 후보
- imageStore.ts -> src/common/storage/imageStore.ts 후보
- restoreProfileStore.ts -> restore boundary 확정 후 components/restore/utils 또는 common/storage 재판단
- profiles.ts -> Test/restore 영향 확인 후 보류 또는 common/data/components/restore/utils
- groundTruthStore.ts -> TestWorkspace 정책상 보류 또는 common/storage 별도 precheck
- testsets.ts -> TestWorkspace 승인 전 보류
- bizNumber.ts -> src/common/utils/bizNumber.ts 별도 precheck
- autofillEngine.ts -> storage boundary 이후 별도 precheck

## 10. TestWorkspace 영향
- historyStore: {test_impact_for('src/lib/historyStore.ts', next(i for i in files if i['currentPath'] == 'src/lib/historyStore.ts')['importedBy'])}
- imageStore: {test_impact_for('src/lib/imageStore.ts', next(i for i in files if i['currentPath'] == 'src/lib/imageStore.ts')['importedBy'])}
- autofillEngine: {test_impact_for('src/lib/autofillEngine.ts', next(i for i in files if i['currentPath'] == 'src/lib/autofillEngine.ts')['importedBy'])}
- groundTruthStore: {test_impact_for('src/lib/groundTruthStore.ts', next(i for i in files if i['currentPath'] == 'src/lib/groundTruthStore.ts')['importedBy'])}
- restoreProfileStore: {test_impact_for('src/lib/restoreProfileStore.ts', next(i for i in files if i['currentPath'] == 'src/lib/restoreProfileStore.ts')['importedBy'])}
- profiles: {test_impact_for('src/lib/profiles.ts', next(i for i in files if i['currentPath'] == 'src/lib/profiles.ts')['importedBy'])}
- testsets: {test_impact_for('src/lib/testsets.ts', next(i for i in files if i['currentPath'] == 'src/lib/testsets.ts')['importedBy'])}
- bizNumber: {test_impact_for('src/lib/bizNumber.ts', next(i for i in files if i['currentPath'] == 'src/lib/bizNumber.ts')['importedBy'])}

## 11. 이동 순서 추천
{chr(10).join(f"- {p['phase']}: {p['name']} ({', '.join(p['items'])}) - {p['notes']}" for p in move_phases)}

## 12. static check 설계
{chr(10).join(f"- {item}" for item in static_check_plan)}

## 13. dirty 상태
```text
{dirty_text}
```

## 14. typecheck/build 결과
- typecheck: {typecheck.get('status')} (exitCode={typecheck.get('exitCode')})
- build: {build.get('status')} (exitCode={build.get('exitCode')})
- known stderr noise: ESLint nextVitals is not iterable은 exit code 0이면 known issue로 기록.

## 15. 다음 작업 제안
- src/common/storage boundary를 도입하는 방향을 확정한다.
- 첫 move는 imageStore -> common/storage가 가장 자연스럽다.
- 그 다음 historyStore -> common/storage를 진행한다.
- autofillEngine과 TestWorkspace 관련 파일은 별도 precheck/승인 후 진행한다.
"""
    MD_PATH.write_text(md, encoding="utf-8")

    print(f"Wrote {MD_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Wrote {JSON_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Wrote {CSV_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print("Recommendation: INTRODUCE_COMMON_STORAGE_BOUNDARY")
    print(f"typecheck={typecheck.get('status')} build={build.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
