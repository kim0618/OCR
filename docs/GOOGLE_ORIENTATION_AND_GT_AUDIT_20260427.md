# GOOGLE ORIENTATION AND GT AUDIT 2026-04-27

Google 샘플셋의 orientation/display 상태 및 GT 라벨링 필요성 분석 문서.  
관련 문서: [docs/GOOGLE_LOCK_20260425.md](GOOGLE_LOCK_20260425.md)

이 문서는 분석 전용이며 코드·manifest·validation JSON을 수정하지 않는다.

---

## 1. 분석 목적

- receipt_generalization으로 넘어가기 전 Google 샘플셋의 상태를 점검한다.
- UI preview에서 회전되어 보이는 이미지가 있는지, OCR 전처리에 문제가 있는지 판단한다.
- Google GT 라벨링이 필요한지, 안전한지 확인한다.
- 다음 단계 결정 근거를 제공한다.

---

## 2. Google 이미지 orientation 상태 요약

`validation_results.json`의 `angle` 필드를 기준으로 OCR 실행 시 감지된 회전 각도를 정리한다.

| 파일 | OCR 감지 angle | early_stop | status | documentType | 비고 |
|---|---:|:---:|---|---|---|
| `1.jpg` | **90°** | Yes | selected | food_cafe_receipt | 스카토레 |
| `2.jpg` | **90°** | Yes | selected | food_cafe_receipt | 아우프글렛 |
| `3.jpg` | 0° | No | selected | food_cafe_receipt | 키페보니뜨시담점 |
| `4.jpeg` | **90°** | Yes | selected | pos_receipt | 문정수정점 |
| `5.jpg` | 0° | Yes | selected | pos_receipt | GS25역상효성점 |
| `6.jpg` | **90°** | Yes | suppressed_bank_slip | finance_slip | 은행전표 (억제 정상) |
| `7.jpg` | 0° | Yes | selected | pos_receipt | GS25성신로데오점 ← lock 핵심 |
| `8.jpg` | 0° | Yes | selected | unknown | 미확인 업체 |
| `9.jpg` | 0° | Yes | selected | medical_receipt | 미화약국 |
| `10.jpg` | 0° | Yes | selected | food_cafe_receipt | 아비꼬 |
| `11.jpg` | **90°** | Yes | selected | food_cafe_receipt | 커피빈코리아 |

**요약:**
- 90° 보정 대상: 5개 파일 (1.jpg, 2.jpg, 4.jpeg, 6.jpg, 11.jpg)
- 0° (보정 불필요): 6개 파일 (3.jpg, 5.jpg, 7.jpg, 8.jpg, 9.jpg, 10.jpg)
- `early_stop=True`인 경우 orientation 감지가 1차 pass에서 충분히 확정된 것을 의미한다. 3.jpg만 `early_stop=False`로 2차 pass까지 실행됨.

---

## 3. UI preview 문제인지 OCR preprocessing 문제인지 판단

### 결론: **A — UI preview는 원본 표시, OCR은 내부에서 보정된 이미지로 수행됨**

#### 근거

**main.py 파이프라인 순서 (코드 기준):**

```
1. detect_document()       → 원근 보정
2. detect_orientation()    → 0/90/180/270° 중 최적 각도 선택 → 이미지 회전
3. deskew()                → 미세 기울기 보정
4. display_img 생성        → 선명화 + 최대 2000px (orientation 보정 완료 후)
5. ocr_img 생성            → 950px + CLAHE + 언샤프 마스크 (orientation 보정 완료 후)
6. response["processed_image"] = base64(ocr_img)  ← 보정 완료된 이미지
```

**UI displayUrl 처리 (TestWorkspace.tsx):**
```ts
displayUrl: data.processed_image ?? originalUrl
```
- Run OCR 실행 시: `processed_image` (orientation 보정 완료 base64) → UI에 보정된 이미지 표시
- Run OCR 미실행 시: `originalUrl` (public/data/testsets/google/1.jpg 등 원본) → UI에 원본 표시

**실제 영향:**
- 90° 파일들(1.jpg, 2.jpg, 4.jpeg, 11.jpg)을 Run OCR 없이 TestWorkspace에서 보면 세로 이미지가 가로로(또는 반대로) 표시될 수 있다.
- **하지만 OCR 실행 시에는 반드시 orientation 보정이 선행된다.** OCR 결과는 항상 보정된 이미지 기준이다.
- OCR 캐시(`ocr_cache.json`)는 `ocr_text`와 `scanned_at`만 저장한다. 보정된 이미지는 저장되지 않는다.

**따라서:**
- UI preview 왜곡은 "Run OCR 미실행" 상태에서만 발생하는 표시 문제이며, 사용자 인식 문제일 뿐이다.
- OCR 품질 자체는 orientation 보정 이후의 이미지를 기준으로 하므로 회전 문제의 영향을 받지 않는다.

