# FINANCE_PARSER_TARGET — Test 기준 finance parser 1차 구현 목표

- 작성일: 2026-04-27
- 상위 문서:
  - [TEST_PROFILE_SCHEMA_20260427.md](TEST_PROFILE_SCHEMA_20260427.md)
  - [TEST_SUPPRESSION_POLICY_NOTE_20260427.md](TEST_SUPPRESSION_POLICY_NOTE_20260427.md)
- 범위: **Test 탭 한정** finance_slip 1차 parser 목표 동결. 코드 수정 없음.
- 비범위: full banking parser, 송수금인 정교 추출, 수수료/통화/거래번호, 거래명세서, 실 서비스 UI/DB.
- 변경 시 베이스라인: `ocr-server/main.py`, `ocr-server/document_classifier.py`,
  `ocr-server/signal_lists.py` (`BANK_STRUCT_SIGNALS` / `BANK_BRAND_SIGNALS` 이미 존재),
  `ocr-server/extractors/{business_number,phone,representative,common}.py` (영수증 extractor 패턴 참고).

명칭 노트:
- 코드(`main.py`, `document_classifier.py`)는 doc_type 키로 `bank_slip`을 사용.
- manifest / 본 문서 계열은 `finance_slip`을 사용.
- 본 문서에서 "finance_slip"은 manifest documentType, "bank_slip"은 코드 doc_type 키를 가리킨다. 두 명칭은 본 단계에서 통합하지 않는다 (호환성 보존).

---

## 접근 계획 (요약)

1. 영수증 amount 보수 정책(`_apply_doc_type_amount_policy`)은 그대로 두고, **finance Tier-1 4필드는 별도 슬롯**에서 새 parser가 채우는 구조로 한다.
2. Tier-1 4필드(bankName / transactionType / transactionDateTime / amount)만 1차 목표. Tier-2는 추출되면 보조 저장, 없어도 selected 판정에 영향 없음.
3. 분류기 단계에서 doc_type=`bank_slip`이 결정된 경우에만 finance parser가 동작. profile 결정은 Test 탭 manifest 기준이지만, parser 발동 조건은 코드 doc_type 기반 — 분리 유지.
4. anchor 규칙은 `signal_lists.py`의 `BANK_STRUCT_SIGNALS` / `BANK_BRAND_SIGNALS`를 1차 사용. 신규 정규식은 추가하되 OCR 노이즈 변형(예: `거래후진액`)은 라이브러리에 흡수.
5. 마스킹 정책은 **추출 단계에서 강제**. raw 계좌/카드번호가 검출되면 슬롯을 `accountMasked`로 마스킹 변환하거나, 변환 불가 시 슬롯을 비우고 review 사유를 남김. GT 저장은 마스킹된 형식만 허용.
6. 회귀 안전: 영수증 KPI 분모/분자 변동 0, baseline `9.jpg` / google `6.jpg` 의 lock 문자열 보존(`suppressed_bank_slip` 그대로 반환), Test 탭 표시 매핑만 새 정책으로 분기.
7. 1차 구현은 "Tier-1 4필드 + review 사유 5종 + 마스킹 위반 차단"까지. 수수료/통화/거래번호/송수금인은 비범위.

---

# 1. finance parser 1차 목표

## 1.1 목표

이번 단계 **유일한 목표**: doc_type=`bank_slip`(또는 manifest documentType=`finance_slip`)으로 분류된 문서에서 **Tier-1 4필드를 최소 추출**한다.

- `bankName`
- `transactionType`
- `transactionDateTime`
- `amount` (거래금액 — **영수증 의미의 총합계금액이 아님**)

## 1.2 비목표 (명시)

- "금융전표를 영수증처럼 완전 추출"하는 것은 **목표가 아니다.**
- 송금인 / 수금인 정교 추출, 수수료, 통화, 거래번호, 단말기 ID, 처리은행 분리 등은 **본 단계 비범위**.
- Tier-2 4필드(`balanceAfter`, `accountMasked`, `branchOrChannel`, `memo`)는 **추출되면 보조 저장**, 없어도 `selected` 판정에 직접 영향 없음.
- finance parser가 영수증 amount를 보정하거나 영수증 합계 정책을 대체하지 않는다 (§5).

