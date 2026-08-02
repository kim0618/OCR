---
name: project_eval_replay_testset_workflow
description: "룰작업/측정 새 기준셋 = invoice_replay testset(9,001 held-out). 왜 thin 아닌지 + 앞으로 로컬 replay 실행법(--testset invoice_replay, run_meta+snapshots만 가져오면 --ts 없이 최신 자동)"
metadata: 
  node_type: memory
  type: project
  originSessionId: a262fce8-4a79-4402-aeb4-5536e7b712d5
  modified: 2026-07-22T05:48:30.443Z
---

룰작업/측정 **새 기준셋 = `invoice_replay` testset**(9,001 held-out). 실행 = `--testset invoice_replay` (2천/6천 후속). [[project_replay_set_and_learndata_plan]]

## 왜 thin 아니고 새 testset 이름?
testset = **데이터 + 정답지(GT) + 이미지** 한 세트를 가리키는 이름.
- **2천→6천**: 둘 다 **같은 6월(2606) GT**에서 **샘플 개수만**(sample_6000.txt) 늘린 거라 계속 `invoice_thin` 하나였음.
- **9,001**: **18개월 풀(2501~2606)서 새로 뽑은 데이터 + 새 GT(`ground_truth_replay.json`) + 새 이미지(`images_replay`)** → 6월 GT로는 채점 불가 → **별도 testset 필수**. 프로필은 `thin/nested`(채점방식 동일, 데이터만 새 거). 2026-07-21 사용자가 contract에 등록. **내가 지금 바꾼 게 아님.**

## 6월 study/thin은 안 버림 = 회귀 감시용
checker 기준선·잠긴 baseline·RUN_HISTORY가 걔들에 묶여 있음(9,001로 덮으면 그 이력 깨짐). → 룰작업시 **둘 다** 돌림: `invoice_replay`(새 기준=실력·learndata컬럼) + `study/thin`(회귀0·spurious0 확인, 6월 데이터).

## 앞으로 로컬 replay 실행법 (반복 패턴)
1. AWS `run_all --testset invoice_replay` → 런폴더에 **run_meta.json 자동생성**(testset 태그 + ran 목록).
2. 가져올 때 **`snapshots/` + `run_meta.json` 을 런폴더째로 scp** (compare/ 불요=replay가 새로 만듦, `images_replay`·`ground_truth_replay.json`은 로컬에 이미 있음).
3. 로컬: `replay_compare.py --testset invoice_replay` → `parser_drop_classify.py --testset invoice_replay --compare-dir replay_compare`. `latest_run`이 run_meta.testset로 **최신 invoice_replay 런 자동선택** → **`--ts` 불필요**. 결과 `runs/<ts>/LOCAL_SUMMARY_replay_compare.html`.

★**067은 예외**: 스냅샷만 딸랑 가져와 run_meta가 없어서 `latest_run`이 못찾음 → `--ts 067_20260720_175949` 필요했음. **로컬에서 run_meta.json 하나 만들어 넣어 해결**(이후 067도 이름으로 찾힘). 다음부턴 run_meta만 같이 가져오면 이 예외 없음. [[project_ocr_snapshot_replay]] [[project_eval_runs_untracked_scp]]
