"use client";

import AppShell from "../../components/layout/AppShell";
import RequireLogin from "@/components/common/RequireLogin";
import BHistoryWorkspace from "../../components/history/BHistoryWorkspace";

export default function Page() {
  return (
    <RequireLogin>
      <AppShell headerTitle={"BHistory"} scrollMode="page">
        <BHistoryWorkspace />
      </AppShell>
    </RequireLogin>
  );
}
