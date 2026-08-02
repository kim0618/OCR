---
name: project_free_vs_template_gaps
description: 거래명세서 free(완전비정형) vs template 파서 격차 분석 — free의 OCR 해상도 비대칭 등
metadata: 
  node_type: memory
  type: project
  originSessionId: b49ee55a-fb22-48a0-addb-dedb932d0471
---

거래명세서 free(invoice_statement_free.py) vs template(invoice_statement.py) 심층 비교 (2026-06-10, 코드 검증).

**🔴 결정적: OCR 해상도 비대칭.** free 경로는 **950px 다운스케일** 이미지를 OCR(main.py:2549 `ocr_max_w=950` → 2586 `ocr.ocr(ocr_img)`). template 경로는 **풀사이즈** OCR(main.py:2341 `ocr.ocr(img)`, 주석 "full-image OCR"). → 품명 글자오류(헥사메딘→헥사메던)는 OCR 모델 한계가 아니라 **free가 저해상 입력을 쓰기 때문**. 같은 엔진, 다른 해상도. "OCR 모델 영역이라 못 고침"은 틀린 진단.

**① 공통인데 free가 안 쓰는 것:** (a) 고해상 표-크롭 재OCR `_ocr_table_region`(main.py:1648, 템플릿 경로만, 현재 파서 아닌 UI table_data만 채움), (b) 헤더/컬럼 별칭 인식 `_EXPECTED_COLUMN_ALIASES`(invoice_statement.py:276)+컬럼경계 `_build_boundaries_from_column_guides`(:2333) — free는 x좌표 위치로만 컬럼 잡고 레퍼런스 표결과는 버림(REFERENCE_SCALAR_MERGE_EXCLUDED_KEYS). party 필드는 이미 backfill로 공유(gap 아님).

**② 필요한데 없는 것:** (a) free 고해상 OCR 입력, (b) **사전/마스터 대조 교정 — free·template 둘 다 없음**(인식오류=최대버킷 공략수단, 제품마스터 필요), (c) OCR 신뢰도 활용(둘 다 읽기만 함).

**P1 실측 완료(2026-06-10, eval/diag_ocr_resolution.py, 1.jpg 28품명):** 950px 20/28 vs 풀사이즈 21/28. 풀사이즈가 **작은글자 오류 4건 해결**(헥사메딘/부스론/켈론/프레가스타 — 진짜 해상도 효과 확정). 단 순증 +1뿐: 풀사이즈가 깨뜨린 3건 중 2건은 GT 유사품명쌍 충돌(이소맥/이소액, 메티마졸/메티마줄=OCR회귀 아님), 1건은 단위글자. **결론: 인식오류=해상도(일부)+사전대조(나머지). 전체 풀OCR은 느리고 순이득 작음 → 올바른 해법은 표-크롭 고해상 재OCR(_ocr_table_region main.py:1648 존재하나 free 미배선). 풀사이즈에서도 안잡히는 것(하드칼추어블/아젭틴/나딕사/뮤코론캡)=사전대조 필요.** 원본 1.jpg=2483x3511, free는 950px(0.38배 축소).

**R002 구현·실측 완료(2026-06-11): 표-크롭 고해상 재OCR을 free에 배선했으나 net-negative → 기본 OFF.** 코드: `extractors/table_region.py`(derive_table_bbox 순수함수, 테스트 eval/test_table_region.py) + main.py invoice-free 분기(additive·env게이트 `FREE_HIRES_TABLE_REOCR`, 기본 OFF). 6장 probe(003 run): 품명 +4(뮤코론캡슐/부스론/켈론/프레가스타)/-3(이소맥·단위ng→mg·규격"12000SE"가 품명칸 번짐), **셀 88.7→88.0%(-0.7pp)** + OCR 2패스 지연. 교훈: 고해상=무조건 낫다 아님(비슷한획 글자 오히려 틀리고 재구성이 인접컬럼 번짐). **루프가 회귀를 막아냄**(측정없이 ON배포시 회귀였음). 기본OFF=production 무영향=baseline 자동안전. 수천장 단계에서 ①재구성 컬럼번짐 보강 ②해상도 스윗스팟 튜닝 후 =1로 재측정. 백업 backup/main_20260610_R002_before_free_hires_table_reocr.py.

