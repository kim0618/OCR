# T-27-DIAG: Template RunOCR orientation/performance architecture diagnosis

**생성일**: 2026-05-19  
**사용 도구**: Claude Code (Claude Sonnet 4.6)  
**코드 수정**: **없음** (진단 전용 작업)

---

## 1. 작업 메타

- 사용 도구: Claude Code
- 사용 모델: Claude Sonnet 4.6
- 코드 수정 여부: **수정 없음**
- 파일 롤백 여부: **없음**
- 새 로직 추가 여부: **없음**
- 분석 대상: `ocr-server/main.py`, `ocr-server/preprocess.py`, `ocr-server/extractors/invoice_statement.py`, region crop 함수

---

## 2. 현재 문제 요약

### Symptom (뒤집힌 1.jpg)

| 필드 | 현재 깨진 값 | 정상 기대값 |
|-----|-----------|----------|
| 공급자 사업자번호 | `서울 [배달]` | `118-81-00450` |
| 공급자 상호 최종값 | `부광약품(주)` ✓ **정상** | `부광약품(주)` |
| 공급자 주소 | `-1- ㄱ- 등록` | `서울특별시 동작구 상도로7` |
| 공급자 성명 | `서서` | (대표자명) |
| 공급받는자 사업자번호 | `추` | `1138504425` |
| 공급받는자 상호 최종값 | `백제약품(주)영등포지점` ✓ **정상** | `백제약품(주)영등포지점` |
| 공급받는자 주소 | `028690211 호 D202 등록 1138504425` | `서울특별시 구로구 공원로 8길 24 (구로동)` |
| 품목표 rowCount | 25 | 28 |
| 합계금액 | `30 7,3그` | `18,098,750` |

### Symptom 분석 핵심 단서

- **회사 상호 2개만** 정상 → 다른 모든 필드는 비정상
- 깨진 사업자번호 값 `서울 [배달]`은 정상 방향 1.jpg의 **다른 영역(아마 거래조건/배달지 부근)** 텍스트로 보임 → 회전되지 않은 이미지에 정상 방향 region 좌표를 적용한 결과
- 처리 시간 153~166초 (이전 정상 동작 시 ~60초 수준) → **2~3배 느려짐**

---

## 3. 비정형 OCR 경로 구조 (정상 동작)

`main.py:2173+` `else:` 블록.

```
업로드 image → cv2.imdecode → img
  ↓
detect_document(img) → doc_img (원근 보정)
  ↓
detect_orientation(doc_img, ocr, ...) → 정상 방향 doc_img  ← 자동 회전
  ↓
deskew(doc_img) → doc_deskewed
  ↓
display_max_w=2000 리사이즈, 언샤프 마스크 → display_img (미리보기)
  ↓
ocr_max_w=950 리사이즈 → ocr_img (작은 크기)
  ↓
CLAHE + 언샤프 마스크 → ocr_img 최종
  ↓
ocr.ocr(ocr_img) ← 950px 작은 이미지에 대해 1회 풀 OCR
  ↓
receipt_fields / 금액 추출 등
```

### 왜 비정형 경로가 뒤집힌 이미지도 잘 처리하나
1. `detect_orientation`이 0/90/180/270 후보 OCR 점수 비교 후 최고 점수 방향으로 회전 → 뒤집힌 입력 정상화
2. 이후의 모든 처리(deskew, CLAHE, OCR)는 정상화된 doc_deskewed/ocr_img에 적용 → 깨끗한 입력에 OCR
3. OCR이 950px 작은 이미지에 대해 한 번만 실행 → 속도 빠름

---

## 4. Template RunOCR (region_list) 경로 구조

`main.py:1975+` `if region_list:` 블록.

