# TEST_PROFILE_SCHEMA — Test 탭 기준 profile / 컬럼 / 평가 구조

- 작성일: 2026-04-27
- 범위: **Test 탭 한정** (실제 서비스 UI / DB 구조는 본 문서 범위 밖)
- 목적: `finance_slip`을 더 이상 단순 suppression 대상으로 두지 않고
  Test 탭에서 **profile별로 컬럼 세트 / 평가 기준이 분리되도록** 정책을 동결한다.
- 비범위: OCR 인식 로직 변경, parser 구현, 실제 서비스 화면, DB 스키마.
- 본 문서는 코드 수정 없이 **정책/스키마/UI 분기 방식만 확정**한다.
- 변경 시 베이스라인: `mysuit-ocr/src/components/test/core/finalize.ts`,
  `mysuit-ocr/src/components/test/core/types.ts`,
  `mysuit-ocr/src/lib/testsets.ts`,
  `mysuit-ocr/public/data/testsets/*/manifest.json`.

---

## 접근 계획 (요약)

1. 현재 Test 탭은 `FieldKey`가 영수증 6필드 (회사명 / 사업자번호 / 대표자 / tel / 주소 / 총합계금액) 로 고정.
2. `computeMatchStatus` / `computeStatusPerField` / `scoreEntryAgainstGt` 가 모두 6필드 가정으로 작성됨 → profile 도입 시 분기 지점 명확.
3. profile = "Test에서 어떤 필드들을 평가/렌더할지의 단위". `documentType → profile` 1:1 매핑 (manifest 기준, OCR 동적 변경 금지).
4. `finance_profile`은 Tier-1 4필드 (bankName / transactionType / transactionDateTime / amount) 만 우선 도입.
5. 영수증 컬럼은 finance에서 "—" (해당 없음) 으로 표시하고 KPI 분모에서 제외 → 점수 왜곡 방지.
6. baseline lock 보호: 9.jpg (`suppressed_bank_slip`) 라벨은 lock 문서 변경 없이 **보강 노트**로만 재해석.
7. 코드 변경 전 (a) profile schema 동결, (b) documentType 매핑 동결, (c) GT/manifest 확장 규약 동결의 3단 동결을 마친 후에만 코드 진입.

---

# 1. Test 기준 문서군 분류 최종안

현재 정의된 `DocumentType` 7종을 Test 평가 관점에서 4개 family로 묶는다.

| Family | 포함 documentType | 공유 base profile | overlay |
|---|---|---|---|
| **receipt_family** | `pos_receipt`, `food_cafe_receipt`, `card_receipt`, `medical_receipt` | `receipt_profile` | 항목별로 `card_overlay` / `medical_overlay` |
| **finance_family** | `finance_slip` (= 은행/금융 입출금/이체/ATM 전표 통칭) | `finance_profile` | — |
| **document_family** *(향후 확장)* | `invoice_statement` | `document_profile` (별도 설계) | — |
| **unknown_family** | `unknown` | `none` | — |

원칙:
- `bank_slip`은 **새 documentType으로 추가하지 않는다**. `finance_slip`을 상위 개념으로 유지하고, 세분이 필요하면 manifest의 `notes` 또는 향후 `subType` 필드로만 표현.
- `invoice_statement`는 표·다행·합계산식 구조라 평가 모델이 다르므로 본 문서 범위 밖. profile 슬롯만 예약.
- Test의 family 분류는 **영수증 KPI와 금융 KPI를 절대 같은 분모에 합치지 않기 위한 경계선**이다.

---

# 2. Test 기준 profile 정의

profile은 "Test 탭에서 한 문서를 평가할 때 사용하는 컬럼 세트 + 필수/선택 정의 + KPI 분모 정의"의 단위.

### 2.1 receipt_profile

- 적용 대상: receipt_family 전체 (pos / food_cafe / card / medical)
- 필수 필드 (KPI 분모 포함):
  - `companyName` (회사명)
  - `bizNumber` (사업자번호)
  - `totalAmount` (총합계금액)
- 선택 필드 (KPI 분모 포함, 있을 때만 평가):
  - `representative` (대표자)
  - `phone` (전화번호)
  - `address` (주소)
- 평가 정책: 기존 `computeMatchStatus` (exact / policy / mismatch / no_baseline) 그대로 적용.

### 2.2 finance_profile

