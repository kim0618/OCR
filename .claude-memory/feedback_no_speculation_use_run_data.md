---
name: feedback_no_speculation_use_run_data
description: "추측·하향결론(floor/GPU미루기/\"여기서 멈춤\") 금지. 실제 run 리포트 데이터로만 분석. 사용자가 run 돌리면 그 리포트로 진행"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f9063492-4db1-4118-a63e-d01600f72018
---

추측하지 말고 **실제 run 리포트 데이터**로 분석할 것. 사용자가 run을 돌리면 그 리포트를 분석해 다음을 진행한다(실제 학습 루프처럼). 2026-06-15 사용자가 반복 지적: "너가 너무 추측만해 실제 한게 있는데 왜 계속 넘어가자고 하느냐."

**Why:** 내가 "OCR floor / GPU 몫 / 최적이라 멈추자"로 성급히 결론낸 게 데이터로 확인하니 **반복적으로 틀렸음**. 검증된 반례: 3.pdf buyer 사업자번호 `113-85-04425`가 950px OCR에 **이미 읽혀 있는데** 추출은 빈값 = **OCR floor 아니라 파서가 떨어뜨린 것**. 템플릿(같은 mobile 모델)은 다 읽음 → 모델 한계 아님. 즉 "인식 안 됨"의 상당수는 **읽혔는데 파서가 위치추정·배정 실패**(완전비정형의 본질 과제, CPU에서 고침).

**How to apply:**
- "floor·룰불가·GPU 몫·여기서 멈추자"를 **데이터 확인 없이 결론짓지 말 것.** 기본 가정 = "읽혔는데 파서가 못 가져온 것일 가능성, CPU에서 고칠 수 있음".
- 실패 필드는 먼저 **GT 값이 OCR 원문에 있는지**(읽힘=파서 / 없음=인식) 갈라서 판단.
- 파서 작업을 GPU로 미루지 말 것 — 순수 로직이라 CPU/GPU 동일. [[feedback_local_cpu_vs_gpu_prod]] [[project_free_vs_template_gaps]] [[feedback_analysis_prioritize]]
