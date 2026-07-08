#!/bin/bash
# 파인튜닝 원커맨드 — run-eval.sh 의 파인튜닝판 (PP-OCRv5 mobile 한국어 rec).
#
# tmux 로 돌리는 방식 (run-eval.sh 와 동일):
#   tmux new -s finetune
#   bash ~/OCR/run-finetune.sh          # (나오기: Ctrl+B 떼고 D)
#   tmux attach -t finetune             # 재접속
#
# 흐름: corpus 최신 크롭 -> rec 리스트 -> PaddleX 레이아웃 -> 데이터셋 검증 -> 학습.
# 로그는 ~/OCR/logs/finetune.log 에 tee. best 가중치 = eval/finetune/output/best_accuracy/.
set -eo pipefail
export PYTHONUNBUFFERED=1
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs

CFG=eval/finetune/config_ppocrv5_rec_finetune.yaml
DRV=eval/finetune/paddlex_train.py
{
  echo "==================== 파인튜닝 시작 [$(date +'%F %T')] ===================="
  echo "[1/6] corpus -> rec 리스트 재빌드 (최신 크롭 반영)"
  # 표적=품명만+원문라벨 (v1/v2 실측: 정규화 라벨은 '구분자 벗기기'를 가르쳐 파이프라인 붕괴).
  # raw-only = 원문 GT 라벨 엔트리만(재수확 후 적립분) / hangul-min 2 = 숫자·날짜 크롭 배제
  # (war GT 원문조차 돈엔 콤마가 없어 숫자는 어떤 GT 라벨로도 인쇄형 복원 불가).
  # balance(정답 크롭=base 읽은 원문 그대로)는 전컬럼 유지 -> 숫자·포맷 망각 방지 앵커.
  python eval/build_dataset.py --balance-ratio 1.0 --columns itemName --min-match 0.7 \
      --hangul-min 2 --raw-only
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
  python "$DRV" -c "$CFG" -o Global.mode=train 2>&1 | python eval/finetune_progress.py
  echo "[5/6] export (서버가 읽는 inference 형식으로 변환)"
  python "$DRV" -c "$CFG" -o Global.mode=export
  echo "[6/6] 인식 비교 리포트 (base vs 파인튜닝, held-out test 크롭 직접)"
  python eval/finetune_report.py || echo "  (리포트 생성 실패 — 로그 확인)"
  echo "==================== 파인튜닝 끝 [$(date +'%F %T')] ===================="
  echo "best 가중치: eval/finetune/output/best_accuracy/"
  echo "인식 리포트: eval/finetune/FINETUNE_REPORT.html  (← 로컬에서 열면 됨)"
  echo "--- export된 inference 경로 (main.py rec 를 이걸로 교체) ---"
  find eval/finetune/output -type d -name inference 2>/dev/null || true
} 2>&1 | stdbuf -oL -eL tee -a ~/OCR/logs/finetune.log
