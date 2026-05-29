/**
 * OCR 결과 패널.
 *
 * 역할:
 * - Preview / Custom / Validation / Clean JSON / Markdown / Raw JSON 탭을
 *   통해 OCR 결과를 다양한 표현 방식으로 보여준다.
 * - 편집 모드 / 재검증 / 부분 OCR / 자동저장(onPersist) / 결과 닫기
 *   사용자 인터랙션을 제공한다.
 * - 표시용 변환은 외부 helper 에 위임한다:
 *     · Clean JSON      → @/lib/cleanJsonBuilder
 *     · Markdown        → @/lib/markdownReportBuilder
 *     · table view model→ @/lib/structuredTableViewModel
 *     · invoice 컬럼 표시→ @/lib/invoiceTableDisplay
 *
 * Boundary:
 * - OCR API 호출(엔드포인트/엔진 선택) 책임 없음.
 * - 문서 viewer / bbox overlay 책임 없음 (OcrDocViewer).
 * - 히스토리 저장 책임 없음 — 편집 결과는 onPersist 콜백으로 부모에게 전달.
 * - 재검증/부분 OCR API 호출은 부모(RunOcrWorkspace)가 주입한
 *   onRevalidate / onPartialOcr 콜백으로 위임된다.
 */
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { AutofillAction, AutofillRunSummary, AutofillSuggestion, OutputValueSource } from "@/common/utils/autofillEngine";
import { getGroundTruth, compareToGt, fieldKey } from "@/common/storage/groundTruthStore";
import { useUi } from "../../layout/AppProviders";
import {
  INVOICE_COL_LABEL_MAP as _ALL_COL_LABEL_MAP,
  isInternalTableKey as isInternalKey,
  normalizeTableCell as normalizeCell,
  isMeaninglessTableValue as isMeaningless,
  hasMeaningfulTableValue as hasMeaningfulValue,
  buildInvoicePreviewCols,
} from "@/common/utils/invoiceTableDisplay";
import { buildCleanJsonResult, type CleanJsonResult } from "@/common/utils/cleanJsonBuilder";
import {
  fieldLabel,
  fieldLabelFull,
  getAdoptionLabel,
  isAmountLikeField,
  parseTableField,
} from "@/common/utils/ocrResultFormatters";
import { buildMarkdownReport } from "@/common/utils/markdownReportBuilder";
import { buildStructuredTableViewModel } from "@/common/utils/structuredTableViewModel";
import {
  buildTableResultViewModels,
  selectRepresentativeTableResultViewModels,
  type TableResultViewModel,
} from "@/common/utils/tableResultViewModel";

// UI-PREVIEW-10A-fix: fixed-layout + colgroup 방식 — key가 폭을 밀지 않음
const _IDX_KEYS  = new Set(["rowIndex", "no", "rowNo", "lineNo", "seq"]);
const _CODE_KEYS = new Set(["itemCode", "insuranceCode", "serialNo", "lotNo", "manufacturingNo"]);
const _WIDE_KEYS = new Set(["itemName", "manufacturer"]);
const _NUM_KEYS  = new Set(["quantity", "unitPrice", "consumerUnitPrice", "supplyUnitPrice",
                             "amount", "supplyAmount", "taxAmount", "totalAmount"]);

function _invoiceColWidth(key: string): string {
  if (_IDX_KEYS.has(key))  return "52px";
  if (key === "quantity")  return "64px";
  if (_NUM_KEYS.has(key))  return "92px";
  if (_CODE_KEYS.has(key)) return "96px";
  if (_WIDE_KEYS.has(key)) return "auto";
  return "82px";
}

function _invoiceDataAlign(key: string): React.CSSProperties["textAlign"] {
  if (_IDX_KEYS.has(key)) return "center";
  if (_NUM_KEYS.has(key)) return "right";
  return "left";
}





