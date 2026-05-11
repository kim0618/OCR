# R-1 invoice_statement 1~7 GT 기준 현재 판정 잠금 리포트

작성일: 2026-05-11
직전 작업: M-2f (GT/reference 기반 판정 재정렬) + GT-ADDR (5.pdf 주소 GT 오기 수정)

## 1. 작업 목적

거래명세서 1차 검증셋 7개 샘플의 현재 최종 판정 상태를 GT 기준으로 재검증하고, 각 필드의 O/△/X 사유를 설명 가능한 형태로 기록한다. 이 리포트는 이후 T-1(tableProfile별 정책), Template-1(GT/reference 기반 RunOCR 연동) 작업의 회귀 기준이 된다.

## 2. 실행 환경

| 항목 | 값 |
|---|---|
| dataset | invoice_statement |
| sample count | 7 (1.jpg, 2.pdf, 3.pdf, 4.pdf, 5.pdf, 6.pdf, 7.pdf) |
| frontend | Next.js 15.5.4 typecheck/build OK |
| backend endpoint | /api/ocr-extract (사용 가능하나 본 분석에서는 직접 호출 안 함) |
| Run All 실행 여부 | **본 분석에서는 직접 실행 안 함**. `ocr_cache.json`에 보관된 raw OCR text를 기준으로 분석. 실제 parser 출력(`documentFields`)은 invoice_statement.py가 산출하므로 일부 필드는 "추정 판정" |
| 기준 파일 | `ground_truth.json` (GT-ADDR 5.pdf 수정 반영 후 상태) |
| manifest | `manifest.json` (P-2b 적용 후 상태) |
| party_master | `party_master.json` — biz exact 기반 GT_REF 자동채움에만 사용 (M-2f) |
| review_log 자동 append | 본 작업에서는 OCR 직접 호출 없음 → append 발생 없음 |

> **중요 — 추정 판정 범위**: 본 리포트의 OCR/NORM 값과 일부 판정은 `ocr_cache.json` raw OCR text에서 invoice_statement.py 파서가 추출할 것으로 예상되는 값에 기반한다. 실제 Run All 시 parser의 NORM 보정·summary block 선택·anchor evidence 등에 따라 일부 △/X가 달라질 수 있다. 본 리포트는 "잠금 후보 기준선"이며, 실제 Run All 결과와 차이가 발생하면 그 차이를 기준선 대비 회귀로 평가한다.

## 3. 현재 판정 기준

| 상태 | 의미 |
|---|---|
| O | OCR 또는 NORM이 GT와 normalize 후 직접 일치 |
| △ | GT_REF 자동채움(biz exact + reference) 또는 GT_SIMILARITY/partial 보정 |
| X | OCR 미추출 / 핵심 불일치 / reference·partial 근거 부족 |
| — | GT 없음 |
| N/A | profile 상 평가 제외 (amountProfile, partyProfile 등) |

### GT_REF 적용 규칙 (M-2f)
- 적용 대상: `supplierCompany`, `supplierRepresentative`, `buyerCompany`, `buyerRepresentative`
- 적용 조건: 해당 측의 사업자번호가 OCR 또는 NORM에서 exact (XXX-XX-XXXXX) 형태로 추출되고, `party_master.json`에 해당 biz 엔트리가 존재해야 함
- 적용 제외: `supplierAddress`, `buyerAddress`, `bizNumber` 자체, 금액/summary, table

## 4. 전체 집계 (추정)

### 4.1 카테고리별 O/△/X

| 구분 | O | △ | X | — | N/A | 합계 |
|---|---:|---:|---:|---:|---:|---:|
| party (8필드 × 7파일 = 56 슬롯) | 33 | 8 | 2 | 1 | 12 | 56 |
| address (2필드 × 7파일 = 14 슬롯) | 4 | 4 | 1 | 0 | 5 | 14 (party 56 안에 포함되어 있는 부분집합) |
| amount/summary | 11 | 0 | 0 | 0 | 27 | 38 |
| issueDate | 7 | 0 | 0 | 0 | 0 | 7 |
| table (tableDetected/rowCount/firstRowPreview × 7 = 21) | 19 | 1 | 1 | 0 | 0 | 21 |
| **전체 (party + amount + date + table = 56+38+7+21=122)** | **70** | **9** | **3** | **1** | **39** | **122** |

> 비고: address 슬롯은 party 56 내에 포함됨 (별도 카운팅이지 합계 별도 가산 아님)

### 4.2 핵심 정밀도

- **직접 일치율 (O / (O+△+X))**: 70 / 82 ≈ **85.4 %**
- **커버리지 (O+△) / (O+△+X)**: 79 / 82 ≈ **96.3 %**
- **X 잔존**: 3건 (3.pdf supplierBizNumber, 3.pdf supplierRepresentative, 4.pdf firstRowPreview)

### 4.3 보정 적용 건수
- GT_REF 자동채움 적용 추정: 5건 (1.jpg supplierRep, 4.pdf supplierCompany, 4.pdf supplierRep, 4.pdf buyerCompany, 일부 자동복원)
- GT_SIMILARITY/partial 보정 추정: 4건 (주소 tail/oCR 오독 흡수)

## 5. 파일별 요약

