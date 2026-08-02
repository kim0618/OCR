---
name: project_invoice_rule_work_priorities
description: 거래명세서 룰 작업. 2026-07-03 세션서 thin 셀 13.4→22.7%(+9.3pp) 달성 — 행번호스트립+blob샐비지+R2fill. R1-나머지(itemName토큰)는 062 GT로 반증·폐기. 미커밋. 다음 레버·게이트·측정루프
metadata: 
  node_type: memory
  type: project
  originSessionId: d6421aa9-6d52-4b4f-8f72-44a5decc4782
---

2026-07-02. [[project_invoice_column_matching_complete]] 완료(base) 후 **룰 단계** 착수 계획. 순서=룰→마스터→파인튜닝 확정([[project_master_match_baseline]]). 새 채팅에서 이어감.

**Base(룰 출발점, run 061 replay):** thin 필드 **46.5%** / 셀 **12.4%**, study 90.1%(회귀 가드레일). BASELINE_MATRIX.html의 Paddle열=061/replay 자동반영(load_paddle가 replay_compare 우선 읽게 수정함).

**근거 데이터(run 061 replay 전수):**
- **행 과분할이 지배적**: ext>gt(행 지어냄) **1052장(53%)** ≫ ext<gt(놓침) 385(19%) ≫ 일치 565(28%). rowCountMatch 실패 72%. → 한 GT행을 여러 행으로 쪼갬이 최대 결함원.
- **header-anchored fill 발동 822/2002(41%)**. 미발동: too_few_columns 357 / no_header 335 / too_few_rows 346 / no_pharma 110 / no_body 32.
- 컬럼 드롭(패턴 drop 지배=행세그·커버리지): spec 9098·unitPrice 8978·amount 7959·quantity 7060·manufacturingNo 7050·expiryDate 6528·insuranceCode 5638. **itemName 6798은 wrongpick 2940 지배(=코드+규격+날짜 blob 흡수)**.

**⚠️ 2026-07-03 갱신 — base=062, R1 재해석+일부 완료:** base가 **run 062(전처리 orientation 완료+컬럼매칭)**로 이동. BASELINE_MATRIX Paddle=062(필드 47.7%/셀 14.8%). 룰 작업은 **062 스냅샷에 로컬 replay**(AWS 불요). [[project_preprocess_orientation_fix]].
- **R1 "행 과분할=병합" 프레임 틀렸음(전수분해로 교정).** 진짜 과분할은 +1~3뿐이고 "초과행 5045"의 63%는 정렬실패 아티팩트(itemName 미파싱). 진짜 초과=보일러플레이트(합계/총매출/이하여백/☆☆) 647 + 중복 438 + 파편 288. **병합 아니라 노이즈행 DROP이 정답.**
- **R1-boilerplate DONE(로컬검증):** `drop_boilerplate_table_rows`(+`_row_names_a_pharma_product` 보호막) invoice_statement_free.py, main.py 합류점+replay_compare 배선. 고정밀(진짜약품 보호, 표 안비움 안전망). **061 replay: 과분할 1052→845, rowCountMatch +158, 초과행 −512, cell 12.44→12.56, spurious 0, study 90.1→90.1(회귀0), 오드롭 사실상0**. **미커밋.** 큰 cell상승은 아직 itemName-blob이 막음(=R4).