**헤더/컬럼 이식(P3) 판단 완료(2026-06-11): 이식 불필요 — 측정으로 확정.** 같은 1.jpg 950px 토큰으로 컬럼 정확 대조(eval/probe_header_mapping.py): **free 126 vs template(헤더매핑) 50 vs template+expected_columns힌트 1 (/140)**. 템플릿 파서는 비정형 raw 토큰에선 itemName=0·단가+금액 뭉갬, 힌트줄수록 더 무너짐(per-form 컬럼좌표 있어야만 작동). **free 위치추론 파서가 무템플릿에선 2.5배 우수.** 또 free는 6장 전체 컬럼밀림(layout)=0 — 고칠 컬럼문제 자체가 없음. itemName 미스(20/28)는 컬럼아니라 OCR글자(해상도). **결론: template↔free 인식률差의 출처 = 파서아님, OCR입력(해상도)+per-form좌표(비정형엔 정의상 없음). 이식할 파서능력 없음.** 안전성검증(import순수·columnar충돌없음·additive)도 했으나 가치가 음수라 미실행.

**거래명세서 전용 해상도 스윕 판단 완료(2026-06-11, eval/probe_invoice_resolution.py):** 950px는 영수증용 전역값이라 거래명세서가 발목잡혔다는 가설 → **측정상 거짓.** 1.jpg를 free파서로 950/1400/1900/full 스윕한 컬럼정확: **950=126(최고,41.8s) · 1400=120(-6) · 1900=126 · full=126(52.4s).** 950이 이미 최적(동률)+최速. 풀해상 raw토큰이 글자 더 맞아도 파서 거치면 사라짐. **결론: 950px=영수증용이 아니라 이 모바일OCR모델의 거래명세서 최적점. 해상도 레버 완전히 닫힘.** 단 `_is_unstructured_template`(main.py:2079)은 해상도단계(2549) 前 결정되므로 거래명세서 전용 해상도 분기는 *기술적으론* 가능(불필요).

**해상도 레버 3번 측정 다 null/음수:** R002 표크롭고해상=-0.7pp · 풀페이지고해상=950과 동일(net-zero) · 파서이식=126→50. **거래명세서 품명 글자오류(헥사메딘→헥사메던)는 해상도/파서로 못고침. 남은 유일 레버=제품마스터 사전대조 교정(데이터 단계).**

**⚠️ 구분 정정 (2026-06-15, 사용자 지적 + 검증):** 위 "못고침"은 **표 안 품명 글자오류(인식)** 한정. **party/상단 스칼라 필드(사업자번호·상호·대표자·주소)의 누락은 별개 = 파서 위치추정·배정 실패 = CPU에서 고침.** 검증: 3.pdf buyer 사업자번호 `113-85-04425`가 950px OCR에 **이미 읽혔는데** 추출 빈값(단일-biz 배정 실패, 3.pdf=landscape 1654x1169). 템플릿(같은 모델)은 좌표로 다 가져옴. P1(raw biz 배정)·P3-a(cross-party)·P3-b가 이 종류였고 **더 남음**(단일-biz/landscape party 검출 등). 즉 "인식 못함=floor"로 뭉뚱그리지 말고 **읽힘(파서)vs안읽힘(인식)** 갈라서 — 읽힌 건 파서로 CPU에서 줍는다. [[feedback_no_speculation_use_run_data]]

**검증 승리 (2026-06-15, run 024 vs 023): 위 방법론으로 +7pp·회복17·회귀0.** 진단: 3-패밀리(3.pdf landscape)가 party 통째 누락 → invoice_statement 디버그 `party_candidates.bizs=[]`(사업자번호 후보0) 인데 OCR full_text엔 존재 → **OCR가 `113=85-04425`로 읽음(대시-를 =로 오인)**, `_BIZ_RE` 구분자 `[-\s.]`가 `=` 거부 → 매칭실패 → bizs0 → party split 전체 실패. **수정: `_BIZ_RE` 구분자 `[-\s.]`→`[-=~\s.]`**(invoice_statement.py:6, OCR 대시오인 일반화). + eval 타임아웃 300→600(run_batch.py, 28행 변동성 드롭 방지). **결과: 필드 54.5→61.5%, 3-패밀리 buyerBiz 전부 ext_missing→match, 1-2복귀, 회귀0, base+1.** 백업 `invoice_statement_20260615_before_bizsep_dashconfusion.py`. **교훈 재확인: party/스칼라 누락은 floor 아님 — OCR가 읽은 값을 정규식/위치가 거부하는 파서 문제, CPU로 줍는다. 진단법: extract_debug.invoice_statement(party_candidates.bizs/companies, header_limit_y) + full_text에 GT값 있나.** 남은 worklist: 4-2/4-3(상호·주소), 6-2/6-3(orientation별건), supplierBiz 일부(572-81-01750 읽힘 확인 필요). [[project_eval_loop_strategy]] [[project_eval_loop_strategy]] [[feedback_analysis_prioritize]] [[project_invoice_3bd_4pdf_supply_tax]] 참조.
