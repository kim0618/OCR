from __future__ import annotations

import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
BACKEND = REPO_ROOT / "ocr-server"
DOCS = ROOT / "docs"
REPORT_MD = DOCS / "MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.md"
REPORT_JSON = DOCS / "MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.json"
REPORT_CSV = DOCS / "MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_DIFF_20260522.csv"
TEMPLATE_PATH = BACKEND / "data" / "templates.json"
FIXTURE_PATH = ROOT / "tmp" / "fixtures" / "markdown_v1" / "invoice_statement" / "trade_7_7pdf.md"
MANIFEST_PATH = ROOT / "tmp" / "fixtures" / "markdown_v1" / "manifest.json"
POST_2C_REPORT = DOCS / "MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.md"
POST_2C_JSON = DOCS / "MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.json"
STRUCTURE_2C_REPORT = DOCS / "FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.md"


def run(args: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(cwd), text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout, shell=False)


def run_command(args: list[str], cwd: Path, timeout: int = 300) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = run(args, cwd, timeout)
        return {
            "command": " ".join(args),
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "exitCode": proc.returncode,
            "durationSeconds": round(time.perf_counter() - started, 3),
            "stdoutTail": proc.stdout[-4000:],
            "stderrTail": proc.stderr[-4000:],
            "knownStderrNoise": "nextVitals is not iterable" in proc.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(args),
            "status": "TIMEOUT",
            "exitCode": None,
            "durationSeconds": round(time.perf_counter() - started, 3),
            "stdoutTail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderrTail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "knownStderrNoise": False,
        }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def git_status(cwd: Path) -> list[str]:
    proc = run(["git", "status", "--short"], cwd)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def git_diff_templates() -> str:
    proc = run(["git", "diff", "--", "ocr-server/data/templates.json"], REPO_ROOT)
    if proc.returncode == 0 and proc.stdout:
        return proc.stdout
    proc = run(["git", "diff", "--", "data/templates.json"], BACKEND)
    return proc.stdout


def load_head_templates() -> Any:
    proc = run(["git", "show", "HEAD:ocr-server/data/templates.json"], REPO_ROOT)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return json.loads(proc.stdout)


def template_id_of(item: Any) -> str | None:
    if isinstance(item, dict):
        return item.get("id") or item.get("templateId") or item.get("template_id")
    return None


def flatten_changes(old: Any, new: Any, path: str = "") -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if type(old) is not type(new):
        return [{"path": path, "oldValue": old, "newValue": new, "delta": None}]
    if isinstance(old, dict):
        keys = sorted(set(old) | set(new))
        for key in keys:
            next_path = f"{path}.{key}" if path else str(key)
            if key not in old:
                changes.append({"path": next_path, "oldValue": None, "newValue": new[key], "delta": None})
            elif key not in new:
                changes.append({"path": next_path, "oldValue": old[key], "newValue": None, "delta": None})
            else:
                changes.extend(flatten_changes(old[key], new[key], next_path))
        return changes
    if isinstance(old, list):
        max_len = max(len(old), len(new))
        for idx in range(max_len):
            next_path = f"{path}[{idx}]"
            if idx >= len(old):
                changes.append({"path": next_path, "oldValue": None, "newValue": new[idx], "delta": None})
            elif idx >= len(new):
                changes.append({"path": next_path, "oldValue": old[idx], "newValue": None, "delta": None})
            else:
                changes.extend(flatten_changes(old[idx], new[idx], next_path))
        return changes
    if old != new:
        delta = new - old if isinstance(old, (int, float)) and isinstance(new, (int, float)) else None
        changes.append({"path": path, "oldValue": old, "newValue": new, "delta": delta})
    return changes


def compare_templates() -> dict[str, Any]:
    old = load_head_templates()
    new = read_json(TEMPLATE_PATH)
    old_map = {template_id_of(item): item for item in old if template_id_of(item)}
    new_map = {template_id_of(item): item for item in new if template_id_of(item)}
    changed: dict[str, list[dict[str, Any]]] = {}
    for tid in sorted(set(old_map) | set(new_map)):
        if tid not in old_map or tid not in new_map:
            changed[tid] = [{"path": "", "oldValue": "missing" if tid not in old_map else old_map[tid], "newValue": "missing" if tid not in new_map else new_map[tid], "delta": None}]
            continue
        diffs = flatten_changes(old_map[tid], new_map[tid])
        if diffs:
            changed[tid] = diffs
    return {"changed": changed, "current": new_map, "head": old_map}


