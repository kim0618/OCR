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
  # ★★한글(품명 포함 전 한글필드) 라운드 (2026-07-23, 재검증으로 확대):
  #  어제 전필드 학습은 숫자 58%→콤마붕괴로 net −3,524 기각. 단 한글은 +6.4%p로 올랐음.
  #  ★재검증(2026-07-23): failure 한글 크롭이 itemName 310k 외에 회사명·주소 254k+ 있는데
  #   itemName만 돌리면 그걸 버려 "한글 전체"가 안 됨 → 한글 필드 전체로 확대.
  #  - failure(한글, 다양성 있는 필드만): itemName(고유 94k) + supplierCompany/supplierAddress
  #    (고유 ~1.1k). ★buyerCompany(고유 11)·buyerAddress(고유 14) 제외 = 16.6만 크롭이 25개
  #    문자열 반복뿐 → 암기·빈도편향 유발(학습가치 0, 실측). itemNameMaster 제외=rewrite,
  #    spec·taxType 제외=짧고 반복.
  #  - balance(한글만) + 숫자 앵커(소량, ~15%): 한글 망각방지 + 숫자 망각만 방지(콤마붕괴 회피).
  #  - max-train 100만: 학습시간 관리(≈10h). 숫자 앵커 형식혼재·비율은 게이트로 튜닝.
  #  기대 구성: 한글 ~85% / 숫자 앵커 ~15% (아래 '학습셋 구성' 로그로 반드시 확인).
  python eval/build_dataset.py --balance-ratio 1.0 --max-train 1000000 \
      --columns itemName,supplierCompany,supplierAddress \
      --min-match 0.7 --hangul-min 2 --raw-only \
      --balance-hangul-min 1 --number-anchor-ratio 0.3
  # [label-gate] 출력 확인: 공백/슬래시/대문자 보존율이 0%대면 학습 중단하고 라벨부터 볼 것
  # [학습셋 구성] 로그 확인: 한글이 ~80% 주도해야 정상. 숫자가 다시 다수면 필터가 안 먹은 것.
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
