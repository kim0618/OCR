# T-24: Receipt Baseline GT Mismatch/Missing Root Cause Analysis

- 생성일: 2026-05-19
- 작업명: T-24
- 담당 모델: Claude Sonnet 4.6
- 분석 방법: Codex 실행 결과 JSON 정적 분석 + parser 소스 정적 분석 + GT 재검토
- 코드 수정: **없음**

---

## 1. 요약

| 항목 | 값 |
|------|-----|
| 분석 대상 샘플 | 9개 (baseline 10개 - 은행전표 9.jpg) |
| 전체 필드 수 | 54 |
| match | 41 |
| mismatch | 9 |
| missing | 4 |
| 전체 정확도 | 75.93% |
| 가장 약한 필드 | no_5 주소 (33.33%) |
| GT 이슈 의심 건수 | 1건 (2.jpg no_4) |
| **안전 개선 가능 후보** | **3건** (주소 공백/도 생략 규칙) |
| **POS 영수증 개선 후보** | **2건** (a1.jpg 대표자/전화번호) |
| **OCR source garbled (보류)** | **7건** |
| **GT 이슈 수동 확인** | **1건** |

---

## 2. 입력 리포트

| 항목 | 경로 |
|------|------|
| Codex GT audit JSON | `D:\Free_Vue\tmp\CODEX_RECEIPT_TEMPLATE_GT_AUDIT_BASELINE10_MINUS_BANK_20260519.json` |
| Codex GT audit MD | `D:\Free_Vue\tmp\CODEX_RECEIPT_TEMPLATE_GT_AUDIT_BASELINE10_MINUS_BANK_20260519.md` |
| Codex TestTab vs RunOCR JSON | `D:\Free_Vue\tmp\CODEX_TESTTAB_VS_RUNOCR_RECEIPT_BASELINE10_MINUS_BANK_20260519.json` |
| GT source | `mysuit-ocr/public/data/testsets/baseline/ground_truth.json` |
| Parser 정적 분석 | `ocr-server/extractors/address.py`, `company.py`, `representative.py` |
| Parser 정적 분석 | `ocr-server/amount_extractor.py`, `ocr-server/main.py` |
| Parser 정적 분석 | `ocr-server/utils/regex_patterns.py` |

### 대상 샘플 9개

| 파일 | documentType (manifest) | documentType (RunOCR) | 비고 |
|------|------------------------|----------------------|------|
| 1.jpg | card_receipt | receipt_card | PASS |
| 2.jpg | card_receipt | receipt_card | no_4 mismatch |
| 3.jpg | card_receipt | receipt_card | no_5 mismatch |
| 4.jpg | card_receipt | receipt_card | no_1 mismatch |
| 7.jpg | food_cafe_receipt | receipt_card | no_5 mismatch |
| 8.jpg | medical_receipt | medical_receipt | no_5 mismatch |
| 10.jpg | card_receipt | receipt_card | no_5 mismatch |
| a1.jpg | card_receipt | **receipt_pos** | 4건 실패 집중 |
| a2.jpg | card_receipt | **form_or_handwritten** | 3건 실패 |

---

## 3. Mismatch/Missing 전체 목록 — 원인 재분류

