from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "docs" / "FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522.json"
REPORT_CSV = ROOT / "docs" / "FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_MAP_20260522.csv"

ANNOTATOR = Path("src/components/template/ui/OcrAnnotator.tsx")
TARGET_FILES = [
    ANNOTATOR,
    Path("src/components/template/ui/TemplateRightPanel.tsx"),
    Path("src/common/ui/OcrCanvasPane.tsx"),
    Path("src/components/template/TemplateWorkspace.tsx"),
    Path("src/app/ocr/page.tsx"),
    Path("src/app/template/page.tsx"),
    Path("src/components/runocr/RunOcrWorkspace.tsx"),
    Path("src/components/test/TestWorkspace.tsx"),
    Path("src/components/template/utils/buildTemplateExportPayload.ts"),
]

REFERENCE_REPORTS = [
    Path("docs/FRONTEND_STRUCTURE_4B_TEMPLATE_EDITOR_UI_MOVE_20260522.md"),
    Path("docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.md"),
    Path("docs/FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME_20260522.md"),
    Path("docs/FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_PRECHECK_20260522.md"),
]

SEARCH_PATTERNS = [
    "OcrAnnotator",
    "TemplateAnnotator",
    "components/template/ui/OcrAnnotator",
    "components/ocr/OcrAnnotator",
    "./OcrAnnotator",
    "../ui/OcrAnnotator",
    "@/components/template/ui/OcrAnnotator",
]


def rel(path: Path) -> str:
    return path.as_posix()


def read(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def lines(path: Path) -> list[str]:
    return read(path).splitlines()


def run_git_status() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def extract_imports(text: str) -> list[str]:
    imports: list[str] = []
    for match in re.finditer(r"^import\s+.*?;\s*$", text, flags=re.MULTILINE | re.DOTALL):
        imports.append(" ".join(match.group(0).split()))
    return imports


def extract_exports(text: str) -> list[str]:
    exports: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("export "):
            exports.append(stripped)
    return exports


def extract_props(text: str) -> dict[str, object]:
    signature = re.search(r"export default function OcrAnnotator\((.*?)\)\s*\{", text, flags=re.DOTALL)
    inline_props = signature.group(1).strip() if signature else ""
    return {
        "style": "inline destructured props type",
        "interfaceOrTypeName": None,
        "signature": " ".join(inline_props.split()),
        "props": ["selectedTemplate?: any | null", "selectedTemplateId?: string | null"],
    }


def classify_feature(path: Path) -> str:
    p = rel(path)
    if "/template/" in p or p.startswith("src/app/template"):
        return "template"
    if p.startswith("src/app/ocr"):
        return "route"
    if "/runocr/" in p:
        return "runocr"
    if "/test/" in p:
        return "test"
    return "unknown"


def find_imported_by() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    candidate_files = [p for p in (ROOT / "src").rglob("*") if p.suffix in {".ts", ".tsx", ".js", ".jsx"}]
    for abs_path in sorted(candidate_files):
        path = abs_path.relative_to(ROOT)
        text = abs_path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"import\((['\"])(?P<dynamic>[^'\"]*OcrAnnotator[^'\"]*)\1\)|import\s+(?P<static>[^;]*?from\s+['\"][^'\"]*OcrAnnotator[^'\"]*['\"])", text):
            import_path = match.group("dynamic") or re.search(r"['\"]([^'\"]*OcrAnnotator[^'\"]*)['\"]", match.group(0)).group(1)
            is_dynamic = bool(match.group("dynamic"))
            if path == ANNOTATOR:
                continue
            results.append({
                "file": rel(path),
                "importPath": import_path,
                "importKind": "dynamic" if is_dynamic else "static",
                "usagePurpose": "route-level client-only Template annotator entry" if is_dynamic else "component import",
                "feature": classify_feature(path),
                "needsImportUpdateOnRename": True,
            })
    return results


