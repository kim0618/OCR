"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import AppShell from "../../components/layout/AppShell";
import UnstructuredBuilder from "../../components/template/UnstructuredBuilder";

const OcrAnnotator = dynamic(
  () => import("../../components/ocr/OcrAnnotator"),
  {
    ssr: false,
    loading: () => <div style={{ padding: 16, color: "var(--muted)" }}>로딩중...</div>,
  },
);

type Mode = "template" | "unstructured";

function ModeCard({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: 120,
        height: 32,
        borderRadius: 8,
        border: active ? "2px solid var(--accent)" : "1.5px solid rgba(255,255,255,0.12)",
        background: active ? "var(--accentBg)" : "var(--panel2)",
        color: active ? "var(--accent)" : "var(--muted)",
        cursor: "pointer",
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        transition: "all 0.15s",
        flexShrink: 0,
        boxShadow: active ? "inset 0 0 0 1px var(--accent)" : "none",
      }}
    >
      <span style={{ fontSize: 14, lineHeight: 1 }}>{icon}</span>
      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 0.3 }}>{label}</span>
    </button>
  );
}


export default function Page() {
  const [mode, setMode] = useState<Mode>("template");

  return (
    <AppShell headerTitle="Template" scrollMode="fixed">
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          gap: 8,
          boxSizing: "border-box",
        }}
      >
        {/* 상단: 모드 카드 + 저장된 템플릿 영역 (전체 폭) */}
        <div style={{
          flexShrink: 0,
          display: "flex",
          gap: 12,
          alignItems: "stretch",
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: "10px 14px",
        }}>
          {/* 모드 선택 (위/아래) */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8, flexShrink: 0 }}>
            <ModeCard
              active={mode === "template"}
              onClick={() => setMode("template")}
              icon="＋"
              label="템플릿 생성"
            />
            <ModeCard
              active={mode === "unstructured"}
              onClick={() => setMode("unstructured")}
              icon="≡"
              label="비정형 생성"
            />
          </div>

          {/* 구분선 */}
          <div style={{ width: 1, background: "var(--border)" }} />

          {/* 저장된 템플릿 (우측 — 추후 채워짐) */}
          <div style={{
            flex: 1,
            minWidth: 0,
            display: "flex",
            alignItems: "center",
            gap: 10,
            color: "var(--muted)",
            fontSize: 12,
          }}>
            <span style={{ fontWeight: 700 }}>저장된 템플릿</span>
            <span style={{ fontSize: 11, opacity: 0.7 }}>아직 저장된 템플릿이 없습니다.</span>
          </div>
        </div>

        {/* 모드 콘텐츠 */}
        <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
          {mode === "template" ? (
            <OcrAnnotator />
          ) : (
            <UnstructuredBuilder />
          )}
        </div>
      </div>
    </AppShell>
  );
}
