#!/usr/bin/env node
/**
 * JS-side Clean JSON v1 fixture checker.
 *
 * Purpose:
 * - Directly import src/lib/cleanJsonBuilder.ts through a tiny local TS
 *   transpilation step.
 * - Build helper inputs in memory from locked Clean JSON v1 fixtures.
 * - Compare buildCleanJsonResult(...) output with the locked fixtures.
 *
 * This script never writes fixture files.
 */

import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const __filename = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(__filename), "..");
const TASK = "CODEX_FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER";
const FIXTURE_ROOT = path.join(ROOT, "tmp", "fixtures", "clean_json_v1");
const MANIFEST_PATH = path.join(FIXTURE_ROOT, "manifest.json");
const REPORT_JSON = path.join(ROOT, "docs", "FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json");
const REPORT_MD = path.join(ROOT, "docs", "FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md");
const BUILD_DIR = path.join(ROOT, "tmp", ".clean_json_fixture_runner_build");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + "\n", "utf8");
}

function runCommand(command, args, cwd = ROOT, timeoutMs = 300000) {
  const started = performance.now();
  const isWindowsCmd = process.platform === "win32" && command.toLowerCase().endsWith(".cmd");
  const actualCommand = isWindowsCmd ? "cmd.exe" : command;
  const actualArgs = isWindowsCmd ? ["/c", command, ...args] : args;
  const result = spawnSync(actualCommand, actualArgs, {
    cwd,
    encoding: "utf8",
    timeout: timeoutMs,
    shell: false,
  });
  return {
    command: [command, ...args].join(" "),
    status: result.status === 0 ? "PASS" : "FAIL",
    exitCode: result.status,
    durationSeconds: Number(((performance.now() - started) / 1000).toFixed(3)),
    stdoutTail: (result.stdout || "").slice(-4000),
    stderrTail: (result.stderr || "").slice(-4000),
    error: result.error ? String(result.error) : "",
  };
}

function gitStatus() {
  const result = runCommand("git", ["-c", "safe.directory=D:/Free_Vue/OCR", "status", "--short"], path.resolve(ROOT, ".."));
  const entries = (result.stdoutTail || "").split(/\r?\n/).filter(Boolean);
  return { isDirty: entries.length > 0, entries, command: result };
}

function transpileTsToCjs(sourcePath, outPath, replacements = []) {
  let source = fs.readFileSync(sourcePath, "utf8");
  for (const [from, to] of replacements) {
    source = source.replaceAll(from, to);
  }
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
      strict: true,
    },
    fileName: sourcePath,
  }).outputText;
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, output, "utf8");
}

async function loadBuilder() {
  fs.rmSync(BUILD_DIR, { recursive: true, force: true });
  fs.mkdirSync(BUILD_DIR, { recursive: true });
  const invoiceSrc = path.join(ROOT, "src", "lib", "invoiceTableDisplay.ts");
  const builderSrc = path.join(ROOT, "src", "lib", "cleanJsonBuilder.ts");
  const invoiceOut = path.join(BUILD_DIR, "invoiceTableDisplay.cjs");
  const builderOut = path.join(BUILD_DIR, "cleanJsonBuilder.cjs");
  transpileTsToCjs(invoiceSrc, invoiceOut);
  transpileTsToCjs(builderSrc, builderOut, [["@/lib/invoiceTableDisplay", "./invoiceTableDisplay.cjs"]]);
  const mod = require(builderOut);
  if (typeof mod.buildCleanJsonResult !== "function") {
    throw new Error("buildCleanJsonResult export was not found");
  }
  return {
    buildCleanJsonResult: mod.buildCleanJsonResult,
    importMode: "typescript.transpileModule to transient tmp/.clean_json_fixture_runner_build/*.cjs, then require()",
    generatedFiles: [
      path.relative(ROOT, invoiceOut),
      path.relative(ROOT, builderOut),
    ],
  };
}

function stableStringify(value) {
  return JSON.stringify(value, null, 2);
}