- 적용 대상: finance_family (`finance_slip`)
- Tier-1 (필수, KPI 분모 포함):
  - `bankName`
  - `transactionType` (입금 / 출금 / 이체 / ATM)
  - `transactionDateTime`
  - `amount` (거래금액)
- Tier-2 (선택, GT 있을 때만 분모 포함):
  - `balanceAfter`
  - `accountMasked` (저장 시 항상 마스킹된 형태로만 허용)
  - `branchOrChannel`
  - `memo`
- 평가 정책: 기존 4상태 체계 그대로 적용 (8장 참고). `accountMasked`는 마스킹 정책 위반 시 강제 `mismatch`.

### 2.3 card_overlay

- 적용 대상: `card_receipt` (receipt_profile 위에 덧씌움)
- 추가 필드 (전부 선택, 있을 때만 분모 포함):
  - `cardIssuer`
  - `cardNumberMasked` (raw 4자리 이상 노출 금지)
  - `approvalNo`
  - `approvalDateTime`
  - `installment`
- 평가 정책: receipt_profile과 동일. overlay 필드는 별도 KPI 카드 ("카드 overlay 보정률") 로 분리.

### 2.4 medical_overlay

- 적용 대상: `medical_receipt` (receipt_profile 위에 덧씌움)
- 추가 필드 (전부 선택, 1차에서는 평가 분모에 넣지 않음):
  - `patientName` (개인정보 — Test에서는 마스킹 표시만, GT 저장 권장하지 않음)
  - `department`
  - `insuranceType`
- 1차 운영: receipt_profile만 평가하고 overlay 필드는 **표시는 하되 KPI 비반영**.

### 2.5 none

- 적용 대상: `unknown`
- 컬럼: 없음 (문서 정보 영역에 documentType과 사유만 표시)
- 평가 정책: KPI 분모/분자 모두에서 제외. `suppressed` / `unknown` 카운트로만 집계.

---

# 3. documentType → profile 매핑표

원칙: **manifest의 documentType이 profile을 결정한다.** OCR 결과로 profile을 동적 변경하지 않는다.

| documentType | base profile | overlay | KPI 카드 그룹 |
|---|---|---|---|
| `pos_receipt` | receipt_profile | — | 영수증 정확도 |
| `food_cafe_receipt` | receipt_profile | — | 영수증 정확도 |
| `card_receipt` | receipt_profile | card_overlay | 영수증 정확도 + 카드 overlay 보정률 |
| `medical_receipt` | receipt_profile | medical_overlay (표시만) | 영수증 정확도 |
| `finance_slip` | **finance_profile** | — | 금융전표 추출률 |
| `invoice_statement` | document_profile *(예약, 미구현)* | — | 미정 (KPI 미산출) |
| `unknown` | none | — | suppressed / unknown 건수 |

### 3.1 manifest 메타데이터 오류 의심 시 보완 기준

manifest의 documentType은 GT이지만, 사람이 잘못 분류한 경우를 막기 위해 다음을 추가한다.

- Test 탭은 OCR 결과의 휴리스틱 신호 (예: "은행명 키워드 + 거래후잔액 키워드" vs "사업자번호 패턴") 와 manifest profile 이 **명백히 어긋나는 항목을 별도 리스트로 표시**한다 (KPI 변경은 하지 않음, 단순 경고).
- 경고 라벨 예시: `profile_suspected_mismatch` (영수증 profile인데 금융 신호가 우세 등).
- 이 경고는 manifest 수정 트리거이지 profile 자동 변경 트리거가 아니다.
- 경고 발생 시 처리 흐름: 사람이 manifest 수정 → 다음 실행에서 profile 재산출.

---

# 4. receipt_profile 컬럼 세트

현행 `FieldKey` 6종을 그대로 유지하되, 필수/선택을 명확히 한다.

| 컬럼 (논리명) | 현행 FieldKey | 필수/선택 | 비고 |
|---|---|---|---|
| companyName | `회사명` | 필수 | KPI 분모 포함 |
| bizNumber | `사업자번호` | 필수 | autofill 키 |
| totalAmount | `총합계금액` | 필수 | autofill 금지 (`allowAutofill=false`) |
| representative | `대표자` | 선택 (GT 있을 때만 분모) | — |
| phone | `tel` | 선택 (GT 있을 때만 분모) | — |
| address | `주소` | 선택 (GT 있을 때만 분모) | — |

