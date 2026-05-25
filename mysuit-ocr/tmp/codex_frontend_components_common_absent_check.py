from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASK = "CODEX_FRONTEND_COMPONENTS_COMMON_ABSENT_CHECK_NO_PROD_MODIFY"
REPORT = "FRONTEND_COMPONENTS_COMMON_ABSENT_CHECK_20260522"
DOCS = ROOT / "docs"
TMP = ROOT / "tmp"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


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


def rg(pattern: str, *paths: str) -> list[dict]:
    code, out = run(["rg", "-n", pattern, *paths])
    rows = []
    if code not in (0, 1):
        return [{"file": "<rg-error>", "line": 0, "text": out.strip()}]
    for line in out.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            rows.append({"file": parts[0].replace("\\", "/"), "line": int(parts[1]), "text": parts[2]})
    return rows


def check_exports(path: Path, default_name: str, named: list[str]) -> dict:
    text = read(path)
    return {
        "defaultExport": bool(re.search(r"export\s+default\s+function\s+" + re.escape(default_name), text)),
        "namedExports": {name: bool(re.search(r"export\s+(?:function|const|type|interface)\s+" + re.escape(name), text)) for name in named},
    }


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    components_common = ROOT / "src/components/common"
    app_providers = ROOT / "src/components/layout/AppProviders.tsx"
    require_login = ROOT / "src/components/login/ui/RequireLogin.tsx"
    old_app = ROOT / "src/components/common/AppProviders.tsx"
    old_login = ROOT / "src/components/common/RequireLogin.tsx"

    remaining = []
    if components_common.exists():
        remaining = [rel(p) for p in components_common.rglob("*") if p.is_file()]

    residue_patterns = [
        "components/common",
        "components/common/AppProviders",
        "components/common/RequireLogin",
        r"\.\./common/AppProviders",
        r"\.\./\.\./common/AppProviders",
        r"\.\./common/RequireLogin",
        r"\.\./\.\./common/RequireLogin",
        "@/components/common/AppProviders",
        "@/components/common/RequireLogin",
    ]
    residues = {pattern: rg(pattern, "src") for pattern in residue_patterns}
    blocking_residues = {
        pattern: rows for pattern, rows in residues.items()
        if rows and not (len(rows) == 1 and rows[0]["file"] == "<rg-error>")
    }

    app_imports = rg("AppProviders|useUi", "src")
    require_imports = rg("RequireLogin", "src")

    _, dirty_out = run(["git", "status", "--short"])
    dirty = [line for line in dirty_out.splitlines() if line and not line.startswith("warning:")]

    runners = load_json(TMP / "codex_components_common_absent_check_runner_results.json", [])
    typecheck = load_json(TMP / "codex_components_common_absent_check_typecheck.json", {})
    build = load_json(TMP / "codex_components_common_absent_check_build.json", {})

    checks = [
        {"name": "components_common_absent_or_empty", "status": "PASS" if (not components_common.exists() or len(remaining) == 0) else "FAIL"},
        {"name": "app_providers_exists", "status": "PASS" if app_providers.exists() else "FAIL"},
        {"name": "require_login_exists", "status": "PASS" if require_login.exists() else "FAIL"},
        {"name": "old_app_providers_absent", "status": "PASS" if not old_app.exists() else "FAIL"},
        {"name": "old_require_login_absent", "status": "PASS" if not old_login.exists() else "FAIL"},
        {"name": "components_common_import_residue_absent", "status": "PASS" if not blocking_residues else "FAIL"},
        {"name": "app_providers_exports", "status": "PASS" if app_providers.exists() and check_exports(app_providers, "AppProviders", ["useUi"])["defaultExport"] and check_exports(app_providers, "AppProviders", ["useUi"])["namedExports"]["useUi"] else "FAIL"},
        {"name": "require_login_default_export", "status": "PASS" if require_login.exists() and check_exports(require_login, "RequireLogin", [])["defaultExport"] else "FAIL"},
    ]
    for item in runners:
        checks.append({"name": item.get("name"), "status": item.get("status"), "exitCode": item.get("exitCode"), "command": item.get("command")})
    checks.append({"name": "typecheck", "status": typecheck.get("status"), "exitCode": typecheck.get("exitCode")})
    checks.append({"name": "build", "status": build.get("status"), "exitCode": build.get("exitCode")})

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "task": TASK,
        "codeModified": False,
        "componentsCommon": {
            "exists": components_common.exists(),
            "isEmpty": len(remaining) == 0,
            "remainingFiles": remaining,
        },
        "appProviders": {
            "expectedPath": "src/components/layout/AppProviders.tsx",
            "exists": app_providers.exists(),
            "oldPathAbsent": not old_app.exists(),
            "exports": check_exports(app_providers, "AppProviders", ["useUi"]),
            "importResidues": {k: v for k, v in residues.items() if "AppProviders" in k or k == "components/common"},
            "currentReferences": app_imports,
        },
        "requireLogin": {
            "expectedPath": "src/components/login/ui/RequireLogin.tsx",
            "exists": require_login.exists(),
            "oldPathAbsent": not old_login.exists(),
            "exports": check_exports(require_login, "RequireLogin", []),
            "importResidues": {k: v for k, v in residues.items() if "RequireLogin" in k or k == "components/common"},
            "currentReferences": require_imports,
        },
        "checks": checks,
        "typecheck": typecheck,
        "build": build,
        "dirtyStatus": {"entries": dirty},
        "nextSteps": [
            "Proceed to the next structural cleanup area if all checks remain PASS.",
            "Keep TestWorkspace structure work out of scope until separately approved.",
            "After remaining structure checks, proceed toward Template table column definition work.",
        ],
    }
    overall = all(c.get("status") == "PASS" for c in checks)
    report["overall"] = "PASS" if overall else "FAIL"

    json_path = DOCS / f"{REPORT}.json"
    md_path = DOCS / f"{REPORT}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = f"""# FRONTEND components/common absent check

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `{TASK}`

