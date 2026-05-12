# T-6g expectedColumns schema 기준 row grouping / rowCount 보정 결과

## 1. 수정 파일
- `C:\OCR\ocr-server\extractors\invoice_statement.py`

## 2. 백업 파일
- `C:\OCR\ocr-server\backup\invoice_statement_20260512_before_T6g_expected_schema_row_grouping.py`
- `C:\OCR\ocr-server\backup\verify_invoice_table_rows_t6d_20260512_before_T6g.py`

## 3. 핵심 요약

**이번 작업의 초점**: T-6e-fix로 고정된 expectedColumns schema 위에서 row candidate 생성 로직과 summary/footer 제외 조건을 보정.

주요 변경:
1. **summary break 조건 완화** — body row가 충분히 쌓인 뒤(min_before_break ≥ min(3, required_count))에만 summary로 break
2. **`row_has_data` 조건 확장** — expiryDate+quantity, spec+quantity, lot+amount 조합 추가
3. **`expected_col_hit_count` 도입** — expected column 중 2개 이상 값이 있으면 row 후보로 우선 인정
4. **T-6e path + T-6 fallback path 모두 적용** — 동일한 개선을 두 경로에 일관되게 적용

---

## 4. row grouping 변경 내용

### 4.1 `_table_items_with_expected_columns` 내 summary break 완화

**변경 전**:
```python
if items and row_y >= page_h * 0.72:
    break
```

**변경 후**:
```python
min_before_break = min(3, len(required)) if required else 2
if items and len(items) >= min_before_break and row_y >= page_h * 0.65:
    break
```

- 최소 3개(required 수 부족하면 그 수) 이상의 body row가 쌓인 후에만 break 허용
- 65% 이후부터 summary로 종료 (기존 72%)
- 1.jpg처럼 긴 표에서 소계 행 직전 마지막 row가 잘리는 문제 완화

### 4.2 `row_has_data` 조건 확장 (두 경로 모두)

**기존 조건**:
- `has_code and (has_qty or has_price)`
- `has_qty and has_price`
- `has_ins and has_code`
- `has_lot and has_qty`

**추가된 조건 (T-6g)**:
- `expected_col_hit_count >= 2` — expected column 중 2개 이상 값 있음 (T-6e path의 주요 기준)
- `has_lot and has_price` — lotNo + 금액
- `has_exp and has_qty` — expiryDate/manufacturingNo + 수량
- `has_spec_val and (has_qty or has_price)` — spec + 수량/금액

### 4.3 `expected_col_hit_count` 도입

row 유효성 판단 전에 expected column key들의 값 보유 수를 카운트하여:
- 2개 이상이면 우선적으로 row 후보로 인정
- debug의 `rejectedRows`에 `expectedColumnHitCount` 필드 추가

---

## 5. summary/footer 제외 조건 변경

| 항목 | 변경 전 | 변경 후 |
|---|---|---|
| break threshold (y) | 72% of page_h | 65% of page_h |
| min body rows before break | 1 (items 존재) | min(3, required count) |
| 조기 summary (y < 65%) | skip | skip (동일) |
| 하단 summary (y ≥ 65%, rows ≥ min) | break | break (동일) |

---

## 6. 샘플별 rowCount 비교

| 샘플 | 실제 row 수 | T-6g 전 (synthetic) | T-6g 후 (synthetic) | 결과 | 비고 |
|---|---:|---:|---:|---|---|
| 1.jpg | 28 | 23 | 26 | ✗ (-2) | synthetic 한계; 실제 RunAll 27→28 개선 기대 |
| 2.pdf | 확인 필요 | 2 | 2 | 확인필요 | synthetic에서 T-6e 경로 미활성(헤더 없음) |
| 3.pdf | 확인 필요 | 2 | 2 | 확인필요 | 동일 |
| 4.pdf | 확인 필요 | 1 | 1 | 확인필요 | 동일 |
| 5.pdf | 6 | 6 | 6 | ✓ | 회귀 없음 |
| 6.pdf | 6 | 6 | 6 | ✓ | 회귀 없음 |
| 7.pdf | 1 | 1 | 1 | ✓ | 회귀 없음 |

---

## 7. rejectedRows 분석 (synthetic 기준)