## 1.3 영수증 parser와의 분리 원칙

- 영수증 extractor(`business_number`, `phone`, `representative`, `address`, `company` 등)는 finance에서 **호출하지 않는다.**
- 반대로 finance parser는 영수증 결과 슬롯(`receipt_fields`)에 값을 쓰지 않는다.
- 두 parser가 동시에 같은 OCR 결과에 접근하더라도, **출력 슬롯은 완전히 분리** (응답 빌더 단계에서 profile별로 격리).

---

# 2. Tier-1 필드별 추출 목표

각 필드는 다음 표 형식으로 정의한다.

## 2.1 `bankName`

| 항목 | 내용 |
|---|---|
| 의미 | 발행 은행 식별. 카드 브랜드 / 가맹점명과 구분 가능한 정식 은행명. |
| 최소 허용 추출 | OCR raw에 명시된 정식 은행명 토큰 (예: "국민은행", "신한은행"). 단독 한글 약어 ("국민", "농협") 는 **불충분 — 채택 금지**. |
| OCR 노이즈 허용 범위 | `signal_lists.BANK_BRAND_SIGNALS`의 패턴 + 도메인 형태 (`kbstar.com`, `ibk.co.kr` 등). 변형 1~2자 노이즈는 흡수하지 않는다 (오추출 위험). |
| 대표 anchor text | "기업은행", "국민은행", "신한은행", "우리은행", "하나은행", "농협은행", "KB국민은행", "NH농협은행", "i-ONE Bank", `kbstar.co.kr` |
| 우선순위 후보 규칙 | (1) `*은행` 접미 토큰 > (2) 공식 도메인 토큰 > (3) `KB`, `NH`, `KEB`, `IBK` 같은 ISO/약어 prefix가 `*은행`/`Bank`와 연결된 경우. 단독 약어는 review 후보. |
| review로 보낼 경우 | ① 단독 한글 약어만 검출, ② 카드 브랜드(농협카드 등)와 동음 충돌 가드 발동, ③ 두 개 이상의 은행명이 동시 검출되어 단일화 불가, ④ 신뢰도 점수 임계 미달. |

## 2.2 `transactionType`

| 항목 | 내용 |
|---|---|
| 의미 | 거래 종류. enum 값. |
| 1차 enum | `deposit` (입금) / `withdraw` (출금) / `transfer` (이체) / `atm_cash` (ATM 현금) / `unknown` |
| 최소 허용 추출 | 한국어 표면형 또는 그 노이즈 변형이 `BANK_STRUCT_SIGNALS`의 입출금/이체 패턴과 매칭되었을 때 enum으로 사상. 표면형이 enum과 1:1 매칭이 명확할 때만 채택. |
| OCR 노이즈 허용 범위 | `입\s*출\s*금`, `예금\s*입금`, `예금\s*출금`, `타행이체`, `자동이체` 등 기존 패턴. 단어 경계는 한국어 어미 접속 때문에 사용 금지 (기존 정책 준수). |
| 대표 anchor text | "입금", "출금", "이체", "타행이체", "자동이체", "현금자동입출금", "ATM" |
| 우선순위 후보 규칙 | (1) 거래내역 영역 헤더에 명시된 토큰 > (2) 라벨 직후 값 토큰 > (3) ATM/자동화기기 컨텍스트로부터의 추론. 라벨 외 본문에서 산발적으로 발견된 입출금 토큰은 가산 점수 낮춤. |
| review로 보낼 경우 | ① enum과 매칭되지 않는 토큰만 검출 → `unknown`으로 두고 review, ② 입금·출금이 동시에 강하게 검출, ③ ATM 컨텍스트만 있고 거래방향 불명. |

## 2.3 `transactionDateTime`

