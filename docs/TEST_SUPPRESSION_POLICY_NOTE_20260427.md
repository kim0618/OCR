# TEST_SUPPRESSION_POLICY_NOTE — Test 기준 suppression 정책 보강 노트

- 작성일: 2026-04-27
- 상위 문서: [TEST_PROFILE_SCHEMA_20260427.md](TEST_PROFILE_SCHEMA_20260427.md)
- 범위: **Test 탭 한정**의 정책 보강. 실제 서비스 / DB / parser 코드 변경 없음.
- 목적: 기존 영수증 amount 중심으로 만들어진 suppression 해석 (특히 `suppressed_bank_slip`)을
  새 profile 구조 기준으로 어떻게 재해석할지 동결한다.
- 비범위: OCR 인식 로직, parser 구현, baseline / google lock 문서의 직접 수정.
- 변경 시 베이스라인:
  `ocr-server/main.py` (`_apply_doc_type_amount_policy`),
  `mysuit-ocr/public/data/testsets/*/manifest.json`,
  `docs/BASELINE_LOCK_20260425.md`, `docs/GOOGLE_LOCK_20260425.md` (모두 무수정 유지).

---

## 접근 계획 (요약)

1. 현행 suppression은 영수증 `amount` 채택 정책의 부산물. `bank_slip` 문서의 amount 자동채택을 막기 위해 status를 `suppressed_bank_slip`로 덮어쓰는 구조.
2. 새 profile 구조에서는 `finance_slip`을 영수증 amount로 평가하지 않음 → 같은 status를 "전체 문서 실패"로 해석할 이유가 사라짐.
3. suppression의 의미를 "문서군 식별 실패 + 추출 자체 불가"로 좁히고, finance_slip은 Tier-1 4필드 추출 가능 여부로 selected / review 판정.
4. lock 문서는 무수정. 본 노트가 lock 수치를 **재해석**하는 권위 있는 보강 자료가 된다 (수치 자체는 lock과 일치).
5. `suppressed_bank_slip` 라벨은 "정책 라벨"로는 폐지하되, **lock 문서에 박힌 라벨 문자열은 보존** (호환성).
6. KPI는 영수증 / finance / 카드 overlay / suppressed&unknown 4계로 분리. review는 별도 카운트.
7. 1차 즉시 구현 상태는 3종 (selected / review / suppressed) 으로 단순화, partial은 정책 문서에만 정의 후 데이터 누적 후 분리.

---

# 1. 기존 suppression 해석 요약

## 1.1 어디서 무엇이 suppression이 되었는가

현행 `ocr-server/main.py`의 `_apply_doc_type_amount_policy`가 사후 정책으로 `amount_value`를 비우면서 다음 status로 덮어쓰는 구조.

| 기존 status | 발동 조건 | 의미 (영수증 amount 관점) |
|---|---|---|
| `suppressed_bank_slip` | doc_type=`bank_slip` + 강한 합계 근거 부족 (selected score < 40) | 거래후잔액/수수료/계좌 문맥 숫자를 영수증 합계로 오채택하지 않기 위해 amount를 비움 |
| `suppressed_handwritten` | doc_type=`form_or_handwritten` + 저신뢰 또는 bare 단일 후보 | 수기 OCR 저신뢰 시 amount 자동채택 보수화 |
| `suppressed_unknown_bare` | doc_type=`unknown` + bare 저신뢰 단독 | 분류 근거 부족 + 약한 후보 → 비움 |

핵심 사실: 위 status는 **amount 채택만의 사후 보수 정책**이지, "문서 자체가 실패했다"는 의미는 아니었다. 그러나 Test 탭은 영수증 6필드를 강제 평가하는 구조였기 때문에 결과적으로 **문서 전체 실패**처럼 표시되어 왔다.

## 1.2 finance_slip / bank 계열이 suppression으로 간 이유

