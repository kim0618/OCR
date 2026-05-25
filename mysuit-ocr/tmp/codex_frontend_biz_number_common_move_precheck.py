import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

MD_PATH = DOCS_DIR / "FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_20260522.md"
JSON_PATH = DOCS_DIR / "FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_20260522.json"
CSV_PATH = DOCS_DIR / "FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_MAP_20260522.csv"

TYPECHECK_RESULT = PROJECT_ROOT / "tmp" / "codex_biz_number_common_move_precheck_typecheck.json"
BUILD_RESULT = PROJECT_ROOT / "tmp" / "codex_biz_number_common_move_precheck_build.json"

TARGET_REL = "src/lib/bizNumber.ts"
TARGET_NEXT = "src/common/utils/bizNumber.ts"


def read_rel(rel: str) -> str:
    path = PROJECT_ROOT / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


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
    if p.startswith("src/components/test/core/"):
        return "test-core"
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
        "bizNumber",
        "../lib/bizNumber",
        "../../lib/bizNumber",
        "@/lib/bizNumber",
        "./bizNumber",
        "normalizeBiz",
        "formatBiz",
        "validateBiz",
        "businessNumber",
        "사업자번호",
    ] + [item["name"] for item in exports]
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
                    "needsImportUpdateOnMove": "@/lib/bizNumber" in text
                    or "../lib/bizNumber" in text
                    or "../../lib/bizNumber" in text
                    or "./bizNumber" in text,
                    "testWorkspaceImpact": hit.get("file") == "src/components/test/TestWorkspace.tsx",
                    "testCoreImpact": hit.get("file", "").startswith("src/components/test/core/"),
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
    production_imports = [
        row
        for row in used_by
        if row["feature"] != "tmp" and row["runtimeOrTypeOnly"] != "reference"
    ]

    autofill_text = read_rel("src/lib/autofillEngine.ts")
    runocr_text = read_rel("src/components/runocr/RunOcrWorkspace.tsx")
    detail_text = read_rel("src/components/history/ui/DetailHistoryView.tsx")
    ocr_formatter_text = read_rel("src/common/utils/ocrResultFormatters.ts")

    role = {
        "mainResponsibility": "Business registration number normalization/checksum validation and OCR text extraction helper.",
        "normalizesBusinessNumber": "normalizeBizNumber" in text,
        "formatsBusinessNumber": "slice(0, 3)" in text and "slice(3, 5)" in text,
        "validatesBusinessNumber": "validateChecksum" in text,
        "ocrAutofillUse": "extractBizNumber" in text,
        "reactDependency": "from \"react\"" in text or "from 'react'" in text,
        "domWindowDocumentLocalStorageDependency": any(k in text for k in ["window", "document", "localStorage", "sessionStorage"]),
        "backendApiDependency": "fetch(" in text or "axios" in text,
        "componentsDependency": "@/components/" in text or "../components/" in text,
        "sideEffects": False,
        "commonUtilsReadiness": "COMMON_UTIL_READY_WITH_IMPORT_ONLY",
        "moveRisk": "MEDIUM",
    }

    test_workspace_impact = {
        "classification": "TEST_CORE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY",
        "testWorkspaceDirectImport": any(row["testWorkspaceImpact"] and row["runtimeOrTypeOnly"] != "reference" for row in used_by),
        "testCoreDirectImport": any(row["testCoreImpact"] and row["runtimeOrTypeOnly"] != "reference" for row in used_by),
        "tmpRunnerReferences": [row for row in used_by if row["tmpReference"]],
        "needsTestWorkspaceModificationOnMove": any(row["testWorkspaceImpact"] and row["needsImportUpdateOnMove"] for row in used_by),
        "needsTestCoreModificationOnMove": any(row["testCoreImpact"] and row["needsImportUpdateOnMove"] for row in used_by),
        "logicChangeNeeded": False,
        "notes": "TestWorkspace and test/core import bizNumber directly; move impact is import path-only, but TestWorkspace policy should be explicitly acknowledged in move step.",
    }

    dependency_impact = {
        "bizNumberImportsOtherLib": len(imports) > 0,
        "autofillEngineImportsBizNumber": "./bizNumber" in autofill_text or "@/lib/bizNumber" in autofill_text,
        "ocrResultFormattersBizNumberRelation": "bizNumber" in ocr_formatter_text or "normalizeBiz" in ocr_formatter_text,
        "runocrDirectUse": "@/lib/bizNumber" in runocr_text,
        "historyDirectUse": "@/lib/bizNumber" in detail_text,
        "cleanJsonMarkdownTableRunnerImpact": "No direct production dependency found; tmp/static checks reference filename only.",
        "commonUtilsWouldImportSrcLib": False,
        "cycleRisk": "LOW: bizNumber has no imports.",
        "notes": "Moving bizNumber to common/utils makes autofillEngine, RunOCR, History and Test consumers depend on common util rather than src/lib.",
    }

    target_candidates = [
        {
            "target": TARGET_NEXT,
            "pros": [
                "Pure business number normalize/extract helper fits common/utils.",
                "Shared by RunOCR, History, autofillEngine and Test code.",
                "No React/DOM/storage/backend/components dependency.",
            ],
            "cons": [
                "TestWorkspace and test/core need import path-only updates in actual move.",
                "autofillEngine remains in src/lib and will temporarily import common/utils.",
            ],
            "importScope": [
                "src/lib/autofillEngine.ts",
                "src/components/runocr/RunOcrWorkspace.tsx",
                "src/components/history/ui/DetailHistoryView.tsx",
                "src/components/test/TestWorkspace.tsx",
                "src/components/test/core/extract.ts",
                "src/components/test/core/autofill.ts",
                "static checks/tmp references",
            ],
            "testWorkspaceImpact": "import path-only",
            "risk": "MEDIUM",
            "recommended": True,
        },
        {
            "target": TARGET_REL,
            "pros": ["No import changes."],
            "cons": ["src/lib cleanup remains incomplete.", "shared pure util remains in lib."],
            "importScope": [],
            "testWorkspaceImpact": "none",
            "risk": "LOW",
            "recommended": False,
        },
        {
            "target": "src/components/test/utils/bizNumber.ts",
            "pros": ["Test imports become feature-local."],
            "cons": ["RunOCR/History/autofillEngine would import test feature util; invalid boundary."],
            "importScope": "cross-feature",
            "testWorkspaceImpact": "feature-local but bad for app",
            "risk": "HIGH",
            "recommended": False,
        },
        {
            "target": "autofillEngine internal helper",
            "pros": ["autofillEngine dependency shrinks."],
            "cons": ["RunOCR/History/Test also use it directly; duplication or bad dependency would result."],
            "importScope": "large refactor",
            "testWorkspaceImpact": "requires broader changes",
            "risk": "HIGH",
            "recommended": False,
        },
        {
            "target": "보류",
            "pros": ["Avoids touching TestWorkspace imports now."],
            "cons": ["A safe pure util move is delayed."],
            "importScope": [],
            "testWorkspaceImpact": "none",
            "risk": "LOW",
            "recommended": False,
        },
    ]

    recommendation = {
        "choice": "A",
        "summary": "Move only bizNumber.ts to src/common/utils/bizNumber.ts and update import paths.",
        "readiness": "COMMON_UTIL_READY_BUT_TEST_IMPORT_CHECK_REQUIRED",
        "risk": "MEDIUM",
        "reason": "bizNumber is pure normalize/validate/extract helper shared by app and test code. TestWorkspace/test-core impact is import path-only.",
        "doNotBundle": ["autofillEngine move", "TestWorkspace structure work", "fixture rebake", "autorestore work"],
    }

    static_check_plan = [
        "tmp/check_biz_number_common_utils_move_bz1.mjs",
        "src/common/utils/bizNumber.ts 존재",
        "src/lib/bizNumber.ts 부재",
        "src/common/utils/bizNumber.ts가 components/*를 import하지 않음",
        "React/DOM/window/document/localStorage 의존 없음",
        "@/lib/bizNumber 잔존 없음",
        "TestWorkspace 미수정 또는 import-only 확인",
        "test/core 미수정 또는 import-only 확인",
        "autofillEngine import path 정상",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]

    validation_plan = [
        "실제 move 단계는 bizNumber 단일 파일 이동과 import path 보정만 수행한다.",
        "autofillEngine 이동과 묶지 않는다.",
        "fixture rebake 없이 static check/typecheck/build로 검증한다.",
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
            "commonUtilReadiness": "COMMON_UTIL_READY_BUT_TEST_IMPORT_CHECK_REQUIRED",
            "targetCandidates": target_candidates,
            "recommendation": recommendation,
            "risk": "MEDIUM",
            "testWorkspaceImpact": test_workspace_impact,
        },
        "dependencyImpact": dependency_impact,
        "staticCheckPlan": static_check_plan,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "Run BZ-1 move: move bizNumber.ts to src/common/utils/bizNumber.ts.",
            "Update imports in autofillEngine, RunOcrWorkspace, DetailHistoryView, TestWorkspace, test/core.",
            "Run tmp/check_biz_number_common_utils_move_bz1.mjs plus typecheck/build.",
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
                "testCoreImpact",
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

    md = f"""# FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/rename/import 수정: 없음
- fixture/templates/backend 수정: 없음
- autorestore 관련 작업: 없음
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- tmp/codex_frontend_biz_number_common_move_precheck.py
- docs/FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_20260522.md
- docs/FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_20260522.json
- docs/FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_MAP_20260522.csv

## 4. 분석 범위
- src/lib/bizNumber.ts
- src/lib/autofillEngine.ts
- src/components/runocr/**
- src/components/history/**
- src/components/test/TestWorkspace.tsx
- src/components/test/core/**
- src/common/**
- src/app/**

## 5. bizNumber 역할 요약
- currentPath: {TARGET_REL}
- lineCount: {line_count(TARGET_REL)}
- imports: {json.dumps(imports, ensure_ascii=False)}
- exports: {export_summary}
- mainResponsibility: 사업자번호 normalize/checksum validation/OCR text extraction helper.
- normalize 여부: {role['normalizesBusinessNumber']}
- format 여부: {role['formatsBusinessNumber']}
- validate 여부: {role['validatesBusinessNumber']}
- OCR/autofill 사용 여부: {role['ocrAutofillUse']}
- React 의존: {role['reactDependency']}
- DOM/window/document/localStorage 의존: {role['domWindowDocumentLocalStorageDependency']}
- backend/API 의존: {role['backendApiDependency']}
- components/* 의존: {role['componentsDependency']}
- side effect: {role['sideEffects']}
- common/utils 적합성: {role['commonUtilsReadiness']}
- moveRisk: {role['moveRisk']}

## 6. importedBy 분석
{prod_summary if prod_summary else "- production import 없음"}

핵심 직접 import:
- src/lib/autofillEngine.ts: normalizeBizNumber
- src/components/runocr/RunOcrWorkspace.tsx: extractBizNumber
- src/components/history/ui/DetailHistoryView.tsx: normalizeBizNumber
- src/components/test/TestWorkspace.tsx: extractBizNumber, normalizeBizNumber
- src/components/test/core/extract.ts: normalizeBizNumber
- src/components/test/core/autofill.ts: extractBizNumber, normalizeBizNumber

## 7. TestWorkspace/test-core 영향
- 판정: {test_workspace_impact['classification']}
- TestWorkspace 직접 import: {test_workspace_impact['testWorkspaceDirectImport']}
- test/core 직접 import: {test_workspace_impact['testCoreDirectImport']}
- TestWorkspace 수정 필요: {test_workspace_impact['needsTestWorkspaceModificationOnMove']}
- test/core 수정 필요: {test_workspace_impact['needsTestCoreModificationOnMove']}
- logic 수정 필요: {test_workspace_impact['logicChangeNeeded']}
- 설명: {test_workspace_impact['notes']}

## 8. dependency 영향
- bizNumber가 다른 lib를 import하는지: {dependency_impact['bizNumberImportsOtherLib']}
- autofillEngine -> bizNumber: {dependency_impact['autofillEngineImportsBizNumber']}
- ocrResultFormatters 관계: {dependency_impact['ocrResultFormattersBizNumberRelation']}
- RunOCR 직접 사용: {dependency_impact['runocrDirectUse']}
- History 직접 사용: {dependency_impact['historyDirectUse']}
- Clean JSON/Markdown/table runner 영향: {dependency_impact['cleanJsonMarkdownTableRunnerImpact']}
- 이동 후 common/utils가 src/lib를 import하게 되는지: {dependency_impact['commonUtilsWouldImportSrcLib']}
- 순환 의존 가능성: {dependency_impact['cycleRisk']}

## 9. common/utils 적합성
- 판정: COMMON_UTIL_READY_BUT_TEST_IMPORT_CHECK_REQUIRED
- 이유: 순수 문자열/번호 normalize/format/validate/extract helper이며 storage, React, DOM, backend, components 의존이 없다.
- TestWorkspace/test-core가 직접 import하므로 실제 move 단계에서 import path-only 변경임을 static check로 보장해야 한다.

## 10. target path 비교
| 후보 | 추천 | 장점 | 단점 | risk |
| --- | --- | --- | --- | --- |
| src/common/utils/bizNumber.ts | YES | shared pure util 위치, RunOCR/History/Test/autofill 공유 | TestWorkspace/test-core import path 보정 필요 | MEDIUM |
| src/lib 유지 | NO | 변경 없음 | src/lib cleanup 지연 | LOW |
| src/components/test/utils/bizNumber.ts | NO | Test feature-local | app code가 test util을 import하게 됨 | HIGH |
| autofillEngine 내부 흡수 | NO | autofillEngine 의존 축소 | RunOCR/History/Test 직접 사용과 충돌 | HIGH |
| 보류 | NO | TestWorkspace import를 건드리지 않음 | 안전한 common util 이동 지연 | LOW |

## 11. 실제 이동 추천
- 추천 선택지: A. bizNumber.ts만 src/common/utils/bizNumber.ts로 이동
- autofillEngine과 묶지 않는다.
- TestWorkspace/test-core는 import path-only 변경으로 제한한다.
- common/utils가 src/lib를 import하지 않도록 static check에 포함한다.

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
- BZ-1 move에서 bizNumber 단일 파일 이동과 import path 보정만 수행한다.
- `tmp/check_biz_number_common_utils_move_bz1.mjs`를 작성/실행한다.
- autorestore/restoreProfileStore/profiles 작업은 이번 흐름과 분리한다.
"""
    MD_PATH.write_text(md, encoding="utf-8")

    print(f"Wrote {MD_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Wrote {JSON_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Wrote {CSV_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    print("Recommendation: COMMON_UTIL_READY_BUT_TEST_IMPORT_CHECK_REQUIRED")
    print(f"typecheck={typecheck.get('status')} build={build.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