| 샘플 | T-6g 전 rejected | T-6g 후 rejected | 주요 reason | 비고 |
|---|---:|---:|---|---|
| 1.jpg | 9 | 6 | header_or_contact:6 | no_item_name 3건 해소됨 |
| 2.pdf | 0 | 0 | — | T-6e 경로 미활성 |
| 5.pdf | 0 | 0 | — | — |
| 6.pdf | 0 | 0 | — | — |

1.jpg에서 `no_item_name` 3건 해소: `expected_col_hit_count >= 2` 조건이 실제 품목 row를 살린다.  
6건의 `header_or_contact` 거부는 garbled 합성 OCR의 한계 (실제 OCR에서는 Korean 품목명이 정상 처리됨).

---

## 8. 1.jpg rowCount 분석

**synthetic 모드 한계**:
- OCR cache는 plain text(좌표 없음) → make_synthetic_lines에서 각 line이 단일 token으로 처리됨
- 실제 OCR에서 header band의 모든 헤더(품목, 규격, 제조번호, 유효기간, 수량, 단가, 금액)가 같은 y-좌표에 존재 → 실제 RunAll에서 T-6e path 정상 활성화

**실제 RunAll에서 예상 개선**:
- summary break 65% 임계값 적용 → 소계 행 직전 마지막 row 살아날 가능성
- `expected_col_hit_count >= 2` → 경계 근처 row 구제
- 기존 27 → 28 달성 여부는 실제 RunAll 확인 필요

**지속되는 제한**:
- 6건의 `header_or_contact` 거부는 synthetic 좌표 아티팩트
- 실제 OCR에서 이 6건은 정상 Korean 품목명으로 통과될 것으로 예상

---

## 9. 2.pdf rowCount 분석

**synthetic 한계**:
- OCR cache에 2.pdf의 품목 헤더(품목코드, 품목명, 수량, 소비자단가, 공급금액, 보험No)가 없음
- T-6e expectedColumns 경로 미활성 → legacy_text_items fallback (rowCount=2)

**실제 RunAll에서 예상**:
- T-6f 연결로 manifest의 `tableExpectedColumns`가 backend에 전달됨
- 실제 이미지에서 landscape 방향 헤더 band 탐색 → T-6e 경로 활성화 예상
- T-6e 경로 활성화되면 expected 6개 컬럼 기준으로 row 추출
- `expected_col_hit_count >= 2` 조건이 itemCode+quantity, itemName+insuranceCode 등 조합 row를 살림

---

## 10. 샘플별 tableRows 앞 3개 (synthetic, 참고용)

**1.jpg (rowCount=26)**:
- row1: itemName=더모픽스크림 24001... qty=400 30g
- row2: itemName=하드칼씨플러스정 20270116... qty=100 30T
- row3: itemName=비타민C캡슐140 190,800... qty=6OT 40 30c

**5.pdf (rowCount=6)**: 6개 유지 ✓

**6.pdf (rowCount=6)**: 6개 유지, expiryDate 제외 expected 4개 감지 ✓

---

## 11. 검증 결과

- **py_compile**: ✓ PASS
- **verify script**: ✓ 실행 완료 (1.jpg 23→26, 5/6/7.pdf 회귀 없음)
- **typecheck**: ✓ PASS
- **build**: ✓ PASS

---

## 12. 남은 문제

1. **1.jpg rowCount 28 미달성** (synthetic 26, 실제 RunAll 27 수준): 
   - 6건의 header_or_contact 거부는 실제 OCR에서는 발생하지 않을 것으로 예상
   - summary break 개선이 28번째 row에 영향 주는지 실제 RunAll 확인 필요
   
2. **2.pdf rowCount 2 수준**: 
   - synthetic 모드에서는 검증 불가 (OCR cache에 헤더 없음)
   - T-6f로 연결된 실제 RunAll에서 T-6e 경로 활성화 여부 확인 필요

3. **실제 RunAll 미확인**: backend 재시작 후 Test UI RunAll로 실제 결과 확인 필요

---

## 13. 다음 작업 판단

**T-6g 구현 완료**: row grouping 보정 및 summary break 완화 구현됨.

실제 RunAll 후:
- **1.jpg rowCount 28 달성 + 2.pdf rowCount 개선** → **T-7 금액 계열 검토 가능**
- **1.jpg 27이나 2.pdf 개선** → 실질적 개선; T-7 일부 진행 가능
- **1.jpg 여전히 27, 2.pdf 여전히 2** → T-6g-fix 필요 (boundary 보정 또는 template bounds 연동)
- **5/6/7.pdf 회귀 발생** → 즉시 revert 후 원인 분석
