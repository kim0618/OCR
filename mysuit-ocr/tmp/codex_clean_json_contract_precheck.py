from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_CLEAN_JSON_CONTRACT_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT_JSON = DOCS / "CLEAN_JSON_CONTRACT_20260521.json"
OUT_MD = DOCS / "CLEAN_JSON_CONTRACT_20260521.md"

FILES = {
    "OcrResultPanel": ROOT / "src/components/upload/OcrResultPanel.tsx",
    "invoiceTableDisplay": ROOT / "src/lib/invoiceTableDisplay.ts",
    "DetailHistoryView": ROOT / "src/components/history/DetailHistoryView.tsx",
    "TestWorkspace": ROOT / "src/components/test/TestWorkspace.tsx",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def run_command(args: list[str], cwd: Path, timeout: int = 180) -> dict[str, Any]:
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
    result = run_command(
        ["git", "-c", "safe.directory=D:/Free_Vue/OCR", "status", "--short"],
        ROOT,
        timeout=30,
    )
    lines = [line for line in result.get("stdoutTail", "").splitlines() if line.strip()]
    return {
        "statusCommand": result,
        "isDirty": len(lines) > 0,
        "entries": lines,
    }


def has(text: str, needle: str) -> bool:
    return needle in text


def first_line(text: str, needle: str) -> int | None:
    for idx, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return idx
    return None


def source_findings() -> dict[str, Any]:
    sources = {name: read_text(path) for name, path in FILES.items()}
    ocr = sources["OcrResultPanel"]
    display = sources["invoiceTableDisplay"]
    history = sources["DetailHistoryView"]
    test = sources["TestWorkspace"]

    return {
        "checkedFiles": {name: str(path.relative_to(ROOT)) for name, path in FILES.items()},
        "OcrResultPanel": {
            "cleanJsonDefinedAtLine": first_line(ocr, "const cleanJson: CleanJsonResult = useMemo"),
            "toCleanJsonDefinedAtLine": first_line(ocr, "const toCleanJson = () => JSON.stringify(cleanJson, null, 2)"),
            "docTableRowsFromDocumentFields": has(ocr, "const rows = df.tableRows"),
            "docTableMetaFromDocumentFields": has(ocr, "const tm = df.tableMeta"),
            "docTableDisplayColsUsesBuildInvoicePreviewCols": has(ocr, "buildInvoicePreviewCols(docTableMeta, docTableRows)"),
            "cleanRowsUsesDisplayColumnOrder": has(ocr, "cols.map((col) => col.key)") and has(ocr, "for (const key of orderedKeys)"),
            "cleanJsonInfoUsesFieldTypeField": has(ocr, '.filter((f) => f.field_type === "field")'),
            "cleanJsonTablesUsesFieldTypeTable": has(ocr, '.filter((f) => f.field_type === "table")'),
            "tableRowsPriority": [
                "document_fields.tableRows + docTableDisplayCols",
                "field.tableRows",
                "field.table_data",
                "JSON.parse(field.value) as legacy table_data",
            ],
            "hasFallbackFieldTableRows": has(ocr, "Array.isArray(f.tableRows)"),
            "hasFallbackTableData": has(ocr, "Array.isArray(f.table_data)"),
            "hasFallbackValueJsonParse": has(ocr, "JSON.parse(f.value)"),
            "templateNameFallback": 'templateName ?? ""',
            "copyExportUseCurrentMode": has(ocr, "previewMode === \"markdown\" ? toMarkdown() : toCleanJson()"),
            "previewUsesDocTableDisplayCols": has(ocr, "const finalDisplayCols = docTableDisplayCols"),
            "customUsesDocTableDisplayCols": has(ocr, "{docTableDisplayCols.map((col) => ("),
            "rawJsonModeSeparate": has(ocr, "JSON.stringify(result, null, 2)"),
        },
        "invoiceTableDisplay": {
            "shouldDisplayRowIndexDefinedAtLine": first_line(display, "export function shouldDisplayRowIndex"),
            "buildInvoicePreviewColsDefinedAtLine": first_line(display, "export function buildInvoicePreviewCols"),
            "rowIndexAllowedByExternalExpectedKeys": has(display, "externalExpectedKeys") and has(display, 'k === "rowIndex"'),
            "rowIndexAllowedByExpectedColumnKeys": has(display, "tableMeta?.expectedColumnKeys") and has(display, 'String(k) === "rowIndex"'),
            "tableMetaColumnsNotStandaloneRowIndexSignal": has(display, 'filter((k) => k !== "rowIndex"') and has(display, "tableMeta?.columns"),
            "rowValuesNotStandaloneRowIndexSignal": not has(display, 'hasMeaningfulTableValue(rows, "rowIndex")'),
            "rowIndexPrependedByPolicy": has(display, "if (shouldDisplayRowIndex(tableMeta, externalExpectedKeys))"),
            "internalKeysFiltered": has(display, "isInternalTableKey"),
        },
        "DetailHistoryView": {
            "usesBuildInvoicePreviewCols": has(history, "buildInvoicePreviewCols(tableMeta, tableRows)"),
            "tableRowsFromDocumentFields": has(history, "const rows = df.tableRows"),
            "tableMetaFromDocumentFields": has(history, "document_fields?.tableMeta"),
        },
        "TestWorkspace": {
            "importsShouldDisplayRowIndex": has(test, "shouldDisplayRowIndex"),
            "getDisplayTableColumnsDefinedAtLine": first_line(test, "function getDisplayTableColumns"),
            "allModeIntentionallyUnfiltered": has(test, 'if (mode === "all") return [...ALL_CANONICAL_COLS]'),
            "expectedModeUsesManifestExpected": has(test, "manifestExpectedColKeys && manifestExpectedColKeys.length > 0"),
            "detectedModeFiltersRowIndexThenPolicyPrepends": has(test, 'const baseCols = metaCols.filter((c) => c !== "rowIndex")'),
            "hasValueModeSuppressesRowIndexUnlessPolicy": has(test, 'if (col === "rowIndex" && !showRowIndex) return false'),
        },
    }


def build_report(typecheck: dict[str, Any], build: dict[str, Any]) -> dict[str, Any]:
    findings = source_findings()
    status = git_status()
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "task": TASK,
        "generatedAt": now,
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "noProductionCodeModifiedByThisTask": True,
        "allowedOutputs": [str(Path("tmp/codex_clean_json_contract_precheck.py")), str(OUT_MD.relative_to(ROOT)), str(OUT_JSON.relative_to(ROOT))],
        "repoDirtyStatus": status,
        "sourceFindings": findings,
        "currentCleanJsonFlow": [
            "OcrResultPanel.tsx computes docTableRows from result.document_fields.tableRows.",
            "docTableMeta is read from result.document_fields.tableMeta.",
            "docTableDisplayCols is computed with buildInvoicePreviewCols(docTableMeta, docTableRows).",
            "Clean JSON info is built from editedFields where field_type === 'field'.",
            "Clean JSON tables are built from editedFields where field_type === 'table'.",
            "For structured invoice rows, Clean JSON uses document_fields.tableRows ordered by docTableDisplayCols.",
            "Legacy fallbacks are field.tableRows, field.table_data, and JSON.parse(field.value).",
            "Copy/export serializes the currently selected markdown or Clean JSON representation.",
        ],
        "cleanJsonV1Contract": {
            "topLevel": {
                "templateName": "Always present. Current code uses templateName ?? ''. documentType/doc_type is not substituted as templateName.",
                "info": "Optional array. Present only when one or more field entries exist.",
                "tables": "Optional array. Present only when one or more table entries exist.",
                "forbiddenExpansionPattern": "Do not add top-level info2/info3/table2 keys.",
            },
            "infoItems": {
                "source": "editedFields filtered by field_type === 'field'.",
                "shape": {"key": "field.name", "label": "field.ko || field.label || field.name", "value": "field.value ?? ''"},
                "emptyValueRule": "null/undefined values become an empty string; empty strings remain included.",
                "excludedByConstruction": ["confidence", "bbox", "sourceBboxes", "overlayAdoption", "autofillAction", "source", "original"],
            },
            "tableItems": {
                "source": "editedFields filtered by field_type === 'table'.",
                "shape": {"key": "field.name", "label": "field.ko || field.label || field.name", "rows": "array of ordered row objects"},
                "columnsOutput": "Current v1 does not emit a separate columns array in Clean JSON tables.",
                "rowSourcePriority": [
                    "document_fields.tableRows when docTableDisplayCols exists",
                    "field.tableRows",
                    "field.table_data",
                    "JSON.parse(field.value) legacy table payload",
                ],
                "excludedByConstruction": ["confidence", "bbox", "table_data raw cells", "raw debug", "tableMeta", "valueMappingWarnings"],
            },
            "rowRules": {
                "rowsAreArrays": True,
                "rowObjectsAreOrderedByDisplayColumns": True,
                "doNotUseObjectKeysForStructuredInvoiceRows": True,
                "normalizeValuesWith": "normalizeCell(row[key])",
                "legacyCellsFallback": "Cells are mapped to INVOICE_TABLE_COL_PRIORITY fallback keys, then col_N for overflow.",
            },
            "rawResponseExcludedFromCleanJson": [
                "extract_debug",
                "templateImageNormalization",
                "processing_time",
                "full_text",
                "document_fields",
                "raw OCR/debug timing",
                "processed_image",
                "original_image",
            ],
        },
        "rowIndexContract": {
            "principle": "rowIndex is included only when it is an expected/display column, not merely because row data contains 1..N values.",
            "displaySignals": ["externalExpectedKeys includes rowIndex", "tableMeta.expectedColumnKeys includes rowIndex"],
            "nonSignals": ["tableMeta.columns contains rowIndex", "rows contain rowIndex values"],
            "cleanJsonRule": "Clean JSON must follow docTableDisplayCols; it must not re-add rowIndex with Object.keys(row).",
            "documentFieldsMutation": "document_fields.tableRows remains unchanged.",
            "currentInvoiceExpectation": {
                "exclude": ["거래_1", "거래_4", "거래_5", "거래_7"],
                "include": ["거래_2", "거래_3", "거래_6"],
                "separateIssue": "거래_3 insuranceCode/amount extra columns are not a rowIndex policy issue.",
            },
        },
        "previewCleanJsonColumnContract": {
            "previewSource": "Preview table columns use docTableDisplayCols from buildInvoicePreviewCols.",
            "cleanJsonSource": "Clean JSON structured table rows use the same docTableDisplayCols.",
            "guarantees": [
                "Clean JSON table row key order equals Preview display column order for structured invoice tableRows.",
                "Preview-hidden internal columns remain hidden in Clean JSON.",
                "Preview-visible expected columns remain visible in Clean JSON.",
                "Clean JSON builder must not depend on the original object key order of tableRows.",
            ],
            "relatedSurfaces": {
                "Custom": "OcrResultPanel custom table rendering also uses docTableDisplayCols when structured rows exist.",
                "Validation": "Validation table rendering in OcrResultPanel uses structured row/display column path for table fields.",
                "History": "DetailHistoryView computes tableDisplayCols with buildInvoicePreviewCols.",
                "TestWorkspace": "Uses a separate getDisplayTableColumns path, but it imports shouldDisplayRowIndex and has matching rowIndex policy except intentional all mode.",
            },
        },
        "cleanJsonV2Direction": {
            "status": "Future direction only. FRONTEND-CLEANUP-1 must keep v1 output unchanged.",
            "principles": [
                "Top-level keys remain templateName, info, tables.",
                "Multiple info regions are represented as items in the info array, not info2/info3 keys.",
                "Multiple tables are represented as items in the tables array, not table2/table3 keys.",
                "Future info items may become sections with key, label, fields.",
                "Future table items may carry key, label, rows and optional internal display metadata.",
                "Do not introduce v2 shape as part of the first helper extraction.",
            ],
            "exampleShape": {
                "templateName": "영수증",
                "info": [{"key": "info_1", "label": "가맹점 정보", "fields": [{"key": "merchantName", "label": "상호", "value": "세광전기조명"}]}],
                "tables": [{"key": "table_1", "label": "품목표", "rows": []}],
            },
        },
        "helperExtractionDraft": {
            "candidateNames": ["buildCleanJsonResult", "buildCleanOcrJson", "createCleanJsonPayload"],
            "recommendedName": "buildCleanJsonResult",
            "inputDraft": {
                "templateName": "string | null | undefined",
                "fields": "OcrField[]",
                "documentFields": "Record<string, unknown> | null | undefined",
                "docTableRows": "Record<string, unknown>[] | null",
                "docTableDisplayCols": "{ key: string }[] | null",
                "tableMeta": "Record<string, unknown> | null | undefined",
            },
            "outputDraft": "CleanJsonV1Payload = { templateName: string; info?: CleanInfoItem[]; tables?: CleanTableItem[] }",
            "responsibilities": [
                "Build Clean JSON v1 only.",
                "Normalize field values and table cell values.",
                "Use provided display columns for structured table row order.",
                "Preserve existing fallback behavior for field.tableRows/table_data/value JSON.",
                "Exclude UI/debug/raw OCR fields from Clean JSON.",
            ],
            "nonResponsibilities": [
                "Do not compute Preview columns itself except through inputs supplied by caller.",
                "Do not mutate result/document_fields/tableRows.",
                "Do not build Raw JSON.",
                "Do not know React state, hooks, copy/export UI, or preview mode.",
                "Do not introduce Clean JSON v2 output shape yet.",
            ],
        },
        "beforeAfterValidationCriteria": [
            "Clean JSON before/after deep equality for representative fixtures.",
            "templateName unchanged.",
            "info array unchanged.",
            "tables array unchanged.",
            "Invoice rows key order unchanged.",
            "rowIndex policy unchanged: 거래_1/4/5/7 excluded, 거래_2/3/6 included.",
            "거래_3 insuranceCode/amount behavior unchanged.",
            "Preview column order equals Clean JSON row keys.",
            "Raw JSON mode unchanged.",
            "Copy/export behavior unchanged.",
            "npm run typecheck PASS.",
            "npm run build PASS.",
        ],
        "recommendedFixtures": [
            "invoice_statement 거래_1~거래_7",
            "receipt TPL-003 baseline samples",
            "field-only document",
            "document with no tables",
            "legacy table_data fallback document",
        ],
        "risks": [
            "OcrResultPanel useMemo dependencies can regress if helper inputs are incomplete.",
            "docTableDisplayCols can be omitted accidentally, causing Object.keys/fallback order drift.",
            "Legacy field.tableRows/table_data/value fallback can be lost during extraction.",
            "rowIndex can reappear if helper rebuilds keys from raw rows.",
            "Applying v2 shape too early would be a breaking change.",
            "Confusing current v1 info field-array with future v2 info section-array.",
            "Mixing Clean JSON and Raw JSON responsibilities.",
        ],
        "typecheck": typecheck,
        "build": build,
        "nextWork": [
            "FRONTEND-CLEANUP-1: extract Clean JSON builder as a pure helper while preserving v1 output exactly.",
            "Add before/after fixture comparison for invoice_statement 거래_1~거래_7.",
            "Keep 거래_3 insuranceCode/amount as a separate policy task.",
            "After helper extraction, consider shared table renderer and label map cleanup.",
        ],
    }


