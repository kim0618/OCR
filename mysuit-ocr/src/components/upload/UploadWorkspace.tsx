"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useUi } from "../common/AppProviders";
import OcrResultPanel, { type FieldOverlayAdoption, type FieldSourceBox, type OcrResult, type OcrFieldResult } from "./OcrResultPanel";
import OcrDocViewer from "./OcrDocViewer";
import CornerAdjust, { type Corner } from "./CornerAdjust";
import FileDropzone from "../common/FileDropzone";
import type { Region, FieldType, LoadedImage } from "../ocr/core/types";
import { appendHistoryRun, updateHistoryRun, syncHistoryIndexAndDetailOnCreate, type HistoryDetailDocumentFields, type HistoryOcrField, type HistoryOutputField } from "@/lib/historyStore";
import { getTemplateImage } from "@/lib/imageStore";
import { extractBizNumber } from "@/lib/bizNumber";
import {
  applyAutofillToOutputFields,
  buildAutofillSuggestionsFromCandidates,
  canAutoApplySuggestion,
  collectInternalAutofillCandidates,
  isAutofillableField,
  isEmptyOcrValue,
  normalizeAutofillFieldKey,
  suggestionsForHistoryField,
  type AutofillRunSummary,
  type AutofillSuggestion,
} from "@/lib/autofillEngine";

const OcrCanvasPane = dynamic(() => import("../ocr/OcrCanvasPane"), { ssr: false });

type TemplateItem = {
  id: string;
  name: string;
  regions?: Region[];
  mode?: string;
  fields?: { no?: number; enField?: string; koField?: string }[];
  // T-9-fix: document type from template metadata (e.g. "invoice_statement")
  documentType?: string;
  // T-10-overlay-scale-fix: original image dimensions for overlay scale correction
  image?: { width: number; height: number };
  // UI-IMG-IDB-1: 카드 썸네일용 base64 dataURL (IndexedDB에서 hydrate)
  imageSrc?: string;
};

const DEFAULT_TEMPLATES: TemplateItem[] = [];
const LOCAL_TEMPLATES_KEY = "mysuit_ocr_templates";

type UploadWorkspaceVariant = "upload" | "runocr";
type RunOcrTemplateMode = "template" | "unstructured";

type UploadWorkspaceProps = {
  variant?: UploadWorkspaceVariant;
};

type BboxLikeField = OcrFieldResult & Record<string, unknown>;
const OCR_REGION_ID_PREFIX = "ocr_";

function ocrRegionIdForField(index: number) {
  return `${OCR_REGION_ID_PREFIX}${index}`;
}

function fieldIndexFromOcrRegionId(id: string | null) {
  if (!id?.startsWith(OCR_REGION_ID_PREFIX)) return null;
  const index = Number(id.slice(OCR_REGION_ID_PREFIX.length));
  return Number.isInteger(index) && index >= 0 ? index : null;
}

function unionSourceBoxes(boxes: FieldSourceBox[]) {
  if (boxes.length === 0) return null;
  const left = Math.min(...boxes.map((box) => box.x));
  const top = Math.min(...boxes.map((box) => box.y));
  const right = Math.max(...boxes.map((box) => box.x + box.width));
  const bottom = Math.max(...boxes.map((box) => box.y + box.height));
  return {
    x: left,
    y: top,
    width: Math.max(1, right - left),
    height: Math.max(1, bottom - top),
  };
}

const MODEL_OPTIONS = [
  { id: "paddleocr", name: "PaddleOCR" },
  { id: "easyocr", name: "EasyOCR" },
  { id: "clova", name: "CLOVA OCR" },
  { id: "tesseract", name: "Tesseract OCR" },
];

function isTiff(file: File) {
  return (
    file.type === "image/tiff" ||
    file.type === "image/tif" ||
    file.name.toLowerCase().endsWith(".tif") ||
    file.name.toLowerCase().endsWith(".tiff")
  );
}

type PreprocessDetail = {
  status: string;
  detail: string;
};

type PreprocessResult = {
  image_size: string;
  document?: PreprocessDetail;
  upscale: PreprocessDetail;
  deskew: PreprocessDetail;
  denoise: PreprocessDetail;
  contrast: PreprocessDetail;
} | null;

