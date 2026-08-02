---
name: feedback_git_as_transport
description: "로컬↔AWS 데이터·리포트 이동은 git이 기본 파이프 — scp 일회성이나 \"그냥 놔두라\" 제안 금지"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d7a1049b-4a93-4349-97d5-be3be7d00faf
  modified: 2026-07-28T00:12:33.506Z
---

2026-07-08, 파인튜닝 리포트/corpus 이동 논의에서. 사용자가 scp 일회성 전송을 거부: "어차피 로컬이랑 aws랑 계속 git으로 왔다갔다할건데 지금 당장만 보는게 아니잖니". 그 전에도 corpus가 git status에 계속 뜨는 걸 "놔두라"고 반복 제안했다가 "말을 못알아쳐먹네" 강한 질책.

**Why:** 사용자 워크플로 = git이 로컬↔AWS 유일한 동기화 파이프. 일회성 우회(scp)나 방치는 다음 왕복에서 또 마찰을 만들 뿐. 반복 사용될 산출물(리포트·corpus·ledger)은 git 흐름에 태워야 함.

**★2026-07-27 재발·강화 (사용자 3회 충돌 겪음): "aws에서 수정하지말고 로컬에서 수정하고 내가 git으로 올릴거야 계속 aws에 직접 수정하니까 충돌나잖아".**
- **코드 수정은 무조건 로컬에서만.** AWS로 scp 하지 말 것 — scp한 파일이 워킹트리 수정으로 남아 사용자가 push→AWS pull 할 때마다 "local changes would be overwritten" 충돌(이 세션에서 3번). 내가 "즉시 반영용"이라며 scp한 게 원인.
- **AWS = 순수 소비자**: `git pull` 로만 코드를 받고, 워킹트리는 항상 clean 유지. AWS에서 하는 건 실행(학습/채점)과 read-only 확인뿐.
- AWS에서 `git commit`·`git checkout --`·`git rm --cached` 등 상태 변경도 하지 말 것(사용자 몫). 필요하면 명령만 전달.

**How to apply:**
- ⚠️ **git 실행은 사용자 몫 — 내가 `git commit`/`push` 직접 치지 말 것**(2026-07-14 질책: "왜 너가 계속 커밋을 하는거야? git은 내가 관리하는건데"). 나는 파일 변경만 준비하고 커밋 명령/구성은 제안으로만 넘긴다. "커밋할까요?"에 대한 애매한 답("main.py 빼")을 커밋 승인으로 넘겨짚지 말 것. 임의 커밋했으면 `git reset --soft`로 되돌려 파일보존한 채 결정권을 돌려줄 것. [[feedback_user_runs_not_me]]
- 산출물 이동 요청 시 기본 답 = git add/commit/push+pull 명령 세트(사용자가 실행). scp는 사용자가 명시할 때만.
- 추적분만 옮길 땐 `git add -u`(untracked 대형 폴더 안전). 모델 가중치(output*/)만은 예외로 git 금지 유지.
- git status 노이즈 문제는 "놔두라"가 아니라 근본 해결(untrack+gitignore를 그 자리에서 끝까지)로.
- [[feedback_workspace_hygiene]] [[project_finetune_pipeline_runnable]]