def md_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = "| " + " | ".join(rows[0]) + " |\n"
    sep = "| " + " | ".join(["---"] * len(rows[0])) + " |\n"
    body = "".join("| " + " | ".join(row) + " |\n" for row in rows[1:])
    return header + sep + body


def make_md(report: dict[str, Any]) -> str:
    dirty = report["repoDirtyStatus"]
    findings = report["sourceFindings"]
    typecheck = report["typecheck"]
    build = report["build"]
    rows = [
        ["Command", "Status", "Exit", "Seconds"],
        ["npm run typecheck", typecheck["status"], str(typecheck["exitCode"]), str(typecheck["durationSeconds"])],
        ["npm run build", build["status"], str(build["exitCode"]), str(build["durationSeconds"])],
    ]

    return f"""# CLEAN JSON CONTRACT 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`
- 생성 시각: `{report['generatedAt']}`

## 2. 운영 코드 수정 없음 확인
- 이번 작업은 문서화/계약 정의 전용이다.
- 운영 frontend/backend/templates/manifest/GT는 수정하지 않았다.
- 생성 파일은 이 스크립트와 docs 리포트만이다.
- repo dirty 상태: `{'DIRTY' if dirty['isDirty'] else 'CLEAN'}`
- dirty entries:
```text
{chr(10).join(dirty['entries']) if dirty['entries'] else '(none)'}
```

## 3. 확인한 소스
- `src/components/upload/OcrResultPanel.tsx`
- `src/lib/invoiceTableDisplay.ts`
- `src/components/history/DetailHistoryView.tsx`
- `src/components/test/TestWorkspace.tsx`

핵심 위치:
- Clean JSON 생성: `OcrResultPanel.tsx:{findings['OcrResultPanel']['cleanJsonDefinedAtLine']}`
- `toCleanJson`: `OcrResultPanel.tsx:{findings['OcrResultPanel']['toCleanJsonDefinedAtLine']}`
- `shouldDisplayRowIndex`: `invoiceTableDisplay.ts:{findings['invoiceTableDisplay']['shouldDisplayRowIndexDefinedAtLine']}`
- `buildInvoicePreviewCols`: `invoiceTableDisplay.ts:{findings['invoiceTableDisplay']['buildInvoicePreviewColsDefinedAtLine']}`
- TestWorkspace `getDisplayTableColumns`: `TestWorkspace.tsx:{findings['TestWorkspace']['getDisplayTableColumnsDefinedAtLine']}`

## 4. 현재 Clean JSON 생성 흐름
1. `document_fields.tableRows`를 `docTableRows`로 읽는다.
2. `document_fields.tableMeta`를 `docTableMeta`로 읽는다.
3. `docTableDisplayCols = buildInvoicePreviewCols(docTableMeta, docTableRows)`로 Preview 표시 컬럼을 만든다.
4. `field_type === "field"`는 `info` 항목이 된다.
5. `field_type === "table"`은 `tables` 항목이 된다.
6. 구조화 거래명세서 rows는 `docTableDisplayCols` 순서로 ordered object를 만든다.
7. fallback은 `field.tableRows` -> `field.table_data` -> `JSON.parse(field.value)` 순서다.
8. Copy/Export는 현재 Markdown/Clean JSON 모드에 따라 문자열을 내보낸다.

## 5. Clean JSON v1 Contract
현재 운영 출력은 다음 top-level 구조를 유지한다.

```ts
type CleanJsonV1Payload = {{
  templateName: string;
  info?: Array<{{ key: string; label: string; value: string }}>;
  tables?: Array<{{ key: string; label: string; rows: Array<Record<string, string>> }}>;
}};
```

- `templateName`: 항상 존재한다. 현재 코드는 `templateName ?? ""`를 사용하며 `documentType/doc_type`으로 대체하지 않는다.
- `info`: `field_type === "field"` 항목에서 만든다. `key=f.name`, `label=f.ko || f.label || f.name`, `value=f.value ?? ""`.
- `tables`: `field_type === "table"` 항목에서 만든다. `key=f.name`, `label=f.ko || f.label || f.name`, `rows`를 가진다.
- v1 tables는 사용자 출력에 별도 `columns` 배열을 넣지 않는다.
- `confidence`, `bbox`, `source`, `original`, OCR debug/timing/raw image 계열 값은 Clean JSON의 사용자용 구조에 포함하지 않는다.

## 6. Rows / Column Order Contract
- `rows`는 배열이다.
- 각 row는 표시 컬럼 순서 기반 ordered object다.
- 구조화 거래명세서에서는 `Object.keys(row)` 원본 순서에 의존하지 않는다.
- Clean JSON rows key order는 Preview `docTableDisplayCols` 순서와 같아야 한다.
- Preview에서 숨긴 내부 컬럼은 Clean JSON에서도 숨겨야 한다.
- Preview에서 표시한 실제 컬럼은 Clean JSON에서도 표시해야 한다.

## 7. rowIndex Contract
- rowIndex는 무조건 숨기지 않는다.
- 실제 expected 컬럼이면 Clean JSON rows에 포함한다.
- 내부 생성 행번호이면 Clean JSON rows에서 제외한다.
- 표시 근거는 `externalExpectedKeys` 또는 `tableMeta.expectedColumnKeys`의 `rowIndex`다.
- `tableMeta.columns`에만 있는 `rowIndex`는 단독 표시 근거가 아니다.
- rows 안의 `rowIndex` 값만으로 표시하지 않는다.
- `document_fields.tableRows` 원본은 변경하지 않는다.
- Clean JSON builder는 display columns를 신뢰해야 하며, `Object.keys(row)`로 `rowIndex`를 되살리면 안 된다.

현재 거래명세서 기준:
- rowIndex 제외: 거래_1, 거래_4, 거래_5, 거래_7
- rowIndex 유지: 거래_2, 거래_3, 거래_6
- 거래_3 `insuranceCode`/`amount` extra는 rowIndex와 별도 이슈다.

## 8. Preview / Custom / Validation / History / TestWorkspace
- Preview: `docTableDisplayCols`를 사용한다.
- Clean JSON: 같은 `docTableDisplayCols`로 row object를 만든다.
- Custom/Validation: 구조화 tableRows가 있으면 `docTableDisplayCols` 경로를 사용한다.
- History: `DetailHistoryView`가 `buildInvoicePreviewCols(tableMeta, tableRows)`를 사용한다.
- TestWorkspace: 별도 `getDisplayTableColumns` 경로가 있으나 `shouldDisplayRowIndex`를 사용한다. `all` 모드는 의도적으로 정책 미적용이다.

## 9. Clean JSON v2 확장 방향
FRONTEND-CLEANUP-1에서는 v1 출력 구조를 바꾸지 않는다.

장기 방향:
- top-level key는 `templateName`, `info`, `tables` 중심으로 유지한다.
- `info2`, `info3`, `table2` 같은 top-level key는 만들지 않는다.
- 여러 영역은 `info` 배열의 여러 item으로 표현한다.
- 여러 테이블은 `tables` 배열의 여러 item으로 표현한다.
- 향후 v2의 `info` item은 `key`, `label`, `fields`를 가진 section이 될 수 있다.
- v1 field-array info를 v2 section-array info로 바꾸는 작업은 별도 마이그레이션이다.

## 10. Helper 분리 계약 초안
추천 helper 이름: `buildCleanJsonResult`

입력 후보:
```ts
type BuildCleanJsonInput = {{
  templateName?: string | null;
  fields: OcrField[];
  documentFields?: Record<string, unknown> | null;
  docTableRows?: Record<string, unknown>[] | null;
  docTableDisplayCols?: Array<{{ key: string }}> | null;
  tableMeta?: Record<string, unknown> | null;
}};
```

출력 후보:
```ts
type CleanJsonV1Payload = {{
  templateName: string;
  info?: CleanInfoItem[];
  tables?: CleanTableItem[];
}};
```

책임:
- Clean JSON v1만 생성한다.
- field/table 값을 현재와 동일하게 정규화한다.
- 구조화 tableRows는 입력받은 display columns 순서를 따른다.
- legacy fallback을 유지한다.

책임 아님:
- Raw JSON 생성
- React state/useMemo/copy/export UI
- Preview column 자체 계산
- `document_fields.tableRows` 원본 변경
- v2 출력 구조 도입

## 11. Before / After 검증 기준
- Clean JSON before/after deep equality
- `templateName` 동일
- `info` 배열 동일
- `tables` 배열 동일
- 거래명세서 rows key order 동일
- 거래_1/4/5/7 rowIndex 제외 유지
- 거래_2/3/6 rowIndex 유지
- 거래_3 `insuranceCode`/`amount` 동작 변경 없음
- Preview column order와 Clean JSON row keys 일치
- Raw JSON 모드 변경 없음
- Copy/Export 동작 변경 없음
- typecheck/build PASS

권장 fixture:
- invoice_statement 거래_1~거래_7
- 영수증 TPL-003 baseline 일부 또는 전체
- field-only 문서
- table 없는 문서
- legacy `table_data` fallback 문서

## 12. 리스크와 주의사항
- `OcrResultPanel.tsx`의 `useMemo` 의존성 누락 위험
- `docTableDisplayCols` 전달 누락으로 row order/rowIndex 회귀 위험
- `field.tableRows/table_data/value` fallback 누락 위험
- helper가 `Object.keys(row)`를 사용해 숨긴 컬럼을 되살릴 위험
- v2 구조를 너무 일찍 적용해 breaking change가 생길 위험
- 현재 v1 `info` field-array와 미래 v2 `info` section-array 혼동 위험

## 13. Typecheck / Build 결과
{md_table(rows)}

### typecheck stdout tail
```text
{typecheck['stdoutTail'] or '(empty)'}
```

### typecheck stderr tail
```text
{typecheck['stderrTail'] or '(empty)'}
```

### build stdout tail
```text
{build['stdoutTail'] or '(empty)'}
```

### build stderr tail
```text
{build['stderrTail'] or '(empty)'}
```

## 14. 다음 작업 제안
1. FRONTEND-CLEANUP-1에서 `buildCleanJsonResult` 순수 helper를 분리하되 v1 출력 deep equality를 먼저 고정한다.
2. 거래_1~거래_7 fixture로 Preview column order와 Clean JSON row keys를 비교한다.
3. 거래_3 `insuranceCode`/`amount`는 별도 정책 작업으로 분리한다.
4. Clean JSON helper 분리 후 table renderer/label map 공통화를 다음 단계로 진행한다.
"""


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    print(f"[{TASK}] root={ROOT}")
    print("[check] running npm run typecheck")
    typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180)
    print(f"[check] typecheck={typecheck['status']} duration={typecheck['durationSeconds']}s")
    print("[check] running npm run build")
    build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)
    print(f"[check] build={build['status']} duration={build['durationSeconds']}s")

    report = build_report(typecheck, build)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(make_md(report), encoding="utf-8")
    print(f"[write] {OUT_JSON}")
    print(f"[write] {OUT_MD}")
    return 0 if typecheck["status"] == "PASS" and build["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
