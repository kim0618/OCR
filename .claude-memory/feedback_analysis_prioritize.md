---
name: feedback_analysis_prioritize
description: 분석 요청 시 선택지 떠넘기지 말고 중요도순 우선순위로 정리해 추천까지 줄 것
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b49ee55a-fb22-48a0-addb-dedb932d0471
---

사용자가 "분석해봐 / 어떤 룰 보강해야 하는지 봐"라고 하면, AskUserQuestion으로 "어느 걸 할까요?" 되묻지 말 것. 내가 데이터를 직접 읽고 **중요도순으로 정리 + 추천**까지 해서 줘야 함. 사용자는 그 정리된 우선순위를 보고 결정함.

**Why:** 사용자는 나를 분석가로 씀. 우선순위 산정(빈도·고칠수있나·일반화·회귀위험)은 내 일이지 사용자에게 떠넘길 일이 아님. 선택지만 나열하면 분석을 안 한 것.

**How to apply:** 결함 데이터를 까서 ① 원시 건수의 함정 제거(예: 품명 11건 중 9건은 OCR 모델 오류라 룰 대상 아님), ② "룰로 고칠 수 있는 것"만 추려, ③ 빈도×고칠수있나×일반화×회귀위험으로 표 만들어 순위, ④ 1순위 추천 + 이유. 그 다음 "이걸로 갈까요?"로 confirm만. [[feedback_eval_loop_probe_not_perfect]] [[feedback_planning_style]] 참조.