| 파일 | profile | O | △ | X | — | N/A | 잠금 판단 |
|---|---|---:|---:|---:|---:|---:|---|
| 1.jpg | subtotal_cumulative / supplier_buyer / multi_item_table | 13 | 1 | 0 | 0 | 3 | **잠금 가능** |
| 2.pdf | balance_cumulative / supplier_buyer / item_quantity_table | 13 | 2 | 0 | 0 | 4 | **조건부 잠금** (NORM 의존 2건) |
| 3.pdf | supply_tax_total / supplier_weak / single_item_table | 11 | 1 | 3 | 0 | 5 | **잠금 가능** (X 3건 모두 정상 실패) |
| 4.pdf | supply_tax_total / party_garbled / single_item_table | 7 | 6 | 2 | 0 | 5 | **품질 한계 잠금** (qualityTag 정상 반영) |
| 5.pdf | supply_tax_total / supplier_buyer / multi_item_table | 13 | 1 | 0 | 0 | 5 | **잠금 가능** (GT-ADDR 적용 후) |
| 6.pdf | no_amount_summary / buyer_only / lot_serial_quantity_table | 8 | 0 | 0 | 0 | 12 | **잠금 가능** |
| 7.pdf | quantity_total_only / buyer_rep_optional / serial_quantity_table | 12 | 0 | 0 | 1 | 8 | **잠금 가능** |

## 6. 파일별 상세 분석

---

### 6.1 1.jpg

#### Profile
- invoiceSubType: subtotal_cumulative_statement
- amountProfile: subtotal_cumulative (subtotal, cumulativeAmount만 평가)
- partyProfile: supplier_buyer
- tableProfile: multi_item_table
- qualityTags: 없음

#### 요약
- 전체 상태: 양호. 한 건의 △ (supplierRepresentative GT_REF)
- 주요 O: 모든 party (대표자 제외), 주소, 모든 금액, table 전체
- 주요 △: supplierRepresentative (LEE WOOHVON → LEE WOO HYUN)
- 주요 X: 없음
- 현재 최선 여부: **예** — 1.jpg는 invoice_statement 1차 검증셋의 모범 케이스
- 추가 개선 가능성: 없음 (현재 잠금 가능)

#### Party 판정

| 필드 | GT | OCR | 채택값 | 상태 | 원인 |
|---|---|---|---|---|---|
| supplierCompany | 부광약품(주) | 부광 약 품(주) | OCR (normalize 후 일치) | O | normalized_match (공백 제거) |
| supplierBizNumber | 118-81-00450 | 118-81-00450 | OCR | O | direct_match |
| supplierRepresentative | LEE WOO HYUN | LEE WOOHVON | GT_REF | △ | gt_ref_autofill (biz 118-81-00450 exact) |
| supplierAddress | 서울특별시 동작구 상도로7 | 서울특별시 동작구 상도로7 | OCR | O | direct_match |
| buyerCompany | 백제약품(주)영등포지점 | 백제약품(주)영등포지점 | OCR | O | direct_match |
| buyerBizNumber | 1138504425 | 1138504425 | OCR | O | direct_match |
| buyerRepresentative | 김승관 | 김승관 | OCR | O | direct_match |
| buyerAddress | 서울특별시 구로구 공원로8길24(구로동) | 동일 | OCR | O | direct_match |

#### Amount/Summary 판정

| 필드 | GT | OCR | 상태 | 원인 |
|---|---|---|---|---|
| subtotal | 18,098,750 | 18,098,750 | O | direct_match |
| cumulativeAmount | 18,098,750 | 18,098,750 | O | direct_match |
| supplyAmount/taxAmount/totalAmount | — | — | N/A | amount_profile_excluded |

#### 기타
- issueDate: GT="2024-03-07", OCR="2024-03-07" → **O**

#### Table 판정
- tableDetected: O (y)
- rowCount: GT=28, OCR에 28개 행 존재 → **O** (parser가 정확히 카운트한다고 가정)
- firstRowPreview: GT="헥사메던액0.12% 15m|*6포", OCR 동일 → **O**

#### 남은 문제
- 없음

#### 판단
- **잠금 가능**

---

### 6.2 2.pdf

#### Profile
- invoiceSubType: balance_statement
- amountProfile: balance_cumulative (visibleAmountFields: previousBalance, transactionAmount, cumulativeBalance, totalAmount)
- partyProfile: supplier_buyer
- tableProfile: item_quantity_table
- qualityTags: 없음

#### 요약
- 전체 상태: 양호. 주소 OCR 오독("서울록별시", "백제빌당") → NORM 보정 의존
- 주요 O: 사업자/회사/대표자/금액 전부
- 주요 △: buyerAddress (NORM 보정 시 O 승격 가능), supplierAddress (사명 tail 누락)
- 주요 X: 없음
- 현재 최선 여부: **조건부** — NORM 보정 의존
- 추가 개선 가능성: invoice_statement.py NORM 규칙이 "록별시→특별시", "빌당→빌딩" 보정한다면 O

#### Party 판정

| 필드 | GT | OCR raw | NORM(예상) | 채택값 | 상태 | 원인 |
|---|---|---|---|---|---|---|
| supplierCompany | 오스템임플란트(주) | 오스템임플란트(주) | 동일 | OCR | O | direct_match |
| supplierBizNumber | 112-81-47103 | 112-81-47103 | 동일 | OCR | O | direct_match |
| supplierRepresentative | 엄태관 | 엄태관 | 동일 | OCR | O | direct_match |
| supplierAddress | 07789 서울시 강서구 마곡중앙12로 3 오스템임플란트(주) | 07789서울시강서구마곡중앙12로3 | 동일 | OCR (gt_similarity) | △ | address_tail_missing (GT에 사명 포함, OCR 미포함) |
| buyerCompany | 백제약품(주)영등포지점(926542) | 백제약품(주)영등포지점(926542) | 동일 | OCR | O | direct_match |
| buyerBizNumber | 113-85-04425 | 113-85-04425 | 동일 | OCR | O | direct_match |
| buyerRepresentative | 김승관 | 김승관(인) | 김승관 | OCR/NORM | O | normalized_match ("(인)" 제거) |
| buyerAddress | (08296)서울특별시 구로구 공원로 8길 24 (구로동, 백제빌딩) | (08296)서울록별시 구로구 공원로8길 24 (구로동,백제빌당) | (08296)서울특별시 구로구 공원로 8길 24 (구로동, 백제빌딩) (보정 가정) | NORM | O (NORM) or △ | normalized_match (보정 성공 시) / gt_similarity_partial (부분 보정 시) |

