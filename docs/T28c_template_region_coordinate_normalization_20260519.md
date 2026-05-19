# T-28c: Template Region Coordinate Normalization

**Date:** 2026-05-19  
**Tool:** Claude Code  
**Model:** Claude Sonnet 4.6  

---

## 1. 사용 도구와 모델

- 도구: Claude Code
- 모델: Claude Sonnet 4.6

---

## 2. 원인

T-28b에서 `appliedRotation=180`이 확인됐음에도 불구하고 field crop 결과가 여전히 잘못됐다.

**핵심 원인:**
- 템플릿 region 좌표는 1.jpg(2483×3511) 기준으로 저장됨
- 현재 업로드된 1-1.jpg는 3000×4000 (스마트폰 촬영, 더 큰 이미지)
- `main.py`는 region 좌표를 normalized image에 **스케일 변환 없이 직접 적용**하고 있었음

**예시 (field_1 합계금액):**
- 템플릿 y=405 in 3511px → 11.5% 위치
- 1-1.jpg에서 y=405 직접 사용 → 10.1% 위치 (틀림)
- 1-1.jpg에서 y=461 사용해야 함 → 11.5% 위치 (정확)

**field_9 (합계금액)의 경우 오차가 매우 큼:**
- 템플릿 y=3155 → 89.9% 위치
- 1-1.jpg 직접 사용: y=3155 → 78.9% (10% 오차, ~440px 어긋남)
- 스케일 적용 후: y=3594 → 89.8% (정확)

---

## 3. 백업 파일 목록

| 백업 파일 | 원본 |
|---|---|
| `backup/main_20260519_2300_before_T28c_template_coordinate_normalization.py` | `ocr-server/main.py` |

---

## 4. 수정 파일 목록

| 파일 | 변경 내용 |
|---|---|
| `ocr-server/main.py` | T-28c: region 좌표 스케일 변환 로직 추가 |

---

## 5. 핵심 수정 내용

### 구현 위치

`main.py` template region 루프 직전 (T-28b 정규화 코드 이후, region 루프 이전)

### 스케일 계산 (lines 2017~2035)

```python
# T-28c: template region coordinate normalization
_coord_scale_x = 1.0
_coord_scale_y = 1.0
_tmpl_coord_base = [0, 0]
try:
    _tj_ref_c = locals().get("template_json") or locals().get("_tj") or {}
    if isinstance(_tj_ref_c, dict):
        _img_c = _tj_ref_c.get("image") or {}
        if isinstance(_img_c, dict):
            _ts_w = int(_img_c.get("width") or 0)
            _ts_h = int(_img_c.get("height") or 0)
            if _ts_w > 0 and _ts_h > 0 and (_ts_w != orig_w or _ts_h != orig_h):
                _coord_scale_x = orig_w / _ts_w
                _coord_scale_y = orig_h / _ts_h
                _tmpl_coord_base = [_ts_w, _ts_h]
except Exception:
    pass
```

### 스케일 소스
- `template_json.image.width/height`: 템플릿 저장 시 기록된 원본 이미지 크기
- `orig_w / orig_h`: detect_orientation 이후의 normalized image 크기

### region_list 변환 (lines 2058~2076)

```python
if _coord_scale_x != 1.0 or _coord_scale_y != 1.0:
    def _scale_region_coords(r):
        r2 = dict(r)
        r2["x"] = r.get("x", 0) * _coord_scale_x
        r2["y"] = r.get("y", 0) * _coord_scale_y
        r2["width"] = r.get("width", 0) * _coord_scale_x
        r2["height"] = r.get("height", 0) * _coord_scale_y
        # table.colX (absolute pixel column positions) also scaled
        tbl = r.get("table")
        if isinstance(tbl, dict) and tbl.get("colX"):
            r2["table"] = dict(tbl)
            r2["table"]["colX"] = [cx * _coord_scale_x for cx in tbl["colX"]]
        return r2
    region_list = [_scale_region_coords(r) for r in region_list]
```

### 적용 범위

- `region_list`를 in-place 변환 → 모든 하위 코드 자동 적용:
  - `_ocr_crop_region` (field crops) ✓
  - `_ocr_table_region` (table crops) ✓
  - T-6i 테이블 bounds 파생 코드 (lines 2491~2527) ✓
- `table.colX` (T-6j column guide 절대 픽셀 위치) 스케일 ✓
- `templateImageNormalization` meta에 `coordScaleX`, `coordScaleY`, `coordBaseSize` 추가 ✓

---

## 6. 좌표 변환 기준

| 항목 | 값 |
|---|---|
| Template base (1.jpg) | 2483×3511 |
| 1-1.jpg normalized (after 180° rotation) | 3000×4000 |
| scaleX | 3000/2483 = **1.2082** |
| scaleY | 4000/3511 = **1.1393** |

### 주요 필드 좌표 변환

| field | before (template coords) | after (scaled) | y비율 |
|---|---|---|---|
| field_1 (공급자 사업자번호) | (250, 405, 695, 110) | (302, 461, 840, 125) | 11.5% → 11.5% ✓ |
| field_2 (공급자 상호) | (263, 524, 400, 40) | (318, 597, 483, 46) | 14.9% → 14.9% ✓ |
| field_3 (공급자 주소) | (255, 642, 700, 40) | (308, 731, 846, 46) | 18.3% → 18.3% ✓ |
| field_5 (공급받는자 사업자번호) | (1433, 396, 500, 40) | (1731, 451, 604, 46) | 11.3% → 11.3% ✓ |
| field_9 (합계금액) | (1940, 3155, 477, 75) | (2344, 3594, 576, 85) | 89.9% → 89.8% ✓ |
| table_1 (품목표) | (47, 831, 2300, 2200) | (57, 947, 2779, 2506) | 23.7% → 23.7% ✓ |

