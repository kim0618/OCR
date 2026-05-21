"use client";

import React, { useEffect, useState } from "react";
import { useUi } from "../common/AppProviders";

type Field = {
  no: number;
  enField: string;
  koField: string;
};

const LOCAL_TEMPLATES_KEY = "mysuit_ocr_templates";

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
  const [fields, setFields] = useState<Field[]>([]);
  const [selectedNo, setSelectedNo] = useState<number | null>(null);

  const addField = () => {
    const nextNo = fields.length > 0 ? Math.max(...fields.map((f) => f.no)) + 1 : 1;
    setFields([...fields, { no: nextNo, enField: "", koField: "" }]);
  };

  const updateField = (no: number, key: "enField" | "koField", v: string) => {
    setFields(fields.map((f) => f.no === no ? { ...f, [key]: v } : f));
  };

  useEffect(() => {
    if (!selectedTemplate) return;
    setTemplateName(String(selectedTemplate.templateName ?? selectedTemplate.template_name ?? ""));
    if (Array.isArray(selectedTemplate.fields)) {
      setFields(selectedTemplate.fields);
      setSelectedNo(null);
    }
  }, [selectedTemplate]);

  const handleSave = async () => {
    const name = templateName.trim();
    if (!name) { await ui.alert("템플릿 명을 입력해주세요."); return; }
    if (fields.length === 0) { await ui.alert("필드를 하나 이상 정의해주세요."); return; }
    // 저장/수정 전 확인 다이얼로그
    const proceed = await ui.confirm({
      title: isEditMode ? "템플릿 수정" : "템플릿 저장",
      message: `"${name}" 템플릿을 ${isEditMode ? "수정" : "저장"}하시겠습니까?`,
      okText: isEditMode ? "수정" : "저장",
      cancelText: "취소",
    });
    if (!proceed) return;
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
      setFields([]);
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
      setFields([]);
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
          {/* 템플릿명 */}
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

          {/* 출력 필드 정의 — Template과 동일한 oc-section */}
          <div className="oc-section">
            <div className="oc-section-header">
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

          {/* 필드 목록 */}
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
              <div style={{ fontSize: 13, color: "var(--muted)", padding: "4px 0" }}>필드가 없습니다.</div>
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
        </div>
      </div>
    </div>
  );
}
