import type { Rect, TableRowOverride } from "./types";
import { clampRectToArea } from "./ops";

/**
 * TPL-12A: 행 개별 조정의 최소 row 높이 (px). OcrCanvasPane drag handler 의
 * minSize 와 일치. 잘못된 override 로 인한 degenerate row 방지용.
 */
export const MIN_ROW_HEIGHT = 4;

function isFiniteNumber(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function cloneRect(r: Rect): Rect {
  return { x: r.x, y: r.y, width: r.width, height: r.height };
}

/**
 * TPL-12A: sparse per-row overrides 를 baseRows 에 적용하고, 이후 행들의 y 를
 * 재캐스케이드한다. area 안으로 clamp 하고, 더 이상 안 들어가는 trailing row 는 trim.
 *
 * Pure: baseRows/rowOverrides/area 어느 것도 변형하지 않고, 항상 fresh 배열 반환.
 *
 * Policy:
 *  - rowOverrides 없으면 baseRows clone.
 *  - 각 override 는 rowIndex 키. 잘못된 항목은 무시:
 *      * rowIndex 유한 정수 아님
 *      * rowIndex < 0 OR >= baseRows.length
 *      * height 가 MIN_ROW_HEIGHT 미만
 *      * y 가 유한수 아님 (height-only override 는 여전히 적용 가능)
 *  - override.y 유효시 그 위치에 배치 + 이후 행은 y + height 부터 cascade.
 *  - override.height 만 있으면 base.y 유지, 이후 행은 새 height 기준 cascade.
 *  - locked 는 materialize 시 무시 (UI 잠금용 reserved).
 *  - 전체 결과는 area 안으로 clamp. area bottom 초과시 height clamp 또는 trim.
 */
export function materializeTableRowsWithOverrides(
  baseRows: ReadonlyArray<Rect>,
  rowOverrides: ReadonlyArray<TableRowOverride> | undefined,
  area: Rect,
): Rect[] {
  if (!Array.isArray(baseRows) || baseRows.length === 0) return [];

  const indexed = new Map<number, TableRowOverride>();
  if (Array.isArray(rowOverrides)) {
    for (const ov of rowOverrides) {
      if (!ov || typeof ov !== "object") continue;
      const ri = (ov as TableRowOverride).rowIndex;
      if (!isFiniteNumber(ri) || !Number.isInteger(ri)) continue;
      if (ri < 0 || ri >= baseRows.length) continue;
      indexed.set(ri, ov as TableRowOverride);
    }
  }

  const out: Rect[] = [];
  let cursorY: number | null = null;
  for (let i = 0; i < baseRows.length; i++) {
    const base = baseRows[i];
    if (!base) continue;
    const ov = indexed.get(i);

    let height = base.height;
    if (ov && isFiniteNumber(ov.height) && ov.height >= MIN_ROW_HEIGHT) {
      height = ov.height;
    }

    let y: number;
    if (ov && isFiniteNumber(ov.y)) {
      y = ov.y;
    } else if (cursorY !== null) {
      y = cursorY;
    } else {
      y = base.y;
    }

    out.push({ x: base.x, y, width: base.width, height });
    cursorY = y + height;
  }

  const result: Rect[] = [];
  const areaTop = area.y;
  const areaBottom = area.y + area.height;
  for (const r of out) {
    const xyClamped = clampRectToArea(cloneRect(r), area);
    if (r.y >= areaBottom) continue;
    const y = Math.max(r.y, areaTop);
    let height = r.height;
    if (y + height > areaBottom) height = areaBottom - y;
    if (height < MIN_ROW_HEIGHT) continue;
    result.push({ x: xyClamped.x, y, width: xyClamped.width, height });
  }
  return result;
}

/** OCR 엔진에서 내려주는 텍스트 박스(표 영역 내) */
export type OcrBox = {
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
};

export function normalizeColGuides(guides?: number[]): number[] {
  if (!Array.isArray(guides) || guides.length === 0) return [];
  // 0~1 사이만, 양 끝(0/1)은 제외
  const filtered = guides
    .map((v) => (Number.isFinite(v) ? v : NaN))
    .filter((v) => Number.isFinite(v))
    .filter((v) => v > 0 && v < 1)
    .sort((a, b) => a - b);

  // 근접 중복 제거(드래그/클릭 반복 시)
  const eps = 0.002;
  const out: number[] = [];
  for (const v of filtered) {
    if (out.length === 0) out.push(v);
    else if (Math.abs(out[out.length - 1] - v) > eps) out.push(v);
  }

  // 과도하게 많은 가이드 방지(실사용 상한)
  return out.slice(0, 40);
}

export function buildTableRows(area: Rect, rowTemplate: Rect): Rect[] {
  const rt = clampRectToArea(rowTemplate, area);
  const rows: Rect[] = [];
  const endY = area.y + area.height;
  if (rt.height <= 0 || rt.width <= 0) return rows;

  let y = rt.y;
  let idx = 0;
  while (y + rt.height <= endY) {
    rows.push({ x: rt.x, y, width: rt.width, height: rt.height });
    idx++;
    // safety: 무한루프 방지
    if (idx > 5000) break;
    y += rt.height;
  }
  return rows;
}

/** stopKeywords 정규화(빈값 제거/중복 제거) */
export function normalizeStopKeywords(list?: string[]): string[] {
  if (!Array.isArray(list)) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const raw of list) {
    const s = String(raw ?? "").trim();
    if (!s) continue;
    const key = s.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(s);
  }
  return out.slice(0, 30);
}

