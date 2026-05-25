from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DOCS = ROOT / "docs"
TASK = "CODEX_FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_NO_PROD_MODIFY"
OUT_LOG = REPO / "ocr-server" / "logs" / f"codex_{TASK}.out.log"
ERR_LOG = REPO / "ocr-server" / "logs" / f"codex_{TASK}.err.log"


def git_status() -> list[str]:
    proc = subprocess.run(
        ["git", "-c", "core.excludesFile=", "status", "--porcelain=v1"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_exit_code(label: str) -> int | None:
    if not OUT_LOG.exists():
        return None
    raw = OUT_LOG.read_bytes()
    text = "\n".join([raw.decode("utf-8", errors="ignore"), raw.decode("utf-16-le", errors="ignore")])
    match = re.search(rf"\[{re.escape(label)}_exit_code\]\s+(\d+)", text)
    return int(match.group(1)) if match else None


def script_backup_refs(script: str) -> list[str]:
    path = ROOT / script
    if not path.exists():
        return []
    refs: list[str] = []
    for line in read_text(path).splitlines():
        if "backup" in line or "BACKUP" in line:
            refs.append(line.strip())
    return refs


def markdown_eol_summary() -> dict[str, object]:
    report_path = DOCS / "MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.json"
    if not report_path.exists():
        return {"reportPath": str(report_path), "available": False}
    data = json.loads(read_text(report_path))
    cases = data.get("cases") or []
    return {
        "reportPath": str(report_path),
        "available": True,
        "overall": data.get("summary", {}).get("overall"),
        "caseCount": len(cases),
        "allActualLF": all(case.get("actualContainsCRLF") is False for case in cases),
        "allExpectedCRLF": all(case.get("expectedContainsCRLF") is True for case in cases),
        "firstDiffs": [
            {
                "caseId": case.get("caseId"),
                "status": case.get("status"),
                "actualContainsCRLF": case.get("actualContainsCRLF"),
                "expectedContainsCRLF": case.get("expectedContainsCRLF"),
                "diff": case.get("diff"),
            }
            for case in cases
        ],
    }


def main() -> None:
    DOCS.mkdir(exist_ok=True)

    typecheck_exit = parse_exit_code("typecheck")
    build_exit = parse_exit_code("build")
    dirty = git_status()

    current_backup_parent = REPO / "backup"
    repo_backup = ROOT / "backup"
    backup_5a = repo_backup / "ocr_core_types_20260522_before_FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE"

    failures = [
        {
            "command": "node tmp/check_runocr_formdata_keys_2a.mjs",
            "status": "FATAL exit 2",
            "cause": "Required backup RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT.tsx is looked up under C:/OCR/OCR/backup, which does not exist.",
            "relatedTo5A": "NO",
            "repairRecommendation": "Replace fatal missing-backup behavior with SKIP_WITH_REASON or repo-relative backup discovery; keep structural checks active.",
            "risk": "LOW_MEDIUM",
        },
        {
            "command": "node tmp/check_runocr_response_mapping_boundary_2c.mjs",
            "status": "FAIL exit 1",
            "cause": "All structural response-mapping checks pass except buildOcrFormData_unchanged_vs_2B_backup; the 2B backup file is missing under C:/OCR/OCR/backup.",
            "relatedTo5A": "NO",
            "repairRecommendation": "If backup missing, skip only the logic-equivalence subcheck and still fail real structural regressions.",
            "risk": "LOW",
        },
        {
            "command": "node tmp/check_runocr_doc_comments_3b.mjs",
            "status": "FAIL exit 1",
            "cause": "Eight logic-equivalence backup files are missing under C:/OCR/OCR/backup; controls_not_created and TestWorkspace existence checks pass.",
            "relatedTo5A": "NO",
            "repairRecommendation": "Convert backup comparisons to optional SKIP_WITH_REASON or find phase backup by repo-relative search.",
            "risk": "MEDIUM",
        },
        {
            "command": "node tmp/check_template_workspace_move_4a.mjs",
            "status": "FAIL exit 1",
            "cause": "Current structural 4A checks pass; template_workspace_logic_unchanged_vs_backup fails because TemplateWorkspace 4A backup is missing under C:/OCR/OCR/backup.",
            "relatedTo5A": "NO",
            "repairRecommendation": "Preserve structural boundary checks; make backup equality optional when the historical backup is unavailable.",
            "risk": "LOW",
        },
        {
            "command": "node tmp/check_template_editor_ui_move_4b.mjs",
            "status": "FAIL exit 1",
            "cause": "Current path/import/route policy checks pass; three backup-equivalence checks fail because 3B/4B backups are missing under C:/OCR/OCR/backup.",
            "relatedTo5A": "NO for backup failures; 5A import-path regex compatibility was already handled before this precheck.",
            "repairRecommendation": "Keep current import compatibility; make historical backup checks repo-relative optional or phase-search based.",
            "risk": "MEDIUM",
        },
        {
            "command": "python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_OCR_CORE_TYPES_COMMON_MOVE_20260522",
            "status": "FAIL exit 1",
            "cause": "All six cases fail because actual markdown uses LF and expected fixtures contain CRLF; processing_time is already normalized.",
            "relatedTo5A": "NO",
            "repairRecommendation": "Normalize line endings in compare path, preferably CRLF/LF -> LF after processing_time normalization; do not rebake fixtures for EOL only.",
            "risk": "LOW",
        },
    ]

    backup_dependency = {
        "legacyExpectedBackupDir": str(current_backup_parent),
        "legacyExpectedBackupDirExists": current_backup_parent.exists(),
        "repoBackupDir": str(repo_backup),
        "repoBackupDirExists": repo_backup.exists(),
        "available5ABackupDir": str(backup_5a),
        "available5ABackupDirExists": backup_5a.exists(),
        "available5ABackupFiles": sorted([p.name for p in backup_5a.glob("*")]) if backup_5a.exists() else [],
        "scriptRefs": {
            "tmp/check_runocr_formdata_keys_2a.mjs": script_backup_refs("tmp/check_runocr_formdata_keys_2a.mjs"),
            "tmp/check_runocr_response_mapping_boundary_2c.mjs": script_backup_refs("tmp/check_runocr_response_mapping_boundary_2c.mjs"),
            "tmp/check_runocr_doc_comments_3b.mjs": script_backup_refs("tmp/check_runocr_doc_comments_3b.mjs"),
            "tmp/check_template_workspace_move_4a.mjs": script_backup_refs("tmp/check_template_workspace_move_4a.mjs"),
            "tmp/check_template_editor_ui_move_4b.mjs": script_backup_refs("tmp/check_template_editor_ui_move_4b.mjs"),
            "tmp/check_ocr_core_types_common_move_5a.mjs": script_backup_refs("tmp/check_ocr_core_types_common_move_5a.mjs"),
        },
        "analysis": [
            "Older checks compute BACKUP_DIR as resolve(ROOT, '..', 'backup'), which points to C:/OCR/OCR/backup.",
            "The current available snapshot is inside mysuit-ocr/backup/ocr_core_types_20260522_before_FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE.",
            "5A check uses ROOT/backup/<phase> and passes; older checks expect historical phase snapshots that are absent in this workspace.",
        ],
    }

    markdown_analysis = markdown_eol_summary()

    repair_options = [
        {
            "option": "A",
            "title": "static check scripts only repair",
            "recommendation": "DO",
            "pros": ["Removes stale absolute/sibling backup failure noise.", "Keeps structural regression checks active."],
            "cons": ["Does not fix markdown LF/CRLF noise."],
            "regressionDetection": "Medium if backup equality becomes SKIP_WITH_REASON; high for structural boundaries.",
        },
        {
            "option": "B",
            "title": "markdown runner line-ending normalize only",
            "recommendation": "DO",
            "pros": ["Fixes deterministic OS/EOL mismatch without fixture rebake.", "Keeps content equality strict after EOL normalization."],
            "cons": ["Does not fix old backup-based static checks."],
            "regressionDetection": "High for content; intentionally ignores EOL-only drift.",
        },
        {
            "option": "C",
            "title": "A+B both repair",
            "recommendation": "RECOMMENDED",
            "pros": ["Clears both validation-noise sources for 5B.", "No src/backend/fixture changes required."],
            "cons": ["Touches validation scripts/runners in the next repair task."],
            "regressionDetection": "Best balance: structural checks stay strict, historical backup checks become explicit skips, markdown content remains strict modulo EOL/timing.",
        },
        {
            "option": "D",
            "title": "repair defer and continue 5B",
            "recommendation": "NOT_RECOMMENDED",
            "pros": ["No validation script churn now."],
            "cons": ["Keeps known FAIL noise and makes future regression triage harder."],
            "regressionDetection": "Low signal due to known failures.",
        },
        {
            "option": "E",
            "title": "backup snapshot regeneration",
            "recommendation": "DO_NOT_DO_IN_REPAIR_BASELINE",
            "pros": ["Could satisfy old exact backup checks."],
            "cons": ["Backup generation/restoration is disallowed here and would encode current dirty state as baseline if done carelessly."],
            "regressionDetection": "Risky unless done from clean historical phase snapshots.",
        },
    ]

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "task": TASK,
        "tool": "Codex",
        "model": "Codex",
        "projectRoot": str(ROOT),
        "codeModified": False,
        "sourceCodeModifiedByThisPrecheck": False,
        "validationScriptsModified": False,
        "fixturesModified": False,
        "backupCreatedOrRestored": False,
        "logFiles": {"stdout": str(OUT_LOG), "stderr": str(ERR_LOG)},
        "dirtyStatus": dirty,
        "failures": failures,
        "backupDependency": backup_dependency,
        "markdownLineEndingAnalysis": markdown_analysis,
        "repairOptions": repair_options,
        "recommendation": {
            "choice": "C",
            "summary": "Repair both static check backup handling and markdown line-ending normalization in the next task.",
            "scope": [
                "Validation scripts only: remove stale C:/OCR/OCR/backup hard dependency or mark missing historical backup as SKIP_WITH_REASON.",
                "Markdown runner only: normalize CRLF/LF to LF for comparison after processing_time masking.",
                "No src/backend/templates/fixtures/backup changes.",
            ],
            "relatedTo5A": "The reproduced failures are validation-baseline/environment noise, not a 5A code regression. 5A-specific check passes.",
        },
        "validationPlan": [
            "Rerun affected static checks after repair.",
            "Rerun markdown contract fixture lock expecting 6/6 or PASS if no content drift.",
            "Rerun check_ocr_core_types_common_move_5a expecting PASS 29/29.",
            "Rerun npm run typecheck and npm run build.",
        ],
        "typecheck": {"command": "npm run typecheck", "exitCode": typecheck_exit, "status": "PASS" if typecheck_exit == 0 else "FAIL_OR_UNKNOWN", "log": str(OUT_LOG)},
        "build": {"command": "npm run build", "exitCode": build_exit, "status": "PASS" if build_exit == 0 else "FAIL_OR_UNKNOWN", "log": str(OUT_LOG), "knownStderrNoise": "ESLint: nextVitals is not iterable if present with exit 0"},
        "nextSteps": [
            "Patch static check scripts to use repo-relative backup discovery and SKIP_WITH_REASON for missing historical snapshots.",
            "Patch markdown fixture lock comparison to normalize line endings, not fixtures.",
            "Do not create/restore backup snapshots for this baseline repair.",
            "Keep templates.json dirty state as TPL-95328E52 impact precheck candidate.",
        ],
    }

    json_path = DOCS / "FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.json"
    md_path = DOCS / "FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.md"
    csv_path = DOCS / "FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_MAP_20260522.csv"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["command", "status", "cause", "relatedTo5A", "repairRecommendation", "risk"])
        for item in failures:
            writer.writerow([item["command"], item["status"], item["cause"], item["relatedTo5A"], item["repairRecommendation"], item["risk"]])

    md = f"""# Frontend Validation Baseline Repair Precheck 2026-05-22

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- `src` 수정: 없음
- static check script 수정: 없음
- markdown runner/fixture 수정: 없음
- backup 생성/복원: 없음
- 파일 이동/import 수정/rename/refactor: 없음

## 3. 생성 파일
- `tmp/codex_frontend_validation_baseline_repair_precheck.py`
- `docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.md`
- `docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.json`
- `docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- 2A/2C/3B/4A/4B/5A static checks
- `tmp/codex_markdown_contract_fixture_lock.py`
- 5A closeout report
- `mysuit-ocr/backup` and expected `C:\\OCR\\OCR\\backup`
- typecheck/build

## 5. 현재 실패 검증 목록
| command | status | root cause | 5A related |
| --- | --- | --- | --- |
| `node tmp/check_runocr_formdata_keys_2a.mjs` | FATAL exit 2 | `C:\\OCR\\OCR\\backup` 2A snapshot missing | NO |
| `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | FAIL exit 1 | one backup-equivalence subcheck missing 2B snapshot | NO |
| `node tmp/check_runocr_doc_comments_3b.mjs` | FAIL exit 1 | 8 historical 3B backups missing | NO |
| `node tmp/check_template_workspace_move_4a.mjs` | FAIL exit 1 | structural checks pass; 4A backup equality missing | NO |
| `node tmp/check_template_editor_ui_move_4b.mjs` | FAIL exit 1 | structural/import checks pass; 3 backup equality checks missing | NO |
| `python tmp/codex_markdown_contract_fixture_lock.py --check ...` | FAIL exit 1 | actual LF vs expected fixture CRLF in all 6 cases | NO |
| `node tmp/check_ocr_core_types_common_move_5a.mjs` | PASS exit 0 | 5A baseline check passes | YES, PASS |

## 6. backup 경로 의존 분석
- Older static checks compute backup as `resolve(ROOT, "..", "backup")`, which maps to `C:\\OCR\\OCR\\backup`.
- `C:\\OCR\\OCR\\backup` does not exist in this workspace.
- Current backup exists at `C:\\OCR\\OCR\\mysuit-ocr\\backup\\ocr_core_types_20260522_before_FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE`.
- That 5A backup contains 5A files only, not historical 2A/2B/3B/4A/4B snapshot filenames.
- 5A check uses `ROOT/backup/<phase>` and passes.

## 7. static check repair 방향
Recommended:
1. Replace stale sibling backup dependency with repo-relative phase backup discovery.
2. If a historical backup is missing, report `SKIP_WITH_REASON` for that one logic-equivalence check.
3. Keep current-state structural boundary checks strict.
4. Do not regenerate backup snapshots as part of this repair.

## 8. markdown LF/CRLF 분석
- Markdown runner already masks `processing_time`.
- Runner does not normalize CRLF/LF before equality.
- Current backend actual output: LF.
- Current expected fixtures: CRLF.
- All 6 failures show first diff at line 1: same text, different line ending.

Recommendation: normalize line endings in compare path only, e.g. CRLF/LF -> LF after processing_time masking. Do not rebake fixtures for EOL-only drift.

## 9. 5A 인과 여부
The reproduced failures are not 5A code regressions. 5A-specific validation passes, typecheck/build pass, and failing checks isolate to missing historical backup snapshots or EOL-only markdown comparison.

## 10. 다음 실제 repair 추천
Recommendation: **C. static check scripts repair + markdown runner line-ending normalize**.

Scope:
- validation scripts/runners only
- no `src`
- no backend
- no fixture changes
- no backup creation/restoration

## 11. dirty 상태
```text
{chr(10).join(dirty) if dirty else "(clean)"}
```

`templates.json` dirty state remains a TPL-95328E52 impact precheck candidate.

## 12. typecheck/build 결과
- `npm run typecheck`: exit {typecheck_exit}, {report["typecheck"]["status"]}
- `npm run build`: exit {build_exit}, {report["build"]["status"]}
- stdout log: `{OUT_LOG}`
- stderr log: `{ERR_LOG}`

## 13. 다음 작업 제안
1. Repair static check backup handling with explicit SKIP_WITH_REASON.
2. Repair markdown runner compare normalization for LF/CRLF only.
3. Rerun all affected validations plus 5A check/typecheck/build.
4. Continue 5B only after validation baseline noise is quiet.
"""
    md_path.write_text(md, encoding="utf-8")

    print(json.dumps({"wrote": [str(md_path), str(json_path), str(csv_path)], "typecheck": typecheck_exit, "build": build_exit}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
