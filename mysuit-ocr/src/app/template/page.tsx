"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import AppShell from "../../components/layout/AppShell";
import UnstructuredBuilder from "../../components/template/UnstructuredBuilder";
import { getTemplateImage } from "@/lib/imageStore";

const OcrAnnotator = dynamic(
  () => import("../../components/template/ui/OcrAnnotator"),
  {
    ssr: false,
    loading: () => <div style={{ padding: 16, color: "var(--muted)" }}>로딩중...</div>,
  },
);

type Mode = "template" | "unstructured";
type SavedTemplate = {
  id: string;
  name: string;
  mode?: string;
  templateJson?: any;
};

const LOCAL_TEMPLATES_KEY = "mysuit_ocr_templates";

function readSavedTemplates(): SavedTemplate[] {
  try {
    const list = JSON.parse(localStorage.getItem(LOCAL_TEMPLATES_KEY) || "[]");
    if (!Array.isArray(list)) return [];
    return list
      .map((item: any) => ({
        id: String(item?.template_id ?? ""),
        name: String(item?.template_name ?? ""),
        mode: String(item?.template_json?.mode ?? "template"),
        templateJson: item?.template_json ?? null,
      }))
      .filter((item) => item.id && item.name);
  } catch {
    return [];
  }
}

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
  const [hover, setHover] = useState(false);
  const showAccent = active || hover;
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        width: 120,
        height: 32,
        borderRadius: 8,
        border: showAccent ? "1px solid var(--accent)" : "1px solid rgba(255,255,255,0.12)",
        background: active ? "var(--accentBg)" : hover ? "var(--panel2)" : "var(--panel2)",
        color: showAccent ? "var(--accent)" : "var(--muted)",
        cursor: "pointer",
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        transition: "all 0.15s",
        flexShrink: 0,
        boxShadow: hover && !active ? "0 0 0 2px var(--accentBg)" : "none",
      }}
    >
      <span style={{ fontSize: 14, lineHeight: 1 }}>{icon}</span>
      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 0.3 }}>{label}</span>
    </button>
  );
}


type TooltipInfo = { imgSrc: string; x: number; y: number };