| # | 파일 | docType | 필드 | GT raw | OCR raw | 상태 | Codex분류 | **재분류** | 개선 가능성 |
|---|------|---------|------|--------|---------|------|-----------|-----------|------------|
| 1 | 2.jpg | card_receipt | no_4 전화번호 | `03147900090` | `031-479-0090` | mismatch | ocr_garbled | **J gt_issue** | GT 수정 필요 (수동) |
| 2 | 3.jpg | card_receipt | no_5 주소 | `경기도...7-117,11` | `경기...7-117.11` | mismatch | ocr_garbled | **H+C 복합** | 일부 개선 가능 |
| 3 | 4.jpg | card_receipt | no_1 회사명 | `정공구` | `가행점` | mismatch | ocr_garbled | **H+D 복합** | OCR raw 미확인 |
| 4 | 7.jpg | food_cafe | no_5 주소 | `...의왕월드비젼` | `...의왕월드 비전` | mismatch | ocr_garbled | **H** | OCR 맞춤법 차이 |
| 5 | 8.jpg | medical | no_5 주소 | `경수대로 237` | `경수대로237` | mismatch | ocr_garbled | **C** | 도로명+번지 공백 규칙 |
| 6 | 10.jpg | card_receipt | no_5 주소 | `(오전동) 1층` | `(오전동)1층` | mismatch | parser_rule | **C** | 괄호 후 공백 규칙 |
| 7 | a1.jpg | card_receipt | no_1 회사명 | `정공구` | `기계공구` | mismatch | ocr_garbled | **H+D 복합** | POS 포맷 문제 |
| 8 | a1.jpg | card_receipt | no_3 대표자 | `정영달` | `` | missing | parser_rule | **E** | POS 영수증 대표자 |
| 9 | a1.jpg | card_receipt | no_4 전화번호 | `031-479-3690` | `` | missing | parser_rule | **F** | POS 영수증 전화번호 |
| 10 | a1.jpg | card_receipt | no_5 주소 | `경기 안양시...엘에스로 92` | `` | missing | ocr_garbled | **H+I 복합** | POS 영수증 주소 없음 |
| 11 | a2.jpg | card_receipt | no_3 대표자 | `이정은` | `이정` | mismatch | ocr_garbled | **H** | 수기 글자 잘림 |
| 12 | a2.jpg | card_receipt | no_5 주소 | `...76, 7-117, 118(호계동...)` | `...76,7-117, (호계동...)` | mismatch | ocr_garbled | **H** | 수기 118 누락 |
| 13 | a2.jpg | card_receipt | no_6 총합계금액 | `480,000` | `` | missing | ocr_garbled | **G+H 복합** | form policy + OCR |

**재분류 코드:**
- A: mapping_fix_candidate / B: parser_rule_candidate / C: address_rule_candidate
- D: merchant_name_candidate / E: representative_rule_candidate / F: tel_rule_candidate
- G: amount_rule_candidate / H: ocr_source_garbled / I: ocr_source_missing
- J: gt_issue_or_ambiguous / K: document_type_mismatch

---

## 4. 필드별 상세 분석

### no_1 회사명 (77.78% / mismatch 2건)

**4.jpg mismatch — GT: `정공구` / OCR: `가행점`**
- OCR가 `가행점`을 반환. `가행점`은 "가맹점"의 OCR 노이즈("가맹점" → "가행점")로 추정.
- `company.py`의 `_company_candidate_score`가 가맹점 컨텍스트 텍스트를 높게 평가했을 가능성.
- `정공구`가 OCR raw에 있었는지 확인 불가 (cache 없음). OCR이 회사명을 못 읽었거나 가맹점명 라벨에서 잘못된 후보를 선택.
- **근본 원인**: OCR source garbled (가맹점 영역 텍스트 오인식) + merchantName 후보 선택 오류
- **재분류**: H (ocr_source_garbled) + D (merchant_name_candidate)

**a1.jpg mismatch — GT: `정공구` / OCR: `기계공구`**
- a1.jpg는 4.jpg와 같은 가게 (정공구, 사업자번호 동일). a1.jpg는 POS 영수증 (receipt_pos).
- `기계공구`는 업종/카테고리 텍스트 ("기계공구 판매업")에서 추출됐을 가능성.
- `정공구`가 POS 영수증 상단에 인쇄되어 있어도 OCR이 다른 텍스트를 우선 선택.
- `company.py` rescue 경로에서 `기계공구` 후보 score가 더 높게 평가됨.
- **근본 원인**: POS 영수증 merchantName 위치 다름 + score 역전
- **재분류**: H (ocr_source_garbled) + D (merchant_name_candidate)

**no_1 개선 방향**: 4.jpg, a1.jpg 모두 OCR raw 확인 없이 parser만으로 고치기 어려움. OCR raw cache가 없어 `정공구`가 실제로 읽혔는지 불확실. **T-25 보류**.

---

### no_2 사업자번호 (100.00% / 이상 없음)

- 9/9 완벽 match. 사업자번호 regex + checksum validation이 안정적으로 작동.
- **이번 개선에서 절대 건드리지 않음. 회귀 방지 최우선.**

---

### no_3 대표자 (77.78% / mismatch 1건 + missing 1건)

