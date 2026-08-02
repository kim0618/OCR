---
name: project-rekey-105k-batches
description: "리키잉 10.5만장 파이프라인 (2026-07-20) — g6전환·검증완료(L4 Paddle OK), 1차(28,005) 실행중(run-rekey.sh). ★2차 즉시실행 절차 기록됨(1차ts에 --resume 이어붙여 같은폴더). '2차 시작하자' 하면 그 절차대로 바로"
metadata: 
  node_type: memory
  type: project
  originSessionId: 994242e9-0f87-472b-abad-4f409a76545f
  modified: 2026-07-22T02:01:10.809Z
---

리키잉 교정송장 원본 = **93,723 unique** (매니페스트 105,714줄 − 중복 11,991). copy_result.csv **missing 0 = 원본 실존 100%**.

## ★2026-07-20 대량 prep 파이프라인 완성 (로컬 검증)
- **tar 로컬 도착**: `C:\Users\jinsung\Desktop\[신규] 프리세일즈\1_OCR\1_학습이미지\10만장` = **69 tar, 26.6GB, 월별(2501~2606), 93,723 all present**. (경로 대괄호 → glob/PowerShell 주의)
- **★매니페스트 = PDF+JPG 혼합** (전엔 전부 PDF로 오해): **2501~2507=PDF 34,005**(`<docId>___<ts>_<hash>.pdf`), **2505~2606=JPG 59,718**(`<docId>___<ts>_<seq>.jpg`, 이미 분리이미지).
- **GT 키 = war separate_img_path** (per-page 분리이미지 `<월>/<docId>/<파일>`). PDF는 렌더 필요, JPG는 `___`→`/` 재배치만.
- **prep_rekey_images.py** (eval/data/invoice_war/, 신규·검증): PDF→page-1 렌더(GT총페이지 기준 이름), JPG→복사. **page 1만**(사용자 확정: 멀티페이지도 1p). GT기반이라 GT없는 문서 자동 스킵. 실측: 2501 PDF 2519렌더 + 2606 JPG 복사, 에러0.
- **18개월 GT**: `build_all_gt.sh`(신규, build_gt.sql을 2501~2606 반복+월접두어 병합) → **ground_truth_all.json 571,687문서**. build_gt.sql에 **bigint 오버플로 가드**(OCR오독 28자리 금액 → supplyAmount만 NULL, 월전체 죽던 것 수정, 백업함).
- **filter_gt_rekey.py**(신규): GT_all → rekey 대상만 → **ground_truth_rekey.json 307MB 93,708문서** (매칭 99.98%). **AWS 업로드 완료** (`~/OCR/ocr-server/eval/data/invoice_war/`, 검증됨).
- **워커 3**: start-backend.sh `--workers 2→3` (L4 24GB 근거, T4폴백시 2로 되돌림 주석). git push 대기.
- **make_rekey_tars.ps1**: 자체 dedup 추가(HashSet, 매니페스트 안 건드려도 tar 고유만).

## 접속·인프라
- **키: `C:\Users\jinsung\Desktop\[신규] 프리세일즈\1_OCR\1_키페어\mysuit-ocr.pem`**. SSH `ubuntu@3.37.51.240` 작동 확인. AWS 디스크 **48G 여유**(96G중 49G사용) → 27GB tar+변환이미지 빠듯, 반씩+원본삭제 필요.
- 6월 셋 그대로: `eval/data/invoice_war/images/`(6002장), ground_truth_2606.json(60MB).

## 설계 확정 (스냅샷 나온 뒤 만들 것)
- **learndata**: war = `tbl_ocr_learndata_invoice_modify`(214,891행, 9컬럼: ocr_item_nm/user_item_cd/user_item_st/user_item_order_amt/brch_cd/invoice_seq/item_seq/reg_date). master_dict.learndata(75,332)는 이걸 GROUP BY한 룩업. **우리 것 = 우리Paddle읽기→GT코드** 리키잉(war키=구글이라 못물려받음). learndata_build.py = finetune_ledger 정렬 재사용, 같은 9컬럼 출력 → DB이식은 동일테이블 COPY. [[project_master_match_baseline]]
- **리플레이 셋**: ★★**2026-07-21 확정·완성 → 별도 메모리 [[project_replay_set_and_learndata_plan]]로 이관.** 요지: 원설계(greedy5k+fill3~4k, 품명기준)를 **월쿼터 greedy·universe=itemCode(999999제외)·9,001+버퍼299**로 개선(월편차0.01%·코드커버95.7%). 산출물 4종 로컬완성(images_replay 2.4GB·GT·목록·contract testset). learndata **2벌**(84,707측정용/93,708배포·對Google용) + 실행순서 Phase0~7 그 메모리에.

