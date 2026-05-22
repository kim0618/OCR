/**
 * 문서 코너 보정 UI.
 *
 * 역할:
 * - 이미지 위에서 사용자가 4개의 모서리(TL/TR/BR/BL) 를 클릭/드래그로
 *   지정해 transform 입력을 만든다.
 * - 좌표는 0~1 normalized space 로 외부에 노출한다 (onCornersChange).
 *
 * Boundary:
 * - OCR API 호출 / 결과 매핑 / 히스토리 책임 없음.
 * - 이미지 표시 자체는 자기 책임이지만, 보정 결과(corners)는 부모가 어떻게
 *   사용할지 결정한다.
 *
 * 좌표 주의:
 * - 외부 API 는 normalized(0~1), 내부 렌더는 px. toPixel / toNorm 으로 양방향
 *   변환하며 렌더 사이즈는 ResizeObserver 로 imgSize 에 동기화한다.
 * - 4개 미만이면 click-to-place 모드(placing), 4개가 되면 드래그 보정 모드.
 */
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";

export type Corner = { x: number; y: number }; // 0~1 normalized

type Props = {
  imageUrl: string;
  corners: Corner[]; // [TL, TR, BR, BL]
  onCornersChange: (corners: Corner[]) => void;
};

const HANDLE_R = 14;
const LABELS = ["1", "2", "3", "4"];
const LABEL_NAMES = ["좌상", "우상", "우하", "좌하"];

/**
 * CornerAdjust 컴포넌트. `corners` 길이가 4 미만이면 클릭으로 좌표를 추가하고,
 * 4개를 채우면 핸들 드래그로만 위치를 조정한다. 매 변경은 `onCornersChange`
 * 콜백으로 정규화된 좌표(0~1) 배열을 전체 통보한다.
 */
export default function CornerAdjust({ imageUrl, corners, onCornersChange }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [dragging, setDragging] = useState<number | null>(null);
  const [imgSize, setImgSize] = useState<{ w: number; h: number } | null>(null);
  // click-to-place 모드: corners가 4개 미만이면 클릭으로 추가
  const placing = corners.length < 4;

  useEffect(() => {
    const el = imgRef.current;
    if (!el) return;
    const measure = () => setImgSize({ w: el.offsetWidth, h: el.offsetHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [imageUrl]);

  const toPixel = (c: Corner) =>
    imgSize ? { x: c.x * imgSize.w, y: c.y * imgSize.h } : { x: 0, y: 0 };

  const toNorm = (px: { x: number; y: number }): Corner =>
    imgSize
      ? { x: Math.min(1, Math.max(0, px.x / imgSize.w)), y: Math.min(1, Math.max(0, px.y / imgSize.h)) }
      : { x: 0, y: 0 };

  // 이미지 클릭 → 코너 추가
  const onImgClick = useCallback((e: React.MouseEvent) => {
    if (!placing || !imgRef.current) return;
    const rect = imgRef.current.getBoundingClientRect();
    const px = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    const updated = [...corners, toNorm(px)];
    onCornersChange(updated);
  }, [placing, corners, imgSize, onCornersChange]);

  // 핸들 드래그
  const onPointerDown = useCallback((e: React.PointerEvent, idx: number) => {
    if (placing) return;
    e.preventDefault();
    e.stopPropagation();
    (e.target as Element).setPointerCapture(e.pointerId);
    setDragging(idx);
  }, [placing]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (dragging === null || !imgRef.current || !imgSize) return;
    const rect = imgRef.current.getBoundingClientRect();
    const px = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    const updated = [...corners];
    updated[dragging] = toNorm(px);
    onCornersChange(updated);
  }, [dragging, corners, imgSize, onCornersChange]);

  const onPointerUp = useCallback(() => setDragging(null), []);

  const pts = corners.map(toPixel);
  const poly = pts.map((p) => `${p.x},${p.y}`).join(" ");

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", userSelect: "none", display: "flex", flexDirection: "column", alignItems: "center" }}>
      {/* 안내 메시지 */}
      <div style={{
        position: "absolute", top: 8, left: "50%", transform: "translateX(-50%)",
        zIndex: 10, background: "rgba(0,0,0,0.65)", color: "white",
        borderRadius: 8, padding: "6px 14px", fontSize: 13, whiteSpace: "nowrap",
        pointerEvents: "none",
      }}>
        {placing
          ? `${corners.length + 1}번째 코너를 클릭 — ${LABEL_NAMES[corners.length]} (${corners.length}/4)`
          : "핸들을 드래그해서 코너를 조정하세요"}
      </div>

      <div
        ref={containerRef}
        style={{ position: "relative", display: "inline-block", maxWidth: "100%", maxHeight: "100%" }}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        <img
          ref={imgRef}
          src={imageUrl}
          alt="adjust"
          style={{
            maxWidth: "100%",
            maxHeight: "calc(100vh - 280px)",
            width: "auto",
            height: "auto",
            display: "block",
            borderRadius: 8,
            objectFit: "contain",
            cursor: placing ? "crosshair" : "default",
            boxShadow: "0 2px 16px rgba(0,0,0,0.12)",
          }}
          onClick={onImgClick}
        />

        {imgSize && corners.length > 0 && (
          <svg
            style={{ position: "absolute", top: 0, left: 0, width: imgSize.w, height: imgSize.h, overflow: "visible", pointerEvents: placing ? "none" : "auto" }}
            viewBox={`0 0 ${imgSize.w} ${imgSize.h}`}
          >
            {/* 연결선 */}
            {pts.map((p, i) => {
              const next = pts[(i + 1) % pts.length];
              if (i >= corners.length - 1 && placing) return null;
              return (
                <line key={i} x1={p.x} y1={p.y} x2={next.x} y2={next.y}
                  stroke="#0891b2" strokeWidth="2" strokeDasharray="6 3" />
              );
            })}

            {/* 완성된 폴리곤 채우기 */}
            {!placing && corners.length === 4 && (
              <polygon points={poly} fill="rgba(8,145,178,0.10)" stroke="#0891b2" strokeWidth="2" strokeDasharray="6 3" />
            )}

            {/* 핸들 */}
            {pts.map((p, i) => (
              <g key={i}
                onPointerDown={(e) => onPointerDown(e, i)}
                style={{ cursor: placing ? "default" : "grab" }}
              >
                <circle cx={p.x} cy={p.y} r={HANDLE_R + 6} fill="transparent" />
                <circle
                  cx={p.x} cy={p.y} r={HANDLE_R}
                  fill={dragging === i ? "#0891b2" : "white"}
                  stroke="#0891b2" strokeWidth="2.5"
                />
                <text x={p.x} y={p.y + 5} textAnchor="middle" fontSize="12"
                  fontWeight="700" fill={dragging === i ? "white" : "#0891b2"}
                  style={{ pointerEvents: "none" }}
                >
                  {LABELS[i]}
                </text>
              </g>
            ))}
          </svg>
        )}
      </div>

      {/* 초기화 버튼 */}
      {corners.length > 0 && (
        <button
          type="button"
          onClick={() => onCornersChange([])}
          style={{
            position: "absolute", bottom: 10, right: 10, zIndex: 10,
            background: "rgba(0,0,0,0.55)", color: "white",
            border: "none", borderRadius: 6, padding: "4px 10px",
            fontSize: 12, cursor: "pointer",
          }}
        >
          다시 찍기
        </button>
      )}
    </div>
  );
}
