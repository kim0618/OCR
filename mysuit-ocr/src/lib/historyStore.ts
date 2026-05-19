// TEMP: 히스토리 DB 미구축 상태에서 RunOCR/Upload 실행 결과를
// 브라우저 localStorage 에 기록한다. DB 준비되면 이 모듈만 교체하면 됨.

const STORAGE_KEY = "mysuit_ocr_history";
const MAX_RECORDS = 50; // localStorage 5MB 제약 보호
const FALLBACK_RECORD_LIMITS = [30, 15, 5, 1];

export type RunStatus = "success" | "fail";

export type HistoryOcrField = {
  name: string;
  en?: string;       // 템플릿이 enField 를 정의해 둔 경우 같은 인덱스로 채움
  ko?: string;       // 템플릿이 koField 를 정의해 둔 경우 같은 인덱스로 채움
  field_type?: string;
  value: string;
  confidence: number;
  bbox?: number[];
};

export type HistoryOutputField = {
  no?: number;
  en: string;
  ko: string;
  original: string;
  modified: string;
  confidence: number;
  source?: "ocr" | "biz" | "gt" | "text";
  applied?: string;
  autofillAction?: "filled" | "corrected" | "confirmed" | "none";
  suggestions?: Array<{
    source: "biz";
    value: string;
    label?: string;
    reason?: string;
    confidence?: number;
    sourceType?: "history" | "groundTruth" | "cache" | "restoreProfile";
    createdAt?: string;
    updatedAt?: string;
    templateName?: string | null;
    fileName?: string;
    hitCount?: number;
  }>;
};

export type HistoryAutofillRunSummary = {
  status: "not_run" | "no_business_number" | "no_candidates" | "confirmed" | "corrected" | "applied";
  businessNumber?: string;
  candidateCount: number;
  confirmedCount: number;
  correctedCount: number;
  filledCount: number;
  skippedCount?: number;
  message?: string;
};

// 이미지 저장 모드.
// "legacy": image_url 단일 필드 (H-0/H-1 이전 데이터)
// "url": original_image_url + processed_image_url 분리 (H-2 이후 신규)
export type HistoryImageStorageMode = "legacy" | "url";

export type HistoryRunRecord = {
  job_id: string;
  file_name: string;
  template_name: string | null;
  processing_time: number;
  created_at: string; // "YYYY-MM-DD HH:mm:ss"
  status: RunStatus;
  // 이미지 필드 — DB 전환 시 URL/path만 저장하는 구조를 미리 맞춤
  image_url?: string;               // legacy: 전처리 후 이미지 단일 URL (이전 데이터 호환)
  original_image_url?: string | null;  // 전처리 전 원본 이미지 URL (서버 저장 후 채움)
  processed_image_url?: string | null; // 전처리 후 이미지 URL (H-2 이후 명시적 저장)
  image_storage_mode?: HistoryImageStorageMode; // 저장 모드 구분
  // 상세보기용 (선택)
  ocr_fields?: HistoryOcrField[];
  output_fields?: HistoryOutputField[];
  autofill_summary?: HistoryAutofillRunSummary;
  // HISTORY-DETAIL-1: detail.runSnapshot.documentFields 전달 (거래명세서 tableRows 등)
  document_fields?: HistoryDetailDocumentFields;
};

function pad2(n: number) {
  return String(n).padStart(2, "0");
}

function nowTimestamp() {
  const d = new Date();
  return (
    `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ` +
    `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`
  );
}

