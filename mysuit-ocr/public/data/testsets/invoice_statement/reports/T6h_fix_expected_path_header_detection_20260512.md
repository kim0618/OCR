# T-6h-fix expected_columns 경로 활성화 및 header detection 보정 결과

## 1. 수정 파일
- `d:/Free_Vue/OCR/ocr-server/extractors/invoice_statement.py`

## 2. 백업 파일
- `d:/Free_Vue/OCR/ocr-server/backup/invoice_statement_20260512_before_T6h_fix_expected_path_header_detection.py`

## 3. 핵심 요약
- **7.pdf `composite_display_empty` 완전 제거**: serialNo, unit, serialLotComposite 이제 모두 채워짐
- **7.pdf expected_columns_header_match 경로 활성화**: 이전에 legacy 사용 → 이제 expected_columns 사용
- **근본 원인**: `_PHONE_RE`에 `(?!\d)` trailing lookbehind 추가 → lot/serial 번호 형식 `0350623-231024-260811`이 전화번호로 오인식되던 문제 해결
- **5.pdf**: header detection 완화 시도 → 5→1 대규모 회귀 → 즉시 revert → 5.pdf는 이번 작업 한계로 남김

## 4. expected path 진입 조건 변경

### 변경 사항 (유지됨)
- `_PHONE_RE`: `(?!\d)` trailing lookbehind 추가

```python
# 수정 전
_PHONE_RE = re.compile(r"...(?<!\d)(?:0\d{1,2})[-)\s]?\d{3,4}[-\s]?\d{4}")
# 수정 후
_PHONE_RE = re.compile(r"...(?<!\d)(?:0\d{1,2})[-)\s]?\d{3,4}[-\s]?\d{4}(?!\d)")
```

**효과**: `0350623-231024-260811` 형식의 시리얼/lot번호가 `035-0623-2310` 패턴으로 오인식되지 않음. `(?!\d)` 없으면 "2310" 뒤 "24" 상관없이 매칭 → 있으면 "24" 때문에 실패.

### 시도 후 revert된 변경 (위험)
- `_find_expected_header_band`: score >= 1 완화 → 5.pdf에서 잘못된 header row를 저점수로 매칭 → expected_columns path 강제 활성화 → boundary 오배치 → rowCount 6→1 대규모 회귀 → **즉시 revert**
- `_build_boundaries_from_expected_columns`: min_matches=1 완화 → 동반 revert

## 5. 샘플별 rowCount
| 샘플 | 목표 | T-6h | T-6h-fix | 판정 |
|---|---:|---:|---:|---|
| 1.jpg | 28 | 29 | 29 | ✓ 유지 |
| 2.pdf | 확인 필요 | 2 | 2 | 변화 없음 |
| 3.pdf | 확인 필요 | 1 | 1 | ✓ 유지 |
| 4.pdf | 확인 필요 | 4 | 3 | T-6h 4행 중 1개 false positive 제거됨 |
| 5.pdf | 6 | 6 | 6 | ✓ 유지 (회귀 없음) |
| 6.pdf | 6 | 5 | 5 | ✓ 유지 |
| 7.pdf | 1 | 1 | 1 | ✓ 유지 |

## 6. value mapping 변화
| 샘플 | T-6h 문제 | T-6h-fix 결과 | 남은 문제 |
|---|---|---|---|
| 7.pdf | serialLotComposite/unit/quantity 비어 있음 | serialNo, unit, serialLotComposite 채워짐 | quantity 미채워짐 ("1,000" 별도 행 거부) |
| 5.pdf | itemCode/unitPrice/amount 비어 있음 | 변화 없음 | header 미매칭 → expected_columns path 미활성화 |
| 6.pdf | rowCount 5/6 | 변화 없음 | 1행 여전히 부족 |
| 2.pdf | rowCount 2 | 변화 없음 | legacy path 한계 |

