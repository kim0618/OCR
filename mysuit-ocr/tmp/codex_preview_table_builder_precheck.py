from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

TASK = "CODEX_FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OCR_ROOT = REPO / "ocr-server"

REPORT_MD = ROOT / "docs" / "FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.json"

OCR_RESULT_PANEL = ROOT / "src" / "components" / "upload" / "OcrResultPanel.tsx"
FORMATTERS = ROOT / "src" / "lib" / "ocrResultFormatters.ts"
INVOICE_DISPLAY = ROOT / "src" / "lib" / "invoiceTableDisplay.ts"
CLEAN_JSON = ROOT / "src" / "lib" / "cleanJsonBuilder.ts"
MARKDOWN = ROOT / "src" / "lib" / "markdownReportBuilder.ts"
HISTORY_DETAIL = ROOT / "src" / "components" / "history" / "DetailHistoryView.tsx"
TEST_WORKSPACE = ROOT / "src" / "components" / "test" / "TestWorkspace.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def line_of(text: str, pattern: str) -> int | None:
    for i, line in enumerate(text.splitlines(), start=1):
        if pattern in line:
            return i
    return None


def find_lines(text: str, pattern: str) -> list[int]:
    return [i for i, line in enumerate(text.splitlines(), start=1) if pattern in line]


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


def extract_static_findings() -> dict[str, Any]:
    ocr = read(OCR_RESULT_PANEL)
    fmt = read(FORMATTERS)
    inv = read(INVOICE_DISPLAY)
    clean = read(CLEAN_JSON)
    md = read(MARKDOWN)
    history = read(HISTORY_DETAIL) if HISTORY_DETAIL.exists() else ""
    test = read(TEST_WORKSPACE) if TEST_WORKSPACE.exists() else ""

    return {
        "files": {
            "OcrResultPanel.tsx": {
                "path": str(OCR_RESULT_PANEL.relative_to(ROOT)),
                "lineCount": len(ocr.splitlines()),
                "imports": {
                    "buildInvoicePreviewCols": bool(re.search(r"buildInvoicePreviewCols", ocr)),
                    "normalizeTableCellAsNormalizeCell": "normalizeTableCell as normalizeCell" in ocr,
                    "parseTableField": bool(re.search(r"parseTableField", ocr)),
                    "buildCleanJsonResult": "buildCleanJsonResult" in ocr,
                    "buildMarkdownReport": "buildMarkdownReport" in ocr,
                },
                "locations": {
                    "filterInvoicePreviewDisplayCols": line_of(ocr, "function filterInvoicePreviewDisplayCols"),
                    "toMarkdown": line_of(ocr, "const toMarkdown"),
                    "docTableRowsUseMemo": line_of(ocr, "const docTableRows = useMemo"),
                    "docTableMetaUseMemo": line_of(ocr, "const docTableMeta = useMemo"),
                    "docTableDisplayColsUseMemo": line_of(ocr, "const docTableDisplayCols = useMemo"),
                    "previewTableFieldsUseMemo": line_of(ocr, "const previewTableFields = useMemo"),
                    "missingExpectedWarningUseMemo": line_of(ocr, "const missingExpectedWarning = useMemo"),
                    "cleanJsonUseMemo": line_of(ocr, "const cleanJson"),
                    "previewMarkdownRender": line_of(ocr, "{toMarkdown()}</Markdown>"),
                    "previewTableMap": line_of(ocr, "{previewTableFields.map"),
                    "customStructuredTableBranch": line_of(ocr, "UI-CUSTOM-1"),
                    "validationStructuredTableBranch": line_of(ocr, "UI-VALIDATION-1"),
                },
                "parseTableFieldCallLines": find_lines(ocr, "parseTableField("),
                "docTableDisplayColsLineCount": len(find_lines(ocr, "docTableDisplayCols")),
                "docTableRowsLineCount": len(find_lines(ocr, "docTableRows")),
            },
            "ocrResultFormatters.ts": {
                "path": str(FORMATTERS.relative_to(ROOT)),
                "exports": {
                    "fieldLabel": "export function fieldLabel" in fmt,
                    "fieldLabelFull": "export function fieldLabelFull" in fmt,
                    "getAdoptionLabel": "export function getAdoptionLabel" in fmt,
                    "parseTableField": "export function parseTableField" in fmt,
                    "isAmountLikeField": "export function isAmountLikeField" in fmt,
                },
                "purityCommentPresent": "No React hooks" in fmt,
            },
            "invoiceTableDisplay.ts": {
                "path": str(INVOICE_DISPLAY.relative_to(ROOT)),
                "exports": {
                    "buildInvoicePreviewCols": "export function buildInvoicePreviewCols" in inv,
                    "shouldDisplayRowIndex": "export function shouldDisplayRowIndex" in inv,
                    "normalizeTableCell": "export function normalizeTableCell" in inv,
                    "hasMeaningfulTableValue": "export function hasMeaningfulTableValue" in inv,
                },
                "rowIndexPolicyIgnoresTableMetaColumnsAlone": "tableMeta.columns" in inv and "shouldDisplayRowIndex" in inv,
            },
            "cleanJsonBuilder.ts": {
                "path": str(CLEAN_JSON.relative_to(ROOT)),
                "usesDocTableRows": "docTableRows" in clean,
                "usesDocTableDisplayCols": "docTableDisplayCols" in clean,
                "hasFallbacks": all(token in clean for token in ["field.tableRows", "field.table_data", "JSON.parse(field.value)"]),
            },
            "markdownReportBuilder.ts": {
                "path": str(MARKDOWN.relative_to(ROOT)),
                "usesParseTableField": "parseTableField" in md,
                "doesNotUseDisplayCols": "docTableDisplayCols" not in md,
            },
            "DetailHistoryView.tsx": {
                "path": str(HISTORY_DETAIL.relative_to(ROOT)),
                "usesBuildInvoicePreviewCols": "buildInvoicePreviewCols" in history,
                "usesTableRows": "tableRows" in history,
            },
            "TestWorkspace.tsx": {
                "path": str(TEST_WORKSPACE.relative_to(ROOT)),
                "usesBuildInvoicePreviewCols": "buildInvoicePreviewCols" in test,
                "usesShouldDisplayRowIndex": "shouldDisplayRowIndex" in test,
            },
        }
    }