**a1.jpg missing — GT: `정영달` / OCR: ``**
- POS 영수증 (receipt_pos). POS 영수증은 카드영수증보다 정보가 간략화됨.
- 4.jpg(같은 가게 카드영수증)에서는 `정영달` 정상 인식 → 포맷 차이 문제.
- `representative.py`의 `_fill_lone_representative_from_lines`가 POS 영수증에서 대표자 라벨 없이 이름만 있을 때 실패.
- `_is_person_like_name`: 3-4자 한글, 성씨 조건. `정영달` (3자, 정씨) → 조건 충족이지만 business_hint 인접 여부 실패 가능.
- **근본 원인**: POS 영수증에서 대표자 라벨/힌트 부재
- **재분류**: E (representative_rule_candidate)
- **개선 후보**: POS 영수증에서 사업자번호 행 ±3 이내에 3-4자 한글 이름 탐색 강화

**a2.jpg mismatch — GT: `이정은` / OCR: `이정`**
- a2.jpg는 form_or_handwritten 타입. 수기 문서에서 `은` 자가 잘림.
- 3.jpg(같은 가게, 카드영수증)에서는 `이정은` 정상 인식.
- **근본 원인**: 수기 OCR 글자 잘림 (H - ocr_source_garbled)
- **개선 불가**: parser 수정으로 복구 불가. 이미지 품질 이슈.

---

### no_4 전화번호 (77.78% / mismatch 1건 + missing 1건)

**2.jpg mismatch — GT: `03147900090` / OCR: `031-479-0090`**
- GT normalized: `03147900090` (11자리), OCR normalized: `0314790090` (10자리)
- **GT 이슈 의심**: `031-479-0090` → 정규화 → `0314790090` (10자리, 정상 한국 지역번호)
- GT raw `03147900090`은 11자리 → 한국 지역번호 `031-479-0090` (10자리)와 불일치
- GT 작성 시 `031 479 0090`을 공백 없이 연결하다 오입력한 것으로 추정 (`0314790090` 10자리가 맞음)
- OCR 결과 `031-479-0090` → 정규화 `0314790090` (10자리)가 실제로 올바른 전화번호
- **재분류: J (gt_issue_or_ambiguous)** — OCR이 정답이고 GT가 오입력
- **수동 확인 필요**: GT 수정은 이번 작업 범위 외. T-25에서 GT 검증 후 수정.

**a1.jpg missing — GT: `031-479-3690` / OCR: ``**
- POS 영수증 (receipt_pos). 4.jpg(카드영수증)에서는 동일 전화번호 정상 인식.
- POS 영수증 형식에서 전화번호가 다른 위치/형식으로 인쇄되거나 없을 수 있음.
- `_extract_fields_from_rows`의 tel 추출이 POS 영수증 레이아웃에서 실패.
- **재분류: F (tel_rule_candidate)**
- **개선 후보**: POS 영수증에서 사업자번호 인접 행 전화번호 패턴 보강

---

### no_5 주소 (33.33% — 가장 약한 필드 / mismatch 5건 + missing 1건)

이슈 유형 분류:

**① 괄호 닫힘 후 공백 누락 — 10.jpg (C: address_rule_candidate)**
- GT: `경기 의왕시 효행로 47 (오전동) 1층`
- OCR: `경기 의왕시 효행로 47 (오전동)1층`
- 패턴: `)\d` 또는 `)[가-힣]` → `) \d`, `) [가-힣]`
- Codex도 `parser_rule_candidate`로 분류
- **주소 후처리 정규화 규칙 추가로 안전하게 수정 가능**
- `re.sub(r'\)([가-힣0-9])', r') \1', address_value)` 적용
- 회귀 위험: 낮음 (`)숫자` 패턴이 이미 올바른 경우는 드물기 때문)

**② 도로명+번지 공백 누락 — 8.jpg (C: address_rule_candidate)**
- GT: `경기 의왕시 경수대로 237`
- OCR: `경기 의왕시 경수대로237`
- 패턴: `[로길대로가](\d)` → `[로길대로가] \1`
- OCR raw에서 `경수대로237`로 붙여 읽힘 → 주소 후처리에서 공백 삽입 가능
- `re.sub(r'([로길가])\b(\d)', r'\1 \2', address_value)` 근사 적용
- 회귀 위험: 중간 (이미 붙어있는 `강남대로123` 같은 케이스는 드물지만 점검 필요)
- **T-25a 1순위 후보**

