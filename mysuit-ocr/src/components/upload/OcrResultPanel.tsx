"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AutofillAction, AutofillRunSummary, AutofillSuggestion, OutputValueSource } from "@/lib/autofillEngine";
import { getGroundTruth, compareToGt, fieldKey } from "@/lib/groundTruthStore";
import { useUi } from "../common/AppProviders";

export type FieldSourceBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type FieldOverlayAdoption = "ocr" | "restored" | "excluded" | "unknown";

export type OcrFieldResult = {
  name: string;
  field_type: string;
  value: string;
  confidence: number;
  bbox: number[];
  source?: OutputValueSource;
  applied?: string;
  autofillAction?: AutofillAction;
  suggestions?: AutofillSuggestion[];
  original?: string;
  sourceBboxes?: FieldSourceBox[];
  overlayAdoption?: FieldOverlayAdoption;
  en?: string;
  ko?: string;
};

export type OcrResult = {
  fields: OcrFieldResult[];
  full_text: string;
  processing_time: number;
  raw_ocr_fields?: OcrFieldResult[];
  processed_image?: string;
  autofill_summary?: AutofillRunSummary;
};

type Props = {
  result: OcrResult;
  onRerun: () => void;
  onRevalidate: (fields: { index: number; bbox: number[] }[]) => Promise<OcrFieldResult[]>;
  selectedIndex: number | null;
  onSelectField: (index: number) => void;
  templateName?: string | null;
  fileName?: string;
  onTabChange?: (tab: "preview" | "custom" | "validation") => void;
  drawMode?: string | null;
  onDrawModeChange?: (mode: string | null) => void;
  isScanning?: boolean;
  onScanChange?: (scanning: boolean) => void;
  onPartialOcr?: (targets: { index: number; bbox: number[] }[]) => Promise<OcrFieldResult[]>;
  canvasRegions?: { id: string; name: string; fieldType: string; x: number; y: number; width: number; height: number }[];
};

type TabKey = "preview" | "custom" | "validation";

