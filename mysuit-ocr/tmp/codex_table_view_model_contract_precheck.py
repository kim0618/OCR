from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

TASK = "CODEX_FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]

REPORT_MD = ROOT / "docs" / "FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.json"

OCR_RESULT_PANEL = ROOT / "src" / "components" / "upload" / "OcrResultPanel.tsx"
INVOICE_DISPLAY = ROOT / "src" / "lib" / "invoiceTableDisplay.ts"
FORMATTERS = ROOT / "src" / "lib" / "ocrResultFormatters.ts"
CLEAN_JSON = ROOT / "src" / "lib" / "cleanJsonBuilder.ts"
MARKDOWN = ROOT / "src" / "lib" / "markdownReportBuilder.ts"
HISTORY_DETAIL = ROOT / "src" / "components" / "history" / "DetailHistoryView.tsx"
TEST_WORKSPACE = ROOT / "src" / "components" / "test" / "TestWorkspace.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def line_of(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return i
    return None


def count(text: str, needle: str) -> int:
    return sum(1 for line in text.splitlines() if needle in line)


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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def static_inputs() -> dict[str, Any]:
    ocr = read(OCR_RESULT_PANEL)
    inv = read(INVOICE_DISPLAY)
    clean = read(CLEAN_JSON)
    return {
        "structuredInputs": {
            "docTableRows": {
                "line": line_of(ocr, "const docTableRows = useMemo"),
                "shape": "Record<string, unknown>[] from result.document_fields.tableRows; null if missing/empty",
                "usedIn": ["Preview rows", "Custom edit row initialization", "Validation rows", "Clean JSON rows", "Markdown table summary"],
            },
            "docTableMeta": {
                "line": line_of(ocr, "const docTableMeta = useMemo"),
                "shape": "Record<string, unknown> from result.document_fields.tableMeta; null if missing",
                "usedIn": ["buildInvoicePreviewCols", "missingExpectedWarning"],
            },
            "docTableDisplayCols": {
                "line": line_of(ocr, "const docTableDisplayCols = useMemo"),
                "shape": "InvoiceDisplayCol[] = { key: string; labelKo: string }[]",
                "source": "buildInvoicePreviewCols(docTableMeta, docTableRows)",
                "usedIn": ["Preview header/body", "Custom header/body", "Validation header/body", "Clean JSON ordered rows"],
            },
            "customTableEdits": {
                "line": line_of(ocr, "const [customTableEdits"),
                "shape": "Record<string, string>[] | null",
                "usedIn": ["Custom textarea values only"],
            },
            "alignWidth": {
                "widthLine": line_of(ocr, "function _invoiceColWidth"),
                "alignLine": line_of(ocr, "function _invoiceDataAlign"),
                "note": "currently local UI helpers in OcrResultPanel; view model can encode width/align or leave to UI",
            },
            "normalization": {
                "import": "normalizeTableCell as normalizeCell",
                "usageCount": count(ocr, "normalizeCell("),
                "source": "invoiceTableDisplay.normalizeTableCell",
            },
        },
        "policySources": {
            "buildInvoicePreviewCols": "export function buildInvoicePreviewCols" in inv,
            "shouldDisplayRowIndex": "export function shouldDisplayRowIndex" in inv,
            "cleanJsonUsesDocTableDisplayCols": "docTableDisplayCols" in clean and "cleanTableRowsFromObjects" in clean,
            "rowIndexPolicy": "rowIndex is resolved before view model through docTableDisplayCols; tableMeta.columns alone is not sufficient.",
        },
        "locations": {
            "previewStructuredRows": line_of(ocr, "{docTableRows.map((row, ri) => ("),
            "customEditRows": line_of(ocr, "const editRows: Record<string, string>[]"),
            "validationStructuredRows": line_of(ocr, "{docTableRows!.map((row, ri) => ("),
            "missingExpectedWarning": line_of(ocr, "const missingExpectedWarning = useMemo"),
        },
    }


def clean_json_vs_view_model() -> dict[str, Any]:
    return {
        "judgement": "기존 Clean JSON fixture 일부 재사용 가능하지만 table_view_model_v1 fixture 별도 필요",
        "why": [
            "Clean JSON tables.rows is user export payload, not UI render model.",
            "Clean JSON rows are ordered objects keyed by docTableDisplayCols but do not include columns metadata.",
            "Clean JSON does not include cell displayValue/isEmpty/align/width/rowIndex metadata.",
            "Preview/Custom/Validation need rendering metadata and mode-specific decoration decisions.",
            "Clean JSON fixture can still guard ordered row values and rowIndex/column order baseline.",
        ],
        "cleanJsonHas": ["templateName", "info", "tables[].rows ordered by docTableDisplayCols"],
        "viewModelNeeds": ["columns", "rows", "cells", "displayValue", "isEmpty", "align", "width", "row/column indexes", "meta flags"],
        "reuse": {
            "possible": True,
            "scope": "ordered raw values and rowIndex/column key baseline",
            "insufficientFor": ["column labels", "width/align", "empty cell display", "cell metadata", "Custom edit overlay", "Validation decoration"],
        },
    }


