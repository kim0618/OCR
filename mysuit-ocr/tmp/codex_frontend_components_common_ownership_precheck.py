from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASK = "CODEX_FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_NO_PROD_MODIFY"
REPORT = "FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_20260522"
DOCS = ROOT / "docs"
TMP = ROOT / "tmp"
FILES = [
    ROOT / "src/components/common/AppProviders.tsx",
    ROOT / "src/components/common/RequireLogin.tsx",
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def line_count(text: str) -> int:
    return 0 if text == "" else len(text.splitlines())


def find_imports(text: str) -> list[str]:
    rows: list[str] = []
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
    exports: list[str] = []
    names: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("export "):
            exports.append(s)
            m = re.match(r"export\s+(?:default\s+)?(?:function|const|type|interface|class)\s+([A-Za-z0-9_]+)", s)
            if m:
                names.append(m.group(1))
    return exports, names


def feature_for(path: str) -> str:
    p = path.replace("\\", "/")
    if "/app/" in p:
        return "app"
    if "/components/runocr/" in p:
        return "runocr"
    if "/components/template/" in p:
        return "template"
    if "/components/history/" in p:
        return "history"
    if "/components/restore/" in p or "/components/autorestore/" in p:
        return "restore"
    if "/components/login/" in p:
        return "login"
    if "/components/layout/" in p:
        return "layout"
    if "/components/test/" in p:
        return "test"
    if "/components/common/" in p:
        return "components-common"
    if "/common/" in p:
        return "common"
    if "/src/lib/" in p:
        return "lib"
    return "unknown"


def extract_imported_symbols(text: str, import_path: str) -> str:
    pattern = re.compile(r"import\s+(.+?)\s+from\s+[\"']" + re.escape(import_path) + r"[\"']", re.S)
    m = pattern.search(text)
    return " ".join(m.group(1).split()) if m else ""


def code_paths() -> list[Path]:
    paths: list[Path] = []
    for base in [ROOT / "src"]:
        for path in base.rglob("*"):
            if path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
                paths.append(path)
    return sorted(paths)


def scan_imported_by(file_kind: str) -> list[dict]:
    if file_kind == "AppProviders":
        needles = [
            "@/components/common/AppProviders",
            "../common/AppProviders",
            "../../common/AppProviders",
            "../components/common/AppProviders",
            "components/common/AppProviders",
        ]
        symbols = ["AppProviders", "useUi"]
    else:
        needles = [
            "@/components/common/RequireLogin",
            "../common/RequireLogin",
            "../../common/RequireLogin",
            "../components/common/RequireLogin",
            "components/common/RequireLogin",
        ]
        symbols = ["RequireLogin"]

    rows: list[dict] = []
    seen = set()
    for path in code_paths():
        text = read(path)
        rel_path = rel(path)
        if rel_path in {
            "src/components/common/AppProviders.tsx",
            "src/components/common/RequireLogin.tsx",
        }:
            continue
        for needle in needles:
            if needle in text:
                key = (rel_path, needle)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "file": rel_path,
                        "importPath": needle,
                        "importedSymbols": extract_imported_symbols(text, needle),
                        "feature": feature_for("/" + rel_path),
                        "importKind": "static",
                        "needsImportUpdateOnMove": True,
                        "testWorkspaceImpact": rel_path.startswith("src/components/test/"),
                    }
                )
        for sym in symbols:
            if sym in text and rel_path.startswith("src/components/test/") and not any(r["file"] == rel_path for r in rows):
                pass
    return rows


def scan_symbol_hits(symbol: str) -> list[str]:
    code, out = run(["rg", "-n", symbol, "src"])
    if code not in (0, 1):
        return []
    return sorted({line.split(":", 1)[0].replace("\\", "/") for line in out.splitlines() if ":" in line})


