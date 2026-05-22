from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

TASK = "CODEX_FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]

REPORT_MD = ROOT / "docs" / "FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.json"

OCR_RESULT_PANEL = ROOT / "src" / "components" / "upload" / "OcrResultPanel.tsx"
INVOICE_DISPLAY = ROOT / "src" / "lib" / "invoiceTableDisplay.ts"
CLEAN_JSON = ROOT / "src" / "lib" / "cleanJsonBuilder.ts"
DOC_3C = ROOT / "docs" / "FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md"
DOC_3D0 = ROOT / "docs" / "FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md"


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


def source_facts() -> dict[str, Any]:
    ocr = read(OCR_RESULT_PANEL)
    inv = read(INVOICE_DISPLAY)
    clean = read(CLEAN_JSON)
    doc_3c = read(DOC_3C) if DOC_3C.exists() else ""
    doc_3d0 = read(DOC_3D0) if DOC_3D0.exists() else ""
    return {
        "locations": {
            "_IDX_KEYS": line_of(ocr, "const _IDX_KEYS"),
            "_NUM_KEYS": line_of(ocr, "const _NUM_KEYS"),
            "_invoiceColWidth": line_of(ocr, "function _invoiceColWidth"),
            "_invoiceDataAlign": line_of(ocr, "function _invoiceDataAlign"),
            "customTableEdits": line_of(ocr, "const [customTableEdits"),
            "customEditRows": line_of(ocr, "const editRows: Record<string, string>[]"),
            "customSetByRowAndColumn": line_of(ocr, "return base.map((r, idx) => idx === ri ?"),
            "previewNormalizeCell": line_of(ocr, "{normalizeCell(row[col.key]) ||"),
            "validationNormalizeCell": line_of(ocr, "{normalizeCell(row[col.key]) ||"),
        },
        "usageCounts": {
            "_invoiceColWidth": count(ocr, "_invoiceColWidth("),
            "_invoiceDataAlign": count(ocr, "_invoiceDataAlign("),
            "_NUM_KEYS": count(ocr, "_NUM_KEYS"),
            "_IDX_KEYS": count(ocr, "_IDX_KEYS"),
            "normalizeCell": count(ocr, "normalizeCell("),
            "sourceRowLiteral": count(ocr, "sourceRow"),
            "hasEmptyCellsLiteral": count(ocr, "hasEmptyCells"),
        },
        "policySources": {
            "buildInvoicePreviewCols": "export function buildInvoicePreviewCols" in inv,
            "normalizeTableCell": "export function normalizeTableCell" in inv,
            "cleanJsonOrderedRows": "cleanTableRowsFromObjects" in clean and "docTableDisplayCols" in clean,
            "doc3cExists": DOC_3C.exists(),
            "doc3d0Exists": DOC_3D0.exists(),
            "doc3d0HadWideContract": "hasEmptyCells" in doc_3d0 and "sourceRow" in doc_3d0 and "align" in doc_3d0,
            "doc3cSaidAlignWidthDiffers": "alignment/width" in doc_3c,
        },
    }


