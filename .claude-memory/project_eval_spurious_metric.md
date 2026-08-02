---
name: project_eval_spurious_metric
description: 평가루프에 spurious(지어내기) 측정 추가 — GT 빈칸에 추출이 값 채운 false positive. recall 사각지대 닫음. 2바퀴 자기교정 루프 입증
metadata: 
  node_type: memory
  type: project
  originSessionId: 55827c6c-9c6d-4bb5-ad73-163dc51285dd
---

**배경 (2026-06-16):** 사용자가 1.jpg UI에서 세액=`합`(라벨 글자), buyerRep=`총수량` 같은 garbage 지적. 원인: **eval이 GT 빈칸(gt_empty)을 채점 제외**해서, "비워야 할 칸에 값 지어내기"(false positive)를 정확도(recall)가 통째로 못 봄. GT는 사용자가 완벽히 채웠음(빈칸=정답) — 문제는 지표가 빈칸 비교를 버린 것.

**추가한 것 — spurious 지표 (eval 4파일, recall·게이트·TREND 불변):**
- `compare_fields.py`/`compare_table.py`: `spurious = gt_empty and not ext_empty` **가산 플래그**(status는 gt_empty 그대로 → recall 0줄 변경, 트렌드 연속성 구조적 보장). `_spurious_tag()`: amount/bizno/date 타입 불변식 위반=`rule`, 그 외=`learn`.
- `metrics.py`: `_new_counts`에 spurious, overall에 `spurious{field,cell:{count,gtEmpty,rate}}`. rate=spurious/gt_empty.
- `report.py`: md+html "지어내기" 섹션(건수·율·이미지·필드·추출값·rule/learn 태그). `run_all.py`: SUMMARY 한 줄.
- **checker 특정키만 검사**(`scored==m+mm+miss`)라 키 추가 안전. phase3/4 PASS 확인.

**rule vs learn 분류 = 우리 루프의 수정목록.** rule=보편 타입가드로 즉시(money=숫자/이름≠라벨) · learn=엉뚱한 칸 매핑(학습 몫) · 변주(각도) 셀=GPU.

**2바퀴 자기교정 루프 입증 (run032→034, study 24장):**
- run032: 필드 spurious **8** 첫 측정(taxAmount`합`×4 + buyerRep`총수량`×3 + `삼호명`×1). 이전엔 0으로 안 보이던 것.
- 가드 2개 추가 후 예측 8→1.
- run033: 실측 **8→5** ❗. 리포트가 money가드 위치오류 드러냄 — money 가드를 free **reference 백필**에만 둠 → free가 `합`을 직접 채우면 "free 승리 스킵"으로 가드 미실행. (party-name 가드는 **합류점**이라 작동).
- 재수정: `sanitize_document_scalar_fields`(money 비숫자 + party-name 라벨)를 **main.py 3111행 free/fallback 합류점**(경로무관)으로 통합. `_PARTY_NAME_REJECT_LABELS` 블록셋.
- run034: **5→1** ✅ 예측 일치. recall 0.6311/0.7429 전회차 불변, 체커 PASS.

**교훈:** 추출 후처리 가드는 **free/fallback 합류점**에 둬야 경로무관. free merge 백필은 "free 승리" 때문에 free 직접출력 garbage를 못 잡음.

**잔존(룰로 안 밀 것):** buyerRep`삼호명`1(=`상호명` OCR오독, 정확블록셋 밖 → OCR/learn) · 셀 spurious 8(전부 변주 spec/lot = **GPU** warp). 측정은 되니 GPU 전후 비교 지표로 살아있음. [[project_cpu_phase_exhausted]] [[project_learn_loop_infra_plan]] [[feedback_no_speculation_use_run_data]]
