"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  type HistoryRunRecord,
  type HistoryOutputField,
  updateHistoryRun,
} from "@/lib/historyStore";
import {
  getGroundTruth,
  saveGroundTruth,
  fieldKey,
  compareToGt,
  type GroundTruthMap,
  type MatchStatus,
} from "@/lib/groundTruthStore";
import { useUi } from "../common/AppProviders";

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
  border: "1px solid var(--border)",
  borderRadius: 12,
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

const emptyCellStyle: React.CSSProperties = {
  ...tdStyle,
  textAlign: "center",
  color: "var(--muted)",
  padding: "18px 10px",
  whiteSpace: "pre-line",
  fontSize: 12,
  lineHeight: 1.55,
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

function SourceBadge({ source }: { source?: HistoryOutputField["source"] }) {
  if (!source || source === "ocr") return null;
  const meta =
    source === "biz" ? { label: "매칭복원", bg: "#6366f1", title: "사업자번호 기반 내부 매칭복원" } :
    source === "gt" ? { label: "정답", bg: "#16a34a", title: "저장된 정답" } :
    source === "text" ? { label: "직접입력", bg: "#a855f7", title: "직접 입력값" } :
    null;
  if (!meta) return null;
  return (
    <span
      title={meta.title}
      style={{
        display: "inline-flex",
        alignItems: "center",
        width: "fit-content",
        fontSize: 9,
        fontWeight: 800,
        padding: "2px 6px",
        borderRadius: 4,
        color: "#fff",
        background: meta.bg,
        whiteSpace: "nowrap",
      }}
    >
      {meta.label}
    </span>
  );
}

export default function DetailHistoryView({ item, onBack, onSaved }: Props) {
  const ui = useUi();
  const [outputs, setOutputs] = useState<HistoryOutputField[]>([]);
  const [gtMap, setGtMap] = useState<GroundTruthMap>({});

  useEffect(() => {
    setOutputs(item?.output_fields ? [...item.output_fields] : []);
    if (item) {
      setGtMap(getGroundTruth(item.template_name, item.file_name));
    } else {
      setGtMap({});
    }
  }, [item]);

  const ocrRows = useMemo(() => item?.ocr_fields ?? [], [item]);

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
      onSaved?.(updated);
      await ui.alert("저장되었습니다. 동일한 템플릿·파일로 다음에 OCR 을 실행하면 일치 여부가 표시됩니다.");
    } else {
      await ui.alert("저장 중 오류가 발생했습니다.");
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
                    <th style={thStyle}>일치</th>
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
                      const cmp = compareToGt(row.original, gtMap[fieldKey(row.en, row.ko)]);
                      return (
                        <tr key={`${row.en}-${idx}`}>
                          <td style={{ ...tdStyle, textAlign: "center" }}>{row.no ?? idx + 1}</td>
                          <td style={tdStyle}>{row.en}</td>
                          <td style={tdStyle}>{row.ko}</td>
                          <td style={tdStyle}>{row.original}</td>
                          <td style={tdStyle}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <input
                                type="text"
                                value={row.modified}
                                onChange={(e) => handleModify(idx, e.target.value)}
                                style={inputStyle}
                              />
                              <SourceBadge source={row.source} />
                            </div>
                          </td>
                          <td style={{ ...tdStyle, textAlign: "right" }}>{fmtConf(row.confidence)}</td>
                          <td style={tdStyle}>
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
                    <th style={thStyle}>일치</th>
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
                          <td style={{ ...tdStyle, textAlign: "right" }}>{fmtConf(row.confidence)}</td>
                          <td style={tdStyle}>
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
    </div>
  );
}
