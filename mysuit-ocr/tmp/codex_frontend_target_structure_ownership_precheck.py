from __future__ import annotations

import csv
import json
import re
import subprocess
import time
from collections import Counter, defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DOCS = ROOT / "docs"
REPORT_MD = DOCS / "FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md"
REPORT_JSON = DOCS / "FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json"
REPORT_CSV = DOCS / "FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv"

EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".d.ts"}
MODULE_EXTENSIONS = ["", ".ts", ".tsx", ".js", ".jsx", ".json", ".d.ts"]
INDEX_EXTENSIONS = ["/index.ts", "/index.tsx", "/index.js", "/index.jsx"]

IMPORT_RE = re.compile(
    r"(?:import\s+(?:type\s+)?(?:[^'\"\n]+?\s+from\s+)?|export\s+(?:type\s+)?(?:[^'\"\n]+?\s+from\s+)|import\s*\()\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)
DEFAULT_EXPORT_RE = re.compile(r"export\s+default\b")
NAMED_EXPORT_RE = re.compile(
    r"export\s+(?:type\s+)?(?:const|function|class|interface|type|enum)\s+([A-Za-z0-9_]+)|export\s*\{([^}]+)\}",
    re.MULTILINE,
)


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


def collect_files() -> list[Path]:
    files: list[Path] = []
    for path in SRC.rglob("*"):
        if not path.is_file():
            continue
        suffix = ".d.ts" if path.name.endswith(".d.ts") else path.suffix
        if suffix in EXTENSIONS:
            files.append(path)
    return sorted(files, key=lambda p: rel(p))


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
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
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


def route_entries(files: list[str]) -> list[str]:
    names = ("/page.tsx", "/layout.tsx", "/loading.tsx", "/error.tsx", "/not-found.tsx", "/route.ts")
    return [path for path in files if path.startswith("src/app/") and (path.endswith(names) or path in {"src/app/page.tsx", "src/app/layout.tsx"})]


def reachable_from(entries: list[str], imports_by_file: dict[str, list[str]]) -> set[str]:
    seen: set[str] = set(entries)
    queue = deque(entries)
    while queue:
        current = queue.popleft()
        for nxt in imports_by_file.get(current, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def importing_feature(path: str) -> str:
    if path.startswith("src/app/runocr/"):
        return "runocr"
    if path.startswith("src/app/template/") or path.startswith("src/app/ocr/"):
        return "template"
    if path.startswith("src/app/history/"):
        return "history"
    if path.startswith("src/app/autorestore/"):
        return "restore"
    if path.startswith("src/app/test/"):
        return "test"
    if path.startswith("src/app/login/"):
        return "login"
    if path.startswith("src/components/upload/"):
        return "runocr"
    if path.startswith("src/components/ocr/") or path.startswith("src/components/template/"):
        return "template"
    if path.startswith("src/components/history/"):
        return "history"
    if path.startswith("src/components/autorestore/"):
        return "restore"
    if path.startswith("src/components/test/"):
        return "test"
    if path.startswith("src/components/login/"):
        return "login"
    if path.startswith("src/components/layout/"):
        return "layout"
    return "unknown"


def classify(path: str, text: str, imported_by: list[str]) -> dict[str, Any]:
    features = sorted({importing_feature(parent) for parent in imported_by if importing_feature(parent) != "unknown"})
    has_react = any(token in text for token in ["useState", "useEffect", "useMemo", "useCallback", "React", "tsx"])
    has_fetch = any(token in text for token in ["fetch(", "axios", "FormData", "localStorage", "sessionStorage"])
    is_type = path.endswith(".d.ts") or "/types." in path or path.endswith("/types.ts")
    is_route = path.startswith("src/app/")
    name = Path(path).name

    owner = "unknown/review"
    shared = "review-needed"
    category = "unknown"
    target = path
    target_role = ""
    risk = "LOW"
    phase = "Phase 0"
    notes: list[str] = []

    if is_route:
        owner = "app-route"
        shared = "route-entry"
        category = "route"
        target = path
        target_role = "Next.js app route/API entry"
        risk = "HIGH" if "/api/" in path else "MEDIUM"
        phase = "Phase 0"
    elif path.startswith("src/components/upload/"):
        owner = "runocr"
        shared = "feature-private-component"
        category = "workspace component" if name == "UploadWorkspace.tsx" else "feature component"
        new_name = "RunOcrWorkspace.tsx" if name == "UploadWorkspace.tsx" else name
        sub = "" if new_name == "RunOcrWorkspace.tsx" else "components/"
        target = f"src/components/runocr/{sub}{new_name}"
        target_role = "RunOCR upload/result UI"
        risk = "HIGH" if name in {"UploadWorkspace.tsx", "OcrResultPanel.tsx"} else "MEDIUM"
        phase = "Phase 1"
    elif path.startswith("src/components/ocr/core/"):
        owner = "template"
        shared = "feature-private-utils"
        category = "template core logic/type"
        target = "src/components/template/utils/" + name
        target_role = "Template editor core logic"
        risk = "MEDIUM"
        phase = "Phase 3"
        notes.append("Could become common/utils if RunOCR also consumes template core later.")
    elif path.startswith("src/components/ocr/"):
        owner = "template"
        shared = "feature-private-component"
        category = "template component"
        target = f"src/components/template/components/{name}" if name != "TemplateWorkspace.tsx" else "src/components/template/TemplateWorkspace.tsx"
        target_role = "Template editor UI"
        risk = "HIGH" if name in {"OcrCanvasPane.tsx", "OcrRightPanel.tsx", "OcrAnnotator.tsx"} else "MEDIUM"
        phase = "Phase 3"
    elif path.startswith("src/components/template/"):
        owner = "template"
        shared = "feature-private-component"
        category = "template component"
        target = f"src/components/template/components/{name}"
        target_role = "Template helper UI"
        risk = "MEDIUM"
        phase = "Phase 3"
    elif path.startswith("src/components/history/"):
        owner = "history"
        shared = "feature-private-component"
        category = "history component"
        target = f"src/components/history/{name}" if name in {"HistoryWorkspace.tsx", "DetailHistoryView.tsx"} else f"src/components/history/components/{name}"
        target_role = "History UI"
        risk = "HIGH" if name == "DetailHistoryView.tsx" else "MEDIUM"
        phase = "Phase 4"
    elif path.startswith("src/components/autorestore/"):
        owner = "restore"
        shared = "feature-private-component"
        category = "restore workspace component"
        target = f"src/components/restore/{name}"
        target_role = "Restore workspace UI"
        risk = "MEDIUM"
        phase = "Phase 4"
    elif path.startswith("src/components/test/"):
        owner = "test"
        shared = "feature-private-component" if path.endswith(".tsx") else "feature-private-utils"
        category = "test workspace" if name == "TestWorkspace.tsx" else "test core logic"
        target = f"src/components/test/{name}" if name == "TestWorkspace.tsx" else f"src/components/test/utils/{name}"
        target_role = "Internal QA/test UI and runner logic"
        risk = "HIGH" if name == "TestWorkspace.tsx" else "MEDIUM"
        phase = "Phase 6"
        notes.append("TestWorkspace work requires explicit user confirmation before changes.")
    elif path.startswith("src/components/login/"):
        owner = "login"
        shared = "feature-private-component"
        category = "login component"
        target = path
        target_role = "Login UI"
        risk = "LOW"
        phase = "Phase 0"
    elif path.startswith("src/components/layout/"):
        owner = "layout"
        shared = "feature-private-component"
        category = "layout component"
        target = path
        target_role = "Global shell/layout UI"
        risk = "LOW"
        phase = "Phase 0"
    elif path.startswith("src/components/common/"):
        owner = "common/components"
        shared = "shared-component"
        category = "common component/provider"
        target = f"src/common/components/{name}" if name != "AppProviders.tsx" else path
        target_role = "Shared UI/provider"
        risk = "MEDIUM" if name == "AppProviders.tsx" else "LOW"
        phase = "Phase 5" if name != "AppProviders.tsx" else "Phase 0"
    elif path.startswith("src/lib/"):
        category = "lib/helper"
        lib_targets = {
            "cleanJsonBuilder.ts": ("common/utils", "shared-utils", "src/common/utils/cleanJsonBuilder.ts", "Clean JSON builder", "Phase 5", "MEDIUM"),
            "markdownReportBuilder.ts": ("common/utils", "shared-utils", "src/common/utils/markdownReportBuilder.ts", "Markdown report builder", "Phase 5", "MEDIUM"),
            "structuredTableViewModel.ts": ("common/utils", "shared-utils", "src/common/utils/structuredTableViewModel.ts", "Structured table view model helper", "Phase 5", "MEDIUM"),
            "invoiceTableDisplay.ts": ("common/utils", "shared-utils", "src/common/utils/invoiceTableDisplay.ts", "Invoice table display policy", "Phase 5", "HIGH"),
            "ocrResultFormatters.ts": ("common/utils", "shared-utils", "src/common/utils/ocrResultFormatters.ts", "OCR result formatters", "Phase 5", "MEDIUM"),
            "historyStore.ts": ("history", "feature-private-utils", "src/components/history/utils/historyStore.ts", "History storage", "Phase 4", "HIGH"),
            "restoreProfileStore.ts": ("restore", "feature-private-utils", "src/components/restore/utils/restoreProfileStore.ts", "Restore profile storage", "Phase 4", "MEDIUM"),
            "autofillEngine.ts": ("restore", "feature-private-utils", "src/components/restore/utils/autofillEngine.ts", "Autofill/restore matching engine", "Phase 4", "HIGH"),
            "testsets.ts": ("test", "feature-private-utils", "src/components/test/utils/testsets.ts", "Testset loader", "Phase 6", "MEDIUM"),
            "groundTruthStore.ts": ("test", "feature-private-utils", "src/components/test/utils/groundTruthStore.ts", "Ground truth storage", "Phase 6", "MEDIUM"),
            "login.ts": ("login", "feature-private-utils", "src/components/login/utils/login.ts", "Login helper", "Phase 0", "LOW"),
            "axios.ts": ("common/utils", "shared-utils", "src/common/utils/axios.ts", "API client", "Phase 5", "MEDIUM"),
            "bizNumber.ts": ("common/utils", "shared-utils", "src/common/utils/bizNumber.ts", "Business number validation", "Phase 5", "LOW"),
            "profiles.ts": ("restore", "feature-private-utils", "src/components/restore/utils/profiles.ts", "Restore/autofill profile definitions", "Phase 4", "HIGH"),
            "imageStore.ts": ("common/utils", "shared-utils", "src/common/utils/imageStore.ts", "Image/cache store", "Phase 5", "MEDIUM"),
            "invoiceFieldLabels.ts": ("common/utils", "shared-utils", "src/common/utils/invoiceFieldLabels.ts", "Invoice field label policy", "Phase 5", "LOW"),
            "theme.ts": ("common/utils", "shared-utils", "src/common/utils/theme.ts", "Theme constants", "Phase 5", "LOW"),
        }
        owner, shared, target, target_role, phase, risk = lib_targets.get(name, ("common/utils", "shared-utils", f"src/common/utils/{name}", "Shared utility", "Phase 5", "MEDIUM"))
        if has_fetch:
            notes.append("Contains IO/browser/API storage signal; verify feature boundary before move.")
    elif path.startswith("src/types/"):
        owner = "common/types"
        shared = "shared-types"
        category = "type declaration"
        target = f"src/common/types/{name}"
        target_role = "Shared type declaration"
        risk = "MEDIUM"
        phase = "Phase 5"
    else:
        owner = "unknown/review"
        shared = "review-needed"
        category = "unknown"
        target = path
        target_role = "Review needed"
        risk = "MEDIUM"
        phase = "Phase 0"

    if len(features) > 1 and not is_route:
        notes.append(f"Imported from multiple feature areas: {', '.join(features)}.")
        if owner not in {"common/components", "common/utils", "common/types", "layout"}:
            risk = "HIGH"
    if is_type:
        notes.append("Type/declaration file: do not judge by importedBy only.")
    if has_react and shared.endswith("utils"):
        notes.append("React signal found; verify before placing under utils.")
    return {
        "owner": owner,
        "sharedStatus": shared,
        "category": category,
        "targetPath": target,
        "targetRole": target_role,
        "moveRisk": risk,
        "recommendedPhase": phase,
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
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "currentPath",
                "targetPath",
                "owner",
                "sharedStatus",
                "category",
                "lineCount",
                "importedByCount",
                "moveRisk",
                "recommendedPhase",
                "notes",
            ],
        )
        writer.writeheader()
        for item in report["files"]:
            writer.writerow(
                {
                    "currentPath": item["currentPath"],
                    "targetPath": item["targetPath"],
                    "owner": item["owner"],
                    "sharedStatus": item["sharedStatus"],
                    "category": item["category"],
                    "lineCount": item["lineCount"],
                    "importedByCount": len(item["importedBy"]),
                    "moveRisk": item["moveRisk"],
                    "recommendedPhase": item["recommendedPhase"],
                    "notes": "; ".join(item["notes"]),
                }
            )

    files = report["files"]
    mapping_rows = [
        [
            item["currentPath"],
            item["targetPath"],
            item["owner"],
            item["sharedStatus"],
            item["lineCount"],
            len(item["importedBy"]),
            item["moveRisk"],
            item["recommendedPhase"],
            item["targetRole"],
            item["notes"],
        ]
        for item in files
    ]
    common_rows = [
        [item["currentPath"], item["targetPath"], item["owner"], item["sharedStatus"], item["moveRisk"], item["notes"]]
        for item in report["commonCandidates"]
    ]
    private_rows = [
        [item["currentPath"], item["targetPath"], item["owner"], item["sharedStatus"], item["moveRisk"]]
        for item in report["featurePrivateCandidates"]
    ]
    review_rows = [
        [item["currentPath"], item["targetPath"], item["owner"], item["sharedStatus"], item["moveRisk"], item["notes"]]
        for item in report["reviewNeeded"]
    ]
    phase_rows = [[p["id"], p["scope"], p["risk"], p["validation"], p["notes"]] for p in report["phases"]]

    md = f"""# FRONTEND TARGET STRUCTURE OWNERSHIP PRECHECK 20260522

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
- `tmp/codex_frontend_target_structure_ownership_precheck.py`
- `docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv`

## 4. 사용자가 정한 목표 구조
- route entry는 `src/app`.
- 탭/기능별 UI는 `src/components/{{runocr,template,history,restore,test,login,layout}}`.
- 여러 탭 공통 UI는 `src/common/components`.
- 여러 탭 공통 순수 로직/정책/변환 함수는 `src/common/utils`.
- 여러 탭 공통 타입은 `src/common/types`.

## 5. 분석 범위
- 포함: `src/app`, `src/components`, `src/lib`, `src/types`, `src/hooks`가 있다면 포함.
- 제외: `node_modules`, `.next`, `dist`, `build`, `public`, `backup`, `tmp`, `docs`, backend.

## 6. 전체 파일 수
- totalFiles: {report['totalFiles']}
- routeReachableFiles: {report['routeReachableCount']}

## 7. ownership 분류 요약
{md_table(['owner', 'count'], [[k, v] for k, v in report['ownershipSummary'].items()])}

## 8. common 후보 목록
{md_table(['currentPath', 'targetPath', 'owner', 'sharedStatus', 'risk', 'notes'], common_rows)}

## 9. feature-private 후보 목록
{md_table(['currentPath', 'targetPath', 'owner', 'sharedStatus', 'risk'], private_rows)}

## 10. currentPath -> targetPath 매핑표
{md_table(['currentPath', 'targetPath', 'owner', 'sharedStatus', 'lines', 'importedBy', 'risk', 'phase', 'targetRole', 'notes'], mapping_rows)}

## 11. 공통으로 빼야 할 파일
- `src/lib/cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `structuredTableViewModel.ts`, `invoiceTableDisplay.ts`, `ocrResultFormatters.ts`는 Preview/Clean JSON/Markdown/table 정책 계층이라 `src/common/utils` 후보.
- `src/components/common/FileDropzone.tsx`, `RequireLogin.tsx`는 `src/common/components` 후보.
- `src/types/utif.d.ts`는 `src/common/types` 후보. 단, declaration file은 importedBy만으로 삭제/이동 판단하지 않는다.

## 12. feature 안에 남겨야 할 파일
- RunOCR 전용: `src/components/upload/*` -> `src/components/runocr`.
- Template 전용: `src/components/ocr/*`, `src/components/template/*`, `src/components/ocr/core/*`.
- History 전용: `src/components/history/*`, `src/lib/historyStore.ts`.
- Restore 전용: `src/components/autorestore/*`, `src/lib/restoreProfileStore.ts`, `autofillEngine.ts`, `profiles.ts`.
- Test 전용: `src/components/test/*`, `src/lib/testsets.ts`, `groundTruthStore.ts`.

## 13. review needed 파일
{md_table(['currentPath', 'targetPath', 'owner', 'sharedStatus', 'risk', 'notes'], review_rows)}

## 14. 위험도 평가
- HIGH: app route/API entry, 큰 workspace, canvas/template core, shared policy util, TestWorkspace.
- MEDIUM: 여러 import 경로 변경이 필요한 feature component/utils.
- LOW: import 수가 적고 목표 위치가 명확한 단순 이동.

## 15. phase별 이동 계획
{md_table(['phase', 'scope', 'risk', 'validation', 'notes'], phase_rows)}

## 16. phase별 검증 계획
- 공통: `npm run typecheck`, `npm run build`.
- RunOCR 이동 후: `/runocr` 업로드/Preview smoke, Clean JSON runner, Markdown check, table_view_model runner.
- Template 이동 후: `/template` 및 `/ocr` route 확인, 영역/캔버스 smoke.
- Restore/History 이동 후: `/autorestore`, `/history` route smoke.
- Common 이동 후: 전체 typecheck/build와 주요 runner 재수행.

## 17. TestWorkspace gate
- `TestWorkspace.tsx`는 매우 큰 내부 QA 화면이며 Phase 6으로만 분류한다.
- TestWorkspace 분리/이동은 사용자에게 먼저 확인한 뒤 별도 작업으로 진행한다.

## 18. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| {report['typecheck']['command']} | {report['typecheck']['status']} | {report['typecheck']['exitCode']} | {report['typecheck']['durationSeconds']} | {report['typecheck']['knownStderrNoise']} |
| {report['build']['command']} | {report['build']['status']} | {report['build']['exitCode']} | {report['build']['durationSeconds']} | {report['build']['knownStderrNoise']} |

## 19. 다음 작업 추천
1. 3D4 display policy fix 완료.
2. Phase 0 목표 구조 문서화 확정.
3. Phase 1 RunOCR 폴더 이동 precheck/이동.
4. Phase 2 RunOCR 내부 utils 분리.
5. Phase 3 Template 정리.
6. Phase 4 Restore/History 정리.
7. Phase 5 Common 이동.
8. Phase 6 TestWorkspace는 사용자 확인 후 별도 진행.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    paths = collect_files()
    file_set = {p.resolve() for p in paths}
    texts = {rel(p): read_text(p) for p in paths}

    imports_by_file: dict[str, list[str]] = {}
    raw_imports_by_file: dict[str, list[str]] = {}
    for path in paths:
        r = rel(path)
        specs = IMPORT_RE.findall(texts[r])
        raw_imports_by_file[r] = specs
        imports_by_file[r] = sorted({resolved for spec in specs if (resolved := resolve_import(spec, path, file_set))})

    imported_by: dict[str, list[str]] = defaultdict(list)
    for src, targets in imports_by_file.items():
        for target in targets:
            imported_by[target].append(src)
    for key in imported_by:
        imported_by[key] = sorted(imported_by[key])

    all_rel = [rel(p) for p in paths]
    entries = route_entries(all_rel)
    reachable = reachable_from(entries, imports_by_file)

    files: list[dict[str, Any]] = []
    for path in paths:
        r = rel(path)
        text = texts[r]
        classification = classify(r, text, imported_by.get(r, []))
        files.append(
            {
                "currentPath": r,
                "targetPath": classification["targetPath"],
                "owner": classification["owner"],
                "sharedStatus": classification["sharedStatus"],
                "category": classification["category"],
                "extension": ".d.ts" if path.name.endswith(".d.ts") else path.suffix,
                "lineCount": line_count(text),
                "sizeBytes": path.stat().st_size,
                "imports": imports_by_file.get(r, []),
                "rawImports": raw_imports_by_file.get(r, []),
                "importedBy": imported_by.get(r, []),
                "routeReachable": r in reachable,
                "dynamicUsageSignals": ["dynamic import"] if "import(" in text else [],
                "currentRole": classification["category"],
                "targetRole": classification["targetRole"],
                "exports": extract_exports(text),
                "moveRisk": classification["moveRisk"],
                "recommendedPhase": classification["recommendedPhase"],
                "notes": classification["notes"],
            }
        )

    ownership_summary = dict(sorted(Counter(item["owner"] for item in files).items()))
    common_candidates = [item for item in files if item["owner"].startswith("common/")]
    feature_private = [item for item in files if item["sharedStatus"].startswith("feature-private")]
    review_needed = [item for item in files if item["owner"] == "unknown/review" or item["sharedStatus"] == "review-needed"]
    phases = [
        {"id": "Phase 0", "scope": "목표 구조 문서화/route 유지", "risk": "LOW", "validation": "typecheck/build", "notes": "실제 이동 전 기준선"},
        {"id": "Phase 1", "scope": "components/upload -> components/runocr", "risk": "HIGH", "validation": "/runocr smoke + runners", "notes": "UploadWorkspace rename 포함"},
        {"id": "Phase 2", "scope": "RunOCR 내부 utils/components 분리", "risk": "HIGH", "validation": "/runocr smoke + runners", "notes": "이동 후 내부 분리"},
        {"id": "Phase 3", "scope": "template/ocr 폴더 정리", "risk": "HIGH", "validation": "/template, /ocr smoke", "notes": "canvas/core 영향 큼"},
        {"id": "Phase 4", "scope": "restore/history 네이밍 및 utils 위치 정리", "risk": "MEDIUM", "validation": "/autorestore, /history smoke", "notes": "store import 영향 확인"},
        {"id": "Phase 5", "scope": "src/lib -> src/common/utils/types/components", "risk": "HIGH", "validation": "전체 runners + typecheck/build", "notes": "공통 import 영향 큼"},
        {"id": "Phase 6", "scope": "TestWorkspace 및 test utils", "risk": "HIGH", "validation": "/test smoke + user confirmation", "notes": "사용자 확인 전 진행 금지"},
    ]

    print("[analysis] ownership map prepared", flush=True)
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
        "targetStructure": {
            "app": "src/app route entries",
            "components": ["runocr", "template", "history", "restore", "test", "login", "layout"],
            "common": ["components", "utils", "types"],
        },
        "totalFiles": len(files),
        "routeEntries": entries,
        "routeReachableCount": sum(1 for item in files if item["routeReachable"]),
        "files": files,
        "ownershipSummary": ownership_summary,
        "commonCandidates": common_candidates,
        "featurePrivateCandidates": feature_private,
        "reviewNeeded": review_needed,
        "phases": phases,
        "validationPlan": {
            "common": ["npm run typecheck", "npm run build"],
            "runocr": ["/runocr smoke", "Clean JSON runner", "Markdown fixture check", "table_view_model runner"],
            "template": ["/template smoke", "/ocr smoke"],
            "historyRestore": ["/history smoke", "/autorestore smoke"],
            "test": ["/test smoke after explicit user approval"],
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
            "Finish 3D4 display policy fix first.",
            "Start with Phase 1 RunOCR folder move after a dedicated move precheck.",
            "Keep TestWorkspace gated behind explicit user confirmation.",
            "Move src/lib shared utilities to common/utils only after feature folders stabilize.",
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
