#!/bin/bash
set -eo pipefail
export PYTHONUNBUFFERED=1
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs
CFG=eval/finetune/config_ppocrv5_rec_finetune.yaml
DRV=eval/finetune/paddlex_train.py
{
  echo "==================== 파인튜닝 시작 [$(date +'%F %T')] ===================="
  echo "[1/5] corpus -> rec 리스트 재빌드"
  python eval/build_dataset.py --balance-ratio 1.0
  echo "[2/5] PaddleX 레이아웃 + 중첩 정리"
  python eval/build_paddlex_dataset.py
  rm -f eval/finetune_corpus/dataset/train.txt eval/finetune_corpus/dataset/val.txt eval/finetune_corpus/dataset/test.txt
  echo "[3/5] 데이터셋 검증"
  python "$DRV" -c "$CFG" -o Global.mode=check_dataset
  echo "[4/5] 학습"
  python "$DRV" -c "$CFG" -o Global.mode=train
  echo "[5/5] export (inference 형식)"
  python "$DRV" -c "$CFG" -o Global.mode=export
  echo "==================== 파인튜닝 끝 [$(date +'%F %T')] ===================="
  echo "best: eval/finetune/output/best_accuracy/"
  find eval/finetune/output -type d -name inference 2>/dev/null || true
} 2>&1 | stdbuf -oL -eL tee -a ~/OCR/logs/finetune.log
