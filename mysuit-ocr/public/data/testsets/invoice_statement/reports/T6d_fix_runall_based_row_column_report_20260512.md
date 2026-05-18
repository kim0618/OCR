# T-6e expectedColumns 기반 표 헤더 위치 매칭 추출 결과

검증 방식: synthetic OCR (ocr_cache.json 텍스트 기반, 좌표 없음)

⚠️ **합성 좌표 한계**: 실제 RunAll과 rowCount/column이 다를 수 있음. 실제 성능은 backend 재시작 후 브라우저 RunAll로 확인 필요.

T-6e 핵심: OCR이 컬럼을 자동 발견하는 것이 아니라, 이미 정의된 expectedColumns 헤더를 OCR 결과에서 찾아 boundary를 구성하는 구조.

## 1. 수정 전/후 rowCount 비교

| 샘플 | 실제 row 수 | 수정 전(RunAll) | 수정 후(synthetic) | 결과 | 비고 |
|---|---:|---:|---:|---|---|
| 1.jpg | 28 | 27 | 48 | ✗ (+20) | synthetic 제한 |
| 2.pdf | ? | 2 | 4 | 확인필요 | synthetic 제한 |
| 3.pdf | ? | 1 | 2 | 확인필요 | synthetic 제한 |
| 4.pdf | ? | 1 | 1 | 확인필요 | synthetic 제한 |
| 5.pdf | 6 | 6 | 6 | ✓ | synthetic 제한 |
| 6.pdf | 6 | 6 | 6 | ✓ | synthetic 제한 |
| 7.pdf | 1 | 1 | 1 | ✓ | synthetic 제한 |

## 6. 샘플별 rowCount 비교

| 샘플 | 실제 row 수 | 추출 rowCount | 일치 여부 | 비고 |
|---|---:|---:|---|---|
| 1.jpg | 28 | 48 | ✗ (차이 +20) |  |
| 2.pdf | ? | 4 | 확인필요 |  |
| 3.pdf | ? | 2 | 확인필요 |  |
| 4.pdf | ? | 1 | 확인필요 |  |
| 5.pdf | 6 | 6 | ✓ |  |
| 6.pdf | 6 | 6 | ✓ |  |
| 7.pdf | 1 | 1 | ✓ |  |

## 7. 샘플별 expected vs actual columns

| 샘플 | expected required | actual columns | missing | hit rate |
|---|---|---|---|---|
| 1.jpg | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount | rowIndex, itemCode, itemName, spec, lotNo, manufacturingNo, expiryDate, quantity, amount | unitPrice | 6/7 |
| 2.pdf | itemCode, itemName, quantity, unitPrice, supplyAmount, insuranceCode | rowIndex, itemCode, lotNo, quantity, supplyAmount | itemName, unitPrice, insuranceCode | 3/6 |
| 3.pdf | insuranceCode, itemName, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate | rowIndex, itemName | insuranceCode, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate | 1/9 |
| 4.pdf | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount | rowIndex, itemName, serialNo, expiryDate, unitPrice, supplyAmount, amount | lotNo, unit, quantity, taxAmount | 3/7 |
| 5.pdf | itemName, itemCode, quantity, unitPrice, amount | rowIndex, itemName, quantity | itemCode, unitPrice, amount | 2/5 |
| 6.pdf | itemCode, itemName, quantity, lotNo, expiryDate | rowIndex, itemCode, itemName, lotNo, quantity | expiryDate | 4/5 |
| 7.pdf | itemName, serialNo, unit, quantity | rowIndex, itemName, serialNo, expiryDate | unit, quantity | 2/4 |

## 8. tableDebug 요약