**③ `경기도` → `경기` 단축 — 3.jpg (H+C 복합)**
- GT: `경기도 안양시 동안구 엘에스로 76 (호계동) 7-117,11`
- OCR: `경기 안양시 동안구 엘에스로 76 (호계동)7-117.11`
- 서브이슈 3개 혼재:
  - `경기도` → `경기`: OCR이 `도` 누락. 정규화 규칙으로 `경기 ` → `경기도 ` 추가 가능하나 false positive 위험 (경기가 문장 중간에 나올 수 있음)
  - `(호계동)7` → `(호계동) 7`: ① 케이스와 동일 패턴 → 개선 가능
  - `7-117,11` vs `7-117.11`: OCR이 `,`를 `.`으로 오인식 → parser만으로 복구 불가
- **일부 개선 가능, 일부 garbled**

**④ 공백/맞춤법 차이 — 7.jpg (H: ocr_source_garbled)**
- GT: `경기도 의왕시 경수대로 209 102호 (고천동, 의왕월드비젼)`
- OCR: `경기도 의왕시 경수대로 209 102호(고천동,의왕월드 비전)`
- `102호 ` vs `102호`: 공백 — ① 케이스와 유사 (괄호 전 공백 추가 가능)
- `의왕월드비젼` vs `의왕월드 비전`: 맞춤법 차이 + OCR이 단어 내 공백 추가. **복구 불가**.
- ① 규칙을 적용하면 `102호(`→`102호 (`는 개선 가능. 나머지 garbled.

**⑤ a1.jpg missing — `경기 안양시 동안구 엘에스로 92` (H+I)**
- OCR: `` (완전 없음)
- POS 영수증에서 주소 자체가 인쇄되지 않았거나 OCR raw에 없음.
- 4.jpg(카드영수증 동일 가게)에서는 정상 인식 → POS 포맷 문제 또는 OCR 미인식.
- **복구 불가**: parser 수정으로 해결 불가.

**⑥ a2.jpg mismatch — 수기 주소 118 누락 (H)**
- GT: `...76, 7-117, 118(호계동, 국제유통단지)`
- OCR: `...76,7-117, (호계동, 국제유통단지)` — `118`이 완전히 누락
- 수기 문서에서 `118`이 OCR로 읽히지 않음.
- **복구 불가**: OCR source 문제.

**주소 no_5 소결**:
- 개선 가능 안전 케이스: 10.jpg (괄호 후 공백), 8.jpg (도로명+번지 공백), 7.jpg+3.jpg 일부 (괄호 후 공백)
- 개선 불가: a1.jpg (POS 없음), a2.jpg (수기 118 누락), 3.jpg 일부 (`,` vs `.`), 7.jpg `비젼`/`비전`
- 주소 false positive 위험 때문에 공격적 개선 금지. 보수적 규칙만 T-25b로 분리.

---

### no_6 총합계금액 (88.89% / missing 1건)

**a2.jpg missing — GT: `480,000` / OCR: ``**
- a2.jpg: form_or_handwritten 타입
- `_apply_doc_type_amount_policy`: form_or_handwritten → `score ≥45` 또는 non-bare 필요
- `480,000`이 OCR raw에 있어도 bare pattern이고 score가 낮으면 suppressed됨
- 수기 문서에서 금액 인식 자체가 어렵거나 policy가 너무 엄격
- **재분류: G (amount_rule_candidate) + H (ocr_source_garbled)**
- form_or_handwritten policy 완화는 false positive 위험 (다른 숫자를 총합계로 잘못 선택) → **신중하게 접근 필요**
- **T-25에서 단독 분리 검토 필요**

---

## 5. 샘플별 분석

### 5-1. a1.jpg — 집중 분석 (4건 실패)

```
파일: a1.jpg
GT documentType: card_receipt (manifest)
RunOCR documentType: receipt_pos ← manifest와 불일치!
사업자번호: 123-23-94265 (4.jpg와 동일 가게)
실패 필드: no_1(mismatch), no_3(missing), no_4(missing), no_5(missing)
성공 필드: no_2(match), no_6(match)
```

**핵심 원인: document type mismatch**
- a1.jpg는 manifest에서 `card_receipt`로 분류되었으나 실제 RunOCR이 `receipt_pos`로 인식
- POS 영수증(receipt_pos)과 카드영수증(card_receipt)은 구조적으로 다름
- POS 영수증은 가맹점 정보(대표자, 전화, 주소)가 생략되거나 다른 레이아웃

