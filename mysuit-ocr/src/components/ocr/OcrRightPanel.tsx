"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import type { FieldType, LoadedImage, Rect, Region } from "./core/types";
import {
  normalizeRatios,
  calcMultiSubRegions,
} from "./core/ops";
import { normalizeColGuides } from "./core/table";

type Props = {
  imgRef: React.RefObject<HTMLImageElement | null>;
  templateName: string;
  setTemplateName: React.Dispatch<React.SetStateAction<string>>;
  loaded: LoadedImage | null;
  regions: Region[];
  setRegions: React.Dispatch<React.SetStateAction<Region[]>>;
  selectedId: string | null;
  setSelectedId: React.Dispatch<React.SetStateAction<string | null>>;
  /** table: 행 템플릿 지정 모드(대상 table id) */
  rowTemplateTargetId: string | null;
  setRowTemplateTargetId: React.Dispatch<React.SetStateAction<string | null>>;
  /** table: 세로 가이드선(colGuides) 지정 모드(대상 table id) */
  colGuideTargetId: string | null;
  setColGuideTargetId: React.Dispatch<React.SetStateAction<string | null>>;
  updateName: (id: string, name: string) => void;
  deleteRegion: (id: string) => void;
};

export default function OcrRightPanel(props: Props) {
  const {
    imgRef,
    templateName,
    setTemplateName,
    loaded,
    regions,
    setRegions,
    selectedId,
    setSelectedId,
    rowTemplateTargetId,
    setRowTemplateTargetId,
    colGuideTargetId,
    setColGuideTargetId,
    updateName,
    deleteRegion,
  } = props;

  const selected = selectedId
    ? (regions.find((r) => r.id === selectedId) ?? null)
    : null;

  // 종료 키워드 입력은 타이핑 경험(쉼표 입력/마지막 쉼표 유지)을 위해
  // 로컬에서 raw 문자열을 유지하고, blur 시점에만 파싱하여 저장한다.
  const [stopKeywordsRaw, setStopKeywordsRaw] = useState<string>("");
  useEffect(() => {
    if (!selected || selected.fieldType !== "table") {
      setStopKeywordsRaw("");
      return;
    }
    const list = selected.table?.stopKeywords ?? [];
    setStopKeywordsRaw(list.join(", "));
  }, [selectedId, selected?.fieldType, selected?.table?.stopKeywords]);

  function typeBadge(t: FieldType) {
    if (t === "field")
      return {
        text: "필드",
        bg: "rgba(14,165,233,0.12)",
        bd: "rgba(14,165,233,0.35)",
        fg: "#0369a1",
      };
    if (t === "multi")
      return {
        text: "멀티",
        bg: "rgba(16,185,129,0.12)",
        bd: "rgba(16,185,129,0.35)",
        fg: "#047857",
      };
    if (t === "table")
      return {
        text: "표",
        bg: "rgba(16,185,129,0.12)",
        bd: "rgba(16,185,129,0.35)",
        fg: "#047857",
      };
    return {
      text: "체크",
      bg: "rgba(244,63,94,0.10)",
      bd: "rgba(244,63,94,0.30)",
      fg: "#be123c",
    };
  }

  function clearTableMeta(tableId: string) {
    setRegions((prev) =>
      prev.map((r) =>
        r.id !== tableId
          ? r
          : r.fieldType === "table"
            ? {
                ...r,
                table: {
                  ...(r.table ?? {}),
                  mode: r.table?.mode ?? "repeat",
                  rowTemplate: undefined,
                  rows: undefined,
                },
              }
            : r,
      ),
    );
  }

  function setTableMode(tableId: string, mode: "repeat" | "auto") {
    setRegions((prev) =>
      prev.map((r) => {
        if (r.id !== tableId) return r;
        if (r.fieldType !== "table") return r;
        const cur = r.table ?? {};
        // auto 모드에서는 rowTemplate/rows를 사용하지 않으므로 정리
        const cleaned =
          mode === "auto"
            ? { ...cur, mode, rowTemplate: undefined, rows: undefined }
            : { ...cur, mode };
        return { ...r, table: cleaned };
      }),
    );
  }

  function updateStopKeywords(tableId: string, raw: string) {
    const list = raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 30);
    setRegions((prev) =>
      prev.map((r) =>
        r.id !== tableId
          ? r
          : r.fieldType === "table"
            ? {
                ...r,
                table: { ...(r.table ?? {}), stopKeywords: list.length ? list : undefined },
              }
            : r,
      ),
    );
  }

  function clearTableColGuides(tableId: string) {
    setRegions((prev) =>
      prev.map((r) =>
        r.id !== tableId
          ? r
          : r.fieldType === "table"
            ? { ...r, table: { ...(r.table ?? {}), colGuides: undefined } }
            : r,
      ),
    );
  }

  function removeTableColGuide(tableId: string, index: number) {
    setRegions((prev) =>
      prev.map((r) => {
        if (r.id !== tableId) return r;
        if (r.fieldType !== "table") return r;
        const cur = normalizeColGuides(r.table?.colGuides);
        const next = cur.filter((_, i) => i !== index);
        return {
          ...r,
          table: {
            ...(r.table ?? {}),
            colGuides: next.length ? next : undefined,
          },
        };
      }),
    );
  }

  // ====== Crop 미리보기 캐시(우측 패널에서만) ======
  const loadedRef = useRef<LoadedImage | null>(loaded);
  const cropCacheRef = useRef<Map<string, string>>(new Map());
  useEffect(() => {
    loadedRef.current = loaded;
  }, [loaded]);
  useEffect(() => {
    cropCacheRef.current.clear();
  }, [loaded?.src]);

  function makeCropKey(args: {
    src: string;
    sx: number;
    sy: number;
    sw: number;
    sh: number;
    targetMax: number;
  }) {
    const { src, sx, sy, sw, sh, targetMax } = args;
    return `${src}|${sx}|${sy}|${sw}|${sh}|${targetMax}`;
  }

  function cropToDataUrl(opts: {
    sx: number;
    sy: number;
    sw: number;
    sh: number;
    targetMax: number;
  }): string | null {
    const l = loadedRef.current;
    const imgEl = imgRef.current;
    if (!l || !imgEl) return null;
    const src = l.src;
    const sx = Math.max(0, Math.floor(opts.sx));
    const sy = Math.max(0, Math.floor(opts.sy));
    const sw = Math.max(1, Math.floor(opts.sw));
    const sh = Math.max(1, Math.floor(opts.sh));
    const targetMax = Math.max(16, Math.floor(opts.targetMax));

    const key = makeCropKey({ src, sx, sy, sw, sh, targetMax });
    const cached = cropCacheRef.current.get(key);
    if (cached) return cached;

    try {
      const canvas = document.createElement("canvas");
      const ar = sw / sh;
      const dw = ar >= 1 ? targetMax : Math.round(targetMax * ar);
      const dh = ar >= 1 ? Math.round(targetMax / ar) : targetMax;
      canvas.width = Math.max(1, dw);
      canvas.height = Math.max(1, dh);
      const ctx = canvas.getContext("2d");
      if (!ctx) return null;
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(imgEl, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
      const url = canvas.toDataURL("image/png");
      cropCacheRef.current.set(key, url);
      return url;
    } catch {
      return null;
    }
  }

  function getRegionThumb(r: Region, targetMax: number) {
    return cropToDataUrl({
      sx: r.x,
      sy: r.y,
      sw: r.width,
      sh: r.height,
      targetMax,
    });
  }

  function getMultiThumbs(r: Region, targetMax: number) {
    const subs = calcMultiSubRegions(r);
    return subs
      .map((s) =>
        cropToDataUrl({
          sx: s.x,
          sy: s.y,
          sw: s.width,
          sh: s.height,
          targetMax,
        }),
      )
      .filter((x): x is string => Boolean(x));
  }

  const selectedThumbLarge = useMemo(() => {
    if (!selected) return null;
    if (selected.fieldType === "multi") return null;
    return getRegionThumb(selected, 260);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    selectedId,
    selected?.x,
    selected?.y,
    selected?.width,
    selected?.height,
    loaded?.src,
  ]);

  const selectedMultiThumbsLarge = useMemo(() => {
    if (!selected || selected.fieldType !== "multi") return [];
    const parts = (selected.parts ?? 2) as 2 | 3;
    const ratios = normalizeRatios(parts, selected.ratios);
    const rr: Region = { ...selected, parts, ratios };
    return getMultiThumbs(rr, 180);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    selectedId,
    selected?.x,
    selected?.y,
    selected?.width,
    selected?.height,
    selected?.parts,
    JSON.stringify(selected?.ratios ?? []),
    loaded?.src,
  ]);

  return (
    <aside className="oc-panel">
      {/* 템플릿 명 입력 */}
      <div className="oc-template-input-wrap">
        <h2 className="oc-label">템플릿 명</h2>
        <input
          value={templateName}
          onChange={(e) => setTemplateName(e.target.value)}
          placeholder="템플릿 명"
          className="ms-input"
          style={{ width: "100%" }}
        />
      </div>

      {/* 스크롤 영역 */}
      <div className="oc-panel-scroll">
      <div className="oc-section">
        <div className="oc-section-header">
          <h3 className="oc-section-title" style={{ margin: 0 }}>영역 목록</h3>
          <span className="oc-muted">{regions.length}개</span>
        </div>

        <div style={{ marginTop: 10, display: "flex", flexDirection: "column" }}>
          {regions.length === 0 ? (
            <div className="oc-muted" style={{ fontSize: 13 }}>
              영역이 없습니다.
            </div>
          ) : (
            regions.map((r) => {
              const isSel = r.id === selectedId;
              const badge = typeBadge(r.fieldType);

              return (
                <div
                  key={r.id}
                  className={`oc-region-item${isSel ? " oc-region-item-sel" : ""}`}
                  onClick={() => setSelectedId(r.id)}
                >
                  {/* ✅ 헤더: 종류 + 좌표만(멀티 색 막대/ratio 텍스트 제거) */}
                  <div
                    style={{
                      display: "flex",
                      gap: 8,
                      alignItems: "center",
                      marginBottom: 8,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 10,
                        padding: "2px 6px",
                        borderRadius: 999,
                        background: badge.bg,
                        border: `1px solid ${badge.bd}`,
                        color: badge.fg,
                        flex: "0 0 auto",
                      }}
                    >
                      {badge.text}
                    </span>

                    <span style={{ fontSize: 12, color: "#666" }}>
                      ({Math.round(r.x)}, {Math.round(r.y)}) /{" "}
                      {Math.round(r.width)}×{Math.round(r.height)}
                    </span>
                  </div>

                  {/* 이름 입력 + 삭제 */}
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      value={r.name}
                      onChange={(e) => updateName(r.id, e.target.value)}
                      className={`oc-region-input${isSel ? " oc-region-input-sel" : ""}`}
                    />
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteRegion(r.id);
                      }}
                      className="ms-btn-sm"
                    >
                      삭제
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* 선택 영역 */}
        <div className="oc-section">
          <h3 className="oc-section-title">선택 영역</h3>
          {!selected ? (
            <div className="oc-muted" style={{ fontSize: 13 }}>
              선택된 영역이 없습니다.
            </div>
          ) : (
            <div style={{ fontSize: 13, color: "#555", lineHeight: 1.6 }}>
              <div>
                <b>{selected.name}</b>
              </div>
{/* table 전용 컨트롤 */}
              {selected.fieldType === "table" && (
                <div className="oc-table-controls">
                  <div className="oc-muted" style={{ fontSize: 12, marginBottom: 8 }}>
                    테이블필드(표)
                  </div>
{/* 모드 선택 (가변 그리드 우선) */}
                  <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                    <button
                      type="button"
                      onClick={() => setTableMode(selected.id, "auto")}
                      className={`ms-btn-sm${(selected.table?.mode ?? "auto") === "auto" ? " oc-mode-btn-active" : ""}`}
                      title="컬럼(세로 가이드)만 고정하고, OCR 단계에서 행을 자동 감지(가변 그리드)"
                    >
                      가변 그리드
                    </button>
                    <button
                      type="button"
                      onClick={() => setTableMode(selected.id, "repeat")}
                      className={`ms-btn-sm${(selected.table?.mode ?? "auto") === "repeat" ? " oc-mode-btn-active" : ""}`}
                      title="행 템플릿으로 고정 그리드를 구성해 rows를 만드는 방식(기존)"
                    >
                      고정 그리드
                    </button>
                  </div>

                  {/* 가변 그리드 옵션: 종료 키워드는 가변 그리드(auto)에서만 사용 */}
                  {(selected.table?.mode ?? "auto") === "auto" && (
                    <div style={{ display: "grid", gap: 8, marginBottom: 10 }}>
                      <div>
                        <div className="oc-muted" style={{ fontSize: 12, marginBottom: 6 }}>
                          종료 키워드(쉼표로 구분)
                        </div>
                        <input
                          type="text"
                          value={stopKeywordsRaw}
                          onChange={(e) => setStopKeywordsRaw(e.target.value)}
                          onBlur={() => updateStopKeywords(selected.id, stopKeywordsRaw)}
                          placeholder="예: 전체 합계, 합계, 총액, 부가세"
                          className="ms-input"
                          style={{ width: "100%", fontSize: 12 }}
                        />
                      </div>
                    </div>
                  )}

                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {(selected.table?.mode ?? "auto") === "repeat" && (
                      <button
                        type="button"
                        onClick={() => { setColGuideTargetId(null); setRowTemplateTargetId(selected.id); }}
                        className={`ms-btn-sm${rowTemplateTargetId === selected.id ? " oc-mode-btn-active" : ""}`}
                      >
                        행 템플릿 지정
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => { setRowTemplateTargetId(null); setColGuideTargetId(selected.id); }}
                      className={`ms-btn-sm${colGuideTargetId === selected.id ? " oc-mode-btn-active" : ""}`}
                    >
                      세로 가이드 찍기
                    </button>

                    {(selected.table?.mode ?? "auto") === "repeat" && (
                      <button
                        type="button"
                        onClick={() => { setRowTemplateTargetId(null); setColGuideTargetId(null); clearTableMeta(selected.id); }}
                        className="ms-btn-sm"
                        disabled={!selected.table?.rowTemplate && !Array.isArray(selected.table?.rows)}
                      >
                        행 템플릿 해제
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => { setColGuideTargetId(null); clearTableColGuides(selected.id); }}
                      className="ms-btn-sm"
                      disabled={normalizeColGuides(selected.table?.colGuides).length === 0}
                    >
                      가이드 전체 삭제
                    </button>

                    {rowTemplateTargetId === selected.id && (
                      <button
                        type="button"
                        onClick={() => setRowTemplateTargetId(null)}
                        className="ms-btn-sm"
                        style={{ borderColor: "rgba(244,63,94,0.4)", color: "#be123c" }}
                      >
                        템플릿 지정 취소
                      </button>
                    )}

                    {colGuideTargetId === selected.id && (
                      <button
                        type="button"
                        onClick={() => setColGuideTargetId(null)}
                        className="ms-btn-sm"
                        style={{ borderColor: "rgba(244,63,94,0.4)", color: "#be123c" }}
                      >
                        가이드 찍기 취소
                      </button>
                    )}
                  </div>

                  {(selected.table?.mode ?? "auto") === "auto" && (
                    <div className="oc-info-text">
                      가변 그리드 모드에서는 <b>행 템플릿/rows</b>를 저장하지 않습니다. 대신 <b>세로 가이드(컬럼)</b>와
                      <b> 종료 키워드</b>를 기반으로 실제 OCR 단계에서 행을 자동 감지합니다.
                    </div>
                  )}

                  {rowTemplateTargetId === selected.id && (
                    <div className="oc-info-text">
                      캔버스에서 <b>표 내부 한 줄(행)</b>을 드래그해서 지정하세요.
                    </div>
                  )}

                  {colGuideTargetId === selected.id && (
                    <div className="oc-info-text">
                      캔버스에서 <b>표 안</b>을 클릭하면 세로 가이드선이 추가됩니다. (선 위를 드래그하면 위치 조절)
                    </div>
                  )}

                  {/* 세로 가이드 목록 */}
                  {normalizeColGuides(selected.table?.colGuides).length > 0 && (
                    <div style={{ marginTop: 10 }}>
                      <div className="oc-muted" style={{ fontSize: 12, marginBottom: 6 }}>
                        세로 가이드선 목록
                      </div>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {normalizeColGuides(selected.table?.colGuides).map((g, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => removeTableColGuide(selected.id, idx)}
                            className="ms-btn-sm"
                            style={{ borderRadius: 999 }}
                            title="클릭하면 해당 가이드 삭제"
                          >
                            {Math.round(g * 1000) / 10}% ✕
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="oc-preview-box">
                <div className="oc-muted" style={{ fontSize: 12, marginBottom: 8 }}>미리보기</div>

                {selected.fieldType !== "multi" ? (
                  <div className="oc-preview-img-wrap">
                    {selectedThumbLarge ? (
                      <img
                        src={selectedThumbLarge}
                        alt="selected-crop"
                        style={{ width: "100%", height: "100%", objectFit: "contain" }}
                      />
                    ) : (
                      <span className="oc-muted" style={{ fontSize: 12 }}>
                        이미지 로딩 후 표시됩니다.
                      </span>
                    )}
                  </div>
                ) : (
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {selectedMultiThumbsLarge.length === 0 ? (
                      <span className="oc-muted" style={{ fontSize: 12 }}>
                        이미지 로딩 후 표시됩니다.
                      </span>
                    ) : (
                      selectedMultiThumbsLarge.map((u, idx) => (
                        <div
                          key={idx}
                          style={{
                            width: 96, height: 72,
                            border: "1px solid var(--border)",
                            borderRadius: 10,
                            background: "var(--panel)",
                            overflow: "hidden",
                            display: "grid",
                            placeItems: "center",
                          }}
                          title={`part ${idx + 1}`}
                        >
                          <img src={u} alt={`sel-m-${idx}`} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      {/* scroll wrapper end */}
      </div>
    </aside>
  );
}
