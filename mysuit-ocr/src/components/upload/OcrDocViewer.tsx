"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import type { OcrFieldResult } from "./OcrResultPanel";

type Props = {
  imageUrl: string;
  fields: OcrFieldResult[];
  selectedIndex: number | null;
  onSelectField: (index: number) => void;
};

export default function OcrDocViewer({ imageUrl, fields, selectedIndex, onSelectField }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [scale, setScale] = useState<{ x: number; y: number } | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

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
    <div className="odv-root">
      <div className="odv-img-wrap" ref={wrapRef}>
        <img ref={imgRef} src={imageUrl} alt="document" className="odv-img" />
        {scale && fields.map((field, i) => {
          const [x, y, w, h] = field.bbox;
          const isSelected = selectedIndex === i;

          return (
            <div
              key={i}
              data-box-idx={i}
              style={{
                position: "absolute",
                left: x * scale.x - (isSelected ? 4 : 1),
                top: y * scale.y - (isSelected ? 4 : 1),
                width: w * scale.x + (isSelected ? 8 : 2),
                height: h * scale.y + (isSelected ? 8 : 2),
                cursor: "pointer",
                border: isSelected ? "3px solid #0891b2" : "1px solid rgba(8,145,178,0.35)",
                borderRadius: isSelected ? 4 : 2,
                background: isSelected ? "rgba(8,145,178,0.15)" : "rgba(8,145,178,0.05)",
                boxShadow: isSelected ? "0 0 12px rgba(8,145,178,0.5)" : "none",
                zIndex: isSelected ? 10 : 1,
                transition: "all 0.15s",
              }}
              onClick={() => onSelectField(i)}
            />
          );
        })}
      </div>
    </div>
  );
}
