# T-8a 5.pdf 다단 OCR layout value mapping 결과

**작업일**: 2026-05-14
**모델**: Claude Code Sonnet

---

## 1. 수정 파일

- `ocr-server/extractors/invoice_statement.py`: `_postprocess_multiline_column_layout` 함수 추가 + `extract_invoice_statement_fields` T-8a 호출 블록

## 2. 백업 파일

- `backup/invoice_statement_20260514_before_T8a_multiline_layout.py`

## 3. 핵심 요약

5.pdf의 itemCode/unitPrice/amount를 OCR 다단 블록 위치 매핑으로 복구했다.

- 기존: itemCode 0/6, unitPrice 0/6, amount 0/6
- 개선: itemCode 6/6, unitPrice 6/6, amount 6/6
- fill rate: 14.8% to 48.1% (+33.3%)
- rowCount 6/6 유지, 다른 샘플 회귀 없음

## 4. 5.pdf OCR 원문 후보 분석

| 후보 유형 | 후보 수 | 예시 | 판정 |
|---|---:|---|---|
| itemCode (연속 블록) | 6/6 | NRFS75M, NRDA4P, NPRT1OT, NASP15P, INAP250G, DPNL30M | 매핑 성공 |
| unitPrice (단가 이후) | 6/6 | 2,000 / 2,300 / 4,000 / 2,730 / 550 / 545 | 매핑 성공 |
| amount (금액 이후) | 6/6 | 1,650,000 / 100,000 / 163,635 / 460,000 / 400,000 / 273,000 | 매핑 성공 |
| amount 합계 검증 | - | 3,046,635 = 문서 공급가액 | 일치 |
| quantity (수량 이후) | 불완전 | 3,000 / 300 / 9 / C(잡음) / 100 | 부정확 - 미적용 |

## 5. 적용한 guard 조건

1. extractionSource == "legacy_text_items" (header 미검출 경로)
2. rowCount >= 2
3. expected columns에 itemCode / unitPrice / amount 포함
4. 해당 컬럼이 50% 이상 비어 있음
5. OCR에서 정확히 N개의 연속 코드 블록 / 라벨 이후 N개 숫자 발견
6. itemName으로 OCR-행 순서 매핑 가능

현재 테스트셋에서 guard를 통과하는 샘플: 5.pdf 전용 (다른 샘플은 legacy_text_items 경로 아님)

## 6. 5.pdf before/after

| key | before filled | after filled | 변화 | 비고 |
|---|---:|---:|---:|---|
| itemName | 6 | 6 | 0 | 유지 |
| itemCode | 0 | 6 | +6 | OCR 연속 블록에서 매핑 |
| quantity | 2 | 2 | 0 | 불완전 OCR - 미적용 |
| unitPrice | 0 | 6 | +6 | 단가 라벨 이후 추출 |
| amount | 0 | 6 | +6 | 금액 라벨 이후 추출 |

## 7. rowCount 회귀 확인

| 샘플 | GT | OCR | 상태 |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | OK |
| 2.pdf | 13 | 13 | OK |
| 3.pdf | 1 | 1 | OK |
| 4.pdf | 1 | 1 | OK |
| 5.pdf | 6 | 6 | OK |
| 6.pdf | 6 | 6 | OK |
| 7.pdf | 1 | 1 | OK |

## 8. valueMappingWarnings

| 샘플 | warnings |
|---|---|
| 5.pdf | multiline_layout_mapping_applied |
| 4.pdf | taxAmount=doc_level_pushdown; totalAmount=doc_level_pushdown |
| 2.pdf | insuranceCode:ocr_source_missing:... |
| 3.pdf | insuranceCode:ocr_source_missing:... |

## 9. 검증 결과

| 검증 항목 | 결과 |
|---|---|
| py_compile extractors/invoice_statement.py | PASS |
| python scripts/verify_invoice_table_rows_t8a.py | PASS (rowCount 7/7, 5.pdf +33.3%) |
| npm run typecheck | PASS |
| npm run build | PASS |

## 10. 다음 작업 판단

T-8a 완료.

5.pdf itemCode/unitPrice/amount 모두 6/6 복구 성공.

남은 한계:
- 5.pdf quantity: OCR 수량 섹션 불완전 (잡음 포함), 2/6 유지
- 5.pdf supplyAmount/taxAmount/totalAmount: OCR 원문 연결 불가

T-8 시리즈 완료 판단:
- rowCount 7/7 exact 유지
- 4.pdf taxAmount/totalAmount 복구 (T-7a)
- 7.pdf quantity=1,000 복구 (T-7a)
- 2.pdf/3.pdf insuranceCode OCR source missing warning 추가 (T-8b)
- 5.pdf itemCode/unitPrice/amount 복구 (T-8a)
- Test UI warning 표시 추가 (T-8b)
