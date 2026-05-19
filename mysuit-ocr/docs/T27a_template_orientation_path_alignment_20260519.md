# T-27a: Template RunOCR orientation path alignment with existing unstructured OCR flow

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**코드 수정**: `ocr-server/main.py` 1개

---

## 1. 원인 (왜 비정형은 되고 템플릿은 깨졌나)

### 비정형 OCR 경로가 정상 동작하는 이유

비정형/영수증 경로 ([main.py:2050+](ocr-server/main.py#L2050))는 `detect_orientation`을 통해 0/90/180/270 회전 후보를 OCR 점수로 비교하고 가장 좋은 방향으로 이미지를 자동 회전한다:

```python
# main.py:2076 (비정형 경로)
doc_img, orient_meta = detect_orientation(doc_img, ocr, original_wh=(orig_w, orig_h))
```

`detect_orientation` ([preprocess.py:131](ocr-server/preprocess.py#L131))은 small 이미지에 대해 각 방향별 OCR 점수(한글+숫자+conf+line_count)를 계산해 최고 점수 방향으로 원본을 회전한다. 따라서 뒤집힌 입력도 정상 방향으로 복구된다.

### 템플릿 RunOCR 경로가 깨진 실제 원인

템플릿 경로 ([main.py:1975](ocr-server/main.py#L1975) `if region_list:`)에는 `detect_orientation` 호출이 **없었다**. 원본 뒤집힌 이미지에 정상 방향 기준으로 저장된 template region 좌표를 그대로 적용 → 잘못된 영역 crop → 깨진 OCR 결과.

```python
# 수정 전 (문제)
table_rows = _ocr_table_region(img, ocr, region)   # img = 뒤집힌 원본
_tmpl_inv_result = ocr.ocr(img)                    # img = 뒤집힌 원본
```

증상 (뒤집힌 1.jpg):
- 공급자 사업자번호: `IHIY IC` (정상: `118-81-00450`)
- 공급자 상호: `092'860811FC` (정상: `부광약품(주)`)
- 공급받는자 사업자번호: `2C)V61282a 11` (정상: `1138504425`)
- 품목표 rowCount: 22 (정상: 28)

---

## 2. 비정형 경로와 템플릿 경로 차이 요약

| 단계 | 비정형 경로 | 템플릿 경로 (수정 전) | 템플릿 경로 (수정 후) |
|----|-----------|------------------|------------------|
| detect_document | ✓ | ✗ (region 좌표 사용) | ✗ (region 좌표 사용) |
| **detect_orientation** | ✓ | **✗ (누락)** | **✓ (T-27a 추가)** |
| deskew | ✓ | ✗ | ✗ |
| CLAHE / 리사이즈 | ✓ | ✗ | ✗ |
| OCR 입력 | 정상화된 ocr_img | 원본 (뒤집힘 가능) | 정상화된 img |

---

## 3. 백업 파일 목록

```
ocr-server/backup/main_20260519_1631_before_T27a_template_orientation_path_alignment.py
```

---

## 4. 수정 파일 목록

| 파일 | 변경 내용 |
|-----|---------|
| `ocr-server/main.py` | `if region_list:` 진입 직후, region for-loop 직전에 `detect_orientation` 호출 블록 추가 |

invoice_statement.py, preprocess.py, frontend, preprocessing_policy.py — **전부 미변경**

---

## 5. 핵심 수정 내용

[main.py:1975](ocr-server/main.py#L1975) `if region_list:` 블록 진입 직후, region for-loop 직전에 추가:

```python
if region_list:
    # === 템플릿 영역 기반 OCR ===
    # T-27a: 비정형 경로와 동일한 detect_orientation을 템플릿 경로에도 적용
    _t_orient_tmpl0 = time.time()
    try:
        img, _orient_meta_tmpl = detect_orientation(img, ocr, original_wh=(orig_w, orig_h))
        _orient_angle_tmpl = int(_orient_meta_tmpl.get("angle", 0) or 0)
        orig_h, orig_w = img.shape[:2]  # 회전 후 새 크기로 갱신
        timings["template_detect_orientation_ms"] = _ms(time.time() - _t_orient_tmpl0)
        timings["template_orientation_angle"] = _orient_angle_tmpl
        if _orient_angle_tmpl != 0:
            print(f"[template] orientation auto-corrected: angle={_orient_angle_tmpl}")
    except Exception as _orient_tmpl_e:
        print(f"[template] detect_orientation failed (using original image): {_orient_tmpl_e}")
        timings["template_detect_orientation_error"] = str(_orient_tmpl_e)

    for idx, region in enumerate(region_list):
        ...
```

### 설계 원칙
1. **새 알고리즘 추가 없음** — 비정형 경로에서 검증된 `detect_orientation` 재사용
2. **정상 입력 회귀 방지** — 정상 방향 입력에서 `detect_orientation`은 angle=0을 추천 → 회전 없음 → 결과 동일
3. **안전망** — try/except로 detect_orientation 실패 시 원본 이미지 fallback
4. **OCR 좌표 일관성** — 회전 후 `orig_h`/`orig_w` 갱신, region 좌표는 정상 방향 기준이므로 그대로 작동
5. **비정형 경로 무영향** — 패치는 `if region_list:` 블록 안에만 추가 (`else:` 블록은 그대로)

---

## 6. 정상 1.jpg 검증

`detect_orientation`이 angle=0을 추천하면 이미지 변경 없음 → 기존 결과 그대로:

| 필드 | 기대값 (T-26a-fix 기준) |
|-----|-----------------------|
| 공급자 사업자번호 | `118-81-00450` |
| 공급자 상호 OCR 원본 | `부광 약 품(주)` |
| 공급자 상호 최종값 | `부광약품(주)` |
| 공급받는자 사업자번호 | `1138504425` |
| 공급받는자 상호 최종값 | `백제약품(주)영등포지점` |
| 품목표 rowCount | 28 |
| T-25d cleanup (qty 360, amount space) | 유지 |
| T-25g spec cleanup (500T(B), 150ml, 500ml) | 유지 |

---

## 7. 뒤집힌 1.jpg 검증

`detect_orientation` → angle=180 추천 → image 180도 회전 → 정상 방향으로 복구 → 이후 region crop이 정상 작동.

| 필드 | Before (수정 전) | After (T-27a) |
|-----|----------------|---------------|
| 공급자 사업자번호 | `IHIY IC` (깨짐) | **`118-81-00450`** (기대) |
| 공급자 상호 최종값 | `092'860811FC` (깨짐) | **`부광약품(주)`** (기대) |
| 공급받는자 사업자번호 | `2C)V61282a 11` (깨짐) | **`1138504425`** (기대) |
| 공급받는자 상호 최종값 | 깨짐 | **`백제약품(주)영등포지점`** (기대) |
| 품목표 rowCount | 22 (깨짐) | **28** (기대) |

서버 재시작 후 live 검증 필요.

---

## 8. 비정형 영수증 경로 영향 없음 확인

| 항목 | 결과 |
|-----|------|
| 비정형 `else:` 블록 (line 2050+) | 미변경 |
| 비정형 detect_orientation 호출 (line 2076) | 미변경 |
| receipt parser | 미변경 |
| preprocessing_policy.py | 미변경 |

비정형 경로의 자동 방향 보정 동작은 **그대로 유지**됨.

---

## 9. T-25 / T-26 기준선 유지 확인

| 기준선 | 상태 |
|-------|------|
| T-25d amount comma-space cleanup | ✓ invoice_statement.py 미변경 |
| T-25d quantity trailing symbol cleanup | ✓ 미변경 |
| T-25g spec trailing cleanup (500T(B), 150ml, 500ml) | ✓ 미변경 |
| T-25f RESET (Custom 탭 cell warning 없음) | ✓ OcrResultPanel.tsx 미변경 |
| T-26a company normalization | ✓ 미변경 |
| T-26a-fix OCR 원본/최종값 분리 | ✓ 미변경 |
| invoice_statement rowCount 7/7 exact | ✓ parser 미변경 |
| itemName 자동 보정 금지 | ✓ 준수 |
| Custom 탭 warning UI 재도입 금지 | ✓ 준수 |

---

## 10. py_compile / typecheck / build 결과

| 항목 | 결과 |
|-----|------|
| `py_compile main.py` | **OK** |
| `detect_orientation` 시그니처 호환성 | **OK** (image, ocr_engine, original_wh) |
| T-27a 코드 위치 (region for-loop 직전) | **확인됨** |
| `npm run typecheck` | **PASS** (frontend 미변경) |
| `npm run build` | **PASS** |

---

## 11. 한계점

- `detect_orientation`은 OCR 엔진을 한 번 더 호출 → 템플릿 RunOCR 처리 시간 소폭 증가 (small thumb 224px 기준 수십~수백 ms)
- `detect_orientation`이 잘못된 방향을 추천하는 케이스는 비정형 경로와 동일한 한계 (그러나 검증된 함수)
- `original_b64` (History "전처리 전" 표시용)는 회전 전 원본 그대로 — 일관성을 위해 의도적으로 유지

---

## 12. 다음 작업 제안

| 작업 | 내용 |
|-----|------|
| **T-27a-followup (즉시)** | 서버 재시작 후 1.jpg 정상 + 뒤집힌 1.jpg live RunOCR 검증. 비정형 receipt 샘플도 회귀 없음 확인. |
| **T-27b** | 만약 일부 케이스에서 회귀가 발견되면 doc_type=invoice_statement 한정 또는 quality flag 기반 guard 추가 검토 (현재는 모든 템플릿 RunOCR에 일괄 적용) |
| **RUNOCR-AUTO-TEMPLATE-1** | orientation 보정 이후 documentType + anchor 기반 template 추천 |
