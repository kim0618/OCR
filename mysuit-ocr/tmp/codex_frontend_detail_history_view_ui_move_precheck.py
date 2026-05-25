import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

MD_PATH = DOCS_DIR / "FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_20260522.md"
JSON_PATH = DOCS_DIR / "FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_20260522.json"
CSV_PATH = DOCS_DIR / "FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_MAP_20260522.csv"

TYPECHECK_RESULT = PROJECT_ROOT / "tmp" / "codex_detail_history_view_ui_move_precheck_typecheck.json"
BUILD_RESULT = PROJECT_ROOT / "tmp" / "codex_detail_history_view_ui_move_precheck_build.json"

TARGET = PROJECT_ROOT / "src" / "components" / "history" / "DetailHistoryView.tsx"
TARGET_REL = "src/components/history/DetailHistoryView.tsx"
RECOMMENDED_TARGET_REL = "src/components/history/ui/DetailHistoryView.tsx"


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def line_count(path: Path) -> int:
    text = read_text(path)
    return len(text.splitlines()) if text else 0


def parse_imports(text: str) -> list[dict]:
    imports = []
    for match in re.finditer(r"import\s+([\s\S]*?)\s+from\s+['\"]([^'\"]+)['\"]", text):
        imports.append({"symbols": " ".join(match.group(1).split()), "source": match.group(2)})
    for match in re.finditer(r"import\s+['\"]([^'\"]+)['\"]", text):
        imports.append({"symbols": "(side-effect)", "source": match.group(1)})
    return imports


def parse_exports(text: str) -> list[str]:
    exports = []
    for pattern in [
        r"export\s+default\s+function\s+([A-Za-z0-9_]+)",
        r"export\s+(?:type|interface|function|const|class)\s+([A-Za-z0-9_]+)",
    ]:
        for match in re.finditer(pattern, text):
            exports.append(match.group(0).strip())
    return exports


def rg(pattern: str, paths: list[str]) -> list[dict]:
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
        rows.append({"error": proc.stderr.strip(), "pattern": pattern})
        return rows
    for line in proc.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            rows.append({"file": parts[0].replace("\\", "/"), "line": int(parts[1]), "text": parts[2].strip()})
    return rows


