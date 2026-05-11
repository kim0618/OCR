# T-1 invoice_statement tableProfile별 tableRows 컬럼 정책 리포트

작성일: 2026-05-11  
기준 리포트: R-1, R-2, OP-0  
기준 파일: manifest.json (P-2b 상태), ground_truth.json (GT-ADDR 적용 후), ocr_cache.json

---

## 1. 작업 목적

거래명세서 1차 검증셋 7개 샘플을 기준으로 tableRows 정책을 설계한다.  
표의 컬럼 구조를 제품이 이해할 수 있는 공통 tableRows 구조로 정리하고, tableProfile별 표준 컬럼 정책을 정의한다.

코드 수정: **없음**. 리포트 생성만.

---

## 2. 전제

- 고정그리드 / 가변그리드 선택은 **사용자가 Template 탭에서 결정**한다
- T-1은 "이 문서는 고정/가변"이라고 강제 확정하지 않는다
- T-1의 결과물은 추천 기준과 공통 출력 구조이며, T-2/OP-1/Template-Table-1/RunOCR-Table-1의 기준이 된다
- tableRows parser 수정은 하지 않는다
- OCR 인식 로직 수정은 하지 않는다

---

## 3. 현재 샘플 profile 요약

| 파일 | tableProfile | amountProfile | partyProfile | summaryFields | qualityTags |
|---|---|---|---|---|---|
| 1.jpg | multi_item_table | subtotal_cumulative | supplier_buyer | subtotal, cumulativeAmount | (없음) |
| 2.pdf | item_quantity_table | balance_cumulative | supplier_buyer | previousBalance, transactionAmount, cumulativeBalance | (없음) |
| 3.pdf | single_item_table | supply_tax_total | supplier_weak | (없음) | (없음) |
| 4.pdf | single_item_table | supply_tax_total | party_garbled | (없음) | ocr_garbled, party_block_garbled, address_garbled |
| 5.pdf | multi_item_table | supply_tax_total | supplier_buyer | (없음) | (없음) |
| 6.pdf | lot_serial_quantity_table | no_amount_summary | buyer_only | (없음) | no_amount_summary, lot_serial_table, buyer_only_document, optional_supplier |
| 7.pdf | serial_quantity_table | quantity_total_only | buyer_rep_optional | totalQuantity | address_tail_missing, no_amount_summary |

**tableProfile 분포**: multi_item_table(2), single_item_table(2), item_quantity_table(1), lot_serial_quantity_table(1), serial_quantity_table(1) — 총 5종

**관찰**:
- 두 amountProfile이 금액 없는 표를 가진다: no_amount_summary(6.pdf), quantity_total_only(7.pdf)
- single_item_table 두 샘플(3.pdf, 4.pdf)이 다른 컬럼 구성 → 세분화 필요
- multi_item_table 두 샘플(1.jpg, 5.pdf)이 다른 컬럼 구성 → lot/expiry 중심 vs code/amount 중심

---

## 4. 표준 tableRows 컬럼 정의

| canonicalColumn | 한글명 | 의미 | valueType | 필수 여부 | 비고 |
|---|---|---|---|---|---|
| rowIndex | 행번호 | 표 내 행 순서 번호 | number | optional | 미리 인쇄된 행 번호 (1,2,3…) |
| itemCode | 품목코드 | 제품 고유 식별 코드 | code | optional | ERP 코드, 단품 코드 |
| itemName | 품명 | 제품/품목 이름 | text | **required** | 모든 tableProfile에서 필수 |
| spec | 규격 | 제품 규격/용량/포장 형태 | text | optional | 의약품 중심 (15mL×6포 등) |
| lotNo | 제조번호/Lot | Lot 번호, 제조번호 | code | optional | 배치 단위 추적. manufacturingNo와 통합 권장 |
| serialNo | 일련번호 | Serial 번호 (개별 단위) | code | optional | 시리얼/로트No. 복합 식별자 포함 |
| manufacturingNo | 별도제조번호 | lotNo와 구분 필요한 경우 | code | optional | 대부분 lotNo로 통합 권장 |
| expiryDate | 유효기간 | 사용기한/유통기한 | date | optional | YYYYMMDD 또는 YYMMDD 형식 |
| quantity | 수량 | 출고/납품 수량 | quantity | **required** | 모든 tableProfile에서 필수 |
| unit | 단위 | 수량 단위 | text | optional | BOX, EA, T, P, mL 등 |
| unitPrice | 단가 | 개당 가격 | amount | conditional | 금액 있는 tableProfile에서 사용 |
| supplyAmount | 공급가액(행) | "공급가액/공급금액" 라벨 명시 시 행별 금액 | amount | conditional | 컬럼 라벨이 "공급금액/공급가액"인 경우 |
| taxAmount | 세액(행) | 행별 부가세 | amount | optional | 행 단위 세액 명시 시 |
| amount | 금액(행) | "금액" 라벨 명시 시 행별 금액 | amount | conditional | 컬럼 라벨이 "금액"인 경우 |
| totalAmount | 합계금액(행) | 세금 포함 행 합계 | amount | optional | amount + taxAmount (행 단위) |
| manufacturer | 제조사 | 제품 제조사 | text | optional | 의약품 중심 |
| insuranceCode | 보험코드 | 건강보험 약품 코드 | code | optional | 보험코드, 보험NO |
| remark | 비고 | 행별 추가 메모/적요 | text | optional | |

**주의 — amount vs supplyAmount**:
- `amount`: 컬럼 라벨이 "금액"인 경우 (1.jpg, 5.pdf)
- `supplyAmount`: 컬럼 라벨이 "공급금액", "공급가액"인 경우 (2.pdf, 4.pdf)
- 계산식은 동일(수량 × 단가)하나 문서 라벨로 구분
- 문서 단위 합계(총 공급가액)는 tableRows 밖 documentFields에서 처리

**주의 — lotNo vs manufacturingNo**:
- 의약품 거래명세서에서 "제조번호" = lot 번호 (배치 식별자)
- 1~7 샘플에서 별도 lotNo + manufacturingNo 동시 존재 케이스 미확인
- 권장: `lotNo`로 통합, alias에 "제조번호" 포함
- 향후 별도 제조번호 필드 필요 시 `manufacturingNo` 분리

