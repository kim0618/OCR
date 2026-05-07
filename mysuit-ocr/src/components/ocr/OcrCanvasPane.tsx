"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import type {
  DragKind,
  FieldType,
  LoadedImage,
  Rect,
  Region,
} from "./core/types";
import {
  boxLabelStyle,
  clamp,
  clampRectToArea,
  normalizeRatios,
  normalizeRect,
  parseIndex,
  uid,
} from "./core/ops";
import { buildTableRows, normalizeColGuides } from "./core/table";

type Props = {
  // ✅ 여기 중요: RefObject 제네릭에 | null 넣지 마세요
  imgRef: React.RefObject<HTMLImageElement>;
  fileInputRef?: React.RefObject<HTMLInputElement | null>;

  loaded: LoadedImage | null;

  regions: Region[];
  setRegions: React.Dispatch<React.SetStateAction<Region[]>>;

  selectedId: string | null;
  setSelectedId: React.Dispatch<React.SetStateAction<string | null>>;

  /** table: 행 템플릿 지정 모드(선택된 table id) */
  rowTemplateTargetId: string | null;
  setRowTemplateTargetId: React.Dispatch<React.SetStateAction<string | null>>;

  /** table: 세로 가이드선(colGuides) 지정 모드(대상 table id) */
  colGuideTargetId: string | null;
  setColGuideTargetId: React.Dispatch<React.SetStateAction<string | null>>;

  // ✅ 상단 툴바는 부모(OcrAnnotator)로 이동
  drawMode: FieldType | null;
  setDrawMode: React.Dispatch<React.SetStateAction<FieldType | null>>;
  zoomPct: number;
  visibleRegionIds?: string[];
  emptySelectionHint?: string;
  drawTargetRegionId?: string | null;
  drawTargetName?: string;
  drawTargetFieldType?: FieldType;
  onClearSelection?: () => void;
};