def build_report_data(typecheck: dict[str, Any], build: dict[str, Any]) -> dict[str, Any]:
    static = extract_static_findings()
    known_noise = {
        "id": "ISSUE-FRONTEND-BUILD-LOG-1",
        "message": "ESLint: nextVitals is not iterable",
        "observed": "nextVitals is not iterable" in (build.get("stderrTail") or ""),
    }

    preview_contract = {
        "inputs": [
            "editedFields: OcrFieldResult[]",
            "result.document_fields.tableRows -> docTableRows",
            "result.document_fields.tableMeta -> docTableMeta",
            "docTableDisplayCols = buildInvoicePreviewCols(docTableMeta, docTableRows)",
            "parseTableField(field.value) for legacy table field fallback",
        ],
        "previewTableFieldsShape": {
            "idx": "1-based original field index",
            "label": "fieldLabelFull(field)",
            "rows": "ParsedTableField.rows from field.value",
            "nonEmpty": "ParsedTableField.nonEmpty",
            "displayRows": "ParsedTableField.displayRows",
            "isSingleCol": "ParsedTableField.isSingleCol",
            "rowLabel": "ParsedTableField.rowLabel",
        },
        "sourcePriority": [
            "Preview JSX structured branch: document_fields.tableRows + docTableDisplayCols for first table field",
            "Preview JSX fallback branch: parseTableField(field.value).displayRows",
            "Clean JSON additionally supports field.tableRows, field.table_data, JSON.parse(field.value) fallbacks",
        ],
        "columnOrder": [
            "Structured invoice preview uses docTableDisplayCols exactly as returned by buildInvoicePreviewCols",
            "docTableDisplayCols uses tableMeta.expectedColumnKeys, then tableMeta.columns, then INVOICE_TABLE_COL_PRIORITY fallback",
            "Structured preview does not use Object.keys(row) for display order",
            "Legacy fallback displayRows uses cell array order from parseTableField(field.value)",
        ],
        "rowIndex": [
            "Preview does not decide rowIndex directly in previewTableFields",
            "Structured Preview follows docTableDisplayCols",
            "docTableDisplayCols follows shouldDisplayRowIndex: externalExpectedKeys or tableMeta.expectedColumnKeys only",
            "tableMeta.columns or row values alone do not display rowIndex",
        ],
    }

    extraction_layers = [
        {
            "layer": "pure data builder",
            "candidate": "buildPreviewTableFields",
            "extractable": True,
            "scope": "editedFields table filtering + fieldLabelFull + parseTableField + docTableRows non-empty inclusion",
            "inputs": ["fields", "docTableRows"],
            "output": "PreviewTableField[] legacy parsed table descriptors",
            "risk": "LOW-MEDIUM",
            "note": "This is the safest first extraction; it does not touch JSX rendering.",
        },
        {
            "layer": "structured invoice table display data",
            "candidate": "buildStructuredPreviewTableData",
            "extractable": "later",
            "scope": "combine docTableRows + docTableDisplayCols + missingExpectedWarning metadata",
            "inputs": ["docTableRows", "docTableDisplayCols", "missingExpectedWarning"],
            "output": "rows/cols/warning metadata for JSX",
            "risk": "MEDIUM",
            "note": "Useful, but should follow a small PreviewTableFields extraction.",
        },
        {
            "layer": "JSX renderer",
            "candidate": "PreviewInvoiceTable component",
            "extractable": "not in first step",
            "scope": "colgroup, header, body, cell alignment, low-confidence fallback cells",
            "inputs": ["cols", "rows", "align/width helpers"],
            "output": "React nodes",
            "risk": "HIGH",
            "note": "Rendering is heavily coupled to CSS/classes and should be a later component split.",
        },
    ]

    dependency_direction = {
        "recommended": [
            "previewTableBuilder.ts may import ocrResultFormatters.ts",
            "previewTableBuilder.ts may import invoiceTableDisplay.ts only if it computes structured cols; first step can avoid this",
            "cleanJsonBuilder.ts remains Clean JSON output-only",
            "markdownReportBuilder.ts remains Markdown output-only",
            "OcrResultPanel.tsx remains the owner of React state, useMemo, JSX rendering, copy/export UI",
        ],
        "avoid": [
            "previewTableBuilder.ts importing React or OcrResultPanel",
            "previewTableBuilder.ts importing cleanJsonBuilder.ts or markdownReportBuilder.ts",
            "cleanJsonBuilder.ts <-> previewTableBuilder.ts circular dependency",
            "TestWorkspace.tsx included in this extraction scope",
        ],
    }

    fixture_strategy = {
        "needPreviewTableDataFixtures": True,
        "recommendation": "Create tmp/fixtures/preview_table_v1 in a later step before extraction if the helper goes beyond previewTableFields filtering.",
        "cases": [
            "invoice_statement trade_1~trade_7 for structured docTableRows/rowIndex/column order",
            "synthetic legacy table field without document_fields.tableRows for parseTableField fallback",
        ],
        "reuseCleanJsonFixtures": "Useful for API case coverage, but not sufficient because Preview fallback displayRows and JSX table descriptors are not Clean JSON output.",
        "receiptFieldOnly": "Not necessary for Preview table fixture because there is no table field path.",
    }

    risks = [
        {"risk": "Preview JSX and data builder are coupled", "likelihood": "MEDIUM", "impact": "MEDIUM", "mitigation": "First extract only previewTableFields pure data list; leave JSX in component.", "needsFixture": True},
        {"risk": "legacy table_data / field.value fallback omitted", "likelihood": "MEDIUM", "impact": "HIGH", "mitigation": "Add synthetic legacy fallback fixture before broad extraction.", "needsFixture": True},
        {"risk": "rowIndex policy regression", "likelihood": "LOW", "impact": "HIGH", "mitigation": "Keep rowIndex in buildInvoicePreviewCols; preview builder should consume cols, not recalculate policy.", "needsFixture": True},
        {"risk": "docTableDisplayCols not passed to structured renderer", "likelihood": "MEDIUM", "impact": "HIGH", "mitigation": "Contract explicitly requires cols from OcrResultPanel useMemo.", "needsFixture": True},
        {"risk": "Clean JSON and Preview column order diverge", "likelihood": "LOW-MEDIUM", "impact": "HIGH", "mitigation": "Both must continue using same docTableDisplayCols.", "needsFixture": True},
        {"risk": "Custom/Validation behavior changes accidentally", "likelihood": "MEDIUM", "impact": "MEDIUM", "mitigation": "Do not move shared parseTableField or structured JSX branches in first extraction.", "needsFixture": False},
        {"risk": "History/TestWorkspace policy divergence", "likelihood": "LOW", "impact": "MEDIUM", "mitigation": "Reference only in this stage; do not include in extraction scope.", "needsFixture": False},
    ]

    return {
        "task": TASK,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "noProductionCodeModifiedByThisTask": True,
        "createdFiles": [
            "tmp/codex_preview_table_builder_precheck.py",
            "docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md",
            "docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.json",
        ],
        "staticFindings": static,
        "previewTableContract": preview_contract,
        "extractionLayers": extraction_layers,
        "dependencyDirection": dependency_direction,
        "fixtureStrategy": fixture_strategy,
        "risks": risks,
        "typecheck": typecheck,
        "build": build,
        "knownStderrNoise": known_noise,
        "repoDirtyStatus": git_status(),
        "overallStatus": "PASS" if typecheck["status"] == "PASS" and build["status"] == "PASS" else "FAIL",
    }