def trim_table() -> list[dict[str, Any]]:
    def row(field: str, derive: str, common: bool, display: bool, custom: str, validation: str, array: bool, duplicate: str, fixture: bool, rec: str, reason: str) -> dict[str, Any]:
        return {
            "field": field,
            "deriveFrom": derive,
            "commonData": common,
            "displayPolicy": display,
            "customNeed": custom,
            "validationNeed": validation,
            "deriveFromArrayPosition": array,
            "duplicate": duplicate,
            "fixtureValue": fixture,
            "recommendation": rec,
            "reason": reason,
        }
    return [
        row("columns.key", "displayCols[].key", True, False, "yes", "yes", False, "no", True, "include", "primary column identity and rowIndex/column-order baseline"),
        row("columns.label", "displayCols[].labelKo", True, False, "yes", "yes", False, "no", True, "include", "header label needed by all structured table branches"),
        row("columns.index", "columns array index", False, False, "no", "no", True, "yes", False, "exclude", "derivable and brittle in fixture"),
        row("columns.align", "_invoiceDataAlign(col.key)", False, True, "textarea style only", "style only", True, "display policy", False, "exclude", "renderer/style policy; can be added by later display policy helper"),
        row("columns.width", "_invoiceColWidth(col.key)", False, True, "colgroup style", "colgroup style", True, "display policy", False, "exclude", "style policy likely to change independently"),
        row("columns.isNumeric", "_NUM_KEYS.has(key)", False, True, "nowrap/style", "nowrap/style", True, "display policy", False, "exclude", "classification only supports style, not core data"),
        row("columns.isIndex", "_IDX_KEYS.has(key)", False, True, "nowrap/style", "nowrap/style", True, "display policy", False, "exclude", "avoid confusion with actual rowIndex data column"),
        row("rows.rowIndex", "rows array index", False, False, "row index available in map", "row index available in map", True, "confusing with rowIndex column", False, "exclude", "derive from array position and avoid naming collision"),
        row("rows.sourceRow", "input rows[n]", False, False, "not needed; editRows uses row index + key", "not needed", False, "large duplicate", False, "exclude", "would bloat fixtures and duplicate raw OCR values"),
        row("cells.key", "column key", True, False, "yes", "yes", False, "no", True, "include", "cell identity for edit overlay and assertions"),
        row("cells.label", "columns.label by key/index", False, False, "no", "no", False, "duplicates columns.label", False, "exclude", "derive from columns; avoid repeated labels per cell"),
        row("cells.value", "normalizeTableCell(row[key])", True, False, "textarea base value", "read-only value", False, "no", True, "include", "normalized canonical cell value before empty display replacement"),
        row("cells.displayValue", "value or emptyValue", True, False, "optional display", "display", False, "no", True, "include", "captures '-' behavior without renderer logic"),
        row("cells.isEmpty", "value === '' / meaningless", True, False, "useful", "useful", False, "no", True, "include", "small stable semantic flag"),
        row("cells.align", "_invoiceDataAlign(key)", False, True, "style", "style", True, "duplicates column display policy", False, "exclude", "same reason as columns.align"),
        row("cells.rowIndex", "rows array index", False, False, "no", "no", True, "duplicate", False, "exclude", "derive from row array"),
        row("cells.columnIndex", "cells array index", False, False, "no", "no", True, "duplicate", False, "exclude", "derive from cell array"),
        row("meta.rowCount", "rows.length", True, False, "summary", "summary", True, "summary duplicate", True, "include", "cheap and useful manifest/body sanity"),
        row("meta.columnCount", "columns.length", True, False, "summary", "summary", True, "summary duplicate", True, "include", "cheap and useful fixture sanity"),
        row("meta.hasRows", "rows.length > 0", True, False, "yes", "yes", True, "summary duplicate", True, "include", "clear guard for empty state"),
        row("meta.hasColumns", "columns.length > 0", True, False, "yes", "yes", True, "summary duplicate", True, "include", "clear guard for empty state"),
        row("meta.hasEmptyCells", "cells.some(isEmpty)", False, False, "not currently used", "not currently used", True, "derive from cells", False, "exclude", "derive easily; avoid fixture churn"),
    ]


def final_contract() -> dict[str, Any]:
    input_type = """type BuildStructuredTableViewModelInput = {
  rows: ReadonlyArray<Record<string, unknown>>;
  displayCols: ReadonlyArray<{
    key: string;
    labelKo: string;
  }>;
  emptyValue?: string; // default "-"
};"""
    output_type = """type StructuredTableViewModel = {
  columns: Array<{
    key: string;
    label: string;
  }>;
  rows: Array<{
    cells: Array<{
      key: string;
      value: string;
      displayValue: string;
      isEmpty: boolean;
    }>;
  }>;
  meta: {
    rowCount: number;
    columnCount: number;
    hasRows: boolean;
    hasColumns: boolean;
  };
};"""
    return {
        "selectedCandidate": "candidate_1_minimal",
        "inputType": input_type,
        "outputType": output_type,
        "excludedGroups": {
            "displayPolicy": ["align", "width", "isNumeric", "isIndex"],
            "derivedIndexes": ["columns.index", "rows.rowIndex", "cells.rowIndex", "cells.columnIndex"],
            "duplicates": ["cells.label"],
            "rawDuplication": ["rows.sourceRow"],
            "derivedMeta": ["meta.hasEmptyCells"],
        },
        "why": [
            "Fixture should lock shared data contract, not style policy.",
            "Array positions provide indexes without serializing them.",
            "columns.label makes cells.label redundant.",
            "Custom edit overlay uses row position + cell key; sourceRow is not required.",
            "hasEmptyCells is derivable from cells.isEmpty.",
        ],
    }


