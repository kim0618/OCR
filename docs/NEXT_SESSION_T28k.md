# T-28k: Template Field Extraction via Warped OCR Lines

**작성일:** 2026-05-19  
**도구:** Claude Code / Claude Sonnet 4.6  
**프로젝트:** OCR  

---

## 1. 이 채팅에서 한 작업 전체 요약

### 배경
OCR 제품. 두 경로가 있다:
- **비정형 경로**: 영수증 등, 전체 OCR → 파서 추출 (건드리지 않음)
- **템플릿 경로**: 사용자가 정의한 region 좌표로 field crop → OCR 추출

테스트 이미지:
- `1.jpg`: 거래명세서 스캔본 (2483×3511). 템플릿(TPL-31D13CF3)의 기준 이미지.
- `1-1.jpg`: 같은 문서를 스마트폰으로 뒤집어서 촬영 (3000×4000). 어떤 이미지도 1.jpg와 동일한 결과가 나와야 한다.

목표 결과 (1.jpg 기준):
- 공급자 사업자번호: 118-81-00450
- 공급자 상호: 부광약품(주)
- 공급자 주소: 서울특별시 동작구 상도로7
- 공급자 성명: LEE WOOHYUN
- 공급받는자 사업자번호: 1138504425
- 공급받는자 상호: 백제약품(주)영등포지점
- 공급받는자 주소: 서울특별시 구로구 공원로 8길 24 (구로동)
- 공급받는자 성명: 김승관
- 품목표: 28행
- 합계금액: 18,098,750

---

### T-28a (완료)
Template 경로에서 detect_orientation 적용 누락 → region crop 전에 방향 정규화 추가.  
`templateImageNormalization` 메타 추가.

### T-28b (완료)
뒤집힌 1-1.jpg에서 detect_orientation이 angle=0 반환.  
원인: 224px thumbnail에서 거래명세서 텍스트가 0°/180° 점수 차이 부족.  
해결: invoice_statement template에 한해 512px thumbnail + 0°/180° 비교만.  
결과: `appliedRotation=180` 확인.

### T-28c (완료, 효과 제한적)
`template.image.width/height` 기반 scaleX/scaleY 적용.  
결과: 단순 비율 스케일로는 부족. 1-1.jpg에 문서 상단에 "거래명세서" 타이틀/헤더 행이 있어 수직 오프셋(~350px) 발생. 스케일만으로 보정 불가.

### T-28d (완료)
파서(invoice_statement parser)가 올바르게 추출한 값으로 template field를 패치.
- 사업자번호: party_candidates.bizs + ocr_lines_raw 검색 + 체크섬 검증
- 주소: warped OCR space에서 파서가 supplier/buyer를 split_x 기준으로 분리 → 정확
- 합계금액, 상호: 파서 출력 활용

### T-28e (완료)
Template 경로에서도 processed_image를 회전/정렬된 이미지로 인코딩 → 화면 정방향 표시.

### T-28h (완료) ← 핵심 구조
**배경**: 올바른 OCR 제품 구조 분석.  
업로드 이미지가 어떤 각도/크기든 → 템플릿 기준 이미지 공간으로 정렬 → 템플릿 좌표 적용.

**구현**:
1. `_generate_reference_ocr()`: 템플릿 저장 시 기준 이미지 OCR 실행 → `template_json.referenceOcr`에 저장
2. 기존 9개 invoice_statement template에 referenceOcr migration 완료 (TPL-31D13CF3: 263개)
3. 런타임 pipeline:
   - 업로드 이미지 전체 OCR 1회 → `_tmpl_ocr_lines`
   - 텍스트 앵커 매칭: 160쌍, RANSAC 121 inliers
   - `warpPerspective` → template 공간으로 정렬
   - OCR lines를 H 행렬로 변환 → `_tmpl_warped_ocr_lines`
   - invoice_statement parser에 `_tmpl_warped_ocr_lines` 재사용 (2차 OCR 없음)

**결과**: 총 OCR 1회, 처리 ~76초, 121 inliers (ORB 방식 67에서 2배 향상).