---

## 5. 컬럼 alias 정의

| canonicalColumn | aliases (한글/영문) |
|---|---|
| rowIndex | NO, 번호, 순번, 순서 |
| itemCode | 품목코드, 코드, 상품코드, 제품코드, 단품코드 |
| itemName | 품명, 품목, 품목명, 상품명, 제품명, 약품명, 내역, 품 |
| spec | 규격, 규격명, 포장, 용량, 단위규격 |
| lotNo | Lot, LOT, Lot No, LotNo., 제조번호, 제조번호/로트, 로트번호 |
| serialNo | Serial, S/N, 시리얼, 일련번호, serial, 시리얼/로트No. |
| manufacturingNo | 제조번호(별도), 제조NO |
| expiryDate | 유효기간, 유효일자, 사용기한, 유효기한 |
| quantity | 수량, Qty, QTY, 수, 수량(EA), 출고수량 |
| unit | 단위, 단위규격, EA, BOX |
| unitPrice | 단가, 공급단가, 소비자단가 |
| supplyAmount | 공급금액, 공급가액, 공급액 |
| taxAmount | 세액, 부가세, VAT |
| amount | 금액, 행금액, 합계금액 |
| totalAmount | 합계금액(행), 합계(행) |
| manufacturer | 제조사, 제조원, 제조회사, 회사 |
| insuranceCode | 보험코드, 보험NO, 보험번호 |
| remark | 비고, 적요, 메모 |

---

## 6. tableProfile별 기본 컬럼 세트

| tableProfile | 설명 | 필수 컬럼 | conditional 컬럼 | optional 컬럼 | 비고 |
|---|---|---|---|---|---|
| multi_item_table | 다품목 일반 거래명세서 | itemName, quantity | amount 또는 supplyAmount, unitPrice | spec, lotNo, expiryDate, itemCode, manufacturer, taxAmount, insuranceCode, rowIndex, unit | pharma_lot 패턴(1.jpg)과 code_amount 패턴(5.pdf) 두 가지 존재 |
| single_item_table | 단일 품목 거래명세서 | itemName, quantity | unitPrice, supplyAmount 또는 amount | taxAmount, lotNo, expiryDate, manufacturer, insuranceCode, unit, spec | 1행 전용 폼. 3.pdf(보험/제조사)와 4.pdf(lot/공급가액/세액) 패턴 상이 |
| item_quantity_table | 코드 중심 수량/금액 거래명세표 | itemCode, itemName, quantity | supplyAmount | unitPrice, insuranceCode, taxAmount, amount, remark | 2.pdf 기준. 소비자단가/공급단가 두 종 가능 |
| lot_serial_quantity_table | Lot/수량 중심 세부 내역 | itemName, quantity, lotNo | expiryDate | itemCode, serialNo, unit, rowIndex, remark | no_amount_summary 패턴. 금액 없음 |
| serial_quantity_table | Serial/수량 중심 세부 내역 | itemName, serialNo, quantity | unit | lotNo, itemCode, spec, remark | no_amount_summary 또는 quantity_total_only 패턴 |

**multi_item_table 두 패턴**:
- **pharma_lot** (1.jpg): itemName + spec + lotNo + expiryDate + quantity + unitPrice + amount
- **code_amount** (5.pdf): itemCode + itemName + quantity + unitPrice + amount

두 패턴은 현재 동일 tableProfile 공유. T-2 이후 subProfile 분기 여부 결정.

---

## 7. 샘플별 표 구조 분석

---

### 7.1 1.jpg

**ocr_cache.json 실제 확인 컬럼**: 품목 / 규격 / 제조번호 / 유효기간 / 수량 / 단가 / 금 액

- tableProfile: multi_item_table
- rowCount(GT): 28
- firstRowPreview(GT): "헥사메던액0.12% 15m|*6포"

#### grid recommendation: **fixed (강력 추천)**

추천 이유:
- 28개 행 고정 프레임 (OCR에서 28개 품목 행 확인)
- 행 높이 일정, 반복 가로줄 존재
- 세로 컬럼선 7개가 표 끝까지 유지
- 소계(18,098,750) 위치가 표 하단 고정
- 전체 표 외곽선 존재 (거래명세서 인쇄폼)

#### 실제 컬럼 → canonical 매핑

| 원본 라벨 | canonicalColumn | valueType |
|---|---|---|
| 품목 | itemName | text |
| 규격 | spec | text |
| 제조번호 | lotNo | code |
| 유효기간 | expiryDate | date |
| 수량 | quantity | quantity |
| 단가 | unitPrice | amount |
| 금 액 | amount | amount |

- 필수: itemName, quantity, amount
- optional: spec, lotNo, expiryDate, unitPrice
- 종료 키워드: "소계", "누계" (fixed이라 미사용)

#### firstRowPreview 컬럼 기준: itemName | spec | quantity | amount
예: "헥사메던액0.12% | 15m|*6포 | 400 | 420,000"

#### Template 설정 추천
- 전체 표 영역 드래그 (28행 포함)
- 행 템플릿: 1행 높이 지정
- 세로 가이드: 7개 (품목 / 규격 / 제조번호 / 유효기간 / 수량 / 단가 / 금액)

#### RunOCR 출력 예시 (첫 행)
```json
{
  "rowIndex": 1,
  "itemName": "헥사메던액0.12%",
  "spec": "15m|*6포",
  "lotNo": "24027",
  "expiryDate": "20270205",
  "quantity": "400",
  "unitPrice": "1,050",
  "amount": "420,000"
}
```

---

### 7.2 2.pdf

**ocr_cache.json 실제 확인 컬럼**: 품목코드 / 품목명 / 수량 / 소비자단가 / 공급단가 / 공급금액 / 보험NO

- tableProfile: item_quantity_table
- rowCount(GT): 13
- firstRowPreview(GT): "LOXOLIFEN TABLET 3OT3Z"