- 영수증 합계 추출 정책을 그대로 finance_slip에 적용하면 "거래후잔액"·"이체금액"·"수수료" 등을 합계로 오채택할 위험이 컸다.
- 1차 보수 정책으로 amount를 비우는 선택을 했고, 그 결과 status가 `suppressed_bank_slip`로 덮였다.
- Test 탭의 6필드 KPI에서는 회사명·사업자번호·총합계금액이 모두 빈/오답으로 보여, **사실상 "이 문서는 처리 실패"** 처럼 카운트되어 왔다.

## 1.3 `suppressed_bank_slip` 라벨이 가졌던 실제 의미

- 정확한 의미: "이 문서는 영수증 amount 정책으로는 안전하게 합계를 뽑을 수 없으니 비움."
- 잘못 해석되어 온 의미: "이 문서는 OCR이 인식하지 못했고 모든 필드가 실패."
- 두 의미가 분리되지 않은 채 baseline 9.jpg / google 6.jpg가 lock에 들어갔다 → 본 노트가 정리해야 할 핵심 갭.

## 1.4 lock에 박힌 현행 케이스

| 데이터셋 | 파일 | documentType (manifest) | expectedStatus (lock) | 새 정책에서의 위치 |
|---|---|---|---|---|
| baseline | `9.jpg` | `finance_slip` | `suppressed_bank_slip` | finance_profile partial / selected 후보 |
| google | `6.jpg` | `finance_slip` | `suppressed_bank_slip` | finance_profile partial / selected 후보 |
| baseline | `a2.jpg` | `card_receipt` (qualityTags=handwritten) | `suppressed_handwritten` | suppressed 유지 (정당한 suppression) |

원칙: 위 expectedStatus 문자열은 lock 보호로 변경하지 않는다. 본 노트가 "재해석 매핑"을 명시한다.

---

# 2. 새 Test 기준 suppression 정책

## 2.1 핵심 변경점 (요약)

1. **`finance_slip`은 더 이상 suppression 기본값이 아니다.** finance_profile (Tier-1 4필드) 로 평가한다.
2. **suppression의 정의를 좁힌다.** "문서군 식별 실패 + OCR/추출 자체 불가" 만 suppression.
3. **읽을 수 있는 필드는 읽고**, 불확실한 필드는 비우거나 review로 둔다. 전체 문서 실패로 카운트하지 않는다.
4. **profile에 없는 필드는 `X` 가 아니라 `not_applicable` (시각적으로는 `—`)** 로 표시하고 KPI 분모에서 제외한다.
5. **마스킹 정책 위반** (계좌 raw / 카드 raw 노출) 은 selected가 아니라 review로 강제 분류한다.

## 2.2 Test 탭에서의 suppression 새 정의

> **suppression** = "어떤 profile에도 매칭되지 않거나, 매칭되더라도 OCR/추출 자체가 불가능한 경우."

판단 기준 (Test 탭 한정):
- documentType = `unknown` 이면서 OCR 결과로도 어떤 profile 신호도 우세하지 않음 → suppressed
- documentType이 명시되어 있어도 OCR raw 텍스트가 사실상 비어 있거나 (의미 토큰 0) 손상으로 추출 불가 → suppressed
- qualityTags=`handwritten` + Tier-1 필수 필드 0개 추출 → suppressed (`a2.jpg` 패턴)
- 그 외, **profile의 Tier-1 필수 필드 중 일부라도 추출되었다면 suppressed가 아니다** (review 또는 selected)

## 2.3 suppression의 KPI 위치

- suppression은 **성공 KPI에 포함하지 않는다.**
- 영수증 정확도 / finance 추출률 KPI의 분모에서도 제외한다.
- "suppressed / unknown 건수" 라는 별도 카운트 카드로만 집계.
- 즉 suppression은 더 이상 영수증 KPI를 깎는 항목이 아니다.

## 2.4 영수증 amount 보수 정책 자체는 코드에서 제거하지 않는다

