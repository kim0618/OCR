# CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_SPEED_PRECHECK

- 사용 도구: Codex
- 사용 모델: Codex
- 운영 코드 수정: 없음
- repo dirty before work: True
- API URL: `http://127.0.0.1:9099/ocr/extract`
- 스크립트: `D:\Free_Vue\OCR\tmp\codex_receipt_unstructured_template_speed_precheck.py`
- 템플릿: 영수증 / `TPL-003`
- 제외 파일: 9.jpg

## 대상 파일
1.jpg, 2.jpg, 3.jpg, 4.jpg, 7.jpg, 8.jpg, 10.jpg, a1.jpg, a2.jpg

## Baseline 속도 / 인식률

| file | doc_type | processing | wall | raw KB | slim KB | fillRate | biz | total | status |
|---|---|---:|---:|---:|---:|---:|:---:|:---:|---|
| 1.jpg | receipt_card | 24.52 | 24.563 | 660.0 | 3.7 | 1.0 | True | True | PASS |
| 2.jpg | receipt_card | 32.61 | 32.636 | 655.9 | 4.3 | 1.0 | True | True | PASS |
| 3.jpg | receipt_card | 27.82 | 27.877 | 650.2 | 3.2 | 1.0 | True | True | PASS |
| 4.jpg | receipt_card | 20.67 | 20.713 | 709.5 | 3.6 | 1.0 | True | True | PASS |
| 7.jpg | receipt_card | 16.51 | 16.568 | 719.4 | 4.1 | 1.0 | True | True | PASS |
| 8.jpg | medical_receipt | 20.12 | 20.177 | 753.7 | 3.9 | 1.0 | True | True | PASS |
| 10.jpg | receipt_card | 16.48 | 16.506 | 726.0 | 4.9 | 1.0 | True | True | PASS |
| a1.jpg | receipt_pos | 20.84 | 20.894 | 953.3 | 4.5 | 0.5 | True | True | PASS |
| a2.jpg | form_or_handwritten | 27.14 | 27.195 | 924.6 | 4.5 | 0.8333 | True | False | WARN |

## 느린 파일 TOP
- 2.jpg: processing=32.61s, wall=32.636s, fillRate=1.0, doc=receipt_card
- 3.jpg: processing=27.82s, wall=27.877s, fillRate=1.0, doc=receipt_card
- a2.jpg: processing=27.14s, wall=27.195s, fillRate=0.8333, doc=form_or_handwritten
- 1.jpg: processing=24.52s, wall=24.563s, fillRate=1.0, doc=receipt_card
- a1.jpg: processing=20.84s, wall=20.894s, fillRate=0.5, doc=receipt_pos

## 주요 필드 결과
### 1.jpg
- 회사명: (주)안전볼트
- 사업자번호: 138-81-68468
- 대표자: 윤봉상
- tel: 031-479-0485
- 주소: 경기 안양시 동안구 호계동 555-9 국
- 총합계금액: 10,560
### 2.jpg
- 회사명: 화성툴
- 사업자번호: 138-08-99333
- 대표자: 이태주
- tel: 031-479-0090
- 주소: 경기 안양시 동안구 엘에스로 92 8동140호
- 총합계금액: 11,000
### 3.jpg
- 회사명: 세광전기조명
- 사업자번호: 119-10-88385
- 대표자: 이정은
- tel: 031-479-2280
- 주소: 경기 안양시 동안구 엘에스로 76 (호계동)7-117.11
- 총합계금액: 33,000
### 4.jpg
- 회사명: 가행점
- 사업자번호: 123-23-94265
- 대표자: 정영달
- tel: 031-479-3690
- 주소: 경기 안양시 동안구 엘에스로 92
- 총합계금액: 17,600
### 7.jpg
- 회사명: 서울집
- 사업자번호: 581-10-00658
- 대표자: 신미남
- tel: 031-388-1080
- 주소: 경기도 의왕시 경수대로 209 102호(고천동,의왕월드 비전)
- 총합계금액: 35,000
### 8.jpg
- 회사명: 효성온누리약국
- 사업자번호: 134-04-13602
- 대표자: 최성환
- tel: 031-455-9955
- 주소: 경기 의왕시 경수대로237
- 총합계금액: 11,000
### 10.jpg
- 회사명: 토탈철물
- 사업자번호: 761-21-00890
- 대표자: 전용민
- tel: 010-9388-9936
- 주소: 경기 의왕시 효행로 47 (오전동)1층
- 총합계금액: 19,250
### a1.jpg
- 회사명: 기계공구
- 사업자번호: 123-23-94265
- 대표자: 
- tel: 
- 주소: 
- 총합계금액: 110,000
### a2.jpg
- 회사명: 세광전기조명
- 사업자번호: 119-10-88385
- 대표자: 이정
- tel: 031-479-2280
- 주소: 경기도 안양시 동안구 엘에스로 76,7-117, (호계동, 국제유통단지)
- 총합계금액: 

