from __future__ import annotations

import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "src" / "components" / "runocr" / "RunOcrWorkspace.tsx"
DOCS = ROOT / "docs"
REPORT_MD = DOCS / "FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.md"
REPORT_JSON = DOCS / "FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.json"
REPORT_CSV = DOCS / "FRONTEND_RUNOCR_UTILS_SPLIT_MAP_20260522.csv"

STATE_RE = re.compile(r"const\s+\[([^,\]]+),\s*([^\]]+)\]\s*=\s*useState(?:<([^>]*)>)?\((.*)\)")
REF_RE = re.compile(r"const\s+([A-Za-z0-9_]+)\s*=\s*useRef(?:<([^>]*)>)?\((.*)\)")
MEMO_RE = re.compile(r"const\s+([A-Za-z0-9_]+)\s*=\s*useMemo\(")
FUNCTION_RE = re.compile(r"^\s*(?:async\s+)?function\s+([A-Za-z0-9_]+)\b|^\s*const\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>")
TYPE_RE = re.compile(r"^\s*(?:type|interface)\s+([A-Za-z0-9_]+)\b")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def numbered_lines(text: str) -> list[tuple[int, str]]:
    return list(enumerate(text.splitlines(), start=1))


def line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


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


def classify_state(name: str) -> tuple[str, str]:
    low = name.lower()
    if "file" in low or "previewurl" in low or "renderedurl" in low or "upload" in low or "preprocess" in low:
        return "file/preprocess state", "utils/useRunOcrState.ts candidate"
    if "template" in low or "model" in low or "documenttype" in low or "tooltip" in low:
        return "template/model selection state", "RunOcrWorkspace 유지 또는 useRunOcrState.ts"
    if "ocr" in low or "result" in low or "job" in low or "created" in low or "initialoutput" in low:
        return "OCR result/job state", "utils/useRunOcr.ts candidate"
    if "field" in low or "tab" in low or "layout" in low:
        return "result panel UI state", "RunOcrWorkspace 유지 또는 ui local state candidate"
    if "corner" in low or "canvas" in low or "zoom" in low or "region" in low or "guide" in low:
        return "viewer/canvas state", "RunOcrWorkspace 유지; UI split later"
    return "other state", "review"


def find_usages(lines: list[tuple[int, str]], token: str) -> list[int]:
    pat = re.compile(rf"\b{re.escape(token)}\b")
    return [line_no for line_no, line in lines if pat.search(line)]


def collect_states(lines: list[tuple[int, str]]) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for line_no, line in lines:
        match = STATE_RE.search(line)
        if match:
            name = match.group(1).strip()
            setter = match.group(2).strip()
            responsibility, move_candidate = classify_state(name)
            states.append(
                {
                    "kind": "useState",
                    "name": name,
                    "setter": setter,
                    "line": line_no,
                    "type": match.group(3) or "",
                    "initializer": match.group(4).strip(),
                    "usageLines": find_usages(lines, name)[:40],
                    "responsibility": responsibility,
                    "moveCandidate": move_candidate,
                }
            )
            continue
        match = REF_RE.search(line)
        if match:
            name = match.group(1).strip()
            responsibility, move_candidate = classify_state(name)
            states.append(
                {
                    "kind": "useRef",
                    "name": name,
                    "setter": "",
                    "line": line_no,
                    "type": match.group(2) or "",
                    "initializer": match.group(3).strip(),
                    "usageLines": find_usages(lines, name)[:40],
                    "responsibility": responsibility,
                    "moveCandidate": move_candidate,
                }
            )
            continue
        match = MEMO_RE.search(line)
        if match:
            name = match.group(1).strip()
            states.append(
                {
                    "kind": "useMemo",
                    "name": name,
                    "setter": "",
                    "line": line_no,
                    "type": "",
                    "initializer": "useMemo",
                    "usageLines": find_usages(lines, name)[:40],
                    "responsibility": "derived state",
                    "moveCandidate": "keep until dependencies are reduced",
                }
            )
    for line_no, line in lines:
        if "useEffect(" in line:
            states.append(
                {
                    "kind": "useEffect",
                    "name": f"useEffect@{line_no}",
                    "setter": "",
                    "line": line_no,
                    "type": "",
                    "initializer": "",
                    "usageLines": [line_no],
                    "responsibility": "side effect",
                    "moveCandidate": "review after request/state split",
                }
            )
    return states