- `ocr-server/main.py`의 `_apply_doc_type_amount_policy`는 본 단계에서 손대지 않는다.
- 이유: parser가 finance_profile Tier-1을 직접 채울 때까지는 영수증 amount 오채택 방지 보수 정책이 안전망 역할을 함.
- Test 탭이 status 문자열을 받았을 때 **표시 매핑만** 새 정책에 맞게 분기 (KPI 반영 변경) → 코드 단계에서 진행할 작업.

---

# 3. selected / review / suppressed / unknown 정의

## 3.1 정책 문서 기준 (5종 — 본 노트 동결)

| 상태 | 정의 | 적용 profile |
|---|---|---|
| `selected` | profile의 **필수 필드를 모두 추출** + 신뢰도 정상 + 정책 위반 없음 | 전체 |
| `partial` | profile의 **필수 필드 일부만 추출**, 나머지는 빈 값으로 정직하게 출력. 정책 위반 없음 | 전체 (특히 finance_profile에서 흔함) |
| `review` | 추출은 됐으나 ① 마스킹 정책 위반 의심, ② 신뢰도 낮음, ③ profile mismatch 경고, ④ Tier-2 GT 있음에도 큰 불일치, ⑤ amount 후보가 거래후잔액/수수료 문맥과 충돌 | 전체 |
| `suppressed` | 어떤 profile에도 매칭 불가 + Tier-1 필수 필드 0개 추출 + 추출 자체 불가 (손글씨 / 손상 / 비문서 이미지) | 전체 |
| `unknown` | manifest documentType=`unknown` 이거나 문서군 식별 자체가 미수행 | none |

## 3.2 즉시 구현 기준 (3종 — 1차 단순화)

상태 폭증을 막기 위해 1차 코드 도입은 3종으로 시작.

| 즉시 구현 상태 | 통합 대상 |
|---|---|
| `selected` | 정책의 selected |
| `review` | 정책의 partial + review 통합 |
| `suppressed` | 정책의 suppressed + unknown 통합 |

근거:
- `partial`을 단독 상태로 분리하려면 **충분한 finance 샘플**이 필요. 현재 `finance_slip` 케이스가 baseline/google 합산 2건뿐 → 분리하면 통계 의미 없음.
- 데이터 누적 (3차 검증셋 이상 / 파일 10건 이상) 후 `partial` 분리.
- `unknown`도 1차에서는 `suppressed`로 통합 표시하되 카운트는 별도 컬럼으로 관리.

## 3.3 partial 도입 시점의 트리거

- 트리거 1: finance_slip 항목이 누적 10건 이상 확보된 시점.
- 트리거 2: Tier-1 4필드 중 1~3개만 잡히는 케이스가 전체 finance의 30% 이상이 된 시점.
- 트리거 3: 고객 데모에서 "부분 성공"을 별도로 보여줘야 하는 SI 요구가 발생한 시점.
- 위 중 하나라도 만족하면 정책의 partial을 즉시 구현 상태로 승격.

---

# 4. finance_slip 상태 판정 기준

## 4.1 finance_profile Tier-1 / Tier-2 회수율 기반

| 조건 | 정책 상태 | 1차 즉시 구현 상태 |
|---|---|---|
| Tier-1 4필드 모두 추출 + 마스킹 정책 통과 + 정책 위반 없음 | `selected` | `selected` |
| Tier-1 1~3필드 추출 + 정책 위반 없음 | `partial` | `review` |
| Tier-1 1개 이상 추출 + ① 마스킹 위반 의심 또는 ② 거래후잔액/수수료 문맥 충돌 또는 ③ Tier-2 큰 불일치 | `review` | `review` |
| Tier-1 0개 추출 + OCR raw 텍스트는 존재 (인식 자체는 됨) | `partial` 또는 `review` | `review` |
| Tier-1 0개 추출 + OCR raw 텍스트도 사실상 비어 있음 / 손상 | `suppressed` | `suppressed` |
| documentType=`finance_slip`이지만 OCR 신호가 명백히 영수증 → manifest 오의심 | `review` (`profile_suspected_mismatch` 경고) | `review` |