function diffValues(expected, actual, basePath = "$", diffs = []) {
  if (Object.is(expected, actual)) return diffs;
  if (typeof expected !== typeof actual) {
    diffs.push({ path: basePath, expectedType: typeof expected, actualType: typeof actual, expected, actual });
    return diffs;
  }
  if (expected === null || actual === null || typeof expected !== "object") {
    diffs.push({ path: basePath, expected, actual });
    return diffs;
  }
  if (Array.isArray(expected) || Array.isArray(actual)) {
    if (!Array.isArray(expected) || !Array.isArray(actual)) {
      diffs.push({ path: basePath, expected, actual });
      return diffs;
    }
    if (expected.length !== actual.length) {
      diffs.push({ path: `${basePath}.length`, expected: expected.length, actual: actual.length });
    }
    const max = Math.max(expected.length, actual.length);
    for (let i = 0; i < max; i += 1) diffValues(expected[i], actual[i], `${basePath}[${i}]`, diffs);
    return diffs;
  }
  const expectedKeys = Object.keys(expected);
  const actualKeys = Object.keys(actual);
  if (expectedKeys.join("\u0000") !== actualKeys.join("\u0000")) {
    diffs.push({ path: `${basePath}.__keys`, expected: expectedKeys, actual: actualKeys });
  }
  const keys = Array.from(new Set([...expectedKeys, ...actualKeys]));
  for (const key of keys) diffValues(expected[key], actual[key], `${basePath}.${key}`, diffs);
  return diffs;
}

function makeInputFromFixture(fixture) {
  const fields = [];
  for (const item of fixture.info || []) {
    fields.push({
      name: item.key,
      field_type: "field",
      value: item.value,
      ko: item.label,
    });
  }
  let docTableRows = null;
  let docTableDisplayCols = null;
  for (const table of fixture.tables || []) {
    fields.push({
      name: table.key,
      field_type: "table",
      ko: table.label,
    });
    if (!docTableRows && Array.isArray(table.rows)) {
      docTableRows = table.rows.map((row) => ({ ...row }));
      const firstRow = table.rows[0] || {};
      docTableDisplayCols = Object.keys(firstRow).map((key) => ({ key }));
    }
  }
  return {
    templateName: fixture.templateName,
    fields,
    docTableRows,
    docTableDisplayCols,
  };
}

function validateSpecialPolicy(caseEntry, fixture, output) {
  const firstTable = output.tables?.[0] || null;
  const rowKeys = firstTable?.rows?.[0] ? Object.keys(firstTable.rows[0]) : [];
  const fixtureRowKeys = fixture.tables?.[0]?.rows?.[0] ? Object.keys(fixture.tables[0].rows[0]) : [];
  const rowIndexActual = rowKeys.includes("rowIndex") ? "included" : "excluded";
  const rowIndexExpected = caseEntry.rowIndexExpected || null;
  const warnings = [];
  const checks = {
    rowKeys,
    fixtureRowKeys,
    previewCleanJsonColumnOrderSame: rowKeys.join("\u0000") === fixtureRowKeys.join("\u0000"),
    rowIndexExpected,
    rowIndexActual: rowIndexExpected ? rowIndexActual : null,
    rowIndexPolicyPass: rowIndexExpected ? rowIndexExpected === rowIndexActual : true,
    receiptFieldOnlyPass: caseEntry.caseId.startsWith("tpl_")
      ? Array.isArray(output.info) && output.info.length === 6 && !output.tables
      : true,
    trade3LockedBehaviorPass: caseEntry.caseId === "trade_3_3pdf"
      ? rowKeys.includes("insuranceCode") && rowKeys.includes("amount")
      : true,
  };
  if (caseEntry.caseId === "trade_3_3pdf" && checks.trade3LockedBehaviorPass) {
    warnings.push("unresolved but locked current behavior preserved: insuranceCode, amount");
  }
  return { ...checks, warnings };
}

function mdTable(headers, rows) {
  const out = [];
  out.push(`| ${headers.join(" | ")} |`);
  out.push(`| ${headers.map(() => "---").join(" | ")} |`);
  for (const row of rows) out.push(`| ${row.map((cell) => String(cell ?? "")).join(" | ")} |`);
  return out.join("\n");
}