## 병목 / OCR 호출 구조
- runOcrPayload: UploadWorkspace uses activeTemplate.mode === 'unstructured' to avoid sending regions; it sends file, template_id, model_id, and optional documentType only.
- backendRoute: ocr-server/main.py /ocr/extract loads template metadata, but because TPL-003 has no regions/template_json regions, region_list stays empty and the non-template full OCR path runs.
- ocrCalls: Unstructured receipt path performs detect_document, detect_orientation OCR/classification, one full OCR on resized/preprocessed ocr_img, then conditional upper/amount/handwritten re-OCR crops.
- preprocessing: Path deskews for preview, resizes OCR input to width 950 unless already between 760 and 950, then applies CLAHE and unsharp mask.
- responsePayload: Default unstructured response includes processed_image, original_image, full_text, fields, receipt_fields, extract_debug with timings, and doc_type.
- fieldCrop: The unstructured '영수증' template does not send region_list, so template field crop OCR is not used. Output fields are frontend mapping from receipt_fields.
- autofill: Backend API does not run frontend autofill. UploadWorkspace may run frontend autofill suggestions after API response; this script measures API/OCR only.
- futureInfoTablesCompatibility: The measured bottlenecks are OCR/preprocessing/conditional re-OCR and response size; they do not depend on current outputFields/no_1~no_6 UI naming.

## 응답 크기
- 평균 raw response: 768282 bytes
- 평균 slim response: 4161 bytes
- 평균 Clean JSON estimate: 499 bytes
- response slim은 OCR processing_time 자체보다는 전송/렌더링/Raw JSON 표시 비용에 유효.

## 최적화 후보
### P1 OCR cache for repeated RunOCR
- 추천: PASS
- 예상 효과: Large on repeated runs: cache hit can skip full OCR and conditional re-OCR for identical file/template/options.
- 정확도 위험: Low if cache key includes file hash, template id, OCR model version, preprocessing options, debug/autoApply flags.
- 향후 info/tables 호환성: Compatible; cache stores OCR/parser result independent of outputFields/info/tables UI.
- 검증 방법: Repeat same 9-file set twice; require identical receipt_fields, doc_type, fillRate.
### P2 Response slim / omit images and debug by default
- 추천: PASS
- 예상 효과: UI/transfer/render improvement; average removable payload about 764121 bytes per response. Does not materially reduce OCR processing_time.
- 정확도 위험: Low for OCR values if debug/images remain opt-in.
- 향후 info/tables 호환성: Compatible; Clean JSON info/tables can be generated from structured fields without base64/debug.
- 검증 방법: Verify Preview image/history features with explicit includeImages/includeDebug option.
### P3 Conditional re-OCR gating review
- 추천: WARN
- 예상 효과: Potential when upper/amount re-OCR runs; current avg upper=5.70s, amount=0.58s. Optimize only if field recall is unchanged.
- 정확도 위험: Medium; upper re-OCR can recover company/business/phone/address and amount re-OCR can recover totals.
- 향후 info/tables 호환성: Compatible if gating is based on semantic field confidence, not outputFields labels.
- 검증 방법: A/B with GT: no loss of company, businessNo, phone, address, totalAmount; fillRate must not decrease.
### P4 OCR input downscale below current 950px width
- 추천: FAIL for default optimization
- 예상 효과: May reduce full OCR time (avg full OCR 8.37s), but current path already resizes to 950px and comments note 850px caused receipt regressions.
- 정확도 위험: High for small receipt digits, business numbers, total amount.
- 향후 info/tables 호환성: Technically compatible but accuracy risk affects info/tables extraction.
- 검증 방법: Only revisit with tmp A/B at 900/850/800 and full GT comparison.
### P5 Parser regex/post-processing micro-optimization
- 추천: WARN/low priority
- 예상 효과: Small; field_extract/pre_extract/classify timings are usually much smaller than OCR.
- 정확도 위험: Medium if regex behavior changes.
- 향후 info/tables 호환성: Compatible but not the main bottleneck.
- 검증 방법: Profile CPU-only parser on saved OCR lines before code changes.
### P99 no_1~no_6/outputFields-specific shortcut
- 추천: FAIL/exclude
- 예상 효과: Not evaluated.
- 정확도 위험: High coupling to current UI.
- 향후 info/tables 호환성: Conflicts with future info/tables structure.
- 검증 방법: Do not pursue.

## 운영 반영 추천 순서
- 1. Add/validate OCR cache for repeated identical file+template+options runs.
- 2. Add opt-in images/debug and slim default response if UI/history can request images separately.
- 3. Investigate conditional re-OCR gating only with GT A/B; do not skip upper/amount re-OCR by default yet.
- 4. Do not globally downscale below current 950px without separate GT PASS evidence.

## 운영 반영 전 추가 검증
- Run the same target set twice for cache validation; receipt_fields/doc_type/fillRate must be identical.
- For response slim, verify Preview image, History detail, Raw JSON/debug toggles explicitly.
- For any re-OCR gating change, require per-file GT comparison for company/businessNo/phone/address/totalAmount and no fillRate decrease.
- Keep all candidates independent of outputFields/no_1~no_6 and compatible with future info/tables Clean JSON.
