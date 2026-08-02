---
name: feedback_user_runs_not_me
description: 실행(서버 기동·eval run·스크립트 돌리기)은 사용자가 직접 한다. 나는 준비만 하고 명령만 넘김
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f649e999-a806-4625-8cd2-8df7f15844df
---

서버 기동, eval `run_all`/`run_batch`, 학습 루프, **로컬 측정/채점/분석 스크립트까지 — 무언가를 '돌리는' 것은 전부 사용자가 직접 한다.** 나는 코드/manifest/GT 페어링/스크립트 등 준비까지만 하고, 돌릴 **명령만 넘긴다**. 임의로 Bash/백그라운드로 스크립트를 실행하지 말 것. (예외: 파일 탐색·grep·구조 확인용 읽기전용 조회는 내가 해도 됨. 하지만 "측정/채점/평가 스크립트를 돌려 수치를 낸다"는 사용자 몫.)

**Why:** 2026-07-06 재확인 — 품명클린 로컬 스코어러(`score_clean_local.py`)를 내가 백그라운드로 돌리자 "로컬측정은 내가 하잖아"라고 정정. DB든 로컬이든 **run은 사용자**. 실행 타이밍·환경을 본인이 통제하려 함.

**How to apply:** 준비 끝나면 복붙 가능한 정확한 명령(cwd, .venv 경로 포함)을 제시하고 멈춤. 결과는 사용자가 돌린 뒤 붙여주면 그때 분석. 판단 기준: "이게 수치/산출물을 만드는 실행인가?" → 그렇다면 넘긴다. [[feedback_server_startup]] [[feedback_server_restart]] 의 ".venv 자동 사용·pip 제안 금지"와 함께 적용.
