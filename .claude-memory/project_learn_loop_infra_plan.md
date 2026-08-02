---
name: project_learn_loop_infra_plan
description: "거래명세서 평가/개선 루프 인프라(LEARN-LOOP-INFRA) 확정 계획 + 새 채팅방 인수인계. Phase 0~7, GT 계약, 검증된 정합성"
metadata: 
  node_type: memory
  type: project
  originSessionId: 068550ef-1295-415a-828f-127ace19a9eb
---

2026-06-09 거래명세서 비정형 추출 **평가/개선 루프 인프라** 계획 lock. 전체 자기완결 문서 = `OCR/docs/LEARN_LOOP_INFRA_PLAN_20260609.md`.

**진행상태(2026-06-09 갱신): Phase 0~5 구현·검증 완료 = MVP GO.** 코드 전부 `ocr-server/eval/`. `python eval/run_all.py --reuse <run_ts>`(또는 인자 없이 fresh re-OCR) 한 커맨드로 manifest→run_batch→compare→metrics→report→checker 재현, 통합 checker 7항목 PASS. 첫 실측 run = `eval/runs/20260609_143048/`(6장, field 62.3%/cell 88.7% = 가설). 단계별 산출물 = `eval/PHASE{0..5}_SUMMARY.md`, 계약 = `eval/GT_CONTRACT.md`.
- **계획 대비 실측 교정사항:** ① "샘플 1p" 거짓(4.pdf=2p,5.pdf=22p) → 서버 page-0 스코프 확인, pageCount 기록+multiPage 플래그(비치명적, assert==1 폐기). ② free 모듈 docstring "미배선" stale → 실제 main.py:2958 배선됨(주석만 수정, backup함). ③ extractionSource는 마커문자열(`..._free_success_shape`) → "free" 부분일치 분류. ④ rowIndex 추출=str/GT=int → 비교 시 타입정규화. ⑤ per-sample 필드 = totalAmount/totalQuantity 중 정확히1개. ⑥ 콘솔 한글깨짐=cp949 표시 artifact(저장은 정상 UTF-8).
- **진단 하이라이트:** edited=false 필드 97.4% vs edited=true 4.3% → 하니스가 OCR오류 위치를 정확히 지목(룰 보강 워크리스트). 주소필드 0%(노이즈 덧붙임), 인식오류 다수(헥사메딘→헥사메던 등).
- **Phase 6 = 사용자 24~30장 GT 흡수 → BLOCKED on 사용자 GT 제공.** GT 작업 재개 규칙(실제 GT 입력/승인 시에만) 준수 — 아직 새 GT 안 받음. Phase 7 = DB 데이터 올 때.

**목표:** 대량 (이미지+정답) → 측정→4버킷분류(인식A/구조B/전처리/레이아웃)→룰 보강→재측정→회귀추적이 자동으로 도는 루프를, 지금 6→30장으로 다 만들어 검증하고, 데이터 오면 DB연결 한 줄만 추가해 드롭인.

**핵심 결정/검증:**
- GT fixture = `mysuit-ocr/public/data/testsets/invoice_study/` (이미지6 + GT/6, draft-gt-document.v1). 2.pdf 일시제외. 3/4/7=단일행 확정.
- **3대 정합성 코드검증 통과**: free 추출기(`invoice_statement_free.py`) 출력 scalar키=GT labelEn(14) 완전일치, 행키 포함, 응답봉투=`response["document_fields"]`(main.py:3012).
- 하니스는 GT파일 계약만 안다(DB는 ETL이 흡수). 코어비교=값+행 공통분모, bbox/edited=optional(rich 지금GT / thin ETL GT 둘다 통과).
- 6~30장=인프라 검증(기계가 도는가)이지 정확도 합격 아님. 소표본=가설.
- 코드=`ocr-server/eval/`(신규·측정전용), 결과=`runs/`, public/data·운영OCR 무수정. CLAUDE.md 단계규칙 준수.

**Phase:** 0 SCHEMA-CONTRACT → 1 INGEST(manifest자동생성+loader) → 2 RUNNER(run_batch) → 3 COMPARE(field+table+4버킷) → 4 METRICS-REPORT → 5 CHECKER-RUNALL(=MVP GO) → 6 SCALE-DRYRUN-30 → 7 DATA-SEAM(데이터 올때, ETL 정렬).

**수천 장 데이터 출처 = bak.war DB**(검증된 이미지+정답). ETL 초안 `d:\Free_Vue\_waranalysis\bjocr_db_to_gt_etl.py`(평면형 → Phase7서 draft스키마로 정렬 필요). ERP코드 매칭/교정학습=SI 영역(범위밖). 컬럼 갭 [[project_invoice_column_gaps]]. 로드맵 단계맥락 [[project_invoice_unstructured_roadmap]].

**Phase 7 GT 보강 규칙 확정(2026-06-09):** 거래테이블에 없는 회사명/주소는 **master 테이블 코드 JOIN으로 보강** — `invoice_master.cust_cd → tbl_ocr_master_buycust.cust_nm/cust_address`. cust_cd가 확정 링크라 유사도 대조 불필요(ERP등록 전 사람확인됨). master로 채운 필드는 `source:master` 태그 부착(마스터=공식값/종이=인쇄값, 정규화가 (주)·공백 흡수, 드물게 지점명/옛이름 어긋남 → 소수 스팟체크). 적용=회사명/주소만(품목명·금액·수량·날짜·사업자번호는 거래테이블 직접). 대표자·요약필드는 마스터에도 없음→invoice_study(rich) 담당. 상세 = LEARN_LOOP_INFRA_PLAN §6.5.

