"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  type HistoryRunRecord,
  type HistoryOutputField,
  updateHistoryRun,
  getOriginalHistoryImage,
  getProcessedHistoryImage,
  syncHistoryIndexAndDetailOnSave,
  syncHistoryDetailTableRowsOnSave,
} from "@/lib/historyStore";
import {
  buildInvoicePreviewCols,
  normalizeTableCell,
} from "@/lib/invoiceTableDisplay";
import { resolveFieldLabel } from "@/lib/invoiceFieldLabels";
import {
  getGroundTruth,
  saveGroundTruth,
  fieldKey,
  compareToGt,
  type GroundTruthMap,
  type MatchStatus,
} from "@/lib/groundTruthStore";
import { useUi } from "../common/AppProviders";
import { normalizeBizNumber } from "@/lib/bizNumber";
import { normalizeAutofillFieldKey } from "@/lib/autofillEngine";
import {
  type RestoreProfile,
  type RestoreProfileFields,
  AUTOFILL_TO_PROFILE_KEY,
  PROFILE_FIELD_LABELS,
  isMeaninglessValue,
  readRestoreProfiles,
  writeRestoreProfiles,
} from "@/lib/restoreProfileStore";

type Props = {
  item: HistoryRunRecord | null;
  onBack: () => void;
  onSaved?: (record: HistoryRunRecord) => void;
};

const rootStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 12,
  width: "100%",
  height: "100%",
  minHeight: 0,
};

const headerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "10px 14px",
  background: "var(--panel)",
  border: "1px solid var(--border)",
  borderRadius: 12,
};

const headerLeftStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 12,
};

const closeButtonStyle: React.CSSProperties = {
  border: "1px solid var(--border)",
  background: "var(--panel2)",
  color: "var(--text)",
  borderRadius: 8,
  width: 30,
  height: 30,
  fontSize: 14,
  fontWeight: 700,
  cursor: "pointer",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  lineHeight: 1,
  flexShrink: 0,
};

const titleStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 800,
  color: "var(--text)",
};

const metaStyle: React.CSSProperties = {
  fontSize: 12,
  color: "var(--muted)",
};

const bodyStyle: React.CSSProperties = {
  flex: 1,
  minHeight: 0,
  display: "flex",
  gap: 14,
};

const leftPaneStyle: React.CSSProperties = {
  flex: "0 0 44%",
  display: "flex",
  flexDirection: "column",
  gap: 8,
  minWidth: 0,
  overflow: "hidden",
};

const imageCardStyle: React.CSSProperties = {
  flex: 1,
  border: "1px solid var(--border)",
  borderRadius: 12,
  background: "var(--panel2)",
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
  minHeight: 0,
};

const imageCardHeaderStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 700,
  color: "var(--muted)",
  padding: "6px 10px",
  borderBottom: "1px solid var(--border)",
  background: "var(--panel)",
  flexShrink: 0,
};

const imageCardBodyStyle: React.CSSProperties = {
  flex: 1,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  overflow: "hidden",
  minHeight: 0,
  padding: 4,
};

const imagePlaceholderStyle: React.CSSProperties = {
  color: "var(--muted)",
  fontSize: 12,
  textAlign: "center",
  padding: "12px 8px",
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
  background: "var(--panel)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 12,
};

const sectionHeaderStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  paddingBottom: 8,
  borderBottom: "1px solid var(--border)",
};

const sectionLabelStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 800,
  color: "var(--accent)",
  letterSpacing: 0.2,
};

const tableWrapStyle: React.CSSProperties = {
  borderRadius: 8,
  overflow: "auto",
  flex: 1,
  minHeight: 0,
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

const restoreButtonStyle: React.CSSProperties = {
  border: "1px solid var(--accent)",
  background: "transparent",
  color: "var(--accent)",
  borderRadius: 8,
  padding: "6px 14px",
  fontSize: 12,
  fontWeight: 800,
  cursor: "pointer",
};

const modalOverlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.55)",
  zIndex: 1000,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const modalCardStyle: React.CSSProperties = {
  background: "var(--panel)",
  border: "1px solid var(--border)",
  borderRadius: 14,
  padding: 24,
  maxWidth: 540,
  width: "90%",
  display: "flex",
  flexDirection: "column",
  gap: 14,
};