#### grid recommendation: **variable (추천)**

추천 이유:
- 텍스트 기반 POS/ERP 출력 스타일
- 13개 행 가변 (주문별 품목 수 변동)
- 종료 키워드 명확 ("공급금액합계", "소비자금액합계")
- 고정 프레임 약함 (외곽선 없이 텍스트 라인만)

#### 실제 컬럼 → canonical 매핑

| 원본 라벨 | canonicalColumn | valueType | 비고 |
|---|---|---|---|
| 품목코드 | itemCode | code | OP-NA0300 등 |
| 품목명 | itemName | text | |
| 수량 | quantity | quantity | |
| 소비자단가 | unitPrice | amount | 소비자가 기준 |
| 공급단가 | unitPrice | amount | 공급가 기준 (두 단가 병존) |
| 공급금액 | supplyAmount | amount | |
| 보험NO | insuranceCode | code | |

주의: 소비자단가/공급단가 두 종 병존. 현재 `unitPrice` 통합. T-2에서 `consumerPrice`/`supplyPrice` 분리 검토.

- 필수: itemCode, itemName, quantity, supplyAmount
- optional: unitPrice (두 종), insuranceCode
- 종료 키워드: ["공급금액합계", "소비자금액합계", "합계", "당일거래금액"]

#### firstRowPreview 컬럼 기준: itemName | quantity | supplyAmount
예: "LOXOLIFEN TABLET 3OT3Z | 300 | 18,295,140"

#### Template 설정 추천
- row 영역: 1행 높이
- 세로 가이드: 7개 (코드 / 품목명 / 수량 / 소비자단가 / 공급단가 / 공급금액 / 보험NO)
- 종료 키워드: "공급금액합계", "합계"

#### RunOCR 출력 예시 (첫 행)
```json
{
  "rowIndex": 1,
  "itemCode": "OP-L00500",
  "itemName": "LOXOLIFEN TABLET 3OT3Z",
  "quantity": "300",
  "unitPrice": "30,360",
  "supplyAmount": "18,295,140"
}
```

---

### 7.3 3.pdf

**ocr_cache.json 실제 확인 컬럼**: 보험코드 / 품목 / 수량 / 단가 / 제조번호 / 유효기간 / 제조회사

- tableProfile: single_item_table
- rowCount(GT): 1
- firstRowPreview(GT): "에스피씨세파클러캡슬250mg30 캡슐"

#### grid recommendation: **fixed — 단일행 폼 (강력 추천)**

추천 이유:
- 미리 인쇄된 단일 행 전용 폼
- 보험코드 / 품목 / 수량 / 단가 / 제조번호 / 유효기간 / 제조회사 각 칸 고정
- 전체 표 영역 = 단일 행 (rowTemplate = tableArea)

#### 실제 컬럼 → canonical 매핑

| 원본 라벨 | canonicalColumn | valueType |
|---|---|---|
| 보험코드 | insuranceCode | code |
| 품목 | itemName | text |
| 수량 | quantity | quantity |
| 단가 | unitPrice | amount |
| 제조번호 | lotNo | code |
| 유효기간 | expiryDate | date |
| 제조회사 | manufacturer | text |

- 필수: itemName, quantity
- optional: insuranceCode, unitPrice, lotNo, expiryDate, manufacturer
- 종료 키워드: 불필요 (1행 고정)

#### firstRowPreview 컬럼 기준: itemName | quantity
예: "에스피씨세파클러캡슬250mg30 캡슐 | 30"

(행 단위 금액 컬럼 없음 — 문서 단위 공급가액은 documentFields에서 처리)

#### Template 설정 추천
- 단일 행 영역 지정 (전체 표 영역과 동일)
- 세로 가이드: 7개
- endKeywords: 불필요

#### RunOCR 출력 예시
```json
{
  "rowIndex": 1,
  "insuranceCode": "23004A",
  "itemName": "에스피씨세파클러캡슬250mg30",
  "spec": "캡슐",
  "quantity": "30",
  "unitPrice": "10,044",
  "lotNo": "23004A",
  "expiryDate": "20261204",
  "manufacturer": "(주)에스피씨(추정)"
}
```

---

### 7.4 4.pdf

**ocr_cache.json 실제 확인 컬럼**: 품목명 / LotNo. / 단위 / 수량 / 단가 / 공급가액 / 세역(세액)

- tableProfile: single_item_table
- rowCount(GT): 1
- firstRowPreview(GT): "클리마토플란정" (OCR: "클리마트플란정" → X, ocr_garbled)

#### grid recommendation: **fixed — 단일행 폼 / manual review (OCR 품질 불량)**

추천 이유:
- 미리 인쇄된 거래명세표 양식
- 품목명 / LotNo. / 단위 / 수량 / 단가 / 공급가액 / 세액 각 칸 고정
- TOTAL 라인이 표 하단 고정 위치
- qualityTag=ocr_garbled로 OCR 추출 신뢰도 낮음 → manual review 권장

3.pdf와의 차이: 3.pdf(보험코드/제조회사) vs 4.pdf(LotNo./공급가액/세액) — 동일 single_item_table이나 컬럼 구성 상이

#### 실제 컬럼 → canonical 매핑

| 원본 라벨 | canonicalColumn | valueType |
|---|---|---|
| 품목명 | itemName | text |
| LotNo. | lotNo | code |
| (단위 컬럼) | unit | text |
| 수량 | quantity | quantity |
| 단가 | unitPrice | amount |
| 공급가액 | supplyAmount | amount |
| 세역 | taxAmount | amount |

- 필수: itemName, quantity
- optional: lotNo, unit, unitPrice, supplyAmount, taxAmount
- 종료 키워드: 불필요 (1행 고정)

#### firstRowPreview 컬럼 기준: itemName | quantity | supplyAmount
예: "클리마토플란정 | 1,000 | 25,760,000"
주의: OCR 오독 "클리마트플란정" → X 판정 유지. fuzzy match 없이는 X.

#### Template 설정 추천
- 단일 행 영역 지정
- 세로 가이드: 7개
- OCR 품질 불량으로 사용자 수동 확인 권장

