from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS = PROJECT_ROOT / "docs"
MD_PATH = DOCS / "FRONTEND_RUNOCR_COMMENT_PLAN_PRECHECK_20260522.md"
JSON_PATH = DOCS / "FRONTEND_RUNOCR_COMMENT_PLAN_PRECHECK_20260522.json"
CSV_PATH = DOCS / "FRONTEND_RUNOCR_COMMENT_PLAN_MAP_20260522.csv"

TARGET_FILES = [
    "src/components/runocr/RunOcrWorkspace.tsx",
    "src/components/runocr/ui/RunOcrResultLayout.tsx",
    "src/components/runocr/ui/OcrResultPanel.tsx",
    "src/components/runocr/ui/OcrDocViewer.tsx",
    "src/components/runocr/ui/CornerAdjust.tsx",
    "src/components/runocr/utils/buildOcrFormData.ts",
    "src/components/runocr/utils/runOcrRequest.ts",
    "src/components/runocr/utils/mapOcrResponse.ts",
]


ROLE_DATA = {
    "src/components/runocr/RunOcrWorkspace.tsx": {
        "role": "RunOCR 탭 최상위 workspace",
        "mainResponsibility": "파일/템플릿/모델 상태, OCR 실행 흐름, history/autofill orchestration, viewer/result 조립을 담당한다.",
        "boundary": "FormData 구성, API 호출, raw response mapping, 결과 layout의 세부 구현은 utils/ui 파일로 위임한다.",
        "doNotPutHere": "FormData key 세부 계약, fetch 세부 구현, 순수 mapping 세부 구현, OcrResultPanel 내부 tab 렌더링 정책.",
        "relatedFiles": [
            "buildOcrFormData.ts",
            "runOcrRequest.ts",
            "mapOcrResponse.ts",
            "RunOcrResultLayout.tsx",
            "OcrResultPanel.tsx",
            "OcrDocViewer.tsx",
        ],
        "header": "RunOCR 탭의 최상위 orchestration 컴포넌트입니다. 파일/템플릿/모델 상태와 OCR 실행 흐름을 관리하고, 요청 구성/API 호출/응답 매핑/결과 레이아웃의 세부 구현은 runocr utils/ui 파일에 위임합니다. 이 파일을 수정할 때는 history/autofill 저장 순서와 결과 state 반영 순서를 함께 확인해야 합니다.",
        "riskNotes": "runOcr 함수가 history/autofill/result state를 이어 붙이는 중심 경로라 회귀 위험이 크다.",
    },
    "src/components/runocr/ui/RunOcrResultLayout.tsx": {
        "role": "RunOCR 결과 화면 layout 전용 presentational component",
        "mainResponsibility": "viewer/resultPanel/scanOverlay/hiddenFileInput node를 배치한다.",
        "boundary": "OCR state, API, history, autofill, result mapping을 알지 않는다.",
        "doNotPutHere": "OcrDocViewer/OcrResultPanel props 조립, OCR 실행 handler, 상태 변경 로직.",
        "relatedFiles": ["RunOcrWorkspace.tsx", "OcrDocViewer.tsx", "OcrResultPanel.tsx"],
        "header": "RunOCR 결과 화면의 배치만 담당하는 presentational layout입니다. viewer/resultPanel/scanOverlay/hiddenFileInput을 React node로 받아 배치하며, OCR 상태나 API 흐름을 직접 알지 않도록 유지합니다.",
        "riskNotes": "node composition 경계를 유지해야 props 중계 컴포넌트로 비대해지지 않는다.",
    },
    "src/components/runocr/ui/OcrResultPanel.tsx": {
        "role": "OCR 결과 표시 패널",
        "mainResponsibility": "Preview, Custom, Validation, Clean JSON, Markdown, Raw JSON tab을 렌더링한다.",
        "boundary": "결과 표시와 사용자 편집/검증 UI를 담당하고, Clean JSON/Markdown/table view model 생성은 helper를 사용한다.",
        "doNotPutHere": "RunOCR API 호출, workspace-level history 저장, 파일/템플릿 선택 상태.",
        "relatedFiles": [
            "cleanJsonBuilder.ts",
            "markdownReportBuilder.ts",
            "structuredTableViewModel.ts",
            "invoiceTableDisplay.ts",
        ],
        "header": "OCR 결과 패널입니다. Preview/Custom/Validation/Clean JSON/Markdown/Raw JSON 표시를 담당하며, JSON/Markdown/table view model 생성은 전용 helper 계약을 통해 수행합니다. tab별 표시 정책을 바꿀 때는 관련 fixture runner를 함께 확인해야 합니다.",
        "riskNotes": "파일이 크고 tab별 책임이 많으므로 실제 주석 추가는 header와 핵심 helper 경계 중심으로 제한하는 편이 안전하다.",
    },
    "src/components/runocr/ui/OcrDocViewer.tsx": {
        "role": "OCR 대상 문서 viewer",
        "mainResponsibility": "이미지/PDF 렌더링 결과 위에 OCR field overlay를 표시하고 선택 상태를 연결한다.",
        "boundary": "문서 표시와 bbox overlay interaction에 집중한다.",
        "doNotPutHere": "OCR 요청, 결과 mapping, result tab 정책, history/autofill.",
        "relatedFiles": ["RunOcrWorkspace.tsx", "OcrResultPanel.tsx"],
        "header": "RunOCR 문서 viewer입니다. OCR 대상 이미지/PDF 렌더링 결과와 field bbox overlay를 표시하고 선택 이벤트를 workspace로 전달합니다. 원본 이미지 크기와 화면 scale 계산이 overlay 정합성에 영향을 줍니다.",
        "riskNotes": "scale/overlay 좌표 계산은 시각 회귀가 나기 쉬워 주석 가치가 있다.",
    },
    "src/components/runocr/ui/CornerAdjust.tsx": {
        "role": "문서 코너 보정 UI",
        "mainResponsibility": "이미지 위 normalized corner point를 표시/드래그하여 코너 보정 입력을 만든다.",
        "boundary": "코너 선택/드래그 interaction만 담당한다.",
        "doNotPutHere": "전처리 실행, OCR 요청, history 저장.",
        "relatedFiles": ["RunOcrWorkspace.tsx"],
        "header": "문서 코너 보정용 UI입니다. 이미지 위의 normalized corner 좌표를 표시하고 드래그 결과를 상위 컴포넌트에 전달합니다. 좌표는 0~1 비율 기준이므로 pixel 좌표와 혼동하지 않도록 주의합니다.",
        "riskNotes": "pointer event와 normalized 좌표 변환은 짧은 주석이 있으면 유지보수성이 좋아진다.",
    },
    "src/components/runocr/utils/buildOcrFormData.ts": {
        "role": "OCR 요청 FormData 구성 helper",
        "mainResponsibility": "/ocr/extract 요청에 필요한 multipart FormData key를 만든다.",
        "boundary": "request body 구성만 담당하고 fetch, response parsing, UI state를 알지 않는다.",
        "doNotPutHere": "API 호출, response ok/json 처리, 화면 result mapping.",
        "relatedFiles": ["runOcrRequest.ts", "RunOcrWorkspace.tsx"],
        "header": "/ocr/extract 요청의 FormData를 구성하는 helper입니다. backend가 기대하는 key와 append 순서를 보존하는 것이 목적이며, API 호출이나 response 처리는 runOcrRequest에서 담당합니다.",
        "riskNotes": "FormData key parity와 연결되어 함수 JSDoc에 검증 기준을 적는 것이 좋다.",
    },
    "src/components/runocr/utils/runOcrRequest.ts": {
        "role": "OCR API request helper",
        "mainResponsibility": "endpoint 결정, buildOcrFormData 호출, fetch, !ok 처리, json parsing을 담당한다.",
        "boundary": "loading/error UI state, response mapping, history/autofill은 workspace에 남긴다.",
        "doNotPutHere": "setState, toast/UI error 표시, OcrResult 변환, history/autofill.",
        "relatedFiles": ["buildOcrFormData.ts", "mapOcrResponse.ts", "RunOcrWorkspace.tsx"],
        "header": "RunOCR API 호출 helper입니다. endpoint 결정, FormData 구성, fetch, 응답 ok/json 처리까지만 담당하고 UI state나 history/autofill/mapping에는 관여하지 않습니다.",
        "riskNotes": "Error 메시지와 endpoint fallback은 request boundary 검증 대상이다.",
    },
    "src/components/runocr/utils/mapOcrResponse.ts": {
        "role": "raw OCR response to OcrResult mapper",
        "mainResponsibility": "backend raw response를 OcrResultPanel이 소비하는 OcrResult 구조로 변환한다.",
        "boundary": "순수 mapping만 담당하며 React state, history, autofill, restore, localStorage에 의존하지 않는다.",
        "doNotPutHere": "fetch, FormData, setState, history write, autofill apply.",
        "relatedFiles": ["runOcrRequest.ts", "RunOcrWorkspace.tsx", "OcrResultPanel.tsx"],
        "header": "backend raw OCR response를 OcrResultPanel용 OcrResult로 변환하는 순수 mapper입니다. history/autofill/restore나 React state에 의존하지 않아야 하며, field key normalization은 options로 주입받습니다.",
        "riskNotes": "raw response shape와 OcrResult contract 사이 경계라 JSDoc이 필요하다.",
    },
}


