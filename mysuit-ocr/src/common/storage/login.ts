export type StoredLogin = {
  accessToken?: string;
  user_id?: string;
  user_nm?: string;
  adminYn?: string;
  masterYn?: string;
  comp_cd?: string;
  comp_nm?: string;
  envMysuitUrl?: string;
  envMagellanVersion?: string;
};

const STORAGE_KEY = "mysuit_ocr_login";

function normalizeToken(token?: string) {
  if (!token) return "";
  const trimmed = token.trim();
  return trimmed.startsWith("Bearer ") ? trimmed.substring(7).trim() : trimmed;
}

function normalizeLogin(login: StoredLogin | null): StoredLogin | null {
  if (!login) return null;
  return {
    ...login,
    accessToken: normalizeToken(login.accessToken),
  };
}

export function getStoredLogin(): StoredLogin | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return normalizeLogin(JSON.parse(raw) as StoredLogin);
  } catch {
    return null;
  }
}

export function saveLogin(login: StoredLogin) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      ...login,
      accessToken: normalizeToken(login.accessToken),
    }),
  );
}

export function clearLogin() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function hasStoredLogin() {
  const login = getStoredLogin();
  return Boolean(login?.accessToken || login?.user_id);
}
