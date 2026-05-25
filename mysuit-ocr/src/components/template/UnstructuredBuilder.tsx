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

type Field = {
  no: number;
  enField: string;
  koField: string;
};

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
  const [selectedNo, setSelectedNo] = useState<number | null>(null);

  // ── 일반 영역 helpers ────────────────────────────────────────────────
  const addField = () => {
    const nextNo = fields.length > 0 ? Math.max(...fields.map((f) => f.no)) + 1 : 1;
    const def = createDefaultInfoField(nextNo);
    setFields([...fields, { no: nextNo, enField: def.labelEn ?? "", koField: def.labelKo }]);
  };

  const updateField = (no: number, key: "enField" | "koField", v: string) => {
    setFields(fields.map((f) => f.no === no ? { ...f, [key]: v } : f));
  };

  // ── 테이블 정의 helpers ──────────────────────────────────────────────
  const addTable = () => {
    const order = tables.length + 1;
    const def = createDefaultTableDef(order);
    def.columns = [createDefaultTableColumn(1)];
    setTables([...tables, def]);
  };

  const updateTable = (tableIdx: number, patch: Partial<UnstructuredTableDef>) => {
    setTables(tables.map((t, i) => (i === tableIdx ? { ...t, ...patch } : t)));
  };

  const removeTable = (tableIdx: number) => {
    setTables(tables.filter((_, i) => i !== tableIdx));
  };

  const addColumn = (tableIdx: number) => {
    setTables(
      tables.map((t, i) => {
        if (i !== tableIdx) return t;
        const nextOrder = (t.columns?.length ?? 0) + 1;
        const col = createDefaultTableColumn(nextOrder);
        return { ...t, columns: [...(t.columns ?? []), col] };
      }),
    );
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

  const removeColumn = (tableIdx: number, colIdx: number) => {
    setTables(
      tables.map((t, i) => {
        if (i !== tableIdx) return t;
        return { ...t, columns: t.columns.filter((_, j) => j !== colIdx) };
      }),
    );
  };

  useEffect(() => {
    if (!selectedTemplate) return;
    const normalized = normalizeUnstructuredTemplate(selectedTemplate);
    setTemplateName(normalized.templateName ?? "");
    setDocumentType(normalized.documentType ?? "");
    setFields(
      normalized.fields.map(({ no, enField, koField }) => ({ no, enField, koField })),
    );
    setTables(normalized.tables);
    setSelectedNo(null);
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
      setSelectedNo(null);
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
      setSelectedNo(null);
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

        {/* 삭제 / 저장 */}
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
                <button onClick={addField} className="ms-btn-sm">+ 영역 정의</button>
                <button onClick={addTable} className="ms-btn-sm">+ 테이블 정의</button>
                <button
                  onClick={() => {
                    if (selectedNo == null) return;
                    setFields(fields.filter((f) => f.no !== selectedNo));
                    setSelectedNo(null);
                  }}
                  className="ms-btn-sm"
                  style={{ color: "#ef4444", borderColor: "rgba(239,68,68,0.4)" }}>
                  삭제
                </button>
              </div>
            </div>

            {/* ── 일반 영역 ── */}
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", letterSpacing: 0.3, textTransform: "uppercase", marginBottom: 6 }}>
                일반 영역
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {/* 헤더 — No / 영문 필드명 / 한글 필드명 */}
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

                {fields.length === 0 ? (
                  <div style={{ fontSize: 13, color: "var(--muted)", padding: "4px 0" }}>정의된 영역이 없습니다.</div>
                ) : (
                  fields.map((f) => {
                    const isSel = selectedNo === f.no;
                    return (
                      <div
                        key={f.no}
                        onClick={() => setSelectedNo(isSel ? null : f.no)}
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
                          placeholder="영문 필드명"
                          className="ms-input"
                          style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                        />
                        <input
                          value={f.koField}
                          onChange={(e) => updateField(f.no, "koField", e.target.value)}
                          onClick={(e) => e.stopPropagation()}
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
                  {tables.map((t, tableIdx) => (
                    <div
                      key={`table_${tableIdx}`}
                      style={{
                        background: "var(--panel2)",
                        border: "1px solid var(--border)",
                        borderRadius: 10,
                        padding: 10,
                        display: "flex",
                        flexDirection: "column",
                        gap: 8,
                      }}
                    >
                      {/* 카드 헤더 — 테이블명 + [+ 컬럼] [표 삭제] */}
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto auto", gap: 6, alignItems: "center" }}>
                        <input
                          value={t.tableKey ?? ""}
                          onChange={(e) => updateTable(tableIdx, { tableKey: e.target.value })}
                          placeholder="영문 테이블 key"
                          className="ms-input"
                          style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                        />
                        <input
                          value={t.labelKo ?? ""}
                          onChange={(e) => updateTable(tableIdx, { labelKo: e.target.value })}
                          placeholder="테이블명"
                          className="ms-input"
                          style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                        />
                        <button
                          type="button"
                          onClick={() => addColumn(tableIdx)}
                          className="ms-btn-sm"
                        >
                          + 컬럼
                        </button>
                        <button
                          type="button"
                          onClick={() => removeTable(tableIdx)}
                          className="ms-btn-sm"
                          style={{ color: "#ef4444", borderColor: "rgba(239,68,68,0.4)" }}
                        >
                          표 삭제
                        </button>
                      </div>

                      {/* 컬럼 grid */}
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        <div style={{
                          display: "grid", gridTemplateColumns: "28px 1fr 1fr 24px",
                          gap: 6, alignItems: "center",
                          padding: "6px 8px",
                          background: "rgba(255,255,255,0.04)",
                          border: "1px solid var(--border)",
                          borderRadius: 6,
                        }}>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>No</span>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>영문 컬럼명</span>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>한글 컬럼명</span>
                          <span />
                        </div>
                        {(t.columns ?? []).length === 0 ? (
                          <div style={{ fontSize: 12, color: "var(--muted)", padding: "4px 0" }}>컬럼이 없습니다.</div>
                        ) : (
                          (t.columns ?? []).map((c, colIdx) => (
                            <div
                              key={`col_${colIdx}`}
                              style={{
                                display: "grid", gridTemplateColumns: "28px 1fr 1fr 24px",
                                gap: 6, alignItems: "center",
                                padding: "6px 8px",
                                background: "var(--panel)",
                                border: "1px solid var(--border)",
                                borderRadius: 8,
                              }}
                            >
                              <span style={{ textAlign: "center", fontSize: 12, fontWeight: 700, color: "var(--text)" }}>
                                {colIdx + 1}
                              </span>
                              <input
                                value={c.columnKey ?? ""}
                                onChange={(e) => updateColumn(tableIdx, colIdx, { columnKey: e.target.value })}
                                placeholder="영문 컬럼명"
                                className="ms-input"
                                style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                              />
                              <input
                                value={c.labelKo ?? ""}
                                onChange={(e) => updateColumn(tableIdx, colIdx, { labelKo: e.target.value })}
                                placeholder="한글 컬럼명"
                                className="ms-input"
                                style={{ minWidth: 0, width: "100%", boxSizing: "border-box" }}
                              />
                              <button
                                type="button"
                                onClick={() => removeColumn(tableIdx, colIdx)}
                                className="ms-btn-sm"
                                title="컬럼 삭제"
                                style={{ color: "#ef4444", borderColor: "rgba(239,68,68,0.4)", padding: "2px 6px" }}
                              >
                                ✕
                              </button>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