## 4.2 마스킹 위반 / 정책 위반 사례

다음 중 하나라도 발생하면 selected가 아니라 **review로 강제 분류**:

- `accountMasked` 슬롯에 raw 형식 (예: `123-456-789012`, 8자리 이상 연속 숫자) 이 들어옴 → `MASKING_POLICY_VIOLATION_ACCOUNT`
- (이후 확장) `cardOverlay.cardNumberMasked`에 raw 4자리 이상 연속 숫자가 노출 → `MASKING_POLICY_VIOLATION_CARD`
- `memo`에 전화/주민번호 패턴 통과 → `PII_LEAK_MEMO`
- `transactionType` enum 외 값 (예: 한자, 깨진 토큰) → `INVALID_TRANSACTION_TYPE`

## 4.3 amount 충돌 사례 (영수증 보수 정책과의 경계)

기존 `_apply_doc_type_amount_policy`가 비워둔 영수증 amount 영역과 finance_profile의 `amount`는 **분리된 슬롯**.

- 영수증 `totalAmount`가 비어 있는 것은 finance_slip에서 `not_applicable` → KPI 분모 제외 → review 사유 아님.
- finance `amount`가 비어 있는 것은 Tier-1 결손 → review 사유.
- 두 슬롯을 같은 컬럼으로 병합 표시하면 안 됨 (UI 레이어 책임, 본 노트 §7 / 상위 문서 §7 참조).

## 4.4 baseline 9.jpg / google 6.jpg 의 새 기준 위치

| 파일 | lock expectedStatus | 새 정책 매핑 (정책 문서 기준) | 새 정책 매핑 (1차 즉시 구현) |
|---|---|---|---|
| baseline `9.jpg` | `suppressed_bank_slip` | finance_profile + Tier-1 추출 결과에 따라 selected / partial / review | selected 또는 review (lock 수치 변동 0 유지) |
| google `6.jpg` | `suppressed_bank_slip` | 동일 | 동일 |

원칙: **lock 문자열은 변경하지 않고**, 본 노트의 매핑표가 "정상 카운트 분류 시 어디로 가는지"를 결정한다 (§5).

---

# 5. lock 문서 재해석 원칙

## 5.1 무수정 원칙

- `docs/BASELINE_LOCK_20260425.md`, `docs/GOOGLE_LOCK_20260425.md`는 **직접 수정하지 않는다.**
- lock에 박힌 모든 수치 (baseline 43/57, final 52/57, biz 9/9, amount 8/10 등) 는 그대로 보존한다.
- 본 노트는 lock 수치를 깎거나 늘리지 않는다.

## 5.2 보강 노트 형식의 재해석

새 정책은 **"보강 매핑표"** 로만 작용한다.

- 보강 매핑표 = `(파일, lock의 expectedStatus) → 새 정책의 1차 상태 + KPI 분류`
- 예시:
  - `(baseline/9.jpg, suppressed_bank_slip) → 1차 상태 review, KPI 분류 finance_profile, suppression KPI 미산입`
  - `(google/6.jpg, suppressed_bank_slip) → 1차 상태 review, KPI 분류 finance_profile, suppression KPI 미산입`
  - `(baseline/a2.jpg, suppressed_handwritten) → 1차 상태 suppressed, KPI 분류 suppressed/unknown 카운트`
- 매핑표는 본 노트 §4.4 / §6.2 가 권위 있는 출처.

## 5.3 manifest / documentType 재검토 케이스

다음 조건 중 하나라도 만족하면 **별도 리뷰 리스트**에 올린다 (manifest 자동 변경은 하지 않음).

- documentType=영수증 계열 인데 OCR 결과의 finance 신호 (은행명 / 거래후잔액 / 입출금 등 키워드) 가 우세
- documentType=`finance_slip` 인데 OCR 결과의 영수증 신호 (사업자번호 패턴 / 가맹점/주소 키워드) 가 우세
- 라벨: `profile_suspected_mismatch`