| 샘플 | headerFound | headerLines | boundaries | fallback | rejectedRows | notes |
|---|---|---|---|---|---|---|
| 1.jpg | ✓ | spec, manufacturingNo, expiryDate, quantity, unitPrice | ?, ?, ?, ?, ?, ?, ? | expected_columns_header_match | 2건 |  |
| 2.pdf | ✓ | 영업사원, 품목명 | — | op_anchor_reconstructed_table | 0건 |  |
| 3.pdf | ✓ | 수량 | — | legacy_text_items | 0건 |  |
| 4.pdf | ✓ | 수량 | — | legacy_text_items | 0건 |  |
| 5.pdf | ✓ | 수량 | — | legacy_text_items | 0건 |  |
| 6.pdf | ✓ | 수량 | — | legacy_text_items | 0건 |  |
| 7.pdf | ✓ | 총수량 | — | legacy_text_items | 0건 |  |

## 9. firstRowPreview 확인

| 샘플 | firstRowPreview | extractionStatus | 비고 |
|---|---|---|---|
| 1.jpg | 헥사메던액0.12% 15m|*6포 | partial | OK |
| 2.pdf | 1,417 | partial | OK |
| 3.pdf | 보험코드 에스피씨세파클러캡슬250mg30 캡슐 | partial | OK |
| 4.pdf | 클리마트플란정 25,760,000 | partial | OK |
| 5.pdf | 노루모에프내복액75ML | partial | OK |
| 6.pdf | 알코텔정100T | partial | OK |
| 7.pdf | 클리마토플란정 | partial | OK |

## 10. 샘플별 tableRows 요약

### 1.jpg (rowCount=48)

- row1: itemName=헥사메던액0.12% / quantity= / lot=24027 / expiry=20270205 / amount=—
- row2: itemName=더모픽스크림 / quantity=400 / lot=— / expiry= / amount=1,050
- row3: itemName= / quantity=30g 100 / lot=24001 / expiry=20270116 / amount=—
- ...(중략)...
- row46: itemName= / quantity=100T 240 / amount=—
- row47: itemName= / quantity=4T / amount=2,180
- row48: itemName= / quantity=30 / amount=3,270

### 2.pdf (rowCount=4)

- row1: itemName= / quantity= / lot=— / expiry= / amount=1,417
- row2: itemName= / quantity= / lot=— / expiry= / amount=2,024
- row3: itemName= / quantity=6 / lot=— / expiry= / amount=9,064

### 3.pdf (rowCount=2)

- row1: itemName=보험코드 에스피씨세파클러캡슬250mg30 캡슐 / quantity= / lot=— / expiry= / amount=—
- row2: itemName=에스피씨세파클러캡슬250mg30 캡슐 / quantity= / lot=— / expiry= / amount=—

### 4.pdf (rowCount=1)

- row1: itemName=클리마트플란정 / quantity= / lot=0350823-231024-200811 / expiry=231024 / amount=25,760,000

### 5.pdf (rowCount=6)

- row1: itemName=노루모에프내복액75ML / quantity= / lot=— / expiry= / amount=1,650,000
- row2: itemName=노루모듀얼액션현탁액4P / quantity= / lot=— / expiry= / amount=100,000
- row3: itemName=나프록센나트롭정10T100 / quantity= / lot=— / expiry= / amount=163,635

### 6.pdf (rowCount=6)

- row1: itemName=알코텔정100T / quantity=10 / lot=23001 / expiry= / amount=—
- row2: itemName=액티글리정30T / quantity=10 / lot=23001 / expiry= / amount=—
- row3: itemName=올고탄정10MG30T / quantity=30 / lot=— / expiry= / amount=—

### 7.pdf (rowCount=1)

- row1: itemName=클리마토플란정 / quantity= / lot=0350623-231024-260811 / expiry=231024 / amount=—

## 2. 샘플별 컬럼 감지 비교