#### RunOCR 출력 예시
```json
{
  "rowIndex": 1,
  "itemName": "클리마토플란정",
  "lotNo": "0350823-231024-200811",
  "unit": "BOX",
  "quantity": "1,000",
  "supplyAmount": "25,760,000",
  "taxAmount": "2,576,000"
}
```

---

### 7.5 5.pdf

**ocr_cache.json 실제 확인 컬럼**: 품목코드 / 품목 / 수량 / 단가 / 금액

- tableProfile: multi_item_table
- rowCount(GT): 6
- firstRowPreview(GT): "노루모에프내복액75ML"

#### grid recommendation: **variable (추천)**

추천 이유:
- 텍스트 기반 POS/ERP 출력 스타일
- 6개 행 가변 (거래마다 품목 수 변동)
- 종료 키워드 명확 ("합계", "공급가액", "부가세")
- 품목코드(NRFS75M 등) → 코드 기반 가변 인쇄

1.jpg와의 차이: 1.jpg(의약품 lot/expiry 중심, fixed) vs 5.pdf(코드+금액 중심, variable)

#### 실제 컬럼 → canonical 매핑

| 원본 라벨 | canonicalColumn | valueType |
|---|---|---|
| 품목코드 | itemCode | code |
| 품목 | itemName | text |
| 수량 | quantity | quantity |
| 단가 | unitPrice | amount |
| 금액 | amount | amount |

- 필수: itemName, quantity, amount
- optional: itemCode, unitPrice
- 종료 키워드: ["합계", "공급가액", "부가세", "부가서"]

#### firstRowPreview 컬럼 기준: itemName | quantity | amount
예: "노루모에프내복액75ML | 3,000 | 1,650,000"

#### Template 설정 추천
- row 영역: 1행 높이
- 세로 가이드: 5개 (품목코드 / 품목 / 수량 / 단가 / 금액)
- 종료 키워드: "합계", "공급가액", "부가세"

#### RunOCR 출력 예시 (첫 행)
```json
{
  "rowIndex": 1,
  "itemCode": "NRFS75M",
  "itemName": "노루모에프내복액75ML",
  "quantity": "3,000",
  "unitPrice": "550",
  "amount": "1,650,000"
}
```

---

### 7.6 6.pdf

**ocr_cache.json 실제 확인 컬럼**: NO / 제품코드 / 제품명 / 수량 / Lot No / 유효일자

- tableProfile: lot_serial_quantity_table
- rowCount(GT): 6 (수량=0인 행 포함)
- firstRowPreview(GT): "알코텔정100T"

#### grid recommendation: **fixed (추천)**

추천 이유:
- 행 번호(NO) 1~6 미리 인쇄
- 전체 6행 고정 (수량=0인 행 5, 6도 존재 → 빈 행이 있어도 고정 폼)
- 세로 컬럼선 6개가 표 끝까지 유지
- 표 외곽선 존재 (거래명세서 세부내역 고정 폼)
- 행 높이 일정

빈 행 처리: 수량=0인 행(5, 6행)도 rowCount에 포함. emptyRowCount 별도 관리는 T-2에서 정의.

#### 실제 컬럼 → canonical 매핑

| 원본 라벨 | canonicalColumn | valueType |
|---|---|---|
| NO | rowIndex | number |
| 제품코드 | itemCode | code |
| 제품명 | itemName | text |
| 수량 | quantity | quantity |
| Lot No | lotNo | code |
| 유효일자 | expiryDate | date |

- 필수: itemName, quantity, lotNo
- optional: rowIndex, itemCode, expiryDate
- 종료 키워드: 불필요 (fixed, NO 기준)

#### firstRowPreview 컬럼 기준: itemName | lotNo | expiryDate | quantity
예: "알코텔정100T | 24001 | 270305 | 5"

#### Template 설정 추천
- 전체 표 영역 드래그 (6행 포함)
- 행 템플릿: 1행 높이
- 세로 가이드: 6개 (NO / 제품코드 / 제품명 / 수량 / Lot No / 유효일자)

#### RunOCR 출력 예시 (첫 행)
```json
{
  "rowIndex": 1,
  "itemCode": "ATT100T",
  "itemName": "알코텔정100T",
  "quantity": "5",
  "lotNo": "24001",
  "expiryDate": "270305"
}
```

---

### 7.7 7.pdf

**ocr_cache.json 실제 확인 컬럼**: 품명 / 시리얼/로트No. / 단위 / 수량

- tableProfile: serial_quantity_table
- rowCount(GT): 1
- firstRowPreview(GT): "클리마토플란정"

#### grid recommendation: **variable 또는 single-row**

추천 이유:
- 1개 항목만 존재 → variable/single-row 결과 동일
- 총수량 라인(총수량: 1,000)이 종료 키워드로 사용 가능
- 고정 프레임 약함 (텍스트 기반, 상단에 거래처/주소 정보가 많음)

4.pdf와의 차이: 4.pdf(single_item_table, 재무 문서 — 금액 중심) vs 7.pdf(serial_quantity_table, 납품 문서 — 수량 중심)

#### 실제 컬럼 → canonical 매핑

| 원본 라벨 | canonicalColumn | valueType |
|---|---|---|
| 품명 | itemName | text |
| 시리얼/로트No. | serialNo | code |
| 단위 | unit | text |
| 수량 | quantity | quantity |

- 필수: itemName, quantity
- optional: serialNo, unit
- 종료 키워드: ["총수량", "합계", "특이사항"]

#### firstRowPreview 컬럼 기준: itemName | serialNo | unit | quantity
예: "클리마토플란정 | 0350623-231024-260811 | BOX | 1,000"

#### Template 설정 추천
- row 영역: 1행 높이
- 세로 가이드: 4개 (품명 / 시리얼/로트No. / 단위 / 수량)
- 종료 키워드: "총수량", "합계"

#### RunOCR 출력 예시
```json
{
  "rowIndex": 1,
  "itemName": "클리마토플란정",
  "serialNo": "0350623-231024-260811",
  "unit": "BOX",
  "quantity": "1,000"
}
```