const cancelButtonStyle: React.CSSProperties = {
  border: "1px solid var(--border)",
  background: "var(--panel2)",
  color: "var(--text)",
  borderRadius: 8,
  padding: "6px 16px",
  fontSize: 12,
  fontWeight: 700,
  cursor: "pointer",
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

// ── 품목표 렌더링 헬퍼 (HISTORY-DETAIL-1) ────────────────────────────────────

const _TBL_IDX_KEYS  = new Set(["rowIndex", "no", "rowNo", "lineNo", "seq"]);
const _TBL_NUM_KEYS  = new Set(["quantity", "unitPrice", "consumerUnitPrice", "supplyUnitPrice",
                                "amount", "supplyAmount", "taxAmount", "totalAmount"]);
const _TBL_CODE_KEYS = new Set(["itemCode", "insuranceCode", "serialNo", "lotNo", "manufacturingNo"]);
const _TBL_WIDE_KEYS = new Set(["itemName", "manufacturer"]);

function tblColWidth(key: string): string {
  if (_TBL_IDX_KEYS.has(key))  return "48px";
  if (key === "quantity")       return "60px";
  if (_TBL_NUM_KEYS.has(key))  return "88px";
  if (_TBL_CODE_KEYS.has(key)) return "92px";
  if (_TBL_WIDE_KEYS.has(key)) return "auto";
  return "78px";
}

function tblDataAlign(key: string): React.CSSProperties["textAlign"] {
  if (_TBL_IDX_KEYS.has(key)) return "center";
  if (_TBL_NUM_KEYS.has(key)) return "right";
  return "left";
}

const tblInputStyle: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  border: "1px solid var(--border)",
  borderRadius: 4,
  padding: "3px 6px",
  fontSize: 12,
  background: "var(--panel2)",
  color: "var(--text)",
};

const tblThStyle: React.CSSProperties = {
  background: "var(--panel2)",
  color: "var(--muted)",
  fontWeight: 700,
  textAlign: "center",
  padding: "6px 8px",
  borderBottom: "1px solid var(--border)",
  whiteSpace: "nowrap",
  position: "sticky",
  top: 0,
  zIndex: 1,
  fontSize: 11,
};

const tblTdStyle: React.CSSProperties = {
  padding: "5px 8px",
  borderBottom: "1px solid var(--border)",
  color: "var(--text)",
  verticalAlign: "middle",
  fontSize: 12,
};

const matchCellMatch: React.CSSProperties = {
  color: "#22c55e",
  fontWeight: 800,
};
const matchCellMismatch: React.CSSProperties = {
  color: "#f87171",
  fontWeight: 700,
};
const matchCellNone: React.CSSProperties = {
  color: "var(--muted)",
};

function MatchCell({ status, gt }: { status: MatchStatus; gt?: string }) {
  if (status === "match") {
    return <span style={matchCellMatch}>✓</span>;
  }
  if (status === "mismatch") {
    return (
      <span style={matchCellMismatch} title={gt ? `정답: ${gt}` : undefined}>
        ✗ <span style={{ fontWeight: 500, color: "var(--muted)", marginLeft: 4 }}>
          {gt ? `정답: ${gt}` : ""}
        </span>
      </span>
    );
  }
  return <span style={matchCellNone}>-</span>;
}

function fmtConf(value: number | undefined) {
  if (!Number.isFinite(value)) return "-";
  const v = Number(value);
  if (v <= 1) return `${(v * 100).toFixed(1)}%`;
  return `${v.toFixed(1)}%`;
}

type ImagePanelProps = {
  title: string;
  imageUrl: string | null;
  emptyText: string;
  alt: string;
};

