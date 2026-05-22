from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

TASK = "CODEX_FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]

REPORT_MD = ROOT / "docs" / "FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.json"

OCR_RESULT_PANEL = ROOT / "src" / "components" / "upload" / "OcrResultPanel.tsx"
FORMATTERS = ROOT / "src" / "lib" / "ocrResultFormatters.ts"
INVOICE_DISPLAY = ROOT / "src" / "lib" / "invoiceTableDisplay.ts"
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


def find_lines(text: str, needle: str) -> list[int]:
    return [i for i, line in enumerate(text.splitlines(), start=1) if needle in line]


def snippet_range(text: str, start_needle: str, end_needle: str | None = None, window: int = 80) -> dict[str, int | None]:
    start = line_of(text, start_needle)
    if start is None:
        return {"start": None, "end": None}
    if end_needle:
        end = None
        for i, line in enumerate(text.splitlines()[start:], start=start + 1):
            if end_needle in line:
                end = i
                break
        return {"start": start, "end": end or start + window}
    return {"start": start, "end": start + window}


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


def static_locations() -> dict[str, Any]:
    ocr = read(OCR_RESULT_PANEL)
    fmt = read(FORMATTERS)
    inv = read(INVOICE_DISPLAY)
    clean = read(CLEAN_JSON)
    md = read(MARKDOWN)
    history = read(HISTORY_DETAIL) if HISTORY_DETAIL.exists() else ""
    test = read(TEST_WORKSPACE) if TEST_WORKSPACE.exists() else ""
    return {
        "OcrResultPanel.tsx": {
            "path": str(OCR_RESULT_PANEL.relative_to(ROOT)),
            "lineCount": len(ocr.splitlines()),
            "locations": {
                "docTableRows": line_of(ocr, "const docTableRows = useMemo"),
                "docTableMeta": line_of(ocr, "const docTableMeta = useMemo"),
                "docTableDisplayCols": line_of(ocr, "const docTableDisplayCols = useMemo"),
                "previewTableFields": line_of(ocr, "const previewTableFields = useMemo"),
                "previewRenderer": line_of(ocr, "{previewTableFields.map"),
                "customStructuredBranch": line_of(ocr, "UI-CUSTOM-1"),
                "customFallbackBranch": line_of(ocr, "fallback: raw parseTableField"),
                "validationStructuredBranch": line_of(ocr, "UI-VALIDATION-1"),
                "missingExpectedWarning": line_of(ocr, "const missingExpectedWarning = useMemo"),
                "customTableEditsState": line_of(ocr, "const [customTableEdits"),
            },
            "ranges": {
                "previewRenderer": snippet_range(ocr, "{previewTableFields.map", "{rawOcrFields.length > 0", 120),
                "customTableBranch": snippet_range(ocr, "UI-CUSTOM-1", ") : (", 150),
                "validationTableBranch": snippet_range(ocr, "UI-VALIDATION-1", "return (", 130),
            },
            "usageCounts": {
                "docTableRows": len(find_lines(ocr, "docTableRows")),
                "docTableDisplayCols": len(find_lines(ocr, "docTableDisplayCols")),
                "parseTableField": len(find_lines(ocr, "parseTableField(")),
                "normalizeCell": len(find_lines(ocr, "normalizeCell(")),
                "getAdoptionLabel": len(find_lines(ocr, "getAdoptionLabel(")),
                "fieldLabelFull": len(find_lines(ocr, "fieldLabelFull(")),
                "orTableResult": len(find_lines(ocr, "or-table-result")),
            },
        },
        "ocrResultFormatters.ts": {
            "path": str(FORMATTERS.relative_to(ROOT)),
            "exports": {
                "parseTableField": "export function parseTableField" in fmt,
                "fieldLabel": "export function fieldLabel" in fmt,
                "fieldLabelFull": "export function fieldLabelFull" in fmt,
                "getAdoptionLabel": "export function getAdoptionLabel" in fmt,
            },
        },
        "invoiceTableDisplay.ts": {
            "path": str(INVOICE_DISPLAY.relative_to(ROOT)),
            "exports": {
                "buildInvoicePreviewCols": "export function buildInvoicePreviewCols" in inv,
                "shouldDisplayRowIndex": "export function shouldDisplayRowIndex" in inv,
                "normalizeTableCell": "export function normalizeTableCell" in inv,
            },
        },
        "cleanJsonBuilder.ts": {
            "path": str(CLEAN_JSON.relative_to(ROOT)),
            "usesDocTableDisplayCols": "docTableDisplayCols" in clean,
            "fallbackMentions": [token for token in ["field.tableRows", "field.table_data", "JSON.parse(field.value)"] if token in clean],
        },
        "markdownReportBuilder.ts": {
            "path": str(MARKDOWN.relative_to(ROOT)),
            "usesParseTableField": "parseTableField" in md,
            "doesNotRenderStructuredRows": "docTableDisplayCols" not in md,
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
            "note": "reference only; out of scope for this extraction",
        },
    }


