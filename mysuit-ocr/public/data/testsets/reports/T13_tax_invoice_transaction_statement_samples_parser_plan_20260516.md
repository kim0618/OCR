# T-13 tax_invoice / transaction_statement 샘플 추가 및 parser 분기 준비 결과

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `mysuit-ocr/public/data/testsets/tax_invoice/manifest.json` | 신규 생성 (placeholder 1건 포함) |
| `mysuit-ocr/src/lib/testsets.ts` | TESTSETS 배열에 tax_invoice 추가 |
| `mysuit-ocr/src/components/test/TestWorkspace.tsx` | DEFAULT_TESTSETS, DOC_TYPE_ORDER/LABEL/COLOR/ABBR에 tax_invoice/transaction_statement 추가 |

## 2. 신규 샘플/manifest

| filename | documentType | difficulty | qualityTags | expectedStatus | 비고 |
|---|---|---|---|---|---|
| tax_invoice_sample_placeholder.jpg | tax_invoice | medium | [] | selected | PLACEHOLDER — 실제 이미지 없음 |

> ⚠ 현재 실제 세금계산서 샘플 이미지가 없어 placeholder 항목으로 구조만 준비했습니다.
> 실제 샘플 추가 시 manifest.json의 placeholder 항목을 교체하고, 이미지 파일을 `public/data/testsets/tax_invoice/` 에 저장하세요.

### tax_invoice manifest 구조

- `tableExpectedColumns.required`: itemName, quantity, unitPrice, supplyAmount, taxAmount
- `tableExpectedColumns.optional`: rowIndex, spec, remark, amount, totalAmount
- display labels: 일자/품목/규격/수량/단가/공급가액/세액 (세금계산서 표준 컬럼)
- `expectedRowCount`: 1 (placeholder — 실제 샘플 추가 시 업데이트 필요)

## 3. profile / documentType 연결 확인

| documentType | profile base | UI 표시 | 색상 | 약어 | 확인 |
|---|---|---|---|---|---|
| tax_invoice | document | 세금계산서 | #b45309 (갈색) | 세금 | ✓ |
| transaction_statement | document | 거래전표/계산서류 | #92400e (진갈색) | 전표 | ✓ (샘플 없음) |

두 타입 모두 `profiles.ts` DOCUMENT_TYPE_PROFILE_MAP에 `{ base: "document" }` 로 등록되어 있어 Test UI documentType 집계 및 RunAll export/diff가 자동 지원됩니다.

## 4. OCR 1차 결과 요약

실제 세금계산서 이미지가 없어 실제 OCR 실행 결과는 없습니다.
도메인 지식 기반 예측 분석:

| 항목 | 예상 OCR 결과 | 현재 invoice_statement 재사용 가능성 |
|---|---|---|
| 공급자/공급받는자 | 사업자번호, 상호, 대표자, 주소 | ✓ (현재 extractor가 party block 처리) |
| 작성일자 | YYYY.MM.DD 형식 | ✓ |
| 공급가액 | 숫자 형식 | ✓ |
| 세액 | 공급가액의 10% | ✓ |
| 합계금액 | 공급가액 + 세액 | ✓ |
| 품목표 | itemName/수량/단가/공급가액/세액 | △ (테이블 구조는 재사용 가능하나 세금계산서 특유 컬럼 처리 필요) |

## 5. tax_invoice parser 후보

### 필요한 필드 (세금계산서 특유)
- `issuanceDate`: 작성일자 (세금계산서 발행일)
- `supplierRegistrationNumber`: 공급자 등록번호 (사업자번호)
- `supplierCompany`, `supplierRepresentative`, `supplierAddress`
- `buyerRegistrationNumber`: 공급받는자 등록번호
- `buyerCompany`, `buyerRepresentative`, `buyerAddress`
- `supplyAmount`: 공급가액 합계
- `taxAmount`: 세액 합계
- `totalAmount`: 합계금액 (= supplyAmount + taxAmount)
- `tableRows`: 품목별 일자/품목명/규격/수량/단가/공급가액/세액

### 기존 invoice_statement 로직 재사용 가능성

