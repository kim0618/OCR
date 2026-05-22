from __future__ import annotations

import csv
import json
import re
import subprocess
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any


TASK = "CODEX_FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DOCS = ROOT / "docs"
OCR_LOG_DIR = ROOT.parent / "ocr-server" / "logs"
REPORT_MD = DOCS / "FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md"
REPORT_JSON = DOCS / "FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.json"
REPORT_CSV = DOCS / "FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_TABLE_20260521.csv"

INCLUDED_EXTS = {".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".d.ts"}
EXCLUDED_DIR_NAMES = {"node_modules", ".next", "dist", "build", "public", "backup", "tmp", "docs"}
ROUTE_FILENAMES = {"page.tsx", "page.ts", "layout.tsx", "layout.ts", "loading.tsx", "loading.ts", "error.tsx", "error.ts", "not-found.tsx", "not-found.ts", "route.ts", "route.js"}

IMPORT_RE = re.compile(r"""(?:import\s+(?:type\s+)?(?:[\s\S]*?\s+from\s+)?|export\s+(?:type\s+)?[\s\S]*?\s+from\s+)["']([^"']+)["']""")
DYNAMIC_RE = re.compile(r"""(?:import\s*\(\s*|require\s*\(\s*)["']([^"']+)["']""")
DEFAULT_EXPORT_RE = re.compile(r"\bexport\s+default\b")
NAMED_DECL_EXPORT_RE = re.compile(r"\bexport\s+(?:async\s+)?(?:function|const|let|var|class|interface|type|enum)\s+([A-Za-z0-9_$]+)")
BRACE_EXPORT_RE = re.compile(r"\bexport\s+(?:type\s+)?\{([^}]+)\}")


def to_posix(path: Path) -> str:
    return path.as_posix()


def rel(path: Path) -> str:
    return to_posix(path.relative_to(ROOT))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def collect_files() -> list[Path]:
    out: list[Path] = []
    for path in SRC.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(ROOT).parts):
            continue
        suffix = ".d.ts" if path.name.endswith(".d.ts") else path.suffix
        if suffix in INCLUDED_EXTS:
            out.append(path)
    return sorted(out, key=lambda p: rel(p).lower())


def extension(path: Path) -> str:
    return ".d.ts" if path.name.endswith(".d.ts") else path.suffix