| 항목 | 내용 |
|---|---|
| 의미 | 거래 일자 + 시각 결합. 영수증 totalAmount 위치에 해당하는 "전표 의미" 필드. |
| 1차 출력 형식 | `YYYY-MM-DD HH:MM` (ISO 분 단위). 초까지 잡히면 `YYYY-MM-DD HH:MM:SS`도 허용. 날짜만 잡히면 `YYYY-MM-DD` (시각 결손 표시는 §4 참조). |
| 최소 허용 추출 | "거래일시" / "거래일자" anchor 라벨 직후 토큰. 라벨 없이 단독 날짜만 있을 때는 가산 점수 낮춤. |
| OCR 노이즈 허용 범위 | 구분자 변형 (`.`, `/`, `-`, 공백) 흡수. 한자 연도 표시(`2026年`)는 1차 비지원 (review). 두 자리 연도(`26-04-27`)는 1차 비지원 (review). |
| 대표 anchor text | "거래일시", "거래일자", "처리일시", "이체일시", "처리시간", `요청일시` |
| 우선순위 후보 규칙 | (1) 라벨 직후 동일행/다음행 토큰 > (2) 헤더 영역 첫 일시 토큰 > (3) 본문 산발 일시. 둘 이상이면 라벨이 가장 강한 것 채택. |
| review로 보낼 경우 | ① 시각 결손 (날짜만), ② 한자/두자리 연도, ③ 두 개 이상의 후보가 30분 이상 차이로 충돌, ④ 미래 날짜 (오늘 날짜 +1일 초과). |

## 2.4 `amount`

| 항목 | 내용 |
|---|---|
| 의미 | 거래금액. **영수증 totalAmount 와 다른 슬롯**. (§5) |
| 최소 허용 추출 | "거래금액" / "이체금액" / "입금액" / "출금액" / "요청금액" anchor 라벨 직후 숫자 토큰. raw 숫자는 콤마/공백 흡수, "원"/"₩" suffix 허용. |
| OCR 노이즈 허용 범위 | 콤마 누락(`105600`)·공백 삽입(`105 600`)은 흡수. 자릿수 절단(`,560`)·접합(`10560 105600`)은 review. |
| 대표 anchor text | "거래금액", "이체금액", "입금액", "출금액", "송금액", "요청금액", "거래내역금액" |
| 우선순위 후보 규칙 | (1) 거래방향(`transactionType`)과 일치하는 anchor 라벨 우선, (2) 동일행 토큰 > 다음행 토큰, (3) `balanceAfter` / 수수료 라벨 직후 숫자는 **거래금액 후보에서 제외** (가장 흔한 오채택 원인), (4) 후보 둘 이상이면 anchor 강도 점수 합으로 단일화. |
| review로 보낼 경우 | ① anchor 라벨 없는 단독 숫자만 검출, ② 거래후잔액/수수료 후보와 본 후보의 점수 차가 임계 미만, ③ 자릿수 절단/접합 의심, ④ `transactionType`과 부호/의미 충돌 (예: `withdraw`인데 양수 amount만 있고 명시 부호 없음 — 1차에서는 review로). |

---

# 3. Tier-2 처리 방침

전 4필드 모두 **추출되면 보조값으로 저장 / 없어도 `selected` 판정에 직접 영향 없음**. 단 마스킹 정책은 강제.

| 필드 | 1차 처리 | review 트리거 |
|---|---|---|
| `balanceAfter` | "거래후잔액" / "잔액조회" anchor 라벨 직후 숫자만 채택. 라벨 없는 숫자는 채택 금지. | GT 존재하면서 큰 자릿수 차이로 mismatch. |
| `accountMasked` | 추출 단계에서 **마스킹 변환을 강제**. raw 계좌 패턴이 검출되면 패턴 자체를 마스킹 형식 (예: `***-***-789`)으로 변환해서 저장. 변환 불가 시 슬롯 비우고 review 사유 부여 (§6). | raw 계좌 의심, 마스킹 변환 실패. |
| `branchOrChannel` | 지점명("강남지점", "역삼동지점") / 채널명("인터넷뱅킹", "ATM", "자동화기기", "콜센터") 토큰 단순 채택. 단어 매칭 우선. | 두 종류 (지점 + 채널) 동시 강하게 검출. |
| `memo` | "적요" / "메모" / "비고" anchor 직후 토큰. 길이 상한 (예: 64자) 적용. PII 패턴(전화/주민) 단순 필터로 차단. | PII 패턴 통과 검출, 길이 상한 초과. |

원칙:
- Tier-2는 **추출되지 않아도 selected**.
- Tier-2 추출 결과가 마스킹/PII 정책을 위반하면 **전체 문서를 review로 강제**한다 (§4 / §6).
- Tier-2 GT는 본 단계에서 manifest에 추가하지 않는다 (선택 슬롯만 예약).

