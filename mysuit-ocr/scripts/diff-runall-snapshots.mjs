#!/usr/bin/env node
/**
 * T-12d: RunAll snapshot before/after diff tool
 *
 * Usage:
 *   node scripts/diff-runall-snapshots.mjs <before.json> <after.json> [output-dir]
 *   npm run diff:runall -- before.json after.json
 *
 * Compares two T-12c RunAll snapshot JSONs and generates:
 *   - JSON diff file
 *   - Markdown diff report
 */

import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { resolve, dirname, join, basename } from "path";

// ── Helpers ──────────────────────────────────────────────────────────────────

function loadSnapshot(filePath) {
  const abs = resolve(filePath);
  let text;
  try {
    text = readFileSync(abs, "utf-8");
  } catch (e) {
    console.error(`[ERROR] Cannot read file: ${abs}\n  ${e.message}`);
    process.exit(1);
  }
  try {
    return { data: JSON.parse(text), path: abs };
  } catch (e) {
    console.error(`[ERROR] JSON parse failed: ${abs}\n  ${e.message}`);
    process.exit(1);
  }
}

function numDelta(a, b) {
  const d = (b ?? 0) - (a ?? 0);
  return d > 0 ? `+${d}` : String(d);
}

function sign(n) {
  return n > 0 ? "+" : n < 0 ? "" : "";
}

function pad(s, len) {
  return String(s ?? "—").padStart(len);
}

function tableRow(cells) {
  return `| ${cells.join(" | ")} |`;
}

function tsNow() {
  const d = new Date();
  return (
    String(d.getFullYear()) +
    String(d.getMonth() + 1).padStart(2, "0") +
    String(d.getDate()).padStart(2, "0") +
    "_" +
    String(d.getHours()).padStart(2, "0") +
    String(d.getMinutes()).padStart(2, "0")
  );
}

// ── Core diff logic ───────────────────────────────────────────────────────────

function diffRowCountSummary(bRc, aRc) {
  const keys = ["exact", "short", "over", "unknown", "samplesWithExpected"];
  const delta = {};
  for (const k of keys) {
    delta[k] = (aRc?.[k] ?? 0) - (bRc?.[k] ?? 0);
  }
  return delta;
}

function diffRecordCounts(bCounts, aCounts) {
  const allKeys = new Set([
    ...Object.keys(bCounts ?? {}),
    ...Object.keys(aCounts ?? {}),
  ]);
  const result = [];
  for (const k of allKeys) {
    const before = bCounts?.[k] ?? 0;
    const after = aCounts?.[k] ?? 0;
    const delta = after - before;
    if (delta !== 0) {
      result.push({ key: k, before, after, delta });
    }
  }
  return result.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
}

function diffDocumentTypeSummary(bDts, aDts) {
  const bMap = new Map((bDts ?? []).map((r) => [r.documentType, r]));
  const aMap = new Map((aDts ?? []).map((r) => [r.documentType, r]));
  const allDts = new Set([...bMap.keys(), ...aMap.keys()]);
  const diffs = [];
  for (const dt of allDts) {
    const b = bMap.get(dt) ?? {};
    const a = aMap.get(dt) ?? {};
    const rowExactDelta = (a.rowExactCount ?? 0) - (b.rowExactCount ?? 0);
    const rowShortDelta = (a.rowShortCount ?? 0) - (b.rowShortCount ?? 0);
    const rowOverDelta = (a.rowOverCount ?? 0) - (b.rowOverCount ?? 0);
    const warnDelta = (a.tableRowsWarningCount ?? 0) - (b.tableRowsWarningCount ?? 0);
    const missingDiffs = diffRecordCounts(b.missingFieldCounts, a.missingFieldCounts);
    const warningDiffs = diffRecordCounts(b.warningTypeCounts, a.warningTypeCounts);
    const totalMissingDelta = missingDiffs.reduce((s, d) => s + d.delta, 0);
    let verdict = "unchanged";
    if (rowExactDelta > 0 || totalMissingDelta < 0) verdict = "improved";
    else if (rowExactDelta < 0 || totalMissingDelta > 0) verdict = "regressed";
    diffs.push({
      documentType: dt,
      before: { total: b.total, selected: b.selected, rowExactCount: b.rowExactCount, rowShortCount: b.rowShortCount, rowOverCount: b.rowOverCount, tableRowsWarningCount: b.tableRowsWarningCount },
      after: { total: a.total, selected: a.selected, rowExactCount: a.rowExactCount, rowShortCount: a.rowShortCount, rowOverCount: a.rowOverCount, tableRowsWarningCount: a.tableRowsWarningCount },
      deltas: { rowExact: rowExactDelta, rowShort: rowShortDelta, rowOver: rowOverDelta, warning: warnDelta },
      missingFieldDiffs: missingDiffs,
      warningTypeDiffs: warningDiffs,
      verdict,
    });
  }
  return diffs;
}

