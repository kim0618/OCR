// TEMP: DB 미구축 상태에서 사용자가 History 상세보기에서 입력한 "수정 데이터" 를
// 정답(기준값) 으로 보존하는 localStorage 저장소.
// 키 = (template_name, file_name) 페어. DB 준비되면 이 모듈만 교체하면 됨.

import type { HistoryOutputField } from "./historyStore";

const STORAGE_KEY = "mysuit_ocr_groundtruth";

export type GroundTruthMap = Record<string, string>;       // { [fieldKey]: 정답값 }
type GroundTruthStore = Record<string, GroundTruthMap>;    // { [compositeKey]: map }

export function compositeKey(template: string | null | undefined, file: string): string {
  return `${template ?? ""}::${file ?? ""}`;
}

// 필드 식별 키. en 우선, 없으면 ko. 비교용으로 trim + lowercase.
export function fieldKey(en?: string, ko?: string): string {
  const e = (en ?? "").trim();
  const k = (ko ?? "").trim();
  return (e || k).toLowerCase();
}

function readStore(): GroundTruthStore {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeStore(store: GroundTruthStore) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch (e) {
    console.error("[groundTruthStore] write failed", e);
  }
}

export function getGroundTruth(
  template: string | null | undefined,
  file: string,
): GroundTruthMap {
  const store = readStore();
  return store[compositeKey(template, file)] ?? {};
}

// fields 의 modified 값 중 비어있지 않은 것만 정답으로 저장.
// 빈 값으로 기존 정답을 덮지 않는다 (보존 우선).
export function saveGroundTruth(
  template: string | null | undefined,
  file: string,
  fields: HistoryOutputField[],
): GroundTruthMap {
  const store = readStore();
  const key = compositeKey(template, file);
  const existing = store[key] ?? {};
  const next: GroundTruthMap = { ...existing };

  for (const f of fields) {
    const fk = fieldKey(f.en, f.ko);
    if (!fk) continue;
    const v = (f.modified ?? "").trim();
    if (!v) continue;
    next[fk] = v;
  }

  store[key] = next;
  writeStore(store);
  return next;
}

export function clearGroundTruth(
  template: string | null | undefined,
  file: string,
): void {
  const store = readStore();
  delete store[compositeKey(template, file)];
  writeStore(store);
}

// 단일 행과 정답을 비교. 빈 정답이면 "none".
export type MatchStatus = "none" | "match" | "mismatch";

export function compareToGt(
  rowValue: string,
  gt: string | undefined,
): { status: MatchStatus; gt?: string } {
  if (!gt || !gt.trim()) return { status: "none" };
  const a = (rowValue ?? "").trim();
  const b = gt.trim();
  return a === b ? { status: "match", gt: b } : { status: "mismatch", gt: b };
}
