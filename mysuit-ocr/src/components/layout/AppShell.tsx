"use client";

import React, { useState } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";

type ScrollMode = "page" | "fixed";

export default function AppShell({
  headerTitle,
  headerRight,
  scrollMode = "fixed",
  children,
}: {
  headerTitle: React.ReactNode;
  headerRight?: React.ReactNode;
  scrollMode?: ScrollMode;
  children: React.ReactNode;
}) {
  // ✅ Sidebar 접힘 상태를 Shell에서 관리(레이아웃/에디터 리사이즈 안정)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <main
      style={{
        height: "100vh",
        width: "100%", // ✅ 100vw 대신 100% (미세 오버플로우 방지)
        display: "flex",
        background: "var(--bg)",
        overflow: "hidden", // ✅ 가장 바깥에서 삐져나감 방지
      }}
    >
      <Sidebar
        collapsed={sidebarCollapsed}
        onCollapsedChange={setSidebarCollapsed}
      />

      <section
        style={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          height: "100%",
          overflow: "hidden", // ✅ 내부도 한번 더 막아줌(안전)
        }}
      >
        <Header title={headerTitle} right={headerRight} />

        {/*
          ✅ 패딩(상/하/좌/우)을 “항상” 보이게 유지하기 위한 2단 래퍼
          - 바깥 래퍼: padding 전담(스크롤 없음)
          - 안쪽 래퍼: 실제 스크롤/사이징 전담
          
          이유:
          children 쪽에서 height: '100%' 같은 값을 쓰면, 부모 padding 영역까지 덮어버려
          하단 여백이 없어 보이는 현상이 생길 수 있음.
        */}
        <div
          style={{
            flex: 1,
            minHeight: 0,
            padding: 18,
            boxSizing: "border-box",
            overflowX: "hidden",
            overflowY: "visible",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              flex: 1,
              minHeight: 0,
              overflowY: scrollMode === "page" ? "auto" : "hidden",
              overflowX: "hidden",
            }}
          >
            {children}
          </div>
        </div>
      </section>
    </main>
  );
}