def target_candidates(kind: str) -> list[dict]:
    if kind == "AppProviders":
        return [
            {
                "target": "src/components/layout/AppProviders.tsx",
                "pros": ["Matches app-shell/provider responsibility", "Avoids putting global app state provider under generic common/ui"],
                "cons": ["Many feature imports of useUi need path updates"],
                "importUpdateScope": "app layout plus runocr/template/history/restore/login/test relative imports",
                "commonBoundaryRisk": "LOW",
                "routeImpact": "src/app/layout.tsx import path only",
                "recommended": True,
                "risk": "MEDIUM",
            },
            {
                "target": "src/common/ui/AppProviders.tsx",
                "pros": ["Provider is shared UI infrastructure"],
                "cons": ["common/ui would own app-level global context/provider rather than reusable leaf UI"],
                "importUpdateScope": "broad",
                "commonBoundaryRisk": "LOW if no components/* import, but semantic fit is weaker",
                "routeImpact": "src/app/layout.tsx import path only",
                "recommended": False,
                "risk": "MEDIUM",
            },
            {
                "target": "src/common/utils/AppProviders.tsx",
                "pros": [],
                "cons": ["Not a utility; React provider component belongs in UI/layout"],
                "importUpdateScope": "broad",
                "commonBoundaryRisk": "MEDIUM",
                "routeImpact": "path only",
                "recommended": False,
                "risk": "HIGH",
            },
            {
                "target": "src/components/common 유지",
                "pros": ["No import updates"],
                "cons": ["Leaves components/common folder alive outside target structure"],
                "importUpdateScope": "none",
                "commonBoundaryRisk": "LOW",
                "routeImpact": "none",
                "recommended": False,
                "risk": "LOW",
            },
            {
                "target": "보류",
                "pros": ["Can wait for layout folder cleanup"],
                "cons": ["Delays removing components/common"],
                "importUpdateScope": "none",
                "commonBoundaryRisk": "LOW",
                "routeImpact": "none",
                "recommended": False,
                "risk": "LOW",
            },
        ]
    return [
        {
            "target": "src/components/login/ui/RequireLogin.tsx",
            "pros": ["Auth guard is login/auth feature UI policy", "Keeps login helper dependency inside login feature boundary"],
            "cons": ["App route imports need path updates"],
            "importUpdateScope": "src/app/autorestore/page.tsx and src/app/history/page.tsx",
            "commonBoundaryRisk": "LOW",
            "routeImpact": "route wrapper import path only",
            "recommended": True,
            "risk": "LOW_MEDIUM",
        },
        {
            "target": "src/components/login/RequireLogin.tsx",
            "pros": ["Auth guard belongs to login feature"],
            "cons": ["Less consistent if login/ui folder is used for UI components"],
            "importUpdateScope": "two route imports",
            "commonBoundaryRisk": "LOW",
            "routeImpact": "path only",
            "recommended": False,
            "risk": "LOW_MEDIUM",
        },
        {
            "target": "src/common/ui/RequireLogin.tsx",
            "pros": ["Route wrapper is shared"],
            "cons": ["Would make common/ui import login/auth policy via @/lib/login; semantically not generic UI"],
            "importUpdateScope": "two route imports",
            "commonBoundaryRisk": "MEDIUM semantic boundary risk",
            "routeImpact": "path only",
            "recommended": False,
            "risk": "MEDIUM",
        },
        {
            "target": "src/components/layout/RequireLogin.tsx",
            "pros": ["It wraps route content"],
            "cons": ["Auth policy is stronger than layout concern"],
            "importUpdateScope": "two route imports",
            "commonBoundaryRisk": "LOW",
            "routeImpact": "path only",
            "recommended": False,
            "risk": "MEDIUM",
        },
        {
            "target": "src/components/common 유지",
            "pros": ["No import updates"],
            "cons": ["Leaves components/common folder alive outside target structure"],
            "importUpdateScope": "none",
            "commonBoundaryRisk": "LOW",
            "routeImpact": "none",
            "recommended": False,
            "risk": "LOW",
        },
        {
            "target": "보류",
            "pros": ["Can wait for login/layout ownership decision"],
            "cons": ["Delays folder cleanup"],
            "importUpdateScope": "none",
            "commonBoundaryRisk": "LOW",
            "routeImpact": "none",
            "recommended": False,
            "risk": "LOW",
        },
    ]


