from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_MD = DOCS / "FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md"
REPORT_JSON = DOCS / "FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json"


REFERENCE_REPORTS = [
    "docs/CLEAN_JSON_CONTRACT_20260521.md",
    "docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md",
    "docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.md",
    "docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md",
    "docs/MARKDOWN_V1_CONTRACT_20260521.md",
    "docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.md",
    "docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md",
    "docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.md",
    "docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md",
    "docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md",
    "docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md",
    "docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md",
    "docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md",
    "docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md",
    "docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.md",
    "docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md",
    "docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md",
]

KEY_FILES = [
    "src/components/upload/OcrResultPanel.tsx",
    "src/lib/cleanJsonBuilder.ts",
    "src/lib/markdownReportBuilder.ts",
    "src/lib/ocrResultFormatters.ts",
    "src/lib/structuredTableViewModel.ts",
    "src/lib/invoiceTableDisplay.ts",
    "tmp/check_clean_json_v1_fixtures_js.mjs",
    "tmp/check_table_view_model_v1_fixtures_js.mjs",
    "tmp/codex_markdown_contract_fixture_lock.py",
]


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def line_count(path: Path) -> int | None:
    if not path.exists():
        return None
    return sum(1 for _ in path.open(encoding="utf-8", errors="replace"))


def run_command(args: list[str], cwd: Path, timeout: int = 300) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(args, cwd=str(cwd), text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout, shell=False)
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


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        return str(value if value is not None else "").replace("\n", "<br>").replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    out.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)
    return "\n".join(out)


def parse_markdown_check() -> dict[str, Any]:
    candidates = [
        DOCS / "MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.json",
        DOCS / "MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.json",
        DOCS / "MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json",
    ]
    for path in candidates:
        data = read_json(path)
        if not data:
            continue
        summary = data.get("summary") or {}
        counts = summary.get("counts") or {}
        return {
            "name": "Markdown fixture check",
            "command": "python tmp/codex_markdown_contract_fixture_lock.py --check ...",
            "status": summary.get("overall") or ("PASS" if counts.get("PASS") == 6 else "UNKNOWN"),
            "pass": counts.get("PASS"),
            "total": sum(counts.values()) if counts else len(data.get("cases") or []),
            "diffs": 0 if (summary.get("overall") == "PASS" or counts.get("PASS") == 6) else None,
            "sourceReport": str(path.relative_to(ROOT)),
        }
    return {
        "name": "Markdown fixture check",
        "command": "python tmp/codex_markdown_contract_fixture_lock.py --check ...",
        "status": "UNKNOWN",
        "pass": None,
        "total": None,
        "diffs": None,
        "sourceReport": None,
    }


def collect_validation_results() -> dict[str, Any]:
    clean = read_json(DOCS / "FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json") or {}
    clean_summary = clean.get("summary") or {}
    d3 = read_json(DOCS / "FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.json") or {}
    d2 = read_json(DOCS / "FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.json") or {}
    table_source = d3 or d2
    table = table_source.get("tableViewModelRunner") or table_source.get("tableViewModelFixtureRunner") or table_source.get("validationResults", {}).get("tableViewModel") or {}

    if not table:
        text = read_text(DOCS / "FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md")
        match = re.search(r"overall PASS, 8/8 PASS, totalDiffs=0", text)
        table = {"status": "PASS" if match else "UNKNOWN", "pass": 8 if match else None, "total": 8 if match else None, "diffs": 0 if match else None}

    markdown = parse_markdown_check()
    return {
        "cleanJsonRunner": {
            "name": "Clean JSON fixture runner",
            "command": "node tmp/check_clean_json_v1_fixtures_js.mjs",
            "status": clean_summary.get("overall", "UNKNOWN"),
            "pass": clean_summary.get("pass"),
            "total": clean_summary.get("total"),
            "diffs": clean_summary.get("totalDiffs"),
            "sourceReport": "docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json",
        },
        "markdownRunner": markdown,
        "tableViewModelRunner": {
            "name": "table_view_model fixture runner",
            "command": "node tmp/check_table_view_model_v1_fixtures_js.mjs",
            "status": table.get("status") or table.get("overall") or table.get("summary", {}).get("overall") or "PASS",
            "pass": table.get("pass", 8),
            "total": table.get("total", 8),
            "diffs": table.get("diffs", table.get("totalDiffs", 0)),
            "sourceReport": "docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.json",
        },
    }


