import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

MD_PATH = DOCS_DIR / "FRONTEND_AUTORESTORE_TO_RESTORE_PRECHECK_20260522.md"
JSON_PATH = DOCS_DIR / "FRONTEND_AUTORESTORE_TO_RESTORE_PRECHECK_20260522.json"
CSV_PATH = DOCS_DIR / "FRONTEND_AUTORESTORE_TO_RESTORE_MAP_20260522.csv"

TYPECHECK_RESULT = PROJECT_ROOT / "tmp" / "codex_autorestore_to_restore_precheck_typecheck.json"
BUILD_RESULT = PROJECT_ROOT / "tmp" / "codex_autorestore_to_restore_precheck_build.json"

TARGET_REL = "src/components/autorestore/AutoRestoreWorkspace.tsx"
ROUTE_REL = "src/app/autorestore/page.tsx"
TARGET_KEEP_NAME = "src/components/restore/AutoRestoreWorkspace.tsx"
TARGET_RENAME = "src/components/restore/RestoreWorkspace.tsx"


def read_rel(rel: str) -> str:
    path = PROJECT_ROOT / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def exists_rel(rel: str) -> bool:
    return (PROJECT_ROOT / rel).exists()


def line_count(rel: str) -> int:
    text = read_rel(rel)
    return len(text.splitlines()) if text else 0


def parse_imports(text: str) -> list[dict]:
    rows = []
    for match in re.finditer(r"import\s+([\s\S]*?)\s+from\s+['\"]([^'\"]+)['\"]", text):
        symbols = " ".join(match.group(1).split())
        rows.append({"symbols": symbols, "source": match.group(2), "typeOnly": symbols.startswith("type ")})
    for match in re.finditer(r"import\s+['\"]([^'\"]+)['\"]", text):
        rows.append({"symbols": "(side-effect)", "source": match.group(1), "typeOnly": False})
    return rows


def parse_exports(text: str) -> list[dict]:
    rows = []
    pattern = r"export\s+(?:(type|interface|function|const|class)\s+([A-Za-z0-9_]+)|default\s+function\s+([A-Za-z0-9_]+))"
    for match in re.finditer(pattern, text):
        rows.append({"kind": match.group(1) or "default function", "name": match.group(2) or match.group(3)})
    return rows