NEED_JSDOC = {
    "RunOcrWorkspace": "RunOCR 화면 전체 흐름의 owner를 설명한다.",
    "runOcr": "API 호출, raw response mapping, autofill, history 저장, result state 반영 순서를 설명한다.",
    "handlePersistEdits": "편집 결과를 history run에 반영하는 경로다.",
    "handleResultClose": "결과 화면에서 초기 화면으로 돌아갈 때 초기화되는 state 범위를 설명한다.",
    "unionSourceBoxes": "여러 OCR source box를 하나의 overlay box로 합치는 좌표 helper다.",
    "buildOcrFormData": "backend multipart key 계약과 FormData key parity 검증 대상이다.",
    "runOcrRequest": "request boundary와 UI state 비소유 원칙을 설명한다.",
    "buildRunOcrResult": "raw response에서 OcrResult로 매핑하는 순수 contract다.",
    "RunOcrResultLayout": "node composition layout 원칙을 설명한다.",
    "OcrResultPanel": "tab별 결과 표시 패널의 책임과 fixture runner 영향 범위를 설명한다.",
    "OcrDocViewer": "scale/overlay 좌표 계산과 선택 이벤트 전달 역할을 설명한다.",
    "updateScale": "viewer overlay 정합성에 영향을 주는 scale 측정 helper다.",
    "CornerAdjust": "normalized corner coordinate interaction을 설명한다.",
    "onImgClick": "corner point 추가 방식과 normalized coordinate 변환을 설명한다.",
    "onPointerMove": "drag 중 normalized coordinate update를 설명한다.",
}


