"use client";

import AppShell from "../../components/layout/AppShell";
import RunOcrWorkspace from "../../components/runocr/RunOcrWorkspace";

export default function Page() {
  return (
    <AppShell headerTitle={"RunOCR"} scrollMode="fixed">
      <RunOcrWorkspace variant="runocr" />
    </AppShell>
  );
}