function diffSamples(bSamples, aSamples) {
  const bMap = new Map((bSamples ?? []).map((s) => [s.filename, s]));
  const aMap = new Map((aSamples ?? []).map((s) => [s.filename, s]));
  const allFiles = new Set([...bMap.keys(), ...aMap.keys()]);
  const diffs = [];

  for (const filename of allFiles) {
    const b = bMap.get(filename);
    const a = aMap.get(filename);

    if (!b) { diffs.push({ filename, verdict: "new", before: null, after: a }); continue; }
    if (!a) { diffs.push({ filename, verdict: "removed", before: b, after: null }); continue; }

    const rowStatusChanged = b.rowCountStatus !== a.rowCountStatus;
    const rowImproved = b.rowCountStatus !== "exact" && a.rowCountStatus === "exact";
    const rowRegressed = b.rowCountStatus === "exact" && a.rowCountStatus !== "exact";
    const rowActualDelta = (a.actualRowCount ?? 0) - (b.actualRowCount ?? 0);

    const missingBefore = (b.missingFields ?? []).length;
    const missingAfter = (a.missingFields ?? []).length;
    const missingDelta = missingAfter - missingBefore;

    const warnBefore = (b.valueMappingWarnings ?? []).length;
    const warnAfter = (a.valueMappingWarnings ?? []).length;
    const warnDelta = warnAfter - warnBefore;

    const statusChanged = b.status !== a.status;
    const docTypeChanged = b.docType !== a.docType;
    const sourceChanged = b.extractionSource !== a.extractionSource;

    // Determine verdict
    let verdict = "unchanged";
    const improvements = [];
    const regressions = [];

    if (rowImproved) improvements.push(`rowCount: ${b.rowCountStatus} → ${a.rowCountStatus}`);
    if (rowRegressed) regressions.push(`rowCount: ${b.rowCountStatus} → ${a.rowCountStatus}`);
    if (missingDelta < 0) improvements.push(`missing: ${missingBefore} → ${missingAfter}`);
    if (missingDelta > 0) regressions.push(`missing: ${missingBefore} → ${missingAfter}`);
    if (a.status === "selected" && b.status !== "selected") improvements.push(`status: ${b.status} → ${a.status}`);
    if (b.status === "selected" && a.status !== "selected") regressions.push(`status: ${b.status} → ${a.status}`);

    if (improvements.length > 0 && regressions.length === 0) verdict = "improved";
    else if (regressions.length > 0 && improvements.length === 0) verdict = "regressed";
    else if (improvements.length > 0 || regressions.length > 0) verdict = "mixed";

    diffs.push({
      filename,
      verdict,
      improvements,
      regressions,
      before: {
        rowCountStatus: b.rowCountStatus, actualRowCount: b.actualRowCount,
        expectedRowCount: b.expectedRowCount, missingFieldsCount: missingBefore,
        warningCount: warnBefore, status: b.status, docType: b.docType,
        extractionSource: b.extractionSource,
      },
      after: {
        rowCountStatus: a.rowCountStatus, actualRowCount: a.actualRowCount,
        expectedRowCount: a.expectedRowCount, missingFieldsCount: missingAfter,
        warningCount: warnAfter, status: a.status, docType: a.docType,
        extractionSource: a.extractionSource,
      },
      deltas: { rowActual: rowActualDelta, missing: missingDelta, warning: warnDelta },
      changed: { rowStatus: rowStatusChanged, status: statusChanged, docType: docTypeChanged, source: sourceChanged },
    });
  }
  return diffs.sort((a, b) => {
    const order = { regressed: 0, mixed: 1, improved: 2, unchanged: 3, new: 4, removed: 5 };
    return (order[a.verdict] ?? 9) - (order[b.verdict] ?? 9);
  });
}