```
업로드 image → cv2.imdecode → img
  ↓
[T-27a] detect_orientation(img, ocr, ...) → img 재할당 가능   (main.py:1985)
  ↓
[T-27a-fix2] invoice_statement이면 anchor fallback 검사:    (main.py:2003-2098)
  - 768px short-side thumb로 ocr.ocr() → orig_anchors 카운트
  - orig_anchors < 5 이면 cv2.rotate(img, ROTATE_180) → 768px thumb 다시 ocr.ocr() → rot_anchors
  - rot_anchors >= orig_anchors+2 AND rot_anchors >= 4 이면 img = rotated_180_img
  ↓
for region in region_list:                                   (main.py:2100+)
  - field_type=="table":   _ocr_table_region(img, ocr, region)   (main.py:2109)
  - field_type=="field":   _ocr_crop_region(img, ocr, x, y, w, h)  (main.py:2132)
  ↓
classify_document(full_lines) → doc_type 결정                  (main.py:2143-2152)
  ↓
doc_type == "invoice_statement" 이면:
  - ocr.ocr(img) → ocr_lines_raw                              (main.py:2166)  ← 전체 풀 OCR
  - extract_invoice_statement_fields(ocr_lines_raw) → document_fields  (main.py:2622)
  ↓
[T-26a-fix] fields[i]["value"]를 document_fields["supplierCompany"/"buyerCompany"]로 덮어씀  (main.py:2643-2669)
  - "공급자 상호" / "공급자 회사명" / "공급받는자 상호" / "공급받는자 회사명" 4개 koField만 패치
  - 사업자번호/주소/성명/품목표는 건드리지 않음
  ↓
response 생성, original_image / processed_image / extract_debug 포함
```

### 비정형 vs Template 결정적 차이

| 단계 | 비정형 | Template |
|-----|------|---------|
| detect_document (원근 보정) | ✓ | ✗ |
| detect_orientation | ✓ (line 2199) | ✓ T-27a (line 1985) |
| deskew | ✓ | ✗ |
| Resize → 950px | ✓ | ✗ (full size 그대로) |
| CLAHE / 선명화 | ✓ | ✗ |
| OCR 입력 크기 | ~950px | **2483×3511 (full)** |
| 풀 OCR 실행 횟수 | 1회 | 1회 + anchor fallback 1~2회 |
| region crop OCR | - | 7~10회 |
| 평균 시간 | ~10~20s | ~60~180s |

---

## 5. T-27a/T-27a-fix/T-27a-fix2 변경점 정리

| 마커 | 위치 | 동작 | OCR 추가 호출 | 영향 |
|-----|-----|------|------------|------|
| **T-27a** | `main.py:1983-1995` | `detect_orientation(img, ocr, original_wh)` 1회 호출. 224px thumb 기반 0/90/180/270 점수 비교 후 best_angle 방향으로 img 회전 | 224px thumb × 2~4회 (early-stop 조건에 따라) | 모든 region crop이 회전된 img 사용. 정상 방향 입력에서는 angle=0 → 영향 없음. **invoice_statement / 그 외 모든 doc_type 적용** |
| **T-27a-fix** (이전) | (deprecated, T-27a-fix2로 대체됨) | anchor < 4 / rot > orig+1 | 768px × 1~2회 | invoice_statement 한정 |
| **T-27a-fix2** | `main.py:1997-2098` | anchor 카운트 비교 강화. orig < 5 / rot >= orig+2 AND rot >= 4 / anchor 15개로 확장. `_tmpl_orient_debug` dict 빌드 후 `response["templateOrientationDebug"]` 에 노출 | 768px × 1~2회 (정상 입력에서도 1회는 실행됨) | invoice_statement 한정. 미발동이면 img 변경 없음 |

### T-27a-fix2가 정상 입력에서도 비용을 발생시키는 부분

`main.py:2050`:
```python
_orig_anchors = _count_inv_anchors_t27a(img)   # ← invoice_statement이면 항상 실행
```

→ **정상 방향 1.jpg에서도 768px thumb 풀 OCR 1회 추가**. 정상에서는 fallback 미발동이지만 비용 1회는 무조건 발생.

---

## 6. Image object/path 흐름 분석

| 단계 | 이미지 source | 회전 적용 가능 |
|-----|------------|-------------|
| `cv2.imdecode(arr, ...)` (main.py:944) | 업로드 바이트 → BGR numpy. EXIF 무시. | 없음 |
| `detect_orientation` (T-27a) | 반환된 image로 `img` 재할당 | best_angle != 0 이면 회전 |
| T-27a-fix2 fallback | 조건 충족 시 `img = cv2.rotate(img, ROTATE_180)` 재할당 | 180만 가능 |
| `_ocr_crop_region(img, ocr, x, y, w, h)` (main.py:1015-1043) | **위에서 전달된 img** numpy 배열 사용. `img[y1:y2, x1:x2]`로 직접 crop. 파일 경로 재오픈 없음 | 회전된 img면 회전된 crop |
| `_ocr_table_region(img, ocr, region)` (main.py:1502+) | **위에서 전달된 img** 직접 사용. `img[y1:y2, x1:x2]` 같은 패턴 | 회전된 img면 회전된 crop |
| invoice_statement parser용 `ocr.ocr(img)` (main.py:2166) | **같은 img 변수** 사용 | 회전 일관 |
| `original_b64` (response["original_image"]) | 회전 전 원본 그대로 (의도된 동작) | UI 표시용 |

