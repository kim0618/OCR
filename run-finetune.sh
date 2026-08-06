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
# ★결정성(2026-08-06). 같은 설정·같은 데이터로 두 번 돌렸는데(v5→v9 재실행) 잃어버림이
#  593→718 로 갈라졌다. 시드는 PaddleOCR train.py 가 기본 1024 로 이미 고정하고 있으므로
#  (random/np/paddle.seed — repo tools/train.py:298) 원인은 RNG 가 아니라 GPU 비결정성이다:
#  cuDNN 알고리즘 자동선택 + atomic 누산. 아래 플래그는 paddle 초기화 전에 환경변수로
#  있어야 먹는다(스크립트 최상단인 이유). 비용: 학습 10~20% 느려질 수 있음.
#  성패는 A/A(동결 데이터셋으로 2회, --dataset-from)로 판정한다 — 개별 예측까지 같아야 성공.
export FLAGS_cudnn_deterministic=1
export FLAGS_cudnn_exhaustive_search=0
export PYTHONHASHSEED=0
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs
_FT_START=$SECONDS   # 실행 이력 장부용 타이머
RUN_TAG="$(date +%y%m%d_%H%M)"
TRAIN_LOG="$HOME/OCR/logs/finetune_${RUN_TAG}.train.log"

# RUN_HISTORY의 AWS 예상요금은 실행시간×시간당 단가다. 서버별 실제 계약 단가를
# 환경변수로 한 번만 지정하면 이후 eval/FT 모두 자동 기록한다.
#   export AWS_INSTANCE_TYPE=g6.xlarge AWS_REGION=ap-northeast-2
#   export AWS_PURCHASE_OPTION=OnDemand AWS_EC2_HOURLY_USD=<현재 시간당 USD>

CFG=eval/finetune/config_ppocrv5_rec_finetune.yaml
DRV=eval/finetune/paddlex_train.py

# --- 라운드 선택: hangul(품명) | numeric(숫자만) | combined(품명+숫자, ★권장) ---
#   bash run-finetune.sh                              # 품명(한글) 라운드 (1차·완료)
#   bash run-finetune.sh --round=combined --from-adopted  # ★품명+숫자 통합(품명v1 이어받아, 구덩이없음)
#   bash run-finetune.sh --round=fields   --from-adopted  # ★★실필드(combined−itemCode바코드) 2026-07-26
#   bash run-finetune.sh --round=numeric  --from-adopted  # 숫자만 target + 품명 앵커(순차, 18문턱)
ROUND=hangul
TARGETS=""
DATASET_FROM=""
WORKERS=""
DEMO_EPOCHS_ARG=20
EPOCH_LADDER=0
EPOCH_CLEANUP=0
DEMO_SCAN=1
for a in "$@"; do
  case "$a" in
    --round=*) ROUND="${a#*=}" ;;
    --numeric) ROUND=numeric ;;
    --targets=*) TARGETS="${a#*=}" ;;
    --dataset-from=*) DATASET_FROM="${a#*=}" ;;
    --workers=*) WORKERS="${a#*=}" ;;
    --epochs=*) DEMO_EPOCHS_ARG="${a#*=}" ;;
    --epoch-ladder) EPOCH_LADDER=1 ;;
    --epoch-cleanup) EPOCH_CLEANUP=1 ;;
    --no-scan) DEMO_SCAN=0 ;;
  esac
done

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
    BASE_TAG=$(python -c "import json;m=json.load(open('$ADOPTED_META'));print(m.get('runTs') or m.get('version','adopted'))" 2>/dev/null || echo adopted)
    echo "[이어받기] 채택본을 base 로 학습: $ADOPTED_PDP  (부모=$BASE_TAG)"
  else
    echo "[이어받기] 아직 채택본 없음($ADOPTED_PDP) → official pretrained 로 시작(트리 뿌리)"
  fi
