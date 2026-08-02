---
name: project_learn_loop_audit
description: "학습루프 전수 감사 결과(W1~13/C1~6) + 심각도 정정 + \"스케일 전 체크리스트\". 리포트는 repo docs/에 있음"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2760a9ad-7e14-435b-b20f-db7b97d95547
---

2026-06-16 학습루프(eval) 전수 감사. 리포트 = repo **`OCR/docs/`**:
- `LEARNING_ROUTE_SYSTEM_INSPECTION_BRIEF_20260616.md` (검증판 브리프, 실제 구조+W1~6)
- `LEARNING_ROUTE_SYSTEM_REPORT_20260616.md` (Codex W1~12)
- `LEARNING_LOOP_AUDIT_REPORT_20260616.md` (첫 측정감사)

**핵심 — 실측으로 심각도 정정됨(코드만 보고 Critical로 비약했다가 run034 데이터로 하향):**
- **필드 측정 = 견고**(cross-foot 7불변식). **표/셀 측정 = 약함**: W1=셀 메트릭이 통째누락행을 분모서 제외(`compare_table.py:127`+`metrics.py:110`) → **단 run034 실측 영향 3pp뿐**(인플레 아직 미발현, macro는 정직). server_det가 행 더 찾으면/스케일서 커짐.
- **게이트 갭**: phase4는 *필드만* cross-foot, phase3는 셀 *내부정합*만 봄(행커버리지 불변식 없음 → W1을 못 잡음). phase2는 빈 추출(`documentFields:{}`) 통과 + run_meta 자기보고 재집계 안 함(C2).
- **trend**: 회귀판정이 base+변주 섞인 micro라 base 회귀 은폐 가능(C3). macro/coverage/spurious 미적재(W2). 기준선 취약(C6).
- **W4**: OCR민감 상수(정렬0.30·버킷0.7/0.3·"24장 캘리브") → server_det서 측정 드리프트. [[project_gpu_transition_state]] 035 하락의 1번 용의자.
- **W13**: normalize digits-only → 소수·2자리연 false-mismatch(잠복, 현 정수GT엔 미발현).
- **GT**: 1.jpg 공급/세액·6.pdf bizno 빈칸(시각 미검증). 단 GPU-vs-CPU 델타엔 상쇄.
- **thin(C1)**: mock+6일stale+parity게이트 없음 → 점수 신뢰불가. **단 의도된 placeholder**(실데이터 오면 교체, [[project_learn_loop_infra_plan]] Phase7). 지금 손대지 말 것.

**판정: 이건 다 "스케일(수천장) 전 체크리스트"지 GPU 블로커 아님.** GPU 프로브는 study-live를 *내가 수동분석*하므로 자동화/트렌드 약점이 안 물림. 그래서 GPU 전 수정 0으로 결론(세 번 over-engineering했다가 정정).

**파서 상태(run034 전수분해):** base 6레이아웃 = **plateau**. recognition 193(OCR=GPU), cell-absent 117(OCR), 오배정 4(전부 변주=deskew). CPU 파서 후보 = 3.pdf bizno 1건(경계선, OCR노이즈라 server_det가 풀 수도). 지배적 잔여=OCR바운드+deskew → GPU/전처리 몫. [[feedback_class_not_per_case]] [[project_preprocess_image_deskew_gap]]