원칙:
- "필수"는 **GT가 비어 있어도 분모에 포함**한다 (영수증인데 회사명을 못 읽으면 감점).
- "선택"은 **GT가 있을 때만 분모에 포함** (현행 `scoreEntryAgainstGt`의 `if (!g) continue;` 동작 유지).
- 본 분기를 곧바로 finalize.ts에 반영하지 않는다. 코드 변경은 11장 우선순위에 따라 별도 단계.

---

# 5. finance_profile 컬럼 세트

### 5.1 Tier-1 (필수, KPI 분모 포함)

| 컬럼 | 의미 | 비고 |
|---|---|---|
| `bankName` | 발행 은행 식별 | family resolver 핵심. ex. KB / 신한 / 우리 / 농협 |
| `transactionType` | 거래유형 | 입금 / 출금 / 이체 / ATM. enum 후보 동결 권장 |
| `transactionDateTime` | 거래일시 | 일자+시각 결합. 영수증의 totalAmount 위치에 해당하는 "전표 의미" 필드 |
| `amount` | 거래금액 | 가장 중요한 숫자. 음/양 구분은 `transactionType`이 담당 |

### 5.2 Tier-2 (선택, GT 있을 때만 분모)

| 컬럼 | 의미 | 비고 |
|---|---|---|
| `balanceAfter` | 거래후잔액 | 민감도 중간 |
| `accountMasked` | 계좌번호(마스킹) | 저장 단계에서 마스킹 강제. raw 형식이면 `mismatch` 처리 |
| `branchOrChannel` | 지점/채널 | "강남지점" / "인터넷뱅킹" / "ATM" / "콜센터" |
| `memo` | 적요/비고 | PII 포함 가능. 길이 제한 + 단순 필터 (전화/주민번호 패턴 차단) |

### 5.3 영수증 필드의 처리 (중요)

`finance_slip`에서는 다음 영수증 필드는 **평가 대상이 아니다**:

- `companyName` (회사명)
- `bizNumber` (사업자번호)
- `representative` (대표자)
- `phone` (전화번호)
- `address` (주소)
- `totalAmount` (영수증 의미의 합계금액 — finance에서는 `amount`로 별도 평가)

처리 규약:
- Test UI: 표시는 하되 셀 값을 `—` (해당 없음) 로 렌더. **`X` (틀림) 로 카운트하지 않는다.**
- KPI: 위 필드는 finance_profile의 분모/분자 어디에도 포함하지 않는다.
- MatchStatus: 새 상태 `not_applicable` 도입 (8장 참조). `no_baseline`과 의미가 다르다 ("정답 없음"이 아니라 "이 profile에는 해당 없음").

### 5.4 1차 베이스 vs SI 단계 구분

- 1차 (공통 데모 베이스): Tier-1 4필드만 추출 시도. Tier-2는 비어 있어도 selected 가능.
- SI 단계 (계약 후 고객 문서 기반): Tier-2 일부를 필수로 격상하는 정책을 고객별 manifest로 오버라이드. (본 문서에서는 슬롯만 예약.)

---

# 6. card_receipt / medical_receipt 위치 판단

### 6.1 card_receipt — receipt_profile + card_overlay (권장)

근거:
- 한국 카드매출전표는 "영수증 + 카드 승인정보" 일체형이 압도적 다수. 가맹점명 / 사업자번호 / 주소가 함께 인쇄됨 → receipt_profile 그대로 적용 가능.
- 카드 단독 항목 (카드사 / 카드번호 마스킹 / 승인번호 / 승인일시) 만 overlay로 추가하면 충분.
- baseline의 1.jpg / 2.jpg / 3.jpg / 4.jpg / 10.jpg / a1.jpg 가 모두 `card_receipt`인데 영수증 KPI 9/10에서 정상 동작하는 것이 근거.

기각:
- **별도 family로 분리** → documentType 폭증 + 영수증 KPI 분모가 깨짐.
- **finance_profile로 보내기** → 카드매출전표는 가맹점 영수증이지 금융전표가 아님. 의미 충돌.

예외 처리:
- "카드사 단독 발급 매출전표 사본" (영수증 정보가 빠진 케이스) → manifest의 `notes: "card_only"` 또는 향후 `subType: "card_slip"` 로 표시.
  - 이때 receipt_profile의 필수 필드 (회사명 / 사업자번호 / 합계) 가 비어 있어도 selected 판정 가능하도록 SI 단계에서 별도 정책. 1차 범위 밖.

