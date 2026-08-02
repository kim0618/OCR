---
name: project_matching_bench_handoff
description: "②매칭 벤치 G1~G4 완료(2026-07-06): thin 셀 24.2→32.5%(+8.3pp), 매칭엔진 82.8%@floor0.2, parity 99.2%. 남은 것=G3 floor 사용자 확정·AWS 배포·G5 판독. 산출물/수치/다음단계"
metadata: 
  node_type: memory
  type: project
  originSessionId: cfa126d1-55b6-4dfa-9a7c-f8c945510fe2
---

**2026-07-06 ②매칭 벤치 G1~G4 구현·측정 완료** (같은 날 두번째 세션). 원리·천장은 [[project_master_match_baseline]].

## 산출물 (전부 미커밋)
- **G1** `eval/gen_match_bench.py` → `data/invoice_war/_match_engine.csv` 10,000행(matched 7,780+ext_only 2,220). **replay 기반으로 재작성**(replay_compare rows[]엔 ext-only 페이로드 없음→spurious 모집단 확보 위해). 단가 "950.00" 소수점버그 수정(digits-only=100배 오류).
- **G2** `data/invoice_war/_match_engine.sql`(psql, 내가 직접 run 사용자허가): clean+trigram KNN30+가격tiebreak, floor스윕 0~0.5, spurious/애매밴드/단가유무별 동시측정. 출력 `_match_engine_out.txt`, per-row 덤프 `_me_pick.csv`.
- **G4** `extractors/master_match.py`: pg_trgm 등가 파이썬 매처(fn_get_item_name_clean=괄호쌍 greedy 1회 제거+공백strip, 단어별 '  w ' 패딩 trigram, jaccard). master_dict.json 정적사전(38,842), 없으면 자동 비활성. `MATCH_SIM_FLOOR=0.20`(잠정). main.py 합류점(recover_shifted 뒤)+replay_compare.py 미러 배선, 빈칸만 채움.
- **parity** `eval/match_parity_check.py`: sim 일치 99.22%(pg_trgm 등가 확인). cd만 다른 16.6%=애매밴드 동점 임의스왑(무해), sim불일치 0.78%=psql sim0 임의top1 vs 파이썬 무배정(floor>0에선 동일).
- **staging** `replay_compare.py --no-master-match --out-subdir replay_compare_rule` 추가. baseline_matrix: Rule=replay_compare_rule / Master=replay_compare 분리.

## 실측 (062 thin replay)
- **thin 셀 24.22→32.54% (+8.3pp)**, itemNameMaster 0→44.2%, itemCode 0.08→32.9%, **spurious 0, study 회귀 0**(rich GT는 두 컬럼 미채점=구조적 무영향).
- 벤치(floor 스윕): floor0 overall 76.3%(code-or-name) / floor0.2 coverage85.9·배정중82.8·spurious39.1 / floor0.35 64.4·86.5·18.6. **애매밴드 62%**(top1=top2 동점, 동명이품·팩수 변형)=가격 tiebreak가 가르는 모집단이자 랭킹개선(G4후속) 타깃.
- 단가 실측: matched 결측 33.5%(war 22.5%보다 높음), ext_only 67.8%.
- **단가 룰 가치 판정(사용자 질문 회신함)**: 매칭엔 +1.4pp 상한(결측33.5%×갭4.2pp)으로 소폭, **셀 지표엔 ~5.4pp 상한**(unitPrice parser-drop 6,269/115,144, 86%가 룰몫) → 매칭용 아닌 일반 셀 룰 백로그 상위로.

## 랭킹 V3 (2026-07-06 추가, 같은 세션)
- **품목 랭킹 tiebreak 개선 배선 완료.** `eval/match_rank_bench.py`(V0~V3, _match_engine.csv에 spec/qty/amount 컬럼 추가 재생성): V1 규격(dose/pack 토큰, 일치>정보없음>모순) code +2.2pp, V2 가격 결측 amount/qty 역산 +0.3pp → **V3 채택: 배정중 code 74.4→76.9%**. master_match.py match()가 top30 rerank(sim→dose→가격)로 재구조화, fill이 spec/quantity/amount 전달. master_dict에 pyojun 추가(재발행, 36,398건).
- 062 재측정: **itemCode 34.3%·itemNameMaster 44.9%·셀 32.8%**, spurious 0. 랭킹 "+20pp"는 top10 천장 기준이었고 top1 tiebreak 실측은 +2.5pp — 남은 애매밴드는 규격 정보 자체가 없는 동명이품(가격만 남음, war도 동일 천장).

