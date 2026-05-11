"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { extractBizNumber, normalizeBizNumber } from "@/lib/bizNumber";
import { useUi } from "../common/AppProviders";

import {
  Entry,
  EMPTY_ENTRY,
  EMPTY_GT,
  FIELDS,
  FieldKey,
  GtRecord,
  OcrCacheRecord,
  OcrResponse,
  OcrEntry,
  AutofillRecord,
  AutofillSuggestion,
  ValueSourceTag,
  BIZ_AUTO_APPLY_CONFIDENCE,
} from "./core/types";
import { matchField, MatchResult } from "./core/match";
import { extractFieldsFallback, normalizeEntry, parseAmounts } from "./core/extract";
import { buildAutofillSuggestions, canAutoApply } from "./core/autofill";
import {
  computeAllFieldViews,
  sourceLabel,
  sortSuggestions,
  scoreTriplet,
  computeMatchStatus,
  computeStatusPerField,
  MatchStatus,
} from "./core/finalize";
import type { DatasetManifest, ManifestItem, InvoiceProfile, AmountProfile, PartyProfile, TableProfile } from "@/lib/testsets";
import { resolveProfile, FINANCE_COLUMNS, FINANCE_TIER1_FIELDS, DOCUMENT_COLUMNS, DOCUMENT_PARTY_FIELDS, isNotApplicableField } from "@/lib/profiles";

type ViewMode = "compare" | "ocr_only" | "autofill" | "gt_edit";

type DocTypeSummaryRow = {
  documentType: string;
  total: number;
  selected: number;
  suppressed: number;
  unknown: number;   // receipt: unknown status / finance: review status (재활용)
  error: number;
  notRun: number;
  fieldFilled: Record<FieldKey, number>;
  documentFieldFilled: Record<string, number>;
  financeFieldFilled: Record<string, number>;  // finance 전용 필드 채움 수
};

type QualityTagSummaryRow = {
  tag: string;
  total: number;
  selected: number;
  suppressed: number;
  unknown: number;
  error: number;
  notRun: number;
  fieldFilled: Record<FieldKey, number>;
};

type TestsetMeta = {
  id: string;
  label: string;
  path: string;
  description?: string;
};

const DEFAULT_TESTSETS: TestsetMeta[] = [
  { id: "baseline", label: "기존 검증셋", path: "/data/testsets/baseline", description: "기존 10장 회귀 테스트용" },
  { id: "google", label: "Google 샘플셋", path: "/data/testsets/google", description: "사용자가 Google 폴더에 추가한 검증 이미지" },
];

DEFAULT_TESTSETS.splice(
  1,
  0,
  { id: "baseline_fast", label: "Baseline Fast", path: "/data/testsets/baseline_fast", description: "빠른 회귀 확인용 5장 미니셋" },
);
DEFAULT_TESTSETS.push({
  id: "google_fast",
  label: "Google Fast",
  path: "/data/testsets/google_fast",
  description: "실전형 상단 필드 확인용 5장 미니셋",
});

DEFAULT_TESTSETS.push({
  id: "invoice_statement",
  label: "거래명세서 1차 검증셋",
  path: "/data/testsets/invoice_statement",
  description: "거래명세서 계열 헤더/합계/표 구조 1차 검증용",
});

const datasetQuery = (datasetId: string) => `dataset=${encodeURIComponent(datasetId)}`;
const imageUrl = (baseUrl: string, filename: string) => `${baseUrl}/${encodeURIComponent(filename)}`;
const fileExt = (filename: string) => filename.split(".").pop()?.toLowerCase() ?? "";
const isPdfFile = (filename: string | null | undefined) => fileExt(filename ?? "") === "pdf";

function deriveUiStatus(data: OcrResponse): string {
  if (data.status) return data.status;
  if (data.doc_type === "bank_slip") return "suppressed_bank_slip";
  if (data.doc_type === "form_or_handwritten") return "suppressed_handwritten";
  if (data.doc_type === "unknown") return "unknown";
  return "selected";
}

function normalizeDocumentCompare(value: string): string {
  return value.replace(/\s+/g, "").replace(/[,\-\/().]/g, "").toLowerCase();
}

function documentFieldMatches(gtVal: string, ocrVal: string): boolean {
  const gtNorm = normalizeDocumentCompare(gtVal);
  const ocrNorm = normalizeDocumentCompare(ocrVal);
  if (!gtNorm || !ocrNorm) return false;
  return gtNorm === ocrNorm || gtNorm.includes(ocrNorm) || ocrNorm.includes(gtNorm);
}

function documentMatchStatus(gtVal: string, ocrVal: string): "O" | "△" | "X" | "—" {
  if (!gtVal) return "—";
  if (!ocrVal) return "X";
  if (gtVal === ocrVal || normalizeDocumentCompare(gtVal) === normalizeDocumentCompare(ocrVal)) return "O";
  return documentFieldMatches(gtVal, ocrVal) ? "△" : "X";
}

function documentMatchMeta(status: "O" | "△" | "X" | "—"): { symbol: string; color: string; title: string } {
  switch (status) {
    case "O": return { symbol: "O", color: "#22c55e", title: "GT exact/normalized match" };
    case "△": return { symbol: "△", color: "#f59e0b", title: "GT fuzzy/partial match" };
    case "X": return { symbol: "X", color: "#ef4444", title: "GT mismatch or missing OCR value" };
    default: return { symbol: "—", color: "rgba(255,255,255,0.35)", title: "No GT value" };
  }
}

type NormalizationRule = {
  rule?: string;
  before?: string;
  after?: string;
  confidence?: string;
  reason?: string;
};

type NormalizationFieldRecord = {
  field?: string;
  fieldType?: string;
  role?: string;
  rawValue?: string;
  normalizedValue?: string;
  valueChanged?: boolean;
  appliedRules?: NormalizationRule[];
  addressSimilarityAnalysis?: {
    addressSimilarityStatus?: string;
    matchedTokenTypes?: string[];
    appearsTruncated?: boolean;
    partialReason?: string;
  };
};

type InvoiceNormalization = {
  valueDirectChange?: boolean;
  normalizedFields?: Record<string, string>;
  fields?: NormalizationFieldRecord[];
};

type NormalizedAuxStatus = "O" | "△" | "X" | "—";

type SummaryTotalRisk = {
  value: string;
  source: string;
  score: string;
  reason: string;
  evidenceText: string;
  flags: string[];
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" ? value as Record<string, unknown> : null;
}

function getInvoiceNormalization(entry?: OcrEntry | null): InvoiceNormalization | null {
  const root = asRecord(entry?.extractDebug);
  const invoice = asRecord(root?.invoice_statement);
  const normalization = asRecord(invoice?.normalization);
  return normalization as InvoiceNormalization | null;
}

function getInvoiceDebug(entry?: OcrEntry | null): Record<string, unknown> | null {
  const root = asRecord(entry?.extractDebug);
  return asRecord(root?.invoice_statement);
}

function unknownToText(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function unknownToNumberText(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : unknownToText(value);
}

function normalizedMoneyText(value: string): string {
  return (value ?? "").replace(/[^\d]/g, "");
}

function getSelectedSummaryRisk(invoiceDebug: Record<string, unknown> | null, selectedValue: string): Record<string, unknown> | null {
  const blocks = Array.isArray(invoiceDebug?.amount_summary_blocks) ? invoiceDebug?.amount_summary_blocks : [];
  const selectedDigits = normalizedMoneyText(selectedValue);

  for (const item of blocks) {
    const block = asRecord(item);
    const selected = asRecord(block?.selected);
    const total = asRecord(selected?.totalAmount);
    if (!total) continue;

    const value = unknownToText(total.value);
    if (!selectedDigits || normalizedMoneyText(value) === selectedDigits) {
      return asRecord(total.risk);
    }
  }

  return null;
}

function getSummaryTotalRisk(invoiceDebug: Record<string, unknown> | null, fieldKey: string, value: string): SummaryTotalRisk | null {
  if (fieldKey !== "totalAmount") return null;

  const evidence = asRecord(invoiceDebug?.amount_total_evidence);
  if (!evidence) return null;

  const evidenceValue = unknownToText(evidence.value);
  if (value && evidenceValue && normalizedMoneyText(value) !== normalizedMoneyText(evidenceValue)) return null;

  const source = unknownToText(evidence.source);
  const score = unknownToNumberText(evidence.score);
  const reason = unknownToText(evidence.reason);
  const bestOccurrence = asRecord(evidence.bestOccurrence);
  const evidenceText = unknownToText(bestOccurrence?.text);
  const selectedRisk = getSelectedSummaryRisk(invoiceDebug, value || evidenceValue);
  const flags: string[] = [];

  if (/low_confidence/i.test(source) || /low_confidence|low confidence/i.test(reason) || (Number(score) > 0 && Number(score) < 50)) {
    flags.push("low confidence");
  }
  if (selectedRisk?.codeLotLike === true || /code|lot/i.test(reason + " " + evidenceText)) flags.push("code/lot risk");
  if (selectedRisk?.embeddedCode === true) flags.push("embedded code");
  if (selectedRisk?.dateLike === true) flags.push("date-like");
  if (selectedRisk?.tableBodyLike === true || /table_body_like/i.test(reason)) flags.push("table/body-like");
  if (reason && /party_or_noise/i.test(reason)) flags.push("party/noise context");

  if (flags.length === 0 && !source && !reason) return null;

  return {
    value: evidenceValue,
    source,
    score,
    reason,
    evidenceText,
    flags: Array.from(new Set(flags)),
  };
}

function getNormalizationRecord(normalization: InvoiceNormalization | null, fieldKey: string): NormalizationFieldRecord | null {
  const direct = normalization?.fields?.find((item) => item.field === fieldKey);
  if (direct) return direct;
  const alias = fieldKey.startsWith("buyer") ? fieldKey.replace(/^buyer/, "customer") : fieldKey.replace(/^customer/, "buyer");
  return normalization?.fields?.find((item) => item.field === alias) ?? null;
}

function getNormalizedFieldValue(normalization: InvoiceNormalization | null, fieldKey: string): string {
  const direct = normalization?.normalizedFields?.[fieldKey];
  if (typeof direct === "string") return direct;
  const alias = fieldKey.startsWith("buyer") ? fieldKey.replace(/^buyer/, "customer") : fieldKey.replace(/^customer/, "buyer");
  return normalization?.normalizedFields?.[alias] ?? "";
}

function compactForNormalizedCompare(fieldType: string, value: string): string {
  const raw = (value ?? "").trim();
  if (!raw) return "";
  if (fieldType === "business_number") return raw.replace(/\D/g, "");
  if (fieldType === "representative") return raw.replace(/\s*[,/]\s*/g, ",").replace(/\s+/g, "").toLowerCase();
  if (fieldType === "company") return raw.replace(/[\s().,\-_/]/g, "").toLowerCase();
  if (fieldType === "address") return raw.replace(/\s+/g, "").replace(/[(),.\-_/]/g, "").toLowerCase();
  return normalizeDocumentCompare(raw);
}

function digitSignature(value: string): string {
  return (value ?? "").match(/\d+/g)?.join("|") ?? "";
}

function computeNormalizedAuxStatus(args: {
  normalizedValue: string;
  gtValue: string;
  fieldType: string;
  rules: NormalizationRule[];
}): NormalizedAuxStatus {
  const { normalizedValue, gtValue, fieldType, rules } = args;
  if (!normalizedValue || !gtValue) return "—";
  const hasDebugOnly = rules.some((rule) => /debug_only|low/i.test(rule.confidence ?? ""));
  const gtNorm = compactForNormalizedCompare(fieldType, gtValue);
  const normalizedNorm = compactForNormalizedCompare(fieldType, normalizedValue);
  if (!gtNorm || !normalizedNorm) return "—";
  if (gtNorm === normalizedNorm) return hasDebugOnly ? "△" : "O";
  if (fieldType === "address" && digitSignature(gtValue) && digitSignature(normalizedValue) && digitSignature(gtValue) !== digitSignature(normalizedValue)) {
    // Allow △ only when normalized digits are a proper subset of GT digits AND
    // normalized text is a substring of GT (prefix/tail truncation, not a different address)
    const gtDigitParts = new Set(digitSignature(gtValue).split("|").filter(Boolean));
    const normDigitParts = digitSignature(normalizedValue).split("|").filter(Boolean);
    const normIsDigitSubset = normDigitParts.length > 0 && normDigitParts.every(d => gtDigitParts.has(d));
    if (!normIsDigitSubset || !gtNorm.includes(normalizedNorm)) return "X";
    // Fall through: normalized is both a digit-subset and text-substring of GT → △
  }
  if (!hasDebugOnly && (gtNorm.includes(normalizedNorm) || normalizedNorm.includes(gtNorm))) return "△";
  return hasDebugOnly ? "△" : "X";
}

function normalizedStatusLabel(status: NormalizedAuxStatus): string {
  if (status === "O") return "정규화 기준 일치 가능";
  if (status === "△") return "normalized △";
  if (status === "X") return "normalized X";
  return "정규화 후보";
}

function normalizedStatusColor(status: NormalizedAuxStatus): string {
  if (status === "O") return "#22c55e";
  if (status === "△") return "#f59e0b";
  if (status === "X") return "#64748b";
  return "#0ea5e9";
}

type EntryNormalizationFieldSummary = {
  fieldKey: string;
  rawValue: string;
  normalizedValue: string;
  gtValue: string;
  exactStatus: ReturnType<typeof documentMatchStatus>;
  normalizedStatus: NormalizedAuxStatus;
  rules: NormalizationRule[];
  hasRiskRule: boolean;
};

type EntryNormalizationSummary = {
  candidateCount: number;
  normPassCandidateCount: number;
  normPartialCount: number;
  normFailCount: number;
  debugOnlyCount: number;
  overcorrectionRiskCount: number;
  unknownCount: number;
  fields: EntryNormalizationFieldSummary[];
};

type DatasetNormalizationSummary = EntryNormalizationSummary & {
  entryCountWithCandidates: number;
};

const EMPTY_ENTRY_NORMALIZATION_SUMMARY: EntryNormalizationSummary = {
  candidateCount: 0,
  normPassCandidateCount: 0,
  normPartialCount: 0,
  normFailCount: 0,
  debugOnlyCount: 0,
  overcorrectionRiskCount: 0,
  unknownCount: 0,
  fields: [],
};

function hasNormalizationRiskRule(rules: NormalizationRule[]): boolean {
  return rules.some((rule) => {
    const haystack = `${rule.rule ?? ""} ${rule.confidence ?? ""} ${rule.reason ?? ""}`.toLowerCase();
    return /debug_only|low_confidence|\blow\b|possible_overcorrection|overcorrection|company_ocr_confusion|representative_spelling|skipped_low_confidence|skipped_possible/.test(haystack);
  });
}

function collectEntryNormalizationSummary(
  entry: OcrEntry | undefined,
  docGt: Record<string, string>,
): EntryNormalizationSummary {
  const normalization = getInvoiceNormalization(entry);
  if (!normalization) return EMPTY_ENTRY_NORMALIZATION_SUMMARY;

  const docFields = entry?.documentFields ?? {};
  const summary: EntryNormalizationSummary = {
    candidateCount: 0,
    normPassCandidateCount: 0,
    normPartialCount: 0,
    normFailCount: 0,
    debugOnlyCount: 0,
    overcorrectionRiskCount: 0,
    unknownCount: 0,
    fields: [],
  };

  for (const col of DOCUMENT_FIELD_META) {
    const record = getNormalizationRecord(normalization, col.key);
    const normalizedValue = getNormalizedFieldValue(normalization, col.key);
    const rawValue = docFields[col.key] ?? "";
    const gtValue = docGt[col.key] ?? "";
    const rules = record?.appliedRules ?? [];
    const hasCandidate = Boolean(rules.length > 0 || (normalizedValue && normalizedValue !== rawValue));
    if (!hasCandidate) continue;

    const exactStatus = documentMatchStatus(gtValue, rawValue);
    const normalizedStatus = computeNormalizedAuxStatus({
      normalizedValue,
      gtValue,
      fieldType: record?.fieldType ?? "",
      rules,
    });
    const hasRiskRule = hasNormalizationRiskRule(rules);

    summary.candidateCount += 1;
    if (rules.some((rule) => /debug_only/i.test(`${rule.rule ?? ""} ${rule.confidence ?? ""} ${rule.reason ?? ""}`))) {
      summary.debugOnlyCount += 1;
    }
    if (hasRiskRule) summary.overcorrectionRiskCount += 1;

    if (!gtValue || !normalizedValue) {
      summary.unknownCount += 1;
    } else if (exactStatus !== "O" && normalizedStatus === "O" && !hasRiskRule) {
      summary.normPassCandidateCount += 1;
    } else if (normalizedStatus === "△" || hasRiskRule) {
      summary.normPartialCount += 1;
    } else if (normalizedStatus === "X") {
      summary.normFailCount += 1;
    }

    summary.fields.push({
      fieldKey: col.key,
      rawValue,
      normalizedValue,
      gtValue,
      exactStatus,
      normalizedStatus,
      rules,
      hasRiskRule,
    });
  }

  return summary;
}

function mergeNormalizationSummary(target: DatasetNormalizationSummary, item: EntryNormalizationSummary): void {
  if (item.candidateCount > 0) target.entryCountWithCandidates += 1;
  target.candidateCount += item.candidateCount;
  target.normPassCandidateCount += item.normPassCandidateCount;
  target.normPartialCount += item.normPartialCount;
  target.normFailCount += item.normFailCount;
  target.debugOnlyCount += item.debugOnlyCount;
  target.overcorrectionRiskCount += item.overcorrectionRiskCount;
  target.unknownCount += item.unknownCount;
  target.fields.push(...item.fields);
}

function normalizationSummaryTitle(summary: EntryNormalizationSummary): string {
  if (summary.candidateCount <= 0) return "No normalization candidates";
  return [
    `candidate ${summary.candidateCount}`,
    `Norm O ${summary.normPassCandidateCount}`,
    `Norm partial ${summary.normPartialCount}`,
    `risk ${summary.overcorrectionRiskCount}`,
    `unknown ${summary.unknownCount}`,
  ].join(" · ");
}

function inferInvoiceDocumentFields(data: OcrResponse): Record<string, string> {
  const explicit = data.document_fields ?? data.invoice_fields;
  if (explicit && Object.keys(explicit).length > 0) return explicit;

  const text = data.full_text ?? "";
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const joined = lines.join(" ");
  const fields: Record<string, string> = {};
  const dateMatch = joined.match(/(\d{4}[.\-\/]\d{1,2}[.\-\/]\d{1,2}|\d{2}[.\-\/]\d{1,2}[.\-\/]\d{1,2})/);
  if (dateMatch) fields.issueDate = dateMatch[1];

  const amountMatches = [...joined.matchAll(/\d{1,3}(?:,\d{3})+(?:원)?|\d{5,}(?:원)?/g)].map((m) => m[0]);
  if (amountMatches.length > 0) fields.totalAmount = amountMatches[amountMatches.length - 1].replace(/원$/, "");
  if (amountMatches.length > 1) fields.supplyAmount = amountMatches[Math.max(0, amountMatches.length - 3)].replace(/원$/, "");
  if (amountMatches.length > 2) fields.taxAmount = amountMatches[Math.max(0, amountMatches.length - 2)].replace(/원$/, "");

  const tableHeaderIndex = lines.findIndex((line) => /품명|규격|수량|단가|공급가액|세액|합계|금액/.test(line));
  const tableDetected = tableHeaderIndex >= 0 || /품명|규격|수량|단가|공급가액|세액|합계|금액/.test(joined);
  fields.tableDetected = tableDetected ? "Y" : "N";
  if (tableDetected) {
    const candidateRows = lines.filter((line) =>
      /\d/.test(line) && /[,0-9]/.test(line) && !/사업자|등록|전화|주소/.test(line),
    );
    fields.rowCount = String(candidateRows.length);
    const firstRow = tableHeaderIndex >= 0 ? lines.slice(tableHeaderIndex + 1).find((line) => line.length > 0) : candidateRows[0];
    if (firstRow) fields.firstRowPreview = firstRow.slice(0, 120);
  }
  return fields;
}

async function readJsonResponse<T>(res: Response, label: string): Promise<T> {
  const text = await res.text();
  if (!res.ok) {
    let detail = text;
    try {
      const payload = JSON.parse(text) as { detail?: unknown; message?: unknown; error?: unknown };
      const picked = payload.detail ?? payload.message ?? payload.error;
      detail = typeof picked === "string" ? picked : JSON.stringify(picked ?? payload);
    } catch {
      detail = text;
    }
    throw new Error(`${label} 실패 (${res.status}): ${detail.slice(0, 260) || res.statusText}`);
  }
  try {
    return (text ? JSON.parse(text) : {}) as T;
  } catch {
    throw new Error(`${label} 응답이 JSON이 아닙니다: ${text.slice(0, 180)}`);
  }
}

async function fetchOcr(filename: string, imageBaseUrl: string): Promise<OcrEntry> {
  const originalUrl = imageUrl(imageBaseUrl, filename);
  const imageRes = await fetch(originalUrl);
  if (!imageRes.ok) {
    throw new Error(`${filename} 이미지 로드 실패 (${imageRes.status})`);
  }
  const blob = await imageRes.blob();
  const form = new FormData();
  form.append("file", new File([blob], filename, { type: blob.type || "image/jpeg" }));
  const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL;
  const ocrEndpoint = backendBase ? `${backendBase}/ocr/extract` : "/api/ocr-extract";
  const ocrRes = await fetch(ocrEndpoint, { method: "POST", body: form });
  const data = await readJsonResponse<OcrResponse>(ocrRes, `${filename} OCR`);

  const raw: Entry = data.receipt_fields
    ? { ...EMPTY_ENTRY(), ...data.receipt_fields }
    : extractFieldsFallback(data.full_text);

  return {
    raw,
    normalized: normalizeEntry(raw),
    fullText: data.full_text,
    displayUrl: data.processed_image ?? originalUrl,
    processingTime: data.processing_time,
    scannedAt: new Date().toISOString(),
    status: deriveUiStatus(data),
    docType: data.doc_type,
    financeFields: data.finance_fields,
    documentFields: inferInvoiceDocumentFields(data),
    extractDebug: data.extract_debug,
    financeReviewReasons: data.finance_review_reasons,
  };
}

type PdfPagePreviewProps = {
  url: string;
  filename: string;
  variant: "thumb" | "preview";
};

function PdfPagePreview({ url, filename, variant }: PdfPagePreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    let renderTask: { cancel: () => void; promise: Promise<unknown> } | null = null;

    async function renderPdf() {
      setStatus("loading");
      try {
        const pdfjs = await import("pdfjs-dist/legacy/build/pdf");
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.js";
        const loadingTask = pdfjs.getDocument({ url });
        const pdf = await loadingTask.promise;
        if (cancelled) {
          await pdf.destroy();
          return;
        }

        const page = await pdf.getPage(1);
        if (cancelled) {
          await pdf.destroy();
          return;
        }

        const pageRotation = typeof page.rotate === "number" ? page.rotate : 0;
        const baseViewport = page.getViewport({ scale: 1, rotation: pageRotation });
        const targetWidth = variant === "thumb" ? 128 : 980;
        const scale = targetWidth / baseViewport.width;
        const viewport = page.getViewport({ scale, rotation: pageRotation });
        const canvas = canvasRef.current;
        if (!canvas) {
          await pdf.destroy();
          return;
        }

        const context = canvas.getContext("2d");
        if (!context) {
          await pdf.destroy();
          return;
        }

        canvas.width = Math.ceil(viewport.width);
        canvas.height = Math.ceil(viewport.height);
        renderTask = page.render({ canvasContext: context, viewport }) as { cancel: () => void; promise: Promise<unknown> };
        await renderTask.promise;
        await pdf.destroy();
        if (!cancelled) setStatus("ready");
      } catch (error) {
        // StrictMode 재마운트로 인한 의도적 cancel은 PDF.js가 RenderingCancelledException으로 reject함
        // 이 경우 console.error 노이즈 방지 + setStatus 스킵
        if (cancelled) return;
        console.error("[TestWorkspace] PDF preview failed", { filename, url, variant, error });
        setStatus("error");
      }
    }

    renderPdf();
    return () => {
      cancelled = true;
      renderTask?.cancel();
    };
  }, [url, variant]);

  const fallback = variant === "thumb" ? (
    <div style={styles.pdfThumb}>
      <span style={styles.pdfBadge}>PDF</span>
    </div>
  ) : (
    <div style={styles.pdfPreview}>
      <span style={styles.pdfPreviewBadge}>PDF</span>
      <strong style={{ fontSize: 14, color: "var(--text)", textAlign: "center", wordBreak: "break-all" }}>{filename}</strong>
      {status === "loading" && <span style={{ fontSize: 11, color: "var(--muted)" }}>preview loading...</span>}
      {status === "error" && <span style={{ fontSize: 11, color: "#fca5a5" }}>preview failed</span>}
    </div>
  );

  return (
    <div style={variant === "thumb" ? styles.pdfCanvasWrapThumb : styles.pdfCanvasWrapPreview}>
      <canvas
        ref={canvasRef}
        aria-label={`${filename} PDF preview`}
        style={{
          ...(variant === "thumb" ? styles.pdfCanvasThumb : styles.pdfCanvasPreview),
          opacity: status === "ready" ? 1 : 0,
        }}
      />
      {status !== "ready" && fallback}
    </div>
  );
}