export default function Page() {
  const [mode, setMode] = useState<Mode>("template");
  const [savedTemplates, setSavedTemplates] = useState<SavedTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<SavedTemplate | null>(null);
  const [resetKey, setResetKey] = useState(0);
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  const handleModeChange = (next: Mode) => {
    setSelectedTemplate(null);
    setResetKey((k) => k + 1);
    setMode(next);
  };

  useEffect(() => {
    const refreshSavedTemplates = () => {
      const base = readSavedTemplates();
      setSavedTemplates(base);
      // UI-IMG-IDB-1: localStorage에 src 없는 템플릿은 IndexedDB에서 hydrate
      void (async () => {
        const hydrated = await Promise.all(base.map(async (t) => {
          if (t?.templateJson?.image?.src) return t;
          if (!t?.id || !t?.templateJson?.image) return t;
          const src = await getTemplateImage(t.id);
          if (!src) return t;
          return { ...t, templateJson: { ...t.templateJson, image: { ...t.templateJson.image, src } } };
        }));
        setSavedTemplates(hydrated);
      })();
    };
    refreshSavedTemplates();
    const onRefresh = () => refreshSavedTemplates();
    window.addEventListener("storage", onRefresh);
    window.addEventListener("mysuit-ocr-template-saved", onRefresh);
    return () => {
      window.removeEventListener("storage", onRefresh);
      window.removeEventListener("mysuit-ocr-template-saved", onRefresh);
    };
  }, []);

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
          alignItems: "center",
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: "6px 14px",
        }}>
          {/* 모드 선택 (위/아래) */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8, flexShrink: 0 }}>
            <ModeCard
              active={mode === "template" && !selectedTemplate}
              onClick={() => handleModeChange("template")}
              icon="＋"
              label="템플릿 생성"
            />
            <ModeCard
              active={mode === "unstructured" && !selectedTemplate}
              onClick={() => handleModeChange("unstructured")}
              icon="≡"
              label="비정형 생성"
            />
          </div>

          {/* 구분선 */}
          <div style={{ width: 1, height: 68, background: "var(--border)", flexShrink: 0 }} />

          {/* 저장된 템플릿 (우측 — 추후 채워짐) */}
          <div style={{
            flex: 1,
            minWidth: 0,
            display: "flex",
            alignItems: "center",
            gap: 12,
            color: "var(--muted)",
            fontSize: 12,
            overflowX: "auto",
          }}>
            {savedTemplates.length > 0 ? (
              <div className="uw-runocr-template-cards">
                {savedTemplates.map((template) => {
                  const isSelected = selectedTemplate?.id === template.id;
                  const imgSrc = template.templateJson?.image?.src as string | undefined;
                  return (
                  <button
                    key={template.id}
                    type="button"
                    className={`uw-runocr-template-card${isSelected ? " uw-runocr-template-card-active" : ""}`}
                    onClick={() => {
                      setSelectedTemplate(template);
                      setMode(template.mode === "unstructured" ? "unstructured" : "template");
                    }}
                    title={template.name}
                    onMouseEnter={(e) => {
                      if (!imgSrc) return;
                      const rect = e.currentTarget.getBoundingClientRect();
                      setTooltip({ imgSrc, x: rect.left + rect.width / 2, y: rect.bottom + 10 });
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  >
                    {template.mode === "unstructured" ? (
                      <span className="uw-runocr-template-card-preview">
                        <img
                          src="/images/unstructured-template-preview.svg"
                          alt=""
                          className="uw-template-card-img"
                        />
                      </span>
                    ) : imgSrc ? (
                      <span className="uw-runocr-template-card-preview">
                        <img
                          src={imgSrc}
                          alt=""
                          className="uw-template-card-img"
                          style={{ objectFit: "cover" }}
                        />
                      </span>
                    ) : (
                      <span className="uw-runocr-template-card-preview" />
                    )}
                    <span className="uw-runocr-template-card-name">{template.name}</span>
                  </button>
                  );
                })}
              </div>
            ) : (
              <>
                <span style={{ fontWeight: 700, color: "var(--accent)", flexShrink: 0 }}>저장된 템플릿</span>
                <span style={{ fontSize: 11, opacity: 0.7 }}>아직 저장된 템플릿이 없습니다.</span>
              </>
            )}
          </div>
        </div>

        {/* 모드 콘텐츠 */}
        <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
          {mode === "template" ? (
            <OcrAnnotator
              key={selectedTemplate && selectedTemplate.mode !== "unstructured" ? `tpl-${selectedTemplate.id}` : `new-${resetKey}`}
              selectedTemplate={selectedTemplate?.mode === "unstructured" ? null : selectedTemplate?.templateJson}
              selectedTemplateId={selectedTemplate?.mode === "unstructured" ? null : selectedTemplate?.id ?? null}
            />
          ) : (
            <UnstructuredBuilder
              key={selectedTemplate && selectedTemplate.mode === "unstructured" ? `tpl-${selectedTemplate.id}` : `new-${resetKey}`}
              selectedTemplate={selectedTemplate?.mode === "unstructured" ? selectedTemplate?.templateJson : null}
              selectedTemplateId={selectedTemplate?.mode === "unstructured" ? selectedTemplate?.id ?? null : null}
            />
          )}
        </div>
      </div>
      {tooltip && (
        <div
          className="template-hover-tooltip"
          style={{
            position: "fixed",
            top: tooltip.y,
            left: Math.min(
              Math.max(tooltip.x - 160, 8),
              (typeof window !== "undefined" ? window.innerWidth : 1200) - 328,
            ),
            zIndex: 9999,
            borderRadius: 8,
            overflow: "hidden",
            boxShadow: "0 4px 20px rgba(0,0,0,0.35)",
            pointerEvents: "none",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={tooltip.imgSrc}
            alt=""
            style={{ width: 320, height: "auto", display: "block", borderRadius: 6 }}
          />
        </div>
      )}
    </AppShell>
  );
}