function makeMarkdown(report) {
  const rows = report.cases.map((item) => [
    item.caseId,
    item.status,
    item.diffCount,
    item.rowIndexActual ?? "",
    (item.rowKeys || []).join(", "),
    item.fixturePath,
  ]);
  return `# FRONTEND CLEANUP 1B JS CLEAN JSON FIXTURE RUNNER 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: \`${TASK}\`
- 생성 시각: \`${report.generatedAt}\`

## 2. 코드 수정 여부
- 운영 기능 코드는 수정하지 않았다.
- Clean JSON 출력 로직, OcrResultPanel, invoiceTableDisplay, backend/parser/templates/manifest/GT, fixture output JSON은 수정하지 않았다.
- 생성/갱신한 것은 JS fixture runner와 docs 리포트뿐이다.

## 3. Runner 구현 방식
- 선택 방식: \`${report.runnerMode}\`
- 이유: ${report.runnerReason}
- import 방식: ${report.importMode}
- fixture manifest: \`${report.manifestPath}\`
- fixture 파일은 읽기 전용으로 사용했다.

## 4. JS Fixture Deep Equality 결과
- overall: \`${report.summary.overall}\`
- total cases: ${report.summary.total}
- pass: ${report.summary.pass}
- fail: ${report.summary.fail}
- total diffs: ${report.summary.totalDiffs}

${mdTable(["caseId", "status", "diffs", "rowIndex", "rowKeys", "fixture"], rows)}

## 5. rowIndex / 거래_3 / 영수증 확인
- 거래_1/4/5/7 rowIndex 제외: ${report.policyChecks.rowIndexExcludedPass ? "PASS" : "FAIL"}
- 거래_2/3/6 rowIndex 유지: ${report.policyChecks.rowIndexIncludedPass ? "PASS" : "FAIL"}
- 거래_3 insuranceCode/amount locked behavior: ${report.policyChecks.trade3LockedBehaviorPass ? "PASS" : "FAIL"}
- 영수증 TPL-003 1.jpg/2.jpg field-only shape: ${report.policyChecks.receiptFieldOnlyPass ? "PASS" : "FAIL"}

## 6. Helper 순수성 재확인
- React hook import 없음: ${report.purity.reactHookFree ? "PASS" : "FAIL"}
- DOM/window/localStorage/network 접근 없음: ${report.purity.noBrowserOrNetworkAccess ? "PASS" : "FAIL"}
- Raw JSON/copy/export/UI state 책임 없음: ${report.purity.noUiResponsibility ? "PASS" : "FAIL"}
- 입력 mutation 없음: ${report.purity.inputMutationFree ? "PASS" : "FAIL"}

## 7. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | --- | --- |
| npm run typecheck | ${report.typecheck.status} | ${report.typecheck.exitCode} | ${report.typecheck.durationSeconds} |
| npm run build | ${report.build.status} | ${report.build.exitCode} | ${report.build.durationSeconds} |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: \`ESLint: nextVitals is not iterable\` can appear with build exit code 0.

## 8. 남은 리스크
- 이 runner는 helper를 직접 검증하지만, OCR API를 재실행하지 않는다.
- 입력은 locked fixture에서 메모리로 합성하므로 API-to-helper integration 회귀는 기존 Python fixture check와 함께 봐야 한다.
- table_data legacy fallback 전용 fixture는 아직 별도로 없다.

## 9. 다음 작업 제안
1. FRONTEND-CLEANUP 후속 작업마다 이 JS runner를 회귀 검증으로 실행한다.
2. 필요하면 별도 작업에서 API 기반 input fixture를 추가해 integration coverage를 넓힌다.
3. 거래_3 insuranceCode/amount 정책은 별도 이슈로 유지한다.
`;
}

