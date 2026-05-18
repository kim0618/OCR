"use client";

import AppShell from "../../components/layout/AppShell";
import RequireLogin from "@/components/common/RequireLogin";
import AutoRestoreWorkspace from "../../components/autorestore/AutoRestoreWorkspace";

export default function Page() {
  return (
    <RequireLogin>
      <AppShell headerTitle={"Restore"} scrollMode="page">
        <AutoRestoreWorkspace />
      </AppShell>
    </RequireLogin>
  );
}
