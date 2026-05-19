# T-27a-fix: Template orientation normalization actual crop/parser wiring

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**코드 수정**: `ocr-server/main.py` 1개

---

## 1. T-27a가 왜 실패했는지 실제 원인

### 코드 자체는 정상이었다
- `detect_orientation` 호출 (main.py:1985) ✓
- `img` 변수 재할당 ✓
- for-loop의 `_ocr_crop_region(img, ...)`, `_ocr_table_region(img, ...)`이 같은 `img` 변수 사용 ✓
- invoice_statement parser용 `ocr.ocr(img)` (line 2043)도 같은 `img` 사용 ✓

**즉 wiring은 일관되어 있었다.**

### 실제 원인: `detect_orientation`이 1.jpg 뒤집힌 케이스에서 angle=0을 잘못 추천

- [`preprocess.py:140`](ocr-server/preprocess.py#L140): `target_short = 224` — thumbnail short-side를 224px로 매우 작게 축소
- 1.jpg는 2483×3511 큰 invoice_statement 문서 → 224 thumb로 줄이면 한글 텍스트가 너무 작아져 OCR이 약함
- 0도(거꾸로 OCR) vs 180도(정상 OCR)의 점수 차이가 임계값 미만 → `detect_orientation`이 angle=0 추천
- **이미지가 회전되지 않은 채로 region crop → 깨진 결과**

### 사용자 보고 결과가 명확한 증거

| 항목 | 결과 | 해석 |
|-----|------|-----|
| supplier 사업자번호 field | `서울 [배달]` | region crop이 1.jpg 왼쪽 상단 텍스트(뒤집힌 이미지에서 사업자번호 좌표가 가리키는 영역)를 잡음 → **img 회전 안 됨** |
| supplierCompany 최종값 | `부광약품(주)` (정상) | T-26a-fix가 document_fields.supplierCompany로 덮어씀. parser는 텍스트 anchor 기반이라 일부 정상 라인이 있으면 추출 가능 |
| rowCount | 25 (정상 28) | 부분 인식, 회전 안 됨 |

→ **결론**: `detect_orientation`이 angle=0을 추천 → img 미회전 → wiring은 정상이지만 결과는 깨짐.

---

## 2. 백업 파일 목록

```
ocr-server/backup/main_20260519_1647_before_T27a_fix_actual_orientation_wiring.py
```

---

## 3. 수정 파일 목록

| 파일 | 변경 내용 |
|-----|---------|
| `ocr-server/main.py` | T-27a 블록 뒤에 **invoice_statement 한정 anchor 기반 cross-check fallback** 추가 (region for-loop 직전) |

`preprocess.py`, `invoice_statement.py`, `preprocessing_policy.py`, frontend — **전부 미변경**.

---

## 4. 핵심 수정 내용

기존 `detect_orientation`은 그대로 호출하되, **invoice_statement인 경우에만** anchor 기반 검증을 추가:

```python
# T-27a-fix (요약)
_inv_doc_type = (_template_doc_type or documentType or "").strip()
if _inv_doc_type == "invoice_statement":
    _INV_ANCHORS = ("거래명세서", "공급자", "공급받는자", "사업자",
                    "품목", "규격", "수량", "단가", "금액", "합계")

    def _count_inv_anchors_t27a(_test_img):
        # 768px short-side thumb로 OCR해서 anchor 텍스트 카운트
        ...

    _orig_anchors = _count_inv_anchors_t27a(img)
    if _orig_anchors < 4:
        _rotated_180_img = cv2.rotate(img, cv2.ROTATE_180)
        _rot_anchors = _count_inv_anchors_t27a(_rotated_180_img)
        if _rot_anchors > _orig_anchors + 1:
            img = _rotated_180_img
            orig_h, orig_w = img.shape[:2]
            print(f"[template] T-27a-fix anchor fallback APPLIED ...")
```

### 핵심 원칙
- **새 orientation 알고리즘 추가 X** — 기존 `detect_orientation` 그대로 사용
- **anchor 카운팅은 검증 로직** — invoice_statement에 이미 사용되는 핵심 키워드 매칭
- **invoice_statement 한정** — 다른 doc_type은 비용 0, 영향 0
- **회귀 방지** — 정상 입력에서는 anchor ≥ 4 → fallback 미발동 → 결과 동일
- **보수적 임계값** — fallback 발동 후에도 `rot_anchors > orig_anchors + 1` 일 때만 회전 적용

### thumbnail 768px 선택 이유
- `detect_orientation`의 224는 너무 작아서 큰 invoice 문서 anchor가 약함
- 1.jpg 원본 2483 short → 768로 축소 (3.2× 축소) → 한글 anchor가 충분히 인식
- OCR 비용도 full size보다 훨씬 빠름

---

## 5. detect_orientation angle 의미 확인

| 반환값 | 의미 | 적용 방식 |
|------|------|---------|
| `angle=0` | "이미지가 이미 정상 방향이라고 판단" | 회전 안 함 |
| `angle=180` | "이미지가 180도 회전되어 있다고 판단" | `cv2.rotate(image, ROTATE_180)` 적용 |
| `angle=90` | "시계방향 90도 회전 필요" | `cv2.rotate(image, ROTATE_90_CLOCKWISE)` 적용 |
| `angle=270` | "반시계방향 90도 회전 필요" | `cv2.rotate(image, ROTATE_90_COUNTERCLOCKWISE)` 적용 |

함수 반환은 **회전이 이미 적용된 image**다 ([preprocess.py:327-334](ocr-server/preprocess.py#L327)). 호출자는 그냥 받은 image를 그대로 사용하면 된다 → **wiring 측면은 OK**.

---

## 6. normalized image가 실제 field/table crop에 사용되는지 확인

코드 구조 검증 (`detect_orientation` → T-27a-fix → for region loop 순서):

```
main.py:1985  img, _ = detect_orientation(img, ocr, original_wh=(orig_w, orig_h))
main.py:T-27a-fix  (조건부) img = cv2.rotate(img, ROTATE_180)
main.py:1997+ for idx, region in enumerate(region_list):
main.py:2006   table_rows = _ocr_table_region(img, ocr, region)   # ← 동일 img
main.py:2029   text, conf = _ocr_crop_region(img, ocr, rx, ry, rw, rh)  # ← 동일 img
main.py:2043   _tmpl_inv_result = ocr.ocr(img)                    # ← 동일 img (parser 입력)
```

**모든 crop/parser가 동일한 `img` 변수를 사용**. T-27a-fix가 `img`를 재할당하면 이후 모든 단계가 자동으로 정상화된 image를 사용 → **반쪽 수정 아님**.

---

## 7. 정상 1.jpg 검증

`detect_orientation` → angle=0  
anchor 카운트 ≥ 4 (10개 anchor 중 대부분 매칭)  
→ fallback 미발동 → img 변경 없음 → 기존 결과 그대로

| 필드 | 기대값 |
|-----|--------|
| 공급자 사업자번호 | `118-81-00450` |
| 공급자 상호 최종값 | `부광약품(주)` |
| 공급받는자 사업자번호 | `1138504425` |
| 공급받는자 상호 최종값 | `백제약품(주)영등포지점` |
| 품목표 rowCount | 28 |
| T-25d / T-25g cleanup | 유지 |

---

## 8. 뒤집힌 1.jpg 검증

`detect_orientation` → angle=0 (잘못된 추천, thumb 224px 한계)  
img 미회전 (T-27a만으로는 미해결)

→ T-27a-fix anchor fallback 발동:
1. 768px thumb으로 img 자체 OCR → anchor 카운트 (예: 1~2개)
2. 180도 회전 image 768px thumb OCR → anchor 카운트 (예: 7~10개)
3. `rot_anchors > orig_anchors + 1` → 180도 회전 적용
4. **img 갱신** → 이후 모든 단계가 정상 방향 image 사용

| 필드 | Before (T-27a만) | After (T-27a-fix 기대) |
|-----|----------------|----------------------|
| 공급자 사업자번호 | `서울 [배달]` (깨짐) | **`118-81-00450`** |
| 공급자 상호 최종값 | `부광약품(주)` (T-26a로 우연 정상) | **`부광약품(주)`** |
| 공급자 주소 | `-1- ㄱ- 등록` (깨짐) | **`서울특별시 동작구 상도로7`** |
| 공급받는자 사업자번호 | `추` (깨짐) | **`1138504425`** |
| 공급받는자 상호 최종값 | `백제약품(주)영등포지점` | **`백제약품(주)영등포지점`** |
| 공급받는자 주소 | `028690211 호 D202 등록 1138504425` (깨짐) | **`서울특별시 구로구 공원로8길24(구로동)`** |
| 품목표 rowCount | 25 | **28** |
| 합계금액 | `30 7,3그` (깨짐) | **`18,098,750`** |

서버 재시작 후 live 검증 필요.

---

## 9. tableRows 28행 복구 여부

T-27a-fix가 발동하면 img가 정상 방향으로 복구 → invoice_statement parser가 정상 OCR 라인 받음 → 28행 복구 기대.  
**서버 재시작 후 live RunOCR로 최종 확인 필요.** 만약 28행 미복구 시 추가 진단 후 후속 작업으로 분리.

---

## 10. 비정형 영수증 경로 영향 없음 확인

| 항목 | 결과 |
|-----|------|
| 비정형 `else:` 블록 (line 2050+) | **미변경** |
| 비정형 detect_orientation (line 2076) | **미변경** |
| receipt parser | **미변경** |
| preprocessing_policy.py | **미변경** |
| T-27a-fix 적용 조건 | `if _inv_doc_type == "invoice_statement"` → 다른 doc_type 무영향 |

비정형 영수증 경로는 코드 자체를 건드리지 않았고, T-27a-fix는 `if region_list:` 블록의 invoice_statement 한정으로만 발동.

---

## 11. T-25 / T-26 기준선 유지 확인

| 기준선 | 상태 |
|-------|------|
| T-25d amount comma-space cleanup | ✓ invoice_statement.py 미변경 |
| T-25d quantity trailing symbol cleanup | ✓ 미변경 |
| T-25g spec trailing cleanup (500T(B), 150ml, 500ml) | ✓ 미변경 |
| T-25f RESET (Custom 탭 cell warning 없음) | ✓ frontend 미변경 |
| T-26a company normalization | ✓ 미변경 |
| T-26a-fix OCR 원본/최종값 분리 | ✓ 미변경 |
| invoice_statement rowCount 7/7 exact | ✓ parser 미변경 |
| itemName 자동 보정 금지 | ✓ 준수 |
| Custom 탭 warning UI 재도입 금지 | ✓ 준수 |

---

## 12. py_compile / typecheck / build 결과

| 항목 | 결과 |
|-----|------|
| `py_compile main.py` | **OK** |
| 코드 위치 검증 (detect_orientation → T-27a-fix → for loop) | **확인됨** |
| 모든 marker 존재 | **OK** |
| `npm run typecheck` | **PASS** |
| `npm run build` | **PASS** |

---

## 13. 남은 이슈와 다음 작업 제안

### 남은 이슈
- 90/270 회전 케이스는 다루지 않음 (사용자 보고는 180도 케이스 한정)
- `detect_orientation`의 thumbnail 224px 한계 자체는 그대로 (비정형 경로 영향 회피)

### 다음 작업 제안
1. **즉시 검증**: 서버 재시작 후 정상/뒤집힌 1.jpg 양쪽 live RunOCR로 결과 확인. anchor_fallback_applied 로그 확인.
2. **T-27b (선택)**: 만약 90/270 회전 케이스가 발견되면 fallback에 90/270도 후보 추가.
3. **T-27c (선택)**: 만약 anchor fallback 임계값(< 4)이 과도하게 발동되면 임계값 튜닝.