### 6.2 medical_receipt — receipt_profile + medical_overlay (1차) / 별도 medical_profile (장기)

#### 1차 (지금 당장 가장 현실적인 구조)

- receipt_profile 그대로 사용. 약국·병원 영수증은 가맹점명·사업자번호·합계 구조가 영수증과 동일.
- medical_overlay 필드 (`patientName` / `department` / `insuranceType`) 는 표시만 하고 KPI 비반영.
- baseline 8.jpg (효성온누리약국) 가 이 구조로 정상 동작 중.

#### 장기 확장 가능성

- 진료비 영수증 (병원) 은 본인부담금 / 공단부담금 / 비급여 등 금융전표와 다른 구조의 금액 계열이 있어, **장기적으로는 별도 `medical_profile`** 신설 가능성 열어둠.
- 단, 본 문서 범위 (1차 베이스) 에서는 receipt_profile + overlay 표시만 채택. medical_profile은 슬롯만 예약.

---

# 7. Test UI 반영 방식

### 7.1 컬럼 헤더 분기

현행: 단일 표 + 6컬럼 고정 헤더.

변경 (Test 탭 한정):
- 현재 이미 documentType 그룹화가 적용되어 있으므로 (`SESSION_SUMMARY.md`의 "1차 UI" 참조), **그룹 안에서 컬럼 헤더 자체를 profile별로 다르게** 렌더한다.
- 하나의 그룹 안에서는 모든 항목이 동일 profile 사용 → 표가 깨지지 않는다.
- 컬럼 표시 우선순위: `필수 (Tier-1) → 선택 (Tier-2)` 순.

| 그룹 | 컬럼 헤더 |
|---|---|
| receipt_family 그룹 | companyName · bizNumber · totalAmount · representative · phone · address |
| receipt_family 그룹 (card overlay 활성 항목 한정) | 위 6열 + card overlay 5열 (옵션 노출 토글) |
| finance_family 그룹 | bankName · transactionType · transactionDateTime · amount · (Tier-2 4열 옵션 노출) |
| unknown 그룹 | (컬럼 없음, 문서 정보 + 처리 사유만) |

### 7.2 Summary KPI 분리

profile별로 KPI 카드를 분리한다. **영수증 점수와 금융전표 점수를 절대 같은 분모에 섞지 않는다.**

| KPI 카드 | 대상 profile | 분자 / 분모 |
|---|---|---|
| 영수증 정확도 | receipt_profile | `selected 건수` / `receipt_family 총건수` |
| 카드 overlay 보정률 | card_overlay 사용 항목 | `overlay 필수 충족 건수` / `card_receipt 총건수` |
| 금융전표 추출률 | finance_profile | `Tier-1 4필드 모두 채워진 건수` / `finance_family 총건수` |
| 미분류 / suppressed | none + suppressed | 단순 건수 (KPI %로 환산하지 않음) |

### 7.3 Profile resolver 단일 진입점

UI / 평가 / 요약 모두 한 함수에서만 profile을 결정한다.

- 위치 (제안): `mysuit-ocr/src/lib/profiles.ts` (신설 예정)
- 시그니처 (개념):
  - `resolveProfile(docType: DocumentType): { base: "receipt" | "finance" | "document" | "none", overlays: Array<"card" | "medical"> }`
- 정책 변경 시 한 군데만 수정.

### 7.4 manifest 없는 케이스

- manifest가 없거나 documentType이 누락된 항목은 **profile=none + 회색 라벨 ("미분류 — manifest 누락")** 로 표시.
- KPI 분모/분자 어디에도 포함하지 않는다.
- 현행 `TestWorkspace`의 manifest non-blocking fetch / fallback 처리 흐름 유지.

---

# 8. O / △ / X / — 유지 방식

기존 매칭 상태 4종 (`exact` / `policy` / `mismatch` / `no_baseline`) 은 그대로 유지하고, **`not_applicable` 한 종을 추가**한다.

### 8.1 상태 정의

| MatchStatus | 표시 | 의미 | KPI 분모 |
|---|---|---|---|
| `exact` | O | 사람이 보기에 똑같음 (필드별 strict 정규화 후 동일) | 포함 |
| `policy` | △ | 정책 경로로 채택 (정규화 / 유사도 / anchor / autofill 등) | 포함 |
| `mismatch` | X | GT와 일치하지 않음 (마스킹 정책 위반 포함) | 포함 |
| `no_baseline` | — | GT 자체가 없음 (선택 필드의 통상 케이스) | 제외 |
| **`not_applicable`** *(신규)* | — | **이 profile에는 해당 없는 필드** (예: finance에서 `companyName`) | **제외** |

