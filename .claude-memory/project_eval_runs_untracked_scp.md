---
name: project_eval_runs_untracked_scp
description: "eval/runs/ 는 git 추적 안 함(2026-07-20 결정) — 재생성 산출물, 필요할 때만 scp. 10만장 대비"
metadata: 
  node_type: memory
  type: project
  originSessionId: d7a1049b-4a93-4349-97d5-be3be7d00faf
---

2026-07-20 결정(사용자): **`ocr-server/eval/runs/` 는 git 추적하지 않는다.** `.gitignore`에 blanket `ocr-server/eval/runs/` 추가 + `git rm -r --cached ocr-server/eval/runs/`(91,349 파일)로 추적 해제. 파일은 디스크 유지, 추적만 끊음.

**Why:** run 하나가 git에 수만 파일(6천장=31,626 파일, thin/ per-image 5×N). **10만장이면 run당 ~50만 파일 + `*_replay_compare.json` 단일 81MB→~1.4GB**로 git 100MB 한도 초과. runs/ 전체가 재생성 가능한 산출물이라 git에 태울 이유 없음.

**How to apply:**
- runs/ 산출물(snapshots·compare·replay_compare·samples·processed·SUMMARY 등)은 **scp on-demand**. 로컬 replay/분석에 필요한 run만 골라 받는다: `scp -i 키.pem -r ubuntu@3.37.51.240:~/OCR/ocr-server/eval/runs/<batch>/thin/snapshots ./`. 로컬 replay 필수입력=snapshots/ 뿐([[project_ocr_snapshot_replay]]).
- 영속 이력은 **`eval/RUN_HISTORY.jsonl`(eval/ 바로 아래, runs/ 밖)** 에만 git으로 남는다. 트렌드/계보는 이 파일 기반.
- 역할 분리: 코드·RUN_HISTORY·요약스크립트=git / runs 산출물=scp / 이미지·GT·모델가중치=scp·zip([[feedback_git_as_transport]]).

**배경 사고(AWS pull 충돌):** 이 결정 직전 AWS pull이 막혔던 원인 = AWS에 커밋 안 한 로컬 변경(runs/ 옛 산출물 6,879 삭제 + 중복 .gitignore 수정)이 원격 .gitignore 변경과 겹침. runs/ untrack 커밋을 로컬서 push → AWS는 `git stash -u && git pull && git stash drop` 으로 해소(그 정리들이 untrack으로 대체돼 무의미해짐). [[project_gpu_transition_state]]