**P0 thin-ready 재설계 LOCK (2026-06-09, war-검증판):** Phase 0~5 MVP가 rich invoice_study에 하드코딩 → DB thin GT는 로드부터 실패("thin 통과"는 문서원칙일 뿐 미구현). war 컬럼계약을 SQL로 검증하고 전 파이프라인 GT-driven 재설계 확정. 상세 = `OCR/docs/LEARN_LOOP_INFRA_PLAN_20260609.md` **§6.6**. 핵심: ⓮'(ETL이 정식봉투+thin콘텐츠 per-file, bi-format 폐기) · ⓳'(profile은 testset프로파일서 주입, 콘텐츠추론 폐지) · GT-driven 전파(로더 A/⓫ · 채점 ➊⓭⓰ · 메트릭 difficultySplit+커버리지2분모 · 체커 per-testset프로파일) · **SSOT(다운프로젝터=ETL thin필드셋=단일상수)** · 양방향게이트(thin fixture통과 ∧ 6장 thin-projected 일치 ∧ 6장 rich green). war컬럼=스칼라10(신규3=documentNumber/discountAmount/taxType=추출기 미배출→정직한miss)+행6(rowIndex없음). **이건 정확도 아니라 측정·수용 인프라.**

**war SQL 검증 완료(2026-06-09):** `_waranalysis/WEB-INF/classes/mybatis/mapper/ocr.xml`의 insertInvoiceMaster/Body·updateInvoiceMaster 대조 → ETL 컬럼매핑 **정확 확인**. cust_biz_num_final=update(검증)단계에 실재, separate_img_path 실재(=페이지당 master=1이미지1GT). body에 product_code 실재하나 ETL이 drop(인쇄코드 vs ERP 불명→defer).

**preprocess 텔레메트리 캡처 완료(2026-06-09):** run_batch가 응답 `extract_debug.preprocess`(orientation.angle/applied + deskew.absAngle/applied/overApplyGuard) 저장. 분석(정확도 by 회전각 슬라이스)은 미구현=증거 나올때. 싼 보험(재OCR 없이 attribution). 기존 게이트 무영향(compare/metrics/checker가 안 읽음), 수정 후 checker 7/7 green 재확인.

**전처리 판단:** orientation/deskew 로직은 이미 존재(락). DB 이미지가 원본(ori_pdf_path)이면 eval이 전처리도 같이 테스트됨(우리 파이프라인 통과). "원본인가"는 defer. 전처리 보강은 블라인드 X, 증거(통째실패 문서 UI확인 or 변형 통제실험) 후 신중히.

**Deferred(실데이터 와야, 추측금지):** ①product_code 의미(인쇄코드 vs ERP) ②brcd_name 의미(거래처명 vs 지점명) ③page-spanning(separate_img=논리적송장 1:1?) ④저장이미지 원본/처리본. 코드에 가시화만(extNotAttempted 경로 등), 실데이터 대기.

**P0 thin-ready 빌드 COMPLETE (2026-06-10):** §6.6 step 0~6 TDD red→green 전부 빌드+게이트 통과. **게이트 2개 동시 green: `python eval/p0_thin_check.py`(11/11) + `python eval/checker.py`(7/7 rich 6장).** 핵심 산출물:
- `contract.py` = SSOT(THIN_SCALAR(10)/THIN_ROW(6)/NEW_3/RICH_ONLY(7) + `TESTSETS` 레지스트리{invoice_study rich·live / invoice_thin thin·canned} + required_scalar_fields/enforce_per_sample/THIN_LOW_CONFIDENCE_FIELDS). 커버리지 오라클: (THIN_SCALAR−NEW_3)∪RICH_ONLY==ALL_SCALAR_LABELS(14).
- `gen_thin_fixture.py` = 6 rich GT 다운프로젝션(추측값0) → `eval/fixtures/invoice_thin/{GT,rec}`. canned(이미지·서버 불요).
- load_gt(path,**profile**) 주입(⓳' 콘텐츠추론 폐지→checker 일관성검사로 강등) / rowIndex optional(⓫) / per-sample rich-gate(➋) / scored=gt.keys()(➊⓭) / GT제공키 셀(⓰) / 내용기반 행정렬(B)+rich rowIndex oracle 43/43 100%(➏) / normalize 신규3+이름휴리스틱(➍) / difficultySplit(➐)+coverage 2분모(➌E) / checker --testset(➑➓⓬ literal13제거) / **양방향 oracle(rich다운프로젝션 thin vs rich-path 공유필드·셀 verdict 일치)**.
- 1커맨드: `eval/run_all.py --reuse <rich_ts>`(rich) / `eval/run_all.py --testset invoice_thin`(thin canned, 서버불요) 둘다 MVP GO. 백업 `ocr-server/backup/*_20260610_p0step*`.
- 의미: thin DB GT가 와도 **하니스 무수정 드롭인** 준비됨. 남은 건 Phase 7 실 ETL GT(데이터)·Phase 6 사용자 GT.

**How to apply:** 새 채팅방에서 하니스 작업 시 위 문서(§6.6) 읽고 — Phase 0~5 MVP done, **§6.6 P0 thin-ready도 빌드 완료(2026-06-10).** 다음 = Phase 6(사용자 GT) 또는 Phase 7(실데이터 ETL). 게이트 회귀확인은 `p0_thin_check.py`+`checker.py` 동시 green. 추측 금지(deferred 4개는 데이터 와야).
