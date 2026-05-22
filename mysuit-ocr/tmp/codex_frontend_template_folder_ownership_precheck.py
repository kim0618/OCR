from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS = PROJECT_ROOT / "docs"
MD_PATH = DOCS / "FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_PRECHECK_20260522.md"
JSON_PATH = DOCS / "FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_PRECHECK_20260522.json"
CSV_PATH = DOCS / "FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_MAP_20260522.csv"


CANDIDATE_PATHS = [
    "src/app/template/page.tsx",
    "src/app/ocr/page.tsx",
    "src/components/ocr/TemplateWorkspace.tsx",
    "src/components/ocr/OcrAnnotator.tsx",
    "src/components/ocr/OcrCanvasPane.tsx",
    "src/components/ocr/OcrRightPanel.tsx",
    "src/components/ocr/core/types.ts",
    "src/components/ocr/core/table.ts",
    "src/components/ocr/core/ops.ts",
    "src/components/ocr/core/export.ts",
    "src/components/template/UnstructuredBuilder.tsx",
    "src/components/common/FileDropzone.tsx",
    "src/components/common/RequireLogin.tsx",
    "src/components/runocr/RunOcrWorkspace.tsx",
    "src/components/test/TestWorkspace.tsx",
]


ROLE_OVERRIDES = {
    "src/app/template/page.tsx": {
        "role": "Template tab route entry",
        "ownership": "TEMPLATE_WORKSPACE",
        "targetPath": "src/app/template/page.tsx",
        "risk": "MEDIUM",
        "notes": "Template route의 실제 entry. OcrAnnotator와 UnstructuredBuilder를 직접 조립한다.",
    },
    "src/app/ocr/page.tsx": {
        "role": "legacy /ocr route entry",
        "ownership": "REVIEW_NEEDED",
        "targetPath": "src/app/ocr/page.tsx",
        "risk": "HIGH",
        "notes": "OcrAnnotator와 TemplateWorkspace를 직접 import한다. Template 이동 시 legacy route 유지 여부를 먼저 결정해야 한다.",
    },
    "src/components/ocr/TemplateWorkspace.tsx": {
        "role": "Template workspace wrapper",
        "ownership": "TEMPLATE_WORKSPACE",
        "targetPath": "src/components/template/TemplateWorkspace.tsx",
        "risk": "LOW",
        "notes": "현재 /ocr route에서 사용. 목표 구조상 components/template 루트로 이동 후보.",
    },
    "src/components/ocr/OcrAnnotator.tsx": {
        "role": "Template annotation/editor workspace",
        "ownership": "TEMPLATE_PRIVATE_UI",
        "targetPath": "src/components/template/ui/OcrAnnotator.tsx",
        "risk": "HIGH",
        "notes": "Template page와 legacy /ocr route에서 dynamic import. canvas/right panel/core/save 흐름을 품고 있어 Phase 1에서는 보류 권장.",
    },
    "src/components/ocr/OcrCanvasPane.tsx": {
        "role": "OCR region canvas editor/viewer",
        "ownership": "RUNOCR_SHARED_CANDIDATE",
        "targetPath": "src/common/ui/OcrCanvasPane.tsx 또는 src/components/template/ui/OcrCanvasPane.tsx",
        "risk": "VERY_HIGH",
        "notes": "Template editor와 RunOCR Custom tab이 동시에 사용한다. 바로 template 전용으로 이동하면 RunOCR import 영향이 크다.",
    },
    "src/components/ocr/OcrRightPanel.tsx": {
        "role": "Template region/right-side property panel",
        "ownership": "TEMPLATE_PRIVATE_UI",
        "targetPath": "src/components/template/ui/TemplateRightPanel.tsx",
        "risk": "HIGH",
        "notes": "Template region metadata/documentType/table controls에 가깝다. rename은 별도 phase 권장.",
    },
    "src/components/ocr/core/types.ts": {
        "role": "Template/canvas region type definitions",
        "ownership": "COMMON_UTIL_CANDIDATE",
        "targetPath": "src/common/types/ocrCanvas.ts 또는 src/components/template/utils/types.ts",
        "risk": "HIGH",
        "notes": "RunOCR OcrCanvasPane도 의존하므로 common/types 후보. common 이동은 feature 안정화 후.",
    },
    "src/components/ocr/core/table.ts": {
        "role": "Template table/column guide helpers",
        "ownership": "TEMPLATE_PRIVATE_UTIL",
        "targetPath": "src/components/template/utils/table.ts",
        "risk": "MEDIUM",
        "notes": "Template table column definition의 기반 후보.",
    },
    "src/components/ocr/core/ops.ts": {
        "role": "Template region editing operations",
        "ownership": "TEMPLATE_PRIVATE_UTIL",
        "targetPath": "src/components/template/utils/ops.ts",
        "risk": "HIGH",
        "notes": "region add/update/delete/geometry 성격. OcrAnnotator와 같이 이동하는 phase가 안전하다.",
    },
    "src/components/ocr/core/export.ts": {
        "role": "Template export/serialization helper",
        "ownership": "TEMPLATE_PRIVATE_UTIL",
        "targetPath": "src/components/template/utils/templateMapper.ts",
        "risk": "MEDIUM",
        "notes": "목표 구조의 templateMapper.ts 후보. templates.json contract와 연결되어 검증 필요.",
    },
    "src/components/template/UnstructuredBuilder.tsx": {
        "role": "Unstructured template builder UI",
        "ownership": "TEMPLATE_PRIVATE_UI",
        "targetPath": "src/components/template/ui/UnstructuredBuilder.tsx",
        "risk": "MEDIUM",
        "notes": "이미 template 폴더에 있으나 ui 하위로 이동 후보.",
    },
    "src/components/common/FileDropzone.tsx": {
        "role": "Shared file dropzone UI",
        "ownership": "COMMON_UI_CANDIDATE",
        "targetPath": "src/common/ui/FileDropzone.tsx",
        "risk": "MEDIUM",
        "notes": "RunOCR에서 사용. Template에서도 재사용 가능하지만 common 이동은 별도 phase.",
    },
    "src/components/common/RequireLogin.tsx": {
        "role": "Shared login guard UI",
        "ownership": "COMMON_UI_CANDIDATE",
        "targetPath": "src/common/ui/RequireLogin.tsx",
        "risk": "LOW",
        "notes": "route guard 성격. Template 전용 아님.",
    },
    "src/components/runocr/RunOcrWorkspace.tsx": {
        "role": "RunOCR workspace using OcrCanvasPane dynamically",
        "ownership": "DO_NOT_MOVE_YET",
        "targetPath": "src/components/runocr/RunOcrWorkspace.tsx",
        "risk": "VERY_HIGH",
        "notes": "OcrCanvasPane 공유 여부 판단 때문에 읽기 대상. 이번 Template move 범위 아님.",
    },
    "src/components/test/TestWorkspace.tsx": {
        "role": "Internal QA/test workspace",
        "ownership": "TEST_ONLY_OR_TEST_SHARED",
        "targetPath": "NO_MOVE_WITHOUT_USER_CONFIRMATION",
        "risk": "VERY_HIGH",
        "notes": "사용자 확인 전 작업 금지. 이번 precheck에서는 읽기/영향 기록만.",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_command(args: list[str]) -> dict:
    print(f"$ {' '.join(args)}")
    proc = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        shell=False,
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    return {
        "command": " ".join(args),
        "exitCode": proc.returncode,
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "stdoutTail": proc.stdout[-4000:],
        "stderrTail": proc.stderr[-4000:],
        "knownStderrNoise": "ESLint: nextVitals is not iterable" if "nextVitals is not iterable" in proc.stderr else None,
    }


def git_status() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        shell=False,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def all_source_files() -> list[Path]:
    exts = {".ts", ".tsx", ".js", ".jsx", ".css", ".d.ts"}
    return [p for p in (PROJECT_ROOT / "src").rglob("*") if p.is_file() and p.suffix in exts]


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_imports(text: str) -> list[str]:
    imports: list[str] = []
    for m in re.finditer(r"import(?:\s+type)?(?:[\s\S]*?)from\s+[\"']([^\"']+)[\"']", text):
        imports.append(m.group(1))
    for m in re.finditer(r"import\(\s*[\"']([^\"']+)[\"']\s*\)", text):
        imports.append(m.group(1))
    return sorted(set(imports))


def normalize_import(source_file: Path, spec: str) -> str | None:
    if not (spec.startswith(".") or spec.startswith("@/")):
        return None
    if spec.startswith("@/"):
        base = PROJECT_ROOT / "src" / spec[2:]
    else:
        base = (source_file.parent / spec).resolve()
    candidates = [
        base,
        base.with_suffix(".ts"),
        base.with_suffix(".tsx"),
        base.with_suffix(".js"),
        base.with_suffix(".jsx"),
        base / "index.ts",
        base / "index.tsx",
    ]
    for cand in candidates:
        if cand.exists() and cand.is_file():
            try:
                return rel(cand)
            except ValueError:
                return None
    return None


def build_graph() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    imports_by: dict[str, list[str]] = {}
    imported_by: dict[str, list[str]] = {}
    for path in all_source_files():
        source_rel = rel(path)
        specs = extract_imports(read(path))
        resolved = []
        for spec in specs:
            target = normalize_import(path, spec)
            if target:
                resolved.append(target)
                imported_by.setdefault(target, []).append(source_rel)
        imports_by[source_rel] = sorted(set(resolved))
    return imports_by, {k: sorted(set(v)) for k, v in imported_by.items()}


def exports_for(path: Path) -> list[str]:
    text = read(path)
    out: list[str] = []
    for m in re.finditer(r"export\s+(?:default\s+)?(?:function|const|type|interface|class)\s+(\w+)", text):
        out.append(m.group(1))
    if "export default" in text and not any(x.startswith("default") for x in out):
        out.append("default")
    return sorted(set(out))


def route_reachable(path_rel: str, imported_by: dict[str, list[str]]) -> bool:
    seen = set()
    stack = [path_rel]
    route_prefix = ("src/app/",)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        if cur.startswith(route_prefix):
            return True
        stack.extend(imported_by.get(cur, []))
    return False


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    DOCS.mkdir(parents=True, exist_ok=True)
    imports_by, imported_by = build_graph()

    files = []
    for path_rel in CANDIDATE_PATHS:
        path = PROJECT_ROOT / path_rel
        info = ROLE_OVERRIDES[path_rel]
        text = read(path) if path.exists() else ""
        imports = imports_by.get(path_rel, [])
        ib = imported_by.get(path_rel, [])
        files.append(
            {
                "currentPath": path_rel,
                "exists": path.exists(),
                "lineCount": len(text.splitlines()) if text else 0,
                "sizeBytes": path.stat().st_size if path.exists() else 0,
                "role": info["role"],
                "imports": imports,
                "importedBy": ib,
                "exports": exports_for(path) if path.exists() else [],
                "routeReachable": route_reachable(path_rel, imported_by),
                "ownership": info["ownership"],
                "targetPath": info["targetPath"],
                "risk": info["risk"],
                "riskReason": risk_reason(info["risk"], info["ownership"], ib),
                "mitigation": mitigation(info["ownership"], info["risk"]),
                "requiredValidation": validation_for(info["ownership"], info["risk"]),
                "notes": info["notes"],
            }
        )

    phase1 = {
        "recommendation": "A. route/workspace만 먼저 이동",
        "scope": [
            "src/components/ocr/TemplateWorkspace.tsx -> src/components/template/TemplateWorkspace.tsx",
            "src/app/ocr/page.tsx 및 관련 route import만 최소 수정",
            "OcrAnnotator/OcrCanvasPane/OcrRightPanel/core는 그대로 둔다",
            "UnstructuredBuilder ui 하위 이동은 Phase 1B 또는 Phase 2로 둔다",
        ],
        "doNotInclude": [
            "OcrAnnotator 이동",
            "OcrCanvasPane 이동",
            "OcrRightPanel rename",
            "components/ocr/core 이동",
            "TestWorkspace 관련 이동",
            "common/ui 또는 common/utils 이동",
        ],
        "risk": "LOW_TO_MEDIUM",
        "reason": "첫 이동은 import 영향이 작아야 한다. canvas/annotation/core는 RunOCR와 legacy route까지 얽혀 있어 별도 phase가 안전하다.",
    }

    future_template_column_files = [
        {
            "path": "src/components/template/ui/TemplateTableColumnEditor.tsx",
            "purpose": "테이블 컬럼 정의/순서/label 편집 UI",
        },
        {
            "path": "src/components/template/utils/recommendTemplateColumns.ts",
            "purpose": "OCR/header 기반 자동 컬럼 추천",
        },
        {
            "path": "src/components/template/utils/mapHeaderToCanonicalKey.ts",
            "purpose": "표 헤더를 canonical key로 매핑",
        },
        {
            "path": "src/components/template/utils/templateColumnStore.ts",
            "purpose": "template column definition 저장/로드 후보",
        },
        {
            "path": "src/common/utils/invoiceTableDisplay.ts",
            "purpose": "현재 display policy와 연결. common 이동은 feature 안정화 후 검토.",
        },
    ]

    common_candidates = [
        {
            "path": "src/components/ocr/OcrCanvasPane.tsx",
            "targetPath": "src/common/ui/OcrCanvasPane.tsx",
            "reason": "Template editor와 RunOCR Custom tab이 공유한다.",
            "timing": "feature 폴더 안정화 후",
        },
        {
            "path": "src/components/ocr/core/types.ts",
            "targetPath": "src/common/types/ocrCanvas.ts",
            "reason": "Region/FieldType type은 Template과 RunOCR canvas 양쪽에 걸친다.",
            "timing": "OcrCanvasPane ownership 확정 후",
        },
        {
            "path": "src/components/common/FileDropzone.tsx",
            "targetPath": "src/common/ui/FileDropzone.tsx",
            "reason": "RunOCR에서 쓰는 shared UI이며 Template에서도 재사용 가능하다.",
            "timing": "common 폴더 전환 phase",
        },
        {
            "path": "src/components/common/RequireLogin.tsx",
            "targetPath": "src/common/ui/RequireLogin.tsx",
            "reason": "feature 전용이 아닌 route guard.",
            "timing": "common 폴더 전환 phase",
        },
    ]

    validation_plan = [
        "npm run typecheck",
        "npm run build",
        "Template route smoke: /template",
        "Legacy route decision/smoke: /ocr if retained",
        "RunOCR smoke if OcrCanvasPane import changes",
        "table view model runner",
        "Clean JSON runner",
        "Markdown fixture check",
        "diff review: move/import-only change 확인",
    ]

    dirty_status = git_status()
    typecheck = run_command(["npm.cmd", "run", "typecheck"])
    build = run_command(["npm.cmd", "run", "build"])

    report = {
        "generatedAt": now_iso(),
        "projectRoot": str(PROJECT_ROOT),
        "codeModified": False,
        "dirtyStatus": dirty_status,
        "files": files,
        "phase1Recommendation": phase1,
        "futureTemplateColumnFiles": future_template_column_files,
        "commonCandidates": common_candidates,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "Template folder move Phase 1: TemplateWorkspace route/workspace 이동만 진행",
            "OcrAnnotator/OcrRightPanel/core 이동은 별도 Phase 2 precheck 후 진행",
            "OcrCanvasPane common/shared ownership은 RunOCR 영향 분석 후 결정",
            "TPL-95328E52 dirty 영향 precheck 유지",
            "TestWorkspace는 사용자 확인 전 이동/수정 금지",
        ],
    }

    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CSV_PATH.write_text(make_csv(files), encoding="utf-8-sig")
    MD_PATH.write_text(make_md(report), encoding="utf-8")

    print(json.dumps({"md": str(MD_PATH), "json": str(JSON_PATH), "csv": str(CSV_PATH)}, ensure_ascii=False, indent=2))
    return 0 if typecheck["exitCode"] == 0 and build["exitCode"] == 0 else 1


def risk_reason(risk: str, ownership: str, imported_by: list[str]) -> str:
    if risk == "VERY_HIGH":
        return "RunOCR/Test/legacy route 공유 또는 canvas/coordinate 로직으로 회귀 위험이 크다."
    if risk == "HIGH":
        return "canvas/annotation/save/template metadata 경로 또는 다중 route import가 있다."
    if risk == "MEDIUM":
        return "import 수정은 제한적이지만 route smoke와 typecheck가 필요하다."
    return "단일 workspace/import 이동 중심으로 영향이 작다."


def mitigation(ownership: str, risk: str) -> str:
    if "TEST" in ownership:
        return "사용자 확인 전 이동하지 않는다."
    if risk in {"HIGH", "VERY_HIGH"}:
        return "Phase 1에서 제외하고 별도 precheck, route smoke, RunOCR smoke를 먼저 수행한다."
    return "move/import-only patch로 제한하고 typecheck/build를 실행한다."


def validation_for(ownership: str, risk: str) -> list[str]:
    checks = ["npm run typecheck", "npm run build"]
    if ownership.startswith("TEMPLATE") or ownership == "TEMPLATE_WORKSPACE":
        checks.append("/template manual smoke")
    if ownership in {"RUNOCR_SHARED_CANDIDATE", "COMMON_UTIL_CANDIDATE"}:
        checks.append("/runocr manual smoke")
    if risk in {"HIGH", "VERY_HIGH"}:
        checks.extend(["canvas interaction smoke", "template save/load smoke"])
    return checks


def make_csv(files: list[dict]) -> str:
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "currentPath",
            "lineCount",
            "role",
            "importedBy",
            "ownership",
            "targetPath",
            "risk",
            "notes",
        ],
    )
    writer.writeheader()
    for f in files:
        writer.writerow(
            {
                "currentPath": f["currentPath"],
                "lineCount": f["lineCount"],
                "role": f["role"],
                "importedBy": "; ".join(f["importedBy"]),
                "ownership": f["ownership"],
                "targetPath": f["targetPath"],
                "risk": f["risk"],
                "notes": f["notes"],
            }
        )
    return buf.getvalue()


