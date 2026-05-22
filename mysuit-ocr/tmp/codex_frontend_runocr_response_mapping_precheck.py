from __future__ import annotations

import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "components" / "runocr" / "RunOcrWorkspace.tsx"
RUN_OCR_REQUEST = ROOT / "src" / "components" / "runocr" / "utils" / "runOcrRequest.ts"
FORMDATA = ROOT / "src" / "components" / "runocr" / "utils" / "buildOcrFormData.ts"
DOCS = ROOT / "docs"
REPORT_MD = DOCS / "FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.md"
REPORT_JSON = DOCS / "FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.json"
REPORT_CSV = DOCS / "FRONTEND_RUNOCR_RESPONSE_MAPPING_MAP_20260522.csv"


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


def function_range(lines: list[tuple[int, str]], signature: str) -> dict[str, int]:
    start = find_line(lines, signature)
    if not start:
        return {"start": 0, "end": 0}
    depth = 0
    opened = False
    for no, line in lines:
        if no < start:
            continue
        depth += line.count("{")
        if "{" in line:
            opened = True
        depth -= line.count("}")
        if opened and depth == 0:
            return {"start": start, "end": no}
    return {"start": start, "end": lines[-1][0]}


def block_range(lines: list[tuple[int, str]], start_needle: str, end_needle: str, start: int, end: int) -> dict[str, int]:
    block_start = find_line(lines, start_needle, start)
    block_end = find_line(lines, end_needle, block_start or start) if block_start else None
    return {"start": block_start or 0, "end": block_end or end}


def hits(lines: list[tuple[int, str]], keywords: list[str], start: int | None = None, end: int | None = None) -> list[dict[str, Any]]:
    out = []
    for no, line in lines:
        if start is not None and no < start:
            continue
        if end is not None and no > end:
            continue
        found = [kw for kw in keywords if kw in line]
        if found:
            out.append({"line": no, "keywords": found, "snippet": line.strip()})
    return out


def analyze_build_run_ocr_result(lines: list[tuple[int, str]], r: dict[str, int]) -> dict[str, Any]:
    text = "\n".join(line for no, line in lines if r["start"] <= no <= r["end"])
    raw_fields = sorted(set(re.findall(r"\braw\.([A-Za-z0-9_]+)", text)))
    return {
        "definition": r,
        "signature": next((line.strip() for no, line in lines if no == r["start"]), ""),
        "inputs": ["raw: any", "template?: TemplateItem"],
        "output": "OcrResult",
        "rawFieldsRead": raw_fields,
        "templateDependencies": ["template.fields", "template.regions", "template.mode", "field.enField/koField/no"],
        "reactStateOrClosureDependencies": [],
        "includesHistorySnapshot": False,
        "includesAutofill": False,
        "includesPreprocessingDocumentFields": "document_fields" in text or "tableRows" in text,
        "role": "Maps raw OCR JSON into display-oriented OcrResult fields before autofill/source bbox/history.",
        "candidate": "mapOcrResponse.ts candidate; safest if moved as buildRunOcrResult only.",
    }


def raw_json_usages(lines: list[tuple[int, str]], start: int, end: int) -> list[dict[str, Any]]:
    raw = hits(lines, ["json?.", "(json as", "json,", "json)", "json.", "json?."], start, end)
    out = []
    for item in raw:
        snippet = item["snippet"]
        purpose = "unknown"
        movable = "review"
        if "buildRunOcrResult" in snippet:
            purpose = "initial display result mapping"
            movable = "yes, if buildRunOcrResult-only extraction"
        elif "full_text" in snippet or "receipt_fields" in snippet:
            purpose = "autofill business number text source"
            movable = "no for Phase 2C; keep with autofill"
        elif "processing_time" in snippet or "document_fields" in snippet:
            purpose = "history/detail snapshot"
            movable = "no for Phase 2C; keep with history"
        elif "ocr_lines" in snippet:
            purpose = "history raw OCR lines"
            movable = "no for Phase 2C; keep with history"
        out.append({**item, "purpose": purpose, "mapOcrResponseMove": movable})
    return out


