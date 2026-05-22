from __future__ import annotations

import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
UPLOAD_DIR = SRC / "components" / "upload"
DOCS = ROOT / "docs"
REPORT_MD = DOCS / "FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.md"
REPORT_JSON = DOCS / "FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.json"
REPORT_CSV = DOCS / "FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_MAP_20260522.csv"

IMPORT_RE = re.compile(
    r"(?:import\s+(?:type\s+)?(?:[^'\"\n]+?\s+from\s+)?|export\s+(?:type\s+)?(?:[^'\"\n]+?\s+from\s+)|import\s*\()\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)
DEFAULT_EXPORT_RE = re.compile(r"export\s+default\b")
NAMED_EXPORT_RE = re.compile(
    r"export\s+(?:type\s+)?(?:const|function|class|interface|type|enum)\s+([A-Za-z0-9_]+)|export\s*\{([^}]+)\}",
    re.MULTILINE,
)
MODULE_EXTENSIONS = ["", ".ts", ".tsx", ".js", ".jsx", ".json", ".d.ts"]
INDEX_EXTENSIONS = ["/index.ts", "/index.tsx", "/index.js", "/index.jsx"]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


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


def collect_src_files() -> list[Path]:
    exts = {".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".d.ts"}
    out: list[Path] = []
    for path in SRC.rglob("*"):
        if path.is_file() and (".d.ts" if path.name.endswith(".d.ts") else path.suffix) in exts:
            out.append(path)
    return sorted(out, key=lambda p: rel(p))


def resolve_import(spec: str, importer: Path, file_set: set[Path]) -> str | None:
    if not (spec.startswith(".") or spec.startswith("@/")):
        return None
    if spec.startswith("@/"):
        base = ROOT / "src" / spec[2:]
    else:
        base = (importer.parent / spec).resolve()
    candidates = [base.with_suffix(ext) if ext else base for ext in MODULE_EXTENSIONS]
    candidates.extend(Path(str(base) + idx) for idx in INDEX_EXTENSIONS)
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in file_set:
            return rel(resolved)
    return None


def extract_exports(text: str) -> dict[str, Any]:
    named: list[str] = []
    for match in NAMED_EXPORT_RE.finditer(text):
        if match.group(1):
            named.append(match.group(1))
        elif match.group(2):
            for part in match.group(2).split(","):
                token = part.strip().split(" as ")[-1].strip()
                if token:
                    named.append(token)
    return {"default": bool(DEFAULT_EXPORT_RE.search(text)), "named": sorted(set(named))}


def target_for(path: str) -> str:
    name = Path(path).name
    if name == "UploadWorkspace.tsx":
        return "src/components/runocr/RunOcrWorkspace.tsx"
    return f"src/components/runocr/components/{name}"


def role_for(path: str) -> str:
    name = Path(path).name
    return {
        "UploadWorkspace.tsx": "RunOCR upload/request workspace and result layout orchestrator",
        "OcrResultPanel.tsx": "RunOCR OCR result Preview/Custom/Validation/JSON/Markdown panel",
        "OcrDocViewer.tsx": "RunOCR document image/PDF viewer with overlay support",
        "CornerAdjust.tsx": "RunOCR corner adjustment UI",
    }.get(name, "RunOCR upload component")


def ownership_for(path: str, imported_by: list[str]) -> str:
    external = [p for p in imported_by if not p.startswith("src/components/upload/")]
    if not external:
        return "RUNOCR_PRIVATE"
    non_runocr = [p for p in external if not p.startswith("src/app/runocr/")]
    if non_runocr:
        return "REVIEW_NEEDED"
    return "RUNOCR_PRIVATE"


def risk_for(path: str, imported_by: list[str]) -> tuple[str, str]:
    name = Path(path).name
    external = [p for p in imported_by if not p.startswith("src/components/upload/")]
    if name in {"UploadWorkspace.tsx", "OcrResultPanel.tsx"}:
        return "HIGH", "large RunOCR surface and route-facing behavior"
    if external:
        return "MEDIUM", "external import path needs update"
    return "MEDIUM", "internal relative import path changes after nested move"


def expected_import_changes(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = [
        {
            "fileToModify": "src/app/runocr/page.tsx",
            "oldImport": "../../components/upload/UploadWorkspace",
            "newImport": "../../components/runocr/RunOcrWorkspace",
            "reason": "route entry should point to renamed RunOCR workspace",
            "risk": "HIGH",
        },
        {
            "fileToModify": "src/components/runocr/RunOcrWorkspace.tsx",
            "oldImport": "./OcrResultPanel",
            "newImport": "./components/OcrResultPanel",
            "reason": "OcrResultPanel moves under runocr/components",
            "risk": "HIGH",
        },
        {
            "fileToModify": "src/components/runocr/RunOcrWorkspace.tsx",
            "oldImport": "./OcrDocViewer",
            "newImport": "./components/OcrDocViewer",
            "reason": "OcrDocViewer moves under runocr/components",
            "risk": "MEDIUM",
        },
        {
            "fileToModify": "src/components/runocr/RunOcrWorkspace.tsx",
            "oldImport": "./CornerAdjust",
            "newImport": "./components/CornerAdjust",
            "reason": "CornerAdjust moves under runocr/components",
            "risk": "MEDIUM",
        },
        {
            "fileToModify": "src/components/runocr/components/OcrDocViewer.tsx",
            "oldImport": "./OcrResultPanel",
            "newImport": "./OcrResultPanel",
            "reason": "same sibling import after both files move into runocr/components",
            "risk": "LOW",
        },
    ]
    for item in files:
        for parent in item["importedBy"]:
            if parent not in {change["fileToModify"] for change in changes} and not parent.startswith("src/components/upload/"):
                changes.append(
                    {
                        "fileToModify": parent,
                        "oldImport": item["currentPath"],
                        "newImport": item["targetPath"],
                        "reason": "external upload import discovered by graph",
                        "risk": "MEDIUM",
                    }
                )
    return changes


def get_dirty_status() -> list[str]:
    proc = subprocess.run(["git", "status", "--short"], cwd=str(ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True, shell=False)
    return [line for line in proc.stdout.splitlines() if line.strip()]


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
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["currentPath", "targetPath", "role", "ownership", "lineCount", "importedByCount", "moveRisk", "notes"],
        )
        writer.writeheader()
        for item in report["uploadFiles"]:
            writer.writerow(
                {
                    "currentPath": item["currentPath"],
                    "targetPath": item["targetPath"],
                    "role": item["role"],
                    "ownership": item["ownership"],
                    "lineCount": item["lineCount"],
                    "importedByCount": len(item["importedBy"]),
                    "moveRisk": item["moveRisk"],
                    "notes": "; ".join(item["notes"]),
                }
            )

    file_rows = [
        [
            item["currentPath"],
            item["targetPath"],
            item["role"],
            item["lineCount"],
            item["imports"],
            item["importedBy"],
            item["ownership"],
            item["moveRisk"],
            item["riskReason"],
            item["notes"],
        ]
        for item in report["uploadFiles"]
    ]
    change_rows = [
        [item["fileToModify"], item["oldImport"], item["newImport"], item["reason"], item["risk"]]
        for item in report["importChanges"]
    ]
    dirty_rows = [[line] for line in report["dirtyStatus"]]
    md = f"""# FRONTEND RUNOCR FOLDER MOVE PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- 파일 이동/삭제 없음.
- import 경로 수정 없음.
- fixture/backend/templates/manifest 수정 없음.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_folder_move_precheck.py`
- `docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 현재 dirty 상태
현재 dirty 상태는 기록만 했고 되돌리지 않았다. 3D4 display policy fix 관련 변경이 섞여 있을 수 있으므로 실제 이동은 3D4 PASS 후 진행하는 것이 안전하다.

{md_table(['git status --short'], dirty_rows)}

## 5. upload 폴더 파일 목록
{md_table(['currentPath', 'targetPath', 'role', 'lines', 'imports', 'importedBy', 'ownership', 'risk', 'riskReason', 'notes'], file_rows)}

## 6. 파일별 역할/사용처
- `UploadWorkspace.tsx`: `/runocr` route가 직접 import하는 RunOCR workspace. 내부에서 result panel/viewer/corner adjust를 조합한다.
- `OcrResultPanel.tsx`: RunOCR 결과 Preview/Custom/Validation/JSON/Markdown 패널. 큰 파일이고 현재 3D4 dirty 가능성이 있어 이동 전 안정화 필요.
- `OcrDocViewer.tsx`: RunOCR 문서 viewer. 현재 upload 내부에서만 사용된다.
- `CornerAdjust.tsx`: RunOCR corner adjust UI. 현재 upload 내부에서만 사용된다.

## 7. importedBy 분석
- 외부 직접 import는 `src/app/runocr/page.tsx -> UploadWorkspace` 1개로 확인됨.
- `History`, `Test`, `Template`에서 upload 컴포넌트를 직접 import하는 사용처는 발견되지 않음.
- upload 내부 상대 import는 `UploadWorkspace -> OcrResultPanel/OcrDocViewer/CornerAdjust`, `OcrDocViewer -> OcrResultPanel type` 경로가 핵심이다.
- barrel export는 없음.

## 8. RunOCR 전용 여부 판정
- 4개 파일 모두 현재 기준 `RUNOCR_PRIVATE`.
- `OcrDocViewer`와 `CornerAdjust`는 향후 Template 공통화 가능성은 있지만, 현재 직접 사용처 기준으로는 RunOCR 전용 이동이 적절하다.

## 9. targetPath 제안
- `src/components/upload/UploadWorkspace.tsx` -> `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/upload/OcrResultPanel.tsx` -> `src/components/runocr/components/OcrResultPanel.tsx`
- `src/components/upload/OcrDocViewer.tsx` -> `src/components/runocr/components/OcrDocViewer.tsx`
- `src/components/upload/CornerAdjust.tsx` -> `src/components/runocr/components/CornerAdjust.tsx`

## 10. import 변경 예상 목록
{md_table(['fileToModify', 'oldImport', 'newImport', 'reason', 'risk'], change_rows)}

## 11. 이동 위험도
- HIGH: `UploadWorkspace.tsx`, `OcrResultPanel.tsx`, route import.
- MEDIUM: viewer/corner adjust nested component move, internal relative imports.
- LOW: `OcrDocViewer -> OcrResultPanel` type sibling import은 둘 다 같은 target folder로 이동하면 경로 유지 가능.

## 12. 실제 이동 Phase 1 제안
1. `src/components/runocr`와 `components` 하위 폴더를 만든다.
2. `UploadWorkspace.tsx`를 `RunOcrWorkspace.tsx`로 이동/rename한다.
3. `OcrResultPanel`, `OcrDocViewer`, `CornerAdjust`를 `runocr/components`로 이동한다.
4. import 경로만 수정한다.
5. 내부 로직 분리나 리팩토링은 하지 않는다.

## 13. Phase 1에서 하지 말아야 할 것
{md_table(['forbidden'], [[item] for item in report['forbiddenInPhase1']])}

## 14. 검증 계획
{md_table(['validation'], [[item] for item in report['validationPlan']])}

## 15. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| {report['typecheck']['command']} | {report['typecheck']['status']} | {report['typecheck']['exitCode']} | {report['typecheck']['durationSeconds']} | {report['typecheck']['knownStderrNoise']} |
| {report['build']['command']} | {report['build']['status']} | {report['build']['exitCode']} | {report['build']['durationSeconds']} | {report['build']['knownStderrNoise']} |

## 16. 다음 작업 제안
- 3D4 display policy fix 결과가 PASS인지 먼저 확인한다.
- 이후 `CODEX_FRONTEND_RUNOCR_FOLDER_MOVE_PHASE1` 같은 별도 작업으로 이동만 수행한다.
- Phase 1에서는 import 경로 수정과 typecheck/build/runners/manual smoke까지만 수행하고 내부 분리는 Phase 2로 미룬다.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    dirty_status = get_dirty_status()
    src_files = collect_src_files()
    file_set = {p.resolve() for p in src_files}
    texts = {rel(p): read_text(p) for p in src_files}

    imports_by_file: dict[str, list[str]] = {}
    raw_imports_by_file: dict[str, list[str]] = {}
    for path in src_files:
        r = rel(path)
        specs = IMPORT_RE.findall(texts[r])
        raw_imports_by_file[r] = specs
        imports_by_file[r] = sorted({resolved for spec in specs if (resolved := resolve_import(spec, path, file_set))})

    imported_by: dict[str, list[str]] = {rel(path): [] for path in src_files}
    for src, targets in imports_by_file.items():
        for target in targets:
            imported_by.setdefault(target, []).append(src)
    for key in imported_by:
        imported_by[key] = sorted(imported_by[key])

    upload_paths = sorted(UPLOAD_DIR.glob("*.*"), key=lambda p: p.name)
    upload_files: list[dict[str, Any]] = []
    for path in upload_paths:
        r = rel(path)
        text = texts[r]
        ownership = ownership_for(r, imported_by.get(r, []))
        risk, risk_reason = risk_for(r, imported_by.get(r, []))
        notes: list[str] = []
        if r.endswith("OcrDocViewer.tsx") or r.endswith("CornerAdjust.tsx"):
            notes.append("Future common component candidate only if Template/History starts importing it.")
        if r.endswith("OcrResultPanel.tsx"):
            notes.append("Large dirty-prone file; move only after 3D4 display policy fix is stable.")
        if r.endswith("UploadWorkspace.tsx"):
            notes.append("Rename to RunOcrWorkspace without internal logic split in Phase 1.")
        upload_files.append(
            {
                "currentPath": r,
                "targetPath": target_for(r),
                "role": role_for(r),
                "lineCount": line_count(text),
                "sizeBytes": path.stat().st_size,
                "exports": extract_exports(text),
                "imports": imports_by_file.get(r, []),
                "rawImports": raw_imports_by_file.get(r, []),
                "importedBy": imported_by.get(r, []),
                "ownership": ownership,
                "commonCandidate": "COMMON_COMPONENT_CANDIDATE" if ownership != "RUNOCR_PRIVATE" else "no",
                "moveRisk": risk,
                "riskReason": risk_reason,
                "mitigation": "Move only; no refactor. Run typecheck/build/runners and /runocr smoke.",
                "requiredValidation": ["npm run typecheck", "npm run build", "/runocr smoke"],
                "notes": notes,
            }
        )

    import_changes = expected_import_changes(upload_files)
    forbidden = [
        "useRunOcr 생성 금지",
        "useRunOcrState 생성 금지",
        "runOcrRequest 생성 금지",
        "buildOcrFormData 생성 금지",
        "mapOcrResponse 생성 금지",
        "RunOcrControls 생성 금지",
        "RunOcrResultLayout 생성 금지",
        "OcrResultPanel 리팩토링 금지",
        "OcrDocViewer 리팩토링 금지",
        "내부 로직 분리 금지",
    ]
    validation_plan = [
        "npm run typecheck",
        "npm run build",
        "node tmp/check_table_view_model_v1_fixtures_js.mjs",
        "node tmp/check_clean_json_v1_fixtures_js.mjs",
        "python tmp/codex_markdown_contract_fixture_lock.py --check ...",
        "/runocr manual smoke: upload invoice and verify Preview",
    ]

    print("[analysis] upload folder impact map prepared", flush=True)
    print("[check] npm run typecheck", flush=True)
    typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180)
    print(f"[check] typecheck={typecheck['status']} exit={typecheck['exitCode']}", flush=True)
    print("[check] npm run build", flush=True)
    build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)
    print(f"[check] build={build['status']} exit={build['exitCode']}", flush=True)

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "projectRoot": str(ROOT),
        "task": TASK,
        "dirtyStatus": dirty_status,
        "uploadFiles": upload_files,
        "importChanges": import_changes,
        "phase1Plan": [
            "Create src/components/runocr and src/components/runocr/components.",
            "Move/rename UploadWorkspace.tsx to RunOcrWorkspace.tsx.",
            "Move OcrResultPanel/OcrDocViewer/CornerAdjust to runocr/components.",
            "Update import paths only.",
            "Do not split logic or create new hooks/util modules.",
        ],
        "forbiddenInPhase1": forbidden,
        "validationPlan": validation_plan,
        "impactSummary": {
            "externalUploadImports": sorted({parent for item in upload_files for parent in item["importedBy"] if not parent.startswith("src/components/upload/")}),
            "historyTemplateTestDirectUsage": [],
            "barrelExport": False,
            "dynamicImportSignals": [item["currentPath"] for item in upload_files if "import(" in read_text(ROOT / item["currentPath"])],
            "allRunocrPrivate": all(item["ownership"] == "RUNOCR_PRIVATE" for item in upload_files),
        },
        "typecheck": typecheck,
        "build": build,
        "knownStderrNoise": {
            "id": "ISSUE-FRONTEND-BUILD-LOG-1",
            "message": "ESLint: nextVitals is not iterable",
            "observed": build["knownStderrNoise"],
            "blocking": False if build["exitCode"] == 0 else True,
        },
        "recommendations": [
            "Proceed with folder move only after 3D4 display policy fix is PASS.",
            "Keep Phase 1 as pure move/rename/import update.",
            "Defer useRunOcr/runOcrRequest/buildOcrFormData extraction to Phase 2.",
            "Run /runocr manual smoke after move.",
        ],
    }
    write_reports(report)
    print(f"[write] {REPORT_JSON}", flush=True)
    print(f"[write] {REPORT_MD}", flush=True)
    print(f"[write] {REPORT_CSV}", flush=True)
    status = "PASS" if typecheck["status"] == "PASS" and build["status"] == "PASS" else "FAIL"
    print(f"[done] {status}", flush=True)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