export default function OcrResultPanel({ result, onRerun, onRevalidate, selectedIndex, onSelectField, templateName, fileName, onTabChange, drawMode, onDrawModeChange, isScanning, onScanChange, onPartialOcr, canvasRegions }: Props) {
  const ui = useUi();
  const [activeTab, setActiveTab] = useState<TabKey>("preview");
  const [previewMode, setPreviewMode] = useState<"markdown" | "json">("markdown");
  const [editedFields, setEditedFields] = useState<OcrFieldResult[]>(result.fields);
  const [validationFilter, setValidationFilter] = useState<"all" | "success" | "warning" | "error">("success");
  const [confRange, setConfRange] = useState<number | null>(null); // null=전체, 0=0~10%, 10=10~20%, ... 90=90~100%
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [activeFieldType, setActiveFieldType] = useState<string>("field");
  const [isRevalidating, setIsRevalidating] = useState(false);
  const [rawOcrOpen, setRawOcrOpen] = useState(true);
  const [autofillDetailOpen, setAutofillDetailOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // canvasRegions에서 새로 그린 영역을 editedFields에 동기화
  useEffect(() => {
    if (!canvasRegions) return;
    const newRegions = canvasRegions.filter((r) => !r.id.startsWith("ocr_"));
    const existingIds = new Set(editedFields.map((f) => f.name));
    const toAdd: OcrFieldResult[] = [];
    newRegions.forEach((r) => {
      if (!existingIds.has(r.name)) {
        toAdd.push({
          name: r.name,
          field_type: r.fieldType,
          value: "",
          confidence: 0,
          bbox: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
        });
      }
    });
    if (toAdd.length > 0) {
      setEditedFields((prev) => [...prev, ...toAdd]);
    }
  }, [canvasRegions]);

  const FIELD_TYPES = [
    { key: "field", label: "필드" },
    { key: "multi", label: "멀티필드" },
    { key: "check", label: "체크필드" },
    { key: "table", label: "테이블필드" },
  ];

  const deleteField = (index: number) => {
    setEditedFields((prev) => prev.filter((_, i) => i !== index));
    if (selectedIndex === index) onSelectField(-1);
  };

  const updateFieldType = (index: number, type: string) => {
    setEditedFields((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], field_type: type };
      return next;
    });
  };

  const updateFieldName = (index: number, name: string) => {
    setEditedFields((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], name };
      return next;
    });
  };

  // 선택된 필드로 스크롤 + Validation 탭에서 편집 연동
  useEffect(() => {
    if (selectedIndex == null) return;
    if (activeTab === "validation") {
      // 현재 필터에 선택된 필드가 없으면 전체 보기로 전환
      const field = editedFields[selectedIndex];
      if (field) {
        const status = getValidationStatus(field);
        const inCurrentFilter = validationFilter === "all" || validationFilter === status;
        const inConfRange = confRange === null || (field.confidence * 100 >= confRange && field.confidence * 100 < confRange + 10);
        if (!inCurrentFilter || !inConfRange) {
          setValidationFilter("all");
          setConfRange(null);
        }
      }
      setEditingIdx(selectedIndex);
      setEditValue(editedFields[selectedIndex]?.value ?? "");
    }
    // 스크롤은 DOM 업데이트 후 실행
    setTimeout(() => {
      if (contentRef.current) {
        const el = contentRef.current.querySelector(`[data-field-idx="${selectedIndex}"]`) as HTMLElement;
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 50);
  }, [selectedIndex]);

  const tabs: { key: TabKey; label: string }[] = [
    { key: "preview", label: "Preview" },
    { key: "custom", label: "Custom" },
    { key: "validation", label: "Validation" },
  ];

  const getValidationStatus = (field: OcrFieldResult) => {
    if (!field.value || field.value.trim() === "") return "error";
    if (field.confidence < 0.7) return "warning";
    return "success";
  };

  const validationCounts = {
    success: editedFields.filter((f) => getValidationStatus(f) === "success").length,
    warning: editedFields.filter((f) => getValidationStatus(f) === "warning").length,
    error: editedFields.filter((f) => getValidationStatus(f) === "error").length,
  };
  const rawOcrFields = Array.isArray(result.raw_ocr_fields) ? result.raw_ocr_fields : [];
  const gtMap = useMemo(
    () => (templateName && fileName ? getGroundTruth(templateName, fileName) : {}),
    [templateName, fileName],
  );
  const hasGt = Object.keys(gtMap).length > 0;

  const formatConfidence = (confidence: number | null | undefined) => {
    const value = Number(confidence ?? 0);
    const pct = value <= 1 ? value * 100 : value;
    return `${pct.toFixed(1)}%`;
  };

  const getGtForField = (field: OcrFieldResult, map: Record<string, string>) => {
    const flexible = field as OcrFieldResult & {
      en?: string;
      ko?: string;
      label?: string;
      enField?: string;
      koField?: string;
    };
    const candidates = [
      fieldKey(flexible.en, flexible.ko),
      fieldKey(flexible.enField, flexible.koField),
      fieldKey(undefined, flexible.label),
      fieldKey(undefined, field.name),
      fieldKey(field.name),
    ].filter(Boolean);

    for (const key of [...new Set(candidates)]) {
      const value = map[key];
      if (value !== undefined && value !== null && String(value).trim() !== "") {
        return String(value);
      }
    }
    return "";
  };

  const matchSummary = useMemo(() => {
    if (!hasGt) return null;
    const comparableRows = editedFields.filter((field) => getGtForField(field, gtMap).trim() !== "");
    if (comparableRows.length === 0) return null;

    const matched = comparableRows.filter((field) => {
      const gt = getGtForField(field, gtMap);
      return compareToGt(field.value, gt).status === "match";
    }).length;
    const total = comparableRows.length;
    const pct = Math.round((matched / total) * 100);
    return { matched, total, pct };
  }, [editedFields, gtMap, hasGt]);

  const getAdoptionLabel = (field: OcrFieldResult): "OCR" | "복원" | "-" => {
    if (field.autofillAction === "confirmed") return "OCR";
    if (field.autofillAction === "corrected") return "복원";
    if (field.autofillAction === "filled") return "복원";
    if (field.value && String(field.value).trim()) return "OCR";
    return "-";
  };

  const renderAdoption = (field: OcrFieldResult) => {
    const label = getAdoptionLabel(field);
    const color = label === "OCR" ? "#2563eb" : label === "복원" ? "#4f46e5" : "var(--muted)";
    return <span style={{ color, fontWeight: 900 }}>{label}</span>;
  };

  const renderSourceBadge = (source?: OutputValueSource) => {
    if (!source || source === "ocr") return null;
    const meta =
      source === "biz" ? { label: "매칭복원", bg: "#6366f1", title: "사업자번호 기반 내부 매칭복원" } :
      source === "gt" ? { label: "정답", bg: "#16a34a", title: "저장된 정답" } :
      source === "text" ? { label: "직접입력", bg: "#a855f7", title: "직접 입력값" } :
      null;
    if (!meta) return null;
    return (
      <span
        title={meta.title}
        style={{
          fontSize: 9,
          fontWeight: 800,
          padding: "2px 6px",
          borderRadius: 4,
          color: "#fff",
          background: meta.bg,
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        {meta.label}
      </span>
    );
  };

  const fieldLabel = (field: OcrFieldResult) => field.ko || field.name || field.en || "-";

  const isAmountLikeField = (field: OcrFieldResult) => {
    const label = fieldLabel(field).replace(/\s+/g, "").toLowerCase();
    return [
      "총합계금액",
      "합계금액",
      "총액",
      "totalamount",
      "amount",
      "판매금액",
      "부가세",
      "공급가액",
    ].some((key) => label.includes(key.toLowerCase()));
  };

  const actionMeta = (action?: AutofillAction, excluded = false) => {
    if (action === "corrected") return { label: "복원", bg: "rgba(99,102,241,0.14)", color: "#4f46e5", title: "OCR 값을 복원 후보값으로 보정했습니다." };
    if (action === "filled") return { label: "복원", bg: "rgba(99,102,241,0.14)", color: "#4f46e5", title: "빈 OCR 값을 복원 후보값으로 채웠습니다." };
    if (excluded) return { label: "제외", bg: "rgba(148,163,184,0.12)", color: "var(--muted)", title: "금액 계열은 자동복원 대상에서 제외됩니다." };
    return null;
  };

  const renderAutofillActionBadge = (field: OcrFieldResult, showExcluded = false) => {
    const meta = actionMeta(field.autofillAction, showExcluded && isAmountLikeField(field));
    if (!meta || field.autofillAction === "none") return null;
    return (
      <span
        title={meta.title}
        style={{
          fontSize: 9,
          fontWeight: 800,
          padding: "2px 6px",
          borderRadius: 4,
          color: meta.color,
          background: meta.bg,
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        {meta.label}
      </span>
    );
  };

  const autofillDetailRows = useMemo(() => editedFields.map((field) => {
    const candidate = field.applied || field.suggestions?.[0]?.value || (field.autofillAction === "confirmed" ? field.value : "");
    const action = field.autofillAction && field.autofillAction !== "none"
      ? field.autofillAction
      : isAmountLikeField(field)
        ? "none"
        : undefined;
    return {
      label: fieldLabel(field),
      ocrValue: field.original ?? field.value ?? "",
      candidate,
      action,
      excluded: isAmountLikeField(field),
    };
  }), [editedFields]);

  const hasAutofillDetail = autofillDetailRows.some((row) => row.action || row.candidate || row.excluded);

  const autofillHelpText = (summary: AutofillRunSummary) => {
    if (summary.status === "no_business_number") return "사업자번호를 찾지 못해 자동복원을 건너뛰었습니다.";
    if (summary.status === "no_candidates") return "사업자번호는 찾았지만 내부 저장 후보가 없습니다.";
    if (summary.status === "corrected") return "사업자번호 기준 저장 기록으로 일부 값을 보정했습니다.";
    if (summary.status === "applied") {
      if (summary.filledCount > 0 && summary.correctedCount > 0) return "OCR이 비운 필드와 다르게 읽은 필드를 저장 기록으로 보완했습니다.";
      if (summary.filledCount > 0) return "OCR이 비운 필드를 저장 기록으로 채웠습니다.";
      return "사업자번호 기준 저장 기록으로 값을 확인했습니다.";
    }
    if (summary.status === "confirmed") return "사업자번호 기준 저장 기록과 OCR 값이 일치합니다.";
    return "자동복원이 실행되지 않았습니다.";
  };

  const renderAutofillSummary = (summary?: AutofillRunSummary) => {
    if (!summary) return null;
    const mainText =
      summary.status === "no_business_number" ? "자동복원: 사업자번호 없음" :
      summary.status === "no_candidates" ? "자동복원: 같은 사업자번호의 저장 기록 없음" :
      summary.status === "corrected" ? `자동복원: 보정 ${summary.correctedCount}건 · 확인 ${summary.confirmedCount}건` :
      summary.status === "applied" ? `자동복원: 채움 ${summary.filledCount}건 · 보정 ${summary.correctedCount}건 · 확인 ${summary.confirmedCount}건` :
      summary.status === "confirmed" ? `자동복원: 확인 ${summary.confirmedCount}건 · 보정 0건` :
      "자동복원: 미실행";
    const subText =
      summary.businessNumber
        ? `사업자번호 ${summary.businessNumber} · 저장 후보 ${summary.candidateCount}건`
        : "";
    return (
      <div
        style={{
          margin: "10px 12px 0",
          padding: "7px 10px",
          border: "1px solid rgba(99,102,241,0.18)",
          borderRadius: 6,
          background: "rgba(99,102,241,0.06)",
          color: "var(--text)",
          fontSize: 12,
          lineHeight: 1.45,
        }}
      >
        <div style={{ fontWeight: 800 }}>{mainText}</div>
        {subText && <div style={{ color: "var(--muted)", marginTop: 2 }}>{subText}</div>}
        <div style={{ color: "var(--muted)", marginTop: 2 }}>{autofillHelpText(summary)}</div>
        {hasAutofillDetail && summary.status !== "no_business_number" && summary.status !== "no_candidates" && (
          <>
            <button
              type="button"
              onClick={() => setAutofillDetailOpen((open) => !open)}
              style={{
                marginTop: 6,
                padding: 0,
                border: "none",
                background: "transparent",
                color: "#4f46e5",
                fontSize: 12,
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              {autofillDetailOpen ? "상세 접기" : "상세 보기"}
            </button>
            {autofillDetailOpen && (
              <div style={{ marginTop: 8, border: "1px solid rgba(148,163,184,0.18)", borderRadius: 6, overflow: "auto", maxHeight: 220 }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                  <thead>
                    <tr style={{ background: "rgba(148,163,184,0.08)" }}>
                      <th style={{ padding: "6px 8px", textAlign: "left", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>필드</th>
                      <th style={{ padding: "6px 8px", textAlign: "left", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>OCR 값</th>
                      <th style={{ padding: "6px 8px", textAlign: "left", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>복원 후보값</th>
                      <th style={{ width: 76, padding: "6px 8px", textAlign: "center", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>채택</th>
                    </tr>
                  </thead>
                  <tbody>
                    {autofillDetailRows.map((row, index) => (
                      <tr key={`${row.label}-${index}`}>
                        <td style={{ padding: "6px 8px", borderBottom: "1px solid rgba(148,163,184,0.08)", fontWeight: 800, whiteSpace: "nowrap" }}>{row.label}</td>
                        <td title={row.ocrValue || "빈 값"} style={{ padding: "6px 8px", borderBottom: "1px solid rgba(148,163,184,0.08)", maxWidth: 160, wordBreak: "break-word" }}>{row.ocrValue || "-"}</td>
                        <td title={row.candidate || ""} style={{ padding: "6px 8px", borderBottom: "1px solid rgba(148,163,184,0.08)", maxWidth: 180, wordBreak: "break-word" }}>{row.candidate || "-"}</td>
                        <td style={{ padding: "6px 8px", borderBottom: "1px solid rgba(148,163,184,0.08)", textAlign: "center" }}>
                          {row.action === "confirmed" ? "OCR" :
                           row.action === "corrected" ? "복원" :
                           row.action === "filled" ? "복원" :
                           row.excluded ? "제외" : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    );
  };

  const filteredValidation = editedFields.filter((f) => {
    if (validationFilter === "all") return true;
    return getValidationStatus(f) === validationFilter;
  });

  const toMarkdown = () => {
    const esc = (s: string) => s.replace(/\|/g, "\\|").replace(/\n/g, " ");
    let md = `# OCR 결과\n\n`;
    md += `- 처리 시간: **${result.processing_time.toFixed(2)}s**\n`;
    md += `- 필드 수: **${editedFields.length}건**\n\n`;
    md += `| No | 필드명 | 값 | 신뢰도 | 채택 |\n`;
    md += `|:---:|--------|-----|:------:|:---:|\n`;
    editedFields.forEach((f, i) => {
      md += `| ${i + 1} | ${esc(f.name)} | ${esc(f.value)} | ${(f.confidence * 100).toFixed(1)}% | ${getAdoptionLabel(f)} |\n`;
    });
    return md;
  };

  const toJson = () => {
    return JSON.stringify({ fields: editedFields, processing_time: result.processing_time }, null, 2);
  };

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    await ui.alert("클립보드에 복사되었습니다.");
  };

  const handleExport = (text: string, ext: string) => {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ocr_result.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const updateFieldValue = (index: number, value: string) => {
    setEditedFields((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], value, source: "text" };
      return next;
    });
  };

  return (
    <div className="or-root">
      {/* Tab bar */}
      <div className="or-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`or-tab ${activeTab === tab.key ? "or-tab-active" : ""}`}
            onClick={() => { setActiveTab(tab.key); onTabChange?.(tab.key); if (tab.key !== "validation") { onSelectField(-1); setEditingIdx(null); } }}
          >
            {tab.label}
            {tab.key === "validation" && validationCounts.error > 0 && (
              <span className="or-tab-badge or-badge-error">{validationCounts.error}</span>
            )}
            {tab.key === "validation" && validationCounts.error === 0 && validationCounts.warning > 0 && (
              <span className="or-tab-badge or-badge-warn">{validationCounts.warning}</span>
            )}
          </button>
        ))}
      </div>

      {matchSummary && (
        <div
          style={{
            margin: "10px 12px 0",
            padding: "7px 10px",
            border: "1px solid rgba(34,197,94,0.22)",
            borderRadius: 6,
            background: "rgba(34,197,94,0.08)",
            color: "var(--text)",
            fontSize: 12,
            fontWeight: 800,
          }}
        >
          저장된 정답 매칭 {matchSummary.matched}/{matchSummary.total} · {matchSummary.pct}%
        </div>
      )}

      {renderAutofillSummary(result.autofill_summary)}

      {/* Tab content */}
      <div className="or-content" ref={contentRef}>
        {/* Preview Tab */}
        {activeTab === "preview" && (
          <div className="or-preview">
            <div className="or-preview-modes">
              <button
                type="button"
                className={`ms-btn-sm ${previewMode === "markdown" ? "oc-mode-btn-active" : ""}`}
                onClick={() => setPreviewMode("markdown")}
              >
                Markdown
              </button>
              <button
                type="button"
                className={`ms-btn-sm ${previewMode === "json" ? "oc-mode-btn-active" : ""}`}
                onClick={() => setPreviewMode("json")}
              >
                JSON
              </button>
              <div style={{ flex: 1 }} />
              <button type="button" className="ms-btn-sm" onClick={() => handleExport(previewMode === "markdown" ? toMarkdown() : toJson(), previewMode === "markdown" ? "md" : "json")}>
                내보내기
              </button>
              <button type="button" className="ms-btn-sm" onClick={() => void handleCopy(previewMode === "markdown" ? toMarkdown() : toJson())}>
                복사
              </button>
            </div>
            {previewMode === "markdown" ? (
              <div
                className="or-preview-content or-markdown"
                style={{
                  display: "grid",
                  gridTemplateRows: rawOcrFields.length > 0
                    ? "minmax(0, 1fr) minmax(0, 1fr)"
                    : "minmax(0, 1fr)",
                  flex: 1,
                  minHeight: 0,
                  height: 0,
                  maxHeight: "calc(100vh - 220px)",
                  gap: 12,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    minHeight: 0,
                    overflow: "auto",
                  }}
                >
                  <Markdown remarkPlugins={[remarkGfm]}>{toMarkdown()}</Markdown>
                </div>
                {rawOcrFields.length > 0 && (
                  <div
                    style={{
                      minHeight: 0,
                      display: "flex",
                      flexDirection: "column",
                      overflow: "hidden",
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => setRawOcrOpen((v) => !v)}
                      style={{
                        cursor: "pointer",
                        color: "var(--muted)",
                        fontSize: 12,
                        fontWeight: 800,
                        userSelect: "none",
                        padding: "8px 0",
                        borderTop: "1px solid rgba(148,163,184,0.16)",
                        background: "transparent",
                        border: "none",
                        borderBottomWidth: 0,
                        textAlign: "left",
                        flexShrink: 0,
                        display: "block",
                        width: "100%",
                      }}
                    >
                      {rawOcrOpen ? "▼" : "▶"} 전체 OCR 텍스트 ({rawOcrFields.length}줄)
                    </button>
                    {rawOcrOpen && (
                    <div
                      style={{
                        flex: 1,
                        minHeight: 0,
                        overflow: "auto",
                        marginTop: 8,
                        border: "1px solid rgba(148,163,184,0.18)",
                        borderRadius: 6,
                      }}
                    >
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                        <thead>
                          <tr style={{ background: "rgba(148,163,184,0.08)" }}>
                            <th style={{ width: 44, padding: "6px 8px", textAlign: "right", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>No</th>
                            <th style={{ padding: "6px 8px", textAlign: "left", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>텍스트</th>
                            <th style={{ width: 76, padding: "6px 8px", textAlign: "right", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>신뢰도</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rawOcrFields.map((field, index) => (
                            <tr key={`${index}-${field.value || field.name}`}>
                              <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.08)" }}>
                                {index + 1}
                              </td>
                              <td style={{ padding: "5px 8px", color: "var(--text)", borderBottom: "1px solid rgba(148,163,184,0.08)", wordBreak: "break-word" }}>
                                {field.value || field.name || "-"}
                              </td>
                              <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.08)", whiteSpace: "nowrap" }}>
                                {formatConfidence(field.confidence)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <pre className="or-preview-content">{toJson()}</pre>
            )}
          </div>
        )}

        {/* Custom Tab */}
        {activeTab === "custom" && (
          <div className="or-custom">
            {/* 필드 타입 버튼 + OCR 재실행 */}
            <div className="or-custom-toolbar">
              <div className="or-custom-types">
                {FIELD_TYPES.map((ft) => (
                  <button
                    key={ft.key}
                    type="button"
                    className={`or-type-btn ${drawMode === ft.key ? "or-type-btn-active" : ""}`}
                    onClick={() => onDrawModeChange?.(drawMode === ft.key ? null : ft.key)}
                  >
                    {ft.label}
                  </button>
                ))}
              </div>
              <button type="button" className="hw-btn-primary" style={{ fontSize: 12, padding: "6px 12px" }} onClick={async () => {
                // 신뢰도 70% 미만 또는 값이 빈 필드만 재실행
                const targets = editedFields
                  .map((f, i) => ({ index: i, field: f }))
                  .filter((item) => {
                    return item.field.confidence < 0.7 || !item.field.value || item.field.value.trim() === "";
                  })
                  .map((item) => ({ index: item.index, bbox: item.field.bbox }));

                if (targets.length === 0) {
                  await ui.alert("재실행할 대상이 없습니다. (모두 100%)");
                  return;
                }

                try {
                  onScanChange?.(true);
                  const updated = await (onPartialOcr ?? onRevalidate)(targets);
                  onScanChange?.(false);
                  if (!updated || updated.length === 0) return;
                  setEditedFields((prev) => {
                    const next = [...prev];
                    updated.forEach((f: any, i: number) => {
                      const targetIdx = targets[i]?.index;
                      if (targetIdx != null && f) {
                        next[targetIdx] = { ...next[targetIdx], value: f.value, confidence: f.confidence };
                      }
                    });
                    return next;
                  });
                  // 완료 - 별도 알림 없이 결과 반영
                } catch (err) {
                  onScanChange?.(false);
                  console.error("[Partial OCR error]", err);
                  await ui.alert("OCR 재실행 중 오류가 발생했습니다.");
                }
              }}>
                OCR 재실행
              </button>
            </div>

            {/* 필드 목록 */}
            <div className="or-custom-list-header">
              <span className="or-custom-label">필드 목록</span>
              <span className="or-custom-count">{editedFields.length}건</span>
            </div>

            <div className="or-field-list">
              {editedFields.map((field, i) => (
                <div
                  key={i}
                  data-field-idx={i}
                  className={`or-field-item ${selectedIndex === i ? "or-field-item-selected" : ""}`}
                  onClick={() => onSelectField(i)}
                >
                  <div className="or-field-header">
                    <input
                      className="or-field-name-input"
                      value={field.name}
                      onChange={(e) => updateFieldName(i, e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <select
                      className="or-field-type-select"
                      value={field.field_type}
                      onChange={(e) => updateFieldType(i, e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {FIELD_TYPES.map((ft) => (
                        <option key={ft.key} value={ft.key}>{ft.label}</option>
                      ))}
                    </select>
                    <span className={`or-field-conf ${field.confidence >= 0.7 ? "" : field.confidence >= 0.4 ? "or-conf-low" : "or-conf-error"}`}>
                      <span className="or-conf-bar-wrap">
                        <span className="or-conf-bar" style={{
                          width: `${(field.confidence * 100).toFixed(0)}%`,
                          background: field.confidence >= 0.7 ? "#16a34a" : field.confidence >= 0.4 ? "#d97706" : "#dc2626",
                        }} />
                      </span>
                      {field.confidence >= 0.7 ? "✓" : field.confidence >= 0.4 ? "△" : "✕"}
                      {(field.confidence * 100).toFixed(1)}%
                    </span>
                    <span
                      title="최종값 채택 출처"
                      style={{
                        width: 28,
                        textAlign: "center",
                        fontSize: 13,
                        flexShrink: 0,
                      }}
                    >
                      {renderAdoption(field)}
                    </span>
                    <button
                      type="button"
                      className="or-field-delete"
                      onClick={(e) => { e.stopPropagation(); deleteField(i); }}
                      title="삭제"
                    >
                      ✕
                    </button>
                  </div>
                  {field.field_type === "table" ? (() => {
                    let rows: { value: string; confidence: number }[][] = [];
                    try { rows = JSON.parse(field.value); } catch { /* ignore */ }
                    return rows.length > 0 ? (
                      <div className="or-table-wrap" onClick={(e) => e.stopPropagation()}>
                        <table className="or-table-result">
                          <tbody>
                            {rows.map((row, ri) => (
                              <tr key={ri}>
                                {row.map((cell, ci) => (
                                  <td
                                    key={ci}
                                    className={`or-table-cell ${cell.confidence < 0.7 ? "or-table-cell-low" : ""}`}
                                    title={`신뢰도: ${(cell.confidence * 100).toFixed(1)}%`}
                                  >
                                    {cell.value || "-"}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="or-empty" style={{ fontSize: 12 }}>테이블 데이터 없음</div>
                    );
                  })() : (
                    <input
                      className="or-field-input"
                      value={field.value}
                      onChange={(e) => updateFieldValue(i, e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      placeholder="인식된 값"
                    />
                  )}
                  {field.source && field.source !== "ocr" && (
                    <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 6 }}>
                      {renderAutofillActionBadge(field) ?? renderSourceBadge(field.source)}
                    </div>
                  )}
                  {(!field.source || field.source === "ocr") && field.autofillAction && field.autofillAction !== "none" && (
                    <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 6 }}>
                      {renderAutofillActionBadge(field)}
                    </div>
                  )}
                </div>
              ))}
              {editedFields.length === 0 && (
                <div className="or-empty">인식된 필드가 없습니다.</div>
              )}
            </div>
          </div>
        )}

        {/* Validation Tab */}
        {activeTab === "validation" && (() => {
          const errorFields = editedFields
            .map((f, i) => ({ field: f, idx: i, status: getValidationStatus(f) }))
            .filter((item) => {
              // 신뢰도 구간 필터
              if (confRange !== null) {
                const pct = item.field.confidence * 100;
                return pct >= confRange && pct < confRange + 10;
              }
              if (validationFilter === "all") return true;
              return item.status === validationFilter;
            });

          const currentEditing = editingIdx != null ? editedFields[editingIdx] : null;

          const navigateError = (direction: "prev" | "next") => {
            const targets = editedFields
              .map((f, i) => ({ idx: i, status: getValidationStatus(f) }))
              .filter((item) => item.status === "warning" || item.status === "error");
            if (targets.length === 0) return;

            if (editingIdx == null) {
              setEditingIdx(targets[0].idx);
              setEditValue(editedFields[targets[0].idx].value);
              onSelectField(targets[0].idx);
              return;
            }

            const curPos = targets.findIndex((t) => t.idx === editingIdx);
            let nextPos: number;
            if (direction === "next") {
              nextPos = curPos < targets.length - 1 ? curPos + 1 : 0;
            } else {
              nextPos = curPos > 0 ? curPos - 1 : targets.length - 1;
            }
            setEditingIdx(targets[nextPos].idx);
            setEditValue(editedFields[targets[nextPos].idx].value);
            onSelectField(targets[nextPos].idx);
          };

          const applyEdit = () => {
            if (editingIdx == null) return;
            updateFieldValue(editingIdx, editValue);
          };

          return (
            <div className="or-validation">
              {/* 상태 필터 */}
              <div className="or-validation-filters">
                {(["success", "warning", "error"] as const).map((filter) => (
                  <button
                    key={filter}
                    type="button"
                    className={`or-vf-btn or-vf-${filter} ${validationFilter === filter && confRange === null ? "or-vf-active" : ""}`}
                    onClick={() => { setValidationFilter(filter); setConfRange(null); }}
                  >
                    {filter === "success" ? `성공` : filter === "warning" ? `경고` : `오류`}
                  </button>
                ))}
              </div>

              {/* 신뢰도 구간 필터 */}
              <div className="or-conf-range-filters">
                <button
                  type="button"
                  className={`or-conf-range-btn ${confRange === null && validationFilter === "all" ? "or-conf-range-active" : ""}`}
                  onClick={() => { setConfRange(null); setValidationFilter("all"); }}
                >
                  전체
                </button>
                {[70, 80, 90].map((r) => {
                  const count = editedFields.filter((f) => {
                    const pct = f.confidence * 100;
                    return pct >= r && pct < r + 10;
                  }).length;
                  return (
                    <button
                      key={r}
                      type="button"
                      className={`or-conf-range-btn ${confRange === r ? "or-conf-range-active" : ""} ${count === 0 ? "or-conf-range-empty" : ""}`}
                      onClick={() => { setConfRange(r); setValidationFilter("all"); }}
                    >
                      {r}~{r + 10}%
                      {count > 0 && <span className="or-conf-range-count">{count}</span>}
                    </button>
                  );
                })}
              </div>

              {/* 건수 + 재검증 */}
              <div className="or-val-summary">
                {validationFilter === "success" ? (
                  <span className="or-val-summary-text">
                    성공 <b>{validationCounts.success}</b>건 / 경고 <b>{validationCounts.warning}</b>건 / 오류 <b>{validationCounts.error}</b>건
                  </span>
                ) : (
                  <span className="or-val-summary-text">
                    {validationFilter === "warning" ? "경고" : "오류"}{" "}
                    <b>{errorFields.length}</b>건
                  </span>
                )}
                {validationFilter !== "success" && (
                  <button type="button" className="ms-btn-sm" disabled={isRevalidating} onClick={async () => {
                    if (isRevalidating) return;
                    try {
                      const targets = errorFields.map((item) => ({
                        index: item.idx,
                        bbox: item.field.bbox,
                      }));
                      if (targets.length === 0) return;
                      setIsRevalidating(true);
                      onScanChange?.(true);
                      const updated = await onRevalidate(targets);
                      onScanChange?.(false);
                      setIsRevalidating(false);
                      if (!updated || updated.length === 0) {
                        await ui.alert("재검증 결과가 없습니다.");
                        return;
                      }
                      setEditedFields((prev) => {
                        const next = [...prev];
                        updated.forEach((f: any, i: number) => {
                          const targetIdx = targets[i]?.index;
                          if (targetIdx != null && f) {
                            next[targetIdx] = { ...next[targetIdx], value: f.value, confidence: f.confidence };
                          }
                        });
                        return next;
                      });
                      await ui.alert(`재검증 완료: ${targets.length}개 필드 처리됨`);
                    } catch (err) {
                      onScanChange?.(false);
                      setIsRevalidating(false);
                      console.error("[Revalidate error]", err);
                      await ui.alert("재검증 중 오류가 발생했습니다.");
                    }
                  }}>
                    {isRevalidating
                      ? `재검증 중... (${errorFields.length}건)`
                      : validationFilter === "warning" ? "경고 재검증" : "오류 재검증"}
                  </button>
                )}
              </div>

              {/* 내역 */}
              <div className="or-val-section-title">
                {validationFilter === "success" ? "성공 내역" : validationFilter === "warning" ? "경고 내역" : "오류 내역"}
              </div>
              <div className="or-val-error-list">
                {errorFields.length === 0 ? (
                  <div className="or-empty">해당 항목이 없습니다.</div>
                ) : (
                  errorFields.map((item) => (
                    <div
                      key={item.idx}
                      data-field-idx={item.idx}
                      className={`or-val-error-row ${editingIdx === item.idx ? "or-val-error-row-active" : ""}`}
                      onClick={() => {
                        setEditingIdx(item.idx);
                        setEditValue(item.field.value);
                        onSelectField(item.idx);
                      }}
                    >
                      <span className={`or-val-dot or-dot-${item.status}`} />
                      <span className="or-val-error-name">{item.field.name}</span>
                      <span className="or-val-error-value">{item.field.value || "(빈값)"}</span>
                      <span className="or-val-error-conf">{(item.field.confidence * 100).toFixed(1)}%</span>
                    </div>
                  ))
                )}
              </div>

              {/* 선택 필드 수정 */}
              {currentEditing && (
                <div className="or-val-edit-section">
                  <div className="or-val-section-title">필드 수정</div>
                  <div className="or-val-edit-info">
                    <span className="or-val-edit-field">{currentEditing.name}</span>
                    <span className="or-field-type">{currentEditing.field_type}</span>
                  </div>
                  <div className="or-val-edit-info" style={{ fontSize: 11, color: "var(--muted)" }}>
                    위치: [{currentEditing.bbox.join(", ")}]
                  </div>

                  <div className="or-val-edit-row">
                    <span className="or-val-label">현재 값:</span>
                    <input className="or-field-input" value={currentEditing.value} readOnly />
                  </div>

                  <div className="or-val-edit-row">
                    <span className="or-val-label">수정 값:</span>
                    <input
                      className="or-field-input"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                    />
                    <button type="button" className="ms-btn-sm" onClick={applyEdit}>수정</button>
                  </div>

                  <div className="or-val-edit-nav">
                    <button type="button" className="ms-btn-sm" onClick={() => navigateError("prev")}>이전</button>
                    <button type="button" className="ms-btn-sm" onClick={() => navigateError("next")}>다음</button>
                  </div>
                </div>
              )}
            </div>
          );
        })()}
      </div>

    </div>
  );
}
