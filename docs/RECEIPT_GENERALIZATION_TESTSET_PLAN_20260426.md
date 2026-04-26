# RECEIPT GENERALIZATION TESTSET PLAN 2026-04-26

영수증 계열 신규 일반화 검증셋 구성 계획 문서.
관련 문서: [SESSION_SUMMARY.md](../SESSION_SUMMARY.md), [docs/REFACTOR_MINIMAL_COMMON_READY_20260426.md](REFACTOR_MINIMAL_COMMON_READY_20260426.md)

이 문서는 계획 문서이며, **코드/샘플/manifest 추가는 이 문서 작성 자체로 수행하지 않는다.**

---

## 1. 목적

baseline(10장)과 google(11장)은 각각 회귀 안전 기준셋 / 실전형 일반화 기준셋으로 잠금 상태이다.  
신규 `receipt_generalization` 셋은 아래 목적으로 구성한다.

1. **card_receipt 과적합 방지 확인** — 현재 baseline 대부분이 card_receipt 계열. 다른 documentType 성능이 실제로 유지되는지 확인.
2. **documentType별 약점 발굴** — pos_receipt(편의점/마트), food_cafe_receipt(음식점/카페), medical_receipt(병원/약국) 에서 반복되는 실패 패턴 확인.
3. **suppression 문서가 selected로 오인되지 않는지 확인** — finance_slip(은행/금융 전표), handwritten 계열이 selected로 잘못 올라오는 케이스 확인.
4. **qualityTags별 성능 약점 확인** — ocr_noise, small_text, low_contrast, folded 등 실제 품질 조건에서 취약한 패턴 식별.
5. **TestWorkspace documentType/qualityTags UI가 실제 분석에 유용한지 검증** — 신규셋을 통해 summary/filter/range 뷰가 실전에서 의미 있는지 확인.
6. **거래명세서 진입 전 영수증 계열 안정성 확인** — 큰 구조적 문제가 없음을 확인한 뒤 invoice_statement로 이동.

---

## 2. Dataset 이름 및 위치

| 항목 | 값 |
|---|---|
| datasetId | `receipt_generalization` |
| folder | `mysuit-ocr/public/data/testsets/receipt_generalization/` |
| datasetRole | `generalization` |
| status | `draft` (initial 검증 후 필요 시 lock 문서 작성 가능) |
| lockDoc | 없음 (초기 단계) |
| description | 영수증 계열 신규 일반화 검증셋 (draft). baseline/google과 별개로 운용. |

최초 manifest 구조 예시는 §8 참고.

---

## 3. 포함할 documentType

아래 유형을 반드시 포함한다. 각 유형별 목적을 명시.

| documentType | 의미 | 포함 이유 |
|---|---|---|
| `card_receipt` | 카드전표/일반 영수증 | baseline의 주요 유형. 과적합 여부 확인. |
| `pos_receipt` | POS/마트/편의점 영수증 | google에서 GS25 계열만 포함. 다른 편의점/마트 일반화 확인. |
| `food_cafe_receipt` | 음식점/카페 영수증 | google에 포함되나 추가 케이스 확인. 회사명 추출 노이즈 패턴 다양화. |
| `medical_receipt` | 병원/약국 영수증 | google에 미화약국 1장만 존재. 추가 케이스 필요. |
| `finance_slip` | 은행/금융 전표 | suppression 정상 동작 확인. 1~2장으로 충분. |
| `unknown` | 미분류/확실하지 않은 경우 | 필요 시 소수 포함. 분류 판단이 어려운 케이스 기록용. |

이번 계획에서 `invoice_statement`(거래명세서/세금계산서)는 포함하지 않는다.

---

## 4. 권장 샘플 수와 비율

**총 권장 장수: 15~30장 (1차)**

초기부터 100장을 목표로 하지 않는다. 15~30장으로 initial validation을 먼저 수행하고, 결과를 보고 점진적으로 확대한다.

권장 구성 비율:

| documentType | 권장 장수 | 비율 |
|---|---|---|
| pos_receipt | 5~10장 | 30~40% |
| food_cafe_receipt | 4~8장 | 20~30% |
| card_receipt | 3~6장 | 15~20% |
| medical_receipt | 2~4장 | 10~15% |
| finance_slip (suppression용) | 1~3장 | 5~10% |
| unknown (필요 시) | 0~2장 | 선택 |

### qualityTags 다양성 권장

