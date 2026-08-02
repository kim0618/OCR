---
name: project_baseline_matrix_stages
description: baseline_matrix 단계(Base/Rule/Master)가 ocr.xml 어느 쿼리에 매핑되는지 + 룰=구글기준(우리파서 아님)
metadata: 
  node_type: memory
  type: project
  originSessionId: 03cae375-76f7-4148-823f-6e64de9dcc19
  modified: 2026-07-27T00:37:09.412Z
---

baseline_matrix.py = war GT 필드×단계(Base/Rule/Master/Fine-tune) 정확도 매트릭스(Google vs Paddle). **2026-07-09 6천장 확대**(SAMPLE_PATH=sample_6000.txt, 6073장, 2606⊂6000 superset). 출력 runs/BASELINE_MATRIX.html.

**★★9000 preset 추가(2026-07-22) — 리플레이 기준셋 18개월 벤치:** baseline_matrix.py **파라미터화**(argparse `--preset {6000,9000}` + `--sample/--gt/--out/--mmatch/--cust` 오버라이드, 6000 기본=비파괴, 백업 `backup/baseline_matrix_20260721_before_9000_preset.py`). `--preset 9000` = SAMPLE=replay_set_v1.txt·GT=ground_truth_replay.json·캐시=*_9000.json·출력=**runs/BASELINE_MATRIX_9000.html**·`PADDLE_FILTER`(대량 run compare에서 9,001만 safe-id로 추림, replay run 없으면 대시=정상). 캐시=**master_match_google_9000.sql·cust_match_google_9000.sql**(2606판 복제+3곳만: `\copy`=replay_set_v1.txt, strip `'^.*/2606/'`→**`'^.*/processed/'`**(월접두 키 `<월>/<docId>/<파일>` 산출), 월필터 제거). ★war DB **18개월 전부 있음**(2501~2606 확인). 함정=master SQL 재작성 때 `JOIN tbl_ocr_invoice_body b` 빠뜨려 즉시에러→복원. 생성완료: **master_match_google_9000.json 51,942엔트리**(L14,429/NM_L9,771/SIMILAR27,742)·**cust_match_google_9000.json 8,238**(키 전원 replay셋내). **★9000 Google 결과(어려운 셋=새품목 최대수집): Base품명 28.4→Rule 47.8→Master 95.1%, itemCode 0→25.2→88.4%. 순환제외(독립) 품명 74.7%(7,708/10,324)·itemCode 54.1%(5,810/10,745)·공급자상호 89.9/주소 88.6·지점 100.** 6000(품명99.4·코드독립73.6)보다 낮은 게 정상=희귀품목 얹혀 war조차 덜맞음→헤드룸 크게 드러남. **★목표선=95%아니라 독립값(품명74.7/코드54.1)에 Paddle로 도달=파리티**(판정은 Paddle열이 replay run으로 채워질 때 같은행 비교). Paddle=아직 replay run 前이라 대시.

**★2026-07-27 정정(067 replay 채워짐, 대시보드 실측 — 내 이전 오독 교정):** OCR읽기 탭 공정비교(순환제외·동일행)에서 **Paddle raw 42.1% > Google raw 30.7%(+11.4pp)** = 우리가 품명을 더 잘 읽음. **74.7%는 Google raw가 아니라 최종매칭(inm_pct=learndata→LIKE→trigram 캐스케이드 후, 독립행), Google raw독립=30.7%(inm_base_pct).** 우리 최종=LearnData A(held-out)~73~75%(RUN_HISTORY 067 learnA 74.8/learnB 75.4) ≈ Google 최종 74.7 → **검증가능 독립행에선 사실상 파리티, 26pp 해자 아님.** 6천 Master 99.4는 순환행(GT=war자기출력=검증불가) 포함 부풀림이라 held-out 독립 74.7과 비교 불가. 최대레버=**리랭커**(top-10 recall 91%→top-1 회수하면 Google 위로 갈 여지). 절대 "Google 74.7 raw가 우리보다 낫다"고 쓰지 말 것(내가 두 번 틀림).

