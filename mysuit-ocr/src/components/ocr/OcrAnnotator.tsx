"use client";

import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import type { FieldType, LoadedImage, Region } from "./core/types";
import { buildExportPayload } from "./core/export";
import OcrCanvasPane from "./OcrCanvasPane";
import OcrRightPanel from "./OcrRightPanel";
import { saveTemplateImage, getTemplateImage, deleteTemplateImage } from "@/lib/imageStore";
import { useUi } from "../common/AppProviders";

const LOCAL_TEMPLATES_KEY = "mysuit_ocr_templates";

export default function OcrAnnotator({
  selectedTemplate = null,
  selectedTemplateId = null,
}: {
  selectedTemplate?: any | null;
  selectedTemplateId?: string | null;
}) {
  const isEditMode = !!selectedTemplateId;
  const ui = useUi();
  const imgRef = useRef<HTMLImageElement | null>(null);

  const DEFAULT_ZOOM_PCT = 100;

  const [templateName, setTemplateName] = useState<string>("");
  const [documentType, setDocumentType] = useState<string>("");
  const [loaded, setLoaded] = useState<LoadedImage | null>(null);
  const [regions, setRegions] = useState<Region[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [zoomPct, setZoomPct] = useState<number>(DEFAULT_ZOOM_PCT);
  const [drawMode, setDrawMode] = useState<FieldType | null>(null);
  const [rowTemplateTargetId, setRowTemplateTargetId] = useState<string | null>(null);
  const [colGuideTargetId, setColGuideTargetId] = useState<string | null>(null);

  // 수동 변경 추적 + 업로드 토큰 (stale 응답 방지)
  const docTypeManualRef = useRef(false);
  const uploadTokenRef = useRef(0);

  const VALID_AUTO_DOC_TYPES = [
    "invoice_statement", "card_receipt", "pos_receipt",
    "food_cafe_receipt", "finance_slip", "medical_receipt",
  ];

  // 사용자 수동 선택 시 호출 — 이후 자동 감지 결과가 덮어쓰지 않음
  const handleSetDocumentType = useCallback((value: string) => {
    docTypeManualRef.current = true;
    setDocumentType(value);
  }, []);

  function updateName(id: string, name: string) {
    setRegions((prev) => prev.map((r) => (r.id === id ? { ...r, name } : r)));
  }

  function deleteRegion(id: string) {
    setRegions((prev) => prev.filter((r) => r.id !== id));
    setSelectedId((cur) => (cur === id ? null : cur));
  }

  const exportPayload = useMemo(
    () => buildExportPayload({ templateName, loaded, regions, documentType }),
    [loaded, regions, templateName, documentType],
  );

  useEffect(() => {
    if (!selectedTemplate) return;
    setTemplateName(String(selectedTemplate.templateName ?? selectedTemplate.template_name ?? ""));
    setDocumentType(String(selectedTemplate.documentType ?? ""));

    // 저장된 이미지 dataURL이 있으면 loaded 상태 복원
    // UI-IMG-IDB-1: localStorage에 src 없으면 IndexedDB에서 fallback 조회
    const savedSrc = selectedTemplate.image?.src;
    const fileName = String(selectedTemplate.file?.name ?? "");
    const w = Number(selectedTemplate.image?.width ?? 0);
    const h = Number(selectedTemplate.image?.height ?? 0);
    if (savedSrc) {
      setLoaded({ src: savedSrc, fileName, naturalWidth: w, naturalHeight: h });
    } else if (selectedTemplateId && w > 0 && h > 0) {
      void (async () => {
        const idbSrc = await getTemplateImage(selectedTemplateId);
        if (idbSrc) setLoaded({ src: idbSrc, fileName, naturalWidth: w, naturalHeight: h });
      })();
    }

    if (Array.isArray(selectedTemplate.regions)) {
      setRegions(selectedTemplate.regions);
      setSelectedId(null);
      setDrawMode(null);
      setRowTemplateTargetId(null);
      setColGuideTargetId(null);
    }
  }, [selectedTemplate, selectedTemplateId]);

  async function onPickFile(file: File) {
    const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");

    // 새 파일 업로드 시 수동 변경 플래그 초기화 + 토큰 갱신
    docTypeManualRef.current = false;
    const token = ++uploadTokenRef.current;

    // 자동 documentType 감지 — fire-and-forget, UI 오류 없이 조용히 실패
    void (async () => {
      try {
        const fd = new FormData();
        fd.append("file", file);
        const res = await fetch("/api/ocr-extract", { method: "POST", body: fd });
        if (!res.ok) return;
        const json = await res.json() as Record<string, unknown>;
        const detected = String(json?.doc_type ?? json?.documentType ?? json?.detectedDocType ?? "");
        if (
          detected &&
          detected !== "unknown" &&
          VALID_AUTO_DOC_TYPES.includes(detected) &&
          !docTypeManualRef.current &&
          uploadTokenRef.current === token
        ) {
          setDocumentType(detected);
        }
      } catch (err) {
        console.error("[auto docType detect error]", err);
      }
    })();

    if (isPdf) {
      try {
        const arrayBuffer = await file.arrayBuffer();
        const pdfjs = await import("pdfjs-dist/legacy/build/pdf");
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.js";
        const loadingTask = pdfjs.getDocument({ data: arrayBuffer });
        const pdf = await loadingTask.promise;
        const page = await pdf.getPage(1);
        const pageRotation = typeof page.rotate === "number" ? page.rotate : 0;
        const baseViewport = page.getViewport({ scale: 1, rotation: pageRotation });
        // backend(PyMuPDF 200 DPI)와 좌표계 일치: 72pt/inch 기준 200dpi = 200/72
        const scale = 200 / 72;
        const viewport = page.getViewport({ scale, rotation: pageRotation });
        const canvas = document.createElement("canvas");
        canvas.width = Math.ceil(viewport.width);
        canvas.height = Math.ceil(viewport.height);
        const ctx = canvas.getContext("2d");
        if (!ctx) { alert("캔버스를 생성할 수 없습니다."); await pdf.destroy(); return; }
        await page.render({ canvasContext: ctx, viewport }).promise;
        await pdf.destroy();
        const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
        setLoaded({
          src: dataUrl,
          fileName: file.name,
          naturalWidth: canvas.width,
          naturalHeight: canvas.height,
        });
        // 편집 모드에서 이미지 재업로드 시 기존 영역 유지 (이미지 손실 복구용)
        if (!isEditMode) {
          setRegions([]);
          setSelectedId(null);
          setDrawMode(null);
        }
        setZoomPct(DEFAULT_ZOOM_PCT);
        setRowTemplateTargetId(null);
        setColGuideTargetId(null);
      } catch (e) {
        console.error("[PDF render error]", e);
        alert("PDF 렌더링에 실패했습니다.");
      }
      return;
    }

    // base64 dataURL로 읽어서 localStorage에 영속 가능하도록 처리
    const reader = new FileReader();
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string;
      const img = new Image();
      img.onload = () => {
        setLoaded({
          src: dataUrl,
          fileName: file.name,
          naturalWidth: img.naturalWidth,
          naturalHeight: img.naturalHeight,
        });
        // 편집 모드에서 이미지 재업로드 시 기존 영역 유지 (이미지 손실 복구용)
        if (!isEditMode) {
          setRegions([]);
          setSelectedId(null);
          setDrawMode(null);
        }
        setZoomPct(DEFAULT_ZOOM_PCT);
        setRowTemplateTargetId(null);
        setColGuideTargetId(null);
      };
      img.onerror = () => alert("이미지 로딩에 실패했습니다.");
      img.src = dataUrl;
    };
    reader.onerror = () => alert("이미지 파일을 읽을 수 없습니다.");
    reader.readAsDataURL(file);
  }

  function toggleMode(m: FieldType) {
    setDrawMode((cur) => (cur === m ? null : m));
  }

  function resetForm() {
    setTemplateName("");
    setLoaded(null);
    setRegions([]);
    setSelectedId(null);
    setDrawMode(null);
    setRowTemplateTargetId(null);
    setColGuideTargetId(null);
  }

  function handleDelete() {
    if (selectedTemplateId) {
      // 편집 모드 — 저장된 템플릿 삭제
      if (!confirm(`"${templateName || selectedTemplateId}" 템플릿을 삭제하시겠습니까?`)) return;
      try {
        const current = JSON.parse(localStorage.getItem(LOCAL_TEMPLATES_KEY) || "[]");
        const list = Array.isArray(current) ? current : [];
        const next = list.filter((item: any) => item?.template_id !== selectedTemplateId);
        localStorage.setItem(LOCAL_TEMPLATES_KEY, JSON.stringify(next));
        // UI-IMG-IDB-1: IndexedDB의 템플릿 이미지도 정리 (fire-and-forget)
        void deleteTemplateImage(selectedTemplateId);
        window.dispatchEvent(new Event("mysuit-ocr-template-saved"));
      } catch (err) {
        console.error("[template delete error]", err);
      }
      resetForm();
      alert("템플릿이 삭제되었습니다.");
    } else {
      // 새 템플릿 작성 중 — 폼 초기화
      if (!confirm("작성 중인 내용을 초기화하시겠습니까?")) return;
      resetForm();
    }
  }

  async function saveTemplateJson() {
    if (!loaded) {
      await ui.alert("파일을 선택해주세요.");
      return;
    }
    const name = templateName.trim();
    if (!name) {
      await ui.alert("템플릿 명을 입력해주세요.");
      return;
    }
    if (!documentType) {
      await ui.alert("문서 유형을 선택해주세요.");
      return;
    }
    if (regions.length === 0) {
      await ui.alert("필드를 하나 이상 정의해주세요.");
      return;
    }
    // edit mode: include template_id so backend updates by ID instead of creating new
    const serverPayload = selectedTemplateId
      ? { ...exportPayload, template_id: selectedTemplateId }
      : exportPayload;
    const txt = JSON.stringify(serverPayload, null, 2);

    // UI-IMG-IDB-1: 큰 base64 이미지(image.src)는 IndexedDB로 보내고, localStorage에는 메타만 저장.
    const templateId = selectedTemplateId || `LOCAL-${Date.now()}`;
    const imgSrc: string | undefined = (exportPayload as any)?.image?.src;
    if (imgSrc) {
      void saveTemplateImage(templateId, imgSrc);
    }
    const localExportPayload: any = imgSrc
      ? { ...exportPayload, image: { ...(exportPayload as any).image, src: undefined } }
      : exportPayload;

    const localTemplate = {
      template_id: templateId,
      template_name: name,
      template_json: localExportPayload,
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
      console.error("[local template save error]", err);
    }

    try {
      const res = await fetch("/templates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: txt,
      });
      if (!res.ok) throw new Error("template save failed");
      alert(isEditMode ? "템플릿이 수정되었습니다." : "템플릿이 저장되었습니다.");
    } catch (err) {
      console.error("[template save error]", err);
      alert("임시 저장소에 저장되었습니다. 서버 저장은 아직 연결되지 않았습니다.");
    }

  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) 420px",
        gridTemplateRows: "auto 1fr",
        gap: 8,
        width: "100%",
        height: "100%",
        minHeight: 0,
        minWidth: 0,
      }}
    >
      {/* Toolbar — full width */}
      <div className="oc-toolbar" style={{ gridColumn: "1 / -1", gridRow: 1, border: "1px solid var(--border)" }}>
        {(["field", "multi", "check", "table"] as FieldType[]).map((m) => {
          const labels: Record<FieldType, string> = {
            field: "필드",
            multi: "멀티필드",
            check: "체크필드",
            table: "테이블필드",
          };
          return (
            <button
              key={m}
              type="button"
              onClick={() => toggleMode(m)}
              className={`oc-mode-btn${drawMode === m ? " oc-mode-btn-active" : ""}`}
              disabled={!loaded}
            >
              {labels[m]}
            </button>
          );
        })}

        <div className="oc-zoom-group">
          <span className="oc-zoom-label">줌</span>
          <input
            type="range"
            min={10}
            max={200}
            value={zoomPct}
            onChange={(e) => setZoomPct(Number(e.target.value))}
          />
          <span className="oc-zoom-val">{zoomPct}%</span>
          <button
            type="button"
            onClick={() => setZoomPct(DEFAULT_ZOOM_PCT)}
            className="ms-btn-sm"
            disabled={!loaded}
          >
            초기화
          </button>
        </div>
      </div>

      {/* Left: canvas */}
      <div style={{ gridColumn: 1, gridRow: 2, minHeight: 0 }}>
        <OcrCanvasPane
          imgRef={imgRef}
          onPickFile={(f) => void onPickFile(f)}
          loaded={loaded}
          regions={regions}
          setRegions={setRegions}
          selectedId={selectedId}
          setSelectedId={setSelectedId}
          rowTemplateTargetId={rowTemplateTargetId}
          setRowTemplateTargetId={setRowTemplateTargetId}
          colGuideTargetId={colGuideTargetId}
          setColGuideTargetId={setColGuideTargetId}
          drawMode={drawMode}
          setDrawMode={setDrawMode}
          zoomPct={zoomPct}
        />
      </div>

      {/* Right: 삭제/저장 박스 + 패널 (col 2, row 2) */}
      <div style={{ gridColumn: 2, gridRow: 2, minHeight: 0, display: "flex", flexDirection: "column", gap: 8 }}>
        {/* 삭제 / 저장 — 독립 박스 */}
        <div style={{
          flexShrink: 0,
          display: "flex", gap: 8, justifyContent: "flex-end", alignItems: "center",
          background: "var(--panel)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          padding: "10px 12px",
        }}>
          <button type="button" onClick={handleDelete} className="ms-btn">
            삭제
          </button>
          <button type="button" onClick={() => void saveTemplateJson()}
            className="ms-btn"
            style={{ background: "var(--accent)", color: "#fff", border: "none" }}>
            {isEditMode ? "수정" : "저장"}
          </button>
        </div>
        {/* 패널 */}
        <OcrRightPanel
          imgRef={imgRef}
          templateName={templateName}
          setTemplateName={setTemplateName}
          documentType={documentType}
          setDocumentType={handleSetDocumentType}
          loaded={loaded}
          regions={regions}
          setRegions={setRegions}
          selectedId={selectedId}
          setSelectedId={setSelectedId}
          rowTemplateTargetId={rowTemplateTargetId}
          setRowTemplateTargetId={setRowTemplateTargetId}
          colGuideTargetId={colGuideTargetId}
          setColGuideTargetId={setColGuideTargetId}
          updateName={updateName}
          deleteRegion={deleteRegion}
        />
      </div>
    </div>
  );
}
