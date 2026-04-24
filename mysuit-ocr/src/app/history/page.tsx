"use client";

import AppShell from "../../components/layout/AppShell";
import RequireLogin from "@/components/common/RequireLogin";
import HistoryWorkspace from "../../components/history/HistoryWorkspace";

export default function Page() {
  return (
    <RequireLogin>
      <AppShell headerTitle={"History"} scrollMode="page">
        <HistoryWorkspace />
      </AppShell>
    </RequireLogin>
  );
}
