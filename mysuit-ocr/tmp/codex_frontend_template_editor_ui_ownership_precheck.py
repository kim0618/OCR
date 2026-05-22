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
MD_PATH = DOCS / "FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_PRECHECK_20260522.md"
JSON_PATH = DOCS / "FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_PRECHECK_20260522.json"
CSV_PATH = DOCS / "FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_MAP_20260522.csv"


TARGET_FILES = [
    "src/components/ocr/OcrAnnotator.tsx",
    "src/components/ocr/OcrRightPanel.tsx",
    "src/components/ocr/OcrCanvasPane.tsx",
    "src/components/ocr/core/types.ts",
    "src/components/ocr/core/table.ts",
    "src/components/ocr/core/ops.ts",
    "src/components/ocr/core/export.ts",
    "src/components/template/TemplateWorkspace.tsx",
    "src/components/template/UnstructuredBuilder.tsx",
    "src/app/ocr/page.tsx",
    "src/app/template/page.tsx",
    "src/components/runocr/RunOcrWorkspace.tsx",
    "src/components/test/TestWorkspace.tsx",
]


FILE_META = {
    "src/components/ocr/OcrAnnotator.tsx": {
        "role": "Template editor annotation workspace",
        "ownership": "TEMPLATE_PRIVATE_UI",
        "targetPath": "src/components/template/ui/OcrAnnotator.tsx",
        "risk": "MEDIUM_HIGH",
        "notes": "Template route와 legacy /ocr route에서 dynamic import되며 OcrCanvasPane/OcrRightPanel/core/export/imageStore/template save 흐름을 조립한다.",
    },
    "src/components/ocr/OcrRightPanel.tsx": {
        "role": "Template editor right-side region/table metadata panel",
        "ownership": "TEMPLATE_PRIVATE_UI",
        "targetPath": "src/components/template/ui/OcrRightPanel.tsx",
        "risk": "MEDIUM",
        "notes": "OcrAnnotator 내부에서만 사용된다. rename 없이 OcrAnnotator와 함께 이동하는 것이 안전하다.",
    },
    "src/components/ocr/OcrCanvasPane.tsx": {
        "role": "Shared OCR canvas pane for template editing and RunOCR custom tab",
        "ownership": "RUNOCR_SHARED_CANDIDATE",
        "targetPath": "KEEP_AT_src/components/ocr/OcrCanvasPane.tsx_FOR_4B",
        "risk": "VERY_HIGH",
        "notes": "OcrAnnotator와 RunOcrWorkspace가 모두 사용한다. 4B 이동 범위에서 제외해야 한다.",
    },
    "src/components/ocr/core/types.ts": {
        "role": "Region/FieldType/LoadedImage/TableMeta types",
        "ownership": "COMMON_TYPES_CANDIDATE",
        "targetPath": "KEEP_AT_src/components/ocr/core/types.ts_FOR_4B",
        "risk": "VERY_HIGH",
        "notes": "OcrCanvasPane, OcrRightPanel, OcrAnnotator, RunOCR formdata/mapping path가 의존한다.",
    },
    "src/components/ocr/core/table.ts": {
        "role": "Table region helpers and row/column guide utilities",
        "ownership": "TEMPLATE_PRIVATE_OR_COMMON_UTIL_REVIEW",
        "targetPath": "KEEP_AT_src/components/ocr/core/table.ts_FOR_4B",
        "risk": "HIGH",
        "notes": "OcrCanvasPane/OcrRightPanel/export helper가 의존한다. Template table definition과 연결되지만 4B에서는 보류.",
    },
    "src/components/ocr/core/ops.ts": {
        "role": "Region geometry/editing operations",
        "ownership": "COMMON_UTIL_CANDIDATE",
        "targetPath": "KEEP_AT_src/components/ocr/core/ops.ts_FOR_4B",
        "risk": "HIGH",
        "notes": "Canvas drag/region geometry/right panel/export helper에서 공유된다.",
    },
    "src/components/ocr/core/export.ts": {
        "role": "Template export payload mapper",
        "ownership": "TEMPLATE_PRIVATE_UTIL",
        "targetPath": "KEEP_AT_src/components/ocr/core/export.ts_FOR_4B",
        "risk": "MEDIUM_HIGH",
        "notes": "OcrAnnotator save path가 직접 사용한다. 4B에서 OcrAnnotator 이동 후 import만 보정하고 파일 이동은 보류.",
    },
    "src/components/template/TemplateWorkspace.tsx": {
        "role": "Template list workspace after 4A move",
        "ownership": "TEMPLATE_WORKSPACE",
        "targetPath": "src/components/template/TemplateWorkspace.tsx",
        "risk": "LOW",
        "notes": "4A에서 이미 이동 완료. 4B에서 수정 대상 아님.",
    },
    "src/components/template/UnstructuredBuilder.tsx": {
        "role": "Unstructured template builder UI",
        "ownership": "TEMPLATE_PRIVATE_UI",
        "targetPath": "KEEP_AT_src/components/template/UnstructuredBuilder.tsx_FOR_4B",
        "risk": "MEDIUM",
        "notes": "template/ui 이동 후보지만 4B 범위에서는 OcrAnnotator/OcrRightPanel에 집중하기 위해 보류.",
    },
    "src/app/ocr/page.tsx": {
        "role": "Legacy /ocr route",
        "ownership": "ROUTE_IMPORT_IMPACT",
        "targetPath": "src/app/ocr/page.tsx",
        "risk": "MEDIUM",
        "notes": "OcrAnnotator dynamic import와 TemplateWorkspace import를 가진 route. 4B에서 OcrAnnotator import만 보정 대상.",
    },
    "src/app/template/page.tsx": {
        "role": "Template route",
        "ownership": "ROUTE_IMPORT_IMPACT",
        "targetPath": "src/app/template/page.tsx",
        "risk": "MEDIUM",
        "notes": "OcrAnnotator와 UnstructuredBuilder를 직접 사용한다. 4B에서 OcrAnnotator import 보정 대상.",
    },
    "src/components/runocr/RunOcrWorkspace.tsx": {
        "role": "RunOCR workspace sharing OcrCanvasPane",
        "ownership": "DO_NOT_MOVE_IN_4B",
        "targetPath": "src/components/runocr/RunOcrWorkspace.tsx",
        "risk": "VERY_HIGH",
        "notes": "OcrCanvasPane dynamic import와 core types를 사용한다. 4B에서는 수정하지 않는 것이 목표.",
    },
    "src/components/test/TestWorkspace.tsx": {
        "role": "Internal QA/test workspace",
        "ownership": "TEST_ONLY_OR_TEST_SHARED",
        "targetPath": "NO_MOVE_WITHOUT_USER_CONFIRMATION",
        "risk": "VERY_HIGH",
        "notes": "사용자 확인 전 수정/이동 금지. 이번 precheck에서 읽기만 한다.",
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


def rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def source_files() -> list[Path]:
    return [p for p in (PROJECT_ROOT / "src").rglob("*") if p.is_file() and p.suffix in {".ts", ".tsx", ".js", ".jsx"}]


def extract_imports(text: str) -> list[str]:
    specs = []
    for m in re.finditer(r"import(?:\s+type)?(?:[\s\S]*?)from\s+[\"']([^\"']+)[\"']", text):
        specs.append(m.group(1))
    for m in re.finditer(r"import\(\s*[\"']([^\"']+)[\"']\s*\)", text):
        specs.append(m.group(1))
    return sorted(set(specs))


def resolve_import(source: Path, spec: str) -> str | None:
    if spec.startswith("@/"):
        base = PROJECT_ROOT / "src" / spec[2:]
    elif spec.startswith("."):
        base = (source.parent / spec).resolve()
    else:
        return None
    candidates = [base, base.with_suffix(".ts"), base.with_suffix(".tsx"), base.with_suffix(".js"), base.with_suffix(".jsx"), base / "index.ts", base / "index.tsx"]
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
    for src in source_files():
        src_rel = rel(src)
        resolved = []
        for spec in extract_imports(read(src)):
            target = resolve_import(src, spec)
            if target:
                resolved.append(target)
                imported_by.setdefault(target, []).append(src_rel)
        imports_by[src_rel] = sorted(set(resolved))
    return imports_by, {k: sorted(set(v)) for k, v in imported_by.items()}


def exports_for(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = read(path)
    exports = []
    for m in re.finditer(r"export\s+(?:default\s+)?(?:function|const|type|interface|class)\s+(\w+)", text):
        exports.append(m.group(1))
    if "export default" in text and not exports:
        exports.append("default")
    return sorted(set(exports))


def line_count(path: Path) -> int:
    return len(read(path).splitlines()) if path.exists() else 0


def collect_file_records(imports_by: dict[str, list[str]], imported_by: dict[str, list[str]]) -> list[dict]:
    records = []
    for path_rel in TARGET_FILES:
        path = PROJECT_ROOT / path_rel
        meta = FILE_META[path_rel]
        records.append(
            {
                "currentPath": path_rel,
                "exists": path.exists(),
                "lineCount": line_count(path),
                "role": meta["role"],
                "importedBy": imported_by.get(path_rel, []),
                "imports": imports_by.get(path_rel, []),
                "exports": exports_for(path),
                "ownership": meta["ownership"],
                "targetPath": meta["targetPath"],
                "risk": meta["risk"],
                "notes": meta["notes"],
            }
        )
    return records


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    DOCS.mkdir(parents=True, exist_ok=True)
    imports_by, imported_by = build_graph()
    files = collect_file_records(imports_by, imported_by)

    shared_analysis = {
        "ocrCanvasPane": {
            "currentPath": "src/components/ocr/OcrCanvasPane.tsx",
            "importedBy": imported_by.get("src/components/ocr/OcrCanvasPane.tsx", []),
            "decision": "EXCLUDE_FROM_4B",
            "reason": "OcrAnnotator와 RunOcrWorkspace가 모두 사용한다. Template 전용 위치로 옮기면 RunOCR import까지 흔든다.",
            "futureCandidate": "src/common/ui/OcrCanvasPane.tsx",
            "needsPrecheck": True,
        },
        "ocrCore": {
            "files": [
                f for f in files if f["currentPath"].startswith("src/components/ocr/core/")
            ],
            "decision": "EXCLUDE_FROM_4B",
            "reason": "core/types는 RunOCR도 의존하고, ops/table/export는 canvas/right panel/export save path에 묶여 있다.",
            "futureCandidates": ["src/components/template/utils/*", "src/common/utils/*", "src/common/types/*"],
            "needsPrecheck": True,
        },
    }

    route_impact = {
        "appOcrPage": {
            "path": "src/app/ocr/page.tsx",
            "expected4BChange": "OcrAnnotator dynamic import path only",
            "routePolicyChange": False,
        },
        "appTemplatePage": {
            "path": "src/app/template/page.tsx",
            "expected4BChange": "OcrAnnotator dynamic import path only",
            "routePolicyChange": False,
        },
        "templateWorkspace": {
            "path": "src/components/template/TemplateWorkspace.tsx",
            "expected4BChange": "none",
            "routePolicyChange": False,
        },
    }

    phase4b_options = [
        {
            "option": "1. OcrAnnotator만 이동",
            "risk": "MEDIUM_HIGH",
            "pros": ["Template editor entry가 template/ui 아래로 간다."],
            "cons": ["OcrRightPanel이 기존 ocr 폴더에 남아 ownership이 반쪽짜리가 된다.", "OcrAnnotator 내부 상대 import가 더 어색해진다."],
            "recommendation": "NOT_PRIMARY",
        },
        {
            "option": "2. OcrAnnotator + OcrRightPanel 이동, rename 없음",
            "risk": "MEDIUM",
            "pros": ["Template private UI 두 파일이 함께 이동한다.", "rename이 없어 diff가 작다.", "OcrCanvasPane/core는 그대로 두어 RunOCR 영향이 제한된다."],
            "cons": ["OcrRightPanel 이름은 아직 목표명 TemplateRightPanel이 아니다.", "OcrAnnotator 내부 core/canvas import 보정이 필요하다."],
            "recommendation": "DO_4B",
        },
        {
            "option": "3. OcrAnnotator + OcrRightPanel 이동 + TemplateRightPanel rename",
            "risk": "HIGH",
            "pros": ["목표 이름에 더 가깝다."],
            "cons": ["move와 rename을 동시에 해 review가 어려워진다.", "문자열/참조 static check가 더 복잡해진다."],
            "recommendation": "DEFER_MICRO_STEP",
        },
        {
            "option": "4. OcrAnnotator/OcrRightPanel/OcrCanvasPane 같이 이동",
            "risk": "VERY_HIGH",
            "pros": ["components/ocr를 크게 비울 수 있다."],
            "cons": ["RunOCR Custom tab도 건드리게 된다.", "shared/common ownership 결정을 건너뛰게 된다."],
            "recommendation": "DO_NOT_DO",
        },
        {
            "option": "5. 이동 보류, ocr/core precheck 먼저",
            "risk": "LOW",
            "pros": ["더 보수적이다."],
            "cons": ["Template UI ownership 정리 진척이 없다.", "OcrAnnotator/OcrRightPanel은 이미 private UI로 판정 가능하다."],
            "recommendation": "ACCEPTABLE_BUT_NOT_PRIMARY",
        },
    ]

    phase4b_recommendation = {
        "recommendation": "OcrAnnotator + OcrRightPanel 이동, rename 없음",
        "targetPaths": [
            {
                "from": "src/components/ocr/OcrAnnotator.tsx",
                "to": "src/components/template/ui/OcrAnnotator.tsx",
            },
            {
                "from": "src/components/ocr/OcrRightPanel.tsx",
                "to": "src/components/template/ui/OcrRightPanel.tsx",
            },
        ],
        "keepInPlace": [
            "src/components/ocr/OcrCanvasPane.tsx",
            "src/components/ocr/core/*",
            "src/components/template/UnstructuredBuilder.tsx",
            "src/components/template/TemplateWorkspace.tsx",
            "src/components/runocr/*",
            "src/components/test/TestWorkspace.tsx",
        ],
        "expectedImportChanges": [
            "src/app/ocr/page.tsx: dynamic import ../../components/ocr/OcrAnnotator -> ../../components/template/ui/OcrAnnotator",
            "src/app/template/page.tsx: dynamic import ../../components/ocr/OcrAnnotator -> ../../components/template/ui/OcrAnnotator",
            "src/components/template/ui/OcrAnnotator.tsx: OcrCanvasPane import -> ../../ocr/OcrCanvasPane",
            "src/components/template/ui/OcrAnnotator.tsx: OcrRightPanel import -> ./OcrRightPanel",
            "src/components/template/ui/OcrAnnotator.tsx: core imports -> ../../ocr/core/*",
            "src/components/template/ui/OcrRightPanel.tsx: core imports -> ../../ocr/core/*",
            "src/components/template/ui/OcrAnnotator.tsx: AppProviders import -> ../../common/AppProviders 또는 alias 사용 여부 결정",
        ],
        "risk": "MEDIUM",
        "reason": "두 파일은 Template private UI이고 RunOCR/Test 직접 import가 없다. OcrCanvasPane/core를 그대로 두면 shared 영향이 제한된다.",
    }

    static_check_plan = [
        "src/components/template/ui/OcrAnnotator.tsx exists",
        "src/components/template/ui/OcrRightPanel.tsx exists",
        "src/components/ocr/OcrAnnotator.tsx absent",
        "src/components/ocr/OcrRightPanel.tsx absent",
        "src/components/ocr/OcrCanvasPane.tsx remains",
        "src/components/ocr/core/types.ts/table.ts/ops.ts/export.ts remain",
        "src/app/ocr/page.tsx route policy unchanged; only dynamic import path adjusted",
        "src/app/template/page.tsx route policy unchanged; only dynamic import path adjusted",
        "TestWorkspace.tsx unchanged",
        "RunOCR files unchanged",
        "No components/ocr/OcrAnnotator import string remains",
        "No components/ocr/OcrRightPanel import string remains",
        "No OcrRightPanel -> TemplateRightPanel rename in 4B",
        "npm run typecheck PASS",
        "npm run build PASS",
    ]

    future_template_column_notes = [
        "TemplateTableColumnEditor는 src/components/template/ui/TemplateTableColumnEditor.tsx 후보.",
        "OcrRightPanel에 table section으로 붙일 수 있지만, 첫 구현은 별도 component로 두는 편이 좋다.",
        "template column recommend/store/mapper는 src/components/template/utils 아래 후보.",
        "ocr/core/export.ts는 나중에 templateMapper.ts 후보지만 4B에서는 이동하지 않는다.",
        "invoiceTableDisplay/common utils와의 연결은 Template table column definition 도입 시 별도 precheck가 필요하다.",
    ]

    validation_plan = [
        "npm run typecheck",
        "npm run build",
        "Template route smoke: /template",
        "Legacy route smoke: /ocr",
        "RunOCR smoke only if OcrCanvasPane/core imports change unexpectedly",
        "table view model runner",
        "Clean JSON runner",
        "Markdown fixture check",
        "4B static check script",
        "diff review: move/import-only, no rename, no logic change",
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
        "sharedAnalysis": shared_analysis,
        "routeImpact": route_impact,
        "phase4BOptions": phase4b_options,
        "phase4BRecommendation": phase4b_recommendation,
        "staticCheckPlan": static_check_plan,
        "futureTemplateColumnNotes": future_template_column_notes,
        "validationPlan": validation_plan,
        "typecheck": typecheck,
        "build": build,
        "nextSteps": [
            "Phase 4B: OcrAnnotator + OcrRightPanel을 rename 없이 components/template/ui로 이동",
            "OcrCanvasPane와 ocr/core는 그대로 유지",
            "4B static check를 만들고 typecheck/build 및 /template, /ocr smoke를 실행",
            "4B 이후 OcrRightPanel rename은 별도 micro-step으로 검토",
            "OcrCanvasPane/common 이동은 RunOCR 공유 영향 precheck 후 진행",
        ],
    }

    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    CSV_PATH.write_text(make_csv(files), encoding="utf-8-sig")
    MD_PATH.write_text(make_md(report), encoding="utf-8")

    print(json.dumps({"md": str(MD_PATH), "json": str(JSON_PATH), "csv": str(CSV_PATH)}, ensure_ascii=False, indent=2))
    return 0 if typecheck["exitCode"] == 0 and build["exitCode"] == 0 else 1


def make_csv(files: list[dict]) -> str:
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["currentPath", "lineCount", "role", "importedBy", "imports", "ownership", "targetPath", "risk", "notes"])
    writer.writeheader()
    for f in files:
        writer.writerow({
            "currentPath": f["currentPath"],
            "lineCount": f["lineCount"],
            "role": f["role"],
            "importedBy": "; ".join(f["importedBy"]),
            "imports": "; ".join(f["imports"]),
            "ownership": f["ownership"],
            "targetPath": f["targetPath"],
            "risk": f["risk"],
            "notes": f["notes"],
        })
    return buf.getvalue()


def make_md(report: dict) -> str:
    files = report["files"]
    file_rows = "\n".join(
        f"| `{f['currentPath']}` | {f['lineCount']} | {f['ownership']} | `{f['targetPath']}` | {f['risk']} | {f['notes']} |"
        for f in files
    )
    import_rows = "\n".join(
        f"| `{f['currentPath']}` | {', '.join(f['importedBy']) or '-'} | {', '.join(f['imports']) or '-'} |"
        for f in files
    )
    option_rows = "\n".join(
        f"| {o['option']} | {o['risk']} | {o['recommendation']} | {'; '.join(o['pros'])} | {'; '.join(o['cons'])} |"
        for o in report["phase4BOptions"]
    )
    return f"""# FRONTEND TEMPLATE EDITOR UI OWNERSHIP PRECHECK 20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/리팩토링/주석 추가/fixture/templates/backend 수정: 없음
- 현재 dirty 상태는 되돌리지 않았다.

## 3. 생성 파일
- `tmp/codex_frontend_template_editor_ui_ownership_precheck.py`
- `docs/FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/OcrAnnotator.tsx`
- `src/components/ocr/OcrRightPanel.tsx`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/ocr/core/*`
- `src/components/template/TemplateWorkspace.tsx`
- `src/components/template/UnstructuredBuilder.tsx`
- `src/app/ocr/page.tsx`
- `src/app/template/page.tsx`
- `src/components/runocr/*`
- `src/components/test/TestWorkspace.tsx` 읽기 전용

## 5. OcrAnnotator ownership 분석
- 판정: `TEMPLATE_PRIVATE_UI`
- target: `src/components/template/ui/OcrAnnotator.tsx`
- import 사용처: `{', '.join(next(f for f in files if f['currentPath']=='src/components/ocr/OcrAnnotator.tsx')['importedBy'])}`
- RunOCR 직접 import: 없음
- TestWorkspace 직접 import: 없음
- 판단: Template editor entry로 이동 가능하지만 `OcrCanvasPane`, `OcrRightPanel`, `ocr/core/export`, `imageStore`, template save/localStorage 흐름을 조립하므로 logic 변경 없이 move/import-only로 제한해야 한다.

## 6. OcrRightPanel ownership 분석
- 판정: `TEMPLATE_PRIVATE_UI`
- target: `src/components/template/ui/OcrRightPanel.tsx`
- import 사용처: `{', '.join(next(f for f in files if f['currentPath']=='src/components/ocr/OcrRightPanel.tsx')['importedBy'])}`
- RunOCR 직접 import: 없음
- TestWorkspace 직접 import: 없음
- 판단: OcrAnnotator 내부 right-side panel이므로 OcrAnnotator와 같이 이동하는 것이 좋다. `TemplateRightPanel` rename은 별도 micro-step으로 미룬다.

## 7. OcrCanvasPane shared 영향
- 판정: `{report['sharedAnalysis']['ocrCanvasPane']['decision']}`
- importedBy: `{', '.join(report['sharedAnalysis']['ocrCanvasPane']['importedBy'])}`
- 이유: {report['sharedAnalysis']['ocrCanvasPane']['reason']}
- future candidate: `{report['sharedAnalysis']['ocrCanvasPane']['futureCandidate']}`

## 8. ocr/core 의존 분석
- 판정: `{report['sharedAnalysis']['ocrCore']['decision']}`
- 이유: {report['sharedAnalysis']['ocrCore']['reason']}
- 후보: {', '.join(report['sharedAnalysis']['ocrCore']['futureCandidates'])}
- 4B에서는 `ocr/core/*` 이동 금지.

## 9. route 영향 분석
- `/ocr`: route policy 변경 없음. `OcrAnnotator` dynamic import path만 4B 수정 후보.
- `/template`: route policy 변경 없음. `OcrAnnotator` dynamic import path만 4B 수정 후보.
- `TemplateWorkspace`: 4A 이동 완료 상태이며 4B 수정 대상 아님.

## 10. Phase 4B 후보 비교
| option | risk | recommendation | pros | cons |
| --- | --- | --- | --- | --- |
{option_rows}

## 11. Phase 4B 추천 범위
- 추천: {report['phase4BRecommendation']['recommendation']}
- 위험도: {report['phase4BRecommendation']['risk']}
- 이유: {report['phase4BRecommendation']['reason']}
- 이동:
{chr(10).join(f"  - `{item['from']}` -> `{item['to']}`" for item in report['phase4BRecommendation']['targetPaths'])}
- 유지:
{chr(10).join(f"  - `{item}`" for item in report['phase4BRecommendation']['keepInPlace'])}

## 12. target path 제안
- `src/components/ocr/OcrAnnotator.tsx` -> `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/ocr/OcrRightPanel.tsx` -> `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/ocr/OcrCanvasPane.tsx` 유지
- `src/components/ocr/core/*` 유지
- `src/components/template/UnstructuredBuilder.tsx` 유지

## 13. static check 설계
{chr(10).join(f"- {item}" for item in report['staticCheckPlan'])}

## 14. Template table column definition 대비
{chr(10).join(f"- {item}" for item in report['futureTemplateColumnNotes'])}

## 15. 파일별 import/ownership 표
| currentPath | lines | ownership | targetPath | risk | notes |
| --- | ---: | --- | --- | --- | --- |
{file_rows}

## 16. importedBy/imports
| file | importedBy | imports |
| --- | --- | --- |
{import_rows}

## 17. dirty 상태
```text
{chr(10).join(report['dirtyStatus'])}
```

## 18. typecheck/build 결과
- `npm run typecheck`: {report['typecheck']['status']} (exit {report['typecheck']['exitCode']})
- `npm run build`: {report['build']['status']} (exit {report['build']['exitCode']})
- known stderr noise: {report['build']['knownStderrNoise'] or '없음'}

## 19. 다음 작업 제안
{chr(10).join(f"{idx}. {item}" for idx, item in enumerate(report['nextSteps'], start=1))}
"""


if __name__ == "__main__":
    raise SystemExit(main())
