---
name: planning-style
description: "큰 작업 전 게이트 달린 단계별 플랜을 함께 잠그고 시작하는 것을 선호. 측정 우선, 가설/확정 구분"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f976f5f5-7cb0-4892-9e4b-40453e4c9d76
---

본격 구현 전에 **단계별 로드맵을 문서로 함께 다듬어 잠근 뒤** 실행하는 것을 선호. 각 단계에 명시적 go/no-go 게이트(가능하면 숫자 기준)와 작업명을 붙이는 방식을 좋아함.

**Why:** 2026-05-29 거래명세서 완전 비정형 로드맵 수립 시, 내가 준 개념적 순서를 본인이 0~6단계 + 게이트 + 산출물 구조(script/summary JSON/report/checker)까지 구체화한 정식 문서로 발전시킴. 여러 턴에 걸쳐 "어때?"로 플랜을 반복 검토하며 합의를 만든 뒤 실행하는 패턴.

**검증된 선호:**
- 측정 우선 ("학습할지 말지"를 감이 아니라 baseline 측정·버킷 분류로 판정)
- 7장 같은 소표본 결과는 "가설"로 다루고 대규모 데이터 holdout으로 재확인 (확정과 명확히 구분)
- 반복 평가는 재실행 가능한 하니스(script + summary + report + checker)로

**How to apply:** 비슷한 큰 작업은 바로 코드부터 짜지 말고, 단계·게이트·산출물 구조를 먼저 제안해 합의를 만든 뒤 실행. 소표본 결과로 큰 결정(아키텍처 등)을 확정하지 말 것. 관련: [[invoice-unstructured-roadmap]].
