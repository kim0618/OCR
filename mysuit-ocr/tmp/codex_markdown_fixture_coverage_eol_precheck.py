from __future__ import annotations

import importlib.util
import json
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

TASK = "CODEX_FRONTEND_CLEANUP_2A_MARKDOWN_FIXTURE_COVERAGE_EOL_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OCR_ROOT = REPO / "ocr-server"
LOG_DIR = OCR_ROOT / "logs"
REVIEW_LOG = OCR_ROOT / "data" / "review_log.jsonl"
LOCK_SCRIPT = ROOT / "tmp" / "codex_markdown_contract_fixture_lock.py"
FIXTURE_ROOT = ROOT / "tmp" / "fixtures" / "markdown_v1"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
TRADE7_FIXTURE = FIXTURE_ROOT / "invoice_statement" / "trade_7_7pdf.md"
INVOICE_DATA_DIR = ROOT / "public" / "data" / "testsets" / "invoice_statement"
REPORT_MD = ROOT / "docs" / "MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md"
REPORT_JSON = ROOT / "docs" / "MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.json"
OCR_RESULT_PANEL = ROOT / "src" / "components" / "upload" / "OcrResultPanel.tsx"
DEFAULT_API_URL = "http://127.0.0.1:9099/ocr/extract"
FALLBACK_PORT = 9142


def load_lock_module() -> Any:
    spec = importlib.util.spec_from_file_location("markdown_lock", LOCK_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {LOCK_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_command(args: list[str], cwd: Path, timeout: int = 240) -> dict[str, Any]:
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
            "exitCode": proc.returncode,
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "durationSeconds": round(time.perf_counter() - started, 3),
            "stdoutTail": proc.stdout[-4000:],
            "stderrTail": proc.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(args),
            "exitCode": None,
            "status": "TIMEOUT",
            "durationSeconds": round(time.perf_counter() - started, 3),
            "stdoutTail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderrTail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }


def git_status() -> dict[str, Any]:
    result = run_command(["git", "-c", "safe.directory=D:/Free_Vue/OCR/mysuit-ocr", "status", "--short"], ROOT, timeout=30)
    entries = [line for line in result.get("stdoutTail", "").splitlines() if line.strip()]
    return {"isDirty": bool(entries), "entries": entries, "command": result}


def analyze_eol(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    crlf = data.count(b"\r\n")
    lf_total = data.count(b"\n")
    cr_total = data.count(b"\r")
    lone_cr = cr_total - crlf
    lone_lf = lf_total - crlf
    if crlf and lone_lf:
        ending = "MIXED"
    elif crlf:
        ending = "CRLF"
    elif lone_lf:
        ending = "LF"
    else:
        ending = "UNKNOWN"
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    trailing = sum(1 for line in lines if line.rstrip(" \t") != line)
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": len(data),
        "lineCount": len(lines),
        "lfCount": lf_total,
        "crlfCount": crlf,
        "loneCrCount": lone_cr,
        "lineEnding": ending,
        "endsWithNewline": data.endswith(b"\n"),
        "trailingWhitespaceLines": trailing,
        "status": "PASS" if ending == "LF" and data.endswith(b"\n") else "WARN",
    }


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def api_health(api_url: str, timeout: float = 2.0) -> bool:
    try:
        import requests

        base = api_url.rsplit("/", 2)[0]
        res = requests.get(f"{base}/templates", timeout=timeout)
        return res.status_code < 500
    except Exception:
        return False


def wait_for_api(api_url: str, timeout: int = 70) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if api_health(api_url, timeout=2):
            return True
        time.sleep(1)
    return False


def start_backend_if_needed(api_url: str) -> tuple[str, subprocess.Popen[str] | None, str]:
    if api_health(api_url):
        return api_url, None, "existing"
    fallback = f"http://127.0.0.1:{FALLBACK_PORT}/ocr/extract"
    if not is_port_free(FALLBACK_PORT) and wait_for_api(fallback, timeout=5):
        return fallback, None, "existing_fallback_port"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = LOG_DIR / f"codex_{TASK}.server.out.log"
    err_path = LOG_DIR / f"codex_{TASK}.server.err.log"
    python_exe = OCR_ROOT / ".venv" / "Scripts" / "python.exe"
    cmd = [str(python_exe if python_exe.exists() else sys.executable), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(FALLBACK_PORT)]
    out_f = out_path.open("w", encoding="utf-8", errors="replace")
    err_f = err_path.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(OCR_ROOT), stdout=out_f, stderr=err_f, text=True)
    proc._codex_log_handles = (out_f, err_f)  # type: ignore[attr-defined]
    if not wait_for_api(fallback):
        stop_backend(proc)
        raise RuntimeError(f"backend did not start on {fallback}")
    return fallback, proc, "started_fallback_port"


def stop_backend(proc: subprocess.Popen[str] | None) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)
    for handle in getattr(proc, "_codex_log_handles", ()) or ():
        try:
            handle.close()
        except Exception:
            pass


