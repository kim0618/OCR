# T-19raw OCR raw line bbox/confidence snapshot export 결과

## 1. 수정 파일
- `ocr-server/utils/ocr_snapshot.py` (신규) — normalize helper
- `ocr-server/scripts/export_ocr_raw_lines_snapshot_t19raw.py` (신규) — export script

## 2. 백업 파일
- 코드 수정 없음 (신규 파일만 추가)

## 3. 핵심 요약
- 처리 샘플: 57개
- 총 OCR 라인 (synthetic): 2196개
- bbox 실제 보존: 0/57 (cache-only 모드, live OCR 필요)
- confidence 실제 보존: 0/57 (cache-only 모드)
- T-18 failure 연결 분석: 20건

## 4. raw line normalize 구조
| field | 설명 |
|---|---|
| page | PDF 페이지 번호 (이미지=1) |
| lineIndex | 라인 인덱스 (0부터) |
| text | OCR 텍스트 |
| confidence | OCR 신뢰도 (0~1), cache-only 시 null |
| pts | 4점 다각형 [[x,y]×4], cache-only 시 null |
| bbox | {x,y,width,height,source}, synthetic or paddleocr |
| center | {x,y} 중심점 |
| yRatio | 문서 내 세로 위치 비율 (0=상단, 1=하단) |
| synthetic | true=추정값, false=실제 OCR |
| category | 라인 카테고리 (text_candidate/amount_like/biz_number/phone/address/date/noise_label/other) |

## 5. snapshot 생성 결과
| 항목 | 결과 |
|---|---:|
| total samples | 57 |
| bbox available (real) | 0/57 |
| confidence available (real) | 0/57 |
| total synthetic raw lines | 2196 |

### failure reason 분포
| reason | count | 설명 |
|---|---:|---|
| ok | 30 | 정상 추출 |
| classification_mismatch | 9 | doc_type 오분류 |
| suppressed_policy | 7 | suppressed 정책 (정상) |
| parser_missed_source_exists | 4 | OCR 원문 있으나 parser 미추출 |
| ocr_source_garbled | 3 | OCR 원문 손상/garbled |
| ocr_source_missing | 2 | OCR 원문 없음 |
| metadata_mismatch | 1 | manifest 오기입 |
| ambiguous_candidates | 1 | 후보 모호성 |