| 기능 | 재사용 여부 | 비고 |
|---|---|---|
| party block 추출 (supplierCompany, buyerCompany 등) | ✓ 높음 | 세금계산서도 좌우 공급자/수신자 블록 구조 동일 |
| amount 추출 (supplyAmount, taxAmount, totalAmount) | ✓ 높음 | 금액 추출 로직 공유 가능 |
| tableRows (품목표) | △ 중간 | 컬럼 구조 유사하나 '일자' 컬럼이 rowIndex 역할 특이 |
| documentType routing | △ 중간 | classify_document가 현재 invoice_statement로 분류할 가능성 높음 |

### 별도 extractor 필요성
- **1차 판단**: invoice_statement extractor 기반으로 tax_invoice 전용 분기를 추가하면 됨
- 새 파일 `tax_invoice.py` 생성보다 invoice_statement.py에 `if doc_type == "tax_invoice":` 분기 추가가 효율적
- 단, OCR 로직 안정화 단계이므로 extractor 수정은 별도 작업으로 분리 (T-14 이후)

## 6. transaction_statement parser 후보

### transaction_statement의 정의 결정
- 현재 `invoice_statement`가 거래명세서를 담당하고 있어 **역할 중복 위험**이 있음
- 다음 중 하나로 사용 방향 결정 필요:

| 사용 방향 | 적합성 | 설명 |
|---|---|---|
| 거래명세서 변형 (invoice_statement 하위) | 낮음 | invoice_statement에 이미 여러 subtype 있음 |
| 은행 거래내역서 | 낮음 | finance_slip으로 처리하는 것이 적합 |
| 계약서/계약명세서 | 중간 | 별도 documentType 필요할 수 있음 |
| 예비 타입 (forward-compatible) | **높음** | 실제 사용 시나리오가 명확해지면 지정 |

**T-13 결정**: `transaction_statement`는 현재 forward-compatible 예비 타입으로 유지.
실제 샘플이 확보되면 재분류 예정. 현재 TestWorkspace에는 UI label만 추가됨.

### invoice_statement와의 차이점
- invoice_statement (거래명세서): 납품/배송 내역, 수량/금액 중심
- transaction_statement (잠정): 거래 내역서/정산서 계열, 정의 미확정

## 7. Test UI / RunAll / export 영향

| 기능 | tax_invoice | transaction_statement |
|---|---|---|
| DOC_TYPE_ORDER | ✓ 추가됨 (invoice_statement 다음) | ✓ 추가됨 |
| DOC_TYPE_LABEL | "세금계산서" | "거래전표/계산서류" |
| DOC_TYPE_COLOR | #b45309 (갈색) | #92400e (진갈색) |
| DOC_TYPE_ABBR | "세금" | "전표" |
| docTypeSummary 집계 | ✓ (샘플 추가 시 자동 반영) | ✓ (샘플 추가 시 자동 반영) |
| RunAll JSON/MD export | ✓ (documentTypeSummary 포함) | ✓ |
| diff tool | ✓ | ✓ |

### 현재 제한
- `tax_invoice/` 에 placeholder 이미지가 없어 RunAll 시 "이 테스트셋에 이미지가 없습니다" 표시 예상
- 실제 이미지 파일을 `public/data/testsets/tax_invoice/` 에 추가하면 자동으로 검출/실행 가능

## 8. 검증 결과

- typecheck: **passed** (0 errors)
- build: **passed**
- profiles.ts 연결: ✓ (tax_invoice, transaction_statement 모두 `{ base: "document" }` 매핑)
- OCR regression: 없음 (추출 로직 미수정)

## 9. 다음 작업 판단

### 현재 상황
- tax_invoice testset 인프라 준비 완료
- 실제 세금계산서 샘플 이미지 없음 → **샘플 확보가 우선**

### 권장 우선순위

1. **샘플 확보 먼저** → 실제 세금계산서 이미지(1~3장) 를 `public/data/testsets/tax_invoice/`에 추가 후 RunAll 실행
2. **OCR 결과 분석 후 parser 설계** → 어떤 필드가 자동 추출되는지 확인
3. **invoice_statement extractor 분기 추가 (T-14)** → `doc_type == "tax_invoice"` 분기로 세금계산서 특화 처리
4. **qualityTags × missing field 교차 집계** (기존 샘플 기반으로 즉시 가능)