처리 흐름: 사람이 manifest를 검토 → 필요 시 manifest 수정 → 다음 실행에서 profile 재산출.

## 5.4 lock 보강 노트 산출물 위치

본 노트가 보강 매핑의 권위 있는 출처. 별도 매핑 JSON 파일은 만들지 않는다 (단일 진실 원천 유지). 코드 단계에서는 본 §4.4 / §6.2 매핑을 참조하는 상수 테이블을 두는 것을 권장.

---

# 6. `suppressed_bank_slip` 폐지 방향

## 6.1 왜 폐지해야 하는가

- 의미가 두 갈래로 갈라져 있음: ① "amount 보수 정책으로 비움" (정확) ② "문서 전체 실패" (오해).
- finance_slip을 영수증 6필드로 평가하지 않게 되면, ②의 의미는 사라진다.
- 동일한 status가 KPI에서 정상 분모를 깎고 있어 영수증 점수가 왜곡됨.
- 새 profile 구조에서는 `finance_profile`이 Tier-1 4필드로 따로 평가되므로, `suppressed_bank_slip` 라벨을 정책 라벨로 유지할 이유가 없음.

## 6.2 어떤 라벨/상태 체계로 대체하는가

### 정책 라벨 차원

| 폐지 대상 | 대체 |
|---|---|
| `suppressed_bank_slip` | **정책 라벨에서 제거.** finance_profile의 selected / partial / review로 자연스럽게 분류 |
| `suppressed_handwritten` | 그대로 유지 (정당한 suppression) |
| `suppressed_unknown_bare` | 그대로 유지 (정당한 suppression — unknown profile 미매칭) |

### 코드/문자열 호환성 차원 (중요)

- `ocr-server/main.py`가 반환하는 status 문자열 `suppressed_bank_slip`는 **본 단계에서 제거하지 않는다.**
- 이유: lock 문서·검증 결과 JSON·기존 manifest의 `expectedStatus`가 모두 이 문자열을 참조 중.
- 대신 Test 탭이 이 문자열을 받았을 때 **표시 매핑을 새 정책으로 분기**한다 (코드 단계 작업).
- 즉 "라벨 문자열은 보존, 의미와 KPI 분류는 새 정책으로 재해석" 의 단계적 폐지.
- 완전 제거는 다음 조건 충족 후 별도 단계:
  1. finance parser Tier-1이 안정적으로 동작
  2. baseline / google lock의 다음 회차 갱신 (lock 자체 갱신 시점에 라벨도 정리)

### 매핑표 (status 문자열 → 새 정책 1차 상태)

| status 문자열 (코드/lock 보존) | 새 정책 1차 상태 | KPI 분류 |
|---|---|---|
| `selected` | `selected` | profile별 KPI 정상 산입 |
| `low_confidence` | `review` | review 카운트 |
| `no_candidate` | `review` (단, 영수증 필수 필드 0개면 `suppressed`) | review 또는 suppressed 카운트 |
| `all_rejected` | `review` | review 카운트 |
| `suppressed_bank_slip` | **`review`** (단, OCR raw도 비면 `suppressed`) | **finance_profile review 카운트, 영수증 KPI 미산입** |
| `suppressed_handwritten` | `suppressed` | suppressed/unknown 카운트 |
| `suppressed_unknown_bare` | `suppressed` | suppressed/unknown 카운트 |

## 6.3 과거 결과 vs 새 결과 비교 시 주의사항

- 같은 데이터셋의 lock 수치 (43/57, 52/57 등) 는 **새 정책 적용 후에도 영수증 KPI 분모/분자에서 동일하게 유지**되어야 한다 (회귀 안전).
  - 영수증 KPI 분모는 receipt_family 항목 수로 한정되므로, finance_slip 항목이 빠진다고 분모가 줄지 않음. (lock 시점부터 finance_slip은 사실상 점수 기여 0이었음 → 분모 감소 효과 없음)