function diffMissingFields(bMfs, aMfs) {
  const allDts = new Set([...Object.keys(bMfs ?? {}), ...Object.keys(aMfs ?? {})]);
  const result = {};
  for (const dt of allDts) {
    const d = diffRecordCounts(bMfs?.[dt], aMfs?.[dt]);
    if (d.length > 0) result[dt] = d;
  }
  return result;
}

function diffWarningSummary(bWs, aWs) {
  const allDts = new Set([...Object.keys(bWs ?? {}), ...Object.keys(aWs ?? {})]);
  const result = {};
  for (const dt of allDts) {
    const d = diffRecordCounts(bWs?.[dt], aWs?.[dt]);
    if (d.length > 0) result[dt] = d;
  }
  return result;
}

// ── Markdown generation ───────────────────────────────────────────────────────

function buildMarkdown(diff) {
  const lines = [];
  const { before, after, summary, documentTypeDiffs, sampleDiffs, missingFieldDiffs, warningDiffs } = diff;

  lines.push("# RunAll Snapshot Diff Report");
  lines.push("");

  // 1. 입력 파일
  lines.push("## 1. 입력 파일");
  lines.push(`- **before**: \`${before.file}\` (생성: ${before.generatedAt}, testset: ${before.testsetId})`);
  lines.push(`- **after**: \`${after.file}\` (생성: ${after.generatedAt}, testset: ${after.testsetId})`);
  lines.push(`- **diff 생성**: ${diff.generatedAt}`);
  lines.push("");

  // 2. 전체 요약
  lines.push("## 2. 전체 요약");
  const s = summary;
  lines.push("| 항목 | before | after | delta |");
  lines.push("|---|---:|---:|---:|");
  lines.push(`| totalSamples | ${s.totalSamplesBefore} | ${s.totalSamplesAfter} | ${numDelta(s.totalSamplesBefore, s.totalSamplesAfter)} |`);
  lines.push(`| samplesRun | ${s.samplesRunBefore} | ${s.samplesRunAfter} | ${numDelta(s.samplesRunBefore, s.samplesRunAfter)} |`);
  lines.push(`| improved | — | ${s.improvedCount} | — |`);
  lines.push(`| regressed | — | ${s.regressedCount} | — |`);
  lines.push(`| unchanged | — | ${s.unchangedCount} | — |`);
  lines.push("");

  // 3. rowCount 변화
  const rc = s.rowCountSummaryDelta;
  if (rc) {
    lines.push("## 3. rowCount 집계 변화");
    lines.push("| 상태 | before | after | delta |");
    lines.push("|---|---:|---:|---:|");
    const rcKeys = ["exact", "short", "over", "unknown"];
    for (const k of rcKeys) {
      const bv = diff.beforeData.summary?.rowCountSummary?.[k] ?? 0;
      const av = diff.afterData.summary?.rowCountSummary?.[k] ?? 0;
      const d = rc[k] ?? 0;
      const color = k === "exact" ? (d > 0 ? " ✓" : d < 0 ? " ✗" : "") : (d < 0 ? " ✓" : d > 0 ? " ✗" : "");
      lines.push(`| ${k}${color} | ${bv} | ${av} | ${numDelta(bv, av)} |`);
    }
    lines.push("");
  }

  // 4. 개선 샘플
  const improved = sampleDiffs.filter((d) => d.verdict === "improved");
  if (improved.length > 0) {
    lines.push("## 4. 개선 샘플");
    lines.push("| 파일 | 변화 항목 |");
    lines.push("|---|---|");
    for (const d of improved) {
      lines.push(`| ${d.filename} | ${d.improvements.join("; ")} |`);
    }
    lines.push("");
  }

  // 5. 회귀 샘플
  const regressed = sampleDiffs.filter((d) => d.verdict === "regressed");
  if (regressed.length > 0) {
    lines.push("## 5. 회귀 샘플");
    lines.push("| 파일 | 변화 항목 |");
    lines.push("|---|---|");
    for (const d of regressed) {
      lines.push(`| ${d.filename} | ${d.regressions.join("; ")} |`);
    }
    lines.push("");
  }

  // Mixed
  const mixed = sampleDiffs.filter((d) => d.verdict === "mixed");
  if (mixed.length > 0) {
    lines.push("## 5b. 혼재 샘플 (개선+회귀)");
    lines.push("| 파일 | 개선 | 회귀 |");
    lines.push("|---|---|---|");
    for (const d of mixed) {
      lines.push(`| ${d.filename} | ${d.improvements.join("; ") || "—"} | ${d.regressions.join("; ") || "—"} |`);
    }
    lines.push("");
  }

  // 6. documentType별 변화
  lines.push("## 6. documentType별 변화");
  lines.push("| documentType | rowExact Δ | rowShort Δ | rowOver Δ | warn Δ | missing Δ합 | 판정 |");
  lines.push("|---|---:|---:|---:|---:|---:|---|");
  for (const d of documentTypeDiffs) {
    const mDelta = d.missingFieldDiffs.reduce((s, x) => s + x.delta, 0);
    const verdict = d.verdict === "improved" ? "✓ 개선" : d.verdict === "regressed" ? "✗ 회귀" : "— 변화없음";
    lines.push(`| ${d.documentType} | ${numDelta(0, d.deltas.rowExact)} | ${numDelta(0, d.deltas.rowShort)} | ${numDelta(0, d.deltas.rowOver)} | ${numDelta(0, d.deltas.warning)} | ${numDelta(0, mDelta)} | ${verdict} |`);
  }
  lines.push("");

  // 7. missing field 변화
  const mfdEntries = Object.entries(missingFieldDiffs);
  if (mfdEntries.length > 0) {
    lines.push("## 7. missing field 변화");
    for (const [dt, diffs] of mfdEntries) {
      lines.push(`**${dt}**`);
      lines.push("| field | before | after | delta |");
      lines.push("|---|---:|---:|---:|");
      for (const d of diffs) {
        const icon = d.delta < 0 ? " ✓" : " ✗";
        lines.push(`| ${d.key}${icon} | ${d.before} | ${d.after} | ${numDelta(d.before, d.after)} |`);
      }
      lines.push("");
    }
  }

  // 8. warning 변화
  const wdEntries = Object.entries(warningDiffs);
  if (wdEntries.length > 0) {
    lines.push("## 8. warning 변화");
    for (const [dt, diffs] of wdEntries) {
      lines.push(`**${dt}**`);
      lines.push("| warning | before | after | delta |");
      lines.push("|---|---:|---:|---:|");
      for (const d of diffs) {
        const icon = d.delta < 0 ? " ↓" : " ↑";
        lines.push(`| ${d.key}${icon} | ${d.before} | ${d.after} | ${numDelta(d.before, d.after)} |`);
      }
      lines.push("");
    }
  }

  // 9. sample별 상세 (변화 있는 것만)
  const changedSamples = sampleDiffs.filter((d) => d.verdict !== "unchanged");
  if (changedSamples.length > 0) {
    lines.push("## 9. sample별 상세 (변화 있는 샘플)");
    lines.push("| 파일 | 판정 | rowCountStatus | actualRow | expected | missing Δ | warn Δ |");
    lines.push("|---|---|---|---:|---:|---:|---:|");
    for (const d of changedSamples) {
      const b = d.before;
      const a = d.after;
      const rcStatus = b && a ? `${b.rowCountStatus} → ${a.rowCountStatus}` : (b ? `${b.rowCountStatus} (삭제)` : `(신규) ${a?.rowCountStatus}`);
      const actual = b && a ? `${b.actualRowCount ?? "—"} → ${a.actualRowCount ?? "—"}` : "—";
      const exp = (b ?? a)?.expectedRowCount ?? "—";
      const mDelta = d.deltas?.missing != null ? numDelta(0, d.deltas.missing) : "—";
      const wDelta = d.deltas?.warning != null ? numDelta(0, d.deltas.warning) : "—";
      const verdictIcon = { improved: "✓ 개선", regressed: "✗ 회귀", mixed: "△ 혼재", new: "★ 신규", removed: "× 삭제", unchanged: "— 변화없음" };
      lines.push(`| ${d.filename} | ${verdictIcon[d.verdict] ?? d.verdict} | ${rcStatus} | ${actual} | ${exp} | ${mDelta} | ${wDelta} |`);
    }
    lines.push("");
  } else {
    lines.push("## 9. sample별 상세");
    lines.push("변화 있는 샘플 없음 (모든 샘플 unchanged)");
    lines.push("");
  }

  return lines.join("\n");
}