---

## 8. 고정그리드/가변그리드 추천 기준

> 이 기준은 강제 로직이 아니다. Template UI에서 "추천" 또는 "도움말"로 사용하기 위한 참고 기준이다. 사용자가 최종 선택한다.

| 추천 | 조건 | 설명 | 예시 파일 |
|---|---|---|---|
| **fixed 추천** | ① 행 번호(NO) 존재 ② 빈 행(수량=0) 다수 ③ 행 높이 일정 ④ 세로 컬럼선이 표 끝까지 유지 ⑤ 합계/소계 위치 고정 ⑥ 전체 표 외곽선 존재 | 미리 인쇄된 고정 프레임. Template에서 전체 표 영역 + 행 템플릿 + 세로 가이드로 처리. | 1.jpg(28행), 3.pdf(1행 폼), 4.pdf(1행 폼), 6.pdf(6행+빈행) |
| **variable 추천** | ① 텍스트 행이 아래로 동적 반복 ② 종료 키워드로 표 끝 인식 ③ 행 수 거래마다 가변 ④ 고정 프레임 약함 ⑤ 품목코드 기반 ERP 출력 스타일 | 텍스트 인쇄로 row 반복. Template에서 row 영역 + 세로 가이드 + 종료 키워드로 처리. | 2.pdf(13행 가변), 5.pdf(6행 가변) |
| **either** | 행 수 5~15 중간, 반복 행선 중간, 고정/가변 모두 처리 가능 | 어느 쪽 선택해도 무방. 사용자 문서 패턴에 따라 결정. | (현재 샘플 미해당) |
| **single-row** | rowCount=1 고정, 미리 인쇄된 단일 항목 폼 | fixed 1행 = 전체 표 영역. variable로도 처리 가능(1회 반복 후 종료). | 3.pdf, 4.pdf, 7.pdf |
| **manual review** | OCR 품질 불량, 컬럼선 불명확, 표 구조 해석 불가 | 사용자가 직접 이미지 확인 후 구조 지정 필요. | 4.pdf (ocr_garbled) |

**핵심 판단 기준**:
- 고정/가변 판단은 "데이터가 몇 행 들어갔는가"가 아니다
- 빈 행이 많아도 고정 그리드일 수 있다 (6.pdf: 수량=0 행 존재)
- 진짜 기준은 **표의 행/열 구조가 미리 인쇄된 고정 프레임인지**, 아니면 **텍스트 행이 종료 키워드 전까지 유동적으로 반복되는 구조인지**다

---

## 9. gridMode별 저장 metadata 제안

### 9.1 고정 그리드 (fixed)

```json
{
  "gridMode": "fixed",
  "tableArea": {
    "x": 0,
    "y": 0,
    "width": 0,
    "height": 0
  },
  "rowTemplate": {
    "y": 0,
    "height": 0
  },
  "columnGuides": [120, 250, 340, 430, 490, 560, 620],
  "columns": [
    { "index": 0, "label": "품목", "canonicalColumn": "itemName", "required": true },
    { "index": 1, "label": "규격", "canonicalColumn": "spec", "required": false },
    { "index": 2, "label": "제조번호", "canonicalColumn": "lotNo", "required": false },
    { "index": 3, "label": "유효기간", "canonicalColumn": "expiryDate", "required": false },
    { "index": 4, "label": "수량", "canonicalColumn": "quantity", "required": true },
    { "index": 5, "label": "단가", "canonicalColumn": "unitPrice", "required": false },
    { "index": 6, "label": "금액", "canonicalColumn": "amount", "required": true }
  ]
}
```

설명:
- `tableArea`: 전체 표 외곽 좌표 (픽셀)
- `rowTemplate.y`: 첫 번째 행 y 좌표, `rowTemplate.height`: 행 높이 → 이 패턴이 아래로 반복
- `columnGuides`: 컬럼 분할 x 좌표 목록
- `columns`: 각 컬럼의 인덱스, 라벨, canonicalColumn, 필수 여부

### 9.2 가변 그리드 (variable)

```json
{
  "gridMode": "variable",
  "rowTemplate": {
    "x": 0,
    "y": 0,
    "width": 0,
    "height": 0
  },
  "columnGuides": [80, 280, 350, 430, 510, 590],
  "columns": [
    { "index": 0, "label": "품목코드", "canonicalColumn": "itemCode", "required": false },
    { "index": 1, "label": "품목명", "canonicalColumn": "itemName", "required": true },
    { "index": 2, "label": "수량", "canonicalColumn": "quantity", "required": true },
    { "index": 3, "label": "단가", "canonicalColumn": "unitPrice", "required": false },
    { "index": 4, "label": "공급금액", "canonicalColumn": "supplyAmount", "required": true },
    { "index": 5, "label": "보험NO", "canonicalColumn": "insuranceCode", "required": false }
  ],
  "endKeywords": ["공급금액합계", "합계", "소계", "총계", "전체합계", "당일거래금액"]
}
```

설명:
- `rowTemplate`: 하나의 row 영역 좌표 (이 영역이 반복)
- `columnGuides`: 컬럼 분할 x 좌표
- `endKeywords`: 이 키워드를 만나면 표 끝으로 인식

### 9.3 단일 행 fixed (single-row = fixed 1행의 특수 케이스)

```json
{
  "gridMode": "fixed",
  "tableArea": { "x": 0, "y": 0, "width": 0, "height": 0 },
  "rowTemplate": { "y": 0, "height": 0 },
  "columnGuides": [80, 160, 240, 320, 420, 510, 600],
  "columns": [
    { "index": 0, "label": "보험코드", "canonicalColumn": "insuranceCode", "required": false },
    { "index": 1, "label": "품목", "canonicalColumn": "itemName", "required": true },
    { "index": 2, "label": "수량", "canonicalColumn": "quantity", "required": true },
    { "index": 3, "label": "단가", "canonicalColumn": "unitPrice", "required": false },
    { "index": 4, "label": "제조번호", "canonicalColumn": "lotNo", "required": false },
    { "index": 5, "label": "유효기간", "canonicalColumn": "expiryDate", "required": false },
    { "index": 6, "label": "제조회사", "canonicalColumn": "manufacturer", "required": false }
  ]
}
```

