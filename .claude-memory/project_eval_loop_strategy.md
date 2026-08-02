---
name: project_eval_loop_strategy
description: 평가루프 운용 전략 — 6장으로 일반화 룰 개선→기준셋 lock→수천장으로 일반화 검증
metadata: 
  node_type: memory
  type: project
  originSessionId: b49ee55a-fb22-48a0-addb-dedb932d0471
---

사용자 확정 전략 (2026-06-10): **6장 = 일반화 룰을 최대한 짜서 기준셋 만들기, 수천장 = 그 일반화가 실제로 먹히는지 검증.**

순서:
1. 6장 루프로 룰 보강 — 단 6장 외우기(오버핏) 금지, **일반화되는 룰만**
2. 개선된 상태 = study(회귀 기준점) lock
3. 실데이터 수천장 → 같은 추출기 룰 타므로 개선 자동 이월 → "더 좋아지는지" 측정

**핵심 제약 (매 룰 선택 시 명시할 것):** 6장으로는 "일반화됐다"를 증명 못 함 = 가설 생성 단계일 뿐. 일반/오버핏 판정 기준은 **점수가 아니라 룰의 성격** — 구조·패턴 의존(✅ "주소칸에 대표자패턴 오면 재배정") vs 특정값 외우기(❌ "5.pdf의 '김동연,정유석' 제거"). 6장 점수 상승은 필요조건이지 증명 아님. 진짜 일반화 채점은 수천장에서.

수천장에서 전부 좋아지진 않음이 정상: 일부는 개선 이월, 일부는 6장에 없던 새 패턴으로 안 좋아짐(=다음 루프 일감). compare.html이 매 사이클 개선/신규회귀 추적. [[feedback_eval_loop_probe_not_perfect]] [[feedback_analysis_prioritize]] [[project_learn_loop_infra_plan]] 참조.