**★★ 2026-07-03 룰 세션 대성과 — thin 셀 13.4%→22.7% (+9.3pp), study 회귀0·spurious0 ★★**
전수분해로 우선순위 재도출(062 GT 시뮬 직접) → 3룰 구현·로컬검증. **모두 미커밋.** 측정=062 스냅샷 로컬 replay(`foreach study,thin { replay_compare --testset $t; parser_drop_classify --testset $t --compare-dir replay_compare }`).
- **❌ R1-나머지(itemName-blob 토큰스트립) 반증·폐기.** 062 GT 직접 시뮬: 선행코드+날짜 스트립 FIX 3~8, 공격적 spec까지 FIX36/BREAK80 = 순손실. **itemName 불일치의 진짜 원인=공백**(GT 61.5%가 spec 포함, 공백무시시 +893). itemName cell은 dead end. → 소표본 추론(061) 반증 사례.
- **진짜 병목=행 정렬/세그먼트**(base: GT행 48.7% 미매칭, 허위행 7181). body컬럼 drop 47k는 대부분 놓친행의 하류. 매칭행 fill 레버는 소진기.
- **✅ R2 fill 확장 DONE(+0.65pp):** `_ha_fill_arith_and_spec`+`fill_pharma_columns` 확장. money(amount/unitPrice/quantity)를 **산술삼각검증**(qty×unit≈amount일때만=spurious-proof)+spec 토큰가드로 빈칸 채움. 정렬 이미 된 행만.
- **✅ 행번호 스트립 DONE(+3.4pp, 최대 클린레버):** `_strip_leading_row_index` → `_parse_table_row_candidate`/relaxed 배선. **뿌리원인**=war 표 행앞 순번(1,2,3…)→free 컬럼파서가 첫토큰 숫자라 거부→fallback blob→content-align 실패→행8셀 손실. 가드=선행 1~3자리 뒤 한글품명+콤마금액2개. 검증: 463011 fallback30blob→free25행(=GT) 전부 amount복원.
- **✅ blob amount 샐비지 DONE(+5.24pp, 최대 단일점프):** `salvage_blob_amount`(main.py 합류점 drop_boiler→salvage→fill + replay 미러). amount빈 blob행의 _rawText 마지막 콤마금액을 amount로 살려 aligner(0.5·name+**0.35·amt**+0.15·qty, thr0.30)를 먹임→놓친행 정렬복원. 근거=놓친행 30%가 GT amt==마지막콤마금액. 가드=한글품명+요약행제외(`_BOILERPLATE_ROW_RE`에 순매출·품절·미출고·반품 추가)+**마지막금액==기존qty/unit이면 skip**(수량을 amount로 넣는 spurious 방지, study 7-2/7.pdf 2건 잡음).

**aligner 이해(compare_table.py `_row_similarity`):** `0.5·itemName유사도(SequenceMatcher) + 0.35·amount정확일치 + 0.15·qty정확일치`, threshold 0.30. **amount만 field에 있으면 0.35로 정렬성공.** 그래서 blob(amount 필드 빈)→행손실, salvage가 결정타.

**다음 남은 레버(우선순위, 현 22.7% 기준):** ①놓친GT행 아직 44%(54,999셀)—rownum後 잔여 blob은 heterogeneous(일반화 선행코드 +4%, 요약드롭 +2%만, 클린레버 소진기). ②매칭행 빈셀 29k(master 컬럼 다수+저정밀 spec). ③itemName 공백(checker 정규화=~893+정렬보조, 스코어링 의미변경이라 사용자 승인필요). ④45% 놓친행은 진짜 인식실패(OCR바운드). itemCode/itemNameMaster/company/address=**마스터매칭** 몫([[project_baseline_matrix_stages]]).

**각 룰 필수 게이트:** ①study 회귀 0(소표본 가드레일 — whole-replace가 study 깨뜨린 전례), ②replay_compare로 격리 측정, ③일반화 룰만(구조·패턴 의존 O, 특정값 외우기 X [[feedback_class_not_per_case]]), ④spurious 0 유지.

**미커밋 코드(2026-07-03 세션):** invoice_statement_free.py(`_strip_leading_row_index`·`salvage_blob_amount`·`_ha_fill_arith_and_spec`·`_BOILERPLATE_ROW_RE` 확장)·main.py(salvage 합류점 배선)·replay_compare.py(salvage 미러)·eval/trend.py(회차 061+ 필터·표본 소폭차 델타표시)·eval/run_all.py(SUMMARY 상단 필드/셀 델타)·eval/replay_summary.py(history carry-forward lockstep). **측정루프 그대로:** `replay_compare.py --testset invoice_{study,thin}` → `parser_drop_classify.py --testset ... --compare-dir replay_compare`. 실행=사용자.
