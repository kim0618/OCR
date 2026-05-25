from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASK = "CODEX_FRONTEND_HISTORY_RESTORE_STRUCTURE_PRECHECK_NO_PROD_MODIFY"
REPORT = "FRONTEND_HISTORY_RESTORE_STRUCTURE_PRECHECK_20260522"
DOCS = ROOT / "docs"
TMP = ROOT / "tmp"

HISTORY_COMPONENTS = [
    "src/components/history/HistoryWorkspace.tsx",
    "src/components/history/DetailHistoryView.tsx",
    "src/components/history/popup/CreateHistoryPopup.tsx",
    "src/components/history/popup/EditHistoryPopup.tsx",
    "src/app/history/page.tsx",
]
RESTORE_COMPONENTS = [
    "src/components/autorestore/AutoRestoreWorkspace.tsx",
    "src/app/autorestore/page.tsx",
]
LIB_FILES = [
    "src/lib/historyStore.ts",
    "src/lib/imageStore.ts",
    "src/lib/restoreProfileStore.ts",
    "src/lib/profiles.ts",
    "src/lib/autofillEngine.ts",
    "src/lib/bizNumber.ts",
    "src/lib/groundTruthStore.ts",
    "src/lib/testsets.ts",
]


def p(s: str) -> Path:
    return ROOT / s


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, shell=False, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def line_count(text: str) -> int:
    return 0 if not text else len(text.splitlines())


def find_imports(text: str) -> list[str]:
    rows = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("import "):
            block = [line.rstrip()]
            while ";" not in lines[i] and i + 1 < len(lines):
                i += 1
                block.append(lines[i].rstrip())
            rows.append(" ".join(s.strip() for s in block))
        i += 1
    return rows


def find_exports(text: str) -> tuple[list[str], list[str]]:
    exports, names = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("export "):
            exports.append(s)
            m = re.match(r"export\s+(?:default\s+)?(?:function|const|type|interface|class)\s+([A-Za-z0-9_]+)", s)
            if m:
                names.append(m.group(1))
    return exports, names


def feature_for(path: str) -> str:
    q = path.replace("\\", "/")
    if "/app/" in q:
        return "app"
    if "/components/runocr/" in q:
        return "runocr"
    if "/components/template/" in q:
        return "template"
    if "/components/history/" in q:
        return "history"
    if "/components/autorestore/" in q or "/components/restore/" in q:
        return "restore"
    if "/components/login/" in q:
        return "login"
    if "/components/layout/" in q:
        return "layout"
    if "/components/test/" in q:
        return "test"
    if "/common/" in q:
        return "common"
    if "/src/lib/" in q:
        return "lib"
    return "unknown"


def extract_symbols(text: str, import_path: str) -> str:
    m = re.search(r"import\s+(.+?)\s+from\s+[\"']" + re.escape(import_path) + r"[\"']", text, re.S)
    return " ".join(m.group(1).split()) if m else ""


def source_files() -> list[Path]:
    out = []
    for path in (ROOT / "src").rglob("*"):
        if path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
            out.append(path)
    return sorted(out)


def imported_by(module_stem: str) -> list[dict]:
    needles = [
        f"@/lib/{module_stem}",
        f"./{module_stem}",
        f"../{module_stem}",
        f"../../{module_stem}",
        f"@/components/autorestore/{module_stem}",
        f"../../components/autorestore/{module_stem}",
        f"./popup/{module_stem}",
        f"./{module_stem}",
    ]
    rows, seen = [], set()
    for path in source_files():
        rel = path.relative_to(ROOT).as_posix()
        text = read(path)
        for needle in needles:
            if needle in text:
                key = (rel, needle)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "file": rel,
                    "importPath": needle,
                    "importedSymbols": extract_symbols(text, needle),
                    "feature": feature_for("/" + rel),
                    "importKind": "static",
                    "needsImportUpdateOnMove": True,
                    "testWorkspaceImpact": rel.startswith("src/components/test/"),
                })
    return rows