## 2. 코드 수정 여부
- codeModified: false
- 운영 코드 수정 없음
- 파일 이동/import 수정/rename/fixture/templates/backend 수정 없음

## 3. 생성 파일
- `tmp/codex_frontend_components_common_absent_check.py`
- `docs/{REPORT}.md`
- `docs/{REPORT}.json`
- `ocr-server/logs/codex_{TASK}.out.log`
- `ocr-server/logs/codex_{TASK}.err.log`

## 4. 검증 범위
- `src/components/layout/AppProviders.tsx`
- `src/components/login/ui/RequireLogin.tsx`
- `src/app/**`
- `src/components/**`
- `src/common/**`
- `src/lib/**`
- `src/components/test/TestWorkspace.tsx` 읽기 전용

## 5. components/common absent 상태
- exists: {report['componentsCommon']['exists']}
- isEmpty: {report['componentsCommon']['isEmpty']}
- remainingFiles: {report['componentsCommon']['remainingFiles']}

## 6. AppProviders 위치/export 확인
- expectedPath: `src/components/layout/AppProviders.tsx`
- exists: {report['appProviders']['exists']}
- oldPathAbsent: {report['appProviders']['oldPathAbsent']}
- default export AppProviders: {report['appProviders']['exports']['defaultExport']}
- named export useUi: {report['appProviders']['exports']['namedExports'].get('useUi')}

## 7. RequireLogin 위치/export 확인
- expectedPath: `src/components/login/ui/RequireLogin.tsx`
- exists: {report['requireLogin']['exists']}
- oldPathAbsent: {report['requireLogin']['oldPathAbsent']}
- default export RequireLogin: {report['requireLogin']['exports']['defaultExport']}

## 8. import 잔존 검색 결과
"""
    for pattern, rows in residues.items():
        md += f"- `{pattern}`: {len(rows)} hit(s)\n"
        for row in rows[:10]:
            md += f"  - `{row['file']}:{row['line']}` {row['text'].strip()}\n"
    md += """

## 9. runner/static check 결과
| check | status | exitCode |
|---|---|---|
"""
    for c in checks:
        md += f"| {c.get('name')} | {c.get('status')} | {c.get('exitCode', '')} |\n"
    md += f"""

## 10. typecheck/build 결과
- typecheck: {typecheck.get('status')} / exitCode {typecheck.get('exitCode')}
- build: {build.get('status')} / exitCode {build.get('exitCode')}
- known stderr noise: ESLint `nextVitals is not iterable`는 exit code 0이면 known issue

## 11. dirty 상태
```text
{chr(10).join(dirty)}
```

## 12. 다음 작업 제안
- components/common 정리 상태는 `{report['overall']}`.
- 다음 구조 cleanup 영역으로 이동 가능.
- TestWorkspace 구조 정리는 별도 승인 전까지 보류.
"""
    md_path.write_text(md, encoding="utf-8")

    print(json.dumps({"status": report["overall"], "json": rel(json_path), "md": rel(md_path)}, ensure_ascii=False))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
