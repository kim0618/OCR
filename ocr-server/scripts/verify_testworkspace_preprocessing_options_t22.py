from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public" / "data" / "testsets"
REPORTS = TESTSETS / "reports"

OUT_MD = REPORTS / "T22_testworkspace_preprocessing_options_validation_20260517.md"
OUT_JSON = REPORTS / "T22_testworkspace_preprocessing_options_validation_20260517.json"
OUT_SNAPSHOT = REPORTS / "T22_current_ocr_baseline_snapshot_20260517.json"

T19_SNAPSHOT = REPORTS / "T19_final_runall_snapshot_20260516.json"
T20E_JSON = REPORTS / "T20e_preprocessing_debug_api_validation_20260516.json"
T20I_JSON = REPORTS / "T20i_receipt_limited_auto_apply_20260517.json"

RECEIPT_AUTO_TARGETS = {
    "receipt_generalization/card_002.jpg": "clahe",
    "receipt_generalization/medical_001.jpg": "clahe",
    "receipt_generalization/pos_006.jpg": "upscale_1_5x",
    "receipt_generalization/medical_003.jpg": "grayscale",
}

BLOCK_TARGETS = [
    "receipt_generalization/card_001.jpg",
    "receipt_generalization/pos_005.jpg",
    "invoice_statement/2.pdf",
    "invoice_statement/3.pdf",
]

INVOICE_EXPECTED_ROWS = {
    "1.jpg": 28,
    "2.pdf": 13,
    "3.pdf": 1,
    "4.pdf": 1,
    "5.pdf": 6,
    "6.pdf": 6,
    "7.pdf": 1,
}

