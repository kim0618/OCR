"use client";

import React, { useEffect, useState } from "react";
import { useUi } from "../common/AppProviders";
import {
  type RestoreProfile,
  type RestoreProfileFields,
  PROFILE_FIELD_LABELS,
  readRestoreProfiles,
  deleteRestoreProfile,
  sortRestoreProfilesByUpdatedAt,
} from "@/lib/restoreProfileStore";

const rootStyle: React.CSSProperties = {
  display: "flex",
  gap: 14,
  width: "100%",
  height: "100%",
  minHeight: 0,
};

const sectionStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
  background: "var(--panel)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 12,
  minHeight: 0,
};

const sectionHeaderStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  paddingBottom: 8,
  borderBottom: "1px solid var(--border)",
  flexShrink: 0,
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

const emptyStyle: React.CSSProperties = {
  textAlign: "center",
  padding: "40px 20px",
  color: "var(--text)",
  fontSize: 13,
  lineHeight: 1.8,
};

const deleteButtonStyle: React.CSSProperties = {
  border: "1px solid #f87171",
  background: "transparent",
  color: "#f87171",
  borderRadius: 6,
  padding: "4px 10px",
  fontSize: 11,
  fontWeight: 700,
  cursor: "pointer",
};

const closeButtonStyle: React.CSSProperties = {
  border: "1px solid var(--border)",
  background: "var(--panel2)",
  color: "var(--text)",
  borderRadius: 8,
  width: 28,
  height: 28,
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  flexShrink: 0,
};

const detailDividerStyle: React.CSSProperties = {
  borderTop: "1px solid var(--border)",
  margin: "4px 0",
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
  maxWidth: 460,
  width: "90%",
  display: "flex",
  flexDirection: "column",
  gap: 12,
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

const confirmDeleteButtonStyle: React.CSSProperties = {
  border: "none",
  background: "#ef4444",
  color: "#ffffff",
  borderRadius: 8,
  padding: "6px 16px",
  fontSize: 12,
  fontWeight: 800,
  cursor: "pointer",
};

function fmtDate(v: string | undefined): string {
  if (!v) return "-";
  return v.slice(0, 16);
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", gap: 8, fontSize: 12, alignItems: "flex-start" }}>
      <div style={{ color: "var(--muted)", flexShrink: 0, width: 112 }}>{label}</div>
      <div style={{ color: "var(--text)", flex: 1, wordBreak: "break-all" }}>{value}</div>
    </div>
  );
}