- `suppression` 카운트 는 새 정책에서 **줄어든다.** finance_slip 2건이 review로 이동.
  - lock 문서의 "suppression: 2 (baseline)" / "suppression: 1 (google)" 수치는 lock 시점의 통계로 보존, 새 정책 통계와 **별도로 표시**.
- 비교 보고 시 반드시 다음을 명시: "수치는 lock 시점 정책 기준 / 새 정책 기준" 의 두 컬럼을 같이 표시.
- 단순 합계 비교는 하지 않는다 (분류 기준이 다름).

---

# 7. KPI 반영 기준

## 7.1 KPI 카드 분리 (상위 문서 §7과 일치)

| KPI 카드 | 분자 | 분모 | suppression 영향 |
|---|---|---|---|
| 영수증 정확도 | receipt_profile selected 건수 | receipt_family 총건수 | suppression 미산입 (분자/분모 모두) |
| 카드 overlay 보정률 | card_overlay 필수 충족 건수 | `card_receipt` 총건수 | 동일 |
| 금융전표 추출률 | finance_profile Tier-1 4필드 모두 채운 건수 | finance_family 총건수 | 동일 |
| review 카운트 | review 1차 상태 건수 (profile별 분리) | — | review는 **별도 카운트**, %로 환산하지 않음 |
| suppressed / unknown 건수 | suppressed + unknown 1차 상태 합산 | — | suppression은 **여기에만** 카운트 |

## 7.2 not_applicable 의 KPI 처리

- `not_applicable` (예: finance_slip의 영수증 필드) 은 **분모/분자 어디에도 포함하지 않는다.**
- `no_baseline` (GT 미존재) 도 분모 제외이지만 의미가 다름. tooltip / 색상으로 시각 구분 (상위 문서 §8).

## 7.3 review의 위치

- review는 **selected와 다른 KPI**.
  - 즉 selected % 분자에 들어가지 않는다.
  - "review 비율" 이라는 별도 보조 지표로 표시 (선택적).
- review는 **suppression이 아니다.** suppression KPI에도 들어가지 않음.
- review의 의미: "값은 있지만 사람 검토 필요" → SI 단계에서 운영자에게 보내야 할 큐.

## 7.4 receipt KPI ↔ finance KPI 절대 합산 금지

- 영수증 정확도와 금융전표 추출률은 **다른 분모/다른 의미**.
- 한 줄 KPI ("전체 OCR 성공률") 같은 통합 수치는 **만들지 않는다.**
- 데모/보고용으로 통합 수치가 필요하면 "영수증 X% / 금융 Y%" 식 분리 표기.

## 7.5 lock 시점 KPI vs 새 정책 KPI 병기

- 본 노트가 적용된 후의 KPI 카드는 다음 두 컬럼을 함께 표시하는 것을 권장:
  - "lock 시점 정책 (영수증 6필드 강제, finance_slip은 suppression)"
  - "새 정책 (profile 분리, finance_slip은 finance KPI)"
- 비교의 단순 합계가 아닌 **해석 기준이 다름**을 명시.

---

# 8. 절대 하면 안 되는 해석