function ImagePanel({ title, imageUrl, emptyText, alt }: ImagePanelProps) {
  return (
    <div style={imageCardStyle}>
      <div style={imageCardHeaderStyle}>{title}</div>
      <div style={imageCardBodyStyle}>
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={alt}
            style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }}
            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
          />
        ) : (
          <span style={imagePlaceholderStyle}>{emptyText}</span>
        )}
      </div>
    </div>
  );
}

function SourceBadge(_: { source?: HistoryOutputField["source"] }) {
  return null;
}

export default function DetailHistoryView({ item, onBack, onSaved }: Props) {
  const ui = useUi();
  const [outputs, setOutputs] = useState<HistoryOutputField[]>([]);
  const [gtMap, setGtMap] = useState<GroundTruthMap>({});
  const [restoreConfirm, setRestoreConfirm] = useState<{
    existing: RestoreProfile;
    newProfile: RestoreProfile;
  } | null>(null);

  useEffect(() => {
    setOutputs(item?.output_fields ? [...item.output_fields] : []);
    const rawRows = item?.document_fields?.tableRows;
    setEditedTableRows(
      Array.isArray(rawRows) && rawRows.length > 0
        ? (rawRows as Record<string, unknown>[]).map((row) => ({ ...row }))
        : null,
    );
    if (item) {
      setGtMap(getGroundTruth(item.template_name, item.file_name));
    } else {
      setGtMap({});
    }
  }, [item]);

  const ocrRows = useMemo(() => item?.ocr_fields ?? [], [item]);
  const [tableRowsOpen, setTableRowsOpen] = useState(false);
  const [editedTableRows, setEditedTableRows] = useState<Record<string, unknown>[] | null>(null);

  // HISTORY-DETAIL-1: detail.runSnapshot.documentFields.tableRows 표시
  const tableRows = useMemo((): Record<string, unknown>[] | null => {
    const df = item?.document_fields;
    if (!df) return null;
    const rows = df.tableRows;
    if (!Array.isArray(rows) || rows.length === 0) return null;
    return rows as Record<string, unknown>[];
  }, [item]);

  const tableMeta = useMemo(
    () => (item?.document_fields?.tableMeta ?? null) as Record<string, unknown> | null,
    [item],
  );

  const tableDisplayCols = useMemo(
    () => (tableRows ? buildInvoicePreviewCols(tableMeta, tableRows) : null),
    [tableRows, tableMeta],
  );

  if (!item) return null;

  const legacyRecord = item.output_fields === undefined && item.ocr_fields === undefined;
  const legacyMessage =
    "이 기록은 이전 버전에서 생성되어 상세 데이터가 없습니다.\n새로 OCR 을 실행하면 다음 행부터 표시됩니다.";

  const handleModify = (idx: number, value: string) => {
    setOutputs((prev) => {
      const next = [...prev];
      if (!next[idx]) return prev;
      next[idx] = { ...next[idx], modified: value, source: "text" };
      return next;
    });
  };

  const handleSave = async () => {
    const updated = updateHistoryRun(item.job_id, { output_fields: outputs });
    if (updated) {
      // 정답(기준값) 저장소에도 동시 반영. 빈 modified 는 모듈 내부에서 자동 제외.
      const newGt = saveGroundTruth(item.template_name, item.file_name, outputs);
      setGtMap(newGt);
      // HISTORY-DETAIL-1: legacy store 반환값에 document_fields 보존 (편집된 tableRows 반영)
      const savedDocFields = item.document_fields
        ? { ...item.document_fields, tableRows: editedTableRows ?? item.document_fields.tableRows }
        : undefined;
      onSaved?.({ ...updated, document_fields: savedDocFields });
      // HISTORY-STRUCTURE-2A: confirmedResult + index.updatedAt 병행 갱신 (실패해도 기존 저장 유지)
      try {
        syncHistoryIndexAndDetailOnSave(item.job_id, outputs);
      } catch (e) {
        console.warn("[history-structure] index/detail sync failed on save", e);
      }
      // 편집된 tableRows 저장 (실패해도 기존 저장 유지)
      if (editedTableRows) {
        try {
          syncHistoryDetailTableRowsOnSave(item.job_id, editedTableRows);
        } catch (e) {
          console.warn("[history-detail] tableRows save failed", e);
        }
      }
      await ui.alert("저장되었습니다. 동일한 템플릿·파일로 다음에 OCR 을 실행하면 일치 여부가 표시됩니다.");
    } else {
      await ui.alert("저장 중 오류가 발생했습니다.");
    }
  };

  const handleSaveRestoreProfile = async () => {
    let businessNo: string | null = null;
    const fields: RestoreProfileFields = {};

    for (const row of outputs) {
      const canonicalKey = normalizeAutofillFieldKey(row.ko || row.en);
      const value = row.modified.trim() || row.original.trim();
      if (!value || isMeaninglessValue(value)) continue;

      if (canonicalKey === "사업자번호") {
        businessNo = normalizeBizNumber(value);
      } else {
        const profileKey = AUTOFILL_TO_PROFILE_KEY[canonicalKey];
        if (profileKey) {
          fields[profileKey] = value;
        }
      }
    }

    if (!businessNo) {
      await ui.alert("자동복원 후보를 저장할 수 없습니다. 사업자번호가 필요합니다.");
      return;
    }
    if (Object.keys(fields).length === 0) {
      await ui.alert("자동복원 후보로 저장할 필드가 없습니다.");
      return;
    }

    const now = new Date().toISOString().slice(0, 19).replace("T", " ");
    const newProfile: RestoreProfile = {
      businessNo,
      partyType: "generic",
      fields,
      sourceHistoryId: item.job_id,
      sourceFileName: item.file_name,
      createdAt: now,
      updatedAt: now,
    };

    const profiles = readRestoreProfiles();
    const existingIdx = profiles.findIndex(
      (p) => p.businessNo === businessNo && p.partyType === "generic",
    );

    if (existingIdx === -1) {
      profiles.push(newProfile);
      try {
        writeRestoreProfiles(profiles);
        await ui.alert(`자동복원 후보 저장 완료 · ${Object.keys(fields).length}개 필드`);
      } catch {
        await ui.alert("저장 중 오류가 발생했습니다.");
      }
      return;
    }

    const existing = profiles[existingIdx]!;
    const allSame = Object.entries(fields).every(([key, val]) => {
      const existingVal = (existing.fields[key as keyof RestoreProfileFields] ?? "").trim();
      return existingVal === val.trim();
    });

    if (allSame) {
      await ui.alert("이미 동일한 자동복원 후보가 저장되어 있습니다.");
      return;
    }

    setRestoreConfirm({ existing, newProfile });
  };

  const handleRestoreConfirmOk = () => {
    if (!restoreConfirm) return;
    const { existing, newProfile } = restoreConfirm;

    const profiles = readRestoreProfiles();
    const idx = profiles.findIndex(
      (p) => p.businessNo === newProfile.businessNo && p.partyType === newProfile.partyType,
    );

    const mergedFields: RestoreProfileFields = { ...existing.fields };
    for (const [key, val] of Object.entries(newProfile.fields)) {
      if (!isMeaninglessValue(val)) {
        mergedFields[key as keyof RestoreProfileFields] = val;
      }
    }

    const updated: RestoreProfile = {
      ...newProfile,
      fields: mergedFields,
      createdAt: existing.createdAt,
    };

    if (idx !== -1) {
      profiles[idx] = updated;
    } else {
      profiles.push(updated);
    }

    try {
      writeRestoreProfiles(profiles);
      setRestoreConfirm(null);
      void ui.alert(`자동복원 후보 갱신 완료 · ${Object.keys(newProfile.fields).length}개 필드`);
    } catch {
      setRestoreConfirm(null);
      void ui.alert("저장 중 오류가 발생했습니다.");
    }
  };

  return (
    <div style={rootStyle}>
      <div style={headerStyle}>
        <div style={headerLeftStyle}>
          <div style={titleStyle}>상세보기</div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "var(--accent)",
              padding: "2px 10px",
              border: "1px solid var(--border)",
              borderRadius: 999,
              background: "var(--panel2)",
            }}
            title="템플릿 이름"
          >
            {item.template_name ?? "-"}
          </div>
          <div style={metaStyle}>
            {item.file_name} · {item.created_at}
          </div>
          {Object.keys(gtMap).length > 0 && (
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: "var(--accent)",
                border: "1px solid var(--accent)",
                borderRadius: 999,
                padding: "2px 9px",
              }}
              title={`정답 ${Object.keys(gtMap).length}개 저장됨`}
            >
              정답 저장됨 ({Object.keys(gtMap).length})
            </span>
          )}
        </div>
        <button type="button" style={closeButtonStyle} onClick={onBack} aria-label="닫기">
          ✕
        </button>
      </div>

      <div style={bodyStyle}>
        <div style={leftPaneStyle}>
          {/* 상단: 전처리 전 원본 이미지 */}
          <ImagePanel
            title="전처리 전 이미지"
            imageUrl={getOriginalHistoryImage(item)}
            emptyText="원본 이미지 없음"
            alt={`원본 - ${item.file_name}`}
          />
          {/* 하단: 전처리 후 이미지 (processed_image_url → image_url legacy fallback) */}
          <ImagePanel
            title="전처리 후 이미지"
            imageUrl={getProcessedHistoryImage(item)}
            emptyText="전처리 후 이미지 없음"
            alt={`전처리 - ${item.file_name}`}
          />
        </div>

        <div style={rightPaneStyle}>
          <div style={{ ...sectionStyle, flex: tableRowsOpen ? 7 : 1 }}>
            <div style={sectionHeaderStyle}>
              <div style={sectionLabelStyle}>출력 필드</div>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="button" style={saveButtonStyle} onClick={() => void handleSave()}>
                  저장
                </button>
                <button type="button" style={restoreButtonStyle} onClick={() => void handleSaveRestoreProfile()}>
                  자동복원 후보 저장
                </button>
              </div>
            </div>
            <div style={tableWrapStyle}>
              <table style={{ ...tableStyle, tableLayout: "fixed" }}>
                <colgroup>
                  <col style={{ width: 44 }} />
                  <col />
                  <col />
                  <col style={{ width: "28%" }} />
                  <col style={{ width: "28%" }} />
                  <col style={{ width: 72 }} />
                  <col style={{ width: 48 }} />
                </colgroup>
                <thead>
                  <tr>
                    <th style={{ ...thStyle, textAlign: "center" }}>No</th>
                    <th style={thStyle}>영문 필드명</th>
                    <th style={thStyle}>한글 필드명</th>
                    <th style={thStyle}>원본 데이터</th>
                    <th style={thStyle}>수정 데이터</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>정확도</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>일치</th>
                  </tr>
                </thead>
                <tbody>
                  {outputs.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={emptyCellStyle}>
                        {legacyRecord ? legacyMessage : "출력 필드가 없습니다"}
                      </td>
                    </tr>
                  ) : (
                    outputs.map((row, idx) => {
                      const isRawTable = /^\s*\[[\[{]/.test(row.original ?? "") || /^\s*\[[\[{]/.test(row.modified ?? "");
                      const cmp = isRawTable ? { status: "none" as const, gt: undefined } : compareToGt(row.original, gtMap[fieldKey(row.en, row.ko)]);
                      // ko 없으면 ocrRows[idx].name 으로 한글 라벨 보강 (canonical key → INVOICE_FIELD_KO 매핑)
                      const displayKo = row.ko || (() => {
                        const ocrRow = ocrRows[idx];
                        if (!ocrRow) return "";
                        const { primary } = resolveFieldLabel({ name: ocrRow.name, ko: ocrRow.ko ?? "", en: ocrRow.en ?? row.en });
                        return primary !== ocrRow.name && primary !== row.en ? primary : "";
                      })();
                      return (
                        <tr key={`${row.en}-${idx}`}>
                          <td style={{ ...tdStyle, textAlign: "center" }}>{row.no ?? idx + 1}</td>
                          <td style={tdStyle}>{row.en}</td>
                          <td style={tdStyle}>{displayKo}</td>
                          <td style={tdStyle}>
                            {isRawTable
                              ? `표 데이터${tableRows ? ` (${tableRows.length}행)` : ""}`
                              : row.original}
                          </td>
                          <td style={tdStyle}>
                            {isRawTable ? (
                              <span>-</span>
                            ) : (
                              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                <input
                                  type="text"
                                  value={row.modified}
                                  onChange={(e) => handleModify(idx, e.target.value)}
                                  style={inputStyle}
                                />
                                <SourceBadge source={row.source} />
                              </div>
                            )}
                          </td>
                          <td style={{ ...tdStyle, textAlign: "center" }}>{fmtConf(row.confidence)}</td>
                          <td style={{ ...tdStyle, textAlign: "center" }}>
                            <MatchCell status={cmp.status} gt={cmp.gt} />
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* HISTORY-DETAIL-1: 품목표 — 접이식, tableRows가 있을 때만 표시 */}
            {tableRows && tableRows.length > 0 && tableDisplayCols && tableDisplayCols.length > 0 && (
              <>
                <button
                  type="button"
                  onClick={() => setTableRowsOpen((v) => !v)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    width: "100%",
                    paddingTop: 10,
                    paddingBottom: 0,
                    borderTop: "1px solid var(--border)",
                    marginTop: 4,
                    background: "transparent",
                    border: "none",
                    borderTopWidth: 1,
                    borderTopStyle: "solid",
                    borderTopColor: "var(--border)",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <span style={sectionLabelStyle}>품목표</span>
                  <span style={{ fontSize: 12, color: "var(--muted)", display: "flex", alignItems: "center", gap: 6 }}>
                    <span>표 데이터 · {tableRows.length}행</span>
                    <span style={{ fontSize: 10 }}>{tableRowsOpen ? "▲" : "▼"}</span>
                  </span>
                </button>
                {tableRowsOpen && (
                  <div style={{ overflowX: "auto", overflowY: "auto", maxHeight: 200, borderRadius: 8 }}>
                    <table style={{ ...tableStyle, tableLayout: "fixed", minWidth: "100%" }}>
                      <colgroup>
                        {tableDisplayCols.map((col) => (
                          <col key={col.key} style={{ width: tblColWidth(col.key) }} />
                        ))}
                      </colgroup>
                      <tbody>
                        <tr>
                          {tableDisplayCols.map((col) => (
                            <th key={col.key} style={tblThStyle}>
                              <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={col.labelKo}>
                                {col.labelKo}
                              </div>
                              {col.labelKo !== col.key && (
                                <div title={col.key} style={{
                                  fontSize: 10,
                                  opacity: 0.5,
                                  marginTop: 1,
                                  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                                  whiteSpace: "nowrap",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                }}>
                                  ({col.key})
                                </div>
                              )}
                            </th>
                          ))}
                        </tr>
                        {(editedTableRows ?? tableRows)!.map((row, ri) => (
                          <tr key={ri}>
                            {tableDisplayCols.map((col) => (
                              <td key={col.key} style={{ ...tblTdStyle, padding: "3px 6px" }}>
                                <input
                                  type="text"
                                  value={normalizeTableCell(row[col.key])}
                                  onChange={(e) => {
                                    setEditedTableRows((prev) => {
                                      const base = prev ?? (tableRows ? tableRows.map((r) => ({ ...r })) : []);
                                      return base.map((r, i) => i === ri ? { ...r, [col.key]: e.target.value } : r);
                                    });
                                  }}
                                  style={{
                                    ...tblInputStyle,
                                    textAlign: tblDataAlign(col.key),
                                  }}
                                />
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </div>

          <div style={{ ...sectionStyle, flex: tableRowsOpen ? 3 : 1 }}>
            <div style={sectionHeaderStyle}>
              <div style={sectionLabelStyle}>OCR 데이터</div>
            </div>
            <div style={tableWrapStyle}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={{ ...thStyle, width: 44 }}>No</th>
                    <th style={thStyle}>영문 필드명</th>
                    <th style={thStyle}>한글 필드명</th>
                    <th style={thStyle}>원본 데이터</th>
                    <th style={{ ...thStyle, width: 72, textAlign: "center" }}>정확도</th>
                    <th style={{ ...thStyle, width: 48, textAlign: "center" }}>일치</th>
                  </tr>
                </thead>
                <tbody>
                  {ocrRows.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={emptyCellStyle}>
                        {legacyRecord ? legacyMessage : "OCR 데이터가 없습니다"}
                      </td>
                    </tr>
                  ) : (
                    ocrRows.map((row, idx) => {
                      // 1순위: 템플릿이 정의한 enField/koField (저장 시 함께 적재됨).
                      // 2순위(legacy): name 의 한글 포함 여부로 자동 분리.
                      const hasKorean = /[가-힯]/.test(row.name);
                      const enName = row.en ?? (hasKorean ? "" : row.name);
                      const koName = row.ko ?? (hasKorean ? row.name : "");
                      const cmp = compareToGt(row.value, gtMap[fieldKey(enName, koName) || fieldKey(row.name)]);
                      return (
                        <tr key={`${row.name}-${idx}`}>
                          <td style={{ ...tdStyle, textAlign: "center" }}>{idx + 1}</td>
                          <td style={tdStyle}>{enName || "-"}</td>
                          <td style={tdStyle}>{koName || "-"}</td>
                          <td style={tdStyle}>{row.value}</td>
                          <td style={{ ...tdStyle, textAlign: "center" }}>{fmtConf(row.confidence)}</td>
                          <td style={{ ...tdStyle, textAlign: "center" }}>
                            <MatchCell status={cmp.status} gt={cmp.gt} />
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {restoreConfirm && (
        <div style={modalOverlayStyle} onClick={() => setRestoreConfirm(null)}>
          <div style={modalCardStyle} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontWeight: 800, fontSize: 14, color: "var(--text)" }}>
              이미 저장된 자동복원 후보가 있습니다.
            </div>
            <div style={{ fontSize: 12, color: "var(--muted)" }}>
              사업자번호: {restoreConfirm.newProfile.businessNo}
            </div>
            <div style={{ display: "flex", gap: 16 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 8, color: "var(--muted)" }}>기존 후보</div>
                {(Object.keys(PROFILE_FIELD_LABELS) as (keyof RestoreProfileFields)[]).map((key) => (
                  <div key={key} style={{ fontSize: 12, marginBottom: 4 }}>
                    <span style={{ color: "var(--muted)", marginRight: 6 }}>{PROFILE_FIELD_LABELS[key]}:</span>
                    <span style={{ color: "var(--text)" }}>{restoreConfirm.existing.fields[key] || "-"}</span>
                  </div>
                ))}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 8, color: "var(--accent)" }}>새 후보</div>
                {(Object.keys(PROFILE_FIELD_LABELS) as (keyof RestoreProfileFields)[]).map((key) => {
                  const existingVal = (restoreConfirm.existing.fields[key] ?? "").trim();
                  const newVal = (restoreConfirm.newProfile.fields[key] ?? "").trim();
                  const changed = newVal !== "" && newVal !== existingVal;
                  return (
                    <div key={key} style={{ fontSize: 12, marginBottom: 4 }}>
                      <span style={{ color: "var(--muted)", marginRight: 6 }}>{PROFILE_FIELD_LABELS[key]}:</span>
                      <span style={{ color: changed ? "var(--accent)" : "var(--text)", fontWeight: changed ? 700 : 400 }}>
                        {newVal || "-"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
            <div style={{ fontSize: 12, color: "var(--text)", borderTop: "1px solid var(--border)", paddingTop: 12 }}>
              기존 후보를 새 값으로 갱신하시겠습니까?
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button type="button" style={cancelButtonStyle} onClick={() => setRestoreConfirm(null)}>
                취소
              </button>
              <button type="button" style={saveButtonStyle} onClick={handleRestoreConfirmOk}>
                최신값으로 갱신
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
