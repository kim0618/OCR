// UI-IMG-IDB-1: IndexedDB-based image storage.
// localStorage 5MB 제약을 피하기 위해 History 상세보기용 이미지(base64 data URL)는
// IndexedDB에 저장한다. 키는 `${historyId}:${kind}` (kind: "original" | "processed").

const DB_NAME = "mysuit_ocr_images";
const STORE_NAME = "images";
const DB_VERSION = 1;

type ImageKind = "original" | "processed" | "template";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined") { reject(new Error("no window")); return; }
    const req = window.indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function key(historyId: string, kind: ImageKind): string {
  return `${historyId}:${kind}`;
}

export async function saveImage(historyId: string, kind: ImageKind, dataUrl: string | null | undefined): Promise<void> {
  if (!dataUrl) return;
  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).put(dataUrl, key(historyId, kind));
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch (e) {
    console.warn("[imageStore] saveImage failed", historyId, kind, e);
  }
}

export async function getImage(historyId: string, kind: ImageKind): Promise<string | null> {
  try {
    const db = await openDb();
    const result = await new Promise<string | null>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const req = tx.objectStore(STORE_NAME).get(key(historyId, kind));
      req.onsuccess = () => resolve((req.result as string | undefined) ?? null);
      req.onerror = () => reject(req.error);
    });
    db.close();
    return result;
  } catch (e) {
    console.warn("[imageStore] getImage failed", historyId, kind, e);
    return null;
  }
}

export async function deleteImagesFor(historyId: string): Promise<void> {
  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      store.delete(key(historyId, "original"));
      store.delete(key(historyId, "processed"));
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch (e) {
    console.warn("[imageStore] deleteImagesFor failed", historyId, e);
  }
}

// ── Template image helpers (kind="template", id=templateId) ──────────────────
export async function saveTemplateImage(templateId: string, dataUrl: string | null | undefined): Promise<void> {
  return saveImage(`tpl:${templateId}`, "template", dataUrl);
}

export async function getTemplateImage(templateId: string): Promise<string | null> {
  return getImage(`tpl:${templateId}`, "template");
}

export async function deleteTemplateImage(templateId: string): Promise<void> {
  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).delete(key(`tpl:${templateId}`, "template"));
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch (e) {
    console.warn("[imageStore] deleteTemplateImage failed", templateId, e);
  }
}

export async function clearAllImages(): Promise<void> {
  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      tx.objectStore(STORE_NAME).clear();
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch (e) {
    console.warn("[imageStore] clearAllImages failed", e);
  }
}