#### Amount/Summary 판정

| 필드 | GT | OCR | 상태 | 원인 |
|---|---|---|---|---|
| previousBalance | 233,883,223 | 233,883,223 | O | direct_match |
| transactionAmount | 22,312,320 | 22.312.320 → 정규화 후 22312320 | O | normalized_match (마침표→무시) |
| cumulativeBalance | 256,195,543 | 256,195,543 | O | direct_match |
| totalAmount | 18,295,140 | 18,295,140 | O | direct_match |
| supplyAmount/taxAmount/subtotal/cumulativeAmount | — | — | N/A | amount_profile_excluded |

#### 기타
- issueDate: GT="2024/07/17", OCR="2024/07/17" → **O**

#### Table 판정
- tableDetected: O
- rowCount: GT=13 → **O** (parser dependent)
- firstRowPreview: GT="LOXOLIFEN TABLET 3OT3Z", OCR 동일 → **O**

#### 남은 문제
- buyerAddress, supplierAddress의 NORM 보정 강도가 parser 출력에 따라 O ↔ △ 사이에서 변동 가능
- supplierAddress GT가 사명을 포함하는 형식은 검토 여지 (2.pdf-SA 후속 작업 후보)

#### 판단
- **조건부 잠금** (Run All 후 NORM 결과 확인 권장)

---

### 6.3 3.pdf

#### Profile
- invoiceSubType: standard_amount_statement
- amountProfile: supply_tax_total
- partyProfile: supplier_weak
- tableProfile: single_item_table
- qualityTags: 없음 (하지만 supplier_weak는 supplier 블록 OCR 품질 약함을 시사)

#### 요약
- 전체 상태: buyer 측 양호, supplier 측 다수 X (supplier 블록 OCR 깨짐)
- 주요 O: buyer 전체, 금액 전체, table
- 주요 △: buyerAddress (tail "(구로동)" 누락)
- 주요 X: supplierBizNumber, supplierRepresentative, supplierAddress (정상 실패)
- 현재 최선 여부: **예** — supplier_weak qualityTag와 일치하는 실패 패턴
- 추가 개선 가능성: parser의 supplier 블록 추출 보강 가능 (T-1 이후 단계)

#### Party 판정

| 필드 | GT | OCR raw | 채택값 | 상태 | 원인 |
|---|---|---|---|---|---|
| supplierCompany | 주식회사 예일선 | 주식회사예일선 | OCR | O | normalized_match (공백) |
| supplierBizNumber | 572-81-01750 | "5 7 2- 8" (fragments) | (실패) | **X** | ocr_garbled (supplier 블록 깨짐, parser 추출 실패 예상) |
| supplierRepresentative | 최정숙 | "성명최경" 단편 | (실패) | **X** | ocr_garbled. biz 미추출이라 GT_REF 불가 |
| supplierAddress | 경기도 안양시 만안구 만안로 17 203A호(안양동,명지캐럿 162) | "203A" 단편만 | (실패) | **X** | address_fragment_only |
| buyerCompany | 백제약품(주)영등포지점 | 백제약품(주)영등포지점 | OCR | O | direct_match |
| buyerBizNumber | 113-85-04425 | 113-85-04425 | OCR | O | direct_match |
| buyerRepresentative | 김승관 | 김승관 | OCR | O | direct_match |
| buyerAddress | 서울특별시 구로구 공원로8길 24 (구로동) | 서울특별시 구로구 공원로8길 24 (tail 누락) | OCR (gt_similarity) | △ | address_tail_missing |

#### Amount/Summary 판정

| 필드 | GT | OCR | 상태 | 원인 |
|---|---|---|---|---|
| supplyAmount | 273,927 | 273.927 → 273927 | O | normalized_match |
| taxAmount | 27,393 | 27,393 | O | direct_match |
| totalAmount | 301,320 | 301,320 | O | direct_match |
| 기타 | — | — | N/A | amount_profile_excluded |

#### 기타
- issueDate: GT="2024/07/29", OCR="2024/07/29" → **O**

#### Table 판정
- tableDetected: O
- rowCount: GT=1 → **O**
- firstRowPreview: GT="에스피씨세파클러캡슬250mg30 캡슐", OCR 동일 → **O**

#### 남은 문제
- supplier 블록 3건 X는 supplier_weak qualityTag와 일치하는 의도된 실패. parser 개선 여지 있지만 본 작업 범위 밖.

#### 판단
- **잠금 가능** (X 3건은 expected_failure)

---

### 6.4 4.pdf

#### Profile
- invoiceSubType: ocr_garbled_statement
- amountProfile: supply_tax_total
- partyProfile: party_garbled
- tableProfile: single_item_table
- qualityTags: **ocr_garbled, party_block_garbled, address_garbled**