def resolve_local_import(from_file: Path, spec: str, file_set: set[Path]) -> Path | None:
    if not (spec.startswith(".") or spec.startswith("@/")):
        return None
    base = (SRC / spec[2:]) if spec.startswith("@/") else (from_file.parent / spec)
    candidates: list[Path] = []
    if base.suffix:
        candidates.append(base)
    for ext in [".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".d.ts"]:
        candidates.append(Path(str(base) + ext))
    for ext in [".ts", ".tsx", ".js", ".jsx", ".json"]:
        candidates.append(base / f"index{ext}")
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in file_set:
            return resolved
    return None


def route_path_for_entry(path: Path) -> str:
    app_rel = path.relative_to(SRC / "app")
    parts = list(app_rel.parts[:-1])
    if path.name == "layout.tsx" and not parts:
        return "ROOT_LAYOUT"
    if path.name == "route.ts":
        route = "/" + "/".join(parts)
        return (route if route != "/" else "/") + " (api route)"
    route = "/" + "/".join(parts)
    return route if route != "/" else "/"


def category_for(path: Path, line_count: int) -> str:
    r = rel(path)
    name = path.name
    if r == "src/app/globals.css":
        return "style"
    if r.startswith("src/app/api/"):
        return "api route"
    if r.startswith("src/app/") and name in ROUTE_FILENAMES:
        return "page/layout"
    if r.startswith("src/app/"):
        return "route"
    if r.startswith("src/types/") or name.endswith(".d.ts"):
        return "type"
    if r.startswith("src/lib/"):
        if "Store" in name or name in {"historyStore.ts", "groundTruthStore.ts", "restoreProfileStore.ts", "imageStore.ts"}:
            return "store"
        return "lib/helper"
    if r.startswith("src/components/common/"):
        return "common component"
    if r.startswith("src/components/layout/"):
        return "layout component"
    if "Workspace" in name:
        return "workspace component"
    if r.startswith("src/components/") and "/core/" in r:
        return "feature core/helper"
    if r.startswith("src/components/"):
        return "feature component"
    return "unknown"


def named_exports(text: str) -> list[str]:
    names: list[str] = []
    names.extend(match.group(1) for match in NAMED_DECL_EXPORT_RE.finditer(text))
    for match in BRACE_EXPORT_RE.finditer(text):
        chunk = match.group(1)
        for part in chunk.split(","):
            token = part.strip()
            if not token:
                continue
            token = token.split(" as ")[-1].strip()
            if token:
                names.append(token)
    return sorted(set(names))


def imported_symbol_summary(text: str) -> list[str]:
    specs = []
    for match in IMPORT_RE.finditer(text):
        specs.append(match.group(1))
    for match in DYNAMIC_RE.finditer(text):
        if match.group(1) not in specs:
            specs.append(match.group(1))
    return specs


def role_for(path: Path, category: str, exports: dict[str, Any], line_count: int) -> str:
    r = rel(path)
    name = path.stem
    special: dict[str, str] = {
        "src/components/upload/OcrResultPanel.tsx": "OCR 결과 Preview/Custom/Validation/Clean JSON/Markdown 표시 패널",
        "src/components/upload/UploadWorkspace.tsx": "RunOCR 업로드 화면의 파일 선택, OCR 실행, 결과 패널 조합 workspace",
        "src/components/test/TestWorkspace.tsx": "테스트셋 실행/비교/리포트 생성을 담당하는 내부 QA workspace",
        "src/components/ocr/OcrAnnotator.tsx": "템플릿 영역/테이블 주석 편집용 OCR annotator 화면",
        "src/components/ocr/core/table.ts": "OCR 템플릿 테이블/행/컬럼 관련 순수 계산 로직",
        "src/components/ocr/core/ops.ts": "OCR annotator 상태 조작/유틸성 operation 로직",
        "src/components/ocr/core/export.ts": "OCR annotator/template export payload 생성 로직",
        "src/components/ocr/core/types.ts": "OCR annotator core 타입 정의",
        "src/lib/cleanJsonBuilder.ts": "OCR 결과를 Clean JSON v1 contract로 변환하는 순수 helper",
        "src/lib/markdownReportBuilder.ts": "OCR 결과를 Markdown v1 report 문자열로 변환하는 helper",
        "src/lib/ocrResultFormatters.ts": "OCR 결과 라벨/금액/table field formatting helper",
        "src/lib/invoiceTableDisplay.ts": "거래명세서 tableRows 표시 컬럼/정규화/rowIndex 정책 helper",
        "src/lib/structuredTableViewModel.ts": "structured table input을 trimmed table view model로 변환하는 순수 helper",
        "src/types/utif.d.ts": "utif 패키지 TypeScript ambient declaration",
    }
    if r in special:
        return special[r]
    if category == "api route":
        return f"Next.js API route handler: {route_path_for_entry(path)}"
    if category == "page/layout":
        return f"Next.js App Router entry: {route_path_for_entry(path)}"
    if category == "style":
        return "전역 CSS 스타일"
    if category == "store":
        return f"{name} 상태/스토리지 접근 helper"
    if category == "lib/helper":
        return f"{name} 순수 helper 또는 클라이언트 유틸"
    if category == "type":
        return f"{name} 타입 선언"
    if "Workspace" in path.name:
        return f"{path.stem} 화면 workspace 컴포넌트"
    if category.endswith("component"):
        return f"{path.stem} UI 컴포넌트"
    if category == "feature core/helper":
        return f"{path.stem} feature 내부 core/helper"
    return f"{path.stem} 역할 추가 확인 필요"


def location_assessment(path: Path, category: str, imported_by_count: int) -> tuple[str, bool, bool, bool, list[str]]:
    r = rel(path)
    notes: list[str] = []
    relocate = False
    split = False
    delete_candidate = False
    assessment = "적절"
    if r.startswith("src/components/ocr/core/"):
        assessment = "순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보"
        relocate = True
        notes.append("이동 전 import 영향 범위 확인 필요")
    if r.startswith("src/components/autorestore/"):
        assessment = "기능 위치는 대체로 적절하지만 메뉴/도메인명이 restore라면 폴더명 정리 후보"
        relocate = True
    if r == "src/components/ocr/OcrAnnotator.tsx" and imported_by_count == 0:
        assessment = "현재 import graph상 고립되어 삭제 후보이나 template/annotator 기능 복구 가능성 검증 필요"
        delete_candidate = True
    if r.startswith("src/components/common/") and imported_by_count <= 1 and path.name != "AppProviders.tsx":
        notes.append("common 배치가 과한지 feature-local 후보 검토 가능")
    return assessment, delete_candidate, relocate, split, notes


def usage_status_for(
    path: Path,
    route_reachable: bool,
    imported_by: list[str],
    barrel_exported_by: list[str],
    dynamic_signals: list[str],
    category: str,
    delete_candidate_hint: bool,
) -> str:
    r = rel(path)
    if route_reachable:
        return "USED_CONFIRMED"
    if category in {"style", "type"}:
        return "USED_INDIRECT"
    if imported_by:
        return "USED_CONFIRMED"
    if barrel_exported_by:
        return "USED_INDIRECT"
    if dynamic_signals:
        return "REVIEW_USAGE"
    if delete_candidate_hint or r == "src/components/ocr/OcrAnnotator.tsx":
        return "DELETE_CANDIDATE_SAFE_CHECK_REQUIRED"
    return "DELETE_CANDIDATE_SAFE_CHECK_REQUIRED"


def apply_keep_candidate_status(base_status: str, relocate: bool, split: bool) -> str:
    if base_status == "USED_CONFIRMED":
        if split:
            return "KEEP_BUT_SPLIT_CANDIDATE"
        if relocate:
            return "KEEP_BUT_RELOCATE_CANDIDATE"
    return base_status


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


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        return str(value if value is not None else "").replace("\n", "<br>").replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    out.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)
    return "\n".join(out)