## ★배치 파일 분할 확정 (tar 34개, 로컬 `...\10만장\`)
- **1차 = 2501~2506 (17 tar, 14.0GB)**: 2501_p1·p2, 2502_p1~p3, 2503_p1~p3, 2504_p1~p3, 2505_p1~p3, 2506_p1~p3. (glob `250[1-6]_p*.tar`)
- **2차 = 2507~2606 (17 tar, 12.6GB)**: 2507_p1~p3, 2508_p1, 2509_p1, 2510_p1, 2511_p1, 2512_p1, 2601_p1, 2602_p1, 2603_p1·p2, 2604_p1·p2, 2605_p1·p2, 2606_p1.
- 균형분할 근거: 2025 상반기가 무거워 6개월 vs 12개월. 1차에 PDF(2501~04)+JPG(2505~06) 둘 다 포함 = 스모크서 렌더·복사 양경로 검증됨.

## ★1차(2501~2506) 진행완료 (2026-07-20)
scp 업로드(14GB 4.5분, 55MB/s) → AWS `~/rekey_tars/` → 풀기(28,017파일) → tar삭제 → **prep_rekey_images.py 변환(serial ~50분, PDF렌더 26,713+JPG복사 1,292)** → **이미지 28,005장, GT매칭 100.00%(28,005/28,005), 에러0** 검증완료. images_rekey/<월>/<docId>/파일 (~11GB). 원본 rekey_raw 15GB는 삭제대기(로컬 tar 백업 있어 안전). AWS 디스크 22G여유. **prep 병렬판(mp.Pool 4코어+idempotent skip)은 로컬만 수정·미배포**(serial로 완주해서 안 씀, 2차 때 배포하면 ~13분). 다음=rekey_raw삭제→g6전환→git pull→스모크.

## ★g6 전환+1차 실행 (2026-07-20, 진행상태)
- **g6.xlarge 전환·검증 완료**: NVIDIA L4 23GB, 드라이버 595.71.05, `paddle.utils.run_check()` PASS(sm 8.9). 데이터 EBS유지(stop/start 안전). EIP 3.37.51.240 고정. **가장 큰 불확실성(L4-Paddle호환) 해소.**
- **서버 워커3**: tmux `backend` 세션 start-backend.sh. 재시작=`fuser -k 9099/tcp; sleep3; tmux kill-session -t backend; tmux new-session -d -s backend "bash ~/OCR/start-backend.sh"`. (`pgrep uvicorn` 카운트 1로 보이는 건 fork워커 undercount—정상. fuser로 보면 마스터+워커3 PID 확인됨.)
- **코드 배포됨**: contract.py(invoice_rekey testset: gt=ground_truth_rekey.json, dir=images_rekey/, images_nested)+start-backend.sh(워커3)은 origin에 이미 있음(git pull "up to date"). prep_rekey_images.py는 scp배포. **git commit/push=사용자몫**.
- **1차 검증**: build_manifest active **28,005** / gt_orphan 65,703(=2차, 이미지無). 스모크: **GPU 95%(GPU바운드→g6.xlarge 정답, 2xlarge 불필요)**, ~0.8장/s, path free89/fallback241(정상혼합), 고해상0(변환JPG<2MB 전부병렬).
- **1차 실행커맨드**: `bash ~/OCR/run-rekey.sh` (=`run_all.py --testset invoice_rekey`, tmux eval_rekey). ~10~11h. 로그 `~/OCR/logs/eval_rekey.log`. ★`run-eval.sh(--all)` 쓰지말것(6월study/thin까지 다 돌음).

## ★2차 진행상태 (2026-07-21)
- **1차 완료**: run `20260720_175949`, 28,005장 OCR+분석+checker PASS(MVP GO), 필드59.5%·셀45.3%. 스냅샷28,005·크롭누적660k.
- **2차 Step2~6 완료(내가 함)**: 1차이미지삭제→2차업로드(17tar)→풀기(65,706)→tar삭제→변환**65,703장(에러0)**→원본삭제. active=65,703 확인. 디스크19G.
- **`run-rekey-2.sh` 생성됨**(AWS ~/OCR/): `run_batch --resume 20260720_175949` + `run_all --reuse 20260720_175949` (venv활성화 포함). **Step7=사용자가 tmux서 `bash ~/OCR/run-rekey-2.sh` 실행**. ETA ~23h. 완료시 runs/20260720_175949에 1+2차 93,708 통합.

