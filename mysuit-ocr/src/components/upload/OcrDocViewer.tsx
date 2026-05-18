"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import type { OcrFieldResult } from "./OcrResultPanel";
import { resolveFieldLabel } from "@/lib/invoiceFieldLabels";

type Props = {
  imageUrl: string;
  fields: OcrFieldResult[];
  selectedIndex: number | null;
  onSelectField: (index: number) => void;
  enableFieldOverlay?: boolean;
  /** Original image dimensions in the coordinate space of field bboxes.
   *  When provided (template mode), corrects scale mismatch between the
   *  backend 200-DPI render (bbox space) and the frontend display render. */
  originalWidth?: number;
  originalHeight?: number;
};

export default function OcrDocViewer({
  imageUrl,
  fields,
  selectedIndex,
  onSelectField,
  enableFieldOverlay = true,
  originalWidth,
  originalHeight,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [scale, setScale] = useState<{ x: number; y: number } | null>(null);
  const [showFieldOverlay, setShowFieldOverlay] = useState(true);

  // Estimate image natural dimensions from first rendered image for large-region detection
  const [imgNatural, setImgNatural] = useState<{ w: number; h: number } | null>(null);

  const overlayBoxes = fields
    .flatMap((field, fieldIndex) => {
      const boxes = field.sourceBboxes?.length
        ? field.sourceBboxes
        : field.bbox?.length >= 4 && field.bbox[2] > 0 && field.bbox[3] > 0
          ? [{ x: field.bbox[0], y: field.bbox[1], width: field.bbox[2], height: field.bbox[3] }]
          : [];

      return boxes.map((box, boxIndex) => {
        const adoption = field.overlayAdoption ?? "unknown";
        const { primary, secondary } = resolveFieldLabel({ name: field.name, ko: field.ko, en: field.en });
        const fieldName = primary;
        const isTableType = field.field_type === "table";
        const isLargeRegion = imgNatural
          ? (box.height > imgNatural.h * 0.2 || box.width > imgNatural.w * 0.8)
          : false;
        const scaleX = imgNatural ? (imgNatural.w > 0 ? 1 : 1) : 1; // scale factors from updateScale
        const renderedX = scale ? Math.round(box.x * scale.x) : box.x;
        const renderedY = scale ? Math.round(box.y * scale.y) : box.y;
        const renderedW = scale ? Math.round(box.width * scale.x) : box.width;
        const renderedH = scale ? Math.round(box.height * scale.y) : box.height;
        const tooltipLines = [
          `${fieldIndex + 1}. ${fieldName}`,
          secondary && secondary !== fieldName ? `key: ${secondary}` : "",
          `raw: ${field.name}`,
          `source: ${adoption}`,
          `original bbox: ${box.x},${box.y}, ${box.width}×${box.height}`,
          scale ? `rendered: ${renderedX},${renderedY}, ${renderedW}×${renderedH}` : "",
          (originalWidth && imgNatural)
            ? `scale: x${(imgNatural.w / (originalWidth || imgNatural.w)).toFixed(3)}` : "",
          field.confidence > 0 ? `신뢰도: ${(field.confidence * 100).toFixed(1)}%` : "",
          isLargeRegion ? "⚠ 큰 영역 (원본 기준)" : "",
        ].filter(Boolean).join("\n");
        return {
          adoption,
          area: Math.max(0, box.width * box.height),
          box,
          boxIndex,
          fieldIndex,
          fieldName,
          secondary,
          isTableType,
          isLargeRegion,
          rowNo: fieldIndex + 1,
          title: tooltipLines,
        };
      });
    })
    .sort((a, b) => b.area - a.area);

  const updateScale = useCallback(() => {
    const img = imgRef.current;
    if (!img || img.naturalWidth === 0) return;
    // Use originalWidth/Height (bbox coordinate space) if provided.
    // Falls back to img.naturalWidth/Height (displayed image space) when not set.
    const bboxW = (originalWidth && originalWidth > 0) ? originalWidth : img.naturalWidth;
    const bboxH = (originalHeight && originalHeight > 0) ? originalHeight : img.naturalHeight;
    setScale({
      x: img.offsetWidth / bboxW,
      y: img.offsetHeight / bboxH,
    });
    setImgNatural({ w: bboxW, h: bboxH });
  }, [originalWidth, originalHeight]);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;
    img.addEventListener("load", updateScale);
    updateScale();
    const ro = new ResizeObserver(updateScale);
    ro.observe(img);
    return () => {
      img.removeEventListener("load", updateScale);
      ro.disconnect();
    };
  }, [imageUrl, updateScale]);

  return (
    <div className="odv-root" style={{ position: "relative" }}>
      {enableFieldOverlay && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 8,
            padding: "5px 10px",
            borderBottom: "1px solid rgba(148,163,184,0.16)",
            background: "rgba(15,23,42,0.72)",
            color: "#e5e7eb",
            fontSize: 11,
            fontWeight: 800,
            flexShrink: 0,
          }}
        >
          <label style={{ display: "inline-flex", alignItems: "center", gap: 5, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={showFieldOverlay}
              onChange={(event) => setShowFieldOverlay(event.target.checked)}
            />
            필드 영역 표시
          </label>
          <span style={{ color: "#22d3ee" }}>OCR</span>
          <span style={{ color: "#f59e0b" }}>복원</span>
          <span style={{ color: "#94a3b8" }}>제외</span>
          <span style={{ color: "#cbd5e1", fontWeight: 700 }}>번호는 오른쪽 No와 연결됩니다.</span>
        </div>
      )}
      <div className="odv-img-wrap" ref={wrapRef}>
        <img ref={imgRef} src={imageUrl} alt="document" className="odv-img" />
        {enableFieldOverlay &&
          showFieldOverlay &&
          scale &&
          overlayBoxes.map((item, renderIndex) => {
            const isSelected = selectedIndex === item.fieldIndex;
            const adoption = item.adoption;
            const color =
              adoption === "restored" ? "#f59e0b" : adoption === "excluded" ? "#94a3b8" : "#22d3ee";
            const background =
              adoption === "restored"
                ? "rgba(245,158,11,0.13)"
                : adoption === "excluded"
                  ? "rgba(148,163,184,0.10)"
                  : "rgba(34,211,238,0.10)";
            const left = Math.max(0, item.box.x * scale.x - (isSelected ? 4 : 1));
            const top = Math.max(0, item.box.y * scale.y - (isSelected ? 4 : 1));
            const width = Math.max(1, item.box.width * scale.x + (isSelected ? 8 : 2));
            const height = Math.max(1, item.box.height * scale.y + (isSelected ? 8 : 2));
            const badgeTop = top < 18 ? 2 : -10;
            const zIndex = 10 + renderIndex;
            return (
              <div
                key={`${item.fieldIndex}-${item.boxIndex}`}
                data-box-idx={item.fieldIndex}
                style={{
                  position: "absolute",
                  left,
                  top,
                  width,
                  height,
                  cursor: "pointer",
                  border: isSelected ? `3px solid ${color}` : `1.5px solid ${color}`,
                  borderRadius: isSelected ? 4 : 2,
                  background,
                  boxShadow: isSelected ? `0 0 12px ${color}` : "none",
                  zIndex,
                  transition: "all 0.15s",
                  pointerEvents: "none",
                  overflow: "visible",
                }}
              >
                {item.boxIndex === 0 && (
                  <span
                    style={{
                      position: "absolute",
                      left: 0,
                      top: badgeTop,
                      minWidth: 18,
                      height: 18,
                      padding: "0 6px",
                      border: "1px solid rgba(255,255,255,0.82)",
                      borderRadius: 9999,
                      background: color,
                      color: "#ffffff",
                      fontSize: 11,
                      fontWeight: 900,
                      whiteSpace: "nowrap",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 2px 10px rgba(0,0,0,0.62)",
                      textShadow: "0 1px 2px rgba(0,0,0,0.45)",
                      zIndex: zIndex + 200,
                      cursor: "help",
                    }}
                    title={item.title}
                  >
                    {item.rowNo}
                  </span>
                )}
              </div>
            );
          })}
      </div>
    </div>
  );
}