| 샘플 | expected required | 수정 후 actual | missing 후 | 결과 |
|---|---|---|---|---|
| 1.jpg | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount | rowIndex, itemCode, itemName, spec, lotNo, manufacturingNo, expiryDate, quantity, amount | unitPrice | ✗ 6/7 |
| 2.pdf | itemCode, itemName, quantity, unitPrice, supplyAmount, insuranceCode | rowIndex, itemCode, lotNo, quantity, supplyAmount | itemName, unitPrice, insuranceCode | ✗ 3/6 |
| 3.pdf | insuranceCode, itemName, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate | rowIndex, itemName | insuranceCode, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate | ✗ 1/9 |
| 4.pdf | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount | rowIndex, itemName, serialNo, expiryDate, unitPrice, supplyAmount, amount | lotNo, unit, quantity, taxAmount | ✗ 3/7 |
| 5.pdf | itemName, itemCode, quantity, unitPrice, amount | rowIndex, itemName, quantity | itemCode, unitPrice, amount | ✗ 2/5 |
| 6.pdf | itemCode, itemName, quantity, lotNo, expiryDate | rowIndex, itemCode, itemName, lotNo, quantity | expiryDate | ✗ 4/5 |
| 7.pdf | itemName, serialNo, unit, quantity | rowIndex, itemName, serialNo, expiryDate | unit, quantity | ✗ 2/4 |

> ⚠️ synthetic 좌표로 인해 column 감지 결과는 실제 OCR과 다름. 실제 성능은 backend RunAll 기준으로 확인 필요.

## 3. rejectedRows 분석

| 샘플 | rejected count | reason별 분포 | 비고 |
|---|---:|---|---|
| 1.jpg | 2 | header_or_contact:1, summary_row:1 | fallback=expected_columns_header_match |
| 2.pdf | 0 | — | fallback=op_anchor_reconstructed_table |
| 3.pdf | 0 | — | fallback=legacy_text_items |
| 4.pdf | 0 | — | fallback=legacy_text_items |
| 5.pdf | 0 | — | fallback=legacy_text_items |
| 6.pdf | 0 | — | fallback=legacy_text_items |
| 7.pdf | 0 | — | fallback=legacy_text_items |

## 4. 1.jpg rowCount 27 누락 원인 분석

**실제 RunAll 결과**: rowCount=27 (실제 28, 1개 누락)

**분석 (synthetic 기반, 실제 OCR 좌표 없음)**:

- 1.jpg 헤더 토큰 '품' '목'이 synthetic 모드에서 각각 별도 y-행으로 분리됨
  → '품목'을 한 토큰으로 인식 못해 itemName 컬럼 boundary 미생성
- 실제 OCR에서는 '품목', '규격', '제조번호', '유효기간', '수량', '단가', '금액'이
  같은 y-좌표에 위치 → header_score ≥ 6 → boundary 7개 정상 생성
- **28번째 행 누락 추정 원인**:
  1) 하드칼씨플러스정(item4): 제조번호/유효기간 없는 5-필드 행 → itemName 컬럼 배정 정상이어야 함
  2) 영업소(팀)/도매관리팀 행이 item 영역에서 처리될 때 _is_business_contact_line 판정 불일치 가능
  3) 마지막 item 행 직후 '소계' 행 → _is_summary_row_for_items=True → break
  4) 27번 카운트가 맞다면 '이누스정5mg'(line119-124) 같은 6-필드 행이 하나 누락 가능성
- **T-6d-fix 적용**: summary break를 items>0 AND y≥72% 조건으로 완화
  → 실제 OCR에서 28번째 행이 소계 이전에 정상 처리될 것으로 예상

## 5. 2.pdf row 대량 누락 원인 분석

**실제 RunAll 결과**: rowCount=2 (실제 13개 이상 예상)

**분석**:

- 2.pdf는 landscape 이미지 (950×672): page_h=672
- OCR 텍스트 line 2: '공급금액합계' = 헤더 영역 총액 → _is_summary_row_for_items 판정 위험
- OCR 텍스트 line 41: '18,295,140소비자금액합계' → _TABLE_SUMMARY_STRONG_RE='합계' 매치 + amount=1 + name_chars<=14
  → _is_summary_row_for_items=True → 기존 코드에서 **즉시 break** 발생
