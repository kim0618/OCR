# T-6j-check 실제 Template colGuides 기반 RunOCR 검증

## 1. 검증 목적
- 실제 RunOCR/Template payload의 `regions[].table.colX`가 backend에서 `tableBounds + columnGuides`로 변환되는지 확인
- 목표 경로: `extractionSource=template_colguides_expected_columns`
- 우선 샘플: `5.pdf`
- 추가 샘플: `2.pdf`

## 2. 사용 데이터와 한계
- 확인한 저장 템플릿: `ocr-server/data/templates.json`
- 저장된 table colGuides 템플릿은 `1.jpg`용 1개만 존재함
- `5.pdf`, `2.pdf`용으로 실제 저장된 Template annotation은 없음
- 따라서 이번 검증은 RunOCR가 보내는 것과 같은 `regions` JSON 형태를 구성해 API 호출함
- 원시 결과:
  - `T6j_check_template_colguides_runocr_20260512.raw.json`
  - `T6j_check_template_colguides_direct_control_20260512.raw.json`

## 3. 실제 RunOCR형 regions payload 검증

### 5.pdf
- payload: `regions`에 `fieldType="table"` + `table.colX=[331,610,854,1132]`
- 기대 변환: `region.table.colX` → OCR space `column_guides`
- 결과: HTTP 500
- 실패 지점: colGuides extractor 진입 전
- 서버 오류: `UnboundLocalError: cannot access local variable 'doc_type' where it is not associated with a value`

### 2.pdf
- payload: `regions`에 `fieldType="table"` + `table.colX=[120,330,610,820,975,1132,1324]`
- 기대 변환: `region.table.colX` → OCR space `column_guides`
- 결과: HTTP 500
- 실패 지점: colGuides extractor 진입 전
- 서버 오류: `UnboundLocalError: cannot access local variable 'doc_type' where it is not associated with a value`

## 4. RunOCR 경로 판정
| 샘플 | tableBoundsUsed | columnGuidesReceived | columnGuidesUsed | extractionSource | rowCount | 판정 |
|---|---|---|---|---|---:|---|
| 5.pdf | 확인 불가 | 확인 불가 | 확인 불가 | 확인 불가 | - | API 500 |
| 2.pdf | 확인 불가 | 확인 불가 | 확인 불가 | 확인 불가 | - | API 500 |

결론: 현재 실제 Template/RunOCR `regions` 경로는 `doc_type` 미정의 오류로 인해 T-6j extractor까지 도달하지 못함.

## 5. direct-control 검증
RunOCR 연결 문제와 extractor 문제를 분리하기 위해, 같은 서버에 `regions` 없이 `tableBounds + columnGuides + tableExpectedColumns`를 직접 Form field로 주입했다.

| 샘플 | HTTP | tableBoundsUsed | extractionSource | rowCount | valueColumnKeys | missingExpectedColumnKeys |
|---|---:|---|---|---:|---|---|
| 5.pdf | 200 | true | template_colguides_expected_columns | 4 | rowIndex, itemCode, itemName, expiryDate, quantity, unitPrice, amount | 없음 |
| 2.pdf | 200 | true | template_colguides_expected_columns | 1 | rowIndex, itemCode, supplyAmount, insuranceCode | itemName, quantity, consumerUnitPrice, supplyUnitPrice |

### direct-control 해석
- T-6j extractor 경로 자체는 동작함
- `5.pdf`는 `itemCode`, `unitPrice`, `amount`가 direct-control에서 값 있는 컬럼으로 잡힘
- 다만 임의/근사 guide라 rowCount는 목표 6이 아니라 4
- `2.pdf`는 기존 rowCount 2보다 direct-control rowCount가 1로 줄어 개선 없음
- `2.pdf`는 `supplyAmount`, `insuranceCode` 일부가 잡히지만 `consumerUnitPrice`, `supplyUnitPrice`는 비어 있음

