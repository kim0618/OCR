"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AutofillAction, AutofillRunSummary, AutofillSuggestion, OutputValueSource } from "@/lib/autofillEngine";
import { getGroundTruth, compareToGt, fieldKey } from "@/lib/groundTruthStore";
import { useUi } from "../common/AppProviders";
import { resolveFieldLabel } from "@/lib/invoiceFieldLabels";

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
  original_image?: string;
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
  jobId?: string | null;
  createdAt?: string | null;
  onClose?: () => void;
  onPersist?: (fields: OcrFieldResult[]) => void;
};

type TabKey = "preview" | "custom" | "validation";

export default function OcrResultPanel({ result, onRerun, onRevalidate, selectedIndex, onSelectField, templateName, fileName, onTabChange, drawMode, onDrawModeChange, isScanning, onScanChange, onPartialOcr, canvasRegions, jobId, createdAt, onClose, onPersist }: Props) {
  const ui = useUi();
  const [activeTab, setActiveTab] = useState<TabKey>("preview");
  const [previewMode, setPreviewMode] = useState<"markdown" | "json">("markdown");
  const [editedFields, setEditedFields] = useState<OcrFieldResult[]>(result.fields);
  const [activeFieldType, setActiveFieldType] = useState<string>("field");
  const [rawOcrOpen, setRawOcrOpen] = useState(true);
  const [autofillDetailOpen, setAutofillDetailOpen] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const editedFieldsRef = useRef<OcrFieldResult[]>(editedFields);
  useEffect(() => { editedFieldsRef.current = editedFields; }, [editedFields]);

  // onBlur/구조변경 시 호출되는 자동저장. jobId 가 있을 때만 동작.
  const flushSave = () => {
    if (!jobId || !onPersist) return;
    onPersist(editedFieldsRef.current);
    setLastSavedAt(new Date());
  };

  // 컴포넌트 unmount 또는 jobId 변경(다음 OCR) 직전에 미저장분 flush.
  useEffect(() => {
    return () => {
      if (jobId && onPersist) {
        onPersist(editedFieldsRef.current);
      }
    };
  }, [jobId, onPersist]);

  // canvasRegions에서 새로 그린 영역을 editedFields에 동기화
  useEffect(() => {
    if (!canvasRegions) return;
    setEditedFields((prev) => {
      let changed = false;
      const next = [...prev];
      canvasRegions.forEach((r) => {
        if (!r.id.startsWith("ocr_")) return;
        const index = Number(r.id.slice("ocr_".length));
        if (!Number.isInteger(index) || index < 0 || !next[index]) return;
        const bbox = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
        const current = next[index];
        const sameBbox =
          Array.isArray(current.bbox) &&
          current.bbox.length >= 4 &&
          current.bbox.slice(0, 4).every((value, i) => value === bbox[i]);
        if (sameBbox && current.sourceBboxes?.length === 1) return;
        next[index] = {
          ...current,
          field_type: r.fieldType || current.field_type,
          bbox,
          sourceBboxes: [{ x: bbox[0], y: bbox[1], width: bbox[2], height: bbox[3] }],
        };
        changed = true;
      });
      return changed ? next : prev;
    });
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

  const FIELD_TYPE_DESCRIPTIONS: Record<string, string> = {
    field: "단일 영역에서 하나의 값을 읽습니다.",
    multi: "여러 영역 또는 여러 줄을 합쳐 하나의 값으로 사용합니다.",
    check: "체크 여부나 선택 상태를 판정합니다.",
    table: "반복되는 표 영역을 읽습니다.",
  };

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

  const goToCustomField = (index: number) => {
    setActiveTab("custom");
    onTabChange?.("custom");
    onDrawModeChange?.(null);
    onSelectField(index);
    setTimeout(() => {
      const el = contentRef.current?.querySelector(`[data-field-idx="${index}"]`) as HTMLElement | null;
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 80);
  };

  const validationSummaryMessage =
    validationCounts.error > 0
      ? "\uC800\uC7A5 \uC804 \uC218\uC815\uC774 \uD544\uC694\uD55C \uD544\uB4DC\uAC00 \uC788\uC2B5\uB2C8\uB2E4."
      : validationCounts.warning > 0
        ? "\uC800\uC7A5\uC740 \uAC00\uB2A5\uD558\uC9C0\uB9CC \uD655\uC778\uC774 \uD544\uC694\uD55C \uD544\uB4DC\uAC00 \uC788\uC2B5\uB2C8\uB2E4."
        : "\uC800\uC7A5 \uAC00\uB2A5\uD55C \uC0C1\uD0DC\uC785\uB2C8\uB2E4.";

  const validationState =
    validationCounts.error > 0
      ? { key: "error", label: "\uC218\uC815 \uD544\uC694" }
      : validationCounts.warning > 0
        ? { key: "warning", label: "\uD655\uC778 \uD544\uC694" }
        : { key: "success", label: "\uC800\uC7A5 \uAC00\uB2A5" };
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

  const getAdoptionLabel = (field: OcrFieldResult): "OCR" | "복원" | "직접입력" | "-" => {
    if (field.autofillAction === "confirmed") return "OCR";
    if (field.autofillAction === "corrected") return "복원";
    if (field.autofillAction === "filled") return "복원";
    if (field.source === "text") return "직접입력";
    if (field.source === "biz" || field.source === "gt") return "복원";
    if (field.value && String(field.value).trim()) return "OCR";
    return "-";
  };

  const renderAdoption = (field: OcrFieldResult) => {
    const label = getAdoptionLabel(field);
    const color =
      label === "OCR" ? "#2563eb" :
      label === "복원" ? "#4f46e5" :
      label === "직접입력" ? "#a855f7" :
      "var(--muted)";
    return <span style={{ color, fontWeight: 900 }}>{label}</span>;
  };

  const getOriginalOcrValue = (field: OcrFieldResult) => {
    if (typeof field.original === "string" && field.original.trim()) return field.original.trim();
    if ((!field.source || field.source === "ocr") && field.value && String(field.value).trim()) {
      return String(field.value).trim();
    }
    return "-";
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

  const fieldLabel = (field: OcrFieldResult) => {
    const { primary } = resolveFieldLabel({ name: field.name, ko: field.ko, en: field.en });
    return primary;
  };

  const fieldLabelFull = (field: OcrFieldResult) => {
    const { primary, secondary } = resolveFieldLabel({ name: field.name, ko: field.ko, en: field.en });
    if (secondary && secondary !== primary) return `${primary} (${secondary})`;
    return primary;
  };

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
    const candidate = field.applied || field.suggestions?.[0]?.value || "";
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


  // Parse table field rows and compute display orientation.
  // Rules:
  //   - All rows have uniform N > 1 columns → real multi-row table, keep as-is.
  //   - Otherwise (single-col rows, or jagged/mixed column counts) → flatten all
  //     cells into one display row (transposed representation).
  const parseTableField = (value: string) => {
    let rows: { value: string; confidence: number }[][] = [];
    try { rows = JSON.parse(value); } catch { /* ignore */ }
    const nonEmpty = rows.filter((r) => r.length > 0);
    const colCounts = nonEmpty.map((r) => r.length);
    const uniqueCounts = new Set(colCounts);
    const firstCount = nonEmpty[0]?.length ?? 0;
    // Keep original multi-row structure only when all non-empty rows share the
    // same column count AND that count is > 1 (genuine multi-row table).
    const keepAsIs = uniqueCounts.size === 1 && firstCount > 1;
    const displayRows = keepAsIs
      ? rows
      : [nonEmpty.flatMap((r) => r)]; // flatten all cells into 1 row
    const actualRows = keepAsIs ? nonEmpty.length : 1;
    const rowLabel = actualRows === 1
      ? `${nonEmpty.flatMap((r) => r).length}항목, 1행`
      : `${actualRows}행`;
    return { rows, nonEmpty, displayRows, isSingleCol: !keepAsIs, rowLabel };
  };

  const toMarkdown = () => {
    const esc = (s: string) => s.replace(/\|/g, "\\|").replace(/\n/g, " ");
    let md = `# OCR 결과\n\n`;
    md += `- 처리 시간: **${result.processing_time.toFixed(2)}s**\n`;
    md += `- 필드 수: **${editedFields.length}건**\n\n`;
    md += `| No | 필드명 | 값 | 신뢰도 | 채택 |\n`;
    md += `|:---:|--------|-----|:------:|:---:|\n`;

    editedFields.forEach((f, i) => {
      const label = fieldLabelFull(f);
      if (f.field_type === "table") {
        const { rowLabel } = parseTableField(f.value);
        md += `| ${i + 1} | ${esc(label)} | 표 데이터 (${rowLabel}) | ${(f.confidence * 100).toFixed(1)}% | ${getAdoptionLabel(f)} |\n`;
      } else {
        md += `| ${i + 1} | ${esc(label)} | ${esc(f.value)} | ${(f.confidence * 100).toFixed(1)}% | ${getAdoptionLabel(f)} |\n`;
      }
    });

    return md;
  };

  // Table field list for JSX rendering in Preview tab (separate from Markdown)
  const previewTableFields = useMemo(() =>
    editedFields
      .map((f, i) => ({ f, i }))
      .filter(({ f }) => f.field_type === "table")
      .map(({ f, i }) => ({ idx: i + 1, label: fieldLabelFull(f), ...parseTableField(f.value) }))
      .filter(({ nonEmpty }) => nonEmpty.length > 0),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [editedFields]);

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
      const current = next[index];
      const original =
        current.original ??
        (!current.source || current.source === "ocr" ? current.value : undefined);
      next[index] = { ...current, value, source: "text", original };
      return next;
    });
  };

  const formatHHMM = (d: Date) => {
    const h = String(d.getHours()).padStart(2, "0");
    const m = String(d.getMinutes()).padStart(2, "0");
    return `${h}:${m}`;
  };
  const headerCreatedAt = createdAt ?? "";

  return (
    <div className="or-root">
      {/* Detail header — 템플릿/파일 컨텍스트 + 자동저장 인디케이터 + 닫기 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 10,
          padding: "8px 12px",
          background: "var(--panel2)",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0, flex: 1 }}>
          {templateName && (
            <span
              title="템플릿 이름"
              style={{
                fontSize: 12,
                fontWeight: 800,
                color: "var(--accent)",
                padding: "2px 9px",
                border: "1px solid var(--border)",
                borderRadius: 999,
                background: "var(--panel2)",
                whiteSpace: "nowrap",
                flexShrink: 0,
              }}
            >
              {templateName}
            </span>
          )}
          {fileName && (
            <span
              title={fileName}
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: "var(--text)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                minWidth: 0,
              }}
            >
              {fileName}
            </span>
          )}
          {headerCreatedAt && (
            <span style={{ fontSize: 11, color: "var(--muted)", whiteSpace: "nowrap" }}>
              {headerCreatedAt}
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          {jobId && lastSavedAt && (
            <span style={{ fontSize: 11, color: "var(--muted)", whiteSpace: "nowrap" }}>
              저장됨 · {formatHHMM(lastSavedAt)}
            </span>
          )}
          {onClose && (
            <button
              type="button"
              aria-label="닫기"
              onClick={onClose}
              style={{
                width: 26,
                height: 26,
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--panel2)",
                color: "var(--text)",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                lineHeight: 1,
                flexShrink: 0,
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Tab bar */}
      <div className="or-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`or-tab ${activeTab === tab.key ? "or-tab-active" : ""}`}
            onClick={() => { setActiveTab(tab.key); onTabChange?.(tab.key); if (tab.key !== "validation") onSelectField(-1); }}
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
                    ? "minmax(0, 7fr) minmax(0, 3fr)"
                    : "minmax(0, 1fr)",
                  flex: 1,
                  minHeight: 0,
                  height: 0,
                  maxHeight: "calc(100vh - 220px)",
                  gap: 12,
                  overflow: "hidden",
                }}
              >
                <div style={{ minHeight: 0, overflow: "auto" }}>
                  <Markdown remarkPlugins={[remarkGfm]}>{toMarkdown()}</Markdown>
                  {/* Table fields rendered as JSX (reliable layout, not markdown) */}
                  {previewTableFields.map(({ idx, label, displayRows, rowLabel }) => (
                    <div key={idx} style={{ marginTop: 12 }}>
                      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6 }}>
                        {idx}. {label}
                        <span style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)", marginLeft: 8 }}>{rowLabel}</span>
                      </div>
                      <div className="or-table-wrap">
                        <table className="or-table-result">
                          <tbody>
                            {displayRows.map((row, ri) => (
                              <tr key={ri}>
                                {row.map((cell, ci) => (
                                  <td key={ci} className={`or-table-cell ${cell.confidence < 0.7 ? "or-table-cell-low" : ""}`}
                                    title={`신뢰도: ${(cell.confidence * 100).toFixed(1)}%`}>
                                    {cell.value || "-"}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
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
            <div className="or-custom-guide">
              <span>필드 영역 수정, 필드 추가, OCR 재실행, 최종값 입력을 진행하는 작업 공간입니다.</span>
              <span>직접 입력한 값은 최종값으로 사용되며 Validation에 자동 반영됩니다.</span>
            </div>
            {/* 필드 타입 버튼 + OCR 재실행 */}
            <div className="or-custom-toolbar">
              <div className="or-custom-types">
                {FIELD_TYPES.map((ft) => (
                  <button
                    key={ft.key}
                    type="button"
                    className={`or-type-btn ${drawMode === ft.key ? "or-type-btn-active" : ""}`}
                    title={FIELD_TYPE_DESCRIPTIONS[ft.key]}
                    onClick={() => {
                      const nextMode = drawMode === ft.key ? null : ft.key;
                      setActiveFieldType(nextMode ?? "field");
                      onDrawModeChange?.(nextMode);
                    }}
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
                        next[targetIdx] = { ...next[targetIdx], value: f.value, confidence: f.confidence, source: "ocr" };
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
            <div className="or-custom-type-help">
              {FIELD_TYPE_DESCRIPTIONS[drawMode ?? activeFieldType] ?? FIELD_TYPE_DESCRIPTIONS.field}
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
                    <span
                      style={{ flex: 1, minWidth: 0, fontSize: 11, fontWeight: 700, color: "var(--text)", lineHeight: 1.3, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
                      title={`${fieldLabelFull(field)} (${field.name})`}
                    >
                      {fieldLabel(field)}
                      <span style={{ fontSize: 9, fontWeight: 400, color: "var(--muted)", marginLeft: 4 }}>
                        {field.en || field.name}
                      </span>
                    </span>
                    <select
                      className="or-field-type-select"
                      value={field.field_type}
                      onChange={(e) => { updateFieldType(i, e.target.value); flushSave(); }}
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
                        minWidth: 28,
                        textAlign: "center",
                        fontSize: 13,
                        flexShrink: 0,
                        display: "inline-flex",
                        alignItems: "center",
                      }}
                    >
                      {renderAdoption(field)}
                    </span>
                    <button
                      type="button"
                      className="or-field-delete"
                      onClick={(e) => { e.stopPropagation(); deleteField(i); flushSave(); }}
                      title="삭제"
                    >
                      ✕
                    </button>
                  </div>
                  {field.field_type === "table" ? (() => {
                    const { rows, displayRows, isSingleCol, rowLabel } = parseTableField(field.value);
                    const firstRowPreview = displayRows[0]
                      ? displayRows[0].map((c) => c.value).filter(Boolean).slice(0, 4).join(" / ")
                      : "";
                    return rows.length > 0 ? (
                      <>
                        <div className="or-field-value-meta" onClick={(e) => e.stopPropagation()}>
                          <span style={{ fontWeight: 700, color: "var(--accent)" }}>표 데이터 · {rowLabel}</span>
                          {firstRowPreview && (
                            <span style={{ color: "var(--muted)", fontSize: 11 }} title="첫 번째 행 미리보기">
                              {firstRowPreview.length > 50 ? firstRowPreview.slice(0, 48) + "…" : firstRowPreview}
                            </span>
                          )}
                          <span>채택: {getAdoptionLabel(field)}</span>
                        </div>
                        <div className="or-table-wrap" onClick={(e) => e.stopPropagation()}>
                          <table className="or-table-result">
                            <tbody>
                              {displayRows.map((row, ri) => (
                                <tr key={ri}>
                                  {row.map((cell, ci) => {
                                    // Map display (ri,ci) back to original rows index for editing
                                    const origRowIdx = isSingleCol ? ci : ri;
                                    const origColIdx = isSingleCol ? 0 : ci;
                                    return (
                                      <td
                                        key={ci}
                                        className={`or-table-cell ${cell.confidence < 0.7 ? "or-table-cell-low" : ""}`}
                                        title={`신뢰도: ${(cell.confidence * 100).toFixed(1)}%`}
                                        style={{ padding: 0 }}
                                      >
                                        <textarea
                                          className="or-table-cell-input"
                                          value={cell.value || ""}
                                          rows={1}
                                          onChange={(e) => {
                                            // auto-grow
                                            e.target.style.height = "auto";
                                            e.target.style.height = e.target.scrollHeight + "px";
                                            const newValue = e.target.value;
                                            updateFieldValue(i, (() => {
                                              const updated = rows.map((r) => [...r]);
                                              updated[origRowIdx][origColIdx] = { ...updated[origRowIdx][origColIdx], value: newValue };
                                              return JSON.stringify(updated);
                                            })());
                                          }}
                                          onFocus={() => onSelectField(i)}
                                          onBlur={flushSave}
                                        />
                                      </td>
                                    );
                                  })}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    ) : (
                      <div className="or-empty" style={{ fontSize: 12 }}>테이블 데이터 없음</div>
                    );
                  })() : (
                    <div className="or-field-value-editor" onClick={(e) => e.stopPropagation()}>
                      <div className="or-field-value-meta">
                        <span>OCR 원본: {getOriginalOcrValue(field)}</span>
                        <span>채택: {getAdoptionLabel(field)}</span>
                      </div>
                      <label className="or-field-final-label" htmlFor={`or-field-final-${i}`}>최종값</label>
                      <input
                        id={`or-field-final-${i}`}
                        className="or-field-input"
                        value={field.value}
                        onChange={(e) => updateFieldValue(i, e.target.value)}
                        onFocus={() => onSelectField(i)}
                        onBlur={flushSave}
                        placeholder="최종값 입력"
                      />
                    </div>
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
          const rows = editedFields.map((field, idx) => {
            const status = getValidationStatus(field);
            return { field, idx, status };
          });
          const sections = [
            { status: "error", title: "\uC624\uB958 \uB0B4\uC5ED", rows: rows.filter((item) => item.status === "error") },
            { status: "warning", title: "\uACBD\uACE0 \uB0B4\uC5ED", rows: rows.filter((item) => item.status === "warning") },
            { status: "success", title: "\uC131\uACF5 \uB0B4\uC5ED", rows: rows.filter((item) => item.status === "success") },
          ] as const;

          return (
            <div className="or-validation">
              <div className="or-val-summary">
                <div className="or-val-summary-main">
                  <div className="or-val-summary-heading">
                    <span className="or-val-summary-title">{"\uAC80\uC218 \uACB0\uACFC"}</span>
                    <span className={"or-val-state-badge or-val-state-" + validationState.key}>
                      {validationState.label}
                    </span>
                  </div>
                  <span className="or-val-summary-text">
                    {"\uC624\uB958"} <b>{validationCounts.error}</b>{"\uAC74 / \uACBD\uACE0"} <b>{validationCounts.warning}</b>{"\uAC74 / \uC131\uACF5"} <b>{validationCounts.success}</b>{"\uAC74"}
                  </span>
                  <span className="or-val-summary-guide">{validationSummaryMessage}</span>
                </div>
              </div>

              <div className="or-val-review-list">
                {sections.map((section) => (
                  <section key={section.status} className="or-val-review-section">
                    <div className="or-val-section-title">
                      <span>
                        {section.title}: {section.rows.length === 0 ? "\uC5C6\uC74C" : section.rows.length + "\uAC74"}
                      </span>
                      {section.status === "error" && section.rows.length > 0 && (
                        <button type="button" className="ms-btn-sm" onClick={() => goToCustomField(section.rows[0].idx)}>
                          {"\uC624\uB958 \uC218\uC815"}
                        </button>
                      )}
                      {section.status === "warning" && section.rows.length > 0 && (
                        <button type="button" className="ms-btn-sm" onClick={() => goToCustomField(section.rows[0].idx)}>
                          {"\uACBD\uACE0 \uD655\uC778"}
                        </button>
                      )}
                    </div>
                    {section.rows.length === 0 ? (
                      <div className="or-val-empty-line">{"\uD574\uB2F9 \uD56D\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."}</div>
                    ) : (
                      <div className="or-val-error-list">
                        {section.rows.map((item) => {
                          if (item.field.field_type === "table") {
                            const { displayRows, rowLabel } = parseTableField(item.field.value);
                            return (
                              <div
                                key={item.idx}
                                data-field-idx={item.idx}
                                className={"or-val-error-row or-val-review-row or-val-" + item.status}
                                style={{ display: "block", overflow: "hidden" }}
                                onClick={() => onSelectField(item.idx)}
                              >
                                {/* 헤더: 일반 필드와 동일한 grid */}
                                <div style={{
                                  display: "grid",
                                  gridTemplateColumns: "10px minmax(120px, 1.6fr) minmax(0, 2.8fr) 52px 58px",
                                  gap: 8,
                                  alignItems: "center",
                                  marginBottom: displayRows.length > 0 ? 6 : 0,
                                }}>
                                  <span className={"or-val-dot or-dot-" + item.status} />
                                  <span className="or-val-error-name" title={fieldLabelFull(item.field)}>
                                    {fieldLabel(item.field)}
                                  </span>
                                  <span style={{ color: "var(--accent)", fontWeight: 700, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                    표 데이터 · {rowLabel}
                                  </span>
                                  <span className={"or-val-adoption or-val-adoption-" + getAdoptionLabel(item.field)}>{getAdoptionLabel(item.field)}</span>
                                  <span className="or-val-error-conf">{formatConfidence(item.field.confidence)}</span>
                                </div>
                                {/* 표 데이터 */}
                                {displayRows.length > 0 && (
                                  <div
                                    className="or-table-wrap"
                                    onClick={(e) => e.stopPropagation()}
                                    style={{ marginLeft: 18, width: "calc(100% - 18px)" }}
                                  >
                                    <table className="or-table-result">
                                      <tbody>
                                        {displayRows.map((row, ri) => (
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
                                )}
                              </div>
                            );
                          }
                          return (
                            <div
                              key={item.idx}
                              data-field-idx={item.idx}
                              className={"or-val-error-row or-val-review-row or-val-" + item.status}
                              onClick={() => onSelectField(item.idx)}
                            >
                              <span className={"or-val-dot or-dot-" + item.status} />
                              <span className="or-val-error-name" title={fieldLabelFull(item.field)}>
                                {fieldLabel(item.field)}
                              </span>
                              <span className="or-val-error-value">{item.field.value || "-"}</span>
                              <span className={"or-val-adoption or-val-adoption-" + getAdoptionLabel(item.field)}>{getAdoptionLabel(item.field)}</span>
                              <span className="or-val-error-conf">{formatConfidence(item.field.confidence)}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </section>
                ))}
              </div>
            </div>
          );
        })()}
      </div>

    </div>
  );
}