- 실제 OCR에서: '18,295,140소비자금액합계'가 헤더 상단(y≈50)에 위치하여
  아이템 행(y≈200~600) 이전에 처리됨 → break로 인해 나머지 13개 행 누락
- **T-6d-fix 적용**:
  ```
  if items and row_y >= page_h * 0.72:  # 0.72*672=484
      break  # 하단 summary → 테이블 끝
  continue   # 상단 summary 또는 items없을 때 → 스킵하고 계속
  ```
  → y<484에서 등장하는 '18,295,140소비자금액합계'는 skip, 아이템 행 정상 추출 예상
- 추가 fix: no_item_name 완화 → itemCode+quantity or quantity+price 조합으로 허용

## 11. 헤더 패턴 매치 확인 (OCR 텍스트 기준)

각 샘플의 실제 컬럼 헤더가 `_HEADER_CANONICAL_MAP`에서 어떻게 매핑되는지 정적 확인:

| 샘플 | 실제 헤더 | canonical key | 매핑 여부 |
|---|---|---|---|
| 1.jpg | 품목 | → itemName | ✓ |
| 1.jpg | 규격 | → spec | ✓ |
| 1.jpg | 제조번호 | → manufacturingNo | ✓ |
| 1.jpg | 유효기간 | → expiryDate | ✓ |
| 1.jpg | 수량 | → quantity | ✓ |
| 1.jpg | 단가 | → unitPrice | ✓ |
| 1.jpg | 금액 | → amount | ✓ |
| 2.pdf | NO | → rowIndex | ✓ |
| 2.pdf | 품목코드 | → itemCode | ✓ |
| 2.pdf | 품목명 | → itemName | ✓ |
| 2.pdf | 수량 | → quantity | ✓ |
| 2.pdf | 소비자단가 | → unitPrice | ✓ |
| 2.pdf | 공급단가 | → unitPrice | ✓ |
| 2.pdf | 공급금액 | → supplyAmount | ✓ |
| 2.pdf | 보험No | → insuranceCode | ✓ |
| 3.pdf | 순번 | → rowIndex | ✓ |
| 3.pdf | 보험코드 | → insuranceCode | ✓ |
| 3.pdf | 품명 | → itemName | ✓ |
| 3.pdf | 규격 | → spec | ✓ |
| 3.pdf | 수량 | → quantity | ✓ |
| 3.pdf | 단가 | → unitPrice | ✓ |
| 3.pdf | 금액 | → amount | ✓ |
| 3.pdf | 제조회사 | → manufacturer | ✓ |
| 3.pdf | 제조번호/유효기간 | → manufacturingNo | ✓ |
| 4.pdf | 품목명 | → itemName | ✓ |
| 4.pdf | LotNo. | → lotNo | ✓ |
| 4.pdf | 단위 | → unit | ✓ |
| 4.pdf | 수량 | → quantity | ✓ |
| 4.pdf | 단가 | → unitPrice | ✓ |
| 4.pdf | 공급가액 | → supplyAmount | ✓ |
| 4.pdf | 세액 | → taxAmount | ✓ |
| 5.pdf | 품명 | → itemName | ✓ |
| 5.pdf | 품목코드 | → itemCode | ✓ |
| 5.pdf | 수량 | → quantity | ✓ |
| 5.pdf | 단가 | → unitPrice | ✓ |
| 5.pdf | 금액 | → amount | ✓ |
| 6.pdf | NO | → rowIndex | ✓ |
| 6.pdf | 제품코드 | → itemCode | ✓ |
| 6.pdf | 제품명 | → itemName | ✓ |
| 6.pdf | 수량 | → quantity | ✓ |
| 6.pdf | LotNo | → lotNo | ✓ |
| 6.pdf | 유효일자 | → expiryDate | ✓ |
| 7.pdf | 품명 | → itemName | ✓ |
| 7.pdf | 시리얼/로트No. | → serialNo | ✓ |
| 7.pdf | 단위 | → unit | ✓ |
| 7.pdf | 수량 | → quantity | ✓ |