### 핵심 발견
- 모든 crop/parser가 같은 `img` 변수를 사용 → **img wiring 자체는 일관됨**
- **즉, 만약 회전이 진짜 적용됐다면 모든 결과가 정상이어야 한다**

---

## 7. OCR 호출 횟수 / 성능 병목 분석

### Template path (invoice_statement) OCR 호출 횟수

| 단계 | 입력 크기 | 호출 횟수 | 예상 시간 (CPU PaddleOCR) |
|-----|---------|--------|----------------------|
| T-27a detect_orientation thumb | 224×316 | 2~4 (early-stop 조건) | 2~6s |
| T-27a-fix2 anchor 768px 원본 | 768×1086 | **1회 항상** | 15~30s |
| T-27a-fix2 anchor 768px 회전 | 768×1086 | **0~1회** (orig_anchors < 5일 때) | 15~30s |
| Region crop OCR | 작은 crop 영역 | 7~10회 | 5~15s 총 |
| Table region OCR | 표 영역 크기 | 1회 | 10~20s |
| invoice_statement parser full OCR | **2483×3511 (full size)** | **1회** | **40~80s** |

총 합 (뒤집힌 1.jpg, 정상 동작 가정):
- T-27a thumb: ~5s
- T-27a-fix2 (2회): ~30~60s
- region/table crops: ~25~35s
- parser full OCR (full size): ~40~80s
- **합계: 100~180s** (사용자 보고 153~166s와 일치)

### 성능 회귀의 핵심 원인

1. **T-27a-fix2 768px thumb OCR이 정상 입력에서도 1회 추가** (15~30s)
2. **T-27a-fix2 fallback 발동 시 추가 1회 더** (15~30s)
3. **invoice_statement parser at line 2166이 full-resolution(2483×3511) img를 통째로 OCR** ← T-27 이전부터 있던 비효율. 비정형 경로는 950px로 리사이즈 후 OCR하지만 Template invoice_statement는 이 리사이즈를 거치지 않음

→ **속도 회귀 책임의 약 60~70%는 T-27a-fix2 추가 OCR, 나머지 30~40%는 기존 full-res parser OCR의 본질적 비용**

---

## 8. live 실패 원인 가설별 평가

### H1: detect_orientation/T-27a-fix2 fallback이 실제로 발동하지 않는다
- **가능성: 매우 높음**
- 근거:
  - 깨진 결과 `서울 [배달]`이 정상 방향 1.jpg에서 사업자번호 region 좌표가 다른 위치에 적용된 모양과 일치 → img가 회전되지 않은 상태
  - detect_orientation은 224px thumb로 OCR 점수 비교. 2483×3511 큰 invoice를 224 short로 줄이면 한글 텍스트가 미세해져서 0°/180° 점수 차이가 작아 angle=0 추천될 수 있음 (preprocess.py:131-345)
  - T-27a-fix2가 도입되었지만 `templateOrientationDebug.fallbackApplied`를 live에서 확인하지 않은 상태 → 발동 여부 미확정
  - 가능 시나리오:
    1. orig_anchors >= 5 (뒤집힌 이미지에서 짧은 한글 anchor가 우연히 5개 이상 매칭 → fallback 검사 건너뜀)
    2. orig_anchors < 5 이지만 rot_anchors가 orig+2 미만 또는 4 미만 (정확도 부족)
    3. **서버 재시작 안 됨**으로 T-27a-fix2 코드 자체가 live에 반영되지 않았을 가능성
- 추가 확인 필요: **다음 RunOCR 실행 후 response.templateOrientationDebug 값 확인 필수**

### H2: fallback은 발동하지만 rotated image가 crop/parser에 전달되지 않는다
- **가능성: 낮음**
- 근거: main.py:2059의 `img = _rotated_180_img` 재할당 후 for-loop(2100+) 및 parser(2166)는 같은 `img` 변수 사용 (코드 직접 확인됨)
- → 발동만 되면 전달은 보장됨