참고: single-row는 tableArea ≈ rowTemplate (1행 전체가 표 영역)

---

## 10. RunOCR 공통 tableRows 출력 구조

고정그리드든 가변그리드든 RunOCR 결과는 **같은 구조**로 출력되어야 한다.

```json
{
  "tableRows": [
    {
      "rowIndex": 1,
      "itemCode": "",
      "itemName": "",
      "spec": "",
      "lotNo": "",
      "serialNo": "",
      "manufacturingNo": "",
      "expiryDate": "",
      "quantity": "",
      "unit": "",
      "unitPrice": "",
      "supplyAmount": "",
      "taxAmount": "",
      "amount": "",
      "totalAmount": "",
      "manufacturer": "",
      "insuranceCode": "",
      "remark": "",
      "_rawText": "",
      "_confidence": null,
      "_source": "template_table"
    }
  ],
  "tableMeta": {
    "gridMode": "fixed",
    "tableProfile": "multi_item_table",
    "rowCount": 28,
    "emptyRowCount": 0,
    "columns": [
      { "canonicalColumn": "itemName", "label": "품목", "index": 0 },
      { "canonicalColumn": "spec", "label": "규격", "index": 1 },
      { "canonicalColumn": "lotNo", "label": "제조번호", "index": 2 },
      { "canonicalColumn": "expiryDate", "label": "유효기간", "index": 3 },
      { "canonicalColumn": "quantity", "label": "수량", "index": 4 },
      { "canonicalColumn": "unitPrice", "label": "단가", "index": 5 },
      { "canonicalColumn": "amount", "label": "금액", "index": 6 }
    ],
    "firstRowPreview": "헥사메던액0.12% | 15m|*6포 | 400 | 420,000",
    "endKeywordMatched": null
  }
}
```

필드 설명:
- `""` vs `null`: `""` = OCR 시도했으나 빈값, `null` = 해당 컬럼 미사용
- `_rawText`: 해당 행의 원본 OCR 텍스트 (디버깅용)
- `_confidence`: 행 단위 평균 신뢰도
- `_source`: "template_table" (고정/가변 동일). 향후 "parser_auto" 추가 가능
- `tableMeta.emptyRowCount`: 수량=0 또는 itemName=빈값인 행 수 (6.pdf 적용)
- `tableMeta.endKeywordMatched`: variable grid에서 실제 매칭된 종료 키워드

설계 원칙:
- 미사용 컬럼은 `null` 전달 또는 응답에서 제외 (parser 설정에 따라)
- 현재(T-1 단계)는 구조 정의만, 실제 값 채움은 T-3 이후

---

## 11. firstRowPreview 생성 기준

### 11.1 컬럼 우선순위 (앞에서부터 최대 4개 표시)

1. `itemName` (항상 첫 번째)
2. `spec` (있으면)
3. `lotNo` 또는 `serialNo` (있으면)
4. `expiryDate` (lotNo/serialNo 없으면 3순위)
5. `quantity` (항상 포함)
6. `unitPrice` (있으면)
7. `amount` 또는 `supplyAmount` (있으면 마지막)

포맷: "|" 구분자. 빈값 스킵. 최대 4개 컬럼.

### 11.2 파일별 권장 firstRowPreview 조합

| 파일 | tableProfile | 권장 컬럼 조합 | 예시 |
|---|---|---|---|
| 1.jpg | multi_item_table | itemName \| spec \| quantity \| amount | "헥사메던액0.12% \| 15m\|*6포 \| 400 \| 420,000" |
| 2.pdf | item_quantity_table | itemName \| quantity \| supplyAmount | "LOXOLIFEN TABLET 3OT3Z \| 300 \| 18,295,140" |
| 3.pdf | single_item_table | itemName \| quantity | "에스피씨세파클러캡슬250mg30 캡슐 \| 30" |
| 4.pdf | single_item_table | itemName \| quantity \| supplyAmount | "클리마토플란정 \| 1,000 \| 25,760,000" |
| 5.pdf | multi_item_table | itemName \| quantity \| amount | "노루모에프내복액75ML \| 3,000 \| 1,650,000" |
| 6.pdf | lot_serial_quantity_table | itemName \| lotNo \| expiryDate \| quantity | "알코텔정100T \| 24001 \| 270305 \| 5" |
| 7.pdf | serial_quantity_table | itemName \| serialNo \| unit \| quantity | "클리마토플란정 \| 0350623-231024-260811 \| BOX \| 1,000" |

### 11.3 현재 GT firstRowPreview와의 관계

현재 GT firstRowPreview는 첫 행의 itemName(또는 itemName+spec 연결) 텍스트다.  
컬럼 기반 확장 시 "|" 구분자로 정보량이 늘어나지만 기존 GT는 유지한다.  
T-2에서 Test UI에 컬럼별 preview를 별도 표시하고, firstRowPreview GT는 itemName 기준 매칭으로 계속 사용.

---

## 12. T-2 Test UI tableRows 표시 기준

### 12.1 T-2 목표

현재 Test UI: rowCount / firstRowPreview / tableDetected 세 항목만 표시  
T-2: tableRows 컬럼별 preview 표시, column 매핑 정확도 검증

### 12.2 T-2에서 필요한 데이터 구조

```typescript
type TableColumnValidation = {
  canonicalColumn: string;       // "itemName", "quantity" 등
  label: string;                 // 실제 문서 컬럼 라벨 ("품목", "수량" 등)
  expected: string | null;       // GT에 있는 경우 예상 값
  actual: string | null;         // OCR 추출 값
  status: "O" | "△" | "X" | "—";
};

type TableRowsValidation = {
  tableProfile: string;
  gridMode: "fixed" | "variable" | null;
  expectedColumns: string[];             // tableProfile 기준 expected canonical columns
  actualColumns: string[];               // 실제 추출된 columns
  columnMatchStatus: "full" | "partial" | "mismatch";
  missingColumns: string[];
  extraColumns: string[];
  rowCountExpected: number;
  rowCountActual: number;
  rowCountStatus: "O" | "△" | "X";
  firstRowPreviewExpected: string;
  firstRowPreviewActual: string;
  firstRowPreviewStatus: "O" | "△" | "X";
  columnValidations: TableColumnValidation[];
};
```