---

# 4. selected / review / suppressed / unknown 기준

상위 문서 [TEST_SUPPRESSION_POLICY_NOTE §3](TEST_SUPPRESSION_POLICY_NOTE_20260427.md)와 정합하게 정의. 본 문서에서는 finance_slip 한정으로 구체화.

## 4.1 selected (정책 / 1차 동일)

다음을 **모두** 만족:

- Tier-1 4필드 모두 추출 (날짜만 + 시각 결손은 selected가 아님 — review).
- 마스킹 / PII 정책 위반 없음.
- `transactionType`이 enum (`deposit` / `withdraw` / `transfer` / `atm_cash`) 중 하나로 결정.
- amount가 거래후잔액/수수료 anchor 후보와 명확히 분리됨 (점수 차 임계 이상).

## 4.2 review

### 정책 문서 기준 (5종 사유)

| 사유 코드 | 발동 조건 |
|---|---|
| `TIER1_PARTIAL` | Tier-1 1~3개만 추출 |
| `AMOUNT_AMBIGUOUS` | bankName 있음 + amount 후보가 잔액/수수료 후보와 점수차 임계 미만 |
| `DATETIME_FORMAT_UNSTABLE` | 시각 결손, 한자 연도, 두자리 연도, 미래 날짜 |
| `MASKING_POLICY_VIOLATION_ACCOUNT` | raw 계좌 의심 또는 마스킹 변환 실패 (§6) |
| `PROFILE_SUSPECTED_MISMATCH` | manifest=`finance_slip`인데 OCR 신호가 영수증 우세 (또는 그 반대) |

### 1차 구현 기준

- 정책 5종 그대로 즉시 구현. 사유 코드는 응답에 함께 실어 Test UI에서 노출.
- partial을 별도 상태로 분리하지 않음 (상위 문서 §3.2).

## 4.3 suppressed

다음 중 하나라도 만족:

- doc_type 분류기가 `bank_slip` 외(예: `unknown`, `form_or_handwritten`)로 결정했고, manifest documentType도 `finance_slip`이 아니거나 OCR raw 텍스트가 사실상 비어 있음.
- qualityTags=`handwritten` + Tier-1 0개 추출.
- 손상/스캔 실패로 OCR 의미 토큰 0.

## 4.4 unknown

- manifest documentType = `unknown` 이거나 분류기 결과 = `unknown` 이며 finance 신호 우세 아님.
- 본 단계 1차 구현에서는 `suppressed`와 통합 표시 (상위 문서 §3.2). 카운트는 별도 컬럼.

## 4.5 lock 보존 매핑 (요약)

| 코드 status (lock 문자열) | 1차 상태 | KPI 분류 |
|---|---|---|
| `selected` | `selected` | finance_profile selected |
| `suppressed_bank_slip` | **`review`** (단, OCR raw도 비면 `suppressed`) | finance_profile review (영수증 KPI 미산입) |
| `suppressed_handwritten` | `suppressed` | suppressed/unknown |
| `suppressed_unknown_bare` | `suppressed` | suppressed/unknown |

자세한 매핑 출처: [TEST_SUPPRESSION_POLICY_NOTE §6.2](TEST_SUPPRESSION_POLICY_NOTE_20260427.md).

---

# 5. amount 처리 원칙

매우 중요. 본 절을 위반하면 KPI가 즉시 왜곡된다.

## 5.1 슬롯 분리

- 영수증 `totalAmount`와 finance `amount`는 **완전히 다른 슬롯**.
- finance `amount`는 거래금액 의미(이체액 / 입금액 / 출금액). **총합계금액 의미가 아니다.**
- 같은 응답 객체 안에서 두 슬롯을 같은 키 (`total_amount` 등) 로 병합하지 않는다.

## 5.2 영수증 amount 보수 정책 보존

- `ocr-server/main.py`의 `_apply_doc_type_amount_policy`는 본 단계에서 **수정하지 않는다.**
- doc_type=`bank_slip`일 때 `amount_value`를 비우고 status를 `suppressed_bank_slip`으로 덮는 기존 동작은 **유지**.
- 새 finance parser는 영수증 `amount_value` 슬롯과 **별개의 finance amount 슬롯**에 결과를 쓴다.
- 이 분리로 lock 문서의 `suppressed_bank_slip` 문자열이 그대로 반환되며 회귀 안전이 보장된다.