### H3: rotated image는 전달되지만 crop 함수가 원본 image_path를 재오픈한다
- **가능성: 매우 낮음**
- 근거: `_ocr_crop_region(img, ocr, x, y, w, h)` (main.py:1015-1043) 및 `_ocr_table_region(img, ocr, region)` (main.py:1502+) 둘 다 numpy `img`를 직접 받아 `img[y1:y2, x1:x2]`로 crop. 파일 경로 재오픈 없음

### H4: field crop과 table crop이 서로 다른 image 기준을 쓴다
- **가능성: 매우 낮음**
- 근거: for-loop(main.py:2100-2141)에서 둘 다 같은 `img` 인자로 호출

### H5: OCR은 rotated를 쓰지만 overlay/preview만 원본 → 사용자 헷갈림
- **가능성: 부분적 가능, 그러나 불충분**
- 근거: `response["original_image"]`는 회전 전 원본을 보존(의도된 동작). UI는 이를 표시. 하지만 사용자가 보고한 사업자번호 깨진 값 `서울 [배달]`은 진짜 OCR 결과값이므로 단순 표시 혼동만으로 설명되지 않음

### H6: detect_orientation의 angle 의미를 반대로 해석한다
- **가능성: 매우 낮음**
- 근거: `preprocess.py:327-334` — best_angle==180이면 `cv2.rotate(image, ROTATE_180)` 반환. 호출자는 반환받은 image를 그대로 사용 (의미 일치)

### H7: template region 좌표가 표시 이미지 기준으로 저장됨
- **가능성: 낮음~중간 (확인 필요)**
- 근거: 사용자 시나리오상 정상 방향 1.jpg에서 template를 생성했다면 좌표는 정상 방향 기준. 그러나 사용자가 어느 시점에 template를 새로 만들었는지 코드만으로 확정 불가
- 추가 확인 필요: DB의 region 좌표 기록과 정상 1.jpg의 실제 사업자번호 좌표를 비교

### H8: T-26a-fix가 일부 field value만 parser 값으로 덮어써서 상호만 정상처럼 보임
- **가능성: 매우 높음 (확정)**
- 근거: `main.py:2643-2669`. `_T26A_KOFIELD_MAP`에 4개 koField만 포함 (`공급자 상호`, `공급자 회사명`, `공급받는자 상호`, `공급받는자 회사명`). 사업자번호/주소/성명/품목표는 region crop의 원본 결과 그대로 노출
- → 회사 상호만 정상으로 나오는 비대칭 패턴을 정확히 설명

---

## 9. 왜 공급자 사업자번호가 `서울 [배달]`로 나오는가 (구조적 설명)

```
[가설 흐름: img가 회전 안 된 상태]
업로드 이미지: 180° 뒤집힌 1.jpg (픽셀 기준)
  ↓
T-27a detect_orientation → angle=0 추천 (224px thumb 한계)
  ↓
T-27a-fix2 anchor fallback:
  - orig_anchors 카운트 → 5 이상으로 우연히 매칭 → fallback 건너뜀
  - 또는 orig_anchors < 5 이지만 rot_anchors가 +2 미만 → 발동 안 함
  - 또는 코드 자체가 live에 미반영 (서버 재시작 안 됨)
  ↓
img는 뒤집힌 그대로
  ↓
for-loop region crops:
  - 공급자 사업자번호의 region 좌표는 정상 방향 1.jpg 기준의 (x, y, w, h)
  - 뒤집힌 img에 정상 방향 좌표를 적용 → 좌표 (x, y, w, h)가 가리키는 위치는
    원본 정상 이미지로 보면 (orig_w - x - w, orig_h - y - h, w, h) 즉 우측 하단의
    "거래조건/배달지/요청사항" 텍스트가 있는 영역
  - 그 영역의 OCR 결과가 "서울 [배달]"
```

---

## 10. 왜 공급자/공급받는자 상호 최종값은 정상처럼 보이는가

