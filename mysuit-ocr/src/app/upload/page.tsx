"use client";

import AppShell from "../../components/layout/AppShell";
import UploadWorkspace from "../../components/upload/UploadWorkspace";

export default function Page() {
  return (
    <AppShell headerTitle={"Upload"} scrollMode="fixed">
      <UploadWorkspace />
    </AppShell>
  );
}
