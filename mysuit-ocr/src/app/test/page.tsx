"use client";

import AppShell from "../../components/layout/AppShell";
import TestWorkspace from "../../components/test/TestWorkspace";

export default function Page() {
  return (
    <AppShell headerTitle={"Test"} scrollMode="fixed">
      <TestWorkspace />
    </AppShell>
  );
}
