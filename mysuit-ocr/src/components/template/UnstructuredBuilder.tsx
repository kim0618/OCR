"use client";

import React, { useEffect, useState } from "react";
import { useUi } from "../layout/AppProviders";
import {
  normalizeUnstructuredTemplate,
  serializeUnstructuredTemplate,
  createDefaultInfoField,
  createDefaultTableDef,
  createDefaultTableColumn,
  type UnstructuredInfoField,
  type UnstructuredTableDef,
  type UnstructuredTableColumn,
} from "./utils/unstructuredDefinition";
import {
  CANONICAL_COLUMN_OPTIONS,
  canonicalColumnLabel,
  findCanonicalValueByKey,
} from "./utils/canonicalColumnOptions";

type Field = {
  no: number;
  enField: string;
  koField: string;
};

// TPL-14A — 출력 정의 영역(일반 영역 / 테이블 / 컬럼)을 하나의 선택 모델로
// 통일하기 위한 단일 selection target.
type SelectedUnstructuredTarget =
  | { type: "info"; index: number }
  | { type: "table"; tableIndex: number }
  | { type: "column"; tableIndex: number; columnIndex: number }
  | null;

const LOCAL_TEMPLATES_KEY = "mysuit_ocr_templates";

// MVP 문서 유형 — TPL-5 spec(영수증/거래명세서/세금계산서). Test 전용
// profiles.ts에 의존하지 않기 위해 여기에 직접 선언한다. 빈 문자열이면
// payload에서 documentType 키가 omit되도록 serialize helper가 처리한다.
const DOCUMENT_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "선택 안 함" },
  { value: "receipt", label: "영수증" },
  { value: "invoice_statement", label: "거래명세서" },
  { value: "tax_invoice", label: "세금계산서" },
];