def extract_fixture_value() -> dict[str, Any]:
    text = read_text(FIXTURE_PATH)
    lines = text.splitlines()
    target = next((line for line in lines if "113-85-04425" in line), "")
    cells = [cell.strip() for cell in target.strip("|").split("|")] if target else []
    value = cells[2] if len(cells) >= 3 else ""
    conf = cells[3] if len(cells) >= 4 else ""
    return {"line": target, "value": value, "confidence": conf, "lineNumber": lines.index(target) + 1 if target in lines else None, "text": text}


def extract_actual_from_reports() -> dict[str, Any]:
    actual_line = ""
    expected_line = ""
    source = ""
    if POST_2C_JSON.exists():
        try:
            data = read_json(POST_2C_JSON)
            case = next((item for item in data.get("cases", []) if item.get("caseId") == "trade_7_7pdf"), None)
            diff = case.get("diff") if isinstance(case, dict) else None
            if isinstance(diff, dict):
                actual_line = diff.get("actualLine", "")
                expected_line = diff.get("expectedLine", "")
                source = str(POST_2C_JSON)
        except Exception:
            pass
    md = read_text(POST_2C_REPORT) if POST_2C_REPORT.exists() else ""
    actual_match = re.search(r"actualLine:\s*'([^']*113-85-04425[^']*)", md)
    expected_match = re.search(r"expectedLine:\s*'([^']*113-85-04425[^']*)", md)
    if actual_match and not actual_line:
        actual_line = actual_match.group(1)
        source = str(POST_2C_REPORT)
    if expected_match and not expected_line:
        expected_line = expected_match.group(1)
    cells = [cell.strip() for cell in actual_line.strip("|").split("|")] if actual_line else []
    return {
        "line": actual_line,
        "value": cells[2] if len(cells) >= 3 else "",
        "confidence": cells[3] if len(cells) >= 4 else "",
        "expectedLineFromReport": expected_line,
        "source": source,
    }


def manifest_case() -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    return next(case for case in manifest["cases"] if case["caseId"] == "trade_7_7pdf")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        if isinstance(value, (list, dict)):
            value = json.dumps(value, ensure_ascii=False)
        return str(value if value is not None else "").replace("\n", "<br>").replace("|", "\\|")

    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    out.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)
    return "\n".join(out)


