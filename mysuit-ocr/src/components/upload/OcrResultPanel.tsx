"use client";

import React, { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useUi } from "../common/AppProviders";

export type OcrFieldResult = {
  name: string;
  field_type: string;
  value: string;
  confidence: number;
  bbox: number[];
};

export type OcrResult = {
  fields: OcrFieldResult[];
  full_text: string;
  processing_time: number;
};

type Props = {
  result: OcrResult;
  onRerun: () => void;
  onRevalidate: (fields: { index: number; bbox: number[] }[]) => Promise<OcrFieldResult[]>;
  selectedIndex: number | null;
  onSelectField: (index: number) => void;
  onTabChange?: (tab: "preview" | "custom" | "validation") => void;
  drawMode?: string | null;
  onDrawModeChange?: (mode: string | null) => void;
  isScanning?: boolean;
  onScanChange?: (scanning: boolean) => void;
  onPartialOcr?: (targets: { index: number; bbox: number[] }[]) => Promise<OcrFieldResult[]>;
  canvasRegions?: { id: string; name: string; fieldType: string; x: number; y: number; width: number; height: number }[];
};

type TabKey = "preview" | "custom" | "validation";

export default function OcrResultPanel({ result, onRerun, onRevalidate, selectedIndex, onSelectField, onTabChange, drawMode, onDrawModeChange, isScanning, onScanChange, onPartialOcr, canvasRegions }: Props) {
  const ui = useUi();
  const [activeTab, setActiveTab] = useState<TabKey>("preview");
  const [previewMode, setPreviewMode] = useState<"markdown" | "json">("markdown");
  const [editedFields, setEditedFields] = useState<OcrFieldResult[]>(result.fields);
  const [validationFilter, setValidationFilter] = useState<"all" | "success" | "warning" | "error">("success");
  const [confRange, setConfRange] = useState<number | null>(null); // null=전체, 0=0~10%, 10=10~20%, ... 90=90~100%
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [activeFieldType, setActiveFieldType] = useState<string>("field");
  const [isRevalidating, setIsRevalidating] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // canvasRegions에서 새로 그린 영역을 editedFields에 동기화
  useEffect(() => {
    if (!canvasRegions) return;
    const newRegions = canvasRegions.filter((r) => !r.id.startsWith("ocr_"));
    const existingIds = new Set(editedFields.map((f) => f.name));
    const toAdd: OcrFieldResult[] = [];
    newRegions.forEach((r) => {
      if (!existingIds.has(r.name)) {
        toAdd.push({
          name: r.name,
          field_type: r.fieldType,
          value: "",
          confidence: 0,
          bbox: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
        });
      }
    });
    if (toAdd.length > 0) {
      setEditedFields((prev) => [...prev, ...toAdd]);
    }
  }, [canvasRegions]);

  const FIELD_TYPES = [
    { key: "field", label: "필드" },
    { key: "multi", label: "멀티필드" },
    { key: "check", label: "체크필드" },
    { key: "table", label: "테이블필드" },
  ];

  const deleteField = (index: number) => {
    setEditedFields((prev) => prev.filter((_, i) => i !== index));
    if (selectedIndex === index) onSelectField(-1);
  };

  const updateFieldType = (index: number, type: string) => {
    setEditedFields((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], field_type: type };
      return next;
    });
  };

  const updateFieldName = (index: number, name: string) => {
    setEditedFields((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], name };
      return next;
    });
  };

  // 선택된 필드로 스크롤 + Validation 탭에서 편집 연동
  useEffect(() => {
    if (selectedIndex == null) return;
    if (activeTab === "validation") {
      // 현재 필터에 선택된 필드가 없으면 전체 보기로 전환
      const field = editedFields[selectedIndex];
      if (field) {
        const status = getValidationStatus(field);
        const inCurrentFilter = validationFilter === "all" || validationFilter === status;
        const inConfRange = confRange === null || (field.confidence * 100 >= confRange && field.confidence * 100 < confRange + 10);
        if (!inCurrentFilter || !inConfRange) {
          setValidationFilter("all");
          setConfRange(null);
        }
      }
      setEditingIdx(selectedIndex);
      setEditValue(editedFields[selectedIndex]?.value ?? "");
    }
    // 스크롤은 DOM 업데이트 후 실행
    setTimeout(() => {
      if (contentRef.current) {
        const el = contentRef.current.querySelector(`[data-field-idx="${selectedIndex}"]`) as HTMLElement;
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 50);
  }, [selectedIndex]);

  const tabs: { key: TabKey; label: string }[] = [
    { key: "preview", label: "Preview" },
    { key: "custom", label: "Custom" },
    { key: "validation", label: "Validation" },
  ];

  const getValidationStatus = (field: OcrFieldResult) => {
    if (!field.value || field.value.trim() === "") return "error";
    if (field.confidence < 0.7) return "warning";
    return "success";
  };

  const validationCounts = {
    success: editedFields.filter((f) => getValidationStatus(f) === "success").length,
    warning: editedFields.filter((f) => getValidationStatus(f) === "warning").length,
    error: editedFields.filter((f) => getValidationStatus(f) === "error").length,
  };

  const filteredValidation = editedFields.filter((f) => {
    if (validationFilter === "all") return true;
    return getValidationStatus(f) === validationFilter;
  });

  const toMarkdown = () => {
    const esc = (s: string) => s.replace(/\|/g, "\\|").replace(/\n/g, " ");
    let md = `# OCR 결과\n\n`;
    md += `- 처리 시간: **${result.processing_time.toFixed(2)}s**\n`;
    md += `- 필드 수: **${editedFields.length}건**\n\n`;
    md += `| No | 필드명 | 값 | 신뢰도 |\n`;
    md += `|:---:|--------|-----|:------:|\n`;
    editedFields.forEach((f, i) => {
      md += `| ${i + 1} | ${esc(f.name)} | ${esc(f.value)} | ${(f.confidence * 100).toFixed(1)}% |\n`;
    });
    return md;
  };

  const toJson = () => {
    return JSON.stringify({ fields: editedFields, processing_time: result.processing_time }, null, 2);
  };

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    await ui.alert("클립보드에 복사되었습니다.");
  };

  const handleExport = (text: string, ext: string) => {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ocr_result.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const updateFieldValue = (index: number, value: string) => {
    setEditedFields((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], value };
      return next;
    });
  };

  return (
    <div className="or-root">
      {/* Tab bar */}
      <div className="or-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`or-tab ${activeTab === tab.key ? "or-tab-active" : ""}`}
            onClick={() => { setActiveTab(tab.key); onTabChange?.(tab.key); if (tab.key !== "validation") { onSelectField(-1); setEditingIdx(null); } }}
          >
            {tab.label}
            {tab.key === "validation" && validationCounts.error > 0 && (
              <span className="or-tab-badge or-badge-error">{validationCounts.error}</span>
            )}
            {tab.key === "validation" && validationCounts.error === 0 && validationCounts.warning > 0 && (
              <span className="or-tab-badge or-badge-warn">{validationCounts.warning}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="or-content" ref={contentRef}>
        {/* Preview Tab */}
        {activeTab === "preview" && (
          <div className="or-preview">
            <div className="or-preview-modes">
              <button
                type="button"
                className={`ms-btn-sm ${previewMode === "markdown" ? "oc-mode-btn-active" : ""}`}
                onClick={() => setPreviewMode("markdown")}
              >
                Markdown
              </button>
              <button
                type="button"
                className={`ms-btn-sm ${previewMode === "json" ? "oc-mode-btn-active" : ""}`}
                onClick={() => setPreviewMode("json")}
              >
                JSON
              </button>
              <div style={{ flex: 1 }} />
              <button type="button" className="ms-btn-sm" onClick={() => handleExport(previewMode === "markdown" ? toMarkdown() : toJson(), previewMode === "markdown" ? "md" : "json")}>
                내보내기
              </button>
              <button type="button" className="ms-btn-sm" onClick={() => void handleCopy(previewMode === "markdown" ? toMarkdown() : toJson())}>
                복사
              </button>
            </div>
            {previewMode === "markdown" ? (
              <div className="or-preview-content or-markdown">
                <Markdown remarkPlugins={[remarkGfm]}>{toMarkdown()}</Markdown>
              </div>
            ) : (
              <pre className="or-preview-content">{toJson()}</pre>
            )}
          </div>
        )}

        {/* Custom Tab */}
        {activeTab === "custom" && (
          <div className="or-custom">
            {/* 필드 타입 버튼 + OCR 재실행 */}
            <div className="or-custom-toolbar">
              <div className="or-custom-types">
                {FIELD_TYPES.map((ft) => (
                  <button
                    key={ft.key}
                    type="button"
                    className={`or-type-btn ${drawMode === ft.key ? "or-type-btn-active" : ""}`}
                    onClick={() => onDrawModeChange?.(drawMode === ft.key ? null : ft.key)}
                  >
                    {ft.label}
                  </button>
                ))}
              </div>
              <button type="button" className="hw-btn-primary" style={{ fontSize: 12, padding: "6px 12px" }} onClick={async () => {
                // 신뢰도 70% 미만 또는 값이 빈 필드만 재실행
                const targets = editedFields
                  .map((f, i) => ({ index: i, field: f }))
                  .filter((item) => {
                    return item.field.confidence < 0.7 || !item.field.value || item.field.value.trim() === "";
                  })
                  .map((item) => ({ index: item.index, bbox: item.field.bbox }));

                if (targets.length === 0) {
                  await ui.alert("재실행할 대상이 없습니다. (모두 100%)");
                  return;
                }

                try {
                  onScanChange?.(true);
                  const updated = await (onPartialOcr ?? onRevalidate)(targets);
                  onScanChange?.(false);
                  if (!updated || updated.length === 0) return;
                  setEditedFields((prev) => {
                    const next = [...prev];
                    updated.forEach((f: any, i: number) => {
                      const targetIdx = targets[i]?.index;
                      if (targetIdx != null && f) {
                        next[targetIdx] = { ...next[targetIdx], value: f.value, confidence: f.confidence };
                      }
                    });
                    return next;
                  });
                  // 완료 - 별도 알림 없이 결과 반영
                } catch (err) {
                  onScanChange?.(false);
                  console.error("[Partial OCR error]", err);
                  await ui.alert("OCR 재실행 중 오류가 발생했습니다.");
                }
              }}>
                OCR 재실행
              </button>
            </div>

            {/* 필드 목록 */}
            <div className="or-custom-list-header">
              <span className="or-custom-label">필드 목록</span>
              <span className="or-custom-count">{editedFields.length}건</span>
            </div>

            <div className="or-field-list">
              {editedFields.map((field, i) => (
                <div
                  key={i}
                  data-field-idx={i}
                  className={`or-field-item ${selectedIndex === i ? "or-field-item-selected" : ""}`}
                  onClick={() => onSelectField(i)}
                >
                  <div className="or-field-header">
                    <input
                      className="or-field-name-input"
                      value={field.name}
                      onChange={(e) => updateFieldName(i, e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <select
                      className="or-field-type-select"
                      value={field.field_type}
                      onChange={(e) => updateFieldType(i, e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {FIELD_TYPES.map((ft) => (
                        <option key={ft.key} value={ft.key}>{ft.label}</option>
                      ))}
                    </select>
                    <span className={`or-field-conf ${field.confidence >= 0.7 ? "" : field.confidence >= 0.4 ? "or-conf-low" : "or-conf-error"}`}>
                      <span className="or-conf-bar-wrap">
                        <span className="or-conf-bar" style={{
                          width: `${(field.confidence * 100).toFixed(0)}%`,
                          background: field.confidence >= 0.7 ? "#16a34a" : field.confidence >= 0.4 ? "#d97706" : "#dc2626",
                        }} />
                      </span>
                      {field.confidence >= 0.7 ? "✓" : field.confidence >= 0.4 ? "△" : "✕"}
                      {(field.confidence * 100).toFixed(1)}%
                    </span>
                    <button
                      type="button"
                      className="or-field-delete"
                      onClick={(e) => { e.stopPropagation(); deleteField(i); }}
                      title="삭제"
                    >
                      ✕
                    </button>
                  </div>
                  {field.field_type === "table" ? (() => {
                    let rows: { value: string; confidence: number }[][] = [];
                    try { rows = JSON.parse(field.value); } catch { /* ignore */ }
                    return rows.length > 0 ? (
                      <div className="or-table-wrap" onClick={(e) => e.stopPropagation()}>
                        <table className="or-table-result">
                          <tbody>
                            {rows.map((row, ri) => (
                              <tr key={ri}>
                                {row.map((cell, ci) => (
                                  <td
                                    key={ci}
                                    className={`or-table-cell ${cell.confidence < 0.7 ? "or-table-cell-low" : ""}`}
                                    title={`신뢰도: ${(cell.confidence * 100).toFixed(1)}%`}
                                  >
                                    {cell.value || "-"}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="or-empty" style={{ fontSize: 12 }}>테이블 데이터 없음</div>
                    );
                  })() : (
                    <input
                      className="or-field-input"
                      value={field.value}
                      onChange={(e) => updateFieldValue(i, e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                      placeholder="인식된 값"
                    />
                  )}
                </div>
              ))}
              {editedFields.length === 0 && (
                <div className="or-empty">인식된 필드가 없습니다.</div>
              )}
            </div>
          </div>
        )}

        {/* Validation Tab */}
        {activeTab === "validation" && (() => {
          const errorFields = editedFields
            .map((f, i) => ({ field: f, idx: i, status: getValidationStatus(f) }))
            .filter((item) => {
              // 신뢰도 구간 필터
              if (confRange !== null) {
                const pct = item.field.confidence * 100;
                return pct >= confRange && pct < confRange + 10;
              }
              if (validationFilter === "all") return true;
              return item.status === validationFilter;
            });

          const currentEditing = editingIdx != null ? editedFields[editingIdx] : null;

          const navigateError = (direction: "prev" | "next") => {
            const targets = editedFields
              .map((f, i) => ({ idx: i, status: getValidationStatus(f) }))
              .filter((item) => item.status === "warning" || item.status === "error");
            if (targets.length === 0) return;

            if (editingIdx == null) {
              setEditingIdx(targets[0].idx);
              setEditValue(editedFields[targets[0].idx].value);
              onSelectField(targets[0].idx);
              return;
            }

            const curPos = targets.findIndex((t) => t.idx === editingIdx);
            let nextPos: number;
            if (direction === "next") {
              nextPos = curPos < targets.length - 1 ? curPos + 1 : 0;
            } else {
              nextPos = curPos > 0 ? curPos - 1 : targets.length - 1;
            }
            setEditingIdx(targets[nextPos].idx);
            setEditValue(editedFields[targets[nextPos].idx].value);
            onSelectField(targets[nextPos].idx);
          };

          const applyEdit = () => {
            if (editingIdx == null) return;
            updateFieldValue(editingIdx, editValue);
          };

          return (
            <div className="or-validation">
              {/* 상태 필터 */}
              <div className="or-validation-filters">
                {(["success", "warning", "error"] as const).map((filter) => (
                  <button
                    key={filter}
                    type="button"
                    className={`or-vf-btn or-vf-${filter} ${validationFilter === filter && confRange === null ? "or-vf-active" : ""}`}
                    onClick={() => { setValidationFilter(filter); setConfRange(null); }}
                  >
                    {filter === "success" ? `성공` : filter === "warning" ? `경고` : `오류`}
                  </button>
                ))}
              </div>

              {/* 신뢰도 구간 필터 */}
              <div className="or-conf-range-filters">
                <button
                  type="button"
                  className={`or-conf-range-btn ${confRange === null && validationFilter === "all" ? "or-conf-range-active" : ""}`}
                  onClick={() => { setConfRange(null); setValidationFilter("all"); }}
                >
                  전체
                </button>
                {[70, 80, 90].map((r) => {
                  const count = editedFields.filter((f) => {
                    const pct = f.confidence * 100;
                    return pct >= r && pct < r + 10;
                  }).length;
                  return (
                    <button
                      key={r}
                      type="button"
                      className={`or-conf-range-btn ${confRange === r ? "or-conf-range-active" : ""} ${count === 0 ? "or-conf-range-empty" : ""}`}
                      onClick={() => { setConfRange(r); setValidationFilter("all"); }}
                    >
                      {r}~{r + 10}%
                      {count > 0 && <span className="or-conf-range-count">{count}</span>}
                    </button>
                  );
                })}
              </div>

              {/* 건수 + 재검증 */}
              <div className="or-val-summary">
                {validationFilter === "success" ? (
                  <span className="or-val-summary-text">
                    성공 <b>{validationCounts.success}</b>건 / 경고 <b>{validationCounts.warning}</b>건 / 오류 <b>{validationCounts.error}</b>건
                  </span>
                ) : (
                  <span className="or-val-summary-text">
                    {validationFilter === "warning" ? "경고" : "오류"}{" "}
                    <b>{errorFields.length}</b>건
                  </span>
                )}
                {validationFilter !== "success" && (
                  <button type="button" className="ms-btn-sm" disabled={isRevalidating} onClick={async () => {
                    if (isRevalidating) return;
                    try {
                      const targets = errorFields.map((item) => ({
                        index: item.idx,
                        bbox: item.field.bbox,
                      }));
                      if (targets.length === 0) return;
                      setIsRevalidating(true);
                      onScanChange?.(true);
                      const updated = await onRevalidate(targets);
                      onScanChange?.(false);
                      setIsRevalidating(false);
                      if (!updated || updated.length === 0) {
                        await ui.alert("재검증 결과가 없습니다.");
                        return;
                      }
                      setEditedFields((prev) => {
                        const next = [...prev];
                        updated.forEach((f: any, i: number) => {
                          const targetIdx = targets[i]?.index;
                          if (targetIdx != null && f) {
                            next[targetIdx] = { ...next[targetIdx], value: f.value, confidence: f.confidence };
                          }
                        });
                        return next;
                      });
                      await ui.alert(`재검증 완료: ${targets.length}개 필드 처리됨`);
                    } catch (err) {
                      onScanChange?.(false);
                      setIsRevalidating(false);
                      console.error("[Revalidate error]", err);
                      await ui.alert("재검증 중 오류가 발생했습니다.");
                    }
                  }}>
                    {isRevalidating
                      ? `재검증 중... (${errorFields.length}건)`
                      : validationFilter === "warning" ? "경고 재검증" : "오류 재검증"}
                  </button>
                )}
              </div>

              {/* 내역 */}
              <div className="or-val-section-title">
                {validationFilter === "success" ? "성공 내역" : validationFilter === "warning" ? "경고 내역" : "오류 내역"}
              </div>
              <div className="or-val-error-list">
                {errorFields.length === 0 ? (
                  <div className="or-empty">해당 항목이 없습니다.</div>
                ) : (
                  errorFields.map((item) => (
                    <div
                      key={item.idx}
                      data-field-idx={item.idx}
                      className={`or-val-error-row ${editingIdx === item.idx ? "or-val-error-row-active" : ""}`}
                      onClick={() => {
                        setEditingIdx(item.idx);
                        setEditValue(item.field.value);
                        onSelectField(item.idx);
                      }}
                    >
                      <span className={`or-val-dot or-dot-${item.status}`} />
                      <span className="or-val-error-name">{item.field.name}</span>
                      <span className="or-val-error-value">{item.field.value || "(빈값)"}</span>
                      <span className="or-val-error-conf">{(item.field.confidence * 100).toFixed(1)}%</span>
                    </div>
                  ))
                )}
              </div>

              {/* 선택 필드 수정 */}
              {currentEditing && (
                <div className="or-val-edit-section">
                  <div className="or-val-section-title">필드 수정</div>
                  <div className="or-val-edit-info">
                    <span className="or-val-edit-field">{currentEditing.name}</span>
                    <span className="or-field-type">{currentEditing.field_type}</span>
                  </div>
                  <div className="or-val-edit-info" style={{ fontSize: 11, color: "var(--muted)" }}>
                    위치: [{currentEditing.bbox.join(", ")}]
                  </div>

                  <div className="or-val-edit-row">
                    <span className="or-val-label">현재 값:</span>
                    <input className="or-field-input" value={currentEditing.value} readOnly />
                  </div>

                  <div className="or-val-edit-row">
                    <span className="or-val-label">수정 값:</span>
                    <input
                      className="or-field-input"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                    />
                    <button type="button" className="ms-btn-sm" onClick={applyEdit}>수정</button>
                  </div>

                  <div className="or-val-edit-nav">
                    <button type="button" className="ms-btn-sm" onClick={() => navigateError("prev")}>이전</button>
                    <button type="button" className="ms-btn-sm" onClick={() => navigateError("next")}>다음</button>
                  </div>
                </div>
              )}
            </div>
          );
        })()}
      </div>
    </div>
  );
}
