# R-2 invoice_statement 잔여 X/△ 개선 가능성 분석 리포트

작성일: 2026-05-11
직전 리포트: R-1 (R1_invoice_statement_lock_20260511.md)

---

## 1. 작업 목적

R-1에서 "조건부 잠금" 상태로 정리된 invoice_statement 1~7의 잔여 X/△를 더 세밀하게 분류한다.
목표는 인식률 강화가 아니라 다음 3가지 결정이다.

1. 지금 당장 안전하게 개선 가능한 것을 선별
2. 보류/보존해야 할 것(과적합 위험)을 확정
3. T-1(tableRows 정책) 진입 가능 여부를 확정

코드 수정: **없음**. 리포트 생성만.

---

## 2. 입력 기준

| 항목 | 값 |
|---|---|
| 기준 리포트 | R1_invoice_statement_lock_20260511.md |
| dataset | invoice_statement |
| sample count | 7 |
| Run All 여부 | 미실행 (R-1과 동일 — raw OCR text 기반) |
| 분석 기준 | GT vs OCR/NORM + GT_REF/GT_SIMILARITY (M-2f 기준) |
| 코드 수정 여부 | **없음** |

---

## 3. 현재 판정 기준 요약

| 상태 | 의미 |
|---|---|
| O | OCR/NORM이 normalizeDocumentCompare 후 GT와 직접 일치 |
| △ | GT_REF 자동채움 또는 GT_SIMILARITY/partial 보정으로 설명 가능 |
| X | OCR 미추출 / 핵심 불일치 / reference·partial 근거 부족 |
| — | GT 없음 |
| N/A | profile 상 평가 제외 |

---

## 4. 남은 X 전체 목록 (R-1 기준 + R-2 재분류 반영)

R-1은 주요 X를 3~4건으로 표기했으나, address 불확정 건을 포함하면 실제 X 후보는 총 6건이다.

| # | 파일 | 필드 | GT | OCR raw | 현재 상태 | 원인 |
|---|---|---|---|---|---|---|
| 1 | 3.pdf | supplierBizNumber | 572-81-01750 | "5 7 2- 8" + "1-01" 단편 | **X** | ocr_garbled (OCR 자체 분절) |
| 2 | 3.pdf | supplierRepresentative | 최정숙 | "성명최경" (다른 텍스트 혼입) | **X** | ocr_garbled + biz 미추출로 GT_REF 불가 |
| 3 | 3.pdf | supplierAddress | 경기도 안양시 만안구 만안로 17 203A호(안양동,명지캐럿 162) | "203A" 단편만 | **X** | address_fragment_only |
| 4 | 4.pdf | supplierAddress | 서울특별시 영등포구 당산로41길 11, 301호 302호(당산동4가, SK V1 센터) | "서울특법시…당산통4가" | **X** (conservative) | ocr_garbled. NORM 완전 보정 시 O 가능성 있으나 보수적 X 유지 |
| 5 | 4.pdf | buyerAddress | (17811) 경기도 평택시 청북읍 청북로 175(현곡리) | "(1781)경기도력시 창북 청175(현곡레)" | **X** ← R-1에서 △로 표기했으나 재분류 | address_core_mismatch (17811 vs 1781 핵심 우편번호 1자리 누락, "평택" vs "력시" 지역 완전 불일치) |
| 6 | 4.pdf | firstRowPreview | 클리마토플란정 | 클리마트플란정 | **X** | ocr_garbled 1자 차이, fuzzy 없으면 substring 불일치 |

### R-2 재분류 포인트

**4.pdf buyerAddress: △ → X로 재분류**

R-1은 4.pdf buyerAddress를 "△ (보수적)" 으로 표기했다. 그러나 정밀 분석 결과:
- `normalizeDocumentCompare(GT)` = "17811경기도평택시청북읍청북로175현곡리"
- `normalizeDocumentCompare(OCR)` = "1781경기도력시창북청175현곡레"
- `digitSignature` 체크: GT digits = {17811, 175}, OCR digits = {1781, 175} → 17811 ≠ 1781 → subset 불성립
- 핵심 지역명 "평택시" vs "력시" → text mismatch
- `documentMatchStatus` → **X** 확정
- NORM이 보정할 근거도 없음 (OCR 원문 자체 깨짐)
- 따라서 올바른 판정은 **X**

---

## 5. X 원인 분류 요약