def build_graph(files: list[Path]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, list[str]], dict[str, list[str]]]:
    file_set = {path.resolve() for path in files}
    records: dict[str, dict[str, Any]] = {}
    reverse: dict[str, list[str]] = defaultdict(list)
    barrel_exported_by: dict[str, list[str]] = defaultdict(list)
    unresolved_imports: list[dict[str, Any]] = []
    dynamic_references: dict[str, list[str]] = defaultdict(list)

    for path in files:
        text = read_text(path)
        specs = imported_symbol_summary(text)
        local_imports: list[str] = []
        external_imports: list[str] = []
        alias_imports: list[str] = []
        relative_imports: list[str] = []
        dynamic_specs = [m.group(1) for m in DYNAMIC_RE.finditer(text)]
        reexport_specs = [m.group(1) for m in re.finditer(r"""export\s+(?:type\s+)?(?:\*|\{[\s\S]*?\})\s+from\s+["']([^"']+)["']""", text)]

        for spec in specs:
            if spec.startswith("@/"):
                alias_imports.append(spec)
            elif spec.startswith("."):
                relative_imports.append(spec)
            target = resolve_local_import(path, spec, file_set)
            if target:
                local_imports.append(rel(target))
                reverse[rel(target)].append(rel(path))
                if spec in dynamic_specs:
                    dynamic_references[rel(target)].append(rel(path))
                if spec in reexport_specs or path.name in {"index.ts", "index.tsx", "export.ts"}:
                    barrel_exported_by[rel(target)].append(rel(path))
            elif spec.startswith(".") or spec.startswith("@/"):
                unresolved_imports.append({"from": rel(path), "specifier": spec})
            else:
                external_imports.append(spec)

        suffix = extension(path)
        line_count = text.count("\n") + (1 if text else 0)
        category = category_for(path, line_count)
        records[rel(path)] = {
            "path": rel(path),
            "extension": suffix,
            "lineCount": line_count,
            "sizeBytes": path.stat().st_size,
            "folder": to_posix(path.parent.relative_to(ROOT)),
            "category": category,
            "isRouteEntry": path.parent.is_relative_to(SRC / "app") and path.name in ROUTE_FILENAMES,
            "routePath": route_path_for_entry(path) if path.parent.is_relative_to(SRC / "app") and path.name in ROUTE_FILENAMES else None,
            "exports": {
                "hasDefault": bool(DEFAULT_EXPORT_RE.search(text)),
                "named": named_exports(text),
            },
            "imports": {
                "local": sorted(set(local_imports)),
                "external": sorted(set(external_imports)),
                "alias": sorted(set(alias_imports)),
                "relative": sorted(set(relative_imports)),
                "dynamic": sorted(set(dynamic_specs)),
            },
            "rawImportSpecifiers": specs,
            "barrelReexports": sorted(set(reexport_specs)),
            "importedBy": [],
            "barrelExportedBy": [],
            "dynamicUsageSignals": [],
        }

    for path_key, importers in reverse.items():
        if path_key in records:
            records[path_key]["importedBy"] = sorted(set(importers))
    for path_key, exporters in barrel_exported_by.items():
        if path_key in records:
            records[path_key]["barrelExportedBy"] = sorted(set(exporters))
    for path_key, users in dynamic_references.items():
        if path_key in records:
            records[path_key]["dynamicUsageSignals"] = sorted(set(users))

    return records, unresolved_imports, reverse, barrel_exported_by


