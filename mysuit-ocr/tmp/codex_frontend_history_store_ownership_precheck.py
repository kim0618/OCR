import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

MD_PATH = DOCS_DIR / "FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_20260522.md"
JSON_PATH = DOCS_DIR / "FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_20260522.json"
CSV_PATH = DOCS_DIR / "FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_MAP_20260522.csv"

TYPECHECK_RESULT = PROJECT_ROOT / "tmp" / "codex_history_store_ownership_precheck_typecheck.json"
BUILD_RESULT = PROJECT_ROOT / "tmp" / "codex_history_store_ownership_precheck_build.json"

TARGET_REL = "src/lib/historyStore.ts"
TARGET = PROJECT_ROOT / TARGET_REL


def read_text(path: Path, encoding: str = "utf-8") -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding=encoding, errors="replace")


def line_count(path: Path) -> int:
    text = read_text(path)
    return len(text.splitlines()) if text else 0


def parse_imports(text: str) -> list[dict]:
    rows = []
    for match in re.finditer(r"import\s+([\s\S]*?)\s+from\s+['\"]([^'\"]+)['\"]", text):
        raw_symbols = " ".join(match.group(1).split())
        rows.append(
            {
                "symbols": raw_symbols,
                "source": match.group(2),
                "typeOnly": raw_symbols.startswith("type ") or raw_symbols == "type",
            }
        )
    for match in re.finditer(r"import\s+['\"]([^'\"]+)['\"]", text):
        rows.append({"symbols": "(side-effect)", "source": match.group(1), "typeOnly": False})
    return rows


def parse_exports(text: str) -> list[dict]:
    rows = []
    for match in re.finditer(
        r"export\s+(?:(type|interface|function|const|class)\s+([A-Za-z0-9_]+)|default\s+function\s+([A-Za-z0-9_]+))",
        text,
    ):
        kind = match.group(1) or "default function"
        name = match.group(2) or match.group(3)
        rows.append({"kind": kind, "name": name})
    return rows