- region crop 자체는 잘못된 영역 → OCR 원본은 garbage
- 그러나 parser full OCR(line 2166)이 `ocr.ocr(img)` 호출. img가 뒤집혀 있어도 PaddleOCR는 텍스트 박스를 감지하는데, 다음 둘 중 하나:
  - **가능성 A**: img가 실제로 회전됐다면(즉 T-27a 또는 fallback이 발동) parser는 정상 텍스트를 받음. 그러면 region crop도 정상이어야 하는데 깨졌으므로 모순 → **시나리오 A 가능성 낮음**
  - **가능성 B**: img는 뒤집힌 상태로 parser에 전달됐고, PaddleOCR가 뒤집힌 텍스트의 일부를 어떻게든 인식. invoice_statement.py의 anchor 기반 회사명 추출이 뒤집힌 잡음 텍스트에서 부분적으로 `부광약품(주)` 글자열을 찾았을 가능성 (또는 사용자가 정상 1.jpg를 한번 테스트한 결과의 캐시/잔존 가능성)
  - **가능성 C**: 사용자 보고에서 사실 supplier company가 빈 값 또는 noise로 시작하다가, T-26a-fix가 빈 값이면 패치 안 함(`if not _norm: continue`). 따라서 supplier company가 정상으로 보이려면 parser가 진짜로 `부광약품(주)`을 추출했어야 함 → parser가 어딘가의 img를 정상 방향으로 받았을 가능성
- **이 불일치는 “회사 상호만 정상”이라는 패턴이 가짜 정상(parser가 어찌어찌 anchor 매칭한 결과) 또는 부분 정상(detect_orientation이 가끔 발동) 일 가능성을 시사**. **확정을 위해 다음 실행에서 `templateOrientationDebug` 와 `extract_debug.invoice_statement` 동시 확인 필요**

---

## 11. 수정 전략 비교

### 평가 기준
1. 정상 문서 속도 회복 (현재 153~166s → 60s 이하)
2. 비정형 경로 무영향
3. 회귀 위험
4. 구현 난이도
5. 뒤집힌 문서 해결 가능성

| 전략 | 정상 속도 회복 | 비정형 무영향 | 회귀 위험 | 구현 난이도 | 뒤집힌 해결 |
|-----|------------|-----------|--------|---------|----------|
| **1. T-27a/fix/fix2 전부 롤백** | ◎ (즉시 회복) | ◎ | ◎ (낮음) | ◎ (낮음) | ✗ (뒤집힌 깨짐 복원) |
| **2. 현재 T-27 유지하고 wiring만 수정** | ✗ (속도 그대로) | ◎ | △ (이미 회귀 상태) | ○ | △ (조건 튜닝 필요) |
| **3. 자동 orientation 제거 + 깨짐 감지 시 1회 180 재시도** | ○ (정상은 빠름) | ◎ | ○ | △ (실패 판정 기준 필요) | ○ (뒤집힘만 추가 비용) |
| **4. RunOCR UI 수동 회전 버튼** | ◎ | ◎ | ◎ (낮음) | ◎ (낮음) | ◎ (사용자가 눌러 해결) |
| **5. 업로드 시점에 orientation normalization → 정상화 image 저장** | ○ | ○ (preview/overlay 정리 필요) | ○ | ✗ (높음) | ◎ |

---

## 12. 최종 추천 수정 방향

### 추천: 전략 1 + 전략 4 조합

**Phase A (즉시 적용 권장)**
- **T-27a/T-27a-fix/T-27a-fix2 전부 롤백** → 코드를 T-27 이전 상태로 되돌림
  - 백업된 `main_20260519_1631_before_T27a_template_orientation_path_alignment.py` 로 단일 복원 가능
  - 효과: 처리 시간 즉시 회복 (153~166s → 60s 이하), 정상 문서 회귀 위험 0
  - 비용: 뒤집힌 문서는 다시 깨짐 (그러나 뒤집힌 입력은 사용자가 인지 가능)

**Phase B (UI 단순 보완)**
- **RunOCR 화면에 수동 90°/180° 회전 버튼 추가** (frontend 단독 작업, OCR 코드 무영향)
  - 사용자가 미리보기에서 뒤집힘 인지 → 회전 → RunOCR 실행
  - 좌표 기준이 정상 방향이므로 사용자 회전이 곧 모든 결과 보장
  - 자동 detection 비용 0, 정상 문서 100% 정상 동작

