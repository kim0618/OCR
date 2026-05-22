from __future__ import annotations

import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "components" / "runocr" / "RunOcrWorkspace.tsx"
FORMDATA = ROOT / "src" / "components" / "runocr" / "utils" / "buildOcrFormData.ts"
DOCS = ROOT / "docs"
REPORT_MD = DOCS / "FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.md"
REPORT_JSON = DOCS / "FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.json"
REPORT_CSV = DOCS / "FRONTEND_RUNOCR_REQUEST_EXTRACT_MAP_20260522.csv"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def numbered_lines(text: str) -> list[tuple[int, str]]:
    return list(enumerate(text.splitlines(), start=1))


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


def git_status() -> list[str]:
    proc = subprocess.run(["git", "status", "--short"], cwd=str(ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True, shell=False)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def find_line(lines: list[tuple[int, str]], needle: str, start: int = 1) -> int | None:
    for no, line in lines:
        if no >= start and needle in line:
            return no
    return None


def find_hits(lines: list[tuple[int, str]], keywords: list[str], start: int | None = None, end: int | None = None) -> list[dict[str, Any]]:
    hits = []
    for no, line in lines:
        if start is not None and no < start:
            continue
        if end is not None and no > end:
            continue
        found = [kw for kw in keywords if kw in line]
        if found:
            hits.append({"line": no, "keywords": found, "snippet": line.strip()})
    return hits


def find_function_range(lines: list[tuple[int, str]], signature: str) -> dict[str, int]:
    start = find_line(lines, signature)
    if not start:
        return {"start": 0, "end": 0}
    depth = 0
    seen_open = False
    for no, line in lines:
        if no < start:
            continue
        depth += line.count("{")
        if "{" in line:
            seen_open = True
        depth -= line.count("}")
        if seen_open and depth == 0:
            return {"start": start, "end": no}
    return {"start": start, "end": lines[-1][0]}


def extract_endpoint(lines: list[tuple[int, str]], run_range: dict[str, int]) -> dict[str, Any]:
    endpoint_line = find_line(lines, "const ocrEndpoint", run_range["start"])
    snippets = []
    if endpoint_line:
        for no, line in lines:
            if endpoint_line <= no <= endpoint_line + 1:
                snippets.append(line.strip())
    return {
        "line": endpoint_line,
        "expression": " ".join(snippets),
        "fallback": "/api/ocr-extract",
        "backend": "`${NEXT_PUBLIC_BACKEND_URL}/ocr/extract` when env exists",
    }


def formdata_type_summary(text: str) -> dict[str, Any]:
    keys = re.findall(r'formData\.append\("([^"]+)"', text)
    type_start = text.find("export type BuildOcrFormDataInput")
    func_start = text.find("export function buildOcrFormData")
    return {
        "path": "src/components/runocr/utils/buildOcrFormData.ts",
        "appendKeys": keys,
        "hasExportedInputType": "export type BuildOcrFormDataInput" in text,
        "typeStartOffset": type_start,
        "functionStartOffset": func_start,
    }


def boundary_options() -> list[dict[str, Any]]:
    return [
        {
            "id": "option_1_fetch_only",
            "name": "fetch only",
            "scope": "runOcrRequest(formData, endpoint) returns raw Response",
            "inputs": ["FormData", "endpoint"],
            "outputs": ["Response"],
            "pros": "smallest extraction; response mapping untouched",
            "cons": "caller still owns ok/json boilerplate, so findability improvement is limited",
            "regressionRisk": "LOW",
            "workspaceRemainder": "response.ok, response.json, mapping, loading/error stay in RunOcrWorkspace",
            "recommendation": "NOT_PRIMARY",
        },
        {
            "id": "option_2_fetch_ok_json",
            "name": "fetch + response.ok + json",
            "scope": "runOcrRequest(input) builds FormData, POSTs, checks ok, returns parsed JSON",
            "inputs": ["BuildOcrFormDataInput", "endpoint?"],
            "outputs": ["unknown/raw OCR response JSON"],
            "pros": "clear OCR API request location; endpoint/fetch/ok/json co-located",
            "cons": "introduces helper-thrown Error path; message parity must be kept",
            "regressionRisk": "LOW-MEDIUM",
            "workspaceRemainder": "loading state, catch/ui alert, response mapping, history/autofill stay in RunOcrWorkspace",
            "recommendation": "RECOMMENDED",
        },
        {
            "id": "option_3_request_error_normalization",
            "name": "request + error normalization",
            "scope": "option 2 plus normalized error message/status details",
            "inputs": ["BuildOcrFormDataInput", "endpoint?", "errorMessage?"],
            "outputs": ["unknown/raw OCR response JSON"],
            "pros": "future-friendly API boundary",
            "cons": "more behavior than current code; can accidentally alter UI alert/error console behavior",
            "regressionRisk": "MEDIUM",
            "workspaceRemainder": "loading state and catch stay outside; mapping/history untouched",
            "recommendation": "DO_LATER_OR_KEEP_MINIMAL",
        },
    ]


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
        writer = csv.DictWriter(handle, fieldnames=["category", "line", "keywords", "snippet"])
        writer.writeheader()
        for category in ["buildOcrFormDataCall", "fetchCall", "responseOkHandling", "responseJsonHandling", "errorHandling", "loadingHandling"]:
            value = report["requestFlow"].get(category)
            if isinstance(value, dict):
                writer.writerow({"category": category, "line": value.get("line"), "keywords": category, "snippet": value.get("snippet")})
            elif isinstance(value, list):
                for item in value:
                    writer.writerow({"category": category, "line": item.get("line"), "keywords": item.get("keywords"), "snippet": item.get("snippet")})

    flow = report["requestFlow"]
    flow_rows = [
        ["runOcr line range", flow["runOcrLineRange"], ""],
        ["buildOcrFormData call", flow["buildOcrFormDataCall"].get("line"), flow["buildOcrFormDataCall"].get("snippet")],
        ["fetch call", flow["fetchCall"].get("line"), flow["fetchCall"].get("snippet")],
        ["endpoint", flow["endpoint"].get("line"), flow["endpoint"].get("expression")],
        ["response.ok", flow["responseOkHandling"].get("line"), flow["responseOkHandling"].get("snippet")],
        ["response.json", flow["responseJsonHandling"].get("line"), flow["responseJsonHandling"].get("snippet")],
        ["catch", flow["errorHandling"].get("line"), flow["errorHandling"].get("snippet")],
        ["finally", flow["loadingHandling"].get("finallyLine"), flow["loadingHandling"].get("finallySnippet")],
    ]
    option_rows = [
        [o["id"], o["scope"], o["inputs"], o["outputs"], o["pros"], o["cons"], o["regressionRisk"], o["recommendation"]]
        for o in report["boundaryOptions"]
    ]
    dirty_rows = [[line] for line in report["dirtyStatus"]]
    validation_rows = [[item] for item in report["validationPlan"]]
    expected_file_rows = [[item["path"], item["change"], item["notes"]] for item in report["expectedFiles"]]

    md = f"""# FRONTEND RUNOCR REQUEST EXTRACT PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `RunOcrWorkspace.tsx` 수정 없음.
- `runOcrRequest.ts` 생성 없음.
- `buildOcrFormData.ts`, `src/components/runocr/ui/*`, `src/lib/*` 수정 없음.
- import 수정/파일 이동/fixture 수정 없음.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_request_extract_precheck.py`
- `docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_MAP_20260522.csv`

## 4. 분석 범위
- 필수: `src/components/runocr/RunOcrWorkspace.tsx`
- 필수: `src/components/runocr/utils/buildOcrFormData.ts`
- 참고: `FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522`, RunOCR utils split precheck

## 5. 현재 request flow 요약
{md_table(['item', 'line', 'detail'], flow_rows)}

요약:
- `runOcr()` 안에서 `buildOcrFormData` 호출 후 endpoint를 결정하고 `fetch(POST)`를 수행한다.
- `response.ok` 실패 시 `Error`를 throw하고, 성공 시 `response.json()` 결과를 후속 mapping/autofill/history 로직에 넘긴다.
- `setIsOcrRunning(true/false)`와 catch alert/history fail record는 workspace에 남아 있다.

## 6. runOcrRequest 후보 경계 비교
{md_table(['id', 'scope', 'inputs', 'outputs', 'pros', 'cons', 'risk', 'recommendation'], option_rows)}

## 7. input 타입 초안
권장:

```ts
import type {{ BuildOcrFormDataInput }} from "./buildOcrFormData";

export type RunOcrRequestInput = BuildOcrFormDataInput & {{
  endpoint?: string;
}};
```

판단:
- `BuildOcrFormDataInput`을 그대로 재사용할 수 있다.
- endpoint는 helper 내부에서 `NEXT_PUBLIC_BACKEND_URL` 기준으로 계산하거나, 테스트 용이성을 위해 optional input으로 받을 수 있다.
- 현재 auth header, timeout, AbortSignal은 없다. Phase 2B에는 추가하지 않는 것이 안전하다.

## 8. output 타입 초안
권장:

```ts
export type RunOcrRequestResult = unknown;
```

또는 실제 작업에서는 최소 alias:

```ts
export type RunOcrRawResponse = Record<string, unknown>;
```

판단:
- Phase 2B에서는 response JSON을 그대로 반환한다.
- `mapOcrResponse`는 후순위라 raw response shape를 바꾸지 않는다.

## 9. loading/error 처리 방침
- loading state: `RunOcrWorkspace` 유지.
- catch/alert/fail history record: `RunOcrWorkspace` 유지.
- `runOcrRequest`는 성공 시 JSON 반환, 실패 시 현재와 동일 메시지의 `Error` throw까지만 담당.

## 10. history/restore/autofill 영향
- response 이후 `autofillSuggestions`, `autofillSummary`, `appendHistoryRun`, `syncHistoryIndexAndDetailOnCreate`, `setOcrResult` 흐름은 그대로 workspace에 둔다.
- `runOcrRequest` 추출은 `const json = await runOcrRequest(...)` 형태만 바꾸면 mapping/history/restore에 직접 영향이 없다.
- `mapOcrResponse`는 history/autofill과 얽혀 있으므로 Phase 2B에서 제외한다.

## 11. FormData key parity 영향
- `buildOcrFormData`를 `runOcrRequest` 내부에서 호출해도 input이 같으면 keys는 유지된다.
- 2A parity 기준: `["file","template_id","regions","model_id","documentType"]`.
- 실제 2B에서는 기존 FormData key parity check를 재사용하고, request boundary static check를 추가하는 것이 좋다.

## 12. Phase 2B 추천 범위
추천: **후보 2(fetch + response.ok + json)**.
- 신규 `runOcrRequest.ts` 생성.
- `runOcrRequest(input)` 내부에서 `buildOcrFormData(input)` 호출.
- endpoint 계산, `fetch`, `res.ok`, `res.json()`까지만 포함.
- loading/error UI state, response mapping, history/restore/autofill은 유지.

## 13. Phase 2B 예상 파일
{md_table(['path', 'change', 'notes'], expected_file_rows)}

## 14. Phase 2B 검증 전략
{md_table(['validation'], validation_rows)}

## 15. dirty 상태
현재 dirty 상태는 기록만 했고 되돌리지 않았다.

{md_table(['git status --short'], dirty_rows)}

## 16. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| {report['typecheck']['command']} | {report['typecheck']['status']} | {report['typecheck']['exitCode']} | {report['typecheck']['durationSeconds']} | {report['typecheck']['knownStderrNoise']} |
| {report['build']['command']} | {report['build']['status']} | {report['build']['exitCode']} | {report['build']['durationSeconds']} | {report['build']['knownStderrNoise']} |

## 17. 다음 작업 제안
- `CODEX_FRONTEND_RUNOCR_REQUEST_EXTRACT_2B_FETCH_OK_JSON`로 실제 추출을 진행한다.
- `runOcrRequest.ts`는 request boundary만 담당하고 mapping/history/restore/UI는 건드리지 않는다.
- 검증은 typecheck/build + FormData key parity + runners + `/runocr` manual smoke를 권장한다.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    dirty = git_status()
    workspace_text = read_text(WORKSPACE)
    formdata_text = read_text(FORMDATA)
    lines = numbered_lines(workspace_text)
    run_range = find_function_range(lines, "async function runOcr()")
    run_start = run_range["start"]
    run_end = run_range["end"]

    def hit_one(keyword: str, start: int = run_start, end: int = run_end) -> dict[str, Any]:
        hits = find_hits(lines, [keyword], start, end)
        return hits[0] if hits else {"line": None, "keywords": [keyword], "snippet": ""}

    error_hits = find_hits(lines, ["catch (err)", "console.error(\"[OCR error]\"", "ui.alert", "appendHistoryRun"], run_start, run_end)
    loading_hits = find_hits(lines, ["setIsOcrRunning(true)", "setIsOcrRunning(false)", "finally"], run_start, run_end)
    fetch_hit = hit_one("fetch(ocrEndpoint")
    request_flow = {
        "runOcrLineRange": run_range,
        "buildOcrFormDataCall": hit_one("buildOcrFormData"),
        "fetchCall": {
            **fetch_hit,
            "method": "POST",
            "body": "formData",
            "headers": "none",
        },
        "endpoint": extract_endpoint(lines, run_range),
        "method": "POST",
        "responseOkHandling": hit_one("!res.ok"),
        "responseJsonHandling": hit_one("res.json()"),
        "errorHandling": {
            "line": next((h["line"] for h in error_hits if "catch (err)" in h["snippet"]), None),
            "snippet": next((h["snippet"] for h in error_hits if "catch (err)" in h["snippet"]), ""),
            "related": error_hits,
        },
        "loadingHandling": {
            "setTrueLine": next((h["line"] for h in loading_hits if "setIsOcrRunning(true)" in h["snippet"]), None),
            "finallyLine": next((h["line"] for h in loading_hits if "finally" in h["snippet"]), None),
            "setFalseLine": next((h["line"] for h in loading_hits if "setIsOcrRunning(false)" in h["snippet"]), None),
            "finallySnippet": next((h["snippet"] for h in loading_hits if "finally" in h["snippet"]), ""),
            "related": loading_hits,
        },
        "afterJsonConnectors": find_hits(
            lines,
            ["rawOcrFields", "buildRunOcrResult", "autofillSuggestions", "setOcrResult", "appendHistoryRun", "syncHistoryIndexAndDetailOnCreate"],
            run_start,
            run_end,
        ),
    }
    formdata_summary = formdata_type_summary(formdata_text)
    options = boundary_options()
    validation_plan = [
        "npm run typecheck",
        "npm run build",
        "node tmp/check_table_view_model_v1_fixtures_js.mjs",
        "node tmp/check_clean_json_v1_fixtures_js.mjs",
        "python tmp/codex_markdown_contract_fixture_lock.py --check ...",
        "FormData key parity check: before/after same order and same set",
        "request boundary static check: runOcrRequest imports buildOcrFormData and returns parsed JSON",
        "/runocr manual smoke with invoice upload",
    ]
    expected_files = [
        {"path": "src/components/runocr/utils/runOcrRequest.ts", "change": "create", "notes": "Contains endpoint calculation, buildOcrFormData call, fetch POST, ok check, json parse."},
        {"path": "src/components/runocr/RunOcrWorkspace.tsx", "change": "modify", "notes": "Replace local formData/endpoint/fetch/ok/json block with runOcrRequest call only."},
        {"path": "src/components/runocr/utils/buildOcrFormData.ts", "change": "no behavior change", "notes": "May only need existing BuildOcrFormDataInput export; no logic change expected."},
        {"path": "tmp/check_runocr_request_boundary_2b.mjs", "change": "optional create", "notes": "Static check candidate for request helper boundary."},
    ]

    print("[analysis] request boundary map prepared", flush=True)
    print("[check] npm run typecheck", flush=True)
    typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180)
    print(f"[check] typecheck={typecheck['status']} exit={typecheck['exitCode']}", flush=True)
    print("[check] npm run build", flush=True)
    build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)
    print(f"[check] build={build['status']} exit={build['exitCode']}", flush=True)

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "projectRoot": str(ROOT),
        "dirtyStatus": dirty,
        "requestFlow": request_flow,
        "buildOcrFormData": formdata_summary,
        "boundaryOptions": options,
        "recommendedBoundary": {
            "id": "option_2_fetch_ok_json",
            "summary": "Extract endpoint calculation + buildOcrFormData + fetch POST + response.ok + response.json.",
            "leaveInWorkspace": ["loading state", "catch alert", "fail history record", "response mapping", "history/restore/autofill", "UI state"],
            "risk": "LOW-MEDIUM",
        },
        "inputTypeDraft": {
            "preferred": "RunOcrRequestInput = BuildOcrFormDataInput & { endpoint?: string }",
            "notes": ["No current auth header", "No current AbortSignal", "No timeout behavior; do not add in Phase 2B"],
        },
        "outputTypeDraft": {
            "preferred": "unknown or RunOcrRawResponse = Record<string, unknown>",
            "notes": ["Return parsed JSON unchanged", "Do not introduce mapOcrResponse in Phase 2B"],
        },
        "historyRestoreImpact": {
            "impact": "none expected if raw JSON variable is preserved",
            "reason": "All mapping/autofill/history work starts after response.json and can remain in RunOcrWorkspace.",
            "defer": ["mapOcrResponse", "history adapter", "restore/autofill adapter"],
        },
        "formDataParityImpact": {
            "appendKeys": formdata_summary["appendKeys"],
            "expected2AKeys": ["file", "template_id", "regions", "model_id", "documentType"],
            "impact": "no key change expected if runOcrRequest delegates to buildOcrFormData with same input",
        },
        "phase2BRecommendation": {
            "scope": "runOcrRequest fetch + ok + json",
            "exclude": ["response mapping", "history", "restore", "autofill", "loading UI state", "RunOcrControls", "RunOcrResultLayout"],
            "rationale": "It creates a clear OCR API request location without touching the high-risk mapping/history section.",
        },
        "expectedFiles": expected_files,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "knownStderrNoise": {
            "id": "ISSUE-FRONTEND-BUILD-LOG-1",
            "message": "ESLint: nextVitals is not iterable",
            "observed": build["knownStderrNoise"],
            "blocking": False if build["exitCode"] == 0 else True,
        },
        "nextSteps": [
            "Create runOcrRequest.ts in Phase 2B.",
            "Replace only the request block in RunOcrWorkspace.",
            "Keep response mapping/history/restore/autofill untouched.",
            "Run FormData parity, fixture runners, typecheck/build, and /runocr smoke.",
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