export default function TestWorkspace() {
  const ui = useUi();
  const [testsets, setTestsets] = useState<TestsetMeta[]>(DEFAULT_TESTSETS);
  const [activeDataset, setActiveDataset] = useState("baseline");
  // ── 상태 분리: gt / ocrCache / ocr(세션) / autofill(세션+파일) ──
  const [images, setImages]     = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  const [gt, setGt]             = useState<Record<string, GtRecord>>({});
  const [ocrCache, setOcrCache] = useState<Record<string, OcrCacheRecord>>({});
  const [ocr, setOcr]           = useState<Record<string, OcrEntry>>({});
  const [autofill, setAutofill] = useState<Record<string, AutofillRecord>>({});

  const [bizStatus, setBizStatus] = useState<Record<string, "active" | "closed" | "unknown">>({});
  const [saveState, setSaveState] = useState<"idle" | "pending" | "saved">("idle");

  const [running, setRunning]       = useState(false);
  const [runningAll, setRunningAll] = useState(false);
  const [progress, setProgress]     = useState<{ done: number; total: number } | null>(null);
  const [currentRunningFile, setCurrentRunningFile] = useState<string | null>(null);
  const [uiError, setUiError] = useState<string | null>(null);

  const [viewMode, setViewMode]   = useState<ViewMode>("compare");
  const [showDebug, setShowDebug] = useState(false);
  const [showReasons, setShowReasons] = useState(false);
  const [manifest, setManifest] = useState<DatasetManifest | null>(null);
  const [selectedQualityTags, setSelectedQualityTags] = useState<string[]>([]);
  const [showBatchSummary, setShowBatchSummary] = useState(true);
  const activeTestset = useMemo(
    () => testsets.find((t) => t.id === activeDataset) ?? DEFAULT_TESTSETS[0],
    [testsets, activeDataset],
  );

  const gtRef       = useRef(gt);
  const ocrCacheRef = useRef(ocrCache);
  const autofillRef = useRef(autofill);
  useEffect(() => { gtRef.current = gt; }, [gt]);
  useEffect(() => { ocrCacheRef.current = ocrCache; }, [ocrCache]);
  useEffect(() => { autofillRef.current = autofill; }, [autofill]);

  const saveTimer  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── initial load ──
  useEffect(() => {
    let cancelled = false;
    const query = datasetQuery(activeDataset);

    setSelected(null);
    setImages([]);
    setOcr({});
    setBizStatus({});
    setProgress(null);
    setCurrentRunningFile(null);
    setUiError(null);
    setManifest(null);
    setSelectedQualityTags([]);

    // manifest.json fetch (non-blocking, silent fallback if not present)
    fetch(`/data/testsets/${activeDataset}/manifest.json`)
      .then((r) => (r.ok ? (r.json() as Promise<DatasetManifest>) : Promise.resolve(null)))
      .then((data) => { if (!cancelled) setManifest(data); })
      .catch(() => { if (!cancelled) setManifest(null); });

    Promise.all([
      fetch(`/api/test-images?${query}`).then((r) => readJsonResponse<any>(r, "테스트 이미지 목록")),
      fetch(`/api/ground-truth?${query}`).then((r) => readJsonResponse<any>(r, "기준값")),
      fetch(`/api/ocr-cache?${query}`).then((r) => readJsonResponse<any>(r, "OCR 캐시")),
      fetch(`/api/autofill-cache?${query}`).then((r) => readJsonResponse<any>(r, "자동복원 캐시")).catch(() => ({})),
    ]).then(([imageData, gtData, cacheData, autofillData]) => {
      if (cancelled) return;
      if (imageData.testsets?.length) setTestsets(imageData.testsets);
      const nextImages = imageData.images ?? [];
      setImages(nextImages);
      setSelected(nextImages[0] ?? null);
      setGt(gtData ?? {});
      setOcrCache(cacheData ?? {});
      setAutofill(autofillData ?? {});
      setSaveState("idle");
    }).catch((e) => {
      if (cancelled) return;
      setUiError(e instanceof Error ? e.message : "테스트 데이터 로드 중 오류가 발생했습니다.");
    });

    return () => { cancelled = true; };
  }, [activeDataset]);

  // ── persist 헬퍼 ──
  const persistGt = useCallback((updated: Record<string, GtRecord>) => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
    if (savedTimer.current) clearTimeout(savedTimer.current);
    setSaveState("pending");
    saveTimer.current = setTimeout(async () => {
      try {
        await fetch(`/api/ground-truth?${datasetQuery(activeDataset)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updated),
        });
        setSaveState("saved");
        savedTimer.current = setTimeout(() => setSaveState("idle"), 1500);
      } catch (e) {
        console.error("gt save failed", e);
        setSaveState("idle");
      }
    }, 600);
  }, [activeDataset]);

  const persistOcrCache = useCallback((updated: Record<string, OcrCacheRecord>) => {
    fetch(`/api/ocr-cache?${datasetQuery(activeDataset)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updated),
    }).catch((e) => console.error("ocr-cache save failed", e));
  }, [activeDataset]);

  const persistAutofill = useCallback((updated: Record<string, AutofillRecord>) => {
    fetch(`/api/autofill-cache?${datasetQuery(activeDataset)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updated),
    }).catch((e) => console.error("autofill-cache save failed", e));
  }, [activeDataset]);

  // ── GT 업데이트 (사람 확정만) ──
  const updateGtField = (img: string, field: FieldKey, value: string) => {
    const existing = gt[img] ?? EMPTY_GT();
    const updated = {
      ...gt,
      [img]: { ...existing, fields: { ...existing.fields, [field]: value }, updated_at: new Date().toISOString() },
    };
    setGt(updated);
    persistGt(updated);
  };

  // finance 전용 기준값 편집 — GtRecord.financeFields에 저장. persistGt 재사용.
  const updateFinanceGtField = (img: string, field: string, value: string) => {
    const existing = gt[img] ?? EMPTY_GT();
    const updated: Record<string, GtRecord> = {
      ...gt,
      [img]: {
        ...existing,
        financeFields: { ...(existing.financeFields ?? {}), [field]: value },
        updated_at: new Date().toISOString(),
      },
    };
    setGt(updated);
    persistGt(updated);
  };

  const updateDocumentGtField = (img: string, field: string, value: string) => {
    const existing = gt[img] ?? EMPTY_GT();
    const updated: Record<string, GtRecord> = {
      ...gt,
      [img]: {
        ...existing,
        documentFields: { ...(existing.documentFields ?? {}), [field]: value },
        updated_at: new Date().toISOString(),
      },
    };
    setGt(updated);
    persistGt(updated);
  };

  // 필드별 확정: 단일 필드의 채택값을 GT 로 승격
  const commitFieldToGt = (img: string, field: FieldKey, value: string) => {
    const existing = gt[img] ?? EMPTY_GT();
    const updated: Record<string, GtRecord> = {
      ...gt,
      [img]: {
        ...existing,
        fields: { ...existing.fields, [field]: value },
        updated_at: new Date().toISOString(),
      },
    };
    setGt(updated);
    persistGt(updated);
  };

  // 전체 확정: 미확정(ocr/ocr_normalized/autofill_*) source 가 섞여 있으면 confirm 모달로 이중 확인
  //
  // ⚠️ ground_truth 오염을 막기 위한 관문:
  //   - 사용자 명시 액션(버튼 클릭) 필수
  //   - autofill/ocr source 가 있으면 "어떤 값이 어느 source 인지" 요약을 보여주고 한 번 더 확인
  //   - 취소하면 아무 변경 없음
  const commitFinalsToGt = async (img: string) => {
    if (!ocr[img]) return;
    const views = computeAllFieldViews(gt[img]?.fields ?? EMPTY_ENTRY(), ocr[img], autofill[img] ?? null);

    // 위험 필드 분류 (user_confirmed 가 아닌 것)
    const riskyLines: string[] = [];
    for (const f of FIELDS) {
      const v = views[f.key];
      if (!v.finalValue) continue;
      if (v.finalSource === "user_confirmed") continue;
      const srcDesc =
        v.finalSource === "autofill_biz"              ? "자동복원(사업자번호 매칭)" :
        v.finalSource === "autofill_text_suggestion"  ? "자동복원(텍스트 유사도)" :
        v.finalSource === "ocr_normalized"            ? "OCR 정규화" :
        v.finalSource === "ocr"                       ? "OCR 원본" : "기타";
      riskyLines.push(`• ${f.label}: "${v.finalValue}"  ← ${srcDesc}`);
    }

    if (riskyLines.length > 0) {
      const ok = await ui.confirm({
        title: "전체 확정 전 확인",
        message:
          `아래 ${riskyLines.length}개 필드는 사람이 확정한 값이 아닙니다.\n` +
          `정말로 ground_truth 에 저장할까요?\n\n` +
          riskyLines.join("\n") +
          `\n\n(필드별 확정 버튼을 사용하면 원하는 필드만 선택적으로 저장할 수 있습니다)`,
        okText: "전체 저장",
        cancelText: "취소",
      });
      if (!ok) return;
    }

    const newFields = EMPTY_ENTRY();
    for (const f of FIELDS) newFields[f.key] = views[f.key].finalValue;

    const updated: Record<string, GtRecord> = {
      ...gt,
      [img]: {
        fields: newFields,
        type: gt[img]?.type || "영수증",
        updated_at: new Date().toISOString(),
      },
    };
    setGt(updated);
    persistGt(updated);
  };

  // ── 사업자번호 검증 (NTS) ──
  const validateBizNo = useCallback(async (filename: string, bizNo: string) => {
    try {
      const res = await fetch("/api/biz-validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bizNumbers: [bizNo] }),
      });
      const data = await res.json();
      const item = data?.data?.[0];
      const status = item?.b_stt_cd === "01" ? "active" : item?.b_stt_cd ? "closed" : "unknown";
      setBizStatus((prev) => ({ ...prev, [filename]: status }));
    } catch {
      setBizStatus((prev) => ({ ...prev, [filename]: "unknown" }));
    }
  }, []);

  // ── autofill 제안 적용/해제 (세션 + autofill_cache 저장, GT는 건드리지 않음) ──
  const toggleAutofillApply = (img: string, source: "biz" | "text" | null) => {
    const rec = autofill[img];
    if (!rec) return;
    const nextAppliedSource = rec.appliedSource === source ? null : source;
    const updated: Record<string, AutofillRecord> = {
      ...autofill,
      [img]: {
        ...rec,
        appliedSource: nextAppliedSource,
        appliedAt: nextAppliedSource ? new Date().toISOString() : undefined,
      },
    };
    setAutofill(updated);
    persistAutofill(updated);
  };

  // ── OCR 실행 ──
  //
  // 정책:
  //  - GT 파일은 절대 건드리지 않는다
  //  - autofill 제안을 생성하고 biz+high confidence 조건 충족 시 세션 상태로만 auto apply
  //  - ocrCache만 파일로 저장
  const runOne = async (filename: string) => {
    setRunning(true);
    setCurrentRunningFile(filename);
    setUiError(null);
    try {
      const entry = await fetchOcr(filename, activeTestset.path);
      setOcr((prev) => ({ ...prev, [filename]: entry }));

      const currentGt    = gtRef.current;
      const currentCache = ocrCacheRef.current;
      const currentAuto  = autofillRef.current;

      const suggestions = sortSuggestions(
        buildAutofillSuggestions(filename, entry.fullText, entry, currentGt, currentCache, activeTestset.id)
      );

      // 1) ocr_cache 저장
      const updatedCache: Record<string, OcrCacheRecord> = {
        ...currentCache,
        [filename]: { ocr_text: entry.fullText, scanned_at: entry.scannedAt },
      };
      setOcrCache(updatedCache);
      persistOcrCache(updatedCache);

      // 2) autofill 기록 저장 + 조건부 auto apply
      const autoBiz = suggestions.find((s) => s.source === "biz" && canAutoApply(s));
      const prevApplied = currentAuto[filename]?.appliedSource ?? null;
      const nextApplied: "biz" | "text" | null =
        prevApplied ?? (autoBiz ? "biz" : null); // 기존 사용자 선택 유지, 없으면 조건부 자동
      const updatedAuto: Record<string, AutofillRecord> = {
        ...currentAuto,
        [filename]: {
          suggestions,
          appliedSource: nextApplied,
          appliedAt: nextApplied ? new Date().toISOString() : undefined,
        },
      };
      setAutofill(updatedAuto);
      persistAutofill(updatedAuto);

      // 3) biz 검증
      const bizNo = extractBizNumber(entry.fullText);
      if (bizNo) validateBizNo(filename, bizNo);
    } catch (e) {
      const message = e instanceof Error ? e.message : "OCR 처리 중 오류가 발생했습니다.";
      setUiError(message);
      alert(message);
    } finally {
      setRunning(false);
      setCurrentRunningFile(null);
    }
  };

  const runAll = async () => {
    if (images.length === 0) return;
    setRunningAll(true);
    setProgress({ done: 0, total: images.length });
    setCurrentRunningFile(null);
    setUiError(null);
    let latestCache = ocrCacheRef.current;
    let latestAuto  = autofillRef.current;

    for (let i = 0; i < images.length; i++) {
      const name = images[i];
      setCurrentRunningFile(name);
      setSelected(name);
      try {
        const entry = await fetchOcr(name, activeTestset.path);
        setOcr((prev) => ({ ...prev, [name]: entry }));

        const suggestions = sortSuggestions(
          buildAutofillSuggestions(name, entry.fullText, entry, gtRef.current, latestCache, activeTestset.id)
        );

        latestCache = { ...latestCache, [name]: { ocr_text: entry.fullText, scanned_at: entry.scannedAt } };

        const autoBiz = suggestions.find((s) => s.source === "biz" && canAutoApply(s));
        const prevApplied = latestAuto[name]?.appliedSource ?? null;
        const nextApplied = prevApplied ?? (autoBiz ? "biz" : null);
        latestAuto = {
          ...latestAuto,
          [name]: {
            suggestions,
            appliedSource: nextApplied,
            appliedAt: nextApplied ? new Date().toISOString() : undefined,
          },
        };
      } catch (e) {
        const message = e instanceof Error ? e.message : "OCR 처리 중 오류가 발생했습니다.";
        setUiError(`${name}: ${message}`);
      }
      setProgress({ done: i + 1, total: images.length });
    }

    setOcrCache(latestCache);
    setAutofill(latestAuto);
    persistOcrCache(latestCache);
    persistAutofill(latestAuto);
    setRunningAll(false);
    setProgress(null);
    setCurrentRunningFile(null);
  };

  // ── 현재 선택 파일 기준 계산 ──
  const selGt       = selected ? (gt[selected]?.fields         ?? EMPTY_ENTRY()) : EMPTY_ENTRY();
  const selFinanceGt = selected ? (gt[selected]?.financeFields ?? {})            : {};
  const selDocumentGt = selected ? (gt[selected]?.documentFields ?? {})          : {};
  const selOcr = selected ? (ocr[selected] ?? null)                : null;
  const selAuto = selected && selOcr ? (autofill[selected] ?? null) : null;
  const selMeta = useMemo(
    () => (selected ? (manifest?.items.find((item) => item.filename === selected) ?? null) : null),
    [selected, manifest],
  );
  // 선택된 이미지의 profile — profile resolver 단일 진입점 (docs/TEST_PROFILE_SCHEMA §3)
  const selProfile = useMemo(
    () => resolveProfile(selMeta?.documentType),
    [selMeta],
  );

  // ── documentType별 집계 ──
  const docTypeSummary = useMemo((): DocTypeSummaryRow[] | null => {
    if (!manifest || images.length === 0) return null;
    const map = new Map<string, DocTypeSummaryRow>();
    const ensure = (dt: string): DocTypeSummaryRow => {
      if (!map.has(dt)) {
        const fieldFilled = {} as Record<FieldKey, number>;
        for (const f of FIELDS) fieldFilled[f.key] = 0;
        const financeFieldFilled: Record<string, number> = {};
        for (const col of FINANCE_DISPLAY_COLS) financeFieldFilled[col.key] = 0;
        const documentFieldFilled: Record<string, number> = {};
        for (const col of DOCUMENT_FIELD_META) documentFieldFilled[col.key] = 0;
        map.set(dt, { documentType: dt, total: 0, selected: 0, suppressed: 0, unknown: 0, error: 0, notRun: 0, fieldFilled, financeFieldFilled, documentFieldFilled });
      }
      return map.get(dt)!;
    };
    for (const img of images) {
      const manifestItem = manifest.items.find((i) => i.filename === img);
      const dt = manifestItem?.documentType ?? "unknown";
      const row = ensure(dt);
      row.total++;
      const ocrEntry = ocr[img];
      if (!ocrEntry) {
        row.notRun++;
      } else {
        const baseProfile = resolveProfile(dt).base;
        if (baseProfile === "finance") {
          // finance: derived status 기반 집계 (raw suppressed_bank_slip 보정)
          const fStatus = deriveFinanceStatus(ocrEntry, gt[img]?.financeFields);
          if (fStatus === "selected")        row.selected++;
          else if (fStatus === "review")     row.unknown++;   // unknown 슬롯을 review로 재활용
          else                               row.suppressed++;
          // finance 필드 채움 수
          const finFields = ocrEntry.financeFields ?? {};
          for (const col of FINANCE_DISPLAY_COLS) {
            if (finFields[col.key]) row.financeFieldFilled[col.key]++;
          }
        } else if (baseProfile === "document") {
          const status = ocrEntry.status ?? "selected";
          if (status === "selected") row.selected++;
          else if (status.startsWith("suppressed_")) row.suppressed++;
          else if (status === "unknown") row.unknown++;
          else row.error++;
          const docFields = ocrEntry.documentFields ?? {};
          for (const col of DOCUMENT_FIELD_META) {
            if (docFields[col.key]) row.documentFieldFilled[col.key]++;
          }
        } else {
          // receipt 기존 로직
          const status = ocrEntry.status ?? "selected";
          if (status === "selected") row.selected++;
          else if (status.startsWith("suppressed_")) row.suppressed++;
          else if (status === "unknown") row.unknown++;
          else row.error++;
          const g = gt[img]?.fields ?? EMPTY_ENTRY();
          const v = computeAllFieldViews(g, ocrEntry, autofill[img] ?? null, activeDataset);
          for (const f of FIELDS) { if (v[f.key].finalValue) row.fieldFilled[f.key]++; }
        }
      }
    }
    return Array.from(map.values()).sort((a, b) => b.total - a.total);
  }, [manifest, images, ocr, gt, autofill, activeDataset]);

  // ── qualityTags별 집계 ──
  const qualityTagSummary = useMemo((): QualityTagSummaryRow[] | null => {
    if (!manifest || images.length === 0) return null;
    const map = new Map<string, QualityTagSummaryRow>();
    const ensure = (tag: string): QualityTagSummaryRow => {
      if (!map.has(tag)) {
        const fieldFilled = {} as Record<FieldKey, number>;
        for (const f of FIELDS) fieldFilled[f.key] = 0;
        map.set(tag, { tag, total: 0, selected: 0, suppressed: 0, unknown: 0, error: 0, notRun: 0, fieldFilled });
      }
      return map.get(tag)!;
    };
    for (const img of images) {
      const manifestItem = manifest.items.find((i) => i.filename === img);
      if (!manifestItem || manifestItem.qualityTags.length === 0) continue;
      const ocrEntry = ocr[img];
      let imgStatus = "";
      let imgFieldFilled: Record<FieldKey, boolean> | null = null;
      if (ocrEntry) {
        imgStatus = ocrEntry.status ?? "selected";
        const g = gt[img]?.fields ?? EMPTY_ENTRY();
        const v = computeAllFieldViews(g, ocrEntry, autofill[img] ?? null, activeDataset);
        imgFieldFilled = {} as Record<FieldKey, boolean>;
        for (const f of FIELDS) imgFieldFilled[f.key] = !!v[f.key].finalValue;
      }
      for (const tag of manifestItem.qualityTags) {
        const row = ensure(tag);
        row.total++;
        if (!ocrEntry) {
          row.notRun++;
        } else {
          if (imgStatus === "selected") row.selected++;
          else if (imgStatus.startsWith("suppressed_")) row.suppressed++;
          else if (imgStatus === "unknown") row.unknown++;
          else row.error++;
          if (imgFieldFilled) {
            for (const f of FIELDS) { if (imgFieldFilled[f.key]) row.fieldFilled[f.key]++; }
          }
        }
      }
    }
    if (map.size === 0) return null;
    return Array.from(map.values()).sort((a, b) => b.total - a.total);
  }, [manifest, images, ocr, gt, autofill, activeDataset]);

  const views   = useMemo(
    () => computeAllFieldViews(selGt, selOcr, selAuto, activeDataset),
    [selGt, selOcr, selAuto, activeDataset],
  );

  // ── batch summary (OCR raw / normalized / final 3축 점수 + autofill 효과) ──
  type BatchRow = {
    img: string;
    perField: Record<FieldKey, boolean | null>;       // final 기준 perField (KPI 누적용)
    okCount: number;
    gtCount: number;
    bizHit: boolean;
    textHit: boolean;
    improvedByAutofill: number;
    worsenedByAutofill: number;
    // 축별 요약
    rawPerField: Record<FieldKey, boolean | null>;
    normPerField: Record<FieldKey, boolean | null>;
    // O / △ / X / -- 표기용 — exact match 와 policy adoption 분리
    statusPerField: Record<FieldKey, MatchStatus>;
    exactCount: number;
    policyCount: number;
    mismatchCount: number;
  };
  const batchRows: BatchRow[] = useMemo(() => {
    return images.filter((img) => ocr[img]).map((img) => {
      const g = gt[img]?.fields ?? EMPTY_ENTRY();
      const v = computeAllFieldViews(g, ocr[img], autofill[img] ?? null, activeDataset);
      const finalValues = EMPTY_ENTRY();
      const finalSources = {} as Record<FieldKey, ValueSourceTag>;
      for (const f of FIELDS) {
        finalValues[f.key] = v[f.key].finalValue;
        finalSources[f.key] = v[f.key].finalSource;
      }
      const s = scoreTriplet(g, ocr[img].raw, ocr[img].normalized, finalValues, finalSources);
      const status = computeStatusPerField(g, ocr[img], finalValues, finalSources);
      const hasBiz  = (autofill[img]?.suggestions ?? []).some((x) => x.source === "biz");
      const hasText = (autofill[img]?.suggestions ?? []).some((x) => x.source === "text");
      return {
        img,
        perField: s.final.perField,
        okCount: s.final.okCount,
        gtCount: s.final.gtCount,
        bizHit: hasBiz,
        textHit: hasText,
        improvedByAutofill: s.improvedByAutofill,
        worsenedByAutofill: s.worsenedByAutofill,
        rawPerField:  s.raw.perField,
        normPerField: s.normalized.perField,
        statusPerField: status.statusPerField,
        exactCount:    status.counts.exact,
        policyCount:   status.counts.policy,
        mismatchCount: status.counts.mismatch,
      };
    });
  }, [images, ocr, gt, autofill, activeDataset]);

  // profile-based split: receipt vs finance (docs/TEST_PROFILE_SCHEMA_20260427.md §3)
  const receiptBatchRows = useMemo(
    () => batchRows.filter((r) => {
      const dt = manifest?.items.find((i) => i.filename === r.img)?.documentType;
      return resolveProfile(dt).base === "receipt";
    }),
    [batchRows, manifest],
  );
  const financeBatchRows = useMemo(
    () => batchRows.filter((r) => {
      const dt = manifest?.items.find((i) => i.filename === r.img)?.documentType;
      return resolveProfile(dt).base === "finance";
    }),
    [batchRows, manifest],
  );
  const documentBatchRows = useMemo(
    () => images.filter((img) => {
      if (!ocr[img]) return false;
      const dt = manifest?.items.find((i) => i.filename === img)?.documentType;
      return resolveProfile(dt).base === "document";
    }),
    [images, ocr, manifest],
  );

  // 영수증 계열 총 이미지 수 (미실행 포함) — receipt KPI 분모 (docs/TEST_PROFILE_SCHEMA §7.2)
  const receiptImageCount = useMemo(
    () => images.filter((img) => {
      if (!manifest) return true; // manifest 없으면 전체를 영수증으로 처리 (안전 fallback)
      const dt = manifest.items.find((i) => i.filename === img)?.documentType;
      return resolveProfile(dt).base === "receipt";
    }).length,
    [images, manifest],
  );

  // ── KPI: OCR 자체 성능 vs 채택값 성능 분리 ──
  type AxisStat = { fieldAcc: Record<FieldKey, { ok: number; total: number }>; overallOk: number; overallTotal: number };
  type Kpi = {
    processed: number;
    total: number;
    raw: AxisStat;
    norm: AxisStat;
    final: AxisStat;
    autofillBizApplied: number;
    autofillTextApplied: number;
    autofillBizHits: number;
    autofillTextHits: number;
    improvedByAutofill: number;        // OCR norm 오류 → final 정답 (autofill 순기여 총합)
    worsenedByAutofill: number;        // OCR norm 정답 → final 오류 (자동복원 역효과)
    needsHumanReview: number;
  };
  const emptyAxisStat = (): AxisStat => {
    const fieldAcc = {} as Record<FieldKey, { ok: number; total: number }>;
    for (const f of FIELDS) fieldAcc[f.key] = { ok: 0, total: 0 };
    return { fieldAcc, overallOk: 0, overallTotal: 0 };
  };
  const kpi: Kpi = useMemo(() => {
    const raw  = emptyAxisStat();
    const norm = emptyAxisStat();
    const fin  = emptyAxisStat();
    let autofillBizApplied = 0, autofillTextApplied = 0;
    let autofillBizHits = 0, autofillTextHits = 0;
    let improvedByAutofill = 0, worsenedByAutofill = 0;
    let needsHumanReview = 0;

    const accum = (axis: AxisStat, perField: Record<FieldKey, boolean | null>) => {
      for (const f of FIELDS) {
        const p = perField[f.key];
        if (p === null) continue;
        axis.fieldAcc[f.key].total += 1;
        axis.overallTotal += 1;
        if (p) { axis.fieldAcc[f.key].ok += 1; axis.overallOk += 1; }
      }
    };

    // receipt 계열만 집계 — finance_slip은 finance KPI로 별도 집계 (docs/TEST_PROFILE_SCHEMA §7.1)
    for (const row of receiptBatchRows) {
      accum(raw,  row.rawPerField);
      accum(norm, row.normPerField);
      accum(fin,  row.perField);
      if (row.bizHit)  autofillBizHits  += 1;
      if (row.textHit) autofillTextHits += 1;
      const applied = autofill[row.img]?.appliedSource;
      if (applied === "biz")  autofillBizApplied  += 1;
      if (applied === "text") autofillTextApplied += 1;
      improvedByAutofill += row.improvedByAutofill;
      worsenedByAutofill += row.worsenedByAutofill;
      if (row.gtCount > 0 && row.okCount < row.gtCount) needsHumanReview += 1;
    }
    return {
      processed: receiptBatchRows.length,
      total: receiptImageCount,
      raw, norm, final: fin,
      autofillBizApplied, autofillTextApplied,
      autofillBizHits, autofillTextHits,
      improvedByAutofill, worsenedByAutofill,
      needsHumanReview,
    };
  }, [receiptBatchRows, receiptImageCount, autofill]);

  // finance KPI — Tier-1 추출률 + GT 기반 정확도 포함 (docs/TEST_SUPPRESSION_POLICY_NOTE §6.2)
  type FinanceKpiSummary = {
    total: number;        // 전체 finance 이미지 수 (미실행 포함)
    processed: number;    // OCR 실행 완료 건수
    selected: number;
    review: number;
    suppressed: number;
    // Tier-1 추출률
    tier1Full: number;    // Tier-1 4필드 전부 추출된 이미지 수
    tier1Partial: number; // Tier-1 일부만 추출된 이미지 수
    tier1FieldExtract: Record<string, number>; // 필드별 추출된 이미지 수
    // GT 기반 정확도 (GT 있는 필드-이미지 쌍만 분모)
    gtImageCount: number; // GT financeFields가 하나라도 있는 이미지 수
    gtFieldTotal: number; // GT+OCR 비교 가능 필드 쌍 수 (Tier-1 한정)
    gtFieldMatch: number; // 정확 일치한 필드 쌍 수
    // Tier-1 필드별 GT 일치 상세 (breakdown용)
    tier1FieldGtMatch: Record<string, { match: number; total: number }>;
  };
  const financeKpi = useMemo((): FinanceKpiSummary => {
    const total = images.filter((img) => {
      const dt = manifest?.items.find((i) => i.filename === img)?.documentType;
      return resolveProfile(dt).base === "finance";
    }).length;

    let selected = 0, review = 0, suppressed = 0;
    let tier1Full = 0, tier1Partial = 0;
    let gtImageCount = 0, gtFieldTotal = 0, gtFieldMatch = 0;
    const tier1FieldExtract: Record<string, number> = {};
    const tier1FieldGtMatch: Record<string, { match: number; total: number }> = {};
    for (const k of FINANCE_TIER1_FIELDS) {
      tier1FieldExtract[k] = 0;
      tier1FieldGtMatch[k] = { match: 0, total: 0 };
    }

    for (const row of financeBatchRows) {
      // 상태 집계 — derived finance status 기준 (Tier-1 추출 + GT 비교 반영)
      // 백엔드 raw status는 유지하되 화면 표시용 status로 재해석
      const fStatus = deriveFinanceStatus(ocr[row.img], gt[row.img]?.financeFields);
      if (fStatus === "selected")        selected++;
      else if (fStatus === "review")     review++;
      else                               suppressed++;

      // Tier-1 추출률
      const finFields = ocr[row.img]?.financeFields ?? {};
      let extractCount = 0;
      for (const k of FINANCE_TIER1_FIELDS) {
        if (finFields[k]) {
          tier1FieldExtract[k] += 1;
          extractCount++;
        }
      }
      if (extractCount === FINANCE_TIER1_FIELDS.length) tier1Full++;
      else if (extractCount > 0) tier1Partial++;

      // GT 기반 정확도 (Tier-1, GT 있는 필드만 분모)
      const finGt = gt[row.img]?.financeFields ?? {};
      const hasAnyGt = FINANCE_TIER1_FIELDS.some((k) => finGt[k]);
      if (hasAnyGt) {
        gtImageCount++;
        for (const k of FINANCE_TIER1_FIELDS) {
          const gtVal  = finGt[k]      ?? "";
          const ocrVal = finFields[k]  ?? "";
          if (gtVal) {
            gtFieldTotal++;
            tier1FieldGtMatch[k].total++;
            // 정규화 비교 (콤마/공백/구분자/은행명 substring 흡수)
            if (financeFieldMatches(k, gtVal, ocrVal)) {
              gtFieldMatch++;
              tier1FieldGtMatch[k].match++;
            }
          }
        }
      }
    }

    return {
      total, processed: financeBatchRows.length,
      selected, review, suppressed,
      tier1Full, tier1Partial, tier1FieldExtract,
      gtImageCount, gtFieldTotal, gtFieldMatch,
      tier1FieldGtMatch,
    };
  }, [financeBatchRows, images, manifest, ocr, gt]);

  // document(invoice_statement) KPI — 거래 당사자(공급자/공급받는자) 필드 추출률 + GT 정확도
  // 형태는 financeKpi와 동일 (3개 receipt KPI 대신 거래명세서 dataset 전용으로 표시)
  type DocumentKpiSummary = {
    total: number;        // 전체 document 이미지 수 (미실행 포함)
    processed: number;    // OCR 실행 완료 건수
    selected: number;
    suppressed: number;
    // 거래 당사자 필드 추출률 (DOCUMENT_PARTY_FIELDS 8개 기준)
    partyFull: number;
    partyPartial: number;
    partyFieldExtract: Record<string, number>;
    // GT 기반 정확도 (GT 있는 필드-이미지 쌍만 분모)
    gtImageCount: number;
    gtFieldTotal: number;
    gtFieldMatch: number;
    partyFieldGtMatch: Record<string, { match: number; total: number }>;
  };
  const documentKpi = useMemo((): DocumentKpiSummary => {
    const total = images.filter((img) => {
      const dt = manifest?.items.find((i) => i.filename === img)?.documentType;
      return resolveProfile(dt).base === "document";
    }).length;

    let selected = 0, suppressed = 0;
    let partyFull = 0, partyPartial = 0;
    let gtImageCount = 0, gtFieldTotal = 0, gtFieldMatch = 0;
    const partyFieldExtract: Record<string, number> = {};
    const partyFieldGtMatch: Record<string, { match: number; total: number }> = {};
    for (const k of DOCUMENT_PARTY_FIELDS) {
      partyFieldExtract[k] = 0;
      partyFieldGtMatch[k] = { match: 0, total: 0 };
    }

    for (const img of documentBatchRows) {
      const ocrEntry = ocr[img];
      const status = ocrEntry?.status ?? "selected";
      if (status === "selected") selected++;
      else if (status.startsWith("suppressed_")) suppressed++;
      else selected++; // 기타 상태(예: unknown)는 selected에 포함 — finance와 동일한 보수적 처리

      const docFields = ocrEntry?.documentFields ?? {};
      let extractCount = 0;
      for (const k of DOCUMENT_PARTY_FIELDS) {
        if (docFields[k]) {
          partyFieldExtract[k] += 1;
          extractCount++;
        }
      }
      if (extractCount === DOCUMENT_PARTY_FIELDS.length) partyFull++;
      else if (extractCount > 0) partyPartial++;

      const docGt = gt[img]?.documentFields ?? {};
      const hasAnyGt = DOCUMENT_PARTY_FIELDS.some((k) => docGt[k]);
      if (hasAnyGt) {
        gtImageCount++;
        for (const k of DOCUMENT_PARTY_FIELDS) {
          const gtVal  = docGt[k]    ?? "";
          const ocrVal = docFields[k] ?? "";
          if (gtVal) {
            gtFieldTotal++;
            partyFieldGtMatch[k].total++;
            if (documentFieldMatches(gtVal, ocrVal) || gtVal === ocrVal) {
              gtFieldMatch++;
              partyFieldGtMatch[k].match++;
            }
          }
        }
      }
    }

    return {
      total, processed: documentBatchRows.length,
      selected, suppressed,
      partyFull, partyPartial, partyFieldExtract,
      gtImageCount, gtFieldTotal, gtFieldMatch,
      partyFieldGtMatch,
    };
  }, [documentBatchRows, images, manifest, ocr, gt]);

  const documentNormalizationKpi = useMemo((): DatasetNormalizationSummary => {
    const summary: DatasetNormalizationSummary = {
      candidateCount: 0,
      normPassCandidateCount: 0,
      normPartialCount: 0,
      normFailCount: 0,
      debugOnlyCount: 0,
      overcorrectionRiskCount: 0,
      unknownCount: 0,
      fields: [],
      entryCountWithCandidates: 0,
    };

    for (const img of documentBatchRows) {
      const entry = ocr[img];
      if (!getInvoiceNormalization(entry)) continue;
      mergeNormalizationSummary(summary, collectEntryNormalizationSummary(entry, gt[img]?.documentFields ?? {}));
    }

    return summary;
  }, [documentBatchRows, ocr, gt]);

  // ── invoice profile 집계 (P-1) — manifest 전체 기준 (OCR 미실행 이미지 포함) ──
  const invoiceProfileCounts = useMemo(() => {
    const amounts: Record<string, number> = {};
    const parties: Record<string, number> = {};
    const tables: Record<string, number> = {};
    if (!manifest) return { amounts, parties, tables, hasAny: false };
    for (const item of manifest.items) {
      if (resolveProfile(item.documentType).base !== "document") continue;
      const profile = item.invoiceProfile;
      if (!profile) continue;
      if (profile.amountProfile) amounts[profile.amountProfile] = (amounts[profile.amountProfile] ?? 0) + 1;
      if (profile.partyProfile) parties[profile.partyProfile] = (parties[profile.partyProfile] ?? 0) + 1;
      if (profile.tableProfile) tables[profile.tableProfile] = (tables[profile.tableProfile] ?? 0) + 1;
    }
    const hasAny = Object.keys(amounts).length > 0 || Object.keys(parties).length > 0;
    return { amounts, parties, tables, hasAny };
  }, [manifest]);

  // ── qualityTags 필터 ──
  const availableQualityTags = useMemo(() => {
    if (!manifest) return [];
    const tagSet = new Set<string>();
    for (const item of manifest.items) {
      for (const tag of item.qualityTags) tagSet.add(tag);
    }
    return Array.from(tagSet).sort();
  }, [manifest]);

  const filteredImages = useMemo(() => {
    if (selectedQualityTags.length === 0) return images;
    const selectedSet = new Set(selectedQualityTags);
    return images.filter((img) => {
      const meta = manifest?.items.find((i) => i.filename === img);
      if (!meta) return false;
      return meta.qualityTags.some((t) => selectedSet.has(t));
    });
  }, [images, selectedQualityTags, manifest]);

  const toggleQualityTag = (tag: string) => {
    setSelectedQualityTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  // ── documentType 기준 썸네일 그룹 (manifest 있을 때만) ──
  const docTypeGroups = useMemo((): { documentType: string; images: string[] }[] | null => {
    if (!manifest) return null;
    const map = new Map<string, string[]>();
    for (const img of filteredImages) {
      const dt = manifest.items.find((i) => i.filename === img)?.documentType ?? "unknown";
      if (!map.has(dt)) map.set(dt, []);
      map.get(dt)!.push(img);
    }
    const result: { documentType: string; images: string[] }[] = [];
    for (const dt of DOC_TYPE_ORDER) {
      const imgs = map.get(dt);
      if (imgs && imgs.length > 0) result.push({ documentType: dt, images: imgs });
    }
    for (const [dt, imgs] of map.entries()) {
      if (!DOC_TYPE_ORDER.includes(dt) && imgs.length > 0) {
        result.push({ documentType: dt, images: imgs });
      }
    }
    return result.length > 0 ? result : null;
  }, [manifest, filteredImages]);

  // ── 그룹핑 (사업자번호 기준 — manifest 없을 때 fallback) ──
  const groups: { label: string; biz: string; images: string[] }[] = [];
  const ungrouped: string[] = [];
  const seen: Record<string, number> = {};
  for (const img of filteredImages) {
    const rec  = gt[img];
    const biz  = rec?.fields?.사업자번호 ? normalizeBizNumber(rec.fields.사업자번호) ?? "" : "";
    const name = rec?.fields?.회사명 ?? "";
    if (biz) {
      if (seen[biz] !== undefined) {
        groups[seen[biz]].images.push(img);
      } else {
        seen[biz] = groups.length;
        groups.push({ label: name || biz, biz, images: [img] });
      }
    } else {
      ungrouped.push(img);
    }
  }
  const multiGroups = groups.filter((g) => g.images.length >= 2);
  const singles = [...groups.filter((g) => g.images.length < 2).flatMap((g) => g.images), ...ungrouped];

  // ── 렌더 ──
  const renderThumb = (img: string) => {
    const thumbMeta = manifest?.items.find((i) => i.filename === img) ?? null;
    const pdf = isPdfFile(img);
    return (
      <button
        key={img}
        type="button"
        onClick={() => setSelected(img)}
        style={{
          ...styles.thumb,
          border: selected === img ? "2px solid var(--accent)" : "2px solid transparent",
          boxShadow: selected === img ? "0 0 0 2px var(--accentBg)" : undefined,
        }}
      >
        {pdf ? (
          <PdfPagePreview url={imageUrl(activeTestset.path, img)} filename={img} variant="thumb" />
        ) : (
          <img src={imageUrl(activeTestset.path, img)} alt={img} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        )}
        <div style={styles.thumbLabel}>{img}</div>
        {thumbMeta && (
          <span
            title={thumbMeta.documentType}
            style={{ position: "absolute", top: 3, left: 3, fontSize: 9, fontWeight: 800, padding: "1px 4px", borderRadius: 3, background: DOC_TYPE_COLOR[thumbMeta.documentType] ?? "#6b7280", color: "#fff", lineHeight: 1.4 }}
          >
            {DOC_TYPE_ABBR[thumbMeta.documentType] ?? "?"}
          </span>
        )}
        <div style={{ position: "absolute", bottom: 3, right: 3, display: "flex", gap: 2 }}>
          {!!(gt[img]?.fields?.사업자번호 || gt[img]?.fields?.대표자) && <span style={dot("#22c55e")} title="기준값 있음" />}
          {!!ocrCache[img]?.ocr_text && <span style={dot("#a78bfa")} title="OCR 캐시" />}
          {!!ocr[img] && <span style={dot("var(--accent)")} title="OCR 실행됨" />}
          {autofill[img]?.appliedSource && (
            <span style={dot(autofill[img].appliedSource === "biz" ? "#6366f1" : "#a855f7")} title="자동복원 적용" />
          )}
        </div>
      </button>
    );
  };

  const modes: { id: ViewMode; label: string }[] = [
    { id: "compare",  label: "전체 비교" },
    { id: "ocr_only", label: "OCR만" },
    { id: "autofill", label: "자동복원" },
    { id: "gt_edit",  label: "기준값 편집" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 12 }}>
      <div style={styles.datasetBar}>
        <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 180 }}>
          <span style={{ fontSize: 11, fontWeight: 800, color: "var(--muted)", letterSpacing: 0.5, textTransform: "uppercase" }}>
            Test Dataset
          </span>
          <span style={{ fontSize: 12, color: "var(--text)" }}>{activeTestset.description}</span>
          {manifest && (
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 2 }}>
              <span title={manifest.datasetRole} style={{ fontSize: 9, fontWeight: 800, padding: "1px 6px", borderRadius: 3, color: "#fff", background: DATASET_ROLE_COLOR[manifest.datasetRole] ?? "#6b7280" }}>
                {DATASET_ROLE_LABELS[manifest.datasetRole] ?? manifest.datasetRole}
              </span>
              <span
                title={manifest.lockDoc ?? manifest.status}
                style={{ fontSize: 9, fontWeight: 800, padding: "1px 6px", borderRadius: 3, color: "#fff", background: DATASET_STATUS_COLOR[manifest.status] ?? "#6b7280" }}
              >
                {manifest.status === "locked" ? "🔒 잠금" : (DATASET_STATUS_LABELS[manifest.status] ?? manifest.status)}
              </span>
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {testsets.map((set) => (
            <button
              key={set.id}
              type="button"
              onClick={() => setActiveDataset(set.id)}
              disabled={running || runningAll}
              style={{
                ...styles.datasetBtn,
                background: activeDataset === set.id ? "var(--accent)" : "var(--panel2)",
                color: activeDataset === set.id ? "#fff" : "var(--text)",
                borderColor: activeDataset === set.id ? "transparent" : "rgba(255,255,255,0.08)",
              }}
            >
              {set.label}
              {set.id === activeDataset && (
                <span style={{ marginLeft: 6, opacity: 0.72, fontWeight: 700 }}>{images.length}</span>
              )}
            </button>
          ))}
        </div>
        <div style={{ width: "100%", display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 800 }}>채택값 출처:</span>
          <SourceLegend label="OCR" color="#0284c7" note="이번 OCR 결과" />
          <SourceLegend label="GT_*" color="#16a34a" note="baseline 전용 기준값 채택" />
          <SourceLegend label="AUTO" color="#6366f1" note="자동복원" />
          <SourceLegend label="GT_ONLY" color="#f59e0b" note="기준값만 있음 · 실행 결과 아님" />
          <SourceLegend label="EMPTY" color="#64748b" note="값 없음" />
        </div>
      </div>
      {uiError && (
        <div style={{
          padding: "8px 12px",
          borderRadius: 8,
          border: "1px solid rgba(239,68,68,0.35)",
          background: "rgba(239,68,68,0.10)",
          color: "#fecaca",
          fontSize: 12,
          fontWeight: 700,
          wordBreak: "break-word",
        }}>
          {uiError}
        </div>
      )}



      {/* ── Top bar: 썸네일 + 모드 + 실행 ── */}
      <div style={styles.topBar}>
        <div style={{ display: "flex", gap: 12, overflowX: "auto", flex: 1, alignItems: "center" }}>
          {docTypeGroups
            ? docTypeGroups.map((g) => (
                <div key={g.documentType} style={styles.groupBox}>
                  <div style={styles.groupLabel}>
                    <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 2, background: DOC_TYPE_COLOR[g.documentType] ?? "#6b7280", marginRight: 5, flexShrink: 0, verticalAlign: "middle" }} />
                    <span title={g.documentType}>{DOC_TYPE_LABEL[g.documentType] ?? g.documentType}</span>
                    <span style={{ color: "var(--muted)", fontSize: 9, marginLeft: 4, opacity: 0.7 }}>({g.documentType})</span>
                    <span style={{ color: "var(--muted)", fontWeight: 500, marginLeft: 4 }}>×{g.images.length}</span>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>{g.images.map(renderThumb)}</div>
                </div>
              ))
            : (
              <>
                {multiGroups.map((g) => (
                  <div key={g.biz} style={styles.groupBox}>
                    <div style={styles.groupLabel}>
                      <span style={{ color: "var(--accent)" }}>●</span> {g.label}
                      <span style={{ color: "var(--muted)", fontWeight: 500, marginLeft: 4 }}>×{g.images.length}</span>
                    </div>
                    <div style={{ display: "flex", gap: 6 }}>{g.images.map(renderThumb)}</div>
                  </div>
                ))}
                {singles.length > 0 && multiGroups.length > 0 && (
                  <div style={{ width: 1, height: 56, background: "rgba(255,255,255,0.08)", flexShrink: 0 }} />
                )}
                {singles.length > 0 && (
                  <div style={styles.groupBox}>
                    <div style={{ ...styles.groupLabel, color: "var(--muted)" }}>단독</div>
                    <div style={{ display: "flex", gap: 6 }}>{singles.map(renderThumb)}</div>
                  </div>
                )}
              </>
            )
          }
        </div>

        <div style={{ marginLeft: "auto", flexShrink: 0, display: "flex", alignItems: "center", gap: 8 }}>
          <div style={styles.modeSwitcher}>
            {modes.map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setViewMode(m.id)}
                style={{
                  ...styles.modeBtn,
                  background: viewMode === m.id ? "var(--accent)" : "transparent",
                  color: viewMode === m.id ? "#fff" : "var(--muted)",
                }}
              >{m.label}</button>
            ))}
          </div>
          {saveState !== "idle" && (
            <span style={{
              fontSize: 11, fontWeight: 600,
              padding: "4px 10px", borderRadius: 999,
              color: saveState === "saved" ? "#22c55e" : "var(--muted)",
              background: saveState === "saved" ? "rgba(34,197,94,0.12)" : "var(--panel2)",
            }}>{saveState === "saved" ? "✓ 기준값 저장됨" : "저장 중..."}</span>
          )}
          {selected && (
            <span style={{ fontSize: 12, color: "var(--muted)" }}>
              {selected}
              {runningAll && currentRunningFile === selected && (
                <span style={{ marginLeft: 6, color: "var(--accent)", fontWeight: 800 }}>OCR 실행 중</span>
              )}
              {runningAll && currentRunningFile !== selected && !selOcr && (
                <span style={{ marginLeft: 6, color: "#f59e0b", fontWeight: 800 }}>OCR 대기</span>
              )}
            </span>
          )}
          <button type="button" onClick={() => selected && runOne(selected)}
            disabled={!selected || running || runningAll}
            style={btnStyle(running, "accent")}>
            {running ? "실행 중..." : "Run OCR"}
          </button>
          <button type="button" onClick={runAll}
            disabled={running || runningAll || images.length === 0}
            style={btnStyle(runningAll, "ghost")}>
            {runningAll ? `Run All (${progress?.done}/${progress?.total})` : "Run All"}
          </button>
        </div>
      </div>

      {/* ── KPI: OCR 자체 / 자동복원 효과 / 최종 채택 (분리 표시) ── */}
      {images.length === 0 && (
        <div style={styles.emptyDataset}>
          <div style={{ fontSize: 15, fontWeight: 800, color: "var(--text)" }}>
            {activeDataset === "new_samples" ? "new_samples 폴더에 신규 영수증 파일을 넣어주세요" : "이 테스트셋에 이미지가 없습니다"}
          </div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
            {activeDataset === "new_samples"
              ? "이 세트는 일반화 검증용입니다. 기준값이 없어도 Run OCR과 상세 확인 흐름이 깨지지 않도록 분리되어 있습니다."
              : "테스트셋 폴더와 이미지 파일을 확인해주세요."}
          </div>
          <code style={{ marginTop: 10, display: "inline-block", fontSize: 11, color: "var(--muted)" }}>
            public{activeTestset.path}
          </code>
        </div>
      )}

      {batchRows.length > 0 && (
        <div style={styles.kpiWrapper}>
          {receiptBatchRows.length > 0 && (
          <KpiSection title="OCR 자체 성능" tone="sky" icon="🔎"
            subtitle="autofill 배제 · 모델 개선 지표"
          >
            <KpiChip label="전체" value={pct(kpi.norm.overallOk, kpi.norm.overallTotal)} sub={`${kpi.norm.overallOk}/${kpi.norm.overallTotal}`} tone={toneOf(kpi.norm.overallOk, kpi.norm.overallTotal)} />
            {FIELDS.map((f) => {
              const s = kpi.norm.fieldAcc[f.key];
              if (s.total === 0) return null;
              return <KpiChip key={f.key} label={f.label} value={pct(s.ok, s.total)} sub={`${s.ok}/${s.total}`} tone={toneOf(s.ok, s.total)} />;
            })}
          </KpiSection>
          )}

          {receiptBatchRows.length > 0 && (
          <div style={{ flex: "0.8 1 0", minWidth: 0 }}>
          <KpiSection title="자동복원 효과" tone="indigo" icon="⚡"
            subtitle="OCR 대비 개선 / 악화 카운트"
          >
            <KpiChip label="biz hit"  value={String(kpi.autofillBizHits)}  sub={`적용 ${kpi.autofillBizApplied}`} tone="indigo" />
            <KpiChip label="text hit" value={String(kpi.autofillTextHits)} sub={`적용 ${kpi.autofillTextApplied}`} tone="neutral" />
            <KpiChip label="개선"     value={String(kpi.improvedByAutofill)} sub="OCR→채택 +" tone="green" />
            <KpiChip label="악화"     value={String(kpi.worsenedByAutofill)} sub="OCR→채택 −" tone={kpi.worsenedByAutofill > 0 ? "red" : "neutral"} />
          </KpiSection>
          </div>
          )}

          {receiptBatchRows.length > 0 && (
          <KpiSection title="최종 채택값 성능" tone="green" icon="★"
            subtitle="영수증 계열 · 사용자에게 보여지는 값"
          >
            <KpiChip label="영수증 처리" value={`${kpi.processed}/${kpi.total}`} />
            <KpiChip label="전체" value={pct(kpi.final.overallOk, kpi.final.overallTotal)} sub={`${kpi.final.overallOk}/${kpi.final.overallTotal}`} tone={toneOf(kpi.final.overallOk, kpi.final.overallTotal)} />
            {FIELDS.map((f) => {
              const s = kpi.final.fieldAcc[f.key];
              if (s.total === 0) return null;
              return <KpiChip key={f.key} label={f.label} value={pct(s.ok, s.total)} sub={`${s.ok}/${s.total}`} tone={toneOf(s.ok, s.total)} />;
            })}
            <KpiChip label="사람 검토 필요" value={`${kpi.needsHumanReview}`} tone={kpi.needsHumanReview > 0 ? "amber" : "green"} />
          </KpiSection>
          )}

          {/* ── 금융전표 현황 (finance_profile) ── */}
          {financeKpi.total > 0 && (
          <KpiSection title="금융전표 현황" tone="red" icon="🏦"
            subtitle={`finance_profile · ${financeKpi.processed}/${financeKpi.total} 처리`}
          >
            {/* 기본 상태 카운트 */}
            <KpiChip label="전체" value={`${financeKpi.total}`} sub={`처리 ${financeKpi.processed}`} />
            <KpiChip
              label="selected"
              value={String(financeKpi.selected)}
              tone={financeKpi.selected > 0 ? "green" : "neutral"}
            />
            <KpiChip
              label="review"
              value={String(financeKpi.review)}
              tone={financeKpi.review > 0 ? "amber" : "neutral"}
            />
            {financeKpi.suppressed > 0 && (
              <KpiChip label="suppressed" value={String(financeKpi.suppressed)} tone="red" />
            )}
            <KpiChip
              label="미처리"
              value={String(financeKpi.total - financeKpi.processed)}
              tone={financeKpi.total - financeKpi.processed > 0 ? "neutral" : "green"}
            />
            {/* Tier-1 추출률 — OCR 실행 건 중 4필드 전부 추출된 비율 */}
            {financeKpi.processed > 0 && (
              <KpiChip
                label="Tier-1 완전"
                value={`${financeKpi.tier1Full}/${financeKpi.processed}`}
                sub={pct(financeKpi.tier1Full, financeKpi.processed)}
                tone={toneOf(financeKpi.tier1Full, financeKpi.processed)}
              />
            )}
            {/* GT 기반 정확도 — GT 입력된 Tier-1 필드-이미지 쌍 기준 */}
            {financeKpi.gtFieldTotal > 0 && (
              <KpiChip
                label="GT 일치"
                value={pct(financeKpi.gtFieldMatch, financeKpi.gtFieldTotal)}
                sub={`${financeKpi.gtFieldMatch}/${financeKpi.gtFieldTotal} 필드`}
                tone={toneOf(financeKpi.gtFieldMatch, financeKpi.gtFieldTotal)}
              />
            )}
          </KpiSection>
          )}

          {/* ── 거래명세서 현황 (document profile) ── */}
          {documentKpi.total > 0 && (
          <KpiSection title="거래명세서 현황" tone="amber" icon="📄"
            subtitle={`document profile · ${documentKpi.processed}/${documentKpi.total} 처리`}
          >
            <KpiChip label="전체" value={`${documentKpi.total}`} sub={`처리 ${documentKpi.processed}`} />
            <KpiChip
              label="selected"
              value={String(documentKpi.selected)}
              tone={documentKpi.selected > 0 ? "green" : "neutral"}
            />
            {documentKpi.suppressed > 0 && (
              <KpiChip label="suppressed" value={String(documentKpi.suppressed)} tone="red" />
            )}
            <KpiChip
              label="미처리"
              value={String(documentKpi.total - documentKpi.processed)}
              tone={documentKpi.total - documentKpi.processed > 0 ? "neutral" : "green"}
            />
            {documentKpi.processed > 0 && (
              <KpiChip
                label="거래처 완전"
                value={`${documentKpi.partyFull}/${documentKpi.processed}`}
                sub={pct(documentKpi.partyFull, documentKpi.processed)}
                tone={toneOf(documentKpi.partyFull, documentKpi.processed)}
              />
            )}
            {documentKpi.gtFieldTotal > 0 && (
              <KpiChip
                label="GT 일치"
                value={pct(documentKpi.gtFieldMatch, documentKpi.gtFieldTotal)}
                sub={`${documentKpi.gtFieldMatch}/${documentKpi.gtFieldTotal} 필드`}
                tone={toneOf(documentKpi.gtFieldMatch, documentKpi.gtFieldTotal)}
              />
            )}
            {documentNormalizationKpi.candidateCount > 0 && (
              <>
                <KpiChip
                  label="Norm 후보"
                  value={String(documentNormalizationKpi.candidateCount)}
                  sub={`${documentNormalizationKpi.entryCountWithCandidates} files`}
                  tone="neutral"
                  title="Normalized candidates from extract_debug.invoice_statement.normalization. Existing exact O/X is unchanged."
                />
                <KpiChip
                  label="Norm O 가능"
                  value={String(documentNormalizationKpi.normPassCandidateCount)}
                  sub="exact X 보조"
                  tone={documentNormalizationKpi.normPassCandidateCount > 0 ? "green" : "neutral"}
                  title="Raw/exact X fields whose normalized candidate may match GT. This is only an auxiliary marker."
                />
                <KpiChip
                  label="Norm △"
                  value={String(documentNormalizationKpi.normPartialCount)}
                  tone={documentNormalizationKpi.normPartialCount > 0 ? "amber" : "neutral"}
                  title="Partial normalized candidates or candidates that need human review."
                />
                <KpiChip
                  label="주의"
                  value={String(documentNormalizationKpi.overcorrectionRiskCount)}
                  sub={documentNormalizationKpi.unknownCount > 0 ? `판정불가 ${documentNormalizationKpi.unknownCount}` : undefined}
                  tone={documentNormalizationKpi.overcorrectionRiskCount > 0 ? "amber" : "neutral"}
                  title="debug_only, low-confidence, or possible overcorrection rules. These are not counted as pass."
                />
              </>
            )}
            {invoiceProfileCounts.hasAny && (
              <InvoiceProfileKpi counts={invoiceProfileCounts} />
            )}
          </KpiSection>
          )}

        </div>
      )}

      {/* ── documentType 집계 ── */}
      {docTypeSummary && (
        <DocTypeSummarySection rows={docTypeSummary} totalImages={images.length} />
      )}

      {/* ── Batch summary (접기/펼치기 토글) ── */}
      {batchRows.length > 0 && (
        <div style={styles.batchBox}>
          <div
            style={{ ...styles.sectionHeader, cursor: "pointer", userSelect: "none", display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: showBatchSummary ? 8 : 0 }}
            onClick={() => setShowBatchSummary((v) => !v)}
          >
            <span>
              전체 결과 요약 ({batchRows.length}건)
              <span style={{ marginLeft: 8, color: "var(--muted)", fontWeight: 500, fontSize: 10 }}>
                <span style={{ color: "#22c55e", fontWeight: 700 }}>O</span>=기준값과 정확히 일치 ·{" "}
                <span style={{ color: "#f59e0b", fontWeight: 700 }}>△</span>=정규화/유사도/anchor/자동복원 채택 ·{" "}
                <span style={{ color: "#ef4444", fontWeight: 700 }}>X</span>=불일치 ·{" "}
                <span style={{ color: "rgba(255,255,255,0.45)", fontWeight: 700 }}>—</span>=기준값 없음
              </span>
            </span>
            <span style={{ fontSize: 10, color: "var(--muted)", marginLeft: 8, flexShrink: 0 }}>
              {showBatchSummary ? "▼" : "▶"}
            </span>
          </div>
          {showBatchSummary && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

            {/* ── 영수증 계열 섹션 (receipt_profile) ── */}
            {receiptBatchRows.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              {financeBatchRows.length > 0 && (
                <div style={{ fontSize: 10, color: "var(--muted)", fontWeight: 700, marginBottom: 4, letterSpacing: 0.4 }}>
                  영수증 계열 ({receiptBatchRows.length}건)
                </div>
              )}
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr>
                    <th style={th}>파일명</th>
                    {FIELDS.map((f) => <th key={f.key} style={th}>{f.label}</th>)}
                    <th style={{ ...th, textAlign: "center" }}>매칭률</th>
                    <th style={{ ...th, textAlign: "center" }}>자동복원</th>
                  </tr>
                </thead>
                <tbody>
                  {receiptBatchRows.map((row) => {
                    const applied = autofill[row.img]?.appliedSource ?? null;
                    return (
                      <tr key={row.img} onClick={() => setSelected(row.img)}
                        style={{ cursor: "pointer", background: selected === row.img ? "var(--accentBg)" : undefined }}>
                        <td style={td}>{row.img}</td>
                        {FIELDS.map((f) => {
                          const st = row.statusPerField[f.key];
                          const meta = matchStatusMeta(st);
                          return (
                            <td key={f.key} style={{ ...td, textAlign: "center" }} title={meta.title}>
                              <span style={{ fontWeight: 800, color: meta.color }}>{meta.symbol}</span>
                            </td>
                          );
                        })}
                        <td style={{ ...td, textAlign: "center", fontWeight: 700 }}
                            title={row.gtCount > 0 ? `정확 ${row.exactCount} · 정책 ${row.policyCount} · 불일치 ${row.mismatchCount} / 기준값 ${row.gtCount}` : "기준값 없음"}>
                          {row.gtCount > 0
                            ? (
                              <span style={{
                                color: row.exactCount === row.gtCount
                                  ? "#22c55e"
                                  : (row.exactCount + row.policyCount) === row.gtCount
                                    ? "#f59e0b"
                                    : row.exactCount + row.policyCount > 0
                                      ? "#f59e0b"
                                      : "#ef4444",
                              }}>
                                {row.okCount}/{row.gtCount}
                                {row.exactCount > 0 && row.exactCount < row.okCount && (
                                  <span style={{ color: "rgba(255,255,255,0.5)", fontWeight: 500, fontSize: 10, marginLeft: 4 }}>
                                    (정확 {row.exactCount})
                                  </span>
                                )}
                              </span>
                            )
                            : <span style={{ color: "rgba(255,255,255,0.2)" }}>—</span>}
                        </td>
                        <td style={{ ...td, textAlign: "center" }}>
                          {applied === "biz"
                            ? <span style={{ ...chip, background: "#6366f1" }}>사업자</span>
                            : applied === "text"
                              ? <span style={{ ...chip, background: "#a855f7" }}>유사</span>
                              : row.bizHit
                                ? <span style={{ ...chip, background: "#64748b" }}>biz 제안</span>
                                : row.textHit
                                  ? <span style={{ ...chip, background: "#64748b" }}>text 제안</span>
                                  : <span style={{ color: "rgba(255,255,255,0.25)" }}>-</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            )}

            {/* ── 금융전표 계열 섹션 (finance_profile) — O/△/X/— 비교형 ── */}
            {financeBatchRows.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <div style={{ fontSize: 10, color: "#dc2626", fontWeight: 700, marginBottom: 4, letterSpacing: 0.4 }}>
                금융전표 계열 ({financeBatchRows.length}건) — finance_profile
                <span style={{ marginLeft: 8, fontWeight: 500, color: "var(--muted)" }}>
                  O=일치 · △=정규화일치 · X=불일치 · —=기준값없음
                </span>
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr>
                    <th style={th}>파일명</th>
                    {FINANCE_DISPLAY_COLS.map((col) => (
                      <th key={col.key} style={th}>{col.label}</th>
                    ))}
                    <th style={{ ...th, textAlign: "center" }}>상태</th>
                  </tr>
                </thead>
                <tbody>
                  {financeBatchRows.map((row) => {
                    const ocrEntry = ocr[row.img];
                    const fStatus = deriveFinanceStatus(ocrEntry, gt[row.img]?.financeFields);
                    const statusMeta = getFinanceStatusMetaFromDerived(fStatus, !!ocrEntry);
                    const finFields = ocrEntry?.financeFields ?? {};
                    const finGt     = gt[row.img]?.financeFields ?? {};
                    const reviewReasons = ocrEntry?.financeReviewReasons ?? [];
                    return (
                      <tr key={row.img} onClick={() => setSelected(row.img)}
                        style={{ cursor: "pointer", background: selected === row.img ? "var(--accentBg)" : undefined }}>
                        <td style={td}>{row.img}</td>
                        {FINANCE_DISPLAY_COLS.map((col) => {
                          const gtVal  = finGt[col.key]    ?? "";
                          const ocrVal = finFields[col.key] ?? "";
                          const ms   = financeMatchStatus(col.key, gtVal, ocrVal);
                          const meta = financeMatchMeta(ms);
                          const tooltip = gtVal
                            ? `GT: ${gtVal} / OCR: ${ocrVal || "없음"}`
                            : ocrVal
                              ? `OCR: ${ocrVal} (기준값 없음)`
                              : "미추출";
                          return (
                            <td key={col.key} style={{ ...td, textAlign: "center" }} title={tooltip}>
                              <span style={{ fontWeight: 800, color: meta.color }}>{meta.symbol}</span>
                              {ocrVal && ms !== "—" && (
                                <span style={{ fontSize: 9, color: "var(--muted)", marginLeft: 2, display: "block", whiteSpace: "nowrap", overflow: "hidden", maxWidth: 70, textOverflow: "ellipsis" }}>
                                  {ocrVal.length > 9 ? ocrVal.slice(0, 9) + "…" : ocrVal}
                                </span>
                              )}
                            </td>
                          );
                        })}
                        <td style={{ ...td, textAlign: "center" }}>
                          <span
                            title={reviewReasons.length > 0 ? reviewReasons.join(", ") : undefined}
                            style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: statusMeta.bg, color: "#fff", fontWeight: 700 }}
                          >
                            {statusMeta.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div style={{ fontSize: 9, color: "var(--muted)", marginTop: 4, paddingLeft: 2 }}>
                ※ finance_profile Tier-1 (은행명/거래일시/거래금액). Tier-2 및 정밀 추출은 별도 단계.
              </div>
            </div>
            )}

          </div>
          )}
        </div>
      )}

      {showBatchSummary && documentBatchRows.length > 0 && (
        <div style={styles.batchBox}>
          <div style={{ fontSize: 10, color: "#ca8a04", fontWeight: 700, marginBottom: 4, letterSpacing: 0.4 }}>
            거래명세서 계열 ({documentBatchRows.length}건)
            <span style={{ marginLeft: 8, fontWeight: 500, color: "var(--muted)" }}>
              O=일치 · △=부분일치 · X=불일치 · —=GT 없음
            </span>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr>
                  <th style={th}>파일명</th>
                  {DOCUMENT_FIELD_META.map((col) => (
                    <th key={col.key} style={th}>{col.shortLabel}</th>
                  ))}
                  <th style={{ ...th, textAlign: "center" }} title="amountProfile: 금액 구조 유형 (P-1)">Amount</th>
                  <th style={{ ...th, textAlign: "center" }} title="partyProfile: 거래 당사자 구조 (P-1)">Party</th>
                  <th style={{ ...th, textAlign: "center" }} title="Normalized auxiliary counts. Existing exact O/X is not changed.">Norm</th>
                  <th style={{ ...th, textAlign: "center" }}>상태</th>
                </tr>
              </thead>
              <tbody>
                {documentBatchRows.map((img) => {
                  const entry = ocr[img];
                  const docFields = entry?.documentFields ?? {};
                  const docGt = gt[img]?.documentFields ?? {};
                  const status = entry?.status ?? "selected";
                  const normSummary = collectEntryNormalizationSummary(entry, docGt);
                  const invProfile = manifest?.items.find((i) => i.filename === img)?.invoiceProfile;
                  const amtLabel = getAmountProfileLabel(invProfile?.amountProfile);
                  const partyLabel = getPartyProfileLabel(invProfile?.partyProfile);
                  const amtNoAmount = invProfile?.amountProfile === "no_amount_summary" || invProfile?.amountProfile === "quantity_total_only";
                  return (
                    <tr key={img} onClick={() => setSelected(img)}
                      style={{ cursor: "pointer", background: selected === img ? "var(--accentBg)" : undefined }}>
                      <td style={td}>{img}</td>
                      {DOCUMENT_FIELD_META.map((col) => {
                        const gtVal = docGt[col.key] ?? "";
                        const ocrVal = docFields[col.key] ?? "";
                        const meta = documentMatchMeta(documentMatchStatus(gtVal, ocrVal));
                        return (
                          <td key={col.key} style={{ ...td, textAlign: "center" }} title={`GT: ${gtVal || "-"} / OCR: ${ocrVal || "-"}`}>
                            <span style={{ fontWeight: 800, color: meta.color }}>{meta.symbol}</span>
                            {ocrVal && (
                              <span style={{ fontSize: 9, color: "var(--muted)", marginLeft: 2, display: "block", whiteSpace: "nowrap", overflow: "hidden", maxWidth: 70, textOverflow: "ellipsis" }}>
                                {ocrVal.length > 9 ? ocrVal.slice(0, 9) + "…" : ocrVal}
                              </span>
                            )}
                          </td>
                        );
                      })}
                      <td style={{ ...td, textAlign: "center" }}
                        title={invProfile?.amountProfile ? `amountProfile: ${invProfile.amountProfile}` : "invoiceProfile 없음"}>
                        <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 3, background: amtNoAmount ? "#7c3aed" : "#0369a1", color: "#fff", fontWeight: 700, whiteSpace: "nowrap" }}>
                          {amtLabel}
                        </span>
                      </td>
                      <td style={{ ...td, textAlign: "center" }}
                        title={invProfile?.partyProfile ? `partyProfile: ${invProfile.partyProfile}` : "invoiceProfile 없음"}>
                        <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 3, background: "#374151", color: "#d1d5db", fontWeight: 600, whiteSpace: "nowrap" }}>
                          {partyLabel}
                        </span>
                      </td>
                      <td style={{ ...td, textAlign: "center" }} title={normalizationSummaryTitle(normSummary)}>
                        {normSummary.candidateCount > 0 ? (
                          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                            <span style={{ fontSize: 10, color: "#38bdf8", fontWeight: 800, whiteSpace: "nowrap" }}>
                              O {normSummary.normPassCandidateCount} · △ {normSummary.normPartialCount}
                            </span>
                            {(normSummary.overcorrectionRiskCount > 0 || normSummary.unknownCount > 0) && (
                              <span style={{ fontSize: 9, color: "#f59e0b", fontWeight: 700, whiteSpace: "nowrap" }}>
                                주의 {normSummary.overcorrectionRiskCount} · — {normSummary.unknownCount}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span style={{ color: "rgba(255,255,255,0.35)" }}>—</span>
                        )}
                      </td>
                      <td style={{ ...td, textAlign: "center" }}>
                        <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: 4, background: status === "selected" ? "#16a34a" : "#6b7280", color: "#fff", fontWeight: 700 }}>
                          {status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Main: image + compare ── */}
      <div style={{ display: "flex", flex: 1, gap: 12, overflow: "hidden", minHeight: 0 }}>
        {/* Left: image */}
        <div style={{ ...styles.imagePane, position: "relative" }}>
          {selOcr?.displayUrl && !isPdfFile(selected)
            ? <img key={selOcr.displayUrl} src={selOcr.displayUrl} alt="OCR" style={styles.previewImage} />
            : selected
              ? isPdfFile(selected)
                ? <PdfPagePreview key={selected} url={imageUrl(activeTestset.path, selected)} filename={selected} variant="preview" />
                : <img key={selected} src={imageUrl(activeTestset.path, selected)} alt="original" style={styles.previewImage} />
              : <p style={{ color: "var(--muted)", fontSize: 13 }}>이미지를 선택하세요</p>}
          {(running || runningAll) && <div className="uw-scan-overlay"><div className="uw-scan-line" /></div>}
        </div>

        {/* Right: compare pane */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6, overflow: "auto", minWidth: 0 }}>

          {/* autofill 배지 + 제어 (정보 밀도 낮춘 간소 버전) */}
          {selected && selAuto && selAuto.suggestions.length > 0 && (
            <div style={styles.autofillBar}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", flex: 1 }}>
                <span style={{ fontSize: 12, fontWeight: 800, color: "#818cf8", letterSpacing: 0.4, textTransform: "uppercase" }}>⚡ 자동복원</span>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap", flex: 1, minWidth: 0 }}>
                  {selAuto.suggestions.map((s) => {
                    const isApplied = selAuto.appliedSource === s.source;
                    const autoApplicable = s.source === "biz" && s.confidence >= BIZ_AUTO_APPLY_CONFIDENCE;
                    const kind =
                      s.source === "biz"
                        ? (autoApplicable ? "자동적용" : "제안(근거 부족)")
                        : "제안(승인 필요)";
                    return (
                      <button
                        key={s.source}
                        type="button"
                        onClick={() => toggleAutofillApply(selected, s.source)}
                        title={s.source === "biz" ? `사업자번호 매칭 · ${s.matchedFrom} · 신뢰도 ${Math.round(s.confidence * 100)}%` : `텍스트 유사도 ${Math.round((s.score ?? s.confidence) * 100)}% · ${s.matchedFrom}`}
                        style={{ ...styles.autofillChip,
                          background: isApplied ? (s.source === "biz" ? "#6366f1" : "#a855f7") : "var(--panel2)",
                          color: isApplied ? "#fff" : "var(--text)",
                          border: isApplied ? "1px solid transparent" : `1px solid ${s.source === "biz" ? "rgba(99,102,241,0.4)" : "rgba(168,85,247,0.4)"}`,
                        }}>
                        {isApplied && <span style={{ marginRight: 3 }}>✓</span>}
                        {s.source === "biz" ? "사업자번호" : "유사문서"}
                        <span style={{ opacity: 0.75, fontWeight: 600, margin: "0 4px" }}>·</span>
                        <span style={{ opacity: 0.85 }}>{s.matchedFrom}</span>
                        <span style={{ opacity: 0.75, fontWeight: 600, margin: "0 4px" }}>·</span>
                        <span style={{ fontSize: 10, fontWeight: 800 }}>
                          {s.source === "biz" ? `${Math.round(s.confidence * 100)}%` : `${Math.round((s.score ?? s.confidence) * 100)}%`}
                        </span>
                        <span style={{ opacity: 0.65, fontSize: 10, marginLeft: 6 }}>{kind}</span>
                      </button>
                    );
                  })}
                </div>
                {selAuto.suggestions.some((s) => s.source === "biz" && (s.reasons?.length ?? 0) > 0) && (
                  <button type="button" onClick={() => setShowReasons((x) => !x)}
                    style={{
                      fontSize: 10, fontWeight: 700, color: "var(--muted)",
                      background: "transparent", border: "1px dashed rgba(255,255,255,0.15)",
                      borderRadius: 6, padding: "3px 8px", cursor: "pointer",
                    }}>
                    {showReasons ? "근거 접기 ▲" : "근거 보기 ▼"}
                  </button>
                )}
              </div>
              <button type="button" onClick={() => commitFinalsToGt(selected)} style={styles.commitBtn}>
                전체 채택값을 기준값으로 확정
              </button>

              {/* biz 근거 칩 (토글) */}
              {showReasons && selAuto.suggestions.filter((s) => s.source === "biz" && s.reasons).map((s) => (
                <div key={`r-${s.source}`} style={{
                  width: "100%", display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap",
                  padding: "6px 10px", marginTop: 4,
                  background: "rgba(99,102,241,0.06)", borderRadius: 6,
                  borderTop: "1px dashed rgba(99,102,241,0.2)",
                }}>
                  <span style={{ fontSize: 9, color: "#818cf8", fontWeight: 800, letterSpacing: 0.4 }}>신뢰도 근거</span>
                  {s.reasons!.map((r, ri) => (
                    <span key={ri} title={r.note}
                      style={{
                        fontSize: 10, padding: "1px 6px", borderRadius: 4,
                        background: r.delta > 0 ? "rgba(34,197,94,0.15)"
                                   : r.delta < 0 ? "rgba(239,68,68,0.15)"
                                   : "rgba(255,255,255,0.05)",
                        color:      r.delta > 0 ? "#22c55e"
                                   : r.delta < 0 ? "#ef4444"
                                   : "var(--muted)",
                      }}>
                      {r.code}{r.delta !== 0 ? ` ${r.delta > 0 ? "+" : ""}${r.delta.toFixed(2)}` : ""}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          )}
          {selected && (!selAuto || selAuto.suggestions.length === 0) && selOcr && (
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button type="button" onClick={() => commitFinalsToGt(selected)} style={styles.commitBtn}>
                전체 채택값을 기준값으로 확정
              </button>
            </div>
          )}

          {/* Manifest metadata badges */}
          {selected && selMeta && <ManifestMetaBadges item={selMeta} />}

          {/* Field cards — finance_profile: finance 전용 패널 / receipt_profile: 기존 FieldCard */}
          {selected && selProfile.base === "finance" ? (
            <FinanceDetailPanel
              financeFields={selOcr?.financeFields ?? null}
              reviewReasons={selOcr?.financeReviewReasons ?? []}
              hasOcr={!!selOcr}
              financeGt={selFinanceGt}
              onFinanceGtChange={(field, value) => updateFinanceGtField(selected!, field, value)}
              derivedStatus={selOcr ? deriveFinanceStatus(selOcr, selFinanceGt) : undefined}
            />
          ) : selected && selProfile.base === "document" ? (
            <DocumentDetailPanel
              documentFields={selOcr?.documentFields ?? null}
              normalization={getInvoiceNormalization(selOcr)}
              invoiceDebug={getInvoiceDebug(selOcr)}
              hasOcr={!!selOcr}
              documentGt={selDocumentGt}
              onDocumentGtChange={(field, value) => updateDocumentGtField(selected!, field, value)}
              invoiceProfile={selMeta?.invoiceProfile}
            />
          ) : selected ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {FIELDS.map(({ key, label, allowAutofill }) => {
                // not_applicable: profile에 없는 필드는 X가 아니라 해당없음 (docs/TEST_PROFILE_SCHEMA §8)
                const profileKey = FIELD_KEY_PROFILE_MAP[key] ?? key;
                if (isNotApplicableField(selProfile.base, profileKey)) {
                  return (
                    <div key={key} style={{
                      background: "var(--panel)", borderRadius: 10,
                      border: "1px dashed rgba(255,255,255,0.08)",
                      padding: "7px 12px",
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      opacity: 0.38,
                    }}>
                      <span style={{ fontSize: 13, fontWeight: 800, color: "var(--muted)" }}>{label}</span>
                      <span
                        title={`이 문서 유형(${selMeta?.documentType ?? selProfile.base})에서는 해당 없는 필드 — KPI 분모 제외`}
                        style={{ fontSize: 12, fontWeight: 800, color: "rgba(255,255,255,0.3)", userSelect: "none" }}
                      >
                        —
                      </span>
                    </div>
                  );
                }

                const v = views[key];
                const m: MatchResult = matchField(v.gt, v.finalValue);
                const matchStatus = computeMatchStatus(
                  key, v.gt, v.ocrRaw, v.ocrNormalized, v.finalValue, v.finalSource,
                );
                const isAmount = key === "총합계금액";
                const bs = bizStatus[selected];
                const bsText = bs === "active" ? "정상" : bs === "closed" ? "폐업" : bs ? "미확인" : undefined;
                const bsColor = bs === "active" ? "#22c55e" : bs === "closed" ? "#ef4444" : "#6b7280";
                return (
                  <FieldCard
                    key={key}
                    fieldKey={key}
                    label={label}
                    allowAutofill={allowAutofill}
                    view={v}
                    viewMode={viewMode}
                    hasOcr={!!selOcr}
                    bizStatusText={key === "사업자번호" ? bsText : undefined}
                    bizStatusColor={bsColor}
                    isAmount={isAmount}
                    matchResult={m}
                    matchStatus={matchStatus}
                    onGtChange={(val) => updateGtField(selected, key, val)}
                    onCommit={() => commitFieldToGt(selected, key, v.finalValue)}
                  />
                );
              })}
            </div>
          ) : null}

          {/* timing */}
          {selOcr && (
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 12px", background: "var(--panel)", borderRadius: 7, flexShrink: 0 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 3 }}>
                <span style={{ fontSize: 18, fontWeight: 800, color: selOcr.processingTime > 15 ? "#f59e0b" : "#22c55e", letterSpacing: -0.5 }}>{selOcr.processingTime}</span>
                <span style={{ fontSize: 11, fontWeight: 600, color: "var(--muted)" }}>초</span>
              </div>
              <div style={{ width: 1, height: 16, background: "rgba(255,255,255,0.1)" }} />
              <span style={{ fontSize: 11, color: "var(--muted)" }}>{selOcr.fullText.split("\n").filter(Boolean).length}줄 감지</span>
            </div>
          )}

          {/* Debug panel */}
          {selOcr && (
            <details open={showDebug} onToggle={(e) => setShowDebug((e.target as HTMLDetailsElement).open)} style={{ background: "var(--panel)", borderRadius: 8, padding: "8px 14px" }}>
              <summary style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", cursor: "pointer", letterSpacing: 0.5 }}>
                디버그 패널 {showDebug ? "▼" : "▶"}
              </summary>
              {showDebug && selected && (
                <DebugPanel
                  filename={selected}
                  ocr={selOcr}
                  autofill={selAuto}
                  bizStatus={bizStatus[selected]}
                />
              )}
            </details>
          )}

          {/* raw OCR text (기본 접힘, 디버깅용) */}
          {selOcr && (
            <details style={{ background: "var(--panel)", borderRadius: 8, padding: "8px 14px" }}>
              <summary style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", cursor: "pointer", letterSpacing: 0.5, textTransform: "uppercase" }}>
                전체 OCR 텍스트 ({selOcr.fullText.split("\n").filter(Boolean).length}줄)
              </summary>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 10 }}>
                {selOcr.fullText.split("\n").filter(Boolean).map((line, idx) => (
                  <span key={idx} style={{
                    fontSize: 11, padding: "2px 8px", borderRadius: 4,
                    background: "var(--panel2)", color: "var(--text)",
                    border: "1px solid rgba(255,255,255,0.06)", lineHeight: 1.6,
                  }}>{line}</span>
                ))}
              </div>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// DebugPanel
// ============================================================
function DebugPanel({
  filename, ocr, autofill, bizStatus,
}: {
  filename: string;
  ocr: OcrEntry;
  autofill: AutofillRecord | null;
  bizStatus: "active" | "closed" | "unknown" | undefined;
}) {
  // 사업자번호 raw 후보
  const bizRawList = (ocr.fullText.match(/[1-9]\d{2}[\s\-.]?\d{2}[\s\-.]?\d{5}/g) ?? []);
  const bizPicked = extractBizNumber(ocr.fullText);

  // 전화번호 후보
  const telRawList = (ocr.fullText.match(/0\d{1,2}[-\s.]?\d{3,4}[-\s.]?\d{4}/g) ?? []);

  // 금액 후보
  const amountLines = ocr.fullText.split("\n").map((l) => l.trim()).filter(Boolean);
  const amountCandidates: { line: string; amounts: string[] }[] = [];
  for (const l of amountLines) {
    const a = parseAmounts(l);
    if (a.length) amountCandidates.push({ line: l, amounts: a });
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8, fontSize: 11 }}>
      <DbgBlock title="사업자번호">
        <DbgRow label="raw 후보" value={bizRawList.length ? bizRawList.join(", ") : "-"} />
        <DbgRow label="정규화 결과" value={bizPicked ?? "-"} />
        <DbgRow label="OCR 필드값" value={ocr.raw.사업자번호 || "-"} />
        <DbgRow label="OCR 정규화값" value={ocr.normalized.사업자번호 || "-"} />
        <DbgRow label="NTS 상태" value={bizStatus ?? "-"} />
      </DbgBlock>

      <DbgBlock title="전화번호">
        <DbgRow label="raw 후보" value={telRawList.length ? telRawList.join(", ") : "-"} />
        <DbgRow label="OCR 필드값" value={ocr.raw.tel || "-"} />
        <DbgRow label="OCR 정규화값" value={ocr.normalized.tel || "-"} />
      </DbgBlock>

      <DbgBlock title="총합계금액 (OCR 전용)">
        <DbgRow label="후보 라인"
          value={amountCandidates.length
            ? amountCandidates.slice(0, 6).map((c) => `${c.amounts.join("/")}  ← "${c.line.slice(0, 40)}"`).join(" | ")
            : "-"} />
        <DbgRow label="OCR 필드값" value={ocr.raw.총합계금액 || "-"} />
        <DbgRow label="OCR 정규화값" value={ocr.normalized.총합계금액 || "-"} />
        <DbgRow label="선택 이유" value={"키워드(합계/총액/total 등) 우선 → 없으면 하단 50% 최대값"} />
      </DbgBlock>

      <DbgBlock title="자동복원">
        {!autofill || autofill.suggestions.length === 0
          ? <DbgRow label="제안" value="없음" />
          : autofill.suggestions.map((s, i) => (
              <div key={i} style={{ padding: "4px 0", borderTop: i > 0 ? "1px dashed rgba(255,255,255,0.06)" : undefined }}>
                <DbgRow label="source" value={s.source === "biz" ? "사업자번호 매칭" : "텍스트 유사도"} />
                <DbgRow label="matched_from" value={s.matchedFrom} />
                <DbgRow label="confidence" value={`${Math.round(s.confidence * 100)}%`} />
                <DbgRow label="auto-apply 가능" value={s.source === "biz" && s.confidence >= BIZ_AUTO_APPLY_CONFIDENCE ? "예" : "아니오"} />
                <DbgRow label="적용됨" value={autofill.appliedSource === s.source ? "예" : "아니오"} />
                {s.reasons && s.reasons.length > 0 && (
                  <DbgRow label="reasons" value={s.reasons.map((r) => `${r.code}(${r.delta >= 0 ? "+" : ""}${r.delta.toFixed(2)}): ${r.note}`).join(" | ")} />
                )}
              </div>
            ))}
        {autofill?.appliedAt && <DbgRow label="적용 시각" value={autofill.appliedAt} />}
      </DbgBlock>

      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.35)", fontStyle: "italic" }}>
        * 자동복원 적용은 세션 + autofill_cache.json 에만 기록되며 ground_truth.json 은 절대 변경되지 않습니다.
        * 사람이 “기준값으로 확정” 버튼을 눌러야 ground_truth 에 반영됩니다.
      </div>
    </div>
  );
}

function DbgBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "var(--panel2)", borderRadius: 6, padding: "8px 10px" }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: "var(--accent)", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.6 }}>{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>{children}</div>
    </div>
  );
}

function DbgRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: 8, fontSize: 11 }}>
      <span style={{ color: "var(--muted)" }}>{label}</span>
      <span style={{ color: "var(--text)", wordBreak: "break-all" }}>{value}</span>
    </div>
  );
}

// ============================================================
// FieldCard — 필드 1개를 카드로 표시
//   ▎기준값 / ▎OCR / ▎자동복원 / ━ 채택값  의 수직 스택
//   각 슬롯 좌측에 고정 라벨 + 컬러 바
//   카드 헤더 우측에 유사도 칩 + source 칩 (고정 위치)
// ============================================================
function FieldCard({
  fieldKey, label, allowAutofill, view, viewMode, hasOcr,
  bizStatusText, bizStatusColor, isAmount,
  matchResult,
  matchStatus,
  onGtChange, onCommit,
}: {
  fieldKey: FieldKey;
  label: string;
  allowAutofill: boolean;
  view: import("./core/types").FieldView;
  viewMode: ViewMode;
  hasOcr: boolean;
  bizStatusText?: string;
  bizStatusColor?: string;
  isAmount: boolean;
  matchResult: MatchResult;
  matchStatus: MatchStatus;
  onGtChange: (v: string) => void;
  onCommit: () => void;
}) {
  const src = sourceLabel(view.finalSource);
  const isGtOnly = view.finalSource === "gt_only";
  const isEmpty = view.finalSource === "empty";
  const showOcr      = viewMode !== "gt_edit";
  const showNorm     = viewMode !== "gt_edit" && viewMode !== "ocr_only";
  const showAutofill = viewMode !== "ocr_only" && viewMode !== "gt_edit";

  // 채택값 섹션 강조색 (source별)
  const emphasisBg =
    view.finalSource === "user_confirmed"             ? "rgba(34,197,94,0.12)" :
    view.finalSource === "gt_similarity"              ? "rgba(22,163,74,0.13)" :
    view.finalSource === "gt_anchor_empty"            ? "rgba(21,128,61,0.13)" :
    view.finalSource === "gt_anchor_weak_value"       ? "rgba(22,101,52,0.13)" :
    view.finalSource === "gt_anchor_override"         ? "rgba(20,83,45,0.13)" :
    view.finalSource === "autofill_biz"               ? "rgba(99,102,241,0.13)" :
    view.finalSource === "autofill_text_suggestion"   ? "rgba(168,85,247,0.13)" :
    view.finalSource === "ocr_normalized"             ? "rgba(14,165,233,0.10)" :
    view.finalSource === "ocr"                        ? "rgba(148,163,184,0.10)" :
    view.finalSource === "gt_only"                    ? "rgba(245,158,11,0.10)" :
                                                        "rgba(255,255,255,0.03)";
  const emphasisBorder =
    view.finalSource === "user_confirmed"             ? "rgba(34,197,94,0.4)" :
    view.finalSource === "gt_similarity"              ? "rgba(22,163,74,0.45)" :
    view.finalSource === "gt_anchor_empty"            ? "rgba(21,128,61,0.45)" :
    view.finalSource === "gt_anchor_weak_value"       ? "rgba(22,101,52,0.45)" :
    view.finalSource === "gt_anchor_override"         ? "rgba(20,83,45,0.45)" :
    view.finalSource === "autofill_biz"               ? "rgba(99,102,241,0.4)" :
    view.finalSource === "autofill_text_suggestion"   ? "rgba(168,85,247,0.4)" :
    view.finalSource === "ocr_normalized"             ? "rgba(14,165,233,0.35)" :
    view.finalSource === "ocr"                        ? "rgba(148,163,184,0.35)" :
    view.finalSource === "gt_only"                    ? "rgba(245,158,11,0.45)" :
                                                        "rgba(255,255,255,0.1)";

  return (
    <div style={{
      background: "var(--panel)", borderRadius: 10,
      boxShadow: "var(--shadowSoft)", overflow: "hidden",
      border: `1px solid ${
        !hasOcr
          ? "rgba(255,255,255,0.05)"
          : matchResult.hasBoth
            ? (matchResult.ok ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)")
            : "rgba(255,255,255,0.05)"
      }`,
    }}>
      {/* 헤더: 필드명 + 배지 | 유사도 + source */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "7px 12px",
        background: "var(--panel2)",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 800, color: "var(--text)" }}>{label}</span>
          {fieldKey === "사업자번호" && bizStatusText && (
            <span style={{ fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 999, color: "#fff", background: bizStatusColor }}>
              {bizStatusText}
            </span>
          )}
          {isAmount && (
            <span title="금액은 OCR 결과 기준으로만 유지됩니다 (autofill 제외)"
              style={{ fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 4, color: "#fff", background: "#0ea5e9" }}>
              OCR 기준
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {!hasOcr ? (
            <span style={{
              fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 999,
              color: "rgba(255,255,255,0.55)", background: "rgba(255,255,255,0.06)",
              border: "1px dashed rgba(255,255,255,0.2)", whiteSpace: "nowrap",
            }}>OCR 미실행</span>
          ) : (
            <>
              {(() => {
                const meta = matchStatusMeta(matchStatus);
                return (
                  <span title={meta.title} style={{
                    display: "inline-flex", alignItems: "center", justifyContent: "center",
                    width: 22, height: 22, borderRadius: 999,
                    fontSize: 12, fontWeight: 800, color: "#fff",
                    background: matchStatus === "exact" ? "#22c55e"
                              : matchStatus === "policy" ? "#f59e0b"
                              : matchStatus === "mismatch" ? "#ef4444"
                              : "rgba(255,255,255,0.18)",
                  }}>{meta.symbol}</span>
                );
              })()}
              {!matchResult.hasBoth ? (
                <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", whiteSpace: "nowrap" }}>유사도 —</span>
              ) : (
                <span style={{
                  fontSize: 10, fontWeight: 800, padding: "2px 7px", borderRadius: 999, color: "#fff",
                  background: matchResult.ok ? "#22c55e" : matchResult.score >= 0.3 ? "#f59e0b" : "#ef4444",
                  whiteSpace: "nowrap",
                }}>유사도 {Math.round(matchResult.score * 100)}%</span>
              )}
              {(view.finalValue || isGtOnly || isEmpty) && (
                <span title={src.title} style={{
                  fontSize: 9, fontWeight: 800, padding: "2px 7px", borderRadius: 4,
                  color: "#fff", background: src.color, whiteSpace: "nowrap",
                }}>{src.label}</span>
              )}
            </>
          )}
        </div>
      </div>

      {/* 기준값 슬롯 */}
      <FieldSlot color="#22c55e" label="기준값">
        <input
          type="text"
          value={view.gt}
          onChange={(e) => onGtChange(e.target.value)}
          placeholder="사람이 확정한 기준값을 직접 입력"
          style={{
            ...styles.gtInput,
            background: view.gt ? "rgba(34,197,94,0.06)" : "var(--panel2)",
            borderColor: view.gt ? "rgba(34,197,94,0.3)" : "rgba(255,255,255,0.07)",
          }}
        />
      </FieldSlot>

      {/* OCR 슬롯 (원본 + 정규화) */}
      {showOcr && (
        <FieldSlot color="#94a3b8" label="OCR">
          <div style={{ display: "grid", gridTemplateColumns: "68px 1fr", rowGap: 3, columnGap: 8 }}>
            <span style={{ fontSize: 9, fontWeight: 800, color: "#94a3b8", letterSpacing: 0.5, textTransform: "uppercase" }}>원본</span>
            <span style={{ fontSize: 12, color: view.ocrRaw ? "var(--text)" : "rgba(255,255,255,0.25)", wordBreak: "break-all" }}>{view.ocrRaw || "—"}</span>
            {showNorm && (<>
              <span style={{ fontSize: 9, fontWeight: 800, color: "#0ea5e9", letterSpacing: 0.5, textTransform: "uppercase" }}>정규화</span>
              <span style={{ fontSize: 12, color: view.ocrNormalized ? "var(--text)" : "rgba(255,255,255,0.25)", wordBreak: "break-all" }}>{view.ocrNormalized || "—"}</span>
            </>)}
          </div>
        </FieldSlot>
      )}

      {/* 자동복원 슬롯 */}
      {showAutofill && (
        <FieldSlot
          color={!allowAutofill ? "#475569" : view.autofillSource === "text" ? "#a855f7" : "#6366f1"}
          label="자동복원"
        >
          {!allowAutofill ? (
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.35)", fontStyle: "italic" }}>
              (이 필드는 autofill 제외 · OCR 결과만 유지)
            </span>
          ) : view.autofillValue ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ fontSize: 12, color: "var(--text)", wordBreak: "break-all" }}>{view.autofillValue}</span>
              <span style={{
                fontSize: 9, fontWeight: 800, padding: "1px 6px", borderRadius: 4, color: "#fff",
                background: view.autofillSource === "biz" ? "#6366f1" : "#a855f7",
              }}>
                {view.autofillSource === "biz" ? "사업자" : "유사"} · {Math.round(view.autofillConfidence * 100)}%
              </span>
              {view.autofillMatchedFrom && (
                <span style={{ fontSize: 10, color: "var(--muted)" }}>from {view.autofillMatchedFrom}</span>
              )}
              {view.autofillApplied && (
                <span style={{ fontSize: 10, color: "#22c55e", fontWeight: 800 }}>✓ 적용됨</span>
              )}
            </div>
          ) : (
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.25)" }}>제안 없음</span>
          )}
        </FieldSlot>
      )}

      {/* 채택값 슬롯 (강조) */}
      <FieldSlot color={hasOcr ? src.color : "rgba(255,255,255,0.2)"} label="채택값" emphasis>
        <div style={{
          display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
          padding: "8px 10px",
          background: hasOcr ? emphasisBg : "rgba(255,255,255,0.02)",
          border: `1px ${hasOcr ? "solid" : "dashed"} ${hasOcr ? emphasisBorder : "rgba(255,255,255,0.12)"}`,
          borderRadius: 6,
        }}>
          {!hasOcr ? (
            <span style={{
              fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.45)",
              fontStyle: "italic", flex: 1,
            }}>
              OCR 미실행 · Run OCR 실행 후 채택값이 결정됩니다
            </span>
          ) : (
            <>
              <span title={src.title} style={{
                fontSize: 10, fontWeight: 900, padding: "3px 8px", borderRadius: 999,
                color: "#fff", background: src.color, whiteSpace: "nowrap",
              }}>{src.label}</span>
              <span style={{
                fontSize: 15, fontWeight: 800,
                color: view.finalValue
                  ? "var(--text)"
                  : "rgba(255,255,255,0.25)",
                wordBreak: "break-all", flex: 1, letterSpacing: -0.2,
              }}>{view.finalValue || "—"}</span>
              {isGtOnly && (
                <span style={{ fontSize: 11, color: "#f59e0b", fontWeight: 800 }}>
                  기준값만 존재 · 이번 OCR/AUTO 채택값 아님
                </span>
              )}
              {isEmpty && !view.gt && (
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.38)", fontWeight: 700 }}>
                  OCR/AUTO/GT 모두 없음
                </span>
              )}
              {view.finalReason && (
                <span title={view.finalReason} style={{ fontSize: 10, color: "var(--muted)", fontWeight: 700 }}>
                  {view.finalReason}
                </span>
              )}
              {view.finalValue && view.finalValue !== view.gt && view.finalSource !== "user_confirmed" && (
                <button type="button" onClick={onCommit}
                  title="이 필드만 기준값(ground_truth)에 저장"
                  style={styles.fieldCommitBtn}>↑ 기준값 확정</button>
              )}
            </>
          )}
        </div>
      </FieldSlot>
    </div>
  );
}

function FieldSlot({ color, label, emphasis, children }: { color: string; label: string; emphasis?: boolean; children: React.ReactNode }) {
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "88px 1fr",
      columnGap: 10,
      padding: emphasis ? "10px 14px" : "7px 14px",
      borderTop: emphasis ? "1px solid rgba(255,255,255,0.06)" : undefined,
      alignItems: "center",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
        <span style={{
          display: "inline-block",
          width: 3, height: emphasis ? 22 : 14,
          background: color, borderRadius: 2,
        }} />
        <span style={{
          fontSize: emphasis ? 11 : 10, fontWeight: 800, color,
          letterSpacing: 0.6, textTransform: "uppercase", whiteSpace: "nowrap",
        }}>{label}</span>
      </div>
      <div style={{ minWidth: 0 }}>{children}</div>
    </div>
  );
}

type KpiTone = "green" | "amber" | "red" | "indigo" | "sky" | "neutral";

function KpiChip({ label, value, sub, tone = "neutral", title }: { label: string; value: string; sub?: string; tone?: KpiTone; title?: string }) {
  const toneColors: Record<KpiTone, string> = {
    green: "#22c55e", amber: "#f59e0b", red: "#ef4444",
    indigo: "#6366f1", sky: "#0ea5e9",
    neutral: "rgba(255,255,255,0.55)",
  };
  return (
    <div title={title} style={{ display: "flex", flexDirection: "column", padding: "6px 10px", borderRadius: 8, background: "var(--panel2)", minWidth: 60 }}>
      <span style={{ fontSize: 9, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.4, whiteSpace: "nowrap" }}>{label}</span>
      <span style={{ fontSize: 14, fontWeight: 800, color: toneColors[tone], lineHeight: 1.1 }}>{value}</span>
      {sub && <span style={{ fontSize: 9, color: "var(--muted)", whiteSpace: "nowrap" }}>{sub}</span>}
    </div>
  );
}

function TopStatChip({ label, value, sub, tone = "neutral" }: { label: string; value: string; sub?: string; tone?: KpiTone }) {
  const toneColors: Record<KpiTone, string> = {
    green: "#22c55e", amber: "#f59e0b", red: "#ef4444",
    indigo: "#6366f1", sky: "#0ea5e9",
    neutral: "rgba(255,255,255,0.55)",
  };
  return (
    <div style={{
      display: "flex", flexDirection: "column", padding: "3px 8px", borderRadius: 6,
      background: "var(--panel2)", border: "1px solid rgba(255,255,255,0.08)",
    }}>
      <span style={{ fontSize: 9, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.4, whiteSpace: "nowrap" }}>{label}</span>
      <span style={{ fontSize: 11, fontWeight: 800, color: toneColors[tone], lineHeight: 1.2 }}>{value}</span>
      {sub && <span style={{ fontSize: 9, color: "var(--muted)", whiteSpace: "nowrap" }}>{sub}</span>}
    </div>
  );
}

function SourceLegend({ label, color, note }: { label: string; color: string; note: string }) {
  return (
    <span title={note} style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      fontSize: 10, fontWeight: 800, color: "var(--text)",
      padding: "3px 7px", borderRadius: 999,
      background: "var(--panel2)", border: "1px solid rgba(255,255,255,0.08)",
    }}>
      <span style={{ width: 7, height: 7, borderRadius: 999, background: color, display: "inline-block" }} />
      {label}
      <span style={{ color: "var(--muted)", fontWeight: 600 }}>{note}</span>
    </span>
  );
}

function KpiSection({ title, subtitle, tone, icon, children }: { title: string; subtitle?: string; tone: KpiTone; icon?: string; children: React.ReactNode }) {
  const toneColors: Record<KpiTone, string> = {
    green: "#22c55e", amber: "#f59e0b", red: "#ef4444",
    indigo: "#6366f1", sky: "#0ea5e9",
    neutral: "rgba(255,255,255,0.12)",
  };
  const color = toneColors[tone];
  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: 6,
      padding: "8px 12px 10px",
      borderRadius: 12,
      background: "var(--panel)",
      border: `1px solid ${color}30`,
      boxShadow: `inset 3px 0 0 0 ${color}`,
      minWidth: 0, flex: "1 1 0",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {icon && <span style={{ fontSize: 14, color }}>{icon}</span>}
        <span style={{ fontSize: 11, fontWeight: 800, color, textTransform: "uppercase", letterSpacing: 0.6 }}>{title}</span>
        {subtitle && <span style={{ fontSize: 9, color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{subtitle}</span>}
      </div>
      <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 2 }}>{children}</div>
    </div>
  );
}

// ============================================================
// FinanceDetailPanel — finance_profile 선택 시 상세 패널
// ============================================================
const FINANCE_FIELD_META: { key: string; label: string; required: boolean }[] = [
  { key: "bankName",            label: "은행명",        required: true  },
  { key: "transactionDateTime", label: "거래일시",      required: true  },
  { key: "amount",              label: "거래금액",      required: true  },
  { key: "balanceAfter",        label: "거래후잔액",    required: false },
  { key: "accountMasked",       label: "계좌(마스킹)",  required: false },
  { key: "branchOrChannel",     label: "수취인 계좌",   required: false },
  { key: "memo",                label: "수취인명",      required: false },
];

const DOCUMENT_FIELD_LABELS: Record<string, string> = {
  supplierCompany: "공급자 상호",
  supplierBizNumber: "공급자 사업자번호",
  supplierRepresentative: "공급자 대표자",
  supplierAddress: "공급자 주소",
  buyerCompany: "공급받는자 상호",
  buyerBizNumber: "공급받는자 사업자번호",
  buyerRepresentative: "공급받는자 대표자",
  buyerAddress: "공급받는자 주소",
  issueDate: "작성/거래일자",
  supplyAmount: "공급가액",
  taxAmount: "세액",
  totalAmount: "합계금액",
  tableDetected: "품목표 존재",
  rowCount: "행 수",
  firstRowPreview: "첫 행 미리보기",
  subtotal: "소계",
  cumulativeAmount: "누계",
  previousBalance: "전일잔액",
  transactionAmount: "당일거래금액",
  cumulativeBalance: "누계잔액",
  totalQuantity: "총수량",
};

const DOCUMENT_FIELD_SHORT: Record<string, string> = {
  supplierCompany: "공급자",
  supplierBizNumber: "공급자 사업자",
  supplierRepresentative: "공급자 대표",
  supplierAddress: "공급자 주소",
  buyerCompany: "공급받는자",
  buyerBizNumber: "받는자 사업자",
  buyerRepresentative: "받는자 대표",
  buyerAddress: "받는자 주소",
  issueDate: "일자",
  supplyAmount: "공급가",
  taxAmount: "세액",
  totalAmount: "합계",
  tableDetected: "표",
  rowCount: "행",
  firstRowPreview: "첫 행",
  subtotal: "소계",
  cumulativeAmount: "누계",
  previousBalance: "전일잔액",
  transactionAmount: "거래금액",
  cumulativeBalance: "누계잔액",
  totalQuantity: "총수량",
};

const DOCUMENT_FIELD_META: { key: string; label: string; shortLabel: string; required: boolean }[] =
  DOCUMENT_COLUMNS.map((col) => ({
    key: col.key,
    label: DOCUMENT_FIELD_LABELS[col.key] ?? col.key,
    shortLabel: DOCUMENT_FIELD_SHORT[col.key] ?? DOCUMENT_FIELD_LABELS[col.key] ?? col.key,
    required: col.required,
  }));

// finance GT vs OCR 비교용 정규화 — 보수적 최소 정규화
// 너무 공격적인 fuzzy 매칭 금지. 명백히 같은 값을 다른 표기로 입력한 경우만 흡수.
function normalizeFinanceValue(field: string, value: string): string {
  if (!value) return "";
  const trimmed = value.trim();
  if (field === "amount" || field === "balanceAfter") {
    // 콤마/원/₩/공백 제거 → 숫자만
    return trimmed.replace(/[^0-9]/g, "");
  }
  if (field === "transactionDateTime") {
    // 구분자 정규화: '/' '.' → '-' / 다중 공백 → 단일 공백
    return trimmed.replace(/[./]/g, "-").replace(/\s+/g, " ").trim();
  }
  if (field === "branchOrChannel" || field === "accountMasked") {
    // 맨 앞 [xxx] 기관 코드 prefix 제거 (예: [003]480-... → 480-...) + 공백 제거
    // 하이픈은 유지 (계좌 형식 가독성 보존 + GT 입력 패턴과 일치)
    return trimmed.replace(/^\[\d{2,4}\]/, "").replace(/\s+/g, "").toLowerCase();
  }
  // bankName / transactionType / 기타: 공백 제거 + 소문자
  return trimmed.replace(/\s+/g, "").toLowerCase();
}

// 동일 은행의 다른 표기를 단일 canonical name으로 매핑
// 백엔드 finance_slip._BANK_CANONICAL_MAP과 동일한 규칙 (이중 안전장치)
// 변경 시 양쪽을 함께 업데이트해야 함
const BANK_CANONICAL_PATTERNS: { canonical: string; patterns: RegExp[] }[] = [
  { canonical: "IBK기업은행",  patterns: [/IBK\s*기업은행/i, /기업은행/i, /i-?ONE\s*Bank/i, /ibk\.co\.kr/i] },
  { canonical: "KB국민은행",   patterns: [/KB\s*국민은행/i, /국민은행/i, /kbstar(\.com)?/i, /kbstar\.co\.kr/i] },
  { canonical: "신한은행",     patterns: [/신한은행/i, /shinhanbank(\.com)?/i] },
  { canonical: "우리은행",     patterns: [/우리은행/i, /wooribank(\.com)?/i] },
  { canonical: "KEB하나은행",  patterns: [/KEB\s*하나은행/i, /하나은행/i, /hanabank(\.com)?/i] },
  { canonical: "NH농협은행",   patterns: [/NH\s*농협은행/i, /농협은행/i, /nonghyup\.com/i] },
];

// 매치되는 canonical name 반환. 매핑 없으면 null (오인 방지)
function canonicalizeBankName(name: string): string | null {
  if (!name) return null;
  for (const { canonical, patterns } of BANK_CANONICAL_PATTERNS) {
    for (const p of patterns) {
      if (p.test(name)) return canonical;
    }
  }
  return null;
}

// finance 필드 정규화 비교 (캐스케이드)
//   1) raw exact 일치
//   2) 공백/대소문자/구분자 정규화 일치
//   3) bankName 한정: canonical 비교
//   4) bankName 한정: 양방향 substring containment (보수적 fallback)
function financeFieldMatches(field: string, gt: string, ocr: string): boolean {
  if (!gt || !ocr) return false;
  // 1) raw exact
  if (gt === ocr) return true;

  const gtN  = normalizeFinanceValue(field, gt);
  const ocrN = normalizeFinanceValue(field, ocr);
  if (!gtN || !ocrN) return false;
  // 2) 공백/대소문자/구분자 정규화
  if (gtN === ocrN) return true;

  if (field === "bankName") {
    // 3) canonical 비교 (양쪽 모두 매핑되고 결과가 같을 때만)
    const gtC  = canonicalizeBankName(gt);
    const ocrC = canonicalizeBankName(ocr);
    if (gtC && ocrC && gtC === ocrC) return true;
    // 4) substring containment — 마지막 fallback
    return gtN.includes(ocrN) || ocrN.includes(gtN);
  }
  return false;
}

// finance profile 화면 표시용 status (백엔드 internal 문자열과 분리)
//   - 백엔드 raw status는 backwards-compat 위해 유지
//   - 화면 표시 status는 finance Tier-1 추출 품질 + GT 일치 기준으로 재해석
type FinanceStatus = "selected" | "review" | "suppressed";

// raw OCR entry + finance GT를 받아 화면 표시용 finance status 도출
//
// 정책 (보수적):
//   1) 텍스트 붕괴 (EMPTY_TEXT) 또는 bank_slip 외 다른 suppressed_* → suppressed
//   2) Tier-1 4필드 모두 추출 (transactionType ≠ "unknown") AND
//      finance_review_reasons 빈 배열 AND
//      (GT 미입력 OR GT 입력된 필드 전부 정규화 비교 일치) → selected
//   3) 그 외 (Tier-1 partial / review reason / GT mismatch) → review
function deriveFinanceStatus(
  ocrEntry: import("./core/types").OcrEntry | undefined,
  financeGt: Record<string, string> | undefined,
): FinanceStatus {
  if (!ocrEntry) return "review";  // OCR 미실행 — 호출 측에서 hasOcr로 별도 처리

  const rawStatus = ocrEntry.status ?? "";
  const fields    = ocrEntry.financeFields ?? {};
  const reasons   = ocrEntry.financeReviewReasons ?? [];

  // 1) 진짜 suppressed: bank_slip 외 다른 suppression 또는 텍스트 붕괴
  if (rawStatus.startsWith("suppressed_") && rawStatus !== "suppressed_bank_slip") {
    return "suppressed";
  }
  if (reasons.includes("EMPTY_TEXT")) {
    return "suppressed";
  }

  // 2) Tier-1 완전 추출 여부 (transactionType의 "unknown"은 미추출로 간주)
  const tier1Complete = FINANCE_TIER1_FIELDS.every((k) => {
    const v = fields[k] ?? "";
    if (!v) return false;
    if (k === "transactionType" && v === "unknown") return false;
    return true;
  });

  // 3) review reason 존재 여부 (TIER1_PARTIAL / AMOUNT_AMBIGUOUS / DATETIME_FORMAT_UNSTABLE / BANK_NAME_MULTIPLE_CANDIDATES 등)
  const hasReviewReason = reasons.length > 0;

  // 4) GT 비교 — 입력된 필드만 정규화 비교 (financeFieldMatches: canonical / 구분자 / 콤마 흡수)
  let gtMismatch = false;
  if (financeGt) {
    for (const k of FINANCE_TIER1_FIELDS) {
      const gtVal  = financeGt[k] ?? "";
      const ocrVal = fields[k]    ?? "";
      if (gtVal) {
        if (!ocrVal || !financeFieldMatches(k, gtVal, ocrVal)) {
          gtMismatch = true;
          break;
        }
      }
    }
  }

  if (tier1Complete && !hasReviewReason && !gtMismatch) return "selected";
  return "review";
}

// derived FinanceStatus → 표시 라벨/배경색
function getFinanceStatusMetaFromDerived(s: FinanceStatus, hasOcr: boolean): { label: string; bg: string } {
  if (!hasOcr)              return { label: "미실행",     bg: "#475569" };
  if (s === "selected")     return { label: "selected",  bg: "#16a34a" };
  if (s === "review")       return { label: "review",    bg: "#d97706" };
  if (s === "suppressed")   return { label: "suppressed", bg: "#dc2626" };
  return { label: s, bg: "#6b7280" };
}

const REVIEW_REASON_LABELS: Record<string, string> = {
  TIER1_PARTIAL:                "Tier-1 일부 미추출",
  AMOUNT_AMBIGUOUS:             "거래금액·잔액 충돌",
  AMOUNT_ANCHOR_NOT_FOUND:      "거래금액 anchor 없음",
  DATETIME_FORMAT_UNSTABLE:     "날짜/시각 불완전",
  DATETIME_NOT_FOUND:           "날짜 미탐지",
  BANK_NAME_MULTIPLE_CANDIDATES:"은행명 복수 후보",
  TRANSACTION_TYPE_AMBIGUOUS:   "거래유형 모호",
  TRANSACTION_TYPE_NOT_FOUND:   "거래유형 미탐지",
  EMPTY_TEXT:                   "OCR 텍스트 없음",
};

// FinanceFieldCard — finance 필드 1개를 FieldCard와 동일한 구조로 표시
//   ▎기준값(편집 가능) / ▎OCR / ▎자동복원 / ━ 채택값  의 수직 스택
//   자동복원은 finance autofill 미구현 단계이므로 placeholder 표시
function FinanceFieldCard({
  fieldKey,
  label,
  isTier1,
  value,
  hasOcr,
  gtValue,
  onGtChange,
}: {
  fieldKey: string;
  label: string;
  isTier1: boolean;
  value: string;
  hasOcr: boolean;
  gtValue: string;
  onGtChange: (v: string) => void;
}) {
  const hasValue      = value !== "";
  const hasGt         = gtValue !== "";
  const normalizedVal = hasValue ? normalizeFinanceValue(fieldKey, value) : "";
  const displayVal    = hasValue ? displayFinanceValue(fieldKey, value) : "";

  // 상태 아이콘 — financeMatchStatus 기반으로 배치 테이블과 동일 기준 적용
  //   GT 있음: financeMatchStatus 결과 (O/△/X) 직접 사용
  //   GT 없음: 추출 여부 기준 (O=추출됨 / X=Tier-1 미추출 / —=Tier-2 미추출)
  const ms = (hasGt && hasValue) ? financeMatchStatus(fieldKey, gtValue, value)
           : (hasGt && !hasValue) ? "X"
           : null;  // no GT

  const statusSymbol =
    ms === "O"  ? "O"  :
    ms === "△"  ? "△"  :
    ms === "X"  ? "X"  :
    ms === null ? (hasValue ? "O" : isTier1 ? "X" : "—")
    : "X";
  const statusBg =
    statusSymbol === "O"  ? "#22c55e" :
    statusSymbol === "△"  ? "#f59e0b" :
    statusSymbol === "X"  ? "#ef4444" :
                            "rgba(255,255,255,0.18)";
  const statusTitle =
    ms === "O"  ? "기준값과 일치 (정규화 동일 포함)" :
    ms === "△"  ? "canonical/유사 일치 (은행명 변형 등)" :
    ms === "X"  ? (hasValue ? "기준값과 불일치" : "OCR 미추출") :
    hasValue    ? "정상 추출됨 (기준값 없음)" :
    isTier1     ? "필수 필드(Tier-1) 미추출" :
                  "선택 필드(Tier-2) 미추출";

  // gtMatch: 채택값 테두리 색 등 기타 용도 (O 또는 △ 이면 "일치 계열")
  const gtMatch = statusSymbol === "O" || statusSymbol === "△";

  // 채택값 슬롯 강조색 (finance 전용 — receipt의 source 기반 색과 별개)
  const emphasisBg     = hasValue ? "rgba(220,38,38,0.10)" : "rgba(255,255,255,0.03)";
  const emphasisBorder = hasValue ? "rgba(220,38,38,0.35)" : "rgba(255,255,255,0.12)";
  const finalSrcColor  = hasValue ? "#dc2626" : "#64748b";
  const finalSrcLabel  = hasValue ? "OCR" : "EMPTY";

  return (
    <div style={{
      background: "var(--panel)", borderRadius: 10,
      boxShadow: "var(--shadowSoft)", overflow: "hidden",
      border: `1px solid ${
        !hasOcr   ? "rgba(255,255,255,0.05)" :
        hasValue  ? "rgba(220,38,38,0.25)"   :
                    "rgba(255,255,255,0.05)"
      }`,
    }}>
      {/* 헤더: 필드명 + Tier 배지 | 상태 아이콘 */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "7px 12px",
        background: "var(--panel2)",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 800, color: "var(--text)" }}>{label}</span>
          <span style={{
            fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 4,
            color: "#fff", background: isTier1 ? "#dc2626" : "#475569",
          }}>
            {isTier1 ? "Tier-1" : "Tier-2"}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {!hasOcr ? (
            <span style={{
              fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 999,
              color: "rgba(255,255,255,0.55)", background: "rgba(255,255,255,0.06)",
              border: "1px dashed rgba(255,255,255,0.2)", whiteSpace: "nowrap",
            }}>OCR 미실행</span>
          ) : (
            <span title={statusTitle} style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              width: 22, height: 22, borderRadius: 999,
              fontSize: 12, fontWeight: 800, color: "#fff",
              background: statusBg,
            }}>{statusSymbol}</span>
          )}
        </div>
      </div>

      {/* 기준값 슬롯 — 직접 입력 가능 (receipt FieldCard와 동일 방식) */}
      <FieldSlot color="#22c55e" label="기준값">
        <input
          type="text"
          value={gtValue}
          onChange={(e) => onGtChange(e.target.value)}
          placeholder="사람이 확정한 기준값을 직접 입력"
          style={{
            ...styles.gtInput,
            background: hasGt ? "rgba(34,197,94,0.06)" : "var(--panel2)",
            borderColor: hasGt ? "rgba(34,197,94,0.3)" : "rgba(255,255,255,0.07)",
          }}
        />
      </FieldSlot>

      {/* OCR 슬롯 (원본 + 정규화) */}
      <FieldSlot color="#94a3b8" label="OCR">
        <div style={{ display: "grid", gridTemplateColumns: "68px 1fr", rowGap: 3, columnGap: 8 }}>
          <span style={{ fontSize: 9, fontWeight: 800, color: "#94a3b8", letterSpacing: 0.5, textTransform: "uppercase" }}>원본</span>
          <span style={{
            fontSize: 12, wordBreak: "break-all",
            color: hasValue ? "var(--text)" : (hasOcr ? "#ef4444" : "rgba(255,255,255,0.25)"),
            fontWeight: (!hasValue && hasOcr && isTier1) ? 700 : undefined,
          }}>
            {hasValue ? value : (hasOcr ? "미추출" : "—")}
          </span>
          <span style={{ fontSize: 9, fontWeight: 800, color: "#0ea5e9", letterSpacing: 0.5, textTransform: "uppercase" }}>정규화</span>
          <span style={{ fontSize: 12, color: normalizedVal ? "#93c5fd" : "rgba(255,255,255,0.18)", wordBreak: "break-all" }}>
            {normalizedVal || "—"}
          </span>
        </div>
      </FieldSlot>

      {/* 자동복원 슬롯 */}
      <FieldSlot color="#475569" label="자동복원">
        <span style={{ fontSize: 11, color: "rgba(255,255,255,0.28)", fontStyle: "italic" }}>
          제안 없음
        </span>
      </FieldSlot>

      {/* 채택값 슬롯 (강조) */}
      <FieldSlot color={hasOcr ? finalSrcColor : "rgba(255,255,255,0.2)"} label="채택값" emphasis>
        <div style={{
          display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
          padding: "8px 10px",
          background: hasOcr ? emphasisBg : "rgba(255,255,255,0.02)",
          border: `1px ${hasOcr ? "solid" : "dashed"} ${hasOcr ? emphasisBorder : "rgba(255,255,255,0.12)"}`,
          borderRadius: 6,
        }}>
          {!hasOcr ? (
            <span style={{
              fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.45)",
              fontStyle: "italic", flex: 1,
            }}>
              OCR 미실행 · Run OCR 실행 후 채택값이 결정됩니다
            </span>
          ) : (
            <>
              <span style={{
                fontSize: 10, fontWeight: 900, padding: "3px 8px", borderRadius: 999,
                color: "#fff", background: finalSrcColor, whiteSpace: "nowrap",
              }}>{finalSrcLabel}</span>
              <span style={{
                fontSize: 15, fontWeight: 800,
                color: hasValue ? "var(--text)" : "rgba(255,255,255,0.25)",
                wordBreak: "break-all", flex: 1, letterSpacing: -0.2,
              }}>{displayVal || value || "—"}</span>
              {!hasValue && isTier1 && (
                <span style={{ fontSize: 11, color: "#ef4444", fontWeight: 800 }}>
                  Tier-1 미추출 · review
                </span>
              )}
            </>
          )}
        </div>
      </FieldSlot>
    </div>
  );
}

function FinanceDetailPanel({
  financeFields,
  reviewReasons,
  hasOcr,
  financeGt,
  onFinanceGtChange,
  derivedStatus,
}: {
  financeFields: Record<string, string> | null;
  reviewReasons: string[];
  hasOcr: boolean;
  financeGt: Record<string, string>;
  onFinanceGtChange: (field: string, value: string) => void;
  derivedStatus?: FinanceStatus;
}) {
  const hasData = financeFields !== null;
  const statusMeta = derivedStatus
    ? getFinanceStatusMetaFromDerived(derivedStatus, hasOcr)
    : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {/* finance profile 안내 헤더 */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "6px 12px", borderRadius: 8,
        background: "rgba(220,38,38,0.08)", border: "1px solid rgba(220,38,38,0.2)",
      }}>
        <span style={{ fontSize: 10, fontWeight: 800, color: "#dc2626", letterSpacing: 0.5 }}>
          🏦 FINANCE PROFILE
        </span>
        {/* derived 화면 표시 status 배지 */}
        {hasOcr && statusMeta && (
          <span
            title="finance Tier-1 추출 + GT 비교 기준 화면 status (백엔드 raw status는 별도)"
            style={{
              fontSize: 10, fontWeight: 800, padding: "2px 8px", borderRadius: 999,
              color: "#fff", background: statusMeta.bg, whiteSpace: "nowrap",
            }}
          >
            {statusMeta.label}
          </span>
        )}
        {!hasOcr && (
          <span style={{ fontSize: 10, color: "var(--muted)" }}>OCR 미실행 — 실행 후 Tier-1 값 표시 · 기준값은 미리 입력 가능</span>
        )}
        {hasOcr && !hasData && (
          <span style={{ fontSize: 10, color: "var(--muted)" }}>finance_fields 없음 (OCR 재실행 필요)</span>
        )}
        {hasOcr && hasData && reviewReasons.length > 0 && (
          <span style={{ fontSize: 10, color: "#d97706" }}>
            review: {reviewReasons.map((r) => REVIEW_REASON_LABELS[r] ?? r).join(" · ")}
          </span>
        )}
      </div>

      {/* 필드별 FieldCard 동일 구조 (기준값 편집 가능) */}
      {FINANCE_FIELD_META.map(({ key, label, required }) => (
        <FinanceFieldCard
          key={key}
          fieldKey={key}
          label={label}
          isTier1={required}
          value={financeFields?.[key] ?? ""}
          hasOcr={hasOcr}
          gtValue={financeGt[key] ?? ""}
          onGtChange={(v) => onFinanceGtChange(key, v)}
        />
      ))}
    </div>
  );
}

function DocumentDetailPanel({
  documentFields,
  normalization,
  invoiceDebug,
  hasOcr,
  documentGt,
  onDocumentGtChange,
  invoiceProfile,
}: {
  documentFields: Record<string, string> | null;
  normalization: InvoiceNormalization | null;
  invoiceDebug: Record<string, unknown> | null;
  hasOcr: boolean;
  documentGt: Record<string, string>;
  onDocumentGtChange: (field: string, value: string) => void;
  invoiceProfile?: InvoiceProfile;
}) {
  const amtLabel = getAmountProfileLabel(invoiceProfile?.amountProfile);
  const partyLabel = getPartyProfileLabel(invoiceProfile?.partyProfile);
  const tableLabel = getTableProfileLabel(invoiceProfile?.tableProfile);
  const amtNoAmount = invoiceProfile?.amountProfile === "no_amount_summary" || invoiceProfile?.amountProfile === "quantity_total_only";
  const summaryFieldEntries = invoiceProfile?.summaryFields ? Object.entries(invoiceProfile.summaryFields) : [];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
        padding: "6px 12px", borderRadius: 8,
        background: "rgba(202,138,4,0.08)", border: "1px solid rgba(202,138,4,0.24)",
      }}>
        <span style={{ fontSize: 10, fontWeight: 800, color: "#facc15", letterSpacing: 0.5 }}>
          DOCUMENT PROFILE · invoice_statement
        </span>
        {!hasOcr && (
          <span style={{ fontSize: 10, color: "var(--muted)" }}>OCR 미실행 · GT 선입력 가능</span>
        )}
      </div>
      {invoiceProfile && (
        <div style={{
          display: "flex", flexWrap: "wrap", gap: 6,
          padding: "6px 12px", borderRadius: 8,
          background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
        }}>
          <span style={{ fontSize: 9, fontWeight: 800, color: "var(--muted)", alignSelf: "center", marginRight: 2 }}>PROFILE</span>
          <span style={{ fontSize: 10, padding: "2px 7px", borderRadius: 4, background: amtNoAmount ? "#7c3aed" : "#0369a1", color: "#fff", fontWeight: 700 }}
            title={`amountProfile: ${invoiceProfile.amountProfile ?? "—"}`}>
            Amount: {amtLabel}
          </span>
          <span style={{ fontSize: 10, padding: "2px 7px", borderRadius: 4, background: "#374151", color: "#d1d5db", fontWeight: 700 }}
            title={`partyProfile: ${invoiceProfile.partyProfile ?? "—"}`}>
            Party: {partyLabel}
          </span>
          <span style={{ fontSize: 10, padding: "2px 7px", borderRadius: 4, background: "#374151", color: "#d1d5db", fontWeight: 700 }}
            title={`tableProfile: ${invoiceProfile.tableProfile ?? "—"}`}>
            Table: {tableLabel}
          </span>
          {invoiceProfile.invoiceSubType && (
            <span style={{ fontSize: 9, padding: "2px 6px", borderRadius: 4, background: "rgba(255,255,255,0.06)", color: "var(--muted)", fontWeight: 600 }}
              title={`invoiceSubType: ${invoiceProfile.invoiceSubType}`}>
              {invoiceProfile.invoiceSubType.replace(/_statement$/, "").replace(/_/g, "/")}
            </span>
          )}
          {summaryFieldEntries.length > 0 && (
            <span style={{ fontSize: 9, padding: "2px 6px", borderRadius: 4, background: "rgba(245,158,11,0.12)", color: "#fbbf24", fontWeight: 600 }}
              title={summaryFieldEntries.map(([k, v]) => `${k}: ${v.label}`).join(", ")}>
              Summary: {summaryFieldEntries.map(([, v]) => v.label).join(" / ")}
            </span>
          )}
          {amtNoAmount && (
            <span style={{ fontSize: 9, color: "#a78bfa", fontWeight: 600, alignSelf: "center" }}>
              ※ 공급가/세액/합계 — 은 이 문서 유형 특성
            </span>
          )}
        </div>
      )}

      {DOCUMENT_FIELD_META.map(({ key, label, required }) => (
        <DocumentFieldCard
          key={key}
          fieldKey={key}
          label={label}
          required={required}
          value={documentFields?.[key] ?? ""}
          normalization={normalization}
          invoiceDebug={invoiceDebug}
          hasOcr={hasOcr}
          gtValue={documentGt[key] ?? ""}
          onGtChange={(v) => onDocumentGtChange(key, v)}
        />
      ))}
    </div>
  );
}

function DocumentFieldCard({
  fieldKey,
  label,
  required,
  value,
  normalization,
  invoiceDebug,
  hasOcr,
  gtValue,
  onGtChange,
}: {
  fieldKey: string;
  label: string;
  required: boolean;
  value: string;
  normalization: InvoiceNormalization | null;
  invoiceDebug: Record<string, unknown> | null;
  hasOcr: boolean;
  gtValue: string;
  onGtChange: (v: string) => void;
}) {
  const hasValue = value !== "";
  const hasGt = gtValue !== "";
  const status = documentMatchStatus(gtValue, value);
  const meta = documentMatchMeta(status);
  const normalizationRecord = getNormalizationRecord(normalization, fieldKey);
  const normalizedValue = getNormalizedFieldValue(normalization, fieldKey);
  const normalizationRules = normalizationRecord?.appliedRules ?? [];
  const fieldType = normalizationRecord?.fieldType ?? "";
  const addrPartialStatus = normalizationRecord?.addressSimilarityAnalysis?.addressSimilarityStatus ?? "";
  const showNormalization = Boolean(
    hasOcr &&
    (normalizationRules.length > 0 || (normalizedValue && normalizedValue !== value))
  );
  const normalizedStatus = showNormalization
    ? computeNormalizedAuxStatus({ normalizedValue, gtValue, fieldType, rules: normalizationRules })
    : "—";
  const hasDebugOnlyRule = normalizationRules.some((rule) => /debug_only|low/i.test(rule.confidence ?? ""));
  const ruleNames = normalizationRules.map((rule) => rule.rule).filter(Boolean).join(", ");
  const summaryTotalRisk = getSummaryTotalRisk(invoiceDebug, fieldKey, value);
  const statusSymbol = hasGt ? meta.symbol : (hasValue ? "O" : required ? "X" : "—");
  const statusBg =
    statusSymbol === "O" ? "#22c55e" :
    statusSymbol === "△" ? "#f59e0b" :
    statusSymbol === "X" ? "#ef4444" :
    "rgba(255,255,255,0.18)";

  // 채택값 결정 — baseline 패턴: GT vs OCR 비교로 source/value 선택
  //   OCR 미실행                              → empty
  //   GT 없음 + OCR 없음                       → empty
  //   GT 없음 + OCR 있음                       → OCR (source=ocr)
  //   GT 있음 + OCR 없음                       → GT  (source=gt_anchor_empty: 확정값 채택)
  //   둘 다 있음 · O(정규화 일치)              → OCR (source=ocr)
  //   둘 다 있음 · △(부분/유사 일치)           → GT  (source=gt_similarity: 확정값 우선)
  //   둘 다 있음 · X(불일치)                   → OCR (source=ocr · 불일치 표시)
  const finalView = (() => {
    if (!hasOcr)              return { value: "",       source: "empty"            as const, reason: "OCR 미실행" };
    if (!hasGt && !hasValue)  return { value: "",       source: "empty"            as const, reason: required ? "Tier-1 미추출" : "값 없음" };
    if (!hasGt && hasValue)   return { value: value,    source: "ocr"              as const, reason: "OCR 결과 채택" };
    if (hasGt && !hasValue)   return { value: gtValue,  source: "gt_anchor_empty"  as const, reason: "OCR 공란 → GT 채택" };
    // both
    if (status === "O")       return { value: value,    source: "ocr"              as const, reason: "OCR=GT 정규화 일치" };
    if (status === "△")       return { value: gtValue,  source: "gt_similarity"    as const, reason: "GT/OCR 부분일치 · GT 우선 채택" };
    return                           { value: value,    source: "ocr"              as const, reason: "GT 불일치 · OCR 결과 채택" };
  })();

  const srcMeta: Record<typeof finalView.source, { label: string; color: string; bg: string; border: string }> = {
    empty:            { label: "EMPTY",            color: "#64748b", bg: "rgba(255,255,255,0.03)", border: "rgba(255,255,255,0.12)" },
    ocr:              { label: "OCR",              color: "#0ea5e9", bg: "rgba(14,165,233,0.10)",  border: "rgba(14,165,233,0.35)" },
    gt_anchor_empty:  { label: "GT_ANCHOR_EMPTY",  color: "#15803d", bg: "rgba(21,128,61,0.13)",   border: "rgba(21,128,61,0.45)" },
    gt_similarity:    { label: "GT_SIMILARITY",    color: "#16a34a", bg: "rgba(22,163,74,0.13)",   border: "rgba(22,163,74,0.45)" },
  };
  const fSrc = srcMeta[finalView.source];
  const isGtAdopted = finalView.source === "gt_similarity" || finalView.source === "gt_anchor_empty";

  return (
    <div style={{
      background: "var(--panel)", borderRadius: 10,
      boxShadow: "var(--shadowSoft)", overflow: "hidden",
      border: `1px solid ${hasValue ? "rgba(202,138,4,0.28)" : "rgba(255,255,255,0.05)"}`,
    }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "7px 12px",
        background: "var(--panel2)",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 13, fontWeight: 800, color: "var(--text)" }}>{label}</span>
          <span style={{
            fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 4,
            color: "#fff", background: required ? "#ca8a04" : "#475569",
          }}>
            {required ? "Tier-1" : "optional"}
          </span>
        </div>
        <span title={meta.title} style={{
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          width: 22, height: 22, borderRadius: 999,
          fontSize: 12, fontWeight: 800, color: "#fff",
          background: statusBg,
        }}>{statusSymbol}</span>
      </div>

      <FieldSlot color="#22c55e" label="GT">
        <input
          type="text"
          value={gtValue}
          onChange={(e) => onGtChange(e.target.value)}
          placeholder="거래명세서 기준값 입력"
          style={{
            ...styles.gtInput,
            background: hasGt ? "rgba(34,197,94,0.06)" : "var(--panel2)",
            borderColor: hasGt ? "rgba(34,197,94,0.3)" : "rgba(255,255,255,0.07)",
          }}
        />
      </FieldSlot>

      <FieldSlot color="#94a3b8" label="OCR">
        <span style={{
          fontSize: 12,
          color: hasValue ? "var(--text)" : (hasOcr ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.22)"),
          fontWeight: hasValue ? 700 : 500,
          wordBreak: "break-all",
        }}>
          {hasValue ? value : (hasOcr ? "미추출" : "—")}
        </span>
      </FieldSlot>

      {/* 채택값 슬롯 (강조) — GT vs OCR 비교 결과로 source/value 결정 (baseline 패턴) */}
      {showNormalization && (
        <FieldSlot color={normalizedStatusColor(normalizedStatus)} label="NORM">
          <div style={{ display: "flex", flexDirection: "column", gap: 5, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
              <span style={{
                fontSize: 12,
                color: normalizedValue ? "var(--text)" : "rgba(255,255,255,0.35)",
                fontWeight: 700,
                wordBreak: "break-all",
              }}>
                {normalizedValue || "—"}
              </span>
              <span title="기존 exact O/X는 유지하고 normalized 후보 기준 보조 상태만 표시합니다." style={{
                fontSize: 9, fontWeight: 900, padding: "2px 7px", borderRadius: 999,
                color: "#fff", background: normalizedStatusColor(normalizedStatus), whiteSpace: "nowrap",
              }}>
                {normalizedStatusLabel(normalizedStatus)}
              </span>
              {normalizedValue && normalizedValue !== value && (
                <span style={{
                  fontSize: 9, fontWeight: 800, padding: "2px 7px", borderRadius: 999,
                  color: "#bae6fd", background: "rgba(14,165,233,0.15)",
                  border: "1px solid rgba(14,165,233,0.25)", whiteSpace: "nowrap",
                }}>정규화 후보</span>
              )}
              {addrPartialStatus && addrPartialStatus !== "complete" && (
                <span title={normalizationRecord?.addressSimilarityAnalysis?.partialReason ?? ""} style={{
                  fontSize: 9, fontWeight: 800, padding: "2px 7px", borderRadius: 999,
                  color: "#c4b5fd", background: "rgba(139,92,246,0.13)",
                  border: "1px solid rgba(139,92,246,0.3)", whiteSpace: "nowrap",
                }}>partial: {addrPartialStatus.replace(/_/g, " ")}</span>
              )}
              {hasDebugOnlyRule && !addrPartialStatus && (
                <span style={{
                  fontSize: 9, fontWeight: 800, padding: "2px 7px", borderRadius: 999,
                  color: "#fde68a", background: "rgba(245,158,11,0.14)",
                  border: "1px solid rgba(245,158,11,0.3)", whiteSpace: "nowrap",
                }}>과보정 주의</span>
              )}
            </div>
            {normalizationRules.length > 0 && (
              <div style={{ fontSize: 10, color: "var(--muted)", lineHeight: 1.45, wordBreak: "break-word" }}>
                규칙 {normalizationRules.length}개{ruleNames ? ` · ${ruleNames}` : ""}
              </div>
            )}
          </div>
        </FieldSlot>
      )}

      {summaryTotalRisk && (
        <FieldSlot color="#f59e0b" label="SUMMARY">
          <div style={{ display: "flex", flexDirection: "column", gap: 5, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
              {summaryTotalRisk.flags.map((flag) => (
                <span key={flag} style={{
                  fontSize: 9, fontWeight: 900, padding: "2px 7px", borderRadius: 999,
                  color: "#fde68a", background: "rgba(245,158,11,0.14)",
                  border: "1px solid rgba(245,158,11,0.3)", whiteSpace: "nowrap",
                }}>
                  {flag}
                </span>
              ))}
              {summaryTotalRisk.source && (
                <span style={{ fontSize: 10, color: "var(--muted)", fontWeight: 800 }}>
                  {summaryTotalRisk.source}{summaryTotalRisk.score ? ` · score ${summaryTotalRisk.score}` : ""}
                </span>
              )}
            </div>
            {(summaryTotalRisk.reason || summaryTotalRisk.evidenceText) && (
              <div style={{ fontSize: 10, color: "var(--muted)", lineHeight: 1.45, wordBreak: "break-word" }}>
                {summaryTotalRisk.reason && <span>{summaryTotalRisk.reason}</span>}
                {summaryTotalRisk.evidenceText && (
                  <span title={summaryTotalRisk.evidenceText}>
                    {summaryTotalRisk.reason ? " · " : ""}evidence: {summaryTotalRisk.evidenceText.slice(0, 120)}
                    {summaryTotalRisk.evidenceText.length > 120 ? "..." : ""}
                  </span>
                )}
              </div>
            )}
          </div>
        </FieldSlot>
      )}

      <FieldSlot color={hasOcr ? fSrc.color : "rgba(255,255,255,0.2)"} label="채택값" emphasis>
        <div style={{
          display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
          padding: "8px 10px",
          background: hasOcr ? fSrc.bg : "rgba(255,255,255,0.02)",
          border: `1px ${hasOcr ? "solid" : "dashed"} ${hasOcr ? fSrc.border : "rgba(255,255,255,0.12)"}`,
          borderRadius: 6,
        }}>
          {!hasOcr ? (
            <span style={{
              fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.45)",
              fontStyle: "italic", flex: 1,
            }}>
              OCR 미실행 · Run OCR 실행 후 채택값이 결정됩니다
            </span>
          ) : (
            <>
              <span title={finalView.reason} style={{
                fontSize: 10, fontWeight: 900, padding: "3px 8px", borderRadius: 999,
                color: "#fff", background: fSrc.color, whiteSpace: "nowrap",
              }}>{fSrc.label}</span>
              <span style={{
                fontSize: 15, fontWeight: 800,
                color: finalView.value ? "var(--text)" : "rgba(255,255,255,0.25)",
                wordBreak: "break-all", flex: 1, letterSpacing: -0.2,
              }}>{finalView.value || "—"}</span>
              {finalView.reason && (
                <span title={finalView.reason} style={{ fontSize: 10, color: "var(--muted)", fontWeight: 700 }}>
                  {finalView.reason}
                </span>
              )}
              {finalView.source === "empty" && required && (
                <span style={{ fontSize: 11, color: "#ef4444", fontWeight: 800 }}>
                  Tier-1 미추출
                </span>
              )}
              {isGtAdopted && hasValue && status === "X" && (
                <span style={{ fontSize: 11, color: "#ef4444", fontWeight: 800 }}>
                  ⚠ OCR 불일치
                </span>
              )}
            </>
          )}
        </div>
      </FieldSlot>
    </div>
  );
}

function matchStatusMeta(status: MatchStatus): { symbol: string; color: string; title: string } {
  switch (status) {
    case "exact":
      return { symbol: "O", color: "#22c55e", title: "기준값과 정확히 일치 (필드 표준 정규화 후 동일)" };
    case "policy":
      return { symbol: "△", color: "#f59e0b", title: "정규화/유사도/anchor/자동복원 등 정책 경로로 채택" };
    case "mismatch":
      return { symbol: "X", color: "#ef4444", title: "기준값과 불일치" };
    case "no_baseline":
    default:
      return { symbol: "—", color: "rgba(255,255,255,0.35)", title: "기준값이 없음 — 채점 대상 아님" };
  }
}

// finance_profile 컬럼 한국어 라벨 (docs/FINANCE_PARSER_TARGET_20260427.md §2)
const FINANCE_COL_LABELS: Record<string, string> = {
  bankName:            "은행명",
  transactionType:     "거래유형",
  transactionDateTime: "거래일시",
  amount:              "거래금액",
  balanceAfter:        "거래후잔액",
  accountMasked:       "계좌(마스킹)",
  branchOrChannel:     "수취인 계좌",
  memo:                "수취인명",
};

// 배치 요약 / docType 집계에서 finance에 표시할 컬럼 (거래유형 제외)
const FINANCE_DISPLAY_COLS: readonly { key: string; label: string }[] = [
  { key: "bankName",            label: "은행명" },
  { key: "transactionDateTime", label: "거래일시" },
  { key: "amount",              label: "거래금액" },
  { key: "balanceAfter",        label: "잔액" },
  { key: "accountMasked",       label: "계좌" },
  { key: "branchOrChannel",     label: "수취계좌" },
  { key: "memo",                label: "수취인명" },
];

// finance 필드별 비교 상태 (receipt의 MatchStatus/matchStatusMeta 와 동일 의미 체계)
//
// O: raw exact 일치 OR 보수적 정규화(숫자/구분자/prefix 차이) 후 동일 → "사실상 같은 값"
// △: canonical/fuzzy 일치 (bankName 한정: substring/canonical 매핑) → "의미상 유사"
// X: GT 있으나 핵심 값 불일치
// —: GT 없음
function financeMatchStatus(field: string, gtVal: string, ocrVal: string): "O" | "△" | "X" | "—" {
  if (!gtVal) return "—";
  if (!ocrVal) return "X";
  if (gtVal === ocrVal) return "O";
  const gn = normalizeFinanceValue(field, gtVal);
  const on = normalizeFinanceValue(field, ocrVal);
  // 정규화 후 동일: 형식 차이(쉼표/구분자/[xxx]prefix)만 있고 핵심값 같음 → O
  if (gn && on && gn === on) return "O";
  // bankName canonical/substring fallback → △ (의미상 유사하나 완전 동일은 아님)
  if (financeFieldMatches(field, gtVal, ocrVal)) return "△";
  return "X";
}

function financeMatchMeta(status: "O" | "△" | "X" | "—"): { symbol: string; color: string; title: string } {
  switch (status) {
    case "O":  return { symbol: "O", color: "#22c55e", title: "기준값과 일치 (정규화 동일 포함)" };
    case "△":  return { symbol: "△", color: "#f59e0b", title: "canonical/유사 일치 (은행명 변형 등)" };
    case "X":  return { symbol: "X", color: "#ef4444", title: "기준값과 불일치" };
    default:   return { symbol: "—", color: "rgba(255,255,255,0.35)", title: "기준값 없음" };
  }
}

// 채택값 슬롯 표시용 — [xxx] 기관 코드 prefix 등 표시용 노이즈만 제거 (비교 정규화와 별개)
function displayFinanceValue(field: string, value: string): string {
  if (!value) return "";
  if (field === "branchOrChannel" || field === "accountMasked") {
    return value.trim().replace(/^\[\d{2,4}\]/, "").trim();
  }
  return value;
}

// suppression_policy_note §6.2 status 문자열 → 1차 상태 표시 매핑
function getFinanceStatusMeta(status: string): { label: string; bg: string } {
  if (status === "selected")              return { label: "selected",    bg: "#16a34a" };
  if (status === "suppressed_bank_slip")  return { label: "review",      bg: "#d97706" };
  if (status?.startsWith("suppressed_")) return { label: "suppressed",   bg: "#dc2626" };
  if (status === "unknown")              return { label: "unknown",      bg: "#6b7280" };
  if (!status)                           return { label: "미실행",        bg: "#475569" };
  return { label: status, bg: "#6b7280" };
}

function pct(ok: number, total: number): string {
  if (!total) return "-";
  return `${Math.round((ok / total) * 100)}%`;
}

function toneOf(ok: number, total: number): KpiTone {
  if (!total) return "neutral";
  const p = ok / total;
  if (p >= 0.8) return "green";
  if (p >= 0.5) return "amber";
  return "red";
}

// ============================================================
// Manifest metadata display
// ============================================================
const DOC_TYPE_COLOR: Record<string, string> = {
  card_receipt:      "#0284c7",
  pos_receipt:       "#7c3aed",
  food_cafe_receipt: "#ea580c",
  finance_slip:      "#dc2626",
  medical_receipt:   "#16a34a",
  invoice_statement: "#ca8a04",
  unknown:           "#6b7280",
};
const DOC_TYPE_ABBR: Record<string, string> = {
  card_receipt:      "카드",
  pos_receipt:       "POS",
  food_cafe_receipt: "음식",
  finance_slip:      "금융",
  medical_receipt:   "약국",
  invoice_statement: "거래",
  unknown:           "기타",
};
const DIFF_COLOR: Record<string, string> = {
  easy:   "#22c55e",
  medium: "#f59e0b",
  hard:   "#ef4444",
};
const DOC_TYPE_ORDER: string[] = [
  "card_receipt", "pos_receipt", "food_cafe_receipt",
  "medical_receipt", "finance_slip", "invoice_statement", "unknown",
];
const DOC_TYPE_LABEL: Record<string, string> = {
  card_receipt:      "카드전표/일반 영수증",
  pos_receipt:       "POS/마트/편의점 영수증",
  food_cafe_receipt: "음식점/카페 영수증",
  medical_receipt:   "병원/약국 영수증",
  finance_slip:      "은행/금융 전표",
  invoice_statement: "세금계산서/거래명세서",
  unknown:           "기타/Unknown",
};
const QUALITY_TAG_LABELS: Record<string, string> = {
  ocr_noise:    "OCR 노이즈",
  handwritten:  "필기/수기",
  small_text:   "작은 글씨",
  folded:       "접힘",
  curled:       "말림",
  skewed:       "기울어짐",
  blurred:      "흐림",
  low_contrast: "저대비",
  shadow:       "그림자",
  stamp:        "도장",
  cropped:      "잘림",
  rotated:      "회전",
  long_receipt: "긴 영수증",
  table_layout: "표/테이블 구조",
};
const DIFFICULTY_LABELS: Record<string, string> = {
  easy:   "쉬움",
  medium: "보통",
  hard:   "어려움",
};
const DATASET_ROLE_LABELS: Record<string, string> = {
  regression:    "회귀 검증",
  generalization:"일반화 검증",
  fast_check:    "빠른 점검",
  experimental:  "실험용",
  document_type: "문서유형 관리",
};
const DATASET_STATUS_LABELS: Record<string, string> = {
  locked:      "잠금",
  in_progress: "진행 중",
  draft:       "초안",
};
function getQualityTagLabel(tag: string) { return QUALITY_TAG_LABELS[tag] ?? tag; }

// ── Invoice profile label maps (P-1) ──
const AMOUNT_PROFILE_LABELS: Record<string, string> = {
  supply_tax_total:    "공급가/세액/합계",
  total_only:          "합계만",
  subtotal_cumulative: "소계/누계",
  balance_cumulative:  "잔액/거래금액",
  no_amount_summary:   "금액 없음",
  quantity_total_only: "총수량",
  ambiguous_amount:    "금액 불명확",
};
const PARTY_PROFILE_LABELS: Record<string, string> = {
  supplier_buyer:      "양쪽",
  buyer_only:          "buyer only",
  supplier_weak:       "supplier 약함",
  buyer_rep_optional:  "대표 optional",
  party_garbled:       "OCR 깨짐",
};
const TABLE_PROFILE_LABELS: Record<string, string> = {
  multi_item_table:          "다품목",
  single_item_table:         "단일품목",
  lot_serial_quantity_table: "Lot/Serial/수량",
  serial_quantity_table:     "Serial/수량",
  item_quantity_table:       "품목/수량",
  item_amount_table:         "품목+금액",
};
function getAmountProfileLabel(p: string | undefined) { return p ? (AMOUNT_PROFILE_LABELS[p] ?? p) : "—"; }
function getPartyProfileLabel(p: string | undefined)  { return p ? (PARTY_PROFILE_LABELS[p]  ?? p) : "—"; }
function getTableProfileLabel(p: string | undefined)  { return p ? (TABLE_PROFILE_LABELS[p]  ?? p) : "—"; }

function InvoiceProfileKpi({ counts }: {
  counts: { amounts: Record<string, number>; parties: Record<string, number>; tables: Record<string, number> };
}) {
  const [open, setOpen] = React.useState(false);
  const chipSm: React.CSSProperties = { fontSize: 9, padding: "1px 6px", borderRadius: 3, fontWeight: 700, whiteSpace: "nowrap", display: "inline-block", margin: "0 2px" };
  return (
    <div style={{ flexBasis: "100%", marginTop: 4 }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{ background: "none", border: "none", cursor: "pointer", color: "#ca8a04", fontSize: 10, fontWeight: 700, padding: 0, letterSpacing: 0.4 }}
      >
        {open ? "▾" : "▸"} Profile 집계
      </button>
      {open && (
        <div style={{ paddingTop: 6, display: "flex", flexDirection: "column", gap: 4 }}>
          <div>
            <span style={{ fontSize: 9, color: "var(--muted)", fontWeight: 700, marginRight: 6 }}>Amount</span>
            {Object.entries(counts.amounts).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
              <span key={k} style={{ ...chipSm, background: k === "no_amount_summary" || k === "quantity_total_only" ? "#7c3aed" : "#0369a1", color: "#fff" }} title={k}>
                {getAmountProfileLabel(k)} {v}
              </span>
            ))}
          </div>
          <div>
            <span style={{ fontSize: 9, color: "var(--muted)", fontWeight: 700, marginRight: 6 }}>Party</span>
            {Object.entries(counts.parties).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
              <span key={k} style={{ ...chipSm, background: "#374151", color: "#d1d5db" }} title={k}>
                {getPartyProfileLabel(k)} {v}
              </span>
            ))}
          </div>
          <div>
            <span style={{ fontSize: 9, color: "var(--muted)", fontWeight: 700, marginRight: 6 }}>Table</span>
            {Object.entries(counts.tables).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
              <span key={k} style={{ ...chipSm, background: "#1e3a5f", color: "#bfdbfe" }} title={k}>
                {getTableProfileLabel(k)} {v}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
function getExpectedStatusLabel(s: string): string {
  if (s === "selected") return "정상 선택";
  if (s.startsWith("suppressed_")) return "정상 억제";
  if (s === "unknown") return "미분류";
  if (s === "error") return "오류";
  return s;
}

const DATASET_ROLE_COLOR: Record<string, string> = {
  regression:     "#0284c7",
  generalization: "#7c3aed",
  fast_check:     "#d97706",
  experimental:   "#ea580c",
  document_type:  "#16a34a",
};
const DATASET_STATUS_COLOR: Record<string, string> = {
  locked:      "#16a34a",
  in_progress: "#d97706",
  draft:       "#6b7280",
};

function ManifestMetaBadges({ item }: { item: ManifestItem }) {
  const isSuppr = item.expectedStatus !== "selected";
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 5, flexWrap: "wrap",
      padding: "6px 12px", borderRadius: 8,
      background: "var(--panel)", border: "1px solid rgba(255,255,255,0.06)",
    }}>
      <span style={{ fontSize: 9, fontWeight: 800, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.5, marginRight: 2 }}>
        문서 정보
      </span>
      <span title={item.documentType} style={{ ...chip, background: DOC_TYPE_COLOR[item.documentType] ?? "#6b7280" }}>
        {DOC_TYPE_LABEL[item.documentType] ?? item.documentType}
      </span>
      <span style={{ ...chip, background: DIFF_COLOR[item.difficulty] ?? "#6b7280" }}>
        {DIFFICULTY_LABELS[item.difficulty] ?? item.difficulty}
      </span>
      <span title={item.expectedStatus} style={{ ...chip, background: isSuppr ? "#dc2626" : "#16a34a" }}>
        {getExpectedStatusLabel(item.expectedStatus)}
      </span>
      {item.qualityTags.map((tag) => (
        <span key={tag} title={tag} style={{ ...chip, background: "#475569" }}>
          {getQualityTagLabel(tag)}
        </span>
      ))}
      {item.notes && (
        <span title={item.notes} style={{ fontSize: 10, color: "var(--muted)", marginLeft: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 260, display: "inline-block" }}>
          {item.notes}
        </span>
      )}
    </div>
  );
}

// ============================================================
// DocTypeSummarySection
// ============================================================
const FIELD_SHORT: Record<FieldKey, string> = {
  회사명: "회사", 사업자번호: "사번", 대표자: "대표", tel: "전화", 주소: "주소", 총합계금액: "금액",
};

// 레거시 한국어 FieldKey → profiles.ts ReceiptFieldKey(영문 논리명) 어댑터
// TestWorkspace의 기존 키 체계와 profiles.ts 키 체계를 연결하는 브리지.
const FIELD_KEY_PROFILE_MAP: Record<FieldKey, string> = {
  "회사명":    "companyName",
  "사업자번호": "bizNumber",
  "대표자":    "representative",
  "tel":       "phone",
  "주소":      "address",
  "총합계금액": "totalAmount",
};

function DocTypeSummarySection({
  rows,
  totalImages,
}: {
  rows: DocTypeSummaryRow[];
  totalImages: number;
}) {
  const receiptRows = rows.filter((r) => resolveProfile(r.documentType).base === "receipt");
  const financeRows = rows.filter((r) => resolveProfile(r.documentType).base === "finance");
  const documentRows = rows.filter((r) => resolveProfile(r.documentType).base === "document");
  const otherRows   = rows.filter((r) => !["receipt", "finance", "document"].includes(resolveProfile(r.documentType).base));

  const receiptTotal = receiptRows.reduce((s, r) => s + r.total, 0);
  const financeTotal = financeRows.reduce((s, r) => s + r.total, 0);
  const documentTotal = documentRows.reduce((s, r) => s + r.total, 0);

  const thSm: React.CSSProperties = {
    padding: "4px 8px", textAlign: "left", fontSize: 10, fontWeight: 700,
    color: "var(--muted)", letterSpacing: 0.4, whiteSpace: "nowrap",
    borderBottom: "1px solid rgba(255,255,255,0.07)",
  };
  const tdSm: React.CSSProperties = {
    padding: "4px 8px", fontSize: 11,
    borderBottom: "1px solid rgba(255,255,255,0.04)", verticalAlign: "middle",
  };

  const renderSubGroupHeader = (label: string, count: number, color: string) => (
    <div style={{ fontSize: 10, fontWeight: 800, color, padding: "6px 2px 3px", letterSpacing: 0.4 }}>
      {label} · {count}장
    </div>
  );

  // 공통 상태 셀들 (documentType 배지 + total/selected/suppressed/review/not_run/선택률)
  const renderStatusCells = (row: DocTypeSummaryRow, mode: "receipt" | "finance" | "document") => {
    const runCount = row.total - row.notRun;
    const selRate  = row.total > 0 ? Math.round((row.selected / row.total) * 100) : null;
    const selColor = selRate === 100 ? "#22c55e" : selRate !== null && selRate >= 50 ? "#f59e0b" : "#ef4444";
    const isFinance = mode === "finance";
    const reviewCount = isFinance ? row.unknown : null;  // finance 전용: unknown 슬롯 = review
    return (
      <>
        <td style={tdSm}>
          <span title={row.documentType} style={{ ...chip, background: DOC_TYPE_COLOR[row.documentType] ?? "#6b7280", fontSize: 9 }}>
            {DOC_TYPE_LABEL[row.documentType] ?? row.documentType}
          </span>
        </td>
        <td style={{ ...tdSm, textAlign: "center" }}>{row.total}</td>
        <td style={{ ...tdSm, textAlign: "center", fontWeight: 700, color: row.selected > 0 ? "#22c55e" : "rgba(255,255,255,0.25)" }}>
          {row.selected || "—"}
        </td>
        {isFinance ? (
          <td style={{ ...tdSm, textAlign: "center", color: reviewCount! > 0 ? "#f59e0b" : "rgba(255,255,255,0.25)", fontWeight: 700 }}>
            {reviewCount! || "—"}
          </td>
        ) : (
          <td style={{ ...tdSm, textAlign: "center", fontWeight: 700, color: row.suppressed > 0 ? "#ef4444" : "rgba(255,255,255,0.25)" }}>
            {row.suppressed || "—"}
          </td>
        )}
        <td style={{ ...tdSm, textAlign: "center", color: row.notRun > 0 ? "#94a3b8" : "rgba(255,255,255,0.25)" }}>
          {row.notRun || "—"}
        </td>
        <td style={{ ...tdSm, textAlign: "center", fontWeight: 800, color: selColor }}>
          {selRate !== null ? `${selRate}%` : "—"}
        </td>
        {/* 필드 채움 수 (profile 별 분기) */}
        {mode === "finance"
          ? FINANCE_DISPLAY_COLS.map((col) => {
              const filled = row.financeFieldFilled[col.key] ?? 0;
              return (
                <td key={col.key} style={{
                  ...tdSm, textAlign: "center",
                  color: runCount === 0 ? "rgba(255,255,255,0.2)"
                       : filled === runCount ? "#22c55e"
                       : filled > 0 ? "#f59e0b"
                       : "rgba(255,255,255,0.2)",
                }}>
                  {runCount > 0 ? `${filled}/${runCount}` : "—"}
                </td>
              );
            })
          : mode === "document"
          ? DOCUMENT_FIELD_META.map((col) => {
              const filled = row.documentFieldFilled[col.key] ?? 0;
              return (
                <td key={col.key} style={{
                  ...tdSm, textAlign: "center",
                  color: runCount === 0 ? "rgba(255,255,255,0.2)"
                       : filled === runCount ? "#22c55e"
                       : filled > 0 ? "#f59e0b"
                       : "rgba(255,255,255,0.2)",
                }}>
                  {runCount > 0 ? `${filled}/${runCount}` : "—"}
                </td>
              );
            })
          : FIELDS.map((f) => (
              <td key={f.key} style={{
                ...tdSm, textAlign: "center",
                color: runCount === 0 ? "rgba(255,255,255,0.2)"
                     : row.fieldFilled[f.key] === runCount ? "#22c55e"
                     : row.fieldFilled[f.key] > 0 ? "#f59e0b"
                     : "#ef4444",
              }}>
                {runCount > 0 ? `${row.fieldFilled[f.key]}/${runCount}` : "—"}
              </td>
            ))
        }
      </>
    );
  };

  return (
    <details style={{ background: "var(--panel)", borderRadius: 8, padding: "8px 14px" }}>
      <summary style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", cursor: "pointer", letterSpacing: 0.5, userSelect: "none" }}>
        documentType 집계 ▶
        {receiptTotal > 0 && (
          <span style={{ marginLeft: 10, fontWeight: 800, color: "#0ea5e9" }}>영수증 {receiptTotal}장</span>
        )}
        {financeTotal > 0 && (
          <span style={{ marginLeft: 8, fontWeight: 800, color: "#dc2626" }}>금융전표 {financeTotal}장</span>
        )}
        {documentTotal > 0 && (
          <span style={{ marginLeft: 8, fontWeight: 800, color: "#ca8a04" }}>거래명세서 {documentTotal}장</span>
        )}

        {otherRows.length > 0 && (
          <span style={{ marginLeft: 8, fontWeight: 600, color: "var(--muted)" }}>기타 {otherRows.reduce((s, r) => s + r.total, 0)}장</span>
        )}
        <span style={{ marginLeft: 8, fontWeight: 500, color: "var(--muted)", fontSize: 10 }}>(총 {totalImages}장)</span>
      </summary>

      <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 12 }}>

        {/* ── 영수증 계열 sub-table ── */}
        {receiptRows.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            {renderSubGroupHeader("영수증 계열", receiptTotal, "#0ea5e9")}
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr>
                  <th style={thSm}>documentType</th>
                  <th style={{ ...thSm, textAlign: "center" }}>total</th>
                  <th style={{ ...thSm, textAlign: "center" }}>selected</th>
                  <th style={{ ...thSm, textAlign: "center" }}>suppressed</th>
                  <th style={{ ...thSm, textAlign: "center" }}>not_run</th>
                  <th style={{ ...thSm, textAlign: "center" }}>선택률</th>
                  {FIELDS.map((f) => (
                    <th key={f.key} style={{ ...thSm, textAlign: "center" }}>{FIELD_SHORT[f.key]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {receiptRows.map((row) => (
                  <tr key={row.documentType}>{renderStatusCells(row, "receipt")}</tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── 금융전표 sub-table (finance 전용 컬럼) ── */}
        {financeRows.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            {renderSubGroupHeader("금융전표", financeTotal, "#dc2626")}
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr>
                  <th style={thSm}>documentType</th>
                  <th style={{ ...thSm, textAlign: "center" }}>total</th>
                  <th style={{ ...thSm, textAlign: "center", color: "#22c55e" }}>selected</th>
                  <th style={{ ...thSm, textAlign: "center", color: "#f59e0b" }}>review</th>
                  <th style={{ ...thSm, textAlign: "center" }}>not_run</th>
                  <th style={{ ...thSm, textAlign: "center" }}>선택률</th>
                  {FINANCE_DISPLAY_COLS.map((col) => (
                    <th key={col.key} style={{ ...thSm, textAlign: "center" }}>{col.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {financeRows.map((row) => (
                  <tr key={row.documentType}>{renderStatusCells(row, "finance")}</tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── 거래명세서 sub-table (document 전용 컬럼) ── */}
        {documentRows.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            {renderSubGroupHeader("거래명세서", documentTotal, "#ca8a04")}
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr>
                  <th style={thSm}>documentType</th>
                  <th style={{ ...thSm, textAlign: "center" }}>total</th>
                  <th style={{ ...thSm, textAlign: "center" }}>selected</th>
                  <th style={{ ...thSm, textAlign: "center" }}>suppressed</th>
                  <th style={{ ...thSm, textAlign: "center" }}>not_run</th>
                  <th style={{ ...thSm, textAlign: "center" }}>선택률</th>
                  {DOCUMENT_FIELD_META.map((col) => (
                    <th key={col.key} style={{ ...thSm, textAlign: "center" }}>{col.shortLabel}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {documentRows.map((row) => (
                  <tr key={row.documentType}>{renderStatusCells(row, "document")}</tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── 기타 sub-table ── */}
        {otherRows.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            {renderSubGroupHeader("기타", otherRows.reduce((s, r) => s + r.total, 0), "#6b7280")}
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr>
                  <th style={thSm}>documentType</th>
                  <th style={{ ...thSm, textAlign: "center" }}>total</th>
                  <th style={{ ...thSm, textAlign: "center" }}>selected</th>
                  <th style={{ ...thSm, textAlign: "center" }}>suppressed</th>
                  <th style={{ ...thSm, textAlign: "center" }}>not_run</th>
                  <th style={{ ...thSm, textAlign: "center" }}>선택률</th>
                  {FIELDS.map((f) => (
                    <th key={f.key} style={{ ...thSm, textAlign: "center" }}>{FIELD_SHORT[f.key]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {otherRows.map((row) => (
                  <tr key={row.documentType}>{renderStatusCells(row, "receipt")}</tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      </div>
    </details>
  );
}

// ============================================================
// QualityTagSummarySection
// ============================================================
function QualityTagSummarySection({ rows }: { rows: QualityTagSummaryRow[] }) {
  const thSm: React.CSSProperties = {
    padding: "4px 8px", textAlign: "left", fontSize: 10, fontWeight: 700,
    color: "var(--muted)", letterSpacing: 0.4, whiteSpace: "nowrap",
    borderBottom: "1px solid rgba(255,255,255,0.07)",
  };
  const tdSm: React.CSSProperties = {
    padding: "4px 8px", fontSize: 11,
    borderBottom: "1px solid rgba(255,255,255,0.04)", verticalAlign: "middle",
  };
  return (
    <details style={{ background: "var(--panel)", borderRadius: 8, padding: "8px 14px" }}>
      <summary style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", cursor: "pointer", letterSpacing: 0.5, userSelect: "none" }}>
        qualityTags 집계 ({rows.length}개 태그) ▶
      </summary>
      <div style={{ marginTop: 8, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
          <thead>
            <tr>
              <th style={thSm}>qualityTag</th>
              <th style={{ ...thSm, textAlign: "center" }}>total</th>
              <th style={{ ...thSm, textAlign: "center" }}>selected</th>
              <th style={{ ...thSm, textAlign: "center" }}>suppressed</th>
              <th style={{ ...thSm, textAlign: "center" }}>unknown</th>
              <th style={{ ...thSm, textAlign: "center" }}>not_run</th>
              <th style={{ ...thSm, textAlign: "center" }}>선택률</th>
              {FIELDS.map((f) => (
                <th key={f.key} style={{ ...thSm, textAlign: "center" }}>{FIELD_SHORT[f.key]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const runCount = row.total - row.notRun;
              const selRate = row.total > 0 ? Math.round((row.selected / row.total) * 100) : null;
              const selColor = selRate === 100 ? "#22c55e" : selRate !== null && selRate >= 50 ? "#f59e0b" : "#ef4444";
              return (
                <tr key={row.tag}>
                  <td style={tdSm}>
                    <span title={row.tag} style={{ ...chip, background: "#475569", fontSize: 9 }}>
                      {getQualityTagLabel(row.tag)}
                    </span>
                  </td>
                  <td style={{ ...tdSm, textAlign: "center" }}>{row.total}</td>
                  <td style={{ ...tdSm, textAlign: "center", fontWeight: 700, color: row.selected > 0 ? "#22c55e" : "rgba(255,255,255,0.25)" }}>
                    {row.selected || "—"}
                  </td>
                  <td style={{ ...tdSm, textAlign: "center", fontWeight: 700, color: row.suppressed > 0 ? "#ef4444" : "rgba(255,255,255,0.25)" }}>
                    {row.suppressed || "—"}
                  </td>
                  <td style={{ ...tdSm, textAlign: "center", color: row.unknown > 0 ? "#f59e0b" : "rgba(255,255,255,0.25)" }}>
                    {row.unknown || "—"}
                  </td>
                  <td style={{ ...tdSm, textAlign: "center", color: row.notRun > 0 ? "#94a3b8" : "rgba(255,255,255,0.25)" }}>
                    {row.notRun || "—"}
                  </td>
                  <td style={{ ...tdSm, textAlign: "center", fontWeight: 800, color: selColor }}>
                    {selRate !== null ? `${selRate}%` : "—"}
                  </td>
                  {FIELDS.map((f) => (
                    <td key={f.key} style={{
                      ...tdSm, textAlign: "center",
                      color: runCount === 0 ? "rgba(255,255,255,0.2)"
                           : row.fieldFilled[f.key] === runCount ? "#22c55e"
                           : row.fieldFilled[f.key] > 0 ? "#f59e0b"
                           : "#ef4444",
                    }}>
                      {runCount > 0 ? `${row.fieldFilled[f.key]}/${runCount}` : "—"}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}

// ============================================================
// styles
// ============================================================
const dot = (bg: string): React.CSSProperties => ({
  width: 7, height: 7, borderRadius: "50%", background: bg, display: "block",
});

function btnStyle(active: boolean, variant: "accent" | "ghost"): React.CSSProperties {
  return {
    padding: "8px 16px", borderRadius: 8, fontWeight: 700, fontSize: 13,
    cursor: active ? "not-allowed" : "pointer", whiteSpace: "nowrap",
    border: variant === "ghost" ? "1px solid rgba(255,255,255,0.1)" : "none",
    background: active ? "var(--panel2)" : variant === "accent" ? "var(--accent)" : "var(--panel2)",
    color: active ? "var(--muted)" : variant === "accent" ? "#fff" : "var(--text)",
    transition: "background 0.15s",
  };
}

function cellMuted(value: string): React.CSSProperties {
  return { fontSize: 12, color: value ? "var(--muted)" : "rgba(255,255,255,0.25)", wordBreak: "break-all" };
}

const chip: React.CSSProperties = {
  fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 4, color: "#fff",
};

const styles: Record<string, React.CSSProperties> = {
  datasetBar: {
    display: "flex", alignItems: "center", gap: 12, padding: "10px 12px",
    background: "linear-gradient(135deg, rgba(14,165,233,0.10), rgba(255,255,255,0.03))",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 10, boxShadow: "var(--shadowSoft)",
    flexShrink: 0, flexWrap: "wrap",
  },
  datasetBtn: {
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 999,
    padding: "7px 12px",
    fontSize: 12,
    fontWeight: 800,
    cursor: "pointer",
    transition: "all 0.15s",
  },
  filterBar: {
    display: "flex", alignItems: "center", gap: 8, padding: "7px 12px",
    background: "var(--panel)", borderRadius: 8,
    border: "1px solid rgba(255,255,255,0.06)",
    flexShrink: 0, flexWrap: "wrap",
  },
  emptyDataset: {
    padding: "22px 24px",
    borderRadius: 12,
    background: "var(--panel)",
    border: "1px dashed rgba(255,255,255,0.16)",
    boxShadow: "var(--shadowSoft)",
    flexShrink: 0,
  },
  topBar: {
    display: "flex", alignItems: "center", gap: 12, padding: "8px 12px",
    background: "var(--panel)", borderRadius: 10, boxShadow: "var(--shadowSoft)",
    flexShrink: 0, overflow: "hidden",
  },
  groupBox: {
    display: "flex", flexDirection: "column", gap: 4, flexShrink: 0,
    padding: "4px 8px", borderRadius: 8,
    background: "rgba(255,255,255,0.03)",
    border: "1px solid rgba(255,255,255,0.06)",
  },
  groupLabel: {
    fontSize: 10, fontWeight: 700, color: "var(--text)",
    textTransform: "none", letterSpacing: 0.2,
    display: "flex", alignItems: "center", gap: 3,
    whiteSpace: "nowrap",
  },
  thumb: {
    flexShrink: 0, width: 64, height: 64, borderRadius: 8, overflow: "hidden",
    padding: 0, cursor: "pointer", background: "var(--panel2)", position: "relative",
    transition: "border 0.15s",
  },
  thumbLabel: {
    position: "absolute", top: 0, left: 0, right: 0,
    padding: "2px 4px",
    background: "linear-gradient(to bottom, rgba(0,0,0,0.7), rgba(0,0,0,0))",
    color: "#fff", fontSize: 10, fontWeight: 700,
    textAlign: "center", letterSpacing: 0.3,
    textShadow: "0 1px 2px rgba(0,0,0,0.5)",
    pointerEvents: "none",
  },
  pdfThumb: {
    width: "100%",
    height: "100%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "linear-gradient(135deg, rgba(239,68,68,0.22), rgba(255,255,255,0.06))",
  },
  pdfBadge: {
    fontSize: 14,
    fontWeight: 900,
    color: "#fecaca",
    letterSpacing: 0.4,
  },
  pdfCanvasWrapThumb: {
    width: "100%",
    height: "100%",
    position: "relative",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "var(--panel2)",
  },
  pdfCanvasThumb: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    display: "block",
    background: "#fff",
  },
  imagePane: {
    flex: "0 0 40%", background: "var(--panel)", borderRadius: 10,
    boxShadow: "var(--shadowSoft)", overflow: "hidden",
    display: "flex", alignItems: "center", justifyContent: "center", padding: 12,
  },
  pdfCanvasWrapPreview: {
    width: "100%",
    height: "100%",
    minHeight: 220,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
    borderRadius: 6,
    background: "rgba(255,255,255,0.03)",
  },
  pdfCanvasPreview: {
    display: "block",
    maxWidth: "100%",
    maxHeight: "100%",
    width: "auto",
    height: "auto",
    objectFit: "contain" as const,
    borderRadius: 6,
    background: "#fff",
    boxShadow: "0 10px 30px rgba(0,0,0,0.28)",
  },
  pdfPreview: {
    width: "100%",
    height: "100%",
    minHeight: 220,
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    borderRadius: 6,
    border: "1px solid rgba(255,255,255,0.08)",
    background: "linear-gradient(135deg, rgba(239,68,68,0.12), rgba(255,255,255,0.03))",
  },
  pdfPreviewBadge: {
    padding: "6px 12px",
    borderRadius: 6,
    background: "rgba(239,68,68,0.18)",
    color: "#fecaca",
    fontSize: 18,
    fontWeight: 900,
    letterSpacing: 0.6,
  },
  previewImage: {
    display: "block",
    maxWidth: "100%",
    maxHeight: "100%",
    width: "auto",
    height: "auto",
    objectFit: "contain",
    borderRadius: 6,
    imageOrientation: "from-image" as any,
  },
  modeSwitcher: {
    display: "flex", gap: 2, padding: 2, borderRadius: 8,
    background: "var(--panel2)",
  },
  modeBtn: {
    fontSize: 11, fontWeight: 700, padding: "5px 10px", borderRadius: 6,
    border: "none", cursor: "pointer", transition: "all 0.15s",
  },
  kpiWrapper: {
    display: "flex", gap: 6, flexShrink: 0, flexWrap: "wrap",
  },
  kpiBar: {
    display: "flex", gap: 6, padding: "6px 10px",
    background: "var(--panel)", borderRadius: 10,
    flexShrink: 0, overflowX: "auto",
  },
  batchBox: {
    background: "var(--panel)", borderRadius: 10, boxShadow: "var(--shadowSoft)",
    padding: "10px 14px", flexShrink: 0, maxHeight: 220, overflow: "auto",
  },
  sectionHeader: {
    fontSize: 11, fontWeight: 700, color: "var(--muted)", marginBottom: 8,
    textTransform: "uppercase", letterSpacing: 0.5,
  },
  autofillBar: {
    display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10,
    padding: "8px 12px", borderRadius: 10,
    background: "linear-gradient(135deg, rgba(99,102,241,0.08), rgba(168,85,247,0.06))",
    border: "1px solid rgba(99,102,241,0.22)",
    flexWrap: "wrap",
  },
  autofillChip: {
    display: "inline-flex", alignItems: "center",
    fontSize: 11, fontWeight: 700, padding: "4px 10px", borderRadius: 999,
    cursor: "pointer", transition: "all 0.15s",
    whiteSpace: "nowrap",
  },
  commitBtn: {
    padding: "6px 12px", borderRadius: 6, fontWeight: 700, fontSize: 11,
    border: "1px solid rgba(34,197,94,0.3)",
    background: "rgba(34,197,94,0.15)", color: "#22c55e", cursor: "pointer",
    whiteSpace: "nowrap",
  },
  fieldCommitBtn: {
    padding: "2px 6px", borderRadius: 4, fontWeight: 700, fontSize: 10,
    border: "1px solid rgba(34,197,94,0.35)",
    background: "rgba(34,197,94,0.12)", color: "#22c55e", cursor: "pointer",
    whiteSpace: "nowrap", flexShrink: 0,
  },
  colHeader: {
    display: "grid", gap: 8, padding: "6px 12px",
    fontSize: 11, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase",
    gridAutoColumns: "minmax(0, 1fr)",
  },
  fieldRow: {
    display: "grid", gap: 8, padding: "9px 12px",
    borderRadius: 8, boxShadow: "var(--shadowSoft)",
    alignItems: "center", transition: "background 0.2s",
  },
  fieldLabel: {
    fontSize: 12, fontWeight: 700, color: "var(--muted)",
    display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap",
  },
  gtInput: {
    background: "var(--panel2)", border: "1px solid rgba(255,255,255,0.07)",
    borderRadius: 6, padding: "5px 8px", fontSize: 12,
    color: "var(--text)", outline: "none", width: "100%", boxSizing: "border-box",
  },
};

const th: React.CSSProperties = {
  padding: "6px 10px", textAlign: "left", fontWeight: 700,
  color: "var(--muted)", borderBottom: "1px solid rgba(255,255,255,0.06)",
  whiteSpace: "nowrap",
};

const td: React.CSSProperties = {
  padding: "6px 10px", color: "var(--text)",
  borderBottom: "1px solid rgba(255,255,255,0.04)",
};