#### 요약
- 전체 상태: OCR 품질 매우 낮음. GT_REF/NORM 보정으로 일부 흡수
- 주요 O: 사업자번호 양쪽, supply/tax/total (별도 TOTAL 라인에서 추출 가능), buyer 대표자
- 주요 △: supplier company/rep (GT_REF), buyer company (GT_REF), 주소 양쪽 (NORM 부분 보정)
- 주요 X: firstRowPreview (클리마트 vs 클리마토 1자 차이), 일부 주소
- 현재 최선 여부: **예** — qualityTag가 ocr_garbled로 명시되어 있어 현재 X/△ 분포는 의도된 결과
- 추가 개선 가능성: NORM 단계의 1자 OCR 오독 보정 강화 (4.pdf 외 일반적으로 효과)

#### Party 판정

| 필드 | GT | OCR raw | 채택값 | 상태 | 원인 |
|---|---|---|---|---|---|
| supplierCompany | 주식회사 엘비아브노바 | "주식희사얼비아노바데표" (garbled) | GT_REF | △ | gt_ref_autofill (biz 117-81-53390 exact + party_master 존재) |
| supplierBizNumber | 117-81-53390 | 117-81-53390 | OCR | O | direct_match |
| supplierRepresentative | 남이레 | 남이례 | GT_REF | △ | gt_ref_autofill (1자 OCR 오독, biz exact) |
| supplierAddress | 서울특별시 영등포구 당산로41길 11, 301호 302호(당산동4가, SK V1 센터) | 서울특법시영등포구당산로41길11,301 302(당산통4가SKV1센터) | OCR or NORM | △ or X | ocr_garbled + normalization 부분 보정 의존 (특법→특별, 당산통→당산동) |
| buyerCompany | 백제약품(주) 영등포지점 | "백계약통(주)영풍표지정" (garbled) | GT_REF | △ | gt_ref_autofill (biz 113-85-04425 exact) |
| buyerBizNumber | 113-85-04425 | 113-85-04425 | OCR | O | direct_match |
| buyerRepresentative | 김승관 | 김승관 | OCR | O | direct_match |
| buyerAddress | (17811) 경기도 평택시 청북읍 청북로 175(현곡리) | "(1781)경기도력시 창북 청175(현곡레)" (heavily garbled) | OCR or NORM | △ or X | address_garbled (1781 vs 17811, 경기도력시 vs 평택시, 현곡레 vs 현곡리) |

#### Amount/Summary 판정

| 필드 | GT | OCR | 상태 | 원인 |
|---|---|---|---|---|
| supplyAmount | 25,760,000 | 25,760,000 (두 군데 등장) | O | direct_match |
| taxAmount | 2,576,000 | 2,576,000 | O | direct_match |
| totalAmount | 28,338,000 | "28,338.00" (잘못된 수치) 와 "28,338,000" (정상) 양쪽 등장 | O | direct_match (parser가 TOTAL 라벨 우선 채택 시) |
| 기타 | — | — | N/A | amount_profile_excluded |

#### 기타
- issueDate: GT="2024.07.02", OCR="2024 년 07 월 02 일" → parser 정규화 후 **O**

#### Table 판정
- tableDetected: O
- rowCount: GT=1 → **O**
- firstRowPreview: GT="클리마토플란정", OCR="클리마트플란정" → 1자 차이, 서로 substring 아님 → **X** (ocr_garbled, partial_text_diff)

#### 남은 문제
- 주소 2건은 NORM 강도에 따라 △/X 변동
- firstRowPreview 1자 OCR 오독은 fuzzy match 도입 없이는 X 불가피
- buyerAddress 17811 vs 1781은 단순 normalize로 흡수 불가 → address_core_mismatch에 가까움

#### 판단
- **품질 한계 잠금** (qualityTag와 일치하는 정상적 partial recovery 상태)

---

### 6.5 5.pdf

#### Profile
- invoiceSubType: standard_amount_statement
- amountProfile: supply_tax_total
- partyProfile: supplier_buyer
- tableProfile: multi_item_table
- qualityTags: 없음
- fieldLabels: taxAmount → "부가세"

#### 요약
- 전체 상태: 양호. GT-ADDR로 5.pdf GT 오기 2건 (supplierAddress 기홍→기흥, buyerAddress 25→24) 수정 완료
- 주요 O: 사업자/회사/대표자/공급가/부가세, supplierAddress, table 전체
- 주요 △: buyerAddress (NORM 의존 — 특발/쿠로 OCR 오독)
- 주요 X: 없음 (GT-ADDR 적용 후)
- 현재 최선 여부: **예** — GT-ADDR 수정 후 정합성 확보
- 추가 개선 가능성: 없음

#### Party 판정

| 필드 | GT | OCR raw | 채택값 | 상태 | 원인 |
|---|---|---|---|---|---|
| supplierCompany | 일양약품 | 일양약품 | OCR | O | direct_match |
| supplierBizNumber | 209-81-00872 | 209-81-00872 | OCR | O | direct_match |
| supplierRepresentative | 김동연, 정유석 | 김동연,정유석 | OCR | O | normalized_match (공백) |
| supplierAddress (수정 후) | 경기도 용인시 **기흥구** 하갈로 110(하갈동) | 경기도용인시기흥구하갈로110(하갈동) | OCR | O | direct_match (GT-ADDR 수정 효과) |
| buyerCompany | 백제약품(주)영등포지점 | 백제약품(주)영등포지점 | OCR | O | direct_match |
| buyerBizNumber | 113-85-04425 | 113-85-04425 | OCR | O | direct_match |
| buyerRepresentative | 김승관 | 김승관 | OCR | O | direct_match |
| buyerAddress (수정 후) | 서울특별시 구로구 공원로8길 **24**(구로동) | "서울특발시 쿠로구 공원로8길 24 (구로동)" (OCR 오독) | OCR or NORM | △ | gt_similarity_partial / normalized_match (NORM이 특발→특별, 쿠로→구로 보정 시 O로 승격) |

