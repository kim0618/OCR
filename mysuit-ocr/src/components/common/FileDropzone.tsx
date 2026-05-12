"use client";

import React, { useRef, useState } from "react";

type Props = {
  /** Called when user drops or picks a file via the picker */
  onPickFile: (file: File) => void;
  /** File picker accept attribute. Default supports image + PDF + TIFF. */
  accept?: string;
  /** When true, render `children` instead of the empty state. Drag/drop still works. */
  hasFile?: boolean;
  /** Content rendered when hasFile is true (e.g. preview UI) */
  children?: React.ReactNode;
  /** Optional external ref to the underlying file input (allows external triggers like "파일 변경") */
  fileInputRef?: React.RefObject<HTMLInputElement | null>;
  /** Optional extra class on the outer wrapper */
  className?: string;
  /** Optional inline styles on the outer wrapper */
  style?: React.CSSProperties;
};

/**
 * Shared dropzone used by RunOCR/Template upload flows.
 * - Drag visual feedback (uw-dropzone-drag)
 * - Click to open file picker (when empty)
 * - Accepts image/pdf/tiff by default
 */
export default function FileDropzone({
  onPickFile,
  accept = "image/*,application/pdf,.tif,.tiff",
  hasFile = false,
  children,
  fileInputRef,
  className,
  style,
}: Props) {
  const [isDragging, setIsDragging] = useState(false);
  const internalRef = useRef<HTMLInputElement | null>(null);
  const inputRef = fileInputRef ?? internalRef;

  function openPicker() {
    inputRef.current?.click();
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onPickFile(f);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) onPickFile(f);
    // reset so the same file can be re-selected
    e.target.value = "";
  }

  const cls = [
    "uw-dropzone",
    isDragging ? "uw-dropzone-drag" : "",
    hasFile ? "uw-dropzone-filled" : "",
    className,
  ].filter(Boolean).join(" ");

  return (
    <div
      className={cls}
      style={style}
      onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
      onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
      onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); }}
      onDrop={handleDrop}
      onClick={hasFile ? undefined : openPicker}
    >
      {hasFile && children ? children : (
        <div className="uw-empty-state">
          <div className="uw-empty-icon">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M16 22V10M16 10L11 15M16 10L21 15" stroke="#0891b2" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M7 26h18" stroke="#0891b2" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="uw-empty-title">문서를 드래그하거나 업로드하세요</div>
          <div className="uw-empty-sub">이미지(.jpeg .jpg .png .tif .tiff) 및 PDF 지원</div>
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); openPicker(); }}
            className="uw-upload-btn"
          >
            파일 선택
          </button>
        </div>
      )}
      <input
        ref={inputRef as React.Ref<HTMLInputElement>}
        type="file"
        accept={accept}
        style={{ display: "none" }}
        onChange={handleChange}
      />
    </div>
  );
}