export default function UnstructuredBuilder({
  selectedTemplate = null,
  selectedTemplateId = null,
}: {
  selectedTemplate?: any | null;
  selectedTemplateId?: string | null;
}) {
  const isEditMode = !!selectedTemplateId;
  const ui = useUi();
  const [templateName, setTemplateName] = useState("");
  const [documentType, setDocumentType] = useState("");
  const [fields, setFields] = useState<Field[]>([]);
  const [tables, setTables] = useState<UnstructuredTableDef[]>([]);
  // TPL-14A — info/table/column 선택 통합 상태
  const [selectedTarget, setSelectedTarget] = useState<SelectedUnstructuredTarget>(null);

  // ── 일반 영역 helpers ────────────────────────────────────────────────
  const addField = () => {
    const nextNo = fields.length > 0 ? Math.max(...fields.map((f) => f.no)) + 1 : 1;
    const def = createDefaultInfoField(nextNo);
    const newIndex = fields.length;
    setFields([...fields, { no: nextNo, enField: def.labelEn ?? "", koField: def.labelKo }]);
    setSelectedTarget({ type: "info", index: newIndex });
  };

  const updateField = (no: number, key: "enField" | "koField", v: string) => {
    setFields(fields.map((f) => f.no === no ? { ...f, [key]: v } : f));
  };

  // ── 테이블 정의 helpers ──────────────────────────────────────────────
  const addTable = () => {
    const order = tables.length + 1;
    const def = createDefaultTableDef(order);
    def.columns = [createDefaultTableColumn(1)];
    const newIndex = tables.length;
    setTables([...tables, def]);
    setSelectedTarget({ type: "table", tableIndex: newIndex });
  };

  const updateTable = (tableIdx: number, patch: Partial<UnstructuredTableDef>) => {
    setTables(tables.map((t, i) => (i === tableIdx ? { ...t, ...patch } : t)));
  };

  const addColumn = (tableIdx: number) => {
    const newColIdx = tables[tableIdx]?.columns?.length ?? 0;
    setTables(
      tables.map((t, i) => {
        if (i !== tableIdx) return t;
        const nextOrder = (t.columns?.length ?? 0) + 1;
        // helper가 column_N 같은 기본값을 채우지만, UI에서는 영문/한글
        // 둘 다 비워서 사용자가 직접 입력하거나 표준 컬럼 select로 채우게 한다.
        const col: UnstructuredTableColumn = {
          ...createDefaultTableColumn(nextOrder),
          columnKey: "",
          labelKo: "",
        };
        return { ...t, columns: [...(t.columns ?? []), col] };
      }),
    );
    setSelectedTarget({ type: "column", tableIndex: tableIdx, columnIndex: newColIdx });
  };

  const updateColumn = (
    tableIdx: number,
    colIdx: number,
    patch: Partial<UnstructuredTableColumn>,
  ) => {
    setTables(
      tables.map((t, i) => {
        if (i !== tableIdx) return t;
        return {
          ...t,
          columns: t.columns.map((c, j) => (j === colIdx ? { ...c, ...patch } : c)),
        };
      }),
    );
  };

  // TPL-14A — 선택 대상에 따른 단일 삭제 진입점
  const handleSelectedDelete = () => {
    if (!selectedTarget) return;
    if (selectedTarget.type === "info") {
      // info 삭제 + no 재번호 부여
      const idx = selectedTarget.index;
      setFields((prev) =>
        prev
          .filter((_, i) => i !== idx)
          .map((f, i) => ({ ...f, no: i + 1 })),
      );
    } else if (selectedTarget.type === "table") {
      const idx = selectedTarget.tableIndex;
      setTables((prev) => prev.filter((_, i) => i !== idx));
    } else if (selectedTarget.type === "column") {
      const { tableIndex, columnIndex } = selectedTarget;
      setTables((prev) =>
        prev.map((t, i) =>
          i !== tableIndex
            ? t
            : { ...t, columns: (t.columns ?? []).filter((_, j) => j !== columnIndex) },
        ),
      );
    }
    setSelectedTarget(null);
  };

  // TPL-14A — 선택 대상에 따른 라벨 정책
  const selectedDeleteLabel = (() => {
    if (!selectedTarget) return "삭제";
    if (selectedTarget.type === "info") return "영역 삭제";
    if (selectedTarget.type === "table") return "테이블 삭제";
    if (selectedTarget.type === "column") return "컬럼 삭제";
    return "삭제";
  })();
  const isSelectedDeleteDisabled = selectedTarget == null;

  useEffect(() => {
    if (!selectedTemplate) return;
    const normalized = normalizeUnstructuredTemplate(selectedTemplate);
    setTemplateName(normalized.templateName ?? "");
    setDocumentType(normalized.documentType ?? "");
    setFields(
      normalized.fields.map(({ no, enField, koField }) => ({ no, enField, koField })),
    );
    setTables(normalized.tables);
    setSelectedTarget(null);
  }, [selectedTemplate]);

  const handleSave = async () => {
    const name = templateName.trim();
    if (!name) { await ui.alert("템플릿 명을 입력해주세요."); return; }
    if (fields.length === 0 && tables.length === 0) {
      await ui.alert("영역 또는 테이블을 하나 이상 정의해주세요.");
      return;
    }
    // 저장/수정 전 확인 다이얼로그
    const proceed = await ui.confirm({
      title: isEditMode ? "템플릿 수정" : "템플릿 저장",
      message: `"${name}" 템플릿을 ${isEditMode ? "수정" : "저장"}하시겠습니까?`,
      okText: isEditMode ? "수정" : "저장",
      cancelText: "취소",
    });
    if (!proceed) return;
    // UI fields[] → info[] (source of truth); documentType과 tables는 UI
    // state 그대로 직렬화. documentType이 빈 문자열이면 helper가 payload에서
    // 키 자체를 omit한다 (auto-fill 금지).
    const info: UnstructuredInfoField[] = fields.map((f) => {
      const en = (f.enField ?? "").trim();
      const ko = (f.koField ?? "").trim();
      const entry: UnstructuredInfoField = {
        key: en.length > 0 ? en : `info_${f.no}`,
        labelKo: ko,
        order: f.no,
        no: f.no,
      };
      if (en.length > 0) entry.labelEn = en;
      return entry;
    });
    const trimmedDocType = documentType.trim();
    const template_json = serializeUnstructuredTemplate({
      templateName: name,
      documentType: trimmedDocType.length > 0 ? trimmedDocType : undefined,
      info,
      tables,
    });
    const localTemplate = {
      template_id: selectedTemplateId || `LOCAL-${Date.now()}`,
      template_name: name,
      template_json,
      updated_at: new Date().toISOString(),
    };
    try {
      const current = JSON.parse(localStorage.getItem(LOCAL_TEMPLATES_KEY) || "[]");
      const list = Array.isArray(current) ? current : [];
      const filtered = list.filter((item: any) =>
        item?.template_id !== localTemplate.template_id &&
        item?.template_name !== name,
      );
      const next = [localTemplate, ...filtered];
      localStorage.setItem(LOCAL_TEMPLATES_KEY, JSON.stringify(next));
      window.dispatchEvent(new Event("mysuit-ocr-template-saved"));
    } catch (err) {
      console.error("[local unstructured template save error]", err);
    }
    await ui.alert(isEditMode ? "템플릿이 수정되었습니다." : "템플릿이 저장되었습니다.");
  };

  const handleDelete = async () => {
    if (selectedTemplateId) {
      // 편집 모드 — 저장된 템플릿 삭제
      const ok = await ui.confirm({
        title: "템플릿 삭제",
        message: `"${templateName || selectedTemplateId}" 템플릿을 삭제하시겠습니까?`,
        okText: "삭제",
        cancelText: "취소",
      });
      if (!ok) return;
      try {
        const current = JSON.parse(localStorage.getItem(LOCAL_TEMPLATES_KEY) || "[]");
        const list = Array.isArray(current) ? current : [];
        const next = list.filter((item: any) => item?.template_id !== selectedTemplateId);
        localStorage.setItem(LOCAL_TEMPLATES_KEY, JSON.stringify(next));
        window.dispatchEvent(new Event("mysuit-ocr-template-saved"));
      } catch (err) {
        console.error("[unstructured template delete error]", err);
      }
      setTemplateName("");
      setDocumentType("");
      setFields([]);
      setTables([]);
      setSelectedTarget(null);
      await ui.alert("템플릿이 삭제되었습니다.");
    } else {
      // 새 비정형 작성 중 — 폼 초기화
      const ok = await ui.confirm({
        title: "초기화",
        message: "작성 중인 내용을 초기화하시겠습니까?",
        okText: "초기화",
        cancelText: "취소",
      });
      if (!ok) return;
      setTemplateName("");
      setDocumentType("");
      setFields([]);
      setTables([]);
      setSelectedTarget(null);
    }
  };

  const CARDS = [
    { icon: "📄", title: "다양한 문서 지원", desc: "계약서·이메일·보고서 등 형식이 달라도 적용 가능" },
    { icon: "🏷️", title: "필드 자유 정의", desc: "추출할 항목을 영문·한글로 직접 입력해 커스터마이징" },
    { icon: "🔍", title: "위치 무관 인식", desc: "고정 위치 없이 문서 어디서든 원하는 정보를 찾아냄" },
  ];

  return (
    <div style={{ display: "flex", flex: 1, gap: 8, minHeight: 0, height: "100%" }}>

      {/* ── 좌측: 비정형 설명 (Template 처럼 외곽 panel + 내부 점선 dropzone) ── */}
      <div className="uw-upload-panel" style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
        <div
          className="uw-dropzone"
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 24,
            padding: "32px 40px",
            overflow: "hidden",
          }}
        >
        <div style={{ fontSize: 40, opacity: 0.25 }}>📋</div>
        <div style={{ textAlign: "center", maxWidth: 460 }}>
          <div style={{ fontSize: 17, fontWeight: 800, color: "var(--text)", marginBottom: 10 }}>
            비정형 생성이란?
          </div>
          <div style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.85 }}>
            고정된 양식이 없는 문서에서 원하는 정보를 자유롭게 추출하는 방식입니다.
            <br />
            우측에서 <strong style={{ color: "var(--text)" }}>출력 필드</strong>를 정의하면
            문서 내 해당 정보를 자동으로 찾아 반환합니다.
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
          {CARDS.map((c) => (
            <div
              key={c.title}
              style={{
                width: 152,
                background: "var(--panel2)",
                borderRadius: 10,
                border: "1px solid rgba(255,255,255,0.07)",
                padding: "16px 14px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 8,
                textAlign: "center",
              }}
            >
              <span style={{ fontSize: 22 }}>{c.icon}</span>
              <span style={{ fontSize: 11, fontWeight: 800, color: "var(--text)", whiteSpace: "nowrap" }}>{c.title}</span>
              <span style={{ fontSize: 11, color: "var(--muted)", lineHeight: 1.6 }}>{c.desc}</span>
            </div>
          ))}
        </div>
        </div>
      </div>

      {/* ── 우측: 편집 패널 ── */}
      <div style={{ width: 420, flexShrink: 0, display: "flex", flexDirection: "column", gap: 8, minHeight: 0 }}>

        {/* 삭제 / 저장 — 템플릿 전체에 대한 삭제(편집 모드) 또는 작성 폼 초기화 */}
        <div style={{
          flexShrink: 0,
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: "10px 12px",
          display: "flex",
          gap: 8,
          justifyContent: "flex-end",
        }}>
          <button onClick={handleDelete} className="ms-btn">삭제</button>
          <button onClick={() => void handleSave()} className="ms-btn"
            style={{ background: "var(--accent)", color: "#fff", border: "none" }}>
            {isEditMode ? "수정" : "저장"}
          </button>
        </div>

        {/* 템플릿명 + 문서유형 + 출력 필드 — Template oc-panel처럼 padding: 12px */}
        <div style={{
          flex: 1,
          minHeight: 0,
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: 12,
          display: "flex",
          flexDirection: "column",
          overflow: "auto",
        }}>
          {/* 템플릿명 + 문서 유형 */}
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
              {DOCUMENT_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* 출력 정의 — 일반 영역 + 테이블 정의를 모두 담는 oc-section */}
          <div className="oc-section">
            <div className="oc-section-header">
              <h3 className="oc-section-title" style={{ margin: 0 }}>출력 정의</h3>
              <div style={{ display: "flex", gap: 5 }}>
                <button onClick={addField} className="ms-btn-sm">영역 정의</button>
                <button onClick={addTable} className="ms-btn-sm">테이블 정의</button>
                {/* TPL-14A — 선택 대상(영역/테이블/컬럼)에 따라 라벨이 바뀌는 단일 삭제 버튼 */}
                <button
                  onClick={handleSelectedDelete}
                  disabled={isSelectedDeleteDisabled}
                  className="ms-btn-sm"
                  style={{
                    color: isSelectedDeleteDisabled ? "var(--muted)" : "#ef4444",
                    borderColor: isSelectedDeleteDisabled
                      ? "var(--border)"
                      : "rgba(239,68,68,0.4)",
                    opacity: isSelectedDeleteDisabled ? 0.55 : 1,
                    cursor: isSelectedDeleteDisabled ? "not-allowed" : "pointer",
                  }}>
                  {selectedDeleteLabel}
                </button>
              </div>
            </div>

            {/* ── 일반 영역 ── */}
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", letterSpacing: 0.3, textTransform: "uppercase", marginBottom: 6 }}>
                일반 영역
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {/* 헤더(No/영문/한글)는 fields가 1개 이상일 때만 표시 — 빈 상태에서 어색한 빈 그리드가 보이지 않도록 */}
                {fields.length > 0 && (
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
                )}

                {fields.length === 0 ? (
                  <div style={{ fontSize: 13, color: "var(--muted)", padding: "4px 0" }}>정의된 영역이 없습니다.</div>
                ) : (
                  fields.map((f, infoIdx) => {
                    const isSel = selectedTarget?.type === "info" && selectedTarget.index === infoIdx;
                    return (
                      <div
                        key={f.no}
                        onClick={() => setSelectedTarget({ type: "info", index: infoIdx })}
                        style={{
                          display: "grid", gridTemplateColumns: "28px 1fr 1fr",
                          gap: 6, alignItems: "center",
                          padding: "7px 8px",
                          background: isSel ? "var(--accentBg)" : "var(--panel2)",
                          border: isSel ? "1px solid var(--accent)" : "1px solid var(--border)",
                          borderRadius: 10,
                          cursor: "pointer",
                        }}
                      >
                        <span style={{ textAlign: "center", fontSize: 13, fontWeight: 700, color: isSel ? "var(--accent)" : "var(--text)" }}>
                          {f.no}
                        </span>
                        <input
                          value={f.enField}
                          onChange={(e) => updateField(f.no, "enField", e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          onFocus={() => setSelectedTarget({ type: "info", index: infoIdx })}
                          placeholder="영문 필드명"
                          className="ms-input"
                          style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                        />
                        <input
                          value={f.koField}
                          onChange={(e) => updateField(f.no, "koField", e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          onFocus={() => setSelectedTarget({ type: "info", index: infoIdx })}
                          placeholder="한글 필드명"
                          className="ms-input"
                          style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                        />
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* ── 테이블 정의 ── */}
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", letterSpacing: 0.3, textTransform: "uppercase", marginBottom: 6 }}>
                테이블 정의
              </div>
              {tables.length === 0 ? (
                <div style={{ fontSize: 13, color: "var(--muted)", padding: "4px 0" }}>정의된 테이블이 없습니다.</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {tables.map((t, tableIdx) => {
                    const isTableSel =
                      selectedTarget?.type === "table" && selectedTarget.tableIndex === tableIdx;
                    return (
                    <div
                      key={`table_${tableIdx}`}
                      onClick={() => setSelectedTarget({ type: "table", tableIndex: tableIdx })}
                      style={{
                        background: isTableSel ? "var(--accentBg)" : "var(--panel2)",
                        border: isTableSel
                          ? "1px solid var(--accent)"
                          : "1px solid var(--border)",
                        boxShadow: isTableSel
                          ? "0 0 0 1px rgba(34,211,238,0.25)"
                          : "none",
                        borderRadius: 10,
                        padding: 10,
                        display: "flex",
                        flexDirection: "column",
                        gap: 8,
                        cursor: "pointer",
                      }}
                    >
                      {/* 카드 헤더 — No / 테이블 key / 테이블명 / + 컬럼 (TPL-14A: 표 삭제 버튼 제거) */}
                      <div style={{ display: "grid", gridTemplateColumns: "28px 1fr 1fr auto", gap: 6, alignItems: "center" }}>
                        <span style={{ textAlign: "center", fontSize: 13, fontWeight: 700, color: isTableSel ? "var(--accent)" : "var(--text)" }}>
                          {fields.length + tableIdx + 1}
                        </span>
                        <input
                          value={t.tableKey ?? ""}
                          onChange={(e) => updateTable(tableIdx, { tableKey: e.target.value })}
                          onClick={(e) => e.stopPropagation()}
                          onFocus={() => setSelectedTarget({ type: "table", tableIndex: tableIdx })}
                          placeholder="영문 테이블 key"
                          className="ms-input"
                          style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                        />
                        <input
                          value={t.labelKo ?? ""}
                          onChange={(e) => updateTable(tableIdx, { labelKo: e.target.value })}
                          onClick={(e) => e.stopPropagation()}
                          onFocus={() => setSelectedTarget({ type: "table", tableIndex: tableIdx })}
                          placeholder="테이블명"
                          className="ms-input"
                          style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                        />
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); addColumn(tableIdx); }}
                          className="ms-btn-sm"
                        >
                          + 컬럼
                        </button>
                      </div>

                      {/* 컬럼 grid — TPL-14A: row X 삭제 버튼 제거, 선택 기반으로 통일
                          정형 Template과 동일한 "표준 컬럼" select를 추가해 backend canonical
                          key 매핑을 빠르게 채울 수 있게 한다. (가운데 두 input은 비어 있을
                          때만 표준값/한글명으로 자동 채워지고, 이미 입력한 값은 보호.) */}
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        <div style={{
                          display: "grid", gridTemplateColumns: "28px 1fr 1fr 1fr",
                          gap: 6, alignItems: "center",
                          padding: "6px 8px",
                          background: "rgba(255,255,255,0.04)",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                        }}>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>No</span>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>영문 컬럼명</span>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>한글 컬럼명</span>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>표준 컬럼</span>
                        </div>
                        {(t.columns ?? []).length === 0 ? (
                          <div style={{ fontSize: 12, color: "var(--muted)", padding: "4px 0" }}>컬럼이 없습니다.</div>
                        ) : (
                          (t.columns ?? []).map((c, colIdx) => {
                            const isColSel =
                              selectedTarget?.type === "column" &&
                              selectedTarget.tableIndex === tableIdx &&
                              selectedTarget.columnIndex === colIdx;
                            const columnKeyVal = c.columnKey ?? "";
                            const labelKoVal = c.labelKo ?? "";
                            // 별도 canonicalColumn 필드가 없는 비정형 schema에서는
                            // columnKey가 표준 옵션 value와 일치할 때만 select에 표시.
                            const canonicalVal = findCanonicalValueByKey(columnKeyVal);
                            return (
                            <div
                              key={`col_${colIdx}`}
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedTarget({ type: "column", tableIndex: tableIdx, columnIndex: colIdx });
                              }}
                              style={{
                                display: "grid", gridTemplateColumns: "28px 1fr 1fr 1fr",
                                gap: 6, alignItems: "center",
                                padding: "6px 8px",
                                background: isColSel ? "var(--accentBg)" : "var(--panel)",
                                border: isColSel
                                  ? "1px solid var(--accent)"
                                  : "1px solid var(--border)",
                                borderRadius: 8,
                                cursor: "pointer",
                              }}
                            >
                              <span style={{ textAlign: "center", fontSize: 12, fontWeight: 700, color: isColSel ? "var(--accent)" : "var(--text)" }}>
                                {colIdx + 1}
                              </span>
                              <input
                                value={columnKeyVal}
                                onChange={(e) => updateColumn(tableIdx, colIdx, { columnKey: e.target.value })}
                                onClick={(e) => e.stopPropagation()}
                                onFocus={() => setSelectedTarget({ type: "column", tableIndex: tableIdx, columnIndex: colIdx })}
                                placeholder="영문 컬럼명"
                                className="ms-input"
                                style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                              />
                              <input
                                value={labelKoVal}
                                onChange={(e) => updateColumn(tableIdx, colIdx, { labelKo: e.target.value })}
                                onClick={(e) => e.stopPropagation()}
                                onFocus={() => setSelectedTarget({ type: "column", tableIndex: tableIdx, columnIndex: colIdx })}
                                placeholder="한글 컬럼명"
                                className="ms-input"
                                style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                              />
                              <select
                                value={canonicalVal}
                                onChange={(e) => {
                                  const next = e.target.value;
                                  // "선택 안 함"이면 사용자 입력 유지, 아무것도 변경하지 않음
                                  if (!next) return;
                                  const opt = CANONICAL_COLUMN_OPTIONS.find((o) => o.value === next);
                                  // 표준 컬럼이 source-of-truth: 영문 key + 한글 모두 무조건 덮어쓰기.
                                  // 같은 옵션을 다시 골라도 일관되게 표시되도록.
                                  updateColumn(tableIdx, colIdx, {
                                    columnKey: next,
                                    labelKo: opt?.labelKo ?? "",
                                  });
                                }}
                                onClick={(e) => e.stopPropagation()}
                                onFocus={() => setSelectedTarget({ type: "column", tableIndex: tableIdx, columnIndex: colIdx })}
                                className="ms-input"
                                style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                              >
                                {CANONICAL_COLUMN_OPTIONS.map((opt) => (
                                  <option key={opt.value || "__none"} value={opt.value}>
                                    {canonicalColumnLabel(opt)}
                                  </option>
                                ))}
                              </select>
                            </div>
                            );
                          })
                        )}
                      </div>
                    </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