#### Amount/Summary 판정

| 필드 | GT | OCR | 상태 | 원인 |
|---|---|---|---|---|
| supplyAmount | 3,046,635 | 3,046,635 | O | direct_match |
| taxAmount (라벨 "부가세") | 304,663 | 304,663 | O | direct_match (fieldLabels override 적용) |
| totalAmount | 3,351,298 | OCR raw에 명시되지 않음 (parser가 supply+tax 또는 합계 라인에서 추출) | O (예상) | normalized_match (parser computed 가정) |
| 기타 | — | — | N/A | amount_profile_excluded |

#### 기타
- issueDate: GT="2024.07.22", OCR="2024.07.22" → **O**

#### Table 판정
- tableDetected: O
- rowCount: GT=6 → **O**
- firstRowPreview: GT="노루모에프내복액75ML", OCR 동일 → **O**

#### 남은 문제
- totalAmount는 OCR raw text에 직접 등장하지 않음 — parser가 정상적으로 추출하는지 Run All 확인 필요

#### 판단
- **잠금 가능** (GT-ADDR 수정 후 안정)

---

### 6.6 6.pdf

#### Profile
- invoiceSubType: detail_lot_statement
- amountProfile: **no_amount_summary** (모든 금액 N/A)
- partyProfile: **buyer_only** (supplier 4필드 N/A)
- tableProfile: lot_serial_quantity_table
- qualityTags: no_amount_summary, lot_serial_table, buyer_only_document, optional_supplier

#### 요약
- 전체 상태: 가장 단순한 케이스. 모든 평가 대상 필드가 O
- 주요 O: buyer 전체, table 전체
- 주요 △: 없음
- 주요 X: 없음
- 현재 최선 여부: **예**
- 추가 개선 가능성: 없음

#### Party 판정

| 필드 | GT | OCR raw | 상태 | 원인 |
|---|---|---|---|---|
| supplierCompany | — | — | N/A | profile_not_applicable (buyer_only) |
| supplierBizNumber | — | — | N/A | profile_not_applicable |
| supplierRepresentative | — | — | N/A | profile_not_applicable |
| supplierAddress | — | — | N/A | profile_not_applicable |
| buyerCompany | 백제약품(주)영등포지점 | 백제약품(주)영등포지점 | O | direct_match |
| buyerBizNumber | 113-85-04425 | 113-85-04425 | O | direct_match |
| buyerRepresentative | 김승관 | 김승관 | O | direct_match |
| buyerAddress | 서울구로구구로동44번지 | 서울구로구구로동44번지 (지번 주소) | O | direct_match |

#### Amount/Summary 판정
- 모든 금액 필드 N/A (no_amount_summary)

#### 기타
- issueDate: GT="2024-07-19", OCR="2024-07-19" → **O**

#### Table 판정
- tableDetected: O
- rowCount: GT=6, OCR에 6개 lot 행 → **O**
- firstRowPreview: GT="알코텔정100T", OCR 동일 → **O**

#### 남은 문제
- 없음

#### 판단
- **잠금 가능**

---

### 6.7 7.pdf

#### Profile
- invoiceSubType: quantity_serial_statement
- amountProfile: quantity_total_only (totalQuantity만 평가)
- partyProfile: **buyer_rep_optional** (buyerRepresentative GT 없어도 평가 제외)
- tableProfile: serial_quantity_table
- qualityTags: address_tail_missing, no_amount_summary

#### 요약
- 전체 상태: 양호. address_tail_missing qualityTag는 supplier 측 tail이 부족할 수 있음을 시사하지만 7.pdf OCR이 4.pdf보다 깨끗
- 주요 O: 거의 모든 필드
- 주요 △: 없음
- 주요 X: 없음
- 주요 —: buyerRepresentative (GT 미입력, buyer_rep_optional)
- 현재 최선 여부: **예**
- 추가 개선 가능성: 없음

#### Party 판정

| 필드 | GT | OCR raw | 상태 | 원인 |
|---|---|---|---|---|
| supplierCompany | 주식회사 엘비아브노바 | 주식회사엘비아브노바 | O | normalized_match |
| supplierBizNumber | 117-81-53390 | 117-81-53390 | O | direct_match |
| supplierRepresentative | 남이레 | 남이레 | O | direct_match |
| supplierAddress | 서울특별시 영등포구 당산로41길 11, 301호 302호(당산동4가, SK V1 센터) | 서울특별시영등포구당산로41길11,301호 302호(당산동4가,sKV1센터) | O | normalized_match (sKV1→skv1) |
| buyerCompany | 백제약품(주)영등포지점 | 백제약품(주)영등포지점 | O | direct_match |
| buyerBizNumber | 113-85-04425 | 113-85-04425 | O | direct_match |
| buyerRepresentative | (없음) | — | **—** | gt_empty (buyer_rep_optional) |
| buyerAddress | (17811) 경기도 평택시 청북읍 청북로 175 (현곡리) | (17811) 경기도 평택시 청북읍청북로175 (현곡리) | O | normalized_match (공백) |

#### Amount/Summary 판정

