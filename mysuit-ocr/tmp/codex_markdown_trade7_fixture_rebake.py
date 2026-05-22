from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "MARKDOWN-V1-TRADE7-FIXTURE-REBAKE"
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OCR_ROOT = REPO / "ocr-server"
FIXTURE_ROOT = ROOT / "tmp" / "fixtures" / "markdown_v1"
TRADE7_FIXTURE = FIXTURE_ROOT / "invoice_statement" / "trade_7_7pdf.md"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
LOCK_SCRIPT = ROOT / "tmp" / "codex_markdown_contract_fixture_lock.py"
DOC_MD = ROOT / "docs" / "MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.md"
DOC_JSON = ROOT / "docs" / "MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.json"
LOG_DIR = OCR_ROOT / "logs"
TEMPLATES_JSON = OCR_ROOT / "data" / "templates.json"
REVIEW_LOG = OCR_ROOT / "data" / "review_log.jsonl"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def run_command(args: list[str], cwd: Path, timeout: int = 300) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            shell=False,
        )
        return {
            "command": " ".join(args),
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "exitCode": proc.returncode,
            "durationSeconds": round(time.perf_counter() - started, 3),
            "stdoutTail": proc.stdout[-5000:],
            "stderrTail": proc.stderr[-5000:],
            "knownStderrNoise": "nextVitals is not iterable" in proc.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(args),
            "status": "TIMEOUT",
            "exitCode": None,
            "durationSeconds": round(time.perf_counter() - started, 3),
            "stdoutTail": (exc.stdout or "")[-5000:] if isinstance(exc.stdout, str) else "",
            "stderrTail": (exc.stderr or "")[-5000:] if isinstance(exc.stderr, str) else "",
            "knownStderrNoise": False,
        }


def git_status() -> list[str]:
    result = run_command(["git", "status", "--short"], REPO, timeout=60)
    return [line for line in result["stdoutTail"].splitlines() if line.strip()]


def load_lock_module() -> Any:
    spec = importlib.util.spec_from_file_location("markdown_lock", LOCK_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {LOCK_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_business_line(markdown: str) -> dict[str, Any]:
    lines = markdown.splitlines()
    line = next((item for item in lines if "113-85-04425" in item), "")
    cells = [cell.strip() for cell in line.strip("|").split("|")] if line else []
    return {
        "line": line,
        "lineNumber": lines.index(line) + 1 if line in lines else None,
        "value": cells[2] if len(cells) >= 3 else "",
        "confidence": cells[3] if len(cells) >= 4 else "",
    }


def markdown_fixture_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(FIXTURE_ROOT).as_posix()): sha256(path)
        for path in sorted(FIXTURE_ROOT.rglob("*.md"))
    }


def update_manifest(old_info: dict[str, Any], new_info: dict[str, Any]) -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    case = next(item for item in manifest["cases"] if item["caseId"] == "trade_7_7pdf")
    case["fixtureBytes"] = TRADE7_FIXTURE.stat().st_size
    case["lineCount"] = len(read_text(TRADE7_FIXTURE).splitlines())
    case["rebakedAt"] = datetime.now().isoformat(timespec="seconds")
    case["decision"] = "REBAKE_MARKDOWN_FIXTURE"
    case["reason"] = "TPL-3AFD383E template coordinate update accepted; current backend actual has normalized buyer business number and higher confidence."
    case["previousExpected"] = {
        "value": old_info["value"],
        "confidence": old_info["confidence"],
        "line": old_info["line"],
    }
    case["newExpected"] = {
        "value": new_info["value"],
        "confidence": new_info["confidence"],
        "line": new_info["line"],
    }
    case["templateDirtyAccepted"] = {
        "templateId": "TPL-3AFD383E",
        "note": "templates.json remains dirty by design for this rebake; no rollback performed.",
    }
    manifest["updatedAt"] = datetime.now().isoformat(timespec="seconds")
    write_json(MANIFEST_PATH, manifest)
    return manifest


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        if isinstance(value, (list, dict)):
            value = json.dumps(value, ensure_ascii=False)
        return str(value if value is not None else "").replace("\n", "<br>").replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    out.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)
    return "\n".join(out)


