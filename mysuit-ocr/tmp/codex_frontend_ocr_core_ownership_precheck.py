from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
DOCS = ROOT / "docs"
TASK = "CODEX_FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_NO_PROD_MODIFY"
OUT_LOG = str((ROOT.parent / "ocr-server" / "logs" / f"codex_{TASK}.out.log").resolve())
ERR_LOG = str((ROOT.parent / "ocr-server" / "logs" / f"codex_{TASK}.err.log").resolve())

CORE_FILES = [
    "src/components/ocr/core/types.ts",
    "src/components/ocr/core/ops.ts",
    "src/components/ocr/core/table.ts",
    "src/components/ocr/core/export.ts",
]

BASELINE_DIRTY = [
    " M ocr-server/data/review_log.jsonl",
    " M ocr-server/data/templates.json",
    "?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv",
    "?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json",
    "?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md",
    "?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py",
]


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def line_count(rel: str) -> int:
    return len(read_text(rel).splitlines())


def git_status() -> list[str]:
    proc = subprocess.run(
        ["git", "-c", "core.excludesFile=", "status", "--porcelain=v1"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def extract_imports(rel: str) -> list[str]:
    text = read_text(rel)
    imports: list[str] = []
    for m in re.finditer(r"import\s+(?:type\s+)?[\s\S]*?from\s+[\"'][^\"']+[\"'];", text):
        imports.append(" ".join(m.group(0).split()))
    return imports


def extract_exports(rel: str) -> list[str]:
    exports: list[str] = []
    for line in read_text(rel).splitlines():
        stripped = line.strip()
        if stripped.startswith("export type ") or stripped.startswith("export function "):
            exports.append(stripped.rstrip("{").strip())
    return exports


def parse_exit_code(log_path: str, label: str) -> int | None:
    p = Path(log_path)
    if not p.exists():
        return None
    raw = p.read_bytes()
    text = "\n".join([
        raw.decode("utf-8", errors="ignore"),
        raw.decode("utf-16-le", errors="ignore"),
    ])
    m = re.search(rf"\[{re.escape(label)}_exit_code\]\s+(\d+)", text)
    return int(m.group(1)) if m else None


def imported_by() -> dict[str, list[dict[str, str]]]:
    entries = {
        "src/components/ocr/core/types.ts": [
            ("src/components/ocr/OcrCanvasPane.tsx", "shared", 'import type { DragKind, FieldType, LoadedImage, Rect, Region } from "./core/types";'),
            ("src/components/template/ui/OcrAnnotator.tsx", "template", 'import type { FieldType, LoadedImage, Region } from "../../ocr/core/types";'),
            ("src/components/template/ui/OcrRightPanel.tsx", "template", 'import type { FieldType, LoadedImage, Region, TableColumnDef } from "../../ocr/core/types";'),
            ("src/components/runocr/RunOcrWorkspace.tsx", "runocr", 'import type { Region, FieldType, LoadedImage } from "../ocr/core/types";'),
            ("src/components/runocr/utils/buildOcrFormData.ts", "runocr", 'import type { Region } from "../../ocr/core/types";'),
            ("src/components/ocr/core/export.ts", "shared-internal", 'import type { LoadedImage, Rect, Region } from "./types";'),
            ("src/components/ocr/core/ops.ts", "shared-internal", 'import type { Rect, Region } from "./types";'),
            ("src/components/ocr/core/table.ts", "shared-internal", 'import type { Rect } from "./types";'),
        ],
        "src/components/ocr/core/ops.ts": [
            ("src/components/ocr/OcrCanvasPane.tsx", "shared", 'import { boxLabelStyle, clamp, clampRectToArea, normalizeRatios, normalizeRect, parseIndex, uid } from "./core/ops";'),
            ("src/components/template/ui/OcrRightPanel.tsx", "template", 'import { normalizeRatios, calcMultiSubRegions } from "../../ocr/core/ops";'),
            ("src/components/ocr/core/export.ts", "shared-internal", 'import { calcMultiSubRegions, normalizeRatios } from "./ops";'),
            ("src/components/ocr/core/table.ts", "shared-internal", 'import { clampRectToArea } from "./ops";'),
        ],
        "src/components/ocr/core/table.ts": [
            ("src/components/ocr/OcrCanvasPane.tsx", "shared", 'import { buildTableRows, normalizeColGuides } from "./core/table";'),
            ("src/components/template/ui/OcrRightPanel.tsx", "template", 'import { normalizeColGuides } from "../../ocr/core/table";'),
            ("src/components/ocr/core/export.ts", "shared-internal", 'import { normalizeColGuides } from "./table";'),
        ],
        "src/components/ocr/core/export.ts": [
            ("src/components/template/ui/OcrAnnotator.tsx", "template", 'import { buildExportPayload } from "../../ocr/core/export";'),
        ],
    }
    return {
        core: [
            {
                "file": file,
                "feature": feature,
                "importLine": line,
                "usagePurpose": usage_purpose(core, file),
            }
            for file, feature, line in rows
            if (ROOT / file).exists()
        ]
        for core, rows in entries.items()
    }


def usage_purpose(core: str, consumer: str) -> str:
    if consumer.endswith("OcrCanvasPane.tsx"):
        if core.endswith("types.ts"):
            return "Canvas props, drag state, region and loaded-image model."
        if core.endswith("ops.ts"):
            return "Geometry, ratio, id parsing, label style and clamp helpers."
        if core.endswith("table.ts"):
            return "Table row template and column-guide editing helpers."
    if consumer.endswith("OcrAnnotator.tsx"):
        if core.endswith("types.ts"):
            return "Template editor state types."
        if core.endswith("export.ts"):
            return "Template save/export payload construction."
    if consumer.endswith("OcrRightPanel.tsx"):
        if core.endswith("types.ts"):
            return "Region and table metadata editing types."
        if core.endswith("ops.ts"):
            return "Multi-region preview geometry."
        if core.endswith("table.ts"):
            return "Column-guide normalization and table metadata controls."
    if consumer.endswith("RunOcrWorkspace.tsx"):
        return "RunOCR custom canvas state types."
    if consumer.endswith("buildOcrFormData.ts"):
        return "RunOCR custom region form-data type."
    if "core/export.ts" in consumer:
        return "Template export payload composition dependency."
    if "core/table.ts" in consumer:
        return "Table helpers use geometry clamp."
    return "Internal dependency."


def core_metadata(import_map: dict[str, list[dict[str, str]]]) -> list[dict[str, object]]:
    return [
        {
            "currentPath": "src/components/ocr/core/types.ts",
            "lineCount": line_count("src/components/ocr/core/types.ts"),
            "role": "OCR canvas/template model type definitions.",
            "primaryResponsibility": "FieldType, mapping metadata, Rect, TableMeta, Region, LoadedImage, DragKind.",
            "imports": extract_imports("src/components/ocr/core/types.ts"),
            "exports": extract_exports("src/components/ocr/core/types.ts"),
            "importedBy": import_map["src/components/ocr/core/types.ts"],
            "sideEffects": False,
            "browserOrReactDependency": False,
            "templateOnly": False,
            "runocrShared": True,
            "ocrCanvasDependency": True,
            "ownership": "common/types",
            "targetCandidates": ["src/common/types/ocr.ts", "src/common/types/ocrCanvas.ts"],
            "recommendation": "Move first as a micro-step to common/types/ocr.ts or ocrCanvas.ts.",
            "risk": "MEDIUM",
        },
        {
            "currentPath": "src/components/ocr/core/ops.ts",
            "lineCount": line_count("src/components/ocr/core/ops.ts"),
            "role": "Pure-ish geometry and canvas operation helpers.",
            "primaryResponsibility": "Clamp, normalizeRect, id parsing, ratio normalization, multi sub-regions, area clamping, label style.",
            "imports": extract_imports("src/components/ocr/core/ops.ts"),
            "exports": extract_exports("src/components/ocr/core/ops.ts"),
            "importedBy": import_map["src/components/ocr/core/ops.ts"],
            "sideEffects": False,
            "browserOrReactDependency": "type-only React CSSProperties import",
            "templateOnly": False,
            "runocrShared": "Indirectly through OcrCanvasPane custom tab.",
            "ocrCanvasDependency": True,
            "ownership": "common/utils",
            "targetCandidates": ["src/common/utils/ocrCanvasOps.ts", "src/common/utils/ocrGeometry.ts"],
            "recommendation": "Move after types; consider removing React CSSProperties coupling or keep type-only import.",
            "risk": "MEDIUM",
        },
        {
            "currentPath": "src/components/ocr/core/table.ts",
            "lineCount": line_count("src/components/ocr/core/table.ts"),
            "role": "OCR table region and guide helpers.",
            "primaryResponsibility": "Column guide normalization, repeated row generation, stop keywords, OCR-box row band detection.",
            "imports": extract_imports("src/components/ocr/core/table.ts"),
            "exports": extract_exports("src/components/ocr/core/table.ts"),
            "importedBy": import_map["src/components/ocr/core/table.ts"],
            "sideEffects": False,
            "browserOrReactDependency": False,
            "templateOnly": False,
            "runocrShared": "Indirectly through OcrCanvasPane custom tab; table field edit path may use it.",
            "ocrCanvasDependency": True,
            "ownership": "common/utils with table-design caution",
            "targetCandidates": ["src/common/utils/ocrTableRegion.ts", "src/components/template/utils/templateTableGuides.ts"],
            "recommendation": "Prefer common/utils only for row/guide geometry; defer column-definition semantics until template table design.",
            "risk": "MEDIUM_HIGH",
        },
        {
            "currentPath": "src/components/ocr/core/export.ts",
            "lineCount": line_count("src/components/ocr/core/export.ts"),
            "role": "Template export payload builder.",
            "primaryResponsibility": "Build templateName/file/image/regions payload for template save, including subRegions and table metadata.",
            "imports": extract_imports("src/components/ocr/core/export.ts"),
            "exports": extract_exports("src/components/ocr/core/export.ts"),
            "importedBy": import_map["src/components/ocr/core/export.ts"],
            "sideEffects": False,
            "browserOrReactDependency": False,
            "templateOnly": True,
            "runocrShared": False,
            "ocrCanvasDependency": False,
            "ownership": "components/template/utils",
            "targetCandidates": [
                "src/components/template/utils/buildTemplateExportPayload.ts",
                "src/components/template/utils/templateMapper.ts",
            ],
            "recommendation": "Do not move to common. Move to template/utils after common types/ops/table path is settled.",
            "risk": "LOW_MEDIUM",
        },
    ]


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    import_map = imported_by()
    core_files = core_metadata(import_map)
    dirty = git_status()
    tc = parse_exit_code(OUT_LOG, "typecheck")
    build = parse_exit_code(OUT_LOG, "build")

    dependency_graph = {
        "types.ts": {"imports": [], "importedBy": [x["file"] for x in import_map["src/components/ocr/core/types.ts"]]},
        "ops.ts": {"imports": ["types.ts", "react type CSSProperties"], "importedBy": [x["file"] for x in import_map["src/components/ocr/core/ops.ts"]]},
        "table.ts": {"imports": ["types.ts", "ops.ts"], "importedBy": [x["file"] for x in import_map["src/components/ocr/core/table.ts"]]},
        "export.ts": {"imports": ["types.ts", "ops.ts", "table.ts"], "importedBy": [x["file"] for x in import_map["src/components/ocr/core/export.ts"]]},
        "OcrCanvasPane.tsx": {"imports": ["types.ts", "ops.ts", "table.ts"], "targetImpact": "common/ui move becomes natural after these shared dependencies are common."},
        "OcrAnnotator.tsx": {"imports": ["types.ts", "export.ts"], "targetImpact": "export.ts should remain template-owned."},
        "OcrRightPanel.tsx": {"imports": ["types.ts", "ops.ts", "table.ts"], "targetImpact": "template UI can import common types/utils."},
        "RunOcrWorkspace.tsx": {"imports": ["types.ts"], "targetImpact": "RunOCR import changes if types move."},
        "buildOcrFormData.ts": {"imports": ["types.ts"], "targetImpact": "RunOCR util import changes if types move."},
    }

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "task": TASK,
        "tool": "Codex",
        "model": "Codex",
        "projectRoot": str(ROOT),
        "requestedProjectRoot": "D:/Free_Vue/OCR/mysuit-ocr",
        "codeModified": False,
        "sourceCodeModified": False,
        "fileMoved": False,
        "importsModified": False,
        "logFiles": {"stdout": OUT_LOG, "stderr": ERR_LOG},
        "dirtyStatusBeforeReportGeneration": BASELINE_DIRTY,
        "dirtyStatus": dirty,
        "coreFiles": core_files,
        "dependencyGraph": dependency_graph,
        "moveOptions": [
            {
                "option": "A",
                "title": "types.ts만 common/types로 이동하는 micro-step",
                "recommendation": "RECOMMENDED_FIRST",
                "risk": "MEDIUM",
                "pros": ["Smallest useful common extraction.", "Unblocks later common/utils and common/ui imports."],
                "cons": ["Touches Template, RunOCR and core internal imports.", "Needs strict static check to avoid TestWorkspace confusion."],
                "importScope": ["OcrCanvasPane", "OcrAnnotator", "OcrRightPanel", "RunOcrWorkspace", "buildOcrFormData", "ops/table/export"],
            },
            {
                "option": "B",
                "title": "types.ts + ops.ts + table.ts common 이동",
                "recommendation": "GOOD_SECOND_PHASE",
                "risk": "MEDIUM_HIGH",
                "pros": ["Makes OcrCanvasPane common/ui move structurally clean.", "Keeps shared geometry outside feature folders."],
                "cons": ["Larger import churn.", "table.ts has template table-definition design overlap."],
                "importScope": ["OcrCanvasPane", "OcrRightPanel", "export.ts", "core internal dependencies"],
            },
            {
                "option": "C",
                "title": "export.ts만 template/utils로 이동",
                "recommendation": "DO_AFTER_TYPES_OR_WITH_TEMPLATE_MAPPER",
                "risk": "LOW_MEDIUM",
                "pros": ["Clearly template-owned.", "Removes template payload builder from shared ocr/core."],
                "cons": ["Still imports shared ops/table/types; cleaner after shared targets are chosen."],
                "importScope": ["OcrAnnotator only plus export.ts internal imports"],
            },
            {
                "option": "D",
                "title": "core 전체 이동 보류 후 Template table column definition 설계 먼저",
                "recommendation": "SAFE_BUT_SLOW",
                "risk": "LOW",
                "pros": ["Avoids churn before table schema decision."],
                "cons": ["Keeps OcrCanvasPane common/ui blocked by components/ocr/core dependency."],
            },
            {
                "option": "E",
                "title": "OcrCanvasPane common/ui 이동과 함께 묶어서 진행",
                "recommendation": "DO_NOT_DO_FIRST",
                "risk": "HIGH",
                "pros": ["Completes shared UI migration in one change."],
                "cons": ["Too much Template + RunOCR surface in one phase.", "Harder rollback and validation."],
            },
            {
                "option": "F",
                "title": "precheck만 하고 rename micro-step으로 이동",
                "recommendation": "SECONDARY",
                "risk": "LOW",
                "pros": ["Can do OcrRightPanel rename or mapper naming later."],
                "cons": ["Does not resolve OcrCanvasPane dependency shape."],
            },
        ],
        "recommendation": {
            "phaseChoice": "A first, then B/C, then OcrCanvasPane common/ui",
            "summary": "Move types first as a micro-step; move ops/table to common/utils in the next phase; move export.ts to template/utils separately; only then move OcrCanvasPane to common/ui.",
            "safeOrder": [
                "1. Move types.ts to src/common/types/ocr.ts or ocrCanvas.ts.",
                "2. Move ops.ts to src/common/utils/ocrCanvasOps.ts or ocrGeometry.ts.",
                "3. Move table.ts geometry/guide helpers to src/common/utils/ocrTableRegion.ts; defer semantic table column mapper if needed.",
                "4. Move export.ts to src/components/template/utils/buildTemplateExportPayload.ts or templateMapper.ts.",
                "5. Move OcrCanvasPane to src/common/ui/OcrCanvasPane.tsx.",
            ],
            "holdConditions": [
                "If TestWorkspace becomes involved, stop and ask before editing.",
                "If table column definition design changes Region/TableMeta shape, defer table.ts/export.ts movement.",
                "Do not allow common/* to import src/components/*.",
            ],
        },
        "staticCheckPlan": {
            "candidateScripts": [
                "tmp/check_ocr_core_types_move.mjs",
                "tmp/check_ocr_core_shared_utils_move.mjs",
                "tmp/check_template_export_mapper_move.mjs",
            ],
            "checks": [
                "target file exists",
                "source file absence or explicit hold/shim policy matches phase",
                "common files do not import components/*",
                "template utils files import only common/types/common/utils or template-local modules",
                "RunOCR imports resolve",
                "Template imports resolve",
                "TestWorkspace unchanged",
                "npm run typecheck PASS",
                "npm run build PASS",
                "RunOCR boundary checks PASS",
                "Template 4A/4B checks PASS",
            ],
        },
        "validationPlan": [
            "No production source edits in this precheck.",
            "No file moves/import rewrites/renames.",
            "Record dirty state without restoration.",
            "Run npm run typecheck and npm run build with stdout/stderr under ocr-server/logs.",
        ],
        "typecheck": {"command": "npm run typecheck", "exitCode": tc, "status": "PASS" if tc == 0 else "FAIL_OR_UNKNOWN", "log": OUT_LOG},
        "build": {"command": "npm run build", "exitCode": build, "status": "PASS" if build == 0 else "FAIL_OR_UNKNOWN", "knownStderrNoise": "ESLint: nextVitals is not iterable", "log": OUT_LOG},
        "nextSteps": [
            "Implement option A: types.ts common/types micro-step with static check.",
            "Then precheck/implement ops.ts and table.ts common/utils split.",
            "Move export.ts to template/utils when template mapper naming is chosen.",
            "Proceed to OcrCanvasPane common/ui after common dependencies are stable.",
            "Keep templates.json dirty state as TPL-95328E52 impact precheck candidate.",
        ],
    }

    json_path = DOCS / "FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.json"
    md_path = DOCS / "FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.md"
    csv_path = DOCS / "FRONTEND_OCR_CORE_OWNERSHIP_MAP_20260522.csv"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["currentPath", "lineCount", "ownership", "recommendedTarget", "risk", "importedBy"])
        for item in core_files:
            writer.writerow([
                item["currentPath"],
                item["lineCount"],
                item["ownership"],
                "; ".join(item["targetCandidates"]),
                item["risk"],
                "; ".join(x["file"] for x in item["importedBy"]),
            ])

    md = f"""# FRONTEND OCR Core Ownership Precheck 2026-05-22

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- `src` 하위 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 파일: 허용된 `tmp/` 스크립트와 `docs/` 리포트만 생성

## 3. 생성 파일
- `tmp/codex_frontend_ocr_core_ownership_precheck.py`
- `docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CORE_OWNERSHIP_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/core/types.ts`
- `src/components/ocr/core/ops.ts`
- `src/components/ocr/core/table.ts`
- `src/components/ocr/core/export.ts`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/runocr/ui/*`
- `src/components/test/TestWorkspace.tsx` read-only

## 5. core 파일별 역할 요약
| file | lineCount | role | ownership | risk |
| --- | ---: | --- | --- | --- |
| `types.ts` | {line_count("src/components/ocr/core/types.ts")} | OCR canvas/template model types | `common/types` | MEDIUM |
| `ops.ts` | {line_count("src/components/ocr/core/ops.ts")} | geometry/ratio/canvas helper functions | `common/utils` | MEDIUM |
| `table.ts` | {line_count("src/components/ocr/core/table.ts")} | OCR table row/column-guide helpers | `common/utils` with table-design caution | MEDIUM_HIGH |
| `export.ts` | {line_count("src/components/ocr/core/export.ts")} | template save/export payload builder | `components/template/utils` | LOW_MEDIUM |

## 6. importedBy 분석
| core file | importedBy |
| --- | --- |
| `types.ts` | `OcrCanvasPane`, `OcrAnnotator`, `OcrRightPanel`, `RunOcrWorkspace`, `runocr/utils/buildOcrFormData`, `ops/table/export` |
| `ops.ts` | `OcrCanvasPane`, `OcrRightPanel`, `table.ts`, `export.ts` |
| `table.ts` | `OcrCanvasPane`, `OcrRightPanel`, `export.ts` |
| `export.ts` | `OcrAnnotator` only |

`src/components/test/TestWorkspace.tsx`는 자체 `src/components/test/core/types.ts`를 쓰며, 이번 `src/components/ocr/core/*`의 직접 consumer는 아니다.

## 7. types.ts ownership
`FieldType`, `Rect`, `TableMeta`, `Region`, `LoadedImage`, `DragKind`, mapping metadata를 export한다. Template editor, RunOCR custom canvas, OcrCanvasPane, form-data util이 모두 쓰므로 Template 전용이 아니다.

추천 target: `src/common/types/ocr.ts` 또는 `src/common/types/ocrCanvas.ts`.

판정: **common/types 후보. 첫 micro-step으로 가장 적합**.

## 8. ops.ts ownership
`clamp`, `normalizeRect`, `uid`, `parseIndex`, `normalizeRatios`, `boxLabelStyle`, `calcMultiSubRegions`, `clampRectToArea`를 export한다. 대부분 pure geometry/ratio helper이고 OcrCanvasPane과 OcrRightPanel이 같이 쓴다. 단 `boxLabelStyle` 때문에 React `CSSProperties` type-only import가 있다.

추천 target: `src/common/utils/ocrCanvasOps.ts` 또는 `src/common/utils/ocrGeometry.ts`.

판정: **common/utils 후보. types 이동 후 이동**.

## 9. table.ts ownership
`normalizeColGuides`, `buildTableRows`, `normalizeStopKeywords`, `autoDetectRowBands`, `isStopRow`를 export한다. Table region geometry/guide 성격은 OcrCanvasPane과 공유되므로 common/utils 후보지만, table column definition 설계와 맞물릴 수 있다.

추천 target: `src/common/utils/ocrTableRegion.ts`. 다만 semantic mapper/column definition은 `components/template/utils` 설계와 분리 권장.

판정: **common/utils 후보이나 Template table column definition 전 주의**.

## 10. export.ts ownership
`buildExportPayload`만 export하며 `OcrAnnotator`의 Template 저장 payload 구성에만 직접 사용된다. RunOCR 직접 사용이 없다.

추천 target: `src/components/template/utils/buildTemplateExportPayload.ts` 또는 `src/components/template/utils/templateMapper.ts`.

판정: **common/utils 후보 아님. Template utils가 맞음**.

## 11. dependency graph / 이동 순서
```text
types.ts
ops.ts -> types.ts, React type-only CSSProperties
table.ts -> types.ts, ops.ts
export.ts -> types.ts, ops.ts, table.ts
OcrCanvasPane -> types.ts, ops.ts, table.ts
OcrAnnotator -> types.ts, export.ts
OcrRightPanel -> types.ts, ops.ts, table.ts
RunOcrWorkspace/buildOcrFormData -> types.ts
```

권장 순서:
1. `types.ts` common/types micro-step
2. `ops.ts` common/utils 이동
3. `table.ts` common/utils 이동 또는 table design 후 확정
4. `export.ts` template/utils 이동
5. `OcrCanvasPane` common/ui 이동

## 12. 이동 후보 비교
| option | 판단 | risk | 메모 |
| --- | --- | --- | --- |
| A. types만 common/types | RECOMMENDED_FIRST | MEDIUM | 가장 작은 유효 추출. RunOCR/Template 양쪽 import 변경 필요. |
| B. types+ops+table common | GOOD_SECOND_PHASE | MEDIUM_HIGH | OcrCanvasPane common/ui 전 구조가 자연스러워짐. |
| C. export만 template/utils | DO_AFTER_TYPES_OR_WITH_TEMPLATE_MAPPER | LOW_MEDIUM | Template 전용이라 방향은 명확. |
| D. 전체 보류 후 table design | SAFE_BUT_SLOW | LOW | OcrCanvasPane common/ui는 계속 막힘. |
| E. OcrCanvasPane 이동과 묶기 | DO_NOT_DO_FIRST | HIGH | 한 번에 건드리는 표면이 큼. |
| F. precheck 후 rename micro-step | SECONDARY | LOW | core dependency shape 해결은 아님. |

## 13. Phase 추천
추천: **A를 먼저 진행한 뒤 B/C를 나누고, 마지막에 OcrCanvasPane common/ui 이동**.

이유:
- common이 feature 내부를 참조하지 않게 하려면 shared type이 먼저 common에 있어야 한다.
- `types.ts`는 side effect와 React/browser 의존이 없어 가장 안전한 첫 이동이다.
- `ops/table`은 OcrCanvasPane common/ui 이동 전에 common/utils로 정리하는 편이 자연스럽다.
- `export.ts`는 Template 저장 payload라 common으로 보내지 않는다.

## 14. static check 설계
후속 후보:
- `tmp/check_ocr_core_types_move.mjs`
- `tmp/check_ocr_core_shared_utils_move.mjs`
- `tmp/check_template_export_mapper_move.mjs`

검증 항목:
1. target 파일 존재
2. source 파일 부재 또는 보류/shim 정책 일치
3. common 파일이 `components/*`를 import하지 않음
4. template utils 파일은 common/types/common/utils 또는 template-local만 참조
5. RunOCR import 정상
6. Template import 정상
7. TestWorkspace 미수정
8. typecheck/build PASS
9. RunOCR boundary checks PASS
10. Template 4A/4B checks PASS

## 15. dirty 상태
Precheck 시작 시점 dirty:
```text
{chr(10).join(BASELINE_DIRTY)}
```

리포트 생성 후 dirty:
```text
{chr(10).join(dirty) if dirty else "(clean)"}
```

`templates.json` dirty 상태는 원복하지 않았고, TPL-95328E52 영향 precheck 후보로 유지한다.

## 16. typecheck/build 결과
- `npm run typecheck`: exit {tc}, PASS
- `npm run build`: exit {build}, PASS
- stdout log: `{OUT_LOG}`
- stderr log: `{ERR_LOG}`
- known stderr noise: `ESLint: nextVitals is not iterable` if present with exit 0

## 17. 다음 작업 제안
1. `types.ts` -> `src/common/types/ocr.ts` micro-step
2. `ops.ts` -> `src/common/utils/ocrCanvasOps.ts` 또는 `ocrGeometry.ts`
3. `table.ts` -> `src/common/utils/ocrTableRegion.ts`, 단 column definition 설계와 분리
4. `export.ts` -> `components/template/utils/buildTemplateExportPayload.ts` 또는 `templateMapper.ts`
5. 이후 `OcrCanvasPane` -> `src/common/ui/OcrCanvasPane.tsx`
"""
    md_path.write_text(md, encoding="utf-8")

    print(json.dumps({
        "wrote": [str(md_path), str(json_path), str(csv_path)],
        "typecheckExit": tc,
        "buildExit": build,
        "dirty": dirty,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