def boundary_options() -> list[dict[str, Any]]:
    return [
        {
            "id": "option_1_buildRunOcrResult_only",
            "summary": "Move only buildRunOcrResult to utils/mapOcrResponse.ts",
            "inputs": ["raw JSON", "template?: TemplateItem"],
            "outputs": ["OcrResult before autofill/source bbox/history"],
            "pros": "Smallest pure boundary; no history/autofill movement; findability improves.",
            "cons": "Workspace still contains large post-mapping flow.",
            "reactClosureDependency": "none observed inside function, but requires exported TemplateItem/OcrResult types or colocated types",
            "historyRestoreDependency": "none",
            "risk": "LOW-MEDIUM",
            "recommendation": "RECOMMENDED_IF_PHASE_2C_RUNS",
        },
        {
            "id": "option_2_mapping_plus_normalize",
            "summary": "Move buildRunOcrResult plus rawOcrFields/originalRunFields normalize",
            "inputs": ["raw JSON", "template", "isRunOcr"],
            "outputs": ["runResult", "rawOcrFields", "originalRunFields"],
            "pros": "Captures a more useful response mapping bundle.",
            "cons": "Starts touching source markers and later attachSourceBboxes/autofill assumptions.",
            "reactClosureDependency": "low, but more local type coupling",
            "historyRestoreDependency": "indirect via originalRunFields used by history/autofill",
            "risk": "MEDIUM-HIGH",
            "recommendation": "DO_LATER",
        },
        {
            "id": "option_3_mapping_plus_autofill",
            "summary": "Move response mapping and autofill application together",
            "inputs": ["raw JSON", "template", "selectedFile", "restore/autofill dependencies"],
            "outputs": ["runResult with autofill", "autofillSummary", "autofillSuggestions"],
            "pros": "Removes a large chunk from workspace.",
            "cons": "Crosses restore/autofill feature boundary and business-number extraction policy.",
            "reactClosureDependency": "medium",
            "historyRestoreDependency": "high",
            "risk": "HIGH",
            "recommendation": "DEFER",
        },
        {
            "id": "option_4_mapping_plus_history_snapshot",
            "summary": "Move response mapping, autofill, and history snapshot building",
            "inputs": ["raw JSON", "run context", "template", "file", "history deps"],
            "outputs": ["state updates or large composite payload"],
            "pros": "Largest line-count reduction.",
            "cons": "Too much responsibility; high regression risk; violates clear boundary goal.",
            "reactClosureDependency": "high",
            "historyRestoreDependency": "very high",
            "risk": "VERY_HIGH",
            "recommendation": "DO_NOT_DO_IN_PHASE_2C",
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
        writer = csv.DictWriter(handle, fieldnames=["category", "line", "purpose", "move", "snippet"])
        writer.writeheader()
        for item in report["rawJsonUsages"]:
            writer.writerow({"category": "rawJsonUsage", "line": item["line"], "purpose": item["purpose"], "move": item["mapOcrResponseMove"], "snippet": item["snippet"]})
        for item in report["responseFlow"]["autofillFlow"]["hits"]:
            writer.writerow({"category": "autofill", "line": item["line"], "purpose": ",".join(item["keywords"]), "move": "defer", "snippet": item["snippet"]})
        for item in report["responseFlow"]["historyFlow"]["hits"]:
            writer.writerow({"category": "history", "line": item["line"], "purpose": ",".join(item["keywords"]), "move": "defer", "snippet": item["snippet"]})

    flow = report["responseFlow"]
    flow_rows = [
        ["runOcrRequest call", flow["runOcrRequestCall"].get("line"), flow["runOcrRequestCall"].get("snippet")],
        ["raw json variable", flow["rawJsonVariable"], ""],
        ["buildRunOcrResult call", flow["buildRunOcrResultCall"].get("line"), flow["buildRunOcrResultCall"].get("snippet")],
        ["buildRunOcrResult definition", flow["buildRunOcrResultDefinition"], ""],
        ["autofill flow", flow["autofillFlow"]["range"], f"{len(flow['autofillFlow']['hits'])} hits"],
        ["history flow", flow["historyFlow"]["range"], f"{len(flow['historyFlow']['hits'])} hits"],
        ["set result", flow["setResultFlow"], ""],
    ]
    raw_rows = [[u["line"], u["purpose"], u["mapOcrResponseMove"], u["snippet"]] for u in report["rawJsonUsages"]]
    option_rows = [
        [o["id"], o["summary"], o["inputs"], o["outputs"], o["pros"], o["cons"], o["risk"], o["recommendation"]]
        for o in report["boundaryOptions"]
    ]
    dirty_rows = [[line] for line in report["dirtyStatus"]]
    expected_rows = [[item["path"], item["change"], item["notes"]] for item in report["expectedFiles"]]
    validation_rows = [[item] for item in report["validationPlan"]]

    md = f"""# FRONTEND RUNOCR RESPONSE MAPPING PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `RunOcrWorkspace.tsx` 수정 없음.
- `mapOcrResponse.ts` 생성 없음.
- `runOcrRequest.ts`, `buildOcrFormData.ts`, `runocr/ui/*`, `src/lib/*` 수정 없음.
- import 수정/파일 이동/fixture 수정 없음.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_response_mapping_precheck.py`
- `docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/runocr/utils/runOcrRequest.ts`
- `src/components/runocr/utils/buildOcrFormData.ts`
- 참고: history/autofill 관련 흐름과 최근 2A/2B 리포트

## 5. runOcr response flow 요약
{md_table(['item', 'line/range', 'detail'], flow_rows)}

요약:
- `runOcrRequest`는 raw `json`을 반환한다.
- `buildRunOcrResult(json, activeTemplate)`가 autofill 전 화면용 `OcrResult`를 만든다.
- 이후 `rawOcrFields`, `originalRunFields`, autofill, source bbox attach, history snapshot, `setOcrResult`가 한 흐름에 이어진다.

## 6. buildRunOcrResult 책임 분석
- 정의 범위: {report['buildRunOcrResultAnalysis']['definition']}
- signature: `{report['buildRunOcrResultAnalysis']['signature']}`
- 입력: {report['buildRunOcrResultAnalysis']['inputs']}
- 출력: {report['buildRunOcrResultAnalysis']['output']}
- raw fields read: {report['buildRunOcrResultAnalysis']['rawFieldsRead']}
- template dependencies: {report['buildRunOcrResultAnalysis']['templateDependencies']}
- React state/closure dependency: {report['buildRunOcrResultAnalysis']['reactStateOrClosureDependencies']}
- history 포함: {report['buildRunOcrResultAnalysis']['includesHistorySnapshot']}
- autofill 포함: {report['buildRunOcrResultAnalysis']['includesAutofill']}

판정: `buildRunOcrResult`만 옮기는 것은 `mapOcrResponse.ts`의 최소 안전 범위가 될 수 있다.

## 7. raw response 사용처
{md_table(['line', 'purpose', 'moveToMapOcrResponse', 'snippet'], raw_rows)}

## 8. autofill/restore 경계
- autofill 시작은 business text 구성과 `extractBizNumber` 이후이다.
- raw json의 `full_text`, `receipt_fields["사업자번호"]`, raw fields를 함께 사용한다.
- `applyAutofillToOutputFields`가 `runResult.fields`를 변경하고, 그 결과가 history output_fields에도 들어간다.
- Phase 2C에서는 autofill/restore를 `mapOcrResponse`에 넣지 않는 것이 안전하다.

## 9. history 저장 경계
- 성공 history record는 `appendHistoryRun`에서 생성된다.
- 실패 history record도 catch 안에서 생성된다.
- `processing_time`, `document_fields`, `ocr_lines`, `runResult.processed_image`, `outputFieldsForHistory`, `autofillSummary`가 얽혀 있다.
- Phase 2C에서 history snapshot은 제외하고, 이후 `runOcrHistoryAdapter.ts` 후보로 별도 precheck가 적절하다.

## 10. mapOcrResponse 후보 경계 비교
{md_table(['id', 'summary', 'inputs', 'outputs', 'pros', 'cons', 'risk', 'recommendation'], option_rows)}

## 11. Phase 2C 추천 범위
권장: **B. buildRunOcrResult만 `utils/mapOcrResponse.ts`로 이동**.

조건:
- `autofill`, `history`, `attachSourceBboxes`, `buildResultRegions`, `setOcrResult`는 유지.
- 함수 이름은 `buildRunOcrResult` 유지 또는 `mapOcrResponseToRunOcrResult`로 명확화 가능.
- input/output contract가 명확한 순수 함수만 옮긴다.

대안:
- 2C를 보류하고 UI split/Template 정리로 이동해도 된다. 다만 “OCR raw response mapping은 어디?”라는 목표를 충족하려면 buildRunOcrResult-only 추출은 가치가 있다.

## 12. Phase 2C 예상 파일
{md_table(['path', 'change', 'notes'], expected_rows)}

## 13. 검증 전략
{md_table(['validation'], validation_rows)}

## 14. dirty 상태
현재 dirty 상태는 기록만 했고 되돌리지 않았다.

{md_table(['git status --short'], dirty_rows)}

## 15. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| {report['typecheck']['command']} | {report['typecheck']['status']} | {report['typecheck']['exitCode']} | {report['typecheck']['durationSeconds']} | {report['typecheck']['knownStderrNoise']} |
| {report['build']['command']} | {report['build']['status']} | {report['build']['exitCode']} | {report['build']['durationSeconds']} | {report['build']['knownStderrNoise']} |

## 16. 다음 작업 제안
- 실제 Phase 2C를 한다면 `CODEX_FRONTEND_RUNOCR_RESPONSE_MAPPING_2C_BUILD_RESULT_ONLY`로 작게 진행한다.
- `mapOcrResponse.ts`에는 `buildRunOcrResult`만 이동한다.
- autofill/history/restore는 별도 adapter precheck 전까지 유지한다.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    dirty = git_status()
    text = read_text(WORKSPACE)
    lines = numbered_lines(text)
    run_range = function_range(lines, "async function runOcr()")
    build_range = function_range(lines, "function buildRunOcrResult")
    request_call = hits(lines, ["runOcrRequest"], run_range["start"], run_range["end"])[0]
    build_call = hits(lines, ["buildRunOcrResult"], run_range["start"], run_range["end"])[0]
    autofill_range = block_range(lines, "let autofillSuggestions", "runResult.fields = attachSourceBboxes", run_range["start"], run_range["end"])
    history_range = block_range(lines, "const rawOcrLines", "setInitialOutputFields", run_range["start"], run_range["end"])
    set_result_hits = hits(lines, ["setOcrResult", "setProcessedImageUrl", "setCanvasRegions"], run_range["start"], run_range["end"])
    autofill_hits = hits(
        lines,
        ["autofill", "extractBizNumber", "collectInternalAutofillCandidates", "applyAutofillToOutputFields", "suggestions", "businessNumber"],
        autofill_range["start"],
        autofill_range["end"],
    )
    history_hits = hits(
        lines,
        ["appendHistoryRun", "syncHistoryIndexAndDetailOnCreate", "processing_time", "document_fields", "ocr_lines", "outputFieldsForHistory", "History"],
        history_range["start"],
        history_range["end"],
    )
    raw_usages = raw_json_usages(lines, request_call["line"], run_range["end"])

    response_flow = {
        "runOcrRequestCall": request_call,
        "rawJsonVariable": "json",
        "buildRunOcrResultCall": build_call,
        "buildRunOcrResultDefinition": build_range,
        "autofillFlow": {"range": autofill_range, "hits": autofill_hits},
        "historyFlow": {"range": history_range, "hits": history_hits},
        "setResultFlow": set_result_hits,
        "catchFailHistoryRecord": hits(lines, ["catch (err)", "appendHistoryRun", "status: \"fail\""], run_range["start"], run_range["end"]),
        "responseAfterRequestLineRange": {"start": request_call["line"], "end": run_range["end"]},
    }

    validation_plan = [
        "npm run typecheck",
        "npm run build",
        "node tmp/check_table_view_model_v1_fixtures_js.mjs",
        "node tmp/check_clean_json_v1_fixtures_js.mjs",
        "python tmp/codex_markdown_contract_fixture_lock.py --check ...",
        "FormData key parity check",
        "request boundary static check",
        "response mapping boundary static check: mapOcrResponse does not import history/autofill/React",
        "/runocr manual smoke",
        "history save smoke if mapping boundary expands later",
    ]
    expected_files = [
        {"path": "src/components/runocr/utils/mapOcrResponse.ts", "change": "create if Phase 2C runs", "notes": "Only move buildRunOcrResult or equivalent pure mapping."},
        {"path": "src/components/runocr/RunOcrWorkspace.tsx", "change": "modify if Phase 2C runs", "notes": "Import mapping helper and remove local buildRunOcrResult only."},
        {"path": "tmp/check_runocr_response_mapping_boundary_2c.mjs", "change": "optional create", "notes": "Static boundary check: no history/autofill/React imports in mapping util."},
    ]

    print("[analysis] response mapping boundary map prepared", flush=True)
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
        "responseFlow": response_flow,
        "buildRunOcrResultAnalysis": analyze_build_run_ocr_result(lines, build_range),
        "rawJsonUsages": raw_usages,
        "autofillRestoreImpact": {
            "recommendation": "exclude from Phase 2C",
            "reason": "Autofill reads raw json full_text/receipt_fields and mutates runResult.fields before history snapshot.",
            "futureCandidate": "runAutofillForOcrResult.ts or restore adapter precheck",
        },
        "historyImpact": {
            "recommendation": "exclude from Phase 2C",
            "reason": "History uses raw json processing_time/document_fields/ocr_lines, runResult images, output fields, and autofill summary.",
            "futureCandidate": "runOcrHistoryAdapter.ts",
        },
        "boundaryOptions": boundary_options(),
        "phase2CRecommendation": {
            "recommended": "buildRunOcrResult-only extraction",
            "shouldProceed": True,
            "alternative": "Defer mapping and move to UI split/Template precheck if avoiding any response risk is preferred.",
            "excluded": ["autofill", "history snapshot", "restore adapter", "source bbox attach", "canvas region state", "setOcrResult"],
            "risk": "LOW-MEDIUM",
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
            "If proceeding, create mapOcrResponse.ts with buildRunOcrResult only.",
            "Add static check to prevent history/autofill/React imports in mapping util.",
            "Defer history/autofill adapters to separate prechecks.",
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