def clean_json_reuse() -> dict[str, Any]:
    return {
        "judgement": "Clean JSON fixture는 보조 baseline으로만 사용하고 table_view_model_v1 fixture는 별도 필요",
        "whyStillSeparate": [
            "trim 후에도 columns가 추가된다.",
            "trim 후에도 cells/displayValue/isEmpty가 추가된다.",
            "trim 후에도 meta가 추가된다.",
            "Clean JSON rows는 object rows이고 view model rows는 cells array다.",
        ],
        "reuseFor": ["ordered values", "rowIndex/column key baseline", "trade_3 locked behavior cross-check"],
        "notReuseFor": ["columns labels", "displayValue empty replacement", "isEmpty flags", "view model meta"],
    }


def fixture_instruction() -> dict[str, Any]:
    return {
        "fixtureRoot": "tmp/fixtures/table_view_model_v1/",
        "cases": ["trade_1", "trade_2", "trade_3", "trade_4", "trade_5", "trade_6", "trade_7"],
        "bodyShape": "StructuredTableViewModel only; metadata goes to manifest.json",
        "manifest": ["caseId", "templateName", "templateId", "inputFile", "fixturePath", "rowCount", "columnCount", "rowIndexPolicy", "status", "notes"],
        "rowCount": "compare to known invoice expected rowCount",
        "columnCount": "columns.length in view model",
        "rowIndexPolicy": "check columns.some(c.key === 'rowIndex') for include/exclude cases",
        "trade3Locked": "record whether columns include insuranceCode/amount and preserve current behavior",
        "cleanJsonAssist": "compare key/value baseline with Clean JSON rows as supplemental check only",
        "equality": "deep equality on trimmed view model JSON",
        "doNotInclude": ["align", "width", "style", "sourceRow", "indices", "cells.label", "hasEmptyCells"],
    }


def helper_instruction() -> dict[str, Any]:
    return {
        "helperName": "buildStructuredTableViewModel",
        "fileCandidate": "src/lib/structuredTableViewModel.ts",
        "input": "final trimmed input contract",
        "output": "final trimmed output contract",
        "exclude": ["legacy fallback", "mode", "custom edits", "validation decoration", "React/DOM/localStorage/network", "input mutation"],
        "application": "Prefer helper extraction + direct runner first; OcrResultPanel adoption may be same step only if fixture runner passes and diff remains tiny.",
    }