## 7. tableDebug 요약
| 샘플 | expectedPathUsed | src | headerScore | matchedKeys | fallbackReason |
|---|---|---|---:|---|---|
| 5.pdf | N | legacy_text_items | - | - | header score 부족 (OCR garble) |
| 7.pdf | **Y** | expected_columns_header_match | 5 | itemName, unit, quantity | - |
| 6.pdf | Y | expected_columns_header_match | 8 | 6/6 | - |
| 2.pdf | N | legacy_text_items | - | - | header score 부족 |

## 8. 7.pdf 상세 개선 내용
- **이전**: legacy_text_items path, itemName만 채워짐
- **이후**: expected_columns_header_match path
  - `serialNo = '0350623-231024-260811'` ✓
  - `unit = 'BOX'` ✓  
  - `serialLotComposite = '0350623-231024-260811'` ✓ (자동 생성)
  - `quantity = ''` — "1,000" 값이 별도 y 위치 행에 있어 `no_item_name` 거부됨
- **근본 원인**: `_PHONE_RE`가 "0350623-231024-260811"의 일부("035-0623-2310")를 전화번호로 오인식 → `_is_business_contact_line` 반환 True → 전체 행 `header_or_contact`로 거부

## 8-2. 4.pdf 변화 분석
- T-6h에서 4번째 row는 y>0.96에서 캡처된 footer row (false positive)
- T-6h-fix: expected_columns path에서 3개 row 추출 (column assignment 일부 오인식 있음)
- `unit='0350823-231024-200811'` — serial 번호가 unit 컬럼으로 오분류
- 4.pdf는 `ocr_garbled` 샘플이라 column assignment 품질 제한적

## 9. 회귀 확인
| 샘플 | 확인 항목 | 결과 |
|---|---|---|
| 1.jpg | itemName/unitPrice/amount 유지 | ✓ 유지 (failures=row_count_over만) |
| 5.pdf | rowCount 6 유지 | ✓ 6 유지 |
| 7.pdf | rowCount 1 유지 | ✓ 1 유지 |

## 10. 검증 결과
- backend py_compile: 통과 ✓
- verify script: 7/7 API 성공 ✓
- frontend typecheck: 통과 ✓
- frontend build: 통과 ✓

## 11. 2.pdf 분석 (분석만)
- `rejectedRows (4)`: 모두 `header_or_contact`
  - "1 /1 이 거래명세서 www.ossbook.co.kr을..." — 문서 footer/header
  - "22.312.320 당일거래금액 30,360 3,036 9.064..." — 금액 summary 행
  - "- 거래처 청구금액합계 소비자단가 A3 30,360..." — header/summary 혼합
- `rowCount=2` 유지: legacy path, itemName만 추출 가능한 구조
- 문제: 표 상단에 금액 summary와 헤더 정보가 혼재하여 header detection 실패
- **후속 판단**: T-6h-fix-2pdf 또는 T-6i template bounds 연동 필요

## 12. 5.pdf 분석 (분석만)
- `headerBandFound=None`: OCR이 "품명", "품목코드", "수량", "단가", "금액" 헤더를 인식하지 못함
- `headerLines=['???garbled', '3,000', 'C']`: auto-detection이 데이터 행을 헤더로 오인식
- score >= 1 완화 시도 → 오인식 헤더가 score 1로 통과 → 잘못된 boundary → rowCount 6→1 회귀
- **근본 원인**: 5.pdf OCR garble로 헤더 텍스트 인식 불가
- **후속 판단**: template bounds 연동 또는 다른 접근 필요 (T-6i)

## 13. 다음 작업 판단
- **7.pdf 주요 개선 완료** (serialNo/unit/serialLotComposite): quantity 미채워짐만 남음
- **5.pdf**: header detection 방법론적 한계 → T-6i template bounds 또는 전용 처리 필요
- **6.pdf**: 5/6 → 추가 개선 가능성 낮음, T-6i 또는 별도 처리
- **2.pdf**: 별도 T-6h-fix-2pdf 또는 T-6i
- **1.jpg**: value mapping 완료, rowCount 29 (목표 28, 1행 footer 잔존) → T-7 금액 계열 검토 가능
- **결론**: 주요 value mapping 작업 마무리. 구조적 한계(5.pdf/2.pdf/6.pdf)는 T-6i로 분리.