def data_flows() -> dict[str, Any]:
    return {
        "Preview": {
            "source": "editedFields table fields + document_fields.tableRows/tableMeta",
            "structuredCondition": "tableIdx === 0 && docTableRows && docTableDisplayCols",
            "legacyFallback": "parseTableField(field.value).displayRows",
            "columns": "docTableDisplayCols from buildInvoicePreviewCols",
            "rowIndex": "via docTableDisplayCols only",
            "cellValue": "normalizeCell(row[col.key]) || '-'",
            "emptyCell": "'-'",
            "editing": "read-only",
            "meta": "row count and missingExpectedWarning badge",
        },
        "Custom": {
            "source": "edited field item + docTableRows/docTableDisplayCols + customTableEdits",
            "structuredCondition": "docTableRows && docTableDisplayCols.length > 0",
            "legacyFallback": "parseTableField(field.value); firstRowPreview; displayRows",
            "columns": "docTableDisplayCols",
            "rowIndex": "via docTableDisplayCols only",
            "cellValue": "textarea value from customTableEdits or normalized docTableRows",
            "emptyCell": "empty string in textarea",
            "editing": "editable textarea, setCustomTableEdits, onFocus/onBlur",
            "meta": "adoption label, warning badge, row count",
        },
        "Validation": {
            "source": "validation section rows + item.field + docTableRows/docTableDisplayCols",
            "structuredCondition": "docTableRows && docTableDisplayCols.length > 0",
            "legacyFallback": "rowLabel uses parseTableField(field.value); no legacy table body rendering in snippet",
            "columns": "docTableDisplayCols",
            "rowIndex": "via docTableDisplayCols only",
            "cellValue": "normalizeCell(row[col.key]) || '-'",
            "emptyCell": "'-' or empty table message",
            "editing": "read-only, clickable validation row",
            "meta": "validation status dot/classes, confidence, adoption, missingExpectedWarning",
        },
    }


def difference_matrix() -> list[dict[str, Any]]:
    rows = [
        ("data source", "previewTableFields + docTableRows", "field + docTableRows + customTableEdits", "validation item.field + docTableRows", False, True, "MEDIUM", "same tableRows policy, but Custom/Validation wrap different item state"),
        ("structured table", "first preview table only", "field_type table branch", "validation table item branch", False, True, "MEDIUM", "conditions are similar but mounted in different UI contexts"),
        ("legacy fallback", "renders displayRows body", "renders displayRows body + firstRowPreview", "rowLabel fallback only, no comparable body branch observed", False, False, "HIGH", "fallback behavior differs enough to avoid one renderer now"),
        ("docTableRows", "yes", "yes", "yes", True, True, "LOW", "shared source"),
        ("docTableDisplayCols", "yes", "yes", "yes", True, True, "LOW", "shared column source"),
        ("column order", "docTableDisplayCols", "docTableDisplayCols", "docTableDisplayCols", True, True, "LOW", "same for structured rows"),
        ("rowIndex policy", "docTableDisplayCols/shouldDisplayRowIndex", "docTableDisplayCols/shouldDisplayRowIndex", "docTableDisplayCols/shouldDisplayRowIndex", True, True, "LOW", "do not recalculate in renderer"),
        ("internal key filtering", "already in buildInvoicePreviewCols", "already in buildInvoicePreviewCols", "already in buildInvoicePreviewCols", True, True, "LOW", "structured path aligned"),
        ("cell normalization", "normalizeCell + '-'", "normalizeCell into editRows, textarea empty string", "normalizeCell + '-'", False, True, "MEDIUM", "Custom edit model differs"),
        ("empty cell", "'-'", "empty string in textarea", "'-'", False, True, "MEDIUM", "prop can absorb but UX differs"),
        ("header rendering", "labelKo + key subtitle", "labelKo + key subtitle, title differs", "labelKo + key subtitle inside validation block", False, True, "MEDIUM", "mostly same markup but containers differ"),
        ("alignment/width", "_invoiceColWidth/_invoiceDataAlign", "same + textarea padding 0", "same + validation margins", False, True, "MEDIUM", "can share view model, renderer props may grow"),
        ("editable", "no", "yes textarea/onChange/onBlur", "no", False, True, "HIGH", "major reason against immediate common renderer"),
        ("validation/GT status", "none", "none", "status dot/classes/confidence section", False, False, "HIGH", "Validation wrapper is specialized"),
        ("source/adoption/confidence", "not per table cell; warning badge", "adoption label in meta", "adoption + confidence + status", False, True, "MEDIUM", "mode-specific meta"),
        ("row label/summary", "row count next to title", "row count and firstRowPreview fallback", "rowLabel in validation value line", False, True, "MEDIUM", "view model can supply labels"),
        ("table field summary", "Markdown summary plus JSX table", "field value meta", "validation value line", False, True, "MEDIUM", "containers differ"),
        ("trade_3 locked behavior", "through docTableDisplayCols; warning badge possible", "same cols/edit rows", "same cols in validation table", True, True, "MEDIUM", "fixture must guard insuranceCode/amount behavior"),
    ]
    return [
        {
            "axis": axis,
            "Preview": preview,
            "Custom": custom,
            "Validation": validation,
            "same": same,
            "canAbsorbWithProps": props,
            "risk": risk,
            "notes": notes,
        }
        for axis, preview, custom, validation, same, props, risk, notes in rows
    ]