| 원인 분류 | 건수 | 대표 예시 | 조치 |
|---|---:|---|---|
| D. OCR 품질 한계 (복구 불가) | 5 | 3.pdf supplier 3건 + 4.pdf buyer address | 현재 유지 — qualityTag 또는 supplier_weak로 설명 가능 |
| D+B. OCR 품질 한계 + NORM 의존 | 1 | 4.pdf supplierAddress | NORM 완전 보정 시 O 가능 (불확실) |
| E. table 작업 후보 (보류) | 1 | 4.pdf firstRowPreview | fuzzy match 도입 여부는 T-1 이후 검토 |

**X 6건 모두 parser/normalization 즉시 개선 대상이 아님.**
3.pdf supplier block은 OCR 원문에 값 자체가 없거나 충분하지 않음.
4.pdf는 qualityTag(ocr_garbled, party_block_garbled, address_garbled)가 이 실패를 예고함.

---

## 6. △ 전체 목록 (R-1 기준 + R-2 정밀도 보강)

| # | 파일 | 필드 | GT | OCR raw | △ 사유 | 적절성 | 향후 조치 |
|---|---|---|---|---|---|---|---|
| 1 | 1.jpg | supplierRepresentative | LEE WOO HYUN | LEE WOOHVON | gt_ref_autofill (biz 118-81-00450 exact) | **적절** | 잠금 |
| 2 | 2.pdf | supplierAddress | 07789 서울시 강서구 마곡중앙12로 3 오스템임플란트(주) | 07789서울시강서구마곡중앙12로3 | address_tail_missing (GT에 사명 포함, OCR 미포함) | **GT_REVIEW 필요** | 원문 확인 후 GT 수정 시 O 승격 |
| 3 | 2.pdf | buyerAddress | (08296)서울특별시 구로구 공원로 8길 24 (구로동, 백제빌딩) | (08296)서울록별시 구로구 공원로8길 24 (구로동,백제빌당) | OCR 오독 + NORM 보정 의존 ("록별시"→"특별시", "빌당"→"빌딩") | **적절** | NORM 보정 성공 시 O 승격. 잠금 유지 |
| 4 | 3.pdf | buyerAddress | 서울특별시 구로구 공원로8길 24 (구로동) | 서울특별시 구로구 공원로8길 24 | address_tail_missing "(구로동)" | **적절** | 잠금 |
| 5 | 4.pdf | supplierCompany | 주식회사 엘비아브노바 | 주식희사얼비아노바데표 | gt_ref_autofill (biz 117-81-53390 exact, party_garbled) | **적절** | 잠금 |
| 6 | 4.pdf | supplierRepresentative | 남이레 | 남이례 | gt_ref_autofill (biz exact, 1자 OCR 오독) | **적절** | 잠금 |
| 7 | 4.pdf | supplierAddress | 서울특별시 영등포구 당산로41길 11, 301호 302호(당산동4가, SK V1 센터) | 서울특법시영등포구당산로41길11,301302(당산통4가SKV1센터) | ocr_garbled, NORM 완전 보정 시 O 승격 가능 | **주의** — NORM 보정 성공 여부에 달림 | address_garbled qualityTag와 일치. NORM 결과 Run All 후 재평가 |
| 8 | 4.pdf | buyerCompany | 백제약품(주) 영등포지점 | 백계약통(주)영풍표지정 | gt_ref_autofill (biz 113-85-04425 exact) | **적절** | 잠금 |
| 9 | 5.pdf | buyerAddress | 서울특별시 구로구 공원로8길 24(구로동) | 서울특발시 쿠로구 공원로8길 24 (구로동) | OCR 오독 (특발→특별, 쿠로→구로) + NORM 보정 의존 | **적절** | GT-ADDR 수정(24 확정) 후 NORM 보정 시 O 승격 |

### R-2 재분류 포인트

**4.pdf buyerAddress (△ 목록에서 제거)**

