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
for a in "$@"; do case "$a" in --round=*) ROUND="${a#*=}" ;; --numeric) ROUND=numeric ;; esac; done

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
  echo "[6/6] 인식 비교 리포트 (base vs 파인튜닝, held-out test 크롭 직접)"
  python eval/finetune_report.py --run-tag "$RUN_TAG" || echo "  (리포트 생성 실패 — 로그 확인)"
  python eval/finetune_report_by_type.py || echo "  (타입별 리포트 생성 실패 — 로그 확인)"
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