### 현재 문제 (T-28k로 해결할 것)
- 40px 높이 narrow field에서 homography ±20-30px 잔차로 직접 pixel crop이 텍스트를 놓침
- 박스 overlay 위치가 실제 텍스트와 ±20-130px 어긋남
- T-28i(empty fallback, margin=20) + T-28j(+25px crop margin)으로 임시 대응 중 → 여전히 불완전

---

## 2. 검증된 데이터 (OCR-line matching 오프라인 테스트)

`_tmpl_warped_ocr_lines`에서 field center에 가장 가까운 텍스트를 찾는 방식을 검증:

```
x 조건: rx <= wcx <= rx+rw  (region 수평 범위 내)
y 조건: cy - max(rh*2, 60) <= wcy <= cy + max(rh*2, 60)
선택: 위 범위 내에서 field center에 가장 가까운 텍스트
```

**1.jpg (기준 이미지, 179 inliers):**

| 필드 | 결과 | 위치 오차 |
|---|---|---|
| 공급자 사업자번호 | 118-81-00450 ✓ | dy=+16px |
| 공급자 상호 | 부광약품(주) ✓ | dy=+12px |
| 공급자 주소 | 서울특별시동작구 상도로7 ✓ | dy=+25px |
| 공급자 성명 | LEE WOOHYUN ✓ | dy=+22px |
| 공급받는자 사업자번호 | 1138504425 ✓ | dy=+23px |
| 공급받는자 상호 | 백제약품(주)영등포지점 ✓ | dy=+2px |
| 공급받는자 주소 | 서울특별시 구로구 공원로 8길 24 (구로동) ✓ | dy=+19px |
| 공급받는자 성명 | 김승관 ✓ | dy=+21px |
| 합계금액 | 18,098,750 ✓ | dy=+9px |

**→ 9/9 전부 정확**

**1-1.jpg (뒤집힌 이미지, 121 inliers):**

| 필드 | 결과 | 위치 오차 |
|---|---|---|
| 공급자 사업자번호 | 118-81-00450 ✓ | dy=+3px |
| 공급자 상호 | 부 광약 품(주) △ (T-26a 정규화됨) | dy=+5px |
| **공급자 주소** | **'이' ✗** | **dy=+126px (범위 밖)** |
| 공급자 성명 | LEE WOOHYUN ✓ | dy=+25px |
| 공급받는자 사업자번호 | 1138504425 ✓ | dy=+10px |
| 공급받는자 상호 | 백제약품(주)영등포지점 ✓ | dy=-13px |
| 공급받는자 주소 | 서울특별시 구로구 공원로 8길 24 (구로동) ✓ | dy=+7px |
| 공급받는자 성명 | 김승관 ✓ | dy=+11px |
| 합계금액 | 18,098,750 ✓ | dy=+17px |

**→ 8/9 정확. 공급자 주소 실패 → T-28d 파서로 보완 → 9/9**

**박스 위치**: 실제 OCR line 좌표를 bbox로 사용하면 ±2~25px 내 시각적 정렬 가능.  
공급자 주소는 매칭 실패 시 bbox=템플릿 좌표 (값은 T-28d로 정확).

---

## 3. 구현할 작업: T-28k

### 핵심 변경

**기존 방식 (T-28j + T-28i)**:
```python
# T-28j: pixel crop with +25px margin
_tmpl_xm = 25 if _homography_applied else 0
text, conf = _ocr_crop_region(img, ocr, rx-_tmpl_xm, ry-_tmpl_xm, rw+2*_tmpl_xm, rh+2*_tmpl_xm)
bbox = [rx, ry, rw, rh]  # 항상 템플릿 좌표

# T-28i: empty일 때만 warped OCR lines에서 보완 (margin=20, 부족)
```

