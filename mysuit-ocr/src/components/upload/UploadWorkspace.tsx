"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useUi } from "../common/AppProviders";
import OcrResultPanel, { type OcrResult, type OcrFieldResult } from "./OcrResultPanel";
import OcrDocViewer from "./OcrDocViewer";
import CornerAdjust, { type Corner } from "./CornerAdjust";
import type { Region, FieldType, LoadedImage } from "../ocr/core/types";

const OcrCanvasPane = dynamic(() => import("../ocr/OcrCanvasPane"), { ssr: false });

type TemplateItem = {
  id: string;
  name: string;
};

const DEFAULT_TEMPLATES: TemplateItem[] = [];

function isTiff(file: File) {
  return (
    file.type === "image/tiff" ||
    file.type === "image/tif" ||
    file.name.toLowerCase().endsWith(".tif") ||
    file.name.toLowerCase().endsWith(".tiff")
  );
}

type PreprocessDetail = {
  status: string;
  detail: string;
};

type PreprocessResult = {
  image_size: string;
  document?: PreprocessDetail;
  upscale: PreprocessDetail;
  deskew: PreprocessDetail;
  denoise: PreprocessDetail;
  contrast: PreprocessDetail;
} | null;

export default function UploadWorkspace() {
  const router = useRouter();
  const ui = useUi();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadStartRef = useRef<number>(0);

  const [activeTemplateId, setActiveTemplateId] = useState<string>("");
  const [templates, setTemplates] = useState<TemplateItem[]>(DEFAULT_TEMPLATES);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [renderedUrl, setRenderedUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadDuration, setUploadDuration] = useState<string | null>(null);
  const [preprocessResult, setPreprocessResult] = useState<PreprocessResult>(null);
  const [isPreprocessing, setIsPreprocessing] = useState(false);

  // OCR 결과 상태
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);
  const [isOcrRunning, setIsOcrRunning] = useState(false);
  const [selectedFieldIndex, setSelectedFieldIndex] = useState<number | null>(null);
  const [processedImageUrl, setProcessedImageUrl] = useState<string | null>(null);
  const [corners, setCorners] = useState<Corner[]>([]);
  const [showCornerAdjust, setShowCornerAdjust] = useState(false);

  // OcrCanvasPane용 상태
  const canvasImgRef = useRef<HTMLImageElement>(null!);
  const [canvasRegions, setCanvasRegions] = useState<Region[]>([]);
  const [canvasSelectedId, setCanvasSelectedId] = useState<string | null>(null);
  const [canvasDrawMode, setCanvasDrawMode] = useState<FieldType | null>(null);
  const [canvasZoom, setCanvasZoom] = useState(100);
  const [rowTemplateTargetId, setRowTemplateTargetId] = useState<string | null>(null);
  const [colGuideTargetId, setColGuideTargetId] = useState<string | null>(null);
  const [canvasLoaded, setCanvasLoaded] = useState<LoadedImage | null>(null);
  const [resultTab, setResultTab] = useState<"preview" | "custom" | "validation">("custom");

  // canvasSelectedId ↔ selectedFieldIndex 연동
  useEffect(() => {
    if (!canvasSelectedId) { setSelectedFieldIndex(null); return; }
    const idx = canvasRegions.findIndex((r) => r.id === canvasSelectedId);
    setSelectedFieldIndex(idx >= 0 ? idx : null);
  }, [canvasSelectedId, canvasRegions]);

  useEffect(() => {
    if (selectedFieldIndex == null) return;
    const region = canvasRegions[selectedFieldIndex];
    if (region && region.id !== canvasSelectedId) {
      setCanvasSelectedId(region.id);
    }
  }, [selectedFieldIndex]);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/templates");
        const json = await res.json();
        const list = json.resultMap?.templateList ?? [];
        const mapped = list.map((t: any) => ({ id: t.template_id, name: t.template_name }));
        setTemplates(mapped);
        // 기본값: 전체 인식 (빈 값)
      } catch {
        // 서버 미실행 시 무시 (기본값: 빈 목록)
      }
    })();
  }, []);

  const hintSections = useMemo(
    () => [
      {
        title: "지원 형식",
        desc: "업로드/내보내기 가능한 파일 형식",
        items: [
          "Upload: jpeg, jpg, png, pdf, tif, tiff",
          "Export: json, xlsx, html, hwp(예정)",
        ],
      },
      {
        title: "자동 처리",
        desc: "업로드 직후 자동으로 수행되는 보정",
        items: ["기울기 보정", "노이즈 제거", "대비 강화", "언어 감지"],
      },
      {
        title: "업로드 가이드",
        desc: "정확도를 높이기 위한 권장 조건",
        items: [
          "150~300dpi, 텍스트 선명, 흔들림 없음",
          "글자 높이 10px 이상",
          "가로 2000px 내외 권장",
          "업로드 파일은 24시간 후 자동 삭제",
        ],
      },
    ],
    [],
  );

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      setRenderedUrl(null);
      setUploadDuration(null);
      setPreprocessResult(null);
      return;
    }

    const isNativeImage =
      selectedFile.type.startsWith("image/") && !isTiff(selectedFile);
    const isPdf = selectedFile.type === "application/pdf";
    const isTiffFile = isTiff(selectedFile);

    const elapsed = Date.now() - uploadStartRef.current;
    setUploadDuration(`${(elapsed / 1000).toFixed(2)}초`);

    if (!isNativeImage && !isPdf && !isTiffFile) {
      setPreviewUrl(null);
      setRenderedUrl(null);
      return;
    }

    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    setRenderedUrl(null);

    let cancelled = false;

    if (isPdf) {
      (async () => {
        try {
          const pdfjs = await import("pdfjs-dist/legacy/build/pdf.js");
          pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.js";
          const pdf = await pdfjs.getDocument(url).promise;
          const page = await pdf.getPage(1);
          const viewport = page.getViewport({ scale: 2 });
          const canvas = document.createElement("canvas");
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          const ctx = canvas.getContext("2d")!;
          await page.render({ canvasContext: ctx, viewport }).promise;
          if (!cancelled) setRenderedUrl(canvas.toDataURL("image/png"));
        } catch (err) {
          console.error("[PDF render error]", err);
        }
      })();
    }

    if (isTiffFile) {
      (async () => {
        try {
          const utifModule = await import("utif");
          const utif = (utifModule as any).default ?? utifModule;
          const arrayBuffer = await selectedFile.arrayBuffer();
          const ifds = utif.decode(arrayBuffer);
          utif.decodeImage(arrayBuffer, ifds[0]);
          const first = ifds[0];
          const rgba = utif.toRGBA8(first);
          const canvas = document.createElement("canvas");
          canvas.width = first.width;
          canvas.height = first.height;
          const ctx = canvas.getContext("2d")!;
          const imageData = ctx.createImageData(first.width, first.height);
          imageData.data.set(rgba);
          ctx.putImageData(imageData, 0, 0);
          if (!cancelled) setRenderedUrl(canvas.toDataURL("image/png"));
        } catch (err) {
          console.error("[TIFF render error]", err);
        }
      })();
    }

    return () => {
      cancelled = true;
      URL.revokeObjectURL(url);
    };
  }, [selectedFile]);

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  async function detectCorners(file: File) {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/preprocess/corners`, { method: "POST", body: formData });
      if (!res.ok) { console.error("[corners] HTTP", res.status); return; }
      const json = await res.json();
      console.log("[corners]", json);
      if (json.corners?.length === 4) setCorners(json.corners);
    } catch (e) { console.error("[corners] error", e); }
  }

  async function runPreprocess(file: File) {
    setIsPreprocessing(true);
    setPreprocessResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/preprocess/info`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("전처리 요청 실패");
      const json = await res.json();
      setPreprocessResult(json.result ?? null);
    } catch (err) {
      console.error("[Preprocess error]", err);
      await ui.alert("전처리 중 오류가 발생했습니다.");
    } finally {
      setIsPreprocessing(false);
    }
  }

  function pickFile(f: File) {
    uploadStartRef.current = Date.now();
    setSelectedFile(f);
    setOcrResult(null);
    setProcessedImageUrl(null);
    setCorners([]);
    setShowCornerAdjust(false);
    void runPreprocess(f);
    void detectCorners(f);
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) pickFile(f);
  }

  function formatFileType(file: File) {
    return file.name.split(".").pop()?.toUpperCase() ?? file.type;
  }

  async function runOcr() {
    if (!selectedFile) return;
    setIsOcrRunning(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      if (activeTemplateId) formData.append("template_id", activeTemplateId);
      if (corners.length === 4) formData.append("corners", JSON.stringify(corners));
      const res = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/ocr/extract`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("OCR 요청 실패");
      const json = await res.json();
      setOcrResult(json);
      if (json.processed_image) {
        setProcessedImageUrl(json.processed_image);
      }
      const ocrRegions: Region[] = (json.fields ?? []).map((f: OcrFieldResult, i: number) => ({
        id: `ocr_${i}`,
        name: f.name,
        fieldType: (f.field_type || "field") as FieldType,
        x: f.bbox[0],
        y: f.bbox[1],
        width: f.bbox[2],
        height: f.bbox[3],
      }));
      setCanvasRegions((prev) => {
        const userRegions = prev.filter((r) => !r.id.startsWith("ocr_"));
        return [...ocrRegions, ...userRegions];
      });
      setCanvasSelectedId(null);
    } catch (err) {
      console.error("[OCR error]", err);
      await ui.alert("OCR 처리 중 오류가 발생했습니다.");
    } finally {
      setIsOcrRunning(false);
    }
  }

  // displayUrl 변경 시 canvasLoaded 업데이트
  useEffect(() => {
    // OCR 완료 후엔 전처리된 이미지 사용, 아니면 원본
    const url = processedImageUrl
      ?? ((selectedFile?.type === "application/pdf" || (selectedFile && isTiff(selectedFile)))
        ? renderedUrl : previewUrl);
    if (!url) { setCanvasLoaded(null); return; }
    const img = new Image();
    img.onload = () => {
      setCanvasLoaded({
        src: url,
        fileName: selectedFile?.name ?? "",
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
      });
    };
    img.src = url;
  }, [previewUrl, renderedUrl, selectedFile, processedImageUrl]);

  const needsRender = selectedFile
    ? selectedFile.type === "application/pdf" || isTiff(selectedFile)
    : false;

  const displayUrl = needsRender ? renderedUrl : previewUrl;
  const isRendering = needsRender && !renderedUrl && !!previewUrl;

  // OCR 결과 화면에서 사용할 URL (전처리 이미지 우선)
  const ocrDisplayUrl = processedImageUrl ?? displayUrl;

  // OCR 결과 화면
  if (ocrResult && selectedFile) {
    return (
      <div className="uw-result-root">
        {/* 왼쪽: Custom 탭이면 OcrCanvasPane, 아니면 OcrDocViewer */}
        <div className="uw-result-doc" style={{ position: "relative" }}>
          {ocrDisplayUrl && resultTab === "custom" && canvasLoaded ? (
            <OcrCanvasPane
              imgRef={canvasImgRef}
              loaded={canvasLoaded}
              regions={canvasRegions}
              setRegions={setCanvasRegions}
              selectedId={canvasSelectedId}
              setSelectedId={setCanvasSelectedId}
              drawMode={canvasDrawMode}
              setDrawMode={setCanvasDrawMode}
              zoomPct={canvasZoom}
              rowTemplateTargetId={rowTemplateTargetId}
              setRowTemplateTargetId={setRowTemplateTargetId}
              colGuideTargetId={colGuideTargetId}
              setColGuideTargetId={setColGuideTargetId}
            />
          ) : ocrDisplayUrl ? (
            <OcrDocViewer
              imageUrl={ocrDisplayUrl}
              fields={ocrResult.fields}
              selectedIndex={selectedFieldIndex}
              onSelectField={setSelectedFieldIndex}
            />
          ) : (
            <span style={{ color: "var(--muted)" }}>문서 영역</span>
          )}
          {isOcrRunning && <div className="uw-scan-overlay"><div className="uw-scan-line" /></div>}
        </div>

        {/* 오른쪽: 결과 패널 */}
        <div className="uw-result-panel">
          <OcrResultPanel
            result={ocrResult}
            onRerun={runOcr}
            onRevalidate={async (targets) => {
              if (!selectedFile) return [];
              const formData = new FormData();
              // 전처리된 이미지가 있으면 그걸 사용 (bbox 좌표 일치)
              if (processedImageUrl) {
                const blob = await fetch(processedImageUrl).then((r) => r.blob());
                formData.append("file", blob, "processed.jpg");
              } else {
                formData.append("file", selectedFile);
              }
              const url = `/ocr/revalidate?regions=${encodeURIComponent(JSON.stringify(targets))}`;
              const res = await fetch(url, { method: "POST", body: formData });
              if (!res.ok) throw new Error("재검증 실패");
              const json = await res.json();
              return json.results ?? [];
            }}
            selectedIndex={selectedFieldIndex}
            onSelectField={setSelectedFieldIndex}
            onTabChange={setResultTab}
            drawMode={canvasDrawMode}
            onDrawModeChange={(mode) => setCanvasDrawMode(mode as FieldType | null)}
            isScanning={isOcrRunning}
            onScanChange={setIsOcrRunning}
            canvasRegions={canvasRegions}
            onPartialOcr={async (targets) => {
              if (!selectedFile) return [];
              const formData = new FormData();
              if (processedImageUrl) {
                const blob = await fetch(processedImageUrl).then((r) => r.blob());
                formData.append("file", blob, "processed.jpg");
              } else {
                formData.append("file", selectedFile);
              }
              const url = `/ocr/revalidate?regions=${encodeURIComponent(JSON.stringify(targets))}`;
              const res = await fetch(url, { method: "POST", body: formData });
              if (!res.ok) throw new Error("부분 OCR 실패");
              const json = await res.json();
              return json.results ?? [];
            }}
          />
        </div>

        {/* 숨겨진 파일 인풋 */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,application/pdf,.tif,.tiff"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) pickFile(f);
          }}
        />
      </div>
    );
  }

  // 업로드 화면 (기존)
  const dropzoneClass = [
    "uw-dropzone",
    isDragging ? "uw-dropzone-drag" : "",
    selectedFile ? "uw-dropzone-filled" : "",
  ].filter(Boolean).join(" ");

  return (
    <div className="uw-root">
      {/* Top: Template bar */}
      <div className="uw-topbar">
        <span className="uw-topbar-label">Template</span>

        <div className="uw-topbar-group uw-template-select-wrap">
          <select
            value={activeTemplateId}
            onChange={(e) => setActiveTemplateId(e.target.value)}
            className="ms-select uw-template-select"
          >
            <option value="">자동 인식</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
          <span className="uw-select-arrow">▾</span>
        </div>

        <button type="button" className="hw-btn-primary" onClick={() => router.push("/ocr?mode=new")}>
          + New Template
        </button>
      </div>

      {/* Left: upload panel */}
      <div className="uw-upload-panel">
        <div
          className={dropzoneClass}
          onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
          onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); }}
          onDrop={onDrop}
        >
          {previewUrl && selectedFile ? (
            <div className="uw-preview-wrap">
              <div className="uw-preview-img-area" style={{ position: "relative" }}>
                {isRendering ? (
                  <div className="uw-empty-sub" style={{ margin: "auto" }}>
                    {isTiff(selectedFile) ? "TIFF" : "PDF"} 렌더링 중...
                  </div>
                ) : displayUrl ? (
                  showCornerAdjust ? (
                    <CornerAdjust
                      imageUrl={displayUrl}
                      corners={corners}
                      onCornersChange={setCorners}
                    />
                  ) : (
                    <img src={displayUrl} alt="preview" className="uw-preview-img" />
                  )
                ) : null}
                {isOcrRunning && <div className="uw-scan-overlay"><div className="uw-scan-line" /></div>}
              </div>
              <div className="uw-preview-footer">
                <div className="uw-filename-chip" title={selectedFile.name}>
                  {selectedFile.name}
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (showCornerAdjust) {
                      setShowCornerAdjust(false);
                    } else {
                      setCorners([]); // 빈 상태로 시작 - 직접 클릭
                      setShowCornerAdjust(true);
                    }
                  }}
                  className="ms-btn-sm"
                  style={showCornerAdjust ? { background: "var(--accent)", color: "white", borderColor: "var(--accent)" } : {}}
                >
                  {showCornerAdjust
                    ? corners.length < 4 ? `코너 지정 중 (${corners.length}/4)` : "✓ 조정 완료"
                    : "코너 지정"}
                </button>
                <button type="button" onClick={openFilePicker} className="ms-btn-sm">
                  파일 변경
                </button>
              </div>
            </div>
          ) : (
            <div className="uw-empty-state">
              <div className="uw-empty-icon">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M16 22V10M16 10L11 15M16 10L21 15" stroke="#0891b2" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M7 26h18" stroke="#0891b2" strokeWidth="2" strokeLinecap="round"/>
                </svg>
              </div>
              <div className="uw-empty-title">문서를 드래그하거나 업로드하세요</div>
              <div className="uw-empty-sub">이미지(.jpeg .jpg .png .tif .tiff) 및 PDF 지원</div>
              <button type="button" onClick={openFilePicker} className="uw-upload-btn">
                파일 선택
              </button>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,application/pdf,.tif,.tiff"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) pickFile(f);
            }}
          />
        </div>
      </div>

      {/* Right: guide or file info */}
      <aside className="uw-guide-panel">
        {selectedFile ? (
          <div className="uw-guide-content">
            <div className="uw-file-section">
              <div className="uw-file-section-title">업로드 파일</div>
              <div className="uw-file-row">
                <span className="uw-file-label">파일명</span>
                <span className="uw-file-value" title={selectedFile.name}>{selectedFile.name}</span>
              </div>
              <div className="uw-file-row">
                <span className="uw-file-label">파일타입</span>
                <span className="uw-file-value">{formatFileType(selectedFile)}</span>
              </div>
              <div className="uw-file-row">
                <span className="uw-file-label">소요 시간</span>
                <span className="uw-file-value">{uploadDuration ?? "측정 중..."}</span>
              </div>
            </div>

            <div className="uw-file-section">
              <div className="uw-file-section-title">자동 처리 결과</div>
              {isPreprocessing ? (
                <div className="uw-process-item">
                  <span>전처리 진행 중...</span>
                </div>
              ) : preprocessResult ? (
                <>
                  <div className="uw-process-item">
                    <span>이미지 크기</span>
                    <span className="uw-process-done">{preprocessResult.image_size}</span>
                  </div>
                  {preprocessResult.document && (
                    <>
                      <div className="uw-process-item">
                        <span>문서 감지</span>
                        <span className="uw-process-done">{preprocessResult.document.status}</span>
                      </div>
                      <div className="uw-process-detail">{preprocessResult.document.detail}</div>
                    </>
                  )}
                  <div className="uw-process-item">
                    <span>해상도 보정</span>
                    <span className="uw-process-done">{preprocessResult.upscale.status}</span>
                  </div>
                  <div className="uw-process-detail">{preprocessResult.upscale.detail}</div>
                  <div className="uw-process-item">
                    <span>기울기 보정</span>
                    <span className="uw-process-done">{preprocessResult.deskew.status}</span>
                  </div>
                  <div className="uw-process-detail">{preprocessResult.deskew.detail}</div>
                  <div className="uw-process-item">
                    <span>노이즈 제거</span>
                    <span className="uw-process-done">{preprocessResult.denoise.status}</span>
                  </div>
                  <div className="uw-process-detail">{preprocessResult.denoise.detail}</div>
                  <div className="uw-process-item">
                    <span>대비 강화</span>
                    <span className="uw-process-done">{preprocessResult.contrast.status}</span>
                  </div>
                  <div className="uw-process-detail">{preprocessResult.contrast.detail}</div>
                </>
              ) : (
                <div className="uw-process-item">
                  <span>대기 중</span>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="uw-guide-content">
            {hintSections.map((sec) => (
              <div key={sec.title} className="uw-guide-section">
                <div className="uw-guide-section-header">
                  <span className="uw-guide-section-title">{sec.title}</span>
                  <span className="uw-guide-section-desc">{sec.desc}</span>
                </div>
                <ul className="uw-guide-list">
                  {sec.items.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        <button
          type="button"
          disabled={!selectedFile || isPreprocessing || isOcrRunning}
          className={`uw-run-btn ${isOcrRunning ? "uw-run-btn-loading" : ""}`}
          onClick={() => void runOcr()}
        >
          {isOcrRunning ? (
            <>
              <svg width="16" height="16" viewBox="0 0 20 20" fill="none" style={{ animation: "spin 0.8s linear infinite" }}>
                <circle cx="10" cy="10" r="8" stroke="rgba(255,255,255,0.3)" strokeWidth="2.5"/>
                <path d="M10 2a8 8 0 0 1 8 8" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round"/>
              </svg>
              OCR 처리 중...
            </>
          ) : (
            "Run OCR"
          )}
        </button>
      </aside>
    </div>
  );
}
