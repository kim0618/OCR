---
name: feedback_latest_report_analyze_flow
description: "트리거 '최신 리포트 분석해' → 파서-drop 분류표 열고 부류·우선순위 분석 후 로컬 루프로 진행하는 표준 흐름"
metadata:
  node_type: memory
  type: feedback
  originSessionId: ff562f3b-642a-40c1-9294-7e904b016b26
---

사용자가 **"최신 리포트 분석해"**(또는 "리포트 봐줘"류)라고 하면, 거래명세서 파서 작업의 표준 분석·진행 흐름을 탄다.

**Why:** 파서-drop 회수 작업의 루프 인프라가 다 서 있고(아래), 매번 절차를 다시 설명할 필요 없이 트리거 하나로 바로 분석→우선순위→로컬 루프로 들어가게 하려고. 사용자가 이 흐름을 메모리에 박아달라 명시(2026-06-17).

**How to apply (순서):**
1. 메모리 먼저: [[project_ocr_snapshot_replay]](루프·명령·베이스라인), [[project_preprocess_complete_24base]], [[feedback_class_not_per_case]], [[feedback_systematic_report_analysis]], [[feedback_user_runs_not_me]].
2. 최신 run 폴더의 `PARSER_DROP_CLASSIFY.md`(+ `_replay_compare.md` 있으면 수정 후) 열기. 사용자가 run 폴더명 주면 그걸로, 안 주면 최신 자동.
3. [[feedback_systematic_report_analysis]] 프로토콜대로 **전수 분해**: parser_drop(OCR읽음·회수가능) vs recognition(OCR바운드) 갈래, drop/mislocate/wrongpick 패턴, free/fallback 경로, clean/변형 분리 — **건수로** 정리(1~2케이스 일반화 금지).
4. [[feedback_class_not_per_case]]대로 **부류·우선순위 표 + 추천** 제시(개별수정 아닌 보편 룰 가드). 첫 부류 사용자와 확정.
5. 실행은 사용자가([[feedback_user_runs_not_me]]). 나는 분석·룰보강 준비·복붙명령만. 로컬 루프 = 파서수정 → `eval/replay_compare.py` → `eval/parser_drop_classify.py --compare-dir replay_compare` → 부류 증감확인. 최종확정만 AWS.