function sourcePurityCheck(inputMutationFree) {
  const source = fs.readFileSync(path.join(ROOT, "src", "lib", "cleanJsonBuilder.ts"), "utf8");
  return {
    reactHookFree: !/from\s+["']react["']|useMemo|useState|useEffect|useRef/.test(source),
    noBrowserOrNetworkAccess: !/\bwindow\b|\bdocument\b|\blocalStorage\b|\bsessionStorage\b|\bfetch\s*\(|XMLHttpRequest/.test(source),
    noUiResponsibility: !/clipboard|Blob|URL\.createObjectURL|previewMode|handleCopy|handleExport|Raw JSON|toCleanJson/.test(source),
    inputMutationFree,
  };
}

async function main() {
  const builder = await loadBuilder();
  const manifest = readJson(MANIFEST_PATH);
  const cases = [];
  let inputMutationFree = true;

  for (const item of manifest.cases) {
    const fixturePath = path.join(FIXTURE_ROOT, item.fixturePath);
    const fixture = readJson(fixturePath);
    const input = makeInputFromFixture(fixture);
    const beforeInput = stableStringify(input);
    const actual = builder.buildCleanJsonResult(input);
    const afterInput = stableStringify(input);
    if (beforeInput !== afterInput) inputMutationFree = false;
    const diffs = diffValues(fixture, actual).slice(0, 50);
    const orderedStringEqual = stableStringify(fixture) === stableStringify(actual);
    const policy = validateSpecialPolicy(item, fixture, actual);
    const status = diffs.length === 0 && orderedStringEqual && policy.rowIndexPolicyPass && policy.receiptFieldOnlyPass && policy.trade3LockedBehaviorPass
      ? "PASS"
      : "FAIL";
    cases.push({
      caseId: item.caseId,
      templateName: item.templateName,
      templateId: item.templateId,
      inputFile: item.inputFile,
      fixturePath: item.fixturePath,
      status,
      diffCount: diffs.length,
      orderedStringEqual,
      diffs,
      warnings: policy.warnings,
      rowIndexExpected: policy.rowIndexExpected,
      rowIndexActual: policy.rowIndexActual,
      rowKeys: policy.rowKeys,
      fixtureRowKeys: policy.fixtureRowKeys,
      previewCleanJsonColumnOrderSame: policy.previewCleanJsonColumnOrderSame,
      receiptFieldOnlyPass: policy.receiptFieldOnlyPass,
      trade3LockedBehaviorPass: policy.trade3LockedBehaviorPass,
    });
  }

  const summary = {
    total: cases.length,
    pass: cases.filter((item) => item.status === "PASS").length,
    fail: cases.filter((item) => item.status !== "PASS").length,
    totalDiffs: cases.reduce((sum, item) => sum + item.diffCount, 0),
  };
  summary.overall = summary.fail === 0 ? "PASS" : "FAIL";

  const byId = Object.fromEntries(cases.map((item) => [item.caseId, item]));
  const policyChecks = {
    rowIndexExcludedPass: ["trade_1_1jpg", "trade_4_4pdf", "trade_5_5pdf", "trade_7_7pdf"].every((id) => byId[id]?.rowIndexActual === "excluded"),
    rowIndexIncludedPass: ["trade_2_2pdf", "trade_3_3pdf", "trade_6_6pdf"].every((id) => byId[id]?.rowIndexActual === "included"),
    trade3LockedBehaviorPass: byId.trade_3_3pdf?.trade3LockedBehaviorPass === true,
    receiptFieldOnlyPass: ["tpl_003_1jpg", "tpl_003_2jpg"].every((id) => byId[id]?.receiptFieldOnlyPass === true),
  };

  console.log(`[${TASK}] direct helper fixture check ${summary.overall}: ${summary.pass}/${summary.total} PASS`);
  for (const item of cases) {
    console.log(`[case] ${item.caseId} ${item.status} diffs=${item.diffCount}`);
    for (const diff of item.diffs.slice(0, 5)) console.log(`  diff ${diff.path}`);
  }

  console.log("[check] running npm run typecheck");
  const typecheck = runCommand("npm.cmd", ["run", "typecheck"], ROOT, 180000);
  console.log(`[check] typecheck=${typecheck.status} duration=${typecheck.durationSeconds}s`);
  console.log("[check] running npm run build");
  const build = runCommand("npm.cmd", ["run", "build"], ROOT, 300000);
  console.log(`[check] build=${build.status} duration=${build.durationSeconds}s`);

  const report = {
    task: TASK,
    generatedAt: new Date().toISOString(),
    toolAndModel: { tool: "Codex", model: "Codex" },
    codeModification: {
      productionCodeModifiedByThisTask: false,
      fixtureFilesModified: false,
      generatedFiles: [
        "tmp/check_clean_json_v1_fixtures_js.mjs",
        "docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md",
        "docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json",
      ],
    },
    runnerMode: "B-lite / fixture-derived in-memory input",
    runnerReason: "No extra dependency or API rerun is required; locked output fixtures are read-only, converted to the current helper input contract in memory, then compared by deep equality and ordered stringify.",
    importMode: builder.importMode,
    transpiledTempFiles: builder.generatedFiles,
    transpiledTempFilesCleanedAfterRun: true,
    manifestPath: path.relative(ROOT, MANIFEST_PATH),
    fixtureRoot: path.relative(ROOT, FIXTURE_ROOT),
    cases,
    summary,
    policyChecks,
    purity: sourcePurityCheck(inputMutationFree),
    typecheck,
    build,
    knownStderrNoise: {
      id: "ISSUE-FRONTEND-BUILD-LOG-1",
      message: "ESLint: nextVitals is not iterable",
      observed: (build.stderrTail || "").includes("nextVitals is not iterable"),
      buildExitCode: build.exitCode,
    },
    repoDirtyStatus: gitStatus(),
    remainingRisks: [
      "API-to-helper integration is not rerun by this JS runner.",
      "Inputs are synthesized from locked fixtures, so legacy table_data fallback needs a dedicated fixture if required.",
      "Existing dirty production files were not modified by this task.",
    ],
  };

  writeJson(REPORT_JSON, report);
  fs.writeFileSync(REPORT_MD, makeMarkdown(report), "utf8");
  fs.rmSync(BUILD_DIR, { recursive: true, force: true });
  console.log(`[write] ${REPORT_JSON}`);
  console.log(`[write] ${REPORT_MD}`);

  const ok = summary.overall === "PASS"
    && Object.values(policyChecks).every(Boolean)
    && Object.values(report.purity).every(Boolean)
    && typecheck.status === "PASS"
    && build.status === "PASS";
  process.exit(ok ? 0 : 1);
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exit(1);
});
