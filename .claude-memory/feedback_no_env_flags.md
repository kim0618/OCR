---
name: feedback_no_env_flags
description: 기능 롤아웃에 env 플래그 게이트 쓰지 말 것 — 매번 세팅이 귀찮음. doc-type 등 코드 게이트로 직접 켜라
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f9063492-4db1-4118-a63e-d01600f72018
---

새 기능/패치를 env 환경변수(예: `OCR_FORCE_WARP_ON_SKIP`, `OCR_INVOICE_ANCHOR_ORIENT`)로 게이트하지 말 것. 사용자가 매번 서버 기동 전 env 세팅하는 걸 귀찮아함("env 좀 쓰지마 귀찮게", 2026-06-12).

**Why:** 안전 롤아웃 목적의 env-gated(default off) 패턴은 매 실행마다 수동 세팅을 강제 → 사용자 워크플로우(서버 재기동만 하면 되는)를 망침.

**How to apply:** 무회귀가 이미 다른 수단으로 보장되면(예: documentType=="invoice_statement" 게이트 → 영수증 자동 제외, baseline 안 탐) env 없이 **그 코드 게이트만으로 바로 켜라**. 진짜 위험해서 분리 측정이 필요할 때만 예외적으로 플래그 고려하되, 기본은 env 금지. [[feedback_user_runs_not_me]] [[project_preprocess_image_deskew_gap]]
