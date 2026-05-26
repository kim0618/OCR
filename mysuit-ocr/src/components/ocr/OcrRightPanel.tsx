"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import type { FieldType, LoadedImage, Region, TableColumnDef } from "./core/types";
import { normalizeRatios, calcMultiSubRegions } from "./core/ops";
import { normalizeColGuides } from "./core/table";

type Props = {
  imgRef: React.RefObject<HTMLImageElement | null>;
  templateName: string;
  setTemplateName: React.Dispatch<React.SetStateAction<string>>;
  documentType: string;
  setDocumentType: (value: string) => void;
  loaded: LoadedImage | null;
  regions: Region[];
  setRegions: React.Dispatch<React.SetStateAction<Region[]>>;
  selectedId: string | null;
  setSelectedId: React.Dispatch<React.SetStateAction<string | null>>;
  rowTemplateTargetId: string | null;
  setRowTemplateTargetId: React.Dispatch<React.SetStateAction<string | null>>;
  colGuideTargetId: string | null;
  setColGuideTargetId: React.Dispatch<React.SetStateAction<string | null>>;
  rowAdjustTargetId?: string | null;
  setRowAdjustTargetId?: React.Dispatch<React.SetStateAction<string | null>>;
  updateName: (id: string, name: string) => void;
  deleteRegion: (id: string) => void;
};

