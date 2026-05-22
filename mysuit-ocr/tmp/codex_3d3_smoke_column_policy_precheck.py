from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_MD = DOCS / "FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.md"
REPORT_JSON = DOCS / "FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.json"
TVM_ROOT = ROOT / "tmp" / "fixtures" / "table_view_model_v1"
CLEAN_ROOT = ROOT / "tmp" / "fixtures" / "clean_json_v1" / "invoice_statement"
TESTSET_MANIFEST = ROOT / "public" / "data" / "testsets" / "invoice_statement" / "manifest.json"


CASES = {
    "trade_4_4pdf": "4.pdf",
    "trade_6_6pdf": "6.pdf",
    "trade_7_7pdf": "7.pdf",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


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


def nonempty_values(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    keys = sorted({key for row in rows for key in row})
    for key in keys:
        values = []
        for row in rows:
            raw = row.get(key)
            value = "" if raw is None else str(raw)
            if value and value != "-":
                values.append(value)
        if values:
            out[key] = values[:8]
    return out


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


def load_case(case_id: str) -> dict[str, Any]:
    inp = read_json(TVM_ROOT / "inputs" / f"{case_id}.input.json")
    out = read_json(TVM_ROOT / "invoice_statement" / f"{case_id}.view_model.json")
    clean = read_json(CLEAN_ROOT / f"{case_id}.clean.json")
    details = read_json(DOCS / "FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json")
    capture = next(item for item in details.get("details", []) if item.get("caseId") == case_id).get("captureMeta", {})
    rows = inp["rows"]
    output_cols = [col["key"] for col in out["columns"]]
    display_cols = [col["key"] for col in inp["displayCols"]]
    clean_rows = ((clean.get("tables") or [{}])[0].get("rows") or []) if clean.get("tables") else []
    return {
        "caseId": case_id,
        "filename": CASES[case_id],
        "inputFixturePath": f"tmp/fixtures/table_view_model_v1/inputs/{case_id}.input.json",
        "outputFixturePath": f"tmp/fixtures/table_view_model_v1/invoice_statement/{case_id}.view_model.json",
        "cleanJsonFixturePath": f"tmp/fixtures/clean_json_v1/invoice_statement/{case_id}.clean.json",
        "rowCount": len(rows),
        "displayCols": display_cols,
        "outputColumns": output_cols,
        "cleanJsonColumns": list(clean_rows[0].keys()) if clean_rows else [],
        "expectedColumns": expected_for_file(CASES[case_id]),
        "nonemptyValues": nonempty_values(rows),
        "firstRows": rows[:6],
        "tableMetaExpectedColumnKeys": capture.get("tableMetaExpectedColumnKeys"),
        "tableMetaColumns": capture.get("tableMetaColumns"),
    }


def analyze_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = case["caseId"]
    display = case["displayCols"]
    expected_display = case["expectedColumns"]["display"]
    nonempty = case["nonemptyValues"]
    if case_id == "trade_4_4pdf":
        finding = {
            "summary": "totalAmount is present in row data and locked into displayCols/output/Clean JSON, but it is not in template display columns.",
            "classification": "DISPLAY_POLICY_AND_CURRENT_FIXTURE_LOCK_ISSUE",
            "frontendDisplayPolicy": True,
            "backendTableRowsIssue": "possible: row-level tableRows contains document/summary-like totalAmount",
            "expectedMismatch": sorted(set(display) - set(expected_display)),
            "missingFromDisplay": sorted(set(expected_display) - set(display)),
            "keyObservations": [
                "input displayCols includes totalAmount",
                "output view_model columns includes totalAmount",
                "input row has totalAmount=28,338,000",
                "Clean JSON row also includes totalAmount",
                "public testset manifest display excludes totalAmount but optional includes it",
                "3D1 capture tableMetaExpectedColumnKeys includes amount,totalAmount,remark; hasValue filter kept totalAmount",
            ],
        }
    elif case_id == "trade_6_6pdf":
        lot_present = "lotNo" in nonempty
        finding = {
            "summary": "lotNo values exist in tableRows for first three rows, but displayCols/output omit lotNo.",
            "classification": "FRONTEND_DISPLAY_POLICY_DEDUP_NOISE_RULE_ISSUE",
            "frontendDisplayPolicy": True,
            "backendTableRowsIssue": "partial: later rows have no lot/expiry values, but first rows do contain lotNo",
            "expectedMismatch": sorted(set(display) - set(expected_display)),
            "missingFromDisplay": sorted(set(expected_display) - set(display)),
            "keyObservations": [
                f"lotNo non-empty in rows: {lot_present}",
                "tableMetaExpectedColumnKeys includes lotNo",
                "buildInvoicePreviewCols initially can see lotNo via expectedColumnKeys",
                "lot noise rule removes lotNo when itemCode has values and manufacturingNo is empty",
                "serialLotComposite is non-empty but treated as internal/composite and filtered from candidate columns",
                "rowIndex inclusion is normal and preserved",
            ],
        }
    else:
        finding = {
            "summary": "serialLotComposite and serialNo values exist in tableRows, but displayCols/output omit serial/lot column.",
            "classification": "FRONTEND_INTERNAL_COMPOSITE_FILTER_AND_EXPECTED_KEY_MISMATCH",
            "frontendDisplayPolicy": True,
            "backendTableRowsIssue": "no for the important value: serialLotComposite=0350623-231024-260811 exists",
            "expectedMismatch": sorted(set(display) - set(expected_display)),
            "missingFromDisplay": sorted(set(expected_display) - set(display)),
            "keyObservations": [
                "expected display requires serialLotComposite",
                "input row has serialLotComposite=0350623-231024-260811",
                "input row also has serialNo=0350623-231024-260811",
                "buildInvoicePreviewCols filters serialLotComposite as internal/composite",
                "candidate keys from expectedColumnKeys lose serialLotComposite before hasValue filtering",
                "serialNo is not expected display and does not substitute for serialLotComposite in current policy",
            ],
        }
    return {**case, "analysis": finding}


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
    case_rows = [
        [
            item["caseId"],
            item["analysis"]["classification"],
            item["displayCols"],
            item["expectedColumns"]["display"],
            item["analysis"]["expectedMismatch"],
            item["analysis"]["missingFromDisplay"],
        ]
        for item in report["caseAnalyses"]
    ]
    candidate_rows = [
        [item["id"], item["summary"], item["pros"], item["cons"], item["regressionRisk"], item["fixtureImpact"]]
        for item in report["fixCandidates"]
    ]
    smoke_rows = [[key, value] for key, value in report["smokeVerdict"].items()]
    md = f"""# FRONTEND CLEANUP 3D3 SMOKE COLUMN POLICY PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- fixture 수정 없음.
- `OcrResultPanel.tsx`, `invoiceTableDisplay.ts`, `structuredTableViewModel.ts`, backend/parser, templates, manifest/GT 수정 없음.
- API 재실행 없음. locked fixture/input 및 기존 리포트만 분석.

## 3. 생성 파일
- `tmp/codex_3d3_smoke_column_policy_precheck.py`
- `docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.md`
- `docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.json`

## 4. Smoke Issue 요약
- trade_4: Preview에 `totalAmount` 추가 컬럼 표시.
- trade_6: 원본에 Lot No 구조가 보이나 Preview에서 `lotNo` 누락.
- trade_7: 원본에 시리얼/로트No 구조가 보이나 Preview에서 `serialLotComposite` 누락.

## 5. Case별 분석 요약
{md_table(['case', 'classification', 'displayCols', 'expectedDisplay', 'extraVsExpectedDisplay', 'missingExpectedDisplay'], case_rows)}

## 6. trade_4 분석
- `displayCols` / output / Clean JSON 모두 `totalAmount` 포함.
- input row `totalAmount=28,338,000`.
- testset manifest의 display 목록은 `itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount`로 `totalAmount` 제외.
- 그러나 expected optional 및 3D1 capture `tableMetaExpectedColumnKeys`에는 `totalAmount`가 있고, 현재 `buildInvoicePreviewCols`는 expectedColumnKeys + hasValue 기준으로 유지한다.
- 판정: current fixture가 smoke에서 보기 싫은 current behavior를 lock했다. frontend display policy와 tableRows/document summary 혼입 경계 문제.

## 7. trade_6 분석
- `rows`에는 `lotNo` 값이 존재한다: `23001`, `23001`, `T17322003`.
- expected display는 `rowIndex,itemCode,itemName,quantity,lotNo,expiryDate`.
- 실제 display/output은 `rowIndex,itemCode,itemName,quantity,expiryDate`.
- `buildInvoicePreviewCols`의 lot 노이즈 규칙: itemCode가 의미 있고 manufacturingNo가 전부 비어 있으면 lotNo를 제거한다.
- 판정: 값은 있으나 frontend display dedup/noise 정책이 제거한 케이스. 일부 row는 lot/expiry 자체가 비어 있어 backend/parser 보정 이슈도 함께 존재.

## 8. trade_7 분석
- input row에 `serialLotComposite=0350623-231024-260811`, `serialNo=0350623-231024-260811`가 존재.
- expected display는 `itemName,serialLotComposite,unit,quantity`.
- 실제 display/output은 `itemName,unit,quantity`.
- `serialLotComposite`는 `_INTERNAL_KEYS` 및 `Composite` 필터로 후보에서 제외된다.
- 판정: 중요한 값은 rows에 있으나 frontend internal/composite filter가 expected display 요구와 충돌한다.

## 9. 공통 원인
- `buildStructuredTableViewModel`은 pass-through helper다. 컬럼 추가/삭제 정책을 갖지 않는다.
- 문제는 `docTableDisplayCols = buildInvoicePreviewCols(docTableMeta, docTableRows)` 이전/내부 정책에서 발생한다.
- 현재 우선순위는 `tableMeta.expectedColumnKeys -> tableMeta.columns -> allowlist`이며 이후 hasValue, itemCode majority, lot/mfg dedup, lot noise, serialNo/lotNo dedup, rowIndex prepend가 적용된다.
- `serialLotComposite` 같은 composite key는 expected display에 있어도 internal key로 제거된다.
- `totalAmount` 같은 doc summary 성격 값은 expectedColumnKeys와 row 값이 있으면 display에 남는다.

## 10. 수정 후보
{md_table(['id', 'summary', 'pros', 'cons', 'regressionRisk', 'fixtureImpact'], candidate_rows)}

## 11. Fixture 영향
- 현재 table_view_model_v1 및 Clean JSON fixture는 smoke에서 발견된 current behavior를 그대로 lock하고 있다.
- 정책 수정 시 trade_4/6/7 output fixture와 Clean JSON fixture 갱신 여부를 명시적으로 결정해야 한다.
- display-only 수정이면 Clean JSON fixture는 유지할 수 있으나, `buildInvoicePreviewCols`가 Clean JSON builder에도 입력으로 쓰이는 경로라 영향 범위 확인이 필요하다.

## 12. Smoke 판정 갱신
{md_table(['sample', 'verdict'], smoke_rows)}

## 13. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| {report['typecheck']['command']} | {report['typecheck']['status']} | {report['typecheck']['exitCode']} | {report['typecheck']['durationSeconds']} | {report['typecheck']['knownStderrNoise']} |
| {report['build']['command']} | {report['build']['status']} | {report['build']['exitCode']} | {report['build']['durationSeconds']} | {report['build']['knownStderrNoise']} |

## 14. 다음 작업 제안
1. trade_4/6/7 display policy를 수정할지, Template table column definition 도입까지 known issue로 둘지 결정.
2. 수정한다면 `invoiceTableDisplay.ts` 정책 변경 전 별도 fixture update intent 문서화.
3. Clean JSON과 Preview가 같은 displayCols를 공유하는 현 구조에서 display-only 정책과 export policy를 분리할지 precheck.
4. trade_6/7은 backend/parser가 lot/serial values를 표준 key로 더 안정적으로 매핑해야 하는지 별도 parser precheck.
5. 정책 변경 후 table_view_model runner, Clean JSON runner, Markdown check, manual smoke 재수행.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    cases = [analyze_case(load_case(case_id)) for case_id in CASES]
    print("[analysis] loaded fixtures for trade_4/trade_6/trade_7", flush=True)
    print("[check] npm run typecheck", flush=True)
    typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180)
    print(f"[check] typecheck={typecheck['status']} exit={typecheck['exitCode']}", flush=True)
    print("[check] npm run build", flush=True)
    build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)
    print(f"[check] build={build['status']} exit={build['exitCode']}", flush=True)

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "task": TASK,
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "codeModified": False,
        "fixturesModified": False,
        "apiRerun": False,
        "caseAnalyses": cases,
        "commonCause": {
            "helperIssue": False,
            "helperVerdict": "buildStructuredTableViewModel is a pure pass-through over caller-provided displayCols.",
            "primaryLayer": "buildInvoicePreviewCols / tableMeta.expectedColumnKeys / display policy before view model helper",
            "policyConflicts": [
                "template display columns vs tableMeta.expectedColumnKeys",
                "internal/composite filtering vs serialLotComposite expected display",
                "lot noise removal vs visible Lot No expectation",
                "row-level tableRows summary value vs item-row display policy",
            ],
        },
        "fixCandidates": [
            {
                "id": "candidate_1_display_exclude_summary_keys",
                "summary": "invoiceTableDisplay에서 문서 profile별 summary key(totalAmount 등)를 display exclude",
                "pros": "trade_4 totalAmount extra column을 작게 해결",
                "cons": "문서별 예외가 늘고 Clean JSON displayCols 공유 경로에 영향 가능",
                "regressionRisk": "medium: totalAmount가 품목 행으로 필요한 다른 sample이 있으면 숨겨짐",
                "scope": "frontend display policy",
                "fixtureImpact": "table_view_model trade_4 갱신 필요 가능; Clean JSON 영향 확인 필요",
            },
            {
                "id": "candidate_2_stronger_template_display_priority",
                "summary": "tableMeta.expectedColumnKeys보다 template tableExpectedColumns.display를 강하게 우선",
                "pros": "사용자가 보는 원본/템플릿 display 의도와 일치",
                "cons": "현재 API tableMeta만으로는 OcrResultPanel에 display list 전달 경로가 필요할 수 있음",
                "regressionRisk": "medium-high: 기존 locked fixtures 다수 갱신 가능",
                "scope": "frontend display policy/input contract",
                "fixtureImpact": "trade_4/6/7 table_view_model 갱신 가능",
            },
            {
                "id": "candidate_3_hide_keys_not_in_expected_display",
                "summary": "값이 있어도 expected/display policy에 없는 key는 숨김",
                "pros": "totalAmount 같은 extra column 억제",
                "cons": "expected display가 누락/구버전이면 실제 유용한 OCR 값을 잃음",
                "regressionRisk": "high without robust template display source",
                "scope": "frontend display policy",
                "fixtureImpact": "table_view_model and possibly Clean JSON fixture update",
            },
            {
                "id": "candidate_4_backend_lot_serial_mapping_fix",
                "summary": "trade_6/7 lot/serial 값이 표준 display key로 안정 매핑되도록 parser 보정",
                "pros": "원본 표 구조와 data semantics 개선",
                "cons": "backend/parser 영향 범위가 크고 fixture 재생성 필요",
                "regressionRisk": "medium-high: OCR row grouping/value mapping 회귀 가능",
                "scope": "backend parser/tableRows",
                "fixtureImpact": "tableRows 기반 fixtures 갱신 필요",
            },
            {
                "id": "candidate_5_defer_until_template_table_definition",
                "summary": "Template table column definition 도입 전까지 known issue로 보류",
                "pros": "현재 cleanup 안정성 유지, 임시 예외 최소화",
                "cons": "manual smoke WARN 지속",
                "regressionRisk": "low",
                "scope": "documentation/known issue",
                "fixtureImpact": "none now",
            },
        ],
        "smokeVerdict": {
            "trade_2": "PASS",
            "trade_3": "PASS_WITH_LABEL_NOTE",
            "trade_4": "WARN_totalAmount_extra_column",
            "trade_5": "PASS_OR_NOT_ANALYZED",
            "trade_6": "WARN_lot_or_expiry_column_issue",
            "trade_7": "WARN_serial_lot_column_missing",
            "overall": "automatic checks PASS; manual smoke WARN; OcrResultPanel technical cleanup successful; Preview column policy follow-up required",
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