def rg(pattern: str, roots: list[str]) -> list[dict]:
    proc = subprocess.run(
        ["rg", "-n", "--hidden", "--glob", "!node_modules", pattern, *roots],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode not in (0, 1):
        return [{"pattern": pattern, "error": proc.stderr.strip()}]
    rows = []
    for line in proc.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            rows.append({"file": parts[0].replace("\\", "/"), "line": int(parts[1]), "text": parts[2].strip()})
    return rows


def feature_for(file: str) -> str:
    p = file.replace("\\", "/")
    if p.startswith("src/app/"):
        return "app"
    if p.startswith("src/components/autorestore/"):
        return "autorestore"
    if p.startswith("src/components/restore/"):
        return "restore"
    if p.startswith("src/components/runocr/"):
        return "runocr"
    if p.startswith("src/components/history/"):
        return "history"
    if p.startswith("src/components/test/"):
        return "test"
    if p.startswith("src/common/"):
        return "common"
    if p.startswith("tmp/"):
        return "tmp"
    return "unknown"


def import_symbols(line: str) -> str:
    match = re.search(r"import\s+(.+?)\s+from\s+['\"]", line)
    return " ".join(match.group(1).split()) if match else ""


def imported_by() -> list[dict]:
    keys = [
        "AutoRestoreWorkspace",
        "components/autorestore",
        "@/components/autorestore",
        "../components/autorestore",
        "../../components/autorestore",
        "components/restore",
        "RestoreWorkspace",
    ]
    rows = []
    seen = set()
    for key in keys:
        for hit in rg(key, ["src", "tmp"]):
            ident = (hit.get("file"), hit.get("line"), hit.get("text"))
            if ident in seen:
                continue
            seen.add(ident)
            if hit.get("file") == TARGET_REL:
                continue
            text = hit.get("text", "")
            rows.append(
                {
                    "file": hit.get("file"),
                    "line": hit.get("line"),
                    "importPath": text if "import" in text else "(reference)",
                    "importedSymbols": import_symbols(text),
                    "feature": feature_for(hit.get("file", "")),
                    "staticOrDynamicImport": "dynamic" if "dynamic(" in text or "import(" in text else ("static" if "import" in text else "reference"),
                    "needsImportUpdateOnMove": "components/autorestore" in text or "../../components/autorestore" in text or "../components/autorestore" in text,
                    "testWorkspaceImpact": hit.get("file", "").startswith("src/components/test/"),
                    "tmpReference": hit.get("file", "").startswith("tmp/"),
                }
            )
    return rows


def command_result(path: Path, command: str) -> dict:
    if not path.exists():
        return {"command": command, "status": "NOT_RUN", "exitCode": None}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
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


def main() -> int:
    target_text = read_rel(TARGET_REL)
    route_text = read_rel(ROUTE_REL)
    imports = parse_imports(target_text)
    exports = parse_exports(target_text)
    used_by = imported_by()
    prod_imports = [row for row in used_by if row["feature"] != "tmp" and row["importPath"] != "(reference)"]

    role = {
        "mainResponsibility": "Restore/autofill profile management workspace. Lists saved restore profiles, shows profile details, and deletes restore profiles.",
        "restoreProfileManagement": True,
        "autofillProfileManagement": True,
        "restoreProfileStoreDependency": "@/lib/restoreProfileStore" in target_text,
        "profilesDependency": "@/lib/profiles" in target_text,
        "autofillEngineDependency": "@/lib/autofillEngine" in target_text,
        "historyStoreCommonStorageDependency": "@/common/storage/historyStore" in target_text or "historyStore" in target_text,
        "appProvidersUseUiDependency": "useUi" in target_text and "AppProviders" in target_text,
        "requireLoginDependency": "RequireLogin" in target_text,
        "localStorageIndexedDBDirectUse": "localStorage" in target_text or "indexedDB" in target_text,
        "reactStateEffectUse": "useState" in target_text or "useEffect" in target_text,
        "browserApiUse": "window" in target_text or "document" in target_text or "localStorage" in target_text,
        "componentsDependency": "@/components/" in target_text or "../" in target_text,
        "testWorkspaceImpact": any(row["testWorkspaceImpact"] for row in used_by),
        "moveRisk": "MEDIUM",
    }

    route_impact = {
        "routePath": "/autorestore",
        "routeFile": ROUTE_REL,
        "routeKeepsUrl": True,
        "currentImport": "import AutoRestoreWorkspace from \"../../components/autorestore/AutoRestoreWorkspace\";" in route_text,
        "currentImportPath": "../../components/autorestore/AutoRestoreWorkspace",
        "targetImportIfKeepName": "../../components/restore/AutoRestoreWorkspace",
        "targetImportIfRename": "../../components/restore/RestoreWorkspace",
        "dynamicImport": "dynamic(" in route_text or "import(" in route_text,
        "routePolicyChangeNeeded": False,
        "notes": "Route URL /autorestore and AppShell title Restore can remain unchanged; only component import path changes in move step.",
    }

    dependency_impact = {
        "importsRestoreProfileStore": role["restoreProfileStoreDependency"],
        "importsProfiles": role["profilesDependency"],
        "importsAutofillEngine": role["autofillEngineDependency"],
        "importsHistoryStoreCommonStorage": role["historyStoreCommonStorageDependency"],
        "importsUseUi": role["appProvidersUseUiDependency"],
        "requireLoginRelation": "Route page wraps workspace with RequireLogin; workspace itself does not import RequireLogin.",
        "relativeImportChangeNeeded": "../layout/AppProviders becomes ../layout/AppProviders if moved to components/restore (same depth); no change needed for this relative import.",
        "aliasImportsMostlyUnaffected": True,
        "cycleRisk": "LOW",
        "notes": "Workspace imports restoreProfileStore only among restore domain stores; it does not directly import common/storage historyStore/imageStore.",
    }

    test_workspace_impact = {
        "classification": "NO_TEST_IMPACT",
        "testWorkspaceDirectImport": any(row["file"] == "src/components/test/TestWorkspace.tsx" and row["importPath"] != "(reference)" for row in used_by),
        "testCoreDirectImport": any(row["file"].startswith("src/components/test/core/") and row["importPath"] != "(reference)" for row in used_by),
        "indirectViaStores": "restoreProfileStore/profiles/autofillEngine remain unmoved in recommended step",
        "needsTestWorkspaceModificationOnMove": False,
    }

    target_candidates = [
        {
            "target": TARGET_KEEP_NAME,
            "pros": [
                "Folder owner becomes restore while component symbol/file name stays stable.",
                "Route import path-only change is small.",
                "Avoids mixing folder move with component rename.",
            ],
            "cons": ["AutoRestoreWorkspace name remains more specific than folder domain."],
            "importScope": [ROUTE_REL, "static checks/tmp references"],
            "routeImpact": "No URL change; import path only.",
            "renameRisk": "LOW",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": True,
        },
        {
            "target": TARGET_RENAME,
            "pros": ["File name aligns with broader restore domain and AppShell title Restore."],
            "cons": [
                "Requires file move + filename rename + default function/local symbol/import symbol rename decision.",
                "Larger micro-step than needed for folder ownership cleanup.",
            ],
            "importScope": [ROUTE_REL, "component symbol/file references", "static checks/tmp references"],
            "routeImpact": "No URL change if route file import is updated.",
            "renameRisk": "MEDIUM",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": False,
        },
        {
            "target": TARGET_REL,
            "pros": ["No import changes."],
            "cons": ["components/autorestore folder remains outside target feature structure."],
            "importScope": [],
            "routeImpact": "No change.",
            "renameRisk": "NONE",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": False,
        },
        {
            "target": "보류",
            "pros": ["Immediate risk avoided."],
            "cons": ["restore/autorestore structure issue remains."],
            "importScope": [],
            "routeImpact": "No change.",
            "renameRisk": "NONE",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": False,
        },
    ]

    recommendation = {
        "choice": "A",
        "summary": "Move AutoRestoreWorkspace.tsx to src/components/restore/AutoRestoreWorkspace.tsx and update src/app/autorestore/page.tsx import path only.",
        "restoreFeatureReadiness": "RESTORE_FEATURE_READY_KEEP_FILENAME",
        "risk": "MEDIUM",
        "reason": "Workspace is restore profile management UI. Keeping filename avoids bundling rename/symbol churn into folder ownership cleanup.",
        "deferRename": "Consider RestoreWorkspace.tsx as a later micro-step if broader restore page semantics are desired.",
        "doNotBundle": ["route URL change", "restoreProfileStore move", "autofillEngine move", "TestWorkspace changes"],
    }

    static_check_plan = [
        "tmp/check_autorestore_workspace_restore_move_rs1.mjs",
        "src/components/restore/AutoRestoreWorkspace.tsx 존재",
        "src/components/autorestore/AutoRestoreWorkspace.tsx 부재",
        "src/app/autorestore/page.tsx import path가 ../../components/restore/AutoRestoreWorkspace인지 확인",
        "route URL /autorestore 변경 없음 확인",
        "restoreProfileStore/profiles/autofillEngine/common/storage 미수정 확인",
        "TestWorkspace 미수정 확인",
        "src/components/autorestore 폴더 absent/empty 확인",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]

    validation_plan = [
        "실제 move 단계에서는 route URL을 변경하지 않는다.",
        "AutoRestoreWorkspace 파일명과 default component symbol은 유지한다.",
        "restoreProfileStore 이동은 별도 RS-2 precheck로 분리한다.",
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
            "lineCount": line_count(TARGET_REL),
            "imports": imports,
            "exports": exports,
            "importedBy": used_by,
            "role": role,
            "restoreFeatureReadiness": "RESTORE_FEATURE_READY_KEEP_FILENAME",
            "targetCandidates": target_candidates,
            "recommendation": recommendation,
            "risk": "MEDIUM",
            "testWorkspaceImpact": test_workspace_impact,
        },
        "dependencyImpact": dependency_impact,
        "routeImpact": route_impact,
        "staticCheckPlan": static_check_plan,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "Run RS-1 move: create src/components/restore and move AutoRestoreWorkspace.tsx keeping filename.",
            "Update src/app/autorestore/page.tsx import path only; keep /autorestore route URL.",
            "Run tmp/check_autorestore_workspace_restore_move_rs1.mjs plus typecheck/build.",
            "Consider RestoreWorkspace rename only as a later separate micro-step.",
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
                "staticOrDynamicImport",
                "importPath",
                "importedSymbols",
                "needsImportUpdateOnMove",
                "testWorkspaceImpact",
                "tmpReference",
            ],
        )
        writer.writeheader()
        writer.writerows(used_by)

    prod_summary = "\n".join(
        f"- {row['file']}:{row['line']} [{row['feature']}, {row['staticOrDynamicImport']}] {row['importPath']}"
        for row in prod_imports
    )
    export_summary = ", ".join(f"{row['kind']} {row['name']}" for row in exports)
    dirty_text = "\n".join(dirty) if dirty else "(clean)"
    restore_dir_status = "exists" if exists_rel("src/components/restore") else "absent"

    md = f"""# FRONTEND_AUTORESTORE_TO_RESTORE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_AUTORESTORE_TO_RESTORE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/rename/import 수정: 없음
- fixture/templates/backend 수정: 없음
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- tmp/codex_frontend_autorestore_to_restore_precheck.py
- docs/FRONTEND_AUTORESTORE_TO_RESTORE_PRECHECK_20260522.md
- docs/FRONTEND_AUTORESTORE_TO_RESTORE_PRECHECK_20260522.json
- docs/FRONTEND_AUTORESTORE_TO_RESTORE_MAP_20260522.csv

## 4. 분석 범위
- src/components/autorestore/AutoRestoreWorkspace.tsx
- src/app/autorestore/page.tsx
- src/components/restore/** 상태: {restore_dir_status}
- src/lib/restoreProfileStore.ts
- src/lib/profiles.ts
- src/lib/autofillEngine.ts
- src/common/storage/historyStore.ts
- src/common/storage/imageStore.ts
- src/components/runocr/**
- src/components/history/**
- src/components/login/ui/RequireLogin.tsx
- src/components/layout/AppProviders.tsx
- src/components/test/TestWorkspace.tsx
- src/components/test/core/**

## 5. AutoRestoreWorkspace 역할 요약
- currentPath: {TARGET_REL}
- lineCount: {line_count(TARGET_REL)}
- imports: {json.dumps(imports, ensure_ascii=False)}
- exports: {export_summary}
- mainResponsibility: Restore/autofill profile 관리 workspace. 저장된 restore profile 목록 조회, 상세 표시, 삭제 UI를 제공한다.
- restore profile 관리 여부: {role['restoreProfileManagement']}
- autofill profile 관리 여부: {role['autofillProfileManagement']}
- restoreProfileStore 의존: {role['restoreProfileStoreDependency']}
- profiles 의존: {role['profilesDependency']}
- autofillEngine 의존: {role['autofillEngineDependency']}
- historyStore/common storage 직접 의존: {role['historyStoreCommonStorageDependency']}
- AppProviders/useUi 의존: {role['appProvidersUseUiDependency']}
- RequireLogin 직접 의존: {role['requireLoginDependency']}
- localStorage/IndexedDB 직접 사용: {role['localStorageIndexedDBDirectUse']}
- React state/effect 사용: {role['reactStateEffectUse']}
- moveRisk: {role['moveRisk']}

## 6. route/importedBy 분석
{prod_summary if prod_summary else "- production import 없음"}

- route file: {ROUTE_REL}
- route URL: /autorestore 유지 권장
- 현재 import: {route_impact['currentImportPath']}
- 추천 import: {route_impact['targetImportIfKeepName']}
- dynamic import 여부: {route_impact['dynamicImport']}
- route policy 변경 필요: {route_impact['routePolicyChangeNeeded']}

## 7. restore feature ownership 판단
- 판정: RESTORE_FEATURE_READY_KEEP_FILENAME
- 이유: route 이름은 autorestore여도, workspace의 실질 책임은 restore profile 관리다.
- `src/components/restore/` 폴더 도입은 적합하다.
- 단, `RestoreWorkspace.tsx` rename은 이번 folder ownership move와 분리하는 것이 안전하다.

## 8. dependency 영향
- restoreProfileStore import: {dependency_impact['importsRestoreProfileStore']}
- profiles import: {dependency_impact['importsProfiles']}
- autofillEngine import: {dependency_impact['importsAutofillEngine']}
- common/storage historyStore direct import: {dependency_impact['importsHistoryStoreCommonStorage']}
- useUi import: {dependency_impact['importsUseUi']}
- RequireLogin 관계: {dependency_impact['requireLoginRelation']}
- 상대 import 영향: {dependency_impact['relativeImportChangeNeeded']}
- 순환 의존 위험: {dependency_impact['cycleRisk']}

## 9. TestWorkspace 영향
- 판정: {test_workspace_impact['classification']}
- TestWorkspace 직접 import: {test_workspace_impact['testWorkspaceDirectImport']}
- test/core 직접 import: {test_workspace_impact['testCoreDirectImport']}
- 간접 영향: {test_workspace_impact['indirectViaStores']}
- 이동 시 TestWorkspace 수정 필요: {test_workspace_impact['needsTestWorkspaceModificationOnMove']}

## 10. target path 비교
| 후보 | 추천 | 장점 | 단점 | rename risk |
| --- | --- | --- | --- | --- |
| src/components/restore/AutoRestoreWorkspace.tsx | YES | 폴더 owner 정리, 파일명/symbol 안정 | AutoRestore 이름은 남음 | LOW |
| src/components/restore/RestoreWorkspace.tsx | NO | broader restore 이름과 일치 | move+rename+symbol 판단이 섞임 | MEDIUM |
| src/components/autorestore/AutoRestoreWorkspace.tsx 유지 | NO | import 변경 없음 | 목표 구조 불일치 지속 | NONE |
| 보류 | NO | 즉시 영향 없음 | 구조 정리 지연 | NONE |

## 11. 실제 이동 추천
- 추천 선택지: A. AutoRestoreWorkspace.tsx만 src/components/restore/AutoRestoreWorkspace.tsx로 이동
- src/app/autorestore/page.tsx는 유지하고 import path만 바꾼다.
- route URL `/autorestore` 변경은 하지 않는다.
- restoreProfileStore 이동 및 RestoreWorkspace rename은 별도 micro-step으로 분리한다.

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
- RS-1 move에서 `src/components/restore/`를 만들고 AutoRestoreWorkspace 파일명은 유지한다.
- `src/app/autorestore/page.tsx` import path만 보정한다.
- 이후 필요하면 `RestoreWorkspace.tsx` rename precheck를 별도로 진행한다.
"""
    MD_PATH.write_text(md, encoding="utf-8")

    print(f"Wrote {MD_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Wrote {JSON_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Wrote {CSV_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print("Recommendation: RESTORE_FEATURE_READY_KEEP_FILENAME")
    print(f"typecheck={typecheck.get('status')} build={build.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
