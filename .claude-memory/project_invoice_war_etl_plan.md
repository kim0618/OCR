---
name: project_invoice_war_etl_plan
description: 수천장 실데이터(bak.war Postgres) 도착 시 ETL/배치/테이블 사용 계획 — 형식·저장위치·테이블 역할·순서. 데이터 오면 이거대로 진행
metadata: 
  node_type: memory
  type: project
  originSessionId: 4fd030ef-ed0b-454f-9bb7-4d813e8f8977
---

2026-06-22 확정. 거래명세서 수천장 실데이터 = **bak.war의 PostgreSQL DB**(`jdbc:postgresql://...:54322/bjocr`, 사용자 `bjocr`). [[project_learn_loop_infra_plan]] Phase 7 실행계획.

**도착 형식:** 이미지 = zip. DB = **pg_dump 전체 덤프(CSV 아님 — JOIN·스키마 보존이 핵심).** `pg_restore`로 로컬 Postgres 복원 → 그 위에서 ETL. 이미지 수십GB라 **일부만** 가져옴(정상): manifest가 이미지 없는 GT는 `gt_orphan`으로 자동 스킵, ETL은 가져온 이미지에 매칭되는 GT만 산출. 표본은 **brch_cd·레이아웃 분산**(한 코너 쏠림=일반화 편향).

**저장 배치(결정):**
- 이미지+GT = `ocr-server/eval/data/invoice_war/`(이미지 평면 + `GT/*.json`). **`.gitignore`에 `ocr-server/eval/data/` 추가됨** → git 추적 안 함.
- 이미지는 git 아님 → **별도 업로드(zip→S3/scp)로 AWS에 전달.** GT json(작음)은 ETL 산출 → AWS `GT/`로 sync.
- 신규 **thin/live testset(`invoice_war` 등)** `contract.py TESTSETS`에 등록. **24장 study(rich)는 분리 유지=회귀 앵커**(섞이지 않음, latest_run이 testset 필터).
- **AWS에 DB 안 띄움**(run은 DB 안 보고 이미지+GT만 소비). 로컬 복원본은 ETL 재실행·마스터매칭에 쓰니 **유지**(덤프 보관 + 복원본 유지/재복원).

**★ DB가 thin 계약을 통째로 채움:** 추출기가 못 뱉어 "정직한 miss"로 둔 NEW_3(discountAmount/documentNumber/taxType)가 DB엔 다 있어 **채점 가능해짐**.

**ocr.xml = 실제 Postgres 스키마(MySQL 아님).** `_waranalysis/WEB-INF/classes/mybatis/mapper/ocr.xml`. 매핑 확정:

**테이블 역할 + thin필드 매핑:**
- `tbl_ocr_invoice_master` = GT 척추(스칼라 + 이미지페어링 + JOIN키). total_amount→totalAmount · total_vat_price→taxAmount · total_dc_price→discountAmount · invoice_num→documentNumber · publish_date→issueDate · cust_biz_num_final(검증값)→supplierBizNumber · cust_biz_num_receive→buyerBizNumber · tax_yn→taxType · brcd_name=저신뢰 supplierCompany raw · **separate_img_path=이미지 페어링키(sourceFile)** · cust_cd/brch_cd=JOIN키. PK idx.
- `tbl_ocr_invoice_body` (invoice_master_idx FK) = 행 GT. description→itemName · quantity · unit_price→unitPrice · amount · exp_dt→expiryDate · prod_no→manufacturingNo. product_code=defer(인쇄코드 vs ERP 불명).
- `tbl_ocr_master_buycust` (cust_cd JOIN) = 회사명 cust_nm·주소 cust_address 보강(`source:master` 태그) + 거래처 매칭 사전.
- `tbl_ocr_master_item` (item_cd) = 품목 사전(SIMILARITY pg_trgm + fn_get_item_name_clean, bp1_amt 표준단가) → 마스터매칭 개선단계.
- `tbl_ocr_master_brch` (brch_cd) = 지점 사전, 매칭 스코핑(거의 모든 쿼리가 brch_cd 분할).
- `tbl_ocr_learndata_invoice_modify` = ★사람보정 정답쌍(ocr_item_nm→user_item_cd→item_nm). 용도: 매칭 룰 검증(learn_count 신뢰도) + **파인튜닝 코퍼스 seed**([[project_finetune_ledger_infra]]) + canonical 품목명.
- `tbl_ocr_process_log(_detail)` = 운영로그(process_result S/F·msg) → 난이도/오류 슬라이스(보조, 필수아님).

**사용 순서:** P1 GT생성(master+body, buycust/brch JOIN → `GT/*.json`)=**측정 시작점** → P2 사전적재(item/buycust 매칭, 개선단계②) → P3 learndata(매칭검증+파인튜닝, 개선단계②~③) → P4 process_log(품질 슬라이스, 보조).

**데이터 와서 확인할 3가지(추측 금지):** ①cust_cd 당사자(매입송장이면 cust=공급자→supplierCompany, 자사=buyer→cust_biz_num_receive) ②product_code 의미 ③separate_img_path 파일명 ↔ 가져온 이미지 zip 파일명 일치.

[[project_learn_loop_infra_plan]] [[project_eval_loop_strategy]] [[project_data_storage_architecture]] [[project_finetune_strategy_and_corpus]]