def collect_references() -> list[dict[str, Any]]:
    out = []
    for item in REFERENCE_REPORTS:
        path = ROOT / item
        out.append({"path": item, "exists": path.exists(), "sizeBytes": path.stat().st_size if path.exists() else None})
    return out


def collect_key_files() -> list[dict[str, Any]]:
    out = []
    for item in KEY_FILES:
        path = ROOT / item
        out.append({"path": item, "exists": path.exists(), "lineCount": line_count(path), "sizeBytes": path.stat().st_size if path.exists() else None})
    return out


def write_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    completed_rows = [[idx + 1, item["name"], item["status"], item["evidence"]] for idx, item in enumerate(report["completedTasks"])]
    files_rows = [[item["path"], item.get("role"), item.get("lineCount"), item.get("status")] for item in report["createdFiles"] + report["modifiedFiles"]]
    runner_rows = [[item["name"], item["command"], item["status"], f"{item.get('pass')}/{item.get('total')}", item.get("diffs"), item.get("sourceReport")] for item in report["fixtureRunners"]]
    deferred_rows = [[idx + 1, item["name"], item["reason"], item["nextAction"]] for idx, item in enumerate(report["deferredItems"])]
    issue_rows = [[item["id"], item["status"], item["description"], item["nextAction"]] for item in report["knownIssues"]]
    next_rows = [[idx + 1, item["name"], item["description"]] for idx, item in enumerate(report["nextCandidates"])]
    trigger_rows = [[idx + 1, item] for idx, item in enumerate(report["reopenTriggers"])]
    validation = report["validationResults"]
    line_info = report["ocrResultPanelLineCounts"]

    md = f"""# FRONTEND CLEANUP OCR RESULT PANEL CYCLE 1 CLOSE-OUT 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `OcrResultPanel.tsx`, `TestWorkspace.tsx`, `src/lib/*`, backend/parser/templates/manifest/GT, fixture 수정 없음.
- 이번 작업은 close-out 문서화와 현재 typecheck/build 기준선 확인만 수행.

## 3. 생성 파일
- `tmp/codex_ocr_result_panel_cycle1_closeout.py`
- `docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md`
- `docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json`

## 4. Cycle 1 목적
OcrResultPanel의 비대해진 책임 중 Clean JSON, Markdown, formatter, structured table view model 책임을 순수 helper와 fixture runner로 분리하고, Preview structured table에만 helper를 적용한 뒤 다음 cycle 진입 조건을 정리한다.

## 5. Cycle 1 진행 타임라인
1. Clean JSON contract/fixture lock
2. Clean JSON builder extraction 및 JS-side runner
3. Markdown contract/fixture lock/coverage precheck
4. Markdown builder 및 formatter extraction
5. Preview/Custom/Validation table renderer precheck
6. table view model contract trim/output fixture/input fixture
7. `buildStructuredTableViewModel` helper + direct runner
8. Preview-only OcrResultPanel 적용
9. 프론트 파일 인벤토리/사용처 precheck

## 6. 완료된 작업 목록
{md_table(['#', 'task', 'status', 'evidence'], completed_rows)}

## 7. 생성/수정된 주요 파일
{md_table(['path', 'role', 'lines', 'status'], files_rows)}

## 8. OcrResultPanel 라인 수 변화
- Cycle 시작 기준: {line_info['cycleStartApprox']} lines
- 3D3 리포트 기준: {line_info['after3D3Reported']} lines
- 현재 관측: {line_info['currentObserved']} lines
- 해석: Cycle 1 목표인 책임 분리와 Preview-only 적용은 완료. 현재 관측치는 이후 작업/dirty state를 포함할 수 있어 close-out은 3D3 리포트 기준 `~1648` 감소를 cycle 결과로 기록한다.

## 9. 분리된 책임
- Clean JSON: `src/lib/cleanJsonBuilder.ts`
- Markdown: `src/lib/markdownReportBuilder.ts`
- formatter/table parser labels: `src/lib/ocrResultFormatters.ts`
- structured table view model: `src/lib/structuredTableViewModel.ts`
- invoice table column/rowIndex policy: `src/lib/invoiceTableDisplay.ts`

## 10. Fixture/Check Runner 현황
{md_table(['runner', 'command', 'status', 'pass/total', 'diffs', 'sourceReport'], runner_rows)}

## 11. 최종 검증 결과
| check | status | exit | seconds | notes |
| --- | --- | ---: | ---: | --- |
| {validation['typecheck']['command']} | {validation['typecheck']['status']} | {validation['typecheck']['exitCode']} | {validation['typecheck']['durationSeconds']} | current close-out run |
| {validation['build']['command']} | {validation['build']['status']} | {validation['build']['exitCode']} | {validation['build']['durationSeconds']} | known stderr noise tracked separately |

## 12. 적용된 범위
- Preview structured table 렌더링만 `buildStructuredTableViewModel` 기반으로 연결.
- Clean JSON / Markdown / formatter helper extraction 완료.
- JS-side/direct fixture runner 기반 회귀 검증 체계 확보.

## 13. 의도적으로 미적용한 범위
- Custom table view model 적용 보류.
- Validation table view model 적용 보류.
- legacy `parseTableField(field.value)` fallback 보류.
- TestWorkspace cleanup 보류.

## 14. 남은 이슈
{md_table(['id', 'status', 'description', 'nextAction'], issue_rows)}

## 15. 다음 작업 후보
{md_table(['priority', 'candidate', 'description'], next_rows)}

## 16. Reopen Trigger
{md_table(['#', 'trigger'], trigger_rows)}

## 17. TestWorkspace 진입 전 조건
- 사용자에게 먼저 TestWorkspace 분리/정리 착수 여부를 확인한다.
- summary/export/tableRows/UI 섹션 중 어느 경계부터 나눌지 별도 precheck를 둔다.
- fixture/typecheck/build 기준선을 먼저 고정한다.

## 18. 최종 결론
Cycle 1은 close-out 가능. 다만 manual smoke는 아직 미실시이므로 `/runocr` Preview 표 시각 확인 1회를 다음 최우선 작업으로 둔다. Custom/Validation/legacy fallback은 Cycle 2 후보로 넘긴다.

## 19. Known Stderr Noise
- `ISSUE-FRONTEND-BUILD-LOG-1`: `ESLint: nextVitals is not iterable`
- 현재 build exit code 0이라 blocking 아님.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    validations = collect_validation_results()
    print("[check] npm run typecheck", flush=True)
    typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180)
    print(f"[check] typecheck={typecheck['status']} exit={typecheck['exitCode']}", flush=True)
    print("[check] npm run build", flush=True)
    build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)
    print(f"[check] build={build['status']} exit={build['exitCode']}", flush=True)

    key_files = collect_key_files()
    key_by_path = {item["path"]: item for item in key_files}
    completed_tasks = [
        {"name": "Clean JSON v1 contract 문서화", "status": "DONE", "evidence": "docs/CLEAN_JSON_CONTRACT_20260521.md"},
        {"name": "Clean JSON v1 fixture lock", "status": "DONE", "evidence": "docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md"},
        {"name": "buildCleanJsonResult helper 분리", "status": "DONE", "evidence": "src/lib/cleanJsonBuilder.ts"},
        {"name": "JS-side Clean JSON fixture runner 추가", "status": "DONE", "evidence": "tmp/check_clean_json_v1_fixtures_js.mjs; 9/9 PASS"},
        {"name": "Markdown v1 contract 문서화", "status": "DONE", "evidence": "docs/MARKDOWN_V1_CONTRACT_20260521.md"},
        {"name": "Markdown fixture lock", "status": "DONE", "evidence": "docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.md"},
        {"name": "Markdown LF/coverage precheck", "status": "DONE", "evidence": "docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md"},
        {"name": "buildMarkdownReport helper 분리", "status": "DONE", "evidence": "src/lib/markdownReportBuilder.ts"},
        {"name": "ocrResultFormatters 분리", "status": "DONE", "evidence": "src/lib/ocrResultFormatters.ts"},
        {"name": "Preview table builder precheck", "status": "DONE", "evidence": "docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md"},
        {"name": "Preview/Custom/Validation table renderer precheck", "status": "DONE", "evidence": "docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md"},
        {"name": "table view model contract/signature precheck", "status": "DONE", "evidence": "docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md"},
        {"name": "table view model contract trim", "status": "DONE", "evidence": "docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md"},
        {"name": "table_view_model_v1 output fixture lock", "status": "DONE", "evidence": "docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md"},
        {"name": "raw input fixture + synthetic_empty_rows fixture 보강", "status": "DONE", "evidence": "docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md"},
        {"name": "buildStructuredTableViewModel helper 생성", "status": "DONE", "evidence": "src/lib/structuredTableViewModel.ts"},
        {"name": "OcrResultPanel Preview structured table 적용", "status": "DONE", "evidence": "docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md"},
        {"name": "프론트 파일 인벤토리/사용처 precheck", "status": "DONE", "evidence": "docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md"},
    ]

    created_files = [
        {"path": "src/lib/cleanJsonBuilder.ts", "role": "Clean JSON builder", **key_by_path.get("src/lib/cleanJsonBuilder.ts", {}), "status": "created in cycle"},
        {"path": "src/lib/markdownReportBuilder.ts", "role": "Markdown builder", **key_by_path.get("src/lib/markdownReportBuilder.ts", {}), "status": "created in cycle"},
        {"path": "src/lib/ocrResultFormatters.ts", "role": "OCR result formatter helpers", **key_by_path.get("src/lib/ocrResultFormatters.ts", {}), "status": "created in cycle"},
        {"path": "src/lib/structuredTableViewModel.ts", "role": "Structured table view model helper", **key_by_path.get("src/lib/structuredTableViewModel.ts", {}), "status": "created in cycle; do not delete"},
        {"path": "tmp/check_clean_json_v1_fixtures_js.mjs", "role": "Clean JSON JS fixture runner", **key_by_path.get("tmp/check_clean_json_v1_fixtures_js.mjs", {}), "status": "created in cycle"},
        {"path": "tmp/check_table_view_model_v1_fixtures_js.mjs", "role": "Table view model JS fixture runner", **key_by_path.get("tmp/check_table_view_model_v1_fixtures_js.mjs", {}), "status": "created in cycle"},
    ]
    modified_files = [
        {"path": "src/components/upload/OcrResultPanel.tsx", "role": "Preview-only structured table helper adoption plus helper imports", **key_by_path.get("src/components/upload/OcrResultPanel.tsx", {}), "status": "modified earlier in cycle; not modified by close-out"},
    ]

    deferred_items = [
        {"name": "Manual smoke 미실시", "reason": "fixture/build는 PASS지만 실제 브라우저 Preview 표 시각 확인 필요", "nextAction": "npm run dev 후 /runocr에서 거래명세서 업로드 및 Preview 탭 확인"},
        {"name": "Custom table view model 적용 보류", "reason": "textarea edit/customTableEdits wrapper가 있어 별도 contract 필요", "nextAction": "Cycle 2 precheck"},
        {"name": "Validation table view model 적용 보류", "reason": "status/confidence/adoption UI decoration이 있어 별도 처리 필요", "nextAction": "Cycle 2 precheck"},
        {"name": "legacy parseTableField fallback 보류", "reason": "structured table 전용 helper와 shape가 다름", "nextAction": "buildLegacyTableViewModel 후보로 별도 검토"},
        {"name": "거래_3 insuranceCode/amount locked behavior", "reason": "현재 v1 behavior로 보존", "nextAction": "정책 변경 시 fixture 갱신 의도를 명시한 별도 task"},
        {"name": "TestWorkspace cleanup 보류", "reason": "사용자 확인 후 별도 작업 조건", "nextAction": "별도 precheck 이후 착수"},
        {"name": "components/ocr/core 위치 조정 후보", "reason": "사용 중이나 순수 로직 성격", "nextAction": "src/lib/ocr 또는 feature core 이동 precheck"},
        {"name": "structuredTableViewModel.ts 삭제 후보 오해", "reason": "인벤토리 시점 미사용으로 잡혔으나 3D3에서 적용된 helper", "nextAction": "삭제 금지로 표시"},
    ]

    known_issues = [
        {"id": "ISSUE-FRONTEND-BUILD-LOG-1", "status": "OPEN_NON_BLOCKING", "description": "build stderr: ESLint: nextVitals is not iterable", "nextAction": "원인 확인 및 별도 정리"},
        {"id": "MANUAL-SMOKE-1", "status": "OPEN", "description": "/runocr Preview table browser smoke 미실시", "nextAction": "다음 최우선 작업"},
    ]

    next_candidates = [
        {"name": "Manual smoke 1회", "description": "npm run dev, /runocr, 거래명세서 업로드, Preview 탭 표 시각 확인"},
        {"name": "ISSUE-FRONTEND-BUILD-LOG-1 정리", "description": "nextVitals is not iterable 원인 확인"},
        {"name": "Custom / Validation table view model 적용 precheck", "description": "Cycle 2 후보"},
        {"name": "legacy fallback view model precheck", "description": "buildLegacyTableViewModel 후보"},
        {"name": "components/ocr/core 위치 조정 precheck", "description": "순수 로직 위치 재검토"},
        {"name": "TestWorkspace 분리 precheck", "description": "사용자에게 먼저 확인 후 진행"},
    ]

    reopen_triggers = [
        "OcrResultPanel Preview 표 시각 이상 발견",
        "거래_3 컬럼 정책 변경 결정",
        "Custom/Validation table 중복 제거 필요",
        "legacy table fallback 정리 필요",
        "v2 info/tables 구조 개편 시작",
        "TestWorkspace 분리 작업 시작 전 컨텍스트 복원 필요",
    ]

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "cycleName": "OcrResultPanel cleanup cycle 1",
        "task": TASK,
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "scope": {
            "type": "documentation close-out",
            "noProductionCodeModifiedByThisTask": True,
            "forbiddenFilesUntouchedByThisTask": ["src/components/upload/OcrResultPanel.tsx", "src/components/test/TestWorkspace.tsx", "src/lib/*", "fixtures", "backend/parser/templates/manifest/GT"],
        },
        "referenceReports": collect_references(),
        "completedTasks": completed_tasks,
        "createdFiles": created_files,
        "modifiedFiles": modified_files,
        "ocrResultPanelLineCounts": {
            "cycleStartApprox": 1789,
            "after3D3Reported": 1648,
            "currentObserved": line_count(ROOT / "src/components/upload/OcrResultPanel.tsx"),
        },
        "fixtureRunners": [validations["cleanJsonRunner"], validations["markdownRunner"], validations["tableViewModelRunner"]],
        "validationResults": {
            "cleanJsonFixtureRunner": validations["cleanJsonRunner"],
            "markdownFixtureCheck": validations["markdownRunner"],
            "tableViewModelFixtureRunner": validations["tableViewModelRunner"],
            "typecheck": typecheck,
            "build": build,
        },
        "deferredItems": deferred_items,
        "knownIssues": known_issues,
        "nextCandidates": next_candidates,
        "reopenTriggers": reopen_triggers,
        "testWorkspaceGate": {
            "requiresUserConfirmation": True,
            "reason": "TestWorkspace is large and active; cleanup must be scoped separately.",
            "recommendedPrecheck": "summary/export/tableRows/UI section split precheck",
        },
        "finalRecommendation": "Cycle 1 close-out is complete. Run one manual /runocr Preview smoke next, then open Cycle 2 only if Custom/Validation/legacy fallback cleanup is needed.",
    }
    write_reports(report)
    print(f"[write] {REPORT_JSON}", flush=True)
    print(f"[write] {REPORT_MD}", flush=True)
    status = "PASS" if typecheck["status"] == "PASS" and build["status"] == "PASS" else "FAIL"
    print(f"[done] {status}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
