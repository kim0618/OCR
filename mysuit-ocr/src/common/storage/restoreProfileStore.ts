export const RESTORE_PROFILE_STORAGE_KEY = "mysuit_ocr_restore_profiles";

export type RestoreProfileFields = {
  companyName?: string;
  representative?: string;
  tel?: string;
  address?: string;
};

export type RestoreProfile = {
  businessNo: string;
  partyType: string;
  fields: RestoreProfileFields;
  sourceHistoryId: string;
  sourceFileName: string;
  createdAt: string;
  updatedAt: string;
};

// Maps normalizeAutofillFieldKey() output → RestoreProfileFields key
export const AUTOFILL_TO_PROFILE_KEY: Record<string, keyof RestoreProfileFields> = {
  "회사명": "companyName",
  "대표자": "representative",
  "tel": "tel",
  "주소": "address",
};

export const PROFILE_FIELD_LABELS: Record<keyof RestoreProfileFields, string> = {
  companyName: "회사명",
  representative: "대표자",
  tel: "전화번호",
  address: "주소",
};

const MEANINGLESS_VALUES = new Set([
  "-", "–", "—", "null", "none", "undefined", "n/a",
]);

export function isMeaninglessValue(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  const s = String(value).trim().toLowerCase();
  return s === "" || MEANINGLESS_VALUES.has(s);
}

export function readRestoreProfiles(): RestoreProfile[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(RESTORE_PROFILE_STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as RestoreProfile[];
  } catch {
    return [];
  }
}

export function writeRestoreProfiles(profiles: RestoreProfile[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(RESTORE_PROFILE_STORAGE_KEY, JSON.stringify(profiles));
}

export function deleteRestoreProfile(businessNo: string, partyType: string): void {
  const profiles = readRestoreProfiles();
  const filtered = profiles.filter(
    (p) => !(p.businessNo === businessNo && p.partyType === partyType),
  );
  writeRestoreProfiles(filtered);
}

export function findRestoreProfile(
  businessNo: string,
  partyType: string,
): RestoreProfile | undefined {
  return readRestoreProfiles().find(
    (p) => p.businessNo === businessNo && p.partyType === partyType,
  );
}

export function sortRestoreProfilesByUpdatedAt(profiles: RestoreProfile[]): RestoreProfile[] {
  return [...profiles].sort((a, b) => {
    const aTime = a.updatedAt ?? a.createdAt ?? "";
    const bTime = b.updatedAt ?? b.createdAt ?? "";
    return bTime.localeCompare(aTime);
  });
}
