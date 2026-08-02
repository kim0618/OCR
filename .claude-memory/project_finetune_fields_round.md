---
name: project_finetune_fields_round
description: "FT 4차 fields 프로브 STOP(2026-07-26) — 바코드 제거로도 쉬운숫자 회복 실패(vs V1 숫자 −7·한글 −5.3), '바코드=유일한 독' 반증. V1 실측 확정(품명+12.0/쉬운숫자−18.7/수량−26.8/금액+2.7). same-crop 직접비교=판정 표준. 다음=lr 재프로브 or V1 확정"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2e1f577d-86f6-46fb-9df5-0322285bdea5
  modified: 2026-07-26T13:01:23.798Z
---

2026-07-26 세션. FT 트리: official → ✗1차 → ★itemname_V1(채택, 현 프로덕션) → ✗3차 combined(기각 확정) → **✗4차 fields 프로브 STOP(21:55, 아래)**.

## ★★프로브 결과 (run 260726_1820, 1ep, 12,941s, $3.6) — STOP
- **같은 100k 크롭 3자 비교**: 숫자 전체 순정 66.0% / V1 ~53.6%(−12.4) / **프로브 46.6%(−19.4)** = **V1보다 −7pp 더 하락**. 한글기타 V1 +4.4 → 프로브 **−0.9(−5.3)**. 품명 +11.3(유지 ✓). net −8,268(회귀 13,058).
- **V1 vs 순정 직접실측 확정**(COMPARE_OFFICIAL_VS_V1.json, 같은 100k): 품명 **+12.0**·한글 +4.4·**금액 +2.7**·코드날짜 +1.3 / **쉬운숫자(컬럼미상 balance) −18.7(n=37,451)**·수량 **−26.8**(1.9%, 짧은숫자 삭제). 숫자 가중 **−12.4pp**. ※사용자 직관(−18 실재) 적중 — 내 −6.2 역산은 combined 시험셋(바코드 희석) 착시였음.
- **가설 반증**: 바코드(itemCode 274k) 제거로도 쉬운숫자·한글 하락 재현 → 원인 후보 ①**하드 failure 대량학습 자체**(41만 어려운 크롭이 그래디언트 지배) ②**lr 1e-4가 V1 위 미세조정엔 과격**(한글 동반 드리프트가 신호).
- **다음 레버**: A) lr 1e-4→3e-5 재프로브($3.6, 추천) B) balance-ratio↑(하드 희석) C) A+B D) 숫자FT 중단·V1 확정. **프로브(1ep 확인사격→판정→본판) 방식이 $10 낭비 방지 — 이후 라운드 표준.**
- ⚠시험셋 주의: 숫자:기타 버킷=balance 수확 크롭(수확 당시 정답으로 읽힌 것만 선별)이라 **official 점수는 선택편향 상향** → par(0)는 사실상 상한. **판정은 항상 vs V1**로.
- config는 프로브용 epochs_iters=1 상태(백업 .bak_probe_20260726, 본판 시 3으로).

## ★★same-crop 직접비교 방법론 (이 세션의 핵심 교훈)
- **순정-기준 점수 빼기 금지**: V1(-18.8 숫자)과 combined(-7.1 숫자)는 **서로 다른 test 크롭셋**에서 채점됨(7/24 코퍼스 재작업으로 split 변경). 점수 빼면 "+11 숫자회복" 착시 — 같은크롭 직접비교로 반증됨.
- 시험셋이 왜 달라지나: 크롭 파일은 그대로, **라운드별 필터로 뽑힌 풀이 달라지고 그 10%가 test**가 됨. V1 라운드 test 숫자=쉬운 앵커(순정 고득점→망각 다 드러남=−18.8), 현 test 숫자=어려운 failure 포함(순정 34.5%→격차 압축).
- **combined vs V1 (같은 120k, COMPARE_V1_SUBCOL.json)**: 금액 +1.2pp(86:12)·코드날짜 +1.0·품명 +0.3 / **쉬운숫자(컬럼미상) −4.7·한글기타 −4.5 → 전체 net −1,295** = combined 기각이 옳았음.
- **V1 vs 순정 숫자 진짜 격차 ≈ −6.2pp**(간접 역산: −7.1 −(−0.9); 품명 +11.8 검산 일치). **fields 목표 = V1 대비 숫자 +6.2pp(par)**, +18 아님.
- 직접측정 스크립트 `eval/compare_official_vs_v1.py` 실행 중이었으나 서버 종료로 중단 → **재개 시 완주(~20분)하면 −6.2 확정**.