function _cleanTableLabel(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function _isInvoiceStatementTable(vm: TableResultViewModel): boolean {
  return _cleanTableLabel(vm.meta.documentType) === "invoice_statement";
}

function _isGenericTableLabel(label: string): boolean {
  return label === "문서 표" || /^테이블\s*\d+$/.test(label) || /^table[_\s-]*\d+$/i.test(label);
}

function _isPrimaryInvoiceTableKey(tableKey: string): boolean {
  return tableKey === "table_1" || tableKey === "document_fields.tableRows";
}

function _tableNumberFallback(tableKey: string, fallbackIndex: number): string {
  const match = tableKey.match(/(?:^|[_\s.-])(?:table|unstructured)[_\s.-]*(\d+)$/i);
  return `테이블 ${match?.[1] ?? fallbackIndex + 1}`;
}

function resolveResultTableLabel(
  vm: TableResultViewModel,
  fallbackIndex: number,
  fieldLabelText?: string,
): string {
  const labelKo = _cleanTableLabel(vm.labelKo);
  const labelEn = _cleanTableLabel(vm.labelEn);
  const fieldLabelClean = _cleanTableLabel(fieldLabelText);

  if (labelKo && !(_isInvoiceStatementTable(vm) && _isPrimaryInvoiceTableKey(vm.tableKey) && _isGenericTableLabel(labelKo))) {
    return labelKo;
  }
  if (labelEn && !(_isInvoiceStatementTable(vm) && _isPrimaryInvoiceTableKey(vm.tableKey) && _isGenericTableLabel(labelEn))) {
    return labelEn;
  }
  if (_isInvoiceStatementTable(vm) && _isPrimaryInvoiceTableKey(vm.tableKey)) return "품목표";
  if (fieldLabelClean && !_isGenericTableLabel(fieldLabelClean)) return fieldLabelClean;
  return _tableNumberFallback(vm.tableKey, fallbackIndex);
}

// LOT계열 / 제조번호계열 / itemCode계열 key셋
const _LOT_KEYS = new Set(["lotNo", "serialLot", "lot", "lotNumber"]);
const _MFG_KEYS = new Set(["manufacturingNo", "manufactureNo", "mfgNo"]);
const _ITEMCODE_KEYS = new Set(["itemCode", "productCode"]);

// fix5: Preview majority rule — 95% 이상 비어있거나 중복이면 숨김
const PREVIEW_COLUMN_HIDE_RATIO = 0.95;

// 특정 key의 meaningful 값 row 비율 (0~1)
function meaningfulRatio(rows: Record<string, unknown>[], key: string): number {
  if (rows.length === 0) return 0;
  let count = 0;
  for (const row of rows) {
    if (!isMeaningless(normalizeCell(row[key]))) count++;
  }
  return count / rows.length;
}

// fix6: prefix match — lot이 mfg의 접두어로 포함되면 의미상 중복으로 간주
// (백엔드 extractor가 manufacturingNo에 "lot+수량단위" 또는 "C+lot+추가" 형태로 결합한 케이스 대응)
// 오탐 방지: lot 길이가 충분(>=4)할 때만 prefix match 적용
const _PREFIX_MATCH_MIN_LEN = 4;
function _isLotDupOfMfg(lot: string, mfg: string): boolean {
  if (lot === mfg) return true;
  if (lot.length < _PREFIX_MATCH_MIN_LEN || mfg.length === 0) return false;
  if (mfg.startsWith(lot)) return true;
  // "C" + lot 형태 (예: lot='30915', mfg='C30915-400ea')
  if (mfg.startsWith("C" + lot) || mfg.startsWith("c" + lot)) return true;
  return false;
}

// key1 값이 meaningless이거나 key2 값과 (prefix 포함) 중복인 row 비율
function meaninglessOrDupRatio(
  rows: Record<string, unknown>[],
  key1: string,
  key2: string,
): number {
  if (rows.length === 0) return 0;
  let count = 0;
  for (const row of rows) {
    const v1 = normalizeCell(row[key1]);
    const v2 = normalizeCell(row[key2]);
    if (isMeaningless(v1) || _isLotDupOfMfg(v1, v2)) count++;
  }
  return count / rows.length;
}

// fix7-E: itemCode 기반 표에서 lotNo가 column misidentification 노이즈인지 판단
// 조건: itemCode가 의미 있고(OP-xxx 코드 등) + manufacturingNo가 전 row 비어있으면
// → lotNo는 인접 컬럼 OCR 노이즈일 가능성 높음 → Preview에서 숨김
function isLotNoiseFromItemCodeTable(rows: Record<string, unknown>[]): boolean {
  return hasMeaningfulValue(rows, "itemCode") && !hasMeaningfulValue(rows, "manufacturingNo");
}

// 렌더링 직전 post-filter: 내부키 · 빈컬럼 · itemCode majority · lot중복 majority · lot노이즈 · serial중복
function filterInvoicePreviewDisplayCols(
  cols: { key: string; labelKo: string }[],
  rows: Record<string, unknown>[],
): { key: string; labelKo: string }[] {
  if (!cols || cols.length === 0 || rows.length === 0) return cols ?? [];

  // A. 내부/composite 키 제거
  let out = cols.filter((c) => !isInternalKey(c.key));

  // B. 의미 없는 컬럼 제거 (모든 row에서 빈 값) — strict 룰
  out = out.filter((c) => hasMeaningfulValue(rows, c.key));

  // B-2. itemCode 계열 majority rule — meaningful 비율이 (1 - 0.95) 이하면 숨김
  out = out.filter((c) => {
    if (!_ITEMCODE_KEYS.has(c.key)) return true;
    return meaningfulRatio(rows, c.key) > (1 - PREVIEW_COLUMN_HIDE_RATIO);
  });

  // C. lot계열 vs 제조번호계열 majority 중복 제거 (95% 이상 dup이면 제거)
  const mfgCol = out.find((c) => _MFG_KEYS.has(c.key));
  if (mfgCol) {
    const toRemove = new Set<string>();
    for (const col of out.filter((c) => _LOT_KEYS.has(c.key))) {
      if (meaninglessOrDupRatio(rows, col.key, mfgCol.key) >= PREVIEW_COLUMN_HIDE_RATIO) {
        toRemove.add(col.key);
      }
    }
    // D. labelKo "LOT/제조번호" 컬럼도 majority dup이면 제거
    for (const col of out.filter((c) => c.labelKo === "LOT/제조번호" || c.labelKo === "LOT/제조 번호")) {
      if (toRemove.has(col.key)) continue;
      if (meaninglessOrDupRatio(rows, col.key, mfgCol.key) >= PREVIEW_COLUMN_HIDE_RATIO) {
        toRemove.add(col.key);
      }
    }
    if (toRemove.size > 0) out = out.filter((c) => !toRemove.has(c.key));
  }

  // E. itemCode 기반 표에서 lotNo 노이즈 제거
  // itemCode가 의미있고 mfgNo가 전부 비어있으면 lotNo는 column misidentification 노이즈
  if (out.some((c) => _LOT_KEYS.has(c.key)) && isLotNoiseFromItemCodeTable(rows)) {
    out = out.filter((c) => !_LOT_KEYS.has(c.key));
  }

  // F. serialNo vs lotNo 중복 제거: serialNo === lotNo 95% 이상이면 serialNo 숨김
  const lotCol = out.find((c) => c.key === "lotNo");
  if (lotCol && out.some((c) => c.key === "serialNo")) {
    if (meaninglessOrDupRatio(rows, "serialNo", "lotNo") >= PREVIEW_COLUMN_HIDE_RATIO) {
      out = out.filter((c) => c.key !== "serialNo");
    }
  }

  return out;
}

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
  label?: string;
  tableRows?: Record<string, unknown>[];
  table_data?: unknown;
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
  /**
   * TPL-10: active template that drives `template_region_canonical` projection
   * via `buildTableResultViewModels(result, activeTemplate)`. Optional — when
   * absent, only `backend_document_fields` + `unstructured_definition` sources
   * are produced (TPL-8D behavior).
   */
  activeTemplate?: unknown;
};

type TabKey = "preview" | "custom" | "validation";

/**
 * OcrResultPanel 컴포넌트.
 *
 * 핵심 props 그룹:
 * - result / templateName / fileName / jobId / createdAt: 표시 대상 메타.
 * - selectedIndex / onSelectField: viewer 와의 hover/click 동기화.
 * - onRerun / onRevalidate / onPartialOcr: 부모가 주입하는 API 호출 위임.
 * - onTabChange / drawMode / onDrawModeChange / isScanning / onScanChange /
 *   canvasRegions: Custom 탭(편집 모드) 동기화.
 * - onClose / onPersist: 결과 닫기, 사용자 편집 자동저장 콜백.
 */