def esc_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_reports(data: dict[str, Any]) -> None:
    write_json(REPORT_JSON, data)
    loc = data["staticFindings"]["files"]["OcrResultPanel.tsx"]["locations"]
    loc_rows = "\n".join(f"| {k} | {v} |" for k, v in loc.items())
    layer_rows = "\n".join(
        f"| {esc_cell(x['layer'])} | {esc_cell(x['candidate'])} | {esc_cell(x['extractable'])} | {esc_cell(x['risk'])} | {esc_cell(x['note'])} |"
        for x in data["extractionLayers"]
    )
    risk_rows = "\n".join(
        f"| {esc_cell(x['risk'])} | {x['likelihood']} | {x['impact']} | {esc_cell(x['mitigation'])} | {x['needsFixture']} |"
        for x in data["risks"]
    )
    md = f"""# FRONTEND CLEANUP 3A PREVIEW TABLE BUILDER PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `OcrResultPanel.tsx`, `cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `ocrResultFormatters.ts`, `TestWorkspace.tsx` 수정 없음.
- Preview table builder/helper 추출 없음.
- 생성 파일은 tmp 분석 스크립트와 docs 리포트뿐이다.

## 3. Preview Table 관련 코드 위치
| item | line |
| --- | ---: |
{loc_rows}

## 4. Preview Table Flow 요약
1. `docTableRows`는 `result.document_fields.tableRows`에서 추출한다.
2. `docTableMeta`는 `result.document_fields.tableMeta`에서 추출한다.
3. `docTableDisplayCols`는 `buildInvoicePreviewCols(docTableMeta, docTableRows)` 결과를 사용한다.
4. `previewTableFields`는 `editedFields` 중 `field_type === "table"`만 골라 `fieldLabelFull`과 `parseTableField(field.value)`를 붙인 list다.
5. Preview JSX는 첫 table field에서 `docTableRows + docTableDisplayCols`가 있으면 구조화 거래명세서 표를 렌더링한다.
6. 구조화 rows가 없으면 `parseTableField(field.value).displayRows` fallback을 렌더링한다.

## 5. Current Contract
- 입력: `editedFields`, `docTableRows`, `docTableMeta`, `docTableDisplayCols`, `parseTableField(field.value)`.
- `previewTableFields` 출력 shape: `idx`, `label`, `rows`, `nonEmpty`, `displayRows`, `isSingleCol`, `rowLabel`.
- 구조화 거래명세서 column order는 `docTableDisplayCols`를 그대로 따른다.
- legacy fallback은 `field.value` JSON cell array 순서를 따른다.
- Preview rowIndex 판단은 `previewTableFields`가 직접 하지 않고 `buildInvoicePreviewCols`/`shouldDisplayRowIndex` 결과를 따른다.

## 6. 추출 가능 범위
| layer | candidate | extractable | risk | note |
| --- | --- | --- | --- | --- |
{layer_rows}

## 7. 의존 방향
권장:
{chr(10).join(f"- {item}" for item in data['dependencyDirection']['recommended'])}

피해야 할 방향:
{chr(10).join(f"- {item}" for item in data['dependencyDirection']['avoid'])}

## 8. Fixture / Check 전략
- Preview table data helper가 `previewTableFields` 수준을 넘어서면 `tmp/fixtures/preview_table_v1` 별도 fixture를 먼저 만드는 것을 권장한다.
- 거래명세서 `trade_1~trade_7`은 구조화 tableRows/column order/rowIndex 검증에 적합하다.
- `field.value` fallback과 `table_data` legacy 경로는 별도 synthetic fixture가 필요하다.
- Clean JSON fixture는 API 케이스 커버리지에는 도움이 되지만 Preview fallback displayRows까지 보장하지는 못한다.

## 9. 위험도 평가
| risk | likelihood | impact | mitigation | fixture/check |
| --- | --- | --- | --- | --- |
{risk_rows}

## 10. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | ---: | ---: |
| npm run typecheck | {data['typecheck']['status']} | {data['typecheck']['exitCode']} | {data['typecheck']['durationSeconds']} |
| npm run build | {data['build']['status']} | {data['build']['exitCode']} | {data['build']['durationSeconds']} |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` observed = `{data['knownStderrNoise']['observed']}`

## 11. 다음 작업 제안
1. FRONTEND-CLEANUP-3B는 `buildPreviewTableFields` 수준의 순수 데이터 helper만 추출한다.
2. JSX renderer와 Custom/Validation 구조화 table branch는 건드리지 않는다.
3. 더 넓은 추출 전에는 Preview table v1 fixture를 별도 생성한다.
4. TestWorkspace 정리는 이번 라인에 포함하지 않고 별도 사용자 확인 후 진행한다.
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