**★6천 확대 절차(2026-07-09):** GT(ground_truth_2606.json=23737docs 전체)·master_dict.json은 샘플무관→그대로. 바꾼 것=① baseline_matrix.py SAMPLE_PATH→sample_6000.txt ② master_match_google.sql·cust_match_google.sql의 `\copy`→sample_6000.txt. **두 캐시는 샘플스코프라 반드시 재생성**(안 하면 Google Rule/Master 저평가). 재생성=psql `/c/Program Files/PostgreSQL/17/bin/psql.exe`, PGPASSWORD=root123, data/invoice_war서 실행. master_match=trgm 캐스케이드라 무거움(단일 json_object_agg, ~15분+, 백그라운드 권장), cust=6초. **6천 결과: Rule품명 48.3%(2천 48.1)·Master품명 99.4(동일)·itemCode 98.7(독립73.6)·공급자상호 85.8·주소 84.8·지점 100% — 2배 스케일서 랭킹/매칭 안정(일반화 확인).** 캐시엔트리 mm 21172(행 커버 100%)/cust 5320. Paddle=run 065 자동채움.

**★탭(Base/Rule/Master/Fine)=구글 단계, Paddle열=우리 파이프라인 현재값(모든 탭 동일).** `load_paddle`가 **최신 run 자동 읽음**(thin/replay_compare 우선, 없으면 compare). KPI카드=`_dual(full, 순환제외)` 두값 표시(앞=전체, 뒤=금액·날짜 등 pass-through 뺀 순수실력).

**2026-07-03: Paddle base = run 062**(전처리 orientation 완료+컬럼매칭, **R1 미포함**). 필드 47.7%(47.2→) / 셀 14.8%(13.7→) — orientation이 올림. **R1은 base 아님=첫 룰**(base 대비 델타로 측정, base에 섞으면 기여도 못 잼). 룰 base 정의=전처리+컬럼매칭까지, R1~R4는 그 위. [[project_preprocess_orientation_fix]] [[project_invoice_rule_work_priorities]]

**★단계 = 구글(war) 기준이지 우리 파서가 아니다.** 사용자가 두 번 정정함("구글 기준이라고 분명히 말했다 우리꺼 아니라고"). ocr.xml(`_waranalysis/WEB-INF/classes/mybatis/mapper/ocr.xml`)에 룰이 다 있고 그걸 단계별로 옮기는 것:

- **Base** = 구글 읽은 원문 vs GT (이미 있던 것). itemName 26.7%, itemCode 0%.
- **Rule** = `selectMasterItemLearnData`(line 400). learndata **EXACT** 매칭(`m.ocr_item_nm = #{item_nm}`, clean 아님!) + `learn_count >= N` 게이트, 동점=SIMILARITY(master nm)·가격차. → `compute_google_rule()` 구현. 2004샘플: itemName 26.7→**54.3%**, itemCode 0→**28.4%**(발화 5,408행/cd채점 12,455).
- **Master** ✅완료 = `selectMasterItemLike`(line 452, `fn_get_item_name_clean`+LIKE) → `selectMasterItemBestLike`(line 431, trigram) 캐스케이드. 단계정의=rule 우선, 없으면 master. `compute_google_master()`. 2004샘플: itemName **97.3%**, itemCode **90.6%**(⚑대부분순환), **독립(순환제외) 70.7%**(312/441). 매칭분포 룰3466/LIKE2870/trg6117/miss2.
- **Fine-tune** = 모델 재학습(맨 나중).