def abc_decision(matrix: list[dict[str, Any]]) -> dict[str, Any]:
    different = [row for row in matrix if not row["same"]]
    high = [row for row in matrix if row["risk"] == "HIGH"]
    return {
        "decision": "B",
        "label": "view model / pure helper only",
        "whyNotA": [
            f"difference axes are {len(different)}, more than the A threshold",
            f"HIGH-risk axes exist: {', '.join(row['axis'] for row in high)}",
            "Custom textarea editing and Validation status wrapper would make a common renderer prop-heavy",
        ],
        "whyNotC": [
            "structured table data policy is shared through docTableRows/docTableDisplayCols",
            "rowIndex and column order are already centralized in buildInvoicePreviewCols",
            "a pure view model can be fixture-tested without touching JSX",
        ],
        "recommendedNext": "Do not extract a common React renderer first. If continuing, extract a pure table view-model helper after creating preview/custom/validation view-model fixtures.",
    }


def b_option() -> dict[str, Any]:
    return {
        "pureHelperPreferred": True,
        "hookNeeded": False,
        "candidateFiles": ["src/lib/ocrTableViewModel.ts", "src/lib/structuredTableViewModel.ts"],
        "candidateHelpers": ["buildStructuredTableViewModel", "buildLegacyTableViewModel", "buildOcrTableViewModel"],
        "inputTypeDraft": {
            "rows": "Record<string, unknown>[] | null",
            "displayCols": "{ key: string; labelKo: string }[] | null",
            "mode": "preview | custom | validation",
            "editRows": "Record<string, string>[] | null for custom only",
            "warnings": "missingExpectedWarning or warning flags",
        },
        "outputTypeDraft": {
            "columns": "key/label/width/align",
            "rows": "row index + cells",
            "cells": "key/value/displayValue/align/empty/editable flags",
            "flags": "hasStructured/hasLegacy/empty",
            "modeMetadata": "rowLabel, warning badge, validation/adoption/confidence metadata as needed",
        },
        "reactDependency": "No React dependency required for view model. JSX stays in OcrResultPanel or later components.",
    }


def fixture_strategy() -> dict[str, Any]:
    return {
        "recommendation": "For B, create view-model JSON fixtures before extraction. Avoid DOM snapshot until/if common renderer extraction is attempted.",
        "fixtureRootCandidate": "tmp/fixtures/table_view_model_v1/",
        "cases": [
            "invoice_statement trade_1~trade_7 structured docTableRows",
            "trade_3 to lock insuranceCode/amount behavior",
            "synthetic legacy parseTableField fallback without document_fields.tableRows",
            "optional custom editRows fixture for textarea value behavior",
        ],
        "checkRunnerCandidate": "tmp/check_table_view_model_v1_fixtures_js.mjs or tsx",
        "beforeAfter": "deep equality for view model JSON, plus existing Clean JSON and Markdown fixture runners",
        "ifAChosenLater": "Use Playwright/screenshot or DOM snapshot only after view model fixture is stable.",
    }