def role_for(path: str, text: str) -> str:
    name = Path(path).name
    roles = {
        "HistoryWorkspace.tsx": "History route workspace/list controller with create/edit/detail popup orchestration.",
        "DetailHistoryView.tsx": "History detail view, confirmed result editing, GT comparison, restore profile save/update actions.",
        "CreateHistoryPopup.tsx": "History create popup UI.",
        "EditHistoryPopup.tsx": "History edit popup UI.",
        "AutoRestoreWorkspace.tsx": "Restore/autofill profile management workspace.",
        "page.tsx": "Next route page wrapper.",
        "historyStore.ts": "Browser history persistence store using localStorage plus imageStore IndexedDB helper.",
        "imageStore.ts": "IndexedDB image persistence for history and template images.",
        "restoreProfileStore.ts": "Browser restore profile localStorage store.",
        "profiles.ts": "Test/profile policy and document/table column profile definitions.",
        "autofillEngine.ts": "Shared autofill suggestion/candidate engine using biz/history/restore/ground-truth data.",
        "bizNumber.ts": "Business registration number normalization/extraction utility.",
        "groundTruthStore.ts": "Test/history ground-truth localStorage store.",
        "testsets.ts": "Test dataset metadata and manifest types.",
    }
    return roles.get(name, "Route/component/helper file.")


def dependencies(text: str) -> dict:
    return {
        "localStorage": "localStorage" in text,
        "indexedDB": "indexedDB" in text or "IDBDatabase" in text,
        "browserApi": any(k in text for k in ["window", "crypto", "DOMException", "indexedDB", "localStorage"]),
        "backendApi": "fetch(" in text or "/api/" in text,
        "react": "from \"react\"" in text or "from 'react'" in text,
        "componentsImport": "@/components/" in text or "../components/" in text,
        "runocr": "runocr" in text.lower() or "RunOcr" in text,
        "history": "history" in text.lower() or "History" in text,
        "restore": "restore" in text.lower() or "Restore" in text or "autofill" in text.lower(),
        "testWorkspace": "TestWorkspace" in text or "testsets" in text,
    }


def target_for(path: str) -> tuple[str, str, str, str]:
    mapping = {
        "src/components/history/HistoryWorkspace.tsx": ("history", "src/components/history/HistoryWorkspace.tsx", "LOW", "Keep workspace at feature root."),
        "src/components/history/DetailHistoryView.tsx": ("history/ui", "src/components/history/ui/DetailHistoryView.tsx", "MEDIUM", "UI component under history/ui candidate."),
        "src/components/history/popup/CreateHistoryPopup.tsx": ("history/ui", "src/components/history/ui/CreateHistoryPopup.tsx", "LOW", "Popup UI move candidate."),
        "src/components/history/popup/EditHistoryPopup.tsx": ("history/ui", "src/components/history/ui/EditHistoryPopup.tsx", "LOW", "Popup UI move candidate."),
        "src/components/autorestore/AutoRestoreWorkspace.tsx": ("restore", "src/components/restore/RestoreWorkspace.tsx or src/components/restore/AutoRestoreWorkspace.tsx", "MEDIUM", "Folder/domain rename needs route import update."),
        "src/app/autorestore/page.tsx": ("app/route", "src/app/autorestore/page.tsx", "LOW", "Route path policy separate from component folder rename."),
        "src/lib/historyStore.ts": ("history/utils", "src/components/history/utils/historyStore.ts", "HIGH", "Browser store used by RunOCR, History, autofillEngine, groundTruthStore."),
        "src/lib/imageStore.ts": ("history/common boundary", "src/components/history/utils/imageStore.ts or src/common/utils/imageStore.ts", "HIGH", "Used by historyStore plus template image helpers."),
        "src/lib/restoreProfileStore.ts": ("restore/utils", "src/components/restore/utils/restoreProfileStore.ts", "MEDIUM_HIGH", "Used by restore workspace, history detail, autofillEngine."),
        "src/lib/profiles.ts": ("test/restore shared policy", "DEFER: src/components/test/utils/profiles.ts or src/components/restore/utils/profiles.ts after separate precheck", "HIGH", "Direct TestWorkspace import; defer without user approval."),
        "src/lib/autofillEngine.ts": ("shared domain util", "DEFER_SEPARATE_PRECHECK", "HIGH", "Imports historyStore/restoreProfileStore/bizNumber and is used by RunOCR/History/common types."),
        "src/lib/bizNumber.ts": ("common/utils", "src/common/utils/bizNumber.ts", "HIGH", "Shared pure util but TestWorkspace/test-core direct imports."),
        "src/lib/groundTruthStore.ts": ("test/utils", "DEFER: src/components/test/utils/groundTruthStore.ts", "HIGH", "TestWorkspace/RunOCR/History consumers; user approval needed."),
        "src/lib/testsets.ts": ("test/utils", "DEFER: src/components/test/utils/testsets.ts", "HIGH", "Test APIs and TestWorkspace direct imports."),
    }
    return mapping.get(path, ("unknown", path, "MEDIUM", "Review needed."))