def write_reports(report: dict[str, Any]) -> None:
    DOC_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result_rows = [
        ["markdown", report["validation"]["markdown"]["status"], report["validation"]["markdown"]["exitCode"], report["validation"]["markdown"]["durationSeconds"]],
        ["table_view_model", report["validation"]["tableViewModel"]["status"], report["validation"]["tableViewModel"]["exitCode"], report["validation"]["tableViewModel"]["durationSeconds"]],
        ["clean_json", report["validation"]["cleanJson"]["status"], report["validation"]["cleanJson"]["exitCode"], report["validation"]["cleanJson"]["durationSeconds"]],
        ["typecheck", report["validation"]["typecheck"]["status"], report["validation"]["typecheck"]["exitCode"], report["validation"]["typecheck"]["durationSeconds"]],
        ["build", report["validation"]["build"]["status"], report["validation"]["build"]["exitCode"], report["validation"]["build"]["durationSeconds"]],
    ]
    unchanged_rows = [[path, ok] for path, ok in report["fixtureChangeCheck"]["otherMarkdownFixturesUnchanged"].items()]
    md = f"""# MARKDOWN V1 TRADE7 FIXTURE REBAKE 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 frontend/backend 코드 수정 없음.
- backend parser, `templates.json`, Clean JSON fixture, table view model fixture 수정 없음.
- markdown fixture는 `trade_7_7pdf.md`만 갱신.
- markdown manifest는 trade_7 rebake metadata만 갱신.

## 3. 수정 파일
- `tmp/fixtures/markdown_v1/invoice_statement/trade_7_7pdf.md`
- `tmp/fixtures/markdown_v1/manifest.json`
- `tmp/codex_markdown_trade7_fixture_rebake.py`
- `docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.md`
- `docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.json`

## 4. rebake 결정 이유
- precheck 결과 drift는 2C frontend code와 직접 인과가 없고, backend `TPL-3AFD383E` template 좌표 변경으로 인한 현재 backend actual 차이로 판단됨.
- 사용자가 현재 actual을 새 기준으로 인정함.
- 새 결과는 사업자번호 괄호가 제거되고 confidence가 `100.0%`로 개선됨.

## 5. old expected / new expected 비교
| item | old | new |
| --- | --- | --- |
| value | `{report['oldExpected']['value']}` | `{report['newExpected']['value']}` |
| confidence | `{report['oldExpected']['confidence']}` | `{report['newExpected']['confidence']}` |
| line | `{report['oldExpected']['line']}` | `{report['newExpected']['line']}` |

## 6. TPL-3AFD383E template dirty와의 관계
- `ocr-server/data/templates.json`은 수정하지 않음.
- `TPL-3AFD383E` dirty 좌표 변경을 이번 rebake의 기준으로 수용.
- `TPL-95328E52` dirty는 이번 범위 밖이며 follow-up 후보로 기록.

## 7. 수정하지 않은 범위
- `src/**`
- `ocr-server/data/templates.json`
- backend parser/extractors
- Clean JSON fixtures
- table_view_model fixtures
- trade_7 외 markdown fixtures

## 8. runner 결과
{md_table(['check', 'status', 'exit', 'seconds'], result_rows)}

## 9. 다른 fixture 변경 확인
{md_table(['fixture', 'unchanged'], unchanged_rows)}

## 10. known stderr noise
- build known stderr noise observed: `{report['validation']['build']['knownStderrNoise']}`
- issue: `ESLint: nextVitals is not iterable`
- exit code 0이면 non-blocking.

## 11. 남은 이슈
- `TPL-95328E52` dirty 영향은 이번 작업 범위 밖. 별도 precheck 후보.
- `review_log.jsonl` append 여부: {report['reviewLogImpact']}

## 12. 다음 작업 제안
- RunOCR UI split precheck
- Template folder ownership precheck
- TPL-95328E52 dirty 영향 precheck
- common/utils 이동은 feature 폴더 안정화 후 진행
- TestWorkspace는 사용자 확인 후 진행
"""
    DOC_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    before_status = git_status()
    before_hashes = markdown_fixture_hashes()
    before_templates_hash = sha256(TEMPLATES_JSON)
    before_clean_hashes = {str(p.relative_to(ROOT).as_posix()): sha256(p) for p in (ROOT / "tmp" / "fixtures" / "clean_json_v1").rglob("*") if p.is_file()}
    before_tvm_hashes = {str(p.relative_to(ROOT).as_posix()): sha256(p) for p in (ROOT / "tmp" / "fixtures" / "table_view_model_v1").rglob("*") if p.is_file()}
    review_before_size = file_size(REVIEW_LOG)
    old_md = read_text(TRADE7_FIXTURE)
    old_info = extract_business_line(old_md)

    lock = load_lock_module()
    api_url, backend_proc, api_source = lock.start_backend_if_needed(lock.DEFAULT_API_URL)
    try:
        templates = lock.load_templates()
        manifest = read_json(MANIFEST_PATH)
        case_manifest = next(item for item in manifest["cases"] if item["caseId"] == "trade_7_7pdf")
        case = next(item for item in lock.CASES if item["caseId"] == "trade_7_7pdf")
        template = lock.template_by_id(templates, case_manifest["templateId"])
        if template is None:
            template = lock.template_by_name_file(templates, case["templateName"], case["file"])
        if template is None:
            raise RuntimeError("Could not resolve TPL-3AFD383E / trade_7 template")
        input_path = lock.INVOICE_DATA_DIR / case["file"]
        raw, api_meta = lock.post_ocr(api_url, input_path, template, "invoice_statement")
        new_md, markdown_meta = lock.to_markdown(raw, template, case["templateName"])
    finally:
        lock.stop_backend(backend_proc)

    normalized_new_md = new_md.replace("\r\n", "\n")
    TRADE7_FIXTURE.write_text(normalized_new_md, encoding="utf-8", newline="\n")
    new_info = extract_business_line(normalized_new_md)
    updated_manifest = update_manifest(old_info, new_info)
    after_hashes = markdown_fixture_hashes()
    after_templates_hash = sha256(TEMPLATES_JSON)
    after_clean_hashes = {str(p.relative_to(ROOT).as_posix()): sha256(p) for p in (ROOT / "tmp" / "fixtures" / "clean_json_v1").rglob("*") if p.is_file()}
    after_tvm_hashes = {str(p.relative_to(ROOT).as_posix()): sha256(p) for p in (ROOT / "tmp" / "fixtures" / "table_view_model_v1").rglob("*") if p.is_file()}
    review_after_size = file_size(REVIEW_LOG)

    other_unchanged = {
        path: before_hashes[path] == after_hashes.get(path)
        for path in before_hashes
        if path != "invoice_statement/trade_7_7pdf.md"
    }
    print("[rebake] trade_7 markdown fixture updated", flush=True)

    markdown = run_command(
        [sys.executable, "tmp/codex_markdown_contract_fixture_lock.py", "--check", "--phase", "post_TRADE7_REBAKE_20260522"],
        ROOT,
        timeout=420,
    )
    if markdown["status"] != "PASS":
        venv_python = OCR_ROOT / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            markdown = run_command(
                [str(venv_python), "tmp/codex_markdown_contract_fixture_lock.py", "--check", "--phase", "post_TRADE7_REBAKE_20260522"],
                ROOT,
                timeout=420,
            )
    table_vm = run_command(["node", "tmp/check_table_view_model_v1_fixtures_js.mjs"], ROOT, timeout=180)
    clean_json = run_command(["node", "tmp/check_clean_json_v1_fixtures_js.mjs"], ROOT, timeout=180)
    typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180)
    build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "task": TASK,
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "api": {"url": api_url, "source": api_source, "meta": api_meta},
        "oldExpected": old_info,
        "newExpected": new_info,
        "markdownMeta": markdown_meta,
        "modifiedFiles": [
            "tmp/fixtures/markdown_v1/invoice_statement/trade_7_7pdf.md",
            "tmp/fixtures/markdown_v1/manifest.json",
            "tmp/codex_markdown_trade7_fixture_rebake.py",
            "docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.md",
            "docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.json",
        ],
        "notModified": {
            "templatesJsonUnchangedByThisScript": before_templates_hash == after_templates_hash,
            "cleanJsonFixturesUnchanged": before_clean_hashes == after_clean_hashes,
            "tableViewModelFixturesUnchanged": before_tvm_hashes == after_tvm_hashes,
        },
        "fixtureChangeCheck": {
            "trade7Changed": before_hashes.get("invoice_statement/trade_7_7pdf.md") != after_hashes.get("invoice_statement/trade_7_7pdf.md"),
            "otherMarkdownFixturesUnchanged": other_unchanged,
        },
        "manifestTrade7": next(item for item in updated_manifest["cases"] if item["caseId"] == "trade_7_7pdf"),
        "validation": {
            "markdown": markdown,
            "tableViewModel": table_vm,
            "cleanJson": clean_json,
            "typecheck": typecheck,
            "build": build,
        },
        "knownStderrNoise": {
            "id": "ISSUE-FRONTEND-BUILD-LOG-1",
            "message": "ESLint: nextVitals is not iterable",
            "observed": build["knownStderrNoise"],
            "blocking": False if build["exitCode"] == 0 else True,
        },
        "reviewLogImpact": {
            "beforeBytes": review_before_size,
            "afterBytes": review_after_size,
            "appendedBytes": max(0, review_after_size - review_before_size),
            "note": "Recorded only; no manual revert performed.",
        },
        "dirtyStatusBefore": before_status,
        "dirtyStatusAfter": git_status(),
        "remainingIssues": [
            "TPL-95328E52 dirty is outside this task and should be checked separately if validation noise appears.",
        ],
        "nextSteps": [
            "RunOCR UI split precheck",
            "Template folder ownership precheck",
            "TPL-95328E52 dirty impact precheck",
            "Move common/utils after feature folders stabilize",
            "Gate TestWorkspace work behind explicit user confirmation",
        ],
    }
    write_reports(report)
    print(f"[write] {DOC_JSON}", flush=True)
    print(f"[write] {DOC_MD}", flush=True)
    checks = [markdown, table_vm, clean_json, typecheck, build]
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    print(f"[done] {status}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
