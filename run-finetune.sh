#!/bin/bash
# 파인튜닝 원커맨드 — run-eval.sh 의 파인튜닝판 (PP-OCRv5 mobile 한국어 rec).
#
# tmux 로 돌리는 방식 (run-eval.sh 와 동일):
#   tmux new -s finetune
#   bash ~/OCR/run-finetune.sh          # official pretrained 에서 새로 학습(트리 뿌리)
#   bash ~/OCR/run-finetune.sh --from-adopted   # ★ 채택된 모델을 이어받아 학습(트리 줄기 연장)
#   tmux attach -t finetune             # 재접속
#
# 트리 구조 이어받기:
#   --from-adopted 를 주면 pretrain 을 official 대신 eval/finetune/adopted/best_accuracy.pdparams
#   (직전 채택본)로 바꿔 그 위에 얹어 학습한다. 아직 채택본이 없으면 자동으로 official 로 시작.
#   학습 후 게이트 통과 시 채택:  python eval/finetune_adopt.py --version v6
#   (채택하면 adopted/ 갱신 → main.py 반영 + 다음 --from-adopted 의 base 가 됨)
#
# 흐름: corpus 최신 크롭 -> rec 리스트 -> PaddleX 레이아웃 -> 데이터셋 검증 -> 학습.
# 로그는 ~/OCR/logs/finetune.log 에 tee. best 가중치 = eval/finetune/output/best_accuracy/.
set -eo pipefail
export PYTHONUNBUFFERED=1
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs
_FT_START=$SECONDS   # 실행 이력 장부용 타이머

CFG=eval/finetune/config_ppocrv5_rec_finetune.yaml
DRV=eval/finetune/paddlex_train.py

# --- 이어받기(트리) 결정: --from-adopted 면 채택본을 base 로 pretrain override ---
FROM_ADOPTED=0
for a in "$@"; do [ "$a" = "--from-adopted" ] && FROM_ADOPTED=1; done
ADOPTED_PDP=eval/finetune/adopted/best_accuracy.pdparams
ADOPTED_META=eval/finetune/adopted/META.json
TRAIN_OVERRIDE=""      # 학습 스텝에 추가할 -o (기본: 없음 = config 의 official pretrained)
BASE_TAG="official"    # run_history 계보에 남길 부모
if [ "$FROM_ADOPTED" = "1" ]; then
  if [ -f "$ADOPTED_PDP" ]; then
    TRAIN_OVERRIDE="-o Train.pretrain_weight_path=$PWD/$ADOPTED_PDP"
    BASE_TAG=$(python -c "import json;print(json.load(open('$ADOPTED_META')).get('version','adopted'))" 2>/dev/null || echo adopted)
    echo "[이어받기] 채택본을 base 로 학습: $ADOPTED_PDP  (부모=$BASE_TAG)"
  else
    echo "[이어받기] 아직 채택본 없음($ADOPTED_PDP) → official pretrained 로 시작(트리 뿌리)"
  fi
fi
{
  echo "==================== 파인튜닝 시작 [$(date +'%F %T')] ===================="
  echo "[1/6] corpus -> rec 리스트 재빌드 (최신 크롭 반영)"
  # ★전 필드 인쇄형 학습 (2026-07-09, 10만장 설계):
  #  - failure(품목만+원문라벨): 인식이 약한 품목의 약점 보강 (숫자 failure 는 GT 정규화라
  #    콤마-붕괴 유발 → 제외 유지: --columns itemName --hangul-min 2 --raw-only)
  #  - balance(전 필드 GT-검증 인쇄형): 숫자·날짜·품목의 '인쇄형 정답'을 대량 학습 → 전 필드
  #    인식이 올라감(cap 160/img 로 이미지당 대부분 셀 수확). balance-ratio 3 = 전필드 주도.
  #  - max-train: 10만장 규모면 balance 수백만 → 학습시간 관리. 지금(6천장)은 0(무제한).
  #    10만장 때 예: --max-train 400000 (failure 우선 보존 + balance 축소)
  python eval/build_dataset.py --balance-ratio 3.0 --max-train 0 \
      --columns itemName --min-match 0.7 --hangul-min 2 --raw-only
  # [label-gate] 출력 확인: 공백/슬래시/대문자 보존율이 0%대면 학습 중단하고 라벨부터 볼 것
  echo "[2/6] PaddleX 레이아웃 (dict.txt + 루트 리스트, 중첩 정리)"
  python eval/build_paddlex_dataset.py
  # PaddleX get_dataset_root 는 **/train.txt 가 정확히 1개여야 함. build_paddlex_dataset
  # 구버전은 중첩 dataset/*.txt 를 안 지우므로 여기서 확실히 제거(버전 무관 안전).
  rm -f eval/finetune_corpus/dataset/train.txt \
        eval/finetune_corpus/dataset/val.txt \
        eval/finetune_corpus/dataset/test.txt
  echo "[3/6] 데이터셋 검증 (게이트)"
  python "$DRV" -c "$CFG" -o Global.mode=check_dataset
  echo "[4/6] 학습"
  # 학습 출력을 진행 정리기로 통과 → 왼쪽에 '전체 대비 진행/​%' 카운터로 깔끔하게.
  # (에러·다운로드·평가결과 줄은 그대로 통과하니 문제 생기면 그대로 보임)
  python "$DRV" -c "$CFG" -o Global.mode=train $TRAIN_OVERRIDE 2>&1 | python eval/finetune_progress.py
  echo "[5/6] export (서버가 읽는 inference 형식으로 변환)"
  python "$DRV" -c "$CFG" -o Global.mode=export
  echo "[6/6] 인식 비교 리포트 (base vs 파인튜닝, held-out test 크롭 직접)"
  python eval/finetune_report.py || echo "  (리포트 생성 실패 — 로그 확인)"
  echo "==================== 파인튜닝 끝 [$(date +'%F %T')] ===================="
  echo "best 가중치: eval/finetune/output/best_accuracy/"
  echo "인식 리포트: eval/finetune/FINETUNE_REPORT.html  (← 로컬에서 열면 됨)"
  echo "--- 채택하려면(게이트 통과 시): 트리 줄기로 승격 + main.py 반영 ---"
  echo "  python eval/finetune_adopt.py --version v6      # 부모=직전 채택본(없으면 official)"
  echo "  이후 이어받아 학습: bash ~/OCR/run-finetune.sh --from-adopted"
  # 실행 이력 장부 기록: 학습 크롭 수 · epoch · 소요 시간 · best acc
  _ft_imgs=$(wc -l < eval/finetune_corpus/train.txt 2>/dev/null || echo 0)
  _ft_ep=$(grep -oE 'epochs_iters: [0-9]+' "$CFG" | grep -oE '[0-9]+' | head -1)
  _ft_acc=$(grep -a 'best metric' ~/OCR/logs/finetune.log 2>/dev/null | tail -1 | grep -oE 'acc: [0-9.]+' | grep -oE '[0-9.]+' | head -1)
  python eval/run_history.py --record finetune --ts "$(date +%y%m%d_%H%M)" \
    --base "$BASE_TAG" \
    --images "$_ft_imgs" --epochs "${_ft_ep:-0}" --elapsed "$((SECONDS - _FT_START))" \
    --best-acc "${_ft_acc:-0}" --adopted 0 || true
} 2>&1 | stdbuf -oL -eL tee -a ~/OCR/logs/finetune.log