def load_result(name: str) -> dict:
    path = TMP / name
    if not path.exists():
        return {
            "command": "unknown",
            "status": "NOT_RUN",
            "exitCode": None,
            "outLog": f"ocr-server/logs/codex_{TASK}.out.log",
            "errLog": f"ocr-server/logs/codex_{TASK}.err.log",
        }
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def analyze_file(path: Path) -> dict:
    text = read(path)
    kind = path.stem
    exports, exported_names = find_exports(text)
    imports = find_imports(text)
    imported_by = scan_imported_by(kind)
    role = {}
    if kind == "AppProviders":
        role = {
            "mainResponsibility": "Global UI provider/context for loading overlay and alert/confirm modal API.",
            "provider": True,
            "appShellLayout": True,
            "globalUiState": True,
            "authGuard": False,
            "routeProtection": False,
            "loginFeaturePolicy": False,
            "localStorageSessionStorage": False,
            "browserApi": False,
            "reactContext": True,
            "componentsDependency": False,
            "commonUiFit": "Possible but weaker than layout because it is an app-level provider, not a reusable leaf UI component.",
            "layoutFit": "Strong fit.",
        }
        recommendation = {
            "target": "src/components/layout/AppProviders.tsx",
            "choice": "A",
            "reason": "App shell/global provider ownership fits components/layout better than common/ui.",
        }
        risk = {"level": "MEDIUM", "reasons": ["useUi has many feature consumers", "TestWorkspace imports useUi directly"]}
    else:
        role = {
            "mainResponsibility": "Client-side auth guard that checks stored login state and redirects unauthenticated users to /login.",
            "provider": False,
            "appShellLayout": False,
            "globalUiState": False,
            "authGuard": True,
            "routeProtection": True,
            "loginFeaturePolicy": True,
            "layoutWrapper": True,
            "localStorageSessionStorage": True,
            "browserApi": True,
            "reactContext": False,
            "componentsDependency": False,
            "commonUiFit": "Weak: it imports login/auth policy and is not generic UI.",
            "loginUiFit": "Strong fit.",
            "layoutFit": "Possible but weaker than login/ui.",
        }
        recommendation = {
            "target": "src/components/login/ui/RequireLogin.tsx",
            "choice": "B",
            "reason": "Auth guard is login feature UI/policy and has only app route consumers.",
        }
        risk = {"level": "LOW_MEDIUM", "reasons": ["Two route imports need updates", "No TestWorkspace direct import found"]}
    test_rows = [r for r in imported_by if r["testWorkspaceImpact"]]
    return {
        "currentPath": rel(path),
        "lineCount": line_count(text),
        "imports": imports,
        "exports": exports,
        "exportedComponentsHooksFunctions": exported_names,
        "importedBy": imported_by,
        "symbolHits": {name: scan_symbol_hits(name) for name in exported_names + ([kind] if kind not in exported_names else [])},
        "role": role,
        "targetCandidates": target_candidates(kind),
        "recommendation": recommendation,
        "risk": risk,
        "testWorkspaceImpact": {
            "status": "TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY" if test_rows else "NO_TEST_IMPACT",
            "directImport": bool(test_rows),
            "rows": test_rows,
            "requiresLogicChange": False,
            "note": "Import path-only update needed" if test_rows else "No TestWorkspace import found",
        },
    }


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    TMP.mkdir(exist_ok=True)
    files = [analyze_file(path) for path in FILES]
    _, dirty_out = run(["git", "status", "--short"])
    dirty = [line for line in dirty_out.splitlines() if line and not line.startswith("warning:")]
    typecheck = load_result("codex_components_common_ownership_precheck_typecheck.json")
    build = load_result("codex_components_common_ownership_precheck_build.json")
    imported_rows = []
    for item in files:
        for row in item["importedBy"]:
            imported_rows.append({"source": item["currentPath"], **row})

    ownership_summary = {
        "AppProviders": "src/components/layout/AppProviders.tsx",
        "RequireLogin": "src/components/login/ui/RequireLogin.tsx",
        "keepComponentsCommon": False,
        "rationale": "AppProviders is app-shell/global UI context; RequireLogin is login/auth guard policy. They should be split into layout and login/ui rather than common/ui.",
    }
    move_phases = [
        {
            "phase": "CC-1",
            "name": "Move AppProviders to components/layout",
            "target": "src/components/layout/AppProviders.tsx",
            "risk": "MEDIUM",
            "note": "Requires many useUi import path updates including TestWorkspace import-only update.",
        },
        {
            "phase": "CC-2",
            "name": "Move RequireLogin to components/login/ui",
            "target": "src/components/login/ui/RequireLogin.tsx",
            "risk": "LOW_MEDIUM",
            "note": "Requires two app route import updates.",
        },
        {
            "phase": "CC-3",
            "name": "Verify components/common empty",
            "target": "src/components/common",
            "risk": "LOW",
            "note": "Remove folder only if empty in a later move step; not in this precheck.",
        },
    ]
    static_checks = [
        "target files exist",
        "source files absent after move",
        "src/components/common is empty or absent",
        "import paths resolve",
        "common/ui files do not import components/*",
        "TestWorkspace changes are import-path-only if AppProviders moves",
        "RunOCR/Template checks PASS",
        "LIB checks PASS",
        "typecheck/build PASS",
    ]
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "projectRoot": "mysuit-ocr",
        "task": TASK,
        "codeModified": False,
        "dirtyStatus": {"entries": dirty},
        "files": files,
        "ownershipSummary": ownership_summary,
        "movePhases": move_phases,
        "staticCheckPlan": {
            "scripts": [
                "tmp/check_app_providers_layout_move_cc1.mjs",
                "tmp/check_require_login_ui_move_cc2.mjs",
                "tmp/check_components_common_empty_cc3.mjs",
            ],
            "items": static_checks,
        },
        "validationPlan": [
            "No production code changes in precheck.",
            "Actual moves should be split because targets differ.",
            "Do not modify TestWorkspace logic; AppProviders move may require import path-only update.",
        ],
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "Run CC-1 AppProviders -> components/layout move as a dedicated step, with TestWorkspace import-only approval noted.",
            "Run CC-2 RequireLogin -> components/login/ui move as a separate route-wrapper step.",
            "Verify components/common empty afterward.",
        ],
    }
    json_path = DOCS / f"{REPORT}.json"
    md_path = DOCS / f"{REPORT}.md"
    csv_path = DOCS / "FRONTEND_COMPONENTS_COMMON_OWNERSHIP_MAP_20260522.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = f"""# FRONTEND components/common ownership precheck

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `{TASK}`