def risks() -> list[dict[str, Any]]:
    return [
        {"risk": "rowIndex policy regression", "likelihood": "LOW", "impact": "HIGH", "mitigation": "Do not compute rowIndex in renderer; consume docTableDisplayCols only.", "needsFixture": True},
        {"risk": "trade_3 insuranceCode/amount locked behavior changes", "likelihood": "MEDIUM", "impact": "HIGH", "mitigation": "Include trade_3 view model fixture and Clean JSON runner.", "needsFixture": True},
        {"risk": "Preview/Clean JSON column order divergence", "likelihood": "LOW", "impact": "HIGH", "mitigation": "Keep shared docTableDisplayCols source.", "needsFixture": True},
        {"risk": "Custom textarea edit behavior breaks", "likelihood": "MEDIUM", "impact": "HIGH", "mitigation": "Leave Custom JSX in place; model editRows separately.", "needsFixture": True},
        {"risk": "Validation status/GT wrapper breaks", "likelihood": "MEDIUM", "impact": "HIGH", "mitigation": "Do not merge Validation renderer in first pass.", "needsFixture": True},
        {"risk": "adoption/confidence/source display omitted", "likelihood": "MEDIUM", "impact": "MEDIUM", "mitigation": "Keep metadata outside core table renderer or model explicitly.", "needsFixture": True},
        {"risk": "legacy fallback omitted", "likelihood": "MEDIUM", "impact": "HIGH", "mitigation": "Create synthetic fallback fixture before extraction.", "needsFixture": True},
        {"risk": "props explosion in common renderer", "likelihood": "HIGH", "impact": "MEDIUM", "mitigation": "Choose B, not A, for next step.", "needsFixture": False},
        {"risk": "circular dependency", "likelihood": "LOW", "impact": "HIGH", "mitigation": "View model may import invoiceTableDisplay/formatters only; not Clean JSON/Markdown.", "needsFixture": False},
        {"risk": "TestWorkspace policy divergence", "likelihood": "LOW", "impact": "MEDIUM", "mitigation": "Reference only; handle in separate approved task.", "needsFixture": False},
    ]


def closeout_plan() -> dict[str, Any]:
    return {
        "needed": True,
        "createNow": False,
        "candidateFiles": [
            "docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md",
            "docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json",
        ],
        "include": [
            "Clean JSON builder extraction and fixture runners",
            "Markdown builder extraction and fixture runners",
            "ocrResultFormatters extraction",
            "3A/3C table precheck conclusion",
            "deferred renderer/view-model work",
            "deferred trade_3 policy, TestWorkspace cleanup, nextVitals stderr noise",
        ],
        "reopenTriggers": [
            "table view-model fixtures created",
            "trade_3 insuranceCode/amount policy decided",
            "TestWorkspace cleanup scope approved",
            "Clean JSON v2 info/tables work starts",
        ],
    }