**필드별 원인**:
| 필드 | 원인 | 카드영수증(4.jpg)과 비교 |
|------|------|----------------------|
| no_1 회사명 | POS 영수증에서 업종명(`기계공구`)을 회사명으로 오인식 | 4.jpg에서는 `정공구` 정상 |
| no_3 대표자 | POS 영수증에서 대표자 라벨 없거나 위치 다름 | 4.jpg에서는 `정영달` 정상 |
| no_4 전화번호 | POS 영수증에서 전화번호 없거나 레이아웃 다름 | 4.jpg에서는 `031-479-3690` 정상 |
| no_5 주소 | POS 영수증에서 주소 인쇄 안 됨 | 4.jpg에서는 `경기 안양시...` 정상 |

**결론**: a1.jpg 실패는 POS 영수증 특유 포맷 + document type mismatch가 복합 원인. 사업자번호(no_2)가 정상 인식된 것은 사업자번호가 POS에서도 일관되게 출력되기 때문. 총합계금액(no_6)도 110,000이 정상 인식 — 금액은 POS에서도 명확하게 출력됨.

**일회성 개선 불가**: a1.jpg는 POS 영수증이므로 대표자/전화/주소 정보가 구조적으로 없을 수 있음. parser 단독 개선보다는 POS 영수증에서 누락 필드 warning/qualityTags 처리가 현실적.

---

### 5-2. a2.jpg — 수기/폼 문서 (3건 실패)

```
파일: a2.jpg
GT documentType: card_receipt (manifest)
RunOCR documentType: form_or_handwritten ← 수기 문서 판정
실패 필드: no_3(mismatch), no_5(mismatch), no_6(missing)
성공 필드: no_1(match), no_2(match), no_4(match)
```

- `이정은` → `이정`: 수기 글자 잘림 (은 누락)
- 주소 `118` 누락: 수기 숫자 OCR 실패
- 총합계금액 `480,000` missing: form_or_handwritten policy score ≥45 미달 또는 OCR raw 미인식
- 3건 모두 수기 문서 OCR 한계 → parser 개선보다는 문서 품질 이슈

---

### 5-3. 1.jpg — PASS 샘플 (참고)

- 6/6 match. card_receipt, 경기 안양시 동안구 호계동. 완벽 동작.
- 주소 `경기 안양시 동안구 호계동 555-9 국`이 정확히 일치 → 기준 샘플.

---

### 5-4. 주소 공백 패턴 — 3.jpg, 7.jpg, 8.jpg, 10.jpg

총 5건 중 4건이 주소 관련 공백/포맷 문제:

| 샘플 | 패턴 | 개선 가능? |
|------|------|-----------|
| 3.jpg | `(호계동)7-117.11` (공백+구두점) | 공백 부분만 가능 |
| 7.jpg | `102호(고천동` (공백), `의왕월드 비전` (맞춤법) | 공백만 가능 |
| 8.jpg | `경수대로237` (도로명+번지 공백) | 가능 |
| 10.jpg | `(오전동)1층` (공백) | 가능 |

공통 패턴: `)\d`, `)\[가-힣\]` 패턴에 공백 삽입 → 3, 7, 10.jpg 공백 이슈 해결 가능

---

## 6. 원인 분류 집계

| 코드 | 원인 | 건수 | 개선 가능성 | 권장 조치 |
|------|------|------|------------|----------|
| C | address_rule_candidate | **3건** | 높음 | T-25b 보수적 주소 규칙 |
| E | representative_rule_candidate | **1건** | 중간 | T-25a POS 대표자 |
| F | tel_rule_candidate | **1건** | 중간 | T-25a POS 전화번호 |
| G | amount_rule_candidate | **1건** | 낮음 | T-25c 별도 검토 |
| H | ocr_source_garbled | **7건** (복합 포함) | 낮음 | 전처리/qualityTags |
| I | ocr_source_missing | **1건** (복합) | 없음 | 보류 |
| J | gt_issue_or_ambiguous | **1건** | GT 수정 필요 | 수동 확인 |
| D | merchant_name_candidate | 2건 (H 복합) | 낮음 | T-25 보류 |

> 합산 건수가 13건을 초과하는 것은 복합 분류 때문.

---

## 7. 개선 후보 Top

### 1순위 — 안전하게 수정 가능 (T-25a/25b)