**Master 구현 인프라(2026-07-01):** psycopg 없음→psql 배치만(★-q로 순수JSON), baseline_matrix가 raw json 읽음.
- 품목: `master_match_google.sql`→`master_match_google.json`(9506 name\x01price→{cd,nm,sim,method}). ocr.xml learndata→LIKE→trigram 캐스케이드. 속도=master_item을 fn_get_item_name_clean까지 푼 temp `mi`+trgm 인덱스(GIN=LIKE'%%', GiST=`<->`KNN). tiebreak=SIMILARITY DESC,|bp1-단가|ASC.
- 거래처: `cust_match_google.sql`→`cust_match_google.json`(img_key→{cd,nm,addr}). ★war 실제=selectCustBestLike의 FILE_NAME=파일명 아니라 **OCR 사업자번호**(service_no=사업자번호). **지점(brch_cd)+사업자번호(final,없으면raw) 정확일치**, ★tiebreak=**사용빈도(주거래처) DESC**. 진단: recall 98.7%(war답이 후보에 있음=랭킹문제), tiebreak 최단명80%→**빈도93.6%**(cust_cd재현). 지점 스코프 필수. **최종 supplierCompany 84.5%/Address 83.2%**(사업자번호 매칭 천장 — 매칭된건 ~99%충실, 미달 15%는 사업자번호 없어 war가 주소/수동으로 넣은 것=재현불가, 더 파는건 도박). 상호는 tiebreak에 둔감(같은 사업자번호 여러 cust가 회사명 거의 동일).
- 지점(공급받는자): brch_cd(GT _source)→master_dict brch. 100%.
- **learndata 충실화(2026-07-01):** build_master.sql의 learndata는 count최빈으로 뽑아 war와 어긋남(재현 69.9%). master_match_google.sql에 learndata를 원본 selectMasterItemLearnData대로(learn_count≥3, SIMILARITY(정식명)→가격 tiebreak) 캐스케이드 1단계로 넣어 재작성. 캐시에 ld_cd/ld_nm(rule단계) + cd/method(master단계). compute_google_rule·master 둘 다 캐시 사용.
- **★검증 통과: war 3방식 재현율 learndata 98.4 / NM_L 99.2 / SIMILAR 98.6 → 표 Google값=진짜 war값 확정**(잔차~1.3%=사람손댄 행, 매처재현불가). base itemName 26.7% GT직접계산 일치.
- **war master 최종(=우리 목표 벽, 2004샘플):** 품명 **99.4** / itemCode **98.7**(독립73.6) / 공급자상호 82.6 / 공급자주소 80.0 / 공급받는자 100. 사다리 품명 26.7→48.1→99.4, 코드 0→28.5→98.7. **엔진=easyOCR 스톡, 파인튜닝 없음** [[project_war_ocr_engine]].

**컬럼 목록 = war 실제 목록 정합(2026-07-01, GT/DB로 검증):** body 컬럼 전수 확인 → **보험코드(insuranceCode=bohum_cd, 61% 채움) 추가**(build_gt+FIELDS). ★보험코드는 **OCR로 읽는 인쇄 컬럼**(매칭산출 아님 — body.bohum이 매칭품목 bohum과 62.5%만 일치)이라 FIELDS b=100.0(pass-through, war쪽 순환, 토글 대상). 우리 extractor(invoice_statement.py 라인241·1209 `보험No/보험번호/보험코드/보험약가`)가 **이미 per-row 셀로 추출** → GT에 있으니 compare_table가 자동 채점(ROW_META 아님). product_code(0%)·문서번호("0")=빈값 제외 타당. invoice_med_cd(100%,값01/02)=문서분류 카테고리라 필드 제외. **"war가 뭘 쓰나"는 GT/DB로 100% 확정**(추측 아님). 사람개입·ERP재수정·진짜정확도는 GT밖.

**순환분리 확정:** GT.itemCode=war 최종코드라 Google rule/master는 대부분 순환. `item_match_type`(build_gt.sql 추가, ROW_META_KEYS라 채점제외)로 "war가 같은방식으로 맞춘 행"을 순환처리 → 독립수치 별도. 진짜 정확도는 **Paddle**(우리OCR→같은매처, 비순환)에서 판가름. Master itemCode 90.6%≈war재현 검증(우리 캐스케이드 충실).

**Why:** 내 초기 오해 = 룰을 우리 파서개선으로 봄(메모리 [[project_finetune_strategy_and_corpus]]가 "학습룰=파서개선"이라). 하지만 이 매트릭스의 단계는 **경쟁사(war) 파이프라인을 단계별로 재현**하는 것. fn_get_item_name_clean은 Rule 아니라 Master에 있음(내가 헷갈렸던 지점).

**정직성 주의:** GT.itemCode=body.item_cd=war 최종코드(learndata+trigram+수동 다 거침). 그래서 Rule itemCode 회수율은 **원래 learndata로 맞춘 행=부분순환**. body의 `item_match_type` 컬럼을 GT에 추가(build_gt.sql)하면 순환행 분리 가능(미정·사용자 선택). [[project_master_match_baseline]] [[project_invoice_war_db_restored]] 참조.

**How to apply:** master_dict.json(learndata 75,332 / item 38,848)이 Rule·Master 입력 모두 보유. Paddle 열은 최신 run 자동(load_paddle). 이미지 없이도 Google 단계는 DB/GT만으로 계산됨.
