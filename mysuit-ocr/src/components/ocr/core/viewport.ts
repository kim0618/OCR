import type { Rect } from "./types";
import { clamp } from "./ops";

export type ViewportTransform = {
  /** 화면에 표시되는 이미지의 좌상단 위치 (viewport 기준) */
  left: number;
  top: number;
  /** DOM 상에서의 표시 스케일: screenPx = imagePx * scale */
  scale: number;
  /** 원본 이미지 크기 */
  imageWidth: number;
  imageHeight: number;
};

/** client 좌표(브라우저) → 원본 이미지 좌표(px) */
export function screenPointToImage(
  clientX: number,
  clientY: number,
  imageBoundingClientRect: DOMRect,
  scale: number,
  imageWidth: number,
  imageHeight: number
) {
  const x = (clientX - imageBoundingClientRect.left) / scale;
  const y = (clientY - imageBoundingClientRect.top) / scale;
  return { x: clamp(x, 0, imageWidth), y: clamp(y, 0, imageHeight) };
}

/** 원본 이미지 Rect(px) → 화면 Rect(px) */
export function imageRectToScreen(r: Rect, imageBoundingClientRect: DOMRect, scale: number): Rect {
  return {
    x: (r.x * scale) + 0,
    y: (r.y * scale) + 0,
    width: r.width * scale,
    height: r.height * scale,
  };
}

/** 화면 Rect(px, 이미지 기준) → 원본 이미지 Rect(px) */
export function screenRectToImage(r: Rect, scale: number): Rect {
  return {
    x: r.x / scale,
    y: r.y / scale,
    width: r.width / scale,
    height: r.height / scale,
  };
}
