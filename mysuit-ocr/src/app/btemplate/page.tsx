"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import AppShell from "../../components/layout/AppShell";
import TemplateWorkspace from "../../components/ocr/TemplateWorkspace";

const OcrAnnotator = dynamic(
  () => import("../../components/ocr/OcrAnnotator"),
  {
    ssr: false,
    loading: () => <div style={{ padding: 16 }}>OCR 로딩중...</div>,
  },
);

function BTemplatePageContent() {
  const searchParams = useSearchParams();
  const initialMode = searchParams.get("mode") === "new" ? "editor" : "list";
  const [mode, setMode] = useState<"list" | "editor">(initialMode);

  if (mode === "editor") {
    return (
      <AppShell
        headerTitle="BTemplate / New Template"
        scrollMode="fixed"
      >
        <div style={{ width: "100%", height: "100%", minHeight: 0 }}>
          <OcrAnnotator />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell headerTitle="BTemplate" scrollMode="page">
      <TemplateWorkspace onNewTemplate={() => setMode("editor")} />
    </AppShell>
  );
}

export default function Page() {
  return (
    <Suspense>
      <BTemplatePageContent />
    </Suspense>
  );
}