### 8.2 표시 규칙

- `no_baseline`과 `not_applicable`은 둘 다 시각적으로는 `—`로 표시한다.
- 단, **tooltip / 색상으로 구분**한다:
  - `no_baseline`: "기준값(GT) 없음 — 평가 보류"
  - `not_applicable`: "이 문서 유형(profile)에서는 해당 없는 필드"
- 사용자가 KPI 0% 원인을 "GT가 없어서"인지 "profile이 다르기 때문"인지 헷갈리지 않게 함.

### 8.3 finance_profile 내 영수증 필드 처리

- finance_profile 항목의 `companyName / bizNumber / representative / phone / address / totalAmount(영수증 의미)` → 항상 `not_applicable`.
- KPI 분모 제외. 색상은 회색 (`—`).

### 8.4 finance_profile Tier-1 필드의 마스킹 위반

- `accountMasked` 가 raw 형태 (예: `123-456-789012`) 로 추출된 경우 → 강제 `mismatch` (X).
- 사유 라벨: `MASKING_POLICY_VIOLATION` (이유 표시 컬럼에 노출).

### 8.5 호환성

- 현행 `computeMatchStatus` 시그니처 (`fieldKey`, `gtValue`, `ocrRawValue`, `ocrNormalizedValue`, `finalValue`, `finalSource`) 그대로 유지.
- 신규 분기는 호출 측 (profile resolver) 에서 `not_applicable` 을 먼저 결정하고, 해당 필드는 `computeMatchStatus`를 호출하지 않는 방식으로 구현 가능. 즉 **기존 함수 시그니처 무변경 가능**.

---

# 9. Test 기준 상태 (selected / review / suppressed / unknown) 정의

### 9.1 정책 문서 기준 (이 문서에서 동결)

| 상태 | 정의 |
|---|---|
| `selected` | profile의 **필수 필드 (receipt 3개 / finance Tier-1 4개) 가 모두 추출** + 신뢰도 정상 |
| `partial` | profile 필수 필드의 **일부만 추출**, 나머지는 정직하게 빈 값 |
| `review` | 추출은 됐으나 ① 마스킹 정책 위반 의심, ② 신뢰도 낮음, ③ profile mismatch 경고, ④ Tier-2 GT 있음에도 큰 불일치 등 |
| `suppressed` | 어떤 profile에도 매칭 불가 (손글씨 / 손상 / 비문서 이미지 등으로 추출 자체 불가) |
| `unknown` | manifest documentType이 `unknown`이거나 문서 식별 자체 미수행 |

원칙 변경:
- **기존 `suppressed_bank_slip` 라벨은 폐지 방향**. `finance_slip`은 더 이상 suppression 사유가 아니다.
- suppression의 의미를 좁힘: "문서군 식별 실패 + 추출 자체 불가" 만 suppression.
- 단 baseline lock 보호 차원에서 9.jpg의 expectedStatus는 lock 문서를 **변경하지 않고**, 별도 "보강 노트" 문서에서 "finance_profile partial로 재해석"으로만 명시 (10장 / 11장 참조).

### 9.2 즉시 구현 기준 (1차 단계 — 단순화)

상태 폭증을 막기 위해 1차 코드 도입은 **3종으로만** 시작한다.

| 즉시 구현 상태 | 정책 문서 매핑 |
|---|---|
| `selected` | 정책의 selected |
| `review` | 정책의 partial + review 통합 |
| `suppressed` | 정책의 suppressed + unknown 통합 |

- `partial`은 정책 문서에는 정의하되, 1차 UI 표시에서는 `review`로 통합 표시.
- 데이터 누적 후 (3차 검증셋 이상 확보 시) `partial`을 분리한다.

---

# 10. GT / manifest 확장 방향

### 10.1 GT 스키마 — 단일 Entry 폐지, profile별 분리

현행: `GtRecord = { fields: Entry; type: string; updated_at: string }` (영수증 6필드 강제).

