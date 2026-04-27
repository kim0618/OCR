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
import type { DatasetManifest, ManifestItem } from "@/lib/testsets";
import { resolveProfile, FINANCE_COLUMNS, isNotApplicableField } from "@/lib/profiles";

type ViewMode = "compare" | "ocr_only" | "autofill" | "gt_edit";

type DocTypeSummaryRow = {
  documentType: string;
  total: number;
  selected: number;
  suppressed: number;
  unknown: number;
  error: number;
  notRun: number;
  fieldFilled: Record<FieldKey, number>;
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
  { id: "new_samples", label: "신규 샘플셋", path: "/data/testsets/new_samples", description: "공개 샘플 기반 일반화 검증용" },
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

const datasetQuery = (datasetId: string) => `dataset=${encodeURIComponent(datasetId)}`;
const imageUrl = (baseUrl: string, filename: string) => `${baseUrl}/${encodeURIComponent(filename)}`;

function deriveUiStatus(data: OcrResponse): string {
  if (data.status) return data.status;
  if (data.doc_type === "bank_slip") return "suppressed_bank_slip";
  if (data.doc_type === "form_or_handwritten") return "suppressed_handwritten";
  if (data.doc_type === "unknown") return "unknown";
  return "selected";
}

async function readJsonResponse<T>(res: Response, label: string): Promise<T> {
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`${label} 실패 (${res.status}): ${text.slice(0, 180) || res.statusText}`);
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
  const ocrRes = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/ocr/extract`, { method: "POST", body: form });
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
    financeReviewReasons: data.finance_review_reasons,
  };
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
  const selGt  = selected ? (gt[selected]?.fields ?? EMPTY_ENTRY()) : EMPTY_ENTRY();
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
        map.set(dt, { documentType: dt, total: 0, selected: 0, suppressed: 0, unknown: 0, error: 0, notRun: 0, fieldFilled });
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
      return resolveProfile(dt).base !== "finance";
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

  // 영수증 계열 총 이미지 수 (미실행 포함) — receipt KPI 분모 (docs/TEST_PROFILE_SCHEMA §7.2)
  const receiptImageCount = useMemo(
    () => images.filter((img) => {
      if (!manifest) return true; // manifest 없으면 전체를 영수증으로 처리 (안전 fallback)
      const dt = manifest.items.find((i) => i.filename === img)?.documentType;
      return resolveProfile(dt).base !== "finance";
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

  // finance KPI — 단순 카운트 (parser 미구현 단계) (docs/TEST_SUPPRESSION_POLICY_NOTE §6.2)
  type FinanceKpiSummary = {
    total: number;      // 전체 finance 이미지 수 (미실행 포함)
    processed: number;  // OCR 실행 완료 건수
    selected: number;
    review: number;
    suppressed: number;
  };
  const financeKpi = useMemo((): FinanceKpiSummary => {
    const total = images.filter((img) => {
      const dt = manifest?.items.find((i) => i.filename === img)?.documentType;
      return resolveProfile(dt).base === "finance";
    }).length;
    let selected = 0, review = 0, suppressed = 0;
    for (const row of financeBatchRows) {
      const status = ocr[row.img]?.status ?? "";
      if (status === "selected") {
        selected++;
      } else if (status === "suppressed_bank_slip") {
        review++;          // suppression policy note §6.2: bank_slip → review 재분류
      } else if (status?.startsWith("suppressed_")) {
        suppressed++;
      } else {
        review++;          // unknown / empty 등 → review
      }
    }
    return { total, processed: financeBatchRows.length, selected, review, suppressed };
  }, [financeBatchRows, images, manifest, ocr]);

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
        <img src={imageUrl(activeTestset.path, img)} alt={img} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
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
        <div style={{ marginLeft: "auto", flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 5 }}>
          <span style={{ fontSize: 11, color: "var(--muted)" }}>
            {images.length > 0 ? `${images.length} files` : "0 files"}
          </span>
          <div style={{ display: "flex", gap: 5, flexWrap: "wrap", justifyContent: "flex-end" }}>
            <TopStatChip
              label="OCR 인식률"
              value={pct(kpi.norm.overallOk, kpi.norm.overallTotal)}
              sub={kpi.norm.overallTotal > 0 ? `${kpi.norm.overallOk}/${kpi.norm.overallTotal}` : undefined}
              tone={toneOf(kpi.norm.overallOk, kpi.norm.overallTotal)}
            />
            <TopStatChip
              label="최종 채택"
              value={pct(kpi.final.overallOk, kpi.final.overallTotal)}
              sub={kpi.final.overallTotal > 0 ? `${kpi.final.overallOk}/${kpi.final.overallTotal}` : undefined}
              tone={toneOf(kpi.final.overallOk, kpi.final.overallTotal)}
            />
            <TopStatChip label="처리" value={`${batchRows.length}/${images.length}`} />
            {kpi.norm.overallTotal > 0 && (
              <>
                <div style={{ width: 1, background: "rgba(255,255,255,0.1)", alignSelf: "stretch", margin: "0 2px" }} />
                {FIELDS.map((f) => {
                  const s = kpi.norm.fieldAcc[f.key];
                  if (s.total === 0) return null;
                  return (
                    <TopStatChip key={f.key} label={f.label} value={pct(s.ok, s.total)} sub={`${s.ok}/${s.total}`} tone={toneOf(s.ok, s.total)} />
                  );
                })}
              </>
            )}
          </div>
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

      {/* ── qualityTags 필터 ── */}
      {availableQualityTags.length > 0 && (
        <div style={styles.filterBar}>
          <span style={{ fontSize: 10, fontWeight: 800, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 0.5, whiteSpace: "nowrap" }}>
            태그 필터
          </span>
          <div style={{ display: "flex", gap: 5, flexWrap: "wrap", flex: 1 }}>
            {availableQualityTags.map((tag) => {
              const active = selectedQualityTags.includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  title={tag}
                  onClick={() => toggleQualityTag(tag)}
                  style={{
                    fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 4,
                    cursor: "pointer", whiteSpace: "nowrap",
                    background: active ? "#475569" : "var(--panel2)",
                    color: active ? "#fff" : "var(--muted)",
                    border: active ? "1px solid #94a3b8" : "1px solid rgba(255,255,255,0.08)",
                    transition: "all 0.1s",
                  }}
                >
                  {getQualityTagLabel(tag)}
                </button>
              );
            })}
          </div>
          {selectedQualityTags.length > 0 && (
            <>
              <span style={{ fontSize: 10, fontWeight: 700, color: "#f59e0b", whiteSpace: "nowrap" }}>
                {filteredImages.length} / {images.length} shown
              </span>
              <button
                type="button"
                onClick={() => setSelectedQualityTags([])}
                style={{
                  fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 4,
                  cursor: "pointer", whiteSpace: "nowrap",
                  background: "var(--panel2)", color: "var(--muted)",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                전체 보기
              </button>
            </>
          )}
        </div>
      )}

      {/* ── 문서 유형/태그 안내 범례 ── */}
      <details style={{ background: "var(--panel)", borderRadius: 8, padding: "6px 14px", flexShrink: 0 }}>
        <summary style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)", cursor: "pointer", letterSpacing: 0.4, userSelect: "none" }}>
          문서 유형 / 품질 태그 안내 ▶
        </summary>
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap", marginTop: 8, fontSize: 10, color: "var(--muted)" }}>
          <div>
            <div style={{ fontWeight: 800, marginBottom: 4, color: "var(--text)" }}>문서 유형</div>
            {Object.entries(DOC_TYPE_LABEL).map(([k, v]) => (
              <div key={k} style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 2 }}>
                <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: 2, background: DOC_TYPE_COLOR[k] ?? "#6b7280", flexShrink: 0 }} />
                <span style={{ fontWeight: 700, color: "var(--text)", minWidth: 28 }}>{DOC_TYPE_ABBR[k]}</span>
                <span>{v}</span>
              </div>
            ))}
          </div>
          <div>
            <div style={{ fontWeight: 800, marginBottom: 4, color: "var(--text)" }}>품질 태그</div>
            {Object.entries(QUALITY_TAG_LABELS).slice(0, 7).map(([k, v]) => (
              <div key={k} style={{ marginBottom: 2 }}>
                <span style={{ fontWeight: 700, color: "var(--text)" }}>{v}</span>
                <span style={{ marginLeft: 4, opacity: 0.65 }}>({k})</span>
              </div>
            ))}
          </div>
          <div>
            <div style={{ fontWeight: 800, marginBottom: 4, color: "var(--text)", opacity: 0 }}>-</div>
            {Object.entries(QUALITY_TAG_LABELS).slice(7).map(([k, v]) => (
              <div key={k} style={{ marginBottom: 2 }}>
                <span style={{ fontWeight: 700, color: "var(--text)" }}>{v}</span>
                <span style={{ marginLeft: 4, opacity: 0.65 }}>({k})</span>
              </div>
            ))}
          </div>
        </div>
      </details>

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

          {/* ── 금융전표 현황 (finance_profile) ── */}
          {financeKpi.total > 0 && (
          <KpiSection title="금융전표 현황" tone="red" icon="🏦"
            subtitle={`finance_profile · ${financeKpi.processed}/${financeKpi.total} 처리`}
          >
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
          </KpiSection>
          )}
        </div>
      )}

      {/* ── documentType 집계 ── */}
      {docTypeSummary && (
        <DocTypeSummarySection rows={docTypeSummary} totalImages={images.length} />
      )}
      {qualityTagSummary && (
        <QualityTagSummarySection rows={qualityTagSummary} />
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

            {/* ── 금융전표 계열 섹션 (finance_profile) ── */}
            {financeBatchRows.length > 0 && (
            <div style={{ overflowX: "auto" }}>
              <div style={{ fontSize: 10, color: "#dc2626", fontWeight: 700, marginBottom: 4, letterSpacing: 0.4 }}>
                금융전표 계열 ({financeBatchRows.length}건) — finance_profile
              </div>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr>
                    <th style={th}>파일명</th>
                    {FINANCE_COLUMNS.map((c) => (
                      <th key={c.key} style={{ ...th, color: c.required ? undefined : "var(--muted)" }}>
                        {FINANCE_COL_LABELS[c.key] ?? c.key}
                        {!c.required && (
                          <span style={{ fontSize: 8, marginLeft: 3, opacity: 0.6, fontWeight: 500 }}>선택</span>
                        )}
                      </th>
                    ))}
                    <th style={{ ...th, textAlign: "center" }}>상태</th>
                  </tr>
                </thead>
                <tbody>
                  {financeBatchRows.map((row) => {
                    const ocrEntry = ocr[row.img];
                    const statusMeta = getFinanceStatusMeta(ocrEntry?.status ?? "");
                    const finFields = ocrEntry?.financeFields ?? {};
                    const reviewReasons = ocrEntry?.financeReviewReasons ?? [];
                    return (
                      <tr key={row.img} onClick={() => setSelected(row.img)}
                        style={{ cursor: "pointer", background: selected === row.img ? "var(--accentBg)" : undefined }}>
                        <td style={td}>{row.img}</td>
                        {FINANCE_COLUMNS.map((c) => {
                          const val = finFields[c.key] ?? "";
                          const hasVal = val !== "";
                          return (
                            <td key={c.key} style={{
                              ...td, textAlign: "center",
                              color: hasVal
                                ? (c.required ? "var(--text)" : "var(--muted)")
                                : "rgba(255,255,255,0.22)",
                            }}>
                              {hasVal ? val : "—"}
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
                ※ finance_profile Tier-1 (은행명/거래유형/거래일시/거래금액). Tier-2 및 정밀 추출은 별도 단계.
              </div>
            </div>
            )}

          </div>
          )}
        </div>
      )}

      {/* ── Main: image + compare ── */}
      <div style={{ display: "flex", flex: 1, gap: 12, overflow: "hidden", minHeight: 0 }}>
        {/* Left: image */}
        <div style={{ ...styles.imagePane, position: "relative" }}>
          {selOcr?.displayUrl
            ? <img key={selOcr.displayUrl} src={selOcr.displayUrl} alt="OCR" style={styles.previewImage} />
            : selected
              ? <img key={selected} src={imageUrl(activeTestset.path, selected)} alt="original" style={styles.previewImage} />
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

function KpiChip({ label, value, sub, tone = "neutral" }: { label: string; value: string; sub?: string; tone?: KpiTone }) {
  const toneColors: Record<KpiTone, string> = {
    green: "#22c55e", amber: "#f59e0b", red: "#ef4444",
    indigo: "#6366f1", sky: "#0ea5e9",
    neutral: "rgba(255,255,255,0.55)",
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", padding: "6px 10px", borderRadius: 8, background: "var(--panel2)", minWidth: 60 }}>
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
  { key: "transactionType",     label: "거래유형",      required: true  },
  { key: "transactionDateTime", label: "거래일시",      required: true  },
  { key: "amount",              label: "거래금액",      required: true  },
  { key: "balanceAfter",        label: "거래후잔액",    required: false },
  { key: "accountMasked",       label: "계좌(마스킹)",  required: false },
  { key: "branchOrChannel",     label: "지점/채널",     required: false },
  { key: "memo",                label: "적요",          required: false },
];

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

function FinanceDetailPanel({
  financeFields,
  reviewReasons,
  hasOcr,
}: {
  financeFields: Record<string, string> | null;
  reviewReasons: string[];
  hasOcr: boolean;
}) {
  const hasData = financeFields !== null;

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
        {!hasOcr && (
          <span style={{ fontSize: 10, color: "var(--muted)" }}>OCR 미실행 — 실행 후 Tier-1 값 표시</span>
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

      {/* Tier-1 / Tier-2 필드 카드 */}
      {FINANCE_FIELD_META.map(({ key, label, required }) => {
        const val = financeFields?.[key] ?? "";
        const hasValue = val !== "";
        const isTier1 = required;
        return (
          <div key={key} style={{
            background: "var(--panel)", borderRadius: 10,
            border: `1px solid ${hasValue ? (isTier1 ? "rgba(220,38,38,0.3)" : "rgba(255,255,255,0.08)") : "rgba(255,255,255,0.06)"}`,
            overflow: "hidden",
            opacity: hasOcr ? 1 : 0.5,
          }}>
            {/* 헤더 */}
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "7px 12px", background: "var(--panel2)",
              borderBottom: "1px solid rgba(255,255,255,0.05)",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 800, color: "var(--text)" }}>{label}</span>
                {isTier1 && (
                  <span style={{ fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 4, color: "#fff", background: "#dc2626" }}>
                    Tier-1
                  </span>
                )}
              </div>
              {hasOcr && (
                <span style={{
                  display: "inline-flex", alignItems: "center", justifyContent: "center",
                  width: 22, height: 22, borderRadius: 999,
                  fontSize: 12, fontWeight: 800, color: "#fff",
                  background: hasValue ? "#22c55e" : "rgba(255,255,255,0.18)",
                }}>
                  {hasValue ? "O" : "—"}
                </span>
              )}
            </div>
            {/* 값 영역 */}
            <div style={{ padding: "8px 12px" }}>
              {hasValue ? (
                <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text)", wordBreak: "break-all" }}>
                  {val}
                </span>
              ) : (
                <span style={{ fontSize: 12, color: "rgba(255,255,255,0.25)", fontStyle: "italic" }}>
                  {hasOcr ? (isTier1 ? "미추출 (review)" : "—") : "OCR 미실행"}
                </span>
              )}
            </div>
          </div>
        );
      })}
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
  branchOrChannel:     "지점/채널",
  memo:                "적요",
};

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
        documentType 집계 ({totalImages}장) ▶
      </summary>
      <div style={{ marginTop: 8, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
          <thead>
            <tr>
              <th style={thSm}>documentType</th>
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
                <tr key={row.documentType}>
                  <td style={tdSm}>
                    <span title={row.documentType} style={{ ...chip, background: DOC_TYPE_COLOR[row.documentType] ?? "#6b7280", fontSize: 9 }}>
                      {DOC_TYPE_LABEL[row.documentType] ?? row.documentType}
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
  imagePane: {
    flex: "0 0 40%", background: "var(--panel)", borderRadius: 10,
    boxShadow: "var(--shadowSoft)", overflow: "hidden",
    display: "flex", alignItems: "center", justifyContent: "center", padding: 12,
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
