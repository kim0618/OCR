---
name: project_cpu_phase_exhausted
description: "프로브셋 CPU(파서) 최적화 종료 게이트 도달 — sweep1이 마지막 클린회수, 잔여 전부 OCR/워프=GPU"
metadata: 
  node_type: memory
  type: project
  originSessionId: c5a03213-4e0e-40c0-add3-ebc64dddd396
---

**판정 (2026-06-15, run 031 전수분해): "GPU 전 CPU 최대화" 전략의 종료 게이트 도달.** sweep 1(대표/상호 블록분리 [[project_invoice_repblock_company_split]])이 마지막 클린 CPU 회수였고, 남은 손실은 데이터상 전부 OCR 또는 워프 바운드 = GPU 몫.

**전략 렌즈:** CPU 회수 가능분 = "클린 입력(PDF·free)에서 값은 OCR에 읽혔는데 파서가 오배정한 손실"만. byPath free필드79% vs fallback56% 격차의 분절분.

**증거 (run 031, ~355 결함):** recognition(OCR글자) 195 / variant structure(각도 워프붕괴) 134 / clean structure(클린 파서) 26. 클린입력 결함의 82%가 recognition.
- **주소(P3-c) 소진:** 4.pdf 주소는 supplier꼬리+buyer에 붙은 공급자머리를 **완벽 재라우팅·접합해도 GT와 sim=0.72=mismatch**(영동포≠영등포·8KV1≠SKV1·호누락+양party 글자혼입). 라우팅은 미끼, OCR 바운드. 주소 30건중 27건=워프MISSING10+OCR9+garbled. CPU가능 후보는 7.pdf 절단 1건뿐인데 raw OCR 미저장(sample=documentFields만)이라 파서/OCR 미검증.
- **셀(표) 소진:** 클린 base **1.jpg lotNo 25/28·spec 27/28 정상**(cellAcc0.90)=파서 컬럼매핑 OK. lotNo/spec structure클러스터(22)는 **변형본 전용**(1-1 lotNo20/28, 컬럼 left-shift) = 기하왜곡. 우측컬럼(유효기간·수량)은 변형본도 정상 → 컬럼경계 검출이 왜곡에 무너지는 것 = 전처리.
- clean structure 26 = 19가 1.x변형(이미 78~90%)+PDF 7, 체계적 클린 파서버그 없음.

**run 032 (2026-06-16) 후속 클린회수 1건:** base(정상촬영 6장) structure는 10건(메모리 본문 "26"은 1.x변형 포함 다른 분모). 그중 1.jpg(free) r13 컬럼-누수만 핀포인트 수정 — `invoice_statement_free._parse_table_row_candidate`에서 date-shaped quantity→expiryDate 재배정이 `len(numeric_values)==3` 가드로 막혀 lot번호가 토큰4개로 늘면 스킵됐던 것 + `_money_parse_value('110,450')`가 콤마지운 6자리를 날짜오인→None 함정. 가드 일반화(엄격 YYMMDD)+`_money_for_sum` 교체로 해결. **셀 762→763, 24장중 1.jpg만 변동 회귀0.** r14(itemName 과포획)는 lot탐지 확대 회귀위험이라 미수정→GPU후 재판단. 이게 마지막 클린 CPU 회수 확정.

**결론:** 더 밀면 변형/OCR 잡음을 룰로 덮는 오버핏. **GPU 어젠다 = ①orientation 무조건4방향+512(로컬은 28행 300s타임아웃이라 막힘, variant structure134 핵심) ②perspective 워프강화(MISSING10·셀0% 회복) ③고해상512 OCR(weak-signal변형+recognition일부).** 한국어 server rec 모델 없음. [[project_preprocess_image_deskew_gap]] [[feedback_local_cpu_vs_gpu_prod]] [[project_eval_loop_strategy]] [[feedback_analysis_prioritize]]