확장 방향 (제안):
```
GtRecord {
  profile: "receipt" | "finance" | "document" | "none"
  receipt?: { companyName, bizNumber, representative, phone, address, totalAmount }
  finance?: { bankName, transactionType, transactionDateTime, amount,
              balanceAfter?, accountMasked?, branchOrChannel?, memo? }
  cardOverlay?: { cardIssuer, cardNumberMasked, approvalNo, approvalDateTime, installment }
  medicalOverlay?: { patientName?, department, insuranceType }
  type: string
  updated_at: string
}
```

원칙:
- profile에 해당하는 슬롯만 채운다. 다른 profile 슬롯은 `undefined`.
- finance GT의 `accountMasked` / `cardOverlay`의 `cardNumberMasked` 는 **저장 단계에서 마스킹 강제** (raw 입력 시 거부).
- medical_overlay의 `patientName`은 1차에서 GT 저장 권장하지 않음 (개인정보).

### 10.2 manifest — `expectedFields` 추가

manifest 항목별로 **이 항목에서 어떤 필드가 평가 대상인지** 명시 가능하게 한다 (overlay on/off 등).

```
ManifestItem {
  filename, documentType, qualityTags, difficulty, expectedStatus, notes,
  expectedFields?: {
    receipt?: { required: string[], optional: string[] },
    finance?: { tier1: string[], tier2: string[] },
    cardOverlay?: { enabled: boolean, fields: string[] },
    medicalOverlay?: { enabled: boolean, fields: string[] }
  }
}
```

원칙:
- `expectedFields`는 **선택 필드**. 없으면 profile 기본값을 그대로 사용.
- 고객별 / 케이스별로 필수 필드가 달라지는 SI 단계의 슬롯이기도 함.
- baseline / google lock 문서는 변경하지 않는다. 새 manifest 항목에만 사용.

### 10.3 baseline / google lock 호환성

- `9.jpg` (baseline, expectedStatus=`suppressed_bank_slip`) 와 `6.jpg` (google, suppressed_bank_slip) 는 lock 문서를 **수정하지 않는다.**
- 본 문서가 동결되면, 별도 `docs/SUPPRESSION_POLICY_REINTERPRET_20260427.md` 같은 보강 노트를 작성해 "이 두 항목은 finance_profile partial로 재해석되며 KPI는 영수증과 분리 집계"임을 명시.
- manifest는 신규 필드 (`expectedFields`) 만 추가하고, 기존 `expectedStatus`는 그대로 둔다 (lock 보호).

### 10.4 호환성 우선 정책

- 신규 GT 스키마는 **점진적**: 기존 영수증 GT는 `profile="receipt"` + `receipt` 슬롯에만 채워진 상태로 **자동 마이그레이션 가능**. 별도 변환 없이 동작.
- finance 항목이 등장하기 전까지는 GT 파일 구조가 사실상 무변경.

---

# 11. 구현 우선순위

코드 수정 전 동결할 것을 위에서부터 순서대로.

| # | 항목 | 산출물 | 코드 변경 |
|---|---|---|---|
| 1 | **본 문서 (`TEST_PROFILE_SCHEMA`) 동결** | 본 문서 | 없음 |
| 2 | documentType → profile 매핑 동결 | 본 문서 §3 | 없음 |
| 3 | finance_profile Tier-1 / Tier-2 동결 | 본 문서 §5 | 없음 |
| 4 | GT / manifest 확장 규약 동결 | 본 문서 §10 | 없음 |
| 5 | suppression 정책 재해석 보강 노트 | 별도 문서 (`SUPPRESSION_POLICY_REINTERPRET_*.md`) | 없음, 단 lock 문서는 무수정 |
| 6 | profile resolver 단일 진입점 추가 | `src/lib/profiles.ts` (신설) | 코드 (read-only 함수만) |
| 7 | Test UI 컬럼 헤더 profile 분기 | `TestWorkspace.tsx` 등 | 코드 (UI만) |
| 8 | KPI Summary profile별 분리 | TestWorkspace KPI 영역 | 코드 (UI만) |
| 9 | `not_applicable` 상태 도입 | `finalize.ts` 호출부 변경 (signature 무변경) | 코드 |
| 10 | finance GT 슬롯 추가 (선택 필드만 우선) | `core/types.ts`, `GtRecord` | 코드 |
| 11 | manifest `expectedFields` 옵션 도입 | `lib/testsets.ts` ManifestItem | 코드 |
| 12 | finance parser 최소 목표 동결 (별도 문서) | `docs/FINANCE_PARSER_TARGET_*.md` | 없음 |
| 13 | finance parser 1차 (Tier-1만) | `ocr-server/extractors/...` | 코드, 회귀 baseline/google 영수증 무영향 검증 필수 |

