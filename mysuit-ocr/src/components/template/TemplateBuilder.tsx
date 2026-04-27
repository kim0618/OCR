"use client";

import React, { useRef, useState } from "react";

// ── Types ──────────────────────────────────────────────────────────────────
type Mode = "template" | "unstructured";

type UnstructuredField = {
  no: number;
  enField: string;
  koField: string;
};


// ── Shared styles ─────────────────────────────────────────────────────────
const panelBase: React.CSSProperties = {
  background: "var(--panel)",
  border: "1px solid rgba(255,255,255,0.07)",
  borderRadius: 10,
};

// ── ActionBtn ─────────────────────────────────────────────────────────────
function ActionBtn({
  onClick,
  variant = "primary",
  children,
  style,
}: {
  onClick: () => void;
  variant?: "primary" | "danger" | "ghost";
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  const bg =
    variant === "primary" ? "var(--accent)"
    : variant === "danger" ? "#ef4444"
    : "var(--panel2)";
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: "6px 16px",
        borderRadius: 7,
        border: variant === "ghost" ? "1px solid rgba(255,255,255,0.12)" : "none",
        background: bg,
        color: variant === "ghost" ? "var(--muted)" : "#fff",
        fontWeight: 700,
        fontSize: 12,
        cursor: "pointer",
        ...style,
      }}
    >
      {children}
    </button>
  );
}

// ── LabeledInput ──────────────────────────────────────────────────────────
function LabeledInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          background: "var(--panel2)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 7,
          padding: "7px 10px",
          color: "var(--text)",
          fontSize: 13,
          outline: "none",
          width: "100%",
          boxSizing: "border-box",
        }}
      />
    </div>
  );
}

// ── ModeCard — "+" / 비정형 스타일 선택 카드 ────────────────────────────
function ModeCard({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        width: 96,
        height: 72,
        borderRadius: 10,
        border: active
          ? "2px solid var(--accent)"
          : "1.5px solid rgba(255,255,255,0.12)",
        background: active ? "var(--accentBg)" : "var(--panel2)",
        color: active ? "var(--accent)" : "var(--muted)",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        transition: "all 0.15s",
        flexShrink: 0,
      }}
    >
      <span style={{ fontSize: 20, lineHeight: 1 }}>{icon}</span>
      <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: 0.3 }}>{label}</span>
    </button>
  );
}

// ── Template Mode Content (영역지정 + 미리보기 + 우측 패널) ──────────────
function TemplateModeContent({
  templateName,
  setTemplateName,
  regionEnabled,
  setRegionEnabled,
  uploadedPreview,
  setUploadedPreview,
  onSave,
  onDelete,
}: {
  templateName: string;
  setTemplateName: (v: string) => void;
  regionEnabled: boolean;
  setRegionEnabled: (v: boolean) => void;
  uploadedPreview: string | null;
  setUploadedPreview: (v: string | null) => void;
  onSave: () => void;
  onDelete: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedPreview(URL.createObjectURL(file));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, gap: 8 }}>
      {/* 영역지정 토글 바 */}
      <div
        style={{
          ...panelBase,
          padding: "8px 14px",
          display: "flex",
          alignItems: "center",
          gap: 10,
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)" }}>영역지정</span>
        <button
          type="button"
          onClick={() => setRegionEnabled(!regionEnabled)}
          style={{
            width: 36, height: 20, borderRadius: 10,
            border: "none", cursor: "pointer",
            background: regionEnabled ? "var(--accent)" : "rgba(255,255,255,0.18)",
            position: "relative", transition: "background 0.2s",
            flexShrink: 0,
          }}
        >
          <span style={{
            position: "absolute", top: 2,
            left: regionEnabled ? 18 : 2,
            width: 16, height: 16, borderRadius: 999,
            background: "#fff", transition: "left 0.2s",
          }} />
        </button>
        <span style={{ fontSize: 11, color: regionEnabled ? "var(--accent)" : "rgba(255,255,255,0.35)", fontWeight: 700 }}>
          {regionEnabled ? "ON" : "OFF"}
        </span>
      </div>

      {/* 미리보기 + 우측 패널 */}
      <div style={{ display: "flex", flex: 1, minHeight: 0, gap: 8 }}>
        {/* 중앙 미리보기 */}
        <div
          style={{
            ...panelBase,
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 12,
            position: "relative",
            minHeight: 300,
          }}
        >
          {uploadedPreview ? (
            <>
              <img src={uploadedPreview} alt="preview" style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain", borderRadius: 8 }} />
              <button
                type="button"
                onClick={() => setUploadedPreview(null)}
                style={{
                  position: "absolute", top: 10, right: 10,
                  background: "rgba(0,0,0,0.55)", color: "#fff",
                  border: "none", borderRadius: 6, padding: "3px 10px",
                  fontSize: 11, cursor: "pointer", fontWeight: 700,
                }}
              >
                제거
              </button>
            </>
          ) : (
            <>
              <div style={{ fontSize: 34, opacity: 0.22 }}>📄</div>
              <div style={{ fontSize: 13, color: "var(--muted)" }}>이미지를 업로드하세요</div>
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                style={{
                  padding: "7px 18px", borderRadius: 8,
                  background: "var(--panel2)", color: "var(--text)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  fontSize: 12, fontWeight: 600, cursor: "pointer",
                }}
              >
                파일 선택
              </button>
              <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleFile} />
            </>
          )}
        </div>

        {/* 우측 편집 패널 */}
        <div
          style={{
            ...panelBase,
            width: 200,
            flexShrink: 0,
            padding: "14px 14px",
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          {/* 저장/삭제 버튼 행 */}
          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
            <ActionBtn variant="ghost" onClick={onDelete}>삭제</ActionBtn>
            <ActionBtn variant="primary" onClick={onSave}>저장</ActionBtn>
          </div>
          <div style={{ height: 1, background: "rgba(255,255,255,0.07)" }} />
          <LabeledInput
            label="템플릿명"
            value={templateName}
            onChange={setTemplateName}
            placeholder="템플릿 이름 입력"
          />
        </div>
      </div>
    </div>
  );
}