**T-28k 방식**:
```python
# homography 성공 + warped OCR lines 있을 때: OCR-line nearest matching
if _homography_applied and _tmpl_warped_ocr_lines:
    cx = rx + rw / 2.0
    cy = ry + rh / 2.0
    y_tol = max(rh * 2.0, 60.0)
    
    best_dist = float('inf')
    best_text = ''
    best_conf = 0.0
    best_bbox = [rx, ry, rw, rh]  # fallback: 템플릿 좌표
    
    for _wp, _wt, _wc in _tmpl_warped_ocr_lines:
        if not _wt or _wc < 0.3:
            continue
        _wxs = [p[0] for p in _wp]
        _wys = [p[1] for p in _wp]
        _wcx = (min(_wxs) + max(_wxs)) / 2
        _wcy = (min(_wys) + max(_wys)) / 2
        if not (rx <= _wcx <= rx + rw):          # 수평 범위 엄격
            continue
        if not (cy - y_tol <= _wcy <= cy + y_tol):  # 수직 허용
            continue
        _dist = abs(_wcx - cx) + abs(_wcy - cy)
        if _dist < best_dist:
            best_dist = _dist
            best_text = _wt
            best_conf = _wc
            best_bbox = [
                int(min(_wxs)), int(min(_wys)),
                int(max(_wxs) - min(_wxs)), int(max(_wys) - min(_wys))
            ]
    
    text, conf = best_text, best_conf
    actual_bbox = best_bbox  # 실제 텍스트 위치

else:
    # homography 없거나 warped lines 없을 때: 기존 pixel crop
    text, conf = _ocr_crop_region(img, ocr, rx, ry, rw, rh)
    actual_bbox = [rx, ry, rw, rh]

fields.append({
    "name": name,
    "field_type": field_type,
    "value": text,
    "confidence": conf,
    "bbox": actual_bbox,  # 실제 위치 또는 템플릿 좌표
})
```

### 제거할 것
- **T-28j** (`_tmpl_xm = 25` 관련 코드): T-28k가 대체
- **T-28i** (empty fallback 블록, line ~2314~2340): T-28k가 대체

### 유지할 것
- table field: 기존 `_ocr_table_region` 방식 그대로
- T-28d: OCR-line 매칭 실패(empty) 시 파서 값으로 보완 (기존 그대로)
- T-26a: 상호 정규화 (기존 그대로)
- T-28h: OCR + homography + transform 전체 (건드리지 않음)
- T-28b, T-28c, T-28e: 건드리지 않음

---

## 4. 현재 main.py 라인 번호 (2026-05-19 22:02 기준)

```
line ~2048: T-28b orientation detection
line ~2078: T-28h 시작 (_homography_applied, _tmpl_ocr_lines 초기화)
line ~2089: T-28h Step1 full OCR
line ~2105: T-28h Step2 text anchor matching
line ~2131: T-28h Step3 warpPerspective
line ~2173: T-28h Step4 OCR lines transform → _tmpl_warped_ocr_lines
line ~2193: T-28e processed image 인코딩
line ~2202: T-28c coord scale
line ~2219: _tmpl_img_norm_debug 생성
line ~2257: Region loop 시작
line ~2263: rx, ry, rw, rh 추출
line ~2271: if field_type == "table": (table 분기)
line ~2295: T-28j pixel crop (_tmpl_xm = 25) ← 제거 대상
line ~2311: T-28i empty fallback 시작 ← 제거 대상
line ~2340: T-28i 끝
line ~2364: Parser에 warped OCR lines 재사용
line ~2879: T-28d 파서 패치 시작
line ~2927: _T28D_MAP 정의
```

---

## 5. 작업 순서

### Step 0: 읽기 (수정 전)
```
CLAUDE.md 읽기
SESSION_SUMMARY.md 읽기
main.py line 2257~2350 읽기 (region loop 전체 확인)
main.py line 2879~2960 읽기 (T-28d 확인)
```

### Step 1: 백업
```
backup/main_20260520_before_T28k_ocr_line_extraction.py
```

### Step 2: 오프라인 테스트 (서버 재시작 불필요)

코드 수정 전, Python 스크립트로 T-28k 로직을 검증한다.

```python
# 검증 스크립트 핵심 구조
import json, cv2, numpy as np
from collections import Counter
import sys; sys.path.insert(0, 'c:/OCR/ocr-server')
from main import get_ocr_engine, _parse_ocr_lines

# 1. 템플릿 로드 (TPL-31D13CF3)
# 2. 이미지 로드 + 회전
# 3. Full OCR → text anchor → homography → transform lines
# 4. 각 field에 대해 T-28k 로직 적용
# 5. value, bbox 출력

# 기대 결과:
# 1.jpg:    9/9 필드 정확, bbox dy ≤ ±30px
# 1-1.jpg:  8/9 직접 매칭 (공급자 주소 empty 허용, T-28d가 보완)
```

