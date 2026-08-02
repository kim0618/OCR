---
name: project_finetune_tree_rounds
description: FT 트리 라운드별 결과(1차 기각→2차 품명 itemname_V1 채택→3차 combined 실행중) + 콤마붕괴 근본해결(라벨 재구성) + 기준셋 학습오염 차단 + 운영 노하우
metadata: 
  node_type: memory
  type: project
  originSessionId: d7a1049b-4a93-4349-97d5-be3be7d00faf
  modified: 2026-07-24T06:39:33.657Z
---

2026-07-24 기준. FT 트리 = official → ✗1차 → ★itemname_V1(2차) → (3차 combined 실행중).

## 라운드 결과 (held-out 크롭 exact, 게이트=finetune_report_by_type.py)
- **✗1차 전필드**(92만, 숫자58%, run 260722_2109): net −3,524 기각. 한글 +6.4 / 숫자 −9.1(콤마붕괴).
- **★2차 품명/한글**(66만, buyer제외·숫자앵커 13%, run 260724_0415): **품명 +11.3%p(3.8→15.1)**·한글기타 +3.7·순증 +2,835, 숫자 **−18.8**(앵커 13% 너무 작아 forgetting — 앵커는 적어도 안 되고 라벨 깨진 채 많아도 안 됨). → **itemname_V1 채택**(첫 트리 줄기). 컬럼 선택 근거=다양성 실측: itemName 고유 94k(3.3배 반복)·supplier ~1.1k는 넣고, **buyerCompany 고유 11/buyerAddress 14(16.6만 크롭=25문자열 반복=암기·빈도편향)는 제외**. itemNameMaster 제외=rewrite.
- **068 live eval**(9,001, 품명v1, run 068_20260724_104317): **품명 raw 43.0→50.6(+7.6 제품실증)**, master 73.0→71.4(−1.6, 분석대상), cell 51.1→**39.4**(숫자붕괴 확인), field 55.2. 로컬 반입됨(runs/068_..., processed 1.7G 제외 — 재크롭용 processed는 AWS 유지, [[project_finetune_processed_backup]]).
- **3차 combined**(2026-07-24 14:4x 시작, ~15.3h, ETA 익일 06시+자동중지): 품명v1 이어받아(`--from-adopted`) **품명+숫자 통합 target**. 구성 한글 400k(33%)/숫자 798k(67%), train 96만, epochs 4. 게이트=**품명 유지(+11 근방) AND 숫자 회복(70→88 근방)**. 통과 시 combined_V1 채택(부모=itemname_V1).

## ★콤마붕괴 근본원인 확정 + 해결 (매번 숫자 FT 실패의 정체)
- 원인: **숫자 GT=콤마없는 DB값(819800) vs 크롭 인쇄형(819,800)** → 학습이 '콤마 떼기'를 배움. −18.8/−9.1의 대부분=포맷(자릿수는 맞음: 26,641,755→26,641.755). 실측: 숫자 failure 라벨 콤마보존율 **0%**(4자리+ 71,965 무콤마), garbage(음수·수억) 다수.
- 해결: build_dataset **`--reconstruct-number-labels`** = 금액계열(amount/unitPrice/quantity/supply/tax/total/discount)만 콤마포맷 재구성+garbage(음수·12자리+) 제외. **itemCode(38만)·사업자번호·제조번호·lotNo는 GT가 이미 인쇄형**(평문/하이픈)이라 그대로 포함. 날짜·buyer번호 제외(형식 불확실=콤마↔마침표 혼동 위험).
- 사용자 통찰(순차의 함정): 1차 품명이 숫자에 판 −18.8 구덩이를 순차 숫자라운드가 메워야(문턱 18) → **combined(둘 다 target=구덩이 없음)로 회피**. "콤마로 잃은 18은 콤마 고치면 돌아온다=최소 official 본전" 논리.

## ★기준셋(9,001) 학습오염 차단 (2026-07-24 구축)
- 문제: replay eval이 크롭 자동수확(이번 failure 16만+balance 27.6만=**전부 기준셋**) → 학습하면 측정이 '본 문제로 시험'. 또한 **리키잉 수확에 기준셋 이미 포함**(9,001⊂93,708)이라 품명v1도 약간 오염된 채 측정됨(이미지의 ~9.6%, 068 수치 약간 인플레 가능).
- 차단: build_dataset **`--exclude-sources`**(failure=ledger src / balance=meta src; src없는 meta행=기준셋 배치로 간주 제외). run-finetune.sh가 images_replay 트리에서 목록 자동생성(`replay_sources.txt`, 전 라운드 공통). finetune_crops_balance meta에 `src` 기록 추가(신규 수확부터 완전 추적).
- 잔재(정직): 리키잉-구세대 balance 속 기준셋 크롭은 meta 없어 식별불가(경미한 오염).

## 운영 노하우 (오늘 확립)
- run-finetune.sh 라운드: 기본=hangul / `--round=numeric` / **`--round=combined`(권장)**. FT_CRITERIA가 RUN_HISTORY '학습 기준'에 자동 기록.
- **FT 전 백엔드 내리기**(GPU 13GB 회수, OOM 방지): `fuser -k 9099/tcp; tmux kill-session -t backend`.
- ★스크립트는 **`bash ~/OCR/run-*.sh`** — pull이 실행권한 지움. `bash` 없이 `...sh; sudo shutdown` 치면 Permission denied 후 **shutdown만 즉발**(실제 사고 2026-07-24, 서버 즉시 꺼짐).
- epochs 상한 논리: best_accuracy 자동저장이라 상한=시간만 결정(품질 무관). 정점(ep2~3)+여유1=4. 마지막 ep까지 오르면 다음에 올릴 것.
- run 이름: 단일 `--testset` run은 접두 없음(NNN_은 --all 배치 카운터) → 수동 리네임 규약(067, 068_20260724_104317). run_meta 기반 탐색이라 리네임 안전.
- run-eval.sh = **invoice_replay(9,001) 전용**으로 변경(thin 은퇴, 필요시 study 한 줄 추가).
- RUN_HISTORY: eval/RUN_HISTORY.jsonl(runs/ 밖, git 추적) — **AWS에서 자동기록**(단일 testset 경로 훅 수정으로), 로컬은 git/scp로 동기화(장부는 run 폴더에 안 들어있음). AWS 요금 자동기록: `~/.bashrc`에 AWS_EC2_HOURLY_USD=1.0(가정치, 실요율로 조정) 설정됨. backfill: 리키잉 eval 28h46m $28.77, FT 1차 $11.85/2차 $10.70.
- 채택/롤백: finetune_adopt.py --version <태그> → versions/<태그>/ 영구 스냅샷+adopted/ 활성(main.py 로드). 롤백=adopted 삭제(→official) 또는 versions/ 복사.

[[project_invoice_item_table_p1_gate]] [[project_rekey_105k_batches]] [[project_replay_set_and_learndata_plan]] [[project_eval_runs_untracked_scp]] [[project_finetune_processed_backup]]
