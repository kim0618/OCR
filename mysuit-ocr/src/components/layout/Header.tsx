"use client";

import React, { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearLogin, getStoredLogin, type StoredLogin } from "@/common/storage/login";
import { useTheme } from "./utils/theme";

type HeaderProps = {
  title: React.ReactNode;
  right?: React.ReactNode;
};

function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggle}
      className="ms-btn"
      aria-label={isDark ? "라이트 모드로 전환" : "다크 모드로 전환"}
      title={isDark ? "라이트 모드" : "다크 모드"}
      style={{ padding: "7px 9px", display: "flex", alignItems: "center" }}
    >
      {isDark ? (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1" x2="12" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
          <line x1="1" y1="12" x2="3" y2="12"/>
          <line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
      ) : (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      )}
    </button>
  );
}

export default function Header({ title, right }: HeaderProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [login, setLogin] = useState<StoredLogin | null>(null);

  useEffect(() => {
    setLogin(getStoredLogin());
  }, [pathname]);

  const handleLogout = () => {
    clearLogin();
    router.replace("/login");
  };

  const hideLoginArea = pathname === "/login";

  return (
    <header className="ms-header">
      <div>{title}</div>
      <div className="ms-header-right">
        {right}
        <ThemeToggle />
        {!hideLoginArea && login?.user_id ? (
          <button type="button" onClick={handleLogout} className="ms-btn">
            로그아웃
          </button>
        ) : null}
      </div>
    </header>
  );
}