fi
{
  echo "==================== 파인튜닝 시작 [$(date +'%F %T')] ===================="
  echo "[1/6] corpus -> rec 리스트 재빌드 (라운드=$ROUND)"
  # ★기준셋(9,001 held-out) 보호: replay eval 이 수확한 크롭도 corpus 에 쌓이는데, 그걸
  # 학습에 쓰면 다음 replay 측정이 '본 문제로 시험'이 됨. images_replay 트리에서 소스
  # 목록을 만들어 build_dataset 이 failure/balance 양쪽에서 제외한다(전 라운드 공통).
  REPLAY_SRC=eval/finetune_corpus/replay_sources.txt
  if [ -d eval/data/invoice_war/images_replay ]; then
    find eval/data/invoice_war/images_replay -type f \( -name '*.jpg' -o -name '*.png' \) \
      | sed -E 's#.*/images_replay/([^/]+)/([^/]+)/#\1__\2__#' > "$REPLAY_SRC"
    echo "[기준셋 보호] 제외 소스 $(wc -l < "$REPLAY_SRC")개 -> $REPLAY_SRC"
  else
    : > "$REPLAY_SRC"   # 기준셋 이미지 없으면 빈 목록(제외 없음)
  fi
  if [ "$ROUND" = "combined" ]; then
    # ★★통합 라운드 (2026-07-24): 품명 + 숫자를 한 번에 target. 순차의 "18 구덩이" 회피.
    #  근거: 1차 숫자 −18.8%p 는 대부분 콤마붕괴(포맷)였음(리포트: 26,641,755→26,641.755, 자릿수는
    #  맞음). 숫자 라벨을 인쇄형(콤마)으로 재구성하면 그 18%가 회복 → 최소 official 수준 복귀.
    #  둘 다 target이라 서로 안 까먹음(forgetting 없음). ★--from-adopted 로 품명v1 이어받아
    #  품명 +11.3%p 유지 + 숫자 회복. balance=전체(전필드 망각방지), 앵커 불필요(둘 다 직접 학습).
    #  날짜·buyer번호 제외 = 콤마↔마침표 혼동(포맷 혼재) 위험 차단. hangul-min 미사용(숫자 죽음).
    python eval/build_dataset.py --balance-ratio 1.0 --max-train 1200000 \
        --columns itemName,supplierCompany,supplierAddress,amount,unitPrice,quantity,supplyAmount,taxAmount,totalAmount,discountAmount,itemCode,supplierBizNumber,manufacturingNo,lotNo \
        --min-match 0.7 --raw-only --reconstruct-number-labels \
        --exclude-sources "$REPLAY_SRC"
    FT_CRITERIA="품명+숫자 통합(숫자 콤마재구성) — 품명v1 이어받아 품명유지+숫자회복(콤마 18%)"
  elif [ "$ROUND" = "fields" ]; then
    # ★★실필드 라운드 (2026-07-26): combined 에서 itemCode(바코드)만 뺀 것 — same-crop 실측 근거.
    #  COMPARE_V1_SUBCOL(120k 동일크롭, combined vs V1): 금액 +1.2pp·코드날짜 +1.0 은 올랐지만
    #  쉬운숫자(컬럼미상) −4.7·한글기타 −4.5 broad forgetting 으로 전체 net −1,295 상쇄.
    #  주범 = failure 의 itemCode 바코드 27만장(8자리+ 90%, base 정답률 6.6%=원래 못읽는 하드케이스,
    #  그래디언트가 바코드에 쏠려 딴 걸 까먹음). ★itemCode 는 OCR 산출이 아니라 품명→마스터매칭
    #  산출(top1+가격 87.9%, master_match)이므로 학습 불필요 = 제외가 맞다.
    #  balance=전체(char-type 무필터): 구세대 balance 는 컬럼 미상이지만 match-검증된 정답 크롭
    #  (라벨 건전)이라 일반 망각방지 앵커로 유지. 기준셋 수확분(src 없는 meta행)은 자동 제외됨.
    #  ★반드시 --from-adopted(품명v1) 와 함께.
    python eval/build_dataset.py --balance-ratio 1.0 --max-train 1000000 \
        --columns itemName,supplierCompany,supplierAddress,amount,unitPrice,quantity,supplyAmount,taxAmount,totalAmount,discountAmount,supplierBizNumber,manufacturingNo,lotNo \
        --min-match 0.7 --raw-only --reconstruct-number-labels \
        --exclude-sources "$REPLAY_SRC"
    FT_CRITERIA="실필드 전용(combined−itemCode바코드): 품명유지+직접읽기 숫자, 콤마재구성"
  elif [ "$ROUND" = "fields2" ]; then
    # ★★2차 프로브 (2026-07-27): base 재시작 probe1(품명+5.7·금액+4.4·단가+3.4) 의 두 회귀 교정.
    #  ①spec −5.6 = 학습컬럼 미포함 부수망각 → spec 추가.
    #  ②수량 −5.4 = 긴 문자열(콤마금액·품명) 위주라 1~3자리 짧은숫자가 1%뿐 → 짧은시퀀스
    #    출력붕괴("10"→"1" 끝자리 탈락, 라벨은 정상 확인). --short-num-anchor-ratio 로 보강.
    #  lr 3e-5(config)·바코드 제외·콤마재구성은 probe1 그대로. base 재시작 = --from-adopted 없이.
    python eval/build_dataset.py --balance-ratio 1.0 --max-train 1000000 \
        --columns itemName,spec,supplierCompany,supplierAddress,amount,unitPrice,quantity,supplyAmount,taxAmount,totalAmount,discountAmount,supplierBizNumber,manufacturingNo,lotNo \
        --min-match 0.7 --raw-only --reconstruct-number-labels \
        --short-num-anchor-ratio 0.15 \
        --exclude-sources "$REPLAY_SRC"
    FT_CRITERIA="2차 프로브: fields+spec, 짧은숫자 앵커 0.15 (수량붕괴·spec망각 교정), base 재시작"
  elif [ "$ROUND" = "fields3" ]; then
    # ★★3차 (2026-07-28): probe2(fields2) 실패 부검 반영. 먼저 1ep 프로브(config)로
    #  이 구성이 먹히는지 확인사격 → 게이트 통과 시 epochs 3 으로 본판(프로브 표준).
    #  ①spec 제외 원복 — spec 라벨=gt_trust unverified(구글 raw 노이즈). 학습에 쓴 크롭조차
    #    spec 12.2→1.3% = 암기불가 노이즈 실증, 224k가 그래디언트 오염(val acc 0.41→0.17).
    #    ★미검증 라벨 컬럼은 학습 금지 원칙.
    #  ②balance(망각방지) 비중 복원 — spec 제거로 failure 414k → balance ~49% 회복.
    #  ③짧은숫자 앵커 유지(0.15) — 검증된 정답 라벨이라 무해, balance와 dedup됨.
    #  1ep 게이트: 품명·금액·단가 probe1 수준(+5.7/+4.4/+3.4 근방) AND 유지탭 probe2(−39.8)
    #  대비 완만 AND 수량이 probe1(−5.4)보다 악화 없음 → 본판 3ep(짧은숫자 과도기 회복 검증).
    #  base 재시작(--from-adopted 없이), lr 3e-5, 바코드 제외, 콤마재구성 유지.
    python eval/build_dataset.py --balance-ratio 1.0 --max-train 1000000 \
        --columns itemName,supplierCompany,supplierAddress,amount,unitPrice,quantity,supplyAmount,taxAmount,totalAmount,discountAmount,supplierBizNumber,manufacturingNo,lotNo \
        --min-match 0.7 --raw-only --reconstruct-number-labels \
        --short-num-anchor-ratio 0.15 \
        --exclude-sources "$REPLAY_SRC"
    FT_CRITERIA="3차 프로브: fields(spec 제외 원복)+짧은숫자 앵커 0.15, base 재시작"
  elif [ "$ROUND" = "clean" ]; then
    # ★★clean-core (2026-07-28, probe2 예측원본 재검증 기반): 측정가능·검증된 핵심 7컬럼만.
    #  제거 근거(전부 probe2 실측):
    #   - spec: unverified 라벨 노이즈(SEEN조차 −10.8 = 암기불가) → 학습 금지
    #   - supplierAddress: base 0%→ft 0% = 바코드와 같은 하드케이스 그래디언트 독 패턴
    #   - supplyAmount/taxAmount/totalAmount/discountAmount: base ~0%·n 소수·GT 신뢰 낮음
    #   - lotNo: 벤치에 없어 측정 불가(효과 검증 수단 없음)
    #  보존 강화: balance 2.0(까먹음이 주병목) + 짧은숫자 앵커 0.5(수량 붕괴 방어).
    #  failure ~19만 추정 → 총 ~66만, max-train 여유. base 재시작, lr 3e-5, 1ep 프로브.
    #  게이트: 품명 +5↑ AND 금액·단가 ≥0 AND 수량 −2 이내 AND RETAIN 전체·짧은숫자 −5 이내.
    python eval/build_dataset.py --balance-ratio 2.0 --max-train 1000000 \
        --columns itemName,supplierCompany,amount,unitPrice,quantity,supplierBizNumber,manufacturingNo \
        --min-match 0.7 --raw-only --reconstruct-number-labels \
        --short-num-anchor-ratio 0.5 \
        --exclude-sources "$REPLAY_SRC"
    FT_CRITERIA="clean-core 7컬럼(측정가능·검증만)+balance 2.0+짧은숫자 앵커 0.5, base 재시작"
  elif [ "$ROUND" = "clean2" ]; then
    # ★★★clean2 = clean + 숫자 라벨 실현성 필터 "단 한 변수" (2026-07-29 부검 확정 처방).
    #  004(clean 레시피) E2E 기각의 근본원인이 전수 측정으로 확정됨:
    #   ★숫자 failure 학습크롭의 79%(4~6자리는 87%)가 "라벨이 크롭에 물리적으로 안 들어가는"
    #    모순 라벨(크롭='2' 한 글자·라벨='250010', 크롭='공'·라벨='41,201' — 수확 bbox↔GT
    #    정렬 오류). 육안 30장 검증에서도 2/3 불일치. 9만 장의 거짓 라벨을 학습한 결과:
    #   - 모델이 학습에 쓴 크롭조차 재현 실패(라벨 0=6.7%, 8=10%) = 암기 불가능한 모순
    #   - CTC 는 모순 앞에서 blank 를 선택 → 1자리 빈출력 51.5%·선두탈락 → 수량 공백
    #     → 행 산술·정렬 붕괴 → E2E 셀 −43,012 연쇄
    #   - 품명만 오른 이유: 한글 라벨은 정합 86%라 제대로 배움(문자수 61% 지배)
    #  처방 = --numeric-feasible-min-width 0.45 (자릿수×0.45 > w/h 면 드랍).
    #  나머지는 clean 과 동일(같은 컬럼·balance 2.0·짧은숫자 앵커 0.5·base 재시작·1ep)
    #  → 기존 003/004 가 같은 스케일 대조군이라 필터 효과가 그대로 분리됨.
    #  ★판정 순서(새 표준): ①로컬 조기게이트 = 학습에 쓴 1자리 크롭 재현율 ≥90%(004=6.7%)
    #    → ②벤치(UNSEEN 숫자탭도 같은 오염이 있으니 참고만) → ③E2E(최종심).
    python eval/build_dataset.py --balance-ratio 2.0 --max-train 1000000 \
        --columns itemName,supplierCompany,amount,unitPrice,quantity,supplierBizNumber,manufacturingNo \
        --min-match 0.7 --raw-only --reconstruct-number-labels \
        --short-num-anchor-ratio 0.5 \
        --numeric-feasible-min-width 0.45 \
        --exclude-sources "$REPLAY_SRC"
    FT_CRITERIA="clean2: clean + 숫자 라벨 실현성 필터 0.45 (모순라벨 79% 제거), base 재시작"
  elif [ "$ROUND" = "clean3" ]; then
    # ★★★clean3 = clean2 + 짧은숫자 라벨 self-verify "단 한 변수" (2026-07-30 clean2 부검).
    #  clean2 결과: 실현성 필터가 4+자리를 살림(RETAIN +2.6, UNSEEN 전컬럼 +) — 그러나
    #  1자리 RETAIN -38.1 로 더 붕괴. 원인 실측: 1자리 '정답풀' 크롭의 34%(육안 137/400)가
    #  도장·바코드·표머리글·한글에 숫자 라벨 — 수확 정렬 버그가 balance 에도 있고,
    #  1자리는 길이-실현성 검사의 사각지대(어떤 크롭이든 1자는 '들어가므로').
    #  처방 = 학습 목록의 1~3자리 숫자 라벨을 base 로 재판독해 출력==라벨만 남김(self-verify).
    #  1자리 목표는 '유지'이므로 base 가 읽는 크롭만으로 충분, 오염 1/3 이 직접 제거됨.
    #  게이트(로컬): 학습에 쓴 1자리 크롭 재현율 ≥90% AND RETAIN 1자리 -5 이내.
    python eval/build_dataset.py --balance-ratio 2.0 --max-train 1000000 \
        --columns itemName,supplierCompany,amount,unitPrice,quantity,supplierBizNumber,manufacturingNo \
        --min-match 0.7 --raw-only --reconstruct-number-labels \
        --short-num-anchor-ratio 0.5 \
        --numeric-feasible-min-width 0.45 \
        --exclude-sources "$REPLAY_SRC"
    echo "[clean3] 짧은숫자 라벨 self-verify (base 재판독, GPU ~수분)"
    python eval/verify_short_num_labels.py
    FT_CRITERIA="clean3: clean2 + 짧은숫자(1~3자리) 라벨 self-verify (1자리 정답풀 오염 34% 제거)"
  elif [ "$ROUND" = "clean4" ]; then
    # ★★★clean4 = clean3 + 1자리 오버샘플 x4 "단 한 변수" (2026-07-30 clean3 부검).
    #  clean3 결과: 라벨 정화 성공(검증크롭 official 99.5%)·역대 최고 val 0.5865·RETAIN 전체 -2.6·
    #  한글 -0.2·2-3자리 +2.7·4+ +0.6 — 그러나 1자리 재현 61.5%(게이트 90% 미달)·
    #  base정답 1자리 유지 79.6%. 라벨은 이제 깨끗하므로 남은 원인 = 그래디언트 점유:
    #  CTC 학습신호는 문자수 비례인데 1자리는 전체 문자의 ~1.5%뿐(한글 61% 지배).
    #  처방 = 검증 통과한 1자리 줄만 3회 추가 복제(4배, 문자점유 ~1.5%→~5.5%).
    #  깨끗한 카드만 복제하므로 오염 증폭 없음. 나머지는 clean3 과 완전 동일.
    #  게이트: 1자리 재현 ≥90% AND RETAIN(clean subset) 1자리 유지 ≥95% AND 나머지 버킷 무손상.
    python eval/build_dataset.py --balance-ratio 2.0 --max-train 1000000 \
        --columns itemName,supplierCompany,amount,unitPrice,quantity,supplierBizNumber,manufacturingNo \
        --min-match 0.7 --raw-only --reconstruct-number-labels \
        --short-num-anchor-ratio 0.5 \
        --numeric-feasible-min-width 0.45 \
        --exclude-sources "$REPLAY_SRC"
    echo "[clean4] 짧은숫자 라벨 self-verify + 1자리 오버샘플 x4"
    python eval/verify_short_num_labels.py --oversample-onedigit 3
    FT_CRITERIA="clean4: clean3 + 검증된 1자리 오버샘플 x4 (문자점유 1.5%→5.5%, blank 도피 차단)"
  elif [ "$ROUND" = "demo" ]; then
    # ★★소생 데모 라운드 (2026-08-03, 리뷰 합의). 못 읽는 품명을 파인튜닝으로 '살리는'
    #  것만 증명한다. 부수 회귀(그 외 셀)는 이 데모의 판정 대상이 아님.
    #
    #  ★한 회차 = 품명 2개 = 파인튜닝 2번, 4회차 = 모델 8개
    #    1단계: <직전 모델>이 못 읽던 품명 1개를 살린다.
    #    2단계: 1단계 모델이 새로 잃어버린 품명 1개를 --targets 에 추가해 둘 다 읽게.
    #  ★★모델 체인(트리 줄기): 모든 단계가 <바로 앞 단계 모델> 위에서 이어 학습한다.
    #    base → m1(1차1단계) → m2(1차2단계) → m3(2차1단계) → ... → m8(4차2단계)
    #    누적 타깃도 같이 늘어(1→2→3…→8) 마지막 m8 이 8개 전부 읽으면 그게 채택본이다.
    #    각 단계 모델은 demo/models/step<N>/ 에 보관(다음 단계의 시작점).
    #  판정: demo_report 가 test.txt(학습 안 쓴 같은 품명 크롭)를 직전 모델 vs 새 모델로
    #    채점 → 직전 모델 0%, 새 모델 전부 정답이면 소생 성공.
    #  사용: bash run-finetune.sh --round=demo --targets="디아세렌캡슐"            # 1차 1단계
    #        bash run-finetune.sh --round=demo --targets="디아세렌캡슐,<잃은품명>"  # 1차 2단계
    #        bash run-finetune.sh --round=demo --targets="...,...,<새타깃>"        # 2차 1단계
    if [ -z "$TARGETS" ]; then echo "★demo 라운드는 --targets=\"품명1,품명2\" 필수"; exit 1; fi
    DEMO_N=$(python - "$TARGETS" <<'PY'
import sys
print(len([t for t in sys.argv[1].split(",") if t.strip()]))
PY
)
    DEMO_ROUND=$(( (DEMO_N + 1) / 2 ))
    if [ $((DEMO_N % 2)) -eq 1 ]; then DEMO_STEP=1; else DEMO_STEP=2; fi
    DEMO_MODELS=eval/finetune/demo/models
    DEMO_PREV="$DEMO_MODELS/step$((DEMO_N - 1))"    # 바로 앞 단계 모델 = 이번 시작점
    DEMO_CMP_ARGS=""
    if [ "$DEMO_N" -ge 2 ]; then
      if [ ! -f "$DEMO_PREV/best_accuracy.pdparams" ]; then
        echo "★${DEMO_N}번째 단계인데 직전 단계 모델이 없습니다: $DEMO_PREV/best_accuracy.pdparams"
        echo "  (단계는 순서대로 이어져야 합니다 - 직전 단계를 먼저 완료하세요)"; exit 1
      fi
      TRAIN_OVERRIDE="-o Train.pretrain_weight_path=$PWD/$DEMO_PREV/best_accuracy.pdparams"
      BASE_TAG="demo_step$((DEMO_N - 1))"
      DEMO_CMP_ARGS="--compare-dir $PWD/$DEMO_PREV/inference --compare-step $((DEMO_N - 1))"
      echo "[데모] ${DEMO_ROUND}회차 ${DEMO_STEP}단계 (통산 ${DEMO_N}번째 모델) - 시작 모델 = 직전 $((DEMO_N - 1))번째 모델"
    else
      echo "[데모] 1회차 1단계 (통산 1번째 모델) - 시작 모델 = official base"
    fi
    # 기준셋(9,001) 소스 목록은 '학습 금지'인 동시에 '판정셋 식별자'다:
    #  그 문서에서 온 크롭 = 판정셋, 나머지(코퍼스) = 학습셋. 홀드아웃 불필요.
    # ★앵커 설정 - 아래 세 상수를 직접 고쳐서 바꾼다(환경변수 아님).
    #  배수는 타깃 대비 비율이다. 단계가 갈수록 타깃이 늘어나므로 절대값으로 두면
    #  조건이 계속 달라진다(절대값이 꼭 필요하면 build_demo_dataset.py --anchor 를 직접).
    #  ★수치 근거는 GT 전수 재검수본(eval/finetune/demo/GT_REVIEW_RECOUNT.json).
    #   947 잃어버림 크롭을 전부 육안 판독 → GT 오류·행번호·동형표기 355 를 집계에서 제외.
    #   평가 크롭 45,356 / base 정답 30,726(67.75%).
    #    배수  앵커   품명앵커  판정    실제잃음  되살림   순증      정확도
    #     3    501     40      26/26 ✓  5,764   4,433   -1,331   64.81%  (구형 비균형 구성)
    #     3    501    302      26/26 ✓  2,329   5,803   +3,474   75.40%  ★품명 위주 구성
    #     6   1002    601      26/26 ✓  1,142   6,790   +5,648   80.20%  ★총량 2배
    #    12   2004   1204      26/26 ✓    593   7,608   +7,015   83.21%  ★총량 최적점
    #    24   4008   2409      26/26 ✓    691   7,938   +7,247   83.72%  ✗잃어버림 반등 → 총량축 종료
    #    12   2004   1603      26/26 ✓    760   7,640   +6,880   82.91%  ✗품명0.8 기각
    #    12   2004   1204      26/26 ✓    778   7,494   +6,716   82.55%  ✗품명 성분층화 기각
    #    12   2004   1204      26/26 ✓    718   7,560   +6,842   82.83%  ★v5 동일설정 재실행(v9) → 변동 +125 실측
    #  공정한 곡선은 균형 앵커가 적용된 3배(260804_1439)→6배→12배 셋이다.
    #  12배 실제 잃음 593 의 정체: 편집거리 1 단일 글자 오류가 92%.
    #  ★총량 축 종료(2026-08-05). 24배는 순증만 +232 이고 잃어버림이 반등 → 12배 복귀.
    #  ★거시 비율 축도 종료(2026-08-06). 품명 0.8(v7) 은 593→760 으로 악화.
    #   원인 5분할: 숫자 +79 · 기호 +47 · 영문 +37 · 한글 +4. 품명 앵커를 33% 늘렸는데
    #   한글이 꿈쩍 안 한 게 핵심 — 품명 크롭이 깨지는 건 한글이 아니라 그 안의
    #   숫자·영문·기호이고, 그 방어는 <타 컬럼 크롭>에서 오고 있었다(수량·단가·금액이
    #   10/250/mg/ML/(/)/- 같은 문자 패턴을 학습시킨다). "품명만 평가한다" 와
    #   "품명 앵커만 넣으면 된다" 는 다른 얘기다. 원칙은 <품명 문자열을 구성하는
    #   문자 클래스 분포를 지킨다> 이지 출처 컬럼 비율이 아니다.
    #  ★그리고 v7 은 단일 변수 실험이 아니었다: item-ratio 만 올렸는데 leftover 슬롯이
    #   402→1 로 줄면서 순수 짧은숫자가 513→420 으로 같이 빠졌다(3중 개입). 그래서
    #   지금은 비율이 아니라 --anchor-plan 으로 <버킷별 장수>를 못박는다.
    #
    #  ▼ v8(성분 층화)도 기각. 품명 내부를 √(모수×v5잃음) 가중으로 배분했으나 778.
    #   원인 5분할이 <다섯 층 전부> 악화(한글 +57·영문 +55·기호 +48·숫자 +18·㈜ +7)했고,
    #   앵커를 늘린 HENS(+49장)도 잃음이 +71 늘어 배정 방향과 결과가 어긋났다.
    #   결정적으로 앵커가 <완전히 동일한> HNS(87→87)도 +25 움직였다.
    #
    #  ★★재현성 측정(v9, 2026-08-06) 결과: 같은 설정·같은 학습셋인데 593→718 (+125).
    #   사전 판정선 "700 이상 = 변동 큼" 에 걸렸다 → 배분 실험 4회(24배/품명0.8/층화)의
    #   기각 판정은 전부 <보류>. 차이(98~186)가 재실행 변동(+125)과 같은 자릿수라
    #   설정 효과와 실행 변동이 분리되지 않는다. 채택본은 여전히 v5(593) — 좋은 산출물이지
    #   "최적 비율의 증거"로는 더 쓰지 않는다.
    #   손실 집합 대조: v5 잃음 573 중 네 모델 공통 코어 269(46.9%)뿐, 나머지는 매번 바뀜.
    #
    #  ▼ 현재 단계 = 결정성 확보 후 A/A 통과 (스크립트 최상단 FLAGS_* 주석 참조).
    #   시드(1024)는 이미 고정이었으므로 변동 원인은 GPU 비결정성 → cuDNN 플래그로 잠근다.
    #   절차: ① 동결 번들(--dataset-from=versions/run_260806_1127/dataset)로 D1·D2 실행
    #         ② 성공 기준 = 입력 해시·시작 가중치 해시·개별 예측(45,356) 전부 동일
    #            (demo_aa_compare.py 로 대조. 점수만 비슷한 건 성공이 아니다)
    #         ③ 같으면: 이후 실험은 같은 시드 1회 비교로 판정. 결정적 v5 1회 vs 층화 1회.
    #            다르면: num_workers=0 로 재시도 → 그래도 다르면 B 실패, n회 반복 방식 전환.
    #   v7 은 재실행하지 않는다(3중 개입 설계라 결정성이 있어도 인과 분해 불가).
    #  ★A/A 1차(D1=260806_1224 / D2=260806_1302, cudnn 플래그 ON) 결과 = 실패(2026-08-06):
    #   입력·시작가중치 해시는 동일했으나 pdparams 해시가 다르고 개별 예측 diff 1,943.
    #   단, 집계는 수렴: 정답 수 37,418 로 <완전 동일>, 잃음 693 vs 649(Δ44 — 플래그 전
    #   v5↔v9 의 Δ125 보다 좁음. 각 1쌍이라 통계적 결론은 아님).
    #   → 손잡이 ②: --workers=0 으로 D3·D4. 워커 프로세스 차원을 통째로 제거한 재검증.
    #     그래도 diff>0 이면 완전 결정성은 포기하고, <Δ44 수준의 좁아진 밴드> 를 전제로
    #     n회 반복(밴드) 방식으로 전환한다.
    #  ★판정이 26/26 아래로 떨어지면 앵커가 타깃을 묻은 것 = 그 직전 배수가 상한선.
    DEMO_ANCHOR_RATIO=12.0       # 앵커 총량 = 타깃 크롭 × 이 배수 (167 × 12 = 2,004)
    DEMO_ANCHOR_ITEM=0.60        # v5 원본값. 무작위 추출(성분 층화 없음)
    DEMO_ANCHOR_SHORTNUM=0.20    # v5 원본값
    # ★--anchor-plan 은 쓰지 않는다. v5 는 leftover 402 슬롯이 item 2 / 짧은숫자 98 /
    #  타컬럼 302 로 흩어져 채워진 구성이라, 그 경로를 그대로 타야 재현이 성립한다.
    DEMO_ANCHOR_ARGS="--anchor-ratio $DEMO_ANCHOR_RATIO"
    DEMO_ANCHOR_ARGS="$DEMO_ANCHOR_ARGS --anchor-item-ratio $DEMO_ANCHOR_ITEM"
    DEMO_ANCHOR_ARGS="$DEMO_ANCHOR_ARGS --anchor-shortnum-ratio $DEMO_ANCHOR_SHORTNUM"
    if [ -n "$DATASET_FROM" ]; then
      # ★동결 번들(A/A 용): 데이터셋을 다시 만들지 않고 이전 run 의 보존본을 그대로 쓴다.
      #  재현성 측정에서 "빌드가 byte 단위로 같았나"라는 변수 자체를 제거한다.
      #  사용: --dataset-from=eval/finetune/versions/run_260806_1127/dataset
      echo "[데모] 동결 데이터셋 사용(빌드 생략): $DATASET_FROM"
      for _f in train.txt val.txt test.txt manifest.json; do
        cp "$DATASET_FROM/$_f" eval/finetune_corpus/dataset/ \
          || { echo "★동결 번들에 $_f 가 없습니다: $DATASET_FROM"; exit 1; }
      done
      [ -f "$DATASET_FROM/dict.txt" ] && cp "$DATASET_FROM/dict.txt" eval/finetune_corpus/dict.txt
    else
      python eval/build_demo_dataset.py --targets "$TARGETS" \
          --replay-sources "$REPLAY_SRC" $DEMO_ANCHOR_ARGS
    fi
    if [ -n "$WORKERS" ]; then
      # ★A/A 손잡이 ②: DataLoader 워커 수 고정. cudnn 플래그만으로는 D1/D2 가 갈라져서
      #  (예측 diff 1,943 · pdparams 상이) 워커 프로세스 차원을 통째로 제거해 재검증한다.
      #  PaddleX 는 temp config 를 venv 안 원본 yaml 에서 생성하므로 그 원본을 patch 한다.
      #  ⚠️venv 파일이라 영구적이다 — 되돌리기: --workers=8 (원래 train 8 / eval 4).
      _Y1=".venv/lib/python3.12/site-packages/paddlex/repo_apis/PaddleOCR_api/configs/korean_PP-OCRv5_mobile_rec.yaml"
      _Y2=".venv/lib/python3.12/site-packages/paddlex/repo_manager/repos/PaddleOCR/configs/rec/PP-OCRv5/multi_language/korean_PP-OCRv5_mobile_rec.yml"
      sed -i "s/num_workers: [0-9]*/num_workers: $WORKERS/" "$_Y1" "$_Y2"
      echo "[데모] DataLoader num_workers=$WORKERS 고정 (venv 패치):"
      grep -n "num_workers" "$_Y1" | sed "s/^/    /"
    fi
    # ★에폭 = "같은 타깃 크롭을 몇 번 보여주나". 기본 20 — 앵커 500 + 타깃 167 = 667줄
    #  기준 약 200스텝이고, 실측에서 정점(best)이 13에폭이라 20이면 충분히 여유가 있다.
    #  매 에폭 검증 → best_accuracy 자동 선택이므로 정점을 지나쳐도 손해는 시간뿐.
    #  안 붙으면 에폭이 아니라 lr(3e-5→1e-4)을 올린다 — 같은 크롭 반복만 늘리는 건
    #  학습이 아니라 암기 쪽으로 간다.
    DEMO_EPOCHS=$DEMO_EPOCHS_ARG
    # ★에폭 궤적 실험(opt-in): 서로 다른 ep8/ep20 run 은 GPU 비결정성이 섞이므로,
    #  한 번의 20ep 학습에서 ep8·12·20 을 저장해 같은 궤적 안의 이동만 비교한다.
    #    bash ~/OCR/run-finetune.sh --round=demo --targets="..." --epoch-ladder
    #  기본은 예전처럼 중간 저장을 끈다. 실험 때만 save_interval=4 로 4·8·12·16·20을
    #  만들고, 학습 뒤 정확한 ep8·12·20 가중치를 별도 export/판정/전수스캔한다.
    DEMO_EPOCH_POINTS="8 12 20"
    if [ "$EPOCH_LADDER" = "1" ]; then
      if [ "$DEMO_EPOCHS" -ne 20 ]; then
        echo "★에폭 궤적 실험은 동일 20ep 궤적의 8·12·20 비교입니다: DEMO_EPOCHS=$DEMO_EPOCHS"
        exit 1
      fi
      DEMO_SAVE_INTERVAL=4
      echo "[에폭 궤적] 활성화: points=[$DEMO_EPOCH_POINTS] save_interval=$DEMO_SAVE_INTERVAL"
    else
      # config 기본 1 이면 316MB×에폭수를 남긴다. 보통 run 은 best_accuracy 만 보존한다.
      DEMO_SAVE_INTERVAL=$DEMO_EPOCHS
    fi
    TRAIN_OVERRIDE="$TRAIN_OVERRIDE -o Train.epochs_iters=$DEMO_EPOCHS"
    TRAIN_OVERRIDE="$TRAIN_OVERRIDE -o Train.save_interval=$DEMO_SAVE_INTERVAL"
    # ★학습 입력 증거 보존 — train.txt 는 학습에 소비돼 사라진다.
    #  2026-08-06 실제 사고: v5 의 표본이 남아 있지 않아 "v8 은 v5 대비 품명 내부만
    #  바뀌었다" 를 코드 구조로만 주장할 수 있고 실측으로는 못 보였다. manifest 는
    #  <몇 장씩>만 말해주지 <어느 크롭이었나>는 말해주지 않는다.
    #  시드·풀 고정이라 재현은 되지만 코퍼스가 바뀌면 그 재현도 깨지므로 원본 해시도 같이 남긴다.
    #  ★반드시 학습 <전>에 떠야 한다(여기가 그 자리). 데모 라운드 train.txt 는 ~150KB.
    _EV="eval/finetune/versions/run_${RUN_TAG}/dataset"
    mkdir -p "$_EV"
    for _f in dataset/train.txt dataset/val.txt dataset/test.txt dataset/manifest.json dict.txt; do
      cp "eval/finetune_corpus/$_f" "$_EV/" 2>/dev/null || true
    done
    {
      echo "run_tag=$RUN_TAG"
      echo "round=$ROUND  step=$DEMO_N"
      echo "targets=$TARGETS"
      echo "anchor_args=$DEMO_ANCHOR_ARGS"
      echo "dataset_from=${DATASET_FROM:-'(새로 빌드)'}"
      echo "workers=${WORKERS:-'(기본 train8/eval4)'}"
      echo "epochs=$DEMO_EPOCHS"
      echo "epoch_ladder=$EPOCH_LADDER  points=$DEMO_EPOCH_POINTS  save_interval=$DEMO_SAVE_INTERVAL"
      echo "train_override=$TRAIN_OVERRIDE"
      echo "git_commit=$(git rev-parse HEAD 2>/dev/null || echo unknown)"
      echo "flags=cudnn_deterministic=$FLAGS_cudnn_deterministic exhaustive_search=$FLAGS_cudnn_exhaustive_search pythonhashseed=$PYTHONHASHSEED"
      echo "versions=$(python -c "import paddle;print('paddle',paddle.__version__,'cuda',paddle.version.cuda(),'cudnn',paddle.version.cudnn())" 2>/dev/null || echo unknown)"
    } > "$_EV/run_args.txt"
    ( cd "$_EV" && sha256sum ./* > SHA256SUMS 2>/dev/null ) || true
    ( cd eval/finetune_corpus && sha256sum labels.txt labels_correct.txt \
        labels_correct.meta.jsonl replay_sources.txt 2>/dev/null ) >> "$_EV/SHA256SUMS" || true
    # 시작 가중치 해시 — A/A 는 <같은 출발점>이어야 성립한다. 1단계면 official 사전학습
    # 캐시, 2단계 이상이면 직전 통과본의 pdparams 를 남긴다.
    if [ "$DEMO_N" -ge 2 ]; then
      sha256sum "$DEMO_PREV/best_accuracy.pdparams" >> "$_EV/SHA256SUMS" 2>/dev/null || true
    else
      _PW=$(find ~/.paddlex -name "korean_PP-OCRv5_mobile_rec_pretrained.pdparams" 2>/dev/null | head -1)
      if [ -n "$_PW" ]; then sha256sum "$_PW" >> "$_EV/SHA256SUMS" || true
      else echo "# start-weights cache not found (URL download at train time)" >> "$_EV/SHA256SUMS"; fi
    fi
    if [ "$EPOCH_LADDER" = "1" ]; then
      # output/ 에 과거 iter_epoch_* 가 남아 있어도 이번 run 산출물로 오인하지 않게 하는 경계.
      touch "$_EV/epoch_ladder.started"
    fi
    echo "[증거] 학습 입력 보존 → $_EV ($(ls "$_EV" | wc -l) 파일)"
    FT_CRITERIA="소생 데모 ${DEMO_ROUND}회차 ${DEMO_STEP}단계: 타깃[$TARGETS] held-out 동일품명 재현"
  elif [ "$ROUND" = "numeric" ]; then
    # ★★숫자 라운드 (2026-07-24): 숫자(금액/수량/단가) 인식↑ + 품명 유지~개선.
    #  1차(품명)에서 배운 교훈 = 반대편 앵커가 작으면(13%) 그쪽이 −18.8%p 날아감 →
    #  이번엔 품명(한글) 앵커를 충분히 넣어 방금 얻은 품명 +11.3%p 보존. 단 숫자가 다수(target)여야
    #  숫자가 오르므로 품명은 과반은 안 되게: balance-ratio 1.0(숫자=failure×2) + hangul-anchor 1.5
    #  → 대략 숫자 ~57% / 품명 ~43%. (품명 깎이면 앵커↑, 숫자 안 오르면 앵커↓ — 게이트로 튜닝)
    #  - failure(숫자 전체): 금액계열 + itemCode·사업자번호·제조번호·lotNo. 날짜·buyer번호 제외
    #    (라벨 형식 불확실: 날짜=구분자없는 GT, buyer번호=혼재). ★핵심 --reconstruct-number-labels:
    #    금액계열 GT(819800)를 인쇄형(819,800)으로 재구성 = 콤마붕괴(매번 실패 원인) 근본 차단.
    #    itemCode/사업자번호 등은 GT가 이미 인쇄형(평문·하이픈)이라 그대로.
    #  ★반드시 --from-adopted 와 함께: 품명v1 을 이어받아 그 위에 숫자를 얹어야 품명이 살아있음.
    #  ⚠️ 확인: itemCode(38만)·제조번호(12만)가 크므로 '학습셋 구성' 로그로 숫자 다수·품명 보존
    #    확인. 금액계열만 집중하고 싶으면 --columns 를 금액계열로 좁히면 됨.
    python eval/build_dataset.py --balance-ratio 1.0 --max-train 1000000 \
        --columns amount,unitPrice,quantity,supplyAmount,taxAmount,totalAmount,discountAmount,itemCode,supplierBizNumber,manufacturingNo,lotNo \
        --min-match 0.7 --raw-only --reconstruct-number-labels \
        --balance-digit-min 1 --hangul-anchor-ratio 1.5 \
        --exclude-sources "$REPLAY_SRC"
    FT_CRITERIA="숫자 전체(금액계열 콤마재구성 + itemCode/사업자/제조번호) + 품명 보존 앵커 1.5"
  else
    # ★★한글(품명) 라운드 — failure=한글 다양성필드(itemName+supplier), balance=한글, 숫자앵커 소량.
    #  buyer 제외(반복만)·itemNameMaster 제외(rewrite). 1차 net +2,835·품명 +11.3%p 채택본.
    python eval/build_dataset.py --balance-ratio 1.0 --max-train 1000000 \
        --columns itemName,supplierCompany,supplierAddress \
        --min-match 0.7 --hangul-min 2 --raw-only \
        --balance-hangul-min 1 --number-anchor-ratio 0.3 \
        --exclude-sources "$REPLAY_SRC"
    FT_CRITERIA="품명·공급자명·주소 중심 + 숫자 보존 앵커 0.3 + 한글2자+ + 인쇄형 라벨"
  fi
  # [label-gate]·[학습셋 구성] 로그 확인: 타깃 글자종류가 주도해야 정상(품명=한글↑ / 숫자=숫자↑).
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
  # 원본 학습 로그를 run별로 따로 보존해야 최고 epoch를 정확히 복원할 수 있다.
  python "$DRV" -c "$CFG" -o Global.mode=train $TRAIN_OVERRIDE 2>&1 \
    | tee "$TRAIN_LOG" | python eval/finetune_progress.py
  echo "[5/6] export (서버가 읽는 inference 형식으로 변환)"
  python "$DRV" -c "$CFG" -o Global.mode=export
  # ★run별 모델 자동 보존: output/ 은 다음 run 이 덮어쓰므로(probe1 모델 소실 사고),
  #  best 를 versions/run_<tag>/ 에 복사(~30MB, versions/ 는 gitignore). 채택과 무관하게 항상.
  echo "[모델 보존] eval/finetune/versions/run_${RUN_TAG}/best_accuracy"
  mkdir -p "eval/finetune/versions/run_${RUN_TAG}"
  cp -r eval/finetune/output/best_accuracy "eval/finetune/versions/run_${RUN_TAG}/" 2>/dev/null \
    || echo "  (best_accuracy 복사 실패 — output 확인)"
  # 산출 모델 해시 — A/A 최종 판정용("개별 예측 동일"의 상위 증거). 증거 폴더가 있을 때만.
  if [ -d "eval/finetune/versions/run_${RUN_TAG}/dataset" ]; then
    ( cd "eval/finetune/versions/run_${RUN_TAG}" \
      && sha256sum best_accuracy/best_accuracy.pdparams >> dataset/SHA256SUMS 2>/dev/null ) || true
  fi
  echo "[6/6] 인식 비교 리포트 (base vs 파인튜닝, held-out test 크롭 직접)"
  python eval/finetune_report.py --run-tag "$RUN_TAG" || echo "  (리포트 생성 실패 — 로그 확인)"
  python eval/finetune_report_by_type.py || echo "  (타입별 리포트 생성 실패 — 로그 확인)"
  if [ "$ROUND" = "demo" ]; then
    # ★소생 데모 판정 리포트 — 처음 보는 사람용(기준 문서수·컬럼·선정근거·크롭별 판정·누적 현황).
    #  재료는 방금 [6/6] 이 남긴 FINETUNE_PREDICTIONS.jsonl — 추가 GPU 작업 없음.
    echo "[데모 리포트] 소생 판정 리포트 (eval/finetune/demo/<NNN>_${RUN_TAG}/)"
    python eval/demo_report.py --run-tag "$RUN_TAG" $DEMO_CMP_ARGS \
      || echo "  (데모 리포트 실패 - 수동: python eval/demo_report.py --run-tag $RUN_TAG)"
    # ★★판정 먼저, 저장은 통과했을 때만.
    #  실패한 모델이 step<N>/ 에 박히면 다음 단계가 실패본 위에서 출발해버린다.
    #  실패면 저장하지 않으므로 시작 모델(=직전 단계 모델)이 그대로 유지되고, 같은 단계를
    #  조건 바꿔 다시 돌리면 된다(그 재시도는 '${DEMO_N}-1 모델'로 이력에 카운트).
    DEMO_OUT=$(ls -d eval/finetune/demo/[0-9][0-9][0-9]_"${RUN_TAG}" 2>/dev/null | head -1)
    DEMO_PASS=$(python - "$DEMO_OUT/DEMO_REPORT_${RUN_TAG}.json" <<'PY'
import json, sys
try:
    print("1" if (json.load(open(sys.argv[1], encoding="utf-8"))
                  .get("summary", {}).get("allPass")) else "0")
except Exception:
    print("0")
PY
)
    if [ "$DEMO_PASS" = "1" ]; then
      # ★★타깃 26/26 은 <채택>이 아니라 <후보 자격>이다. 자동 승격하지 않는다.
      #  2026-08-06 사고: v7(품명 0.8)이 26/26 을 넘겨 자동으로 step1 에 박혔는데,
      #  로컬 재집계에서 잃어버림 760(기준 593)으로 기각됐다. 체인이 기각본을 가리킨
      #  채로 남아 있었고, 그 상태로 2단계를 돌렸으면 전 단계가 오염될 뻔했다.
      #  잃어버림은 이 시점에 알 수 없다 — 기준셋 45,356 스캔 + GT 보정
      #  (recount_reviewed_gt.py)까지 끝나야 나오고 그건 로컬 몫이다.
      #  즉 <선택 시점>과 <판정 시점>이 다르므로, 승격은 판정 이후 사람이 한다.
      #  모델 실물은 versions/run_<tag>/ 에 이미 보존돼 있어 언제든 승격할 수 있다.
      _SRC="$PWD/eval/finetune/versions/run_${RUN_TAG}/best_accuracy"
      if [ -f "$_SRC/best_accuracy.pdparams" ] && [ -d "$_SRC/inference" ]; then
        echo "[데모] 타깃 판정 통과 (26/26) — 모델 보존: versions/run_${RUN_TAG}"
        echo "       ★체인은 갱신하지 않았습니다. 로컬에서 잃어버림을 확인하고"
        echo "         (python eval/finetune/demo/check_latest_run.py)"
        echo "         채택이 결정되면 아래를 실행하세요:"
        echo "           ln -sfn \"$_SRC\" $DEMO_MODELS/step${DEMO_N}"
        _CUR=$(readlink "$DEMO_MODELS/step${DEMO_N}" 2>/dev/null || true)
        echo "       현재 step${DEMO_N} = ${_CUR:-(없음)}"
      else
        echo "  ★모델 보존본을 찾지 못했습니다: $_SRC"
      fi
    else
      echo "[데모] ★판정 실패 → 체인에 넣지 않습니다(step${DEMO_N}/ 미갱신)."
      echo "       시작 모델은 그대로이니, 조건(에폭·크롭 수)을 바꿔 같은 --targets 로 재실행하세요."
      echo "       (재시도는 '${DEMO_N}-1 모델'로 실행 이력에 남습니다)"
    fi

    # ★한 궤적 에폭 사다리: exact checkpoint 를 각각 격리 export 하고,
    #  ①타깃 held-out 판정 ②기준 45,617장 전수 스캔을 남긴다.
    #  best_accuracy 는 target-val 20장 기준이라 '잃어버림 최소' 체크포인트가 아니다.
    if [ "$EPOCH_LADDER" = "1" ]; then
      _EPOCH_ROOT="eval/finetune/versions/run_${RUN_TAG}/epochs"
      mkdir -p "$_EPOCH_ROOT"
      printf "epoch\tcheckpoint_sha256\ttarget_eval\tscan_tag\n" > "$_EPOCH_ROOT/EPOCH_LADDER.tsv"
      _LADDER_OK=1
      _LADDER_MARKER="eval/finetune/versions/run_${RUN_TAG}/dataset/epoch_ladder.started"
      for _EP in $DEMO_EPOCH_POINTS; do
        _EP2=$(printf "%02d" "$_EP")
        _CKPT_DIR=$(find eval/finetune/output -maxdepth 1 -type d \
          \( -name "iter_epoch_${_EP}" -o -name "epoch_${_EP}" \) -print -quit)
        if [ -z "$_CKPT_DIR" ]; then
          echo "★epoch ${_EP} 체크포인트 디렉터리가 없습니다 (save_interval 확인)"
          _LADDER_OK=0
          continue
        fi
        _PDP=$(find "$_CKPT_DIR" -maxdepth 1 -type f -name "*.pdparams" -print -quit)
        if [ -z "$_PDP" ]; then
          echo "★epoch ${_EP} pdparams 가 없습니다: $_CKPT_DIR"
          _LADDER_OK=0
          continue
        fi
        if [ ! "$_PDP" -nt "$_LADDER_MARKER" ]; then
          echo "★epoch ${_EP} 체크포인트가 이번 run 보다 오래됐습니다: $_PDP"
          _LADDER_OK=0
          continue
        fi

        _EPOCH_DIR="$_EPOCH_ROOT/epoch_${_EP2}"
        _INF="$_EPOCH_DIR/inference"
        mkdir -p "$_EPOCH_DIR"
        _ARCHIVED_PDP="$_EPOCH_DIR/epoch_${_EP2}.pdparams"
        cp "$_PDP" "$_ARCHIVED_PDP"
        for _SMALL in "$_CKPT_DIR"/*.states "$_CKPT_DIR"/*.json "$_CKPT_DIR"/config.yaml; do
          if [ -f "$_SMALL" ]; then cp "$_SMALL" "$_EPOCH_DIR/"; fi
        done
        sha256sum "$_ARCHIVED_PDP" > "$_EPOCH_DIR/SHA256SUMS"

        echo "[에폭 궤적] epoch ${_EP}: exact weight export → $_INF"
        if ! python "$DRV" -c "$CFG" -o Global.mode=export \
             -o Export.weight_path="$_ARCHIVED_PDP" -o Global.output="$_INF"; then
          echo "★epoch ${_EP} export 실패"
          _LADDER_OK=0
          continue
        fi
        if [ -z "$(find "$_INF" -type f -print -quit)" ]; then
          echo "★epoch ${_EP} inference 산출물이 비어 있습니다: $_INF"
          _LADDER_OK=0
          continue
        fi

        _TARGET_JSON="$_EPOCH_DIR/TARGET_EVAL.json"
        _TARGET_PASS=1
        python eval/demo_checkpoint_eval.py --model-dir "$_INF" \
          --output "$_TARGET_JSON" --tag "${RUN_TAG}_ep${_EP2}" || _TARGET_PASS=0

        # ep20 은 기존 도구(check_latest_run 등)가 run tag 로 찾을 수 있게 본 이름을 쓴다.
        # ep8/12 만 suffix 를 붙여 한 궤적의 중간점임을 명시한다.
        if [ "$_EP" -eq "$DEMO_EPOCHS" ]; then
          _SCAN_TAG="$RUN_TAG"
        else
          _SCAN_TAG="${RUN_TAG}_ep${_EP2}"
        fi
        if [ "$DEMO_SCAN" = "1" ]; then
          echo "[에폭 궤적] epoch ${_EP}: 기준셋 전수 스캔 → ${_SCAN_TAG}.jsonl"
          if ! python -u eval/demo_next_target.py --run-tag "$RUN_TAG" \
               --scan-tag "$_SCAN_TAG" --model-dir "$_INF" --scan-only; then
            echo "★epoch ${_EP} 전수 스캔 실패"
            _LADDER_OK=0
          fi
        else
          _SCAN_TAG="(DEMO_SCAN=0)"
        fi
        _PDP_SHA=$(sha256sum "$_ARCHIVED_PDP" | awk '{print $1}')
        printf "%s\t%s\t%s\t%s\n" "$_EP" "$_PDP_SHA" "$_TARGET_PASS" "$_SCAN_TAG" \
          >> "$_EPOCH_ROOT/EPOCH_LADDER.tsv"
      done
      DEMO_EPOCH_LADDER_DONE=1

      # 판정·스캔이 모두 끝난 뒤에만 큰 optimizer 포함 원본 checkpoint 를 정리한다.
      # 기본 0은 보수적으로 유지. 디스크가 빠듯한 AWS 실행에서만 명시적으로 1을 준다.
      if [ "$EPOCH_CLEANUP" = "1" ] && [ "$_LADDER_OK" = "1" ]; then
        echo "[에폭 궤적] archive/export/scan 완료 — output 중간 체크포인트 정리"
        for _EP in 4 8 12 16 20; do
          _DROP=$(realpath -m "eval/finetune/output/iter_epoch_${_EP}")
          case "$_DROP" in
            "$PWD"/eval/finetune/output/iter_epoch_*)
              [ -d "$_DROP" ] && rm -rf -- "$_DROP"
              ;;
            *) echo "★정리 경로가 output 밖이라 건너뜀: $_DROP" ;;
          esac
        done
      elif [ "$EPOCH_CLEANUP" = "1" ]; then
        echo "★에폭 산출물 일부가 실패해 원본 체크포인트를 정리하지 않았습니다"
      fi
      echo "[에폭 궤적] 인덱스: $_EPOCH_ROOT/EPOCH_LADDER.tsv"
    fi
  fi
  if [ "$ROUND" = "demo" ]; then
    # ★다음 타깃 스캔(기준셋 품명 크롭 ~9만 장 판독, 20분 안팎)은 기본으로 이어서 돌린다.
    #  통과하면 어차피 다음 단계 타깃이 필요하고, 실패하면 아래 조건에서 자동으로 건너뛰므로
    #  낭비가 없다. 판정만 보고 싶으면 --no-scan 으로 끈다.
    #  (스캔은 반드시 판정 통과 run 에서만 — 실패 모델 판독이 demo/scans/ 에 남으면
    #   다음 단계가 그걸 '직전 모델'로 잘못 대조한다.)
    if [ "${DEMO_EPOCH_LADDER_DONE:-0}" = "1" ]; then
      echo "[다음 타깃 스캔] 에폭 궤적의 exact checkpoint 스캔으로 대체했습니다"
    elif [ "$DEMO_PASS" = "1" ] && [ "$DEMO_SCAN" = "1" ]; then
      echo "[다음 타깃 스캔] 기준셋 품명 크롭 판독 → 잃어버린 품명 / 못 읽는 품명 후보"
      # 대조 상대 = 이 run 의 <시작 모델> 스캔. 파일명 순서로 고르면 안 된다 -
      # 재시도(1-1-v2, v3...)는 서로 형제라 직전 시도가 부모가 아니다(둘 다 base 출발).
      # 1단계면 base 기준선, 그 외에는 step<N-1> 심링크가 가리키는 run 의 스캔.
      if [ "$DEMO_N" -le 1 ]; then
        _PREV_SCAN="eval/finetune/demo/scans/000_base.jsonl"
      else
        _PREV_TAG=$(readlink "$DEMO_MODELS/step$((DEMO_N - 1))" 2>/dev/null | sed -E 's#.*/versions/run_([^/]+)/.*#\1#')
        _PREV_SCAN="eval/finetune/demo/scans/${_PREV_TAG}.jsonl"
      fi
      if [ -f "$_PREV_SCAN" ]; then
        echo "  대조 상대(시작 모델): $_PREV_SCAN"
        _PREV_ARG="--prev-scan $_PREV_SCAN"
      else
        echo "  ★시작 모델 스캔이 없습니다: $_PREV_SCAN (대조 없이 진행)"
        _PREV_ARG=""
      fi
      # -u : 진행률 로그가 버퍼에 갇히지 않고 바로 보이게(20분짜리라 무소식이면 불안하다).
      python -u eval/demo_next_target.py --run-tag "$RUN_TAG" --exclude "$TARGETS" $_PREV_ARG \
        || echo "  (타깃 스캔 실패 - 수동: python eval/demo_next_target.py --run-tag $RUN_TAG)"
    elif [ "$DEMO_PASS" = "1" ]; then
      echo "[다음 타깃 스캔] --no-scan 으로 껐습니다. 나중에 돌리려면:"
      echo "  python eval/demo_next_target.py --run-tag $RUN_TAG --exclude \"$TARGETS\""
    else
      echo "[다음 타깃 스캔] 건너뜀 - 판정 실패 모델은 체인/스캔에 넣지 않습니다"
    fi
    echo "==================== 파인튜닝 끝 [$(date +'%F %T')] ===================="
    echo "★★소생 데모 리포트(이번 단계): ${DEMO_OUT:-eval/finetune/demo}/DEMO_REPORT_${RUN_TAG}.html"
    echo "★★회차 종합(회사 제출용): eval/finetune/demo/DEMO_SUMMARY.html"
    echo "★다음 타깃 후보: ${DEMO_OUT:-eval/finetune/demo}/NEXT_TARGETS.json"
    _summary_args=(--ts "$RUN_TAG" --base "$BASE_TAG" --elapsed "$((SECONDS - _FT_START))" \
      --log "$TRAIN_LOG" --config "$CFG" --criteria "$FT_CRITERIA")
    python eval/finetune_run_summary.py "${_summary_args[@]}" || true
    # ★종합본은 RUN_HISTORY 기록 뒤에 생성한다 - 학습(에폭·acc)·AWS 비용 열을 그 파일에서
    #  읽어오기 때문. 먼저 만들면 이번 run 기록이 아직 없어 두 열이 비어 나온다.
    echo "[종합] 회차 탭 리포트 갱신"
    python eval/demo_summary.py \
      || echo "  (종합 리포트 실패 - 수동: python eval/demo_summary.py)"
    exit 0
  fi
  # ★판정용 3탭 벤치(처음/유지/포함) 자동 생성 — 학습 직후 별도 수동실행 없이 바로 판정.
  #  순서 중요: build_ft_bench 가 방금 갱신된 train.txt 로 포함(SEEN)/유지(RETAIN)를 재빌드
  #  한 뒤 채점해야 "이 run 이 실제 학습한 것" 기준이 맞는다. (~70분, 362k 크롭×2모델)
  echo "[벤치] 고정 벤치 재빌드 + 3탭 벤치 리포트 (판정용)"
  python eval/build_ft_bench.py || echo "  (벤치 빌드 실패 — 수동: python eval/build_ft_bench.py)"
  python eval/finetune_report.py --bench --run-tag "$RUN_TAG" \
    || echo "  (벤치 리포트 실패 — 수동: python eval/finetune_report.py --bench --run-tag $RUN_TAG)"
  echo "==================== 파인튜닝 끝 [$(date +'%F %T')] ===================="
  echo "best 가중치: eval/finetune/output/best_accuracy/"
  echo "★run 아카이브(git 제외, scp 반출): eval/finetune/reports/${RUN_TAG}/"
  echo "★판정 리포트(벤치 3탭): eval/finetune/reports/${RUN_TAG}/FINETUNE_BENCH_${RUN_TAG}.html"
  echo "최신 포인터: eval/finetune/FINETUNE_BENCH.html · FINETUNE_REPORT.html"
  if [ "$ROUND" = "demo" ]; then
    echo "★★소생 데모 리포트(이번 차수): eval/finetune/demo/<NNN>_${RUN_TAG}/"
    echo "★★차수 종합(회사 제출용, 요약·1차~4차 탭): eval/finetune/demo/DEMO_SUMMARY.html"
  fi
  echo "--- 채택하려면(게이트 통과 시): 트리 줄기로 승격 + main.py 반영 ---"
  echo "  python eval/finetune_adopt.py --version v6      # 부모=직전 채택본(없으면 official)"
  echo "  이후 이어받아 학습: bash ~/OCR/run-finetune.sh --from-adopted"
  # 실행 이력: 실제 완료/최고 epoch, 학습 기준, 전체·품명·숫자 증감, AWS 예상요금.
  _summary_args=(--ts "$RUN_TAG" --base "$BASE_TAG" --elapsed "$((SECONDS - _FT_START))" \
    --log "$TRAIN_LOG" --config "$CFG")
  if [ -n "${FT_CRITERIA:-}" ]; then
    _summary_args+=(--criteria "$FT_CRITERIA")
  fi
  python eval/finetune_run_summary.py "${_summary_args[@]}" || true
} 2>&1 | stdbuf -oL -eL tee -a ~/OCR/logs/finetune.log
