# T-6d 거래명세서 tableRows 자동 검증 결과

검증 방식: 합성 좌표(synthetic OCR) 기반 추출 — column 배치는 근사치, rowCount/header 감지는 실제와 유사

## 6. 샘플별 rowCount 비교

| 샘플 | 실제 row 수 | 추출 rowCount | 일치 여부 | 비고 |
|---|---:|---:|---|---|
| 1.jpg | 28 | 27 | ✗ (차이 -1) |  |
| 2.pdf | ? | 2 | 확인필요 |  |
| 3.pdf | ? | 2 | 확인필요 |  |
| 4.pdf | ? | 1 | 확인필요 |  |
| 5.pdf | 6 | 6 | ✓ |  |
| 6.pdf | 6 | 6 | ✓ |  |
| 7.pdf | 1 | 1 | ✓ |  |

## 7. 샘플별 expected vs actual columns

| 샘플 | expected required | actual columns | missing | hit rate |
|---|---|---|---|---|
| 1.jpg | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount | rowIndex, itemCode, itemName, spec, lotNo, expiryDate, quantity, unitPrice, supplyAmount ...+3 | manufacturingNo | 6/7 |
| 2.pdf | itemCode, itemName, quantity, unitPrice, supplyAmount, insuranceCode | rowIndex, itemName, spec | itemCode, quantity, unitPrice, supplyAmount, insuranceCode | 1/6 |
| 3.pdf | insuranceCode, itemName, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate | rowIndex, itemName | insuranceCode, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate | 1/9 |
| 4.pdf | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount | rowIndex, itemName, unitPrice, supplyAmount, amount | lotNo, unit, quantity, taxAmount | 3/7 |
| 5.pdf | itemName, itemCode, quantity, unitPrice, amount | rowIndex, itemName, quantity | itemCode, unitPrice, amount | 2/5 |
| 6.pdf | itemCode, itemName, quantity, lotNo, expiryDate | rowIndex, itemCode, itemName, lotNo, quantity | expiryDate | 4/5 |
| 7.pdf | itemName, serialNo, unit, quantity | rowIndex, itemName | serialNo, unit, quantity | 1/4 |

## 8. tableDebug 요약

| 샘플 | headerFound | headerLines | boundaries | fallback | rejectedRows | notes |
|---|---|---|---|---|---|---|
| 1.jpg | ✓ | 목, 규격, 제조번호, 유효기간, 수량 ...+1 | spec, manufacturingNo, expiryDate, quantity, unitPrice | legacy_text_items | 6건 |  |
| 2.pdf | ✓ | 전일잔액, 영업사원, 품목명 | — | legacy_text_items | 0건 |  |
| 3.pdf | ✓ | 수량 | — | legacy_text_items | 0건 |  |
| 4.pdf | ✓ | 수량 | — | legacy_text_items | 0건 |  |
| 5.pdf | ✓ | 수량, 9 | — | legacy_text_items | 0건 |  |
| 6.pdf | ✓ | 수량 | — | legacy_text_items | 0건 |  |
| 7.pdf | ✓ | 총수량 | — | legacy_text_items | 0건 |  |

## 9. firstRowPreview 확인

| 샘플 | firstRowPreview | extractionStatus | 비고 |
|---|---|---|---|
| 1.jpg | 더모픽스크림 | partial | OK |
| 2.pdf | LOXOLIFEN TABLET 3OT3Z | partial | OK |
| 3.pdf | 보험코드 에스피씨세파클러캡슬250mg30 캡슐 | partial | OK |
| 4.pdf | 클리마트플란정 25,760,000 | partial | OK |
| 5.pdf | 노루모에프내복액75ML | partial | OK |
| 6.pdf | 알코텔정100T | partial | OK |
| 7.pdf | 클리마토플란정 | partial | OK |

## 10. 샘플별 tableRows 요약

### 1.jpg (rowCount=27)