→ 비율이 정확히 보존됨 (scale은 비율을 변경하지 않음, 절대 픽셀 위치만 조정)

---

## 7. 뒤집힌 1-1.jpg 검증 (서버 재시작 후 예상 결과)

T-28b에서 확인된 문제:

| field | T-28b 이전 (오류) | T-28c 이후 (예상) |
|---|---|---|
| field_1 공급자 사업자번호 | "서울 [배달]" ✗ | 118-81-00450 (예상) |
| field_2 공급자 상호 | "부광약품(주)" ✓ | 부광약품(주) 유지 |
| field_3 공급자 주소 | "-1 -T - 등록" ✗ | 서울특별시 동작구 상도로7 (예상) |
| field_5 공급받는자 사업자번호 | "추" ✗ | 1138504425 (예상) |
| field_6 공급받는자 상호 | "백제약품(주)영등포지점" ✓ | 백제약품(주)영등포지점 유지 |
| field_7 공급받는자 주소 | "028690211 호 D202 등록..." ✗ | 서울특별시 구로구 공원로 8길 24 (예상) |
| field_9 합계금액 | "30 7,3 그" ✗ | 18,098,750 (예상) |
| table rows | 26행 | 28행 (예상) |
| appliedRotation | 180 ✓ | 180 유지 |

> **주의:** "예상"은 비율 계산 기반 추정. 실제 1-1.jpg의 문서 위치 오프셋에 따라 일부 필드는 여전히 오차가 있을 수 있음.
> 단순 비례 스케일로 완벽히 해결되지 않는 경우 단계 2 (문서 오프셋 보정) 검토 필요.

---

## 8. 정상 1.jpg 검증 (기준선 유지)

1.jpg = template base (2483×3511) → `scale_x=1.0, scale_y=1.0` → region_list **변환 없음**

| 항목 | 예상 |
|---|---|
| appliedRotation | 0 |
| field_1 공급자 사업자번호 | 118-81-00450 |
| field_2 공급자 상호 | 부광약품(주) |
| tableRows | 28행 |
| totalAmount | 18,098,750 |
| 500T(B), 150ml, 500ml (T-25g) | 유지 |
| T-26a 상호 정규화 | 유지 |

---

## 9. 성능 결과

T-28c 추가 연산:
- `locals().get()` 2회 호출: 나노초
- `region_list` comprehension (9~11 items): 마이크로초
- 추가 OCR 호출: **없음** (좌표 계산만)

→ 처리 시간에 유의미한 영향 없음. T-28b 대비 증가 없음.

---

## 10. 기준선 유지 확인

| 기준선 | 상태 |
|---|---|
| T-25d cleanup | 수정 없음 ✓ |
| T-25g spec cleanup (500T(B), 150ml, 500ml) | 수정 없음 ✓ |
| T-25f RESET (Custom 탭 cell warning) | 수정 없음 ✓ |
| T-26a/T-26a-fix 상호 정규화 | 수정 없음 ✓ |
| invoice_statement 7개 rowCount exact | 비템플릿 경로 사용 (T-28c 무영향) ✓ |
| T-28a normalized image pipeline | 유지 ✓ |
| T-28b detect_orientation | 유지 ✓ |
| 비정형 OCR/영수증 경로 | 수정 없음 ✓ |
| py_compile PASS | ✓ |
| frontend 수정 없음 | ✓ |

---

## 11. 단순 스케일로 부족한 경우의 한계

단순 비례 스케일(T-28c)은 **문서가 이미지 프레임을 비례적으로 채우는 경우** 정확하게 동작한다.

만약 1-1.jpg가 다음 조건에 해당하면 잔여 오차가 있을 수 있다:
- 상단/좌측에 고정 여백이 있는 경우 (문서가 (0,0)에서 시작하지 않음)
- 문서 종횡비가 이미지 프레임 종횡비와 다른 경우

**현재 T-28b 결과로 확인된 증거:**
- field_2 (263, 524) 미스케일 상태에서 "부광약품(주)" 정확 → 문서가 (0,0)에 가깝게 위치하는 것으로 추정
- invoice_statement parser가 올바른 결과를 추출 → 문서 내용은 정상 방향으로 정확히 읽힘

**다음 단계 (잔여 오차 있는 경우):**
T-28d: 문서 영역 bounding box 추출 + offset 보정
- 비율 스케일 + 문서 시작 좌표(offX, offY) 오프셋
- 수식: `rx_actual = offX + (rx_template / template_w) * doc_w`

---

## 12. py_compile / typecheck / build 결과

| 검사 | 결과 |
|---|---|
| `py_compile main.py` | **PASS** |
| frontend 수정 | 없음 |
| npm typecheck/build | 불필요 |

---

## 13. 서버 재시작 안내

현재 실행 중인 서버(PID 4656, 시작: 19:33:43)는 T-28c 이전 코드를 로드한 상태다.
T-28c가 적용되려면 서버 재시작이 필요하다.

---

## 14. 다음 작업 제안

1. **서버 재시작 후 뒤집힌 1-1.jpg RunOCR 검증**
   - appliedRotation=180 유지
   - field_1 = 118-81-00450 확인
   - field_9 = 18,098,750 확인
   - tableRows = 28 확인

2. **정상 1.jpg RunOCR 검증**
   - 기준선 전체 유지 확인

3. **잔여 오차 있는 경우: T-28d 문서 오프셋 보정**
   - 단순 스케일로 커버되지 않는 필드가 있으면
   - detect_document로 문서 영역 bbox 추출 → offset 반영

4. **invoice_statement 7개 샘플 Run All 확인**
   - rowCount 7/7 exact 유지 확인 (비템플릿 경로이므로 영향 없을 것으로 예상)