def find_string_hits() -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    for base in [ROOT / "src", ROOT / "docs"]:
        if not base.exists():
            continue
        for abs_path in sorted(p for p in base.rglob("*") if p.is_file() and p.suffix in {".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".csv"}):
            path = abs_path.relative_to(ROOT)
            text = abs_path.read_text(encoding="utf-8", errors="replace")
            for pattern in SEARCH_PATTERNS:
                if pattern in text:
                    hits.append({"file": rel(path), "pattern": pattern})
    return hits


def route_impact() -> list[dict[str, object]]:
    impacts: list[dict[str, object]] = []
    for route in [Path("src/app/ocr/page.tsx"), Path("src/app/template/page.tsx")]:
        text = read(route)
        dynamic_match = re.search(r"dynamic\(\s*\(\)\s*=>\s*import\((['\"])(?P<path>[^'\"]+)\1\)", text, re.DOTALL)
        usage_count = len(re.findall(r"<OcrAnnotator\b", text))
        impacts.append({
            "file": rel(route),
            "dynamicImport": bool(dynamic_match),
            "importPath": dynamic_match.group("path") if dynamic_match else None,
            "usageCount": usage_count,
            "policyImpact": "No route policy change needed; rename only changes the dynamic import path and optionally local symbol.",
            "separateOcrRoutePolicy": route.as_posix().startswith("src/app/ocr"),
        })
    return impacts


def command_result_from_log(command_name: str) -> dict[str, object]:
    result_path = ROOT / "tmp" / f"codex_template_annotator_rename_precheck_{command_name}.json"
    if not result_path.exists():
        return {"command": f"npm run {command_name}", "exitCode": None, "status": "NOT_RUN"}
    return json.loads(result_path.read_text(encoding="utf-8-sig"))


def main() -> None:
    annotator_text = read(ANNOTATOR)
    imported_by = find_imported_by()
    string_hits = find_string_hits()
    dirty_status = run_git_status()

    annotator = {
        "currentPath": rel(ANNOTATOR),
        "lineCount": len(lines(ANNOTATOR)),
        "imports": extract_imports(annotator_text),
        "exports": extract_exports(annotator_text),
        "props": extract_props(annotator_text),
        "importedBy": imported_by,
        "routeImpact": route_impact(),
        "role": {
            "summary": "Template editor annotator that coordinates upload/PDF rendering, template metadata, region drawing state, right-panel editing, local/IndexedDB image persistence, and template save/export payload creation.",
            "templateOnly": True,
            "templateWorkspaceRelationship": "Used indirectly by /ocr when TemplateWorkspace switches from list mode to editor mode; TemplateWorkspace itself does not import OcrAnnotator.",
            "appOcrRelationship": "Legacy /ocr route dynamically imports and renders it for new-template editor mode.",
            "appTemplateRelationship": "/template route dynamically imports and renders it for template create/edit mode.",
            "ocrCanvasPaneRelationship": "Parent of common OcrCanvasPane; passes image refs, loaded image, region state, selection, table guide targets, draw mode, and zoom.",
            "templateRightPanelRelationship": "Parent of TemplateRightPanel; passes template metadata, document type, selected region state, table target setters, and update/delete callbacks.",
            "buildTemplateExportPayloadRelationship": "Directly imports buildExportPayload and memoizes the save/export payload from templateName, loaded image, regions, and documentType.",
            "runOcrDependency": "No direct RunOCR import of OcrAnnotator found; RunOCR shares OcrCanvasPane only.",
            "testDependency": "No direct TestWorkspace import of OcrAnnotator found.",
        },
        "renameReadiness": {
            "verdict": "RENAME_READY_FILE_AND_SYMBOLS",
            "reason": "Production import surface is limited to two route dynamic imports. The component is Template-domain UI, and retaining OcrAnnotator as the default function after a TemplateAnnotator file rename would leave an avoidable file/internal-symbol mismatch.",
            "renameRisk": "LOW_MEDIUM",
        },
        "renameOptions": [
            {
                "option": "candidate1_file_only",
                "description": "Rename file to TemplateAnnotator.tsx and update import paths only; keep OcrAnnotator function/local symbols.",
                "pros": ["Smallest diff", "Only route dynamic import path strings need to change"],
                "cons": ["File name and default component name remain inconsistent", "Searches for OcrAnnotator still point at the renamed file"],
                "importUpdateScope": ["src/app/ocr/page.tsx", "src/app/template/page.tsx"],
                "staticCheckDifficulty": "LOW",
                "recommended": False,
            },
            {
                "option": "candidate2_file_and_symbols",
                "description": "Rename file, default function, and route local dynamic symbols to TemplateAnnotator. No logic change.",
                "pros": ["Best matches Template domain ownership", "Avoids lingering public component-name mismatch", "Still has a very small production touch set"],
                "cons": ["Slightly larger textual rename than file-only"],
                "importUpdateScope": ["src/app/ocr/page.tsx", "src/app/template/page.tsx"],
                "staticCheckDifficulty": "LOW_MEDIUM",
                "recommended": True,
            },
            {
                "option": "candidate3_defer",
                "description": "Keep OcrAnnotator.tsx for now.",
                "pros": ["No immediate production change"],
                "cons": ["Leaves the last Template UI filename mismatch unresolved"],
                "importUpdateScope": [],
                "staticCheckDifficulty": "LOW",
                "recommended": False,
            },
        ],
        "recommendation": {
            "choice": "B",
            "scope": "Rename file plus default function/local dynamic component symbols to TemplateAnnotator; keep prop shape and logic unchanged.",
            "requiredImportUpdates": [
                "src/app/ocr/page.tsx dynamic import path and local const/render symbol",
                "src/app/template/page.tsx dynamic import path and local const/render symbol",
            ],
            "defer": [
                "Do not change route policy for /ocr",
                "Do not touch TestWorkspace",
                "Do not modify templates.json or fixtures",
                "Only rename inline props type if introduced as a named type in the same micro-step; no API shape change",
            ],
            "risk": "LOW_MEDIUM",
        },
        "risk": {
            "mainRisks": [
                "Next dynamic import path must be updated in both route files.",
                "Existing dirty state includes OcrAnnotator.tsx, so actual rename should inspect the current diff before moving.",
                "OcrCanvasPane contains comments naming OcrAnnotator as parent; these are comment-only and can be deferred or adjusted in a symbol rename step.",
            ],
        },
    }

    static_check_plan = [
        "tmp/check_template_annotator_rename_6b.mjs",
        "src/components/template/ui/TemplateAnnotator.tsx exists",
        "src/components/template/ui/OcrAnnotator.tsx absent",
        "src/app/ocr/page.tsx dynamic import points to ../../components/template/ui/TemplateAnnotator",
        "src/app/template/page.tsx dynamic import points to ../../components/template/ui/TemplateAnnotator",
        "No components/ocr/OcrAnnotator string remains in src",
        "No components/template/ui/OcrAnnotator import path remains in src",
        "RunOCR/TestWorkspace unchanged by actual rename step",
        "common/ui/OcrCanvasPane unchanged unless comment-only rename is explicitly included",
        "TemplateRightPanel unchanged",
        "npm run typecheck PASS",
        "npm run build PASS",
        "Existing 4A/4B/5A/5B/5C/5D/5E/5F/6A checks remain PASS",
        "validation baseline repair check remains PASS",
    ]

    data = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "projectRoot": "OCR/mysuit-ocr",
        "codeModified": False,
        "dirtyStatus": dirty_status,
        "analysisScope": [rel(path) for path in TARGET_FILES],
        "referenceReports": [rel(path) for path in REFERENCE_REPORTS],
        "stringHits": string_hits,
        "annotator": annotator,
        "staticCheckPlan": static_check_plan,
        "validationPlan": [
            "Run the rename-specific static checker after the rename micro-step.",
            "Run npm run typecheck and npm run build.",
            "Run prior structure checks from 4A through 6A and validation baseline repair check.",
        ],
        "typecheck": command_result_from_log("typecheck"),
        "build": command_result_from_log("build"),
        "nextSteps": [
            "Proceed with option B as a dedicated rename-only micro-step.",
            "Before renaming, inspect current dirty diff for src/components/template/ui/OcrAnnotator.tsx.",
            "Keep /ocr route naming policy separate from this rename.",
            "After rename, move to Template table column definition design only after checks pass.",
        ],
    }

    REPORT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with REPORT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["file", "importPath", "importKind", "usagePurpose", "feature", "needsImportUpdateOnRename"],
        )
        writer.writeheader()
        writer.writerows(imported_by)

    md = f"""# FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정 여부: false
- 파일 이동/import 수정/rename 수행 여부: false
- 생성 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_template_annotator_rename_precheck.py`
- `docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522.md`
- `docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522.json`
- `docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
{chr(10).join(f"- `{rel(path)}`" for path in TARGET_FILES)}

참고 리포트:
{chr(10).join(f"- `{rel(path)}`" for path in REFERENCE_REPORTS)}

## 5. OcrAnnotator 역할 요약
- currentPath: `{annotator['currentPath']}`
- lineCount: {annotator['lineCount']}
- exports: `{'; '.join(annotator['exports'])}`
- props: `{annotator['props']['signature']}`
- 주요 역할: {annotator['role']['summary']}
- Template 전용 여부: true
- TemplateWorkspace 관계: {annotator['role']['templateWorkspaceRelationship']}
- app/ocr 관계: {annotator['role']['appOcrRelationship']}
- app/template 관계: {annotator['role']['appTemplateRelationship']}
- OcrCanvasPane 관계: {annotator['role']['ocrCanvasPaneRelationship']}
- TemplateRightPanel 관계: {annotator['role']['templateRightPanelRelationship']}
- buildTemplateExportPayload 관계: {annotator['role']['buildTemplateExportPayloadRelationship']}
- RunOCR/Test 의존 여부: {annotator['role']['runOcrDependency']} / {annotator['role']['testDependency']}
- renameRisk: {annotator['renameReadiness']['renameRisk']}

imports:
{chr(10).join(f"- `{item}`" for item in annotator['imports'])}

## 6. importedBy 분석
| file | importPath | kind | feature | rename import 수정 |
|---|---|---|---|---|
{chr(10).join(f"| `{row['file']}` | `{row['importPath']}` | {row['importKind']} | {row['feature']} | {row['needsImportUpdateOnRename']} |" for row in imported_by)}

## 7. route 영향 분석
| route | dynamic import | importPath | usageCount | 영향 |
|---|---:|---|---:|---|
{chr(10).join(f"| `{row['file']}` | {row['dynamicImport']} | `{row['importPath']}` | {row['usageCount']} | {row['policyImpact']} |" for row in annotator['routeImpact'])}

- `/ocr` route 이름 정책은 이번 rename과 분리한다.
- route policy 변경 없이 dynamic import path와 local symbol만 바꿀 수 있다.

## 8. rename 적합성
- 판정: `{annotator['renameReadiness']['verdict']}`
- 이유: {annotator['renameReadiness']['reason']}
- RunOCR/Test 직접 import 없음: true
- route와 Template editor 사용처만 영향: true

## 9. rename 범위 후보 비교
| 후보 | 추천 | 장점 | 단점 | import 수정 범위 | static check 난이도 |
|---|---:|---|---|---|---|
{chr(10).join(f"| {opt['option']} | {opt['recommended']} | {'; '.join(opt['pros'])} | {'; '.join(opt['cons'])} | {'; '.join(opt['importUpdateScope']) or '없음'} | {opt['staticCheckDifficulty']} |" for opt in annotator['renameOptions'])}

## 10. 실제 rename 추천
- 추천 선택지: B. 파일명 + component/function/type 이름까지 TemplateAnnotator로 rename
- 권장 범위: {annotator['recommendation']['scope']}
- 필요한 import 수정:
{chr(10).join(f"  - {item}" for item in annotator['recommendation']['requiredImportUpdates'])}
- 보류:
{chr(10).join(f"  - {item}" for item in annotator['recommendation']['defer'])}
- 위험도: {annotator['recommendation']['risk']}

## 11. static check 설계
{chr(10).join(f"- {item}" for item in static_check_plan)}

## 12. dirty 상태
```text
{chr(10).join(dirty_status)}
```

- `../ocr-server/data/templates.json` dirty 상태가 있으면 실제 rename 전 영향 후보로 유지한다.
- TPL-95328E52 dirty 영향 precheck 후보를 유지한다.

## 13. typecheck/build 결과
- typecheck: `{data['typecheck'].get('status')}` exitCode={data['typecheck'].get('exitCode')}
- build: `{data['build'].get('status')}` exitCode={data['build'].get('exitCode')}
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 known issue로 기록한다.

## 14. 다음 작업 제안
{chr(10).join(f"- {item}" for item in data['nextSteps'])}
"""
    REPORT_MD.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
