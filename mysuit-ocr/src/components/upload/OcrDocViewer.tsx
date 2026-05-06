"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import type { OcrFieldResult } from "./OcrResultPanel";

type Props = {
  imageUrl: string;
  fields: OcrFieldResult[];
  selectedIndex: number | null;
  onSelectField: (index: number) => void;
  enableFieldOverlay?: boolean;
};

export default function OcrDocViewer({
  imageUrl,
  fields,
  selectedIndex,
  onSelectField,
  enableFieldOverlay = true,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [scale, setScale] = useState<{ x: number; y: number } | null>(null);
  const [showFieldOverlay, setShowFieldOverlay] = useState(true);

  const overlayBoxes = fields
    .flatMap((field, fieldIndex) => {
      const boxes = field.sourceBboxes?.length
        ? field.sourceBboxes
        : field.bbox?.length >= 4 && field.bbox[2] > 0 && field.bbox[3] > 0
          ? [{ x: field.bbox[0], y: field.bbox[1], width: field.bbox[2], height: field.bbox[3] }]
          : [];

      return boxes.map((box, boxIndex) => {
        const adoption = field.overlayAdoption ?? "unknown";
        const fieldName = field.ko || field.name || field.en || `필드 ${fieldIndex + 1}`;
        return {
          adoption,
          area: Math.max(0, box.width * box.height),
          box,
          boxIndex,
          fieldIndex,
          fieldName,
          rowNo: fieldIndex + 1,
          title: `${fieldIndex + 1} ${fieldName}${adoption === "restored" ? " · 복원" : ""}`,
        };
      });
    })
    .sort((a, b) => b.area - a.area);

  const updateScale = useCallback(() => {
    const img = imgRef.current;
    if (!img || img.naturalWidth === 0) return;
    setScale({
      x: img.offsetWidth / img.naturalWidth,
      y: img.offsetHeight / img.naturalHeight,
    });
  }, []);

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
            position: "absolute",
            top: 8,
            left: 8,
            zIndex: 5,
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 8,
            width: "fit-content",
            maxWidth: "calc(100% - 16px)",
            padding: "6px 8px",
            borderRadius: 6,
            border: "1px solid rgba(148,163,184,0.24)",
            background: "rgba(15,23,42,0.82)",
            color: "#e5e7eb",
            fontSize: 11,
            fontWeight: 800,
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
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 2px 10px rgba(0,0,0,0.62)",
                      textShadow: "0 1px 2px rgba(0,0,0,0.45)",
                      zIndex: zIndex + 200,
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