## 5.3 거래후잔액 / 수수료 충돌 가드

- finance `amount` 후보 채택 시, 동일 OCR 영역에서 `balanceAfter` / 수수료 anchor 후보가 검출되면 **점수 차 임계 이상**일 때만 selected. 미만이면 review (`AMOUNT_AMBIGUOUS`).
- 본 가드는 영수증 amount 정책의 "score >= 40" 임계와 별개로, finance 자체 임계를 둔다 (구체 수치는 구현 시점에 동결).

## 5.4 통화 / 부호

- 1차에서 통화는 KRW 가정. `₩` / `원` suffix는 흡수, 다른 통화 기호는 review.
- 부호는 `transactionType`이 결정. amount 슬롯에 음수 표기는 저장하지 않는다 (양수 + transactionType 조합).

## 5.5 응답 스키마(개념, 코드 변경 없음)

```
finance_fields: {
  bankName: string | "",
  transactionType: "deposit" | "withdraw" | "transfer" | "atm_cash" | "unknown",
  transactionDateTime: string | "",
  amount: string | "",
  // tier-2 (optional)
  balanceAfter?: string | "",
  accountMasked?: string | "",
  branchOrChannel?: string | "",
  memo?: string | "",
  reviewReasons: ReviewReasonCode[]
}
```

- 영수증 응답 (`receipt_fields`) 와 **분리**. 둘이 동시에 채워지는 일은 정상 케이스에 없다.
- `reviewReasons`는 §4.2의 사유 코드 배열.

---

# 6. 마스킹 정책

## 6.1 raw 계좌번호 / 카드번호 저장 금지

- raw 계좌번호 (10자리 이상 연속 숫자, 또는 은행 표준 마스킹 미적용 형식) 는 **저장하지 않는다.**
- 추출 단계에서 raw 패턴이 검출되면 다음 순서로 처리:
  1. 마스킹 변환 시도 (예: 끝 3자리만 노출, 나머지는 `*`).
  2. 변환 성공 → `accountMasked`에 저장.
  3. 변환 실패 (포맷 식별 불가, 자릿수 비정상) → 슬롯 비우고 review 사유 `MASKING_POLICY_VIOLATION_ACCOUNT` 부여.

## 6.2 마스킹된 값만 허용

- `accountMasked` 슬롯에는 **이미 마스킹된 형식만 허용**. (예: `123-***-****-789`, `***-***-789`)
- 응답/GT 어디에도 raw 형식의 계좌번호가 들어가서는 안 된다.
- 카드 overlay의 `cardNumberMasked`도 동일 정책 (1차 비범위지만 슬롯 정의 시 일관성 유지).

## 6.3 GT 저장 정책

- ground_truth.json 에 **raw 전체값 저장 금지**.
- 사람이 GT로 raw를 입력해도 저장 단계에서 마스킹 변환을 강제하거나 거부.
- 마스킹 강제 책임은 GT 저장 API / Test UI 입력 단계 (본 단계 비범위, 슬롯 도입 시 함께).

## 6.4 PII

- `memo` 슬롯에 전화/주민번호 패턴이 통과하면 review (`PII_LEAK_MEMO`). 1차 단순 정규식 필터.
- `branchOrChannel`에 사람 이름 패턴은 1차에서 검사하지 않음 (false positive 위험).
- 이름/계좌주는 1차 추출 대상 자체가 아니다 (Tier-1/Tier-2 모두 미포함).

## 6.5 마스킹 위반 시 selected 금지

- 마스킹 정책 위반 의심이 하나라도 발생하면 **selected 판정 불가**, 강제 review.
- raw 노출이 lock된 채로 selected가 되는 일은 발생해서는 안 된다.

---

# 7. 과적합 금지 기준

## 7.1 하드코딩 금지

