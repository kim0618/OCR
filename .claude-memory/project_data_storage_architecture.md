---
name: data-storage-architecture-current
description: 2026-05-21 현재 mysuit-ocr 데이터 저장 구조. 템플릿/이미지/history는 브라우저 클라이언트 스토리지. 향후 DB 마이그레이션 예정.
metadata: 
  node_type: memory
  type: project
  originSessionId: 3d564606-0439-4504-ac81-66a37391c611
---

mysuit-ocr 앱의 데이터 저장은 **현재 클라이언트 사이드 (브라우저)** 기반이다:

| 데이터 | 저장 위치 | 코드 위치 |
|---|---|---|
| 템플릿 메타 | `localStorage` (key: `LOCAL_TEMPLATES_KEY`) | `components/ocr/OcrAnnotator.tsx` |
| 템플릿 이미지 (base64) | `IndexedDB` | `lib/imageStore.ts` |
| OCR History | `localStorage` + `IndexedDB` | `lib/historyStore.ts`, `lib/imageStore.ts` |
| Ground Truth | `localStorage` | `lib/groundTruthStore.ts` |
| Restore Profile | `localStorage` | `lib/restoreProfileStore.ts` |
| **(AWS 서버 측)** OCR 모델 / review_log.jsonl | AWS EBS 디스크 | `ocr-server/data/` |

**Why:** 발표 데모 1차 단계까지는 백엔드 DB 없이 빠르게 iteration하기 위함. DB 도입은 발표 후 단계로 미룸.

**How to apply:**
- "AWS에 저장되는지" 같은 질문 받으면 → 템플릿/이미지/history는 **브라우저**, AWS는 OCR API 호출 처리 + 모델/로그만
- 브라우저 storage는 **origin (URL) 기준 분리**: `localhost:3000`, `localhost:8089`, `54.180.124.22:8089` 모두 다른 영역
- 백업/이전 필요 시 DevTools로 localStorage 값 export 또는 별도 export 기능 추가 필요
- 발표 시연 시: **시연 PC + 브라우저 + AWS URL** 조합 고정. 캐시 클리어 금지

**Future direction:** 발표 후 DB-backed storage로 마이그레이션 예정. 그때 진짜 멀티 디바이스/멀티 유저 지원 가능해짐.

[[aws-local-divergence-demo-prep]] [[ocr-servers]]