## 2. 코드 수정 여부
- codeModified: false
- 운영 코드 수정 없음
- 파일 이동/import 수정/rename/fixture/templates/backend 수정 없음

## 3. 생성 파일
- `tmp/codex_frontend_components_common_ownership_precheck.py`
- `docs/{REPORT}.md`
- `docs/{REPORT}.json`
- `docs/FRONTEND_COMPONENTS_COMMON_OWNERSHIP_MAP_20260522.csv`
- `ocr-server/logs/codex_{TASK}.out.log`
- `ocr-server/logs/codex_{TASK}.err.log`

## 4. 분석 범위
- `src/components/common/AppProviders.tsx`
- `src/components/common/RequireLogin.tsx`
- `src/app/**`
- `src/components/runocr/**`, `template/**`, `history/**`, `restore/**`, `autorestore/**`, `login/**`, `layout/**`
- `src/components/test/TestWorkspace.tsx` 읽기 전용
- `src/common/**`
- `src/lib/**`

## 5. AppProviders 역할/import 영향
- currentPath: `src/components/common/AppProviders.tsx`
- lineCount: {files[0]['lineCount']}
- recommendation: `{files[0]['recommendation']['target']}`
- 역할: {files[0]['role']['mainResponsibility']}
- Provider/global UI state/context: true
- common/ui 적합성: {files[0]['role']['commonUiFit']}
- layout 적합성: {files[0]['role']['layoutFit']}