export default function OcrRightPanel(props: Props) {
  const {
    imgRef,
    templateName,
    setTemplateName,
    documentType,
    setDocumentType,
    loaded,
    regions,
    setRegions,
    selectedId,
    setSelectedId,
    rowTemplateTargetId,
    setRowTemplateTargetId,
    colGuideTargetId,
    setColGuideTargetId,
    rowAdjustTargetId,
    setRowAdjustTargetId,
    deleteRegion,
  } = props;

  const selected = selectedId ? (regions.find((r) => r.id === selectedId) ?? null) : null;

  // ── stopKeywords raw (table only) ─────────────────────────────────────
  const [stopKeywordsRaw, setStopKeywordsRaw] = useState<string>("");
  useEffect(() => {
    if (!selected || selected.fieldType !== "table") { setStopKeywordsRaw(""); return; }
    setStopKeywordsRaw((selected.table?.stopKeywords ?? []).join(", "));
  }, [selectedId, selected?.fieldType, selected?.table?.stopKeywords]);

  // ── table name raw (table only) ───────────────────────────────────────
  const [tableNameRaw, setTableNameRaw] = useState<string>("");
  useEffect(() => {
    if (!selected || selected.fieldType !== "table") { setTableNameRaw(""); return; }
    setTableNameRaw(selected.table?.tableName ?? "");
  }, [selectedId, selected?.fieldType]);

  // ── region update helpers ─────────────────────────────────────────────
  function patchRegion(id: string, patch: Partial<Region>) {
    setRegions((prev) => prev.map((r) => r.id === id ? { ...r, ...patch } : r));
  }

  function updateTableMeta(tableId: string, patch: Partial<NonNullable<Region["table"]>>) {
    setRegions((prev) =>
      prev.map((r) => r.id !== tableId ? r : { ...r, table: { ...(r.table ?? {}), ...patch } }),
    );
  }

  function handleRowKoChange(regionId: string, val: string) {
    patchRegion(regionId, { koField: val });
  }

  function handleRowEnChange(regionId: string, val: string) {
    patchRegion(regionId, { enField: val });
  }

  // ── table column helpers ──────────────────────────────────────────────
  function getColumns(r: Region): TableColumnDef[] {
    if (r.fieldType !== "table") return [];
    const existing = r.table?.columns ?? [];
    const guideCount = normalizeColGuides(r.table?.colGuides).length;
    const colCount = guideCount + 1;
    if (colCount <= 0) return existing;
    if (existing.length >= colCount) return existing.slice(0, colCount);
    const result: TableColumnDef[] = [];
    for (let i = 0; i < colCount; i++) result.push(existing[i] ?? { index: i });
    return result;
  }

  function updateColumn(tableId: string, idx: number, patch: Partial<TableColumnDef>) {
    setRegions((prev) =>
      prev.map((r) => {
        if (r.id !== tableId || r.fieldType !== "table") return r;
        const next = getColumns(r).map((c) => c.index === idx ? { ...c, ...patch } : c);
        return { ...r, table: { ...(r.table ?? {}), columns: next } };
      }),
    );
  }

  // ── table meta helpers ────────────────────────────────────────────────
  function clearTableMeta(tableId: string) {
    setRegions((prev) =>
      prev.map((r) =>
        r.id !== tableId ? r
          : r.fieldType === "table"
            ? { ...r, table: { ...(r.table ?? {}), mode: r.table?.mode ?? "repeat", rowTemplate: undefined, rows: undefined } }
            : r,
      ),
    );
  }

  function setTableMode(tableId: string, mode: "repeat" | "auto") {
    setRegions((prev) =>
      prev.map((r) => {
        if (r.id !== tableId || r.fieldType !== "table") return r;
        const cur = r.table ?? {};
        return { ...r, table: mode === "auto" ? { ...cur, mode, rowTemplate: undefined, rows: undefined } : { ...cur, mode } };
      }),
    );
  }

  function updateStopKeywords(tableId: string, raw: string) {
    const list = raw.split(",").map((s) => s.trim()).filter(Boolean).slice(0, 30);
    setRegions((prev) =>
      prev.map((r) =>
        r.id !== tableId ? r
          : r.fieldType === "table"
            ? { ...r, table: { ...(r.table ?? {}), stopKeywords: list.length ? list : undefined } }
            : r,
      ),
    );
  }

  function clearTableColGuides(tableId: string) {
    setRegions((prev) =>
      prev.map((r) =>
        r.id !== tableId ? r
          : r.fieldType === "table" ? { ...r, table: { ...(r.table ?? {}), colGuides: undefined } } : r,
      ),
    );
  }

  function removeTableColGuide(tableId: string, index: number) {
    setRegions((prev) =>
      prev.map((r) => {
        if (r.id !== tableId || r.fieldType !== "table") return r;
        const next = normalizeColGuides(r.table?.colGuides).filter((_, i) => i !== index);
        return { ...r, table: { ...(r.table ?? {}), colGuides: next.length ? next : undefined } };
      }),
    );
  }

  // ── crop preview ──────────────────────────────────────────────────────
  const loadedRef = useRef<LoadedImage | null>(loaded);
  const cropCacheRef = useRef<Map<string, string>>(new Map());
  useEffect(() => { loadedRef.current = loaded; }, [loaded]);
  useEffect(() => { cropCacheRef.current.clear(); }, [loaded?.src]);

  function cropToDataUrl(opts: { sx: number; sy: number; sw: number; sh: number; targetMax: number }): string | null {
    const l = loadedRef.current;
    const imgEl = imgRef.current;
    if (!l || !imgEl) return null;
    const sx = Math.max(0, Math.floor(opts.sx)), sy = Math.max(0, Math.floor(opts.sy));
    const sw = Math.max(1, Math.floor(opts.sw)), sh = Math.max(1, Math.floor(opts.sh));
    const tMax = Math.max(16, Math.floor(opts.targetMax));
    const key = `${l.src}|${sx}|${sy}|${sw}|${sh}|${tMax}`;
    const cached = cropCacheRef.current.get(key);
    if (cached) return cached;
    try {
      const canvas = document.createElement("canvas");
      const ar = sw / sh;
      canvas.width = Math.max(1, ar >= 1 ? tMax : Math.round(tMax * ar));
      canvas.height = Math.max(1, ar >= 1 ? Math.round(tMax / ar) : tMax);
      const ctx = canvas.getContext("2d");
      if (!ctx) return null;
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(imgEl, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
      const url = canvas.toDataURL("image/png");
      cropCacheRef.current.set(key, url);
      return url;
    } catch { return null; }
  }

  const selectedThumbLarge = useMemo(() => {
    if (!selected || selected.fieldType === "multi") return null;
    return cropToDataUrl({ sx: selected.x, sy: selected.y, sw: selected.width, sh: selected.height, targetMax: 260 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, selected?.x, selected?.y, selected?.width, selected?.height, loaded?.src]);

  const selectedMultiThumbsLarge = useMemo(() => {
    if (!selected || selected.fieldType !== "multi") return [];
    const parts = (selected.parts ?? 2) as 2 | 3;
    const ratios = normalizeRatios(parts, selected.ratios);
    return calcMultiSubRegions({ ...selected, parts, ratios })
      .map((s) => cropToDataUrl({ sx: s.x, sy: s.y, sw: s.width, sh: s.height, targetMax: 180 }))
      .filter((x): x is string => Boolean(x));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, selected?.x, selected?.y, selected?.width, selected?.height, selected?.parts, JSON.stringify(selected?.ratios ?? []), loaded?.src]);

  // ── styles ────────────────────────────────────────────────────────────
  const miniInput: React.CSSProperties = {
    background: "var(--panel2)",
    border: "1px solid rgba(255,255,255,0.09)",
    borderRadius: 5,
    padding: "4px 7px",
    color: "var(--text)",
    fontSize: 12,
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  };

  const fieldTypeLabel = (t: FieldType) =>
    t === "field" ? "필드" : t === "multi" ? "멀티" : t === "check" ? "체크" : "테이블";

  return (
    <aside className="oc-panel" style={{ flex: 1, minHeight: 0 }}>

      {/* ── 템플릿 명 ── */}
      <div className="oc-template-input-wrap">
        <h2 className="oc-label">템플릿 명</h2>
        <input
          value={templateName}
          onChange={(e) => setTemplateName(e.target.value)}
          placeholder="템플릿 명"
          className="ms-input"
          style={{ width: "100%" }}
        />
        <h2 className="oc-label" style={{ marginTop: 8 }}>문서 유형</h2>
        <select
          value={documentType}
          onChange={(e) => setDocumentType(e.target.value)}
          className="ms-input"
          style={{ width: "100%" }}
        >
          <option value="">-- 선택 --</option>
          <option value="invoice_statement">invoice_statement (거래명세서)</option>
          <option value="card_receipt">card_receipt (카드영수증)</option>
          <option value="pos_receipt">pos_receipt (POS영수증)</option>
          <option value="food_cafe_receipt">food_cafe_receipt (음식/카페)</option>
          <option value="finance_slip">finance_slip (금융전표)</option>
          <option value="medical_receipt">medical_receipt (의료영수증)</option>
          <option value="unknown">unknown</option>
        </select>
      </div>

      {/* ── 스크롤 영역 ── */}
      <div className="oc-panel-scroll">

        {/* ── 출력 필드 정의 ── */}
        <div className="oc-section">
          <div className="oc-section-header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <h3 className="oc-section-title" style={{ margin: 0 }}>출력 필드 정의</h3>
            <button
              type="button"
              onClick={() => { if (selected) deleteRegion(selected.id); }}
              disabled={!selected}
              className="ms-btn-sm"
              style={{
                fontSize: 11,
                color: selected ? "#ef4444" : "var(--muted)",
                borderColor: selected ? "rgba(239,68,68,0.4)" : "var(--border)",
                opacity: selected ? 1 : 0.5,
                cursor: selected ? "pointer" : "not-allowed",
              }}
            >
              삭제
            </button>
          </div>

          {regions.length === 0 ? (
            <div className="oc-muted" style={{ fontSize: 13, marginTop: 10 }}>영역이 없습니다.</div>
          ) : (
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
              {/* 헤더 */}
              <div style={{
                display: "grid", gridTemplateColumns: "28px 1fr 1fr",
                gap: 6, alignItems: "center",
                padding: "8px 8px",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid var(--border)",
                borderRadius: 8,
              }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>No</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>영문 필드명</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>한글 필드명</span>
              </div>

              {/* 데이터 행 */}
              {regions.map((r, idx) => {
                const isSel = r.id === selectedId;
                const enValue = r.enField || r.id || "";
                const koValue = r.koField || "";
                return (
                  <div
                    key={r.id}
                    onClick={() => setSelectedId(r.id)}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "28px 1fr 1fr",
                      gap: 6,
                      alignItems: "center",
                      padding: "7px 8px",
                      background: isSel ? "var(--accentBg)" : "var(--panel2)",
                      border: isSel ? "1px solid var(--accent)" : "1px solid var(--border)",
                      borderRadius: 10,
                      cursor: "pointer",
                    }}
                  >
                    <span style={{ textAlign: "center", fontSize: 13, fontWeight: 700, color: isSel ? "var(--accent)" : "var(--text)" }}>
                      {idx + 1}
                    </span>

                    {/* 영문 필드명 */}
                    <input
                      value={enValue}
                      onChange={(e) => handleRowEnChange(r.id, e.target.value)}
                      onFocus={() => setSelectedId(r.id)}
                      placeholder="영문 필드명"
                      className="ms-input"
                      style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                    />

                    {/* 한글 필드명 (테이블 포함, 모든 타입에서 편집 가능) */}
                    <input
                      value={koValue}
                      onChange={(e) => handleRowKoChange(r.id, e.target.value)}
                      onFocus={() => setSelectedId(r.id)}
                      placeholder="한글 필드명"
                      className="ms-input"
                      style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                    />
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── 선택 영역 = 미리보기 + 테이블필드 컨트롤 ── */}
        <div className="oc-section">
          <div className="oc-section-header">
            <h3 className="oc-section-title" style={{ margin: 0 }}>
              선택 영역 {selected && <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 500, marginLeft: 6 }}>({selected.id})</span>}
            </h3>
          </div>

          {!selected ? (
            <div className="oc-muted" style={{ fontSize: 13, marginTop: 10 }}>선택된 영역이 없습니다.</div>
          ) : (
            <div style={{ fontSize: 13, color: "#555", lineHeight: 1.6, marginTop: 10 }}>

              {/* ── 테이블필드 컨트롤 (컬럼 정의는 제거, 가변/고정/세로가이드/종료키워드만) ── */}
              {selected.fieldType === "table" && (
                <div className="oc-table-controls">

                  {/* 그리드 모드 */}
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)", letterSpacing: 0.3, textTransform: "uppercase", marginBottom: 6 }}>
                    그리드 모드
                  </div>
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

                  {/* 가변 그리드: 종료 키워드 */}
                  {(selected.table?.mode ?? "auto") === "auto" && (
                    <div style={{ marginBottom: 10 }}>
                      <div className="oc-muted" style={{ fontSize: 12, marginBottom: 6 }}>종료 키워드 (쉼표로 구분)</div>
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
                  )}

                  {/* 가이드 버튼 그룹 */}
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
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
                    {(selected.table?.mode ?? "auto") === "repeat" && setRowAdjustTargetId && (
                      <button
                        type="button"
                        onClick={() => {
                          setRowTemplateTargetId(null);
                          setColGuideTargetId(null);
                          setRowAdjustTargetId(
                            rowAdjustTargetId === selected.id ? null : selected.id,
                          );
                        }}
                        className={`ms-btn-sm${rowAdjustTargetId === selected.id ? " oc-mode-btn-active" : ""}`}
                        disabled={!Array.isArray(selected.table?.rows) || (selected.table?.rows?.length ?? 0) === 0}
                        title="각 행의 하단 경계를 드래그해서 행 높이 조정"
                      >
                        행 개별 조정
                      </button>
                    )}
                    {(selected.table?.mode ?? "auto") === "repeat" && (
                      <button
                        type="button"
                        onClick={() => { setRowTemplateTargetId(null); setColGuideTargetId(null); setRowAdjustTargetId?.(null); clearTableMeta(selected.id); }}
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
                      <button type="button" onClick={() => setRowTemplateTargetId(null)} className="ms-btn-sm" style={{ borderColor: "rgba(244,63,94,0.4)", color: "#be123c" }}>
                        지정 취소
                      </button>
                    )}
                    {colGuideTargetId === selected.id && (
                      <button type="button" onClick={() => setColGuideTargetId(null)} className="ms-btn-sm" style={{ borderColor: "rgba(244,63,94,0.4)", color: "#be123c" }}>
                        찍기 취소
                      </button>
                    )}
                    {rowAdjustTargetId === selected.id && setRowAdjustTargetId && (
                      <button type="button" onClick={() => setRowAdjustTargetId(null)} className="ms-btn-sm" style={{ borderColor: "rgba(244,63,94,0.4)", color: "#be123c" }}>
                        조정 종료
                      </button>
                    )}
                  </div>

                  {(selected.table?.mode ?? "auto") === "auto" && (
                    <div className="oc-info-text">
                      가변 그리드: <b>세로 가이드(컬럼)</b>와 <b>종료 키워드</b> 기반으로 OCR 단계에서 행을 자동 감지합니다.
                    </div>
                  )}
                  {rowTemplateTargetId === selected.id && (
                    <div className="oc-info-text">캔버스에서 <b>표 내부 한 줄(행)</b>을 드래그해서 지정하세요.</div>
                  )}
                  {colGuideTargetId === selected.id && (
                    <div className="oc-info-text">캔버스에서 <b>표 안</b>을 클릭하면 세로 가이드선이 추가됩니다.</div>
                  )}
                  {rowAdjustTargetId === selected.id && (
                    <div className="oc-info-text">각 행의 <b>아래쪽 노란 핸들</b>을 위/아래로 드래그해서 행 높이를 조정하세요.</div>
                  )}

                  {/* 세로 가이드 목록 */}
                  {normalizeColGuides(selected.table?.colGuides).length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <div className="oc-muted" style={{ fontSize: 12, marginBottom: 6 }}>세로 가이드선</div>
                      <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                        {normalizeColGuides(selected.table?.colGuides).map((g, idx) => (
                          <button key={idx} type="button" onClick={() => removeTableColGuide(selected.id, idx)} className="ms-btn-sm" style={{ borderRadius: 999 }} title="클릭 시 삭제">
                            {Math.round(g * 1000) / 10}% ✕
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── 미리보기 ── */}
              <div className="oc-preview-box">
                <div className="oc-muted" style={{ fontSize: 12, marginBottom: 8 }}>미리보기</div>
                {selected.fieldType !== "multi" ? (
                  <div className="oc-preview-img-wrap">
                    {selectedThumbLarge ? (
                      <img src={selectedThumbLarge} alt="selected-crop" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                    ) : (
                      <span className="oc-muted" style={{ fontSize: 12 }}>이미지 로딩 후 표시됩니다.</span>
                    )}
                  </div>
                ) : (
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {selectedMultiThumbsLarge.length === 0 ? (
                      <span className="oc-muted" style={{ fontSize: 12 }}>이미지 로딩 후 표시됩니다.</span>
                    ) : (
                      selectedMultiThumbsLarge.map((u, idx) => (
                        <div key={idx} style={{ width: 96, height: 72, border: "1px solid var(--border)", borderRadius: 10, background: "var(--panel)", overflow: "hidden", display: "grid", placeItems: "center" }}>
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
    </aside>
  );
}