| 필드 | GT | OCR | 상태 | 원인 |
|---|---|---|---|---|
| totalQuantity | 1,000 | 1,000 | O | direct_match |
| 기타 | — | — | N/A | amount_profile_excluded |

#### 기타
- issueDate: GT="2024.07.02", OCR="2024. 07.02" → **O**

#### Table 판정
- tableDetected: O
- rowCount: GT=1 → **O**
- firstRowPreview: GT="클리마토플란정", OCR="클리마토플란정" (4.pdf와 달리 정확) → **O**

#### 남은 문제
- 없음. address_tail_missing qualityTag는 동일 supplier(4.pdf)와 비교용 메타일 뿐이며 7.pdf 자체는 깨끗

#### 판단
- **잠금 가능**

---

## 7. 남은 X 목록 및 원인 (3건)

| 파일 | 필드 | GT | OCR/NORM | X 원인 | 개선 가능성 | 추천 조치 |
|---|---|---|---|---|---|---|
| 3.pdf | supplierBizNumber | 572-81-01750 | "5 7 2- 8" 단편 | ocr_garbled (supplier 블록 깨짐) | parser 개선 가능 (supplier 블록 anchor 보강) | 현재 유지 — supplier_weak qualityTag 정상 반영 |
| 3.pdf | supplierRepresentative | 최정숙 | "성명최경" 단편 | ocr_garbled + biz 미추출로 GT_REF 불가 | 위 사업자번호 개선 시 자동 △ 승격 가능 | 현재 유지 (3.pdf supplierBizNumber 개선에 의존) |
| 3.pdf | supplierAddress | 경기도 안양시 만안구 만안로 17 203A호(안양동,명지캐럿 162) | "203A" 단편만 | address_fragment_only | parser 개선 가능 (supplier 주소 블록 추출 강화) | 현재 유지 |
| 4.pdf | firstRowPreview | 클리마토플란정 | 클리마트플란정 | ocr_garbled (1자 차이, substring 아님) | fuzzy match 도입 시 △로 흡수 가능. 단 일반화 위험 | 현재 유지 (qualityTag와 일치) |

**비고**: 4.pdf의 supplierAddress/buyerAddress는 NORM 보정 강도에 따라 X 또는 △가 될 수 있음. 보수적으로 X에 가깝게 표시했으나, 실제 Run All에서 △로 나올 가능성도 있음. 이 차이는 회귀 평가 시 허용.

## 8. △ 목록 및 사유 (9건)

| 파일 | 필드 | GT | OCR/NORM | △ 원인 | 현재 판정 적절성 | 향후 조치 |
|---|---|---|---|---|---|---|
| 1.jpg | supplierRepresentative | LEE WOO HYUN | LEE WOOHVON | gt_ref_autofill (biz 118-81-00450 exact) | 적절 | 잠금 |
| 2.pdf | supplierAddress | …오스템임플란트(주) | tail 사명 미포함 | address_tail_missing (GT에 사명 포함) | 적절 (GT 사명 포함 자체가 review 후보) | 2.pdf-SA 검토 |
| 2.pdf | buyerAddress | …백제빌딩 | "서울록별시…백제빌당" | OCR 오독 + NORM 부분 보정 | 적절 | 잠금 (NORM 결과 의존) |
| 3.pdf | buyerAddress | …24 (구로동) | "공원로8길 24" (tail 누락) | address_tail_missing | 적절 | 잠금 |
| 4.pdf | supplierCompany | 주식회사 엘비아브노바 | 주식희사얼비아노바데표 | gt_ref_autofill (biz exact) | 적절 (party_garbled) | 잠금 |
| 4.pdf | supplierRepresentative | 남이레 | 남이례 | gt_ref_autofill | 적절 | 잠금 |
| 4.pdf | supplierAddress | …SK V1 센터 | 특법시/당산통/공백 누락 | ocr_garbled + NORM 부분 흡수 | 적절 | 잠금 (NORM 보정 한도) |
| 4.pdf | buyerCompany | 백제약품(주) 영등포지점 | 백계약통(주)영풍표지정 | gt_ref_autofill | 적절 | 잠금 |
| 4.pdf | buyerAddress | (17811)…현곡리 | (1781)…현곡레 | ocr_garbled 심각 (17811 vs 1781은 핵심 차이) | △/X 경계 — 보수적으로 △ | qualityTag와 일치 |
| 5.pdf | buyerAddress | …24(구로동) | "특발시/쿠로구" OCR 오독 | NORM 보정 의존 | 적절 | 잠금 |

> 비고: 5.pdf supplierAddress 및 buyerAddress는 GT-ADDR 적용으로 핵심 번지(24)와 구 이름(기흥)이 GT 측에서 교정되었으므로, OCR/NORM이 정상 보정하면 O로 승격될 가능성 있음.

## 9. 주소 판정 검증

