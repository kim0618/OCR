#!/usr/bin/env python3
"""
CLAUDE_FRONTEND_REMAINING_LIB_FULL_CLEANUP_PLAN_PRECHECK_NO_PROD_MODIFY

Read-only precheck. Analyzes every file remaining in src/lib/ and produces a
move plan that ends with src/lib being empty/absent. NO production code is
modified, NO files are moved, NO imports are edited.

Outputs (when run as __main__):
  docs/FRONTEND_REMAINING_LIB_FULL_CLEANUP_PLAN_PRECHECK_20260522.json
  docs/FRONTEND_REMAINING_LIB_FULL_CLEANUP_PLAN_PRECHECK_20260522.md
  docs/FRONTEND_REMAINING_LIB_FULL_CLEANUP_MAP_20260522.csv

The static analysis tables (file roles, target paths, move phases) are
hard-coded based on the prior reading of each source file; this script
re-validates the live state (file presence, importedBy counts, dirty flag)
on every run so the artifacts stay accurate if the tree drifts.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # mysuit-ocr/
SRC = ROOT / "src"
LIB_DIR = SRC / "lib"
DOCS_DIR = ROOT / "docs"

EXPECTED_LIB_FILES = [
    "autofillEngine.ts",
    "axios.ts",
    "groundTruthStore.ts",
    "login.ts",
    "profiles.ts",
    "restoreProfileStore.ts",
    "testsets.ts",
    "theme.ts",
    "version.ts",
]

CODE_EXTS = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}

# -----------------------------------------------------------------------------
# Per-file static analysis (locked in based on the read of each source file)
# -----------------------------------------------------------------------------

@dataclass
class FileAnalysis:
    currentPath: str
    presentOnDisk: bool
    lineCount: int
    mainResponsibility: str
    exportsKey: list[str]
    importsSummary: list[str]
    pureUtil: bool
    storagePersistence: bool
    configConstants: bool
    apiClient: bool
    featureSpecific: str  # "shared" | "test" | "layout" | "autorestore" | "login" | etc
    reactDependency: bool
    browserApiDependency: bool
    localStorageDependency: bool
    backendDependency: bool
    componentsImport: bool
    commonImport: bool
    testWorkspaceImpact: str
    testCoreImpact: bool
    targetCandidates: list[str]
    recommendedTarget: str
    movePhase: str
    risk: str
    prerequisites: list[str]
    notes: str
    staticCheckScript: str
    staticCheckKeyItems: list[str]
    importedByCount: int = 0
    importedByFiles: list[dict] = field(default_factory=list)


# Hard-coded per the read of each src/lib/*.ts file. Update only when the file
# on disk is materially changed (not just import-path tweaks).
ANALYSES: dict[str, FileAnalysis] = {
    "theme.ts": FileAnalysis(
        currentPath="src/lib/theme.ts",
        presentOnDisk=False, lineCount=0,
        mainResponsibility=(
            "useTheme() React hook: persists light/dark theme in localStorage "
            "and applies data-theme attribute on document.documentElement."
        ),
        exportsKey=["useTheme"],
        importsSummary=["react"],
        pureUtil=False, storagePersistence=False, configConstants=False, apiClient=False,
        featureSpecific="layout",
        reactDependency=True, browserApiDependency=True, localStorageDependency=True,
        backendDependency=False, componentsImport=False, commonImport=False,
        testWorkspaceImpact="NO_TEST_IMPACT", testCoreImpact=False,
        targetCandidates=[
            "src/components/layout/utils/theme.ts",
            "src/common/ui/theme.ts",
        ],
        recommendedTarget="src/components/layout/utils/theme.ts",
        movePhase="LIB-CLEAN-1-THEME-MOVE",
        risk="LOW",
        prerequisites=[],
        notes=(
            "Single consumer (components/layout/Header.tsx). React hook so it "
            "cannot live in src/common/utils (utils boundary forbids React); "
            "layout/utils is the cleanest owner."
        ),
        staticCheckScript="tmp/check_theme_layout_utils_move_th1.mjs",
        staticCheckKeyItems=[
            "new file exists, old file absent",
            "no @/lib/theme residual",
            "Header.tsx import path corrected, logic byte-equivalent vs backup",
            "useTheme export preserved",
        ],
    ),
    "login.ts": FileAnalysis(
        currentPath="src/lib/login.ts",
        presentOnDisk=False, lineCount=0,
        mainResponsibility=(
            "localStorage helpers for the login token blob (getStoredLogin, "
            "saveLogin, clearLogin, hasStoredLogin) plus the StoredLogin type. "
            "Shared between login feature, layout Header (logout), axios "
            "interceptor (auth header)."
        ),
        exportsKey=[
            "StoredLogin (type)",
            "getStoredLogin",
            "saveLogin",
            "clearLogin",
            "hasStoredLogin",
        ],
        importsSummary=[],
        pureUtil=False, storagePersistence=True, configConstants=False, apiClient=False,
        featureSpecific="shared",
        reactDependency=False, browserApiDependency=True, localStorageDependency=True,
        backendDependency=False, componentsImport=False, commonImport=False,
        testWorkspaceImpact="NO_TEST_IMPACT", testCoreImpact=False,
        targetCandidates=[
            "src/common/storage/login.ts",
            "src/components/login/utils/login.ts",
        ],
        recommendedTarget="src/common/storage/login.ts",
        movePhase="LIB-CLEAN-2-LOGIN-STORAGE-MOVE",
        risk="LOW",
        prerequisites=[],
        notes=(
            "Shared persistence helper, not login-UI-local: axios + layout "
            "Header also consume it. Belongs in src/common/storage/ next to "
            "imageStore/historyStore (consistent persistence boundary)."
        ),
        staticCheckScript="tmp/check_login_common_storage_move_lg1.mjs",
        staticCheckKeyItems=[
            "new file exists, old file absent",
            "5 importers updated (axios, RequireLogin, LoginWorkspace, "
            "layout/Header; axios is the sibling pre-move)",
            "STORAGE_KEY 'mysuit_ocr_login' preserved",
            "no @/lib/login residual",
            "no components/* import inside login.ts",
        ],
    ),
    "axios.ts": FileAnalysis(
        currentPath="src/lib/axios.ts",
        presentOnDisk=False, lineCount=0,
        mainResponsibility=(
            "Singleton axios HTTP client with /api baseURL, Bearer auth "
            "interceptor sourced from login.ts, 401/loginCode=9999 redirect "
            "to /login, and an ApiResponseError class."
        ),
        exportsKey=["default api", "ApiResponseError"],
        importsSummary=["axios", "./login"],
        pureUtil=False, storagePersistence=False, configConstants=False, apiClient=True,
        featureSpecific="shared",
        reactDependency=False, browserApiDependency=True, localStorageDependency=False,
        backendDependency=True, componentsImport=False, commonImport=False,
        testWorkspaceImpact="NO_TEST_IMPACT", testCoreImpact=False,
        targetCandidates=[
            "src/common/api/axios.ts",
        ],
        recommendedTarget="src/common/api/axios.ts",
        movePhase="LIB-CLEAN-3-AXIOS-API-MOVE",
        risk="LOW",
        prerequisites=["LIB-CLEAN-2-LOGIN-STORAGE-MOVE (so axios imports @/common/storage/login)"] ,
        notes=(
            "Introduces src/common/api/ as a new domain subdir. 2 direct "
            "importers (HistoryWorkspace, LoginWorkspace). The relative "
            "sibling ./login import gets rewritten to @/common/storage/login."
        ),
        staticCheckScript="tmp/check_axios_common_api_move_api1.mjs",
        staticCheckKeyItems=[
            "new file exists, old file absent",
            "default + ApiResponseError exports preserved",
            "imports @/common/storage/login (sibling form ./login no longer valid)",
            "HistoryWorkspace + LoginWorkspace import path corrected",
            "no @/lib/axios residual",
        ],
    ),
    "groundTruthStore.ts": FileAnalysis(
        currentPath="src/lib/groundTruthStore.ts",
        presentOnDisk=False, lineCount=0,
        mainResponsibility=(
            "localStorage store keyed by (template, file) holding 'corrected "
            "fields → ground-truth' map. Provides getGroundTruth, "
            "saveGroundTruth, clearGroundTruth, compareToGt, compositeKey, "
            "fieldKey."
        ),
        exportsKey=[
            "GroundTruthMap (type)", "MatchStatus (type)",
            "compositeKey", "fieldKey",
            "getGroundTruth", "saveGroundTruth", "clearGroundTruth",
            "compareToGt",
        ],
        importsSummary=["type HistoryOutputField from @/common/storage/historyStore"],
        pureUtil=False, storagePersistence=True, configConstants=False, apiClient=False,
        featureSpecific="shared",
        reactDependency=False, browserApiDependency=True, localStorageDependency=True,
        backendDependency=False, componentsImport=False, commonImport=True,
        testWorkspaceImpact="NO_TEST_IMPACT", testCoreImpact=False,
        targetCandidates=[
            "src/common/storage/groundTruthStore.ts",
            "src/components/test/utils/groundTruthStore.ts",
        ],
        recommendedTarget="src/common/storage/groundTruthStore.ts",
        movePhase="LIB-CLEAN-4-GROUND-TRUTH-STORE-MOVE",
        risk="LOW",
        prerequisites=[],
        notes=(
            "Consumed by runocr (OcrResultPanel) and history (DetailHistoryView) "
            "— NOT by test feature directly. Pairs naturally with the existing "
            "historyStore.ts in common/storage."
        ),
        staticCheckScript="tmp/check_ground_truth_store_common_storage_move_gt1.mjs",
        staticCheckKeyItems=[
            "new file exists, old file absent",
            "STORAGE_KEY 'mysuit_ocr_groundtruth' preserved",
            "8 exports preserved",
            "2 importers updated (DetailHistoryView, OcrResultPanel)",
            "no @/lib/groundTruthStore residual",
            "no components/* import",
        ],
    ),
    "restoreProfileStore.ts": FileAnalysis(
        currentPath="src/lib/restoreProfileStore.ts",
        presentOnDisk=False, lineCount=0,
        mainResponsibility=(
            "localStorage CRUD for restore profiles (businessNo+partyType keyed). "
            "Provides RestoreProfile types, AUTOFILL_TO_PROFILE_KEY map, "
            "PROFILE_FIELD_LABELS, isMeaninglessValue and read/write/find/sort "
            "helpers."
        ),
        exportsKey=[
            "RESTORE_PROFILE_STORAGE_KEY",
            "RestoreProfile (type)", "RestoreProfileFields (type)",
            "AUTOFILL_TO_PROFILE_KEY", "PROFILE_FIELD_LABELS",
            "isMeaninglessValue",
            "readRestoreProfiles", "writeRestoreProfiles",
            "deleteRestoreProfile", "findRestoreProfile",
            "sortRestoreProfilesByUpdatedAt",
        ],
        importsSummary=[],
        pureUtil=False, storagePersistence=True, configConstants=False, apiClient=False,
        featureSpecific="shared",
        reactDependency=False, browserApiDependency=True, localStorageDependency=True,
        backendDependency=False, componentsImport=False, commonImport=False,
        testWorkspaceImpact="NO_TEST_IMPACT", testCoreImpact=False,
        targetCandidates=[
            "src/common/storage/restoreProfileStore.ts",
            "src/components/autorestore/utils/restoreProfileStore.ts",
        ],
        recommendedTarget="src/common/storage/restoreProfileStore.ts",
        movePhase="LIB-CLEAN-5-RESTORE-PROFILE-STORE-MOVE",
        risk="LOW",
        prerequisites=[],
        notes=(
            "Used by autorestore (AutoRestoreWorkspace), history (DetailHistoryView) "
            "and autofillEngine (sibling). Cross-feature persistence helper -> "
            "common/storage is the right home; autorestore/utils would force "
            "history+autofillEngine to import from autorestore feature."
        ),
        staticCheckScript="tmp/check_restore_profile_store_common_storage_move_rp1.mjs",
        staticCheckKeyItems=[
            "new file exists, old file absent",
            "RESTORE_PROFILE_STORAGE_KEY preserved",
            "11 exports preserved",
            "3 importers updated (autofillEngine [sibling], AutoRestoreWorkspace, "
            "DetailHistoryView)",
            "no @/lib/restoreProfileStore residual",
        ],
    ),
    "testsets.ts": FileAnalysis(
        currentPath="src/lib/testsets.ts",
        presentOnDisk=False, lineCount=0,
        mainResponsibility=(
            "Static dataset registry (TESTSETS array, DATASET_FOLDERS map, "
            "getTestset) + manifest item / invoice profile type definitions."
        ),
        exportsKey=[
            "TESTSETS", "DATASET_FOLDERS", "getTestset",
            "TestsetMeta", "DocumentType", "QualityTag", "Difficulty",
            "InvoiceSubType", "AmountProfile", "PartyProfile", "TableProfile",
            "InvoiceTableExpectedDisplayColumn", "InvoiceProfile",
            "DatasetRole", "DatasetStatus", "ExpectedStatus",
            "ManifestItem", "DatasetManifest",
        ],
        importsSummary=[],
        pureUtil=True, storagePersistence=False, configConstants=True, apiClient=False,
        featureSpecific="shared",
        reactDependency=False, browserApiDependency=False, localStorageDependency=False,
        backendDependency=False, componentsImport=False, commonImport=False,
        testWorkspaceImpact="TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY",
        testCoreImpact=False,
        targetCandidates=[
            "src/common/config/testsets.ts",
            "src/components/test/data/testsets.ts",
        ],
        recommendedTarget="src/common/config/testsets.ts",
        movePhase="LIB-CLEAN-6-TESTSETS-COMMON-CONFIG-MOVE",
        risk="MEDIUM",
        prerequisites=[],
        notes=(
            "6 importers across features and API routes (4 app/api/*, profiles "
            "sibling, TestWorkspace). Putting it in components/test/data would "
            "force 4 SSR API routes to import from a feature dir; "
            "src/common/config/ is the cleaner shared home. Introduces "
            "src/common/config/ as a new domain subdir."
        ),
        staticCheckScript="tmp/check_testsets_common_config_move_ts1.mjs",
        staticCheckKeyItems=[
            "new file exists, old file absent",
            "TESTSETS / DATASET_FOLDERS / getTestset preserved",
            "all manifest type exports preserved",
            "6 importers updated (api/ground-truth, api/test-images, "
            "api/autofill-cache, api/ocr-cache, TestWorkspace, profiles "
            "[sibling])",
            "TestWorkspace logic byte-equivalent after import-strip",
            "no @/lib/testsets residual",
            "no components/* import inside testsets.ts",
        ],
    ),
    "profiles.ts": FileAnalysis(
        currentPath="src/lib/profiles.ts",
        presentOnDisk=False, lineCount=0,
        mainResponsibility=(
            "Test-tab profile policy: receipt/finance/document/none profile "
            "resolution, column definitions, table profile policies, KPI "
            "family resolution. Pure types + constants + helpers."
        ),
        exportsKey=[
            "Profile/Overlay/ProfileResolution",
            "ReceiptFieldKey/FinanceFieldKey/DocumentFieldKey/"
            "CardOverlayFieldKey/MedicalOverlayFieldKey/AnyFieldKey",
            "FINANCE_TIER1_FIELDS/FINANCE_TIER2_FIELDS/"
            "DOCUMENT_PARTY_FIELDS",
            "RECEIPT_COLUMNS/FINANCE_COLUMNS/DOCUMENT_COLUMNS/"
            "CARD_OVERLAY_COLUMNS/MEDICAL_OVERLAY_COLUMNS",
            "resolveProfile/getBaseColumns/getOverlayColumns/"
            "getVisibleColumns/isNotApplicableField",
            "isFinanceTier1/isProfileMismatchSuspected",
            "KpiFamily/resolveKpiFamily",
            "TableColumnKey/GridModeRecommendation/TableColumnMeta/"
            "TABLE_COLUMN_META/TableProfilePolicyResult/"
            "getExpectedTableColumns/TableRowsValidation",
        ],
        importsSummary=["type DocumentType from ./testsets"],
        pureUtil=True, storagePersistence=False, configConstants=True, apiClient=False,
        featureSpecific="test",
        reactDependency=False, browserApiDependency=False, localStorageDependency=False,
        backendDependency=False, componentsImport=False, commonImport=False,
        testWorkspaceImpact="TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY",
        testCoreImpact=False,
        targetCandidates=[
            "src/components/test/utils/profiles.ts",
            "src/common/config/profiles.ts",
        ],
        recommendedTarget="src/components/test/utils/profiles.ts",
        movePhase="LIB-CLEAN-7-PROFILES-TEST-UTILS-MOVE",
        risk="LOW",
        prerequisites=["LIB-CLEAN-6-TESTSETS-COMMON-CONFIG-MOVE (profiles type-imports DocumentType from testsets sibling)"] ,
        notes=(
            "Single consumer: TestWorkspace (2 import lines). Test-feature-"
            "specific policy file. Its only dep is testsets (DocumentType "
            "type-only); after LIB-CLEAN-6 the sibling ./testsets becomes "
            "@/common/config/testsets."
        ),
        staticCheckScript="tmp/check_profiles_test_utils_move_pr1.mjs",
        staticCheckKeyItems=[
            "new file exists, old file absent",
            "all profile policy exports preserved",
            "TestWorkspace 2 import lines corrected",
            "TestWorkspace logic byte-equivalent after import-strip",
            "imports @/common/config/testsets (no @/lib/testsets / no sibling)",
            "no @/lib/profiles residual",
        ],
    ),
    "autofillEngine.ts": FileAnalysis(
        currentPath="src/lib/autofillEngine.ts",
        presentOnDisk=False, lineCount=0,
        mainResponsibility=(
            "Autofill business logic: candidate collection from history + "
            "restore profiles, suggestion building/sorting, apply-to-fields. "
            "Pure logic; no React/DOM/storage of its own — it composes the "
            "storage stores."
        ),
        exportsKey=[
            "AutofillSource/OutputValueSource/AutofillAction (types)",
            "AutofillSuggestion/AutofillCandidateRecord/AutofillRunStatus/"
            "AutofillRunSummary/AutofillFieldMetadata/AutofillOutputFieldLike",
            "AUTOFILLABLE_FIELDS",
            "normalizeAutofillFieldKey/isAutofillableField/isEmptyOcrValue",
            "canAutoApplySuggestion/sortAutofillSuggestions",
            "collectInternalAutofillCandidates/"
            "buildAutofillSuggestionsFromCandidates",
            "applyAutofillToOutputFields/suggestionsForHistoryField",
        ],
        importsSummary=[
            "@/common/utils/bizNumber",
            "@/common/storage/historyStore",
            "./restoreProfileStore",
        ],
        pureUtil=True, storagePersistence=False, configConstants=False, apiClient=False,
        featureSpecific="shared",
        reactDependency=False, browserApiDependency=False, localStorageDependency=False,
        backendDependency=False, componentsImport=False, commonImport=True,
        testWorkspaceImpact="NO_TEST_IMPACT", testCoreImpact=False,
        targetCandidates=[
            "src/common/utils/autofillEngine.ts",
        ],
        recommendedTarget="src/common/utils/autofillEngine.ts",
        movePhase="LIB-CLEAN-9-AUTOFILL-ENGINE-MOVE",
        risk="MEDIUM",
        prerequisites=[
            "LIB-CLEAN-5-RESTORE-PROFILE-STORE-MOVE (sibling ./restoreProfileStore becomes @/common/storage/restoreProfileStore)",
            "LIB-CLEAN-8-AUTOFILL-ENGINE-PRECHECK (impact assessment of 4 importers + cycle/storage check)",
        ],
        notes=(
            "Largest remaining file (485 lines). 4 importers: RunOcrWorkspace "
            "(runtime), DetailHistoryView (runtime), OcrResultPanel (type-only), "
            "common/utils/ocrResultFormatters (type-only — the lingering 1A "
            "dependency). Moving it dissolves the lingering @/lib/autofillEngine "
            "import in common/utils. Pure logic so common/utils is appropriate "
            "(no React/DOM)."
        ),
        staticCheckScript="tmp/check_autofill_engine_common_utils_move_af1.mjs",
        staticCheckKeyItems=[
            "new file exists, old file absent",
            "all 18+ exports preserved",
            "imports @/common/utils/bizNumber, @/common/storage/historyStore, "
            "@/common/storage/restoreProfileStore (sibling form gone)",
            "4 importers updated (RunOcrWorkspace, DetailHistoryView, "
            "OcrResultPanel, common/utils/ocrResultFormatters)",
            "no @/lib/autofillEngine residual ANYWHERE in src (including "
            "common/utils)",
            "no components/* import",
            "no React / DOM / localStorage / fetch import",
        ],
    ),
    "version.ts": FileAnalysis(
        currentPath="src/lib/version.ts",
        presentOnDisk=False, lineCount=0,
        mainResponsibility=(
            "Originally listed as a candidate but no longer present on disk."
        ),
        exportsKey=[],
        importsSummary=[],
        pureUtil=False, storagePersistence=False, configConstants=False, apiClient=False,
        featureSpecific="",
        reactDependency=False, browserApiDependency=False, localStorageDependency=False,
        backendDependency=False, componentsImport=False, commonImport=False,
        testWorkspaceImpact="NO_TEST_IMPACT", testCoreImpact=False,
        targetCandidates=[],
        recommendedTarget="N/A (file does not exist)",
        movePhase="N/A",
        risk="N/A",
        prerequisites=[],
        notes=(
            "Listed by the precheck spec but src/lib/version.ts is absent on "
            "disk. Likely removed in a prior cleanup and re-listed by mistake. "
            "No phase needed; no impact on the LIB close-out plan."
        ),
        staticCheckScript="N/A",
        staticCheckKeyItems=[],
    ),
}


# Phase order (low-risk leaves first; autofillEngine last with a precheck).
PHASES_ORDER = [
    ("LIB-CLEAN-1-THEME-MOVE", "theme.ts", "Single-importer React hook leaf — fastest win."),
    ("LIB-CLEAN-2-LOGIN-STORAGE-MOVE", "login.ts", "Foundation for axios; pure localStorage leaf."),
    ("LIB-CLEAN-3-AXIOS-API-MOVE", "axios.ts", "After login.ts so the sibling ./login import becomes @/common/storage/login."),
    ("LIB-CLEAN-4-GROUND-TRUTH-STORE-MOVE", "groundTruthStore.ts", "Persistence leaf; only 2 importers."),
    ("LIB-CLEAN-5-RESTORE-PROFILE-STORE-MOVE", "restoreProfileStore.ts", "Persistence leaf; clears autofillEngine sibling dep."),
    ("LIB-CLEAN-6-TESTSETS-COMMON-CONFIG-MOVE", "testsets.ts", "Introduces src/common/config/; 6 importers (4 API routes + TestWorkspace + profiles sibling)."),
    ("LIB-CLEAN-7-PROFILES-TEST-UTILS-MOVE", "profiles.ts", "After testsets move so ./testsets sibling resolves to @/common/config/testsets."),
    ("LIB-CLEAN-8-AUTOFILL-ENGINE-PRECHECK", "autofillEngine.ts", "Read-only impact analysis on the largest remaining file."),
    ("LIB-CLEAN-9-AUTOFILL-ENGINE-MOVE", "autofillEngine.ts", "Actual move; also resolves the lingering @/lib/autofillEngine import in common/utils/ocrResultFormatters."),
    ("LIB-CLEAN-10-SRC-LIB-ABSENT-CHECK", "(none)", "Final guard: src/lib must be empty or removed; no @/lib/* import anywhere in src; typecheck/build PASS."),
]


# -----------------------------------------------------------------------------
# Live re-validation helpers
# -----------------------------------------------------------------------------

LIB_IMPORT_PATTERNS = {
    name: [
        re.compile(rf'from\s+["\']@/lib/{re.escape(name[:-3])}["\']'),
        re.compile(rf'from\s+["\']\.\./lib/{re.escape(name[:-3])}["\']'),
        re.compile(rf'from\s+["\']\.\./\.\./lib/{re.escape(name[:-3])}["\']'),
        re.compile(rf'from\s+["\']\./{re.escape(name[:-3])}["\']'),  # sibling-in-lib form
    ]
    for name in EXPECTED_LIB_FILES
}


def iter_src_files() -> Iterable[Path]:
    if not SRC.exists():
        return []
    for p in SRC.rglob("*"):
        if p.is_file() and p.suffix in CODE_EXTS:
            yield p


def feature_for(rel_path: str) -> str:
    parts = rel_path.replace("\\", "/").split("/")
    if len(parts) >= 3 and parts[0] == "src":
        if parts[1] == "components" and len(parts) >= 4:
            return parts[2]
        if parts[1] == "app":
            return "app"
        if parts[1] == "common":
            return "common"
        if parts[1] == "lib":
            return "lib"
    return "other"


def file_imports_lib(text: str, lib_name: str, src_file: Path) -> tuple[bool, str | None, bool]:
    """Returns (matched, import_path_form, sibling_only_for_lib_file)."""
    base = lib_name[:-3]
    patterns = [
        (rf'from\s+["\'](@/lib/{re.escape(base)})["\']', "alias"),
        (rf'from\s+["\'](\.\.\./lib/{re.escape(base)})["\']', "relative"),
        (rf'from\s+["\'](\.\./lib/{re.escape(base)})["\']', "relative"),
        (rf'from\s+["\']\./{re.escape(base)}["\']', "sibling"),
    ]
    for pat, form in patterns:
        m = re.search(pat, text)
        if m:
            # Sibling form is only valid when the importer itself lives in src/lib.
            if form == "sibling":
                rel = src_file.resolve().relative_to(ROOT.resolve()).as_posix()
                if not rel.startswith("src/lib/"):
                    continue
            return True, form, form == "sibling"
    return False, None, False


def find_imported_by(lib_name: str) -> list[dict]:
    results: list[dict] = []
    for p in iter_src_files():
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        matched, form, _is_sibling = file_imports_lib(text, lib_name, p)
        if not matched:
            continue
        rel = p.resolve().relative_to(ROOT.resolve()).as_posix()
        if rel == f"src/lib/{lib_name}":
            continue  # self
        symbols = extract_imported_symbols(text, lib_name)
        type_only = is_type_only_import(text, lib_name)
        feature = feature_for(rel)
        results.append({
            "importer": rel,
            "form": form,
            "symbols": symbols,
            "typeOnly": type_only,
            "feature": feature,
            "testWorkspace": rel == "src/components/test/TestWorkspace.tsx",
            "testCore": rel.startswith("src/components/test/core/"),
            "importPathFixNeeded": True,
        })
    return results


def extract_imported_symbols(text: str, lib_name: str) -> list[str]:
    base = lib_name[:-3]
    pat = re.compile(
        r'import\s+(?:(?:type\s+)?(?:\*\s+as\s+\w+|\{[^}]*\}|\w+(?:\s*,\s*\{[^}]*\})?))\s+from\s+["\'][^"\']*' +
        re.escape(base) + r'["\']'
    )
    out: list[str] = []
    for m in pat.finditer(text):
        seg = m.group(0)
        for sym_match in re.finditer(r'\{([^}]*)\}', seg):
            for raw in sym_match.group(1).split(","):
                s = raw.strip()
                if not s:
                    continue
                s = re.sub(r'^type\s+', "", s)
                s = re.sub(r'\s+as\s+\w+$', "", s)
                out.append(s)
        default_match = re.search(r'import\s+(?:type\s+)?(\w+)\s*(?:,|from)', seg)
        if default_match and default_match.group(1) not in ("type",):
            sym = default_match.group(1)
            if sym not in out and not re.match(r'^\{', seg.split("import")[1].strip()):
                out.append(f"default as {sym}")
    return out


def is_type_only_import(text: str, lib_name: str) -> bool:
    base = lib_name[:-3]
    pat = re.compile(
        r'import\s+type\s+\{[^}]*\}\s+from\s+["\'][^"\']*' + re.escape(base) + r'["\']'
    )
    return bool(pat.search(text))


def git_status_short() -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--short"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return [line for line in proc.stdout.splitlines() if line.strip()]
    except Exception as e:
        return [f"<git status failed: {e}>"]


def gather() -> dict:
    # Re-validate each analysis against the live filesystem.
    analyses_out: list[dict] = []
    for name, ana in ANALYSES.items():
        p = LIB_DIR / name
        ana.presentOnDisk = p.exists()
        ana.lineCount = 0
        if ana.presentOnDisk:
            try:
                ana.lineCount = sum(1 for _ in p.open(encoding="utf-8"))
            except Exception:
                pass
        # importedBy only meaningful when the file is still in src/lib.
        if ana.presentOnDisk:
            ib = find_imported_by(name)
            ana.importedByFiles = ib
            ana.importedByCount = len(ib)
        analyses_out.append(asdict(ana))

    dirty = git_status_short()
    templates_dirty = any("data/templates.json" in line for line in dirty)
    return {
        "analyses": analyses_out,
        "dirty": dirty,
        "templatesJsonDirty": templates_dirty,
    }


def write_outputs() -> dict:
    data = gather()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = DOCS_DIR / "FRONTEND_REMAINING_LIB_FULL_CLEANUP_PLAN_PRECHECK_20260522.json"
    csv_path = DOCS_DIR / "FRONTEND_REMAINING_LIB_FULL_CLEANUP_MAP_20260522.csv"

    summary = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "codeModified": False,
        "remainingLibFiles": [
            a["currentPath"] for a in data["analyses"] if a["presentOnDisk"]
        ],
        "missingFromSpec": [
            a["currentPath"] for a in data["analyses"] if not a["presentOnDisk"]
        ],
        "fileAnalyses": data["analyses"],
        "targetRecommendations": [
            {
                "currentPath": a["currentPath"],
                "recommendedTarget": a["recommendedTarget"],
                "targetCandidates": a["targetCandidates"],
                "movePhase": a["movePhase"],
                "risk": a["risk"],
                "prerequisites": a["prerequisites"],
            }
            for a in data["analyses"] if a["presentOnDisk"]
        ],
        "movePhases": [
            {"phase": p, "primaryFile": f, "notes": n}
            for p, f, n in PHASES_ORDER
        ],
        "testWorkspaceImpact": [
            {
                "currentPath": a["currentPath"],
                "testWorkspaceImpact": a["testWorkspaceImpact"],
                "testCoreImpact": a["testCoreImpact"],
            }
            for a in data["analyses"] if a["presentOnDisk"]
        ],
        "staticCheckPlan": [
            {
                "phase": a["movePhase"],
                "script": a["staticCheckScript"],
                "keyItems": a["staticCheckKeyItems"],
            }
            for a in data["analyses"] if a["presentOnDisk"]
        ] + [{
            "phase": "LIB-CLEAN-10-SRC-LIB-ABSENT-CHECK",
            "script": "tmp/check_src_lib_absent_final.mjs",
            "keyItems": [
                "src/lib directory empty or removed",
                "no @/lib/* import anywhere in src",
                "typecheck/build PASS",
            ],
        }],
        "srcLibCloseDecision": "CAN_CLOSE_LIB_AFTER_PLANNED_MOVES",
        "dirty": data["dirty"],
        "templatesJsonDirty": data["templatesJsonDirty"],
        "nextSteps": [
            "Run LIB-CLEAN-1-THEME-MOVE (single-importer hook, lowest risk).",
            "Then proceed phase-by-phase per the movePhases order; each phase: "
            "backup -> git mv -> import path fix -> tmp static check -> "
            "typecheck/build -> reports.",
            "After LIB-CLEAN-9 finishes, run LIB-CLEAN-10 to assert "
            "src/lib is empty/absent and zero @/lib/* residuals remain.",
            "Only after LIB-CLEAN-10 PASS, begin Template table column "
            "definition feature precheck.",
        ],
    }

    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "currentPath", "role", "importedByCount", "mainConsumers",
            "recommendedTarget", "movePhase", "risk",
            "testWorkspaceImpact", "prerequisites", "notes",
        ])
        for a in data["analyses"]:
            consumers = ";".join(sorted({i["importer"] for i in a["importedByFiles"]}))
            w.writerow([
                a["currentPath"],
                a["mainResponsibility"].split(".")[0],
                a["importedByCount"],
                consumers,
                a["recommendedTarget"],
                a["movePhase"],
                a["risk"],
                a["testWorkspaceImpact"],
                "; ".join(a["prerequisites"]),
                a["notes"].replace("\n", " "),
            ])

    return summary


if __name__ == "__main__":
    s = write_outputs()
    print("[precheck] generated:")
    print(f"  json: docs/FRONTEND_REMAINING_LIB_FULL_CLEANUP_PLAN_PRECHECK_20260522.json")
    print(f"  csv:  docs/FRONTEND_REMAINING_LIB_FULL_CLEANUP_MAP_20260522.csv")
    print(f"  remainingLibFiles: {len(s['remainingLibFiles'])}")
    print(f"  missingFromSpec:   {len(s['missingFromSpec'])}")
    print(f"  srcLibCloseDecision: {s['srcLibCloseDecision']}")
