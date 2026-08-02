---
name: no-model-discussion
description: "사용자가 모델을 직접 묻거나 별도 모델이 필요한 작업이 아닐 땐 모델 관련 얘기(OCR fine-tune, KIE, LayoutLM, Donut, ML 모델 등) 꺼내지 말 것"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a4b4b780-944f-41cb-b604-d4267537eb61
---

OCR 프로젝트는 **룰 보강만** 진행. 모델 학습/도입은 범위 밖.

**Why:** 사용자 명시 (2026-06-08). OCR fine-tune, KIE 모델, ML 모델 도입 등은 현재 프로젝트 방향이 아님. 룰 기반 평가 루프 + 사람이 룰 추가하는 방식만 채택. 모델 얘기를 자꾸 꺼내면 의사결정이 흐트러지고 본질에서 멀어짐.

**How to apply:**
- OCR/학습/개선 방향 질문에 답할 때 **룰 보강 단일 방향**으로 답할 것
- "OCR fine-tune", "KIE 모델", "LayoutLM/Donut 같은 모델", "ML 학습" 등 모델 기반 옵션은 **언급 금지**
- 룰만으로 한계 도달이라고 판단해도 모델 옵션을 제안하지 말 것 — 사용자가 묻기 전엔
- 예외: 사용자가 명시적으로 "모델은 어때?", "ML 가면?", "fine-tune 가능?" 같이 모델을 직접 물어보면 그때만 설명
- 예외: 사용자가 작업 방향을 새로 정의하면서 모델을 옵션으로 포함시키면 그 범위 안에서 답변

관련: [[invoice-unstructured-roadmap]] 의 학습 1차 타깃 B(KIE), A(OCR fine-tune) 정의는 메모리 기록이지만 사용자에게 먼저 제안하는 옵션은 아님.