품질 조건이 편향되지 않도록 아래 태그를 최소 1~2장씩 포함한다:

- `ocr_noise`: OCR 오인식 노이즈가 눈에 띄는 샘플
- `small_text`: 텍스트가 작아 판독이 어려운 샘플
- `folded` 또는 `curled`: 접힘/말림이 있는 샘플
- `low_contrast` 또는 `blurred`: 저대비 또는 흐린 샘플

---

## 5. 샘플 수집 기준

### 5.1 수집 우선순위

1. **직접 수집한 실물 영수증** — 가장 선호. 다양한 업종/포맷을 직접 촬영.
2. **가족/지인 제공 영수증** — 실생활 다양성 확보.
3. **기존 프로젝트에서 미사용 샘플** — 기존 tuning에 사용하지 않은 샘플. 과적합 방지에 유리.
4. **공개 이미지/합성 샘플** — 보조용으로만 사용. baseline/google 결과 tuning에는 사용하지 않았던 것만.

### 5.2 민감정보 처리

- 카드번호, 멤버십 번호, 개인 이름, 주민번호 등 민감정보는 마스킹 권장.
- 병원/약국 샘플은 처방 내용, 환자 정보 포함 여부 주의.
- OCR 목표 필드(상호, 사업자번호, 대표자, 전화, 주소, 총합계금액)는 가능하면 남겨둔다. 마스킹 시 notes에 기록.
- 민감정보가 많아 마스킹 후 OCR 의미가 없어지면 해당 샘플은 제외.

### 5.3 이미지 품질 기준

- 영수증 전체가 프레임 안에 들어오는 것 권장.
- 심하게 잘리거나(cropped) OCR 자체가 불가능한 수준은 제외.
- 일부러 극단적으로 어려운 샘플을 많이 넣지 않는다. initial은 평균적인 어려움 기준.

---

## 6. qualityTags 기준 정의

아래 기준으로 태그를 부여한다. **문서 유형(documentType)과 품질 상태(qualityTags)를 절대 혼용하지 않는다.**

| qualityTag | 부여 기준 |
|---|---|
| `ocr_noise` | OCR raw 결과에서 텍스트가 깨지거나 잘못 인식되는 노이즈가 눈에 띔 |
| `small_text` | 영수증 텍스트 크기가 전반적으로 작아 판독이 어려운 샘플 |
| `low_contrast` | 배경-텍스트 명암비가 낮아 OCR이 어려운 샘플 |
| `blurred` | 촬영 흔들림 또는 초점 문제로 전체가 흐린 샘플 |
| `folded` | 종이가 접혀 일부 텍스트가 가려지거나 왜곡된 샘플 |
| `curled` | 영수증 끝이 말려 레이아웃이 왜곡된 샘플 |
| `skewed` | 기울어진 상태로 촬영되어 텍스트 줄이 비스듬한 샘플 |
| `shadow` | 그림자로 인해 일부 텍스트 영역이 가려진 샘플 |
| `cropped` | 프레임에 영수증 일부가 잘린 샘플 |
| `rotated` | 90도/180도 등 회전된 상태로 촬영된 샘플 |
| `long_receipt` | 영수증이 매우 길어 여러 번 이어 촬영하거나 잘린 가능성이 있는 샘플 |
| `handwritten` | 손으로 쓴 내용이 포함된 샘플 (suppressed_handwritten 가능성 있음) |

**주의:**
- `pos_receipt`, `food_cafe_receipt`, `medical_receipt` 등은 documentType (문서 유형).
- `ocr_noise`, `small_text`, `folded` 등은 qualityTags (이미지/인쇄 품질 조건).
- 동일 샘플에 복수 태그 부여 가능 (예: `["small_text", "low_contrast"]`).

---

## 7. expectedStatus 기준

| expectedStatus | 부여 조건 |
|---|---|
| `selected` | 정상 처리 가능한 영수증. OCR 결과가 선택되어야 함. |
| `suppressed_bank_slip` | 은행/금융 전표(finance_slip). 현재 parser 기준 억제가 정상. |
| `suppressed_handwritten` | 수기/손글씨 문서. 현재 parser 기준 억제가 정상. |
| `unknown` | 문서 유형이 애매하거나, 처리 결과 예측이 어려운 케이스. notes에 이유 기록. |

