---
name: project_finetune_processed_backup
description: FT run 20260720_175949 processed/(17G 전처리이미지) 로컬 tar백업+AWS삭제(2026-07-24). 크롭 재-cut 복원법 + AWS FT corpus 디스크 상태 + FT 트리 로드맵
metadata: 
  node_type: memory
  type: reference
  originSessionId: a262fce8-4a79-4402-aeb4-5536e7b712d5
  modified: 2026-07-24T01:16:30.059Z
---

2026-07-24. FT corpus AWS 디스크 관리 — `processed/`(전처리이미지 17G, 93,708장) 로컬 백업 후 AWS 삭제.

## ★processed 백업 위치 (재-cut 필요시 복원)
- **로컬**: `C:\Users\jinsung\Desktop\[신규] 프리세일즈\1_OCR\1_파인튜닝\processed.tar` (16.5GiB, 93,708파일, tar검증 exit0·파일수 일치)
- 전송법(참고): AWS서 `ssh 'tar -cf - -C runs/20260720_175949 processed' > 로컬.tar` (중간저장 없이 스트리밍, ~42MB/s ~7분).
- **왜 백업만 하고 AWS 삭제**: processed는 **크롭 재-cut(새 recipe FT라운드)에만** 필요. 크롭은 이미 잘렸음. → 백업 보존 + AWS 13G→**29G** 확보.
- **복원**: 재-cut 필요시 tar 재업로드 → `tar -xf processed.tar -C runs/20260720_175949` → `finetune_crops_balance.py --cap N`.

## AWS 유지 중 (FT 재사용 자산, 삭제 금지)
`finetune_corpus/crops`(7.5G failure)·`crops_correct`(13G balance)·`ledger.jsonl`·dataset(train/val) = 라운드마다 학습데이터 / `finetune/output`(FT 모델) / `data/invoice_war`(learndata·master_dict·GT·images) / snapshots·compare.

## 라운드 운영법 (디스크 29G로 버티기)
채택 안 된 라운드 `finetune/output/`(~2.2G, iter_epoch_*·latest 포함)는 매번 삭제(v1/v4 지웠듯). 채택본만 `adopted/`로 승격. output 내 **iter_epoch_1~4·latest·check_dataset·train.log는 학습 끝나면 즉시 삭제 가능**(best_accuracy·inference만 판정까지 유지).

## FT 트리 로드맵 (사용자 확정)
① 품명 1차 채택 ✅ → ② 숫자 2차(게이트=**품명 유지 AND 숫자↑**, 통과까지 앵커/config 조정 재시도, 근본 트레이드오프면 최선점서 멈추고 숫자는 룰에) → ③ 전체측정: 약필드 남았나(있으면 그 필드 라운드 추가=트리계속 / 없으면 FT일단락) → ④ 최종모델 제품전체 투입 측정(읽기향상이 품명매칭·필드정확도 얼마나 올렸나=진짜성과). recipe: failure=품명만(`--columns itemName --hangul-min 2 --raw-only`, 숫자 콤마붕괴로 제외)·balance=전필드 인쇄형(`--balance-ratio 3`). [[project_finetune_pipeline_runnable]] [[project_rekey_105k_batches]]
