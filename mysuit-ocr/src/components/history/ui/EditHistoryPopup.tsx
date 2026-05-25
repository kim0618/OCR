"use client";

import React, { useEffect, useMemo, useState } from "react";

export type HistoryPopupRow = {
  job_id: string;
  file_name: string;
  template_name: string | null;
  processing_time: number;
  created_at: string;
};

type Props = {
  open: boolean;
  item: HistoryPopupRow | null;
  templateOptions: string[];
  onClose: () => void;
  onUpdate: (form: HistoryPopupRow) => Promise<void> | void;
};

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  zIndex: 10000,
  background: "rgba(15, 23, 42, 0.45)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 20,
};

const panelStyle: React.CSSProperties = {
  width: "min(560px, 100%)",
  background: "var(--panel)",
  border: "1px solid var(--border)",
  borderRadius: 16,
  boxShadow: "var(--shadow)",
  overflow: "hidden",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  border: "1px solid var(--border)",
  borderRadius: 10,
  padding: "10px 12px",
  fontSize: 13,
  background: "var(--panel2)",
  color: "var(--text)",
};

const buttonStyle: React.CSSProperties = {
  border: "1px solid var(--border)",
  background: "var(--panel2)",
  color: "var(--text)",
  borderRadius: 10,
  padding: "9px 14px",
  fontSize: 13,
  fontWeight: 800,
  cursor: "pointer",
};

const primaryButtonStyle: React.CSSProperties = {
  border: "none",
  background: "var(--accent)",
  color: "#ffffff",
  borderRadius: 10,
  padding: "9px 18px",
  fontSize: 13,
  fontWeight: 800,
  cursor: "pointer",
  boxShadow: "0 4px 14px rgba(8,145,178,0.25)",
  fontFamily: "inherit",
};

function createEmptyValue(): HistoryPopupRow {
  return {
    job_id: "",
    file_name: "",
    template_name: null,
    processing_time: 0,
    created_at: "",
  };
}

export default function EditHistoryPopup({
  open,
  item,
  templateOptions,
  onClose,
  onUpdate,
}: Props) {
  const [form, setForm] = useState<HistoryPopupRow>(createEmptyValue);

  useEffect(() => {
    if (!open) return;
    setForm(item ?? createEmptyValue());
  }, [open, item]);

  useEffect(() => {
    if (!open) return;

    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  const isValid = useMemo(() => {
    return form.file_name.trim() !== "";
  }, [form]);

  if (!open) return null;

  return (
    <div style={overlayStyle} onMouseDown={onClose}>
      <div style={panelStyle} onMouseDown={(e) => e.stopPropagation()}>
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--border)",
            borderLeft: "4px solid var(--accent)",
            background: "var(--panel)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div style={{ fontSize: 16, fontWeight: 900, color: "var(--accent)" }}>히스토리 수정</div>
            <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 3 }}>
              파일명과 템플릿 정보를 수정합니다.
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)", fontSize: 18, lineHeight: 1, padding: 4 }}
          >
            ✕
          </button>
        </div>

        <div
          style={{
            padding: 16,
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 14,
          }}
        >
          <label
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              gridColumn: "1 / -1",
            }}
          >
            <span style={{ fontSize: 12, fontWeight: 800, color: "var(--accent)" }}>파일명</span>
            <input
              value={form.file_name}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, file_name: e.target.value }))
              }
              style={inputStyle}
              placeholder="예: invoice_001.png"
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 800, color: "var(--accent)" }}>템플릿 명</span>
            <input
              list="history-template-options-edit"
              value={form.template_name ?? ""}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  template_name: e.target.value.trim() || null,
                }))
              }
              style={inputStyle}
              placeholder="템플릿 입력 또는 선택"
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 800, color: "var(--accent)" }}>실행시간(초)</span>
            <input
              type="number"
              min={0}
              step="0.1"
              value={String(form.processing_time)}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  processing_time: Number(e.target.value || 0),
                }))
              }
              style={inputStyle}
            />
          </label>

          <datalist id="history-template-options-edit">
            {templateOptions.map((item) => (
              <option key={item} value={item} />
            ))}
          </datalist>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: 8,
            padding: 16,
            borderTop: "1px solid var(--border)",
            background: "var(--panel2)",
          }}
        >
          <button
            type="button"
            style={{ ...primaryButtonStyle, opacity: isValid ? 1 : 0.5 }}
            disabled={!isValid}
            onClick={async () => {
              await onUpdate({
                ...form,
                file_name: form.file_name.trim(),
                template_name: form.template_name?.trim() || null,
              });
            }}
          >
            저장
          </button>
          <button type="button" style={buttonStyle} onClick={onClose}>
            취소
          </button>          
        </div>
      </div>
    </div>
  );
}