**중요:**  
suppressed 결과는 실패가 아니다. finance_slip이 `suppressed_bank_slip`으로 처리되면 **현재 receipt parser 기준에서 정상 억제**이다. initial validation 분석 시 suppression 케이스는 "정상 억제됨" 또는 "suppression 누락" 두 경우를 분리해서 본다.

---

## 8. manifest.json 초안 구조 예시

현재 baseline/google manifest 형식을 그대로 따른다.

```json
{
  "datasetId": "receipt_generalization",
  "datasetRole": "generalization",
  "status": "draft",
  "description": "영수증 계열 신규 일반화 검증셋 (draft). 15~30장 초기 구성.",
  "items": [
    {
      "filename": "rg_01.jpg",
      "documentType": "pos_receipt",
      "qualityTags": ["small_text"],
      "difficulty": "medium",
      "expectedStatus": "selected",
      "notes": "편의점 영수증. 텍스트 작음. 회사명/금액 추출 확인용."
    },
    {
      "filename": "rg_02.jpg",
      "documentType": "food_cafe_receipt",
      "qualityTags": ["ocr_noise"],
      "difficulty": "medium",
      "expectedStatus": "selected",
      "notes": "음식점 영수증. 회사명 OCR 노이즈 케이스."
    },
    {
      "filename": "rg_03.jpg",
      "documentType": "card_receipt",
      "qualityTags": [],
      "difficulty": "easy",
      "expectedStatus": "selected",
      "notes": "표준 카드전표."
    },
    {
      "filename": "rg_04.jpg",
      "documentType": "finance_slip",
      "qualityTags": [],
      "difficulty": "easy",
      "expectedStatus": "suppressed_bank_slip",
      "notes": "은행 입출금 전표. suppression 정상 동작 확인용."
    },
    {
      "filename": "rg_05.jpg",
      "documentType": "medical_receipt",
      "qualityTags": ["low_contrast"],
      "difficulty": "hard",
      "expectedStatus": "selected",
      "notes": "약국 영수증. 명암비 낮은 케이스. 민감정보 마스킹됨."
    }
  ]
}
```

**파일명 명명 규칙 권장:** `rg_01.jpg`, `rg_02.jpg` ... 순번 형식. 또는 `rg_pos_01.jpg` 처럼 documentType prefix를 붙여도 가능. manifest 내 filename과 실제 파일명 일치 필수.

---

## 9. 최초 validation 원칙

1. **첫 실행은 코드 수정 없이 검증만 수행한다.**
2. initial 결과를 기록하고 실패 패턴을 분석한다.
3. **initial 실행 직후 바로 보정하지 않는다.** 결과를 먼저 이해하고 패턴을 식별한 뒤 결정한다.
4. baseline/google 회귀 확인은 보정 시에만 필요. initial 단계에서는 해당 없음.

결과 파일명 규칙:

```
validation_results_receipt_generalization_initial.json
```

또는 추후 engine 비교를 고려해:

```
validation_results_receipt_generalization_initial_paddle.json
```

해당 셋에서 Google/Azure/CLOVA 등 다른 OCR engine 결과를 비교할 때는:

```
validation_results_receipt_generalization_initial_google.json
```

형식으로 구분 가능. 단, 이번 계획에서는 adapter 구현을 하지 않으며 Paddle 단일 engine만 사용.

---

## 10. 분석 기준

initial validation 후 아래 항목을 분석한다.

### 10.1 documentType별 분석

- documentType별 selected / suppression / unknown / error 건수
- documentType별 회사명 / 사업자번호 / 대표자 / 전화 / 주소 / 금액 filled count
- 특정 documentType에서 반복되는 실패 필드

### 10.2 qualityTags별 분석

- 특정 qualityTag가 있는 이미지에서 실패율이 높은지
- `ocr_noise` + `small_text` 조합이 어떤 결과를 내는지

### 10.3 suppression 분석

- finance_slip / handwritten 계열이 `suppressed_*` 로 정상 처리되는지
- 정상 영수증이 잘못 억제되는 케이스가 있는지

### 10.4 실패 원인 분류

각 실패 케이스마다 아래 중 어느 쪽인지 분류한다:

| 원인 | 설명 |
|---|---|
| OCR raw 부재 | OCR 자체가 해당 텍스트를 인식하지 못함 → extractor 룰로 해결 불가 |
| 후보 선택 문제 | OCR raw에 텍스트는 있으나 잘못된 후보 선택 → extractor/scoring 개선 여지 |
| classifier 문제 | doc_type 분류가 잘못되어 정책이 틀리게 적용됨 |
| suppression 오류 | 정상 문서가 억제되거나, 억제 문서가 통과됨 |