| 금지 | 대안 |
|---|---|
| 특정 은행명 한 두 개에만 동작하는 분기 | `BANK_BRAND_SIGNALS` 라이브러리 확장 + 동음이의 가드 패턴화 |
| 특정 ATM/창구 슬립 픽셀 좌표 / 행 인덱스 고정 | `BANK_STRUCT_SIGNALS` anchor 기반 row 추출 (현행 영수증 extractor의 row 파이프라인 패턴 준수) |
| 특정 baseline / google 샘플 (9.jpg, 6.jpg) 전용 예외처리 | 동일 패턴이 다른 샘플에서도 등장하는지 확인 후 일반 anchor에 흡수 |
| 특정 파일명 분기 | 절대 금지. 파일명은 parser 입력에 영향을 주지 않는다 |
| lock 문서 수치에 맞춘 후추 튜닝 | lock은 회귀 안전 기준이지 튜닝 타겟이 아님 |

## 7.2 OCR 노이즈 흡수 범위 제한

- 1~2자 변형 (`거래후잔액` ↔ `거래후진액`) 같이 이미 라이브러리에 있는 변형만 흡수.
- 임의의 5자 이상 노이즈를 강제로 매칭하지 않는다 (오추출 위험).

## 7.3 분류기 결과 우선

- finance parser는 **분류기가 `bank_slip`으로 결정한 경우에만** 동작. 분류기를 우회해 OCR 결과 단독으로 finance를 켜지 않는다.
- 동시에, manifest documentType=`finance_slip`인데 분류기가 `bank_slip`이 아닌 경우 → review 사유 `PROFILE_SUSPECTED_MISMATCH`만 부여하고 parser 발동은 하지 않음 (분류기 신뢰).

## 7.4 일반화 가능성 검증

- 새 정규식/패턴 추가 시 두 가지 검증 필수:
  1. baseline `9.jpg` / google `6.jpg` 만이 아니라 향후 추가될 finance 샘플 (3장 이상) 에서도 매칭 동작.
  2. 영수증 baseline / google에서 false positive 0 (영수증을 finance로 오판하지 않음).

---

# 8. 회귀 검증 기준

## 8.1 영수증 KPI 무영향

- baseline 영수증 lock 수치 (43/57, 52/57, biz 9/9, amount 8/10) **변동 0**.
- google 영수증 lock 수치 (selected 10, suppression 1) **변동 0**.
- 영수증 KPI 분모/분자 모두 변하지 않아야 함.

## 8.2 lock 문자열 보존

- baseline `9.jpg` / google `6.jpg` 의 응답 status 문자열은 `suppressed_bank_slip` **그대로 반환**.
- 변경 가능한 것은 **Test 탭의 표시 매핑** (lock 문자열 → 1차 상태 = `review`)뿐.
- baseline `a2.jpg` 의 `suppressed_handwritten` 보존.

## 8.3 finance KPI는 별도 비교

- finance KPI는 **영수증 KPI와 합산 비교 금지**.
- 1차 측정 항목:
  - finance Tier-1 4필드 추출률 (분모: finance_family 총건수, 분자: 4필드 모두 추출 건수).
  - review 카운트 (사유별 breakdown).
  - 마스킹 정책 위반 검출 건수.

## 8.4 Test UI profile 분리 전/후 비교

- profile 분리 전 KPI = "lock 시점 정책 (영수증 6필드 강제, finance_slip은 suppression)".
- profile 분리 후 KPI = "새 정책 (profile 분리, finance_slip은 finance KPI)".
- 두 컬럼 병기, 단순 합산 비교 금지 (상위 문서 §7.5).

## 8.5 통과해야 할 검증 게이트

코드 단계 진입 시:

1. `python -m pytest` (있다면) / 회귀 검증 스크립트 통과.
2. baseline 데이터셋 KPI 변동 0.
3. google 데이터셋 KPI 변동 0.
4. baseline_fast / google_fast 빠른 회귀 통과.
5. `npm run typecheck` / `npm run build` 통과 (Test UI 변경이 동반될 경우).
6. dataset 전환 / qualityTags filter / Run All 무영향.

---

# 9. 구현 범위 / 비범위

## 9.1 구현 범위 (1차)

- finance Tier-1 4필드 추출 (§2).
- review 사유 5종 정의 + 응답에 `reviewReasons` 배열로 노출 (§4).
- 마스킹 정책 최소 반영: raw 계좌 검출 → 마스킹 변환 또는 슬롯 비움 + review (§6).
- 분류기 doc_type=`bank_slip`일 때만 parser 발동 (§7.3).
- finance 응답 슬롯 분리 (`finance_fields`, §5.5). 영수증 응답과 격리.
- `BANK_STRUCT_SIGNALS` / `BANK_BRAND_SIGNALS`에 필요한 변형 추가 (안전 범위 내, §7.2).