| 금기 | 이유 |
|---|---|
| `finance_slip`을 영수증 실패처럼 취급 | KPI 분모 왜곡. 본 노트가 폐지하려는 핵심 오용 |
| profile에 없는 필드를 `X` (mismatch) 로 계산 | "해당 없음" 과 "오추출" 혼동 → KPI 신뢰도 0 |
| `suppression` 을 `selected` 처럼 해석 (성공 KPI 분자 산입) | 모든 점수 의미 상실 |
| baseline / google lock 문서를 새 정책에 맞춰 직접 수정 | lock 보호 위반. 보강 노트 + 매핑표만 허용 |
| lock의 `expectedStatus` 문자열을 manifest에서 일괄 치환 | 회귀 검증 기준 깨짐. 라벨 문자열 보존 + 표시 매핑만 분기 |
| `ocr-server/main.py`의 `suppressed_bank_slip` 반환을 본 단계에서 제거 | 검증 결과 JSON / lock 문서가 참조 중. 단계적 폐지 (§6.2) |
| `partial` 상태를 즉시 구현 단계에서 별도 카운트로 분리 | finance 샘플 부족. 통계 의미 없음. 트리거 충족 후 분리 (§3.3) |
| review를 suppression KPI에 합산 | review는 "값 있음 + 검토 필요". suppression이 아님 |
| review를 selected KPI에 합산 | review는 success가 아님. 별도 보조 지표로만 |
| 영수증 KPI와 finance KPI를 한 줄 KPI로 통합 | 분모/의미가 다름. 통합 수치는 만들지 않음 |
| profile을 OCR 결과 기반으로 동적 변경해 finance를 receipt KPI로 보내거나 그 반대 | 회귀 검증 불가. profile은 manifest documentType이 결정 (상위 문서 §3) |
| parser 구현 전에 상태 체계 (5종) 를 즉시 코드 확장 | 데이터 부족. 1차는 3종 (selected/review/suppressed) 으로 시작 (§3.2) |
| 새 정책 KPI와 lock 시점 KPI를 단순 합산 비교 | 분류 기준이 다름. 두 컬럼 병기 (§7.5) |
| GT에 raw 계좌번호 / raw 카드번호 저장 (review로 분류되어도 GT는 마스킹 필수) | 마스킹 정책 위반. review 분류와 별개로 저장 단계에서 강제 마스킹 |
| `suppressed_handwritten` / `suppressed_unknown_bare` 까지 묶어서 폐지 선언 | 둘은 정당한 suppression. 폐지 대상은 `suppressed_bank_slip` 라벨 의미만 |
| 본 노트의 §6.2 매핑표를 lock 문서에 직접 반영 | lock 보호 위반. 매핑표는 코드/문서 외부 상수로만 사용 |

---

# 부록 A — 코드 단계 진입 시 영향 지점 (참조용, 본 단계에서는 변경 없음)

| 영역 | 파일 | 변경 성격 | 주의 |
|---|---|---|---|
| status 표시 매핑 | `mysuit-ocr/src/components/test/TestWorkspace.tsx` | UI만 | lock 문자열 보존, 표시/KPI 분류만 분기 |
| profile resolver 단일 진입점 | `mysuit-ocr/src/lib/profiles.ts` (신설) | 신규 | OCR 결과 기반 동적 변경 금지 |
| KPI 집계 | `mysuit-ocr/src/components/test/core/finalize.ts` 호출부 | 호출부만 | `not_applicable` 분기는 호출 측에서, 함수 시그니처 무변경 가능 |
| ocr-server suppression 반환 | `ocr-server/main.py` `_apply_doc_type_amount_policy` | **본 단계 무수정** | parser 안정화 후 별도 단계에서 정리 |
| manifest expectedStatus | `public/data/testsets/*/manifest.json` | **본 단계 무수정** | lock 보호 |

# 부록 B — 회귀 안전 가드

본 노트가 동결되고 코드 단계로 진입할 때 다음을 의무화한다.

- baseline 영수증 KPI 분모/분자 변동 0 (영수증 6필드 강제 시점 대비)
- google 영수증 KPI 분모/분자 변동 0
- baseline `9.jpg` / google `6.jpg` 의 lock 문자열 (`suppressed_bank_slip`) 보존
- baseline `a2.jpg` 의 lock 문자열 (`suppressed_handwritten`) 보존 + suppressed/unknown 카운트 위치 유지
- `ocr-server/main.py`의 `_apply_doc_type_amount_policy` 무수정
- `npm run typecheck` / `npm run build` 통과
- 기존 dataset 전환 / qualityTags filter / Run All 무영향
