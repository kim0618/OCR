---
name: project-invoice-066-master-reprioritization
description: "066 raw×master 교차 실측으로 품명 작업 우선순위 재편 — drop이 1순위, 전문/일반 후처리는 master 순증 ≈0"
metadata: 
  node_type: memory
  type: project
  originSessionId: 942254f1-b38d-41b7-82b8-7fda691d5935
---

2026-07-13 확정 (066 thin 5,964장 전수 실측, 전 수치 재현 검증됨).

**raw×master 행단위 교차표(live compare)**: raw오답 23,779 중 14,160(59.5%)은 master가 이미 흡수. raw정답→master오답(오교정) 945 = 이론상 +2.53pp 방어 레버. raw정답→master전환율 92.7%(12,586/13,581).

**파서결함 10,809 중 master에 실제 남은 것 = 4,252뿐**:
- drop 1,953 → master 회수 0 (구조적: 행이 없으면 master 셀도 없음) → **1순위**
- wrongpick 7,229 → 5,473은 master가 이미 정답, 잔존 1,756
- mislocate 1,627 → 잔존 543
- 잔존의 73.9%(3,143)가 fallback 경로 (fallback: drop1,563/wrongpick1,173/mislocate407)

**oracle 상한**: 26,746+4,252=30,998/37,346=83.0% (전환율 92.7% 반영 시 ~82.2%) → learndata/FT 없이 구글 81.2% 초과 가능. "파서 소진" 주장 반박됨.

**전문/일반 strip 289건: master는 284건 이미 정답 → master 순증 ≤5건(+0.013pp)**. raw 전용 smoke일 뿐 성능 레버 아님.

**확정 실행 순서**: 평가복구(replay 범위=run_meta.ran 고정—49장 gt_orphan 혼입 수정, parser_drop_classify.py:50 CLEAN 하드코딩 6파일=구 study 전용이라 066 clean/angle 통계 무효) → master 순증 게이트 고정(raw+master+오교정945+숫자열 회귀0) → fallback drop 복구 → fallback wrongpick 열경계 → free release-gate는 A/B 먼저(oracle 측정 후 순이득 실패사유만 완화, 063 '78% 탈락' 진단은 066에서 미검증) → mislocate → 945 오교정 방어(jamo V5 배포·검증 후) → 재OCR/FT(cropReady 12,400은 파서개선 후 재산출 필요) → learndata 최종.

**공식 기준 = repo 문서 `OCR/docs/HANDOFF_066_MASTER_REPRIORITIZATION_20260713.md`** (게이트 체크리스트·재현 방법 포함, 이 메모리보다 우선). 역할: 구현=외부 분석 도구, Claude Code=독립 회귀 리뷰(git diff 기준)+FT 운영 모니터링.

관련: [[project_invoice_item_table_p1_gate]] [[project_invoice_rule_work_priorities]] [[project_preprocess_scale_revisit_6k]] [[project_finetune_pipeline_runnable]]
