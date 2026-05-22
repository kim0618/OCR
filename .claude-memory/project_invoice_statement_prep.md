---
name: Invoice Statement 1차 구현 준비 완료
description: 거래명세서 extractor 1차 구현 전 설계 준비 완료 (2026-04-29). 내일 Codex 구현 즉시 진입 가능 상태.
type: project
originSessionId: fca20759-c1a5-4b6b-9294-764645c5fd7a
---
거래명세서 1차 구현 준비 설계 완료 (2026-04-29).

**Why:** 내일 Codex로 바로 구현 진입하기 위해 오늘 범위/샘플/필드/manifest 설계 정리 선행.

**How to apply:** 내일 구현 시 docs/INVOICE_STATEMENT_PREP_20260429.md를 기준 문서로 사용.

## 샘플 분류 (OCR/sample/)

| 파일 | 페이지 | 유형 | 1차 역할 |
|---|---|---|---|
| 2.pdf | 1페이지 | 표준 거래명세서 | 1차 주력 |
| 3.pdf | 1페이지 | 청색 거래명세표 | 1차 보조 |
| 4.pdf | 2페이지 | 2페이지 세트 | 구조 확인용 (p1만) |
| 5.pdf | 22페이지 | 다페이지 PDF | 후속 단계용 |

## 1차 필드 (profiles.ts DOCUMENT_COLUMNS 기준 — 타입 이미 완성)

- required: supplierCompany, supplierBizNumber, buyerCompany, issueDate, totalAmount, tableDetected
- optional: supplierRepresentative, supplierAddress, buyerBizNumber, buyerRepresentative, buyerAddress, supplyAmount, taxAmount, rowCount, firstRowPreview

## 1차 extractor 구현 목표 (내일 Codex 작업)

1. `ocr-server/extractors/invoice_statement.py` 신규 작성
2. `document_classifier.py` 거래명세서 감지 시그널 추가
3. `main.py` invoice_statement 브랜치 최소 연결
4. 2.pdf, 3.pdf GT 입력
5. baseline_fast / google / baseline 회귀 검증

## 핵심 구현 주의점

- PaddleOCR 2열 레이아웃: x좌표 중앙 기준으로 supplier/buyer 열 먼저 분리
- 사업자번호 2개: x좌표로 좌=supplier, 우=buyer 구분
- 발행일 정규식: `r'(\d{4})[년\-\.](\d{1,2})[월\-\.](\d{1,2})[일]?'`
- 표 감지 시그널: "품목", "규격", "단가", "수량", "금액" 중 3개 이상 동일 y범위

## 완료된 준비 파일

- `docs/INVOICE_STATEMENT_PREP_20260429.md` — 전체 설계 문서
- `mysuit-ocr/public/data/testsets/invoice_statement/manifest.json` — 4개 샘플 draft 등록
