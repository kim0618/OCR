---
name: project_eval_loop_preprocess_aware
description: "평가/학습 루프를 '전처리 인지'로 확장하는 결정. 전처리 결함을 루프가 자동 진단하게"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8d7a70d9-8996-454c-b78b-e9daa5f2480a
---

**결정 (2026-06-11):** 평가/학습 루프를 **전처리-인지(preprocessing-aware)**로 확장한다. P3 패치·실데이터(수천장) **실제 진행 전 선결 인프라**로 깔기로 사용자가 결정.

**왜 (사용자 통찰):** 지금까지 전처리 진단(detect_document skip·orientation 누움·keystone)은 전부 **손**(이미지 직접 까보기·ad-hoc 비교). 6+18장이라 가능했음. 두 갭:
- **갭1 분류:** 루프가 전처리 *신호*를 안 읽음. `eval/buckets.py:117` 전처리 버킷 판정이 `scored>=6 and miss_rate>=0.7`(필드 70%+ 비었나)뿐 = GT대비 결과 *역추정*. 표 깨졌지만 값 채워진 케이스(5-2 컬럼밀림)는 layout/structure로 빠짐 → run 전처리버킷=0인 이유.
- **갭2 GT부재:** miss_rate는 GT대비라 실데이터(GT없음)엔 정확도조차 못 잼. 손진단도 불가.

**핵심:** 우리가 손으로 한 진단값(detect_document skip·orientation·keystone)은 **전처리가 이미 계산하는 값**. (a)추출응답에 안 실리고 (b)루프가 안 읽을 뿐 = 모델 문제 아니라 **계측 배선 문제** (룰/신호 보강, [[feedback_no_model_discussion]] 부합).

**3순위 해결책:**
1. **전처리 신호 노출(무위험):** `extract_debug.preprocess`에 detect_document 상태·area%·borders·keystone·measure_skew 잔여각 추가(현재 orientation/deskew만 있음. detect_document 결과는 main.py:2373 `_`로 버려짐). 디버그 메타 추가일 뿐 OCR/추출 로직 불변(3N deskew 메타 추가 전례).
2. **buckets.py 신호기반 자동분류:** 셀/필드 바닥 + 전처리신호 이상(이미지인데 skip/orientation 저신뢰/keystone 큼/잔여기울기 큼) → preprocessing 버킷. 임계는 **24장(GT보유)으로 캘리브레이션**(이번 손진단=라벨셋: 5-2/5-3/7-1=전처리, 6-2=orientation).
3. **실데이터용 GT-불요 품질 프록시(자기일관성: 공급가+세액=합계, 수량×단가≈금액, 행정렬 신뢰).**

**1·2 구현·검증 완료 (2026-06-11, run 009):** 코드=main.py(extract_debug.preprocess에 document블록+orientation margin 노출, detect_document 결과 더이상 안버림), preprocess.py(detect_document가 skipped/areaPct/borders 반환), eval/buckets.py(`_preprocess_signals`+신호기반 preprocessing_suspect, sample-level 유지=phase3 불변식 보존), eval/compare_run.py(preprocess 전달). 백업 `*_before_preproc_aware_instrumentation.py`. **결과: 전처리 버킷 1→10**(recognition/structure/layout 204/221/2 불변). 자동플래그 10장(3-3,4-1~4-3,5-1~5-3,6-1,6-2,7-1)에 run008 워프회복셋(5-2/5-3/7-1/4-1/4-3) 전부 포함=perspective-skip 부류 정확 포착. **갭2개(후속):** ①orientation 부류 미포착(3-1/3-2/6-3=detect_document 완료인데 깨짐, P3와 다른 레버=orientation 오판). firstPassDiff/ratio 이미 노출됨→후속 캘리브레이션. ②임계경계(7-3 skipOnImage지만 cellAcc0.333>0.3라 sample_failed=False 누락). 6장=probe라 임계 미세조정은 실데이터때. 단위테스트 4/4(None graceful·신호분류·좋은표본 오플래그방지·PDF skip 제외).

**리포트 의사결정-신뢰성 수정 (2026-06-12, 전처리 1차 종료 후):** 리포트가 "안정 모집단 반복측정"용 설계라 "표본·코드 계속 변하는 개발중"엔 변화신호가 가짜/역전. 3건 수정(eval 측정코드, 운영무관, 기존 run 데이터로 재생성검증, 백업 `trend_*`/`*_before_report_decision_fixes`, report.py): ①`trend.py _changed_population`: 직전 run과 sampleCount 다르면 pp/버킷 델타 보류(`↕표본`)=6→24장 가짜 ▼19.7 급락 제거. ②🔴 판정을 *정확도(pp)만*으로, 버킷결함수는 코드/계측변경에 민감하므로 회귀신호서 제외하고 '참고 버킷변화'로 강등=셀+2.7pp인데 🔴뜨던 모순 해결(→🟢). ③`report.py _base_variant_split`: study를 base(정상)/변주(각도사진) 분리집계(SSOT=contract._VARIANT_RE)=run011 base 6장 85.7% vs 변주 18장 73.3%(전체76.7%가 가리던 것). SUMMARY.html trend임베드는 다음 run때 자동갱신.

**코덱스 루프검증 후속 수정 (2026-06-12):** 코덱스가 12개 지적, 사용자가 사실여부+우리맥락 위험도로 우선순위화. 코드확인 후 처리: **#10🔴**(trend.py latest_delta_line `if acc and prev` 의 0.0 falsy버그→정확도 0.0이면 delta=0으로 회귀 놓침. `is not None` 가드로 수정, 0.5→0.0이 -50pp로 탐지됨). **#3🟠**(compare_table.py `_index` 중복 rowIndex 조용한 덮어쓰기→`idx in out: continue`로 첫행유지, rich GT unique라 무변화). **#5🔴**(metrics.py overall이 micro(항목가중)뿐→macro(샘플평균) 병기 추가. `_macro()` + overall.fieldMacro/cellMacro. report.py·run_all SUMMARY(md/html/console) 전부 micro/macro 병기+설명. **run011 셀 micro 76.7% vs macro 41.3%=35pp 격차** 드러남=큰표(28행 1.jpg)가 micro 지배, 샘플당으론 변주 다수 깨짐. 수천장 위험 정직신호). 백업 `*_before_5_macro`/`*_before_10_zerodelta`/`*_before_3_dup`. 전부 sqlite 무변경(가벼운안), 기존 데이터 재생성+단위테스트 검증. **미처리(판정대로 보류):** #7🟠(metrics/compare가 현재FS manifest 재빌드=재현성구멍, 실데이터 직전 C묶음 #1과), #8🟡(thin 필수필드 없음, 실 ETL GT전환시), #2/#9/#6/#4/#11-12(설계/수용).

**진행 결정:** **1·2 지금 구현**(measure_first 선결). **3은 실데이터 도착 시 추가여부 판단**(24장엔 GT 있어 정확도가 더 정확, 지금 만들면 미검증 적재=안티패턴). P3 image-한정 패치는 계측 깐 뒤. [[project_learn_loop_infra_plan]] [[project_eval_loop_strategy]] [[project_preprocess_image_deskew_gap]]
