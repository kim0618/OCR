import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

MD_PATH = DOCS_DIR / "FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_20260522.md"
JSON_PATH = DOCS_DIR / "FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_20260522.json"
CSV_PATH = DOCS_DIR / "FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_MAP_20260522.csv"

TYPECHECK_RESULT = PROJECT_ROOT / "tmp" / "codex_image_store_common_storage_move_precheck_typecheck.json"
BUILD_RESULT = PROJECT_ROOT / "tmp" / "codex_image_store_common_storage_move_precheck_build.json"

TARGET_REL = "src/lib/imageStore.ts"
TARGET = PROJECT_ROOT / TARGET_REL
TARGET_NEXT = "src/common/storage/imageStore.ts"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_rel(rel: str) -> str:
    return read_text(PROJECT_ROOT / rel)


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
    if p.startswith("src/components/runocr/") or p.startswith("src/app/runocr/") or p == "src/app/ocr/page.tsx":
        return "runocr"
    if p.startswith("src/components/history/") or p.startswith("src/app/history/"):
        return "history"
    if p.startswith("src/components/template/") or p.startswith("src/app/template/"):
        return "template"
    if p.startswith("src/components/autorestore/") or p.startswith("src/components/restore/"):
        return "restore"
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


def imported_by(exports: list[dict]) -> list[dict]:
    keys = [
        "imageStore",
        "../lib/imageStore",
        "../../lib/imageStore",
        "@/lib/imageStore",
        "./imageStore",
        "saveImage",
        "loadImage",
        "deleteImage",
        "hydrate",
        "IndexedDB",
    ] + [e["name"] for e in exports]
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
                    "runtimeOrTypeOnly": runtime_or_type(text),
                    "needsImportUpdateOnMove": "@/lib/imageStore" in text
                    or "../lib/imageStore" in text
                    or "../../lib/imageStore" in text
                    or "./imageStore" in text,
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
    text = read_rel(TARGET_REL)
    imports = parse_imports(text)
    exports = parse_exports(text)
    used_by = imported_by(exports)
    production_imports = [row for row in used_by if row["feature"] != "tmp" and row["runtimeOrTypeOnly"] != "reference"]

    history_text = read_rel("src/lib/historyStore.ts")
    runocr_text = read_rel("src/components/runocr/RunOcrWorkspace.tsx")
    template_page_text = read_rel("src/app/template/page.tsx")
    template_annotator_text = read_rel("src/components/template/ui/TemplateAnnotator.tsx")
    detail_text = read_rel("src/components/history/ui/DetailHistoryView.tsx")
    workspace_text = read_rel("src/components/history/HistoryWorkspace.tsx")

    role = {
        "mainResponsibility": "IndexedDB image persistence for OCR history images and template images.",
        "imagePersistenceStore": True,
        "indexedDBUse": "indexedDB" in text or "IDBDatabase" in text,
        "localStorageUse": "localStorage" in text,
        "browserApiUse": "window" in text or "indexedDB" in text or "IDBDatabase" in text,
        "blobFileBase64ObjectUrlUse": any(k in text for k in ["Blob", "File", "base64", "dataUrl", "ObjectURL"]),
        "backendApiUse": "fetch(" in text or "axios" in text,
        "reactDependency": "from \"react\"" in text or "from 'react'" in text,
        "componentsDependency": "@/components/" in text or "../components/" in text or "../../components/" in text,
        "historyDependency": "historyStore imports imageStore at runtime; imageStore itself does not import history.",
        "runocrDependency": "@/lib/imageStore" in runocr_text,
        "templateDependency": "@/lib/imageStore" in template_page_text or "@/lib/imageStore" in template_annotator_text,
        "testWorkspaceImpact": any(row["testWorkspaceImpact"] for row in used_by),
        "commonStorageReadiness": "COMMON_STORAGE_READY_WITH_IMPORT_ONLY",
        "moveRisk": "MEDIUM",
    }

    dependency_impact = {
        "historyStoreImportsImageStore": "./imageStore" in history_text,
        "imageStoreImportsHistoryStore": "historyStore" in text,
        "imageStoreImportsComponents": role["componentsDependency"],
        "imageStoreImportsCommonUtilsOrTypes": "@/common/" in text or "../common/" in text,
        "templateAnnotatorDirectImport": "@/lib/imageStore" in template_annotator_text,
        "templateRouteDirectImport": "@/lib/imageStore" in template_page_text,
        "runocrDirectImport": "@/lib/imageStore" in runocr_text,
        "detailHistoryViewDirectImport": "@/lib/imageStore" in detail_text,
        "historyWorkspaceDirectImport": "@/lib/imageStore" in workspace_text,
        "cycleRisk": "LOW: imageStore has no imports and does not depend on historyStore/components.",
        "historyStoreMoveBenefit": "After imageStore moves to common/storage, historyStore can later move to common/storage and import sibling ./imageStore.",
    }

    test_workspace_impact = {
        "classification": "NO_TEST_IMPACT",
        "testWorkspaceDirectImport": any(row["file"] == "src/components/test/TestWorkspace.tsx" and row["runtimeOrTypeOnly"] != "reference" for row in used_by),
        "testCoreDirectImport": any(row["file"].startswith("src/components/test/core/") and row["runtimeOrTypeOnly"] != "reference" for row in used_by),
        "tmpRunnerReferences": [row for row in used_by if row["tmpReference"]],
        "needsTestWorkspaceModificationOnMove": False,
    }

    target_candidates = [
        {
            "target": TARGET_NEXT,
            "pros": [
                "IndexedDB browser persistence 책임을 common/storage에 명확히 둔다.",
                "historyStore와 Template/RunOCR가 feature 간 의존 없이 공유할 수 있다.",
                "imageStore가 import 없는 leaf store라 move-only 범위가 작다.",
            ],
            "cons": ["common/storage 폴더가 실제 move step에서 새로 생성된다.", "여러 runtime import path 보정이 필요하다."],
            "featureDependencyRisk": "LOW",
            "importScope": [
                "src/lib/historyStore.ts",
                "src/app/template/page.tsx",
                "src/components/runocr/RunOcrWorkspace.tsx",
                "src/components/template/ui/TemplateAnnotator.tsx",
                "static checks/tmp references",
            ],
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": True,
        },
        {
            "target": "src/common/utils/imageStore.ts",
            "pros": ["common shared 위치는 된다."],
            "cons": ["browser persistence store라 formatter/helper 중심 common/utils와 의미가 섞인다."],
            "featureDependencyRisk": "LOW",
            "importScope": "same as common/storage",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": False,
        },
        {
            "target": "src/components/history/utils/imageStore.ts",
            "pros": ["history image hydration과 가깝다."],
            "cons": ["Template image helpers도 들어 있어 Template/RunOCR가 history feature를 import하게 된다."],
            "featureDependencyRisk": "HIGH",
            "importScope": "cross-feature imports",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": False,
        },
        {
            "target": "src/components/template/utils/imageStore.ts",
            "pros": ["template image helper와 가깝다."],
            "cons": ["historyStore가 template feature를 import하게 된다."],
            "featureDependencyRisk": "HIGH",
            "importScope": "cross-feature imports",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": False,
        },
        {
            "target": TARGET_REL,
            "pros": ["변경 없음."],
            "cons": ["src/lib cleanup과 common/storage 도입이 지연된다."],
            "featureDependencyRisk": "CURRENT",
            "importScope": "none",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": False,
        },
        {
            "target": "보류",
            "pros": ["즉시 risk 없음."],
            "cons": ["historyStore common/storage 이동의 선행 작업이 지연된다."],
            "featureDependencyRisk": "LOW",
            "importScope": "none",
            "testWorkspaceImpact": "NO_TEST_IMPACT",
            "recommended": False,
        },
    ]

    recommendation = {
        "choice": "A",
        "summary": "Move only imageStore.ts to src/common/storage/imageStore.ts and update import paths.",
        "target": TARGET_NEXT,
        "risk": "MEDIUM",
        "reason": "imageStore is a leaf IndexedDB persistence store shared by historyStore, Template and RunOCR; common/storage avoids feature-to-feature dependency.",
        "importUpdatesNeeded": [item for item in target_candidates[0]["importScope"] if isinstance(item, str)],
        "doNotBundle": ["historyStore move", "Template logic changes", "TestWorkspace changes"],
    }

    static_check_plan = [
        "tmp/check_image_store_common_storage_move_cs1.mjs",
        "src/common/storage/imageStore.ts 존재",
        "src/lib/imageStore.ts 부재",
        "src/common/storage/imageStore.ts가 components/*를 import하지 않음",
        "src/common/storage/imageStore.ts가 React를 import하지 않음",
        "import path 정상",
        "@/lib/imageStore 잔존 없음",
        "src/lib/historyStore.ts가 @/common/storage/imageStore 또는 적절한 상대/alias import 사용",
        "TestWorkspace 미수정 또는 import-only 영향 없음 확인",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]

    validation_plan = [
        "실제 move 단계에서 common/storage 폴더를 생성한다.",
        "imageStore 단일 파일 이동과 import path 보정만 수행한다.",
        "historyStore 이동은 다음 CS-2 micro-step으로 분리한다.",
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
            "storageReadiness": "COMMON_STORAGE_READY_WITH_IMPORT_ONLY",
            "targetCandidates": target_candidates,
            "recommendation": recommendation,
            "risk": "MEDIUM",
            "testWorkspaceImpact": test_workspace_impact,
        },
        "dependencyImpact": dependency_impact,
        "featureDependencyRisk": {
            "commonStorage": "LOW",
            "historyUtils": "HIGH",
            "templateUtils": "HIGH",
            "currentSrcLib": "CURRENT_AMBIGUITY",
        },
        "staticCheckPlan": static_check_plan,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "Run CS-1 move: create src/common/storage and move imageStore.ts.",
            "Update imports in historyStore, template route, RunOcrWorkspace, TemplateAnnotator.",
            "Run tmp/check_image_store_common_storage_move_cs1.mjs plus typecheck/build.",
            "Proceed to historyStore common/storage precheck/move as CS-2.",
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
        writer.writerows(used_by)

    prod_summary = "\n".join(
        f"- {row['file']}:{row['line']} [{row['feature']}, {row['runtimeOrTypeOnly']}] {row['importPath']}"
        for row in production_imports
    )
    export_summary = ", ".join(f"{row['kind']} {row['name']}" for row in exports)
    dirty_text = "\n".join(dirty) if dirty else "(clean)"

    md = f"""# FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/rename/import 수정: 없음
- fixture/templates/backend 수정: 없음
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- tmp/codex_frontend_image_store_common_storage_move_precheck.py
- docs/FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_20260522.md
- docs/FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_20260522.json
- docs/FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_MAP_20260522.csv

## 4. 분석 범위
- src/lib/imageStore.ts
- src/lib/historyStore.ts
- src/lib/autofillEngine.ts
- src/components/runocr/**
- src/components/history/**
- src/components/template/**
- src/components/autorestore/**
- src/components/restore/**
- src/components/test/TestWorkspace.tsx
- src/components/test/core/**
- src/common/**
- src/app/**

## 5. imageStore 역할 요약
- currentPath: {TARGET_REL}
- lineCount: {line_count(TARGET_REL)}
- imports: {json.dumps(imports, ensure_ascii=False)}
- exports: {export_summary}
- mainResponsibility: IndexedDB 기반 image persistence store. History original/processed 이미지와 Template 이미지를 저장/조회/삭제한다.
- image persistence store 여부: YES
- IndexedDB 사용: {role['indexedDBUse']}
- localStorage 사용: {role['localStorageUse']}
- browser API 사용: {role['browserApiUse']}
- Blob/File/base64/objectURL 사용: {role['blobFileBase64ObjectUrlUse']}
- backend/API 사용: {role['backendApiUse']}
- React 의존: {role['reactDependency']}
- components/* 의존: {role['componentsDependency']}
- common/storage 적합성: {role['commonStorageReadiness']}
- moveRisk: {role['moveRisk']}

## 6. importedBy 분석
{prod_summary if prod_summary else "- production import 없음"}

핵심 production import:
- src/lib/historyStore.ts: `./imageStore` runtime import
- src/app/template/page.tsx: `@/lib/imageStore`
- src/components/runocr/RunOcrWorkspace.tsx: `@/lib/imageStore`
- src/components/template/ui/TemplateAnnotator.tsx: `@/lib/imageStore`

## 7. dependency 영향
- historyStore -> imageStore: {dependency_impact['historyStoreImportsImageStore']}
- imageStore -> historyStore: {dependency_impact['imageStoreImportsHistoryStore']}
- imageStore -> components/*: {dependency_impact['imageStoreImportsComponents']}
- TemplateAnnotator 직접 import: {dependency_impact['templateAnnotatorDirectImport']}
- Template route 직접 import: {dependency_impact['templateRouteDirectImport']}
- RunOCR 직접 import: {dependency_impact['runocrDirectImport']}
- DetailHistoryView 직접 import: {dependency_impact['detailHistoryViewDirectImport']}
- HistoryWorkspace 직접 import: {dependency_impact['historyWorkspaceDirectImport']}
- 순환 의존 위험: {dependency_impact['cycleRisk']}
- historyStore 이동 도움: {dependency_impact['historyStoreMoveBenefit']}

## 8. TestWorkspace 영향
- 판정: {test_workspace_impact['classification']}
- TestWorkspace 직접 import: {test_workspace_impact['testWorkspaceDirectImport']}
- test/core 직접 import: {test_workspace_impact['testCoreDirectImport']}
- 이동 시 TestWorkspace 수정 필요: {test_workspace_impact['needsTestWorkspaceModificationOnMove']}

## 9. common/storage 적합성
- 판정: COMMON_STORAGE_READY_WITH_IMPORT_ONLY
- 이유: IndexedDB persistence 책임이 명확하고, history/template/runocr에서 공유한다.
- common/storage로 이동해도 imageStore 자체가 components/*를 import하지 않으므로 common boundary 위반이 생기지 않는다.

## 10. target path 비교
| 후보 | 추천 | 장점 | 단점 | feature dependency risk |
| --- | --- | --- | --- | --- |
| src/common/storage/imageStore.ts | YES | shared browser persistence boundary에 적합 | import path 보정 필요 | LOW |
| src/common/utils/imageStore.ts | NO | common 위치 | storage 책임과 utils 의미가 섞임 | LOW |
| src/components/history/utils/imageStore.ts | NO | history image와 가까움 | Template/RunOCR가 history feature import | HIGH |
| src/components/template/utils/imageStore.ts | NO | template image와 가까움 | historyStore가 template feature import | HIGH |
| src/lib 유지 | NO | 변경 없음 | src/lib cleanup 지연 | CURRENT |
| 보류 | NO | 즉시 risk 없음 | CS-2 historyStore move 선행 작업 지연 | LOW |

## 11. 실제 이동 추천
- 추천 선택지: A. imageStore.ts만 src/common/storage/imageStore.ts로 이동
- historyStore와 묶지 않는다.
- common/storage 폴더는 실제 move step에서 생성한다.
- 필요한 import path 보정: historyStore, template page, RunOcrWorkspace, TemplateAnnotator, 관련 static checks.

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
- CS-1 move에서 imageStore 단일 파일 이동과 import path 보정만 수행한다.
- `tmp/check_image_store_common_storage_move_cs1.mjs`를 작성/실행한다.
- 이후 CS-2로 historyStore -> common/storage 이동을 별도 진행한다.
"""
    MD_PATH.write_text(md, encoding="utf-8")

    print(f"Wrote {MD_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Wrote {JSON_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Wrote {CSV_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print("Recommendation: COMMON_STORAGE_READY_WITH_IMPORT_ONLY")
    print(f"typecheck={typecheck.get('status')} build={build.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