def run_rg(pattern: str, paths: list[str]) -> list[dict]:
    cmd = ["rg", "-n", "--hidden", "--glob", "!node_modules", pattern, *paths]
    proc = subprocess.run(
        cmd,
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


def feature_for(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("src/components/runocr/") or p.startswith("src/app/runocr/") or p == "src/app/ocr/page.tsx":
        return "runocr"
    if p.startswith("src/components/history/") or p.startswith("src/app/history/"):
        return "history"
    if p.startswith("src/components/autorestore/") or p.startswith("src/components/restore/"):
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


def imported_symbols_from_line(text: str) -> str:
    if "import" not in text:
        return ""
    match = re.search(r"import\s+(.+?)\s+from\s+['\"]", text)
    return " ".join(match.group(1).split()) if match else ""


def is_type_only_import(text: str) -> bool:
    if "import type" in text:
        return True
    return bool(re.search(r"import\s+\{[^}]*\btype\b", text))


def command_result(path: Path, command: str) -> dict:
    if not path.exists():
        return {"command": command, "status": "NOT_RUN", "exitCode": None}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"command": command, "status": "UNKNOWN", "exitCode": None, "raw": read_text(path)}


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


def main() -> int:
    src = read_text(TARGET)
    imports = parse_imports(src)
    exports = parse_exports(src)

    patterns = [
        "historyStore",
        "../lib/historyStore",
        "../../lib/historyStore",
        "@/lib/historyStore",
        "./historyStore",
        "appendHistoryRun",
        "updateHistoryRun",
        "listHistoryRuns",
        "readHistoryRuns",
        "readHistoryListWithFallback",
        "readHistoryDetailWithFallback",
        "getHistoryRun",
        "deleteHistoryRun",
        "clearHistoryRuns",
        "hydrateHistoryRecordImages",
        "syncHistoryIndexAndDetailOnCreate",
        "syncHistoryIndexAndDetailOnSave",
        "syncHistoryDetailTableRowsOnSave",
    ]
    hits = []
    seen = set()
    for pattern in patterns:
        for row in run_rg(pattern, ["src", "tmp"]):
            key = (row.get("file"), row.get("line"), row.get("text"))
            if key in seen:
                continue
            seen.add(key)
            hits.append(row)

    imported_by = []
    for row in hits:
        file = row.get("file", "")
        if file == TARGET_REL:
            continue
        text = row.get("text", "")
        imported_by.append(
            {
                "file": file,
                "line": row.get("line"),
                "importPath": text if "import" in text else "(reference)",
                "importedSymbols": imported_symbols_from_line(text),
                "feature": feature_for(file),
                "runtimeOrTypeOnly": "type-only" if is_type_only_import(text) else ("runtime" if "import" in text else "reference"),
                "needsImportUpdateOnMove": "@/lib/historyStore" in text
                or "../lib/historyStore" in text
                or "../../lib/historyStore" in text
                or "./historyStore" in text,
                "testWorkspaceImpact": file.startswith("src/components/test/"),
                "tmpReference": file.startswith("tmp/"),
            }
        )

    production_imports = [row for row in imported_by if row["feature"] != "tmp" and row["importPath"] != "(reference)"]
    runtime_features = sorted({row["feature"] for row in production_imports if row["runtimeOrTypeOnly"] == "runtime"})

    role = {
        "mainResponsibility": "Browser-side OCR history persistence store: legacy run list, index/detail records, image hydration, append/update/delete/clear and sync helpers.",
        "isStore": True,
        "localStorageIndexedDBUse": True,
        "browserApiUse": True,
        "backendApiUse": False,
        "reactDependency": False,
        "componentsDependency": False,
        "historyOnly": False,
        "runocrSaveFlowRelation": "RunOCR calls appendHistoryRun/updateHistoryRun/syncHistoryIndexAndDetailOnCreate at runtime after OCR execution.",
        "detailHistoryViewRelation": "DetailHistoryView imports HistoryRunRecord/HistoryOutputField/updateHistoryRun and sync helpers for detail save/edit flows.",
        "historyWorkspaceRelation": "HistoryWorkspace reads list/detail, hydrates images, deletes and clears history.",
        "imageStoreRelation": "historyStore imports imageStore runtime helpers for IndexedDB image save/get/delete.",
        "restoreProfileStoreRelation": "No direct import from historyStore; DetailHistoryView combines historyStore with restoreProfileStore.",
        "autofillEngineRelation": "autofillEngine imports readHistoryRuns at runtime and HistoryOutputField as a type.",
        "testWorkspaceImpact": "No direct TestWorkspace import found.",
    }

    dependency_impact = {
        "historyStoreImportsImageStore": './imageStore' in src or '"./imageStore"' in src,
        "historyStoreImportsRestoreProfileStore": "restoreProfileStore" in src,
        "historyStoreImportsAutofillEngine": "autofillEngine" in src,
        "historyStoreImportsCommonUtils": "@/common/utils" in src or "../common/" in src,
        "libFilesImportHistoryStore": [
            row for row in production_imports if row["feature"] == "lib"
        ],
        "componentFilesImportHistoryStore": [
            row for row in production_imports if row["feature"] in {"runocr", "history", "restore", "template", "test"}
        ],
        "cycleRiskIfMovedToHistoryUtils": "MEDIUM_HIGH",
        "notes": [
            "Moving only historyStore to components/history/utils makes src/lib/autofillEngine import a feature-owned module at runtime.",
            "RunOCR would import components/history/utils at runtime to persist OCR results.",
            "historyStore itself depends on imageStore, which is still shared by history and template image helpers.",
        ],
    }

    test_workspace_impact = {
        "classification": "NO_TEST_IMPACT",
        "testWorkspaceDirectImport": any(row["file"] == "src/components/test/TestWorkspace.tsx" and row["importPath"] != "(reference)" for row in imported_by),
        "testCoreDirectImport": any(row["file"].startswith("src/components/test/core/") and row["importPath"] != "(reference)" for row in imported_by),
        "tmpRunnerReferences": [row for row in imported_by if row["tmpReference"]],
        "needsTestWorkspaceModificationOnMove": False,
    }

    target_candidates = [
        {
            "target": "src/components/history/utils/historyStore.ts",
            "pros": ["History UI/route ownership naming is clear.", "HistoryWorkspace and DetailHistoryView imports become feature-local."],
            "cons": [
                "RunOCR would import a history feature module at runtime.",
                "src/lib/autofillEngine would import components/history/utils at runtime unless moved first.",
                "imageStore remains outside and shared, so store ownership is only partially resolved.",
            ],
            "featureDependencyRisk": "HIGH",
            "importScope": "RunOCR, HistoryWorkspace, DetailHistoryView, autofillEngine, groundTruthStore type import, static checks",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": False,
        },
        {
            "target": "src/common/utils/historyStore.ts",
            "pros": ["Avoids components/runocr -> components/history feature dependency.", "Existing alias imports can become common-owned shared util imports."],
            "cons": [
                "Stateful browser persistence store is heavier than typical formatter/common utils.",
                "Would still need imageStore ownership decision.",
            ],
            "featureDependencyRisk": "LOW_MEDIUM",
            "importScope": "RunOCR, History, lib/autofillEngine, lib/groundTruthStore type import, static checks",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": False,
        },
        {
            "target": "src/common/storage/historyStore.ts or src/common/data/historyStore.ts",
            "pros": [
                "Best semantic fit for shared browser persistence.",
                "Keeps RunOCR/History/autofill consumers depending on common, not on another feature.",
                "Can later colocate or separately classify imageStore and related persistence helpers.",
            ],
            "cons": [
                "Requires introducing a new common storage/data boundary not yet present in the current target tree.",
                "Needs separate boundary/static check before move.",
            ],
            "featureDependencyRisk": "LOW",
            "importScope": "RunOCR, History, lib/autofillEngine, lib/groundTruthStore type import, static checks",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": True,
        },
        {
            "target": "src/lib 유지",
            "pros": ["No immediate feature dependency regression.", "Avoids moving a high-risk shared store before storage boundary is decided."],
            "cons": ["Leaves src/lib cleanup incomplete.", "Current lib ownership ambiguity remains."],
            "featureDependencyRisk": "CURRENT_STATE",
            "importScope": "none",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": True,
        },
        {
            "target": "보류",
            "pros": ["Allows imageStore/autofillEngine/common storage decision first."],
            "cons": ["History cleanup phase does not progress immediately."],
            "featureDependencyRisk": "LOW",
            "importScope": "none",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": True,
        },
    ]

    recommendation = {
        "choice": "D",
        "summary": "Do not move historyStore directly to components/history/utils yet. Defer or first define common storage/data boundary.",
        "risk": "HIGH",
        "reason": "historyStore is runtime-shared by RunOCR, History and autofillEngine. A direct history/utils move would make RunOCR and src/lib/autofillEngine depend on a history feature module.",
        "preferredFuturePath": "src/common/storage/historyStore.ts or src/common/data/historyStore.ts after a dedicated common storage boundary precheck",
        "notRecommendedNow": "src/components/history/utils/historyStore.ts",
    }

    static_check_plan = [
        "tmp/check_history_store_move_hr3.mjs",
        "target 파일 존재 및 source 파일 부재 확인",
        "historyStore exports 유지 확인",
        "RunOCR/History/autofillEngine/groundTruthStore import path 정상 확인",
        "components/runocr가 components/history/utils를 import하지 않음 확인, 또는 의도된 예외로 명시",
        "src/lib/autofillEngine이 components/history/utils를 runtime import하지 않음 확인",
        "TestWorkspace 미수정 또는 import-only 영향 없음 확인",
        "imageStore/restoreProfileStore/autofillEngine 미수정 확인",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]

    validation_plan = [
        "이번 precheck에서는 운영 코드 수정 없이 ownership만 기록한다.",
        "historyStore 단독 move를 진행한다면 common storage/data boundary precheck를 먼저 수행한다.",
        "imageStore와 묶지 않고, RunOCR adapter 분리도 이번 move와 묶지 않는다.",
    ]

    typecheck = command_result(TYPECHECK_RESULT, "npm run typecheck")
    build = command_result(BUILD_RESULT, "npm run build")
    dirty = git_status()

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "projectRoot": ".",
        "codeModified": False,
        "dirtyStatus": dirty,
        "file": {
            "currentPath": TARGET_REL,
            "lineCount": line_count(TARGET),
            "imports": imports,
            "exports": exports,
            "importedBy": imported_by,
            "role": role,
            "targetCandidates": target_candidates,
            "recommendation": recommendation,
            "risk": "HIGH",
            "testWorkspaceImpact": test_workspace_impact,
        },
        "dependencyImpact": dependency_impact,
        "featureDependencyRisk": {
            "runtimeConsumers": runtime_features,
            "componentsHistoryUtilsMoveRisk": "HIGH",
            "commonStorageMoveRisk": "MEDIUM",
            "currentRisk": "HIGH ownership ambiguity, but no new feature dependency",
        },
        "staticCheckPlan": static_check_plan,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "common storage/data boundary precheck for historyStore and imageStore",
            "or keep src/lib/historyStore.ts until autofillEngine/imageStore ownership is settled",
            "do not move historyStore to components/history/utils as a standalone micro-step",
        ],
    }

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "file",
                "line",
                "feature",
                "runtimeOrTypeOnly",
                "importPath",
                "importedSymbols",
                "needsImportUpdateOnMove",
                "testWorkspaceImpact",
                "tmpReference",
            ],
        )
        writer.writeheader()
        writer.writerows(imported_by)

    prod_summary = "\n".join(
        f"- {row['file']}:{row['line']} [{row['feature']}, {row['runtimeOrTypeOnly']}] {row['importPath']}"
        for row in production_imports
    )
    export_summary = ", ".join(f"{row['kind']} {row['name']}" for row in exports)
    dirty_text = "\n".join(dirty) if dirty else "(clean)"

    md = f"""# FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/rename/import 수정: 없음
- fixture/templates/backend 수정: 없음
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- tmp/codex_frontend_history_store_ownership_precheck.py
- docs/FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_20260522.md
- docs/FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_20260522.json
- docs/FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_MAP_20260522.csv

## 4. 분석 범위
- src/lib/historyStore.ts
- src/lib/imageStore.ts
- src/lib/restoreProfileStore.ts
- src/lib/autofillEngine.ts
- src/lib/profiles.ts
- src/components/history/**
- src/components/runocr/**
- src/components/autorestore/**
- src/components/restore/**
- src/app/history/**
- src/app/runocr/**
- src/components/test/TestWorkspace.tsx
- src/components/test/core/**
- src/common/**

## 5. historyStore 역할 요약
- currentPath: {TARGET_REL}
- lineCount: {line_count(TARGET)}
- imports: {json.dumps(imports, ensure_ascii=False)}
- exports: {export_summary}
- mainResponsibility: browser-side OCR history persistence store. legacy list, index/detail records, append/update/delete/clear, image hydration, sync helpers를 제공한다.
- 저장소 성격: YES
- localStorage/IndexedDB/browser API: YES
- backend/API: NO
- React 의존: NO
- components/* 의존: NO
- History 전용성: NO. History 화면뿐 아니라 RunOCR 저장 흐름과 autofill 후보 수집에서 runtime으로 공유된다.
- moveRisk: HIGH

## 6. importedBy 분석
{prod_summary if prod_summary else "- production import 없음"}

주요 production consumer:
- RunOCR: appendHistoryRun, updateHistoryRun, syncHistoryIndexAndDetailOnCreate 및 History type들을 runtime/type으로 사용한다.
- HistoryWorkspace: list/detail read, delete/clear, image hydration을 사용한다.
- DetailHistoryView: updateHistoryRun, syncHistoryDetailTableRowsOnSave, syncHistoryIndexAndDetailOnSave 및 History type들을 사용한다.
- autofillEngine: readHistoryRuns를 runtime으로 import한다.
- groundTruthStore: HistoryOutputField를 type-only로 import한다.

## 7. dependency 영향
- historyStore -> imageStore runtime import: {dependency_impact['historyStoreImportsImageStore']}
- historyStore -> restoreProfileStore direct import: {dependency_impact['historyStoreImportsRestoreProfileStore']}
- historyStore -> autofillEngine direct import: {dependency_impact['historyStoreImportsAutofillEngine']}
- historyStore -> common/utils direct import: {dependency_impact['historyStoreImportsCommonUtils']}
- 순환 의존 가능성: direct cycle은 없지만, history/utils로 이동하면 src/lib/autofillEngine -> components/history/utils runtime import가 생겨 boundary 위험이 커진다.
- RunOCR가 history 저장을 위해 historyStore를 runtime 사용하므로, components/history/utils로 이동하면 components/runocr -> components/history/utils feature dependency가 생긴다.

## 8. TestWorkspace 영향
- 판정: {test_workspace_impact['classification']}
- TestWorkspace 직접 import: {test_workspace_impact['testWorkspaceDirectImport']}
- test/core 직접 import: {test_workspace_impact['testCoreDirectImport']}
- 이동 시 TestWorkspace 수정 필요: {test_workspace_impact['needsTestWorkspaceModificationOnMove']}

## 9. target path 비교
| 후보 | 추천 | 장점 | 단점 | feature dependency risk |
| --- | --- | --- | --- | --- |
| src/components/history/utils/historyStore.ts | NO | History UI/route와 이름상 맞음 | RunOCR/autofillEngine이 history feature를 runtime import | HIGH |
| src/common/utils/historyStore.ts | NO | feature dependency는 줄어듦 | stateful persistence store라 utils 의미가 약함 | LOW_MEDIUM |
| src/common/storage/historyStore.ts 또는 src/common/data/historyStore.ts | YES, 별도 precheck 후 | shared persistence boundary로 가장 자연스러움 | 새 common boundary 설계 필요 | LOW |
| src/lib 유지 | YES, 당장 유지 후보 | 새 feature dependency를 만들지 않음 | src/lib 정리 지연 | CURRENT |
| 보류 | YES | imageStore/autofillEngine ownership 정리 후 판단 가능 | 즉시 이동 없음 | LOW |

## 10. 실제 이동 추천
- 추천 선택지: D. 이동 보류
- 대안: B. common storage/data 계층을 별도 precheck로 먼저 정의한 뒤 이동
- 비추천: A. historyStore.ts만 src/components/history/utils/historyStore.ts로 이동
- 이유: 단독 history/utils 이동은 RunOCR와 src/lib/autofillEngine에 history feature dependency를 만든다.
- imageStore와 묶지 않고, RunOCR history adapter 분리도 이번 작업에 묶지 않는다.

## 11. static check 설계
{chr(10).join(f"- {item}" for item in static_check_plan)}

## 12. dirty 상태
```text
{dirty_text}
```

## 13. typecheck/build 결과
- typecheck: {typecheck.get('status')} (exitCode={typecheck.get('exitCode')})
- build: {build.get('status')} (exitCode={build.get('exitCode')})
- known stderr noise: ESLint nextVitals is not iterable은 exit code 0이면 known issue로 기록.

## 14. 다음 작업 제안
- common storage/data boundary precheck를 먼저 수행한다.
- historyStore/imageStore/autofillEngine의 공유 저장소 경계를 함께 검토하되 실제 move는 한 파일씩 진행한다.
- Template table column definition 진입 전에는 historyStore를 무리하게 history/utils로 옮기지 않는 편이 안전하다.
"""
    MD_PATH.write_text(md, encoding="utf-8")

    print(f"Wrote {MD_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Wrote {JSON_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Wrote {CSV_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print("Recommendation: DEFER_DIRECT_HISTORY_UTILS_MOVE")
    print(f"typecheck={typecheck.get('status')} build={build.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
