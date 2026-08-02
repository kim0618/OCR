---
name: project_invoice_column_matching_complete
description: "거래명세서 우리컬럼=GT컬럼 매칭 완성 (C1 스칼라 emit + C2 header-anchored pharma fill). thin 필드 31→46.5%, 회귀 0"
metadata: 
  node_type: memory
  type: project
  originSessionId: d6421aa9-6d52-4b4f-8f72-44a5decc4782
---

2026-07-02. 첫 2천장 AWS run(061, invoice_thin 2004장) 분석 → 컬럼 매칭을 **룰 작업 전에** 먼저 완성(사용자 지정 순서: 컬럼정리→룰). replay_compare로 로컬 측정(재-OCR 없이 파서만).

**근본 진단:** free 파서가 표 컬럼을 뭉갬(제조번호→spec, 코드→itemName 블롭)이 아니라, OCR은 열을 이미 x분리해 읽었고 **헤더까지 인쇄됨**. 문제=free가 헤더를 안 씀. 벤더마다 컬럼 순서 다름(보험코드 앞/뒤/없음) → 위치고정=오버핏, **header-anchored(각 장 자기 헤더로 x경계)만 일반화**. 스냅샷 2002장 전수: 표헤더 검출 78%.

**C2 = pharma 컬럼 fill (manufacturingNo/insuranceCode/expiryDate):**
- `_extract_header_anchored_table`(헤더밴드 강신호≥2 → 라벨→표준키 별칭表 → 행 amount앵커 → Voronoi x배정) + `fill_pharma_columns`(빈칸만 채움, 타입클리너로 병합셀서 정답토큰 추출: 날짜/8-11digit/alnum배치). `fill_scalar_defaults`와 함께 **main.py 합류점(sanitize 직후, free+fallback 무관)** + `replay_compare.replay_dispatch`에 배선. 위치: `extractors/invoice_statement_free.py`.
- **whole-table 교체는 실패**(필드 −1pp·수량/단가 mislocate +2500·itemName 코드접두 회귀) → **fill(빈칸만)로 전환**해 회귀 0. 커버 ~32% 문서(헤더×정렬), fallback 경로도 커버(run061 fallback 1656>free 346이라 필수). 셀 11.9→12.4%.

**C1 = 미emit 스칼라 default:** `taxType='과세'`(GT 100%존재, 과세86%→측정 87%, 면세는 full_text 감지불가=후속), `discountAmount='0'`(GT 99%존재, '0'이 90%→측정 90%). **documentNumber는 GT 0%(invoice_num 전부 '0'/blank)라 emit 금지**(스퓨리어스만). spurious 0 확인. → thin 필드 **31.0→46.5%(+15.5pp)**.

**게이트/안전:** study(rich, 24장)=**회귀 0**(75.4/90.1 동일) — rich GT는 taxType/discount/mfg 키 없어 스코어러(`scored_labels=GT키만`)가 무시, expiryDate는 빈칸만 채워 미덮어씀. 소표본 study가 whole-replace 회귀를 즉시 잡아냈음(가드레일 작동).

**남은 것(=룰 작업, 컬럼 아님):** C2 커버리지 32%↑(헤더검출·행정렬·itemName 위치추론), 수량/단가 mislocate, 행세그, 면세 벤더감지. itemCode/itemNameMaster=마스터매칭 몫(별도). [[project_baseline_matrix_stages]] [[project_invoice_column_gaps]] [[project_ocr_snapshot_replay]] [[feedback_no_speculation_use_run_data]]