def collect_handlers(lines: list[tuple[int, str]]) -> list[dict[str, Any]]:
    handlers: list[dict[str, Any]] = []
    for line_no, line in lines:
        match = FUNCTION_RE.search(line)
        if not match:
            continue
        name = match.group(1) or match.group(2)
        if not name:
            continue
        low = name.lower()
        if "ocr" in low or "upload" in low or "preprocess" in low or "corner" in low or "history" in low or "field" in low or "tab" in low or "select" in low:
            if "ocr" in low or "upload" in low:
                category = "OCR request/flow handler"
            elif "preprocess" in low or "corner" in low:
                category = "preprocess/viewer handler"
            elif "history" in low:
                category = "history handler"
            else:
                category = "UI/result handler"
            handlers.append({"name": name, "line": line_no, "category": category, "snippet": line.strip()})
    return handlers


def collect_types(lines: list[tuple[int, str]]) -> list[dict[str, Any]]:
    out = []
    for line_no, line in lines:
        match = TYPE_RE.search(line)
        if match:
            out.append({"name": match.group(1), "line": line_no, "snippet": line.strip()})
    return out


def keyword_hits(lines: list[tuple[int, str]], keywords: list[str]) -> list[dict[str, Any]]:
    hits = []
    for line_no, line in lines:
        found = [kw for kw in keywords if kw in line]
        if found:
            hits.append({"line": line_no, "keywords": found, "snippet": line.strip()})
    return hits


def build_sections(lines: list[tuple[int, str]]) -> list[dict[str, Any]]:
    markers = [
        ("imports/types", 1),
        ("component start", next((n for n, l in lines if "export default function RunOcrWorkspace" in l), 0)),
        ("state declarations", next((n for n, l in lines if "useState" in l), 0)),
        ("template/preprocess effects", next((n for n, l in lines if "fetch(\"/templates\")" in l), 0)),
        ("preprocess helpers", next((n for n, l in lines if "/preprocess/corners" in l), 0)),
        ("main OCR request", next((n for n, l in lines if "/ocr/extract" in l or "/api/ocr-extract" in l), 0)),
        ("history/autofill mapping", next((n for n, l in lines if "autofillSuggestions" in l), 0)),
        ("result sync effects", next((n for n, l in lines if "initialOutputFields" in l and n > 1000), 0)),
        ("viewer/result props", next((n for n, l in lines if "<OcrResultPanel" in l), 0)),
        ("JSX return", next((n for n, l in lines if re.match(r"\s*return \(", l) and n > 1100), 0)),
    ]
    clean = [{"name": name, "startLine": line} for name, line in markers if line]
    clean.sort(key=lambda item: item["startLine"])
    for idx, item in enumerate(clean):
        item["endLine"] = clean[idx + 1]["startLine"] - 1 if idx + 1 < len(clean) else lines[-1][0]
    return clean