def helper_name_candidates() -> list[dict[str, str]]:
    return [
        {
            "name": "buildStructuredTableViewModel",
            "pros": "좁고 명확하다. docTableRows + displayCols 구조화 테이블 전용이라는 현재 1차 범위와 잘 맞는다.",
            "cons": "거래명세서 전용 정책이 숨어 보일 수 있다.",
            "scope": "structured rows only",
            "recommendation": "RECOMMENDED",
        },
        {
            "name": "buildOcrTableViewModel",
            "pros": "향후 범용 OCR table 모델까지 확장하기 좋다.",
            "cons": "현재 단계에는 범위가 넓고 legacy fallback까지 포함해야 할 것처럼 보인다.",
            "scope": "too broad for first helper",
            "recommendation": "NO",
        },
        {
            "name": "buildTableRowsViewModel",
            "pros": "rows 변환 책임을 드러낸다.",
            "cons": "columns/cells/meta까지 담는 output과 이름이 조금 맞지 않는다.",
            "scope": "medium",
            "recommendation": "MAYBE",
        },
        {
            "name": "buildInvoiceStructuredTableViewModel",
            "pros": "거래명세서 rowIndex/column policy와 결합되어 있음을 명확히 한다.",
            "cons": "helper가 displayCols만 받는다면 invoice 전용 이름이 과하게 좁다.",
            "scope": "invoice-specific",
            "recommendation": "MAYBE_LATER",
        },
    ]


def recommended_contract() -> dict[str, Any]:
    input_type = """type BuildStructuredTableViewModelInput = {
  rows: ReadonlyArray<Record<string, unknown>>;
  displayCols: ReadonlyArray<{
    key: string;
    labelKo: string;
  }>;
  emptyValue?: string; // default "-"
};"""
    output_type = """type StructuredTableColumn = {
  key: string;
  label: string;
  index: number;
  align: "left" | "center" | "right";
  width: string;
  isNumeric: boolean;
  isIndex: boolean;
};

type StructuredTableCell = {
  key: string;
  label: string;
  value: string;
  displayValue: string;
  isEmpty: boolean;
  align: "left" | "center" | "right";
  columnIndex: number;
  rowIndex: number;
};

type StructuredTableRow = {
  index: number;
  sourceRow: Record<string, unknown>;
  cells: StructuredTableCell[];
};

type StructuredTableViewModel = {
  columns: StructuredTableColumn[];
  rows: StructuredTableRow[];
  meta: {
    rowCount: number;
    columnCount: number;
    hasRows: boolean;
    hasColumns: boolean;
    hasEmptyCells: boolean;
  };
};"""
    return {
        "recommendedName": "buildStructuredTableViewModel",
        "why": "First helper should be structured table only, not OCR-table universal and not invoice-only by name. rowIndex/column decisions are already embodied in displayCols.",
        "inputType": input_type,
        "outputType": output_type,
        "includeMode": False,
        "modeDecision": "Do not include mode in first helper. Build base table model only; Preview/Custom/Validation should decorate it.",
        "includeTableMeta": False,
        "tableMetaDecision": "Do not pass tableMeta if displayCols is already computed. Recomputing policy here risks rowIndex/column-order drift.",
        "includeCustomEdits": False,
        "customEditDecision": "Keep customTableEdits overlay in Custom caller for first extraction. A later helper can accept editRows if needed.",
        "includeValidationInfo": False,
        "validationDecision": "Validation status/adoption/confidence are row wrapper decorations, not base structured table model.",
        "includeLegacyFallback": False,
        "legacyDecision": "Legacy parseTableField fallback has a different shape. Keep out of first helper; document buildLegacyTableViewModel as separate future candidate.",
        "pureFunction": True,
        "hookNeeded": False,
        "exclude": ["React nodes", "JSX", "event handlers", "textarea callbacks", "validation status UI", "adoption badges", "source/original/debug UI", "OcrResultPanel state"],
    }