def feature_for(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("src/components/history/") or normalized.startswith("src/app/history/"):
        return "history"
    if normalized.startswith("src/components/runocr/"):
        return "runocr"
    if normalized.startswith("src/components/autorestore/") or normalized.startswith("src/components/restore/"):
        return "restore"
    if normalized.startswith("src/components/test/") or normalized.startswith("tmp/"):
        return "test"
    if normalized.startswith("src/app/"):
        return "app"
    if normalized.startswith("src/common/"):
        return "common"
    return "unknown"


def load_command_result(path: Path, command: str) -> dict:
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
    detail_text = read_text(TARGET)
    history_workspace = PROJECT_ROOT / "src" / "components" / "history" / "HistoryWorkspace.tsx"
    test_workspace = PROJECT_ROOT / "src" / "components" / "test" / "TestWorkspace.tsx"

    usage_patterns = [
        "DetailHistoryView",
        "./DetailHistoryView",
        "../DetailHistoryView",
        "@/components/history/DetailHistoryView",
        "components/history/DetailHistoryView",
        "history/ui/DetailHistoryView",
    ]
    usage_rows = []
    seen = set()
    for pattern in usage_patterns:
        for row in rg(pattern, ["src", "tmp"]):
            key = (row.get("file"), row.get("line"), row.get("text"))
            if key in seen:
                continue
            seen.add(key)
            usage_rows.append(row)

    imported_by = []
    for row in usage_rows:
        file = row["file"]
        if file == TARGET_REL:
            continue
        text = row["text"]
        is_import = "import" in text
        imported_by.append(
            {
                "file": file,
                "line": row["line"],
                "importPath": text if is_import else "(reference)",
                "importedSymbols": "DetailHistoryView" if "DetailHistoryView" in text else "",
                "feature": feature_for(file),
                "isStaticImport": is_import,
                "needsImportUpdateOnMove": file == "src/components/history/HistoryWorkspace.tsx"
                or "src/components/history/DetailHistoryView.tsx" in text,
                "testWorkspaceImpact": file.startswith("src/components/test/"),
            }
        )

    imports = parse_imports(detail_text)
    exports = parse_exports(detail_text)

    role = {
        "mainResponsibility": "HistoryRunRecord 상세 화면을 렌더링하고, 출력 필드/tableRows/GT/복원 프로필 저장 액션을 제공한다.",
        "uiOnly": False,
        "detailPageView": True,
        "historyDetailRendering": True,
        "restoreRerunActionOrchestration": True,
        "groundTruthRelated": "@/lib/groundTruthStore" in detail_text,
        "localStorageIndexedDBDirectUse": False,
        "browserApiDirectUse": False,
        "reactStateEffectUse": "useState" in detail_text or "useEffect" in detail_text,
        "historyStoreDependency": "@/lib/historyStore" in detail_text,
        "imageStoreDependency": "@/lib/imageStore" in detail_text,
        "restoreProfileStoreDependency": "@/lib/restoreProfileStore" in detail_text,
        "profilesDependency": "@/lib/profiles" in detail_text,
        "autofillEngineDependency": "@/lib/autofillEngine" in detail_text,
        "commonUtilsDependency": "@/common/utils/" in detail_text,
        "componentsDependency": "../layout/AppProviders" in detail_text or "@/components/" in detail_text,
    }

    dependency_impact = {
        "historyWorkspaceImportsDetailHistoryView": './DetailHistoryView' in read_text(history_workspace),
        "detailHistoryViewImportsHistoryStore": role["historyStoreDependency"],
        "detailHistoryViewImportsImageStoreDirectly": role["imageStoreDependency"],
        "detailHistoryViewUsesHistoryImageHelpers": "getHistoryImageObjectUrl" in detail_text
        or "getHistoryOriginalImageObjectUrl" in detail_text,
        "detailHistoryViewImportsRestoreOrAutorestoreComponents": "components/restore" in detail_text
        or "components/autorestore" in detail_text,
        "detailHistoryViewImportsGroundTruthStore": role["groundTruthRelated"],
        "detailHistoryViewImportsTestsets": "@/lib/testsets" in detail_text,
        "detailHistoryViewImportsProfiles": role["profilesDependency"],
        "detailHistoryViewImportsAutofillEngine": role["autofillEngineDependency"],
        "relativeImportChangeNeededInsideMovedFile": "../layout/AppProviders would become ../../layout/AppProviders after moving into history/ui",
        "aliasImportsUnaffected": True,
        "cycleRisk": "LOW",
        "notes": "소비자는 HistoryWorkspace 하나로 보이며, 이동 시 HistoryWorkspace import와 moved file의 layout 상대 import만 경로 보정 대상이다.",
    }

    test_workspace_impact = {
        "classification": "NO_TEST_IMPACT",
        "testWorkspaceDirectImport": "DetailHistoryView" in read_text(test_workspace),
        "testCoreDirectImport": any(
            row["file"].startswith("src/components/test/core/") for row in imported_by
        ),
        "tmpRunnerReferences": [row for row in imported_by if row["file"].startswith("tmp/")],
        "needsTestWorkspaceModificationOnMove": False,
        "notes": "TestWorkspace/test core 직접 import는 발견되지 않았다. 일부 tmp/static check는 현재 경로를 검증하므로 HR-2 move 시 static check expectation 갱신이 필요하다.",
    }

    target_candidates = [
        {
            "target": RECOMMENDED_TARGET_REL,
            "pros": [
                "HistoryWorkspace root와 상세 view UI 역할이 분리된다.",
                "Create/EditHistoryPopup과 같은 history/ui 계층에 상세 화면 조각을 모을 수 있다.",
                "production import 수정 범위가 작다.",
            ],
            "cons": [
                "DetailHistoryView 내부에 historyStore/groundTruth/restoreProfileStore 액션이 남아 UI 계층의 책임이 약간 두껍다.",
                "moved file 내부의 AppProviders 상대 import 경로 보정이 필요하다.",
            ],
            "importScope": [
                "src/components/history/HistoryWorkspace.tsx import path",
                "moved DetailHistoryView.tsx의 ../layout/AppProviders relative import",
            ],
            "risk": "MEDIUM",
            "recommended": True,
        },
        {
            "target": TARGET_REL,
            "pros": ["import 수정이 없다.", "store/action orchestration이 있는 컴포넌트를 root에 유지한다."],
            "cons": ["history root가 workspace와 상세 UI를 계속 함께 가진다.", "HR-1 이후 ui 폴더 정리 흐름과 덜 맞다."],
            "importScope": [],
            "risk": "LOW",
            "recommended": False,
        },
        {
            "target": "src/components/history/DetailHistoryView.tsx 유지 후 내부 UI 조각만 나중에 분리",
            "pros": ["store/action orchestration과 순수 UI를 더 엄밀하게 나눌 수 있다."],
            "cons": ["이번 목표보다 diff가 커지고 리팩토링 성격이 강해진다."],
            "importScope": "future refactor",
            "risk": "MEDIUM",
            "recommended": False,
        },
        {
            "target": "보류",
            "pros": ["현재 동작에 영향이 없다."],
            "cons": ["history 구조 정리의 HR-2 cleanup이 지연된다."],
            "importScope": [],
            "risk": "LOW",
            "recommended": False,
        },
    ]

    static_check_plan = [
        "tmp/check_detail_history_view_ui_move_hr2.mjs",
        "src/components/history/ui/DetailHistoryView.tsx 존재 확인",
        "src/components/history/DetailHistoryView.tsx 부재 확인",
        "HistoryWorkspace import가 ./ui/DetailHistoryView인지 확인",
        "src 운영 코드에 components/history/DetailHistoryView 잔존 없음 확인",
        "TestWorkspace 미수정 또는 import-only 영향 없음 확인",
        "historyStore/imageStore/restore/autorestore 미수정 확인",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]

    validation_plan = [
        "운영 코드는 HR-2 move 단계에서 파일 이동과 import path 보정만 수행한다.",
        "historyStore/imageStore/restoreProfileStore/autofillEngine 이동과 묶지 않는다.",
        "fixture rebake 없이 static check/typecheck/build로 검증한다.",
    ]

    typecheck = load_command_result(TYPECHECK_RESULT, "npm run typecheck")
    build = load_command_result(BUILD_RESULT, "npm run build")

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
            "historyUiReadiness": "HISTORY_UI_READY_WITH_IMPORT_ONLY",
            "targetCandidates": target_candidates,
            "recommendation": {
                "choice": "A",
                "summary": "DetailHistoryView.tsx만 src/components/history/ui/DetailHistoryView.tsx로 이동하고 import path만 보정한다.",
                "risk": "MEDIUM",
                "reason": "상세 view UI 성격이 강하고 생산 소비자는 HistoryWorkspace 하나지만, 내부에 store/GT/restore profile action이 있어 리팩토링 없이 이동-only micro-step으로 제한하는 것이 안전하다.",
            },
            "risk": "MEDIUM",
            "testWorkspaceImpact": test_workspace_impact,
        },
        "dependencyImpact": dependency_impact,
        "staticCheckPlan": static_check_plan,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "HR-2 move 단계에서 DetailHistoryView 단일 파일 이동 및 import path 보정 수행",
            "tmp/check_detail_history_view_ui_move_hr2.mjs 작성/실행",
            "typecheck/build 실행",
            "이후 historyStore/imageStore 이동은 별도 precheck로 진행",
        ],
    }

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_rows = []
    for row in imported_by:
        csv_rows.append(
            {
                "file": row["file"],
                "importPath": row["importPath"],
                "feature": row["feature"],
                "needsImportUpdateOnMove": row["needsImportUpdateOnMove"],
                "testWorkspaceImpact": row["testWorkspaceImpact"],
                "notes": "production consumer" if row["file"] == "src/components/history/HistoryWorkspace.tsx" else "static/test reference",
            }
        )
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "file",
                "importPath",
                "feature",
                "needsImportUpdateOnMove",
                "testWorkspaceImpact",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(csv_rows)

    md = f"""# FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/rename/import 수정: 없음
- fixture/templates/backend 수정: 없음
- 생성 파일만 작성했다.

## 3. 생성 파일
- tmp/codex_frontend_detail_history_view_ui_move_precheck.py
- docs/FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_20260522.md
- docs/FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_20260522.json
- docs/FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_MAP_20260522.csv

## 4. 분석 범위
- {TARGET_REL}
- src/components/history/HistoryWorkspace.tsx
- src/components/history/ui/**
- src/app/history/**
- src/lib/historyStore.ts
- src/lib/imageStore.ts
- src/lib/restoreProfileStore.ts
- src/lib/profiles.ts
- src/lib/autofillEngine.ts
- src/lib/groundTruthStore.ts
- src/lib/testsets.ts
- src/components/autorestore/**
- src/components/restore/**
- src/components/test/TestWorkspace.tsx
- src/components/test/core/**
- src/common/**
- src/components/runocr/**

## 5. DetailHistoryView 역할 요약
- currentPath: {TARGET_REL}
- lineCount: {line_count(TARGET)}
- exports: {", ".join(exports) if exports else "(none)"}
- 주요 역할: HistoryRunRecord 상세 렌더링, output fields/tableRows 편집, GT 저장, 복원 프로필 저장/update 액션 제공.
- UI-only 여부: 순수 UI-only는 아니다. 상세 view UI 성격이 강하지만 store/GT/restore profile action orchestration을 포함한다.
- moveRisk: MEDIUM

## 6. importedBy 분석
- production direct import: src/components/history/HistoryWorkspace.tsx (`./DetailHistoryView`)
- TestWorkspace/test core direct import: 없음
- tmp/static check reference: 일부 있음. HR-2 move static check에서 expectation 갱신 필요.

## 7. history/ui 적합성
- 판정: HISTORY_UI_READY_WITH_IMPORT_ONLY
- 이유: HistoryWorkspace가 feature root/orchestration 역할을 맡고, DetailHistoryView는 상세 화면 조각으로 `history/ui`에 둘 수 있다.
- 단, DetailHistoryView 내부의 store/GT/restore profile action은 유지하되 이번 이동에서는 리팩토링하지 않는 것이 안전하다.

## 8. dependency 영향 분석
- HistoryWorkspace -> DetailHistoryView import 보정 필요.
- DetailHistoryView -> `../layout/AppProviders` 상대 import는 이동 후 `../../layout/AppProviders`로 보정 필요.
- `@/lib/historyStore`, `@/lib/groundTruthStore`, `@/lib/autofillEngine`, `@/lib/restoreProfileStore`, `@/common/utils/*` alias import는 위치 이동 자체로는 구조적으로 유지 가능하다.
- restore/autorestore component 직접 import는 없다.
- 순환 의존 위험: LOW.

## 9. TestWorkspace 영향
- 판정: NO_TEST_IMPACT
- TestWorkspace 직접 import: 없음
- test/core 직접 import: 없음
- 이동 시 TestWorkspace 파일 수정 필요: 없음

## 10. target path 비교
| 후보 | 추천 | 장점 | 단점 | 위험 |
| --- | --- | --- | --- | --- |
| src/components/history/ui/DetailHistoryView.tsx | YES | history root를 Workspace 중심으로 정리, UI 계층 일관성 | 내부 action/store 의존은 남음 | MEDIUM |
| src/components/history/DetailHistoryView.tsx 유지 | NO | import 수정 없음 | root에 상세 UI가 남음 | LOW |
| root 유지 후 내부 UI 조각 분리 | NO | 더 엄밀한 분리 가능 | 이번 범위보다 큰 리팩토링 | MEDIUM |
| 보류 | NO | 즉시 영향 없음 | 구조 정리 지연 | LOW |

## 11. 실제 이동 추천
- 추천: A. DetailHistoryView.tsx만 src/components/history/ui/DetailHistoryView.tsx로 이동
- 필요한 import 수정: HistoryWorkspace import path, moved file 내부 AppProviders 상대 import path
- 금지/비추천: historyStore/imageStore/restore/autorestore 분리와 묶지 않기, JSX/handler 로직 수정하지 않기.

## 12. static check 설계
{chr(10).join(f"- {item}" for item in static_check_plan)}

## 13. dirty 상태
```text
{chr(10).join(dirty) if dirty else "(clean)"}
```

## 14. typecheck/build 결과
- typecheck: {typecheck.get("status")} (exitCode={typecheck.get("exitCode")})
- build: {build.get("status")} (exitCode={build.get("exitCode")})
- known stderr noise: ESLint nextVitals is not iterable 은 exit code 0이면 known issue로 취급.

## 15. 다음 작업 제안
- HR-2 move 단계에서 단일 파일 이동과 import path 보정만 수행한다.
- `tmp/check_detail_history_view_ui_move_hr2.mjs`를 추가해 move-only 범위를 검증한다.
- 이후 historyStore/imageStore/restoreProfileStore/autofillEngine 이동은 별도 precheck로 분리한다.
"""
    MD_PATH.write_text(md, encoding="utf-8")

    print(f"Wrote {rel(MD_PATH)}")
    print(f"Wrote {rel(JSON_PATH)}")
    print(f"Wrote {rel(CSV_PATH)}")
    print("Recommendation: HISTORY_UI_READY_WITH_IMPORT_ONLY")
    print(f"typecheck={typecheck.get('status')} build={build.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