| 우선순위 | 파일 | 필드 | 원인 | 추천 수정 | 회귀 위험 |
|---------|------|------|------|----------|----------|
| 1 | 10.jpg | no_5 주소 | C | 주소 후처리: `)\d` → `) \d`, `)[가-힣]` → `) [가-힣]` | 낮음 |
| 2 | 8.jpg | no_5 주소 | C | 주소 후처리: `[로길가]\d` → `[로길가] \d` 공백 삽입 | 중간 |
| 3 | 3.jpg | no_5 주소 (부분) | C | 10.jpg와 동일 괄호 후 공백 규칙 | 낮음 |
| 4 | 7.jpg | no_5 주소 (부분) | C | 10.jpg와 동일 괄호 후 공백 규칙 | 낮음 |

> **주의**: 주소 규칙은 false positive 위험이 있으므로 반드시 baseline 9개 + receipt_generalization 17개 전체 회귀 검증 후 적용.

### 2순위 — POS 영수증 개선 (T-25a)

| 우선순위 | 파일 | 필드 | 원인 | 추천 수정 | 회귀 위험 |
|---------|------|------|------|----------|----------|
| 5 | a1.jpg | no_3 대표자 | E | POS 영수증에서 사업자번호 ±3행 내 3-4자 한글 이름 탐색 강화 | 중간 |
| 6 | a1.jpg | no_4 전화번호 | F | POS 영수증에서 사업자번호 인접 행 phone 패턴 추가 | 낮음 |

### 3순위 — GT 수정 (수동 확인)

| 우선순위 | 파일 | 필드 | 원인 | 추천 조치 |
|---------|------|------|------|----------|
| 7 | 2.jpg | no_4 전화번호 | J | GT `03147900090` → `031-479-0090` 수정 검토. OCR 결과가 정답일 가능성 높음. |

### 보류 (수정 비권장)

| 파일 | 필드 | 원인 | 보류 사유 |
|------|------|------|----------|
| 4.jpg | no_1 회사명 | H+D | OCR raw 미확인. `정공구` 인식 가능 여부 불확실. |
| a1.jpg | no_1 회사명 | H+D | POS 영수증 구조적 문제. Parser만으로 해결 어려움. |
| a1.jpg | no_5 주소 | H+I | POS 영수증에서 주소 자체 없음. |
| a2.jpg | no_3 대표자 | H | 수기 문서 OCR 잘림. 복구 불가. |
| a2.jpg | no_5 주소 | H | 수기 문서 `118` 누락. 복구 불가. |
| a2.jpg | no_6 총합계금액 | G+H | form policy + OCR. 별도 T-25c 검토. |

---

## 8. 안전하게 수정 가능한 후보 — T-25a/T-25b

### T-25a: POS 영수증 safe rule improvements

**대상**: a1.jpg no_3 (대표자), a1.jpg no_4 (전화번호)

**수정 범위**:
- `extractors/representative.py`의 `_fill_lone_representative_from_lines` 또는 `_extract_lone_person_name_row`
  - `receipt_pos` doc_type일 때 business_hint 인접 반경 확장 (±2 → ±3)
  - 사업자번호 행 이후 3-4자 한글 이름 우선 탐색
- `main.py`의 `_extract_fields_from_rows`에서 `receipt_pos` 전화번호 경로 점검

**회귀 guard**:
- a1.jpg 개선 시 1.jpg, 2.jpg, 4.jpg 대표자/전화번호 회귀 확인 필수
- receipt_generalization 17개 no_3/no_4 회귀 확인

### T-25b: Address conservative post-processing

**대상**: 8.jpg no_5, 10.jpg no_5, 3.jpg no_5 (부분), 7.jpg no_5 (부분)

**수정 범위** (`extractors/address.py`의 주소 후처리 단계):

```python
# 규칙 1: 닫는 괄호 후 숫자/한글에 공백 추가
# (오전동)1층 → (오전동) 1층
value = re.sub(r'\)([가-힣0-9])', r') \1', value)

# 규칙 2: 도로명 접미어 직후 번지 숫자에 공백 추가  
# 경수대로237 → 경수대로 237
value = re.sub(r'([로길가대로])\b(\d)', r'\1 \2', value)
```

