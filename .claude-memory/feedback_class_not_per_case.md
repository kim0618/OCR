---
name: feedback_class_not_per_case
description: 개별 garbage를 하나하나 고치지 말 것. 스케일·학습 관점에서 부류로 나누고 측정 먼저
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 55827c6c-9c6d-4bb5-ad73-163dc51285dd
---

2026-06-16, spurious garbage(세액=`합`, buyerRep=`총수량`) 발견 시 내가 한 칸씩 고치려 들자 사용자: **"이걸 하나하나 고치라는게 아니라 앞으로 학습 돌리면 이런게 많을텐데 어떻게 할거냐"**.

**Why:** 수천장·거래처별 레이아웃 변형에서 이 부류는 롱테일. 개별 룰=오버핏 두더지잡기. 학습 단계로 가려면 부류의 크기를 측정해 타깃화해야 함.

**How to apply:**
1. 오류를 **부류로 분해**: `rule`=보편 타입 불변식 위반(money=숫자, 이름≠라벨 — 가드 하나로 전체 사망) · `learn`=타입 맞지만 엉뚱한 칸 매핑(거래처 변형 → 학습 몫) · `GPU`=변주(각도/워프).
2. **측정 먼저**: 손대기 전에 그 부류를 평가루프가 숫자로 잡게(예: [[project_eval_spurious_metric]]). 안 보이면 못 고치고, 고쳤는지도 검증 못 함.
3. 개별 케이스는 부류 판정의 *예시*로만 쓰고, 룰은 보편 가드만. 매핑·OCR 잔여는 학습/GPU 대기열로.

[[feedback_analysis_prioritize]] [[feedback_eval_loop_probe_not_perfect]] [[project_cpu_phase_exhausted]] [[feedback_no_speculation_use_run_data]]
