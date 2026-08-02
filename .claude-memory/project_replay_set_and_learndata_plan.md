---
name: project_replay_set_and_learndata_plan
description: "리플레이 기준셋(9,001 held-out) 선정 확정+완성 산출물 + learndata/룰/對Google 실행순서(Phase 0~7). 2026-07-21. 월쿼터 greedy(universe=itemCode). 측정 2벌: held-out 84,707=효과검증, full 93,708=對Google벤치. 2천→6천 후속 기준셋"
metadata: 
  node_type: memory
  type: project
  originSessionId: 83b6634a-70a6-4547-b194-f23bc3ea9884
  modified: 2026-07-22T05:27:54.097Z
---

2026-07-21. [[project_rekey_105k_batches]]의 10.5만장 파이프라인 후속 = **룰작업 새 기준셋(리플레이 셋)** 확정·완성 + learndata/벤치 실행순서. 2천장→6천장(둘 다 2606 단월) 다음 버전으로, 18개월 풀에서 새 품명 최대 수집이 목적.

## ★기준셋 선정 = 확정·완성 (로컬 산출물 4종 done)
- **방식 = 월쿼터 greedy set-cover, universe = itemCode**(raw품명 아님! — raw는 54.6%가 표기변형 singleton이라 부적합. 예전 "고유품목 32,581/5k=86%/8k=96%" 시뮬은 실은 **itemCode 기준**이었음을 실측 확인). 플레이스홀더 **`999999`(4,555문서=코드매칭실패) 제외**.
- **월쿼터 = 월별 문서수 비례 쿼터 안에서만 greedy** → 일반 greedy의 초기월(2501~2502 +834/+624장) 쏠림 제거. **fill 2단 구조 폐기**(원설계 "greedy 5k+fill 3~4k"보다 우수: 월편차 8.8%→0.01%).
- **크기 = 9,001 + 버퍼 299**(OCR실패 치환용, 겹침0). 시드42 고정.
- **검증수치**: itemCode 커버 **95.72%**·itemNameMaster 96.48%·raw품명 35.6% / 월분포 최대편차 **0.01%** / held-out 학습가능 **96.77%**(신규품목 miss 3.23%) / 랜덤9k 대비 코드 **+32pp**(랜덤 63%). 희귀편향=경미(셋 코드빈도 중앙 34 vs 전체풀 55, 레이아웃(행수10/9·필드채움97%)은 전체풀과 동일=룰신호 깨끗).
- ⚠️ 희귀 살짝 얹혀 **헤드라인 정확도를 과거 2천/6천과 1:1 비교금지**(어차피 단월↔18개월이라 이미 깨짐). 룰 before/after는 같은 셋 내라 OK.

## 완성 산출물 (전부 `ocr-server/eval/data/invoice_war/`, git=eval/data 통째 gitignore라 **scp 전송**)
- `images_replay/` = 9,001장 2.38GB (GT키 1:1 정확일치·에러0). ★**AWS 업로드=tar로**(9,001 개별 scp는 파일당오버헤드로 느림): 로컬 `tar -cf images_replay.tar images_replay`→scp→AWS `tar -xf`. GT(31.5M)는 그냥 scp. dest=`~/OCR/ocr-server/eval/data/invoice_war/`. build_manifest가 GT키↔중첩이미지 상대경로 페어링→active=이미지∧GT (contract invoice_replay 배선 검증됨). **AWS 라이브 eval은 P5용**(첫 baseline은 9,001이 대량 run에 이미 포함돼 재-OCR 불요).
- `ground_truth_replay.json` = 9,001문서 31.5MB
- `replay_set_v1.txt`(9,001)·`replay_set_buffer.txt`(299)·`replay_set_report.md`
- 스크립트 3종: `select_replay_set.py`(월쿼터greedy)·`filter_gt_replay.py`·`extract_replay_sources.py`(로컬 tar34개서 원본만 추출, **os.listdir로 대괄호경로 회피**·tar내부=`LIVE//processed//<월>//<docId>___<rest>`·forward매핑으로 key계산)
- `contract.py`에 **`invoice_replay` testset 등록**(gt=ground_truth_replay.json, dir=images_replay, thin/nested). 백업=`backup/contract_20260721_before_invoice_replay_testset.py`. contract.py만 git추적(eval/ 밖).

## ★★측정 2벌 구분 (핵심 — 헷갈리지 말 것)
learndata는 EXACT 룩업(`master_match.py`/`baseline_matrix.py`: ocr_item_nm=읽은품명, learn_count≥3 게이트) → 데이터 많을수록 커버↑.
- **측정1 = learndata 효과/일반화 (내부 게이트)**: learndata를 **9,001 제외한 84,707로 build**(held-out) → 9,001에 ON/OFF replay. 순환방지=자기답으로 자기채점 막음. "처음보는 송장에도 도움되나=파인튜닝 갈까" 판단용 정직수치.
- **측정2 = 對Google 벤치 (대외비교)**: **양쪽 full learndata**. war 99.4%가 full·순환이니 우리도 **전체 93,708(9,001 포함)로 build**해야 사과-대-사과(반쪽으로 우리수치 내면 불공정). = `baseline_matrix`(순환분리 item_match_type 병기). full끼리는 양쪽 다 순환(천장비교), 비순환 진짜실력은 측정1에서. **둘 다 필요·상호대체불가.**
- → **learndata는 2벌 build**: (A)84,707=측정, (B)93,708=배포/벤치.

