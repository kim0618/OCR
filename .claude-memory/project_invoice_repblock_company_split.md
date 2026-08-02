---
name: project_invoice_repblock_company_split
description: "CPU 스윕 1번 — company '법인명 대표 성명' 분리 + 대표앵커 성명 우선. 4.pdf company+rep 동시회복, 커밋가능"
metadata: 
  node_type: memory
  type: project
  originSessionId: c5a03213-4e0e-40c0-add3-ebc64dddd396
---

**스윕 1 (블록 분절 클래스), run 031 vs 029 게이트 통과·커밋가능 (2026-06-15):**

전략=GPU 이관 전 CPU(파서) 최대 회수. 작업단위="클린 PDF·free 경로에서 값은 OCR에 읽혔는데 파서가 오배정한 손실"(byPath free 필드79% vs fallback56%의 격차 중 분절분). 전처리 orientation(A)은 로컬 종착=GPU 몫이라 다음 우선순위는 파서 분절(B).

**supplierRep 35% 전수분해 핵심:** 13 불일치 중 룰대상은 사실상 **4.pdf 1건**. 라카운트 함정 제거 — 3.x(최정숙→최정)는 파서 절단 아니라 **OCR가 '숙' 안 읽음**(sample rawText="성명최정", 클린 3.pdf도 동일) = 인식바닥, 룰 아님. 1.x(영문명)·4-2·5-2/5-3 = 인식 garble. → supplierRep 천장은 OCR 바운드(GPU/모델), 룰로 못 올림.

**확정 파서버그 (4.pdf, 클린 PDF):** `supplierCompany="주식회사엘비아브노바대표남이레"`(대표명이 상호칸 흡수) + `supplierRepresentative="무역업,건강보조식"`(업태/종목이 대표자칸). 원인2: ①`_clean_company_candidate`(invoice_statement.py:405)의 `주식회사[…]{1,24}` 스팬이 '대표남이레'까지 흡수. ②`_is_representative_candidate`(:3254) 이름패턴 `[가-힣]{2,5}(?:[,/]…)?`가 '무역업,건강보조식'을 이중대표명으로 오인.

**패치 (extractors/invoice_statement.py, 백업 `backup/invoice_statement_20260615_170925_before_repblock_company_split.py`):**
- B1 `_split_representative_from_company(party)` 신규(_clean_representative_candidate 뒤): company에서 `(.+?)(대표이사|대표자|대표|성명)…(name)$` 분리, base=`_candidate_ok(.,"company")` ∧ name=`_is_representative_candidate` 이중검증, company=base로 갱신·name 반환.
- B2 `_extract_party_fields`의 `_dedupe_cross_party_representative` 직전: 양 party에 B1 적용, split 성명 있으면 **무조건 채택**(always-win, 대표앵커라 약한 현재값 덮음). debug=`company_split.representative`.

**실패→정정 (run 030, 중요):** 1차엔 A(=`_is_representative_candidate`에 `[가-힣]{1,4}업(?:[,/]|$)` 거부 가드)도 넣었다가 **net-zero+회귀**. company +1이나 ①4.pdf rep는 B2 가드(`not _is_representative_candidate(current)`)가 약한오인값 "상효"를 유효로 보고 남이레 못 덮음 ②**4-1(free) 회귀: A가 후보리스트서 "무역업…" 제거→free 경로 위치기반 `reps[pos]`(:3679) 인덱스 밀림→남이레가 supplier슬롯 이탈→empty.** → **A 제거 + B2 always-win**으로 수정(run 031): A없이도 B2가 남이레로 덮어 해결, 위치교란 사라져 4-1 복귀. **교훈: 위치기반 `reps[pos]` 선택은 후보 add/remove에 취약 — validator 손대면 free 경로 회귀 점검 필수.**

**결과 run 031:** supplierRep 35→40%, supplierCompany 75→80%, 필드 micro 62.3→63.1%, 셀 불변, 회귀0(rep match 7→8=4.pdf획득∧4-1보존, 타필드 비트동일). 커밋가능. 헤더 추출 `_extract_party_fields`는 free/fallback 공용(path 라벨은 표 추출 기준). 다음=스윕2 cross-party 주소 P3-c(4.pdf buyer주소=공급자주소 prepend + supplier주소 절단). [[project_preprocess_image_deskew_gap]] [[project_eval_loop_strategy]] [[feedback_analysis_prioritize]]