## ★★2차 즉시실행 절차 (참고 — 이미 실행됨, 재실행/디버그용)
**목표: 2차를 1차 run폴더 `<ts1>`에 `--resume`으로 이어붙여** 스냅샷·결과·크롭 전부 한곳 → learndata/리플레이 원스톱.
접속: PEM=`C:\Users\jinsung\Desktop\[신규] 프리세일즈\1_OCR\1_키페어\mysuit-ocr.pem`, `ssh ubuntu@3.37.51.240`. venv=`~/OCR/ocr-server/.venv/bin/python`. 로컬 2차 tar=`...\10만장\`의 **2507_p1·p2·p3, 2508_p1, 2509_p1, 2510_p1, 2511_p1, 2512_p1, 2601_p1, 2602_p1, 2603_p1·p2, 2604_p1·p2, 2605_p1·p2, 2606_p1** (17개 12.6GB. glob 안됨→명시나열).
1. **1차완료확인+`<ts1>`파악**: **★1차 run = `20260720_175949`** (2026-07-20 17:59 시작, ~10h). 확인=`ls -dt ~/OCR/ocr-server/eval/runs/*/ | head -1`.
2. **1차 이미지삭제**: `rm -rf ~/OCR/ocr-server/eval/data/invoice_war/images_rekey/*` (결과는 runs/<ts1>+finetune_corpus에 이미 있음).
3. **2차 업로드**: `ssh 'mkdir -p ~/rekey_tars'`; 로컬 `...\10만장\`서 `for f in 2507_p*.tar 2508_p1.tar 2509_p1.tar 2510_p1.tar 2511_p1.tar 2512_p1.tar 2601_p1.tar 2602_p1.tar 2603_p*.tar 2604_p*.tar 2605_p*.tar 2606_p1.tar; do scp -i "$PEM" "$f" ubuntu@3.37.51.240:~/rekey_tars/; done`.
4. **풀기+tar삭제**: ssh `mkdir -p ~/rekey_raw; cd ~/rekey_tars; for f in *.tar; do tar -xf "$f" -C ~/rekey_raw; done; rm -rf ~/rekey_tars`.
5. **★변환**(2차는 JPG많아 빠름): `cd ~/OCR/ocr-server/eval/data/invoice_war; nohup <venv> prep_rekey_images.py --in ~/rekey_raw/LIVE/processed --out $PWD/images_rekey --gt ground_truth_rekey.json >~/prep2.log 2>&1 &`. 모니터=`find images_rekey -name '*.jpg'|wc -l`(65,703 목표). (prep 병렬판 mp.Pool은 로컬만—원하면 scp배포).
6. **rekey_raw 삭제**.
7. **★2차 OCR resume(tmux)**: `tmux new -s eval_rekey2`; `cd ~/OCR/ocr-server; <venv> eval/run_batch.py --resume <ts1> --testset invoice_rekey --workers 3` → **<ts1>에 2차 append**(1차 done이라 skip). ~23h(65,703장).
8. **★통합 분석**: `<venv> eval/run_all.py --reuse <ts1> --testset invoice_rekey` → 1+2차 크롭 등 전량 분석.
9. **2차 images_rekey 삭제**.
→ 결과: `runs/<ts1>`에 1+2차 **93,708 스냅샷/결과**, finetune_corpus에 전량 크롭. **learndata/리플레이=여기 한곳에서**.
**함정**: prep 인라인python 따옴표깨짐→파일/heredoc / pkill·pgrep self-match(명령어에 패턴문자열 포함)→`fuser -k 9099/tcp`·`[u]vicorn`trick·`'run_''batch.py'`concat / Python(win로컬)은 `/c/`경로 못읽음→`C:/`.

## ★2차 완료·분석 thrash (2026-07-22)
- **2차 OCR 완료**: 93,708/93,708, **에러 0**(2차 summary ok65703/free15532/fallback50171). 스냅샷 93,708 = runs/20260720_175949, **EBS라 안전**.
- **★통합분석([4/6]metrics 즈음) → 16GB RAM thrash(swap death)로 SSH먹통**. 원인=서버(Paddle워커3) RAM + 분석이 93k+GT 메모리로드 합쳐 16GB초과. 인스턴스는 살아있음(포트22 열림)·데이터 안전 → **콘솔 재부팅으로 복구**.
- **결정**: **지표는 스킵**(P1~6에 불필요, 측정은 별도 replay/baseline_matrix). **2차 크롭(FT용)은 "파인튜닝 직전(P7 전)"에 생성** — 재부팅후 **서버 끄고**(분석 --reuse라 서버불요, RAM확보) `run_all --reuse 20260720_175949 --testset invoice_rekey` 재실행, 또 터지면 **g6.2xlarge(32GB)로 잠깐**. 1차 크롭은 이미 코퍼스에 있음, 2차만 미완.
- **지금 순서**: 재부팅→스냅샷 무사확인→ **P1(replay 반입)+P2(learndata_build.py)부터** [[project_replay_set_and_learndata_plan]]. 크롭은 FT 갈 때.

## 산출 (1+2차 통합 뒤)
코퍼스크롭(finetune_corpus 단일누적, **2차분 미완=FT전 생성**) + 스냅샷(runs/<ts1>→리플레이셋 greedy 9,001) + ~~지표(스킵)~~ + **learndata(learndata_build.py 미구축, <ts1> 스냅샷서 별도 추출, 9컬럼 tbl_ocr_learndata_invoice_modify형)**.

[[project_war_labor_measurement]] [[project_invoice_war_db_restored]] [[project_finetune_pipeline_runnable]] [[feedback_git_as_transport]]