## 학습구성 진단 (combined이 진 이유, 실측)
- combined train 96만 = **itemCode 바코드 failure 274k(29%) + 컬럼미상 구세대 balance 271k(28%) = 57%가 독/낭비**.
- itemCode는 OCR 산출 아님 — **품명→마스터매칭 산출**(top1+가격 87.9%, [[project_master_match_baseline]]) → 학습 불필요. 바코드(880 EAN 13자리) base 정답률 6.6% 하드케이스가 그래디언트 독점 → broad forgetting.
- ★버그 발견: labels_correct.meta.jsonl **338,592행 전부 src 없음** → --exclude-sources 켜면 전량 드랍(기준셋 replay 수확분이라 드랍이 정답이긴 함). 구세대 balance 3.07M은 meta 자체가 없어 컬럼 미상. **백필 불가**: 크롭명=sha1(src::location::gt::bbox), bbox가 snapshots에만 있는데 rekey run(20260720_175949)의 snapshots/processed 삭제됨(7/24 로컬백업).
- 금액 라벨은 문제없음: 콤마재구성 후 100% 보존 실측(column-aware audit). "라벨 오염" 가설 기각.

## fields 라운드 (준비완료, 9항목 재검증 통과)
- run-finetune.sh에 **--round=fields** 추가 = combined에서 **itemCode만 제거**. 백업 `run-finetune.sh.bak_20260726`.
- dataset 검증: train 800k(failure 실필드 414,462 + balance 앵커 385,538), **바코드 0·기준셋 누출 0·garbage 0·금액콤마 100%·크롭실재 샘플 6000/6000**. 루트 test.txt=새 100k로 갱신됨. epochs=4(config).
- **실행(사용자)**: `tmux new -s finetune` → `bash ~/OCR/run-finetune.sh --round=fields --from-adopted` (~13h). adopted=itemname_V1 확인됨.
- **판정**: FINETUNE_REPORT(vs 순정) + `python eval/compare_v1_subcol.py`(같은크롭 vs V1) — 품명 유지 AND 숫자 V1+6pp↑면 채택.
- 기대(정직): 품명 유지 확신 높음, 숫자 −6.2 대부분 회복 기대, par 초과는 측정으로만 확인.

## 서버 스크립트 (이 세션 추가, eval/)
compare_combined_vs_v1.py · compare_v1_subcol.py(판정용 메인) · compare_official_vs_v1.py(미완주) · audit_numeric_labels.py(조잡-폐기) · audit_money_by_column.py · audit_train_columns.py · verify_fields_dataset.py. 전부 read-only 진단.

## 재개 체크리스트
1. EC2 시작 → SSH(키=Desktop/mysuit-ocr.pem, ubuntu@3.37.51.240)
2. (선택) compare_official_vs_v1.py 완주 → V1 격차 확정
3. FT 실행(사용자, 위 명령) → label-gate(공백 35.6%·괄호 26.6% 근방이면 정상) → ~13h
4. 판정 후 채택 시: finetune_adopt.py --version fields_V1 (부모=itemname_V1)
5. pgrep 자기매칭 주의: `pgrep -f "[c]ompare_..."` 패턴 사용

[[project_finetune_tree_rounds]] [[project_master_match_baseline]] [[project_invoice_numeric_rules_p1p2p3]]
