---
name: feedback_local_cpu_vs_gpu_prod
description: "로컬=CPU(느림, 타임아웃은 로컬 아티팩트). 프로덕션=GPU. 전처리/OCR 비용·속도로 설계 결정하지 말 것 — 게이트는 정확도"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f9063492-4db1-4118-a63e-d01600f72018
---

OCR 추출 속도/타임아웃은 **로컬이 CPU라 느린 것**이고, 실제 배포는 **GPU 모드**(g4dn, [[project_aws_setup]])로 돈다. 사용자 지적(2026-06-12): "지금은 로컬에서 테스트하니까 이렇게 느린데 실제는 gpu모드로 진행".

**Why:** run013(anchor 4× OCR)·run014(detect_orientation 512px×4방향)에서 1-2/1-3 등 28행 무거운 장이 300s ReadTimeout으로 깨졌는데, 이를 근거로 "비용 과다=설계 접기"로 판단한 건 **로컬 CPU 아티팩트에 끌려간 잘못**. GPU에선 512px·4방향 채점도 비용 문제 아님.

**How to apply:** 전처리/OCR 패치의 **채택 게이트는 정확도**(방향 정답·셀↑·base 무회귀)지 로컬 latency가 아니다. 로컬 타임아웃은 *측정 iteration 속도* 문제일 뿐 → 측정은 가벼운 설정(작은 thumb, 단일행 변주만)으로 신호부터 보고, 무거운 설정(512 등)은 GPU 전제로 살려둔다. "로컬에서 느려서/타임아웃나서 안 된다"를 패치 기각 사유로 쓰지 말 것. 단, 로컬 측정 자체가 불가할 만큼 느리면 eval client 타임아웃 상향 또는 서브셋 측정으로 우회. [[feedback_user_runs_not_me]] [[project_preprocess_image_deskew_gap]]

**정정/보강 (2026-06-15, 모델 사실관계 확인 + 사용자 강한 지적):** CPU↔GPU 차이는 **속도 + 검출(server_det) + 약간의 인식**뿐, *근본 능력 차이 아님*. ⚠️ **파서 작업(읽힌 필드 위치추정·배정)은 순수 로직 = CPU에서 다 됨 → GPU로 미루지 말 것.** 내가 파서 작업까지 "GPU 몫"으로 자꾸 넘긴 게 잘못(사용자: "cpu에서 다 하고 가도 되는 작업인데 왜그래"). **모델 사실(실측):** 한국어 인식은 `korean_PP-OCRv5_mobile_rec` **하나뿐 — server 한국어 rec 없음**(server는 범용 다국어 `PP-OCRv5_server_rec`). 그래서 mobile은 CPU속도+**한국어 특화** 둘 다 이유였고 합리적. server 전환은 한글텍스트엔 트레이드(특화 잃음), 숫자/검출엔 도움 가능 → A/B 필요. **결론: "server 모델로 바꾸면 정확도 도약"은 한국어엔 거의 틀림.** AWS 셋업도 device=gpu만 바꾸고 모델은 mobile 그대로([[project_aws_setup]] 8단계). 즉 GPU의 실이득=속도(force_full_eval orientation 싸게) + server_det. 작은 글자 정확도는 모델 스위치 아니라 **파서(CPU)·사전마스터대조**로 [[project_free_vs_template_gaps]]. [[feedback_no_speculation_use_run_data]]
