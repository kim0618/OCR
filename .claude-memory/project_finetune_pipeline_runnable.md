---
name: project_finetune_pipeline_runnable
description: "인식 파인튜닝이 \"뼈대만\"에서 실제 가동 가능으로 전환됨. 스택=PP-OCRv5/PaddleX, 원커맨드 러너+비교 리포트까지 구축"
metadata: 
  node_type: memory
  type: project
  originSessionId: d7a1049b-4a93-4349-97d5-be3be7d00faf
---

2026-07-07. 인식 파인튜닝이 [[project_finetune_ledger_infra]]의 "뼈대만, 실행 X"에서 **실제 가동 가능**으로 전환됨.

**핵심 사실(스택 확정)**: 서버가 서빙하는 rec 모델 = `korean_PP-OCRv5_mobile_rec` (main.py:1135), 스택 = PaddleOCR 3.4.1 / PaddleX 3.4.3. 기존 `config_rec_finetune.yml`(v4 tools/train.py + 수기 Architecture)은 **폐기** — 이 스택엔 안 맞음. PaddleX는 아키텍처를 `Global.model`에서 자동 해석.

**데이터 게이트 통과**: build_dataset의 "failure 141"은 **낡은 manifest**였을 뿐(선별 필터 없음, labels.txt 전체 사용). 재빌드 시 train 70,688 / val 8,836 / test 8,836. 크롭 = crops 48k(failure)+40k(balance), corpus ledger 60k+.

**구축한 파일(로컬=SSOT, git으로 AWS 동기화)**:
- `run-finetune.sh`(repo root): 원커맨드 [1/6~6/6] = build_dataset→build_paddlex_dataset→check_dataset→train→export→finetune_report. run-eval.sh와 동형(tee ~/OCR/logs/finetune.log, tmux 방식)
- `eval/finetune/config_ppocrv5_rec_finetune.yaml`: PaddleX 통합 config(dataset_dir=eval/finetune_corpus, pretrain URL 내장)
- `eval/finetune/paddlex_train.py`: 드라이버(pip엔 Engine만 있고 main.py 없어서 자작). **matplotlib>=3.10 tostring_rgb 제거 shim 포함**(안 넣으면 deep-analyse/plot에서 AttributeError)
- `eval/build_paddlex_dataset.py`: corpus→PaddleX MSTextRecDataset 레이아웃(dict.txt는 모델 inference.yml의 character_dict 11,945자 추출, train.txt는 루트로 surface, 중첩 dataset/*.txt 제거 — get_dataset_root가 **/train.txt 1개만 허용)
- `eval/finetune_report.py`: **"인식 좋아졌나" 직접 답하는 self-contained HTML**. base 모델 vs 파인튜닝 모델을 held-out test 크롭에 직접 돌려 정확일치/문자유사도 비교, 개선/회귀 크롭 base64 박음, 컬럼 영·한 병기, 글자 diff 빨강. run-finetune.sh 6단계로 자동 생성 → FINETUNE_REPORT.html

**학습 실행 = AWS tmux**: `paddlex --install PaddleOCR`(1회, repo_manager/repos 디렉터리 없으면 mkdir 선행) 후 `~/OCR/run-finetune.sh`. venv는 `.venv/bin/python`(PATH에 없음).

**루프(중요, 자동 아님)**: 학습→**export→main.py rec를 export inference로 교체(1회만, text_recognition_model_name→text_recognition_model_dir)→서버 재시작→eval** 라야 효과 반영. 서버가 모델 캐시(get_ocr_engine)라 재시작 필수. 매 사이클 export+재시작 필요(main.py 교체는 1회).

**비교 방법론(한 번에 하나만)**: 룰→eval(064, vs063=룰효과) → 파인튜닝 스왑→eval(065, vs064=파인튜닝효과). "인식 자체 됐나"는 end-to-end eval 말고 **rec evaluate(base vs ft, held-out)**로 직접. 룰base=**063**(062아님, 최신). [[project_invoice_rule_work_priorities]]

**★2026-07-08 v1~v4 실측 → FT 주차(파킹) 결정**: v1(전컬럼)=라벨이 정규화GT라 '콤마/구분자 벗기기'를 학습→064 파이프라인 붕괴(study 77→36.5)·즉시 롤백. v2(품명만)=동일 결함 잔존. v3=failure 라벨 원문화(gtRaw)했지만 balance(labels_correct)가 여전히 gtNorm→절반 오염. v4=balance도 OCR원문으로 수정(마지막 구멍 봉합, 게이트 통과 콤마 11k)했더니 **진짜 실력 노출: net −74(개선71/회귀145), exact 32.3→26.7, val best가 base보다 낮음** — 라벨 버그 아닌 **데이터 규모·구성 한계**. 회귀 패턴=짧은 크롭 파괴(2→빈칸,30T→3T). **결정: 원 로드맵 복귀(룰→매칭→learndata, FT=마지막 카드), corpus 스케일업 후 재시도.** 재시도 레시피: lr 5e-5 / 2~3 epoch / balance 2:1 / 짧은라벨(≤3자) 제외 / 판정은 val 아닌 리포트(vs base). 파이프라인 자산 완성: 라벨 원문화(gtRaw+balance OCR원문)+label-gate(보존율)+리포트 사례검사 게이트. 서버=official 롤백 상태(output_v1_fullcol 백업).

**gitignore**: corpus 텍스트/output이 실수로 커밋돼 로컬↔AWS 왕복 마찰. finetune_corpus/·finetune/output/ gitignore + 바뀌는 txt 8개만 `git rm --cached`(88k 크롭 전체는 느려서 불필요, 안 바뀌니 충돌 안 함). [[feedback_workspace_hygiene]]