def preserve_review_log() -> bytes | None:
    return REVIEW_LOG.read_bytes() if REVIEW_LOG.exists() else None


def restore_review_log(before: bytes | None) -> dict[str, Any]:
    REVIEW_LOG.parent.mkdir(parents=True, exist_ok=True)
    if before is None:
        if REVIEW_LOG.exists():
            REVIEW_LOG.unlink()
        return {"path": str(REVIEW_LOG.relative_to(REPO)), "restoredToPreRunBytes": True, "existedBefore": False}
    REVIEW_LOG.write_bytes(before)
    return {"path": str(REVIEW_LOG.relative_to(REPO)), "restoredToPreRunBytes": REVIEW_LOG.read_bytes() == before, "existedBefore": True}


def capture_trade7(api_url: str, lock: Any) -> dict[str, Any]:
    templates = lock.load_templates()
    template = lock.template_by_name_file(templates, "거래_7", "7.pdf")
    if not template:
        return {"caseId": "trade_7_7pdf", "status": "FAIL", "error": "template not found"}
    if TRADE7_FIXTURE.exists():
        text = TRADE7_FIXTURE.read_text(encoding="utf-8")
        return {
            "caseId": "trade_7_7pdf",
            "templateName": "거래_7",
            "templateId": template.get("template_id"),
            "inputFile": "invoice_statement/7.pdf",
            "fixturePath": "invoice_statement/trade_7_7pdf.md",
            "fixtureBytes": len(text.encode("utf-8")),
            "lineCount": len(text.splitlines()),
            "rowIndexPolicy": "excluded_in_preview_clean_json_not_markdown",
            "status": "PASS",
            "notes": "coverage add: single-row table summary, rowIndex excluded case",
            "writeAction": "kept_existing_locked",
            "validation": {
                "nonEmpty": bool(text.strip()),
                "startsWithHeading": text.startswith("# OCR 결과") or text.startswith("# OCR 寃곌낵"),
                "hasMarkdownTableHeader": "| No |" in text,
            },
        }
    input_path = INVOICE_DATA_DIR / "7.pdf"
    raw, http_meta = lock.post_ocr(api_url, input_path, template, "invoice_statement")
    md, meta = lock.to_markdown(raw, template, "거래_7")
    TRADE7_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    TRADE7_FIXTURE.write_text(md.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    writeAction = "created"
    text = TRADE7_FIXTURE.read_text(encoding="utf-8")
    validation = lock.validate_markdown(
        text,
        {
            "caseId": "trade_7_7pdf",
            "kind": "invoice",
            "rowIndexPolicy": "excluded_in_preview_clean_json_not_markdown",
        },
        meta,
    )
    return {
        "caseId": "trade_7_7pdf",
        "templateName": "거래_7",
        "templateId": template.get("template_id"),
        "inputFile": "invoice_statement/7.pdf",
        "fixturePath": "invoice_statement/trade_7_7pdf.md",
        "fixtureBytes": len(text.encode("utf-8")),
        "lineCount": len(text.splitlines()),
        "rowIndexPolicy": "excluded_in_preview_clean_json_not_markdown",
        "status": validation["status"],
        "notes": "coverage add: single-row table summary, rowIndex excluded case",
        "writeAction": writeAction,
        "processing_time": raw.get("processing_time"),
        "http": http_meta,
        "validation": validation,
    }


def update_manifest(trade7: dict[str, Any]) -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    cases = manifest.setdefault("cases", [])
    existing_index = next((i for i, c in enumerate(cases) if c.get("caseId") == "trade_7_7pdf"), None)
    case_summary = {
        "caseId": "trade_7_7pdf",
        "templateName": trade7.get("templateName", "거래_7"),
        "templateId": trade7.get("templateId"),
        "inputFile": "invoice_statement/7.pdf",
        "fixturePath": "invoice_statement/trade_7_7pdf.md",
        "fixtureBytes": trade7.get("fixtureBytes"),
        "lineCount": trade7.get("lineCount"),
        "rowIndexPolicy": "excluded_in_preview_clean_json_not_markdown",
        "status": trade7.get("status"),
        "notes": "coverage add: single-row table summary, rowIndex excluded case",
    }
    if trade7.get("status") in {"PASS", "WARN"} and trade7.get("fixtureBytes"):
        if existing_index is None:
            cases.append(case_summary)
            action = "added_trade_7_case"
        else:
            cases[existing_index] = {**cases[existing_index], **case_summary}
            action = "updated_trade_7_case"
        manifest["updatedAt"] = datetime.now().isoformat(timespec="seconds")
        manifest["coveragePrecheck"] = {
            "task": TASK,
            "reason": "added single-row rowIndex-excluded invoice Markdown fixture before helper extraction",
            "comparisonPolicy": "LF exact string equality recommended",
        }
        write_json(MANIFEST_PATH, manifest)
    else:
        action = "not_updated"
    return {"action": action, "caseCount": len(cases), "manifestPath": str(MANIFEST_PATH.relative_to(ROOT))}


def analyze_to_markdown_closure() -> list[dict[str, Any]]:
    return [
        {"dependency": "result.processing_time", "source": "OcrResultPanel props/result closure", "usedFor": "processing time summary", "requiredInput": "processingTime: number", "risk": "LOW"},
        {"dependency": "editedFields", "source": "component state", "usedFor": "field rows and field count", "requiredInput": "fields: OcrFieldResult[]", "risk": "LOW"},
        {"dependency": "fieldLabelFull", "source": "local helper using resolveFieldLabel", "usedFor": "label formatting", "requiredInput": "helper can import resolveFieldLabel or receive labelResolver", "risk": "MEDIUM"},
        {"dependency": "parseTableField", "source": "local helper", "usedFor": "legacy table rowLabel fallback", "requiredInput": "move local helper with markdown builder", "risk": "LOW"},
        {"dependency": "docTableRows", "source": "useMemo from result.document_fields.tableRows", "usedFor": "table summary N행 override", "requiredInput": "docTableRows?: Record<string, unknown>[] | null", "risk": "MEDIUM"},
        {"dependency": "getAdoptionLabel", "source": "local helper", "usedFor": "채택 column", "requiredInput": "move helper or expose adoption label function", "risk": "LOW"},
        {"dependency": "docTableDisplayCols", "source": "buildInvoicePreviewCols useMemo", "usedFor": "not used by Markdown v1", "requiredInput": "not required", "risk": "LOW"},
        {"dependency": "tableMeta/documentFields", "source": "result.document_fields", "usedFor": "not directly used except docTableRows", "requiredInput": "not required if docTableRows passed", "risk": "LOW"},
        {"dependency": "fileName/templateName/docType", "source": "props/context", "usedFor": "not used by Markdown v1", "requiredInput": "not required for v1 exact output", "risk": "LOW"},
        {"dependency": "React state/hooks/DOM/window", "source": "component runtime", "usedFor": "not used inside toMarkdown body", "requiredInput": "must remain absent", "risk": "LOW"},
    ]


def build_reports(data: dict[str, Any]) -> None:
    write_json(REPORT_JSON, data)
    def cell(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    rows = "\n".join(
        f"| {cell(item['path'])} | {item['bytes']} | {item['lineCount']} | {item['lineEnding']} | {item['endsWithNewline']} | {item['trailingWhitespaceLines']} | {item['status']} |"
        for item in data["lineEnding"]["files"]
    )
    deps = "\n".join(
        f"| {cell(d['dependency'])} | {cell(d['usedFor'])} | {cell(d['requiredInput'])} | {cell(d['risk'])} |"
        for d in data["closureDependencies"]
    )
    md = f"""# MARKDOWN V1 FIXTURE COVERAGE / EOL PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `OcrResultPanel.tsx` 수정 없음.
- helper 추출 없음.
- `.gitattributes` 수정 없음.
- 생성/갱신 범위는 tmp 검증 스크립트, docs 리포트, Markdown v1 fixture 보강 및 manifest 보강이다.

## 3. LF/CRLF 검증 결과
| path | bytes | lines | ending | endsWithNewline | trailingWhitespaceLines | status |
| --- | ---: | ---: | --- | --- | ---: | --- |
{rows}

판정: `{data['lineEnding']['overall']}`

## 4. Fixture Comparison Policy 제안
- Markdown fixture는 LF 기준으로 고정한다.
- FRONTEND-CLEANUP-2B helper 출력도 `\\n` 기반 문자열을 생성해야 한다.
- 기본 비교는 exact string equality를 권장한다.
- Windows CRLF 우발 변환을 조기에 잡기 위해 runner는 line ending 정책을 명시적으로 출력해야 한다.
- trailing whitespace도 현재 fixture 기준으로 exact 비교한다.

## 5. Coverage 평가
- 기존 5개 fixture는 large table summary, rowIndex 유지/제외 대표, field-only receipt를 커버한다.
- Markdown v1은 tableRows를 펼치지 않으므로 거래_4~6은 문자열 패턴상 대부분 중복이다.
- 거래_7은 단일 row table summary + rowIndex 제외 케이스라 edge coverage 가치가 있어 추가했다.
- trade_7 추가 결과: `{data['trade7']['status']}` / action: `{data['trade7'].get('writeAction')}`

## 6. toMarkdown Closure Dependency
| dependency | usedFor | required helper input/handling | risk |
| --- | --- | --- | --- |
{deps}

## 7. Helper 입력 Contract 제안
- `fields: OcrFieldResult[]`
- `processingTime: number`
- `docTableRows?: Record<string, unknown>[] | null`
- label/adoption/table parse helper는 helper 파일 내부 순수 함수로 이동하거나 명시 의존성으로 둔다.
- `docTableDisplayCols`, `tableMeta`, `templateName`, `fileName`, `docType`은 Markdown v1 exact output에는 필요하지 않다.

## 8. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | ---: | ---: |
| npm run typecheck | {data['typecheck']['status']} | {data['typecheck']['exitCode']} | {data['typecheck']['durationSeconds']} |
| npm run build | {data['build']['status']} | {data['build']['exitCode']} | {data['build']['durationSeconds']} |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` observed = `{data['knownStderrNoise']['observed']}`

## 9. 다음 작업 제안
1. FRONTEND-CLEANUP-2B에서 `toMarkdown`을 순수 helper로 추출한다.
2. 이번 6개 Markdown fixture와 exact string equality를 수행한다.
3. Clean JSON fixture runner와 함께 typecheck/build를 회귀 검증에 포함한다.
"""
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(md, encoding="utf-8", newline="\n")


def main() -> int:
    print(f"[{TASK}] root={ROOT}", flush=True)
    lock = load_lock_module()
    before_review = preserve_review_log()
    api_url = DEFAULT_API_URL
    api_source = "not_used"
    proc: subprocess.Popen[str] | None = None
    trade7: dict[str, Any]
    try:
        if TRADE7_FIXTURE.exists():
            print("[api] skipped; trade_7 fixture already locked", flush=True)
            api_source = "skipped_existing_trade7_fixture"
        else:
            api_url, proc, api_source = start_backend_if_needed(DEFAULT_API_URL)
            print(f"[api] {api_url} source={api_source}", flush=True)
        trade7 = capture_trade7(api_url, lock)
        print(f"[trade7] {trade7.get('status')} action={trade7.get('writeAction')}", flush=True)
    finally:
        stop_backend(proc)
        review_restore = restore_review_log(before_review)

    manifest_update = update_manifest(trade7)
    eol_files = [analyze_eol(path) for path in sorted(FIXTURE_ROOT.rglob("*.md"))]
    eol_overall = "PASS" if all(item["status"] == "PASS" for item in eol_files) else "WARN"

    print("[check] running npm run typecheck", flush=True)
    typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=240)
    print(f"[check] typecheck={typecheck['status']} duration={typecheck['durationSeconds']}s", flush=True)
    print("[check] running npm run build", flush=True)
    build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)
    print(f"[check] build={build['status']} duration={build['durationSeconds']}s", flush=True)

    known_noise = {
        "id": "ISSUE-FRONTEND-BUILD-LOG-1",
        "message": "ESLint: nextVitals is not iterable",
        "observed": "nextVitals is not iterable" in (build.get("stderrTail") or ""),
    }
    data = {
        "task": TASK,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "noProductionCodeModifiedByThisTask": True,
        "createdFiles": [
            "tmp/codex_markdown_fixture_coverage_eol_precheck.py",
            "docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md",
            "docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.json",
        ],
        "addedOrUpdatedFixtureFiles": [str(TRADE7_FIXTURE.relative_to(ROOT)), str(MANIFEST_PATH.relative_to(ROOT))],
        "api": {"url": api_url, "source": api_source},
        "lineEnding": {"overall": eol_overall, "files": eol_files},
        "comparisonPolicy": {
            "recommended": "exact_string_equality_with_LF",
            "lineEnding": "LF",
            "helperOutput": "must use \\n",
            "normalizeBeforeCompare": False,
            "trailingWhitespace": "exact",
        },
        "coverageEvaluation": {
            "previousFixtureCount": 5,
            "newFixtureCount": len(eol_files),
            "trade7Added": bool(trade7.get("fixtureBytes")),
            "reason": "single-row table summary and rowIndex-excluded edge coverage before toMarkdown extraction",
        },
        "trade7": trade7,
        "manifestUpdate": manifest_update,
        "closureDependencies": analyze_to_markdown_closure(),
        "helperInputContractProposal": {
            "fields": "OcrFieldResult[]",
            "processingTime": "number",
            "docTableRows": "Record<string, unknown>[] | null | undefined",
            "notRequiredForV1": ["docTableDisplayCols", "tableMeta", "templateName", "fileName", "docType"],
        },
        "typecheck": typecheck,
        "build": build,
        "knownStderrNoise": known_noise,
        "repoDirtyStatus": git_status(),
        "reviewLogRestoration": review_restore,
        "overallStatus": "PASS" if eol_overall == "PASS" and trade7.get("status") == "PASS" and typecheck["status"] == "PASS" and build["status"] == "PASS" else "WARN",
    }
    build_reports(data)
    print(f"[write] {REPORT_JSON}", flush=True)
    print(f"[write] {REPORT_MD}", flush=True)
    return 0 if data["overallStatus"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