## ③행검출 착수 (2026-07-06 같은 세션, P0~P2 1사이클 banked)
- **P0 전수분류** `eval/missing_row_classify.py`: 미추출 3,539/12,446행(28.4%) = dropped 53.7%·align_fail 21.2%·recognition 21.0%·merged 4.0%. **P0b** `eval/missing_row_why.py`: dropped의 **90.9%가 '품명 단독 라인'(tokens<3)** — 셀이 라인으로 안 뭉침, free/fallback 반반 → 라인=행 로직 구조 한계 확정.
- **P1 = append_missing_ha_rows** (invoice_statement_free.py, main+replay 합류점 boiler-drop 직후): 기존 `_extract_header_anchored_table`(HA, y밴드×컬럼 Voronoi 2D 재구성) 행 중 표에 없는 품목행을 **추가만**(기존행 불변, 이름포함/유사0.6/amount키 중복가드, 요약/보일러 금지).
- **v1 P2 통과**: 셀 32.8→33.9%, 행회수 3,539→3,287(dropped 1,901→1,654=252회수), spurious0·study0.
- **v2 append_mode 게이트**(pharma 요구 제거, itemName+money면 허용): +0.06pp 미미 → 재진단. append_gate 실패 557 중 **475가 자간인쇄 헤더('품|명','금|액','제|품|명')로 itemName 미매핑**이 진짜 병목.
- **★v3 헤더 글자병합**: `_extract_header_anchored_table` col 매핑에서 미매핑 짧은토큰(≤2자) x-연속 run 병합 재매핑. HA-usable 문서 453→791, 셀 **33.9→35.9%(+2.0)**, itemNameMaster 46.7→**49.5%**, itemCode 36.0→**38.5%**, spurious0·study0. **주의**: 이 수정은 append_mode/fill_mode 공유(_extract_header_anchored_table 단일함수)라 fill_pharma_columns도 같이 개선됨. **미추출행수는 3,287로 flat** = v3의 +2pp는 net 행회수 아니라 **회수/기존 행의 셀-내용 품질**(v1은 amount-anchor로 정렬됐지만 itemName junk→master fill 실패, v3는 itemName 정상→master매칭+pharma 셀 채워짐).
- **v4 dropped 잔여 진단**(probe_dropped_ha, missing_row_classify와 동일 부류판정 필수—all-ext concat 부분매칭은 오분류): dropped 628의 HA상태=append_gate 31%·**ha_ok 23%**·no_header 15%·too_few_col 16%·too_few_row 10%. ha_ok 문서(452009) 해부로 2결함 발견·수정:
  - **v4a HA amount 점-천단위 정규화**(267.916→267916, `\d{1,3}(\.\d{3})+`만, 소수단가 950.00 제외): 셀 35.9→**36.05%**(+0.11).
  - **★v4b append 유사도가드 오탐 수정**(가장 큼 +0.93): war 품명 'XX정 용량 포장' 구조라 다른 품목도 접미사 겹쳐 sim0.62 오탐(라코르정 vs 로티브정)→진짜 미추출행 스킵. **amount가 있고 기존에 없으면(=다른 행 확실) 유사도가드 면제**, 빈 amount일 때만 유사도 적용. 셀 36.05→**36.98%**, itemNameMaster 50.4%·itemCode 39.8%, spurious0·study0.
- **★v5 헤더 그리디 분해**(append_gate 302/318=itemName 미매핑 진단→수정): v3 병합이 자간분리 '품|명|규|격'을 '품명규격'으로 뭉치면 _ha_map_label 부분매치가 '규격'(spec, alias순서 먼저)로 잡아 itemName 소실. **x-gap 병합 시도는 과분할로 악화(ok 791→578)→폐기**, 대신 뭉친 concat을 **최장 alias 그리디 분해**(_HA_ALIAS_BY_LEN)로 '품명'+'규격' 둘 다 추출, cx는 문자구간 걸친 토큰 평균. HA-usable 문서 791→**928**, 행 6412→7536. 셀 37.0→**37.9%**(+0.9), spurious0·study0.
- **오늘 누적: thin 셀 24.2→37.9%(+13.7pp)**, 전구간 spurious0·study0. 미커밋.
- **다음 후보**: append_gate 194(HA행 만들었으나 게이트서 잘림, len(out)<2 단일품목 등)·no_header/too_few(HA 자체 실패 ≈40%, 헤더약한 레이아웃)·맥페란정1000T식 빈 amount 행(HA가 amount 못뽑아 유사도가드에 스킵)·align_fail 750(기존행 2D 재배정=회귀위험)·recognition 732(파인튜닝).