// ── Unstructured Mode Content ─────────────────────────────────────────────
function UnstructuredModeContent({
  templateName,
  setTemplateName,
  fields,
  setFields,
  onSave,
  onDelete,
}: {
  templateName: string;
  setTemplateName: (v: string) => void;
  fields: UnstructuredField[];
  setFields: (f: UnstructuredField[]) => void;
  onSave: () => void;
  onDelete: () => void;
}) {
  const addField = () => {
    const nextNo = fields.length > 0 ? Math.max(...fields.map((f) => f.no)) + 1 : 1;
    setFields([...fields, { no: nextNo, enField: "", koField: "" }]);
  };
  const removeField = (no: number) => setFields(fields.filter((f) => f.no !== no));
  const updateField = (no: number, key: "enField" | "koField", value: string) =>
    setFields(fields.map((f) => (f.no === no ? { ...f, [key]: value } : f)));

  const cellInput: React.CSSProperties = {
    background: "var(--panel2)",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 5,
    padding: "5px 8px",
    color: "var(--text)",
    fontSize: 12,
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  };

  return (
    <div style={{ display: "flex", flex: 1, minHeight: 0, gap: 8 }}>
      {/* 중앙 플레이스홀더 */}
      <div
        style={{
          ...panelBase,
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 10,
          minHeight: 300,
        }}
      >
        <div style={{ fontSize: 34, opacity: 0.2 }}>📋</div>
        <div style={{ fontSize: 13, color: "var(--muted)", textAlign: "center", lineHeight: 1.6 }}>
          비정형 문서 영역<br />
          <span style={{ fontSize: 11 }}>업로드 / 미리보기 (준비 중)</span>
        </div>
      </div>

      {/* 우측 편집 패널 */}
      <div
        style={{
          ...panelBase,
          width: 300,
          flexShrink: 0,
          padding: "14px",
          display: "flex",
          flexDirection: "column",
          gap: 12,
          overflow: "hidden",
        }}
      >
        {/* 저장/삭제 행 */}
        <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
          <ActionBtn variant="ghost" onClick={onDelete}>삭제</ActionBtn>
          <ActionBtn variant="primary" onClick={onSave}>저장</ActionBtn>
        </div>
        <div style={{ height: 1, background: "rgba(255,255,255,0.07)" }} />

        <LabeledInput
          label="설정명"
          value={templateName}
          onChange={setTemplateName}
          placeholder="설정 이름 입력"
        />

        {/* 출력 필드 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1, minHeight: 0 }}>
          <span style={{ fontSize: 10, fontWeight: 800, color: "var(--muted)", letterSpacing: 0.5, textTransform: "uppercase" }}>
            출력 필드 정의
          </span>

          {/* 헤더 */}
          <div style={{ display: "grid", gridTemplateColumns: "28px 1fr 1fr 24px", gap: 5 }}>
            {["No", "영문 필드명", "한글 필드명", ""].map((h) => (
              <span key={h} style={{ fontSize: 9, fontWeight: 700, color: "var(--muted)" }}>{h}</span>
            ))}
          </div>

          {/* 행 목록 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 5, overflowY: "auto", flex: 1 }}>
            {fields.length === 0 ? (
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.25)", textAlign: "center", padding: "10px 0" }}>
                필드가 없습니다
              </div>
            ) : (
              fields.map((f) => (
                <div key={f.no} style={{ display: "grid", gridTemplateColumns: "28px 1fr 1fr 24px", gap: 5, alignItems: "center" }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)", textAlign: "center" }}>{f.no}</span>
                  <input value={f.enField} onChange={(e) => updateField(f.no, "enField", e.target.value)} placeholder="fieldName" style={cellInput} />
                  <input value={f.koField} onChange={(e) => updateField(f.no, "koField", e.target.value)} placeholder="필드명" style={cellInput} />
                  <button
                    type="button"
                    onClick={() => removeField(f.no)}
                    style={{ width: 22, height: 22, borderRadius: 5, background: "rgba(239,68,68,0.15)", color: "#ef4444", border: "none", cursor: "pointer", fontSize: 13, display: "grid", placeItems: "center", fontWeight: 800 }}
                  >×</button>
                </div>
              ))
            )}
          </div>

          <button
            type="button"
            onClick={addField}
            style={{
              width: "100%", padding: "6px 0", borderRadius: 6,
              background: "var(--panel2)",
              border: "1px dashed rgba(255,255,255,0.18)",
              color: "var(--muted)", fontSize: 12, fontWeight: 600, cursor: "pointer",
            }}
          >
            + 필드 추가
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main TemplateBuilder ───────────────────────────────────────────────────
export default function TemplateBuilder() {
  const [mode, setMode] = useState<Mode>("template");

  const [templateName, setTemplateName] = useState<string>("");
  const [regionEnabled, setRegionEnabled] = useState<boolean>(false);
  const [uploadedPreview, setUploadedPreview] = useState<string | null>(null);

  const [unstructuredName, setUnstructuredName] = useState<string>("");
  const [unstructuredFields, setUnstructuredFields] = useState<UnstructuredField[]>([]);

  const handleSave = () => {
    const name = mode === "template" ? templateName : unstructuredName;
    if (!name.trim()) { alert("이름을 입력해주세요."); return; }
    alert(`[Mock] "${name}" 저장 완료 (mock)`);
  };

  const handleDelete = () => {
    const name = mode === "template" ? templateName : unstructuredName;
    if (!name.trim()) { alert("삭제할 항목이 없습니다."); return; }
    if (confirm(`"${name}"을(를) 삭제할까요? (mock)`)) {
      if (mode === "template") { setTemplateName(""); setUploadedPreview(null); }
      else { setUnstructuredName(""); setUnstructuredFields([]); }
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        gap: 8,
        padding: 0,
        boxSizing: "border-box",
      }}
    >
        {/* 상단: 모드 선택 카드 행 */}
        <div style={{ display: "flex", gap: 10, alignItems: "flex-start", flexShrink: 0 }}>
          {/* 템플릿 생성 카드 */}
          <ModeCard
            active={mode === "template"}
            onClick={() => setMode("template")}
            icon="＋"
            label="템플릿 생성"
          />
          {/* 비정형 생성 카드 */}
          <ModeCard
            active={mode === "unstructured"}
            onClick={() => setMode("unstructured")}
            icon="≡"
            label="비정형 생성"
          />
          {/* 현재 모드 이름 (카드 옆 텍스트) */}
          <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: 8, marginLeft: 6 }}>
            <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 600 }}>
              {mode === "template" ? "템플릿 생성 모드" : "비정형 생성 모드"}
            </span>
          </div>
        </div>

        {/* 모드 콘텐츠 */}
        <div style={{ flex: 1, minHeight: 0, display: "flex" }}>
          {mode === "template" ? (
            <TemplateModeContent
              templateName={templateName}
              setTemplateName={setTemplateName}
              regionEnabled={regionEnabled}
              setRegionEnabled={setRegionEnabled}
              uploadedPreview={uploadedPreview}
              setUploadedPreview={setUploadedPreview}
              onSave={handleSave}
              onDelete={handleDelete}
            />
          ) : (
            <UnstructuredModeContent
              templateName={unstructuredName}
              setTemplateName={setUnstructuredName}
              fields={unstructuredFields}
              setFields={setUnstructuredFields}
              onSave={handleSave}
              onDelete={handleDelete}
            />
          )}
        </div>
    </div>
  );
}
