---
name: project_invoice_column_gaps
description: 거래명세서 추출 스키마에 추가해야 할 컬럼 갭 목록 (경쟁사 bak.war 대비 분석 결과). documentNumber 등 미보유 표준컬럼
metadata: 
  node_type: memory
  type: project
  originSessionId: 068550ef-1295-415a-828f-127ace19a9eb
---

2026-06-09 경쟁사 `bak.war`(백제약품 OCR, Google Document AI 기반) 컬럼 셋과 우리 `OCR/ocr-server/extractors/invoice_statement.py` 컬럼을 대조한 결과, **추가해야 할 표준 컬럼**이 확인됨. 아래 항목은 우리 코드 역검색 결과 전부 0 hits = 진짜 미보유.

**추가 대상 — 표준컬럼(문서레벨), 우선순위순:**
- `documentNumber` ★1순위 — 전표번호/명세서번호/세금계산서 승인번호(국세청 24자리). 모든 전표 공통인데 우리만 통째 누락. (bak.war `invoice_num`)
- `taxType` ★ — 과세/면세/영세 구분 (bak.war `tax_yn`)
- `discountAmount` ★ — 할인/에누리 금액 (bak.war `total_dc_price`)
- `supplierBusinessType`/`supplierBusinessItem` ★ — 업태/종목 (표준 세금계산서 양식)

**추가 대상 — 테이블표준컬럼(행레벨):**
- `barcode`/`standardCode` — 바코드·제조사 표준코드, 자사 itemCode와 별개 (bak.war `product_code`). 우선순위 낮음

**미포함 유지(추가 안 함):** med_cd(약품 EDI코드)=제약 한정 test-only로만, item_cd/cust_cd/item_match_type/필드별confidence=OCR값 아닌 마스터매칭·메타데이터 영역.

**이미 보유(추가 불필요):** 테이블 18컬럼(lotNo, serialNo, manufacturingNo, expiryDate, manufacturer, insuranceCode=bohum_cd, remark 등) + party 8 + issueDate + 금액3 + 요약6(subtotal/cumulativeAmount/previousBalance/transactionAmount/cumulativeBalance/totalQuantity). 우리 테이블 컬럼이 bak.war body보다 오히려 풍부.

**거버넌스:** [[CLAUDE.md 현재 단계]]는 "OCR 로직 미수정 / invoice parser 추가 보류" → 지금은 스키마 컬럼 목록 확정까지만, 실제 추출 로직은 parser-branching 단계에서. 일반 표준 4종 우선(vendor-specific 금지 방향과 부합).

정의 위치: 테이블컬럼=`_EXPECTED_COLUMN_ALIASES`(KEY_SYNONYMS), 문서요약=`_PROFILE_SUMMARY_FIELD_LABELS`/`_SUMMARY_FIELD_KEYS`, party/amounts=extract 말미 fields.update. 관련 [[project_invoice_1q_column_mapping]] [[project_invoice_unstructured_roadmap]]
