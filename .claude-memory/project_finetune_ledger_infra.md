---
name: project_finetune_ledger_infra
description: 파인튜닝 코퍼스/표정렬진단 인프라 — 파일·위치·동작·AWS 배포 대기
metadata: 
  node_type: memory
  type: project
  originSessionId: 4a11fae8-19da-49c1-b4cb-c487fcd6330c
---

2026-06-22 구축. 파인튜닝 원석 적립 + 표측정 W1 진단. 모두 `ocr-server/eval/`, checker 산출물 무수정 read-only 사이드카.

**파일 (5개, 로컬만 — AWS 배포 대기)**:
- `finetune_ledger.py` (신규): parser_drop_classify 분류 재사용→OCR-bound 결함(recognition/ambiguous_fuzzy)만 골라 GT정답+가장맞는 OCR box(text·score·bbox=크롭타깃) 적립. `cropReady`(신뢰localize) / `lowConf`(box有 ratio<0.55) / `noBox`(못localize) 3분류. box는 항상 보존(정보손실 방지), cropReady만 게이트. 숫자형은 containment 일치만 cropReady(자릿수겹침 오귀속 방지).
- `finetune_crops.py` (신규, Phase A): cropReady bbox로 **실제 크롭 이미지를 잘라** `finetune_corpus/crops/<hash>.jpg` + `labels.txt`(crop\t정답)로 적립. PaddleOCR rec가 먹는 학습데이터. dedup=ledger와 동일키 hash. PAD=2px.
- `run_batch.py` (수정·백업함): 응답의 `processed_image`를 `runs/<ts>/processed/<src>.jpg`로 저장(snapshot 저장하듯, rec.json 스키마 무손상).
- `table_align_diag.py` (신규): compare_table 정렬기 재사용→W1(audit A3) 정량화. 행정렬 실패 explosion을 "더나은 ext 페어링 존재"로 판별→정렬노이즈 vs 진짜셀오류 분리.
- `run_all.py` (수정): checker 다음 `[analysis]` = ledger→crops→table-align (live만). best-effort(게이트 불변).

**적립처(★단일, run 밖)**: `ocr-server/eval/finetune_corpus/`. `ledger.jsonl`(메타, dedup키=src+location+gt+bbox, seenCount++) + `crops/<hash>.jpg`(이미지) + `labels.txt`(학습 라벨). 원자적 쓰기. **compare(실제 OCR run)만 누적, replay 제외**. fine-tune은 여기만 읽음.

**크롭 픽셀화 해결(2026-06-22, 사용자 지적으로 수정)**: 처음 ledger-only로 보류했으나, 추적해보니 **서버 응답에 `processed_image`(=main.py `ocr_img`, OCR이 먹은 바로 그 이미지, 회전/deskew/unwarp 분기마다 재동기화)가 이미 실려옴**(main.py:3525). 즉 **로컬 재현(fragile, 전처리가 OCR과 얽힘)도 main.py 수정도 불필요** — run_batch가 그걸 저장→finetune_crops가 bbox로 자름. bbox좌표=processed_image좌표라 정확. [[feedback_no_offline_rederive_use_response]]

**검증**: 심층재검증 구멍4개 수정+단위7 PASS(ledger) / 크롭 dedup·labels원자성·슬라이스+OOB클램프 3 PASS(crops). 서버/eval run 아닌 함수로직만.

**Phase B/C 추가(2026-06-22 동일세션, "만들수있는건 다 만들자")**:
- `finetune_crops_balance.py` (Phase B): MATCH 셀/필드(GT검증된 정답)만 크롭→`crops_correct/`+`labels_correct.txt`. forgetting 방지 균형풀. 이미지당 cap(기본30). cut_crops 재사용.
- `build_dataset.py` (Phase C, 검증됨): labels.txt+labels_correct.txt 합쳐 비율(--balance-ratio)+train/val/test 분할→`dataset/{train,val,test}.txt`+manifest. 순수 파일연산(GPU불요), 결정론(seed). PaddleOCR data_dir=finetune_corpus.
- `finetune/config_rec_finetune.yml` (템플릿, 미검증 스캐폴드): PP-OCR rec fine-tune config 자리표시. Architecture/Transforms는 서빙 모델 official config서 복사해야(버전특정).
- `finetune/RECIPE.md`: train/eval(도메인+baseline forgetting 2게이트)/export/deploy 명령 문서. **깜깜이 자동래퍼 대신 문서**(PaddleOCR 학습플래그 버전특정+미검증이라). train 래퍼는 AWS 스모크 성공 후.
- run_crops 검증: dataset 비율·분할·결정론 + balance match-only/localize 단위 PASS.
**Phase D(진짜 학습)만 미구축**: 수천장+GT+AWS 학습스택 게이트.

**배포 대기(eval-side, main.py 아님)**: 자동경로(run-eval.sh→run_all --all)= run_batch·finetune_ledger·finetune_crops·finetune_crops_balance·table_align_diag·run_all. 수동(Phase C/D)= build_dataset·config·RECIPE. 첫 live run 자동산출: processed/ + ledger.jsonl + crops/ + crops_correct/ + labels(_correct).txt. import의존 parser_drop_classify·cv2. [[project_finetune_strategy_and_corpus]] [[project_gpu_transition_state]] [[feedback_no_offline_rederive_use_response]]