def fixture_decision() -> dict[str, Any]:
    return {
        "decision": "Clean JSON fixture + table_view_model_v1 fixture 병행",
        "needNewFixture": True,
        "why": [
            "view model output includes columns/cells/meta not present in Clean JSON.",
            "rowIndex and column order still need direct helper output checks.",
            "Custom/Validation decorations are excluded initially, making view model fixture stable and small.",
        ],
        "targetRoot": "tmp/fixtures/table_view_model_v1/",
        "recommendedCases": ["trade_1", "trade_2", "trade_3", "trade_7"],
        "optionalCases": ["trade_4", "trade_5", "trade_6"],
        "runner": "Node/TS helper direct runner after helper extraction; fixture lock can be generated from current OcrResultPanel-derived inputs before extraction.",
        "notRecommended": "fixture 없이 typecheck/build + existing Clean JSON runner만 사용하는 것은 불충분",
    }


def work_breakdown() -> list[dict[str, str]]:
    return [
        {
            "step": "3D-1 table_view_model_v1 fixture lock",
            "description": "current structured table inputs/output contract 기준 JSON fixture 생성",
            "pros": "helper 추출 전 기준선 확보",
            "cons": "작업이 한 단계 늘어남",
            "recommendation": "DO_FIRST",
        },
        {
            "step": "3D-2 buildStructuredTableViewModel helper extraction",
            "description": "src/lib helper 생성 후 OcrResultPanel에서 structured table rows/cells 모델만 사용",
            "pros": "작고 검증 가능",
            "cons": "JSX 중복은 아직 남음",
            "recommendation": "DO_SECOND",
        },
        {
            "step": "3D-3 view model direct runner",
            "description": "helper를 직접 import해 fixture와 deep equality 비교",
            "pros": "Clean JSON/Markdown runner와 같은 안전망",
            "cons": "runner 작성 필요",
            "recommendation": "DO_WITH_OR_AFTER_3D2",
        },
        {
            "step": "3D-4 OcrResultPanel 적용 확대",
            "description": "Preview/Custom/Validation에서 view model 사용 범위 확대",
            "pros": "중복 감소",
            "cons": "Custom/Validation 회귀 위험",
            "recommendation": "LATER",
        },
    ]


def closeout_timing() -> dict[str, Any]:
    return {
        "doNow": False,
        "recommendation": "3D contract -> fixture -> helper extraction -> direct runner 이후 close-out 생성 권장",
        "reason": "지금 close-out하면 table view model 결과가 빠져 cleanup cycle 판단이 덜 닫힌다.",
        "includeLater": [
            "Clean JSON builder extraction",
            "Markdown builder extraction",
            "ocrResultFormatters extraction",
            "table view model contract/fixture/helper result",
            "deferred common renderer",
            "deferred TestWorkspace cleanup",
            "deferred trade_3 policy",
            "known nextVitals stderr noise",
        ],
    }