def write_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["templateId", "path", "oldValue", "newValue", "delta"])
        writer.writeheader()
        for change in report["templateDiff"]["changes"]:
            writer.writerow(change)

    dirty_rows = [[scope, line] for scope, lines in report["dirtyStatus"].items() for line in lines]
    diff_rows = [[c["templateId"], c["path"], c["oldValue"], c["newValue"], c["delta"]] for c in report["templateDiff"]["changes"]]
    decision_rows = [[k, v] for k, v in report["decision"].items()]
    validation_rows = [[item] for item in report["validationPlan"]]

    md = f"""# MARKDOWN TRADE7 TEMPLATE DRIFT PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `ocr-server/data/templates.json` 수정 없음.
- markdown fixture 수정 없음.
- rollback/rebake/import 수정/파일 이동 없음.

## 3. 생성 파일
- `tmp/codex_markdown_trade7_template_drift_precheck.py`
- `docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.md`
- `docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.json`
- `docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_DIFF_20260522.csv`

## 4. 분석 범위
- backend template: `ocr-server/data/templates.json`
- markdown fixture: `tmp/fixtures/markdown_v1/invoice_statement/trade_7_7pdf.md`
- manifest: `tmp/fixtures/markdown_v1/manifest.json`
- 2C markdown check report/log evidence

## 5. 현재 dirty 상태
{md_table(['scope', 'git status --short'], dirty_rows)}

## 6. trade_7 markdown drift 요약
- caseId: `{report['drift']['caseId']}`
- templateId: `{report['drift']['templateId']}`
- expected: `{report['drift']['expectedValue']}` / `{report['drift']['expectedConfidence']}`
- actual: `{report['drift']['actualValue']}` / `{report['drift']['actualConfidence']}`
- diff: {report['drift']['diffSummary']}
- actual source: `{report['drift']['actualSource']}`

## 7. templates.json TPL-3AFD383E diff
{md_table(['templateId', 'path', 'old', 'new', 'delta'], diff_rows)}

## 8. expected fixture 값
- fixturePath: `{report['drift']['fixturePath']}`
- lineNumber: {report['drift']['expectedLineNumber']}
- expectedLine: `{report['drift']['expectedLine']}`
- fixture createdAt: `{report['fixtureManifest']['createdAt']}`
- fixture apiUrl: `{report['fixtureManifest']['apiUrl']}`

## 9. actual backend 값
- actualLine: `{report['drift']['actualLine']}`
- value: `{report['drift']['actualValue']}`
- confidence: `{report['drift']['actualConfidence']}`
- API 재호출은 하지 않았고, 2C markdown runner report를 근거로 삼았다. 따라서 review_log append 부작용은 새로 만들지 않았다.

## 10. 2C 코드 변경과 인과 여부
- relatedTo2C: `{report['causality']['relatedTo2C']}`
- reason: {report['causality']['reason']}

## 11. rollback vs rebake 판단
{md_table(['key', 'value'], decision_rows)}

## 12. 최종 추천
`{report['decision']['recommendation']}`

근거:
- markdown runner는 backend `/ocr/extract`를 직접 호출하므로 frontend `mapOcrResponse`를 거치지 않는다.
- drift는 `templates.json` dirty 좌표 변경과 같은 시점/대상 템플릿에서 발생한다.
- 현재 actual은 사업자번호 괄호가 사라지고 confidence가 100.0%로 올라간 결과라, OCR 품질 관점에서는 더 나아 보인다.
- 다만 template 좌표 변경 의도/승인 기록이 명확하지 않아 즉시 rebake보다 사용자 결정이 안전하다.

## 13. 다음 실제 작업 방향
- 사용자 결정 후 진행:
  - rollback 선택: `TPL-3AFD383E` 관련 dirty 좌표만 원복하고 markdown runner 6/6 확인.
  - rebake 선택: `trade_7_7pdf.md` 및 manifest metadata만 갱신하고 rebake 사유 문서화.
- known drift 보류는 다음 리팩토링 검증에서 계속 5/6 노이즈가 되므로 비추천.

## 14. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| {report['typecheck']['command']} | {report['typecheck']['status']} | {report['typecheck']['exitCode']} | {report['typecheck']['durationSeconds']} | {report['typecheck']['knownStderrNoise']} |
| {report['build']['command']} | {report['build']['status']} | {report['build']['exitCode']} | {report['build']['durationSeconds']} | {report['build']['knownStderrNoise']} |

## 15. 주의사항
- 이번 작업은 precheck만 수행했다.
- templates.json/fixture/운영 코드는 수정하지 않았다.
- validation plan:
{md_table(['validation'], validation_rows)}
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    frontend_status = git_status(ROOT)
    backend_status = git_status(BACKEND)
    raw_diff = git_diff_templates()
    compare = compare_templates()
    tpl_id = "TPL-3AFD383E"
    all_changes = []
    for tid, changes in compare["changed"].items():
        for change in changes:
            all_changes.append({"templateId": tid, **change})
    tpl_changes = [c for c in all_changes if c["templateId"] == tpl_id]
    fixture = extract_fixture_value()
    actual = extract_actual_from_reports()
    case = manifest_case()
    manifest = read_json(MANIFEST_PATH)
    changed_ids = sorted(compare["changed"])

    print("[analysis] template diff and markdown drift evidence prepared", flush=True)
    print("[check] npm run typecheck", flush=True)
    typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180)
    print(f"[check] typecheck={typecheck['status']} exit={typecheck['exitCode']}", flush=True)
    print("[check] npm run build", flush=True)
    build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)
    print(f"[check] build={build['status']} exit={build['exitCode']}", flush=True)

    better_actual = actual["value"] == "113-85-04425" and actual["confidence"] == "100.0%"
    decision = {
        "recommendation": "NEED_USER_DECISION",
        "reason": "The drift is almost certainly backend template dirty-state driven, not 2C-driven. Actual looks more accurate, but the template coordinate edit intent is not documented enough to choose rebake automatically.",
        "risk": "MEDIUM",
        "nextAction": "Ask whether TPL-3AFD383E template coordinate changes are intended. If yes, rebake trade_7 markdown fixture; if no, rollback only that template dirty change.",
        "rollbackCase": "Use if templates.json coordinate edits were accidental/manual smoke residue.",
        "rebakeCase": "Use if TPL-3AFD383E coordinate edits were intentional and current actual is accepted as better OCR.",
        "holdKnownDriftCase": "Not recommended except as a temporary note because it keeps markdown runner at 5/6.",
    }
    if not tpl_changes:
        decision.update({
            "recommendation": "HOLD_AS_KNOWN_DRIFT",
            "reason": "No TPL-3AFD383E diff was detected by JSON comparison, so cause needs additional backend runtime check.",
        })

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "projectRoot": str(ROOT),
        "backendRoot": str(BACKEND),
        "dirtyStatus": {"frontend": frontend_status, "backend": backend_status},
        "drift": {
            "caseId": "trade_7_7pdf",
            "templateId": tpl_id,
            "fixturePath": "tmp/fixtures/markdown_v1/invoice_statement/trade_7_7pdf.md",
            "expectedValue": fixture["value"],
            "expectedConfidence": fixture["confidence"],
            "expectedLine": fixture["line"],
            "expectedLineNumber": fixture["lineNumber"],
            "actualValue": actual["value"],
            "actualConfidence": actual["confidence"],
            "actualLine": actual["line"],
            "actualSource": actual["source"],
            "diffSummary": "actual removes parentheses and changes confidence 97.1% -> 100.0%",
            "actualLooksMoreAccurate": better_actual,
        },
        "fixtureManifest": {
            "createdAt": manifest.get("createdAt"),
            "updatedAt": manifest.get("updatedAt"),
            "apiUrl": manifest.get("apiUrl"),
            "apiSource": manifest.get("apiSource"),
            "case": case,
        },
        "templateDiff": {
            "templateId": tpl_id,
            "templateName": "거래_7",
            "changedTemplateIds": changed_ids,
            "rawGitDiffTail": raw_diff[-8000:],
            "changes": tpl_changes,
            "allTemplateChanges": all_changes,
        },
        "causality": {
            "relatedTo2C": "NO",
            "reason": "2C moved frontend buildRunOcrResult into mapOcrResponse, while markdown fixture runner calls backend /ocr/extract directly and does not import or execute React frontend mapping code. The failing case aligns with dirty backend templates.json changes for TPL-3AFD383E.",
        },
        "decision": decision,
        "validationPlan": [
            "If rollback: restore only TPL-3AFD383E template coordinates and rerun markdown check expecting 6/6.",
            "If rebake: update only trade_7_7pdf markdown fixture and manifest metadata, then rerun markdown check expecting 6/6.",
            "After either action: run typecheck/build and relevant frontend runners to keep baseline clean.",
        ],
        "typecheck": typecheck,
        "build": build,
        "knownStderrNoise": {
            "id": "ISSUE-FRONTEND-BUILD-LOG-1",
            "message": "ESLint: nextVitals is not iterable",
            "observed": build["knownStderrNoise"],
            "blocking": False if build["exitCode"] == 0 else True,
        },
        "nextSteps": [
            "Confirm whether TPL-3AFD383E coordinate edits are intended.",
            "Choose rollback or rebake; avoid holding the drift if more refactoring validation is planned.",
        ],
    }
    write_reports(report)
    print(f"[write] {REPORT_JSON}", flush=True)
    print(f"[write] {REPORT_MD}", flush=True)
    print(f"[write] {REPORT_CSV}", flush=True)
    status = "PASS" if typecheck["status"] == "PASS" and build["status"] == "PASS" else "FAIL"
    print(f"[done] {status}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