위 X 목록(#5)으로 이동. 더 이상 △이 아닌 X로 확정.

**△ 총 건수 재조정**: R-1 기준 10건 → R-2 재분류 후 **9건** (4.pdf buyerAddress가 X로 이동)

---

## 7. △ 원인 분류 요약

| 원인 분류 | 건수 | 대표 예시 | 조치 |
|---|---:|---|---|
| GT_REF 자동보정 | 4 | 1.jpg supplierRep, 4.pdf supplier/buyer 회사·대표 | 잠금 유지 |
| address_tail_missing | 2 | 3.pdf buyerAddress, 2.pdf supplierAddress | 잠금 (2.pdf는 GT_REVIEW 병행) |
| OCR 오독 + NORM 보정 의존 | 3 | 2.pdf buyerAddress, 4.pdf supplierAddress, 5.pdf buyerAddress | NORM 결과에 따라 O 승격 가능. 잠금 유지 |

---

## 8. 지금 개선 가능한 후보

다음 조건을 모두 만족하는 경우만 "지금 개선 가능"으로 분류:
① OCR 원문에 근거 있음 ② parser/normalization 일반화 가능 ③ 과적합 위험 낮음 ④ GT 주입 없음 ⑤ 기존 기준 불흔들림 ⑥ 회귀 위험 낮음

| # | 후보 | 유형 | 기대 효과 | 회귀 위험 | 지금 진행 여부 | 이유 |
|---|---|---|---|---|---|---|
| 1 | 2.pdf supplierAddress GT 수정 (사명 제거) | GT 수정 | △ → O (직접 일치) | **낮음** | **권장** | OCR raw text에서 사명과 주소가 별도 라인 → GT 과캡처 의심. 수정 시 주소 기준 명확화 |
| 2 | (선택) Run All 실행 후 2.pdf buyerAddress / 5.pdf buyerAddress NORM 결과 확인 | 실행/검증 | △ → O 승격 자동 | **없음** | **권장** | NORM 보정이 실제로 동작하는지 확인하는 것은 비용 없는 검증 |

### 후보 1 상세: 2.pdf supplierAddress GT 수정

현재 GT: `"07789 서울시 강서구 마곡중앙12로 3 오스템임플란트(주)"`
제안 GT: `"07789 서울시 강서구 마곡중앙12로 3"`

근거:
- `ocr_cache.json` raw OCR text에서 `"07789서울시강서구마곡중앙12로3"` 과 `"오스템임플란트(주)02-2016-7000"` 이 별도 라인에 위치
- 회사명이 주소와 같은 라인에 인쇄된 것인지 원문 이미지 확인 필요 (2.pdf-SA 작업)
- 수정 후 효과: `normalizeDocumentCompare(GT)` = `normalizeDocumentCompare(OCR)` → O

검토 조건: 원문 이미지에서 주소 필드 영역을 직접 확인 후 수정 여부 결정.

---

## 9. 지금 보류해야 하는 후보

| # | 후보 | 유형 | 보류 이유 |
|---|---|---|---|
| 1 | 4.pdf firstRowPreview fuzzy match | normalization 개선 | 1자 차이 허용 시 타 필드/샘플 과적합 위험. 일반화 불확실 |
| 2 | 3.pdf supplierBizNumber fragment 조합 복원 | parser 개선 | OCR에 "572-8"+"1-01" 있으나 "750" 없음 → 완전 복원 불가. lookup/reference 단계 과제 |
| 3 | 3.pdf supplierRepresentative label 후처리 | parser 개선 | "성명최경" 자체가 GT "최정숙"과 다른 텍스트. OCR 인식 자체 실패. parser 개선으로 해결 불가 |
| 4 | 4.pdf buyerAddress NORM 보정 | normalization 개선 | "1781" vs "17811" 우편번호 자릿수 오류는 텍스트 정규화로 해결 불가. Template reference 단계 과제 |
| 5 | 주소 GT_REF 자동채움 부활 | 정책 변경 | M-2f로 주소 자동채움 제외 결정. 번지/지역 등 검증 없이 덮으면 오류 위험 |
| 6 | 4.pdf addresses qualityTag 수정 | manifest 수정 | address_garbled qualityTag는 현재 실패 상태를 적절히 설명. 제거하면 역효과 |

---

## 10. GT_REVIEW 후보

| # | 파일 | 필드 | 현재 GT | 의심 이유 | 확인 방법 | 우선순위 |
|---|---|---|---|---|---|---|
| 1 | 2.pdf | supplierAddress | 07789 서울시 강서구 마곡중앙12로 3 **오스템임플란트(주)** | OCR raw에서 사명과 주소가 별도 라인. 사명이 주소 필드에 들어가는 형식인지 불명확 | 원문 이미지 주소 블록 확인 | **높음** (2.pdf-SA) |

---

## 11. parser 개선 후보

| # | 파일 | 필드 | 현재 문제 | 개선 방향 | 난이도 | 즉시 진행? |
|---|---|---|---|---|---|---|
| 1 | 3.pdf | supplierBizNumber | "5 7 2- 8" + "1-01" fragments → 완전한 사업자번호 재조합 불가 | supplier 블록 OCR anchor 보강 (제목 라인 패턴 매칭) | 중 | **아니오** — 단독 샘플 최적화 위험 |
| 2 | 3.pdf | supplierRepresentative | "성명최경" ≠ GT "최정숙" → OCR 원문 자체 부정확 | supplier 대표자 label-value 추출 패턴 강화 | 중 | **아니오** — biz 추출 선행 필요 |
| 3 | 3.pdf | supplierAddress | "203A" 단편만 존재 | supplier 주소 블록 multi-line 조합 | 높음 | **아니오** — 한 파일 특화 위험 |
| 4 | 4.pdf | supplierAddress | "특법시"/"당산통" OCR 오독 | 일반 OCR 교정 사전 확장 (특법→특별 등) | 낮음 | **보류** — 일반화 가능하나 address_garbled qualityTag이므로 expected_failure |

---

## 12. normalization 개선 후보

| # | 대상 패턴 | 현재 처리 | 개선 방향 | 위험 | 즉시 진행? |
|---|---|---|---|---|---|
| 1 | "서울록별시" → "서울특별시" 등 1~2자 한국어 OCR 오독 | normalizeDocumentCompare (공백/구두점 제거만) | 일반 OCR 교정 사전 (invoice_statement.py NORM 단계) | 낮음 (일반화 가능) | **보류** — Run All 후 NORM 실제 동작 확인 선행 |
| 2 | "김승관(인)" → "김승관" (날인/서명 접미사 제거) | normalize 후 "(인)" 제거 안됨 | NORM 규칙에 "(인)" 접미사 제거 추가 | 매우 낮음 | **검토 가능** — 단, 2.pdf 1건만 확인된 케이스. 충분한 일반성 확보 후 진행 |
| 3 | "클리마트플란정" vs "클리마토플란정" (1자 OCR 오독) | X (substring 불일치) | fuzzy match (Levenshtein ≤ 1) | 높음 (과적합) | **아니오** |

---

## 13. debug 강화 후보

현재 invoice_statement.py의 `extractDebug.invoice_statement.normalization` 정보가 TestWorkspace.tsx에서 NORM row 표시에 활용된다.
아래는 debug 정보 강화 시 판정 원인 추적에 도움될 항목이다 (코드 수정 아닌 "향후 검토" 목적).

| # | 대상 | 현재 debug 정보 | 강화 방향 |
|---|---|---|---|
| 1 | 3.pdf supplier 블록 미추출 | (없음) | supplier block anchor 매칭 실패 이유 debug 로깅 |
| 2 | 4.pdf OCR 교정 경로 | (있으면 NORM row에 표시) | 교정 전/후 값, 교정 사전 적용 여부 명시 |
| 3 | address_tail 판정 | addressSimilarityAnalysis 있음 | tail 누락 이유(suffix vs 동별칭 등) 세분화 |

---

## 14. tableRows로 넘길 후보

현재 X/△ 중 tableRows 작업으로 해결해야 할 항목은 없다.
단, 아래 항목은 T-1(tableProfile별 정책) 설계 시 고려:

| # | 파일 | 항목 | T-1에서 다룰 내용 |
|---|---|---|---|
| 1 | 4.pdf | firstRowPreview X | single_item_table의 firstRowPreview 추출 신뢰도 정의 |
| 2 | 1.jpg | rowCount=28 검증 | multi_item_table의 rowCount 정확도 기준 정의 |
| 3 | 2.pdf | rowCount=13 검증 | item_quantity_table의 컬럼 구성 / rowCount 기준 |
| 4 | 6.pdf | lot_serial_quantity_table | lot/serial 중심 테이블의 컬럼 정책 |
| 5 | 7.pdf | serial_quantity_table | serial+수량 중심 테이블의 컬럼 정책 |

---

## 15. Template/RunOCR reference 단계로 넘길 후보

| # | 파일 | 필드 | 현재 상태 | Template 단계에서의 처리 방향 |
|---|---|---|---|---|
| 1 | 3.pdf | supplierBizNumber | X (OCR 미추출) | 사업자번호 reference DB lookup 또는 사용자 수동 확인 |
| 2 | 3.pdf | supplierRepresentative | X (OCR 미추출/오독) | biz 확보 후 GT_REF 자동채움 (company/representative) |
| 3 | 3.pdf | supplierAddress | X (203A 단편) | 사업자번호 확보 후 address reference suggest (자동채움 아닌 suggest) |
| 4 | 4.pdf | buyerAddress | X (1781 vs 17811) | 배송지 레이어 분리 — 빌링 주소와 배송지 주소 구분 설계 필요 |
| 5 | 4.pdf/7.pdf | buyerAddress 평택 | X/O 혼재 | 같은 buyer라도 문서별로 배송지가 다를 수 있음 (물류센터) — Template에서 party_side + location_type 분리 |

---

## 16. 파일별 판단

### 1.jpg
- 현재 상태: **잠금 가능**
- 남은 이슈: supplierRepresentative △ (GT_REF) — 적절
- 추가 개선 필요 여부: 없음
- tableRows 진입 영향: 없음

### 2.pdf
- 현재 상태: **GT_REVIEW 1건 처리 후 잠금 가능**
- 남은 이슈: supplierAddress △ (GT 사명 포함) → 원문 확인 후 GT 수정 시 O 승격. buyerAddress △ (NORM 의존).
- 추가 개선 필요 여부: 2.pdf-SA (supplierAddress GT 검토) 1건만
- tableRows 진입 영향: 없음 (party/amount 기준과 분리)

### 3.pdf
- 현재 상태: **잠금 가능** (X 3건 = supplier_weak qualityTag 정상 실패)
- 남은 이슈: supplier 블록 3건 X — OCR 원문 자체 불충분. parser 개선 여지 있으나 현 단계 범위 밖.
- 추가 개선 필요 여부: 없음 (T-1 이후 parser 보강 검토)
- tableRows 진입 영향: 없음

### 4.pdf
- 현재 상태: **품질 한계 잠금** (qualityTag = ocr_garbled, party_block_garbled, address_garbled)
- 남은 이슈: supplierAddress/buyerAddress X 재확정, firstRowPreview X 유지, GT_REF △ 4건 잠금
- 추가 개선 필요 여부: 없음. 4.pdf는 expected_failure 샘플.
- R-2 재분류: buyerAddress **△ → X** 확정
- tableRows 진입 영향: firstRowPreview X는 T-1에서 single_item_table 정책 수립 시 고려

### 5.pdf
- 현재 상태: **잠금 가능** (GT-ADDR 적용 후)
- 남은 이슈: buyerAddress △ (NORM 의존 — 특발/쿠로 오독). NORM 보정 시 O 승격.
- 추가 개선 필요 여부: Run All 후 buyerAddress O/△ 확인 권장
- tableRows 진입 영향: 없음

### 6.pdf
- 현재 상태: **잠금 가능**
- 남은 이슈: 없음 (buyer-only, no_amount_summary — 평가 대상 전부 O)
- 추가 개선 필요 여부: 없음
- tableRows 진입 영향: lot_serial_quantity_table 정책이 T-1에서 필요

### 7.pdf
- 현재 상태: **잠금 가능**
- 남은 이슈: buyerRepresentative — (GT 미입력, buyer_rep_optional)
- 추가 개선 필요 여부: 없음
- tableRows 진입 영향: serial_quantity_table 정책이 T-1에서 필요

---

## 17. 현재 상태가 최선인지 판단

| 질문 | 판단 |
|---|---|
| GT 추가 수정이 필요한가? | **1건** — 2.pdf supplierAddress (사명 포함 여부, 2.pdf-SA) |
| OCR 원문에 있는데 parser가 못 잡은 것이 많은가? | **아니오** — 3.pdf supplier 블록은 OCR 자체 불충분 |
| OCR 품질 한계로 parser 복구 어려운 케이스가 많은가? | **예** — 4.pdf (qualityTag ocr_garbled), 3.pdf supplier (supplier_weak). 이는 expected_failure |
| Test UI 판정 기준이 일관적인가? | **예** — M-2f로 computeFieldFinalStatus 단일 경로 확보 |
| tableRows 작업으로 넘어가도 party/address/amount 기준이 흔들리지 않는가? | **예** — 세 카테고리 기준 안정화됨 |
| Template/RunOCR reference 설계로 넘겨야 할 항목이 있는가? | **예** — 3.pdf supplier biz/rep/addr, 4.pdf buyerAddress 배송지 분리 |

---

## 18. 표 작업 진입 가능성

| 질문 | 판단 |
|---|---|
| party/address/amount가 tableRows 전 충분히 안정적인가? | **예** |
| 남은 X/△이 tableRows 작업을 막을 정도인가? | **아니오** — 모두 party/address/amount 영역이며 table과 무관 |
| R-1을 tableRows 회귀 기준으로 쓸 수 있는가? | **예** — party/amount 판정은 R-1 기준선으로 잠금 |
| tableRows 작업 전 반드시 해결해야 할 X가 있는가? | **없음** |
| 먼저 해야 할 것: 컬럼 정책 vs parser 개선 vs Template 연동? | **컬럼 정책(T-1)이 우선** — parser/Template 연동보다 선행 필요 |

**결론: 바로 T-1 진입 가능**

단, 2.pdf-SA (supplierAddress GT 수정)는 T-1과 병행하여 처리 가능.

---

## 19. 최종 결론

### 잠금 유지 가능 여부
**조건부 잠금 유지**. R-2 재분류 반영:
- 4.pdf buyerAddress: △ → **X** 로 재확정 (R-1 추정에서 보수적 X가 정확했음)
- 전체 X: 3건 → **6건** (4.pdf supplierAddress/buyerAddress 추가)
- 전체 △: 10건 → **9건** (4.pdf buyerAddress X 이동)

재계산된 직접 일치율: 70 / (70+9+6) = 70/85 ≈ **82.4%**
커버리지: 79/85 ≈ **92.9%**

단, X 추가 3건은 전부 **qualityTag로 예고된 expected_failure** (ocr_garbled, address_garbled).
이 수치는 4.pdf가 "의도적으로 어려운 샘플"임을 감안하면 정상 범위.

### 추가 인식률 개선을 할지
**아니오**. 현 단계에서 추가 개선 시도 없음.
인식률 개선은 다음 단계(parser 보강, NORM 교정 사전)에서 일반화 가능한 규칙으로만 수행.

### 바로 T-1로 갈지
**예**. T-1 진입 가능. 병행으로 2.pdf-SA 검토 가능.

### 추천 다음 작업

**주 작업: T-1 — tableProfile별 tableRows 컬럼 정책 정리**

**병행 작업: 2.pdf-SA — supplierAddress GT 원문 확인 (사명 포함 여부)**

---

## 20. 검증 결과

| 검증 | 결과 |
|---|---|
| manifest.json parse | ✅ ok |
| ground_truth.json parse | ✅ ok |
| party_master.json parse | ✅ ok |
| typecheck (`npm.cmd run typecheck`) | ✅ pass (에러 0) |
| build | 생략 (코드 수정 없음) |
| 코드 수정 여부 | **없음** |

---

## Appendix A. R-1 vs R-2 판정 차이 요약

| 파일 | 필드 | R-1 판정 | R-2 판정 | 변경 이유 |
|---|---|---|---|---|
| 4.pdf | buyerAddress | △ (보수적) | **X** | digitSignature 분석: 17811 ≠ 1781 핵심 불일치. NORM 보정 불가. |

## Appendix B. X 총 건수 정오표

| 구분 | 건수 | 내역 |
|---|---:|---|
| R-1 주요 X (명시) | 4 | 3.pdf biz/rep/addr + 4.pdf firstRowPreview |
| R-1 불확정 X (△/X 경계) | 2 | 4.pdf supplierAddress, 4.pdf buyerAddress |
| R-2 재분류 후 확정 X | **6** | 위 6건 전부 X 확정 |
| 중 expected_failure (qualityTag) | 3 | 4.pdf 3건 (ocr_garbled 예고) |
| 중 supplier_weak | 3 | 3.pdf 3건 |

## Appendix C. △ 총 건수 정오표

| 구분 | 건수 | 내역 |
|---|---:|---|
| R-1 △ | 10 | party 8건 + table 1건 (R-1 집계 9건이었으나 4.pdf buyerAddress 포함 시 10건) |
| R-2 재분류 후 △ | **9** | 4.pdf buyerAddress가 X로 이동 |
| 중 GT_REF 자동보정 | 4 | biz exact 기반 |
| 중 address 관련 | 3 | tail missing / NORM 의존 |
| 중 NORM 보정 의존 | 2 | 2.pdf buyerAddress, 5.pdf buyerAddress |