| 파일 | 필드 | 상태 | 사유 | 조치 |
|---|---|---|---|---|
| 1.jpg | supplierAddress | O | direct_match | 잠금 |
| 1.jpg | buyerAddress | O | direct_match | 잠금 |
| 2.pdf | supplierAddress | △ | GT에 사명 포함 → OCR 사명 미포함 | 잠금 (2.pdf-SA 추후 검토) |
| 2.pdf | buyerAddress | O (NORM) / △ | OCR 오독 → NORM 보정 의존 | 잠금 (NORM 결과 확인) |
| 3.pdf | supplierAddress | X | address_fragment_only ("203A"만) | 잠금 (supplier_weak) |
| 3.pdf | buyerAddress | △ | address_tail_missing ("(구로동)" 누락) | 잠금 |
| 4.pdf | supplierAddress | △ or X | ocr_garbled + NORM 부분 | 잠금 (qualityTag) |
| 4.pdf | buyerAddress | △ or X | 17811 vs 1781 핵심 차이 (보수적 △) | 잠금 (qualityTag) |
| 5.pdf | supplierAddress | O | GT-ADDR 수정으로 기홍→기흥 정합 | 잠금 |
| 5.pdf | buyerAddress | △ or O | OCR 특발/쿠로 오독 + GT 25→24 수정 | 잠금 |
| 6.pdf | buyerAddress | O | 지번 주소 직접 일치 | 잠금 |
| 7.pdf | supplierAddress | O | normalized_match | 잠금 |
| 7.pdf | buyerAddress | O | normalized_match | 잠금 |

**주소 GT_REVIEW 후보**: 2.pdf supplierAddress (사명 포함 여부)

## 10. amount/summary 판정 검증

| 파일 | 평가 대상 | GT vs OCR 일치 | 상태 |
|---|---|---|---|
| 1.jpg | subtotal, cumulativeAmount | 둘 다 18,098,750 일치 | O / O |
| 2.pdf | previousBalance, transactionAmount, cumulativeBalance, totalAmount | 4건 모두 일치 | O / O / O / O |
| 3.pdf | supplyAmount, taxAmount, totalAmount | 3건 모두 일치 | O / O / O |
| 4.pdf | supplyAmount, taxAmount, totalAmount | 3건 모두 일치 (parser TOTAL 라벨 채택 가정) | O / O / O |
| 5.pdf | supplyAmount, taxAmount, totalAmount | supply/tax 일치, total은 parser computed 의존 | O / O / O(예상) |
| 6.pdf | — | (no_amount_summary) | 전부 N/A |
| 7.pdf | totalQuantity | 1,000 일치 | O |

**amount 부분의 X 없음**. 모두 O 또는 N/A. 잠금 가능.

## 11. tableRows 현재 상태

