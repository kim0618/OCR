from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_MD = DOCS / "FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.md"
REPORT_JSON = DOCS / "FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.json"
TVM_ROOT = ROOT / "tmp" / "fixtures" / "table_view_model_v1"
CLEAN_ROOT = ROOT / "tmp" / "fixtures" / "clean_json_v1" / "invoice_statement"
TESTSET_MANIFEST = ROOT / "public" / "data" / "testsets" / "invoice_statement" / "manifest.json"

TRADE_CASES = [
    ("trade_1_1jpg", "1.jpg"),
    ("trade_2_2pdf", "2.pdf"),
    ("trade_3_3pdf", "3.pdf"),
    ("trade_4_4pdf", "4.pdf"),
    ("trade_5_5pdf", "5.pdf"),
    ("trade_6_6pdf", "6.pdf"),
    ("trade_7_7pdf", "7.pdf"),
]

SUMMARY_EXCLUDE_KEYS = {"totalAmount"}
LOT_SERIAL_KEYS = {"lotNo", "serialNo", "serialLot", "serialLotComposite"}
MEANINGLESS = {"", "-", "n/a", "null", "none", "undefined"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


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


def normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def has_meaningful(rows: list[dict[str, Any]], key: str) -> bool:
    return any(normalize(row.get(key)).lower() not in MEANINGLESS for row in rows)


def expected_for_file(filename: str) -> dict[str, Any]:
    manifest = read_json(TESTSET_MANIFEST)
    item = next(item for item in manifest["items"] if item["filename"] == filename)
    cols = item["invoiceProfile"]["tableExpectedColumns"]
    return {
        "required": cols.get("required", []),
        "optional": cols.get("optional", []),
        "display": [col["key"] for col in cols.get("display", [])],
        "displayLabels": {col["key"]: col.get("label") for col in cols.get("display", [])},
        "notes": item.get("notes", ""),
    }


def nonempty_values(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    keys = sorted({key for row in rows for key in row})
    out: dict[str, list[str]] = {}
    for key in keys:
        values = [normalize(row.get(key)) for row in rows if normalize(row.get(key)).lower() not in MEANINGLESS]
        if values:
            out[key] = values[:8]
    return out


def load_trade_case(case_id: str, filename: str) -> dict[str, Any]:
    inp = read_json(TVM_ROOT / "inputs" / f"{case_id}.input.json")
    out = read_json(TVM_ROOT / "invoice_statement" / f"{case_id}.view_model.json")
    clean = read_json(CLEAN_ROOT / f"{case_id}.clean.json")
    details = read_json(DOCS / "FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json")
    capture = next(item for item in details.get("details", []) if item.get("caseId") == case_id).get("captureMeta", {})
    clean_rows = ((clean.get("tables") or [{}])[0].get("rows") or []) if clean.get("tables") else []
    expected = expected_for_file(filename)
    rows = inp["rows"]
    return {
        "caseId": case_id,
        "filename": filename,
        "rows": rows,
        "beforeColumns": [col["key"] for col in inp["displayCols"]],
        "outputColumns": [col["key"] for col in out["columns"]],
        "cleanJsonColumns": list(clean_rows[0].keys()) if clean_rows else [],
        "expected": expected,
        "nonemptyValues": nonempty_values(rows),
        "tableMetaExpectedColumnKeys": capture.get("tableMetaExpectedColumnKeys"),
        "tableMetaColumns": capture.get("tableMetaColumns"),
    }


def recommended_after_columns(case: dict[str, Any]) -> list[str]:
    rows = case["rows"]
    before = list(case["beforeColumns"])
    expected_display = list(case["expected"]["display"])
    expected_set = set(expected_display)
    after = [key for key in before if key not in SUMMARY_EXCLUDE_KEYS]

    # trade_3 is a fixture-locked current behavior; do not re-shape columns here.
    if case["caseId"] == "trade_3_3pdf":
        return after

    for key in expected_display:
        if key in SUMMARY_EXCLUDE_KEYS:
            continue
        if key not in after and has_meaningful(rows, key):
            if key in LOT_SERIAL_KEYS or key in expected_set:
                insert_at = len(after)
                key_order = expected_display.index(key)
                for idx, existing in enumerate(after):
                    if existing in expected_set and key_order < expected_display.index(existing):
                        insert_at = idx
                        break
                after.insert(insert_at, key)

    if "rowIndex" in before and "rowIndex" not in after:
        after.insert(0, "rowIndex")
    if "rowIndex" not in before and "rowIndex" in after:
        after.remove("rowIndex")
    return after


def analyze_trade(case: dict[str, Any]) -> dict[str, Any]:
    after = recommended_after_columns(case)
    before = case["beforeColumns"]
    added = [key for key in after if key not in before]
    removed = [key for key in before if key not in after]
    row_index_before = "included" if "rowIndex" in before else "excluded"
    row_index_after = "included" if "rowIndex" in after else "excluded"
    risk = "low"
    notes: list[str] = []
    if case["caseId"] == "trade_4_4pdf":
        risk = "medium"
        notes.append("totalAmount removed from item-row display; fixtures intentionally change if policy is adopted")
    if case["caseId"] == "trade_6_6pdf":
        risk = "medium"
        notes.append("lotNo added by expected/display override of itemCode+manufacturingNo-empty noise rule")
    if case["caseId"] == "trade_7_7pdf":
        risk = "medium"
        notes.append("serialLotComposite added as expected/display exception to internal/composite filter")
    if case["caseId"] == "trade_3_3pdf":
        notes.append("LOCKED_CURRENT_BEHAVIOR insuranceCode/amount remains unchanged")
    return {
        **{k: v for k, v in case.items() if k != "rows"},
        "afterColumnsRecommended": after,
        "addedColumns": added,
        "removedColumns": removed,
        "rowIndexBefore": row_index_before,
        "rowIndexAfter": row_index_after,
        "cleanJsonFixtureImpact": added or removed,
        "tableViewModelFixtureImpact": added or removed,
        "risk": risk,
        "notes": notes,
    }


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
    impact_rows = [
        [
            item["caseId"],
            item["beforeColumns"],
            item["afterColumnsRecommended"],
            item["addedColumns"],
            item["removedColumns"],
            f"{item['rowIndexBefore']} -> {item['rowIndexAfter']}",
            "Y" if item["cleanJsonFixtureImpact"] else "",
            "Y" if item["tableViewModelFixtureImpact"] else "",
            item["risk"],
        ]
        for item in report["tradeImpactMatrix"]
    ]
    candidate_rows = [
        [item["id"], item["summary"], item["pros"], item["cons"], item["regressionRisk"], item["fixtureImpact"], item["recommendation"]]
        for item in report["policyCandidates"]
    ]
    fixture_rows = [[item["fixture"], item["reason"], item["requiredIfPolicyApplied"]] for item in report["fixtureUpdatePlan"]]
    md = f"""# FRONTEND INVOICE TABLE DISPLAY POLICY FIX PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- fixture 수정 없음.
- `OcrResultPanel.tsx`, `invoiceTableDisplay.ts`, `structuredTableViewModel.ts`, `cleanJsonBuilder.ts`, backend/parser, templates, manifest/GT 수정 없음.

## 3. 생성 파일
- `tmp/codex_invoice_table_display_policy_fix_precheck.py`
- `docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.md`
- `docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.json`

## 4. 현재 Display Policy 흐름
1. `OcrResultPanel.tsx`에서 `docTableRows = result.document_fields.tableRows`.
2. `docTableDisplayCols = buildInvoicePreviewCols(docTableMeta, docTableRows)`.
3. Preview는 `buildStructuredTableViewModel({{ rows, displayCols }})` 결과를 사용한다.
4. Clean JSON은 같은 `docTableDisplayCols`를 `buildCleanJsonResult`에 전달한다.
5. 따라서 `invoiceTableDisplay.ts`의 display policy 변경은 Preview와 Clean JSON fixture 모두에 영향을 줄 수 있다.

## 5. trade_4 상세 원인
- `totalAmount`는 input rows/displayCols/view_model/Clean JSON에 모두 존재한다.
- testset manifest display columns에는 `totalAmount`가 없다.
- 현재 `tableMetaExpectedColumnKeys`에는 `totalAmount`가 있고, hasValue 필터를 통과해 표시된다.
- 판정: summary/doc-level 성격의 `totalAmount`를 item row display에서 제외하는 frontend display policy 보정이 필요하다.

## 6. trade_6 상세 원인
- `lotNo` 값은 rows에 존재한다.
- expected display에도 `lotNo`가 있다.
- 현재 `itemCode`가 있고 `manufacturingNo`가 비어 있으면 `lotNo`를 OCR 노이즈로 숨기는 규칙 때문에 displayCols에서 제거된다.
- 판정: expected/display column에 `lotNo`가 있고 값이 있으면 기존 노이즈 규칙보다 우선할지 결정해야 한다.

## 7. trade_7 상세 원인
- `serialLotComposite=0350623-231024-260811` 값은 rows에 존재한다.
- expected display에도 `serialLotComposite`가 있다.
- 현재 internal/composite key 필터가 `serialLotComposite`를 후보에서 제거한다.
- 판정: expected display가 명시한 composite key는 display 가능한 예외로 승격할 필요가 있다.

## 8. Helper 문제 여부
- `buildStructuredTableViewModel` 문제 아님.
- helper는 caller가 준 `displayCols`를 그대로 columns/cells로 변환하는 pass-through다.
- 수정 지점은 `invoiceTableDisplay.ts`의 `buildInvoicePreviewCols` 또는 그 입력으로 들어가는 expected/display policy 계층이다.

## 9. 추천 Display Policy
권장 1차 조합:
- `totalAmount`는 table row display summary key로 제외.
- expected/display columns가 명시한 `lotNo`는 값이 있으면 기존 lot noise rule보다 우선 표시.
- expected/display columns가 명시한 `serialLotComposite`는 internal/composite 필터 예외로 표시 허용.
- 빈 컬럼/완전 무의미 컬럼은 계속 숨김.
- rowIndex 정책과 trade_3 locked behavior는 그대로 유지.

## 10. trade_1~trade_7 예상 영향
{md_table(['case', 'before', 'recommendedAfter', 'added', 'removed', 'rowIndex', 'cleanJsonFixture', 'tableViewModelFixture', 'risk'], impact_rows)}

## 11. 수정 후보 비교
{md_table(['id', 'summary', 'pros', 'cons', 'regressionRisk', 'fixtureImpact', 'recommendation'], candidate_rows)}

## 12. Fixture 갱신 계획
{md_table(['fixture', 'reason', 'requiredIfPolicyApplied'], fixture_rows)}

## 13. Smoke 판정 업데이트
- automatic checks: PASS
- manual smoke: WARN_COLUMN_POLICY
- 3D-3 technical helper migration: PASS
- Preview/Clean JSON column policy: FOLLOW_UP_REQUIRED

## 14. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| {report['typecheck']['command']} | {report['typecheck']['status']} | {report['typecheck']['exitCode']} | {report['typecheck']['durationSeconds']} | {report['typecheck']['knownStderrNoise']} |
| {report['build']['command']} | {report['build']['status']} | {report['build']['exitCode']} | {report['build']['durationSeconds']} | {report['build']['knownStderrNoise']} |

## 15. 다음 작업 제안
- 추천 작업명: `CODEX_FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_OR_DRYRUN` 또는 `FRONTEND-CLEANUP-3D4-INVOICE-TABLE-DISPLAY-POLICY-FIX`.
- 예상 수정 파일: `src/lib/invoiceTableDisplay.ts`.
- 예상 갱신: table_view_model input/output fixtures, Clean JSON fixtures, manifest metadata for affected cases.
- `structuredTableViewModel.ts`와 `OcrResultPanel.tsx`는 수정하지 않을 가능성이 높다.
- 정책 변경 후 table_view_model runner 8/8, Clean JSON runner 9/9, Markdown check 6/6, typecheck/build, manual smoke를 재수행한다.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    trades = [analyze_trade(load_trade_case(case_id, filename)) for case_id, filename in TRADE_CASES]
    print("[analysis] trade_1~trade_7 policy impact matrix prepared", flush=True)
    print("[check] npm run typecheck", flush=True)
    typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180)
    print(f"[check] typecheck={typecheck['status']} exit={typecheck['exitCode']}", flush=True)
    print("[check] npm run build", flush=True)
    build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)
    print(f"[check] build={build['status']} exit={build['exitCode']}", flush=True)

    fixture_update_plan = []
    for item in trades:
        if not (item["addedColumns"] or item["removedColumns"]):
            continue
        case_id = item["caseId"]
        fixture_update_plan.extend(
            [
                {"fixture": f"tmp/fixtures/table_view_model_v1/inputs/{case_id}.input.json", "reason": "displayCols changed", "requiredIfPolicyApplied": True},
                {"fixture": f"tmp/fixtures/table_view_model_v1/invoice_statement/{case_id}.view_model.json", "reason": "columns/cells/meta.columnCount changed", "requiredIfPolicyApplied": True},
                {"fixture": f"tmp/fixtures/clean_json_v1/invoice_statement/{case_id}.clean.json", "reason": "Clean JSON table rows use docTableDisplayCols", "requiredIfPolicyApplied": True},
            ]
        )
    fixture_update_plan.append({"fixture": "tmp/fixtures/table_view_model_v1/manifest.json", "reason": "columnCount/inputFixture metadata may change", "requiredIfPolicyApplied": True})
    fixture_update_plan.append({"fixture": "tmp/fixtures/clean_json_v1/manifest.json", "reason": "rowKeys metadata may change", "requiredIfPolicyApplied": True})

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "task": TASK,
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "codeModified": False,
        "fixturesModified": False,
        "currentFlow": {
            "docTableDisplayColsSource": "buildInvoicePreviewCols(docTableMeta, docTableRows)",
            "previewUses": "buildStructuredTableViewModel({ rows: docTableRows, displayCols: docTableDisplayCols })",
            "cleanJsonUses": "buildCleanJsonResult(..., docTableRows, docTableDisplayCols)",
            "helperIssue": False,
        },
        "tradeImpactMatrix": trades,
        "policyCandidates": [
            {
                "id": "candidate_1_summary_key_hard_exclude",
                "summary": "summary/doc-level key(totalAmount)를 table display에서 제외",
                "pros": "trade_4 문제를 가장 작게 해결; supplyAmount/taxAmount는 유지 가능",
                "cons": "totalAmount가 실제 품목표 컬럼인 문서가 있으면 숨겨짐",
                "regressionRisk": "medium",
                "fixtureImpact": "trade_4 table_view_model/Clean JSON fixture 갱신",
                "recommendation": "adopt as targeted rule with fixture update intent",
            },
            {
                "id": "candidate_2_lot_serial_key_allowlist",
                "summary": "expected/display에 있는 lotNo/serialLotComposite를 값이 있으면 표시 허용",
                "pros": "trade_6/7 원본 표 구조와 맞음",
                "cons": "기존 노이즈 제거 규칙을 우회하므로 일부 샘플에서 중복/노이즈가 살아날 수 있음",
                "regressionRisk": "medium",
                "fixtureImpact": "trade_6/trade_7 table_view_model/Clean JSON fixture 갱신",
                "recommendation": "adopt only when expected/display column explicitly includes the key",
            },
            {
                "id": "candidate_3_expected_display_priority",
                "summary": "manifest/template expected display columns를 우선하고 없는 key는 숨김",
                "pros": "사용자 시각 기준과 가장 일관됨",
                "cons": "runtime에서 template display definition 전달 경로가 약하면 적용 범위가 커짐",
                "regressionRisk": "medium-high",
                "fixtureImpact": "trade_4/6/7 plus possibly more if display source changes",
                "recommendation": "longer-term direction; first fix can be a constrained subset",
            },
            {
                "id": "candidate_4_known_issue_until_template_column_definition",
                "summary": "Template table column definition 도입까지 known issue로 보류",
                "pros": "현재 fixtures and cleanup stability 유지",
                "cons": "manual smoke WARN 지속",
                "regressionRisk": "low",
                "fixtureImpact": "none",
                "recommendation": "acceptable only if UX issue can wait",
            },
            {
                "id": "candidate_5_backend_tableRows_policy",
                "summary": "parser가 row-level이 아닌 doc-level key를 tableRows에 넣지 않게 수정",
                "pros": "데이터 생성 계층을 근본적으로 정리",
                "cons": "backend/parser 영향 범위와 OCR 회귀 위험이 큼",
                "regressionRisk": "high",
                "fixtureImpact": "API-derived fixtures broadly may need regeneration",
                "recommendation": "not first fix; do separate backend precheck if needed",
            },
        ],
        "recommendedPolicy": {
            "phase1": [
                "exclude totalAmount from table row display as summary key",
                "allow lotNo when expected/display explicitly includes lotNo and rows have meaningful values",
                "allow serialLotComposite when expected/display explicitly includes serialLotComposite and rows have meaningful values",
                "keep empty/meaningless column hiding",
                "preserve rowIndex policy and trade_3 locked behavior",
            ],
            "preferredScope": "frontend display policy in invoiceTableDisplay.ts, with explicit fixture update",
        },
        "fixtureUpdatePlan": fixture_update_plan,
        "smokeVerdict": {
            "automaticChecks": "PASS",
            "manualSmoke": "WARN_COLUMN_POLICY",
            "technicalHelperMigration": "PASS",
            "previewCleanJsonColumnPolicy": "FOLLOW_UP_REQUIRED",
        },
        "typecheck": typecheck,
        "build": build,
        "knownStderrNoise": {
            "id": "ISSUE-FRONTEND-BUILD-LOG-1",
            "message": "ESLint: nextVitals is not iterable",
            "observed": build["knownStderrNoise"],
            "blocking": False if build["exitCode"] == 0 else True,
        },
    }
    write_reports(report)
    print(f"[write] {REPORT_JSON}", flush=True)
    print(f"[write] {REPORT_MD}", flush=True)
    status = "PASS" if typecheck["status"] == "PASS" and build["status"] == "PASS" else "FAIL"
    print(f"[done] {status}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
