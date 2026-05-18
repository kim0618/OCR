"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

type NavItem = {
  label: string;
  href: string;
  icon?: string;
  forceActive?: boolean;
};

function NavIcon({ name, size = 16, color = "currentColor" }: { name: string; size?: number; color?: string }) {
  const s = String(size);
  switch (name) {
    case "upload":
      return (
        <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
          <path d="M10 14V4M10 4L6 8M10 4L14 8" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M4 16h12" stroke={color} strokeWidth="1.8" strokeLinecap="round"/>
        </svg>
      );
    case "template":
      return (
        <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
          <rect x="3" y="2" width="14" height="16" rx="2" stroke={color} strokeWidth="1.8"/>
          <line x1="6" y1="6" x2="14" y2="6" stroke={color} strokeWidth="1.5" strokeLinecap="round"/>
          <line x1="6" y1="10" x2="14" y2="10" stroke={color} strokeWidth="1.5" strokeLinecap="round"/>
          <line x1="6" y1="14" x2="10" y2="14" stroke={color} strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      );
    case "history":
      return (
        <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="7.5" stroke={color} strokeWidth="1.8"/>
          <path d="M10 6V10.5L13 12.5" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      );
    case "test":
      return (
        <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
          <path d="M7 2.5V7L3.5 14.5C3 15.5 3.7 16.5 4.8 16.5H15.2C16.3 16.5 17 15.5 16.5 14.5L13 7V2.5" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          <line x1="6" y1="2.5" x2="14" y2="2.5" stroke={color} strokeWidth="1.8" strokeLinecap="round"/>
          <circle cx="8" cy="12" r="0.8" fill={color}/>
          <circle cx="11" cy="13.5" r="0.8" fill={color}/>
        </svg>
      );
    case "restore":
      return (
        <svg width={s} height={s} viewBox="0 0 20 20" fill="none">
          <path d="M3.5 10a6.5 6.5 0 1 0 1.3-3.9" stroke={color} strokeWidth="1.8" strokeLinecap="round"/>
          <path d="M3.5 4.5V8H7" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      );
    default:
      return null;
  }
}

const DEFAULT_ITEMS: NavItem[] = [
  { label: "Template",  href: "/template",     icon: "template" },
  { label: "RunOCR",    href: "/runocr",       icon: "upload" },
  { label: "History",   href: "/history",      icon: "history" },
  { label: "Restore",    href: "/autorestore",  icon: "restore" },
  { label: "BUpload",   href: "/upload",       icon: "upload" },
  { label: "BTemplate", href: "/btemplate",    icon: "template" },
  { label: "BHistory",  href: "/bhistory",     icon: "history" },
  { label: "Test",      href: "/test",         icon: "test" },
];

