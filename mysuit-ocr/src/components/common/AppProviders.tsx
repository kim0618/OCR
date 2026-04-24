"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

type AlertOptions = {
  title?: string;
  message: string;
  okText?: string;
};

type ConfirmOptions = {
  title?: string;
  message: string;
  okText?: string;
  cancelText?: string;
};

type AlertState =
  | { open: false }
  | {
      open: true;
      title?: string;
      message: string;
      kind: "alert";
      okText?: string;
      resolve: () => void;
    }
  | {
      open: true;
      title?: string;
      message: string;
      kind: "confirm";
      okText?: string;
      cancelText?: string;
      resolve: (v: boolean) => void;
    };

type UiApi = {
  /** 전역 로딩 on/off */
  setLoading: (on: boolean) => void;
  /** 비동기 작업을 로딩으로 감싸기 */
  withLoading: <T>(fn: () => Promise<T>) => Promise<T>;

  /**
   * 단순 알림(확인 1개)
   * - 하위호환: alert("메시지", { title })
   * - 권장: alert({ title, message, okText })
   */
  alert: (
    arg: string | AlertOptions,
    opts?: { title?: string },
  ) => Promise<void>;

  /**
   * 확인/취소(boolean 반환)
   * - 하위호환: confirm("메시지", { title })
   * - 권장: confirm({ title, message, okText, cancelText })
   */
  confirm: (
    arg: string | ConfirmOptions,
    opts?: { title?: string },
  ) => Promise<boolean>;
};

const UiContext = createContext<UiApi | null>(null);

export function useUi(): UiApi {
  const ctx = useContext(UiContext);
  if (!ctx) throw new Error("useUi must be used within <AppProviders />");
  return ctx;
}

function Modal({
  state,
  close,
}: {
  state: Exclude<AlertState, { open: false }>;
  close: () => void;
}) {
  const title = state.title ?? (state.kind === "confirm" ? "확인" : "알림");
  const okText = state.okText ?? "확인";
  const cancelText =
    state.kind === "confirm" ? (state.cancelText ?? "취소") : undefined;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(0,0,0,0.5)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        animation: "modal-fade-in 0.15s ease",
      }}
      onMouseDown={(e) => { e.preventDefault(); }}
    >
      <div
        style={{
          width: "min(440px, 100%)",
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          boxShadow: "0 24px 64px rgba(0,0,0,0.25), 0 0 0 1px var(--border)",
          overflow: "hidden",
          animation: "modal-slide-up 0.18s ease",
        }}
      >
        {/* 헤더 */}
        <div
          id="modal-title"
          style={{
            padding: "16px 20px 14px",
            fontSize: 15,
            fontWeight: 800,
            color: "var(--text)",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          {state.kind === "confirm" ? (
            <span style={{ color: "#f59e0b", fontSize: 18, lineHeight: 1 }}>⚠</span>
          ) : (
            <span style={{ color: "var(--accent)", fontSize: 18, lineHeight: 1 }}>ℹ</span>
          )}
          {title}
        </div>

        {/* 본문 */}
        <div
          style={{
            padding: "18px 20px",
            fontSize: 14,
            lineHeight: 1.65,
            color: "var(--text)",
            whiteSpace: "pre-wrap",
          }}
        >
          {state.message}
        </div>

        {/* 푸터 */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: 8,
            padding: "12px 20px 16px",
          }}
        >
          {state.kind === "confirm" ? (
            <>
              <button
                type="button"
                style={{
                  border: "none",
                  background: "var(--accent)",
                  color: "#ffffff",
                  borderRadius: 10,
                  padding: "9px 20px",
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  transition: "opacity 0.15s",
                }}
                onMouseOver={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "0.85"; }}
                onMouseOut={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
                onClick={() => { state.resolve(true); close(); }}
              >
                {okText}
              </button>
              <button
                type="button"
                style={{
                  border: "1px solid var(--border)",
                  background: "var(--panel2)",
                  color: "var(--muted)",
                  borderRadius: 10,
                  padding: "9px 20px",
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  transition: "background 0.15s",
                }}
                onClick={() => { state.resolve(false); close(); }}
              >
                {cancelText}
              </button>
            </>
          ) : (
            <button
              type="button"
              style={{
                border: "none",
                background: "var(--accent)",
                color: "#ffffff",
                borderRadius: 10,
                padding: "9px 24px",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                fontFamily: "inherit",
                transition: "opacity 0.15s",
              }}
              onMouseOver={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "0.85"; }}
              onMouseOut={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
              onClick={() => { state.resolve(); close(); }}
            >
              {okText}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function LoadingOverlay() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="처리 중"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9998,
        background: "rgba(0,0,0,0.35)",
        backdropFilter: "blur(3px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        pointerEvents: "auto",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "14px 22px",
          borderRadius: 14,
          border: "1px solid var(--border)",
          background: "var(--panel)",
          boxShadow: "0 16px 48px rgba(0,0,0,0.2)",
          fontSize: 14,
          fontWeight: 700,
          color: "var(--text)",
        }}
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style={{ animation: "spin 0.8s linear infinite", flexShrink: 0 }}>
          <circle cx="10" cy="10" r="8" stroke="var(--border)" strokeWidth="2.5"/>
          <path d="M10 2a8 8 0 0 1 8 8" stroke="var(--accent)" strokeWidth="2.5" strokeLinecap="round"/>
        </svg>
        처리 중...
      </div>
    </div>
  );
}

export default function AppProviders({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [modal, setModal] = useState<AlertState>({ open: false });

  const setLoading = useCallback((on: boolean) => setIsLoading(on), []);

  const withLoading = useCallback(async <T,>(fn: () => Promise<T>) => {
    setIsLoading(true);
    try {
      return await fn();
    } finally {
      setIsLoading(false);
    }
  }, []);

  const alert = useCallback(
    (arg: string | AlertOptions, opts?: { title?: string }) => {
      const normalized: AlertOptions =
        typeof arg === "string" ? { message: arg, title: opts?.title } : arg;

      return new Promise<void>((resolve) => {
        setModal({
          open: true,
          kind: "alert",
          message: normalized.message,
          title: normalized.title,
          okText: normalized.okText,
          resolve,
        });
      });
    },
    [],
  );

  const confirm = useCallback(
    (arg: string | ConfirmOptions, opts?: { title?: string }) => {
      const normalized: ConfirmOptions =
        typeof arg === "string" ? { message: arg, title: opts?.title } : arg;

      return new Promise<boolean>((resolve) => {
        setModal({
          open: true,
          kind: "confirm",
          message: normalized.message,
          title: normalized.title,
          okText: normalized.okText,
          cancelText: normalized.cancelText,
          resolve,
        });
      });
    },
    [],
  );

  const api = useMemo<UiApi>(
    () => ({ setLoading, withLoading, alert, confirm }),
    [setLoading, withLoading, alert, confirm],
  );

  return (
    <UiContext.Provider value={api}>
      {children}
      {isLoading && <LoadingOverlay />}
      {modal.open && (
        <Modal
          state={modal}
          close={() => {
            setModal({ open: false });
          }}
        />
      )}
    </UiContext.Provider>
  );
}