export default function AutoRestoreWorkspace() {
  const ui = useUi();
  const [profiles, setProfiles] = useState<RestoreProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<RestoreProfile | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<RestoreProfile | null>(null);

  const load = () => {
    try {
      const list = sortRestoreProfilesByUpdatedAt(readRestoreProfiles());
      setProfiles(list);
    } catch {
      setProfiles([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDeleteClick = (profile: RestoreProfile, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteTarget(profile);
  };

  const handleDeleteConfirm = () => {
    if (!deleteTarget) return;
    try {
      deleteRestoreProfile(deleteTarget.businessNo, deleteTarget.partyType);
      if (
        selectedProfile?.businessNo === deleteTarget.businessNo &&
        selectedProfile?.partyType === deleteTarget.partyType
      ) {
        setSelectedProfile(null);
      }
      setDeleteTarget(null);
      load();
    } catch {
      setDeleteTarget(null);
      void ui.alert("삭제 중 오류가 발생했습니다.");
    }
  };

  const isEmpty = profiles.length === 0;
  const hasDetail = selectedProfile !== null;

  return (
    <div style={rootStyle}>
      {/* 목록 패널 */}
      <div
        style={{
          flex: hasDetail ? "0 0 56%" : "1",
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
          ...sectionStyle,
        }}
      >
        <div style={sectionHeaderStyle}>
          <div style={sectionLabelStyle}>자동복원 후보 목록</div>
          <div style={{ fontSize: 12, color: "var(--muted)" }}>
            {profiles.length}개 저장됨
          </div>
        </div>

        <div style={tableWrapStyle}>
          {isEmpty ? (
            <div style={emptyStyle}>
              <div>저장된 자동복원 후보가 없습니다.</div>
              <div style={{ marginTop: 6, color: "var(--muted)", fontSize: 11 }}>
                History 상세보기에서 [자동복원 후보 저장]을 누르면 이곳에 표시됩니다.
              </div>
            </div>
          ) : (
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>사업자번호</th>
                  <th style={thStyle}>회사명</th>
                  {!hasDetail && <th style={thStyle}>대표자</th>}
                  {!hasDetail && <th style={thStyle}>전화번호</th>}
                  <th style={{ ...thStyle, maxWidth: hasDetail ? 70 : 160 }}>주소</th>
                  <th style={thStyle}>원본 파일</th>
                  <th style={thStyle}>최근 갱신일</th>
                  <th style={{ ...thStyle, width: 56 }}>관리</th>
                </tr>
              </thead>
              <tbody>
                {profiles.map((p) => {
                  const isSelected =
                    selectedProfile?.businessNo === p.businessNo &&
                    selectedProfile?.partyType === p.partyType;
                  return (
                    <tr
                      key={`${p.businessNo}::${p.partyType}`}
                      style={{
                        cursor: "pointer",
                        background: isSelected ? "var(--accentBg)" : "transparent",
                      }}
                      onClick={() => setSelectedProfile(isSelected ? null : p)}
                      onMouseEnter={(e) => {
                        if (!isSelected)
                          (e.currentTarget as HTMLTableRowElement).style.background =
                            "var(--panel2)";
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected)
                          (e.currentTarget as HTMLTableRowElement).style.background =
                            "transparent";
                      }}
                    >
                      <td style={tdStyle}>{p.businessNo || "-"}</td>
                      <td style={tdStyle}>{p.fields?.companyName || "-"}</td>
                      {!hasDetail && <td style={tdStyle}>{p.fields?.representative || "-"}</td>}
                      {!hasDetail && <td style={tdStyle}>{p.fields?.tel || "-"}</td>}
                      <td
                        style={{
                          ...tdStyle,
                          maxWidth: hasDetail ? 70 : 160,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                        title={p.fields?.address}
                      >
                        {p.fields?.address || "-"}
                      </td>
                      <td style={tdStyle}>{p.sourceFileName || "-"}</td>
                      <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>
                        {fmtDate(p.updatedAt ?? p.createdAt)}
                      </td>
                      <td style={tdStyle} onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          style={deleteButtonStyle}
                          onClick={(e) => handleDeleteClick(p, e)}
                        >
                          삭제
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* 상세 패널 */}
      {hasDetail && selectedProfile && (
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
            ...sectionStyle,
          }}
        >
          <div style={sectionHeaderStyle}>
            <div style={sectionLabelStyle}>상세보기</div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button
                type="button"
                style={deleteButtonStyle}
                onClick={() => setDeleteTarget(selectedProfile)}
              >
                삭제
              </button>
              <button
                type="button"
                style={closeButtonStyle}
                onClick={() => setSelectedProfile(null)}
                aria-label="닫기"
              >
                ✕
              </button>
            </div>
          </div>

          <div style={{ overflowY: "auto", flex: 1, padding: "8px 2px", display: "flex", flexDirection: "column", gap: 7 }}>
            <DetailRow label="사업자번호" value={selectedProfile.businessNo || "-"} />
            <DetailRow label="구분" value={selectedProfile.partyType || "generic"} />
            <div style={detailDividerStyle} />
            {(Object.keys(PROFILE_FIELD_LABELS) as (keyof RestoreProfileFields)[]).map((key) => (
              <DetailRow
                key={key}
                label={PROFILE_FIELD_LABELS[key]}
                value={selectedProfile.fields?.[key] || "-"}
              />
            ))}
            <div style={detailDividerStyle} />
            <DetailRow label="원본 파일" value={selectedProfile.sourceFileName || "-"} />
            <DetailRow label="원본 History ID" value={selectedProfile.sourceHistoryId || "-"} />
            <DetailRow label="최초 생성" value={selectedProfile.createdAt || "-"} />
            <DetailRow label="최근 갱신" value={selectedProfile.updatedAt || "-"} />
          </div>
        </div>
      )}

      {/* 삭제 확인 모달 */}
      {deleteTarget && (
        <div style={modalOverlayStyle} onClick={() => setDeleteTarget(null)}>
          <div style={modalCardStyle} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontWeight: 800, fontSize: 14, color: "var(--text)" }}>
              자동복원 후보를 삭제하시겠습니까?
            </div>
            <div
              style={{
                fontSize: 12,
                color: "var(--muted)",
                display: "flex",
                flexDirection: "column",
                gap: 3,
                padding: "8px 10px",
                background: "var(--panel2)",
                borderRadius: 8,
                border: "1px solid var(--border)",
              }}
            >
              <div>사업자번호: {deleteTarget.businessNo}</div>
              <div>회사명: {deleteTarget.fields?.companyName || "-"}</div>
            </div>
            <div
              style={{
                fontSize: 12,
                color: "var(--text)",
                borderTop: "1px solid var(--border)",
                paddingTop: 10,
              }}
            >
              삭제하면 다음 OCR에서 이 후보는 자동복원 기준으로 사용할 수 없습니다.
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button
                type="button"
                style={cancelButtonStyle}
                onClick={() => setDeleteTarget(null)}
              >
                취소
              </button>
              <button
                type="button"
                style={confirmDeleteButtonStyle}
                onClick={handleDeleteConfirm}
              >
                삭제
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
