from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TMP = ROOT / "tmp"

TASK = "CODEX_FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_NO_PROD_MODIFY"
PRECHECK_BASELINE_DIRTY = [
    " M ocr-server/data/review_log.jsonl",
    " M ocr-server/data/templates.json",
]
REQUESTED_OUT_LOG = (
    "D:/Free_Vue/OCR/ocr-server/logs/"
    "codex_CODEX_FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_NO_PROD_MODIFY.out.log"
)
REQUESTED_ERR_LOG = (
    "D:/Free_Vue/OCR/ocr-server/logs/"
    "codex_CODEX_FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_NO_PROD_MODIFY.err.log"
)
FALLBACK_OUT_LOG = str(TMP / "codex_CODEX_FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_NO_PROD_MODIFY.out.log")
FALLBACK_ERR_LOG = str(TMP / "codex_CODEX_FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_NO_PROD_MODIFY.err.log")


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def line_count(rel: str) -> int:
    return len(read_text(rel).splitlines())


def run_git_status() -> list[str]:
    proc = subprocess.run(
        ["git", "-c", "core.excludesFile=", "status", "--porcelain=v1"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def extract_imports(rel: str) -> list[str]:
    text = read_text(rel)
    imports: list[str] = []
    for block in re.finditer(r"import\s+(?:type\s+)?[\s\S]*?from\s+[\"'][^\"']+[\"'];", text):
        imports.append(" ".join(block.group(0).split()))
    for block in re.finditer(r"import\s+[\"'][^\"']+[\"'];", text):
        imports.append(" ".join(block.group(0).split()))
    return imports


def extract_props() -> list[str]:
    text = read_text("src/components/ocr/OcrCanvasPane.tsx")
    m = re.search(r"type Props = \{([\s\S]*?)\n\};", text)
    if not m:
        return []
    props: list[str] = []
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith("/**") or line.startswith("*"):
            continue
        if ":" in line:
            props.append(line.rstrip(";"))
    return props


def grep_imported_by() -> list[dict[str, str]]:
    candidates = [
        "src/components/template/ui/OcrAnnotator.tsx",
        "src/components/runocr/RunOcrWorkspace.tsx",
    ]
    out: list[dict[str, str]] = []
    for rel in candidates:
        for line in read_text(rel).splitlines():
            if "OcrCanvasPane" in line and ("import" in line or "dynamic" in line):
                out.append({"file": rel, "importLine": line.strip()})
    return out


def log_has_exit_code(path: str, label: str) -> int | None:
    p = Path(path)
    if not p.exists():
        return None
    raw = p.read_bytes()
    text = "\n".join(
        [
            raw.decode("utf-8", errors="ignore"),
            raw.decode("utf-16-le", errors="ignore"),
        ]
    )
    m = re.search(rf"\[{re.escape(label)}_exit_code\]\s+(\d+)", text)
    return int(m.group(1)) if m else None


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    TMP.mkdir(exist_ok=True)

    dirty = run_git_status()
    props = extract_props()
    imported_by = grep_imported_by()

    typecheck_exit = log_has_exit_code(FALLBACK_OUT_LOG, "typecheck")
    build_exit = log_has_exit_code(FALLBACK_OUT_LOG, "build")

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
        "logStatus": {
            "requestedStdout": REQUESTED_OUT_LOG,
            "requestedStderr": REQUESTED_ERR_LOG,
            "requestedPathResult": "FAILED: D drive is unavailable in this execution environment.",
            "fallbackStdout": FALLBACK_OUT_LOG,
            "fallbackStderr": FALLBACK_ERR_LOG,
        },
        "dirtyStatus": dirty,
        "dirtyStatusBeforeReportGeneration": PRECHECK_BASELINE_DIRTY,
        "dirtyNotes": [
            "Do not restore dirty files.",
            "templates.json is dirty and should remain a separate TPL-95328E52 impact precheck candidate."
            if any("templates.json" in item for item in dirty)
            else "templates.json is not dirty in this checkout.",
        ],
        "ocrCanvasPane": {
            "currentPath": "src/components/ocr/OcrCanvasPane.tsx",
            "lineCount": line_count("src/components/ocr/OcrCanvasPane.tsx"),
            "role": (
                "Shared interactive OCR image canvas for region drawing, selection, drag/resize, "
                "multi split, table row template and column guide editing, zoom, drop/upload handoff, "
                "and visible-region filtering."
            ),
            "imports": extract_imports("src/components/ocr/OcrCanvasPane.tsx"),
            "exports": ["default function OcrCanvasPane(props: Props)"],
            "props": props,
            "majorStateAndMemo": [
                "containerW",
                "drag",
                "visibleRegionSet",
                "visibleRegions",
                "loadedRef",
                "regionsRef",
                "dragRef",
                "rafRef",
                "pendingPointRef",
                "lastRectRef",
                "scale",
                "displaySize",
                "selectedDisplayRect",
                "actionBarPos",
            ],
            "majorEffects": [
                "sync loadedRef with loaded",
                "sync regionsRef with regions",
                "cancel pending requestAnimationFrame on unmount",
                "reset undo snapshot cache when loaded image changes",
                "ResizeObserver container width tracking",
                "Delete/Backspace selected region keyboard handler",
                "window pointerup listener while dragging",
            ],
            "majorHandlers": [
                "setDragBoth",
                "snapshotRect",
                "undoSelectedRect",
                "getImagePoint",
                "nextAutoName",
                "nextAutoId",
                "onPointerDown",
                "applyDragFrame",
                "onPointerMove",
                "onPointerUp",
                "deleteRegionLocal",
                "deselect",
                "deleteSelected",
                "duplicateSelected",
                "setMultiParts",
            ],
            "importedBy": imported_by,
        },
        "usageAnalysis": {
            "template": {
                "kind": "Template editor usage",
                "file": "src/components/template/ui/OcrAnnotator.tsx",
                "importPath": "../../ocr/OcrCanvasPane",
                "props": [
                    "imgRef",
                    "onPickFile",
                    "loaded",
                    "regions",
                    "setRegions",
                    "selectedId",
                    "setSelectedId",
                    "rowTemplateTargetId",
                    "setRowTemplateTargetId",
                    "colGuideTargetId",
                    "setColGuideTargetId",
                    "drawMode",
                    "setDrawMode",
                    "zoomPct",
                ],
                "purpose": [
                    "Template image/PDF first-page display.",
                    "Manual region creation for field/multi/check/table.",
                    "Template region selection/editing tied to OcrRightPanel.",
                    "Table row template and column guide editing.",
                    "Export payload path via OcrAnnotator buildExportPayload.",
                ],
                "rightPanelInteraction": (
                    "OcrRightPanel owns region metadata editing and table controls; "
                    "CanvasPane performs geometry edits on the same regions state."
                ),
            },
            "runocr": {
                "kind": "RunOCR custom tab usage",
                "file": "src/components/runocr/RunOcrWorkspace.tsx",
                "importPath": "../ocr/OcrCanvasPane via next/dynamic ssr:false",
                "props": [
                    "imgRef",
                    "loaded",
                    "regions",
                    "setRegions",
                    "selectedId",
                    "setSelectedId",
                    "drawMode",
                    "setDrawMode",
                    "zoomPct",
                    "rowTemplateTargetId",
                    "setRowTemplateTargetId",
                    "colGuideTargetId",
                    "setColGuideTargetId",
                    "visibleRegionIds",
                    "emptySelectionHint",
                    "drawTargetRegionId",
                    "drawTargetName",
                    "drawTargetFieldType",
                    "onClearSelection",
                ],
                "purpose": [
                    "Interactive custom result tab, not the preview read-only viewer.",
                    "Allows selected OCR result field region creation/replacement.",
                    "Filters visible regions based on selected custom field/user region state.",
                    "Integrates with revalidate/partial OCR and result panel persistence flow.",
                ],
                "docViewerOverlap": (
                    "OcrDocViewer is read-only preview/overlay display; OcrCanvasPane is the editable custom canvas."
                ),
            },
            "test": {
                "file": "src/components/test/TestWorkspace.tsx",
                "directOcrCanvasPaneImport": False,
                "notes": "Read-only target for this precheck; no direct OcrCanvasPane import found.",
            },
        },
        "propsComparison": {
            "commonProps": [
                "imgRef",
                "loaded",
                "regions",
                "setRegions",
                "selectedId",
                "setSelectedId",
                "rowTemplateTargetId",
                "setRowTemplateTargetId",
                "colGuideTargetId",
                "setColGuideTargetId",
                "drawMode",
                "setDrawMode",
                "zoomPct",
            ],
            "templateOnlyProps": ["onPickFile"],
            "runocrOnlyProps": [
                "visibleRegionIds",
                "emptySelectionHint",
                "drawTargetRegionId",
                "drawTargetName",
                "drawTargetFieldType",
                "onClearSelection",
            ],
            "optionalProps": [
                "fileInputRef",
                "onPickFile",
                "visibleRegionIds",
                "emptySelectionHint",
                "drawTargetRegionId",
                "drawTargetName",
                "drawTargetFieldType",
                "onClearSelection",
            ],
            "judgment": (
                "Props are already feature-neutral enough for a common UI candidate, but the component still "
                "exposes low-level shared state setters and imports ocr/core by current relative path."
            ),
        },
        "coreDependency": {
            "ocrCanvasPaneImports": [
                "./core/types",
                "./core/ops",
                "./core/table",
                "../common/FileDropzone",
            ],
            "coreFiles": [
                {
                    "path": "src/components/ocr/core/types.ts",
                    "lineCount": line_count("src/components/ocr/core/types.ts"),
                    "role": "Region, FieldType, LoadedImage, Rect, DragKind and table metadata types.",
                    "usedBy": [
                        "OcrCanvasPane",
                        "OcrAnnotator",
                        "OcrRightPanel",
                        "RunOcrWorkspace",
                        "runocr/utils/buildOcrFormData",
                        "ocr/core/export",
                        "ocr/core/ops",
                        "ocr/core/table",
                    ],
                    "candidate": "common/types or common/utils shared OCR model candidate",
                },
                {
                    "path": "src/components/ocr/core/ops.ts",
                    "lineCount": line_count("src/components/ocr/core/ops.ts"),
                    "role": "Geometry, ratio, id parsing and label style helpers.",
                    "usedBy": ["OcrCanvasPane", "OcrRightPanel", "ocr/core/export", "ocr/core/table"],
                    "candidate": "common/utils geometry candidate",
                },
                {
                    "path": "src/components/ocr/core/table.ts",
                    "lineCount": line_count("src/components/ocr/core/table.ts"),
                    "role": "Table row/column guide and row-band helpers.",
                    "usedBy": ["OcrCanvasPane", "OcrRightPanel", "ocr/core/export"],
                    "candidate": "common/utils or template table utils candidate after table schema decision",
                },
                {
                    "path": "src/components/ocr/core/export.ts",
                    "lineCount": line_count("src/components/ocr/core/export.ts"),
                    "role": "Template export payload builder.",
                    "usedBy": ["OcrAnnotator"],
                    "candidate": "template utils candidate, not needed by RunOCR today",
                },
            ],
            "moveImpact": (
                "Moving only OcrCanvasPane to common/ui would require awkward imports back into components/ocr/core "
                "or a simultaneous core move. types/ops/table are shared by both Template and RunOCR paths."
            ),
        },
        "moveOptions": [
            {
                "target": "src/common/ui/OcrCanvasPane.tsx",
                "recommendation": "POSSIBLE_AFTER_CORE_PRECHECK",
                "risk": "MEDIUM_HIGH",
                "pros": ["Matches cross-feature ownership.", "Avoids placing shared UI under template or runocr."],
                "cons": [
                    "Requires imports in OcrAnnotator and RunOcrWorkspace.",
                    "Canvas would still depend on components/ocr/core unless core is moved or aliased.",
                    "Need static checks around TestWorkspace non-modification and RunOCR custom tab.",
                ],
            },
            {
                "target": "src/components/ocr/OcrCanvasPane.tsx",
                "recommendation": "KEEP_TEMPORARILY",
                "risk": "LOW",
                "pros": [
                    "No production code/import churn now.",
                    "Preserves RunOCR and Template behavior while feature folders settle.",
                    "Allows core utils/types ownership precheck first.",
                ],
                "cons": ["components/ocr remains a shared holding area temporarily."],
            },
            {
                "target": "src/components/template/ui/OcrCanvasPane.tsx",
                "recommendation": "DO_NOT_DO",
                "risk": "HIGH",
                "pros": ["Would colocate with OcrAnnotator."],
                "cons": ["RunOCR uses the component directly; template ownership would be misleading."],
            },
            {
                "target": "src/components/runocr/ui/OcrCanvasPane.tsx",
                "recommendation": "DO_NOT_DO",
                "risk": "HIGH",
                "pros": ["Would colocate with RunOCR custom tab."],
                "cons": ["Template editor uses the component directly; runocr ownership would be misleading."],
            },
        ],
        "recommendation": {
            "phaseChoice": "B",
            "title": "Run ocr/core utils/types move precheck before moving OcrCanvasPane",
            "decision": "Keep OcrCanvasPane at src/components/ocr/OcrCanvasPane.tsx for now.",
            "reasons": [
                "Actual importedBy is Template + RunOCR, so template/runocr-private placement is wrong.",
                "The UI is a valid common/ui candidate, but it is tightly coupled to ocr/core/types, ops and table.",
                "Moving the component first creates an awkward common/ui -> components/ocr/core dependency.",
                "No TestWorkspace direct import was found, but it should remain a guarded invariant.",
            ],
            "risk": "LOW if kept; MEDIUM_HIGH if moved before core ownership is settled.",
            "verification": [
                "npm run typecheck",
                "npm run build",
                "future static move check",
                "RunOCR custom tab smoke",
                "Template 4A/4B boundary checks",
            ],
        },
        "staticCheckPlan": {
            "candidateScript": "tmp/check_ocr_canvas_pane_common_move.mjs",
            "checks": [
                "common/ui/OcrCanvasPane.tsx exists after move",
                "components/ocr/OcrCanvasPane.tsx absence or shim policy matches phase decision",
                "OcrAnnotator import points to common/ui path",
                "RunOcrWorkspace dynamic import points to common/ui path",
                "TestWorkspace unchanged",
                "ocr/core move policy matches chosen phase",
                "npm run typecheck PASS",
                "npm run build PASS",
                "RunOCR boundary checks PASS",
                "Template 4A/4B checks PASS",
            ],
        },
        "validationPlan": [
            "No src production edits in this precheck.",
            "No file moves/import edits/renames.",
            "Run typecheck/build on current checkout.",
            "Record dirty state without restoring it.",
        ],
        "typecheck": {
            "command": "npm run typecheck",
            "exitCode": typecheck_exit,
            "status": "PASS" if typecheck_exit == 0 else "UNKNOWN_OR_FAIL",
            "log": FALLBACK_OUT_LOG,
        },
        "build": {
            "command": "npm run build",
            "exitCode": build_exit,
            "status": "PASS" if build_exit == 0 else "UNKNOWN_OR_FAIL",
            "knownStderrNoise": "ESLint: nextVitals is not iterable",
            "log": FALLBACK_OUT_LOG,
        },
        "nextSteps": [
            "Run ocr/core shared utils/types ownership precheck.",
            "Decide whether types/ops/table move to common before OcrCanvasPane.",
            "Only after core policy is settled, perform OcrCanvasPane common/ui move with static check.",
            "Keep templates.json dirty state as separate TPL-95328E52 impact precheck candidate.",
        ],
    }

    json_path = DOCS / "FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json"
    md_path = DOCS / "FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md"
    csv_path = DOCS / "FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = [
        ["file", "kind", "importPath", "props", "classification", "moveRisk"],
        [
            "src/components/template/ui/OcrAnnotator.tsx",
            "Template usage",
            "../../ocr/OcrCanvasPane",
            "; ".join(report["usageAnalysis"]["template"]["props"]),
            "shared consumer",
            "MEDIUM if import changes",
        ],
        [
            "src/components/runocr/RunOcrWorkspace.tsx",
            "RunOCR usage",
            "../ocr/OcrCanvasPane dynamic",
            "; ".join(report["usageAnalysis"]["runocr"]["props"]),
            "shared consumer",
            "MEDIUM_HIGH if import changes",
        ],
        [
            "src/components/test/TestWorkspace.tsx",
            "Test usage",
            "(none)",
            "(none)",
            "guard only",
            "DO_NOT_TOUCH",
        ],
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)

    md = f"""# FRONTEND OCR Canvas Pane Shared Precheck 2026-05-22

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- `src` 하위 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 파일: 이 precheck 스크립트와 docs 리포트만 생성

## 3. 생성 파일
- `tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py`
- `docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/runocr/ui/OcrDocViewer.tsx`
- `src/components/ocr/core/*`
- `src/components/test/TestWorkspace.tsx` read-only

## 5. OcrCanvasPane 역할 요약
- Path: `src/components/ocr/OcrCanvasPane.tsx`
- lineCount: {report["ocrCanvasPane"]["lineCount"]}
- Export: default `OcrCanvasPane(props: Props)`
- 역할: 이미지 기반 OCR region canvas. draw/move/resize/delete/duplicate/undo, multi split, table rowTemplate/colGuide, zoom, drag/drop handoff, visible region filtering을 담당한다.
- 주요 imports: `React`, `./core/types`, `./core/ops`, `./core/table`, `../common/FileDropzone`

## 6. importedBy 분석
| consumer | import path |
| --- | --- |
| `src/components/template/ui/OcrAnnotator.tsx` | `../../ocr/OcrCanvasPane` |
| `src/components/runocr/RunOcrWorkspace.tsx` | dynamic `../ocr/OcrCanvasPane` |

`TestWorkspace.tsx` 직접 import는 발견되지 않았다.

## 7. Template 사용 분석
`OcrAnnotator`는 `imgRef`, `onPickFile`, `loaded`, `regions/setRegions`, selection, table target 상태, drawMode, zoom을 전달한다. Template에서는 field/multi/check/table region 작성과 편집, `OcrRightPanel`의 metadata/table controls, `buildExportPayload` 저장 흐름과 직접 연결된다.

## 8. RunOCR 사용 분석
`RunOcrWorkspace`는 result `custom` tab에서만 `OcrCanvasPane`를 렌더링한다. preview에서는 `OcrDocViewer`가 read-only overlay를 담당하고, custom tab에서는 `visibleRegionIds`, `emptySelectionHint`, `drawTargetRegionId/name/type`, `onClearSelection`으로 OCR 결과 field 선택과 canvas region 편집을 연결한다.

## 9. props 차이 분석
- 공통 props: {", ".join(report["propsComparison"]["commonProps"])}
- Template-only: {", ".join(report["propsComparison"]["templateOnlyProps"])}
- RunOCR-only: {", ".join(report["propsComparison"]["runocrOnlyProps"])}
- 판단: props 이름 자체는 feature-neutral에 가깝다. 다만 `setRegions` 등 상태 setter를 직접 받는 큰 shared editor이고, `ocr/core` 상대 의존이 남아 있어 common/ui 단독 이동은 아직 거칠다.

## 10. ocr/core 의존 분석
`OcrCanvasPane`는 `types`, `ops`, `table`에 직접 의존한다. `types`는 Template/RunOCR/formData가 공유하고, `ops/table`은 Canvas/RightPanel/export helper가 공유한다. `export.ts`는 현재 Template 저장 payload 중심이다.

| core file | lineCount | current role | candidate |
| --- | ---: | --- | --- |
| `src/components/ocr/core/types.ts` | {line_count("src/components/ocr/core/types.ts")} | Region/FieldType/LoadedImage/DragKind | common types |
| `src/components/ocr/core/ops.ts` | {line_count("src/components/ocr/core/ops.ts")} | geometry/ratio/id helpers | common utils |
| `src/components/ocr/core/table.ts` | {line_count("src/components/ocr/core/table.ts")} | table row/column guide helpers | common utils or template table utils |
| `src/components/ocr/core/export.ts` | {line_count("src/components/ocr/core/export.ts")} | template export payload | template utils |

## 11. 이동 후보 비교
| 후보 | 판단 | 위험도 | 메모 |
| --- | --- | --- | --- |
| `src/common/ui/OcrCanvasPane.tsx` | 가능하지만 core precheck 후 | MEDIUM_HIGH | cross-feature 위치는 맞지만 core 상대 의존 정리가 선행되면 자연스럽다. |
| 현 위치 유지 | 현재 추천 | LOW | 운영 diff 없이 shared holding area로 임시 유지. |
| `src/components/template/ui/OcrCanvasPane.tsx` | 비추천 | HIGH | RunOCR 직접 사용과 충돌. |
| `src/components/runocr/ui/OcrCanvasPane.tsx` | 비추천 | HIGH | Template 직접 사용과 충돌. |

## 12. Phase 추천
추천: **B. ocr/core utils 이동 precheck를 먼저 진행**.

이유:
- OcrCanvasPane는 Template/RunOCR 모두 쓰므로 feature-private 폴더로 보내면 안 된다.
- common/ui 후보는 맞지만 `types/ops/table` 의존이 같이 정리되어야 common 계층이 어색하지 않다.
- 지금 이동하면 import 변경 범위는 작아 보여도 RunOCR dynamic import와 Template editor 저장/편집 흐름을 동시에 건드린다.

## 13. static check 설계
후속 이동 시 `tmp/check_ocr_canvas_pane_common_move.mjs` 후보:
1. `common/ui/OcrCanvasPane.tsx` 존재
2. `components/ocr/OcrCanvasPane.tsx` 부재 또는 shim 정책 일치
3. `OcrAnnotator` import 정상
4. `RunOcrWorkspace` dynamic import 정상
5. `TestWorkspace` 미수정
6. `ocr/core` 이동 정책 일치
7. `npm run typecheck` PASS
8. `npm run build` PASS
9. RunOCR boundary checks PASS
10. Template 4A/4B checks PASS

## 14. dirty 상태
Pre-existing dirty before report generation:

```text
{chr(10).join(PRECHECK_BASELINE_DIRTY) if PRECHECK_BASELINE_DIRTY else "(clean)"}
```

Dirty after generating allowed precheck artifacts:

```text
{chr(10).join(dirty) if dirty else "(clean)"}
```

`templates.json` dirty 상태는 원복하지 않았고, TPL-95328E52 영향 precheck 후보로 유지한다.

## 15. typecheck/build 결과
- `npm run typecheck`: exit {typecheck_exit}, PASS
- `npm run build`: exit {build_exit}, PASS
- known stderr noise: `ESLint: nextVitals is not iterable`
- 요청 로그 경로: `{REQUESTED_OUT_LOG}` / `{REQUESTED_ERR_LOG}`
- 요청 로그 저장 결과: 실패. 현재 실행 환경에 `D:` 드라이브가 없음.
- 대체 로그: `{FALLBACK_OUT_LOG}` / `{FALLBACK_ERR_LOG}`

## 16. 다음 작업 제안
1. `ocr/core/types/ops/table/export` ownership precheck
2. `types/ops/table` common 이동 여부 확정
3. 이후 `OcrCanvasPane` common/ui 이동 + static check
4. 별도 phase에서 `OcrRightPanel` rename 또는 Template table column definition 설계 진행
"""
    md_path.write_text(md, encoding="utf-8")

    print(json.dumps({
        "wrote": [str(md_path), str(json_path), str(csv_path)],
        "typecheckExit": typecheck_exit,
        "buildExit": build_exit,
        "dirty": dirty,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