def split_candidates() -> list[dict[str, Any]]:
    return [
        {
            "name": "buildOcrFormData",
            "targetPath": "src/components/runocr/utils/buildOcrFormData.ts",
            "category": "request input builder",
            "recommendation": "DO_FIRST",
            "inputs": ["selectedFile", "activeTemplateId", "activeTemplate", "isRunOcr", "selectedModelId"],
            "outputs": ["FormData"],
            "risk": "LOW-MEDIUM",
            "reason": "Pure-ish boundary with concrete output; easiest to diff by FormData keys.",
            "validation": ["typecheck", "build", "FormData key before/after diff candidate", "/runocr smoke"],
        },
        {
            "name": "runOcrRequest",
            "targetPath": "src/components/runocr/utils/runOcrRequest.ts",
            "category": "network request",
            "recommendation": "DO_FIRST_WITH_FORMDATA_OR_NEXT",
            "inputs": ["FormData", "backendBase", "AbortSignal?"],
            "outputs": ["raw OCR response JSON"],
            "risk": "MEDIUM",
            "reason": "Endpoint/fetch/error status handling is cohesive, but touches network behavior.",
            "validation": ["typecheck", "build", "manual API smoke", "/runocr smoke"],
        },
        {
            "name": "mapOcrResponse",
            "targetPath": "src/components/runocr/utils/mapOcrResponse.ts",
            "category": "response mapper",
            "recommendation": "DO_LATER",
            "inputs": ["raw response", "selectedFile metadata", "autofill suggestions?", "template metadata?"],
            "outputs": ["OcrResult", "history snapshot inputs"],
            "risk": "HIGH",
            "reason": "Currently intertwined with autofill/history snapshot and state updates.",
            "validation": ["fixture runner", "typecheck", "build", "manual smoke"],
        },
        {
            "name": "useRunOcrState",
            "targetPath": "src/components/runocr/utils/useRunOcrState.ts",
            "category": "state bundle hook",
            "recommendation": "DO_LATER",
            "inputs": ["initial options"],
            "outputs": ["state values and setters"],
            "risk": "MEDIUM-HIGH",
            "reason": "May reduce line count but risks creating a setter bucket without clarifying flow.",
            "validation": ["typecheck", "build", "/runocr smoke"],
        },
        {
            "name": "useRunOcr",
            "targetPath": "src/components/runocr/utils/useRunOcr.ts",
            "category": "flow hook",
            "recommendation": "DEFER",
            "inputs": ["request config", "template state", "history/restore adapters"],
            "outputs": ["run handlers", "result state", "loading/error state"],
            "risk": "HIGH",
            "reason": "Should happen after request/mapping/history seams are clearer.",
            "validation": ["full runners", "typecheck", "build", "manual smoke"],
        },
        {
            "name": "RunOcrControls",
            "targetPath": "src/components/runocr/ui/RunOcrControls.tsx",
            "category": "UI component",
            "recommendation": "DO_LATER",
            "inputs": ["file/template/model/preprocess props", "handlers"],
            "outputs": ["control JSX"],
            "risk": "MEDIUM-HIGH",
            "reason": "Props are still broad; safer after request/state boundaries shrink.",
            "validation": ["typecheck", "build", "visual smoke"],
        },
        {
            "name": "RunOcrResultLayout",
            "targetPath": "src/components/runocr/ui/RunOcrResultLayout.tsx",
            "category": "UI layout component",
            "recommendation": "DO_LATER",
            "inputs": ["viewer props", "result panel props", "layout state"],
            "outputs": ["viewer/result layout JSX"],
            "risk": "HIGH",
            "reason": "Would move many props and can obscure behavior if done before request split.",
            "validation": ["typecheck", "build", "visual smoke"],
        },
        {
            "name": "history adapter",
            "targetPath": "src/components/runocr/utils/buildRunOcrHistorySnapshot.ts",
            "category": "history adapter",
            "recommendation": "DEFER",
            "inputs": ["OcrResult", "autofill summary", "file/template metadata"],
            "outputs": ["appendHistoryRun payload"],
            "risk": "HIGH",
            "reason": "History snapshot preserves immutable autofill metadata; avoid in Phase 2A.",
            "validation": ["history smoke", "typecheck", "build"],
        },
        {
            "name": "restore/autofill adapter",
            "targetPath": "src/components/runocr/utils/runAutofillForOcrResult.ts",
            "category": "restore/autofill adapter",
            "recommendation": "DEFER",
            "inputs": ["document fields", "profile data"],
            "outputs": ["suggestions", "summary", "patched fields"],
            "risk": "HIGH",
            "reason": "Cross-feature restore logic; needs dedicated adapter precheck.",
            "validation": ["restore smoke", "typecheck", "build"],
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
        writer = csv.DictWriter(handle, fieldnames=["name", "line", "category", "recommendation", "targetPath", "risk", "reason"])
        writer.writeheader()
        for state in report["runOcrWorkspace"]["states"]:
            writer.writerow(
                {
                    "name": state["name"],
                    "line": state["line"],
                    "category": state["responsibility"],
                    "recommendation": state["moveCandidate"],
                    "targetPath": "",
                    "risk": "",
                    "reason": state["kind"],
                }
            )
        for candidate in report["splitCandidates"]:
            writer.writerow(
                {
                    "name": candidate["name"],
                    "line": "",
                    "category": candidate["category"],
                    "recommendation": candidate["recommendation"],
                    "targetPath": candidate["targetPath"],
                    "risk": candidate["risk"],
                    "reason": candidate["reason"],
                }
            )

    ws = report["runOcrWorkspace"]
    state_rows = [
        [s["line"], s["kind"], s["name"], s["responsibility"], s["moveCandidate"], s["usageLines"][:12]]
        for s in ws["states"]
    ]
    section_rows = [[s["name"], s["startLine"], s["endLine"]] for s in ws["sections"]]
    handler_rows = [[h["line"], h["name"], h["category"], h["snippet"]] for h in ws["handlers"]]
    request_rows = [[h["line"], h["keywords"], h["snippet"]] for h in ws["requestFlow"]]
    response_rows = [[h["line"], h["keywords"], h["snippet"]] for h in ws["responseFlow"]]
    history_rows = [[h["line"], h["keywords"], h["snippet"]] for h in ws["historyRestoreFlow"]]
    ui_rows = [[h["line"], h["keywords"], h["snippet"]] for h in ws["uiSections"]]
    candidate_rows = [
        [c["name"], c["targetPath"], c["recommendation"], c["inputs"], c["outputs"], c["risk"], c["reason"], c["validation"]]
        for c in report["splitCandidates"]
    ]
    dirty_rows = [[line] for line in report["dirtyStatus"]]
    md = f"""# FRONTEND RUNOCR UTILS SPLIT PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `RunOcrWorkspace.tsx` 및 `src/components/runocr/ui/*` 수정 없음.
- utils 파일 생성 없음.
- import 수정/파일 이동/리팩토링 없음.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_utils_split_precheck.py`
- `docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_UTILS_SPLIT_MAP_20260522.csv`

## 4. 분석 범위
- 필수: `src/components/runocr/RunOcrWorkspace.tsx`
- 참고: `src/components/runocr/ui/*`, history/restore/autofill 관련 import 흐름, 최근 구조 리포트

## 5. RunOcrWorkspace 구조 요약
- path: `{ws['path']}`
- lineCount: {ws['lineCount']}
- sizeBytes: {ws['sizeBytes']}
- type/interface count: {len(ws['types'])}
- state/ref/memo/effect count: {len(ws['states'])}
- handler count: {len(ws['handlers'])}

{md_table(['section', 'start', 'end'], section_rows)}

## 6. 상태 관리 책임 분류
{md_table(['line', 'kind', 'name', 'responsibility', 'moveCandidate', 'usageLines'], state_rows)}

## 7. OCR 요청/FormData 책임 분석
{md_table(['line', 'keywords', 'snippet'], request_rows)}

판정:
- main OCR request 영역에는 `new FormData`, `formData.append`, endpoint 선택, `fetch`, loading/error 처리가 같이 있다.
- `buildOcrFormData`는 입력과 출력이 가장 명확하다.
- `runOcrRequest`는 endpoint/fetch/error handling을 함께 묶을 수 있지만 네트워크 behavior라 Phase 2A에서 같이 할지 신중해야 한다.

## 8. OCR 응답 mapping 책임 분석
{md_table(['line', 'keywords', 'snippet'], response_rows)}

판정:
- OCR response 이후 `autofill`, `history`, `initialOutputFields`, `setOcrResult`가 얽혀 있다.
- `mapOcrResponse`는 유효 후보지만 Phase 2A에서는 범위가 크다.

## 9. History/Restore 연동 분석
{md_table(['line', 'keywords', 'snippet'], history_rows)}

판정:
- `appendHistoryRun`, `updateHistoryRun`, `syncHistoryIndexAndDetailOnCreate`, autofill summary/suggestions 흐름이 workspace 내부에 있다.
- Phase 2A에서는 history/restore adapter를 건드리지 않는 것이 안전하다.

## 10. UI 조립 책임 분석
{md_table(['line', 'keywords', 'snippet'], ui_rows)}

판정:
- `OcrDocViewer`, `OcrResultPanel`, `CornerAdjust` props 전달이 workspace return 근처에 몰려 있다.
- UI split은 props 폭발 위험이 있으므로 request/formdata 분리 이후가 적절하다.

## 11. 분리 후보 우선순위
{md_table(['name', 'targetPath', 'recommendation', 'inputs', 'outputs', 'risk', 'reason', 'validation'], candidate_rows)}

## 12. Phase 2A 추천 범위
권장: **A 또는 작은 B**.
- 가장 안전한 1차: `buildOcrFormData.ts`만 분리.
- 허용 가능한 확장: `buildOcrFormData.ts` + `runOcrRequest.ts`.
- 제외 권장: `mapOcrResponse`, `useRunOcr`, UI component split, history/restore adapter.

## 13. Phase 2A 예상 파일
- `src/components/runocr/utils/buildOcrFormData.ts`
- 선택: `src/components/runocr/utils/runOcrRequest.ts`

## 14. Phase 2A 검증 전략
{md_table(['validation'], [[item] for item in report['validationPlan']])}

## 15. dirty 상태
현재 dirty 상태는 기록만 했고 되돌리지 않았다.

{md_table(['git status --short'], dirty_rows)}

## 16. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| {report['typecheck']['command']} | {report['typecheck']['status']} | {report['typecheck']['exitCode']} | {report['typecheck']['durationSeconds']} | {report['typecheck']['knownStderrNoise']} |
| {report['build']['command']} | {report['build']['status']} | {report['build']['exitCode']} | {report['build']['durationSeconds']} | {report['build']['knownStderrNoise']} |

## 17. 다음 작업 제안
- `CODEX_FRONTEND_RUNOCR_UTILS_SPLIT_2A_FORMDATA_ONLY`로 `buildOcrFormData.ts`만 먼저 분리하는 것을 추천한다.
- 더 공격적으로 가도 `runOcrRequest.ts`까지만 포함하고, mapping/history/UI는 다음 phase로 둔다.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    dirty = git_status()
    text = read_text(WORKSPACE)
    lines = numbered_lines(text)
    states = collect_states(lines)
    handlers = collect_handlers(lines)
    types = collect_types(lines)
    sections = build_sections(lines)
    request_keywords = [
        "new FormData",
        "formData.append",
        "fetch(",
        "/ocr/extract",
        "/api/ocr-extract",
        "template_id",
        "documentType",
        "model_id",
        "regions",
        "selectedFile",
    ]
    response_keywords = [
        "setOcrResult",
        "resultJson",
        "runResult",
        "document_fields",
        "output_fields",
        "initialOutputFields",
        "setCurrentJobId",
        "setCurrentCreatedAt",
    ]
    history_keywords = [
        "appendHistoryRun",
        "updateHistoryRun",
        "syncHistoryIndexAndDetailOnCreate",
        "autofill",
        "AutofillSuggestion",
        "suggestions",
        "restoreProfile",
        "collectInternalAutofillCandidates",
    ]
    ui_keywords = [
        "<OcrDocViewer",
        "<OcrResultPanel",
        "<CornerAdjust",
        "onRerun",
        "onRevalidate",
        "onPartialOcr",
        "return (",
    ]

    workspace = {
        "path": "src/components/runocr/RunOcrWorkspace.tsx",
        "lineCount": line_count(text),
        "sizeBytes": WORKSPACE.stat().st_size,
        "sections": sections,
        "types": types,
        "states": states,
        "handlers": handlers,
        "requestFlow": keyword_hits(lines, request_keywords),
        "responseFlow": keyword_hits(lines, response_keywords),
        "historyRestoreFlow": keyword_hits(lines, history_keywords),
        "uiSections": keyword_hits(lines, ui_keywords),
    }
    candidates = split_candidates()
    validation_plan = [
        "npm run typecheck",
        "npm run build",
        "node tmp/check_table_view_model_v1_fixtures_js.mjs",
        "node tmp/check_clean_json_v1_fixtures_js.mjs",
        "python tmp/codex_markdown_contract_fixture_lock.py --check ...",
        "FormData key before/after diff script candidate",
        "/runocr manual smoke with invoice upload",
    ]

    print("[analysis] RunOcrWorkspace responsibility map prepared", flush=True)
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
        "runOcrWorkspace": workspace,
        "splitCandidates": candidates,
        "phase2ARecommendation": {
            "recommendedScope": "buildOcrFormData only",
            "optionalScope": "buildOcrFormData + runOcrRequest if strict no-behavior-change diff is easy",
            "exclude": ["mapOcrResponse", "useRunOcr", "useRunOcrState", "RunOcrControls", "RunOcrResultLayout", "history adapter", "restore/autofill adapter"],
            "reason": "FormData boundary is concrete, low blast radius, and directly improves findability.",
        },
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
            "Run Phase 2A as formdata-only extraction.",
            "Add a lightweight FormData key diff or snapshot check if practical.",
            "Defer response mapping/history/UI until request boundary is stable.",
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