def build_report_data(typecheck: dict[str, Any], build: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": TASK,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "noProductionCodeModifiedByThisTask": True,
        "createdFiles": [
            "tmp/codex_table_view_model_contract_precheck.py",
            "docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md",
            "docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.json",
        ],
        "staticInputs": static_inputs(),
        "cleanJsonVsViewModel": clean_json_vs_view_model(),
        "helperNameCandidates": helper_name_candidates(),
        "recommendedContract": recommended_contract(),
        "fixtureDecision": fixture_decision(),
        "workBreakdown": work_breakdown(),
        "closeoutTiming": closeout_timing(),
        "typecheck": typecheck,
        "build": build,
        "knownStderrNoise": {
            "id": "ISSUE-FRONTEND-BUILD-LOG-1",
            "message": "ESLint: nextVitals is not iterable",
            "observed": "nextVitals is not iterable" in (build.get("stderrTail") or ""),
        },
        "repoDirtyStatus": git_status(),
        "overallStatus": "PASS" if typecheck["status"] == "PASS" and build["status"] == "PASS" else "FAIL",
    }


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_reports(data: dict[str, Any]) -> None:
    write_json(REPORT_JSON, data)
    name_rows = "\n".join(
        f"| {cell(x['name'])} | {cell(x['pros'])} | {cell(x['cons'])} | {cell(x['recommendation'])} |"
        for x in data["helperNameCandidates"]
    )
    work_rows = "\n".join(
        f"| {cell(x['step'])} | {cell(x['description'])} | {cell(x['recommendation'])} |"
        for x in data["workBreakdown"]
    )
    contract = data["recommendedContract"]
    md = f"""# FRONTEND CLEANUP 3D0 TABLE VIEW MODEL CONTRACT PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- helper 생성 없음.
- fixture 생성 없음.
- `OcrResultPanel.tsx`, `cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `ocrResultFormatters.ts`, `invoiceTableDisplay.ts`, `TestWorkspace.tsx` 수정 없음.
- 생성 파일은 tmp 분석 스크립트와 docs 리포트뿐이다.

## 3. 현재 Structured Table 입력 분석
- `docTableRows`: `result.document_fields.tableRows`에서 온 `Record<string, unknown>[]`.
- `docTableMeta`: `result.document_fields.tableMeta`.
- `docTableDisplayCols`: `buildInvoicePreviewCols(docTableMeta, docTableRows)` 결과.
- rowIndex/column order/internal key filtering은 helper 입력 전 `docTableDisplayCols`에 반영되어 있다.
- `customTableEdits`는 Custom tab textarea 값 전용이며 base view model에는 넣지 않는 것이 안전하다.
- Validation status/adoption/confidence는 table wrapper decoration이며 base view model 책임이 아니다.

## 4. Clean JSON vs Table View Model
판정: **{data['cleanJsonVsViewModel']['judgement']}**

Clean JSON fixture는 ordered row 값과 rowIndex/column key baseline에는 일부 재사용 가능하다. 하지만 view model은 `columns`, `cells`, `displayValue`, `isEmpty`, `align`, `width`, `meta`가 필요하므로 별도 fixture가 필요하다.

## 5. Helper Name 후보
| name | pros | cons | recommendation |
| --- | --- | --- | --- |
{name_rows}

추천 이름: **{contract['recommendedName']}**

## 6. Input Contract
```ts
{contract['inputType']}
```

결정:
- `tableMeta`는 넣지 않는다. 이미 `displayCols`에 정책이 반영되어 있기 때문이다.
- `mode`는 1차 helper에 넣지 않는다.
- `customTableEdits`는 caller가 overlay한다.
- validation/adoption/confidence decoration은 caller가 처리한다.
- legacy fallback은 포함하지 않는다.

## 7. Output Contract
```ts
{contract['outputType']}
```

출력에 포함하지 않을 것:
{chr(10).join(f"- {x}" for x in contract['exclude'])}

## 8. Mode 포함 여부
- `mode: preview | custom | validation`은 1차 helper에 넣지 않는 것을 추천한다.
- 이유: mode를 넣으면 helper가 탭별 UI 정책을 알게 되어 복잡해진다.
- base view model을 만든 뒤 Preview/Custom/Validation이 decoration을 붙이는 구조가 안전하다.

## 9. Legacy Fallback 포함 여부
- 1차 helper는 structured table 전용으로 둔다.
- `parseTableField(field.value)` fallback은 shape가 다르므로 추후 `buildLegacyTableViewModel` 후보로 분리한다.

## 10. Fixture 필요성 판단
판정: **{data['fixtureDecision']['decision']}**
- 새 fixture 필요: `{data['fixtureDecision']['needNewFixture']}`
- 후보 위치: `{data['fixtureDecision']['targetRoot']}`
- 추천 대상: {', '.join(data['fixtureDecision']['recommendedCases'])}
- runner: {data['fixtureDecision']['runner']}

## 11. 3D 작업 분해안
| step | description | recommendation |
| --- | --- | --- |
{work_rows}

## 12. Close-out 타이밍
- 지금 close-out 생성: `{data['closeoutTiming']['doNow']}`
- 권장: {data['closeoutTiming']['recommendation']}
- 이유: {data['closeoutTiming']['reason']}

## 13. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | ---: | ---: |
| npm run typecheck | {data['typecheck']['status']} | {data['typecheck']['exitCode']} | {data['typecheck']['durationSeconds']} |
| npm run build | {data['build']['status']} | {data['build']['exitCode']} | {data['build']['durationSeconds']} |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` observed = `{data['knownStderrNoise']['observed']}`

## 14. 다음 작업 제안
1. 3D-1에서 `table_view_model_v1` fixture lock을 먼저 만든다.
2. 3D-2에서 `buildStructuredTableViewModel` helper를 추출한다.
3. 3D-3에서 helper direct runner로 fixture deep equality를 검증한다.
4. 3D 완료 후 OcrResultPanel cleanup cycle close-out 문서를 생성한다.
"""
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(md, encoding="utf-8", newline="\n")


def main() -> int:
    print(f"[{TASK}] root={ROOT}", flush=True)
    print("[check] running npm run typecheck", flush=True)
    typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=240)
    print(f"[check] typecheck={typecheck['status']} duration={typecheck['durationSeconds']}s", flush=True)
    print("[check] running npm run build", flush=True)
    build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)
    print(f"[check] build={build['status']} duration={build['durationSeconds']}s", flush=True)
    data = build_report_data(typecheck, build)
    write_reports(data)
    print(f"[write] {REPORT_JSON}", flush=True)
    print(f"[write] {REPORT_MD}", flush=True)
    return 0 if data["overallStatus"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
