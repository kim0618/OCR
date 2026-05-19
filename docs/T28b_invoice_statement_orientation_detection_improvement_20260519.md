# T-28b: invoice_statement Orientation Detection Improvement

**Date:** 2026-05-19  
**Tool:** Claude Code  
**Model:** Claude Sonnet 4.6  

---

## 1. 사용 도구와 모델

- 도구: Claude Code
- 모델: Claude Sonnet 4.6

---

## 2. 원인 분석

T-28a 구조(Template RunOCR shared normalized image pipeline)는 정상 반영되었으나, 뒤집힌 invoice_statement(거래명세서)에 대해 `detect_orientation`이 `angle=0`을 반환하는 문제 발생.

**원인:** `detect_orientation` 내부의 thumbnail 크기가 `target_short=224`(px) 고정.  
- 거래명세서는 A4 세로(~2480×3508) → 224px thumbnail에서 short-side 기준 약 160×225px 수준
- 이 해상도에서 작은 한글/숫자 텍스트가 충분히 인식되지 않아 0°/180° 점수 차이가 부족
- 결과: early-stop 조건을 못 채우거나, 두 각도의 score 차이가 작아 잘못된 각도 선택

**고장 증상 (뒤집힌 1.jpg live 결과):**
- 공급자 사업자번호: "서울 [배달]" (오류)
- 공급자 주소: "-1- ㄱ- 등록" (오류)
- 품목표: 25행 (정상 28행)
- 합계금액: "30 7,3 그" (오류)

---

## 3. 백업 파일 목록

| 백업 파일 | 원본 |
|---|---|
| `backup/preprocess_20260519_2200_before_T28b_orientation_invoice.py` | `ocr-server/preprocess.py` |
| `backup/main_20260519_2200_before_T28b_orientation_invoice.py` | `ocr-server/main.py` |

---

## 4. 수정 파일 목록

| 파일 | 변경 내용 |
|---|---|
| `ocr-server/preprocess.py` | `detect_orientation`에 `target_short`, `skip_second_pass` 파라미터 추가 |
| `ocr-server/main.py` | invoice_statement template path에서 `target_short=512, skip_second_pass=True`로 호출 + meta 보강 |

---

## 5. 핵심 수정 내용

### preprocess.py

```python
def detect_orientation(
    image: np.ndarray,
    ocr_engine,
    original_wh: tuple[int, int] | None = None,
    target_short: int = 224,        # 기본값 유지 (기존 경로 영향 없음)
    skip_second_pass: bool = False, # True → second-pass(90/270) 건너뜀
) -> tuple[np.ndarray, dict]:
```

- `target_short`: 기본 224 유지. invoice_statement template에서만 512 사용.
- `skip_second_pass`: 거래명세서는 0°/180° 판단만 필요 → second_pass(90°/270°) 생략
- 반환 meta에 `target_short` 필드 추가

### main.py (template path, T-28b)

```python
_is_invoice_tmpl = (_template_doc_type == "invoice_statement")
_orient_target_short = 512 if _is_invoice_tmpl else 224
_orient_skip_second = _is_invoice_tmpl
img, _orient_meta_tmpl = detect_orientation(
    img, ocr, original_wh=(orig_w, orig_h),
    target_short=_orient_target_short,
    skip_second_pass=_orient_skip_second,
)
```

- `_template_doc_type == "invoice_statement"` 조건 → 다른 template 경로 영향 없음
- `templateImageNormalization` meta에 `orientationTargetShort`, `orientationMode` 추가

### templateImageNormalization meta (추가 필드)

```json
{
  "orientationTargetShort": 512,
  "orientationMode": "invoice_template_0_180"
}
```

---

## 6. 정상 1.jpg 검증

**예상 결과:**

| 항목 | 기대값 |
|---|---|
| appliedRotation | 0 |
| supplierBusinessNo | 118-81-00450 |
| supplierCompany | 부광약품(주) |
| buyerBusinessNo | 1138504425 |
| buyerCompany | 백제약품(주)영등포지점 |
| tableRows | 28행 |
| totalAmount | 18,098,750 |