def build_report_data(typecheck: dict[str, Any], build: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": TASK,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "noProductionCodeModifiedByThisTask": True,
        "createdFiles": [
            "tmp/codex_table_view_model_contract_trim_precheck.py",
            "docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md",
            "docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.json",
        ],
        "sourceFacts": source_facts(),
        "fieldTrimTable": trim_table(),
        "alignWidthDecision": {
            "decision": "exclude_from_v1_contract",
            "reason": "_invoiceColWidth/_invoiceDataAlign are shared today but are style policy, not shared data. Keep them in renderer/display policy for now.",
        },
        "sourceRowDecision": {
            "decision": "exclude",
            "reason": "Custom edit write-back uses row index + col key; sourceRow duplicates raw input and bloats fixture.",
        },
        "duplicateDecision": {
            "cellsLabel": "exclude; derive from columns",
            "indices": "exclude; derive from array positions and avoid rowIndex naming collision",
        },
        "hasEmptyCellsDecision": {
            "decision": "exclude",
            "reason": "derive from rows[].cells[].isEmpty; not currently used as UI input",
        },
        "finalContract": final_contract(),
        "cleanJsonReuse": clean_json_reuse(),
        "fixtureInstruction3D1": fixture_instruction(),
        "helperInstruction3D2": helper_instruction(),
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
    trim_rows = "\n".join(
        f"| {cell(r['field'])} | {cell(r['deriveFrom'])} | {r['commonData']} | {r['displayPolicy']} | {cell(r['customNeed'])} | {cell(r['recommendation'])} | {cell(r['reason'])} |"
        for r in data["fieldTrimTable"]
    )
    contract = data["finalContract"]
    md = f"""# FRONTEND CLEANUP 3D0-2 TABLE VIEW MODEL CONTRACT TRIM PRECHECK 20260521

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

## 3. 3D0 Output Field별 Trim 판단
| field | deriveFrom | commonData | displayPolicy | customNeed | recommendation | reason |
| --- | --- | --- | --- | --- | --- | --- |
{trim_rows}

## 4. align / width / isNumeric / isIndex 판단
- 결정: `{data['alignWidthDecision']['decision']}`
- 근거: {data['alignWidthDecision']['reason']}
- `_invoiceColWidth`, `_invoiceDataAlign`, `_NUM_KEYS`, `_IDX_KEYS`는 현재 세 탭에서 비슷하게 쓰이지만 렌더링 style/nowrap 정책이다.
- 1차 view model fixture에는 넣지 않고, 나중에 renderer/display policy helper에서 다루는 편이 안전하다.

## 5. sourceRow 필요성 판단
- 결정: `{data['sourceRowDecision']['decision']}`
- 근거: {data['sourceRowDecision']['reason']}

## 6. cells.label / index 중복성 판단
- cells.label: {data['duplicateDecision']['cellsLabel']}
- indices: {data['duplicateDecision']['indices']}

## 7. meta.hasEmptyCells 판단
- 결정: `{data['hasEmptyCellsDecision']['decision']}`
- 근거: {data['hasEmptyCellsDecision']['reason']}

## 8. 최종 추천 Contract
선택: `{contract['selectedCandidate']}`

### Input
```ts
{contract['inputType']}
```

### Output
```ts
{contract['outputType']}
```

제외 그룹:
{chr(10).join(f"- {k}: {', '.join(v)}" for k, v in contract['excludedGroups'].items())}

## 9. Clean JSON Fixture 재사용 가능성 재판단
판정: **{data['cleanJsonReuse']['judgement']}**

보조 재사용:
{chr(10).join(f"- {x}" for x in data['cleanJsonReuse']['reuseFor'])}

별도 fixture가 필요한 이유:
{chr(10).join(f"- {x}" for x in data['cleanJsonReuse']['whyStillSeparate'])}

## 10. 3D-1 Fixture Lock 지시안
- 위치: `{data['fixtureInstruction3D1']['fixtureRoot']}`
- 대상: {', '.join(data['fixtureInstruction3D1']['cases'])}
- 본문 shape: {data['fixtureInstruction3D1']['bodyShape']}
- equality: {data['fixtureInstruction3D1']['equality']}
- fixture에 넣지 않을 것: {', '.join(data['fixtureInstruction3D1']['doNotInclude'])}
- rowIndex 확인: {data['fixtureInstruction3D1']['rowIndexPolicy']}
- 거래_3 확인: {data['fixtureInstruction3D1']['trade3Locked']}

## 11. 3D-2 Helper Extraction 지시안
- helper: `{data['helperInstruction3D2']['helperName']}`
- 후보 파일: `{data['helperInstruction3D2']['fileCandidate']}`
- 제외: {', '.join(data['helperInstruction3D2']['exclude'])}
- 적용: {data['helperInstruction3D2']['application']}

## 12. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | ---: | ---: |
| npm run typecheck | {data['typecheck']['status']} | {data['typecheck']['exitCode']} | {data['typecheck']['durationSeconds']} |
| npm run build | {data['build']['status']} | {data['build']['exitCode']} | {data['build']['durationSeconds']} |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` observed = `{data['knownStderrNoise']['observed']}`

## 13. 다음 작업 제안
1. 3D-1에서 trimmed contract 기준으로 `table_view_model_v1` fixture lock을 만든다.
2. 3D-2에서 `buildStructuredTableViewModel` helper를 생성한다.
3. helper direct runner에서 trimmed fixture deep equality를 검증한다.
4. align/width/style 공통화는 renderer 단계까지 보류한다.
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