**Phase C (선택, 정확도 향상 단계)**
- 업로드 시점에 한 번만 detect_orientation 적용해 **정상화 이미지를 저장**하고 이후 RunOCR 입력으로 그 정상화 이미지 사용 (전략 5). 단 preview/overlay/저장 일관성 정리 필요. 다음 작업 분리.

### 비추천

- **전략 2 (현재 T-27 유지하고 wiring만 수정)**: T-27a-fix2 이미 wiring은 정확함. 속도 회귀가 본질적 문제 → 유지할 가치 없음.
- **전략 3 (실패 감지 후 180 재시도)**: 실패 판정 기준이 다시 anchor 매칭이 되면 T-27a-fix2와 같은 회귀 위험. 가능성은 있으나 우선순위 낮음.

### 판단 요지
- 현재 정상 문서까지 3분 걸리는 구조는 **운영 불가** (사용자 명시 기준)
- 비정형 경로는 잘 동작 (전략 4까지 포함해서 변경 X)
- 자동 회전을 모든 invoice_statement에 비싸게 강제하는 것은 비합리 → 수동 회전 + 롤백 조합이 가장 안전
- 뒤집힘 케이스는 빈도 낮음. 사용자가 미리보기에서 인지 가능. 수동 회전 버튼으로 해결되는 케이스

---

## 13. 다음 작업 프롬프트에 포함해야 할 핵심 조건

1. **백업**: 현재 T-27a-fix2 적용된 `main.py`를 `backup/main_20260519_before_T27_rollback.py`로 보관 (롤백 결정 번복 가능성 대비)
2. **롤백 대상 코드 블록** (정확히 3개 마커):
   - T-27a block (`main.py:1977-1995`)
   - T-27a-fix2 block (`main.py:1997-2098`)
   - 그리고 `response["templateOrientationDebug"]` 노출 부분 (`main.py:2507-2509`)
3. **건드리지 말 것**:
   - 비정형 OCR 경로 (else 블록, line 2173+)
   - T-25 cleanup 전체
   - T-26a / T-26a-fix
   - invoice_statement.py
   - preprocess.py (detect_orientation 정의는 비정형 경로에서 그대로 사용)
   - preprocessing_policy.py
   - frontend
4. **검증**:
   - py_compile main.py
   - npm run typecheck / build
   - **live: 정상 1.jpg RunOCR → 처리 시간 60s 이하 확인 + 28행 / 회사상호 / T-25 / T-26 기준선 유지**
5. **수동 회전 버튼 (별도 task)**:
   - frontend RunOCR 미리보기 컴포넌트에만 추가
   - 회전된 이미지를 RunOCR 요청 시 새 이미지로 전송 (또는 회전 각도 파라미터 전송)
   - 백엔드 OCR 코드 무수정

---

## 14. T-25/T-26 기준선 영향 없음 확인

| 기준선 | T-27-DIAG 영향 |
|------|-------------|
| T-25d amount/qty cleanup | **무영향** (invoice_statement.py 미참조) |
| T-25f RESET (Custom warning UI 없음) | **무영향** (frontend 미참조) |
| T-25g spec cleanup | **무영향** (invoice_statement.py 미참조) |
| T-26a/T-26a-fix 회사 상호 정규화 | **무영향** (main.py:2643-2669 미참조) |
| invoice_statement rowCount 7/7 exact | **무영향** (parser 미참조) |
| 비정형 receipt 결과 | **무영향** (else 블록 미참조) |

본 작업은 **분석/리포트만 생성**했으며 어떤 코드도 수정하지 않았다.

---

## 15. 확인 필요 항목 (실제 코드만으로 확정 못한 부분)

1. **`response["templateOrientationDebug"].fallbackApplied`** 실제 live 값 (다음 RunOCR에서 확인) → fallback 발동 여부 직접 검증 가능
2. **DB에 저장된 region 좌표가 어느 방향 기준인지** → template 정의 시점에 어떤 방향 이미지가 사용됐는지 확인 필요
3. **invoice_statement.py의 anchor 매칭 동작이 뒤집힌 OCR 노이즈에서 `부광약품(주)` 단어를 어떻게 잡아내는지** → invoice_statement.py extract 로직 추가 진단 필요 (해당 task: T-27-DIAG-B)
4. **서버 재시작 여부**: T-27a-fix2 코드가 실제로 live에 반영됐는지 (예: `templateOrientationDebug` 키가 response에 보이는지) → 확인 필수