export default function Sidebar({
  items = DEFAULT_ITEMS,
  collapsed: collapsedProp,
  onCollapsedChange,
}: {
  items?: NavItem[];
  /** AppShell에서 상태를 끌어올릴 때 사용(선택) */
  collapsed?: boolean;
  onCollapsedChange?: (next: boolean) => void;
}) {
  const pathname = usePathname();

  // ✅ Controlled/Uncontrolled 모두 지원
  const [collapsedState, setCollapsedState] = useState(false);
  const collapsed = collapsedProp ?? collapsedState;
  const setCollapsed = (next: boolean) => {
    if (collapsedProp === undefined) setCollapsedState(next);
    onCollapsedChange?.(next);
  };

  const [selectedSite, setSelectedSite] = useState("");

  const width = collapsed ? 40 : 150;
  const brandCollapsed = "M";

  // ✅ “위치 고정”을 위한 슬롯 높이 (필요하면 수치만 조정하면 됨)
  const TOP_SLOT_H = 32;
  const MENU_SLOT_H = 20;

  return (
    <aside
      style={{
        width,
        flex: `0 0 ${width}px`,
        background: "var(--panel)",
        boxShadow: "var(--shadowSoft)",
        padding: collapsed ? "16px 6px" : "16px 12px",
        display: "flex",
        flexDirection: "column",
        gap: 14,
        transition: "width 160ms ease",
        overflow: "hidden",
      }}
    >
      {/* Top: ✅ 항상 같은 높이(슬롯) */}
      <div
        style={{
          height: TOP_SLOT_H,
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "space-between",
        }}
      >
        {collapsed ? (
          // 접힌 상태: M 클릭으로 펼치기
          <button
            type="button"
            aria-label="Expand sidebar"
            title="MySuit OCR (Expand)"
            onClick={() => setCollapsed(false)}
            style={{
              width: 28,
              height: 28,
              borderRadius: 10,
              border: "none",
              background: "var(--panel2)",
              color: "var(--accent)",
              fontWeight: 800,
              fontSize: 12,
              display: "grid",
              placeItems: "center",
              userSelect: "none",
              letterSpacing: 0.5,
              cursor: "pointer",
            }}
          >
            {brandCollapsed}
          </button>
        ) : (
          <>
            <div style={{ fontSize: 16, fontWeight: 700 }}>MySuit OCR</div>

            {/* 펼친 상태: ≡ 클릭으로 접기 */}
            <button
              type="button"
              aria-label="Collapse sidebar"
              onClick={() => setCollapsed(true)}
              style={{
                border: "none",
                background: "transparent",
                padding: 7,
                cursor: "pointer",
                color: "var(--muted)",
                fontSize: 18,
                lineHeight: 1,
                width: 28,
                height: 28,
                borderRadius: 8,
                display: "grid",
                placeItems: "center",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background =
                  "rgba(255,255,255,0.06)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background =
                  "transparent";
              }}
            >
              ≡
            </button>
          </>
        )}
      </div>

      {/* 사이트 선택 — MENU 위 */}
      {!collapsed ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)", letterSpacing: 0.4 }}>
            사이트
          </div>
          <select
            value={selectedSite}
            onChange={(e) => setSelectedSite(e.target.value)}
            style={{
              width: "100%",
              background: "var(--panel2)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 7,
              padding: "6px 24px 6px 8px",
              color: selectedSite ? "var(--text)" : "var(--muted)",
              fontSize: 12,
              outline: "none",
              cursor: "pointer",
              appearance: "none",
              WebkitAppearance: "none",
              boxSizing: "border-box",
              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' stroke='%2394a3b8' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
              backgroundRepeat: "no-repeat",
              backgroundPosition: "right 7px center",
            }}
          >
            <option value="">사이트 선택</option>
            <option value="site-a">사이트 A</option>
            <option value="site-b">사이트 B</option>
            <option value="site-c">사이트 C</option>
          </select>
        </div>
      ) : (
        <div
          title="사이트 선택"
          style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 28 }}
        >
          <span style={{ fontSize: 12, color: "var(--muted)" }}>🌐</span>
        </div>
      )}

      {/* Menu slot: ✅ 접혀도 높이 유지해서 아래 메뉴 시작 Y를 고정 */}
      <div
        style={{ height: MENU_SLOT_H, display: "flex", alignItems: "center" }}
      >
        {!collapsed ? (
          <div style={{ fontSize: 11, color: "var(--muted)", fontWeight: 600 }}>MENU</div>
        ) : (
          <div style={{ width: "100%" }} />
        )}
      </div>

      {/* Nav */}
      <nav style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {items.map((item) => {
          const active =
            Boolean(item.forceActive) ||
            (item.href !== "#" && pathname === item.href);

          return (
            <Link
              key={item.label}
              href={item.href}
              style={{ textDecoration: "none" }}
              aria-label={item.label}
              title={collapsed ? item.label : undefined}
              onClick={(e) => {
                if (item.href === "#") e.preventDefault();
              }}
            >
              <div
                style={{
                  fontSize: 13,
                  fontWeight: active ? 800 : 600,
                  color: active ? "var(--accent)" : "var(--muted)",
                  padding: collapsed ? "9px 0" : "9px 10px",
                  borderRadius: 10,
                  background: active ? "var(--accentBg)" : "transparent",
                  boxShadow: active && !collapsed ? `inset 3px 0 0 var(--accent)` : undefined,
                  cursor: item.href === "#" ? "not-allowed" : "pointer",
                  userSelect: "none",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: collapsed ? "center" : "flex-start",
                  gap: 9,
                  transition: "background 0.15s, color 0.15s",
                  position: "relative",
                }}
                onMouseEnter={(e) => {
                  if (!active) (e.currentTarget as HTMLDivElement).style.background = "var(--panel2)";
                }}
                onMouseLeave={(e) => {
                  if (!active) (e.currentTarget as HTMLDivElement).style.background = "transparent";
                }}
              >
                {item.icon && (
                  <NavIcon
                    name={item.icon}
                    size={15}
                    color={active ? "var(--accent)" : "var(--muted)"}
                  />
                )}
                {!collapsed && item.label}
              </div>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