## war 품명 캐스케이드 반영 확인 (2026-07-06, ocr.xml 대조 + 실측)
- ocr.xml 품명 매칭 = **3단계 캐스케이드**: selectMasterItemLearnData(learndata EXACT `ocr_item_nm=입력`, learn_count≥3) → selectMasterItemLike(clean+공백strip LIKE 부분포함) → selectMasterItemBestLike(trigram). 전부 tiebreak=sim DESC, |bp1−단가| ASC.
- **우리 master_match.py = trigram 1개만.** LIKE·learndata 미반영.
- **증분 실측**(`eval/data/invoice_war/_cascade_increment.sql`, 우리 Paddle 읽기 _match_engine.csv 입력, matched 7,780): trigram 76.0% → +LIKE 76.9%(+0.9) → full cascade 78.2%(+1.3 더). **learndata 적중 7.8%**(우리 Paddle이 war 구글읽기 키와 겹침, 메모리 예측 18%보다 낮음—키 불일치 확정). 전체 캐스케이드 미반영분 = 배정 +2.2pp ≈ **전체 셀 +0.3~0.5pp**(두 컬럼·매칭행 한정).
- **판정**: LIKE는 정적 nmclean substring으로 쉽게 추가 가능, learndata는 dict 조회(적중 낮아 상한 낮음). 행검출(미추출 22.8%, 행당 8셀)이 레버 훨씬 큼 → 캐스케이드는 행검출 수확체감 후 파리티 완성용.
- **★LIKE 구현→실측→미채택(2026-07-06)**: master_match.py에 LIKE 우선 캐스케이드 넣으니 **-0.05pp(36.98→36.93)** 순손해. 원인: 벤치 +0.9는 dose 없는 순수 trigram 대비인데 우리는 이미 V3 규격 dose로 trigram 강화 → LIKE 우선이 dose 정답을 규격 다른 동명이품으로 덮음(dose가 LIKE 이점 흡수). **되돌림**(match()는 trigram+dose만, _nmcleans 저장만 미래 대비로 잔존). 교훈: war 재현 벤치는 dose 없는 base 기준이라 우리 dose 강화분과 겹치는 룰은 순증 안 될 수 있음.

## ④거래처(공급자) 매칭 — 필드 트랙 개시 (2026-07-06, 사용자 "필드 갭이 최대" 지적)
- **동기**: BASELINE_MATRIX 필드 16.1% vs war 87.0%(▼71)가 이제 최대 갭. war Master의 supplierCompany 84.5%/buyerCompany 100%는 읽기가 아니라 거래처·지점 매칭. 우리 미구현이었음(품목만).
- **구현** `extractors/master_match.py PartyMatcher` + `fill_party_match`(main+replay 합류점): 공급자=supplierBizNumber 10자리 정확앵커→biznoToCust→cust 마스터(nm/addr) 교체. master_dict에 cust 14,954/biznoToCust(재정규화 후 1,458)/brch 10 이미 있음.
- **buyer(지점) trigram 미채택**: 지점 10곳뿐이라 앵커 없는 trigram이 study 전 문서를 '백제약품 영등포지점'으로 오교체(필드 90.9→54.5). 제거.
- **★norm_company (eval/normalize.py, checker PASS)**: study 회귀 원인=마스터 정식명 vs GT raw 표기차(부광약품(전) vs 부광약품(주), 주식회사X vs (주)). supplierCompany/buyerCompany를 'company' 타입 신설→법인격(㈜/주식회사/(주)/(전)) 중립화+_NON_ALNUM. GT 수정 없이 thin·study 양쪽 매치. **접미사를 party값에서만 떼는 방식은 thin -0.3(GT도 제각각)이라 폐기, normalize 양방향이 정답.**
- **결과**: thin 필드 46.7→**54.2%(+7.5pp)**. supplierCompany 1.8→42.3%·supplierAddress 3.2→29.4%·buyerCompany(raw+norm) 0.2→22.5%. 셀 37.9% 불변(party는 필드만). checker PASS. study 5/6 원복, **1.jpg만 supplierAddress 표기차로 81.8(9pp 잔여)=주소 표기 아티팩트**(thin 주소 +26pp 이득이 압도, 프로덕션 war GT엔 정답). supplierCompany 천장 42.3%=bizno 앵커 커버리지(1,458키).
- **다음**: 주소 정규화(행정구역 축약 '서울특별시'='서울')로 1.jpg 잔여 제거 가능·supplierCompany 커버리지(bizno 사전 확장)·미커밋.

## 남은 것
- **G3 floor 확정 = 사용자와 함께.** overall 최대는 floor0이나 spurious 100%, 0.2=균형 잠정. 스윕표 `_match_engine_out.txt`.
- **G5 파리티 판독**: 매칭엔진 82.8%(배정중) vs war 99.4 — 갭 원인=애매밴드 임의픽+클린한계+미추출행. BASELINE_MATRIX Master 컬럼 채워짐.
- **AWS 배포**: master_dict.json을 ocr-server/ 루트로 + main.py/extractors 반영 (main.py는 push 제외 관례 [[project_gpu_transition_state]] 주의).
- ext_only 2,220행=파서가 만든 행(보일러플레이트+blob) — ③행검출 트랙 소재.