/**
 * A안(완성형)용: 표 영역 내 OCR 박스를 y축 기준으로 군집화하여 "행"을 자동 감지합니다.
 * - 행 높이가 제각각이어도 텍스트 박스 분포로 행을 만들 수 있음
 * - 실제 OCR 단계에서 사용(템플릿 편집기에서는 미리보기 용도로도 사용 가능)
 */
export function autoDetectRowBands(params: {
  tableArea: Rect;
  boxes: OcrBox[];
  /** 같은 행으로 묶을 y 간격(px). 문서에 따라 6~14 정도가 무난 */
  yMergeGap?: number;
  /** 너무 작은 잡음 박스 제거용 */
  minBoxHeight?: number;
}): Rect[] {
  const { tableArea, boxes } = params;
  const yMergeGap = params.yMergeGap ?? 10;
  const minBoxHeight = params.minBoxHeight ?? 6;

  // 1) 테이블 영역 안의 박스만 사용
  const inArea = boxes
    .filter((b) => b.height >= minBoxHeight)
    .filter((b) => {
      const bx0 = b.x;
      const by0 = b.y;
      const bx1 = b.x + b.width;
      const by1 = b.y + b.height;
      const ax0 = tableArea.x;
      const ay0 = tableArea.y;
      const ax1 = tableArea.x + tableArea.width;
      const ay1 = tableArea.y + tableArea.height;
      // 박스가 표 영역과 조금이라도 겹치면 포함
      return bx1 > ax0 && bx0 < ax1 && by1 > ay0 && by0 < ay1;
    })
    .map((b) => ({ ...b, cy: b.y + b.height / 2 }));

  if (inArea.length === 0) return [];
  inArea.sort((a, b) => a.cy - b.cy);

  // 2) y 기준으로 행 밴드 생성
  const bands: { y0: number; y1: number; count: number }[] = [];
  for (const b of inArea) {
    const top = b.y;
    const bottom = b.y + b.height;
    const last = bands[bands.length - 1];
    if (!last) {
      bands.push({ y0: top, y1: bottom, count: 1 });
      continue;
    }
    // 마지막 밴드와 중심선 기준으로 가까우면 병합
    if (top <= last.y1 + yMergeGap) {
      last.y0 = Math.min(last.y0, top);
      last.y1 = Math.max(last.y1, bottom);
      last.count += 1;
    } else {
      bands.push({ y0: top, y1: bottom, count: 1 });
    }
  }

  // 3) Rect로 변환(폭은 tableArea 전체)
  return bands.map((b) => {
    const r: Rect = {
      x: tableArea.x,
      y: b.y0,
      width: tableArea.width,
      height: Math.max(1, b.y1 - b.y0),
    };
    return clampRectToArea(r, tableArea);
  });
}

/**
 * 종료 키워드가 포함된 행인지 판정 (표 footer: 전체 합계/합계/총액 등)
 * - OCR 텍스트 특성상 공백/특수문자 차이가 있을 수 있어, 단순 contains로 시작
 */
export function isStopRow(params: { rowText: string; stopKeywords: string[] }) {
  const { rowText } = params;
  const stop = normalizeStopKeywords(params.stopKeywords);
  const t = (rowText ?? "").replace(/\s+/g, " ").trim();
  if (!t) return false;
  for (const k of stop) {
    if (!k) continue;
    if (t.includes(k)) return true;
  }
  return false;
}