NO_COMMENT_PATTERNS = [
    "단순 setState wrapper",
    "단순 toggle handler",
    "JSX node 변수 또는 JSX wrapper",
    "명확한 상수 import/export",
    "props type 내부 모든 field",
    "1~3줄짜리 명확한 local helper",
    "파일 header와 같은 내용을 반복하는 함수 주석",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def line_count(path: Path) -> int:
    return len(read_text(path).splitlines())


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


def symbol_kind(line: str) -> str:
    if "type " in line:
        return "type"
    if "interface " in line:
        return "interface"
    if "useEffect(" in line:
        return "effect"
    if "useMemo(" in line:
        return "memo"
    if "useCallback(" in line:
        return "callback"
    if "function " in line and line.strip().startswith("export default"):
        return "component"
    if "function " in line:
        return "function"
    if re.search(r"const\s+\w+\s*=", line):
        return "const/helper"
    return "symbol"


def extract_symbols(path: Path) -> list[dict]:
    lines = read_text(path).splitlines()
    symbols: list[dict] = []
    pattern = re.compile(
        r"^\s*(export\s+default\s+function|export\s+async\s+function|export\s+function|function|export\s+type|export\s+interface|const\s+\w+\s*=|useEffect\(|useMemo\(|useCallback\()"
    )
    for i, line in enumerate(lines, start=1):
        if not pattern.search(line):
            continue
        name = None
        for regex in [
            r"export\s+default\s+function\s+(\w+)",
            r"export\s+async\s+function\s+(\w+)",
            r"export\s+function\s+(\w+)",
            r"function\s+(\w+)",
            r"export\s+type\s+(\w+)",
            r"export\s+interface\s+(\w+)",
            r"const\s+(\w+)\s*=",
        ]:
            m = re.search(regex, line)
            if m:
                name = m.group(1)
                break
        if not name:
            name = line.strip().split("(")[0].strip()
        exported = line.strip().startswith("export")
        need = name in NEED_JSDOC or (exported and symbol_kind(line) in {"component", "function"})
        if symbol_kind(line) in {"type", "interface"}:
            need = name in {"BuildOcrFormDataInput", "RunOcrRequestInput", "RunOcrResultLayoutProps"} and path.name in {
                "buildOcrFormData.ts",
                "runOcrRequest.ts",
                "RunOcrResultLayout.tsx",
            }
        complexity = "HIGH" if name in {"runOcr", "OcrResultPanel", "buildRunOcrResult"} else "MEDIUM" if need else "LOW"
        reason = NEED_JSDOC.get(name)
        if not reason and need:
            reason = "exported public boundary라 파일을 여는 유지보수자에게 책임을 알려야 한다."
        no_comment = "" if need else "이름과 주변 코드로 의미가 충분하거나 단순 derived/effect 후보라 과주석 위험이 있다."
        draft = ""
        if need:
            draft = suggested_symbol_comment(name, path.name)
        symbols.append(
            {
                "name": name,
                "kind": symbol_kind(line),
                "lineRange": [i, i],
                "exported": exported,
                "complexity": complexity,
                "shouldHaveJSDoc": need,
                "reason": reason or "",
                "commentDraft": draft,
                "noCommentReason": no_comment,
            }
        )
    return symbols


def suggested_symbol_comment(name: str, file_name: str) -> str:
    drafts = {
        "RunOcrWorkspace": "RunOCR 탭의 상태와 OCR 실행 흐름을 조율하는 최상위 workspace입니다. 요청 구성/API 호출/응답 매핑/결과 layout은 하위 util과 UI 컴포넌트에 위임합니다.",
        "runOcr": "선택된 파일과 템플릿으로 OCR을 실행하고, raw response를 OcrResult로 변환한 뒤 autofill/history/result state를 순서대로 반영합니다. FormData 구성과 fetch는 runocr utils에 위임합니다.",
        "handlePersistEdits": "사용자가 수정한 결과 필드를 현재 history run에 반영합니다. field index와 confidence/source metadata 보존 순서가 중요합니다.",
        "handleResultClose": "결과 화면을 닫고 RunOCR 초기 상태로 되돌립니다. OCR 결과, 선택 필드, canvas state, preprocessing state가 함께 초기화됩니다.",
        "unionSourceBoxes": "여러 source bbox를 하나의 overlay bbox로 합칩니다. OCR field overlay와 canvas selection 정합성에 영향을 줍니다.",
        "buildOcrFormData": "/ocr/extract가 기대하는 multipart FormData를 구성합니다. key 이름과 append 순서는 FormData parity 검증 대상입니다.",
        "runOcrRequest": "RunOCR API 호출 경계입니다. endpoint 결정, FormData 생성, fetch, ok/json 처리만 담당하고 UI state나 mapping에는 관여하지 않습니다.",
        "buildRunOcrResult": "backend raw OCR response를 OcrResultPanel용 OcrResult로 변환합니다. history/autofill/restore는 이 mapper 밖에서 처리합니다.",
        "RunOcrResultLayout": "RunOCR 결과 화면의 viewer/result node 배치만 담당합니다. OCR 상태와 handler를 직접 알지 않는 presentational boundary입니다.",
        "OcrResultPanel": "OCR 결과 tab UI를 렌더링합니다. Preview/Custom/Validation/Clean JSON/Markdown 표시 정책 변경 시 fixture runner 영향을 확인해야 합니다.",
        "OcrDocViewer": "문서 이미지와 OCR bbox overlay를 표시합니다. image scale 계산은 field overlay 위치 정합성에 직접 영향을 줍니다.",
        "updateScale": "렌더된 이미지 크기와 원본 크기 기준으로 overlay scale을 갱신합니다.",
        "CornerAdjust": "문서 코너 보정용 normalized 좌표를 표시하고 수정합니다.",
        "onImgClick": "이미지 클릭 위치를 normalized corner 좌표로 변환해 새 corner point를 추가합니다.",
        "onPointerMove": "drag 중 pointer 위치를 normalized coordinate로 변환해 corner point를 갱신합니다.",
        "BuildOcrFormDataInput": "RunOCR FormData 구성에 필요한 입력 contract입니다.",
        "RunOcrRequestInput": "RunOCR API 요청 경계에 필요한 입력 contract입니다.",
        "RunOcrResultLayoutProps": "RunOcrResultLayout이 배치할 node contract입니다. state/handler를 직접 늘리지 않는 것이 중요합니다.",
    }
    return drafts.get(name, f"{file_name}의 public boundary인 `{name}`의 책임과 수정 시 주의점을 간단히 설명합니다.")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    DOCS.mkdir(parents=True, exist_ok=True)
    files = []
    no_comment_targets = []

    for rel in TARGET_FILES:
        path = PROJECT_ROOT / rel
        data = ROLE_DATA[rel]
        symbols = extract_symbols(path)
        no_comment_targets.extend(
            {
                "file": rel,
                "name": s["name"],
                "reason": s["noCommentReason"],
            }
            for s in symbols
            if not s["shouldHaveJSDoc"]
        )
        files.append(
            {
                "path": rel,
                "lineCount": line_count(path),
                "role": data["role"],
                "mainResponsibility": data["mainResponsibility"],
                "shouldHaveFileHeaderComment": True,
                "headerCommentDraft": data["header"],
                "responsibilityBoundary": data["boundary"],
                "doNotPutHere": data["doNotPutHere"],
                "relatedFiles": data["relatedFiles"],
                "riskNotes": data["riskNotes"],
                "symbols": symbols,
            }
        )

    recommended_scope = {
        "recommendation": "RunOCR 8개 파일 전체에 파일 header를 추가하되, 함수 JSDoc은 utils 3개와 RunOcrWorkspace 핵심 흐름, RunOcrResultLayout boundary에 우선 적용한다.",
        "option": "A_LIGHTWEIGHT_HEADER_ALL_PLUS_CORE_JSDOC",
        "include": [
            "8개 RunOCR 파일 file header",
            "buildOcrFormData / runOcrRequest / buildRunOcrResult JSDoc",
            "RunOcrWorkspace / runOcr / handlePersistEdits / handleResultClose JSDoc",
            "RunOcrResultLayout JSDoc",
            "OcrDocViewer scale helper, CornerAdjust coordinate helpers는 짧게만",
        ],
        "defer": [
            "OcrResultPanel 내부 모든 helper 주석화",
            "props type field-by-field 주석",
            "단순 setter/toggle 주석",
        ],
        "risk": "MEDIUM",
        "reason": "파일 역할 header는 찾기 쉬움에 바로 기여하지만, 대형 UI 파일 내부에 주석을 과하게 넣으면 오히려 읽기 비용이 커진다.",
    }

    validation_plan = [
        "npm run typecheck",
        "npm run build",
        "node tmp/check_table_view_model_v1_fixtures_js.mjs",
        "node tmp/check_clean_json_v1_fixtures_js.mjs",
        "python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_DOC_COMMENTS_20260522",
        "FormData key parity check",
        "request boundary static check",
        "response mapping boundary static check",
        "result layout boundary static check",
        "diff review: comments-only change인지 확인",
        "no excessive comments static/manual review",
    ]

    dirty_status = git_status()
    typecheck = run_command(["npm.cmd", "run", "typecheck"])
    build = run_command(["npm.cmd", "run", "build"])

    report = {
        "generatedAt": now_iso(),
        "projectRoot": str(PROJECT_ROOT),
        "dirtyStatus": dirty_status,
        "codeModified": False,
        "commentsAdded": False,
        "files": files,
        "noCommentTargets": no_comment_targets,
        "overCommentRules": NO_COMMENT_PATTERNS,
        "recommendedScope": recommended_scope,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "FRONTEND-STRUCTURE-3B-RUNOCR-DOC-COMMENTS에서 comments-only patch로 진행한다.",
            "첫 실제 작업은 file header 8개 + core JSDoc 중심으로 제한한다.",
            "OcrResultPanel 내부 helper 전체 주석화는 별도 cycle로 미룬다.",
        ],
    }

    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["file", "lineCount", "role", "symbol", "kind", "line", "shouldHaveJSDoc", "reason"],
        )
        writer.writeheader()
        for item in files:
            if not item["symbols"]:
                writer.writerow(
                    {
                        "file": item["path"],
                        "lineCount": item["lineCount"],
                        "role": item["role"],
                        "symbol": "",
                        "kind": "",
                        "line": "",
                        "shouldHaveJSDoc": "",
                        "reason": "",
                    }
                )
            for sym in item["symbols"]:
                writer.writerow(
                    {
                        "file": item["path"],
                        "lineCount": item["lineCount"],
                        "role": item["role"],
                        "symbol": sym["name"],
                        "kind": sym["kind"],
                        "line": sym["lineRange"][0],
                        "shouldHaveJSDoc": sym["shouldHaveJSDoc"],
                        "reason": sym["reason"] or sym["noCommentReason"],
                    }
                )

    md = build_markdown(report)
    MD_PATH.write_text(md, encoding="utf-8")

    print(json.dumps({"md": str(MD_PATH), "json": str(JSON_PATH), "csv": str(CSV_PATH)}, ensure_ascii=False, indent=2))
    return 0 if typecheck["exitCode"] == 0 and build["exitCode"] == 0 else 1