- row1: itemName=더모픽스크림 / quantity=400 / lot=24001 / expiry= / amount=—
- row2: itemName=하드칼추어블이지정 / quantity=100 / lot=— / expiry=20270116 / amount=—
- row3: itemName=레가론캡슬140 / quantity=40 / lot=— / expiry= / amount=—
- ...(중략)...
- row25: itemName=나덕사크림 / quantity=100 / amount=—
- row26: itemName=오르필시럽 / quantity=320 / amount=4,320,000
- row27: itemName=소아용프리마란시럽 / quantity=30 / amount=—

### 2.pdf (rowCount=2)

- row1: itemName=LOXOLIFEN / quantity= / lot=— / expiry= / amount=—
- row2: itemName=AMOXIS / quantity= / lot=— / expiry= / amount=—

### 3.pdf (rowCount=2)

- row1: itemName=보험코드 에스피씨세파클러캡슬250mg30 캡슐 / quantity= / lot=— / expiry= / amount=—
- row2: itemName=에스피씨세파클러캡슬250mg30 캡슐 / quantity= / lot=— / expiry= / amount=—

### 4.pdf (rowCount=1)

- row1: itemName=클리마트플란정 / quantity= / lot=— / expiry= / amount=25,760,000

### 5.pdf (rowCount=6)

- row1: itemName=노루모에프내복액75ML / quantity= / lot=— / expiry= / amount=—
- row2: itemName=노루모듀얼액션현탁액4P / quantity= / lot=— / expiry= / amount=—
- row3: itemName=나프록센나트롭정10T100 / quantity= / lot=— / expiry= / amount=—

### 6.pdf (rowCount=6)

- row1: itemName=알코텔정100T / quantity=10 / lot=23001 / expiry= / amount=—
- row2: itemName=액티글리정30T / quantity=10 / lot=23001 / expiry= / amount=—
- row3: itemName=올고탄정10MG30T / quantity=30 / lot=— / expiry= / amount=—

### 7.pdf (rowCount=1)

- row1: itemName=클리마토플란정 / quantity= / lot=— / expiry= / amount=—

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
| 2.pdf | NO | ❌ 매핑 없음 | ✗ |
| 2.pdf | 품목코드 | → itemCode | ✓ |
| 2.pdf | 품목명 | → itemName | ✓ |
| 2.pdf | 수량 | → quantity | ✓ |
| 2.pdf | 소비자단가 | → unitPrice | ✓ |
| 2.pdf | 공급단가 | → unitPrice | ✓ |
| 2.pdf | 공급금액 | → supplyAmount | ✓ |
| 2.pdf | 보험No | → insuranceCode | ✓ |
| 3.pdf | 순번 | ❌ 매핑 없음 | ✗ |
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
| 6.pdf | NO | ❌ 매핑 없음 | ✗ |
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

### rowCount 불일치:
- 1.jpg: expected 28, got 27 (diff=-1)

### Missing columns (expected required 기준):
- 1.jpg missing: manufacturingNo
- 2.pdf missing: itemCode, quantity, unitPrice, supplyAmount, insuranceCode
- 3.pdf missing: insuranceCode, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate
- 4.pdf missing: lotNo, unit, quantity, taxAmount
- 5.pdf missing: itemCode, unitPrice, amount
- 6.pdf missing: expiryDate
- 7.pdf missing: serialNo, unit, quantity

### 검증 한계:
- 합성 좌표 기반이므로 column 배치 결과는 실제 OCR과 다를 수 있음
- rowCount는 `_is_summary_row_for_items` / `_is_table_header_row` 필터 영향으로 부정확 가능
- 실제 column boundary 정확도는 브라우저 테스트 필요 (backend 재시작 후 OCR 재실행)

## 13. 다음 작업 판단

- ⚠️ rowCount 불일치 있음 → T-6d-fix row grouping 재보정 필요
- ⚠️ column boundary 미감지 항목 있음 → 실제 OCR 좌표 기반 브라우저 테스트 필요
- 실제 OCR 좌표 기반 완전 검증은 backend 재시작 후 브라우저에서 확인 필요
- 헤더 패턴 매핑 완료 확인 → T-7 금액 계열 보강 또는 T-6e Template table bounds 연동으로 진행 가능