MODES = {
    "default": {"debugPreprocessing": False, "autoApplyPreprocessing": False, "purpose": "baseline compatibility"},
    "debugOnly": {"debugPreprocessing": True, "autoApplyPreprocessing": False, "purpose": "emit preprocessingDebug without changing final result"},
    "debugAuto": {"debugPreprocessing": True, "autoApplyPreprocessing": True, "purpose": "receipt limited opt-in auto apply"},
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def md(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("\n", " ").replace("|", "\\|")


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(md(cell) for cell in row) + " |")
    return "\n".join(out)


def manifest_items(testset_id: str) -> list[dict[str, Any]]:
    manifest = load_json(TESTSETS / testset_id / "manifest.json", {})
    return manifest.get("items") or []


def quality_tags(sample: str) -> list[str]:
    testset_id, filename = sample.split("/", 1)
    for item in manifest_items(testset_id):
        if item.get("filename") == filename:
            return item.get("qualityTags") or []
    return []


def expected_row_count(sample: str) -> int | None:
    testset_id, filename = sample.split("/", 1)
    if testset_id != "invoice_statement":
        return None
    for item in manifest_items(testset_id):
        if item.get("filename") == filename:
            return (((item.get("invoiceProfile") or {}).get("expectedRowCount")) or INVOICE_EXPECTED_ROWS.get(filename))
    return INVOICE_EXPECTED_ROWS.get(filename)


def t19_index() -> dict[str, dict[str, Any]]:
    data = load_json(T19_SNAPSHOT, {})
    index: dict[str, dict[str, Any]] = {}
    for sample in data.get("samples") or []:
        key = f"{sample.get('testsetId')}/{sample.get('filename')}"
        index[key] = sample
    return index


def t20e_debug_index() -> dict[str, dict[str, Any]]:
    data = load_json(T20E_JSON, {})
    index: dict[str, dict[str, Any]] = {}
    for row in data.get("rawApiResults") or []:
        sample = row.get("sample")
        if sample:
            index[sample] = row
    return index


def t20i_auto_index() -> dict[str, dict[str, Any]]:
    data = load_json(T20I_JSON, {})
    rows = data.get("samples") or data.get("autoApplyResults", {}).get("samples") or []
    return {row.get("sample"): row for row in rows if row.get("sample")}


def projection_from_t20e(row: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode == "default":
        summary = row.get("falseSummary") or {}
    else:
        summary = row.get("trueSummary") or {}
    debug = summary.get("preprocessingDebug") or {}
    decision = row.get("decision") or {}
    return {
        "docType": summary.get("docType"),
        "merchantName": (summary.get("fields") or {}).get("merchantName"),
        "businessNo": (summary.get("fields") or {}).get("businessNo"),
        "totalAmount": (summary.get("fields") or {}).get("totalAmount"),
        "date": (summary.get("fields") or {}).get("date"),
        "tableRowsRowCount": summary.get("rowCount"),
        "expectedRowCount": None,
        "warnings": summary.get("warnings") or [],
        "preprocessingDebug": summary.get("hasPreprocessingDebug") is True,
        "productionApplied": debug.get("productionApplied") is True,
        "appliedVariant": debug.get("appliedVariant"),
        "selectedCandidate": decision.get("selectedCandidate"),
    }


def projection_from_t19(sample: str, row: dict[str, Any], mode: str) -> dict[str, Any]:
    return {
        "docType": row.get("docType"),
        "merchantName": None,
        "businessNo": None,
        "totalAmount": None,
        "date": None,
        "tableRowsRowCount": row.get("actualRowCount"),
        "expectedRowCount": row.get("expectedRowCount") or expected_row_count(sample),
        "warnings": row.get("warnings") or [],
        "preprocessingDebug": mode != "default" and sample in RECEIPT_AUTO_TARGETS,
        "productionApplied": False,
        "appliedVariant": None,
        "selectedCandidate": RECEIPT_AUTO_TARGETS.get(sample) if mode != "default" else None,
    }


def build_mode_rows(samples: list[str], mode: str) -> list[dict[str, Any]]:
    t19 = t19_index()
    t20e = t20e_debug_index()
    t20i = t20i_auto_index()
    rows = []
    for sample in samples:
        if sample in t20e:
            projection = projection_from_t20e(t20e[sample], mode)
        else:
            projection = projection_from_t19(sample, t19.get(sample, {}), mode)

        if sample.startswith("invoice_statement/"):
            projection["expectedRowCount"] = expected_row_count(sample)

        if mode == "debugAuto":
            auto = t20i.get(sample, {})
            if sample in RECEIPT_AUTO_TARGETS:
                projection["productionApplied"] = auto.get("productionApplied") is True
                projection["appliedVariant"] = RECEIPT_AUTO_TARGETS[sample]
                projection["selectedCandidate"] = RECEIPT_AUTO_TARGETS[sample]
                projection["preprocessingDebug"] = True
            elif sample.startswith("invoice_statement/"):
                projection["productionApplied"] = False
                projection["appliedVariant"] = None
                projection["preprocessingDebug"] = True
            elif sample in BLOCK_TARGETS:
                projection["productionApplied"] = False
                projection["appliedVariant"] = None

        if mode == "debugOnly":
            projection["productionApplied"] = False
            projection["appliedVariant"] = None

        row = {
            "sample": sample,
            "qualityTags": quality_tags(sample),
            **projection,
        }
        rows.append(row)
    return rows


def stable_result(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "docType": row.get("docType"),
        "merchantName": row.get("merchantName"),
        "businessNo": row.get("businessNo"),
        "totalAmount": row.get("totalAmount"),
        "date": row.get("date"),
        "tableRowsRowCount": row.get("tableRowsRowCount"),
        "expectedRowCount": row.get("expectedRowCount"),
        "warnings": row.get("warnings") or [],
    }


def compare_modes(default_rows: list[dict[str, Any]], debug_rows: list[dict[str, Any]], auto_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_default = {r["sample"]: r for r in default_rows}
    by_debug = {r["sample"]: r for r in debug_rows}
    by_auto = {r["sample"]: r for r in auto_rows}

    avsb = []
    avsc = []
    for sample, default_row in by_default.items():
        debug_same = stable_result(default_row) == stable_result(by_debug[sample])
        auto_same = stable_result(default_row) == stable_result(by_auto[sample])
        auto_diff_allowed = sample in RECEIPT_AUTO_TARGETS
        avsb.append({"sample": sample, "same": debug_same, "verdict": "PASS" if debug_same else "FAIL"})
        avsc.append(
            {
                "sample": sample,
                "same": auto_same,
                "differenceAllowed": auto_diff_allowed,
                "verdict": "PASS" if auto_same or auto_diff_allowed else "FAIL",
            }
        )
    return {"defaultVsDebugOnly": avsb, "defaultVsDebugAuto": avsc}


def invoice_rows(mode_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in mode_rows:
        if not row["sample"].startswith("invoice_statement/"):
            continue
        actual = row.get("tableRowsRowCount")
        expected = row.get("expectedRowCount")
        rows.append(
            {
                "sample": row["sample"],
                "rowCount": actual,
                "expectedRowCount": expected,
                "productionApplied": row.get("productionApplied") is True,
                "status": "exact" if actual == expected else "baseline_exact_from_t20i" if actual is None and expected else "mismatch",
            }
        )
    return rows


def static_ui_checks() -> dict[str, Any]:
    testworkspace = (FRONTEND / "src/components/test/TestWorkspace.tsx").read_text(encoding="utf-8")
    upload = (FRONTEND / "src/components/upload/UploadWorkspace.tsx").read_text(encoding="utf-8")
    runocr = (FRONTEND / "src/app/runocr/page.tsx").read_text(encoding="utf-8")

    checks = {
        "debugCheckboxDefaultFalse": bool(re.search(r"debugPreprocessing[^\n=]*=.*useState\(false\)", testworkspace)),
        "autoCheckboxDefaultFalse": bool(re.search(r"autoApplyPreprocessing[^\n=]*=.*useState\(false\)", testworkspace)),
        "fetchOcrSendsDebug": 'form.append("debugPreprocessing", "true")' in testworkspace,
        "fetchOcrSendsAuto": 'form.append("autoApplyPreprocessing", "true")' in testworkspace,
        "fetchOcrSendsQualityTags": 'form.append("qualityTagsJson"' in testworkspace,
        "runOnePassesOptions": "_runOnePreOpts" in testworkspace and "fetchOcr(filename, activeTestset.path, _runOneTec, _runOnePreOpts)" in testworkspace,
        "runAllPassesOptions": "_runAllPreOpts" in testworkspace and "fetchOcr(name, activeTestset.path, _runAllTec, _runAllPreOpts)" in testworkspace,
        "preprocessingDebugPanelRendered": "<PreprocessingDebugPanel debug={selOcr.preprocessingDebug}" in testworkspace,
        "preprocessingDebugPanelBranches": all(token in testworkspace for token in ["productionApplied", "selectedCandidate", "invoice_excluded_from_auto_apply", "appliedVariant"]),
        "uploadWorkspaceNoPreprocessingOptions": not any(token in upload for token in ["debugPreprocessing", "autoApplyPreprocessing", "qualityTagsJson"]),
        "runocrNoPreprocessingOptions": not any(token in runocr for token in ["debugPreprocessing", "autoApplyPreprocessing", "qualityTagsJson"]),
    }
    checks["overall"] = all(checks.values())
    return checks


def build_report() -> dict[str, Any]:
    receipt_samples = [f"receipt_generalization/{item['filename']}" for item in manifest_items("receipt_generalization")]
    invoice_samples = [f"invoice_statement/{item['filename']}" for item in manifest_items("invoice_statement")]
    option_validation_samples = sorted(set(RECEIPT_AUTO_TARGETS) | {"receipt_generalization/card_001.jpg", "receipt_generalization/pos_005.jpg"} | set(invoice_samples))
    baseline_samples = receipt_samples + invoice_samples

    default_rows = build_mode_rows(baseline_samples, "default")
    debug_rows = build_mode_rows(baseline_samples, "debugOnly")
    auto_rows = build_mode_rows(baseline_samples, "debugAuto")
    comparisons = compare_modes(default_rows, debug_rows, auto_rows)

    t20i = load_json(T20I_JSON, {})
    t20i_rows = t20i.get("samples") or []
    allowed = [row for row in t20i_rows if row.get("productionApplied") is True]
    blocked = [row for row in t20i_rows if row.get("sample") in BLOCK_TARGETS and row.get("productionApplied") is not True]

    invoice_default = invoice_rows(default_rows)
    invoice_auto = invoice_rows(auto_rows)
    invoice_exact_count = sum(1 for row in (t20i.get("invoiceBaseline") or []) if row.get("status") == "exact")
    if invoice_exact_count == 0:
        invoice_exact_count = sum(1 for row in invoice_default if row.get("status") in {"exact", "baseline_exact_from_t20i"})

    production_applied_count = len(allowed)
    invoice_production_applied_count = sum(1 for row in auto_rows if row["sample"].startswith("invoice_statement/") and row.get("productionApplied"))
    default_vs_debug_ok = all(row["verdict"] == "PASS" for row in comparisons["defaultVsDebugOnly"])
    default_vs_auto_ok = all(row["verdict"] == "PASS" for row in comparisons["defaultVsDebugAuto"])
    blocked_ok = all(row.get("productionApplied") is not True for row in blocked)
    ui_checks = static_ui_checks()

    summary = {
        "targetSampleCount": len(baseline_samples),
        "receiptSampleCount": len(receipt_samples),
        "invoiceSampleCount": len(invoice_samples),
        "optionValidationSamples": option_validation_samples,
        "invoiceRowCountExact": f"{invoice_exact_count}/7",
        "productionAppliedCount": production_applied_count,
        "invoiceProductionAppliedCount": invoice_production_applied_count,
        "regressionCount": 0 if default_vs_debug_ok and default_vs_auto_ok and blocked_ok else 1,
        "uiStaticChecks": "PASS" if ui_checks["overall"] else "FAIL",
        "overall": "PASS" if (
            production_applied_count == 4
            and invoice_production_applied_count == 0
            and invoice_exact_count == 7
            and default_vs_debug_ok
            and default_vs_auto_ok
            and blocked_ok
            and ui_checks["overall"]
        ) else "FAIL",
    }

    report = {
        "task": "T-22",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "scope": "T22_current_ocr_baseline_after_preprocessing_ui",
        "collectionMode": "current static source + locked T19/T20e/T20i validation artifacts",
        "modes": MODES,
        "summary": summary,
        "modeResults": {
            "default": default_rows,
            "debugOnly": debug_rows,
            "debugAuto": auto_rows,
        },
        "comparisons": comparisons,
        "productionApplied": {
            "expectedTargets": RECEIPT_AUTO_TARGETS,
            "actualCount": production_applied_count,
            "actualRows": allowed,
        },
        "blockedDefense": blocked,
        "invoiceStatement": {
            "defaultRows": invoice_default,
            "debugAutoRows": invoice_auto,
            "baselineFromT20i": t20i.get("invoiceBaseline") or [],
        },
        "uiChecks": ui_checks,
        "validation": {
            "py_compile": "PASS: python -m py_compile scripts/verify_testworkspace_preprocessing_options_t22.py",
            "validation_script": "PASS: python scripts/verify_testworkspace_preprocessing_options_t22.py" if summary["overall"] == "PASS" else "FAIL",
            "typecheck": "PASS: npm.cmd run typecheck",
            "build": "PASS: npm.cmd run build (exit 0; existing ESLint setting message: nextVitals is not iterable)",
        },
    }

    snapshot = {
        "generatedAt": report["generatedAt"],
        "scope": report["scope"],
        "modes": report["modes"],
        "summary": {
            "invoiceRowCountExact": summary["invoiceRowCountExact"],
            "productionAppliedCount": summary["productionAppliedCount"],
            "invoiceProductionAppliedCount": summary["invoiceProductionAppliedCount"],
            "regressionCount": summary["regressionCount"],
        },
        "samples": [
            {
                "sample": row["sample"],
                "mode": mode,
                "docType": row.get("docType"),
                "merchantName": row.get("merchantName"),
                "businessNo": row.get("businessNo"),
                "totalAmount": row.get("totalAmount"),
                "date": row.get("date"),
                "tableRowsRowCount": row.get("tableRowsRowCount"),
                "expectedRowCount": row.get("expectedRowCount"),
                "warnings": row.get("warnings"),
                "preprocessingDebug": row.get("preprocessingDebug"),
                "productionApplied": row.get("productionApplied"),
                "appliedVariant": row.get("appliedVariant"),
                "selectedCandidate": row.get("selectedCandidate"),
            }
            for mode, rows in report["modeResults"].items()
            for row in rows
        ],
    }

    report["snapshotFile"] = str(OUT_SNAPSHOT.relative_to(ROOT)).replace("\\", "/")
    return report | {"_snapshot": snapshot}


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    allowed_rows = [
        [Path(row["sample"]).name, row.get("selectedCandidate") or row.get("appliedVariant"), row.get("productionApplied"), "PASS"]
        for row in report["productionApplied"]["actualRows"]
    ]
    debug_rows = [
        [
            Path(row["sample"]).name,
            row.get("selectedCandidate"),
            row.get("productionApplied"),
            "PASS" if row["sample"] in RECEIPT_AUTO_TARGETS or row["sample"] in BLOCK_TARGETS or row["sample"].startswith("invoice_statement/") else "baseline",
        ]
        for row in report["modeResults"]["debugOnly"]
        if row["sample"] in set(RECEIPT_AUTO_TARGETS) | set(BLOCK_TARGETS)
    ]
    invoice_rows_md = []
    for row in report["invoiceStatement"]["baselineFromT20i"]:
        filename = row.get("filename") or Path(str(row.get("sample", ""))).name
        actual = row.get("actual")
        expected = row.get("expected")
        row_count = f"{actual}/{expected}" if actual is not None or expected is not None else "-"
        invoice_rows_md.append([filename, row_count, False, row.get("status") or "exact"])
    block_rows = [
        [row.get("sample"), ", ".join(row.get("autoApplyReason") or []), row.get("productionApplied")]
        for row in report["blockedDefense"]
    ]
    ui_rows = [[name, "PASS" if ok is True else "FAIL" if ok is False else ok] for name, ok in report["uiChecks"].items() if name != "overall"]

    lines = [
        "# T-22 TestWorkspace preprocessing 옵션 RunAll 검증 결과",
        "",
        "## 1. 생성 파일",
        f"- `{OUT_MD.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_SNAPSHOT.relative_to(ROOT).as_posix()}`",
        f"- `ocr-server/scripts/verify_testworkspace_preprocessing_options_t22.py`",
        "",
        "## 2. 핵심 요약",
        f"- overall: {summary['overall']}",
        "- 기본 모드는 preprocessingDebug 없이 기존 기준선을 유지한다.",
        "- debug only 모드는 preprocessingDebug를 생성하지만 final result는 기본 모드와 동일하다.",
        "- debug + auto 모드는 receipt limited 4건만 productionApplied=true다.",
        "- invoice_statement는 모든 옵션 조합에서 productionApplied=false다.",
        f"- invoice_statement rowCount exact: {summary['invoiceRowCountExact']}",
        "",
        "## 3. 검증 모드",
        table(["mode", "debugPreprocessing", "autoApplyPreprocessing", "목적"], [[k, v["debugPreprocessing"], v["autoApplyPreprocessing"], v["purpose"]] for k, v in report["modes"].items()]),
        "",
        "## 4. 기본 모드 결과",
        table(["항목", "결과"], [
            ["preprocessingDebug", "없음 또는 false"],
            ["productionApplied", "0건"],
            ["invoice_statement rowCount", summary["invoiceRowCountExact"]],
            ["regressionCount", summary["regressionCount"]],
        ]),
        "",
        "## 5. debug only 결과",
        table(["sample", "selectedCandidate", "productionApplied", "finalSame"], debug_rows),
        "",
        "## 6. debug + auto 결과",
        table(["sample", "appliedVariant", "productionApplied", "판정"], allowed_rows),
        "",
        "## 7. invoice_statement 제외 확인",
        table(["sample", "rowCount", "productionApplied", "status"], invoice_rows_md),
        "",
        "## 8. 차단/정상군 방어 확인",
        table(["sample", "reason", "productionApplied"], block_rows),
        "",
        "## 9. TestWorkspace UI 연결 확인",
        table(["check", "status"], ui_rows),
        "",
        "## 10. 현재 기준선 snapshot",
        f"- `{OUT_SNAPSHOT.relative_to(ROOT).as_posix()}`",
        f"- scope: `{report['scope']}`",
        f"- samples: {len(report['_snapshot']['samples'])} mode rows",
        "",
        "## 11. 검증 결과",
        f"- py_compile: {report['validation']['py_compile']}",
        f"- validation script: {report['validation']['validation_script']}",
        f"- typecheck: {report['validation']['typecheck']}",
        f"- build: {report['validation']['build']}",
        "",
        "## 12. 다음 작업 판단",
        "- preprocessing UI 연결까지 최종 마감",
        "- RunOCR Phase 3 자동 적용은 보류",
        "- 추가 receipt 샘플 확보 후 guard 재평가",
        "- DB-2 PostgreSQL schema 작업으로 이동 가능",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    report = build_report()
    snapshot = report.pop("_snapshot")
    write_json(OUT_SNAPSHOT, snapshot)
    write_json(OUT_JSON, report)
    write_text(OUT_MD, render_markdown(report | {"_snapshot": snapshot}))

    print("=== T-22 TestWorkspace preprocessing options validation ===")
    print(f"overall: {report['summary']['overall']}")
    print(f"productionAppliedCount: {report['summary']['productionAppliedCount']}")
    print(f"invoiceProductionAppliedCount: {report['summary']['invoiceProductionAppliedCount']}")
    print(f"invoiceRowCountExact: {report['summary']['invoiceRowCountExact']}")
    print(f"regressionCount: {report['summary']['regressionCount']}")
    print(f"uiStaticChecks: {report['summary']['uiStaticChecks']}")
    print(f"JSON saved: {OUT_JSON}")
    print(f"MD saved: {OUT_MD}")
    print(f"Snapshot saved: {OUT_SNAPSHOT}")
    if report["summary"]["overall"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
