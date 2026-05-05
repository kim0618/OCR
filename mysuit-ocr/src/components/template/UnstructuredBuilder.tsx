"use client";

import React, { useEffect, useState } from "react";

type Field = { no: number; enField: string; koField: string };
const LOCAL_TEMPLATES_KEY = "mysuit_ocr_templates";

export default function UnstructuredBuilder({
  selectedTemplate = null,
  selectedTemplateId = null,
}: {
  selectedTemplate?: any | null;
  selectedTemplateId?: string | null;
}) {
  const isEditMode = !!selectedTemplateId;
  const [templateName, setTemplateName] = useState("");
  const [fields, setFields] = useState<Field[]>([]);
  const [selectedNo, setSelectedNo] = useState<number | null>(null);

  const addField = () => {
    const nextNo = fields.length > 0 ? Math.max(...fields.map((f) => f.no)) + 1 : 1;
    setFields([...fields, { no: nextNo, enField: "", koField: "" }]);
  };
  const updateField = (no: number, key: "enField" | "koField", v: string) =>
    setFields(fields.map((f) => (f.no === no ? { ...f, [key]: v } : f)));

  useEffect(() => {
    if (!selectedTemplate) return;
    setTemplateName(String(selectedTemplate.templateName ?? selectedTemplate.template_name ?? ""));
    if (Array.isArray(selectedTemplate.fields)) {
      setFields(selectedTemplate.fields);
      setSelectedNo(null);
    }
  }, [selectedTemplate]);

  const handleSave = () => {
    if (!templateName.trim()) { alert("템플릿명을 입력해주세요."); return; }
    const name = templateName.trim();
    const localTemplate = {
      template_id: selectedTemplateId || `LOCAL-${Date.now()}`,
      template_name: name,
      template_json: {
        templateName: name,
        mode: "unstructured",
        fields,
        regions: [],
      },
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
    alert(`[Mock] "${templateName}" ${isEditMode ? "수정" : "저장"} 완료`);
  };
  const handleDelete = () => {
    if (confirm("초기화할까요?")) {
      setTemplateName("");
      setFields([]);
    }
  };

  const inputStyle: React.CSSProperties = {
    background: "var(--panel2)",
    border: "1px solid rgba(255,255,255,0.09)",
    borderRadius: 5,
    padding: "5px 8px",
    color: "var(--text)",
    fontSize: 12,
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  };

  const CARDS = [
    { icon: "📄", title: "다양한 문서 지원", desc: "계약서·이메일·보고서 등 형식이 달라도 적용 가능" },
    { icon: "🏷️", title: "필드 자유 정의", desc: "추출할 항목을 영문·한글로 직접 입력해 커스터마이징" },
    { icon: "🔍", title: "위치 무관 인식", desc: "고정 위치 없이 문서 어디서든 원하는 정보를 찾아냄" },
  ];

  return (
    <div style={{ display: "flex", flex: 1, gap: 8, minHeight: 0, height: "100%" }}>

      {/* ── 좌측: 비정형 설명 ── */}
      <div
        style={{
          flex: 1,
          background: "var(--panel)",
          borderRadius: 10,
          border: "1px solid rgba(255,255,255,0.07)",
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
            우측에서 <strong style={{ color: "var(--text)" }}>출력 필드</strong>를 정의하면
            AI가 문서 내 해당 정보를 자동으로 찾아 반환합니다.
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

      {/* ── 우측: 편집 패널 ── */}
      <div style={{ width: 380, flexShrink: 0, display: "flex", flexDirection: "column", gap: 8, minHeight: 0 }}>

        {/* ① 삭제 / 저장 — 독립 박스 */}
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
          <button onClick={handleSave} className="ms-btn"
            style={{ background: "var(--accent)", color: "#fff", border: "none" }}>
            {isEditMode ? "수정" : "저장"}
          </button>
        </div>

        {/* ② 나머지 (템플릿명 + 출력 필드) — 남은 공간 전부 차지 */}
        <div style={{
          flex: 1,
          minHeight: 0,
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          display: "flex",
          flexDirection: "column",
          overflow: "auto",
        }}>
          {/* 템플릿명 — oc-label 스타일 */}
          <div className="oc-template-input-wrap" style={{ padding: "0 12px 10px" }}>
            <h2 className="oc-label">템플릿 명</h2>
            <input
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              placeholder="템플릿 명"
              className="ms-input"
              style={{ width: "100%" }}
            />
          </div>

          {/* 출력 필드 헤더 — OcrRightPanel oc-section 스타일 (위쪽 구분선) */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "10px 12px 0",
            marginTop: 4,
            borderTop: "1px solid var(--border)",
            flexShrink: 0,
          }}>
            <h3 className="oc-section-title" style={{ margin: 0 }}>출력 필드 정의</h3>
            <div style={{ display: "flex", gap: 5 }}>
              <button onClick={addField} className="ms-btn-sm">추가</button>
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

          {/* 헤더 + 행 (모두 동일 카드 스타일) */}
          <div style={{ padding: "10px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
            {/* 컬럼 헤더 — 카드 스타일 */}
            <div style={{
              display: "grid", gridTemplateColumns: "32px 1fr 1fr",
              gap: 8,
              alignItems: "center",
              padding: "8px 8px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid var(--border)",
              borderRadius: 10,
              boxSizing: "border-box",
            }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>No</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", paddingLeft: 8 }}>영문 필드명</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", paddingLeft: 8 }}>한글 필드명</span>
            </div>

            {/* 필드 행 */}
            {fields.length === 0 ? (
              <div style={{ fontSize: 13, color: "var(--muted)", padding: "4px 0" }}>필드가 없습니다.</div>
            ) : (
              fields.map((f) => {
                const isSel = selectedNo === f.no;
                return (
                  <div
                    key={f.no}
                    onClick={() => setSelectedNo(isSel ? null : f.no)}
                    style={{
                      display: "grid", gridTemplateColumns: "32px 1fr 1fr",
                      gap: 8,
                      alignItems: "center",
                      padding: "6px 8px",
                      background: isSel ? "var(--accentBg)" : "var(--panel2)",
                      border: isSel ? "1px solid var(--accent)" : "1px solid var(--border)",
                      borderRadius: 10,
                      boxSizing: "border-box",
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
      </div>
    </div>
  );
}