def analyze(path: str) -> dict:
    text = read(p(path))
    exports, names = find_exports(text)
    stem = Path(path).stem
    ib = imported_by(stem)
    owner, target, risk, note = target_for(path)
    deps = dependencies(text)
    test = "TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY" if any(r["testWorkspaceImpact"] for r in ib) else "NO_TEST_IMPACT"
    if stem in {"profiles", "bizNumber", "groundTruthStore", "testsets"} and test != "NO_TEST_IMPACT":
        test = "DEFER_DUE_TO_TEST_WORKSPACE_POLICY"
    return {
        "currentPath": path,
        "exists": p(path).exists(),
        "lineCount": line_count(text),
        "imports": find_imports(text),
        "exports": exports,
        "exportedNames": names,
        "importedBy": ib,
        "mainResponsibility": role_for(path, text),
        "dependencies": deps,
        "recommendedOwner": owner,
        "recommendedTarget": target,
        "targetCandidates": [{"target": target, "recommended": True, "risk": risk, "notes": note}],
        "risk": risk,
        "testWorkspaceImpact": test,
        "notes": note,
    }


def load_result(name: str) -> dict:
    path = TMP / name
    if not path.exists():
        return {"command": "unknown", "status": "NOT_RUN", "exitCode": None}
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    history = [analyze(x) for x in HISTORY_COMPONENTS]
    restore = [analyze(x) for x in RESTORE_COMPONENTS]
    libs = [analyze(x) for x in LIB_FILES]
    _, dirty_out = run(["git", "status", "--short"])
    dirty = [line for line in dirty_out.splitlines() if line and not line.startswith("warning:")]
    autofill = next(x for x in libs if x["currentPath"].endswith("autofillEngine.ts"))
    autofill_analysis = {
        "verdict": "DEFER_SEPARATE_PRECHECK",
        "exports": autofill["exportedNames"],
        "runtimeConsumers": [r for r in autofill["importedBy"] if not r["importedSymbols"].startswith("type ")],
        "typeOnlyConsumers": [r for r in autofill["importedBy"] if "type" in r["importedSymbols"]],
        "commonUtilsCandidate": False,
        "reason": "Imports historyStore and restoreProfileStore at runtime and is consumed by RunOCR, History and common type formatting. Move after history/restore store ownership is settled.",
    }
    move_phases = [
        {"phase": "HR-1", "name": "history popup -> history/ui", "risk": "LOW", "items": ["CreateHistoryPopup", "EditHistoryPopup"]},
        {"phase": "HR-2", "name": "DetailHistoryView -> history/ui", "risk": "MEDIUM", "items": ["DetailHistoryView"]},
        {"phase": "HR-3", "name": "historyStore ownership move precheck/move", "risk": "HIGH", "items": ["historyStore"]},
        {"phase": "HR-4", "name": "imageStore separate precheck", "risk": "HIGH", "items": ["imageStore"]},
        {"phase": "RS-1", "name": "autorestore folder -> restore precheck/move", "risk": "MEDIUM", "items": ["AutoRestoreWorkspace"]},
        {"phase": "RS-2", "name": "restoreProfileStore move", "risk": "MEDIUM_HIGH", "items": ["restoreProfileStore"]},
        {"phase": "RS-3", "name": "profiles separate precheck", "risk": "HIGH", "items": ["profiles"]},
        {"phase": "AF-1", "name": "autofillEngine separate ownership precheck", "risk": "HIGH", "items": ["autofillEngine"]},
        {"phase": "BN-1", "name": "bizNumber common/utils precheck", "risk": "HIGH", "items": ["bizNumber"]},
        {"phase": "TEST-1", "name": "groundTruthStore/testsets defer until TestWorkspace approval", "risk": "HIGH", "items": ["groundTruthStore", "testsets"]},
    ]
    static_checks = [
        "target file exists and source absent after each move",
        "import paths resolve",
        "TestWorkspace is unchanged or import-path-only when explicitly approved",
        "common/utils imports no components/* path",
        "history/autorestore routes compile",
        "RunOCR boundary checks PASS",
        "LIB/common checks PASS",
        "typecheck/build PASS",
    ]
    typecheck = load_result("codex_history_restore_structure_precheck_typecheck.json")
    build = load_result("codex_history_restore_structure_precheck_build.json")
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "projectRoot": "mysuit-ocr",
        "codeModified": False,
        "dirtyStatus": {"entries": dirty},
        "historyFiles": history,
        "restoreFiles": restore,
        "libFiles": libs,
        "autofillEngineAnalysis": autofill_analysis,
        "testWorkspaceImpact": {x["currentPath"]: x["testWorkspaceImpact"] for x in libs + history + restore},
        "targetCandidates": [{"currentPath": x["currentPath"], "target": x["recommendedTarget"], "owner": x["recommendedOwner"], "risk": x["risk"]} for x in history + restore + libs],
        "movePhases": move_phases,
        "staticCheckPlan": {"items": static_checks, "scripts": ["tmp/check_history_popup_ui_move_hr1.mjs", "tmp/check_restore_workspace_move_rs1.mjs", "tmp/check_autofill_engine_ownership_af1.mjs"]},
        "validationPlan": ["No production code changes in this precheck.", "Move one small unit at a time.", "Defer TestWorkspace-coupled files until approval."],
        "typecheck": typecheck,
        "build": build,
        "nextSteps": ["Start with HR-1 history popup ui move precheck/move.", "Then HR-2 DetailHistoryView ui move.", "Keep autofillEngine and TestWorkspace-coupled stores for separate prechecks."],
    }
    json_path = DOCS / f"{REPORT}.json"
    md_path = DOCS / f"{REPORT}.md"
    csv_path = DOCS / "FRONTEND_HISTORY_RESTORE_STRUCTURE_MAP_20260522.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["currentPath", "role", "importedByCount", "mainConsumers", "recommendedOwner", "recommendedTarget", "risk", "testWorkspaceImpact", "movePhase", "notes"])
        writer.writeheader()
        phase_by = {item: ph["phase"] for ph in move_phases for item in ph["items"]}
        for x in history + restore + libs:
            stem = Path(x["currentPath"]).stem
            writer.writerow({
                "currentPath": x["currentPath"],
                "role": x["mainResponsibility"],
                "importedByCount": len(x["importedBy"]),
                "mainConsumers": ";".join(sorted({r["feature"] for r in x["importedBy"]})),
                "recommendedOwner": x["recommendedOwner"],
                "recommendedTarget": x["recommendedTarget"],
                "risk": x["risk"],
                "testWorkspaceImpact": x["testWorkspaceImpact"],
                "movePhase": phase_by.get(stem, ""),
                "notes": x["notes"],
            })
    md = f"""# FRONTEND history/restore structure precheck

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `{TASK}`

## 2. 코드 수정 여부
- codeModified: false
- 운영 코드 수정 없음
- 파일 이동/import 수정/rename/fixture/templates/backend 수정 없음

## 3. 생성 파일
- `tmp/codex_frontend_history_restore_structure_precheck.py`
- `docs/{REPORT}.md`
- `docs/{REPORT}.json`
- `docs/FRONTEND_HISTORY_RESTORE_STRUCTURE_MAP_20260522.csv`
- `ocr-server/logs/codex_{TASK}.out.log`
- `ocr-server/logs/codex_{TASK}.err.log`

## 4. 분석 범위
- history/autorestore components and routes
- related src/lib stores/profile/autofill/test files
- src/common, RunOCR, login RequireLogin, layout AppProviders
- TestWorkspace read-only

## 5. history 구조 분석
| file | role | target | risk | importedBy |
|---|---|---|---|---|
"""
    for x in history:
        md += f"| `{x['currentPath']}` | {x['mainResponsibility']} | `{x['recommendedTarget']}` | {x['risk']} | {len(x['importedBy'])} |\n"
    md += "\n## 6. restore/autorestore 구조 분석\n| file | role | target | risk | importedBy |\n|---|---|---|---|---|\n"
    for x in restore:
        md += f"| `{x['currentPath']}` | {x['mainResponsibility']} | `{x['recommendedTarget']}` | {x['risk']} | {len(x['importedBy'])} |\n"
    md += "\n## 7. 관련 src/lib ownership 분석\n| file | owner | target | risk | TestWorkspace |\n|---|---|---|---|---|\n"
    for x in libs:
        md += f"| `{x['currentPath']}` | {x['recommendedOwner']} | `{x['recommendedTarget']}` | {x['risk']} | {x['testWorkspaceImpact']} |\n"
    md += f"""

## 8. autofillEngine 특별 분석
- verdict: `{autofill_analysis['verdict']}`
- reason: {autofill_analysis['reason']}
- runtime consumers: {len(autofill_analysis['runtimeConsumers'])}
- type-only/common consumers include `ocrResultFormatters` if imported as types.

## 9. TestWorkspace 영향 분석
- profiles, bizNumber, groundTruthStore, testsets are TestWorkspace-coupled and should be deferred or approved as import-only work.
- history/restore UI moves do not require TestWorkspace logic changes.

## 10. target path 후보
- See JSON/CSV map for per-file candidates.

## 11. 위험도 분류
- LOW: history popup UI.
- MEDIUM: DetailHistoryView UI move, autorestore folder move.
- HIGH: stores, autofillEngine, TestWorkspace-coupled files.

## 12. 이동 순서 추천
"""
    for ph in move_phases:
        md += f"- {ph['phase']}: {ph['name']} ({ph['risk']})\n"
    md += "\n## 13. static check 설계\n"
    for item in static_checks:
        md += f"- {item}\n"
    md += f"""

## 14. dirty 상태
```text
{chr(10).join(dirty)}
```

## 15. typecheck/build 결과
- typecheck: {typecheck.get('status')} / exitCode {typecheck.get('exitCode')}
- build: {build.get('status')} / exitCode {build.get('exitCode')}
- known stderr noise: ESLint `nextVitals is not iterable`는 exit code 0이면 known issue

## 16. 다음 작업 제안
- HR-1 history popup -> history/ui move precheck/move부터 진행.
- autofillEngine, bizNumber, groundTruthStore/testsets는 별도 precheck 또는 TestWorkspace 승인 후 진행.
"""
    md_path.write_text(md, encoding="utf-8")
    print(json.dumps({"status": "ok", "json": json_path.relative_to(ROOT).as_posix(), "md": md_path.relative_to(ROOT).as_posix(), "csv": csv_path.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
