from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS = PROJECT_ROOT / "docs"
MD_PATH = DOCS / "FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_20260522.md"
JSON_PATH = DOCS / "FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_20260522.json"


RUNOCR_FILES = [
    "src/components/runocr/RunOcrWorkspace.tsx",
    "src/components/runocr/ui/RunOcrResultLayout.tsx",
    "src/components/runocr/ui/OcrResultPanel.tsx",
    "src/components/runocr/ui/OcrDocViewer.tsx",
    "src/components/runocr/ui/CornerAdjust.tsx",
    "src/components/runocr/utils/buildOcrFormData.ts",
    "src/components/runocr/utils/runOcrRequest.ts",
    "src/components/runocr/utils/mapOcrResponse.ts",
]


FILE_ROLES = [
    {
        "path": "src/components/runocr/RunOcrWorkspace.tsx",
        "role": "RunOCR 전체 상태/흐름/orchestration",
        "notes": "파일/템플릿/모델 상태, OCR 실행, history/autofill 흐름, viewer/result 조립을 담당한다.",
    },
    {
        "path": "src/components/runocr/ui/RunOcrResultLayout.tsx",
        "role": "OCR 결과 화면 layout",
        "notes": "viewer/resultPanel/scanOverlay/hiddenFileInput node 배치만 담당한다.",
    },
    {
        "path": "src/components/runocr/ui/OcrResultPanel.tsx",
        "role": "Preview/Custom/Validation/Clean JSON/Markdown/Raw JSON 결과 패널",
        "notes": "결과 표시와 tab별 UI를 담당하며 helper 기반 출력 계약과 연결된다.",
    },
    {
        "path": "src/components/runocr/ui/OcrDocViewer.tsx",
        "role": "문서 viewer 및 bbox overlay",
        "notes": "문서 이미지/PDF와 field overlay, 선택 interaction을 담당한다.",
    },
    {
        "path": "src/components/runocr/ui/CornerAdjust.tsx",
        "role": "normalized corner 보정 UI",
        "notes": "0~1 normalized corner 좌표를 표시하고 drag update를 상위로 전달한다.",
    },
    {
        "path": "src/components/runocr/utils/buildOcrFormData.ts",
        "role": "/ocr/extract FormData 구성",
        "notes": "backend multipart key 계약과 FormData key parity 검증 대상이다.",
    },
    {
        "path": "src/components/runocr/utils/runOcrRequest.ts",
        "role": "OCR API 호출 경계",
        "notes": "endpoint 결정, FormData 구성, fetch, ok/json 처리까지만 담당한다.",
    },
    {
        "path": "src/components/runocr/utils/mapOcrResponse.ts",
        "role": "raw OCR response -> OcrResult 순수 mapping",
        "notes": "history/autofill/restore/React state에 의존하지 않는 mapping boundary다.",
    },
]


COMPLETED_TASKS = [
    {
        "name": "FRONTEND-STRUCTURE-1-RUNOCR-FOLDER-MOVE",
        "summary": "components/upload를 components/runocr로 이동하고 UploadWorkspace를 RunOcrWorkspace로 rename했다.",
        "report": "docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.md",
    },
    {
        "name": "FRONTEND-STRUCTURE-1B-RUNOCR-WORKSPACE-NAMING-CLEANUP",
        "summary": "UploadWorkspace 계열 내부 식별자를 RunOcrWorkspace 계열로 정리했다.",
        "report": "docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.md",
    },
    {
        "name": "FRONTEND-STRUCTURE-2A-RUNOCR-BUILD-OCR-FORMDATA-EXTRACT",
        "summary": "buildOcrFormData.ts를 생성하고 /ocr/extract FormData 구성을 분리했다. key parity PASS.",
        "report": "docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.md",
    },
    {
        "name": "FRONTEND-STRUCTURE-2B-RUNOCR-REQUEST-EXTRACT",
        "summary": "runOcrRequest.ts를 생성하고 endpoint, fetch, ok check, json parse를 분리했다.",
        "report": "docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.md",
    },
    {
        "name": "FRONTEND-STRUCTURE-2C-RUNOCR-BUILD-RUN-OCR-RESULT-EXTRACT",
        "summary": "mapOcrResponse.ts를 생성하고 buildRunOcrResult 순수 mapping을 분리했다.",
        "report": "docs/FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.md",
    },
    {
        "name": "MARKDOWN-V1-TRADE7-FIXTURE-REBAKE",
        "summary": "trade_7 markdown fixture drift를 현재 backend actual 기준으로 rebake해 markdown runner 6/6 PASS를 회복했다.",
        "report": "docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.md",
    },
    {
        "name": "FRONTEND-STRUCTURE-3A-RUNOCR-RESULT-LAYOUT-SPLIT",
        "summary": "RunOcrResultLayout.tsx를 생성하고 결과 화면 layout을 node composition으로 분리했다.",
        "report": "docs/FRONTEND_STRUCTURE_3A_RUNOCR_RESULT_LAYOUT_SPLIT_20260522.md",
    },
    {
        "name": "FRONTEND-STRUCTURE-3B-RUNOCR-DOC-COMMENTS",
        "summary": "RunOCR 8개 파일에 file header/JSDoc을 추가하고 comments-only 검증을 완료했다.",
        "report": "docs/FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS_20260522.md",
    },
]