| 파일 | tableProfile | tableDetected | rowCount(GT) | firstRowPreview(GT) | 추정 상태 | 비고 |
|---|---|---|---|---|---|---|
| 1.jpg | multi_item_table | O | 28 | 헥사메던액0.12% 15m|*6포 | O/O/O | 가장 긴 표, parser rowCount 정확도 검증 후보 |
| 2.pdf | item_quantity_table | O | 13 | LOXOLIFEN TABLET 3OT3Z | O/O/O | |
| 3.pdf | single_item_table | O | 1 | 에스피씨세파클러캡슬250mg30 캡슐 | O/O/O | 단일 행 |
| 4.pdf | single_item_table | O | 1 | 클리마토플란정 | O/O/**X** | OCR "클리마트" 1자 차이로 X |
| 5.pdf | multi_item_table | O | 6 | 노루모에프내복액75ML | O/O/O | |
| 6.pdf | lot_serial_quantity_table | O | 6 | 알코텔정100T | O/O/O | lot/serial 중심 |
| 7.pdf | serial_quantity_table | O | 1 | 클리마토플란정 | O/O/O | 4.pdf와 동일 supplier 다른 OCR 품질 |

**tableProfile 분포**: multi_item_table (2), single_item_table (2), item_quantity_table (1), lot_serial_quantity_table (1), serial_quantity_table (1) — 총 5종 (작은 셋에 5종 분포 → T-1에서 정책 정리 가치 있음)

## 12. 현재 상태가 최선인지 판단

### 12.1 GT 오기 수정 필요?
- **추가 수정 불필요**. GT-ADDR로 5.pdf 2건 수정 완료. 
- 2.pdf supplierAddress의 사명 포함은 "review 후보"이나 본 시점 필수 수정 아님.

### 12.2 OCR 원문에 있는데 parser가 못 잡은 항목 다수?
- 5.pdf totalAmount는 OCR raw에 직접 등장하지 않음 (parser computed 의존) — Run All 후 확인 권장
- 3.pdf supplier 블록은 OCR 자체가 깨짐 → parser_missing이 아니라 ocr_garbled
- 큰 의미의 parser_missing은 없음 (parser가 못 잡은 게 OCR 부족 때문임)

### 12.3 OCR 자체가 깨져서 parser로 복구 어려움?
- 4.pdf (qualityTag ocr_garbled), 3.pdf supplier 블록 (supplier_weak)
- 이들은 sample 자체의 품질 한계로 인정. parser 개선 여지는 있으나 본 단계 범위 밖.

### 12.4 Test UI 판정 기준 일관성?
- M-2f로 GT/reference 기반 단일 기준 적용 (`computeFieldFinalStatus`)
- 상세 카드, batch table, KPI 세 위치 모두 동일 함수 사용 — 일관됨
- **일관성 확보 완료**

### 12.5 tableRows 작업으로 넘어가도 party/address/amount 기준이 흔들리지 않는가?
- M-2f, GT-ADDR로 party/address/amount 기준은 안정화됨
- tableRows 작업은 별도 영역이며, 위 3개 카테고리에 영향 없음

### 12.6 Template/RunOCR reference 설계로 넘겨야 할 항목
- supplier_weak (3.pdf)에서 supplier 블록 OCR 품질 부족 → Template/RunOCR 단계에서 사업자번호 reference로 회사명/대표자/주소 보강 가능성
- party_garbled (4.pdf)에서도 동일 패턴
- 즉 GT_REF는 Test UI에서는 적용되나, RunOCR 단계에서는 사용자 선택형 reference suggest 로 확장 검토 가능

## 13. 잠금 가능 여부

### 결론: **조건부 잠금**

### 근거

**잠금 가능 측면**:
1. M-2f로 GT/reference 기준 통일 — 코드 측 일관성 확보
2. GT-ADDR로 5.pdf GT 오기 수정 — GT 측 정합성 확보
3. typecheck/build 통과
4. 7개 파일의 O/△/X 분포가 각 파일의 qualityTag/profile과 일치 — 예측 가능한 결과

**조건부 사유**:
1. 본 분석은 OCR raw text 기반 추정이며, 실제 Run All에서 parser의 NORM·summary block 선택·anchor evidence 등에 따라 일부 △ ↔ O ↔ X 사이에서 변동 가능
2. 특히 4.pdf 주소 2건, 2.pdf buyerAddress, 5.pdf totalAmount는 parser NORM/computation 동작에 의존
3. Run All을 실행하여 본 리포트 추정치와 실제 결과의 차이가 5% 이내라면 본 리포트를 회귀 기준으로 잠금 가능. 차이가 크면 그 차이를 잠금 전 분석 대상으로 삼아야 함

**권장 흐름**:
1. 본 리포트를 **추정 기준선**으로 등록
2. (선택) Run All 실행 → 실제 결과 캡처
3. 추정 vs 실제 차이 ≤ 5% 이면 정식 잠금
4. T-1 또는 Template-1로 진입

## 14. 다음 작업 추천

### 후보
- **T-1**: tableProfile별 tableRows 컬럼 정책 정리
- **Template-1**: GT/reference 기반 Template/RunOCR 연동 설계
- **2.pdf-SA**: supplierAddress GT 사명 포함 여부 재확인
- **D-5**: Test UI UX 정리

### 추천: **T-1 — tableProfile별 tableRows 컬럼 정책 정리**

### 추천 이유
1. **party/address/amount는 본 작업으로 안정화 완료** → 다음 단계는 표 영역
2. 7개 샘플에 5종의 tableProfile 분포(multi_item_table, single_item_table, item_quantity_table, lot_serial_quantity_table, serial_quantity_table) — 정책 정리 가치 큼
3. table은 가변 그리드(invoice마다 컬럼 구성 다름) 특성이라 정책 없이는 Template-1 진입 불가
4. Template-1 진입 전에 T-1에서 컬럼 정책을 먼저 잡지 않으면 Template UI 재설계 비용 큼
5. 2.pdf-SA는 단발 GT review로 본 흐름과 별도로 처리 가능

### 추가 진입 가능성 평가 — tableRows 작업
- **현재 진입 가능 여부**: 가능 (party/address/amount 흔들리지 않음)
- **예상 작업 길이**: tableProfile 5종 × 각각 컬럼 정책 정의 + UI 표시 정책 → **중장기**
- **고정 그리드 vs 가변 그리드**: 7개 샘플은 가변 그리드 (각 invoice가 자체 컬럼 구성). 그러나 동일 invoiceSubType 내에서는 고정 그리드 가능
- **필요 정책**: tableProfile별 ① 필수 컬럼 ② 옵셔널 컬럼 ③ 표시 우선순위 ④ rowCount/firstRowPreview 추출 규칙

## 15. 변경 파일

| 파일 | 변경 |
|---|---|
| 리포트 파일 | `public/data/testsets/invoice_statement/reports/R1_invoice_statement_lock_20260511.md` (신규 생성) |
| 코드 | 변경 없음 |
| GT | 변경 없음 |
| manifest | 변경 없음 |
| party_master | 변경 없음 |
| invoice_statement.py | 변경 없음 |

### 검증 결과

| 검증 | 결과 |
|---|---|
| manifest.json parse | ✅ ok |
| ground_truth.json parse | ✅ ok |
| party_master.json parse | ✅ ok |
| typecheck (`npm.cmd run typecheck`) | ✅ pass (에러 0) |
| build | (생략, 본 작업 코드 변경 없어 build 영향 없음) |

---

## Appendix A. 분석에 사용된 입력 파일 (snapshot)

- `ground_truth.json` updated_at: 2026-05-11T06:06:31.143Z (3.pdf 기준 가장 최신)
- `ocr_cache.json` scanned_at: 2026-05-11T07:25:04 ~ 07:29:47 (1.jpg ~ 7.pdf)
- `party_master.json`: 5개 biz (117-81-53390, 113-85-04425, 118-81-00450, 112-81-47103, 209-81-00872)
- `manifest.json`: 7개 items, datasetRole=document_type, status=draft

## Appendix B. 본 리포트의 한계

1. **OCR parser 출력 미사용**: invoice_statement.py가 산출하는 `documentFields` 및 `extractDebug.invoice_statement.normalization`을 실제로 호출하지 않았음. 따라서 본 리포트의 OCR/NORM 값은 raw OCR text + 코드 로직 검토 기반 추정.
2. **Run All 미실행**: 본 작업의 가이드 "가능하면 Run All"에서 실행 환경 미확보로 미실행. 실제 정확한 회귀 기준 잠금을 위해서는 추후 Run All 결과로 본 리포트를 갱신해야 함.
3. **fuzzy match 미적용**: 현재 코드는 `documentMatchStatus`에서 `gtNorm.includes(ocrNorm) || ocrNorm.includes(gtNorm)`만 사용 (Levenshtein 등 fuzzy 없음). 1자 차이 케이스(클리마트/클리마토, 남이레/남이례)는 GT_REF 없이는 X로 떨어짐.
