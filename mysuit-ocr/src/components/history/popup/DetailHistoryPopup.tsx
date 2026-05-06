"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  type HistoryRunRecord,
  type HistoryOutputField,
  updateHistoryRun,
} from "@/lib/historyStore";
import { useUi } from "../../common/AppProviders";

type Props = {
  open: boolean;
  item: HistoryRunRecord | null;
  onClose: () => void;
  onSaved?: (record: HistoryRunRecord) => void;
};

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  zIndex: 10000,
  background: "rgba(15, 23, 42, 0.55)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 20,
};

const panelStyle: React.CSSProperties = {
  width: "min(1140px, 100%)",
  height: "min(720px, 100%)",
  background: "var(--panel)",
  border: "1px solid var(--border)",
  borderRadius: 14,
  boxShadow: "var(--shadow)",
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
};

const headerStyle: React.CSSProperties = {
  padding: "12px 16px",
  borderBottom: "1px solid var(--border)",
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  background: "var(--panel2)",
};

const bodyStyle: React.CSSProperties = {
  flex: 1,
  minHeight: 0,
  display: "flex",
  gap: 14,
  padding: 14,
};

const leftPaneStyle: React.CSSProperties = {
  flex: "0 0 44%",
  border: "1px solid var(--border)",
  borderRadius: 10,
  background: "var(--panel2)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  overflow: "hidden",
  minWidth: 0,
};

const rightPaneStyle: React.CSSProperties = {
  flex: 1,
  display: "flex",
  flexDirection: "column",
  gap: 12,
  minWidth: 0,
};

const sectionStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
  flex: 1,
  minHeight: 0,
};

const sectionHeaderStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  paddingBottom: 4,
  borderBottom: "1px solid var(--border)",
};

const sectionLabelStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 800,
  color: "var(--accent)",
  letterSpacing: 0.2,
};

const tableWrapStyle: React.CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: 10,
  overflow: "auto",
  flex: 1,
  minHeight: 0,
  background: "var(--panel)",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 12,
};

const thStyle: React.CSSProperties = {
  background: "var(--panel2)",
  color: "var(--muted)",
  fontWeight: 700,
  textAlign: "left",
  padding: "8px 10px",
  borderBottom: "1px solid var(--border)",
  whiteSpace: "nowrap",
  position: "sticky",
  top: 0,
  zIndex: 1,
};

const tdStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderBottom: "1px solid var(--border)",
  color: "var(--text)",
  verticalAlign: "middle",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  border: "1px solid var(--border)",
  borderRadius: 6,
  padding: "5px 8px",
  fontSize: 12,
  background: "var(--panel2)",
  color: "var(--text)",
};

const closeButtonStyle: React.CSSProperties = {
  border: "1px solid var(--border)",
  background: "var(--panel)",
  color: "var(--text)",
  borderRadius: 8,
  padding: "5px 10px",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
  lineHeight: 1,
};

const saveButtonStyle: React.CSSProperties = {
  border: "none",
  background: "var(--accent)",
  color: "#ffffff",
  borderRadius: 8,
  padding: "6px 14px",
  fontSize: 12,
  fontWeight: 800,
  cursor: "pointer",
  boxShadow: "0 4px 12px rgba(8,145,178,0.25)",
};

const emptyCellStyle: React.CSSProperties = {
  ...tdStyle,
  textAlign: "center",
  color: "var(--muted)",
  padding: "18px 10px",
  whiteSpace: "pre-line",
  fontSize: 12,
  lineHeight: 1.55,
};

function fmtConf(value: number | undefined) {
  if (!Number.isFinite(value)) return "-";
  const v = Number(value);
  if (v <= 1) return `${(v * 100).toFixed(1)}%`;
  return `${v.toFixed(1)}%`;
}