| importedBy | importPath | feature | TestWorkspace |
|---|---|---|---|
"""
    for row in files[0]["importedBy"]:
        md += f"| `{row['file']}` | `{row['importPath']}` | {row['feature']} | {row['testWorkspaceImpact']} |\n"
    md += f"""

## 6. RequireLogin 역할/import 영향
- currentPath: `src/components/common/RequireLogin.tsx`
- lineCount: {files[1]['lineCount']}
- recommendation: `{files[1]['recommendation']['target']}`
- 역할: {files[1]['role']['mainResponsibility']}
- auth guard / route protection / login feature policy: true
- common/ui 적합성: {files[1]['role']['commonUiFit']}
- login/ui 적합성: {files[1]['role']['loginUiFit']}

| importedBy | importPath | feature | TestWorkspace |
|---|---|---|---|
"""
    for row in files[1]["importedBy"]:
        md += f"| `{row['file']}` | `{row['importPath']}` | {row['feature']} | {row['testWorkspaceImpact']} |\n"
    md += """

## 7. target path 후보 비교
### AppProviders
| target | risk | recommended | route/common boundary |
|---|---|---|---|
"""
    for c in files[0]["targetCandidates"]:
        md += f"| `{c['target']}` | {c['risk']} | {c['recommended']} | {c['routeImpact']} / {c['commonBoundaryRisk']} |\n"
    md += """

### RequireLogin
| target | risk | recommended | route/common boundary |
|---|---|---|---|
"""
    for c in files[1]["targetCandidates"]:
        md += f"| `{c['target']}` | {c['risk']} | {c['recommended']} | {c['routeImpact']} / {c['commonBoundaryRisk']} |\n"
    md += f"""

## 8. TestWorkspace 영향
- AppProviders: `{files[0]['testWorkspaceImpact']['status']}`
- RequireLogin: `{files[1]['testWorkspaceImpact']['status']}`
- AppProviders 이동 시 `TestWorkspace.tsx`는 import path-only 수정 후보다. 로직 수정은 필요하지 않다.

## 9. 이동 순서 추천
- CC-1: `AppProviders.tsx` -> `src/components/layout/AppProviders.tsx`
- CC-2: `RequireLogin.tsx` -> `src/components/login/ui/RequireLogin.tsx`
- CC-3: `src/components/common` empty/absent 확인
- 둘은 target ownership이 다르므로 함께 이동보다 분리 micro-step을 권장한다.

## 10. static check 설계
"""
    for item in static_checks:
        md += f"- {item}\n"
    md += f"""

## 11. dirty 상태
```text
{chr(10).join(dirty)}
```

## 12. typecheck/build 결과
- typecheck: {typecheck.get('status')} / exitCode {typecheck.get('exitCode')}
- build: {build.get('status')} / exitCode {build.get('exitCode')}
- known stderr noise: ESLint `nextVitals is not iterable`는 exit code 0이면 known issue

## 13. 다음 작업 제안
- AppProviders layout 이동을 먼저 별도 step으로 진행.
- RequireLogin login/ui 이동은 다음 별도 step으로 진행.
- 마지막에 components/common empty check를 수행.
"""
    md_path.write_text(md, encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source",
                "file",
                "importPath",
                "importedSymbols",
                "feature",
                "importKind",
                "needsImportUpdateOnMove",
                "testWorkspaceImpact",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in imported_rows:
            writer.writerow(row)

    print(json.dumps({
        "status": "ok",
        "json": rel(json_path),
        "md": rel(md_path),
        "csv": rel(csv_path),
        "recommendations": ownership_summary,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