RESPONSIBILITY_BOUNDARIES = [
    {"responsibility": "OCR 요청 파라미터 구성", "owner": "src/components/runocr/utils/buildOcrFormData.ts"},
    {"responsibility": "OCR API 호출", "owner": "src/components/runocr/utils/runOcrRequest.ts"},
    {"responsibility": "raw response mapping", "owner": "src/components/runocr/utils/mapOcrResponse.ts"},
    {"responsibility": "결과 화면 layout", "owner": "src/components/runocr/ui/RunOcrResultLayout.tsx"},
    {"responsibility": "결과 표시 UI", "owner": "src/components/runocr/ui/OcrResultPanel.tsx"},
    {"responsibility": "문서 viewer", "owner": "src/components/runocr/ui/OcrDocViewer.tsx"},
    {"responsibility": "RunOCR 실행 orchestration/history/autofill", "owner": "src/components/runocr/RunOcrWorkspace.tsx"},
]


REMAINING_ISSUES = [
    "runOcr() 본문에 autofill/history/restore orchestration 응집이 500+ 줄 남아 있다.",
    "RunOcrControls는 props 26개+ 위험이 있어 한 번에 큰 컴포넌트로 분리하면 안 된다.",
    "기본 화면 main return은 아직 미분리 상태다.",
    "history/restore adapter 분리는 별도 precheck가 필요하다.",
    "ocr-server/data/templates.json dirty 상태가 남아 있다.",
    "TPL-95328E52 dirty 영향 precheck가 필요할 수 있다.",
    "build stderr의 ESLint: nextVitals is not iterable은 exit 0 non-blocking known issue다.",
    "TestWorkspace는 사용자 확인 전 작업 금지다.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_command(args: list[str]) -> dict:
    print(f"$ {' '.join(args)}")
    proc = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        shell=False,
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    return {
        "command": " ".join(args),
        "exitCode": proc.returncode,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "stdoutTail": proc.stdout[-4000:],
        "stderrTail": proc.stderr[-4000:],
        "knownStderrNoise": "ESLint: nextVitals is not iterable" if "nextVitals is not iterable" in proc.stderr else None,
    }


def git_status() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        shell=False,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def file_info(rel: str) -> dict:
    path = PROJECT_ROOT / rel
    exists = path.exists()
    return {
        "path": rel,
        "exists": exists,
        "lineCount": len(path.read_text(encoding="utf-8").splitlines()) if exists else None,
        "sizeBytes": path.stat().st_size if exists else None,
    }


def report_exists(rel: str) -> bool:
    return (PROJECT_ROOT / rel).exists()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    DOCS.mkdir(parents=True, exist_ok=True)

    current_structure = {
        "root": "src/components/runocr",
        "files": [file_info(rel) for rel in RUNOCR_FILES],
    }

    completed_tasks = [
        {**task, "reportExists": report_exists(task["report"])}
        for task in COMPLETED_TASKS
    ]

    validation_status = {
        "tableViewModelRunner": {"status": "PASS", "result": "8/8", "source": "recent completed task reports"},
        "cleanJsonRunner": {"status": "PASS", "result": "9/9", "source": "recent completed task reports"},
        "markdownFixture": {"status": "PASS", "result": "6/6", "source": "MARKDOWN-V1-TRADE7-FIXTURE-REBAKE and 3B reports"},
        "formDataKeyParity": {"status": "PASS", "source": "FRONTEND-STRUCTURE-2A"},
        "requestBoundaryStaticCheck": {"status": "PASS", "source": "FRONTEND-STRUCTURE-2B"},
        "responseMappingBoundaryStaticCheck": {"status": "PASS", "source": "FRONTEND-STRUCTURE-2C"},
        "resultLayoutBoundaryStaticCheck": {"status": "PASS", "source": "FRONTEND-STRUCTURE-3A"},
        "docCommentsStaticCheck": {"status": "PASS", "source": "FRONTEND-STRUCTURE-3B"},
    }

    dirty_status = git_status()
    typecheck = run_command(["npm.cmd", "run", "typecheck"])
    build = run_command(["npm.cmd", "run", "build"])
    validation_status["typecheck"] = typecheck
    validation_status["build"] = build

    reentry_conditions = {
        "cycle2": [
            "Template folder ownership 정리 후 재진입한다.",
            "RunOcrControls는 큰 단일 컴포넌트가 아니라 작은 control group 단위로 precheck한다.",
            "후보: TemplateTopbar, FileUploadPanel, ModelOptionPanel, RunButtonBar, TemplateHoverTooltip.",
        ],
        "cycle3": [
            "History/Restore 구조 정리 후 재진입한다.",
            "history/autofill orchestration adapter 분리를 검토한다.",
            "후보: buildRunOcrHistoryRecord, applyRunOcrAutofill, restore/autofill adapter.",
        ],
        "commonMigration": [
            "feature 폴더 안정화 후 common/utils 이동 여부를 재점검한다.",
            "runocr/utils 중 common 후보가 있는지 확인한다.",
            "cleanJson/markdown/tableViewModel/invoiceTableDisplay와 import 경계를 확인한다.",
        ],
    }

    next_steps = [
        "Template folder ownership precheck",
        "Template folder 1차 구조 정리",
        "TPL-95328E52 dirty 영향 precheck",
        "RunOCR Cycle 2는 Template 구조 정리 후 재진입",
        "common/utils 이동은 feature 폴더 안정화 후 진행",
        "TestWorkspace는 사용자 확인 후 진행",
    ]

    report = {
        "generatedAt": now_iso(),
        "projectRoot": str(PROJECT_ROOT),
        "cycleName": "RunOCR Cycle 1",
        "codeModified": False,
        "commentsAdded": False,
        "currentStructure": current_structure,
        "completedTasks": completed_tasks,
        "fileRoles": FILE_ROLES,
        "responsibilityBoundaries": RESPONSIBILITY_BOUNDARIES,
        "validationStatus": validation_status,
        "remainingIssues": REMAINING_ISSUES,
        "reentryConditions": reentry_conditions,
        "nextSteps": next_steps,
        "dirtyStatus": dirty_status,
    }

    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MD_PATH.write_text(build_markdown(report), encoding="utf-8")

    print(json.dumps({"md": str(MD_PATH), "json": str(JSON_PATH)}, ensure_ascii=False, indent=2))
    return 0 if typecheck["exitCode"] == 0 and build["exitCode"] == 0 else 1


def build_markdown(report: dict) -> str:
    structure_rows = "\n".join(
        f"| `{item['path']}` | {item['exists']} | {item['lineCount']} | {item['sizeBytes']} |"
        for item in report["currentStructure"]["files"]
    )
    task_rows = "\n".join(
        f"| {idx}. {task['name']} | {task['summary']} | `{task['report']}` | {task['reportExists']} |"
        for idx, task in enumerate(report["completedTasks"], start=1)
    )
    role_rows = "\n".join(
        f"| `{item['path']}` | {item['role']} | {item['notes']} |"
        for item in report["fileRoles"]
    )
    boundary_rows = "\n".join(
        f"| {item['responsibility']} | `{item['owner']}` |"
        for item in report["responsibilityBoundaries"]
    )
    validation = report["validationStatus"]
    validation_rows = "\n".join(
        [
            f"| typecheck | {validation['typecheck']['status']} | exit {validation['typecheck']['exitCode']} |",
            f"| build | {validation['build']['status']} | exit {validation['build']['exitCode']}; known noise: {validation['build']['knownStderrNoise'] or '없음'} |",
            f"| table view model runner | {validation['tableViewModelRunner']['status']} | {validation['tableViewModelRunner']['result']} |",
            f"| Clean JSON runner | {validation['cleanJsonRunner']['status']} | {validation['cleanJsonRunner']['result']} |",
            f"| markdown fixture | {validation['markdownFixture']['status']} | {validation['markdownFixture']['result']} |",
            f"| FormData key parity | {validation['formDataKeyParity']['status']} | {validation['formDataKeyParity']['source']} |",
            f"| request boundary static check | {validation['requestBoundaryStaticCheck']['status']} | {validation['requestBoundaryStaticCheck']['source']} |",
            f"| response mapping boundary static check | {validation['responseMappingBoundaryStaticCheck']['status']} | {validation['responseMappingBoundaryStaticCheck']['source']} |",
            f"| result layout boundary static check | {validation['resultLayoutBoundaryStaticCheck']['status']} | {validation['resultLayoutBoundaryStaticCheck']['source']} |",
            f"| doc comments static check | {validation['docCommentsStaticCheck']['status']} | {validation['docCommentsStaticCheck']['source']} |",
        ]
    )

    return f"""# FRONTEND RUNOCR CYCLE 1 CLOSEOUT 20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 주석 추가: 없음
- 파일 이동/import 수정/fixture 수정/templates.json 수정/backend 수정: 없음
- 이번 작업은 close-out 문서화만 수행했다.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_cycle1_closeout.py`
- `docs/FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_20260522.md`
- `docs/FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_20260522.json`

## 4. Cycle 1 목적
RunOCR Cycle 1의 목적은 업로드 중심의 기존 구조를 `runocr` feature boundary로 옮기고, OCR 요청 구성/API 호출/raw response mapping/결과 layout을 찾기 쉬운 파일로 분리하는 것이었다. 라인 수 감소보다 유지보수자가 "요청은 어디?", "mapping은 어디?", "결과 layout은 어디?"를 바로 찾게 만드는 데 초점을 뒀다.

## 5. 완료 작업 요약
| task | summary | report | exists |
| --- | --- | --- | --- |
{task_rows}

## 6. 현재 RunOCR 구조
```text
src/components/runocr/
  RunOcrWorkspace.tsx
  ui/
    RunOcrResultLayout.tsx
    OcrResultPanel.tsx
    OcrDocViewer.tsx
    CornerAdjust.tsx
  utils/
    buildOcrFormData.ts
    runOcrRequest.ts
    mapOcrResponse.ts
```

| path | exists | lines | bytes |
| --- | --- | ---: | ---: |
{structure_rows}

## 7. 파일별 역할
| path | role | notes |
| --- | --- | --- |
{role_rows}

## 8. 책임 경계
| responsibility | owner |
| --- | --- |
{boundary_rows}

## 9. 검증 상태
| check | status | detail |
| --- | --- | --- |
{validation_rows}

## 10. 남은 이슈
{chr(10).join(f"- {item}" for item in report['remainingIssues'])}

## 11. RunOCR Cycle 2 재진입 조건
{chr(10).join(f"- {item}" for item in report['reentryConditions']['cycle2'])}

## 12. RunOCR Cycle 3 재진입 조건
{chr(10).join(f"- {item}" for item in report['reentryConditions']['cycle3'])}

## 13. common/utils 이동 전 재점검
{chr(10).join(f"- {item}" for item in report['reentryConditions']['commonMigration'])}

## 14. 다음 추천 작업
{chr(10).join(f"{idx}. {item}" for idx, item in enumerate(report['nextSteps'], start=1))}

## 15. 주의사항
- TestWorkspace 작업은 사용자 확인 전 금지한다.
- common/utils 이동은 feature 폴더 안정화 후 진행한다.
- `ocr-server/data/templates.json` dirty 상태와 `TPL-95328E52` 영향은 별도 precheck로 다룬다.
- build stderr의 `ESLint: nextVitals is not iterable`은 exit 0 non-blocking known issue로 추적한다.

## 16. 현재 dirty 상태
이번 close-out에서 dirty 상태는 되돌리지 않았다.

```text
{chr(10).join(report['dirtyStatus'])}
```
"""


if __name__ == "__main__":
    raise SystemExit(main())