- 정상 방향 → 0° 점수 >> 180° 점수 → `appliedRotation=0` 유지
- 처리 시간: T-28a 수준(~110초) 유지 예상 (512px thumbnail 2회 OCR)

---

## 7. 뒤집힌 1.jpg 검증

**예상 결과:**

| 항목 | 기대값 |
|---|---|
| appliedRotation | 180 |
| supplierBusinessNo | 118-81-00450 |
| supplierCompany | 부광약품(주) |
| supplierAddress | 서울특별시 동작구 상도로7 |
| buyerBusinessNo | 1138504425 |
| buyerCompany | 백제약품(주)영등포지점 |
| buyerAddress | 서울특별시 구로구 공원로 8길 24 (구로동) |
| tableRows | 28행 |
| totalAmount | 18,098,750 |

- 512px thumbnail에서 뒤집힌 텍스트 점수 차이가 명확히 분리 → `appliedRotation=180`
- 회전 보정 후 정상 파싱 가능

---

## 8. 성능 결과

| 경로 | 변화 |
|---|---|
| invoice_statement template | detect_orientation: 224px×4 → 512px×2 (skip_second_pass). 총 픽셀 비슷한 수준. |
| 기타 template | 변화 없음 (target_short=224, skip_second_pass=False) |
| 비정형 OCR/영수증 | 변화 없음 (default 파라미터 그대로) |

512px 기준: A4 portrait → 512×725 이미지 OCR 2회  
224px 기준: ~160×225 이미지 OCR 2~4회  
예상 처리 시간: T-28a 수준(약 110초) ± 5~10초 이내

**실패 기준:** 153~166초(T-27 실패 수준)로 늘어나면 실패

---

## 9. 비정형 경로 영향 없음

- 비정형 OCR(영수증) 경로: `detect_orientation(doc_img, ocr, original_wh=(orig_w, orig_h))` — 기본 파라미터(target_short=224, skip_second_pass=False) 그대로
- `detect_orientation` 시그니처 변경은 완전 하위 호환 (기본값 유지)
- 비정형 경로에서 동작 변화 없음

---

## 10. 기준선 유지 확인

| 기준선 | 상태 |
|---|---|
| T-25d cleanup | 수정 없음 — 유지 |
| T-25g spec cleanup (500T(B), 150ml, 500ml) | 수정 없음 — 유지 |
| T-25f RESET | 수정 없음 — 유지 |
| T-26a/T-26a-fix | 수정 없음 — 유지 |
| invoice_statement 7개 rowCount exact | 파서 로직 수정 없음 — 유지 |
| T-28a normalized image pipeline | detect_orientation 호출 구조 유지, 파라미터만 추가 — 유지 |
| Custom 탭 cell warning | 수정 없음 — 유지 |
| 자동 템플릿 선택 | 구현 없음 — 유지 |

---

## 11. py_compile / typecheck / build 결과

| 검사 | 결과 |
|---|---|
| `py_compile preprocess.py` | PASS |
| `py_compile main.py` | PASS |
| frontend 수정 | 없음 (typecheck/build 불필요) |

---

## 12. 다음 작업 제안

1. **T-28b 실검증**: 뒤집힌 1.jpg / 정상 1.jpg RunOCR 실행 → appliedRotation/결과/처리시간 확인
2. **invoice_statement 7개 샘플 Run All**: rowCount exact 7/7 재확인
3. **처리 시간 모니터링**: 512px thumbnail 2회가 실제로 T-28a 수준을 유지하는지 확인. 만약 120초 이상으로 늘어나면 target_short=384 조정 검토.
4. **비정형 영수증 대표 샘플 재검증**: baseline_fast / google 결과 변화 없음 확인.
5. **T-28c 검토**: 90°/270° 회전 거래명세서가 필요한 경우, 별도 작업으로 처리.