def compute_reachability(records: dict[str, dict[str, Any]]) -> tuple[set[str], list[dict[str, Any]]]:
    entries = sorted(path for path, rec in records.items() if rec["isRouteEntry"])
    reachable: set[str] = set()
    route_summaries: list[dict[str, Any]] = []
    for entry in entries:
        seen: set[str] = set()
        queue: deque[str] = deque([entry])
        while queue:
            current = queue.popleft()
            if current in seen or current not in records:
                continue
            seen.add(current)
            reachable.add(current)
            for target in records[current]["imports"]["local"]:
                if target not in seen:
                    queue.append(target)
        route_summaries.append({
            "entry": entry,
            "routePath": records[entry]["routePath"],
            "reachableCount": len(seen),
            "directImports": records[entry]["imports"]["local"],
            "reachableFiles": sorted(seen),
        })
    return reachable, route_summaries


def folder_evaluations(records: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    folder_notes = {
        "src/app": ("Next.js App Router entry와 API route 위치로 적절", "route entry이므로 이동 위험 높음"),
        "src/components/common": ("공통 UI/provider 컴포넌트 위치로 대체로 적절", "feature 전용 컴포넌트가 섞이면 later relocate 검토"),
        "src/components/layout": ("App shell/header/sidebar layout 위치로 적절", "전역 navigation 변경 시 영향 큼"),
        "src/components/login": ("login feature UI 위치로 적절", "현 상태 유지 권장"),
        "src/components/upload": ("RunOCR 업로드/결과 feature 위치로 적절", "OcrResultPanel/UploadWorkspace는 split 후보"),
        "src/components/history": ("history feature UI 위치로 적절", "DetailHistoryView가 크면 section 분리 후보"),
        "src/components/autorestore": ("자동 복원 feature 위치", "메뉴명이 restore라면 폴더명 rename precheck 후보"),
        "src/components/ocr": ("템플릿 annotator/ocr 편집 UI feature 위치", "TemplateWorkspace/UnstructuredBuilder 경계 확인 필요"),
        "src/components/ocr/core": ("OCR annotator 내부 순수 로직 위치", "src/lib/ocr 또는 features/ocr/core 이동 후보"),
        "src/components/template": ("template builder UI 위치", "ocr/template feature boundary precheck 후보"),
        "src/components/test": ("내부 QA/test workspace 위치", "큰 파일 분리 전 사용자 확인 필요"),
        "src/lib": ("순수 helper/store 위치로 적절", "브라우저 저장소 helper와 순수 helper 혼재는 문서화 필요"),
        "src/types": ("ambient/type declaration 위치로 적절", "import graph만으로 삭제 판단 금지"),
    }
    present = sorted({"/".join(path.split("/")[:3]) if path.startswith("src/components/") else "/".join(path.split("/")[:2]) for path in records})
    out = []
    for folder in present:
        if folder == "src/components/ocr":
            # Add both parent and core if present.
            pass
        count = sum(1 for path in records if path == folder or path.startswith(folder + "/"))
        assessment, risk = folder_notes.get(folder, ("역할 추가 확인 필요", "현 단계 이동 금지"))
        out.append({
            "folder": folder,
            "fileCount": count,
            "currentRole": assessment,
            "locationAssessment": assessment,
            "risk": risk,
            "recommendation": "precheck only; no move in this task",
        })
    if any(path.startswith("src/components/ocr/core/") for path in records):
        count = sum(1 for path in records if path.startswith("src/components/ocr/core/"))
        assessment, risk = folder_notes["src/components/ocr/core"]
        out.append({"folder": "src/components/ocr/core", "fileCount": count, "currentRole": assessment, "locationAssessment": assessment, "risk": risk, "recommendation": "relocate precheck candidate"})
    return sorted(out, key=lambda item: item["folder"])


def write_reports(report: dict[str, Any]) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "path", "lineCount", "category", "usageStatus", "routeReachable",
            "importedByCount", "importsCount", "locationAssessment",
            "deleteCandidate", "relocateCandidate", "splitCandidate", "role", "notes",
        ])
        writer.writeheader()
        for item in report["files"]:
            writer.writerow({
                "path": item["path"],
                "lineCount": item["lineCount"],
                "category": item["category"],
                "usageStatus": item["usageStatus"],
                "routeReachable": item["routeReachable"],
                "importedByCount": len(item["importedBy"]),
                "importsCount": len(item["imports"]["local"]),
                "locationAssessment": item["locationAssessment"],
                "deleteCandidate": item["deleteCandidate"],
                "relocateCandidate": item["relocateCandidate"],
                "splitCandidate": item["splitCandidate"],
                "role": item["role"],
                "notes": "; ".join(item["notes"]),
            })

    status_counts = report["summary"]["usageStatusCounts"]
    inventory_rows = [
        [
            item["path"],
            item["role"],
            len(item["importedBy"]),
            len(item["imports"]["local"]),
            item["usageStatus"],
            item["locationAssessment"],
            "Y" if item["deleteCandidate"] else "",
            "Y" if item["relocateCandidate"] else "",
            "Y" if item["splitCandidate"] else "",
            "; ".join(item["notes"][:3]),
        ]
        for item in report["files"]
    ]
    large_rows = [[item["path"], item["lineCount"], item["role"], item["usageStatus"], "Y" if item["splitCandidate"] else "", "; ".join(item["notes"][:2])] for item in report["largeFiles"]]
    route_rows = [[route["routePath"], route["entry"], route["reachableCount"], ", ".join(route["directImports"][:5])] for route in report["routes"]]
    folder_rows = [[item["folder"], item["fileCount"], item["locationAssessment"], item["risk"], item["recommendation"]] for item in report["folders"]]
    delete_rows = [[item["path"], item["usageStatus"], item["role"], item["locationAssessment"], "; ".join(item["notes"][:3])] for item in report["deleteCandidates"]]
    relocate_rows = [[item["path"], item["usageStatus"], item["role"], item["locationAssessment"]] for item in report["relocateCandidates"]]
    split_rows = [[item["path"], item["lineCount"], item["role"], "; ".join(item["notes"][:3])] for item in report["splitCandidates"]]
    special_rows = [[item["path"], item["usageStatus"], item["locationAssessment"], item["role"], "; ".join(item["notes"])] for item in report["specialChecks"]]

    md = f"""# FRONTEND FILE INVENTORY USAGE PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- 파일 삭제/이동/import 수정/리팩토링 없음.
- 현재 dirty 상태는 원복하지 않음.

## 3. 생성 파일
- `tmp/codex_frontend_file_inventory_usage_precheck.py`
- `docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md`
- `docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.json`
- `docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_TABLE_20260521.csv`

## 4. 분석 범위
- projectRoot: `{report['projectRoot']}`
- included: `src/app`, `src/components`, `src/lib`, `src/types`, 기타 `src` 하위 대상 확장자
- excluded: node_modules, .next, dist, build, public, backup, tmp, docs

## 5. 전체 파일 수 요약
- totalFiles: {report['totalFiles']}
- usageStatusCounts: `{status_counts}`
- routeReachableFiles: {report['summary']['routeReachableCount']}
- unresolved local imports: {len(report['unresolvedImports'])}

## 6. Route Reachability 요약
{md_table(['route', 'entry', 'reachableCount', 'directImports'], route_rows)}

## 7. Import/Export Graph 요약
- local import edges: {report['summary']['localImportEdgeCount']}
- alias import users: {report['summary']['aliasImportUserCount']}
- relative import users: {report['summary']['relativeImportUserCount']}
- barrel/export re-export files: {report['summary']['barrelFileCount']}
- dynamic import/require signals: {report['summary']['dynamicSignalCount']}

## 8. 파일별 인벤토리 표
{md_table(['path', 'role', 'importedBy', 'imports', 'usageStatus', 'locationAssessment', 'delete', 'relocate', 'split', 'notes'], inventory_rows)}

## 9. 사용 중 파일 목록
- USED_CONFIRMED: {status_counts.get('USED_CONFIRMED', 0)}
- USED_INDIRECT: {status_counts.get('USED_INDIRECT', 0)}

## 10. 미사용 의심/삭제 후보 목록
{md_table(['path', 'status', 'role', 'locationAssessment', 'notes'], delete_rows)}

## 11. 위치 조정 후보 목록
{md_table(['path', 'status', 'role', 'locationAssessment'], relocate_rows)}

## 12. 큰 파일 TOP 20
{md_table(['path', 'lines', 'role', 'usageStatus', 'split', 'notes'], large_rows)}

## 13. 폴더 구조 평가
{md_table(['folder', 'files', 'assessment', 'risk', 'recommendation'], folder_rows)}

## 14. 특별 확인 대상 결과
{md_table(['path', 'usageStatus', 'locationAssessment', 'role', 'notes'], special_rows)}

## 15. 삭제 전 검증 계획
1. import graph 재확인
2. grep/string reference 재확인
3. dynamic import/require 확인
4. route reachability 확인
5. `npm run typecheck`
6. `npm run build`
7. 주요 화면 수동 확인
8. 삭제 전 백업
9. 삭제 후 diff 확인

## 16. 이동 전 검증 계획
1. import 경로 영향 범위 확인
2. alias import와 상대경로 정책 결정
3. barrel export 영향 확인
4. 이동 전 백업
5. `npm run typecheck`
6. `npm run build`
7. 기능 화면 확인

## 17. 다음 정리 우선순위
{chr(10).join(f'{idx + 1}. {item}' for idx, item in enumerate(report['recommendations']))}

## 18. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| {report['typecheck']['command']} | {report['typecheck']['status']} | {report['typecheck']['exitCode']} | {report['typecheck']['durationSeconds']} | {report['typecheck']['knownStderrNoise']} |
| {report['build']['command']} | {report['build']['status']} | {report['build']['exitCode']} | {report['build']['durationSeconds']} | {report['build']['knownStderrNoise']} |

## 19. Known Stderr Noise
- `ESLint: nextVitals is not iterable` observed: `{report['knownStderrNoise']['observed']}`
- build exit code: `{report['knownStderrNoise']['buildExitCode']}`

## 20. 최종 결론
- 운영 코드 변경 없이 src 파일 인벤토리와 사용처 precheck를 완료했다.
- 삭제/이동 후보는 즉시 조치 대상이 아니라 별도 검증 작업 대상이다.
- TestWorkspace 정리는 사용자 확인 후 별도 작업으로 진행해야 한다.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    print(f"[start] {TASK}", flush=True)
    files = collect_files()
    print(f"[scan] files={len(files)}", flush=True)
    records, unresolved_imports, _reverse, _barrel = build_graph(files)
    reachable, routes = compute_reachability(records)

    for path_key, rec in records.items():
        rec["routeReachable"] = path_key in reachable
        assessment, delete_hint, relocate, split, notes = location_assessment(Path(ROOT / path_key), rec["category"], len(rec["importedBy"]))
        if rec["lineCount"] >= 500 and rec["category"] not in {"style", "type"}:
            split = True
            notes.append("line count >= 500; 분리 후보")
        if path_key == "src/components/test/TestWorkspace.tsx":
            notes.append("TestWorkspace 정리는 사용자 확인 후 별도 작업 필요")
        if path_key == "src/components/upload/OcrResultPanel.tsx":
            notes.append("최근 Clean JSON/Markdown/formatter/table view model helper 분리와 연결됨")
        if path_key == "src/types/utif.d.ts":
            notes.append("ambient declaration은 import graph만으로 삭제 판단 금지")
        base_usage_status = usage_status_for(
            Path(ROOT / path_key),
            rec["routeReachable"],
            rec["importedBy"],
            rec["barrelExportedBy"],
            rec["dynamicUsageSignals"],
            rec["category"],
            delete_hint,
        )
        rec["usageStatus"] = apply_keep_candidate_status(base_usage_status, relocate, split)
        rec["locationAssessment"] = assessment
        rec["deleteCandidate"] = rec["usageStatus"] == "DELETE_CANDIDATE_SAFE_CHECK_REQUIRED"
        rec["relocateCandidate"] = relocate or rec["usageStatus"] == "KEEP_BUT_RELOCATE_CANDIDATE"
        rec["splitCandidate"] = split
        rec["role"] = role_for(Path(ROOT / path_key), rec["category"], rec["exports"], rec["lineCount"])
        rec["notes"] = notes

    file_items = [records[key] for key in sorted(records)]
    usage_counts: dict[str, int] = defaultdict(int)
    for item in file_items:
        usage_counts[item["usageStatus"]] += 1

    special_paths = [
        "src/components/ocr/OcrAnnotator.tsx",
        "src/types/utif.d.ts",
        "src/components/test/TestWorkspace.tsx",
        "src/components/upload/OcrResultPanel.tsx",
        "src/lib/cleanJsonBuilder.ts",
        "src/lib/markdownReportBuilder.ts",
        "src/lib/ocrResultFormatters.ts",
        "src/lib/structuredTableViewModel.ts",
        "src/lib/invoiceTableDisplay.ts",
    ]
    special_checks = [records[path] for path in special_paths if path in records]
    special_checks.extend(item for item in file_items if item["path"].startswith("src/components/ocr/core/"))

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
        "projectRoot": str(ROOT),
        "analysisScope": ["src/app", "src/components", "src/lib", "src/hooks(if present)", "src/types", "other src files"],
        "totalFiles": len(file_items),
        "files": file_items,
        "routes": routes,
        "folders": folder_evaluations(records),
        "largeFiles": sorted(file_items, key=lambda item: item["lineCount"], reverse=True)[:20],
        "deleteCandidates": [item for item in file_items if item["deleteCandidate"]],
        "relocateCandidates": [item for item in file_items if item["relocateCandidate"]],
        "splitCandidates": [item for item in file_items if item["splitCandidate"]],
        "specialChecks": special_checks,
        "unresolvedImports": unresolved_imports,
        "typecheck": typecheck,
        "build": build,
        "knownStderrNoise": {
            "message": "ESLint: nextVitals is not iterable",
            "observed": build["knownStderrNoise"],
            "buildExitCode": build["exitCode"],
        },
        "summary": {
            "usageStatusCounts": dict(sorted(usage_counts.items())),
            "routeReachableCount": sum(1 for item in file_items if item["routeReachable"]),
            "localImportEdgeCount": sum(len(item["imports"]["local"]) for item in file_items),
            "aliasImportUserCount": sum(1 for item in file_items if item["imports"]["alias"]),
            "relativeImportUserCount": sum(1 for item in file_items if item["imports"]["relative"]),
            "barrelFileCount": sum(1 for item in file_items if item["barrelReexports"] or item["path"].endswith("/export.ts") or item["path"].endswith("/index.ts")),
            "dynamicSignalCount": sum(len(item["imports"]["dynamic"]) for item in file_items),
        },
        "recommendations": [
            "삭제 후보 안전 검증 작업을 별도 수행하되 이번 리포트 후보를 즉시 삭제하지 않는다.",
            "components/ocr/core 순수 로직 위치 조정 precheck를 별도 수행한다.",
            "OcrResultPanel Cycle 1 close-out은 table view model helper 적용 이후 진행한다.",
            "TestWorkspace summary/export/tableRows/UI 섹션 분리는 사용자 확인 후 별도 precheck로 진행한다.",
            "UploadWorkspace 책임 분리 precheck를 수행한다.",
            "History Detail tableRows 표시/분리 precheck를 수행한다.",
            "autorestore/restore 네이밍 정리 precheck를 수행한다.",
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