## 9.2 비범위 (1차)

- full banking parser (송금인 / 수금인 / 수수료 / 통화 / 거래번호 / 단말기 ID / 처리은행 분리).
- balanceAfter / branchOrChannel / memo의 정교 보정 (1차는 단순 anchor 채택만).
- card overlay 필드 추출 (별도 단계).
- medical overlay 필드 추출 (별도 단계).
- `invoice_statement` / document_family parser.
- 거래명세서 표 파싱.
- 실제 서비스 UI / DB 반영.
- ground_truth 저장 시 마스킹 강제 입력 단계 (별도 단계, 6.3 슬롯 정의만 본 문서 범위).
- `_apply_doc_type_amount_policy` 로직 변경 (§5.2 보존).
- `suppressed_bank_slip` 코드 문자열 제거 (단계적 폐지, 본 단계 무수정).
- partial 상태 분리 (상위 문서 §3.3 트리거 충족 후).
- main.py R2-d 이후 리팩토링 (별도 트랙).

## 9.3 단계별 진입 게이트

| 게이트 | 다음 단계 진입 조건 |
|---|---|
| 본 문서 동결 | 본 문서 1~9절 합의 완료 |
| 코드 단계 진입 | 본 문서 + 상위 두 문서가 모두 동결, 회귀 검증 인프라 준비 |
| Tier-2 정교 추출 진입 | finance 샘플 10건 이상 확보, Tier-1 추출률 임계 달성 |
| `suppressed_bank_slip` 코드 문자열 제거 | finance parser 안정화 + 다음 lock 회차 시점 |
| card overlay / medical_profile / document_family | 별도 stage. 본 문서 범위 밖 |

---

# 부록 A — 코드 단계 진입 시 영향 지점 (참조용, 본 단계에서는 변경 없음)

| 영역 | 파일 | 변경 성격 | 주의 |
|---|---|---|---|
| finance extractor (신설) | `ocr-server/extractors/finance_slip.py` (예정) | 신규 | 영수증 extractor 패턴 (`business_number.py` / `phone.py`) 참고, row 파이프라인 재사용 |
| signal_lists 보강 | `ocr-server/signal_lists.py` | 패턴 추가 | OCR 노이즈 흡수 범위 제한 (§7.2) |
| 응답 빌더 | `ocr-server/main.py` 응답 조립부 | 슬롯 추가 | `finance_fields` 슬롯 신설, 기존 `receipt_fields`와 격리 |
| 영수증 amount 보수 | `ocr-server/main.py` `_apply_doc_type_amount_policy` | **본 단계 무수정** | `suppressed_bank_slip` 문자열 보존 |
| Test 응답 타입 | `mysuit-ocr/src/components/test/core/types.ts` | 타입 추가 | `OcrResponse`에 `finance_fields` 옵션 추가 |
| Test 표시 매핑 | `mysuit-ocr/src/components/test/TestWorkspace.tsx` | UI만 | lock 문자열 → 1차 상태 매핑 분기 |
| profile resolver | `mysuit-ocr/src/lib/profiles.ts` (신설) | 신규 | manifest documentType 기준 결정 |

# 부록 B — 회귀 안전 가드 체크리스트

- [ ] baseline 영수증 KPI 분모/분자 변동 0
- [ ] google 영수증 KPI 분모/분자 변동 0
- [ ] baseline `9.jpg` / google `6.jpg` 응답 status 문자열 = `suppressed_bank_slip`
- [ ] baseline `a2.jpg` 응답 status 문자열 = `suppressed_handwritten`
- [ ] `_apply_doc_type_amount_policy` 무수정
- [ ] finance Tier-1 추출률 별도 KPI로만 비교 (영수증 KPI와 미합산)
- [ ] raw 계좌/카드번호 응답/GT 어디에도 노출 없음
- [ ] `npm run typecheck` 통과
- [ ] `npm run build` 통과
- [ ] dataset 전환 / qualityTags filter / Run All 무영향