export default function OcrResultPanel({ result, onRerun, onRevalidate, selectedIndex, onSelectField, templateName, fileName, onTabChange, drawMode, onDrawModeChange, isScanning, onScanChange, onPartialOcr, canvasRegions, jobId, createdAt, onClose, onPersist, activeTemplate }: Props) {
  const ui = useUi();
  const [activeTab, setActiveTab] = useState<TabKey>("preview");
  const [previewMode, setPreviewMode] = useState<"markdown" | "json">("markdown");
  const [editedFields, setEditedFields] = useState<OcrFieldResult[]>(result.fields);
  const [activeFieldType, setActiveFieldType] = useState<string>("field");
  const [rawOcrOpen, setRawOcrOpen] = useState(true);
  const [autofillDetailOpen, setAutofillDetailOpen] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [customTableEdits, setCustomTableEdits] = useState<Record<string, string>[] | null>(null);
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

    const restoredCount = (summary.correctedCount ?? 0) + (summary.filledCount ?? 0);
    const isApplied   = summary.status === "applied" || summary.status === "corrected";
    const isConfirmed = summary.status === "confirmed";
    const isNoCandidates = summary.status === "no_candidates";
    const isNoBizNum     = summary.status === "no_business_number";
    const isNotRun = !summary.status || summary.status === "not_run";

    // 한 줄 요약 텍스트
    const summaryText = isNoBizNum        ? "자동복원 불가 · 사업자번호 미인식"
      : isNoCandidates  ? "자동복원 후보 없음"
      : isApplied && restoredCount > 0 ? `자동복원 적용됨 · ${restoredCount}개 필드 보정`
      : isApplied       ? "자동복원 확인됨 · 변경 없음"
      : isConfirmed     ? `자동복원 확인 · ${summary.confirmedCount}개 일치`
      : isNotRun        ? "자동복원 미사용"
      : "자동복원 확인 필요";

    // 상태별 색상 (다크 테마 어울리게)
    const cs = isApplied
      ? { border: "rgba(20,184,166,0.28)", bg: "rgba(20,184,166,0.07)", accent: "#0d9488" }
      : isConfirmed
      ? { border: "rgba(59,130,246,0.22)", bg: "rgba(59,130,246,0.06)", accent: "#3b82f6" }
      : isNoBizNum || isNoCandidates || isNotRun
      ? { border: "rgba(148,163,184,0.18)", bg: "rgba(148,163,184,0.06)", accent: "var(--muted)" }
      : { border: "rgba(234,179,8,0.3)", bg: "rgba(234,179,8,0.07)", accent: "#ca8a04" };

    // 상세 내용 (펼쳤을 때)
    const renderDetail = () => {
      if (isNoBizNum) return (
        <div style={{ marginTop: 6, fontSize: 11, color: "var(--muted)" }}>
          자동복원을 위해 필요한 사업자번호를 OCR 결과에서 찾지 못했습니다.
        </div>
      );
      if (isNoCandidates) return (
        <div style={{ marginTop: 6, fontSize: 11, color: "var(--muted)" }}>
          {summary.businessNumber ? `사업자번호 ${summary.businessNumber} 기준 ` : ""}저장 후보가 없습니다.
        </div>
      );
      if (isNotRun) return (
        <div style={{ marginTop: 6, fontSize: 11, color: "var(--muted)" }}>
          이번 OCR 실행에서는 자동복원을 사용하지 않았습니다.
        </div>
      );
      // applied / corrected / confirmed: 필드별 상세
      if (!hasAutofillDetail) return null;
      return (
        <div style={{ marginTop: 8, border: "1px solid rgba(148,163,184,0.18)", borderRadius: 6, overflow: "auto", maxHeight: 220 }}>
          {summary.businessNumber && (
            <div style={{ padding: "5px 8px", fontSize: 11, color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.12)" }}>
              기준 사업자번호: {summary.businessNumber}
            </div>
          )}
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
            <thead>
              <tr style={{ background: "rgba(148,163,184,0.08)" }}>
                <th style={{ padding: "5px 8px", textAlign: "left", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>필드</th>
                <th style={{ padding: "5px 8px", textAlign: "left", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>OCR 값</th>
                <th style={{ padding: "5px 8px", textAlign: "left", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>복원 후보값</th>
                <th style={{ width: 52, padding: "5px 8px", textAlign: "center", color: "var(--muted)", borderBottom: "1px solid rgba(148,163,184,0.14)" }}>채택</th>
              </tr>
            </thead>
            <tbody>
              {autofillDetailRows.map((row, index) => (
                <tr key={`${row.label}-${index}`}>
                  <td style={{ padding: "5px 8px", borderBottom: "1px solid rgba(148,163,184,0.08)", fontWeight: 700, whiteSpace: "nowrap" }}>{row.label}</td>
                  <td title={row.ocrValue || "빈 값"} style={{ padding: "5px 8px", borderBottom: "1px solid rgba(148,163,184,0.08)", maxWidth: 140, wordBreak: "break-word" }}>{row.ocrValue || "-"}</td>
                  <td title={row.candidate || ""} style={{ padding: "5px 8px", borderBottom: "1px solid rgba(148,163,184,0.08)", maxWidth: 160, wordBreak: "break-word" }}>{row.candidate || "-"}</td>
                  <td style={{ padding: "5px 8px", borderBottom: "1px solid rgba(148,163,184,0.08)", textAlign: "center", color: "var(--muted)" }}>
                    {row.action === "confirmed" ? "OCR" : row.action === "corrected" ? "복원" : row.action === "filled" ? "복원" : row.excluded ? "제외" : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    };

    return (
      <div
        style={{
          margin: "10px 12px 0",
          padding: "6px 10px",
          border: `1px solid ${cs.border}`,
          borderRadius: 6,
          background: cs.bg,
          fontSize: 12,
          lineHeight: 1.4,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          <span style={{ fontWeight: 700, color: cs.accent }}>{summaryText}</span>
          <button
            type="button"
            onClick={() => setAutofillDetailOpen((open) => !open)}
            style={{ padding: 0, border: "none", background: "transparent", color: "var(--muted)", fontSize: 11, cursor: "pointer", flexShrink: 0 }}
          >
            {autofillDetailOpen ? "접기" : "상세"}
          </button>
        </div>
        {autofillDetailOpen && renderDetail()}
      </div>
    );
  };


  // Markdown v1 — extracted to @/lib/markdownReportBuilder (FRONTEND-CLEANUP-2B).
  // parseTableField / fieldLabelFull / getAdoptionLabel now live in
  // @/lib/ocrResultFormatters and are reused by Preview/Custom/Validation JSX.
  //
  // Export-bound payload (Copy / Download): full markdown including the
  // TPL-13B representative table section.
  const toMarkdown = () =>
    buildMarkdownReport({
      fields: editedFields,
      processingTime: result.processing_time,
      docTableRows,
      // TPL-8F + TPL-13B: append the representative table section for the
      // saved file. Preview rendering uses `toMarkdownForPreview` below to
      // avoid duplicating the same table next to the JSX field-row block.
      tableResultViewModels,
    });

  // TPL-13C: Preview-only markdown that intentionally OMITS
  // `tableResultViewModels` so the helper does NOT append the extra
  // representative table section. Preview already renders
  // the representative table via the JSX `previewTableFields.map` block
  // below; without this split the markdown layer would duplicate it.
  // INVOICE-PARITY-4I: Preview-only markdown uses previewDisplayFields so the
  // materialized 품목표 row appears in the field list for the unstructured
  // 거래명세서 too. Export markdown (`toMarkdown`) still uses editedFields, so
  // the saved/exported structure is unchanged.
  const toMarkdownForPreview = () =>
    buildMarkdownReport({
      fields: previewDisplayFields,
      processingTime: result.processing_time,
      docTableRows,
    });

  // invoice_statement structured tableRows + tableMeta (document_fields에서 추출)
  const docTableRows = useMemo(() => {
    const df = (result as Record<string, unknown>).document_fields as Record<string, unknown> | null | undefined;
    if (!df) return null;
    const rows = df.tableRows;
    if (!Array.isArray(rows) || rows.length === 0) return null;
    return rows as Record<string, unknown>[];
  }, [result]);

  const docTableMeta = useMemo(() => {
    const df = (result as Record<string, unknown>).document_fields as Record<string, unknown> | null | undefined;
    if (!df) return null;
    const tm = df.tableMeta;
    return tm && typeof tm === "object" ? (tm as Record<string, unknown>) : null;
  }, [result]);

  // fix8: tableMeta 우선 (TestWorkspace getDisplayTableColumns와 동일 로직)
  // tableMeta.expectedColumnKeys → tableMeta.columns → hasValue fallback + filter
  // fix8/PREVIEW-9A: 공통 helper buildInvoicePreviewCols 사용
  const docTableDisplayCols = useMemo(
    () => (docTableRows ? buildInvoicePreviewCols(docTableMeta, docTableRows) : null),
    [docTableRows, docTableMeta],
  );

  // FRONTEND-CLEANUP-3D-3: Preview structured table view model.
  // Custom / Validation / legacy fallback are intentionally NOT migrated yet.
  const previewStructuredTableViewModel = useMemo(() => {
    if (!docTableRows || !docTableDisplayCols || docTableDisplayCols.length === 0) return null;
    return buildStructuredTableViewModel({
      rows: docTableRows,
      displayCols: docTableDisplayCols,
      emptyValue: "-",
    });
  }, [docTableRows, docTableDisplayCols]);

  // TPL-8E: 공통 TableResult ViewModel. backend document_fields.tableRows와
  // result.unstructuredTables를 단일 source로 normalize. Preview / Custom /
  // Validation 모두 이 ViewModel을 통해 같은 column 순서·cell value·
  // displayValue·empty state를 본다.
  // TPL-10: activeTemplate 전달 시 template_region_canonical source가 추가로
  // 산출된다 (template.regions[].table.columns 기반 projection).
  const tableResultViewModels = useMemo(
    () => buildTableResultViewModels(result, activeTemplate),
    [result, activeTemplate],
  );
  const backendTableResultViewModel: TableResultViewModel | null = useMemo(
    () => tableResultViewModels.find((vm) => vm.source === "backend_document_fields") ?? null,
    [tableResultViewModels],
  );
  // TPL-13B: representative table dedup — pick a single representative source
  // (template > unstructured > backend) and render only that. Drops duplicate
  // source-specific table sections when the same physical table is
  // already shown in the field-row table block.
  const representativeTableResultViewModels: TableResultViewModel[] = useMemo(
    () => selectRepresentativeTableResultViewModels(tableResultViewModels),
    [tableResultViewModels],
  );
  const representativeFirstVM: TableResultViewModel | null =
    representativeTableResultViewModels[0] ?? null;
  const representativeIsNonBackend =
    representativeFirstVM !== null
    && representativeFirstVM.source !== "backend_document_fields";
  // Kept for source-marker compatibility (older runners scan for these
  // names). When the representative dedup is active we still want the
  // separate template/unstructured sections SKIPPED — the guards below
  // gate on representativeIsNonBackend so they only render when there is
  // no field-row table block to host the representative.
  const templateRegionTableResultViewModels: TableResultViewModel[] = useMemo(
    () => tableResultViewModels.filter((vm) => vm.source === "template_region_canonical"),
    [tableResultViewModels],
  );
  const unstructuredTableResultViewModels: TableResultViewModel[] = useMemo(
    () => tableResultViewModels.filter((vm) => vm.source === "unstructured_definition"),
    [tableResultViewModels],
  );

  // INVOICE-PARITY-4I: 거래명세서 품목표를 Preview/Custom 필드 리스트에 table
  // field로 통합. 일반 템플릿은 raw.fields에 field_type==="table"이 들어오지만,
  // 비정형은 info[] 기반이라 표 필드가 없어 standalone 섹션으로 빠졌다.
  // result.fields(영속) / export(JSON·Markdown)는 바꾸지 않고, 표시용으로만
  // representative 품목표 VM을 table field로 materialize한다.
  const previewDisplayFields = useMemo<OcrFieldResult[]>(() => {
    if (editedFields.some((f) => f.field_type === "table")) return editedFields;
    const vm = representativeFirstVM;
    if (!vm || vm.columns.length === 0 || vm.meta.rowCount === 0) return editedFields;
    if (vm.meta.documentType !== "invoice_statement") return editedFields;
    const synthetic: OcrFieldResult = {
      name: vm.tableKey,
      ko: resolveResultTableLabel(vm, editedFields.length),
      en: vm.tableKey,
      field_type: "table",
      value: "[]",
      confidence: 1,
      bbox: [0, 0, 0, 0],
    };
    return [...editedFields, synthetic];
  }, [editedFields, representativeFirstVM]);

  // Table field list for JSX rendering in Preview tab (separate from Markdown)
  // T-28-PERF-3: docTableRows가 있으면 nonEmpty가 비어도 table field를 포함 (defer 최적화 대응)
  const previewTableFields = useMemo(() =>
    previewDisplayFields
      .map((f, i) => ({ f, i }))
      .filter(({ f }) => f.field_type === "table")
      .map(({ f, i }) => ({ idx: i + 1, label: fieldLabelFull(f), ...parseTableField(f.value) }))
      .filter(({ nonEmpty }) => nonEmpty.length > 0 || (!!docTableRows && docTableRows.length > 0)),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [previewDisplayFields, docTableRows]);

  // TPL-13C: explicit flag for the standalone-section dedup guards below.
  // When Preview already has a JSX table field row, the representative table
  // is rendered inside that row — the standalone source-specific JSX
  // sections must hide, and the markdown layer must skip its
  // own duplicate section (handled separately via toMarkdownForPreview).
  const hasPreviewTableFieldRow = previewTableFields.length > 0;

  // PREVIEW-9B: expected 컬럼 중 tableRows에 값이 없는 핵심 컬럼 → 품목표 제목에 안내 배지
  // 배지에 표시할 key allowlist — 사용자 확인이 필요한 항목만 (amount/remark 등 제외)
  const _PREVIEW_BADGE_KEYS = new Set(["insuranceCode"]);
  const missingExpectedWarning = useMemo(() => {
    if (!docTableRows || !docTableMeta) return "";
    const displayKeys = new Set((docTableDisplayCols ?? []).map((c) => c.key));
    const warnKeys = new Set<string>();

    // 조건 B: valueMappingWarnings 중 source_missing 계열 + allowlist 키만
    const vmw = docTableMeta.valueMappingWarnings;
    if (Array.isArray(vmw)) {
      for (const w of vmw) {
        const parts = String(w).split(":");
        if (parts.length >= 2 && (parts[1].includes("source_missing") || parts[1].includes("missing"))) {
          const k = parts[0].trim();
          if (k && _PREVIEW_BADGE_KEYS.has(k)) warnKeys.add(k);
        }
      }
    }

    // 조건 C: expectedColumnKeys에 있으나 전체 빈값 + allowlist 키만
    const expKeys = docTableMeta.expectedColumnKeys;
    if (Array.isArray(expKeys)) {
      for (const k of expKeys) {
        const key = String(k);
        if (!_PREVIEW_BADGE_KEYS.has(key)) continue;
        if (!displayKeys.has(key) && !hasMeaningfulValue(docTableRows, key)) {
          warnKeys.add(key);
        }
      }
    }

    if (warnKeys.size === 0) return "";
    const labels = [...warnKeys].map((k) => _ALL_COL_LABEL_MAP[k] ?? k).join(", ");
    return `확인 필요: ${labels} 미인식`;
  }, [docTableRows, docTableMeta, docTableDisplayCols]);

  // UI-JSON-1: Clean JSON v1 — extracted to @/lib/cleanJsonBuilder (FRONTEND-CLEANUP-1).
  // TPL-8F: pass tableResultViewModels so unstructured tables export. Backend
  // source is filtered out by the builder (overlap with docTableRows; v1
  // fixture lock is preserved when no unstructured entries exist).
  const cleanJson: CleanJsonResult = useMemo(
    () =>
      buildCleanJsonResult({
        templateName,
        fields: editedFields,
        docTableRows,
        docTableDisplayCols,
        tableResultViewModels,
      }),
    [editedFields, docTableRows, docTableDisplayCols, templateName, tableResultViewModels],
  );

  const toCleanJson = () => JSON.stringify(cleanJson, null, 2);

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

  // INVOICE-PARITY-4I: Custom 탭 거래명세서 품목표 editable 표 공통 renderer.
  // field_type==="table" 필드 경로(일반 템플릿)와 representative standalone
  // 경로(비정형/free)가 동일한 textarea 편집 표를 사용하게 해 read-only 차이를
  // 없앤다. tableRows/tableMeta/VM source는 그대로 소비만 한다(변경 없음).
  const renderEditableTableVM = (
    vm: TableResultViewModel,
    fieldIndex: number,
    adoptionField?: OcrFieldResult,
  ) => {
    const baseRows: Record<string, string>[] = vm.rows.map((row) => {
      const obj: Record<string, string> = {};
      for (const cell of row.cells) obj[cell.key] = cell.value;
      return obj;
    });
    const editRows: Record<string, string>[] = customTableEdits ?? baseRows;
    return (
      <>
        <div className="or-field-value-meta" style={{ alignItems: "center" }} onClick={(e) => e.stopPropagation()}>
          <span style={{ fontWeight: 700, color: "var(--accent)" }}>
            표 데이터 · {vm.meta.rowCount}행
          </span>
          {missingExpectedWarning && (
            <span style={{
              fontSize: 11, fontWeight: 600, color: "#d97706",
              background: "rgba(251,191,36,0.12)",
              border: "1px solid rgba(217,119,6,0.25)",
              borderRadius: 4, padding: "1px 7px",
            }}>
              {missingExpectedWarning}
            </span>
          )}
          {adoptionField && <span>채택: {getAdoptionLabel(adoptionField)}</span>}
        </div>
        <div className="or-table-wrap" style={{ overflowX: "auto", borderRadius: 0, marginTop: 6 }} onClick={(e) => e.stopPropagation()}>
          <table className="or-table-result">
            <colgroup>
              {vm.columns.map((col) => (
                <col key={col.columnKey} style={{ width: _invoiceColWidth(col.columnKey) }} />
              ))}
            </colgroup>
            <tbody>
              <tr>
                {vm.columns.map((col) => (
                  <td key={col.columnKey} className="or-table-cell" style={{ textAlign: "center", verticalAlign: "middle" }}>
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={col.columnKey}>
                      {col.labelKo}
                    </div>
                    {col.labelKo !== col.columnKey && (
                      <div title={col.columnKey} style={{
                        fontSize: 10, opacity: 0.55, marginTop: 1,
                        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", display: "block",
                      }}>
                        ({col.columnKey})
                      </div>
                    )}
                  </td>
                ))}
              </tr>
              {editRows.map((row, ri) => (
                <tr key={ri}>
                  {vm.columns.map((col) => (
                    <td key={col.columnKey} className="or-table-cell" style={{
                      textAlign: _invoiceDataAlign(col.columnKey),
                      whiteSpace: _NUM_KEYS.has(col.columnKey) || _IDX_KEYS.has(col.columnKey) ? "nowrap" : "normal",
                      padding: 0,
                    }}>
                      <textarea
                        className="or-table-cell-input"
                        value={row[col.columnKey] ?? ""}
                        rows={1}
                        title={String(row[col.columnKey] ?? "")}
                        style={{ textAlign: _invoiceDataAlign(col.columnKey) }}
                        onChange={(e) => {
                          e.target.style.height = "auto";
                          e.target.style.height = e.target.scrollHeight + "px";
                          const newVal = e.target.value;
                          setCustomTableEdits((prev) => {
                            const base = prev ?? baseRows;
                            return base.map((r, idx) => idx === ri ? { ...r, [col.columnKey]: newVal } : r);
                          });
                        }}
                        onFocus={() => { if (fieldIndex >= 0) onSelectField(fieldIndex); }}
                        onBlur={flushSave}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    );
  };

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
              <button type="button" className="ms-btn-sm" onClick={() => handleExport(previewMode === "markdown" ? toMarkdown() : toCleanJson(), previewMode === "markdown" ? "md" : "json")}>
                내보내기
              </button>
              <button type="button" className="ms-btn-sm" onClick={() => void handleCopy(previewMode === "markdown" ? toMarkdown() : toCleanJson())}>
                복사
              </button>
            </div>
            {previewMode === "markdown" ? (
              <div
                className="or-preview-content or-markdown"
                style={{
                  display: "grid",
                  gridTemplateRows: rawOcrFields.length > 0
                    ? (rawOcrOpen ? "minmax(0, 7fr) minmax(0, 3fr)" : "minmax(0, 1fr) auto")
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
                  <Markdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      td: ({ children, ...props }) => {
                        const text = typeof children === "string" ? children : null;
                        const match = text?.match(/^(.+?)\s+\(([a-zA-Z][a-zA-Z0-9_]*)\)$/);
                        if (match) {
                          return (
                            <td {...(props as React.TdHTMLAttributes<HTMLTableCellElement>)}>
                              {match[1]}
                              <span style={{
                                opacity: 0.55, fontSize: 10, marginLeft: 3,
                                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                              }}>
                                ({match[2]})
                              </span>
                            </td>
                          );
                        }
                        return <td {...(props as React.TdHTMLAttributes<HTMLTableCellElement>)}>{children}</td>;
                      },
                    }}
                  >{toMarkdownForPreview()}</Markdown>
                  {/* Table fields rendered as JSX (reliable layout, not markdown) */}
                  {previewTableFields.map(({ idx, label, displayRows, rowLabel }, tableIdx) => {
                    // fix8: tableMeta 기반이면 백엔드가 이미 계산한 컬럼 사용 (TestWorkspace 동일 로직)
                    // fallback(hasValue 기반)일 때만 filterInvoicePreviewDisplayCols 추가 적용
                    // TPL-13B: pick the representative VM (template > unstructured
                    // > backend) so the field-row table block shows the user-
                    // defined columns when present and falls back to backend.
                    const previewRepVM = representativeFirstVM ?? backendTableResultViewModel;
                    if (tableIdx === 0 && previewRepVM) {
                      // TPL-8E + TPL-13B: Preview structured table consumes the
                      // representative TableResult ViewModel. When template /
                      // unstructured columns are defined they win; otherwise
                      // backend_document_fields fallback. Style / align / width
                      // policy stays Preview-specific (kept inline below).
                      const viewModel = previewRepVM;
                      return (
                        <div key={idx} style={{ marginTop: 12 }}>
                          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
                            <span>{idx}. {resolveResultTableLabel(viewModel, tableIdx, label)}</span>
                            <span style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)" }}>
                              {viewModel.meta.rowCount}행
                            </span>
                            {missingExpectedWarning && (
                              <span style={{
                                fontSize: 11, fontWeight: 600, color: "#d97706",
                                background: "rgba(251,191,36,0.12)",
                                border: "1px solid rgba(217,119,6,0.25)",
                                borderRadius: 4, padding: "1px 7px",
                              }}>
                                {missingExpectedWarning}
                              </span>
                            )}
                          </div>
                          <div className="or-table-wrap" style={{ overflowX: "auto", borderRadius: 0 }}>
                            {/* PREVIEW-10A-fix: fixed-layout + colgroup */}
                            <table className="or-table-result">
                              <colgroup>
                                {viewModel.columns.map((column) => (
                                  <col key={column.columnKey} style={{ width: _invoiceColWidth(column.columnKey) }} />
                                ))}
                              </colgroup>
                              <tbody>
                                {/* 헤더 행 — 항상 가운데 정렬 */}
                                <tr>
                                  {viewModel.columns.map((column) => (
                                    <td key={column.columnKey} className="or-table-cell" style={{ textAlign: "center", verticalAlign: "middle" }}>
                                      <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={column.labelKo}>
                                        {column.labelKo}
                                      </div>
                                      {column.labelKo !== column.columnKey && (
                                        <div title={column.columnKey} style={{
                                          fontSize: 10, opacity: 0.55, marginTop: 1,
                                          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                                          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", display: "block",
                                        }}>
                                          ({column.columnKey})
                                        </div>
                                      )}
                                    </td>
                                  ))}
                                </tr>
                                {/* 데이터 행 — 컬럼 타입별 정렬 */}
                                {viewModel.rows.map((row, ri) => (
                                  <tr key={ri}>
                                    {row.cells.map((cell) => (
                                      <td key={cell.key} className="or-table-cell" style={{
                                        textAlign: _invoiceDataAlign(cell.key),
                                        whiteSpace: _NUM_KEYS.has(cell.key) || _IDX_KEYS.has(cell.key) ? "nowrap" : "normal",
                                      }}>
                                        {cell.displayValue}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      );
                    }
                    // Fallback: raw displayRows (기존 동작)
                    return (
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
                    );
                  })}
                  {/* TPL-10 + TPL-13B + TPL-13C: 템플릿 테이블 standalone
                      section은 hasPreviewTableFieldRow === false 일 때만
                      표시한다. field-row가 있으면 위 블록이 representative
                      VM으로 이미 렌더했고, 마크다운 레이어도
                      `toMarkdownForPreview`로 추가 섹션 없이 출력되므로
                      Preview에는 표가 정확히 하나만 보인다. */}
                  {!hasPreviewTableFieldRow
                    && templateRegionTableResultViewModels.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <div style={{ fontWeight: 700, fontSize: 13, color: "var(--muted)", marginBottom: 6 }}>
                        템플릿 테이블
                      </div>
                      {templateRegionTableResultViewModels.map((vm, vmIdx) => (
                        <div key={`tpl-${vm.tableKey}-${vmIdx}`} style={{ marginTop: 12 }}>
                          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
                            <span>{resolveResultTableLabel(vm, vmIdx)}</span>
                            <span style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)" }}>
                              {vm.meta.rowCount}행
                            </span>
                          </div>
                          {vm.columns.length === 0 ? (
                            <div className="or-empty" style={{ fontSize: 12 }}>정의된 컬럼이 없습니다.</div>
                          ) : vm.rows.length === 0 ? (
                            <div className="or-empty" style={{ fontSize: 12 }}>추출된 행이 없습니다.</div>
                          ) : (
                            <div className="or-table-wrap" style={{ overflowX: "auto", borderRadius: 0 }}>
                              <table className="or-table-result">
                                <tbody>
                                  <tr>
                                    {vm.columns.map((column) => (
                                      <td key={column.columnKey} className="or-table-cell" style={{ textAlign: "center", verticalAlign: "middle" }}>
                                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={column.labelKo}>
                                          {column.labelKo || column.labelEn || column.columnKey}
                                        </div>
                                        {(column.labelKo || "") !== column.columnKey && (
                                          <div title={column.columnKey} style={{
                                            fontSize: 10, opacity: 0.55, marginTop: 1,
                                            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                                            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", display: "block",
                                          }}>
                                            ({column.columnKey})
                                          </div>
                                        )}
                                      </td>
                                    ))}
                                  </tr>
                                  {vm.rows.map((row, ri) => (
                                    <tr key={ri}>
                                      {row.cells.map((cell) => (
                                        <td key={cell.key} className="or-table-cell" style={{
                                          textAlign: _invoiceDataAlign(cell.key),
                                          whiteSpace: _NUM_KEYS.has(cell.key) || _IDX_KEYS.has(cell.key) ? "nowrap" : "normal",
                                        }}>
                                          {cell.displayValue}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  {/* TPL-8E + TPL-13B + TPL-13C: unstructured standalone
                      section은 (a) representative가 template이 아니고
                      (b) hasPreviewTableFieldRow === false 일 때만 표시. */}
                  {!hasPreviewTableFieldRow
                    && representativeFirstVM?.source !== "template_region_canonical"
                    && unstructuredTableResultViewModels.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      {unstructuredTableResultViewModels.map((vm, vmIdx) => (
                        <div key={`u-${vm.tableKey}-${vmIdx}`} style={{ marginTop: 12 }}>
                          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 6, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6 }}>
                            <span>{resolveResultTableLabel(vm, vmIdx)}</span>
                            <span style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)" }}>
                              {vm.meta.rowCount}행
                            </span>
                          </div>
                          {vm.columns.length === 0 ? (
                            <div className="or-empty" style={{ fontSize: 12 }}>정의된 컬럼이 없습니다.</div>
                          ) : vm.rows.length === 0 ? (
                            <div className="or-empty" style={{ fontSize: 12 }}>추출된 행이 없습니다.</div>
                          ) : (
                            <div className="or-table-wrap" style={{ overflowX: "auto", borderRadius: 0 }}>
                              <table className="or-table-result">
                                <tbody>
                                  <tr>
                                    {vm.columns.map((column) => (
                                      <td key={column.columnKey} className="or-table-cell" style={{ textAlign: "center", verticalAlign: "middle" }}>
                                        <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={column.labelKo}>
                                          {column.labelKo || column.labelEn || column.columnKey}
                                        </div>
                                        {(column.labelKo || "") !== column.columnKey && (
                                          <div title={column.columnKey} style={{
                                            fontSize: 10, opacity: 0.55, marginTop: 1,
                                            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                                            whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", display: "block",
                                          }}>
                                            ({column.columnKey})
                                          </div>
                                        )}
                                      </td>
                                    ))}
                                  </tr>
                                  {vm.rows.map((row, ri) => (
                                    <tr key={ri}>
                                      {row.cells.map((cell) => (
                                        <td key={cell.key} className="or-table-cell" style={{
                                          textAlign: _invoiceDataAlign(cell.key),
                                          whiteSpace: _NUM_KEYS.has(cell.key) || _IDX_KEYS.has(cell.key) ? "nowrap" : "normal",
                                        }}>
                                          {cell.displayValue}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
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
              <pre className="or-preview-content">{toCleanJson()}</pre>
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
                      title={`${field.field_type === "table" && representativeFirstVM ? resolveResultTableLabel(representativeFirstVM, 0, fieldLabelFull(field)) : fieldLabelFull(field)} (${field.name})`}
                    >
                      {field.field_type === "table" && representativeFirstVM ? resolveResultTableLabel(representativeFirstVM, 0, fieldLabel(field)) : fieldLabel(field)}
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
                    // TPL-8E + TPL-13B: Custom consumes the representative
                    // ViewModel (template > unstructured > backend) so the
                    // user-defined columns drive both display and edit when
                    // present. customTableEdits per-cell state remains keyed
                    // by columnKey; switching representative columns just
                    // leaves any prior edits inaccessible (no crash).
                    const customRepVM = representativeFirstVM ?? backendTableResultViewModel;
                    if (customRepVM && customRepVM.columns.length > 0) {
                      // INVOICE-PARITY-4I: 공통 editable renderer 재사용.
                      return renderEditableTableVM(customRepVM, i, field);
                    }
                    // fallback: raw parseTableField (docTableRows 없는 경우)
                    const { rows, displayRows, isSingleCol, rowLabel: rawRowLabel } = parseTableField(field.value);
                    const rowLabel = rawRowLabel;
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
              {/* INVOICE-PARITY-4I: 표 필드가 없는 거래명세서(비정형/free)도
                  representative 품목표를 일반 템플릿과 동일한 editable 표로
                  렌더한다. 기존 read-only standalone(템플릿/비정형) 섹션을 대체.
                  region 템플릿은 raw.fields에 table 필드가 있어 위 row 블록에서
                  이미 editable로 렌더되므로 이 분기에 들어오지 않는다. */}
              {editedFields.every((f) => f.field_type !== "table")
                && representativeFirstVM
                && representativeFirstVM.columns.length > 0 && (
                <div className="or-field-item" style={{ marginTop: 12 }}>
                  <div className="or-field-header">
                    <span
                      style={{ flex: 1, minWidth: 0, fontSize: 11, fontWeight: 700, color: "var(--text)", lineHeight: 1.3, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
                      title={`${resolveResultTableLabel(representativeFirstVM, editedFields.length)} (${representativeFirstVM.tableKey})`}
                    >
                      {editedFields.length + 1}. {resolveResultTableLabel(representativeFirstVM, editedFields.length)}
                      <span style={{ fontSize: 9, fontWeight: 400, color: "var(--muted)", marginLeft: 4 }}>
                        {representativeFirstVM.tableKey}
                      </span>
                    </span>
                  </div>
                  {representativeFirstVM.rows.length === 0 ? (
                    <div className="or-empty" style={{ fontSize: 12 }}>추출된 행이 없습니다.</div>
                  ) : (
                    renderEditableTableVM(representativeFirstVM, -1)
                  )}
                </div>
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
                            // UI-VALIDATION-1: docTableRows 기반 표 표시 (Preview/Custom과 동일 helper 재사용)
                            const hasStructured = docTableRows && docTableDisplayCols && docTableDisplayCols.length > 0;
                            const rowLabel = docTableRows ? `${docTableRows.length}행` : (() => {
                              const { rowLabel: raw } = parseTableField(item.field.value);
                              return raw;
                            })();
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
                                  gridTemplateColumns: "10px minmax(160px, 1.6fr) minmax(0, 2.8fr) 42px 58px",
                                  gap: 8,
                                  alignItems: "center",
                                  marginBottom: 6,
                                }}>
                                  <span className={"or-val-dot or-dot-" + item.status} />
                                  <span className="or-val-error-name" title={fieldLabelFull(item.field)}>
                                    {fieldLabel(item.field)}
                                    <span style={{ fontSize: 9, fontWeight: 400, color: "var(--muted)", marginLeft: 4 }}>
                                      ({item.field.en || item.field.name})
                                    </span>
                                  </span>
                                  <span style={{ display: "flex", alignItems: "center", gap: 6, overflow: "hidden" }}>
                                    <span className="or-val-error-value">
                                      표 데이터 · {rowLabel}
                                    </span>
                                    {missingExpectedWarning && (
                                      <span style={{
                                        fontSize: 10, fontWeight: 600, color: "#d97706",
                                        background: "rgba(251,191,36,0.12)",
                                        border: "1px solid rgba(217,119,6,0.25)",
                                        borderRadius: 4, padding: "1px 6px", whiteSpace: "nowrap",
                                      }}>
                                        {missingExpectedWarning}
                                      </span>
                                    )}
                                  </span>
                                  <span className={"or-val-adoption or-val-adoption-" + getAdoptionLabel(item.field)}>{getAdoptionLabel(item.field)}</span>
                                  <span className="or-val-error-conf">{formatConfidence(item.field.confidence)}</span>
                                </div>
                                {/* 표 데이터: docTableRows 기반 */}
                                {hasStructured ? (
                                  <div
                                    className="or-table-wrap"
                                    onClick={(e) => e.stopPropagation()}
                                    style={{ marginLeft: 18, width: "calc(100% - 18px)", overflowX: "auto", borderRadius: 0 }}
                                  >
                                    <table className="or-table-result">
                                      <colgroup>
                                        {docTableDisplayCols!.map((col) => (
                                          <col key={col.key} style={{ width: _invoiceColWidth(col.key) }} />
                                        ))}
                                      </colgroup>
                                      <tbody>
                                        <tr>
                                          {docTableDisplayCols!.map((col) => (
                                            <td key={col.key} className="or-table-cell" style={{ textAlign: "center", verticalAlign: "middle" }}>
                                              <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={col.labelKo}>
                                                {col.labelKo}
                                              </div>
                                              {col.labelKo !== col.key && (
                                                <div title={col.key} style={{
                                                  fontSize: 10, opacity: 0.55, marginTop: 1,
                                                  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                                                  whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", display: "block",
                                                }}>
                                                  ({col.key})
                                                </div>
                                              )}
                                            </td>
                                          ))}
                                        </tr>
                                        {docTableRows!.map((row, ri) => (
                                          <tr key={ri}>
                                            {docTableDisplayCols!.map((col) => (
                                              <td key={col.key} className="or-table-cell" style={{
                                                textAlign: _invoiceDataAlign(col.key),
                                                whiteSpace: _NUM_KEYS.has(col.key) || _IDX_KEYS.has(col.key) ? "nowrap" : "normal",
                                              }}>
                                                {normalizeCell(row[col.key]) || "-"}
                                              </td>
                                            ))}
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                ) : (
                                  docTableRows && docTableRows.length === 0 ? (
                                    <div className="or-empty" style={{ fontSize: 12, marginLeft: 18 }}>테이블 데이터 없음</div>
                                  ) : null
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
                                <span style={{ fontSize: 9, fontWeight: 400, color: "var(--muted)", marginLeft: 4 }}>
                                  ({item.field.en || item.field.name})
                                </span>
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