### 12.3 T-2 화면 표시 항목

| 표시 항목 | 내용 | 판정 |
|---|---|---|
| tableProfile | 현재 sample의 tableProfile | 표시만 |
| expectedColumns | 이 profile의 표준 컬럼 목록 (T-1 기준) | 표시만 |
| columnMatchStatus | 실제 추출 컬럼 vs expected 비교 | full/partial/mismatch |
| missingColumns | 기대했으나 없는 컬럼 | X 표시 |
| extraColumns | 기대 외 추가 컬럼 | 정보 표시 |
| rowCount | GT vs OCR 비교 | O/△/X |
| firstRowPreview | GT vs OCR 비교 | O/△/X |
| 첫 행 상세 | 컬럼별 값 표시 | 컬럼별 O/△/X |

### 12.4 T-2 진입을 위해 T-1에서 확정된 항목

- [x] 표준 canonicalColumn 목록 (18개)
- [x] tableProfile별 expectedColumns 정의
- [x] firstRowPreview 컬럼 우선순위
- [ ] Ground Truth에 컬럼별 값 추가 (T-2 작업 범위)
- [ ] OCR parser가 컬럼별 값을 추출 (T-3 범위, T-2에서는 목 데이터 사용 가능)

---

## 13. OP-1 canonical registry로 넘길 table column 목록

| canonicalColumn | documentTypes | aliases | group | isTableColumn | valueType | side |
|---|---|---|---|---|---|---|
| rowIndex | invoice_statement | NO, 번호, 순번 | table | true | number | any |
| itemCode | invoice_statement | 품목코드, 코드, 상품코드, 제품코드, 단품코드 | table | true | code | any |
| itemName | invoice_statement | 품명, 품목, 품목명, 상품명, 제품명, 약품명, 내역 | table | true | text | any |
| spec | invoice_statement | 규격, 규격명, 포장, 용량 | table | true | text | any |
| lotNo | invoice_statement | Lot, LOT, Lot No, LotNo., 제조번호, 로트번호 | table | true | code | any |
| serialNo | invoice_statement | Serial, S/N, 시리얼, 일련번호, 시리얼/로트No. | table | true | code | any |
| manufacturingNo | invoice_statement | 제조번호(별도), 제조NO | table | true | code | any |
| expiryDate | invoice_statement | 유효기간, 유효일자, 사용기한, 유효기한 | table | true | date | any |
| quantity | invoice_statement | 수량, Qty, QTY, 수, 출고수량 | table | true | quantity | any |
| unit | invoice_statement | 단위, 단위규격, EA, BOX | table | true | text | any |
| unitPrice | invoice_statement | 단가, 공급단가, 소비자단가 | table | true | amount | any |
| supplyAmount | invoice_statement | 공급금액, 공급가액, 공급액 | table | true | amount | any |
| taxAmount | invoice_statement | 세액, 부가세, VAT | table | true | amount | any |
| amount | invoice_statement | 금액, 행금액, 합계금액 | table | true | amount | any |
| totalAmount | invoice_statement | 합계금액(행), 합계(행) | table | true | amount | any |
| manufacturer | invoice_statement | 제조사, 제조원, 제조회사 | table | true | text | any |
| insuranceCode | invoice_statement | 보험코드, 보험NO, 보험번호 | table | true | code | any |
| remark | invoice_statement | 비고, 적요, 메모 | table | true | text | any |

주의: T-1 기준 초안. OP-1 작업 시 `documentTypes`, `amountProfileAware`, `partyProfileAware` 등 필드 추가.

---

## 14. 위험 요소와 보류 항목

| # | 항목 | 위험 | 조치 |
|---|---|---|---|
| 1 | 4.pdf firstRowPreview fuzzy match | "클리마트" vs "클리마토" 1자 차이 → X 유지. fuzzy match 도입 시 타 필드 과적합 위험 | **보류** — T-2/T-3 이후 일반화 가능한 fuzzy 도입 여부 결정 |
| 2 | lotNo와 manufacturingNo 통합 | 1~7 샘플에서 별도 제조번호 필드 미확인 | **lotNo로 통합 권장**. 추가 샘플 확인 후 분리 재검토 |
| 3 | supplyAmount와 amount 혼용 | 1.jpg(금액→amount), 4.pdf(공급가액→supplyAmount) — 계산식 동일하나 라벨 다름 | **라벨 기반 구분 정책 적용** (문서 라벨 우선) |
| 4 | single_item_table 두 패턴 | 3.pdf(보험코드/제조회사)와 4.pdf(LotNo./공급가액/세액) 컬럼 구성 상이 | **T-2 이후 subProfile 분기 검토** — 현재는 동일 profile 유지 |
| 5 | multi_item_table 두 패턴 | 1.jpg(pharma_lot)와 5.pdf(code_amount) 컬럼 구성 상이 | **T-2 이후 subProfile 분기 검토** |
| 6 | 빈 행(수량=0) rowCount 포함 여부 | 6.pdf 수량=0 행 2개 포함 시 rowCount=6, 제외 시 rowCount=4 | **현재 GT rowCount=6 유지** (빈 행 포함). T-2에서 emptyRowCount 별도 표시 |
| 7 | OCR garbled 샘플 과적합 금지 | 4.pdf 특화 규칙을 parser에 추가하면 타 샘플 회귀 위험 | **4.pdf는 expected_failure 유지** — 컬럼 정책에 4.pdf 특화 규칙 추가 금지 |
| 8 | 2.pdf 소비자단가/공급단가 두 종 | unitPrice 하나로 통합 시 두 값 손실 | **T-2에서 consumerPrice/supplyPrice 분리 검토** |
| 9 | 6.pdf expiryDate 형식 | "270305"는 YYMMDD (26-03-05). YYYYMMDD와 혼용 | **expiryDate normalizer 필요** — T-3에서 처리 |

