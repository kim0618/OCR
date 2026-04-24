import type { Rect, Region } from "./types";

/**
 * (전환 대비용) 원본 이미지 좌표(px) 기준으로 hit test를 수행해
 * - 어떤 영역을 눌렀는지
 * - 리사이즈 핸들(코너/변)인지
 * 를 판별하는 모듈.
 *
 * 현재 DOM 구현은 CanvasPane 내부 로직을 그대로 사용하며,
 * Konva 전환 시 이 모듈로 통일하는 것을 권장합니다.
 */
export type HitHandle =
  | "move"
  | "n" | "s" | "e" | "w"
  | "nw" | "ne" | "sw" | "se";

export type HitResult =
  | { type: "none" }
  | { type: "region"; id: string; handle: HitHandle };

export function hitTest(_pt: { x: number; y: number }, _regions: Region[], _handleSizePx = 6): HitResult {
  return { type: "none" };
}