**1~5까지가 본 단계의 범위.** 6 이후는 별도 stage에서 진행.

---

# 12. 절대 하면 안 되는 설계

| 금기 | 이유 |
|---|---|
| `finance_slip`을 영수증 컬럼 (회사명·사업자번호·주소) 으로 평가 | 분모 왜곡 + KPI 의미 상실. 본 문서가 해결하려는 핵심 문제 |
| `finance_slip`에 영수증 필드를 `X` (mismatch) 로 카운트 | "해당 없음" 과 "오추출"이 섞이면 KPI 신뢰도 0 |
| `not_applicable` 과 `no_baseline`을 같은 의미로 처리 | 사용자가 KPI 원인 분석 불가. 둘은 의미가 다름 |
| profile을 OCR 결과 기반으로 **동적으로 변경** | 같은 파일이 실행마다 다른 profile로 평가되면 회귀 검증 불가. profile은 manifest의 documentType으로 결정 |
| `card_receipt`를 성급하게 완전 별도 family로 분리 | 데모 단계 빈도 대비 KPI 분기·UI 컬럼이 과도하게 복잡. overlay로 충분 |
| `bank_slip`을 새 documentType으로 추가 | DocumentType 폭증. `finance_slip` 단일 + subType / notes로 충분 |
| GT에 raw 계좌번호 / raw 카드번호 저장 | 마스킹 정책 위반. 저장 단계에서 강제 마스킹 |
| medical_overlay의 `patientName`을 기본 GT 저장 대상으로 사용 | 개인정보. 1차에서는 표시만, GT 저장 권장하지 않음 |
| baseline / google lock 문서를 직접 수정해 9.jpg / 6.jpg 라벨을 finance partial로 변경 | lock 보호 위반. 보강 노트 + manifest 보강만 허용 |
| suppression 건수를 KPI 정상 분자에 포함 | 영수증 점수 분모/분자 모두 왜곡. suppressed는 별도 KPI |
| 단일 `Entry` 타입에 finance 필드를 끼워 넣어 영수증 schema와 통합 | 곧 medical/invoice가 들어오면 무한 확장됨. profile별 schema 분리가 정답 |
| parser를 먼저 만들고 schema는 나중에 정하기 | Entry/Profile이 바뀌면 parser 출력도 전부 다시 짜야 함. §11의 1~5가 먼저 |
| 단일 KPI에 영수증 + 금융전표 + 카드 overlay를 모두 합산 | 의미 다른 분모를 합치는 가장 위험한 설계. 별도 카드로 분리 필수 |

---

# 부록 A — 현행 코드 영향 지점

본 문서가 동결된 후 코드 단계에서 손대는 지점.

| 영역 | 파일 | 변경 성격 |
|---|---|---|
| profile resolver | `src/lib/profiles.ts` (신설) | 신규 |
| documentType / profile 타입 | `src/lib/testsets.ts` | 타입 추가 (`Profile`, overlays) |
| FieldKey / Entry | `src/components/test/core/types.ts` | profile별 슬롯 분리, 기존 `FieldKey`는 receipt profile 전용으로 의미 한정 |
| MatchStatus | `src/components/test/core/finalize.ts` | `not_applicable` 분기는 호출 측에서 처리, 함수 시그니처 무변경 가능 |
| KPI Summary | `src/components/test/TestWorkspace.tsx` | profile별 카드 분리 |
| manifest | `public/data/testsets/*/manifest.json` | `expectedFields` 옵션 추가 (lock 보호 항목 무수정) |
| ocr-server parser | `ocr-server/extractors/*` | finance Tier-1 추출 로직 (별도 stage) |

# 부록 B — 회귀 안전 가드

코드 변경 단계 진입 시 다음 회귀 가드 통과를 의무화한다.

- baseline (영수증 9/10) 점수 변동 0
- google (영수증 10/11) 점수 변동 0
- baseline `9.jpg` / google `6.jpg` 의 expectedStatus 매핑이 lock 문서와 충돌하지 않음 (lock 문서 무수정)
- `npm run typecheck` 통과
- `npm run build` 통과
- 기존 dataset 전환 / qualityTags filter / Run All 무영향
