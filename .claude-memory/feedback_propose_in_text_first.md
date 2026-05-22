---
name: feedback-propose-in-text-first
description: "UI/UX 변경 같이 주관적 선택이 필요한 작업은 AskUserQuestion 팝업 대신 텍스트로 제안만 먼저 하고, 사용자 OK를 받은 뒤 적용"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 723bad62-513e-404c-a537-21983165aa97
---

UI/UX 튜닝처럼 주관적 선택지가 있는 작업은 AskUserQuestion 멀티셀렉트 팝업으로 묻지 말고, 텍스트로 옵션을 정리해 제안만 먼저 한다. 사용자가 검토하고 OK 하면 그때 수정.

**Why:** 사용자는 d:/Free_Vue/OCR 작업 중 품목표 펼침 비율 튜닝 단계에서 AskUserQuestion으로 옵션 3개를 띄우자 "수정하지말고 어떻게 할지 제안만 해줘 먼저"라며 거절. 팝업보다 텍스트 제안을 선호.

**How to apply:**
- 다수 옵션이 있고 정답이 주관적인 UI 변경 → 텍스트로 옵션 정리 → 사용자 응답 대기 → 적용
- 명확한 한 가지 방향이 있을 때는 텍스트로 단일 제안하고 진행 의사만 묻기
- 이미 한 번 OK 받은 흐름 안에서 작은 결정(파일명, 변수명 등)은 그대로 진행 가능
- 코드 작업이 아닌 단순 정보성 분기점에서는 AskUserQuestion 사용 가능

관련: [[user-collaboration-style]]
