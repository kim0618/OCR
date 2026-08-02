---
name: feedback_no_offline_rederive_use_response
description: 오프라인 재현으로 꼬지 말 것 — 서버 응답/AWS에 데이터가 이미 있다
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4a11fae8-19da-49c1-b4cb-c487fcd6330c
---

2026-06-22. 파인튜닝 크롭 추출을 "로컬에서 preprocess.py로 전처리 이미지 재현"으로 설계했다가 사용자가 "왜 로컬에서 하냐, AWS에서 돌리면 데이터 다 있잖아 폴더에 넣으면 되잖아"로 바로잡음.

**Why**: 전처리가 OCR과 얽혀(한글다움 보고 회전→재-OCR 등 분기) 오프라인 충실재현이 fragile했는데, 정작 **서버가 OCR에 먹인 바로 그 이미지(`processed_image` = `ocr_img`)가 응답에 이미 실려옴**(main.py:3525, 회전/deskew/unwarp 분기마다 재동기화). 재현도 main.py 수정도 불필요했음. 내가 데이터가 이미 있는 곳(서버 응답/AWS run)을 안 보고 로컬 재구성으로 과하게 꼰 것.

**How to apply**: 데이터 추출이 필요하면 **"그 데이터가 이미 어디 흘러나오나"부터 확인**(서버 응답 필드, run 산출물). 워크플로우는 AWS-run 생산 → 로컬 분석이니, **생산 지점(서버 응답/AWS)에 이미 있는 걸 캡처**하는 게 먼저고, 로컬 재현/재계산은 마지막 수단. 복잡한 재구성 설계 전에 "원본이 이미 손에 들어오는 경로"를 묻기. [[project_finetune_ledger_infra]] [[project_ocr_snapshot_replay]]