function genId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `RUN-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
  }
  return `RUN-${Math.random().toString(36).slice(2, 10).toUpperCase()}`;
}

function isQuotaExceededError(error: unknown) {
  return (
    error instanceof DOMException &&
    (error.name === "QuotaExceededError" || error.name === "NS_ERROR_DOM_QUOTA_REACHED")
  );
}

function withoutStoredImages(records: HistoryRunRecord[]): HistoryRunRecord[] {
  return records.map((record) => ({
    ...record,
    image_url: undefined,
    original_image_url: undefined,
    processed_image_url: undefined,
  }));
}

/**
 * 전처리 전 원본 이미지 URL 반환.
 * original_image_url이 없으면 null (placeholder 표시용).
 */
export function getOriginalHistoryImage(record: HistoryRunRecord): string | null {
  return record.original_image_url ?? null;
}

/**
 * 전처리 후 이미지 URL 반환.
 * processed_image_url 우선, 없으면 image_url (legacy) fallback.
 */
export function getProcessedHistoryImage(record: HistoryRunRecord): string | null {
  return record.processed_image_url ?? record.image_url ?? null;
}

function tryWriteHistory(records: HistoryRunRecord[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
}

export function readHistoryRuns(): HistoryRunRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    return arr.filter((r) => r && typeof r === "object") as HistoryRunRecord[];
  } catch {
    return [];
  }
}

export function appendHistoryRun(
  partial: Omit<HistoryRunRecord, "job_id" | "created_at"> & {
    job_id?: string;
    created_at?: string;
  },
): HistoryRunRecord {
  const record: HistoryRunRecord = {
    job_id: partial.job_id ?? genId(),
    file_name: partial.file_name,
    template_name: partial.template_name ?? null,
    processing_time: Number(partial.processing_time) || 0,
    created_at: partial.created_at ?? nowTimestamp(),
    status: partial.status,
    image_url: partial.image_url,
    original_image_url: partial.original_image_url ?? null,
    processed_image_url: partial.processed_image_url ?? null,
    image_storage_mode: partial.image_storage_mode ?? "url",
    ocr_fields: partial.ocr_fields,
    output_fields: partial.output_fields,
    autofill_summary: partial.autofill_summary,
  };
  if (typeof window !== "undefined") {
    try {
      const prev = readHistoryRuns();
      const next = [record, ...prev].slice(0, MAX_RECORDS);
      tryWriteHistory(next);
    } catch (e) {
      if (!isQuotaExceededError(e)) {
        console.warn("[historyStore] append failed", e instanceof Error ? e.message : e);
        return record;
      }
      const prev = readHistoryRuns();
      const compactRecord = { ...record, image_url: undefined };
      const compactNext = withoutStoredImages([compactRecord, ...prev]);
      for (const limit of FALLBACK_RECORD_LIMITS) {
        try {
          tryWriteHistory(compactNext.slice(0, limit));
          console.warn(`[historyStore] quota exceeded; saved compact history (${limit} records, images omitted)`);
          return record;
        } catch (retryError) {
          if (!isQuotaExceededError(retryError)) {
            console.warn("[historyStore] compact append failed", retryError instanceof Error ? retryError.message : retryError);
            return record;
          }
        }
      }
      try {
        tryWriteHistory([{ ...compactRecord, ocr_fields: undefined }]);
        console.warn("[historyStore] quota exceeded; saved latest compact history only");
      } catch {
        console.warn("[historyStore] quota exceeded; history was not saved");
      }
    }
  }
  return record;
}

export function updateHistoryRun(
  jobId: string,
  patch: Partial<HistoryRunRecord>,
): HistoryRunRecord | null {
  if (typeof window === "undefined") return null;
  const prev = readHistoryRuns();
  const idx = prev.findIndex((r) => r.job_id === jobId);
  if (idx < 0) return null;
  const next = [...prev];
  next[idx] = { ...next[idx], ...patch, job_id: next[idx].job_id };
  try {
    tryWriteHistory(next);
  } catch (e) {
    if (!isQuotaExceededError(e)) {
      console.warn("[historyStore] update failed", e instanceof Error ? e.message : e);
      return null;
    }
    try {
      tryWriteHistory(withoutStoredImages(next).slice(0, MAX_RECORDS));
      console.warn("[historyStore] quota exceeded; updated compact history with images omitted");
    } catch {
      console.warn("[historyStore] quota exceeded; history update was not saved");
      return null;
    }
  }
  return next[idx];
}

export function clearHistoryRuns() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(STORAGE_KEY);
    // HISTORY-STRUCTURE-2D: index/detail도 함께 정리
    try { window.localStorage.removeItem(HISTORY_INDEX_KEY); } catch { /* ignore */ }
    try { window.localStorage.removeItem(HISTORY_DETAILS_KEY); } catch { /* ignore */ }
  }
}

/**
 * HISTORY-STRUCTURE-2D: legacy 삭제 성공 후 index/detail 동기화.
 * 각 단계를 독립 try/catch로 감싸 부분 실패가 다른 단계에 영향 없도록 한다.
 */
function syncHistoryIndexAndDetailOnDelete(historyId: string): void {
  // index에서 해당 historyId 항목 제거
  try {
    const index = readHistoryIndex();
    const filtered = index.filter((item) => item.historyId !== historyId);
    if (filtered.length !== index.length) {
      writeHistoryIndex(filtered);
    }
  } catch (e) {
    console.warn("[history-structure] index delete sync failed", historyId, e instanceof Error ? e.message : e);
  }

  // detail에서 해당 historyId 키 제거
  try {
    const details = readHistoryDetails();
    if (Object.prototype.hasOwnProperty.call(details, historyId)) {
      const rest = Object.fromEntries(
        Object.entries(details).filter(([k]) => k !== historyId),
      ) as Record<string, HistoryDetailRecord>;
      writeHistoryDetails(rest);
    }
  } catch (e) {
    console.warn("[history-structure] detail delete sync failed", historyId, e instanceof Error ? e.message : e);
  }
}

export function deleteHistoryRun(jobId: string): boolean {
  if (typeof window === "undefined") return false;
  const prev = readHistoryRuns();
  const next = prev.filter((r) => r.job_id !== jobId);
  if (next.length === prev.length) return false;
  try {
    tryWriteHistory(next);
  } catch (e) {
    console.warn("[historyStore] delete failed", e instanceof Error ? e.message : e);
    return false;
  }
  // HISTORY-STRUCTURE-2D: legacy 삭제 성공 후 index/detail 동기화 (실패해도 true 반환 유지)
  syncHistoryIndexAndDetailOnDelete(jobId);
  return true;
}

// ────────────────────────────────────────────────────────────────────────────
// HISTORY-STRUCTURE-2A: index / detail 병행 저장
// 기존 mysuit_ocr_history 는 그대로 유지하면서, OCR 실행/저장 시 신규 key에
// 경량 index + 무거운 detail 을 병행 저장한다.
// DB 전환 전 단계적 분리를 위한 준비 코드.
// ────────────────────────────────────────────────────────────────────────────

export const HISTORY_INDEX_KEY = "mysuit_ocr_history_index";
export const HISTORY_DETAILS_KEY = "mysuit_ocr_history_details";

// ── 타입 정의 ────────────────────────────────────────────────────────────────

export type HistoryIndexSummary = {
  fieldCount?: number;
  tableRowCount?: number;
  autofillStatus?: string;
  primaryBusinessNo?: string;
  primaryCompanyName?: string;
};

export type HistoryIndexItem = {
  historyId: string;
  fileName?: string;
  templateName?: string | null;
  documentType?: string;
  createdAt?: string;
  updatedAt?: string;
  status?: string;
  summary?: HistoryIndexSummary;
  hasConfirmedResult?: boolean;
  hasRestoreProfile?: boolean;
  sourceFileName?: string;
};

export type HistoryDetailDocumentFields = {
  tableRows?: unknown[];
  tableMeta?: Record<string, unknown>;
};

export type HistoryDetailRecord = {
  historyId: string;
  runSnapshot?: {
    ocrFields?: unknown[];
    documentFields?: HistoryDetailDocumentFields;
    outputFieldsSnapshot?: unknown[];
    autofillSummary?: unknown;
  };
  confirmedResult?: {
    savedAt?: string;
    outputFields?: unknown[];
  };
  images?: {
    originalImageUrl?: string | null;
    processedImageUrl?: string | null;
    imageUrl?: string;
  };
};

// ── Read / Write ──────────────────────────────────────────────────────────────

export function readHistoryIndex(): HistoryIndexItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(HISTORY_INDEX_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as HistoryIndexItem[]) : [];
  } catch {
    return [];
  }
}

function writeHistoryIndex(items: HistoryIndexItem[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(HISTORY_INDEX_KEY, JSON.stringify(items));
}

export function readHistoryDetails(): Record<string, HistoryDetailRecord> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(HISTORY_DETAILS_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return parsed as Record<string, HistoryDetailRecord>;
  } catch {
    return {};
  }
}

function writeHistoryDetails(details: Record<string, HistoryDetailRecord>): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(HISTORY_DETAILS_KEY, JSON.stringify(details));
}

// ── Upsert ───────────────────────────────────────────────────────────────────

function upsertHistoryIndexItem(item: HistoryIndexItem): void {
  const prev = readHistoryIndex();
  const idx = prev.findIndex((i) => i.historyId === item.historyId);
  if (idx >= 0) {
    prev[idx] = { ...prev[idx], ...item };
    writeHistoryIndex(prev);
  } else {
    writeHistoryIndex([item, ...prev].slice(0, MAX_RECORDS));
  }
}

function upsertHistoryDetail(historyId: string, detail: HistoryDetailRecord): void {
  const prev = readHistoryDetails();
  prev[historyId] = { ...(prev[historyId] ?? {}), ...detail };
  writeHistoryDetails(prev);
}

// ── Summary 추출 (autofillEngine import 순환 방지 — inline 처리) ──────────────

const COMPANY_NAME_KO_KEYS = new Set(["회사명", "상호", "상호명", "가맹점명"]);

function extractPrimaryCompanyName(fields?: HistoryOutputField[]): string | undefined {
  if (!fields) return undefined;
  for (const f of fields) {
    if (COMPANY_NAME_KO_KEYS.has((f.ko ?? "").trim())) {
      const val = (f.modified || f.original || "").trim();
      if (val) return val;
    }
  }
  return undefined;
}

// ── Build helpers ─────────────────────────────────────────────────────────────

export function buildHistoryIndexItem(
  record: HistoryRunRecord,
  extra?: { documentType?: string; tableRowCount?: number },
): HistoryIndexItem {
  const outFields = record.output_fields ?? [];
  return {
    historyId: record.job_id,
    fileName: record.file_name,
    templateName: record.template_name,
    documentType: extra?.documentType || undefined,
    createdAt: record.created_at,
    updatedAt: record.created_at,
    status: record.status,
    summary: {
      fieldCount: outFields.length,
      tableRowCount: extra?.tableRowCount,
      autofillStatus: record.autofill_summary?.status,
      primaryBusinessNo: record.autofill_summary?.businessNumber || undefined,
      primaryCompanyName: extractPrimaryCompanyName(outFields),
    },
    hasConfirmedResult: false,
    hasRestoreProfile: false,
    sourceFileName: record.file_name,
  };
}

export function buildHistoryDetail(
  record: HistoryRunRecord,
  extra?: { documentFields?: HistoryDetailDocumentFields },
): HistoryDetailRecord {
  return {
    historyId: record.job_id,
    runSnapshot: {
      ocrFields: record.ocr_fields,
      documentFields: extra?.documentFields,
      outputFieldsSnapshot: record.output_fields,
      autofillSummary: record.autofill_summary,
    },
    images: {
      originalImageUrl: record.original_image_url,
      processedImageUrl: record.processed_image_url,
      imageUrl: record.image_url,
    },
  };
}

// ── Sync helpers ──────────────────────────────────────────────────────────────

/**
 * OCR 실행 완료 후 기존 appendHistoryRun() 직후 호출.
 * 실패해도 기존 history 저장에는 영향 없음 — 호출처에서 try/catch로 감싼다.
 */
export function syncHistoryIndexAndDetailOnCreate(
  record: HistoryRunRecord,
  extra?: {
    documentType?: string;
    documentFields?: HistoryDetailDocumentFields;
  },
): void {
  const tableRowCount = Array.isArray(extra?.documentFields?.tableRows)
    ? extra!.documentFields!.tableRows!.length
    : undefined;

  upsertHistoryIndexItem(
    buildHistoryIndexItem(record, {
      documentType: extra?.documentType,
      tableRowCount,
    }),
  );
  upsertHistoryDetail(
    record.job_id,
    buildHistoryDetail(record, { documentFields: extra?.documentFields }),
  );
}

/**
 * 품목표 편집 후 [저장] 시 detail.runSnapshot.documentFields.tableRows 갱신.
 * 실패해도 기존 저장에는 영향 없음 — 호출처에서 try/catch로 감싼다.
 */
export function syncHistoryDetailTableRowsOnSave(
  historyId: string,
  tableRows: unknown[],
): void {
  const details = readHistoryDetails();
  const existing = details[historyId];
  if (!existing) return;
  details[historyId] = {
    ...existing,
    runSnapshot: {
      ...(existing.runSnapshot ?? {}),
      documentFields: {
        ...(existing.runSnapshot?.documentFields ?? {}),
        tableRows,
      },
    },
  };
  writeHistoryDetails(details);
}

/**
 * History 상세 [저장] 클릭 후 기존 updateHistoryRun() 직후 호출.
 * 실패해도 기존 저장에는 영향 없음 — 호출처에서 try/catch로 감싼다.
 */
export function syncHistoryIndexAndDetailOnSave(
  historyId: string,
  outputFields: HistoryOutputField[],
): void {
  const now = nowTimestamp();

  // index: updatedAt + hasConfirmedResult 갱신
  const index = readHistoryIndex();
  const idx = index.findIndex((i) => i.historyId === historyId);
  if (idx >= 0) {
    index[idx] = { ...index[idx], updatedAt: now, hasConfirmedResult: true };
    writeHistoryIndex(index);
  }

  // detail: confirmedResult 갱신
  const details = readHistoryDetails();
  const existing = details[historyId] ?? { historyId };
  details[historyId] = {
    ...existing,
    confirmedResult: { savedAt: now, outputFields },
  };
  writeHistoryDetails(details);
}

// ────────────────────────────────────────────────────────────────────────────
// HISTORY-STRUCTURE-2B: index 우선 목록 조회
// mysuit_ocr_history_index 데이터로 목록 필드를 보강하되,
// mysuit_ocr_history를 항상 기준(base)으로 읽어 누락·삭제 안전성을 보장한다.
// ────────────────────────────────────────────────────────────────────────────

function indexItemToRunRecord(item: HistoryIndexItem): HistoryRunRecord {
  return {
    job_id: item.historyId,
    file_name: item.fileName ?? "",
    template_name: item.templateName ?? null,
    processing_time: 0, // index에 미포함 — 목록 UI에서 미사용
    created_at: item.createdAt ?? "",
    status: (item.status as RunStatus) ?? "success",
  };
}

/**
 * History 목록 조회.
 *
 * 전략: mysuit_ocr_history 를 항상 base로 읽고,
 * mysuit_ocr_history_index 가 있으면 해당 항목의 목록 필드(templateName, status 등)를 index 값으로 보강한다.
 *
 * 이유:
 * - 삭제 동기화(2D 이전): deleteHistoryRun()이 legacy만 삭제하므로 legacy를 기준으로 해야 삭제 즉시 반영됨
 * - 구 데이터 누락 방지: 2A 이전 entry는 index에 없으나 legacy에는 있으므로 legacy 기준이어야 표시됨
 * - index parse 실패 시 graceful fallback: try/catch로 legacy만 반환
 *
 * index 없음 / 빈 배열 / parse 실패 → readHistoryRuns() 그대로 반환 (완전 fallback)
 */
export function readHistoryListWithFallback(): HistoryRunRecord[] {
  const legacy = readHistoryRuns(); // 항상 읽어 기준점으로 사용
  try {
    const index = readHistoryIndex();
    if (index.length === 0) return legacy;

    // historyId → HistoryIndexItem 맵
    const indexMap = new Map<string, HistoryIndexItem>(
      index.map((item) => [item.historyId, item]),
    );

    // legacy 항목을 기준으로 순회하며 index 데이터로 보강
    const legacySet = new Set(legacy.map((r) => r.job_id));
    const merged: HistoryRunRecord[] = legacy.map((run) => {
      const idx = indexMap.get(run.job_id);
      if (!idx) return run; // 구 데이터 — index 없음, 그대로 유지
      return {
        ...run,
        // index에 값이 있는 필드만 덮어씀 (undefined면 legacy 유지)
        file_name: idx.fileName ?? run.file_name,
        template_name: idx.templateName ?? run.template_name,
        status: (idx.status as RunStatus) ?? run.status,
        created_at: idx.createdAt ?? run.created_at,
      };
    });

    // index에만 있고 legacy에 없는 항목 (정상 흐름에선 발생 안 함, 방어용)
    const indexOnlyRuns: HistoryRunRecord[] = index
      .filter((item) => !legacySet.has(item.historyId))
      .map(indexItemToRunRecord);

    // created_at 기준 최신순 정렬 (legacy 기존 순서와 일치)
    return [...merged, ...indexOnlyRuns].sort((a, b) =>
      b.created_at.localeCompare(a.created_at),
    );
  } catch {
    return legacy; // parse 실패 등 예외 → legacy 완전 fallback
  }
}

// ────────────────────────────────────────────────────────────────────────────
// HISTORY-STRUCTURE-2C: detail 우선 상세 조회
// mysuit_ocr_history_details 에서 상세 record를 먼저 찾고,
// 없거나 이상하면 mysuit_ocr_history 기반 상세로 fallback한다.
// ────────────────────────────────────────────────────────────────────────────

/**
 * HistoryDetailRecord → HistoryRunRecord 변환.
 *
 * output_fields 우선순위:
 *   1) detail.confirmedResult.outputFields  — [저장]한 최신 채택값
 *   2) detail.runSnapshot.outputFieldsSnapshot — OCR 실행 시점 원본
 *   3) [] — 없으면 빈 배열
 *
 * meta: index 또는 legacy에서 가져온 경량 메타데이터 보강용
 */
export function detailToHistoryRunRecord(
  detail: HistoryDetailRecord,
  meta?: {
    file_name?: string;
    template_name?: string | null;
    processing_time?: number;
    created_at?: string;
    status?: string;
    image_storage_mode?: HistoryImageStorageMode;
  },
): HistoryRunRecord {
  const outputFields: HistoryOutputField[] =
    (detail.confirmedResult?.outputFields as HistoryOutputField[] | undefined) ??
    (detail.runSnapshot?.outputFieldsSnapshot as HistoryOutputField[] | undefined) ??
    [];

  return {
    job_id: detail.historyId,
    file_name: meta?.file_name ?? "",
    template_name: meta?.template_name ?? null,
    processing_time: meta?.processing_time ?? 0,
    created_at: meta?.created_at ?? "",
    status: (meta?.status as RunStatus | undefined) ?? "success",
    original_image_url: detail.images?.originalImageUrl ?? null,
    processed_image_url: detail.images?.processedImageUrl ?? null,
    image_url: detail.images?.imageUrl,
    image_storage_mode: meta?.image_storage_mode ?? "url",
    ocr_fields: detail.runSnapshot?.ocrFields as HistoryOcrField[] | undefined,
    output_fields: outputFields,
    autofill_summary: detail.runSnapshot?.autofillSummary as HistoryAutofillRunSummary | undefined,
    document_fields: detail.runSnapshot?.documentFields,
  };
}

/**
 * 상세 조회: mysuit_ocr_history_details 우선, 없거나 오류면 mysuit_ocr_history fallback.
 *
 * detail 있음:
 *   - detail + index 경량 메타로 HistoryRunRecord 생성 (heavy legacy 미로드)
 * detail 없음 / parse 오류:
 *   - readHistoryRuns()에서 job_id 일치 항목 반환 (기존 동작 완전 유지)
 */
export function readHistoryDetailWithFallback(historyId: string): HistoryRunRecord | null {
  try {
    const details = readHistoryDetails();
    const detail = details[historyId];
    if (detail?.historyId) {
      // index에서 경량 메타 보강 (full legacy 로드 없이 처리)
      const indexItem = readHistoryIndex().find((i) => i.historyId === historyId);
      const meta = indexItem
        ? {
            file_name: indexItem.fileName,
            template_name: indexItem.templateName,
            created_at: indexItem.createdAt,
            status: indexItem.status,
          }
        : undefined;
      return detailToHistoryRunRecord(detail, meta);
    }
  } catch {
    // parse 실패 등 예외 → legacy fallback
  }
  // Legacy fallback: full history에서 job_id 검색
  return readHistoryRuns().find((r) => r.job_id === historyId) ?? null;
}
