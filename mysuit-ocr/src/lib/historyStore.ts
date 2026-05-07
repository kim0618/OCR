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
    sourceType?: "history" | "groundTruth" | "cache";
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

export type HistoryRunRecord = {
  job_id: string;
  file_name: string;
  template_name: string | null;
  processing_time: number;
  created_at: string; // "YYYY-MM-DD HH:mm:ss"
  status: RunStatus;
  // 상세보기용 (선택)
  image_url?: string;
  ocr_fields?: HistoryOcrField[];
  output_fields?: HistoryOutputField[];
  autofill_summary?: HistoryAutofillRunSummary;
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
  return records.map((record) => ({ ...record, image_url: undefined }));
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
  }
}

export function deleteHistoryRun(jobId: string): boolean {
  if (typeof window === "undefined") return false;
  const prev = readHistoryRuns();
  const next = prev.filter((r) => r.job_id !== jobId);
  if (next.length === prev.length) return false;
  try {
    tryWriteHistory(next);
    return true;
  } catch (e) {
    console.warn("[historyStore] delete failed", e instanceof Error ? e.message : e);
    return false;
  }
}
