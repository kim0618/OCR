# T-4 Test UI tableRows/tableMeta 연동 결과

## 1. 수정 파일
- `src/components/test/TestWorkspace.tsx`

## 2. 백업 파일
- `backup/TestWorkspace_20260512_before_T4_tableRows_tableMeta.tsx`

## 3. 핵심 요약
- backend `extract_invoice_statement_fields`가 이미 `document_fields` 내에 `tableRows`(배열) 및 `tableMeta`(객체)를 포함해 반환하고 있었음
- OcrEntry.documentFields 타입이 `Record<string, string>`으로 선언되어 있어, 배열/객체 값을 직접 접근하면 타입 오류 발생
- `getInvoiceTableRows` / `getInvoiceTableMeta` 헬퍼로 `Record<string, unknown>` 캐스팅 후 안전하게 추출
- `buildTableRowsValidation` 내 `parser_not_ready` 하드코딩을 `tableMeta.extractionStatus` 기반 판정으로 교체
- `InvoiceTableRowsPanel` 컴포넌트 신규 추가 — canonical column 15개(기본) + 보조 3개(토글) 표 표시, raw JSON 펼치기
- `DocumentDetailPanel` 내 `TableRowsValidationPanel` 바로 아래에 `InvoiceTableRowsPanel` 삽입
- 기존 party/address/amount/summary 필드 판정, 영수증/금융 테스트셋 UI에 영향 없음
- typecheck: 통과 / build: 성공

## 4. tableRows 읽기 구조
- 읽는 위치: `(documentFields as Record<string, unknown>)?.tableRows`
- fallback: 배열이 아닌 경우 빈 배열 `[]` 반환
- 빈 배열 처리: `tableRows.length === 0`이면 상태 메시지만 표시, 패널 자체는 유지
- parser_not_ready 방지: `tableRows.length > 0`이면 `extractionStatus`가 `parser_not_ready`가 되지 않음
  - 실제 `tableMeta.extractionStatus === "partial"` 이면 partial로 표시

## 5. tableMeta 읽기 구조
- 읽는 위치: `(documentFields as Record<string, unknown>)?.tableMeta`
- extractionStatus 표시: `tableMeta.extractionStatus` → "partial" / "not_extracted" / "parser_not_ready"
- rowCount/columnCount 표시: `tableMeta.rowCount`, `tableMeta.columns.length`
- fallback:
  - `tableMeta` 없음 → `tableRows.length`로 rowCount 대체
  - `firstRowPreview` 없음 → `documentFields.firstRowPreview` 대체

## 6. UI 표시 변경
- 표 추출 결과 섹션: `InvoiceTableRowsPanel` 추가 (TableRowsValidationPanel 바로 아래)
- canonical column 표시:
  - 기본: rowIndex / itemCode / itemName / spec / lotNo / manufacturingNo / expiryDate / quantity / unit / unitPrice / supplyAmount / taxAmount / amount / totalAmount / remark (15개)
  - 보조(토글): serialNo / manufacturer / insuranceCode (3개)
  - 가로 스크롤 지원
- raw 보기: "원본 tableMeta 보기" 버튼 / "원본 tableRows JSON 보기" 버튼 (각 독립 토글)
- invoice_statement 외 문서 영향: `invoiceProfile?.tableProfile`이 없으면 InvoiceTableRowsPanel 비표시

## 7. 상태 판정
| 상태 | 기준 | 표시 |
|---|---|---|
| partial | `tableMeta.extractionStatus === "partial"` 또는 `tableRows.length > 0` | "부분 추출 (partial)" — 황색 배경 |
| not_extracted | `tableMeta.extractionStatus === "not_extracted"` 또는 tableMeta/tableRows 모두 없음 | "미추출" — 짙은 배경 |
| parser_not_ready | tableMeta 없고 tableRows 없는데 `documentFields.rowCount` 또는 GT rowCount 존재 | "parser 미구현" — 회색 배경 |
| ready | (현재 백엔드가 "ready"를 아직 반환하지 않으므로 표시 대기) | "추출 완료" — 녹색 배경 |
| error | (별도 경로 없음, 현재 미사용) | "오류" |

## 8. 기존 기능 영향 확인
| 항목 | 결과 |
|---|---|
| invoice_statement party 필드 판정 | 유지 — DocumentFieldCard 변경 없음 |
| 주소 판정 | 유지 — 판정 로직 미수정 |
| amount/summary/meta 표시 | 유지 — visibleMeta/summaryMeta 흐름 미수정 |
| rowCount | 유지 + tableMeta.rowCount 우선 표시 |
| firstRowPreview | 유지 + tableMeta.firstRowPreview fallback 적용 |
| tableDetected | 유지 — documentFields.tableDetected 그대로 읽음 |
| 영수증 테스트셋 | 영향 없음 — selProfile.base === "document" 조건 내에서만 DocumentDetailPanel 호출 |
| Test 탭 진입 | 정상 |
| RunOCR 미수정 | 확인 — RunOCR 관련 파일 미수정 |
| Template 미수정 | 확인 — Template 관련 파일 미수정 |
| History 미수정 | 확인 — History 관련 파일 미수정 |

## 9. 검증 결과
- typecheck: **통과** (오류 0건)
- build: **성공** (Next.js 15.5.4, /test 번들 41.6 kB)
- 브라우저 확인: 백엔드 실행 후 invoice_statement 테스트셋 실행 시 확인 필요

## 10. 확인한 샘플 (브라우저 실행 전 — 구조 분석 기반 예상)
| 샘플 | tableRows | tableMeta 상태 | rowCount | 비고 |
|---|---:|---|---:|---|
| invoice_statement 1 (1.jpg) | 있을 것 | partial | backend 추출값 | item_amount_table |
| invoice_statement 2 (2.pdf) | 있을 것 | partial | backend 추출값 | standard_amount_statement |
| invoice_statement 3 (3.pdf) | 있을 것 | partial | backend 추출값 | blue form |
| invoice_statement 4 (4.pdf) | 불확실 | partial/not_extracted | — | ocr_garbled |
| invoice_statement 5 (5.pdf) | 있을 것 | partial | backend 추출값 | multi-page |
| invoice_statement 6 (6.pdf) | 있을 것 | partial | backend 추출값 | buyer_only |
| invoice_statement 7 (7.pdf) | 있을 것 | partial | backend 추출값 | serial_quantity |

## 11. 남은 문제
- 브라우저에서 실제 샘플별 tableRows 값 확인 필요 (backend 재실행 후)
- 일부 샘플에서 컬럼 매핑 partial (itemName, spec 등이 없는 행 존재 가능)
- tableRows 값 표시만 연결했고 parser 개선은 후속 작업 (T-5 이후)
- RunOCR 화면에 tableRows 표시 반영 미완료
- Template table 영역과 tableRows 연결 미완료

## 12. 다음 추천 작업
- **T-5**: invoice_statement 1~7 tableRows 샘플별 재검증 및 컬럼 실패 유형 정리
- **T-6**: tableRows 컬럼 매핑 보강 (lotNo, expiryDate, itemCode 등 개선)
- **OP-3**: RunOCR canonicalField 기반 output mapping
- **RunOCR-Table-1**: RunOCR 거래명세서 tableRows 표시 반영
