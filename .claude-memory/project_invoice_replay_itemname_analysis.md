---
name: project_invoice_replay_itemname_analysis
description: "067 replay(9,001 held-out) 품명+learndata 심층 검증 실측(2026-07-23). 검증된 룰 재정렬: ①괄호주석 중립화 master +3.55pp ②learndata spec-unit +935 ③선두코드 strip +999. ★꼬리pack strip 기각(net-6907). learndata A net+1045 실체."
metadata: 
  node_type: memory
  type: project
  originSessionId: def30f43-03bf-46ac-aaeb-c44baf2c47d9
  modified: 2026-07-23T00:46:28.739Z
---

2026-07-23. [[project_replay_set_and_learndata_plan]] P3/P4 = 067 replay(9,001 held-out) 품명·learndata **심층 검증(추측 아닌 전수 실측)**. 결함 53,093 전수분해 후 **룰 우선순위 재정렬**(이전 blob 1순위 가설을 실측이 뒤집음).

## 067 헤드라인 (LOCAL_SUMMARY_replay_compare)
- 필드 58.7% / 셀 50.8%. 품명 raw(itemName) **37.2%**, master(itemNameMaster) **65.5%**, itemCode base 59.2%.
- learndata 측정1: itemCode base 59.2 → **A(held-out 비순환) 60.4%(+1,045)** → B(full 순환) 62%.
- 경로 fallback 6,743장(75%)/free 2,258. **품명정확도는 경로 무관**(raw 37.8 vs 35.1) → 품명룰은 경로 공통 합류점.
- 결함분류: recognition 32,540(61%)=FT몫 / parser_drop 19,764(37%) / ambiguous 789.

## ★검증된 룰 재정렬 (전부 9,001 실측)
1. **★괄호주석 중립화 (master 출력) — net +2,968 → master 65.53→69.08%(+3.55pp), BREAK −1.** master 오매칭 최대부류=다른약 아니라 **같은약+행정주석**(`로카탄플러스정(병)`·`(제약사품절)`·`(규격변경)`·`(향정)`·제조사명). master_dict 38.8%(15,064/38,848)가 이 주석 보유(war DB유래), GT는 깨끗(주석 우리출력에만). → **normalize.py `name`타입 신설(=[[project_matching_bench_handoff]] norm_company 선례, GT수정X) + master출력 strip**. 위험 ~0. rawOK_masterX 3,838의 "rerank필요 3,521" 대부분이 실은 이 주석건 → 별도 rerank트랙 거의 소멸.
2. **learndata 다중코드 spec-unit 필터 (itemCode) — A 60.42→61.52%(+935), oracle상한 67.34%.** 다중코드 읽기 17,788개 중 **78%(13,836)가 포장단위(unit) 상이**(같은품명 다른pack=다른코드). 행 spec으로 후보선별. 갭은 spec품질(파서결함 2위 컬럼)에 묶임→spec올리면 동반상승. **기각**: 지점(brch_cd)키 60.05%(A보다↓)·게이트<3완화 net−369·war식 sim+가격 tiebreak +116(spec필터가 우월).
3. **선두 순수코드 strip (raw itemName) — net +999(FIX+1,025/BREAK−26).** 안전(GT 순수숫자 시작 0.72%). master입력 정화 부수효과 소.

## ★기각 — 꼬리 pack-token strip (이전 나의 1순위 가설, 실측이 반증)
- **net −6,907 (FIX +1,212 / BREAK −8,119).** GT itemName이 pack을 **포함**하는 게 압도적(`베타리온정10mg30t`가 GT, bare 9,635 vs pack포함 2,421이지만 blob행 대부분 GT가 pack보유) → 꼬리strip이 정답 8,119행 파괴.
- blob 전체 12,056행 중 **master가 이미 81.3%(9,796) 흡수**(trigram이 pack꼬리 견딤) → blob은 raw지표만의 허수, master(대외 벤치지표)엔 무의미.
- = [[project_invoice_rule_work_priorities]] "R1 itemName토큰스트립 062 GT로 반증·폐기"의 **9k 독립 재확인**. 결함 raw건수로 순위매기면 안 됨(품명은 raw 아니라 master/itemCode가 대외 목표선).

## learndata A net+1,045 실체 (측정1 정직수치)
+4,665 회수 − 3,620 파괴(majority가 base맞힌행 덮어씀). A미스 33,458 원인: 읽기없음(OCR)12,121·미등장(오독/신규)8,288=**FT몫 61%** / 룩업HIT-majority오선택 5,854(spec필터가 회수) / 코드자체틀림 3,023 / 게이트차단 2,933(완화시 net−). blob스트립→learndata키 회수는 net−(+313/−913, keys가 singleton). itemCode는 이미 Google독립 54.1% 상회(59~62%), master만 74.7 대비 −9pp.

## 다음 (미검증)
- P4 4순위=행 통째누락 2,715(gtOnly)+인접시프트 852 → **스냅샷 OCR envelope로 "파서가 떨궜나 vs OCR에 없나" 검증 필요**(HA append_missing_ha_rows 계열).
- recognition 32,540(near sim≥0.85 11,415 + mid 9,131 = raw상한+24pp) = FT 판정 기준선.
- 게이트=study/thin 회귀0·spurious0 + 9,001 replay 재측정. 스크립트: scratchpad itemname_deep.py·learndata_deep.py·p1_blob_verify.py(실측 재현용, 미보존).