def build_markdown(report: dict) -> str:
    files = report["files"]
    jsdoc_needed = [
        (f["path"], s)
        for f in files
        for s in f["symbols"]
        if s["shouldHaveJSDoc"]
    ]
    no_comment = report["noCommentTargets"][:40]
    role_rows = "\n".join(
        f"| `{f['path']}` | {f['lineCount']} | {f['role']} | {f['mainResponsibility']} |"
        for f in files
    )
    header_sections = "\n\n".join(
        f"### `{f['path']}`\n```ts\n/**\n * {f['headerCommentDraft']}\n */\n```"
        for f in files
    )
    jsdoc_rows = "\n".join(
        f"| `{path}` | `{sym['name']}` | {sym['kind']} | {sym['lineRange'][0]} | {sym['reason']} |"
        for path, sym in jsdoc_needed
    )
    no_comment_rows = "\n".join(
        f"| `{item['file']}` | `{item['name']}` | {item['reason']} |"
        for item in no_comment
    )
    utils_files = [f for f in files if "/utils/" in f["path"]]
    ui_files = [f for f in files if "/ui/" in f["path"]]

    return f"""# FRONTEND RUNOCR COMMENT PLAN PRECHECK 20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_RUNOCR_COMMENT_PLAN_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 주석 추가: 없음
- 파일 이동/import 수정/리팩토링/fixture 수정: 없음

## 3. 생성 파일
- `tmp/codex_frontend_runocr_comment_plan_precheck.py`
- `docs/FRONTEND_RUNOCR_COMMENT_PLAN_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_COMMENT_PLAN_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_COMMENT_PLAN_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/runocr/ui/RunOcrResultLayout.tsx`
- `src/components/runocr/ui/OcrResultPanel.tsx`
- `src/components/runocr/ui/OcrDocViewer.tsx`
- `src/components/runocr/ui/CornerAdjust.tsx`
- `src/components/runocr/utils/buildOcrFormData.ts`
- `src/components/runocr/utils/runOcrRequest.ts`
- `src/components/runocr/utils/mapOcrResponse.ts`

## 5. RunOCR 파일별 역할 요약
| path | lines | role | responsibility |
| --- | ---: | --- | --- |
{role_rows}

## 6. 파일 최상단 주석 초안
{header_sections}

## 7. JSDoc 필요 대상
| file | symbol | kind | line | reason |
| --- | --- | --- | ---: | --- |
{jsdoc_rows}

## 8. JSDoc 불필요 대상
아래 대상은 이름과 코드 구조로 의미가 충분하거나, 파일 header와 중복될 가능성이 커서 실제 주석 작업에서 제외하는 편이 좋다.

| file | symbol | reason |
| --- | --- | --- |
{no_comment_rows}

## 9. RunOcrWorkspace 핵심 주석 대상
- `RunOcrWorkspace`: 전체 RunOCR orchestration owner.
- `runOcr`: `runOcrRequest` 호출, `buildRunOcrResult` 변환, autofill 적용, history 저장, result state 반영 순서를 설명.
- `handlePersistEdits`: 수정 결과를 history run에 반영하는 경계.
- `handleResultClose`: 결과 화면 close 시 초기화되는 state 범위.
- `unionSourceBoxes`: field source box를 overlay box로 합치는 좌표 helper.

## 10. utils 파일 주석 대상
{chr(10).join(f"- `{f['path']}`: {f['riskNotes']}" for f in utils_files)}

## 11. ui 파일 주석 대상
{chr(10).join(f"- `{f['path']}`: {f['riskNotes']}" for f in ui_files)}

## 12. 과주석 금지 목록
{chr(10).join(f"- {item}" for item in report['overCommentRules'])}

## 13. 실제 주석 추가 작업 추천 범위
- 추천: {report['recommendedScope']['recommendation']}
- 옵션: `{report['recommendedScope']['option']}`
- 위험도: {report['recommendedScope']['risk']}
- 포함:
{chr(10).join(f"  - {item}" for item in report['recommendedScope']['include'])}
- 보류:
{chr(10).join(f"  - {item}" for item in report['recommendedScope']['defer'])}

## 14. 검증 전략
{chr(10).join(f"- {item}" for item in report['validationPlan'])}

## 15. dirty 상태
이번 precheck에서 dirty 상태는 되돌리지 않았다.

```text
{chr(10).join(report['dirtyStatus'])}
```

## 16. typecheck/build 결과
- `npm run typecheck`: {report['typecheck']['status']} (exit {report['typecheck']['exitCode']})
- `npm run build`: {report['build']['status']} (exit {report['build']['exitCode']})
- known stderr noise: {report['build']['knownStderrNoise'] or '없음'}

## 17. 다음 작업 제안
1. `FRONTEND-STRUCTURE-3B-RUNOCR-DOC-COMMENTS`로 comments-only patch를 진행한다.
2. 8개 파일 header + core JSDoc만 먼저 적용한다.
3. `OcrResultPanel` 내부 helper 전체 주석화는 별도 cycle로 미룬다.
"""


if __name__ == "__main__":
    raise SystemExit(main())
