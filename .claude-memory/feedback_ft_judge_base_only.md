---
name: feedback_ft_judge_base_only
description: "현 FT 라운드 판정 기준 = base→새FT 순증(품명+ AND 숫자+)뿐. V1은 안 본다(base 재시작이라 무관). 옛 'vs V1' 원칙 끌고 오지 말 것"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: fc011ac1-27b3-4315-ba60-b1d15adad845
  modified: 2026-07-27T04:35:21.089Z
---

2026-07-27. base 재시작 품명+숫자 FT 라운드의 판정 기준은 **base 대비 새 FT가 품명·숫자 둘 다 순증하는가, 그것뿐**이다. **V1(itemname_V1)은 이제 참조 대상이 아니다.**

**Why:** base에서 새로 시작(--from-adopted 없이)했으므로 V1은 이 트리와 무관한 다른 가지다. 나(Claude)가 [[project_finetune_fields_round]]의 옛 "판정은 항상 vs V1" 원칙을 반복해서 끌고 와 사용자가 **3회** 정정("V1 볼 필요 없다"). 3자비교(base/V1/후보) 제안도 거부됨.

**How to apply:** FT 벤치 판정·리포트는 **base vs 새 FT 2열**만. V1 export·V1 채점·3자표 만들지 말 것. "품명 V1 이상 유지" 같은 게이트 문구 쓰지 말 것 — 게이트는 "base 대비 품명+ AND 숫자+". [[project_ft_seen_unseen_bench]]