export default function UploadWorkspace({ variant = "upload" }: UploadWorkspaceProps) {
  const router = useRouter();
  const ui = useUi();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadStartRef = useRef<number>(0);

  const [activeTemplateId, setActiveTemplateId] = useState<string>("");
  const [templates, setTemplates] = useState<TemplateItem[]>(DEFAULT_TEMPLATES);
  const [selectedModelId, setSelectedModelId] = useState<string>(MODEL_OPTIONS[0].id);
  const [runOcrTemplateMode, setRunOcrTemplateMode] = useState<RunOcrTemplateMode>("template");
  const [cardTooltip, setCardTooltip] = useState<{ imgSrc: string; x: number; y: number } | null>(null);
  const isRunOcr = variant === "runocr";

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [renderedUrl, setRenderedUrl] = useState<string | null>(null);
  const [uploadDuration, setUploadDuration] = useState<string | null>(null);
  const [preprocessResult, setPreprocessResult] = useState<PreprocessResult>(null);
  const [isPreprocessing, setIsPreprocessing] = useState(false);

  // OCR 결과 상태
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);
  const [isOcrRunning, setIsOcrRunning] = useState(false);
  const [selectedFieldIndex, setSelectedFieldIndex] = useState<number | null>(null);
  const [processedImageUrl, setProcessedImageUrl] = useState<string | null>(null);
  const [corners, setCorners] = useState<Corner[]>([]);
  const [showCornerAdjust, setShowCornerAdjust] = useState(false);

  // OcrCanvasPane용 상태
  const canvasImgRef = useRef<HTMLImageElement>(null!);
  const [canvasRegions, setCanvasRegions] = useState<Region[]>([]);
  const [canvasSelectedId, setCanvasSelectedId] = useState<string | null>(null);
  const [canvasDrawMode, setCanvasDrawMode] = useState<FieldType | null>(null);
  const [canvasZoom, setCanvasZoom] = useState(100);
  const [rowTemplateTargetId, setRowTemplateTargetId] = useState<string | null>(null);
  const [colGuideTargetId, setColGuideTargetId] = useState<string | null>(null);
  const [canvasLoaded, setCanvasLoaded] = useState<LoadedImage | null>(null);
  const [resultTab, setResultTab] = useState<"preview" | "custom" | "validation">("preview");

  // 현재 OCR 결과의 history 레코드 컨텍스트 — Custom 탭 자동저장용.
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [currentCreatedAt, setCurrentCreatedAt] = useState<string | null>(null);
  // appendHistoryRun 시점의 immutable 메타(no/en/ko/original/applied/autofillAction/suggestions)
  // 를 그대로 보존하기 위해 별도 보관. modified 만 onBlur 마다 덮어씀.
  // 이 값이 null 이면 fail 레코드(또는 미실행) 라서 자동저장이 비활성화된다.
  const [initialOutputFields, setInitialOutputFields] = useState<HistoryOutputField[] | null>(null);

  function loadLocalTemplates(): TemplateItem[] {
    try {
      const list = JSON.parse(localStorage.getItem(LOCAL_TEMPLATES_KEY) || "[]");
      if (!Array.isArray(list)) return [];
      return list
        .map((item: any) => {
          const imgMeta = item?.template_json?.image;
          const imgW = typeof imgMeta?.width === "number" ? imgMeta.width : null;
          const imgH = typeof imgMeta?.height === "number" ? imgMeta.height : null;
          // UI-IMG-IDB-1: localStorage에 src 남아있을 수 있음 (구버전 템플릿). IDB hydration은 별도 단계.
          const inlineSrc = typeof imgMeta?.src === "string" ? imgMeta.src : undefined;
          return {
            id: String(item?.template_id ?? ""),
            name: String(item?.template_name ?? ""),
            mode: String(item?.template_json?.mode ?? "template"),
            regions: Array.isArray(item?.template_json?.regions) ? item.template_json.regions : [],
            fields: Array.isArray(item?.template_json?.fields) ? item.template_json.fields : [],
            // T-9-fix: include documentType from template metadata for routing
            documentType: String(item?.template_json?.documentType ?? ""),
            // T-10-overlay-scale-fix: original image dimensions for overlay scale correction
            ...(imgW && imgH ? { image: { width: imgW, height: imgH } } : {}),
            ...(inlineSrc ? { imageSrc: inlineSrc } : {}),
          };
        })
        .filter((item) => item.id && item.name);
    } catch {
      return [];
    }
  }

  function mergeTemplates(serverTemplates: TemplateItem[], localTemplates: TemplateItem[]) {
    const seen = new Set<string>();
    return [...localTemplates, ...serverTemplates].filter((item) => {
      const key = item.id || item.name;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  // canvasSelectedId ↔ selectedFieldIndex 연동
  useEffect(() => {
    const fieldIndex = fieldIndexFromOcrRegionId(canvasSelectedId);
    if (fieldIndex != null) setSelectedFieldIndex(fieldIndex);
  }, [canvasSelectedId]);

  useEffect(() => {
    if (selectedFieldIndex == null || selectedFieldIndex < 0) {
      if (fieldIndexFromOcrRegionId(canvasSelectedId) != null) setCanvasSelectedId(null);
      return;
    }
    const regionId = ocrRegionIdForField(selectedFieldIndex);
    const region = canvasRegions.find((item) => item.id === regionId);
    if (region) {
      if (region.id !== canvasSelectedId) setCanvasSelectedId(region.id);
      return;
    }
    if (fieldIndexFromOcrRegionId(canvasSelectedId) != null) setCanvasSelectedId(null);
  }, [selectedFieldIndex, canvasRegions, canvasSelectedId]);

  // UI-IMG-IDB-1: 템플릿 카드용 이미지를 IndexedDB에서 hydrate.
  // localStorage에 inlineSrc(구버전) 있으면 그대로 사용, 없으면 IDB 조회.
  async function hydrateTemplateImages(items: TemplateItem[]): Promise<TemplateItem[]> {
    return Promise.all(items.map(async (t) => {
      if (t.imageSrc) return t;
      if (!t.image || !t.id) return t;
      const src = await getTemplateImage(t.id);
      return src ? { ...t, imageSrc: src } : t;
    }));
  }

  useEffect(() => {
    (async () => {
      const localTemplates = loadLocalTemplates();
      if (isRunOcr) {
        setTemplates(localTemplates);
        const hydrated = await hydrateTemplateImages(localTemplates);
        setTemplates(hydrated);
        return;
      }
      try {
        const res = await fetch("/templates");
        const json = await res.json();
        const list = json.resultMap?.templateList ?? [];
        const mapped = list.map((t: any) => {
          const imgMeta = t.template_json?.image;
          const imgW = typeof imgMeta?.width === "number" ? imgMeta.width : null;
          const imgH = typeof imgMeta?.height === "number" ? imgMeta.height : null;
          const inlineSrc = typeof imgMeta?.src === "string" ? imgMeta.src : undefined;
          return {
            id: t.template_id,
            name: t.template_name,
            regions: Array.isArray(t.template_json?.regions) ? t.template_json.regions : t.regions,
            // T-9-fix: include documentType from template metadata
            documentType: String(t.template_json?.documentType ?? ""),
            // T-10-overlay-scale-fix: original image dimensions
            ...(imgW && imgH ? { image: { width: imgW, height: imgH } } : {}),
            ...(inlineSrc ? { imageSrc: inlineSrc } : {}),
          };
        });
        const merged = mergeTemplates(mapped, localTemplates);
        setTemplates(merged);
        const hydrated = await hydrateTemplateImages(merged);
        setTemplates(hydrated);
        // 기본값: 전체 인식 (빈 값)
      } catch {
        setTemplates(localTemplates);
        const hydrated = await hydrateTemplateImages(localTemplates);
        setTemplates(hydrated);
        // 서버 미실행 시 무시 (기본값: 빈 목록)
      }
    })();
  }, [isRunOcr]);

  const hintSections = useMemo(
    () => [
      {
        title: "지원 형식",
        desc: "업로드/내보내기 가능한 파일 형식",
        items: [
          "Upload: jpeg, jpg, png, pdf, tif, tiff",
          "Export: json, xlsx, html, hwp(예정)",
        ],
      },
      {
        title: "자동 처리",
        desc: "업로드 직후 자동으로 수행되는 보정",
        items: ["기울기 보정", "노이즈 제거", "대비 강화", "언어 감지"],
      },
      {
        title: "업로드 가이드",
        desc: "정확도를 높이기 위한 권장 조건",
        items: [
          "150~300dpi, 텍스트 선명, 흔들림 없음",
          "글자 높이 10px 이상",
          "가로 2000px 내외 권장",
          "업로드 파일은 24시간 후 자동 삭제",
        ],
      },
    ],
    [],
  );

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      setRenderedUrl(null);
      setUploadDuration(null);
      setPreprocessResult(null);
      return;
    }

    const isNativeImage =
      selectedFile.type.startsWith("image/") && !isTiff(selectedFile);
    const isPdf = selectedFile.type === "application/pdf";
    const isTiffFile = isTiff(selectedFile);

    const elapsed = Date.now() - uploadStartRef.current;
    setUploadDuration(`${(elapsed / 1000).toFixed(2)}초`);

    if (!isNativeImage && !isPdf && !isTiffFile) {
      setPreviewUrl(null);
      setRenderedUrl(null);
      return;
    }

    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    setRenderedUrl(null);

    let cancelled = false;

    if (isPdf) {
      (async () => {
        try {
          const pdfjs = await import("pdfjs-dist/legacy/build/pdf.js");
          pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.js";
          const pdf = await pdfjs.getDocument(url).promise;
          const page = await pdf.getPage(1);
          // Use the same DPI as backend PyMuPDF (200 DPI = 200/72 ≈ 2.778 scale)
          // so that canvas regions and overlay bboxes align with the rendered image.
          const viewport = page.getViewport({ scale: 200 / 72 });
          const canvas = document.createElement("canvas");
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          const ctx = canvas.getContext("2d")!;
          await page.render({ canvasContext: ctx, viewport }).promise;
          if (!cancelled) setRenderedUrl(canvas.toDataURL("image/png"));
        } catch (err) {
          console.error("[PDF render error]", err);
        }
      })();
    }

    if (isTiffFile) {
      (async () => {
        try {
          const utifModule = await import("utif");
          const utif = (utifModule as any).default ?? utifModule;
          const arrayBuffer = await selectedFile.arrayBuffer();
          const ifds = utif.decode(arrayBuffer);
          utif.decodeImage(arrayBuffer, ifds[0]);
          const first = ifds[0];
          const rgba = utif.toRGBA8(first);
          const canvas = document.createElement("canvas");
          canvas.width = first.width;
          canvas.height = first.height;
          const ctx = canvas.getContext("2d")!;
          const imageData = ctx.createImageData(first.width, first.height);
          imageData.data.set(rgba);
          ctx.putImageData(imageData, 0, 0);
          if (!cancelled) setRenderedUrl(canvas.toDataURL("image/png"));
        } catch (err) {
          console.error("[TIFF render error]", err);
        }
      })();
    }

    return () => {
      cancelled = true;
      URL.revokeObjectURL(url);
    };
  }, [selectedFile]);

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  async function detectCorners(file: File) {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/preprocess/corners`, { method: "POST", body: formData });
      if (!res.ok) { console.error("[corners] HTTP", res.status); return; }
      const json = await res.json();
      console.log("[corners]", json);
      if (json.corners?.length === 4) setCorners(json.corners);
    } catch (e) { console.error("[corners] error", e); }
  }

  async function runPreprocess(file: File) {
    setIsPreprocessing(true);
    setPreprocessResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/preprocess/info`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("전처리 요청 실패");
      const json = await res.json();
      setPreprocessResult(json.result ?? null);
    } catch (err) {
      console.error("[Preprocess error]", err);
      await ui.alert("전처리 중 오류가 발생했습니다.");
    } finally {
      setIsPreprocessing(false);
    }
  }

  function pickFile(f: File) {
    uploadStartRef.current = Date.now();
    setSelectedFile(f);
    setOcrResult(null);
    setProcessedImageUrl(null);
    // 코너/전처리 자동 호출 비활성화 — Test 탭과 동일하게 백엔드 detect_document 에 위임
    // setCorners([]);
    // setShowCornerAdjust(false);
    // void runPreprocess(f);
    // void detectCorners(f);
  }

  function formatFileType(file: File) {
    return file.name.split(".").pop()?.toUpperCase() ?? file.type;
  }

  function buildRunOcrResult(raw: any, template?: TemplateItem): OcrResult {
    // 템플릿이 없거나 mode 가 "unstructured" 인 경우 Test 탭과 동일하게
    // receipt_fields / finance_fields 기반으로 fields 를 재구성한다.
    // 템플릿이 있고 region-based(mode !== "unstructured") 이면 백엔드가 region 별로
    // 추출해 둔 raw.fields 를 그대로 사용한다.
    if (template && template.mode !== "unstructured") {
      // Enrich raw.fields with ko/en labels from template regions so the
      // Preview overlay and result table show human-readable field names.
      const regions: any[] = (template as any).regions ?? [];
      const enriched = ((raw.fields ?? []) as any[]).map((field: any, i: number) => {
        const region = regions[i] ?? {};
        return {
          ...field,
          ko: field.ko || String(region.koField ?? "").trim() || "",
          en: field.en || String(region.enField ?? region.canonicalField ?? "").trim() || "",
        };
      });
      return { ...raw, fields: enriched };
    }

    const receiptFields = raw.receipt_fields ?? {};
    const financeFields = raw.finance_fields ?? {};
    const templateFields = template?.fields ?? [];
    const resultFields: OcrFieldResult[] = [];

    // 한글 라벨 ↔ 백엔드 키(영문 short form) alias.
    // 백엔드 receipt_fields 키: 회사명, 사업자번호, 대표자, tel, 주소, 총합계금액
    // 템플릿이 koField="전화번호" 로 정의되어 있어도 receipt_fields["tel"] 을 가져오게 함.
    const RECEIPT_ALIAS: Record<string, string> = {
      "전화번호": "tel",
      "Tel": "tel",
      "TEL": "tel",
    };
    const pickValue = (map: Record<string, unknown>, label: string): { key: string; value: unknown } | undefined => {
      if (!label) return undefined;
      if (label in map) return { key: label, value: map[label] };
      const alias = RECEIPT_ALIAS[label];
      if (alias && alias in map) return { key: alias, value: map[alias] };
      const normalizedLabel = normalizeAutofillFieldKey(label);
      for (const [key, value] of Object.entries(map)) {
        if (normalizeAutofillFieldKey(key) === normalizedLabel) return { key, value };
      }
      return undefined;
    };

    if (templateFields.length > 0) {
      templateFields.forEach((field, index) => {
        const ko = String(field.koField ?? "").trim();
        const en = String(field.enField ?? "").trim();
        const picked = pickValue(receiptFields, ko)
          ?? pickValue(receiptFields, en)
          ?? pickValue(financeFields, ko)
          ?? pickValue(financeFields, en)
          ?? { key: "", value: "" };
        const value = picked.value;
        resultFields.push({
          name: ko || en || `field_${index + 1}`,
          ko,
          en,
          field_type: "field",
          value: String(value ?? ""),
          confidence: value ? 1 : 0,
          bbox: [0, 0, 0, 0],
        });
      });
    } else if (Object.keys(receiptFields).length > 0) {
      Object.entries(receiptFields).forEach(([name, value]) => {
        resultFields.push({
          name,
          field_type: "field",
          value: String(value ?? ""),
          confidence: value ? 1 : 0,
          bbox: [0, 0, 0, 0],
        });
      });
    }

    if (resultFields.length === 0 && Object.keys(financeFields).length > 0) {
      Object.entries(financeFields).forEach(([name, value]) => {
        resultFields.push({
          name,
          field_type: "field",
          value: String(value ?? ""),
          confidence: value ? 1 : 0,
          bbox: [0, 0, 0, 0],
        });
      });
    }

    return {
      ...raw,
      fields: resultFields.length > 0 ? resultFields : (raw.fields ?? []),
    };
  }

  function hasValidBbox(field: OcrFieldResult) {
    return Array.isArray(field.bbox)
      && field.bbox.length >= 4
      && field.bbox[2] > 0
      && field.bbox[3] > 0;
  }

  function normalizeBbox(raw: unknown): FieldSourceBox | null {
    const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
    if (!raw) return null;
    if (Array.isArray(raw)) {
      if (raw.length >= 4 && raw.every(finite)) {
        const [x, y, width, height] = raw;
        return width > 0 && height > 0 ? { x, y, width, height } : null;
      }
      if (raw.length >= 4 && raw.every((p) => Array.isArray(p) && p.length >= 2 && finite(p[0]) && finite(p[1]))) {
        const points = raw as number[][];
        const xs = points.map((p) => p[0]);
        const ys = points.map((p) => p[1]);
        const x = Math.min(...xs);
        const y = Math.min(...ys);
        const width = Math.max(...xs) - x;
        const height = Math.max(...ys) - y;
        return width > 0 && height > 0 ? { x, y, width, height } : null;
      }
      return null;
    }
    if (typeof raw !== "object") return null;
    const box = raw as Record<string, unknown>;
    const x = box.x ?? box.left;
    const y = box.y ?? box.top;
    const width = box.width;
    const height = box.height;
    if (finite(x) && finite(y) && finite(width) && finite(height)) {
      return width > 0 && height > 0 ? { x, y, width, height } : null;
    }
    if (finite(box.x1) && finite(box.y1) && finite(box.x2) && finite(box.y2)) {
      const bx = Math.min(box.x1, box.x2);
      const by = Math.min(box.y1, box.y2);
      const bw = Math.abs(box.x2 - box.x1);
      const bh = Math.abs(box.y2 - box.y1);
      return bw > 0 && bh > 0 ? { x: bx, y: by, width: bw, height: bh } : null;
    }
    return null;
  }

  function normalizeTextForMatch(value: string) {
    return String(value ?? "")
      .toLowerCase()
      .replace(/[₩￦원,\s\-()./\\[\]{}:;'"`_*~!@#$%^&+=|<>?]/g, "");
  }

  function normalizeTextWithIndexMap(value: string) {
    const chars: string[] = [];
    const indexMap: number[] = [];
    const text = String(value ?? "").toLowerCase();
    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      if (/[₩￦원,\s\-()./\\[\]{}:;'"`_*~!@#$%^&+=|<>?]/.test(ch)) continue;
      chars.push(ch);
      indexMap.push(i);
    }
    return { text: chars.join(""), indexMap };
  }

  function digitsOnly(value: string) {
    return String(value ?? "").replace(/\D/g, "");
  }

  function rawTextOf(field: OcrFieldResult) {
    return String(field.value || field.name || "");
  }

  function matchScore(fieldValue: string, rawValue: string) {
    const fieldNorm = normalizeTextForMatch(fieldValue);
    const rawNorm = normalizeTextForMatch(rawValue);
    if (!fieldNorm || !rawNorm) return 0;
    if (fieldNorm === rawNorm) return 100;
    if (rawNorm.includes(fieldNorm)) return 90;
    if (fieldNorm.includes(rawNorm) && rawNorm.length >= Math.min(4, fieldNorm.length)) return 70;
    const fieldDigits = digitsOnly(fieldValue);
    const rawDigits = digitsOnly(rawValue);
    if (fieldDigits && rawDigits) {
      if (fieldDigits === rawDigits) return 95;
      if (rawDigits.includes(fieldDigits)) return 85;
      if (fieldDigits.includes(rawDigits) && rawDigits.length >= 4) return 65;
    }
    return 0;
  }

  function findSegmentRange(lineText: string, fieldValue: string): { start: number; end: number } | null {
    const rawLine = String(lineText ?? "");
    const rawField = String(fieldValue ?? "");
    if (!rawLine.trim() || !rawField.trim()) return null;

    const exactIndex = rawLine.indexOf(rawField);
    if (exactIndex >= 0) return { start: exactIndex, end: exactIndex + rawField.length };

    const lineNorm = normalizeTextWithIndexMap(rawLine);
    const fieldNorm = normalizeTextForMatch(rawField);
    if (fieldNorm) {
      const normIndex = lineNorm.text.indexOf(fieldNorm);
      if (normIndex >= 0) {
        const start = lineNorm.indexMap[normIndex] ?? 0;
        const end = (lineNorm.indexMap[normIndex + fieldNorm.length - 1] ?? start) + 1;
        return { start, end };
      }
    }

    const fieldDigits = digitsOnly(rawField);
    if (fieldDigits.length >= 3) {
      const digitLine = rawLine.split("").reduce<{ text: string; indexMap: number[] }>((acc, ch, index) => {
        if (/\d/.test(ch)) {
          acc.text += ch;
          acc.indexMap.push(index);
        }
        return acc;
      }, { text: "", indexMap: [] });
      const digitIndex = digitLine.text.indexOf(fieldDigits);
      if (digitIndex >= 0) {
        const start = digitLine.indexMap[digitIndex] ?? 0;
        const end = (digitLine.indexMap[digitIndex + fieldDigits.length - 1] ?? start) + 1;
        return { start, end };
      }
    }

    return null;
  }

  function clampBbox(box: FieldSourceBox, outer: FieldSourceBox): FieldSourceBox | null {
    const minWidth = Math.min(Math.max(10, outer.height * 0.7), outer.width);
    const x = Math.max(outer.x, Math.min(box.x, outer.x + outer.width));
    const y = Math.max(outer.y, Math.min(box.y, outer.y + outer.height));
    const right = Math.min(outer.x + outer.width, Math.max(x + minWidth, box.x + box.width));
    const bottom = Math.min(outer.y + outer.height, Math.max(y + 2, box.y + box.height));
    const width = right - x;
    const height = bottom - y;
    return width > 0 && height > 0 ? { x, y, width, height } : null;
  }

  function estimatePartialBboxFromLine(lineText: string, fieldValue: string, lineBox: FieldSourceBox): FieldSourceBox | null {
    const range = findSegmentRange(lineText, fieldValue);
    if (!range) return null;
    const lineLength = Math.max(1, String(lineText ?? "").length);
    const startRatio = Math.max(0, Math.min(1, range.start / lineLength));
    const endRatio = Math.max(startRatio, Math.min(1, range.end / lineLength));
    const padRatio = Math.min(0.015, 1 / lineLength);
    const x = lineBox.x + Math.max(0, startRatio - padRatio) * lineBox.width;
    const width = Math.max(lineBox.height * 0.8, (endRatio - startRatio + padRatio * 2) * lineBox.width);
    return clampBbox({ x, y: lineBox.y, width, height: lineBox.height }, lineBox);
  }

  function shouldAllowLineFallback(lineText: string, fieldValue: string, lineBox: FieldSourceBox) {
    const lineLen = normalizeTextForMatch(lineText).length;
    const fieldLen = normalizeTextForMatch(fieldValue).length;
    if (!lineLen || !fieldLen) return false;
    const ratio = fieldLen / lineLen;
    return lineLen <= 12 || ratio >= 0.6 || lineBox.width <= lineBox.height * 8;
  }

  function isAddressField(field: OcrFieldResult) {
    return normalizeAutofillFieldKey(field.ko || field.name || field.en || "") === "주소";
  }

  function isRepresentativeField(field: OcrFieldResult) {
    return normalizeAutofillFieldKey(field.ko || field.name || field.en || "") === "대표자";
  }

  function hangulNameDistance(a: string, b: string) {
    if (a.length !== b.length) return Number.POSITIVE_INFINITY;
    let distance = 0;
    for (let i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) distance++;
    }
    return distance;
  }

  function representativeLineScore(fieldValue: string, rawValue: string) {
    const target = String(fieldValue ?? "").replace(/\s+/g, "");
    if (!/^[가-힣]{2,4}$/.test(target)) return 0;
    const candidates = String(rawValue ?? "").match(/[가-힣]{2,4}/g) ?? [];
    for (const candidate of candidates) {
      if (candidate === target) return 90;
      if (hangulNameDistance(candidate, target) === 1) return 72;
    }
    return 0;
  }

  function isBadAddressLine(lineText: string) {
    const text = String(lineText ?? "");
    return (
      /\d{2,3}-?\d{3,4}-?\d{4}/.test(text) ||
      /\d{3}-?\d{2}-?\d{5}/.test(text) ||
      /\d{1,3},\d{3}/.test(text) ||
      /(승인|거래일시|전표|가맹no|가맹NO|판매금액|부가가치세|합계)/i.test(text)
    );
  }

  function adoptionOfField(field: OcrFieldResult): FieldOverlayAdoption {
    if (field.autofillAction === "corrected" || field.autofillAction === "filled") return "restored";
    if (field.value && String(field.value).trim()) return "ocr";
    return "unknown";
  }

  function attachSourceBboxes(fields: OcrFieldResult[], rawFields: OcrFieldResult[]): OcrFieldResult[] {
    const rawCandidates = rawFields
      .map((raw) => {
        const flexible = raw as BboxLikeField;
        const box = normalizeBbox(flexible.bbox ?? flexible.boundingBox ?? flexible.box ?? flexible);
        return box ? { raw, box, text: rawTextOf(raw) } : null;
      })
      .filter((item): item is { raw: OcrFieldResult; box: FieldSourceBox; text: string } => !!item);

    return fields.map((field) => {
      const adoption = adoptionOfField(field);
      const lookupValue = field.autofillAction === "corrected"
        ? field.original || field.value
        : field.value;
      if (field.autofillAction === "filled" && !field.original) {
        return { ...field, sourceBboxes: [], overlayAdoption: adoption };
      }
      const boxes = rawCandidates
        .filter((candidate) => !isAddressField(field) || !isBadAddressLine(candidate.text))
        .map((candidate) => {
          const lookupText = String(lookupValue ?? "");
          const score = Math.max(
            matchScore(lookupText, candidate.text),
            isRepresentativeField(field) ? representativeLineScore(lookupText, candidate.text) : 0,
          );
          const partial = score > 0 ? estimatePartialBboxFromLine(candidate.text, lookupText, candidate.box) : null;
          const allowFuzzyRepresentativeLine = isRepresentativeField(field) && representativeLineScore(lookupText, candidate.text) > 0;
          const box = partial ?? (allowFuzzyRepresentativeLine || shouldAllowLineFallback(candidate.text, lookupText, candidate.box) ? candidate.box : null);
          return { box, score };
        })
        .filter((candidate): candidate is { box: FieldSourceBox; score: number } => !!candidate.box)
        .filter((candidate) => candidate.score >= 65)
        .sort((a, b) => b.score - a.score)
        .slice(0, isAddressField(field) ? 2 : 1)
        .map((candidate) => candidate.box);
      const first = boxes[0];
      return {
        ...field,
        bbox: first ? [first.x, first.y, first.width, first.height] : field.bbox,
        sourceBboxes: boxes,
        overlayAdoption: adoption,
      };
    });
  }

  function buildResultRegions(runResult: OcrResult, template?: TemplateItem): Region[] {
    const ocrFieldRegions = (runResult.fields ?? [])
      .flatMap((field: OcrFieldResult, index: number) => {
        const sourceBox = unionSourceBoxes(field.sourceBboxes ?? []);
        const bboxBox = hasValidBbox(field)
          ? { x: field.bbox[0], y: field.bbox[1], width: field.bbox[2], height: field.bbox[3] }
          : null;
        const box = sourceBox ?? bboxBox;
        if (!box) return [];
        return [{
          id: ocrRegionIdForField(index),
          name: field.name,
          fieldType: (field.field_type || "field") as FieldType,
          x: box.x,
          y: box.y,
          width: box.width,
          height: box.height,
        }];
      });
    if (ocrFieldRegions.length > 0) return ocrFieldRegions;

    if (isRunOcr && template?.regions?.length) {
      return template.regions.map((region, index) => ({
        ...region,
        id: ocrRegionIdForField(index),
        name: region.name || runResult.fields?.[index]?.name || `field_${index + 1}`,
        fieldType: (region.fieldType || runResult.fields?.[index]?.field_type || "field") as FieldType,
      }));
    }

    return (runResult.fields ?? [])
      .flatMap((field: OcrFieldResult, index: number) => {
        const box = hasValidBbox(field)
          ? { x: field.bbox[0], y: field.bbox[1], width: field.bbox[2], height: field.bbox[3] }
          : null;
        if (!box) return [];
        return [{
          id: ocrRegionIdForField(index),
          name: field.name,
          fieldType: (field.field_type || "field") as FieldType,
          x: box.x,
          y: box.y,
          width: box.width,
          height: box.height,
        }];
      });
  }

  async function runOcr() {
    if (!selectedFile) return;
    if (isRunOcr && !activeTemplateId) {
      await ui.alert("상단에서 템플릿을 선택한 뒤 Run OCR을 실행하세요.");
      return;
    }
    setIsOcrRunning(true);
    const activeTemplate = templates.find((t) => t.id === activeTemplateId);
    const useRegionTemplate = !!activeTemplate && activeTemplate.mode !== "unstructured";
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (activeTemplateId) formData.append("template_id", activeTemplateId);
      if (useRegionTemplate && activeTemplate?.regions?.length) {
        formData.append("regions", JSON.stringify(activeTemplate.regions));
      }
      if (isRunOcr) formData.append("model_id", selectedModelId);
      // T-9-fix: pass documentType from template metadata to backend for routing priority
      if (activeTemplate?.documentType) {
        formData.append("documentType", activeTemplate.documentType);
      }
      // 코너 페이로드 비활성화 — 백엔드 detect_document 자동 경로 사용 (Test 와 동일)
      // if (corners.length === 4) formData.append("corners", JSON.stringify(corners));
      const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || "";
      const ocrEndpoint = backendBase ? `${backendBase}/ocr/extract` : "/api/ocr-extract";
      const res = await fetch(ocrEndpoint, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("OCR 요청 실패");
      const json = await res.json();
      // 거래명세서 등 일부 template 경로에서 백엔드가 ocr_lines(전체 OCR 라인)를 추가로 반환한다.
      // template region 결과(json.fields)는 region 개수만큼만 있으므로 "전체 OCR 텍스트"
      // 섹션에는 ocr_lines가 있으면 그걸 우선 사용해 모든 라인을 표시한다.
      const ocrLinesFromBackend: Array<{ text: string; confidence: number }> =
        Array.isArray((json as any)?.ocr_lines) ? (json as any).ocr_lines : [];
      const rawOcrFields: OcrFieldResult[] = ocrLinesFromBackend.length > 0
        ? ocrLinesFromBackend.map((line, idx) => ({
            name: `field_${idx + 1}`,
            field_type: "field",
            value: line.text,
            confidence: line.confidence,
            bbox: [0, 0, 0, 0],
          }))
        : (Array.isArray(json?.fields) ? (json.fields as OcrFieldResult[]) : []);
      const runResult = isRunOcr ? buildRunOcrResult(json, activeTemplate) : json;
      runResult.raw_ocr_fields = rawOcrFields;
      const originalRunFields: OcrFieldResult[] = ((runResult.fields ?? []) as OcrFieldResult[]).map((field) => ({
        ...field,
        source: field.value && String(field.value).trim() ? "ocr" : field.source,
      }));
      let autofillSuggestions: AutofillSuggestion[] = [];
      let autofillSummary: AutofillRunSummary = {
        status: "not_run",
        candidateCount: 0,
        confirmedCount: 0,
        correctedCount: 0,
        filledCount: 0,
        message: "자동복원: 미실행",
      };
      // 자동복원은 비정형(unstructured) 모드 전용. region-based 템플릿은 스킵.
      // 데이터 소스: restoreProfileStore (Restore 페이지에서 등록한 프로필).
      const isUnstructuredAutofill = !!activeTemplate && activeTemplate.mode === "unstructured";
      if (!isUnstructuredAutofill) {
        runResult.fields = originalRunFields;
      } else try {
        const businessText = [
          json?.full_text,
          runResult?.full_text,
          ...originalRunFields.map((f: OcrFieldResult) => f.value),
          ...rawOcrFields.map((f) => f.value),
          json?.receipt_fields?.["사업자번호"],
        ].filter(Boolean).join("\n");
        const businessNumber = extractBizNumber(businessText);
        if (!businessNumber) {
          runResult.fields = originalRunFields;
          autofillSummary = {
            status: "no_business_number",
            candidateCount: 0,
            confirmedCount: 0,
            correctedCount: 0,
            filledCount: 0,
            message: "자동복원: 사업자번호 없음",
          };
        } else {
          const internalSuggestions = buildAutofillSuggestionsFromCandidates({
            businessNumber,
            candidates: collectInternalAutofillCandidates(businessNumber),
            templateName: activeTemplate?.name ?? null,
            fileName: selectedFile.name,
          });
          const hasBusinessNumberField = originalRunFields.some((field) => {
            const key = normalizeAutofillFieldKey(field.ko || field.en || field.name);
            return key === "사업자번호";
          });
          const businessNumberSuggestion: AutofillSuggestion[] = hasBusinessNumberField
            ? [{
                field: "사업자번호",
                value: businessNumber,
                source: "biz",
                confidence: 0.99,
                label: "매칭복원",
                reason: "현재 OCR 전체 텍스트에서 추출한 사업자번호",
              }]
            : [];
          autofillSuggestions = [...businessNumberSuggestion, ...internalSuggestions];
          runResult.fields = applyAutofillToOutputFields({
            fields: originalRunFields,
            suggestions: autofillSuggestions,
          });
          const resultFields = ((runResult.fields ?? []) as OcrFieldResult[]);
          const confirmedCount = resultFields.filter((field) => field.autofillAction === "confirmed").length;
          const correctedCount = resultFields.filter((field) => field.autofillAction === "corrected").length;
          const filledCount = resultFields.filter((field) => field.autofillAction === "filled").length;
          const skippedCount = originalRunFields.filter((field) => {
            const key = normalizeAutofillFieldKey(field.ko || field.en || field.name);
            if (isAutofillableField(key)) return false;
            return autofillSuggestions.some((suggestion) => normalizeAutofillFieldKey(suggestion.field) === key && canAutoApplySuggestion(suggestion));
          }).length;
          const status: AutofillRunSummary["status"] =
            autofillSuggestions.length === 0 ? "no_candidates" :
            correctedCount > 0 && filledCount === 0 ? "corrected" :
            filledCount > 0 ? "applied" :
            confirmedCount > 0 ? "confirmed" :
            "no_candidates";
          autofillSummary = {
            status,
            businessNumber,
            candidateCount: autofillSuggestions.length,
            confirmedCount,
            correctedCount,
            filledCount,
            skippedCount,
            message:
              status === "no_candidates" ? "자동복원: 같은 사업자번호의 저장 기록 없음" :
              status === "corrected" ? `자동복원: 보정 ${correctedCount}건 · 확인 ${confirmedCount}건` :
              status === "applied" ? `자동복원: 채움 ${filledCount}건 · 보정 ${correctedCount}건 · 확인 ${confirmedCount}건` :
              `자동복원: 확인 ${confirmedCount}건 · 보정 0건`,
          };
        }
      } catch (err) {
        console.warn("[autofill] skipped", err);
        runResult.fields = originalRunFields;
        autofillSummary = {
          status: "not_run",
          candidateCount: 0,
          confirmedCount: 0,
          correctedCount: 0,
          filledCount: 0,
          message: "자동복원: 미실행",
        };
      }
      runResult.fields = attachSourceBboxes((runResult.fields ?? []) as OcrFieldResult[], rawOcrFields);
      if (isUnstructuredAutofill) {
        runResult.autofill_summary = autofillSummary;
      }
      setOcrResult(runResult);
      if (runResult.processed_image) {
        setProcessedImageUrl(runResult.processed_image);
      }
      const ocrRegions = buildResultRegions(runResult, activeTemplate);
      setCanvasRegions((prev) => {
        const userRegions = prev.filter((r) => !r.id.startsWith("ocr_"));
        return [...ocrRegions, ...userRegions];
      });
      setCanvasSelectedId(null);
      // OCR 데이터 표는 백엔드 raw OCR 결과를 그대로 보여준다 (정제된 receipt_fields 가 아님).
      // 출력 필드 표는 runResult.fields(receipt_fields/template 매핑) 를 사용 → 명확한 분리.
      const isRegionBased =
        !!activeTemplate &&
        activeTemplate.mode !== "unstructured" &&
        (activeTemplate.regions?.length ?? 0) > 0;
      // 비정형 경로와 동일하게: 백엔드가 ocr_lines(전체 raw 라인)를 반환하면 우선 사용.
      // 없으면 기존 template region 필드 기반 fallback.
      const rawOcrLines: { text: string; confidence: number }[] =
        Array.isArray((json as any)?.ocr_lines) ? (json as any).ocr_lines : [];
      const ocrFieldsForHistory: HistoryOcrField[] = rawOcrLines.length > 0
        ? rawOcrLines.map((line, idx) => ({
            name: `field_${idx + 1}`,
            field_type: "field" as const,
            value: line.text,
            confidence: line.confidence,
          }))
        : rawOcrFields.map((f: OcrFieldResult, idx: number) => {
            const tf = isRegionBased ? activeTemplate?.fields?.[idx] : undefined;
            const koFromRegion = isRegionBased
              ? String((activeTemplate?.regions?.[idx] as Record<string, unknown> | undefined)?.koField ?? "").trim()
              : "";
            return {
              name: f.name,
              en: tf?.enField,
              ko: tf?.koField || koFromRegion || undefined,
              field_type: f.field_type,
              value: f.value,
              confidence: f.confidence,
              bbox: f.bbox,
            };
          });
      // 출력 필드 표 데이터 — 정제된 결과(runResult.fields = template/receipt_fields 매핑) 기반.
      const tplFields = activeTemplate?.fields ?? [];
      const structuredFields: OcrFieldResult[] = (runResult.fields ?? []) as OcrFieldResult[];
      const outputFieldsForHistory: HistoryOutputField[] = tplFields.length
        ? tplFields.map((tf, idx) => {
            const ocrF = structuredFields[idx];
            const original = originalRunFields[idx]?.value ?? "";
            const modified = ocrF?.value ?? original;
            const suggestions = suggestionsForHistoryField(
              { en: tf.enField ?? `field_${idx + 1}`, ko: tf.koField ?? "" },
              autofillSuggestions,
            );
            return {
              no: tf.no ?? idx + 1,
              en: tf.enField ?? `field_${idx + 1}`,
              ko: tf.koField || ocrF?.ko || "",
              original,
              modified,
              confidence: Number(ocrF?.confidence ?? 0),
              source: ocrF?.source,
              applied: ocrF?.applied,
              autofillAction: ocrF?.autofillAction,
              suggestions: suggestions.length > 0 ? suggestions : undefined,
            };
          })
        : structuredFields.map((f: OcrFieldResult, idx: number) => {
            // 정형 템플릿은 template.fields[] 가 비어 있어 이 분기를 타지만,
            // runResult.fields 는 이미 region.koField/enField 로 enrich 되어 있으므로
            // 그것을 우선 사용한다. 비어 있으면 기존 name 기반 fallback.
            const isKorean = /[가-힯]/.test(f.name);
            const en = (typeof f.en === "string" && f.en) ? f.en : (isKorean ? "" : f.name);
            const ko = (typeof f.ko === "string" && f.ko) ? f.ko : (isKorean ? f.name : "");
            const original = originalRunFields[idx]?.value ?? "";
            const suggestions = suggestionsForHistoryField({ en, ko }, autofillSuggestions);
            return {
              no: idx + 1,
              en,
              ko,
              original,
              modified: f.value,
              confidence: f.confidence,
              source: f.source,
              applied: f.applied,
              autofillAction: f.autofillAction,
              suggestions: suggestions.length > 0 ? suggestions : undefined,
            };
          });
      const successRecord = appendHistoryRun({
        file_name: selectedFile.name,
        template_name: activeTemplate?.name ?? null,
        processing_time: Number(json?.processing_time) || 0,
        status: "success",
        // legacy 호환: image_url 유지
        image_url: runResult.processed_image,
        // H-2: 명시적 이미지 URL 필드
        processed_image_url: runResult.processed_image ?? null,
        original_image_url: runResult.original_image ?? null,
        image_storage_mode: "url",
        ocr_fields: ocrFieldsForHistory,
        output_fields: outputFieldsForHistory,
        autofill_summary: autofillSummary,
      });
      // HISTORY-STRUCTURE-2A: index/detail 병행 저장 (실패해도 기존 flow 유지)
      try {
        const rawDocFields = (json as Record<string, unknown>)?.document_fields as
          HistoryDetailDocumentFields | undefined;
        syncHistoryIndexAndDetailOnCreate(successRecord, {
          documentType: activeTemplate?.documentType || undefined,
          documentFields: rawDocFields,
        });
      } catch (e) {
        console.warn("[history-structure] index/detail sync failed on create", e);
      }
      setCurrentJobId(successRecord.job_id);
      setCurrentCreatedAt(successRecord.created_at);
      setInitialOutputFields(outputFieldsForHistory);
    } catch (err) {
      console.error("[OCR error]", err);
      const failRecord = appendHistoryRun({
        file_name: selectedFile.name,
        template_name: activeTemplate?.name ?? null,
        processing_time: 0,
        status: "fail",
      });
      setCurrentJobId(failRecord.job_id);
      setCurrentCreatedAt(failRecord.created_at);
      setInitialOutputFields(null);
      await ui.alert("OCR 처리 중 오류가 발생했습니다.");
    } finally {
      setIsOcrRunning(false);
    }
  }

  // displayUrl 변경 시 canvasLoaded 업데이트
  useEffect(() => {
    // OCR 완료 후엔 전처리된 이미지 사용, 아니면 원본
    const url = processedImageUrl
      ?? ((selectedFile?.type === "application/pdf" || (selectedFile && isTiff(selectedFile)))
        ? renderedUrl : previewUrl);
    if (!url) { setCanvasLoaded(null); return; }
    const img = new Image();
    img.onload = () => {
      setCanvasLoaded({
        src: url,
        fileName: selectedFile?.name ?? "",
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
      });
    };
    img.src = url;
  }, [previewUrl, renderedUrl, selectedFile, processedImageUrl]);

  const needsRender = selectedFile
    ? selectedFile.type === "application/pdf" || isTiff(selectedFile)
    : false;

  const displayUrl = needsRender ? renderedUrl : previewUrl;
  const isRendering = needsRender && !renderedUrl && !!previewUrl;
  const canRunOcr = !!selectedFile && !isPreprocessing && !isOcrRunning && (!isRunOcr || !!activeTemplateId);

  // OCR 결과 화면에서 사용할 URL (전처리 이미지 우선)
  const ocrDisplayUrl = processedImageUrl ?? displayUrl;
  const activeTemplateForPanel = templates.find((t) => t.id === activeTemplateId);

  useEffect(() => {
    if (!ocrResult) return;
    const ocrRegions = buildResultRegions(ocrResult, activeTemplateForPanel);
    if (ocrRegions.length === 0) return;
    setCanvasRegions((prev) => {
      const existingIds = new Set(prev.map((region) => region.id));
      const missing = ocrRegions.filter((region) => !existingIds.has(region.id));
      if (missing.length === 0) return prev;
      return [...missing, ...prev];
    });
  }, [ocrResult, activeTemplateForPanel]);

  const customSelectedFieldIndex =
    selectedFieldIndex != null && selectedFieldIndex >= 0 ? selectedFieldIndex : null;
  const customHasSelectedFieldRegion =
    customSelectedFieldIndex != null
      ? canvasRegions.some((region) => region.id === ocrRegionIdForField(customSelectedFieldIndex))
      : false;
  const customSelectedUserRegionId =
    canvasSelectedId && fieldIndexFromOcrRegionId(canvasSelectedId) == null ? canvasSelectedId : null;
  const customDrawTargetRegionId =
    resultTab === "custom" && customSelectedFieldIndex != null
      ? ocrRegionIdForField(customSelectedFieldIndex)
      : null;
  const customDrawTargetField = customSelectedFieldIndex != null
    ? ocrResult?.fields?.[customSelectedFieldIndex]
    : undefined;
  const customVisibleRegionIds =
    resultTab !== "custom"
      ? undefined
      : customSelectedFieldIndex != null
        ? customHasSelectedFieldRegion
          ? [ocrRegionIdForField(customSelectedFieldIndex)]
          : customSelectedUserRegionId
            ? [customSelectedUserRegionId]
            : []
        : canvasSelectedId
          ? [canvasSelectedId]
          : [];
  const customEmptySelectionHint =
    resultTab === "custom" && customSelectedFieldIndex != null && !customHasSelectedFieldRegion && !customSelectedUserRegionId
      ? "선택한 필드의 OCR 원본 영역이 없습니다. 좌측 이미지에서 영역을 지정하거나 최종값을 직접 입력하세요."
      : undefined;

  // Custom 탭 onBlur 자동저장 — 사용자 편집을 history.output_fields.modified 에 반영.
  // immutable 메타(no/en/ko/original/applied/autofillAction/suggestions)는 initialOutputFields 에서 보존.
  // initialOutputFields 가 null 이면 success 레코드가 아니므로 자동저장을 건너뛴다.
  const handlePersistEdits = (edited: OcrFieldResult[]) => {
    if (!currentJobId || !initialOutputFields) return;
    const initial = initialOutputFields;
    const merged: HistoryOutputField[] = edited.map((field, idx) => {
      const base = initial[idx];
      return {
        no: base?.no ?? idx + 1,
        en: base?.en ?? field.en ?? "",
        ko: base?.ko ?? field.ko ?? "",
        original: base?.original ?? "",
        modified: field.value,
        confidence: Number(field.confidence ?? base?.confidence ?? 0),
        source: field.source ?? base?.source,
        applied: field.applied ?? base?.applied,
        autofillAction: field.autofillAction ?? base?.autofillAction,
        suggestions: base?.suggestions,
      };
    });
    updateHistoryRun(currentJobId, { output_fields: merged });
  };

  const handleResultClose = () => {
    // X 버튼: RunOCR 진입 초기 화면(파일 미선택 상태)으로 복귀
    setOcrResult(null);
    setProcessedImageUrl(null);
    setCurrentJobId(null);
    setCurrentCreatedAt(null);
    setInitialOutputFields(null);
    setSelectedFieldIndex(null);
    setCanvasSelectedId(null);
    setSelectedFile(null);
    setPreprocessResult(null);
    setCorners([]);
    setShowCornerAdjust(false);
  };

  // OCR 결과 화면
  if (ocrResult && selectedFile) {
    return (
      <div className="uw-result-root">
        {/* 왼쪽: Custom 탭이면 OcrCanvasPane, 아니면 OcrDocViewer */}
        <div className="uw-result-doc" style={{ position: "relative" }}>
          {ocrDisplayUrl && resultTab === "custom" && canvasLoaded ? (
            <OcrCanvasPane
              imgRef={canvasImgRef}
              loaded={canvasLoaded}
              regions={canvasRegions}
              setRegions={setCanvasRegions}
              selectedId={canvasSelectedId}
              setSelectedId={setCanvasSelectedId}
              drawMode={canvasDrawMode}
              setDrawMode={setCanvasDrawMode}
              zoomPct={canvasZoom}
              rowTemplateTargetId={rowTemplateTargetId}
              setRowTemplateTargetId={setRowTemplateTargetId}
              colGuideTargetId={colGuideTargetId}
              setColGuideTargetId={setColGuideTargetId}
              visibleRegionIds={customVisibleRegionIds}
              emptySelectionHint={customEmptySelectionHint}
              drawTargetRegionId={customDrawTargetRegionId}
              drawTargetName={customDrawTargetField?.name}
              drawTargetFieldType={(canvasDrawMode || customDrawTargetField?.field_type || "field") as FieldType}
              bboxImageWidth={activeTemplateForPanel?.image?.width}
              bboxImageHeight={activeTemplateForPanel?.image?.height}
              onClearSelection={() => {
                setSelectedFieldIndex(null);
                setCanvasSelectedId(null);
              }}
            />
          ) : ocrDisplayUrl ? (
            <OcrDocViewer
              imageUrl={ocrDisplayUrl}
              fields={ocrResult.fields}
              selectedIndex={selectedFieldIndex}
              onSelectField={setSelectedFieldIndex}
              enableFieldOverlay={resultTab === "preview"}
              originalWidth={activeTemplateForPanel?.image?.width}
              originalHeight={activeTemplateForPanel?.image?.height}
            />
          ) : (
            <span style={{ color: "var(--muted)" }}>문서 영역</span>
          )}
          {isOcrRunning && <div className="uw-scan-overlay"><div className="uw-scan-line" /></div>}
        </div>

        {/* 오른쪽: 결과 패널 */}
        <div className="uw-result-panel">
          <OcrResultPanel
            result={ocrResult}
            onRerun={runOcr}
            onRevalidate={async (targets) => {
              if (!selectedFile) return [];
              const formData = new FormData();
              // 전처리된 이미지가 있으면 그걸 사용 (bbox 좌표 일치)
              if (processedImageUrl) {
                const blob = await fetch(processedImageUrl).then((r) => r.blob());
                formData.append("file", blob, "processed.jpg");
              } else {
                formData.append("file", selectedFile);
              }
              const url = `/ocr/revalidate?regions=${encodeURIComponent(JSON.stringify(targets))}`;
              const res = await fetch(url, { method: "POST", body: formData });
              if (!res.ok) throw new Error("재검증 실패");
              const json = await res.json();
              return json.results ?? [];
            }}
            selectedIndex={selectedFieldIndex}
            onSelectField={setSelectedFieldIndex}
            templateName={activeTemplateForPanel?.name ?? null}
            fileName={selectedFile?.name ?? ""}
            onTabChange={setResultTab}
            drawMode={canvasDrawMode}
            onDrawModeChange={(mode) => setCanvasDrawMode(mode as FieldType | null)}
            isScanning={isOcrRunning}
            onScanChange={setIsOcrRunning}
            canvasRegions={canvasRegions}
            jobId={currentJobId}
            createdAt={currentCreatedAt}
            onClose={handleResultClose}
            onPersist={handlePersistEdits}
            onPartialOcr={async (targets) => {
              if (!selectedFile) return [];
              const formData = new FormData();
              if (processedImageUrl) {
                const blob = await fetch(processedImageUrl).then((r) => r.blob());
                formData.append("file", blob, "processed.jpg");
              } else {
                formData.append("file", selectedFile);
              }
              const url = `/ocr/revalidate?regions=${encodeURIComponent(JSON.stringify(targets))}`;
              const res = await fetch(url, { method: "POST", body: formData });
              if (!res.ok) throw new Error("부분 OCR 실패");
              const json = await res.json();
              return json.results ?? [];
            }}
          />
        </div>

        {/* 숨겨진 파일 인풋 */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,application/pdf,.tif,.tiff"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) pickFile(f);
          }}
        />
      </div>
    );
  }

  return (
    <div className={isRunOcr ? "uw-root uw-root-runocr" : "uw-root"}>
      {/* Top: Template bar */}
      <div className={isRunOcr ? "uw-topbar uw-runocr-topbar" : "uw-topbar"}>
        {isRunOcr ? (
          <>
            <div className="uw-runocr-template-cards">
              {templates.length > 0 ? (
                templates.map((template) => (
                  <button
                    key={template.id}
                    type="button"
                    className={`uw-runocr-template-card ${activeTemplateId === template.id ? "uw-runocr-template-card-active" : ""}`}
                    onClick={() => {
                      setRunOcrTemplateMode("template");
                      setActiveTemplateId(template.id);
                    }}
                    title={template.name}
                    onMouseEnter={(e) => {
                      const imgSrc = template.imageSrc;
                      if (!imgSrc) return;
                      const rect = e.currentTarget.getBoundingClientRect();
                      setCardTooltip({ imgSrc, x: rect.left + rect.width / 2, y: rect.bottom + 10 });
                    }}
                    onMouseLeave={() => setCardTooltip(null)}
                  >
                    {template.mode === "unstructured" ? (
                      <span className="uw-runocr-template-card-preview">
                        <img
                          src="/images/unstructured-template-preview.svg"
                          alt=""
                          className="uw-template-card-img"
                        />
                      </span>
                    ) : template.imageSrc ? (
                      <span className="uw-runocr-template-card-preview">
                        <img
                          src={template.imageSrc}
                          alt=""
                          className="uw-template-card-img"
                          style={{ objectFit: "cover" }}
                        />
                      </span>
                    ) : (
                      <span className="uw-runocr-template-card-preview" />
                    )}
                    <span className="uw-runocr-template-card-name">{template.name}</span>
                  </button>
                ))
              ) : (
                <span className="uw-runocr-empty-template-text">저장된 템플릿이 없습니다.</span>
              )}
            </div>
          </>
        ) : (
          <>
            <span className="uw-topbar-label">Template</span>

            <div className="uw-topbar-group uw-template-select-wrap">
              <select
                value={activeTemplateId}
                onChange={(e) => setActiveTemplateId(e.target.value)}
                className="ms-select uw-template-select"
              >
                <option value="">자동 인식</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
              <span className="uw-select-arrow">▾</span>
            </div>

            <button type="button" className="hw-btn-primary" onClick={() => router.push("/ocr?mode=new")}>
              + New Template
            </button>
          </>
        )}
      </div>

      {/* Left: upload panel */}
      <div className="uw-upload-panel">
        <FileDropzone
          onPickFile={pickFile}
          fileInputRef={fileInputRef}
          hasFile={!!(previewUrl && selectedFile)}
        >
          {selectedFile && (
            <div className="uw-preview-wrap">
              <div className="uw-preview-img-area" style={{ position: "relative" }}>
                {isRendering ? (
                  <div className="uw-empty-sub" style={{ margin: "auto" }}>
                    {isTiff(selectedFile) ? "TIFF" : "PDF"} 렌더링 중...
                  </div>
                ) : displayUrl ? (
                  <img src={displayUrl} alt="preview" className="uw-preview-img" />
                ) : null}
                {isOcrRunning && <div className="uw-scan-overlay"><div className="uw-scan-line" /></div>}
              </div>
              <div className="uw-preview-footer">
                <div className="uw-filename-chip" title={selectedFile.name}>
                  {selectedFile.name}
                </div>
                <button type="button" onClick={openFilePicker} className="ms-btn-sm">
                  파일 변경
                </button>
              </div>
            </div>
          )}
        </FileDropzone>
      </div>

      {/* Right: guide or file info */}
      <aside className="uw-guide-panel">
        {isRunOcr && (
          <div className="uw-model-section">
            <label className="uw-model-label" htmlFor="runocr-model-select">모델 선택</label>
            <select
              id="runocr-model-select"
              value={selectedModelId}
              onChange={(e) => setSelectedModelId(e.target.value)}
              className="ms-select uw-model-select"
            >
              {MODEL_OPTIONS.map((model) => (
                <option key={model.id} value={model.id}>{model.name}</option>
              ))}
            </select>
          </div>
        )}
        {selectedFile ? (
          <div className="uw-guide-content">
            <div className="uw-file-section">
              <div className="uw-file-section-title">업로드 파일</div>
              <div className="uw-file-row">
                <span className="uw-file-label">파일명</span>
                <span className="uw-file-value" title={selectedFile.name}>{selectedFile.name}</span>
              </div>
              <div className="uw-file-row">
                <span className="uw-file-label">파일타입</span>
                <span className="uw-file-value">{formatFileType(selectedFile)}</span>
              </div>
              <div className="uw-file-row">
                <span className="uw-file-label">소요 시간</span>
                <span className="uw-file-value">{uploadDuration ?? "측정 중..."}</span>
              </div>
            </div>

            {/* 자동 처리 결과 패널 비활성화 — /preprocess/info 호출 안 함, Test 와 동일 흐름
            <div className="uw-file-section">
              <div className="uw-file-section-title">자동 처리 결과</div>
              {isPreprocessing ? (
                <div className="uw-process-item">
                  <span>전처리 진행 중...</span>
                </div>
              ) : preprocessResult ? (
                <>
                  <div className="uw-process-item">
                    <span>이미지 크기</span>
                    <span className="uw-process-done">{preprocessResult.image_size}</span>
                  </div>
                  {preprocessResult.document && (
                    <>
                      <div className="uw-process-item">
                        <span>문서 감지</span>
                        <span className="uw-process-done">{preprocessResult.document.status}</span>
                      </div>
                      <div className="uw-process-detail">{preprocessResult.document.detail}</div>
                    </>
                  )}
                  <div className="uw-process-item">
                    <span>해상도 보정</span>
                    <span className="uw-process-done">{preprocessResult.upscale.status}</span>
                  </div>
                  <div className="uw-process-detail">{preprocessResult.upscale.detail}</div>
                  <div className="uw-process-item">
                    <span>기울기 보정</span>
                    <span className="uw-process-done">{preprocessResult.deskew.status}</span>
                  </div>
                  <div className="uw-process-detail">{preprocessResult.deskew.detail}</div>
                  <div className="uw-process-item">
                    <span>노이즈 제거</span>
                    <span className="uw-process-done">{preprocessResult.denoise.status}</span>
                  </div>
                  <div className="uw-process-detail">{preprocessResult.denoise.detail}</div>
                  <div className="uw-process-item">
                    <span>대비 강화</span>
                    <span className="uw-process-done">{preprocessResult.contrast.status}</span>
                  </div>
                  <div className="uw-process-detail">{preprocessResult.contrast.detail}</div>
                </>
              ) : (
                <div className="uw-process-item">
                  <span>대기 중</span>
                </div>
              )}
            </div>
            */}
          </div>
        ) : (
          <div className="uw-guide-content">
            {hintSections.map((sec) => (
              <div key={sec.title} className="uw-guide-section">
                <div className="uw-guide-section-header">
                  <span className="uw-guide-section-title">{sec.title}</span>
                  <span className="uw-guide-section-desc">{sec.desc}</span>
                </div>
                <ul className="uw-guide-list">
                  {sec.items.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        <button
          type="button"
          disabled={!canRunOcr}
          className={`uw-run-btn ${isOcrRunning ? "uw-run-btn-loading" : ""}`}
          onClick={() => void runOcr()}
          title={isRunOcr && selectedFile && !activeTemplateId ? "상단 템플릿을 선택해야 실행할 수 있습니다." : undefined}
        >
          {isOcrRunning ? (
            <>
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none" style={{ animation: "spin 0.8s linear infinite" }}>
                <circle cx="10" cy="10" r="8" stroke="rgba(255,255,255,0.3)" strokeWidth="2.5"/>
                <path d="M10 2a8 8 0 0 1 8 8" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round"/>
              </svg>
              OCR 처리 중...
            </>
          ) : (
            "Run OCR"
          )}
        </button>
      </aside>
      {cardTooltip && (
        <div
          className="template-hover-tooltip"
          style={{
            position: "fixed",
            top: cardTooltip.y,
            left: Math.min(
              Math.max(cardTooltip.x - 160, 8),
              (typeof window !== "undefined" ? window.innerWidth : 1200) - 328,
            ),
            zIndex: 9999,
            borderRadius: 8,
            overflow: "hidden",
            boxShadow: "0 4px 20px rgba(0,0,0,0.35)",
            pointerEvents: "none",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={cardTooltip.imgSrc}
            alt=""
            style={{ width: 320, height: "auto", display: "block", borderRadius: 6 }}
          />
        </div>
      )}
    </div>
  );
}
