from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tmp" / "backend_structure_2a_main_route_ownership_precheck.md"
MAIN = ROOT.parent / "ocr-server" / "main.py"

REQUIRED_SECTIONS = [
    "### 1. Summary",
    "### 2. main.py Route Map",
    "### 3. OCR Extract Flow",
    "### 4. Template Route Flow",
    "### 5. Preprocess Route Flow",
    "### 6. Review / Feedback Flow",
    "### 7. main.py Internal Helper Ownership",
    "### 8. Current Coupling / Risk Notes",
    "### 9. Proposed Target Backend Structure",
    "### 10. Refactor Candidate Matrix",
    "### 11. Do Not Move Yet",
    "### 12. Verification Strategy",
    "### 13. Recommended Next Phases",
    "### 14. Zero-touch Verification",
]

ALLOWED_EXACT = {
    "docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json",
    "docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md",
    "docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json",
    "next.config.ts",
    "src/app/api/ocr-extract/route.ts",
    "src/common/ui/OcrCanvasPane.tsx",
    "src/common/utils/cleanJsonBuilder.ts",
    "src/components/runocr/RunOcrWorkspace.tsx",
    "src/components/runocr/ui/OcrResultPanel.tsx",
    "src/components/runocr/utils/mapOcrResponse.ts",
    "src/components/template/UnstructuredBuilder.tsx",
    "src/components/template/ui/TemplateAnnotator.tsx",
    "src/components/template/ui/TemplateRightPanel.tsx",
    "../ocr-server/data/review_log.jsonl",
    "public/data/testsets/invoice_statement/1-1.jpg",
    "src/components/template/utils/canonicalColumnOptions.ts",
    "src/components/template/utils/documentTypeGroup.ts",
    "tmp/backend_structure_2a_main_route_ownership_precheck.md",
    "tmp/check_backend_main_route_ownership_2a.py",
}

ALLOWED_PREFIXES = (
    "tmp/",
    "backup/test_tab_20260526_before_remove/",
    "../ocr-server/logs/",
)

EXPECTED_DELETED_PREFIXES = (
    "src/app/test/",
    "src/components/test/",
    "src/app/api/test-images/",
)


def fail(message: str) -> None:
    print(f"[BACKEND_MAIN_ROUTE_OWNERSHIP_2A] FAIL: {message}")
    sys.exit(1)


def assert_exists(path: Path, label: str) -> None:
    if not path.exists():
        fail(f"{label} missing: {path}")


def git_status_entries() -> list[tuple[str, str]]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        fail(f"git status failed: {proc.stderr.strip()}")
    entries: list[tuple[str, str]] = []
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        status = raw[:2]
        path = raw[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        entries.append((status, path))
    return entries


def allowed_dirty(status: str, path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized in ALLOWED_EXACT:
        return True
    if any(normalized.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return True
    if status.strip() == "D" and any(normalized.startswith(prefix) for prefix in EXPECTED_DELETED_PREFIXES):
        return True
    return False


def count_pattern(paths: list[Path], pattern: str) -> int:
    rx = re.compile(pattern)
    count = 0
    for base in paths:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(part in {".git", "node_modules", ".next"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if rx.search(text):
                count += 1
    return count


def main() -> None:
    assert_exists(REPORT, "report")
    report = REPORT.read_text(encoding="utf-8", errors="ignore")
    if "## BACKEND-STRUCTURE-2A Main Route Ownership Precheck" not in report:
        fail("report title missing")
    for section in REQUIRED_SECTIONS:
        if section not in report:
            fail(f"report section missing: {section}")

    assert_exists(MAIN, "ocr-server/main.py")
    main_text = MAIN.read_text(encoding="utf-8", errors="ignore")
    if "@app." not in main_text and "@router." not in main_text:
        fail("FastAPI route marker missing in main.py")
    if "/ocr/extract" not in main_text:
        fail("/ocr/extract marker missing in main.py")
    if "/templates" not in main_text:
        fail("/templates marker missing in main.py")

    if (ROOT / "src" / "app" / "test").exists():
        fail("src/app/test should be absent")
    if (ROOT / "src" / "components" / "test").exists():
        fail("src/components/test should be absent")
    if (ROOT / "src" / "app" / "api" / "test-images").exists():
        fail("src/app/api/test-images should be absent")

    protected = [
        ROOT / "src" / "common" / "config" / "testsets.ts",
        ROOT / "public" / "data" / "testsets",
        ROOT / "src" / "app" / "api" / "ocr-cache" / "route.ts",
        ROOT / "src" / "app" / "api" / "autofill-cache" / "route.ts",
        ROOT / "src" / "app" / "api" / "ground-truth" / "route.ts",
    ]
    for path in protected:
        assert_exists(path, "protected path")

    src_lib = ROOT / "src" / "lib"
    if src_lib.exists() and any(src_lib.iterdir()):
        fail("src/lib exists and is not empty")
    # Keep this guard focused on production source. Older tmp reports may contain
    # literal examples such as `from "@/lib/*"` as historical notes.
    if count_pattern([ROOT / "src"], r"from ['\"]@/lib|import\(['\"]@/lib"):
        fail("@/lib import found")

    unexpected = [(s, p) for s, p in git_status_entries() if not allowed_dirty(s, p)]
    if unexpected:
        rendered = "; ".join(f"{s} {p}" for s, p in unexpected[:20])
        fail(f"unexpected production dirty entries: {rendered}")

    print("[BACKEND_MAIN_ROUTE_OWNERSHIP_2A] PASS")


if __name__ == "__main__":
    main()