### Step 3: main.py 수정

1. Region loop에서 non-table field 처리를 T-28k로 교체
2. T-28j (_tmpl_xm) 제거
3. T-28i 블록 제거

### Step 4: py_compile PASS 확인

### Step 5: 서버 재시작 → live RunOCR

1.jpg RunOCR:
- 기존 결과 동일 (9/9)
- 박스 위치: 실제 텍스트 위치

1-1.jpg RunOCR:
- field_1 = 118-81-00450
- field_5 = 1138504425
- field_9 = 18,098,750
- 품목표 = 28행
- 박스 위치: 이전보다 텍스트에 가깝게 정렬

### Step 6: 7개 샘플 Run All

invoice_statement rowCount: 1.jpg=28, 2.pdf=13, 3.pdf=1, 4.pdf=1, 5.pdf=6, 6.pdf=6, 7.pdf=1

---

## 6. 반드시 지킬 조건

1. **비정형 OCR/영수증 경로 (else 브랜치) 수정 금지**
2. **T-28h (full OCR + homography + transform) 수정 금지**
3. **T-28b (orientation) 수정 금지**
4. **T-28d (파서 패치) 수정 금지** — T-28k 이후 fallback으로 유지
5. **T-26a (상호 정규화) 수정 금지**
6. **table field: 기존 `_ocr_table_region` 방식 유지**
7. **invoice_statement 7개 rowCount exact 유지**
8. **py_compile PASS**
9. **코드 수정 전 backup 필수**
10. **수정은 main.py 단독**
11. **frontend 수정 금지**
12. **성공 기준**: live 1-1.jpg에서 field_1=118-81-00450 확인 (예상 보고 금지)

---

## 7. 현재 templates.json 상태

경로: `c:/OCR/ocr-server/data/templates.json`

| Template ID | referenceOcr | 비고 |
|---|---|---|
| TPL-31D13CF3 | 263개 ✓ | 거래_1, 핵심 테스트 템플릿 |
| TPL-B8936EDE | 95개 ✓ | |
| TPL-5A8C2374 | 185개 ✓ | |
| TPL-95328E52 | 51개 ✓ | |
| TPL-FD07531C | 67개 ✓ | |
| TPL-E4B15A22 | 66개 ✓ | |
| TPL-3AFD383E | 39개 ✓ | |
| TPL-A4585BC7 | 없음 | table-only template |
| TPL-A6B12CED | 없음 | table-only template |

---

## 8. 알려진 한계

- **공급자 주소 박스 위치**: 1-1.jpg에서 OCR line이 search range 밖 (dy=+126px) → 값은 T-28d로 정확, 박스는 템플릿 좌표 근사
- **이 한계를 완전히 해결**하려면 표 선(line) 기반 정렬이 필요 (다음 단계)
- 그 외 8개 필드는 ±2~25px 내 시각적 정렬 가능

---

## 9. 참고: T-28h 핵심 변수

```python
_homography_applied: bool       # True = T-28h 성공
_tmpl_H: np.ndarray | None      # 3×3 homography 행렬
_tmpl_ocr_lines: list           # OCR lines in rotated image space
_tmpl_warped_ocr_lines: list    # OCR lines transformed to warped space
# 형식: [(pts_list, text, confidence), ...]
# pts_list = [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
```

T-28d 현재 패치 대상:
```python
_T28D_MAP = {
    "공급자 사업자 번호": "supplierBusinessNo",
    "공급자 사업자번호": "supplierBusinessNo",
    "공급자 주소": "supplierAddress",
    "공급자 사업장 주소": "supplierAddress",
    # 성명(representative)은 파서가 공급자/수신자 혼동 → 패치 제외
    "공급받는자 사업자 번호": "buyerBusinessNo",
    "공급받는자 사업자번호": "buyerBusinessNo",
    "공급받는자 주소": "buyerAddress",
    "공급받는자 사업장 주소": "buyerAddress",
    "합계금액": "totalAmount",
    "합계": "totalAmount",
}
```