export default function DetailHistoryPopup({ open, item, onClose, onSaved }: Props) {
  const ui = useUi();
  const [outputs, setOutputs] = useState<HistoryOutputField[]>([]);

  useEffect(() => {
    if (!open) return;
    setOutputs(item?.output_fields ? [...item.output_fields] : []);
  }, [open, item]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  const ocrRows = useMemo(() => item?.ocr_fields ?? [], [item]);

  if (!open || !item) return null;

  const legacyRecord = item.output_fields === undefined && item.ocr_fields === undefined;
  const legacyMessage =
    "이 기록은 이전 버전에서 생성되어 상세 데이터가 없습니다.\n새로 OCR 을 실행하면 다음 행부터 표시됩니다.";

  const handleModify = (idx: number, value: string) => {
    setOutputs((prev) => {
      const next = [...prev];
      if (!next[idx]) return prev;
      next[idx] = { ...next[idx], modified: value };
      return next;
    });
  };

  const handleSave = async () => {
    const updated = updateHistoryRun(item.job_id, { output_fields: outputs });
    if (updated) {
      onSaved?.(updated);
      await ui.alert("저장되었습니다.");
    } else {
      await ui.alert("저장 중 오류가 발생했습니다.");
    }
  };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={panelStyle} onClick={(e) => e.stopPropagation()}>
        <div style={headerStyle}>
          <div style={{ fontSize: 14, fontWeight: 800, color: "var(--text)" }}>상세보기</div>
          <button type="button" style={closeButtonStyle} onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div style={bodyStyle}>
          <div style={leftPaneStyle}>
            {item.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={item.image_url}
                alt={item.file_name}
                style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }}
              />
            ) : (
              <span style={{ color: "var(--muted)", fontSize: 13 }}>OCR 영역지정된 이미지</span>
            )}
          </div>

          <div style={rightPaneStyle}>
            <div style={sectionStyle}>
              <div style={sectionHeaderStyle}>
                <div style={sectionLabelStyle}>출력 필드</div>
                <button type="button" style={saveButtonStyle} onClick={() => void handleSave()}>
                  저장
                </button>
              </div>
              <div style={tableWrapStyle}>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={{ ...thStyle, width: 44 }}>No</th>
                      <th style={thStyle}>영문필드명</th>
                      <th style={thStyle}>한글필드명</th>
                      <th style={thStyle}>원본 데이터</th>
                      <th style={thStyle}>수정 데이터</th>
                      <th style={{ ...thStyle, width: 80 }}>정확도</th>
                    </tr>
                  </thead>
                  <tbody>
                    {outputs.length === 0 ? (
                      <tr>
                        <td colSpan={6} style={emptyCellStyle}>
                          {legacyRecord ? legacyMessage : "출력 필드가 없습니다"}
                        </td>
                      </tr>
                    ) : (
                      outputs.map((row, idx) => (
                        <tr key={`${row.en}-${idx}`}>
                          <td style={{ ...tdStyle, textAlign: "center" }}>{row.no ?? idx + 1}</td>
                          <td style={tdStyle}>{row.en}</td>
                          <td style={tdStyle}>{row.ko}</td>
                          <td style={tdStyle}>{row.original}</td>
                          <td style={tdStyle}>
                            <input
                              type="text"
                              value={row.modified}
                              onChange={(e) => handleModify(idx, e.target.value)}
                              style={inputStyle}
                            />
                          </td>
                          <td style={{ ...tdStyle, textAlign: "right" }}>{fmtConf(row.confidence)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div style={sectionStyle}>
              <div style={sectionHeaderStyle}>
                <div style={sectionLabelStyle}>OCR 데이터</div>
              </div>
              <div style={tableWrapStyle}>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={{ ...thStyle, width: 44 }}>No</th>
                      <th style={thStyle}>영문필드명</th>
                      <th style={thStyle}>한글필드명</th>
                      <th style={thStyle}>원본 데이터</th>
                      <th style={{ ...thStyle, width: 80 }}>정확도</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ocrRows.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={emptyCellStyle}>
                          {legacyRecord ? legacyMessage : "OCR 데이터가 없습니다"}
                        </td>
                      </tr>
                    ) : (
                      ocrRows.map((row, idx) => (
                        <tr key={`${row.name}-${idx}`}>
                          <td style={{ ...tdStyle, textAlign: "center" }}>{idx + 1}</td>
                          <td style={tdStyle}>{row.name}</td>
                          <td style={tdStyle}>-</td>
                          <td style={tdStyle}>{row.value}</td>
                          <td style={{ ...tdStyle, textAlign: "right" }}>{fmtConf(row.confidence)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
