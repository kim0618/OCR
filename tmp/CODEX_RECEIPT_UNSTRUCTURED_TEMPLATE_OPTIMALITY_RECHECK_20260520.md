# CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_OPTIMALITY_RECHECK

- 사용 도구: Codex
- 사용 모델: Codex
- 운영 코드 수정: 없음
- repo dirty before work: True
- API URL: `http://127.0.0.1:9099/ocr/extract`
- 스크립트: `D:\Free_Vue\OCR\tmp\codex_receipt_unstructured_template_optimality_recheck.py`
- 템플릿: 영수증 / `TPL-003`
- 제외 파일: 9.jpg

## Baseline 재확인
- round1 avg processing/wall/fillRate: 22.772s / 22.826s / 0.9259
- round2 avg processing/wall/fillRate: 25.233s / 25.285s / 0.9259

| file | processing | fillRate | fullOCR ms | reOCR ms | share | recoveredByReOCR | canSkip |
|---|---:|---:|---:|---:|---:|---|---|
| 1.jpg | 24.12 | 1.0 | 7948.2 | 6377.9 | 26.44% | 회사명:upper_block, 사업자번호:upper_block, 대표자:upper_block, tel:upper_block, 주소:upper_block, 총합계금액:amount_block | no |
| 2.jpg | 29.9 | 1.0 | 9664.1 | 5812.6 | 19.44% | 회사명:upper_block, 사업자번호:upper_block, 대표자:upper_block, tel:upper_block, 주소:upper_block | no |
| 3.jpg | 28.94 | 1.0 | 10020.6 | 5041.1 | 17.42% | 회사명:upper_block, 사업자번호:upper_block, tel:upper_block, 주소:upper_block | no |
| 4.jpg | 21.93 | 1.0 | 8197.5 | 4183.0 | 19.07% | 사업자번호:upper_block, 대표자:upper_block, tel:upper_block, 주소:upper_block | no |
| 7.jpg | 15.95 | 1.0 | 8383.1 | 6271.8 | 39.32% | 회사명:upper_block, 사업자번호:upper_block, tel:upper_block | no |
| 8.jpg | 19.88 | 1.0 | 8046.4 | 9454.7 | 47.56% | 회사명:upper_block, 사업자번호:upper_block, 대표자:upper_block, tel:upper_block, 주소:upper_block, 총합계금액:amount_block | no |
| 10.jpg | 16.49 | 1.0 | 8172.5 | 6458.9 | 39.17% | 회사명:upper_block, 사업자번호:upper_block, 대표자:upper_block, tel:upper_block, 주소:upper_block | no |
| a1.jpg | 22.75 | 0.5 | 8877.3 | 5800.2 | 25.5% | 사업자번호:upper_block | no |
| a2.jpg | 24.99 | 0.8333 | 7813.0 | 7079.5 | 28.33% | 회사명:upper_block, 사업자번호:upper_block | no |

## OCR Cache 안정성
- verdict: PASS
- stableProjection same: 9/9
- cache key: fileSha256, templateId, template updatedAt or template hash, OCR model/version/language config, preprocessing options: debugPreprocessing, autoApplyPreprocessing, qualityTagsJson, documentType hint, backend code/version for OCR/parser policy

## Response Slim
- raw/noImages/noImagesNoDebug/CleanJSON avg bytes: 768281 / 14561 / 4755 / 499
- serialization raw/slim avg ms: 2.702 / 0.038
- verdict: PASS for UI/transport optimization, not a core OCR processing_time optimization.

## Re-OCR Gating
- verdict: WARN
- upper ran files: 1.jpg, 2.jpg, 3.jpg, 4.jpg, 7.jpg, 8.jpg, 10.jpg, a1.jpg, a2.jpg
- amount ran files: 1.jpg, 8.jpg
- upper re-OCR ran for all measured files; current response-only data cannot prove it can be removed without A/B disabling it.
- field_sources show upper_block contributions for some top fields, so unconditional skip risks company/business/phone/address recall.
- a1/a2 are lower-fill/edge samples; gating should remain conservative there.
- amount re-OCR ran only on selected files, but totalAmount recovery is a critical field; skip only when full/pre extract has strong total.

## Downscale
- verdict: FAIL for default optimization
- OCR image width is capped/upscaled to 950px with min 760px.
- main.py comment says 850px caused regression on small receipt digits/separators, so 950px was restored.

## 최종 후보 순위
| rank | candidate | verdict | single | repeat | risk |
|---:|---|---|---|---|---|
| 1 | OCR cache | PASS | None on first run. | Very high. | Low with complete key/invalidation. |
| 2 | Response slim / opt-in images+debug | PASS | Moderate for wall/UI after OCR; low for backend processing_time. | Moderate storage/network benefit. | Low if preview/history can request images/debug explicitly. |
| 3 | Conservative semantic upper/amount re-OCR gating | WARN | Potentially high, but not yet safe. | Also helps uncached runs. | Medium/high until A/B proves no loss of company/businessNo/phone/address/total. |
| 4 | Parser regex micro-optimization | WARN low priority | Low. | Low. | Medium because parser changes can alter values. |
| 5 | Downscale below current 950px | FAIL for default | Possible but unsafe. | Possible but unsafe. | High: existing code comment records 850px receipt digit/separator regression. |
| 99 | outputFields/no_1~no_6 shortcut | FAIL/excluded | Irrelevant. | Irrelevant. | Conflicts with future info/tables and task constraints. |

## 결론
- 지금 할 수 있는 최선 여부: True
- 가장 안전한 후보: OCR cache, followed by response slim
- 단일 실행 후보: Conservative semantic re-OCR gating, but still WARN and requires A/B before recommendation
- 반복 실행 후보: OCR cache
- 지금 추천: OCR cache dry-run/implementation, response slim with opt-in images/debug
- 지금 비추천: unconditional re-OCR skip, below-950 downscale, outputFields/no_1~no_6 shortcuts

## 운영 반영 전 추가 검증
- For cache: implement lookup dry-run and confirm stableProjection equality on target set.
- For response slim: verify Preview image, History detail, Raw JSON/debug with explicit include flags.
- For re-OCR gating: run A/B disabling only under proposed safe conditions and require zero loss on semantic fields/fillRate.
- Do not pursue below-950 downscale unless 900/850/800 tmp experiment passes all required fields.