---

## 11. 룰 추가 기준

initial validation 후 개선 여부를 판단할 때 아래 기준을 따른다.

| 상황 | 판단 |
|---|---|
| 한 장만 틀린 케이스 | 하드코딩하지 않음. 관찰 후 패턴 확인 |
| 같은 documentType에서 2장 이상 반복 | documentType 룰 후보로 검토 |
| 여러 documentType에서 반복 | 공통 extractor 룰 후보로 검토 |
| 특정 qualityTag 있을 때만 반복 | qualityTag 기반 개선 후보 |
| OCR raw에 없는 값 | extractor 룰로 해결하려 하지 않음 |
| 특정 파일명/업체명만 틀림 | 파일명/업체명 하드코딩 금지 |

**수정 발생 시 의무:**
- baseline_fast → google → baseline 순서로 회귀 확인 필수
- 수정 전 main.py 백업 필수
- 모든 lock 기준 수치 유지 확인

---

## 12. OCR engine benchmark 준비 여지

현재 primary engine은 **PaddleOCR** 기준 유지.

추후 Google Vision / Azure Computer Vision / CLOVA OCR 등과 비교할 때:
- 결과 파일명에 engine 식별자 포함 (`_paddle`, `_google`, `_azure`, `_clova`)
- 동일 이미지셋에서 engine별 결과를 비교하는 방식으로 설계 가능
- 이번 계획에서는 adapter 구현 없음. 파일명 규칙만 예약.

---

## 13. 거래명세서 진입 조건

`receipt_generalization` initial validation 완료 후 아래 조건이 충족되면 invoice_statement로 이동한다.

1. initial validation 결과 파일 생성 완료
2. documentType별 / qualityTags별 결과 분석 기록
3. 큰 구조적 문제(suppression 대규모 오류, selected 전부 누락 등)가 없거나 최소 보정 완료
4. 보정이 있었다면 baseline_fast → google → baseline 회귀 확인 완료
5. `docs/RECEIPT_GENERALIZATION_INITIAL_RESULT_<DATE>.md` 결과 기록 문서 작성
6. 이후 `docs/INVOICE_STATEMENT_SCHEMA_PLAN_<DATE>.md` 으로 이동

---

## 14. 실제 다음 작업 순서

이 문서 작성 이후 실행할 작업:

1. **`receipt_generalization` 폴더 생성**
   - `mysuit-ocr/public/data/testsets/receipt_generalization/` 디렉터리 생성
2. **샘플 이미지 15~30장 수집**
   - §5 수집 기준 준수
   - 민감정보 마스킹 처리
3. **manifest.json 작성**
   - §8 초안 구조 참고
   - datasetRole: generalization, status: draft
4. **testsets.ts에 dataset 추가**
   - `TESTSETS` 배열에 `receipt_generalization` 항목 추가
   - 기존 dataset 선택/Run OCR/Run All 흐름에 영향 없어야 함
5. **TestWorkspace에서 UI 확인**
   - documentType 그룹 정상 구성 확인
   - 한글 라벨 / qualityTags filter 정상 동작 확인
6. **Run All로 initial validation 수행**
   - 코드 수정 없이 실행
   - 결과 파일 저장
7. **결과 분석 문서 작성**
   - `docs/RECEIPT_GENERALIZATION_INITIAL_RESULT_<DATE>.md`
   - §10 분석 기준 적용
8. **필요 시 최소 보정 및 회귀 확인**
9. **거래명세서 schema/field profile 문서 작성으로 이동**

---

## 15. 참조 문서

| 문서 | 내용 |
|---|---|
| [docs/BASELINE_LOCK_20260425.md](BASELINE_LOCK_20260425.md) | baseline 회귀 기준 |
| [docs/GOOGLE_LOCK_20260425.md](GOOGLE_LOCK_20260425.md) | google 일반화 기준 |
| [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md) | main.py 리팩토링 계획 |
| [docs/REFACTOR_MINIMAL_COMMON_READY_20260426.md](REFACTOR_MINIMAL_COMMON_READY_20260426.md) | 최소 공통화 완료 선언 |
| baseline/manifest.json | 기준 manifest 구조 예시 |
| google/manifest.json | 기준 manifest 구조 예시 |