def build_report_data(typecheck: dict[str, Any], build: dict[str, Any]) -> dict[str, Any]:
    matrix = difference_matrix()
    return {
        "task": TASK,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "noProductionCodeModifiedByThisTask": True,
        "createdFiles": [
            "tmp/codex_table_renderer_precheck.py",
            "docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md",
            "docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.json",
        ],
        "staticLocations": static_locations(),
        "dataFlows": data_flows(),
        "differenceMatrix": matrix,
        "abcDecision": abc_decision(matrix),
        "bOption": b_option(),
        "commonRendererPossibility": {
            "recommendedNow": False,
            "reason": "Too many mode-specific differences; common renderer props would become complex before fixtures exist.",
            "possibleLaterAfter": ["view model fixture lock", "mode metadata contract", "optional DOM/Playwright checks"],
        },
        "fixtureStrategy": fixture_strategy(),
        "risks": risks(),
        "closeoutPlan": closeout_plan(),
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
    loc = data["staticLocations"]["OcrResultPanel.tsx"]["locations"]
    loc_rows = "\n".join(f"| {k} | {v} |" for k, v in loc.items())
    matrix_rows = "\n".join(
        f"| {cell(r['axis'])} | {cell(r['Preview'])} | {cell(r['Custom'])} | {cell(r['Validation'])} | {r['same']} | {r['canAbsorbWithProps']} | {r['risk']} |"
        for r in data["differenceMatrix"]
    )
    risk_rows = "\n".join(
        f"| {cell(r['risk'])} | {r['likelihood']} | {r['impact']} | {cell(r['mitigation'])} | {r['needsFixture']} |"
        for r in data["risks"]
    )
    md = f"""# FRONTEND CLEANUP 3C TABLE RENDERER PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `OcrResultPanel.tsx`, `cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `ocrResultFormatters.ts`, `invoiceTableDisplay.ts`, `TestWorkspace.tsx` 수정 없음.
- Preview/Custom/Validation table renderer 또는 view model helper 추출 없음.
- 생성 파일은 tmp 분석 스크립트와 docs 리포트뿐이다.

## 3. Table Code Locations
| item | line |
| --- | ---: |
{loc_rows}

## 4. Data Flow 요약
- Preview: `previewTableFields`와 `docTableRows/docTableDisplayCols`를 사용한다. 구조화 table은 read-only, fallback은 `parseTableField(field.value).displayRows`를 렌더링한다.
- Custom: `docTableRows/docTableDisplayCols`와 `customTableEdits`를 사용한다. 구조화 table은 textarea editable이며 fallback은 raw `parseTableField` 표다.
- Validation: validation section item 안에서 `docTableRows/docTableDisplayCols`를 사용한다. 상태 dot/classes, confidence, adoption이 붙고 legacy fallback은 rowLabel 중심이다.
- 세 탭 모두 구조화 column order와 rowIndex는 `docTableDisplayCols`를 따르며, 직접 재계산하지 않아야 한다.

## 5. Difference Matrix
| axis | Preview | Custom | Validation | same | props? | risk |
| --- | --- | --- | --- | --- | --- | --- |
{matrix_rows}

## 6. A/B/C 추천
- 최종 추천: **B. view model / pure helper만 추출**
- A가 아닌 이유:
{chr(10).join(f"  - {x}" for x in data['abcDecision']['whyNotA'])}
- C가 아닌 이유:
{chr(10).join(f"  - {x}" for x in data['abcDecision']['whyNotC'])}

## 7. B 옵션 구체화
- pure helper 우선: `{data['bOption']['pureHelperPreferred']}`
- hook 필요 여부: `{data['bOption']['hookNeeded']}`
- 후보 파일: `{', '.join(data['bOption']['candidateFiles'])}`
- 후보 helper: `{', '.join(data['bOption']['candidateHelpers'])}`
- React 의존: {data['bOption']['reactDependency']}

## 8. 공통 Renderer 가능성
- 지금 당장 공통 React renderer 추출은 권장하지 않는다.
- 이유: Custom editable textarea, Validation status wrapper, legacy fallback 차이 때문에 props가 과하게 늘어날 가능성이 높다.
- 추후 view model fixture가 안정화된 뒤 DOM/Playwright 검증까지 붙이면 재검토 가능하다.

## 9. Fixture / Check 전략
- 권장 fixture root: `{data['fixtureStrategy']['fixtureRootCandidate']}`
- 권장 runner: `{data['fixtureStrategy']['checkRunnerCandidate']}`
- before/after: {data['fixtureStrategy']['beforeAfter']}
- 대상:
{chr(10).join(f"  - {x}" for x in data['fixtureStrategy']['cases'])}

## 10. 위험도 평가
| risk | likelihood | impact | mitigation | fixture/check |
| --- | --- | --- | --- | --- |
{risk_rows}

## 11. OcrResultPanel Cleanup Cycle Close-out
- close-out 필요: `{data['closeoutPlan']['needed']}`
- 이번 작업에서 생성: `{data['closeoutPlan']['createNow']}`
- 다음 close-out 후보 파일:
{chr(10).join(f"  - `{x}`" for x in data['closeoutPlan']['candidateFiles'])}

## 12. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | ---: | ---: |
| npm run typecheck | {data['typecheck']['status']} | {data['typecheck']['exitCode']} | {data['typecheck']['durationSeconds']} |
| npm run build | {data['build']['status']} | {data['build']['exitCode']} | {data['build']['durationSeconds']} |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` observed = `{data['knownStderrNoise']['observed']}`

## 13. 다음 작업 제안
1. 바로 renderer를 추출하지 말고 table view-model fixture lock 작업을 먼저 수행한다.
2. 이후 `buildStructuredTableViewModel` 같은 pure helper를 작게 추출한다.
3. 공통 React renderer는 view model 검증이 안정화된 뒤 별도 판단한다.
4. OcrResultPanel cleanup cycle 1 close-out 문서를 생성해 완료/보류/재개 조건을 정리한다.
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
