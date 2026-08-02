---
name: project_preprocess_complete_24base
description: 24장 베이스 전처리 완료 선언(2026-06-17) + 검증근거(셀손실 98%=파서). 전처리 더 할지 물으면 이거. 다음=파서
metadata: 
  node_type: memory
  type: project
  originSessionId: ff562f3b-642a-40c1-9294-7e904b016b26
---

**2026-06-17: invoice_study 24장 베이스 기준 전처리(preprocessing) 능동작업 종료.** GPU 레버 전수 테스트 후 확정.

**전수 검증(예측 아닌 직접 대조, run 050):** 전 그룹 표 숫자셀 **460개 중 452개(98%)가 정답값이 OCR 출력에 이미 존재** → 파서가 misplace한 것(전처리/인식 완료). OCR에 아예 없는(인식바운드) 건 **8개(2%)뿐**, 전부 1-series dense 28행의 초소형 글자. 4-series 숫자도 12/12 OCR에 존재(아까 garbled로 본 건 상단 한글라벨이지 표 숫자 아님). **즉 입력은 깨끗, 남은 셀손실은 98% 파서.**

**KEEP(검증된 win/안전, runtime_config 플래그):**
- `IMAGE_BBOX_DESKEW_REOCR`(P3', bbox각도 deskew+재OCR, 진짜기운것만)
- `ORIENT_KOREAN_REVERIFY`(P1, 한글다움<0.10 garbage시 4방향 재OCR)
- `DOC_UNWARPING_GATED`(조건부 UVDoc, dual-pass 신뢰도게이트—휜것만 펴고 평평=원본유지)
- 베이스(mobile_det/950/960, DEVICE만 gpu)

**死(롤백, 재시도 금지):** server_det / 글로벌 고해상(1400·2000, dense표 파괴 두 det 다 확정) / brute 4방향+512(큰표 오회전) / 투영 deskew(dense표 가짜각) / textline orientation(정상줄 오판 1.jpg 90→34) / 전역 UVDoc(clean파괴 5.pdf 97→0).

**누적: 038(59.8/73.3) → 050(64.3/74.7), 회귀0.** (필드 064.3은 047의 65.6보다 약간 낮음=UVDoc 4-1 필드 trade-off, 셀은 047 74.5→050 74.7.)

**남은 셀손실 귀속:** 파서 98%(다중경로 legacy_text_items 컬럼배정, 컬럼밀림15·structure는 OCR깨끗한데 칸 misplace) + 인식 2%(dense 초소형=OCR모델/스케일). 전처리 버킷 '컬럼밀림15'=실제 파서, '전처리4'=하드열화2(4-2/4-3, 레버 다 시도 무효)+미세2(3-3/6-1, OCR깨끗 휴리스틱오표기).

**"봉인" 아니라 "대기":** 지금 능동 전처리=0(24장 오버핏 경계). **스케일서 재방문 조건** = ①임계값(deskew3°·UVDoc마진+0.01·orient0.10) 실데이터 분포서 오발동 ②24장에 없던 조건(그림자·저DPI·구김·극단각) 군집 ③일반화 검증 실패. evidence 기반만, 선제 금지.

**다음 = 파서**(회수가능 셀손실 98%가 거기). 컬럼밀림15+3-3/6-1 흡수. 단 다중경로(legacy/header/structured) 통합 foundation이라 24장 하드코딩=오버핏 → 레이아웃 분포(실데이터) 보고 설계. 인식바운드 2%+4-series 한글라벨=OCR모델 파인튠(학습루프, 스케일). [[project_gpu_transition_state]] [[project_cpu_phase_exhausted]] [[feedback_eval_loop_probe_not_perfect]] [[project_learn_loop_infra_plan]]