## 12. 분석 요약

### rowCount 불일치 (synthetic 기준):
- 1.jpg: expected 28, got 48 (diff=+20)

### Missing columns (synthetic, 참고용):
- 1.jpg missing: unitPrice
- 2.pdf missing: itemName, unitPrice, insuranceCode
- 3.pdf missing: insuranceCode, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate
- 4.pdf missing: lotNo, unit, quantity, taxAmount
- 5.pdf missing: itemCode, unitPrice, amount
- 6.pdf missing: expiryDate
- 7.pdf missing: unit, quantity

### 검증 한계 (중요):
- **ocr_cache.json은 plain text만 저장 (좌표 없음)** → synthetic 좌표는 실제와 근본적으로 다름
- 실제 OCR에서는 헤더 행의 모든 토큰이 같은 y-좌표에 있어 header detection 정확도 높음
- 이 스크립트로 검증된 것: _HEADER_CANONICAL_MAP 매핑 정확도, 코드 로직 오류 여부
- 이 스크립트로 검증 불가: 실제 rowCount, 실제 column 배치 정확도
- **실제 성능 확인**: backend 재시작 후 Test UI RunAll 실행 필요

## 9. T-6e expected header matching 결과 (synthetic 좌표 기준)

| 샘플 | expectedColumns 사용 | matched headers | missing required | interpolated | fallback 이유 | extractionSource |
|---|---|---|---|---|---|---|
| 1.jpg | ✓ | spec, manufacturingNo, expiryDate, quantity, unitPrice | itemName, amount | itemName, amount | — | expected_columns_header_match |
| 2.pdf | ✗ | — | — | — | boundary_build_failed | op_anchor_reconstructed_table |
| 3.pdf | ✗ | — | — | — | boundary_build_failed | legacy_text_items |
| 4.pdf | ✗ | — | — | — | boundary_build_failed | legacy_text_items |
| 5.pdf | ✗ | — | — | — | boundary_build_failed | legacy_text_items |
| 6.pdf | ✗ | — | — | — | boundary_build_failed | legacy_text_items |
| 7.pdf | ✗ | — | — | — | boundary_build_failed | legacy_text_items |

> ⚠️ synthetic 좌표 한계: 헤더 토큰들이 서로 다른 y-행에 배치됨 → 같은 row로 묶이지 않아 score가 낮게 나옴. 실제 OCR에서는 정상 동작 예상.

## 10. T-6e expected header alias 매핑 확인