// ── Main ──────────────────────────────────────────────────────────────────────

function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error([
      "Usage: node scripts/diff-runall-snapshots.mjs <before.json> <after.json> [output-dir]",
      "",
      "  before.json  — first RunAll snapshot (exported by T-12c)",
      "  after.json   — second RunAll snapshot (exported by T-12c)",
      "  output-dir   — directory for output files (default: same as before.json)",
      "",
      "Example:",
      "  node scripts/diff-runall-snapshots.mjs snapshots/before.json snapshots/after.json",
      "  npm run diff:runall -- before.json after.json",
    ].join("\n"));
    process.exit(1);
  }

  const beforePath = args[0];
  const afterPath = args[1];
  const outputDir = args[2] ? resolve(args[2]) : dirname(resolve(beforePath));

  console.log(`[diff-runall-snapshots]`);
  console.log(`  before : ${beforePath}`);
  console.log(`  after  : ${afterPath}`);
  console.log(`  output : ${outputDir}`);
  console.log("");

  const { data: beforeData, path: beforeAbs } = loadSnapshot(beforePath);
  const { data: afterData, path: afterAbs } = loadSnapshot(afterPath);

  // Validate basic structure
  for (const [label, snap] of [["before", beforeData], ["after", afterData]]) {
    if (!snap.samples || !Array.isArray(snap.samples)) {
      console.error(`[ERROR] ${label}.json is missing 'samples' array. Is this a T-12c snapshot?`);
      process.exit(1);
    }
  }

  // ── Run diffs ──
  const sampleDiffs = diffSamples(beforeData.samples, afterData.samples);
  const rowCountDelta = diffRowCountSummary(
    beforeData.summary?.rowCountSummary,
    afterData.summary?.rowCountSummary
  );
  const documentTypeDiffs = diffDocumentTypeSummary(
    beforeData.summary?.documentTypeSummary,
    afterData.summary?.documentTypeSummary
  );
  const missingFieldDiffs = diffMissingFields(
    beforeData.summary?.missingFieldSummary,
    afterData.summary?.missingFieldSummary
  );
  const warningDiffs = diffWarningSummary(
    beforeData.summary?.warningSummary,
    afterData.summary?.warningSummary
  );

  const improvedSamples = sampleDiffs.filter((d) => d.verdict === "improved").map((d) => d.filename);
  const regressedSamples = sampleDiffs.filter((d) => d.verdict === "regressed").map((d) => d.filename);
  const mixedSamples = sampleDiffs.filter((d) => d.verdict === "mixed").map((d) => d.filename);
  const unchangedSamples = sampleDiffs.filter((d) => d.verdict === "unchanged").map((d) => d.filename);

  const diff = {
    generatedAt: new Date().toISOString(),
    before: {
      file: basename(beforeAbs),
      path: beforeAbs,
      generatedAt: beforeData.generatedAt,
      testsetId: beforeData.testsetId,
      testsetLabel: beforeData.testsetLabel,
    },
    after: {
      file: basename(afterAbs),
      path: afterAbs,
      generatedAt: afterData.generatedAt,
      testsetId: afterData.testsetId,
      testsetLabel: afterData.testsetLabel,
    },
    summary: {
      totalSamplesBefore: beforeData.totalSamples,
      totalSamplesAfter: afterData.totalSamples,
      samplesRunBefore: beforeData.samplesRun,
      samplesRunAfter: afterData.samplesRun,
      improvedCount: improvedSamples.length,
      regressedCount: regressedSamples.length,
      mixedCount: mixedSamples.length,
      unchangedCount: unchangedSamples.length,
      improvedSamples,
      regressedSamples,
      mixedSamples,
      rowCountSummaryDelta: rowCountDelta,
    },
    documentTypeDiffs,
    sampleDiffs,
    missingFieldDiffs,
    warningDiffs,
    // raw data references for markdown renderer
    beforeData: { summary: beforeData.summary },
    afterData: { summary: afterData.summary },
  };

  // ── Console summary ──
  const rc = rowCountDelta;
  console.log("=== Diff Summary ===");
  console.log(`  Samples: ${beforeData.totalSamples} before / ${afterData.totalSamples} after`);
  console.log(`  Improved : ${improvedSamples.length} ${improvedSamples.length ? `(${improvedSamples.join(", ")})` : ""}`);
  console.log(`  Regressed: ${regressedSamples.length} ${regressedSamples.length ? `(${regressedSamples.join(", ")})` : ""}`);
  console.log(`  Mixed    : ${mixedSamples.length} ${mixedSamples.length ? `(${mixedSamples.join(", ")})` : ""}`);
  console.log(`  Unchanged: ${unchangedSamples.length}`);
  console.log(`  rowCount.exact  : ${numDelta(0, rc.exact ?? 0)}`);
  console.log(`  rowCount.short  : ${numDelta(0, rc.short ?? 0)}`);
  console.log(`  rowCount.over   : ${numDelta(0, rc.over ?? 0)}`);
  if (regressedSamples.length > 0) {
    console.warn(`\n⚠ REGRESSION detected in: ${regressedSamples.join(", ")}`);
  }

  // ── Output files ──
  mkdirSync(outputDir, { recursive: true });
  const ts = tsNow();
  const testsetId = beforeData.testsetId ?? "unknown";
  const jsonOutPath = join(outputDir, `runall_diff_${testsetId}_${ts}.json`);
  const mdOutPath   = join(outputDir, `runall_diff_${testsetId}_${ts}.md`);

  // Remove internal beforeData/afterData from JSON output (keep it clean)
  const { beforeData: _bd, afterData: _ad, ...jsonDiff } = diff;
  writeFileSync(jsonOutPath, JSON.stringify(jsonDiff, null, 2), "utf-8");

  const md = buildMarkdown(diff);
  writeFileSync(mdOutPath, md, "utf-8");

  console.log("");
  console.log(`✓ JSON : ${jsonOutPath}`);
  console.log(`✓ MD   : ${mdOutPath}`);

  process.exit(regressedSamples.length > 0 ? 1 : 0);
}

main();
