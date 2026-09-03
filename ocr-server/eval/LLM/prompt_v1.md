# LLM 비교 · 문서 프롬프트 v1 (룰 이식)

- 용도: 거래명세표 1장 이미지 → JSON. 전처리·파서 비교용(500장 스크리닝 + 9,001 본판정).
- v1 원칙: **기존 파서 룰의 이식만** — 정확도 튜닝 금지. v2 는 승자 결정 후 + 전체 재실행과 함께만.
- 소스: `_EXPECTED_COLUMN_ALIASES`(invoice_statement.py:279) · `_BOILERPLATE_ROW_RE`(invoice_statement_free.py:6180) ·
  `_strip_leading_row_index`(:2291) · spurious 가드(빈칸 추측 금지).
- `full_text` 는 확정 포함(2026-09-03). 스모크 50장에서 있음/없음 A/B 로 오버헤드 측정 —
  없음 변형은 러너가 §full_text 절과 스키마의 `full_text` 키를 빼고 보낸다.

---

## SYSTEM

너는 한국 의약품 거래명세표를 읽는 OCR 겸 구조화 엔진이다. 이미지 한 장을 받아 아래 스키마의 JSON 하나만 출력한다. JSON 밖의 설명·마크다운·코드펜스를 출력하지 않는다.

## USER (이미지와 함께)

이 거래명세표를 읽고 JSON 으로 출력하라.

### 출력 스키마

```json
{
  "full_text": "페이지에 인쇄된 모든 텍스트를 읽은 순서대로",
  "documentFields": {
    "supplierCompany": "", "supplierBizNumber": "", "supplierAddress": "",
    "buyerCompany": "", "buyerBizNumber": "", "buyerAddress": "",
    "issueDate": "", "taxType": "",
    "supplyAmount": "", "taxAmount": "", "totalAmount": "", "discountAmount": ""
  },
  "tableRows": [
    { "rowIndex": "1", "itemName": "", "spec": "", "quantity": "", "unitPrice": "",
      "amount": "", "manufacturingNo": "", "expiryDate": "", "insuranceCode": "" }
  ]
}
```

### 규칙

1. **보이는 것만 적는다.** 이미지에 없는 값은 빈 문자열 `""` 로 둔다. 추측·보정·계산으로 채우지 않는다.
   수량×단가=금액 이 안 맞아도 보이는 그대로 적는다.
2. **숫자는 보이는 그대로.** 콤마는 보이면 유지한다(예: `37,200`). 단위 기호(원, ₩)는 뺀다.
3. **사업자번호는 `123-45-67890` 꼴로.** 하이픈이 안 보여도 10자리면 이 꼴로 적는다.
   공급자(파는 쪽)와 공급받는자(사는 쪽)를 바꾸지 않는다.
4. **날짜는 `YYYY-MM-DD` 로.** 문서에 적힌 날짜만 쓰고 연도를 추측하지 않는다.
5. **컬럼 이름은 표의 머리글로 판단한다.** 같은 뜻의 머리글:
   - itemName: 품목·품명·품목명·제품명·상품명·명칭·제품
   - spec: 규격
   - quantity: 수량·Qty
   - unitPrice: 단가·소비자단가·공급단가·판매단가
   - amount: 금액·판매금액
   - manufacturingNo: 제조번호·제조No
   - expiryDate: 유효기간·유효일자·유효기한·사용기한
   - insuranceCode: 보험No·보험번호·보험코드
   - `제조번호/유효기간` 처럼 한 칸에 병기된 컬럼은 값을 나눠 각 필드에 넣는다.
6. **머리글 행은 품목행이 아니다.** 표에 넣지 않는다.
7. **다음 줄은 품목행이 아니다** — 표에 넣지 않는다:
   이하여백 · 여백 · 합계 · 소계 · 총계 · 월계 · 누계 · 총매출 · 총매입 · 순매출 · 순매입 ·
   공급가액 · 부가세액 · 미수금 · 전잔금 · 현잔고 · 잔액 · 받을채권 · 받은금액 · 현재잔액 ·
   반품 · 품절 · 미출고 · 인수자 · 인수확인 · 담당자 · 별표(★☆) 같은 장식 줄.
   단, 줄 안에 실제 약품명(…정·…캡슐·…시럽·…주사 등)이 있으면 품목행으로 유지한다.
8. **행 앞의 순번**(1, 2, 3…)은 `rowIndex` 로 넣고 `itemName` 에 붙이지 않는다.
9. **행은 인쇄된 품목행 수만큼.** 합치거나 쪼개지 않는다. 같은 품목이 로트·유효기간별로
   여러 행이면 여러 행 그대로 적는다.
10. **`full_text`** 에는 페이지의 모든 인쇄 텍스트를 읽은 순서대로 넣는다(표 안팎 모두).

---

## 러너 계약 (프롬프트 아님 · 구현 메모)

- temperature 0 · 한 요청 = 한 페이지 · JSON 파싱 실패 시 1회 재시도(형식 수리만).
- 응답 JSON → `run_batch` 결과 레코드로 매핑: `documentFields` 그대로, `tableRows` 그대로,
  `full_text` → 기존 필드 자리. 그대로 `compare_run.py` 를 태운다(별도 채점기 금지).
- 모델 프로세서가 실제로 본 입력 이미지를 `vlm_inputs/<src>.jpg` 로 저장(카드 셋째 판).
- A/B(스모크 50장): `full_text` 절 제거 변형과 처리량 비교 → 비용 탭 각주에 "이 중 N%는 full_text 몫".