def make_md(report: dict) -> str:
    files = report["files"]
    file_rows = "\n".join(
        f"| `{f['currentPath']}` | {f['lineCount']} | {f['ownership']} | `{f['targetPath']}` | {f['risk']} | {f['notes']} |"
        for f in files
    )
    imported_rows = "\n".join(
        f"| `{f['currentPath']}` | {', '.join(f['importedBy']) or '-'} | {', '.join(f['imports']) or '-'} |"
        for f in files
    )
    common_rows = "\n".join(
        f"| `{c['path']}` | `{c['targetPath']}` | {c['reason']} | {c['timing']} |"
        for c in report["commonCandidates"]
    )
    future_rows = "\n".join(
        f"| `{item['path']}` | {item['purpose']} |"
        for item in report["futureTemplateColumnFiles"]
    )
    return f"""# FRONTEND TEMPLATE FOLDER OWNERSHIP PRECHECK 20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/리팩토링/주석 추가/fixture/templates/backend 수정: 없음
- 현재 dirty 상태는 되돌리지 않았다.

## 3. 생성 파일
- `tmp/codex_frontend_template_folder_ownership_precheck.py`
- `docs/FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/*`
- `src/components/ocr/core/*`
- `src/components/template/*`
- `src/app/template/page.tsx`
- `src/app/ocr/page.tsx`
- `src/app/runocr/page.tsx`
- `src/components/runocr/*`
- `src/components/test/TestWorkspace.tsx` 읽기 전용
- `src/lib/*`, `src/types/*` 참고

## 5. Template 관련 파일 목록
| currentPath | lines | ownership | targetPath | risk | notes |
| --- | ---: | --- | --- | --- | --- |
{file_rows}

## 6. importedBy 분석
| file | importedBy | imports |
| --- | --- | --- |
{imported_rows}

## 7. ownership 분류
- `TEMPLATE_WORKSPACE`: route/workspace entry 성격. Phase 1 이동 후보.
- `TEMPLATE_PRIVATE_UI`: Template 전용 UI. annotation/canvas/save와 얽힌 파일은 Phase 2 이후.
- `TEMPLATE_PRIVATE_UTIL`: Template 전용 operation/export/table helper.
- `RUNOCR_SHARED_CANDIDATE`: RunOCR와 Template이 공유 중이라 바로 template 전용 이동 금지.
- `COMMON_UI_CANDIDATE` / `COMMON_UTIL_CANDIDATE`: feature 안정화 후 common 전환 후보.
- `TEST_ONLY_OR_TEST_SHARED`: 사용자 확인 전 이동 금지.

## 8. targetPath 제안
상세 targetPath는 위 표와 JSON/CSV에 기록했다. 핵심은 `TemplateWorkspace`는 `components/template` 루트로, Template 전용 UI는 `components/template/ui`, Template 전용 로직은 `components/template/utils`, 공유 canvas/type은 common 후보로 둔다는 것이다.

## 9. 위험도 평가
- LOW: `TemplateWorkspace` route/workspace 이동처럼 import 영향이 작음.
- MEDIUM: `UnstructuredBuilder`, `export.ts`, `table.ts`처럼 제한적 import 수정과 route smoke가 필요함.
- HIGH: `OcrAnnotator`, `OcrRightPanel`, `ops.ts`처럼 annotation/save/region metadata와 얽힘.
- VERY_HIGH: `OcrCanvasPane`, `TestWorkspace`, RunOCR 공유 파일처럼 다중 feature 영향이 큼.

## 10. Phase 1 이동 추천
- 추천: {report['phase1Recommendation']['recommendation']}
- 범위:
{chr(10).join(f"  - {item}" for item in report['phase1Recommendation']['scope'])}
- Phase 1에서 제외:
{chr(10).join(f"  - {item}" for item in report['phase1Recommendation']['doNotInclude'])}
- 위험도: {report['phase1Recommendation']['risk']}
- 이유: {report['phase1Recommendation']['reason']}

## 11. Template table column definition 대비 파일 위치
| proposedPath | purpose |
| --- | --- |
{future_rows}

## 12. common 후보
| current | target | reason | timing |
| --- | --- | --- | --- |
{common_rows}

## 13. dirty 상태
```text
{chr(10).join(report['dirtyStatus'])}
```

## 14. typecheck/build 결과
- `npm run typecheck`: {report['typecheck']['status']} (exit {report['typecheck']['exitCode']})
- `npm run build`: {report['build']['status']} (exit {report['build']['exitCode']})
- known stderr noise: {report['build']['knownStderrNoise'] or '없음'}

## 15. 다음 작업 제안
{chr(10).join(f"{idx}. {item}" for idx, item in enumerate(report['nextSteps'], start=1))}
"""


if __name__ == "__main__":
    raise SystemExit(main())