## 6. 실패 샘플 연결 결과
| sample | reason | rawLineCount | merchant 후보 | biz 후보 | 활용 가능성 |
|---|---|---:|---|---|---|
| baseline/8.jpg | classification_mismatch | 29 | Q팔페이, www.phampay.cakr | - | doc_type 오분류 → position 기반 signal 가중치 개선 후보 (T-19c |
| baseline/a1.jpg | classification_mismatch | 35 | .C Cashnote Pay, 세 표 | 123-23-94265 | doc_type 오분류 → position 기반 signal 가중치 개선 후보 (T-19c |
| google/5.jpg | classification_mismatch | 36 | 석춘, *정부방침에 의해,교환/환 | - | doc_type 오분류 → position 기반 signal 가중치 개선 후보 (T-19c |
| google/8.jpg | classification_mismatch | 30 | 단가 수량 금액, 상품명 | - | doc_type 오분류 → position 기반 signal 가중치 개선 후보 (T-19c |
| google/9.jpg | classification_mismatch | 52 | www.phampayoakr, 대표자/전 | 사업자/단말:508-17-32861 | doc_type 오분류 → position 기반 signal 가중치 개선 후보 (T-19c |
| google_fast/5.jpg | classification_mismatch | 36 | 석춘, *정부방침에 의해,교환/환 | - | doc_type 오분류 → position 기반 signal 가중치 개선 후보 (T-19c |
| receipt_generalization/card_001.jpg | ocr_source_garbled | 27 | 키스-제크, 김영성명/주소가 실제와다출경무 | 79161161/140-09-20255 | OCR source 손상 → bbox 기반 재처리 또는 preprocessing 개선 후  |
| receipt_generalization/card_002.jpg | ocr_source_garbled | 25 | IO, 전화번오 | 306-13-63556 | OCR source 손상 → bbox 기반 재처리 또는 preprocessing 개선 후  |
| receipt_generalization/food_001.jpg | classification_mismatch | 14 | 티어터 | - | doc_type 오분류 → position 기반 signal 가중치 개선 후보 (T-19c |
| receipt_generalization/food_002.jpg | parser_missed_source_exists | 21 | 품명, '*’표시는 | - | 상단 상호 후보: ['품명', "'*’표시는"] |
| receipt_generalization/food_004.jpg | classification_mismatch | 29 | 쭈꾸미낙지볶음전문점 대성, 대표자:박준영 | - | doc_type 오분류 → position 기반 signal 가중치 개선 후보 (T-19c |
| receipt_generalization/medical_001.jpg | parser_missed_source_exists | 22 | 사업자 등록번호, 전 화 번 호 | - | 상단 상호 후보: ['사업자 등록번호', '전 화 번 호'] |
| receipt_generalization/medical_002.jpg | parser_missed_source_exists | 45 | 세부내역, 수량 | - | 상단 상호 후보: ['세부내역', '수량'] |
| receipt_generalization/pos_001.jpg | ocr_source_garbled | 13 | 합한a, (분첨동) | - | OCR source 손상 → bbox 기반 재처리 또는 preprocessing 개선 후  |
| receipt_generalization/pos_002.jpg | parser_missed_source_exists | 73 | 교환/환을 구매침에서 가능(결제카드지참), 상품명 | - | 상단 상호 후보: ['교환/환을 구매침에서 가능(결제카드지참)', '상품명'] |
| receipt_generalization/pos_003.jpg | metadata_mismatch | 65 | 카드:, 현금: | 사업자동록번호:129-21-65920 | manifest 오기입 → T-15e에서 확인됨, manifest 수정 필요 |
| receipt_generalization/pos_006.jpg | classification_mismatch | 11 | n원'안l은 | - | doc_type 오분류 → position 기반 signal 가중치 개선 후보 (T-19c |
| invoice_statement/2.pdf | ocr_source_missing | 134 | 영업지점, 거래일자 | 112-81-47103 대표자엄태관 | PDF/이미지에서 OCR 원문 없음 → live OCR 재실행 필요 |
| invoice_statement/3.pdf | ocr_source_missing | 72 | GI, 거래일자 | 113-85-04425 | PDF/이미지에서 OCR 원문 없음 → live OCR 재실행 필요 |
| invoice_statement/5.pdf | ambiguous_candidates | 87 | 팀지점코드, 사업자번호 | 209-81-00872 | amount 후보 모호성 → bbox score 기반 선택 개선 후보 (T-19b) |

## 7. 저장 파일
- `mysuit-ocr\public\data\testsets\reports\T19raw_ocr_raw_lines_snapshot_20260516.json`
- `mysuit-ocr\public\data\testsets\reports\T19raw_ocr_raw_line_snapshot_export_20260516.md`
- `mysuit-ocr/public/data/testsets/reports/ocr_raw_lines/{testsetId}_{filename}.json` (샘플별)

## 8. 한계
- **bbox/confidence 없음**: cache-only 모드에서는 실제 bbox/confidence 불가. live OCR 엔진 필요.
- **synthetic y_ratio**: 줄 인덱스 기반 위치 추정, 실제 픽셀 위치와 다를 수 있음.
- **multi-page**: PDF 다중 페이지 지원은 live OCR 모드에서만 가능.
- **기본 응답 미포함**: 운영 /ocr/extract 응답에는 rawLines 미포함. debug 목적으로만 사용.

### live OCR 모드 사용법 (미래, GPU 환경 필요)
```python
# main.py /ocr/extract 에 debugRawLines=true 추가 예시 (architecture hook)
# POST /ocr/extract?debugRawLines=true
# → response.extract_debug.rawLines = normalize된 raw line 목록
```

## 9. 다음 작업 판단

### T-19 readiness
| 작업 | 가능 여부 | 근거 |
|---|---|---|
| T-19a merchantName bbox scoring | **가능 (synthetic)** | y_ratio 기반 상단 라인 필터링 가능 |
| T-19b amount bbox selection | **가능 (synthetic)** | y_ratio 기반 하단 영역 필터링 가능 |
| T-19c classification position weighting | **가능 (synthetic)** | 라인 카테고리 + 위치 조합 분석 가능 |
| live bbox/confidence 기반 개선 | **미가능** | 실제 OCR 엔진 실행 필요 (GPU 환경) |

**결론: synthetic y_ratio 기반 T-19a/T-19b/T-19c 실험은 현재 가능. 실제 bbox precision 개선은 live OCR 환경 구축 후.**