export default function OcrCanvasPane(props: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = props.imgRef;
  const fileInputRef = props.fileInputRef;

  const {
    loaded,
    regions,
    setRegions,
    selectedId,
    setSelectedId,
    rowTemplateTargetId,
    setRowTemplateTargetId,
    colGuideTargetId,
    setColGuideTargetId,
    drawMode,
    setDrawMode,
    zoomPct,
    visibleRegionIds,
    emptySelectionHint,
    drawTargetRegionId,
    drawTargetName,
    drawTargetFieldType,
    onClearSelection,
  } = props;

  // ===== 상태 =====
  const [containerW, setContainerW] = useState<number>(900);

  const [drag, setDrag] = useState<DragKind>(null);
  const visibleRegionSet = useMemo(
    () => (visibleRegionIds ? new Set(visibleRegionIds) : null),
    [visibleRegionIds],
  );
  const visibleRegions = visibleRegionSet
    ? regions.filter((region) => visibleRegionSet.has(region.id))
    : regions;

  // ===== 최신 값 refs (rAF에서 stale 방지) =====
  const loadedRef = useRef<LoadedImage | null>(null);
  const regionsRef = useRef<Region[]>([]);
  const dragRef = useRef<DragKind>(null);

  useEffect(() => {
    loadedRef.current = loaded;
  }, [loaded]);

  useEffect(() => {
    regionsRef.current = regions;
  }, [regions]);

  function setDragBoth(d: DragKind) {
    dragRef.current = d;
    setDrag(d);
  }

  // ===== rAF throttle (포인터 move 성능 개선) =====
  const rafRef = useRef<number | null>(null);
  const pendingPointRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // ===== 직전 좌표/크기 저장(↩ 되돌리기) =====
  const lastRectRef = useRef<
    Record<
      string,
      { x: number; y: number; width: number; height: number } | null
    >
  >({});

  // ✅ 문서가 바뀌면 undo 스냅샷 초기화(이전 문서 좌표로 undo되면 안 됨)
  useEffect(() => {
    lastRectRef.current = {};
  }, [loaded?.src]);

  function snapshotRect(id: string) {
    const cur = regionsRef.current.find((r) => r.id === id);
    if (!cur) return;
    lastRectRef.current[id] = {
      x: cur.x,
      y: cur.y,
      width: cur.width,
      height: cur.height,
    };
  }

  function undoSelectedRect() {
    const l = loadedRef.current;
    if (!l || !selectedId) return;

    const cur = regionsRef.current.find((r) => r.id === selectedId);
    const prev = lastRectRef.current[selectedId];
    if (!cur || !prev) return;

    // swap(토글 가능)
    lastRectRef.current[selectedId] = {
      x: cur.x,
      y: cur.y,
      width: cur.width,
      height: cur.height,
    };

    setRegions((p) =>
      p.map((r) => {
        if (r.id !== selectedId) return r;

        const nx = clamp(prev.x, 0, l.naturalWidth - prev.width);
        const ny = clamp(prev.y, 0, l.naturalHeight - prev.height);
        const nw = clamp(prev.width, 4, l.naturalWidth - nx);
        const nh = clamp(prev.height, 4, l.naturalHeight - ny);

        // 체크필드는 정사각 유지
        if (r.fieldType === "check") {
          const size = clamp(
            Math.max(nw, nh),
            4,
            Math.min(l.naturalWidth - nx, l.naturalHeight - ny),
          );
          return { ...r, x: nx, y: ny, width: size, height: size };
        }

        return { ...r, x: nx, y: ny, width: nw, height: nh };
      }),
    );
  }

  // ===== ResizeObserver로 컨테이너 폭 추적 =====
  useEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (!cr) return;
      setContainerW(Math.max(320, Math.floor(cr.width)));
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  // ===== 렌더 스케일(표시용) =====
  // OcrDocViewer 와 동일하게 컨테이너 폭에 맞춰 채움 (자연 크기보다 컨테이너가 크면 업스케일).
  // 탭 간 좌측 이미지 표시 크기를 통일하기 위해.
  const scale = useMemo(() => {
    if (!loaded) return 1;
    const base = containerW / loaded.naturalWidth;
    const zoom = clamp(zoomPct, 10, 200) / 100;
    return base * zoom;
  }, [containerW, loaded, zoomPct]);

  const displaySize = useMemo(() => {
    if (!loaded) return { w: 900, h: 560 };
    return {
      w: Math.round(loaded.naturalWidth * scale),
      h: Math.round(loaded.naturalHeight * scale),
    };
  }, [loaded, scale]);

  // ===== 좌표 변환(화면 -> 원본 이미지) =====
  function getImagePoint(clientX: number, clientY: number) {
    const el = imgRef.current;
    const l = loadedRef.current;
    if (!el || !l) return null;
    const r = el.getBoundingClientRect();
    const x = (clientX - r.left) / scale;
    const y = (clientY - r.top) / scale;
    return { x: clamp(x, 0, l.naturalWidth), y: clamp(y, 0, l.naturalHeight) };
  }

  // 업로드/저장/복사 UI는 부모(OcrAnnotator)에서 처리한다.

  // ===== 전역 키보드(삭제) =====
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!selectedId) return;

      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase?.() ?? "";
      const isEditing =
        tag === "input" ||
        tag === "textarea" ||
        target?.getAttribute?.("contenteditable") === "true" ||
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        Boolean((target as any)?.isContentEditable);

      if (isEditing) return;

      if (e.key === "Delete" || e.key === "Backspace") {
        deleteRegionLocal(selectedId);
      }
    };

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId]);

  // ===== 자동 이름 생성(타입별) =====
  function nextAutoName(type: FieldType) {
    const prefix =
      type === "field"
        ? "field"
        : type === "multi"
          ? "multi"
          : type === "check"
            ? "check"
            : "table";
    let max = 0;
    for (const r of regionsRef.current) {
      const idx = parseIndex(r.name, prefix);
      if (idx != null) max = Math.max(max, idx);
    }
    return `${prefix}_${max + 1}`;
  }

  // ===== 포인터 이벤트 =====
  function onPointerDown(e: React.PointerEvent) {
    if (!loadedRef.current) return;
    if ((e.target as HTMLElement).dataset?.role) return;

    const p = getImagePoint(e.clientX, e.clientY);
    if (!p) return;

    // table: 세로 가이드선(colGuides) 지정 모드가 켜져 있으면
    // - 클릭한 x 위치를 기준으로 가이드선을 추가한다(여러 개 연속 추가 가능)
    if (colGuideTargetId) {
      const t = regionsRef.current.find(
        (r) => r.id === colGuideTargetId && r.fieldType === "table",
      );
      if (!t || t.fieldType !== "table") {
        setColGuideTargetId(null);
        return;
      }

      const inside =
        p.x >= t.x &&
        p.x <= t.x + t.width &&
        p.y >= t.y &&
        p.y <= t.y + t.height;
      if (!inside) return;

      const anchor =
        t.table?.rowTemplate ??
        ({ x: t.x, y: t.y, width: t.width, height: t.height } as Rect);
      const localX = clamp(p.x - anchor.x, 0, anchor.width);
      const ratio = anchor.width <= 0 ? 0 : localX / anchor.width;

      // 너무 가장자리(0/1)에 붙으면 의미가 없어 제외
      const minEdge = anchor.width > 0 ? 6 / anchor.width : 0.02;
      const safe = clamp(ratio, minEdge, 1 - minEdge);

      setRegions((prev) =>
        prev.map((r) => {
          if (r.id !== t.id) return r;
          if (r.fieldType !== "table") return r;
          const cur = normalizeColGuides(r.table?.colGuides);
          return {
            ...r,
            table: {
              ...(r.table ?? {}),
              colGuides: normalizeColGuides([...cur, safe]),
            },
          };
        }),
      );
      return;
    }

    // table: 행 템플릿(rowTemplate) 지정 모드가 켜져 있으면
    // - 새 영역을 만드는 게 아니라, 지정된 table의 rowTemplate을 드래그로 만든다.
    if (rowTemplateTargetId) {
      const t = regionsRef.current.find(
        (r) => r.id === rowTemplateTargetId && r.fieldType === "table",
      );
      if (!t) {
        setRowTemplateTargetId(null);
        return;
      }
      setSelectedId(t.id);
      setDragBoth({
        type: "drawRowTemplate",
        tableId: t.id,
        startX: p.x,
        startY: p.y,
      });
      return;
    }

    if (drawMode) {
      const id = drawTargetRegionId || uid("draft");
      const type = drawTargetFieldType || drawMode;

      const newDraft: Region = {
        id,
        name: drawTargetName || nextAutoName(type),
        fieldType: type,
        x: p.x,
        y: p.y,
        width: 1,
        height: 1,
        parts: type === "multi" ? 2 : undefined,
        ratios: type === "multi" ? [0.5, 0.5] : undefined,
        checkMode: type === "check" ? "boxOnly" : undefined,
        table: type === "table" ? { mode: "auto" } : undefined,
      };

      setRegions((prev) => {
        const exists = prev.some((region) => region.id === id);
        return exists
          ? prev.map((region) => (region.id === id ? { ...region, ...newDraft } : region))
          : [...prev, newDraft];
      });
      setSelectedId(id);
      setDragBoth({ type: "draw", startX: p.x, startY: p.y, draftId: id });
    } else {
      setSelectedId(null);
      onClearSelection?.();
    }
  }

  function applyDragFrame(pt: { x: number; y: number }) {
    const l = loadedRef.current;
    const d = dragRef.current;
    if (!l || !d) return;

    if (d.type === "drawRowTemplate") {
      setRegions((prev) =>
        prev.map((r) => {
          if (r.id !== d.tableId) return r;
          if (r.fieldType !== "table") return r;

          const area: Rect = {
            x: r.x,
            y: r.y,
            width: r.width,
            height: r.height,
          };
          const raw = normalizeRect(
            d.startX,
            d.startY,
            pt.x - d.startX,
            pt.y - d.startY,
          );
          const clamped = clampRectToArea(raw, area);

          // 너무 작은 템플릿은 그리기 중에는 유지, up에서 정리
          const rows = buildTableRows(area, clamped);

          return {
            ...r,
            table: {
              ...(r.table ?? {}),
              rowTemplate: clamped,
              rows,
            },
          };
        }),
      );
      return;
    }

    if (d.type === "draw") {
      setRegions((prev) =>
        prev.map((r) => {
          if (r.id !== d.draftId) return r;

          if (r.fieldType === "check") {
            const dx = pt.x - d.startX;
            const dy = pt.y - d.startY;
            const size = Math.max(Math.abs(dx), Math.abs(dy)) || 1;

            const wx = (dx < 0 ? -1 : 1) * size;
            const hy = (dy < 0 ? -1 : 1) * size;

            const nr = normalizeRect(d.startX, d.startY, wx, hy);
            const maxW = l.naturalWidth - nr.x;
            const maxH = l.naturalHeight - nr.y;
            const s = clamp(size, 1, Math.min(maxW, maxH));

            return {
              ...r,
              x: clamp(nr.x, 0, l.naturalWidth),
              y: clamp(nr.y, 0, l.naturalHeight),
              width: s,
              height: s,
            };
          }

          const nr = normalizeRect(
            d.startX,
            d.startY,
            pt.x - d.startX,
            pt.y - d.startY,
          );
          const maxW = l.naturalWidth - nr.x;
          const maxH = l.naturalHeight - nr.y;

          const next: Region = {
            ...r,
            x: clamp(nr.x, 0, l.naturalWidth),
            y: clamp(nr.y, 0, l.naturalHeight),
            width: clamp(nr.width, 1, maxW),
            height: clamp(nr.height, 1, maxH),
          };

          if (next.fieldType === "multi") {
            const parts = (next.parts ?? 2) as 2 | 3;
            next.ratios = normalizeRatios(parts, next.ratios);
          }

          return next;
        }),
      );
      return;
    }

    if (d.type === "move") {
      const dx = pt.x - d.startX;
      const dy = pt.y - d.startY;

      setRegions((prev) =>
        prev.map((r) => {
          if (r.id !== d.id) return r;
          const nx = clamp(d.baseX + dx, 0, l.naturalWidth - r.width);
          const ny = clamp(d.baseY + dy, 0, l.naturalHeight - r.height);
          if (r.fieldType === "table" && r.table) {
            const shift = (rect: Rect) => ({
              x: rect.x + (nx - r.x),
              y: rect.y + (ny - r.y),
              width: rect.width,
              height: rect.height,
            });
            return {
              ...r,
              x: nx,
              y: ny,
              table: {
                ...r.table,
                rowTemplate: r.table.rowTemplate
                  ? shift(r.table.rowTemplate)
                  : undefined,
                rows: Array.isArray(r.table.rows)
                  ? r.table.rows.map((rr) => shift(rr))
                  : undefined,
              },
            };
          }
          return { ...r, x: nx, y: ny };
        }),
      );
      return;
    }

    if (d.type === "resize") {
      const minSize = 4;
      const base = d.base;

      let x = base.x;
      let y = base.y;
      let w = base.width;
      let h = base.height;

      let dx = pt.x - d.startX;
      let dy = pt.y - d.startY;

      if (base.fieldType === "check") {
        const size = Math.max(Math.abs(dx), Math.abs(dy)) || minSize;
        dx = (dx < 0 ? -1 : 1) * size;
        dy = (dy < 0 ? -1 : 1) * size;
      }

      if (d.handle === "se") {
        w = base.width + dx;
        h = base.height + dy;
      } else if (d.handle === "sw") {
        x = base.x + dx;
        w = base.width - dx;
        h = base.height + dy;
      } else if (d.handle === "ne") {
        y = base.y + dy;
        h = base.height - dy;
        w = base.width + dx;
      } else {
        x = base.x + dx;
        y = base.y + dy;
        w = base.width - dx;
        h = base.height - dy;
      }

      const nr = normalizeRect(x, y, w, h);

      let nx = clamp(nr.x, 0, l.naturalWidth - minSize);
      let ny = clamp(nr.y, 0, l.naturalHeight - minSize);

      const maxW = l.naturalWidth - nx;
      const maxH = l.naturalHeight - ny;

      let nw = clamp(nr.width, minSize, maxW);
      let nh = clamp(nr.height, minSize, maxH);

      if (base.fieldType === "check") {
        const size = clamp(Math.max(nw, nh), minSize, Math.min(maxW, maxH));
        nw = size;
        nh = size;
      }

      setRegions((prev) =>
        prev.map((r) =>
          r.id === d.id
            ? (() => {
                const updated: Region = {
                  ...r,
                  x: nx,
                  y: ny,
                  width: nw,
                  height: nh,
                };
                if (
                  updated.fieldType === "table" &&
                  updated.table?.rowTemplate
                ) {
                  const area: Rect = { x: nx, y: ny, width: nw, height: nh };
                  const rt = clampRectToArea(updated.table.rowTemplate, area);
                  const rows = buildTableRows(area, rt);
                  updated.table = { ...updated.table, rowTemplate: rt, rows };
                }
                if (
                  updated.fieldType === "table" &&
                  updated.table &&
                  !updated.table.rowTemplate
                ) {
                  // rowTemplate이 없으면 rows는 의미가 없으니 정리
                  updated.table = { ...updated.table, rows: undefined };
                }
                return updated;
              })()
            : r,
        ),
      );
      return;
    }

    if (d.type === "split") {
      const target = regionsRef.current.find((r) => r.id === d.id);
      if (!target || target.fieldType !== "multi") return;

      const parts = (target.parts ?? 2) as 2 | 3;
      const baseRatios = normalizeRatios(parts, d.baseRatios);

      const localX = clamp(pt.x - target.x, 0, target.width);
      const pos = target.width <= 0 ? 0 : localX / target.width;

      const minPx = 10;
      const minR = target.width > 0 ? minPx / target.width : 0.05;

      const ratios = baseRatios.slice();

      const leftSum = ratios.slice(0, d.index).reduce((a, b) => a + b, 0);
      const pairSum = ratios[d.index] + ratios[d.index + 1];

      const minPos = leftSum + minR;
      const maxPos = leftSum + pairSum - minR;

      const bounded = clamp(pos, minPos, maxPos);
      const newLeft = bounded - leftSum;
      const newRight = pairSum - newLeft;

      ratios[d.index] = newLeft;
      ratios[d.index + 1] = newRight;

      const fixed = normalizeRatios(parts, ratios);

      setRegions((prev) =>
        prev.map((r) => (r.id === d.id ? { ...r, ratios: fixed } : r)),
      );
      return;
    }

    if (d.type === "tableCol") {
      const target = regionsRef.current.find((r) => r.id === d.tableId);
      if (!target || target.fieldType !== "table") return;

      const anchor =
        target.table?.rowTemplate ??
        ({
          x: target.x,
          y: target.y,
          width: target.width,
          height: target.height,
        } as Rect);
      const baseGuides = normalizeColGuides(d.baseGuides);
      if (
        baseGuides.length === 0 ||
        d.index < 0 ||
        d.index >= baseGuides.length
      )
        return;

      const localX = clamp(pt.x - anchor.x, 0, anchor.width);
      const pos = anchor.width <= 0 ? 0 : localX / anchor.width;

      const minPx = 10;
      const minR = anchor.width > 0 ? minPx / anchor.width : 0.03;

      const next = baseGuides.slice();
      const prev = d.index > 0 ? next[d.index - 1] : 0;
      const nxt = d.index < next.length - 1 ? next[d.index + 1] : 1;
      const bounded = clamp(pos, prev + minR, nxt - minR);
      next[d.index] = bounded;

      setRegions((prevRegions) =>
        prevRegions.map((r) =>
          r.id !== target.id
            ? r
            : r.fieldType === "table"
              ? {
                  ...r,
                  table: {
                    ...(r.table ?? {}),
                    colGuides: normalizeColGuides(next),
                  },
                }
              : r,
        ),
      );
      return;
    }
  }

  function onPointerMove(e: React.PointerEvent) {
    if (!loadedRef.current) return;
    if (!dragRef.current) return;

    const p = getImagePoint(e.clientX, e.clientY);
    if (!p) return;

    pendingPointRef.current = p;
    if (rafRef.current != null) return;

    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      const pt = pendingPointRef.current;
      if (!pt) return;
      applyDragFrame(pt);
    });
  }

  function onPointerUp() {
    if (rafRef.current != null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    pendingPointRef.current = null;

    const d = dragRef.current;
    if (!d) return;

    if (d.type === "drawRowTemplate") {
      // rowTemplate 지정 모드 종료
      setRowTemplateTargetId(null);

      // 너무 작은 rowTemplate이면 정리
      const t = regionsRef.current.find((r) => r.id === d.tableId);
      const rt = t?.fieldType === "table" ? t.table?.rowTemplate : null;
      const tooSmall = !!rt && (rt.width < 4 || rt.height < 4);
      if (tooSmall) {
        setRegions((prev) =>
          prev.map((r) =>
            r.id !== d.tableId
              ? r
              : r.fieldType === "table"
                ? {
                    ...r,
                    table: {
                      ...(r.table ?? {}),
                      rowTemplate: undefined,
                      rows: undefined,
                    },
                  }
                : r,
          ),
        );
      }
    }

    if (d.type === "draw") {
      setDrawMode(null);

      const draft = regionsRef.current.find((r) => r.id === d.draftId);
      const isTooSmall = !!draft && (draft.width < 4 || draft.height < 4);

      setRegions((prev) =>
        prev.filter((r) =>
          r.id !== d.draftId ? true : r.width >= 4 && r.height >= 4,
        ),
      );
      if (isTooSmall) setSelectedId(null);
    }

    setDragBoth(null);
  }

  // ===== 선택 =====
  const selected = selectedId
    ? (regions.find((r) => r.id === selectedId) ?? null)
    : null;

  function deleteRegionLocal(id: string) {
    setRegions((prev) => prev.filter((r) => r.id !== id));
    setSelectedId((cur) => (cur === id ? null : cur));
    delete lastRectRef.current[id];
  }

  // ===== 선택 박스 외부 마스크 계산 =====
  const selectedDisplayRect = useMemo(() => {
    if (!loaded || !selected) return null;
    const left = clamp(selected.x * scale, 0, displaySize.w);
    const top = clamp(selected.y * scale, 0, displaySize.h);
    const w = clamp(selected.width * scale, 0, displaySize.w - left);
    const h = clamp(selected.height * scale, 0, displaySize.h - top);
    return { left, top, w, h, right: left + w, bottom: top + h };
  }, [loaded, selected, scale, displaySize.w, displaySize.h]);

  // ===== 선택 박스 툴바 위치(박스 아래) =====
  const actionBarPos = useMemo(() => {
    if (!selectedDisplayRect) return null;
    const pad = 8;
    const left = clamp(
      selectedDisplayRect.left + selectedDisplayRect.w / 2,
      pad,
      displaySize.w - pad,
    );
    const top = clamp(selectedDisplayRect.bottom + 8, pad, displaySize.h - pad);
    return { left, top };
  }, [selectedDisplayRect, displaySize.w, displaySize.h]);

  function deselect() {
    setSelectedId(null);
  }

  function deleteSelected() {
    if (!selectedId) return;
    deleteRegionLocal(selectedId);
  }

  function duplicateSelected() {
    const l = loadedRef.current;
    const s = selected;
    if (!l || !s) return;

    const id = uid("r");
    const offset = 10;
    const nx = clamp(s.x + offset, 0, l.naturalWidth - s.width);
    const ny = clamp(s.y + offset, 0, l.naturalHeight - s.height);

    const copy: Region = {
      ...s,
      id,
      name: nextAutoName(s.fieldType),
      x: nx,
      y: ny,
    };

    if (copy.fieldType === "check") copy.checkMode = "boxOnly";
    if (copy.fieldType === "multi") {
      const parts = (s.parts ?? 2) as 2 | 3;
      copy.parts = parts;
      copy.ratios = normalizeRatios(parts, s.ratios);
    }

    setRegions((prev) => [...prev, copy]);
    setSelectedId(id);
  }

  function setMultiParts(parts: 2 | 3) {
    if (!selected || selected.fieldType !== "multi") return;
    const ratios = parts === 2 ? [0.5, 0.5] : [1 / 3, 1 / 3, 1 / 3];
    setRegions((prev) =>
      prev.map((r) => (r.id === selected.id ? { ...r, parts, ratios } : r)),
    );
  }

  // ✅ OcrAnnotator에서 문서를 바꾸면 undo 스냅샷도 초기화
  useEffect(() => {
    lastRectRef.current = {};
  }, [loaded?.src]);

  return (
    <div
      ref={wrapRef}
      style={{
        background: "var(--panel2)",
        height: "100%",
        minHeight: 0,
        minWidth: 0,
        overflow: "auto",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/*
        ✅ 하단 여백이 “확실히” 보이도록 스페이서(div)를 함께 둔다.
        padding만으로도 보통 충분하지만,
        내부 컨텐츠(고정 height, absolute overlay 등) 구성에 따라
        바닥 여백이 체감되지 않는 케이스가 있어 스페이서를 안전장치로 추가.
      */}
      {!loaded ? (
        <div
          style={{
            width: "100%",
            height: "100%",
            minHeight: 400,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 14,
            border: "1.5px dashed rgba(255,255,255,0.18)",
            borderRadius: 8,
            cursor: "pointer",
            boxSizing: "border-box",
          }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const file = e.dataTransfer.files?.[0];
            if (file && fileInputRef?.current) {
              const dt = new DataTransfer();
              dt.items.add(file);
              fileInputRef.current.files = dt.files;
              fileInputRef.current.dispatchEvent(new Event("change", { bubbles: true }));
            }
          }}
          onClick={() => fileInputRef?.current?.click()}
        >
          {/* 업로드 아이콘 */}
          <div style={{
            width: 56, height: 56, borderRadius: 999,
            background: "rgba(255,255,255,0.06)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="26" height="26" viewBox="0 0 20 20" fill="none">
              <path d="M10 14V4M10 4L6 8M10 4L14 8" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M4 16h12" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text)", marginBottom: 5 }}>
              문서를 드래그하거나 업로드하세요
            </div>
            <div style={{ fontSize: 12, color: "var(--muted)" }}>
              이미지(.jpeg .jpg .png .tif .tiff) 및 PDF 지원
            </div>
          </div>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); fileInputRef?.current?.click(); }}
            style={{
              padding: "9px 28px", borderRadius: 8,
              background: "var(--accent)", color: "#fff",
              border: "none", fontWeight: 700, fontSize: 13,
              cursor: "pointer",
            }}
          >
            파일 선택
          </button>
        </div>
      ) : (
        <>
          <div
            style={{
              position: "relative",
              width: displaySize.w,
              height: displaySize.h,
              userSelect: "none",
              touchAction: "none",
            }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerLeave={onPointerUp}
          >
            <img
              ref={imgRef}
              src={loaded.src}
              alt="ocr"
              draggable={false}
              style={{
                width: displaySize.w,
                height: displaySize.h,
                display: "block",
                borderRadius: 10,
              }}
            />

            {/* 아래 오버레이/마스크/리사이즈 핸들은 네 코드 그대로 유지 */}
            {/* 선택 박스 외부 마스크 */}
            {selectedDisplayRect && (
              <>
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    width: displaySize.w,
                    height: selectedDisplayRect.top,
                    background: "rgba(0,0,0,0.45)",
                    zIndex: 5,
                    pointerEvents: "none",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: selectedDisplayRect.top,
                    width: selectedDisplayRect.left,
                    height: selectedDisplayRect.h,
                    background: "rgba(0,0,0,0.45)",
                    zIndex: 5,
                    pointerEvents: "none",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: selectedDisplayRect.right,
                    top: selectedDisplayRect.top,
                    width: Math.max(
                      0,
                      displaySize.w - selectedDisplayRect.right,
                    ),
                    height: selectedDisplayRect.h,
                    background: "rgba(0,0,0,0.45)",
                    zIndex: 5,
                    pointerEvents: "none",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: selectedDisplayRect.bottom,
                    width: displaySize.w,
                    height: Math.max(
                      0,
                      displaySize.h - selectedDisplayRect.bottom,
                    ),
                    background: "rgba(0,0,0,0.45)",
                    zIndex: 5,
                    pointerEvents: "none",
                  }}
                />
              </>
            )}

            {/* 선택 박스 하단 액션바 + (멀티 2/3칸) */}
            {selectedId && actionBarPos && (
              <div
                style={{
                  position: "absolute",
                  left: actionBarPos.left,
                  top: actionBarPos.top,
                  transform: "translateX(-50%)",
                  zIndex: 40,
                  display: "flex",
                  gap: 4,
                  padding: "4px 4px",
                  borderRadius: 10,
                  background: "rgba(0,0,0,0.78)",
                  boxShadow: "0 6px 16px rgba(0,0,0,0.25)",
                  pointerEvents: "auto",
                  maxWidth: displaySize.w - 16,
                  flexWrap: "wrap",
                  alignItems: "center",
                }}
                onPointerDown={(e) => e.stopPropagation()}
              >
                {(
                  [
                    {
                      key: "del",
                      label: "🗑",
                      title: "삭제",
                      onClick: deleteSelected,
                    },
                    {
                      key: "undo",
                      label: "↩",
                      title: "이전 좌표/크기로",
                      onClick: undoSelectedRect,
                    },
                    {
                      key: "dup",
                      label: "⧉",
                      title: "복제(자동 이름)",
                      onClick: duplicateSelected,
                    },
                    {
                      key: "off",
                      label: "✕",
                      title: "선택 해제",
                      onClick: deselect,
                    },
                  ] as const
                ).map((b) => (
                  <button
                    key={b.key}
                    type="button"
                    onClick={b.onClick}
                    style={{
                      border: "1px solid rgba(255,255,255,0.18)",
                      background: "rgba(255,255,255,0.06)",
                      color: "#fff",
                      borderRadius: 8,
                      padding: "4px 6px",
                      cursor: "pointer",
                      fontSize: 12,
                      lineHeight: 1,
                      minWidth: 30,
                      height: 28,
                    }}
                    title={b.title}
                  >
                    {b.label}
                  </button>
                ))}

                {selected?.fieldType === "multi" && (
                  <>
                    <span
                      style={{
                        color: "rgba(255,255,255,0.7)",
                        fontSize: 12,
                        marginLeft: 4,
                      }}
                    >
                      분할
                    </span>
                    <button
                      type="button"
                      onClick={() => setMultiParts(2)}
                      style={{
                        border: "1px solid rgba(255,255,255,0.18)",
                        background:
                          (selected.parts ?? 2) === 2
                            ? "rgba(255,255,255,0.22)"
                            : "rgba(255,255,255,0.06)",
                        color: "#fff",
                        borderRadius: 8,
                        padding: "4px 8px",
                        cursor: "pointer",
                        fontSize: 12,
                        height: 28,
                      }}
                      title="2칸"
                    >
                      2칸
                    </button>
                    <button
                      type="button"
                      onClick={() => setMultiParts(3)}
                      style={{
                        border: "1px solid rgba(255,255,255,0.18)",
                        background:
                          (selected.parts ?? 2) === 3
                            ? "rgba(255,255,255,0.22)"
                            : "rgba(255,255,255,0.06)",
                        color: "#fff",
                        borderRadius: 8,
                        padding: "4px 8px",
                        cursor: "pointer",
                        fontSize: 12,
                        height: 28,
                      }}
                      title="3칸"
                    >
                      3칸
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Overlay Regions (너가 올린 그대로) */}
            {emptySelectionHint && visibleRegions.length === 0 && (
              <div
                style={{
                  position: "absolute",
                  left: 12,
                  top: 12,
                  zIndex: 20,
                  maxWidth: "calc(100% - 24px)",
                  padding: "7px 10px",
                  borderRadius: 6,
                  border: "1px solid rgba(34,211,238,0.28)",
                  background: "rgba(15,23,42,0.84)",
                  color: "#cbd5e1",
                  fontSize: 12,
                  fontWeight: 800,
                  lineHeight: 1.35,
                  pointerEvents: "none",
                }}
              >
                {emptySelectionHint}
              </div>
            )}

            {visibleRegions.map((r) => {
              const isSel = r.id === selectedId;
              const left = r.x * scale;
              const top = r.y * scale;
              const w = r.width * scale;
              const h = r.height * scale;

              const parts =
                r.fieldType === "multi" ? ((r.parts ?? 2) as 2 | 3) : null;
              const ratios =
                r.fieldType === "multi" && parts
                  ? normalizeRatios(parts, r.ratios)
                  : null;

              const splitPositions =
                r.fieldType === "multi" && parts && ratios
                  ? Array.from({ length: parts - 1 }).map((_, idx) =>
                      ratios.slice(0, idx + 1).reduce((a, b) => a + b, 0),
                    )
                  : [];

              const tableRowTemplate =
                r.fieldType === "table" ? r.table?.rowTemplate : undefined;
              const tableRows =
                r.fieldType === "table" && Array.isArray(r.table?.rows)
                  ? (r.table!.rows as Rect[])
                  : [];

              const tableColGuides =
                r.fieldType === "table"
                  ? normalizeColGuides(r.table?.colGuides)
                  : [];

              const colAnchor =
                r.fieldType === "table"
                  ? (tableRowTemplate ??
                    ({
                      x: r.x,
                      y: r.y,
                      width: r.width,
                      height: r.height,
                    } as Rect))
                  : null;

              const isOcrRegion = r.id.startsWith("ocr_");
              const regionColor = isOcrRegion
                ? { border: "rgba(8,145,178,0.7)", bg: "rgba(8,145,178,0.08)", selBorder: "#0891b2", selBg: "rgba(8,145,178,0.10)", selShadow: "rgba(8,145,178,0.18)" }
                : { border: "rgba(59,130,246,0.7)", bg: "rgba(59,130,246,0.08)", selBorder: "#0ea5e9", selBg: "rgba(14,165,233,0.10)", selShadow: "rgba(14,165,233,0.18)" };

              return (
                <div
                  key={r.id}
                  data-role="region"
                  onPointerDown={(e) => {
                    if (!loadedRef.current) return;
                    e.stopPropagation();
                    setSelectedId(r.id);

                    // ✅ table: 행 템플릿 지정 모드일 때는 이동 대신 rowTemplate 드래그로 동작
                    if (
                      rowTemplateTargetId === r.id &&
                      r.fieldType === "table"
                    ) {
                      const p = getImagePoint(e.clientX, e.clientY);
                      if (!p) return;
                      setDragBoth({
                        type: "drawRowTemplate",
                        tableId: r.id,
                        startX: p.x,
                        startY: p.y,
                      });
                      return;
                    }

                    // ✅ table: 세로 가이드선 찍기 모드일 때는 이동 대신 가이드 추가
                    if (colGuideTargetId === r.id && r.fieldType === "table") {
                      const p = getImagePoint(e.clientX, e.clientY);
                      if (!p) return;
                      const t = r;
                      const anchor =
                        t.table?.rowTemplate ??
                        ({
                          x: t.x,
                          y: t.y,
                          width: t.width,
                          height: t.height,
                        } as Rect);
                      const localX = clamp(p.x - anchor.x, 0, anchor.width);
                      const ratio =
                        anchor.width <= 0 ? 0 : localX / anchor.width;
                      const minEdge =
                        anchor.width > 0 ? 6 / anchor.width : 0.02;
                      const safe = clamp(ratio, minEdge, 1 - minEdge);
                      setRegions((prev) =>
                        prev.map((rr) =>
                          rr.id !== t.id
                            ? rr
                            : rr.fieldType === "table"
                              ? {
                                  ...rr,
                                  table: {
                                    ...(rr.table ?? {}),
                                    colGuides: normalizeColGuides([
                                      ...normalizeColGuides(
                                        rr.table?.colGuides,
                                      ),
                                      safe,
                                    ]),
                                  },
                                }
                              : rr,
                        ),
                      );
                      return;
                    }

                    snapshotRect(r.id);

                    const p = getImagePoint(e.clientX, e.clientY);
                    if (!p) return;
                    setDragBoth({
                      type: "move",
                      id: r.id,
                      startX: p.x,
                      startY: p.y,
                      baseX: r.x,
                      baseY: r.y,
                    });
                  }}
                  style={{
                    position: "absolute",
                    left,
                    top,
                    width: w,
                    height: h,
                    border: isSel
                      ? `2px dashed ${regionColor.selBorder}`
                      : `1px solid ${regionColor.border}`,
                    background: isSel
                      ? regionColor.selBg
                      : regionColor.bg,
                    boxShadow: isSel
                      ? `0 0 0 2px ${regionColor.selShadow}`
                      : "none",
                    boxSizing: "border-box",
                    borderRadius: 6,
                    cursor: "move",
                    zIndex: isSel ? 30 : 10,
                  }}
                >
                  {!isSel && (
                    <div className="ocp-hover-label" style={{
                      position: "absolute",
                      left: "50%",
                      top: -20,
                      transform: "translateX(-50%)",
                      zIndex: 40,
                      pointerEvents: "none",
                    }}>
                      <span style={{
                        fontSize: 11,
                        padding: "2px 8px",
                        borderRadius: 4,
                        background: isOcrRegion ? "#0891b2" : "#3b82f6",
                        color: "#fff",
                        whiteSpace: "nowrap",
                        fontWeight: 700,
                      }}>{r.name}</span>
                    </div>
                  )}

                  {isSel && r.fieldType === "multi" && parts && ratios && (
                    <>
                      {splitPositions.map((pRatio, idx) => (
                        <React.Fragment key={idx}>
                          <div
                            style={{
                              position: "absolute",
                              top: 0,
                              bottom: 0,
                              left: `${pRatio * 100}%`,
                              width: 0,
                              borderLeft: "1px dashed rgba(14,165,233,0.95)",
                              pointerEvents: "none",
                            }}
                          />
                          <div
                            data-role="split-handle"
                            onPointerDown={(e) => {
                              if (!loadedRef.current) return;
                              e.stopPropagation();
                              setSelectedId(r.id);

                              const p = getImagePoint(e.clientX, e.clientY);
                              if (!p) return;

                              setDragBoth({
                                type: "split",
                                id: r.id,
                                index: idx,
                                startX: p.x,
                                baseRatios: ratios,
                              });
                            }}
                            style={{
                              position: "absolute",
                              top: 0,
                              bottom: 0,
                              left: `${pRatio * 100}%`,
                              width: 14,
                              transform: "translateX(-50%)",
                              cursor: "col-resize",
                              zIndex: 35,
                              background: "rgba(14,165,233,0.08)",
                            }}
                            title="분할선 드래그로 칸 폭 조절"
                          />
                        </React.Fragment>
                      ))}
                    </>
                  )}

                  {isSel && r.fieldType === "table" && (
                    <>
                      {/* rowTemplate */}
                      {tableRowTemplate && (
                        <div
                          style={{
                            position: "absolute",
                            left: (tableRowTemplate.x - r.x) * scale,
                            top: (tableRowTemplate.y - r.y) * scale,
                            width: tableRowTemplate.width * scale,
                            height: tableRowTemplate.height * scale,
                            border: "2px dashed rgba(16,185,129,0.95)",
                            background: "rgba(16,185,129,0.08)",
                            borderRadius: 6,
                            pointerEvents: "none",
                          }}
                        />
                      )}

                      {/* rows preview */}
                      {tableRows.length > 0 &&
                        tableRows.slice(0, 80).map((rr, idx) => (
                          <div
                            key={idx}
                            style={{
                              position: "absolute",
                              left: (rr.x - r.x) * scale,
                              top: (rr.y - r.y) * scale,
                              width: rr.width * scale,
                              height: rr.height * scale,
                              border: "1px dashed rgba(16,185,129,0.55)",
                              background: "rgba(16,185,129,0.03)",
                              borderRadius: 6,
                              pointerEvents: "none",
                            }}
                            title={`row ${idx + 1}`}
                          />
                        ))}

                      {/* column guides */}
                      {colAnchor &&
                        tableColGuides.map((g, idx) => {
                          const xLocal =
                            (colAnchor.x - r.x + colAnchor.width * g) * scale;
                          return (
                            <React.Fragment key={idx}>
                              <div
                                style={{
                                  position: "absolute",
                                  top: 0,
                                  bottom: 0,
                                  left: xLocal,
                                  width: 0,
                                  borderLeft:
                                    "1px dashed rgba(16,185,129,0.95)",
                                  pointerEvents: "none",
                                }}
                              />
                              <div
                                data-role="col-guide-handle"
                                onPointerDown={(e) => {
                                  if (!loadedRef.current) return;
                                  e.stopPropagation();
                                  setSelectedId(r.id);
                                  const p = getImagePoint(e.clientX, e.clientY);
                                  if (!p) return;
                                  setDragBoth({
                                    type: "tableCol",
                                    tableId: r.id,
                                    index: idx,
                                    startX: p.x,
                                    baseGuides: tableColGuides,
                                  });
                                }}
                                style={{
                                  position: "absolute",
                                  top: 0,
                                  bottom: 0,
                                  left: xLocal,
                                  width: 14,
                                  transform: "translateX(-50%)",
                                  cursor: "col-resize",
                                  zIndex: 35,
                                  background: "rgba(16,185,129,0.06)",
                                }}
                                title="세로 가이드선 드래그로 위치 조절"
                              />
                            </React.Fragment>
                          );
                        })}
                    </>
                  )}

                  {isSel && (
                    <>
                      {(["nw", "ne", "sw", "se"] as const).map((hnd) => {
                        const size = 10;
                        const style: React.CSSProperties = {
                          position: "absolute",
                          width: size,
                          height: size,
                          background: "var(--panel)",
                          border: "2px solid #0ea5e9",
                          borderRadius: 999,
                          boxSizing: "border-box",
                          cursor:
                            hnd === "nw" || hnd === "se"
                              ? "nwse-resize"
                              : "nesw-resize",
                          zIndex: 31,
                        };
                        if (hnd === "nw") {
                          style.left = -size / 2;
                          style.top = -size / 2;
                        }
                        if (hnd === "ne") {
                          style.right = -size / 2;
                          style.top = -size / 2;
                        }
                        if (hnd === "sw") {
                          style.left = -size / 2;
                          style.bottom = -size / 2;
                        }
                        if (hnd === "se") {
                          style.right = -size / 2;
                          style.bottom = -size / 2;
                        }

                        return (
                          <div
                            key={hnd}
                            data-role="handle"
                            onPointerDown={(e) => {
                              if (!loadedRef.current) return;
                              e.stopPropagation();
                              setSelectedId(r.id);

                              snapshotRect(r.id);

                              const p = getImagePoint(e.clientX, e.clientY);
                              if (!p) return;

                              setDragBoth({
                                type: "resize",
                                id: r.id,
                                handle: hnd,
                                startX: p.x,
                                startY: p.y,
                                base: r,
                              });
                            }}
                            style={style}
                          />
                        );
                      })}
                    </>
                  )}
                </div>
              );
            })}
          </div>
          <div style={{ height: 18 }} />
        </>
      )}
    </div>
  );
}
