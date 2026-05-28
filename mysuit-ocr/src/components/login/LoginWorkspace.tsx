"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api, { ApiResponseError } from "@/common/api/axios";
import { useUi } from "../layout/AppProviders";
import { clearLogin, saveLogin } from "@/common/storage/login";

export default function LoginWorkspace() {
  const router = useRouter();
  const ui = useUi();
  const [userId, setUserId] = useState("");
  const [userPw, setUserPw] = useState("");

  useEffect(() => {
    clearLogin();
  }, []);

  const handleLogin = async () => {
    if (!userId.trim() || !userPw.trim()) {
      await ui.alert("아이디와 비밀번호를 입력해 주세요.");
      return;
    }

    try {
      await ui.withLoading(async () => {
        const response = await api.post("/login", {
          user_id: userId.trim(),
          user_pw: userPw,
        });

        const resultMap = response.data?.resultMap || {};
        saveLogin({
          accessToken: resultMap.accessToken,
          user_id: resultMap.user_id ?? userId.trim(),
          user_nm: resultMap.user_nm,
          adminYn: resultMap.adminYn,
          masterYn: resultMap.masterYn,
          comp_cd: resultMap.comp_cd,
          comp_nm: resultMap.comp_nm,
          envMysuitUrl: resultMap.envMysuitUrl,
          envMagellanVersion: resultMap.envMagellanVersion,
        });

        router.replace("/template");
      });
    } catch (error) {
      console.error(error);
      const message =
        error instanceof ApiResponseError
          ? error.message
          : "로그인 중 오류가 발생했습니다.";
      await ui.alert(message);
    }
  };

  return (
    <div className="login-page-3d">
      {/* 배경 파티클 */}
      <div className="login-bg">
        <div className="login-particle login-p1" />
        <div className="login-particle login-p2" />
        <div className="login-particle login-p3" />
        <div className="login-particle login-p4" />
        <div className="login-particle login-p5" />
        <div className="login-particle login-p6" />
      </div>

      {/* 왼쪽: 3D 문서 애니메이션 */}
      <div className="login-visual">
        <div className="login-3d-scene">
          {/* 떠있는 문서들 */}
          <div className="login-doc login-doc-1">
            <div className="login-doc-inner">
              <div className="login-doc-line login-doc-line-title" />
              <div className="login-doc-line" />
              <div className="login-doc-line" />
              <div className="login-doc-line login-doc-line-short" />
              <div className="login-doc-line" />
              <div className="login-doc-line" />
              <div className="login-doc-line login-doc-line-short" />
            </div>
            <div className="login-scan-beam" />
          </div>

          <div className="login-doc login-doc-2">
            <div className="login-doc-inner">
              <div className="login-doc-line login-doc-line-title" />
              <div className="login-doc-line" />
              <div className="login-doc-line login-doc-line-short" />
              <div className="login-doc-line" />
              <div className="login-doc-line" />
            </div>
          </div>

          <div className="login-doc login-doc-3">
            <div className="login-doc-inner">
              <div className="login-doc-line login-doc-line-title" />
              <div className="login-doc-line" />
              <div className="login-doc-line" />
              <div className="login-doc-line login-doc-line-short" />
            </div>
          </div>

          {/* OCR 텍스트 추출 이펙트 */}
          <div className="login-extracted">
            <span className="login-ext-item login-ext-1">Invoice #2024</span>
            <span className="login-ext-item login-ext-2">Total: 73,200</span>
            <span className="login-ext-item login-ext-3">Date: 2026-01</span>
            <span className="login-ext-item login-ext-4">Name: MySuit</span>
          </div>
        </div>

        <div className="login-visual-text">
          <h2 className="login-visual-title">MySuit OCR</h2>
        </div>
      </div>

      {/* 오른쪽: 로그인 폼 */}
      <div className="login-form-side">
        <div className="login-card-3d">
          <div className="login-logo">
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="7" y="4" width="18" height="24" rx="2" stroke="white" strokeWidth="2"/>
              <line x1="11" y1="11" x2="21" y2="11" stroke="white" strokeWidth="1.8" strokeLinecap="round"/>
              <line x1="11" y1="16" x2="21" y2="16" stroke="white" strokeWidth="1.8" strokeLinecap="round"/>
              <line x1="11" y1="21" x2="17" y2="21" stroke="white" strokeWidth="1.8" strokeLinecap="round"/>
              <circle cx="27" cy="27" r="5" fill="white" fillOpacity="0.25" stroke="white" strokeWidth="1.5"/>
              <path d="M25 27L26.5 28.5L29.5 25.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>

          <div className="login-title">
            MySuit <span>OCR</span>
          </div>

          <div className="login-form">
            <label className="login-label">
              <span className="login-label-text">아이디</span>
              <input
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void handleLogin(); }}
                className="login-input"
                placeholder="아이디를 입력하세요"
              />
            </label>

            <label className="login-label">
              <span className="login-label-text">비밀번호</span>
              <input
                type="password"
                value={userPw}
                onChange={(e) => setUserPw(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void handleLogin(); }}
                className="login-input"
                placeholder="비밀번호를 입력하세요"
              />
            </label>

            <button
              type="button"
              onClick={() => void handleLogin()}
              className="login-btn"
            >
              로그인
            </button>

            <div className="login-sub-btns">
              <button type="button" className="login-sub-btn">회원가입</button>
              <button type="button" className="login-sub-btn">비밀번호 찾기</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