## ★실행순서 Phase 0~7
- **P0** [AWS,진행중] 2차 run 완료 → runs/<ts1> 93,708 스냅샷+크롭.
- **P1** [사용자+로컬] 2차이미지삭제→images_replay+GT scp업로드·contract push / 로컬은 **9,001 스냅샷만** 반입(93k전체 아님). 첫baseline=큰run에 이미포함, 별도eval불요.
- **P2** ✅**완성(2026-07-22)** `learndata_build.py`(eval/, scp배포). 소스=**compare/([3/6]완성분) `table.rows[].cells.itemName.{gt,ext}`**(finetune_ledger 아님—그건 defect중심). ext=우리읽기→GT itemCode(compare gt명으로 GT행 조회), 9컬럼 tbl_ocr_learndata_invoice_modify형. GT 1회로드+compare per-doc 스트리밍(RAM안전). **2벌 생성완료**(AWS `data/invoice_war/`): **(A)learndata_heldout.json 138M = 84,671docs/596,098rows/고유249,286/≥3 33,176** (--exclude replay_set_v1.txt 9,001정확제외) · **(B)learndata_full.json 155M = 93,672docs/668,320rows/고유276,919/≥3 36,899**. war대비 고유읽기 3.7배(Paddle이 더 다양하게 읽음)→≥3게이트 통과는 36,899. 샘플페어 정상.
- **P3** [로컬] 측정1: 9,001에 (A) ON/OFF replay. 게이트=비순환 독립수치 상승? **★측정메커니즘 구축완료(2026-07-22)**: replay_compare가 itemCode 옆에 **3컬럼 나란히** 채점(OFF=②master `itemCode` ~70% · `itemCodeLearnA`=held-out A·비순환=측정1 · `itemCodeLearnB`=full B·순환상한). 구현=NEW `eval/learndata_apply.py`(learndata json→{읽기→코드} 룩업, learn_count≥3 게이트, 다중코드는 **majority 근사**(war는 SIMILARITY+가격 tiebreak, ~10%만 영향)). replay_compare가 A/B 룩업 자동로드(`data/invoice_war/learndata_{heldout,full}.json`)→ext·gt행에 주입→compare_table **동적채점**. `contract.MEASUREMENT_KEYS`=측정컬럼은 셀emit하되 **cellAccuracy/spurious/rowMatch·defect 집계 제외**(회귀추적 무오염, 모든 testset 안전). local_summary=라벨+itemCode계열 5행묶음, **flat 단일런도 LOCAL_SUMMARY 자동생성**(auto-hook+build flat지원). 단위검증 PASS(룩업 33,176=A≥3 일치·캐스케이드·cellAcc불변). 6파일(1신규5수정) 백업완료, **미커밋**. ★실행(사용자): `replay_compare.py --testset invoice_replay --ts 067_20260720_175949` → `parser_drop_classify.py --testset invoice_replay --ts 067_20260720_175949 --compare-dir replay_compare` → `runs/067_20260720_175949/LOCAL_SUMMARY_replay_compare.html` 열기. 067=flat(snapshots만, run_meta無)이라 **--ts 필수**(latest_run 못찾음).
- **P4** [로컬] 룰/파서 작업(9,001 스냅샷 replay 반복, 2천/6천 후속). 게이트=study회귀0·spurious0. P2~3과 병행가능.
- **P5** [사용자+AWS] 룰+(B)전체learndata 배포 → `run_all --testset invoice_replay` 1회 → 로컬replay 일치확인(062→065패턴). 사이클당1회.
- **P6** [AWS/로컬] 측정2: (B) 반영 Paddle로 `baseline_matrix` 對Google. 게이트=99.4% 대비 헤드룸 → 파인튜닝 필요성 판단.
- **P7** [AWS] 파인튜닝 — **현재 보류**(마지막카드), P6 결과 보고 결정. 크롭 corpus는 93k run이 이미 적립.

**~~미구축 = learndata_build.py~~ ✅완성(P2 done 2026-07-22).** **P1 데이터반입 ✅(2026-07-22)**: 9,001 스냅샷(AWS서 replay목록으로 tar→scp, `runs/20260720_175949/snapshots/` 로컬) + learndata A(138M)/B(155M) 로컬 `data/invoice_war/`. replay GT/목록/images_replay(9,001)/invoice_replay testset은 기존 로컬산출물. → 로컬 측정 kit 완비. 다음=**P3 측정1**(9,001에 A ON/OFF replay, 비순환 효과판정) — ★측정메커니즘(learndata A를 item매칭에 ON/OFF) 구축 필요(master_match.py는 learndata 미사용, baseline_matrix식 캐스케이드 이식). 실행은 사용자몫(scp/git/AWS). ★2차 분석 [4/6]metrics서 16GB RAM+디스크(499M) thrash로 SSH먹통→재부팅복구(스냅샷93,708·compare 안전, 지표/2차크롭 미완=크롭은 FT전 서버끄고 재생성). [[project_rekey_105k_batches]] [[project_rekey_105k_batches]] [[project_baseline_matrix_stages]] [[project_master_match_baseline]] [[feedback_git_as_transport]] [[project_eval_runs_untracked_scp]]
