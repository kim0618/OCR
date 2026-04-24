import type { CSSProperties } from "react";
import type { Rect, Region } from "./types";

export function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}


export function normalizeRect(x: number, y: number, w: number, h: number) {
  const nx = w < 0 ? x + w : x;
  const ny = h < 0 ? y + h : y;
  return { x: nx, y: ny, width: Math.abs(w), height: Math.abs(h) };
}


export function uid(prefix = "r") {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
}


export function parseIndex(name: string, prefix: string) {
  const m = new RegExp(`^${prefix}_(\\d+)$`).exec(name.trim());
  return m ? Number(m[1]) : null;
}


export function normalizeRatios(parts: 2 | 3, ratios?: number[]) {
  const n = parts;
  let arr = Array.isArray(ratios) ? ratios.slice(0, n) : [];
  if (arr.length !== n) arr = Array.from({ length: n }, () => 1 / n);

  arr = arr.map((v) => (Number.isFinite(v) ? Math.max(0.0001, v) : 0.0001));
  const sum = arr.reduce((a, b) => a + b, 0);
  if (sum <= 0) return Array.from({ length: n }, () => 1 / n);
  return arr.map((v) => v / sum);
}


export function boxLabelStyle(wPx: number, hPx: number): CSSProperties {
  if (wPx < 28 || hPx < 18) return { display: "none" };

  const minSide = Math.min(wPx, hPx);
  const fontSize = clamp(Math.round(minSide * 0.22), 9, 13);
  const padY = clamp(Math.round(fontSize * 0.25), 1, 4);
  const padX = clamp(Math.round(fontSize * 0.55), 3, 8);

  return {
    fontSize,
    padding: `${padY}px ${padX}px`,
    borderRadius: 999,
    background: "rgba(0,0,0,0.55)",
    color: "#fff",
    pointerEvents: "none",
    maxWidth: Math.max(0, wPx - 12),
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    lineHeight: 1.1,
  };
}


export function calcMultiSubRegions(r: Region) {
  const parts = (r.parts ?? 2) as 2 | 3;
  const ratios = normalizeRatios(parts, r.ratios);

  const sub: Array<{ index: number; x: number; y: number; width: number; height: number }> = [];
  let acc = 0;
  for (let i = 0; i < parts; i++) {
    const startX = r.x + r.width * acc;
    const wRaw = i === parts - 1 ? r.width * (1 - acc) : r.width * ratios[i];
    sub.push({
      index: i,
      x: Math.round(startX),
      y: Math.round(r.y),
      width: Math.round(wRaw),
      height: Math.round(r.height),
    });
    acc += ratios[i];
  }
  return sub;
}


export function clampRectToArea(rect: Rect, area: Rect): Rect {
  const ax2 = area.x + area.width;
  const ay2 = area.y + area.height;

  const x = clamp(rect.x, area.x, Math.max(area.x, ax2 - 1));
  const y = clamp(rect.y, area.y, Math.max(area.y, ay2 - 1));

  const maxW = Math.max(1, ax2 - x);
  const maxH = Math.max(1, ay2 - y);

  const width = clamp(rect.width, 1, maxW);
  const height = clamp(rect.height, 1, maxH);

  return { x, y, width, height };
}