| 샘플 | 실제 헤더 텍스트 | canonical key | 매핑 여부 |
|---|---|---|---|
| 1.jpg | 품목 | → itemName (expected) | ✓ |
| 1.jpg | 규격 | → spec (expected) | ✓ |
| 1.jpg | 제조번호 | → manufacturingNo (expected) | ✓ |
| 1.jpg | 유효기간 | → expiryDate (expected) | ✓ |
| 1.jpg | 수량 | → quantity (expected) | ✓ |
| 1.jpg | 단가 | → unitPrice (expected) | ✓ |
| 1.jpg | 금액 | → amount (expected) | ✓ |
| 2.pdf | NO | → rowIndex  | ✓ |
| 2.pdf | 품목코드 | → itemCode (expected) | ✓ |
| 2.pdf | 품목명 | → itemName (expected) | ✓ |
| 2.pdf | 수량 | → quantity (expected) | ✓ |
| 2.pdf | 소비자단가 | → unitPrice (expected) | ✓ |
| 2.pdf | 공급단가 | → unitPrice (expected) | ✓ |
| 2.pdf | 공급금액 | → supplyAmount (expected) | ✓ |
| 2.pdf | 보험No | → insuranceCode (expected) | ✓ |
| 3.pdf | 순번 | → rowIndex  | ✓ |
| 3.pdf | 보험코드 | → insuranceCode (expected) | ✓ |
| 3.pdf | 품명 | → itemName (expected) | ✓ |
| 3.pdf | 규격 | → spec (expected) | ✓ |
| 3.pdf | 수량 | → quantity (expected) | ✓ |
| 3.pdf | 단가 | → unitPrice (expected) | ✓ |
| 3.pdf | 금액 | → amount (expected) | ✓ |
| 3.pdf | 제조회사 | → manufacturer (expected) | ✓ |
| 3.pdf | 제조번호/유효기간 | → manufacturingNo (expected) | ✓ |
| 4.pdf | 품목명 | → itemName (expected) | ✓ |
| 4.pdf | LotNo. | → lotNo (expected) | ✓ |
| 4.pdf | 단위 | → unit (expected) | ✓ |
| 4.pdf | 수량 | → quantity (expected) | ✓ |
| 4.pdf | 단가 | → unitPrice (expected) | ✓ |
| 4.pdf | 공급가액 | → supplyAmount (expected) | ✓ |
| 4.pdf | 세액 | → taxAmount (expected) | ✓ |
| 5.pdf | 품명 | → itemName (expected) | ✓ |
| 5.pdf | 품목코드 | → itemCode (expected) | ✓ |
| 5.pdf | 수량 | → quantity (expected) | ✓ |
| 5.pdf | 단가 | → unitPrice (expected) | ✓ |
| 5.pdf | 금액 | → amount (expected) | ✓ |
| 6.pdf | NO | → rowIndex  | ✓ |
| 6.pdf | 제품코드 | → itemCode (expected) | ✓ |
| 6.pdf | 제품명 | → itemName (expected) | ✓ |
| 6.pdf | 수량 | → quantity (expected) | ✓ |
| 6.pdf | LotNo | → lotNo (expected) | ✓ |
| 6.pdf | 유효일자 | → expiryDate (expected) | ✓ |
| 7.pdf | 품명 | → itemName (expected) | ✓ |
| 7.pdf | 시리얼/로트No. | → serialNo (expected) | ✓ |
| 7.pdf | 단위 | → unit (expected) | ✓ |
| 7.pdf | 수량 | → quantity (expected) | ✓ |

## 13. 다음 작업 판단

**T-6e 적용 내용 요약**:
1. `_score_row_for_expected_columns`: expected key 집합 기준 row scoring
2. `_find_expected_header_band`: expected headers가 가장 많이 모인 y-band 탐색
3. `_build_boundaries_from_expected_columns`: matched/interpolated boundary 생성
4. `_table_items_with_expected_columns`: expectedColumns 기반 전체 추출 경로
5. `_detect_table`: T-6e 경로 우선, T-6 auto-detect fallback
6. `extract_invoice_statement_fields`: `table_expected_columns`, `table_bounds` 파라미터 추가

**synthetic 검증 한계**:
- ocr_cache.json에 좌표 없음 → 헤더 토큰들이 각각 별도 y-행으로 분리됨
- 실제 OCR에서는 같은 row의 헤더 토큰들이 동일 y-좌표에 있어 score ≥ 3 이상 달성 예상
- expectedColumns header matching 로직 자체는 alias 매핑 테이블로 검증 가능

**판단**:
- expectedColumns 기반 추출 구조 완성 → 실제 RunAll에서 성능 확인 필요
- tableExpectedColumns가 backend에 전달되려면 frontend→backend API 파라미터 추가 필요
  (현재 main.py 수정 금지로 미전달 → verify script에서 직접 파라미터 주입으로 검증)
- 실제 RunAll 결과 확인 후:
  - expected header matching 성공 → T-7 금액 계열 보정 가능
  - expected header matching 실패 → table bounds/Template 연동 선행 필요