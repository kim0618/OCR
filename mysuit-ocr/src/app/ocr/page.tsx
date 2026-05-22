"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import AppShell from "../../components/layout/AppShell";
import TemplateWorkspace from "../../components/template/TemplateWorkspace";

const OcrAnnotator = dynamic(
  () => import("../../components/template/ui/OcrAnnotator"),
  {
    ssr: false,
    loading: () => <div style={{ padding: 16 }}>OCR 로딩중...</div>,
  },
);

function OcrPageContent() {
  const searchParams = useSearchParams();
  const initialMode = searchParams.get("mode") === "new" ? "editor" : "list";
  const [mode, setMode] = useState<"list" | "editor">(initialMode);

  if (mode === "editor") {
    return (
      <AppShell
        headerTitle="Template / New Template"
        scrollMode="fixed"
      >
        <div style={{ width: "100%", height: "100%", minHeight: 0 }}>
          <OcrAnnotator />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell headerTitle="Template" scrollMode="page">
      <TemplateWorkspace onNewTemplate={() => setMode("editor")} />
    </AppShell>
  );
}

export default function Page() {
  return (
    <Suspense>
      <OcrPageContent />
    </Suspense>
  );
}