**회귀 guard**:
- baseline 9개 전체 no_5 주소 회귀 확인
- receipt_generalization 17개 no_5 주소 회귀 확인
- `(오전동)1층` → `(오전동) 1층` 확인
- 다른 주소에서 공백이 이중 삽입되지 않는지 확인

---

## 9. 보류/전처리 후보 — OCR source garbled

### OCR garbled 7건 공통 특성

| 건 | 파일 | 증상 | 근본 원인 | qualityTags 후보 |
|----|------|------|----------|-----------------|
| 1 | 3.jpg no_5 | `경기도`→`경기`, `,`→`.` | OCR 노이즈 | small_text, ocr_noise |
| 2 | 4.jpg no_1 | `정공구`→`가행점` | 가맹점 텍스트 오인식 | - |
| 3 | 7.jpg no_5 | `비젼`→`비전`, 공백 차이 | OCR 맞춤법 노이즈 | - |
| 4 | a1.jpg no_1 | `정공구`→`기계공구` | POS 영수증 구조 | - |
| 5 | a1.jpg no_5 | 주소 없음 | POS 포맷 | - |
| 6 | a2.jpg no_3 | `이정은`→`이정` | 수기 글자 잘림 | handwritten |
| 7 | a2.jpg no_5 | `118` 누락 | 수기 숫자 누락 | handwritten |

**T-25c 방향**: a2.jpg에 `handwritten` qualityTag 부여 + form_or_handwritten 결과에 "인식 한계" warning 추가

---

## 10. 회귀 검증 계획

T-25 작업 완료 후 반드시 검증:

1. **baseline 9개 GT 재검증**
   - no_1~no_6 전 필드 재비교
   - 수정 전 75.93% → 목표: ≥78% (안전 케이스 3건 개선 시 약 3/54 = +5.5%p 가능)
   - 단, GT 이슈(2.jpg no_4)가 수정되면 추가 +1.85%p

2. **TestTab vs RunOCR 9개 일치 검증**
   - Codex T-23 결과 PASS (100% 일치) 유지 확인

3. **receipt_generalization 17개 회귀**
   - no_1~no_6 전체 회귀 없음 확인
   - 특히 no_5 주소 규칙 적용 후 기존 match 케이스 유지 확인

4. **npm run typecheck / npm run build**
   - 프론트엔드 코드 변경 없으므로 skip 가능

5. **주소 규칙 false positive 검증**
   - `)\d`, `)\[가-힣\]` 치환 후 기존 올바른 주소 변형 없는지 확인
   - `[로길가]\d` 치환 후 `호계동555-9` 형식에서 오작동 없는지 확인

---

## 11. 결론

### 11-1. 지금 바로 수정 가능한 범위

**최대 3건 개선 가능** (주소 공백 규칙 2종):
- 규칙 1: `)\d` / `)[가-힣]` → 공백 삽입 → 10.jpg, 3.jpg, 7.jpg 일부 개선
- 규칙 2: `[로길가]\d` → 공백 삽입 → 8.jpg 개선

적용 시 이론적 정확도 향상: 최대 75.93% → 79–81% (회귀 없을 경우)

단, GT 이슈(2.jpg no_4)도 확인 후 수정하면 추가 1건 개선.

### 11-2. 주소 개선을 별도 분리해야 하는 이유

- 주소 false positive 위험: 공백 삽입 규칙이 다른 주소를 깨뜨릴 수 있음
- 5건 중 3건은 OCR raw 자체 문제 (복구 불가)
- 개선 가능한 2건만 보수적 규칙으로 T-25b에서 분리 처리

### 11-3. 다음 작업 추천

| 작업 | 내용 | 우선순위 |
|------|------|---------|
| **T-25a** | POS 영수증 대표자/전화번호 rule 보강 (a1.jpg 개선) | HIGH |
| **T-25b** | 주소 괄호/도로명 후 공백 삽입 (8.jpg, 10.jpg) | HIGH |
| **T-25c** | GT 2.jpg no_4 오입력 확인 후 수정, form_or_handwritten amount policy 검토 | MEDIUM |
| **T-26** | receipt_generalization 17개 동일 기준으로 GT 비교 확장 | MEDIUM |
| **T-27** | a2.jpg handwritten qualityTags + OCR warning UI | LOW |

---

*분석 완료: T-24 / Claude Sonnet 4.6 / 2026-05-19 / 코드 수정 없음*
