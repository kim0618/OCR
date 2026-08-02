---
name: project_invoice_war_db_restored
description: war DB(bjocr) 로컬 복원 완료 + 6월 GT 생성 완료. 마스터매칭/GT 작업의 현재 상태와 접속·산출물 위치
metadata: 
  node_type: memory
  type: project
  originSessionId: 643d94e6-d9a2-497c-8aad-f5a1d285e5b7
---

2026-06-24. 경쟁사(백제약품) war DB 덤프를 **로컬 PostgreSQL 17에 복원 완료**. [[project_invoice_war_etl_plan]]의 실행 단계 진입.

**접속:** PG17 `C:\Program Files\PostgreSQL\17\bin`, db=`bjocr`, user=`postgres`, pw=`root123`, localhost:5432. 덤프=`C:\Users\jinsung\Desktop\[신규] 프리세일즈\1_OCR\bjocr.dump`(567MB, PGDMP custom, PG16.4 origin). psql 네이티브라 한글경로=call operator·별칭 ASCII·`$env:PGCLIENTENCODING="UTF8"`.

**테이블(행수):** invoice_master 572,235 / invoice_body 3,743,273 / master_item 38,848(item_cd→item_nm,unit,bp1_amt=사입가) / master_buycust 14,954(cust_cd→cust_nm,cust_address) / learndata_invoice_modify 214,891(ocr_item_nm→user_item_cd+user_item_order_amt = **OCR원문→정답 라벨셋**). 확장 pg_trgm·fuzzystrmatch, 함수 fn_get_item_name_clean(괄호만 제거).

**✅ 6월 GT 완료:** `OCR/ocr-server/eval/data/invoice_war/ground_truth_2606.json`(23,737이미지/150K라인). 생성기 `build_gt.sql`(재사용, `-v mon=2606`). 키=`<하위폴더>/<파일명>`(파일명만은 796건 충돌). **itemName=마스터 정식명 item_nm**(폴백 description) — 사용자 결정. spec=st, 회사/주소=master_buycust JOIN. **documentNumber 제외**(6월 전량 "0" placeholder). taxType/discountAmount는 진짜데이터 확인. data폴더 gitignore.

**war 자동채움 = 우리가 복제할 매칭:** 품목명/거래처/사번=매칭자동채움, 금액/수량/단가/날짜=원본OCR. 캐스케이드(ocr.xml): learndata(L_N) → clean+LIKE → SIMILARITY(트라이그램), 공통 2차정렬 **ABS(bp1_amt−단가)=단가 타이브레이크**(동명이품 구별). item_match_type=L_N/NM_L/SIMILAR.

**이미지 없음:** 전부 `Z:\LIVE\processed\<YYMM>\<하위폴더(1img)>\<file>`. 사용자가 폴더복사 예정. 추천=`2606`(6월,23,737장=사전53%커버) 먼저, 부족시 2605 추가.
