# T-6j-real-template-2pdf rowCount 복구 검증 결과

## 2.pdf 구조 분석
- **표 유형**: 전치(transposed) 컬럼 주도 표
- **품목 배치**: 각 컬럼 = 1개 품목 (13개 컬럼)
- **품목코드 위치**: y=47-70, 세로(회전) 텍스트
- **가격 행 위치**: y=394-397, 463-469
- **GT rowCount**: 13
- **표준 세로 행 추출**: 구조적 한계 (가로 표를 세로 표로 오인식)

## 테스트 결과
| 테스트 | extractionSource | cgUsed | rowCount | rejectedReasons |
|---|---|---|---:|---|
| baseline (no bounds/guides) | legacy_text_items | False | 2 | {'header_or_contact': 3, 'summary_row':  |
| body_only_bounds (y=340-540) | legacy_text_items | False | 2 | {'header_or_contact': 3, 'summary_row':  |
| price_rows_bounds (y=355-490) | legacy_text_items | False | 2 | {'header_or_contact': 3, 'summary_row':  |
| full_table_bounds_no_guides (y=40-560) | legacy_text_items | False | 2 | {'header_or_contact': 3, 'summary_row':  |
| colguides_price_area (8 cols for 8 expected k | legacy_text_items | False | 2 | {'header_or_contact': 3, 'summary_row':  |
| colguides_narrow_price_area (y=385-410) | legacy_text_items | False | 2 | {'header_or_contact': 3, 'summary_row':  |
| colguides_with_insurance (y=340-500) | legacy_text_items | False | 2 | {'header_or_contact': 3, 'summary_row':  |
| colguides_full_page (y=40-560) | template_colguides_expected_co | True | 1 | {'header_or_contact': 4, 'summary_row':  |
| colguides_top_half (y=40-350) | template_colguides_expected_co | True | 1 | {'header_or_contact': 2} |

## 결론
- **최대 달성 rowCount**: 2 (목표 13)
- **근본 원인**: 2.pdf는 전치 표 구조 (가로 = 품목, 세로 = 가격항목). 표준 세로 행 추출기로 13행 복구 불가.
- **Template annotation 없음**: templates.json에 2.pdf 해당 템플릿 없음
- **후속 조치**: 전치 표 전용 추출 로직 개발 또는 2.pdf를 rowCount 검증 대상에서 제외