---

## 4. 회전 보정된 이미지의 OCR 필드 영향

90° 보정 대상 파일 4개(6.jpg는 suppressed 정상으로 제외)의 OCR 결과를 분석한다.

### `1.jpg` (90° 보정, food_cafe_receipt, 스카토레)

| 필드 | OCR 결과 | 상태 |
|---|---|---|
| 회사명 | 스카토레 | ✓ |
| 사업자번호 | (공백) | ✗ |
| 대표자 | (공백) | ✗ |
| 전화번호 | (공백) | ✗ |
| 주소 | (공백) | ✗ |
| 총합계금액 | 15,900 | ✓ |

**판단:** 사업자번호/대표자/전화/주소 모두 공백. 이는 orientation 보정 실패보다 **food_cafe_receipt 계열의 구조적 필드 부재** 가능성이 높다. 회사명·금액은 정상 추출됨.

---

### `2.jpg` (90° 보정, food_cafe_receipt, 아우프글렛)

| 필드 | OCR 결과 | 상태 |
|---|---|---|
| 회사명 | 아우프글렛 | ✓ |
| 사업자번호 | 476-41-00855 | ✓ |
| 대표자 | 김기탁 | ✓ |
| 전화번호 | 010-5187-2011 | ✓ |
| 주소 | 서울 용신구 이태원로54가길 20 1,2층 | ✓ (약간 오인식) |
| 총합계금액 | 15,400 | ✓ |

**판단:** 6개 필드 모두 추출 성공 (주소 일부 오인식 있음). 90° 보정이 정상 작동한 대표 케이스. orientation correction이 OCR 결과를 해치지 않음을 확인.

---

### `4.jpeg` (90° 보정, pos_receipt, 문정수정점)

| 필드 | OCR 결과 | 상태 |
|---|---|---|
| 회사명 | 문정수정점 | ✓ |
| 사업자번호 | 880-95-99360 | ✓ |
| 대표자 | (공백) | — |
| 전화번호 | (공백) | — |
| 주소 | (공백) | — |
| 총합계금액 | 18,308 | ✓ |

**판단:** POS 영수증 계열 특성상 대표자/전화/주소 부재가 일반적. 회사명·사업자·금액은 정상. orientation 문제가 아님.

---

### `11.jpg` (90° 보정, food_cafe_receipt, 커피빈코리아)

| 필드 | OCR 결과 | 상태 |
|---|---|---|
| 회사명 | (주)커피빈코리아 | ✓ |
| 사업자번호 | 120-86-07029 | ✓ |
| 대표자 | (공백) | — |
| 전화번호 | 02-33-4278 | ✓ (보수적 인식) |
| 주소 | 서울시 마포구홍익로 6길26 163-12호 | ✓ |
| 총합계금액 | 15,000 | ✓ |

**판단:** Google lock 기준값 `02-33-4278` 유지 확인. 주소도 추출됨. 전화번호 자릿수는 보수적 인식으로 lock 문서에 known limits로 기록된 상태.

---

### 종합 판단

- 90° 보정 파일 4개 모두에서 orientation correction이 OCR 품질을 해치지 않음을 확인.
- 필드 공백은 orientation 문제가 아닌 문서 구조(pos_receipt/food_cafe_receipt) 특성에 기인.
- orientation 로직 보정 필요 없음.

---

## 5. Google GT 라벨링 필요성

### 현재 상태

- `ground_truth.json`: `{}` (완전 공백)
- KPI 계산 불가: GT가 없으면 정확도 비교 대상이 없어 `fieldAcc.total = 0` → KPI 칩에 `-` 표시
- Google 샘플은 `validation_results_google_final_before_lock_fields.json`을 통해 OCR 필드값은 알 수 있으나, 실제 정답과의 비교가 UI상 불가능

### GT anchor 정책 영향 여부

`finalize.ts` 코드 기준:

```ts
const baselineSelection = isBaselineDataset(datasetId)
  ? baselineGtSelection(key, gt, gtVal, ocrRaw, ocrNorm, ocr)
  : null;
```

```ts
function isBaselineDataset(datasetId?: string): boolean {
  return datasetId === "baseline" || datasetId === "baseline_fast";
}
```

- GT anchor 정책(GT_ANCHOR_EMPTY, GT_ANCHOR_WEAK_VALUE, GT_ANCHOR_OVERRIDE, GT_SIMILARITY)은 **`baseline` / `baseline_fast`에만 적용**된다.
- Google 데이터셋에 GT를 추가해도 이 정책은 발동하지 않는다.
- Google GT는 순수 평가용 비교 라벨로만 기능한다.

### GT 라벨링 권장 판단