## 6. 요청 확인값 상태
| 확인값 | 실제 RunOCR형 regions | direct-control |
|---|---|---|
| tableBoundsUsed=true | 500으로 확인 불가 | 5.pdf/2.pdf true |
| columnGuidesReceived=true | 500으로 확인 불가 | 응답 tableMeta/tableDebug에 노출 안 됨 |
| columnGuidesUsed=true | 500으로 확인 불가 | 응답 tableMeta/tableDebug에 노출 안 됨 |
| extractionSource=template_colguides_expected_columns | 500으로 확인 불가 | 5.pdf/2.pdf 확인 |
| rowCount | 500으로 확인 불가 | 5.pdf=4, 2.pdf=1 |
| expected columns | manifest 기준 전달 | direct-control tableMeta에 반영 |
| valueColumnKeys | 500으로 확인 불가 | direct-control에서 확인 |
| missingExpectedColumnKeys | 500으로 확인 불가 | direct-control에서 확인 |
| tableRows preview | 500으로 확인 불가 | raw json에 첫 3개 저장 |

## 7. 5.pdf 상세
- expected columns: `itemName`, `itemCode`, `quantity`, `unitPrice`, `amount`
- 목표 rowCount: 6
- 실제 RunOCR형 regions: 500으로 결과 없음
- direct-control rowCount: 4
- direct-control 개선:
  - `itemCode`: 값 있음
  - `unitPrice`: 값 있음
  - `amount`: 값 있음
- direct-control 한계:
  - rowCount가 6에 못 미침
  - table guide가 실제 Template 저장 좌표가 아니라 근사 좌표라 row capture가 불완전함

## 8. 2.pdf 상세
- expected columns: `rowIndex`, `itemCode`, `itemName`, `quantity`, `consumerUnitPrice`, `supplyUnitPrice`, `supplyAmount`, `insuranceCode`
- 기존 rowCount: 2
- 실제 RunOCR형 regions: 500으로 결과 없음
- direct-control rowCount: 1
- direct-control 값 있음:
  - `rowIndex`
  - `itemCode`
  - `supplyAmount`
  - `insuranceCode`
- direct-control 값 없음:
  - `itemName`
  - `quantity`
  - `consumerUnitPrice`
  - `supplyUnitPrice`
- 판정: 2.pdf는 colGuides만으로 즉시 개선되지는 않음. table bounds/guide 정확도와 row grouping 보강이 추가로 필요함.

## 9. 발견 이슈
1. **RunOCR regions 경로 500**
   - `regions`가 있으면 현재 코드 흐름에서 `doc_type`이 세팅되지 않은 상태로 후속 분기에 진입한다.
   - 이 때문에 `invoice_statement` extractor 호출 전 실패한다.

2. **columnGuides 디버그 노출 부족**
   - direct-control에서 `extractionSource=template_colguides_expected_columns`는 확인됨.
   - 하지만 응답 `tableMeta`/`tableDebug`에는 `columnGuidesReceived`, `columnGuidesUsed`, `columnGuidesCount`가 노출되지 않음.
   - 현재는 `extractionSource`로 colGuides 사용을 간접 확인해야 한다.

3. **5.pdf/2.pdf 저장 Template 부재**
   - 실제 UI에서 저장된 5.pdf/2.pdf table annotation이 없어 좌표 정확도 검증은 제한적이다.

## 10. 최종 결론
- 현재 상태: T-6j extractor direct path는 동작하지만, 실제 RunOCR `regions` path는 500으로 실패
- 가장 큰 병목: RunOCR template-region 분기에서 `doc_type` 미정의
- 다음 작업명 제안: `T-6j-fix-runocr-template-doc-type`
- 수정 대상 예상 파일:
  - `ocr-server/main.py`
  - 필요 시 `extractors/invoice_statement.py`의 tableDebug 노출 필드
- 후속 검증:
  - 5.pdf/2.pdf 실제 Template 저장
  - RunOCR에서 저장 템플릿 선택 후 재실행
  - `tableBoundsUsed`, `columnGuidesReceived`, `columnGuidesUsed`, `extractionSource`, rowCount/value mapping 재확인