---

## 15. 최종 결론

| 항목 | 판단 | 근거 |
|---|---|---|
| tableRows 컬럼 정책 잠금 가능 여부 | **조건부 잠금 가능** | 18개 canonical column 정의 완료. subProfile 분기는 T-2 후 보완 |
| T-2 진입 가능 여부 | **예** | T-1 컬럼 정책 기준으로 Test UI tableRows column 표시/검증 구조 정의 가능 |
| OP-1 반영 가능 여부 | **예** | 18개 table column 목록 확정. isTableColumn=true로 추가 가능 |
| Template-Table-1 선행 필요 여부 | **T-1 후 진입 가능** | T-1 컬럼 정책 → Template UI column 매핑 UI 추가 가능 |
| RunOCR-Table-1 선행 필요 여부 | **T-3 필요** | RunOCR에서 tableRows 값을 채우려면 parser 개선(T-3) 선행 |

**잠금 확정 항목**:
- [x] 18개 표준 canonical column 목록 및 alias
- [x] tableProfile별 기본 컬럼 세트 (초안)
- [x] gridMode별 저장 metadata 구조 (초안)
- [x] RunOCR 공통 tableRows 출력 구조 (초안)
- [x] firstRowPreview 생성 기준
- [ ] subProfile 분기 (multi_item_table/single_item_table 변형) — T-2 이후 보완

---

## 16. 다음 추천 작업

| 후보 | 설명 | 선행 조건 | 위험도 |
|---|---|---|---|
| **T-2** | Test UI tableRows column 표시/검증 구조 정리 | T-1 완료 | 낮음 |
| **OP-1** | canonicalField registry 설계 (table column 포함) | T-1 완료 | 낮음 |
| T-3 | parser tableRows column extraction | T-1, T-2 완료 | 중간 |
| Template-Table-1 | Template 고정/가변 그리드 연동 | T-1, OP-1 완료 | 중간 |
| RunOCR-Table-1 | RunOCR tableRows 출력 연결 | T-3, OP-3 완료 | 중간 |

### 추천: **T-2** (Test UI tableRows column 표시/검증 구조 정리)

추천 이유:
1. T-1 컬럼 정책을 Test UI에서 시각적으로 검증해야 정책 정합성 확인 가능
2. T-3(parser 개선) 전에 UI 기준을 정해야 회귀 없이 parser를 설계할 수 있다
3. Test 탭 한정 → 운영 탭(Template/RunOCR/History) 회귀 위험 없음
4. T-2에서 expectedColumns를 GT에 추가하는 과정에서 T-1 정책의 오류를 조기 발견 가능

병행 가능: **OP-1** — 영향 영역이 달라 T-2와 병행 가능. 단, OP-1 table column 최종 확정은 T-2 완료 후 권장.

---

## 17. 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `public/data/testsets/invoice_statement/reports/T1_table_profile_column_policy_20260511.md` | **신규 생성** |
| 코드 | **변경 없음** |
| ground_truth.json | **변경 없음** |
| manifest.json | **변경 없음** |
| party_master.json | **변경 없음** |
| invoice_statement.py | **변경 없음** |

---

## 검증 결과

| 검증 | 결과 |
|---|---|
| manifest.json parse | ✅ ok (이전 작업에서 검증 완료) |
| ground_truth.json parse | ✅ ok (이전 작업에서 검증 완료) |
| 코드 수정 여부 | **없음** |
| typecheck/build | 코드 수정 없어 불필요 |

---

## Appendix A. 샘플별 표 컬럼 비교 요약

| 파일 | tableProfile | 실제 컬럼 (원본 라벨) | canonical mapping | grid 추천 |
|---|---|---|---|---|
| 1.jpg | multi_item_table | 품목 / 규격 / 제조번호 / 유효기간 / 수량 / 단가 / 금액 | itemName, spec, lotNo, expiryDate, quantity, unitPrice, amount | fixed |
| 2.pdf | item_quantity_table | 품목코드 / 품목명 / 수량 / 소비자단가 / 공급단가 / 공급금액 / 보험NO | itemCode, itemName, quantity, unitPrice, supplyAmount, insuranceCode | variable |
| 3.pdf | single_item_table | 보험코드 / 품목 / 수량 / 단가 / 제조번호 / 유효기간 / 제조회사 | insuranceCode, itemName, quantity, unitPrice, lotNo, expiryDate, manufacturer | fixed (single-row) |
| 4.pdf | single_item_table | 품목명 / LotNo. / 단위 / 수량 / 단가 / 공급가액 / 세액 | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount | fixed (single-row) |
| 5.pdf | multi_item_table | 품목코드 / 품목 / 수량 / 단가 / 금액 | itemCode, itemName, quantity, unitPrice, amount | variable |
| 6.pdf | lot_serial_quantity_table | NO / 제품코드 / 제품명 / 수량 / Lot No / 유효일자 | rowIndex, itemCode, itemName, quantity, lotNo, expiryDate | fixed |
| 7.pdf | serial_quantity_table | 품명 / 시리얼/로트No. / 단위 / 수량 | itemName, serialNo, unit, quantity | variable (single-row) |

## Appendix B. 컬럼 수 분포

| 파일 | 컬럼 수 | 금액 컬럼 | lot/serial |
|---|---|---|---|
| 1.jpg | 7 | amount | lotNo |
| 2.pdf | 6~7 | supplyAmount | 없음 |
| 3.pdf | 7 | 없음 (문서 단위) | lotNo |
| 4.pdf | 7 | supplyAmount, taxAmount | lotNo |
| 5.pdf | 5 | amount | 없음 |
| 6.pdf | 6 | 없음 (no_amount_summary) | lotNo |
| 7.pdf | 4 | 없음 (quantity_total_only) | serialNo |

관찰: 컬럼 수 4~7 범위. 의약품은 lot/serial 포함하나 금액 없을 수 있음. 일반 거래는 금액 있으나 lot/serial 없을 수 있음.