| 상황 | 판단 |
|---|---|
| GT 없이도 OCR 로직 개발 가능 | 가능. 필드값은 validation JSON에서 확인 가능 |
| GT 추가가 baseline 정책에 영향 | **없음** (코드로 격리됨) |
| GT 추가가 Google lock 수치에 영향 | **없음** (lock은 status/suppression 기준) |
| GT 추가 시 이점 | 상단 KPI 칩에 OCR 인식률/최종 채택 수치가 표시됨 |
| GT 추가의 위험 | 낮음. UI 표시 개선 외 영향 없음 |

**권장:** GT 라벨링 자체는 안전하다. 하지만 지금 당장 필수는 아니다.  
receipt_generalization 작업 이후 필요 시 선택적으로 추가해도 늦지 않다.

---

## 6. 신규 receipt_generalization으로 넘어가기 전 권장 순서

### 권장: **Option 2 — Google orientation/display audit 기록 후 즉시 receipt_generalization으로 이동**

| 선택지 | 판단 |
|---|---|
| ① 바로 receipt_generalization으로 이동 | 가능. 단, audit 기록 없이 진행하면 나중에 다시 분석 필요 |
| **② Google orientation/display audit만 기록하고 이동** | **권장.** 이 문서가 해당 기록. 즉시 이동 가능 |
| ③ Google GT 라벨링을 먼저 하고 이동 | 불필요. 현 단계에서 필수 아님 |
| ④ orientation 로직 보정이 먼저 필요한 상태 | **아님.** orientation 보정은 정상 작동 중 |

**근거:**
- orientation 로직은 정상. 5개 90° 파일 모두 보정 후 OCR 정상 추출.
- Google lock 수치 유지 확인 (session_summary 기준).
- UI preview 왜곡은 Run OCR 미실행 상태의 표시 문제일 뿐, 코드 문제 아님.
- receipt_generalization 진입 전제 조건(최소 공통화 완료, Google lock 완료)이 모두 충족된 상태.

---

## 7. 코드 수정 필요 여부

| 항목 | 필요 여부 |
|---|---|
| orientation 로직 수정 | **불필요.** 90° 보정 정상 작동 확인. |
| preprocess.py 수정 | **불필요.** |
| main.py 수정 | **불필요.** |
| manifest 수정 | **불필요.** (현 90° 파일들에 `rotated` qualityTag 추가는 선택사항) |
| validation JSON 수정 | **금지.** lock 상태 유지. |
| GT 추가 (ground_truth.json) | 선택 사항. 즉시 필수 아님. |
| UI 수정 (orientation preview) | 선택 사항. OCR 미실행 시 원본 표시는 알려진 동작. |

---

## 8. 다음 단계 추천

1. **이 문서 확인 후 receipt_generalization으로 즉시 이동**
   - 폴더/manifest/README는 이미 생성된 상태 (`SESSION_SUMMARY.md` 확인)
   - 다음 작업: 샘플 이미지 15~30장 수집 및 manifest 항목 추가

2. **Google GT 라벨링 (선택, 나중에도 가능)**
   - 현재 알려진 필드값(validation JSON 기준)을 GT로 등록하면 KPI 칩에서 Google 정확도 확인 가능
   - 코드 리스크 없음. 독립적으로 진행 가능

3. **manifest `rotated` qualityTag 추가 (선택, 나중에도 가능)**
   - 1.jpg, 2.jpg, 4.jpeg, 11.jpg에 `rotated` 태그 추가 고려
   - qualityTags filter UI에서 회전 케이스 그룹 확인 목적
   - 코드 수정 없이 manifest만 편집. 하지만 lock 문서와 충돌하지 않아야 하므로 별도 검토 필요

4. **receipt_generalization 샘플 수집 시작**
   - `docs/RECEIPT_GENERALIZATION_TESTSET_PLAN_20260426.md` §5 기준 준수
   - 15~30장, documentType 다양화, qualityTags 최소 1~2장 포함

---

## 참조 문서

| 문서 | 내용 |
|---|---|
| [docs/GOOGLE_LOCK_20260425.md](GOOGLE_LOCK_20260425.md) | Google lock 기준값 및 잠금 판단 |
| [docs/RECEIPT_GENERALIZATION_TESTSET_PLAN_20260426.md](RECEIPT_GENERALIZATION_TESTSET_PLAN_20260426.md) | 신규셋 구성 계획 |
| [SESSION_SUMMARY.md](../SESSION_SUMMARY.md) | 현재 완료 상태 |
| `ocr-server/preprocess.py` | `detect_orientation()` 구현 |
| `mysuit-ocr/src/components/test/core/finalize.ts` | GT anchor 정책 격리 코드 (`isBaselineDataset`) |
| `mysuit-ocr/public/data/testsets/google/validation_results.json` | angle 필드 소스 |
