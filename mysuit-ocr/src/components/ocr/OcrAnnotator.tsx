"use client";

import React, { useMemo, useRef, useState } from "react";
import type { FieldType, LoadedImage, Region } from "./core/types";
import { buildExportPayload } from "./core/export";
import OcrCanvasPane from "./OcrCanvasPane";
import OcrRightPanel from "./OcrRightPanel";

export default function OcrAnnotator() {
  const imgRef = useRef<HTMLImageElement | null>(null);

  const DEFAULT_ZOOM_PCT = 100;

  const [templateName, setTemplateName] = useState<string>("");
  const [loaded, setLoaded] = useState<LoadedImage | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [zoomPct, setZoomPct] = useState<number>(DEFAULT_ZOOM_PCT);
  const [drawMode, setDrawMode] = useState<FieldType | null>(null);
  const [rowTemplateTargetId, setRowTemplateTargetId] = useState<string | null>(null);
  const [colGuideTargetId, setColGuideTargetId] = useState<string | null>(null);

  function updateName(id: string, name: string) {
    setRegions((prev) => prev.map((r) => (r.id === id ? { ...r, name } : r)));
  }

  function deleteRegion(id: string) {
    setRegions((prev) => prev.filter((r) => r.id !== id));
    setSelectedId((cur) => (cur === id ? null : cur));
  }

  const exportPayload = useMemo(
    () => buildExportPayload({ templateName, loaded, regions }),
    [loaded, regions, templateName],
  );

  async function onPickFile(file: File) {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      setLoaded({
        src: url,
        fileName: file.name,
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
      });
      setRegions([]);
      setSelectedId(null);
      setDrawMode(null);
      setZoomPct(DEFAULT_ZOOM_PCT);
      setRowTemplateTargetId(null);
      setColGuideTargetId(null);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      alert("이미지 로딩에 실패했습니다.");
    };
    img.src = url;
  }

  function toggleMode(m: FieldType) {
    setDrawMode((cur) => (cur === m ? null : m));
  }

  async function copyJson() {
    const txt = JSON.stringify(exportPayload, null, 2);
    try {
      await navigator.clipboard.writeText(txt);
      alert("JSON이 클립보드에 복사되었습니다.");
    } catch {
      prompt("복사가 실패했습니다. 아래 텍스트를 복사하세요.", txt);
    }
  }

  function saveTemplateJson() {
    const txt = JSON.stringify(exportPayload, null, 2);
    const safeBase = (templateName || "template")
      .trim()
      .replace(/[\\/:*?"<>|]+/g, "-")
      .slice(0, 80);

    const blob = new Blob([txt], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${safeBase}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) 320px",
        gridTemplateRows: "auto 1fr",
        gap: 12,
        width: "100%",
        height: "100%",
        minHeight: 0,
        minWidth: 0,
      }}
    >
      {/* Toolbar */}
      <div className="oc-toolbar" style={{ gridColumn: "1 / -1", gridRow: 1 }}>
        <label className="oc-mode-btn" style={{ cursor: "pointer" }}>
          문서 선택
          <input
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void onPickFile(f);
            }}
          />
        </label>

        {(["field", "multi", "check", "table"] as FieldType[]).map((m) => {
          const labels: Record<FieldType, string> = {
            field: "필드",
            multi: "멀티필드",
            check: "체크필드",
            table: "테이블필드",
          };
          return (
            <button
              key={m}
              type="button"
              onClick={() => toggleMode(m)}
              className={`oc-mode-btn${drawMode === m ? " oc-mode-btn-active" : ""}`}
              disabled={!loaded}
            >
              {labels[m]}
            </button>
          );
        })}

        <div className="oc-zoom-group">
          <span className="oc-zoom-label">줌</span>
          <input
            type="range"
            min={10}
            max={200}
            value={zoomPct}
            onChange={(e) => setZoomPct(Number(e.target.value))}
          />
          <span className="oc-zoom-val">{zoomPct}%</span>
          <button
            type="button"
            onClick={() => setZoomPct(DEFAULT_ZOOM_PCT)}
            className="ms-btn-sm"
            disabled={!loaded}
          >
            초기화
          </button>
        </div>

        <div className="oc-toolbar-right">
          <button
            type="button"
            onClick={() => void copyJson()}
            className="ms-btn"
            disabled={!loaded}
          >
            JSON 복사
          </button>
          <button
            type="button"
            onClick={() => void saveTemplateJson()}
            className="ms-btn"
            disabled={!loaded}
          >
            템플릿 저장
          </button>
        </div>
      </div>

      {/* Left: canvas */}
      <div style={{ gridColumn: 1, gridRow: 2, minHeight: 0 }}>
        <OcrCanvasPane
          imgRef={imgRef}
          loaded={loaded}
          regions={regions}
          setRegions={setRegions}
          selectedId={selectedId}
          setSelectedId={setSelectedId}
          rowTemplateTargetId={rowTemplateTargetId}
          setRowTemplateTargetId={setRowTemplateTargetId}
          colGuideTargetId={colGuideTargetId}
          setColGuideTargetId={setColGuideTargetId}
          drawMode={drawMode}
          setDrawMode={setDrawMode}
          zoomPct={zoomPct}
        />
      </div>

      {/* Right: panel */}
      <div style={{ gridColumn: 2, gridRow: 2, minHeight: 0 }}>
        <OcrRightPanel
          imgRef={imgRef}
          templateName={templateName}
          setTemplateName={setTemplateName}
          loaded={loaded}
          regions={regions}
          setRegions={setRegions}
          selectedId={selectedId}
          setSelectedId={setSelectedId}
          rowTemplateTargetId={rowTemplateTargetId}
          setRowTemplateTargetId={setRowTemplateTargetId}
          colGuideTargetId={colGuideTargetId}
          setColGuideTargetId={setColGuideTargetId}
          updateName={updateName}
          deleteRegion={deleteRegion}
        />
      </div>
    </div>
  );
}
