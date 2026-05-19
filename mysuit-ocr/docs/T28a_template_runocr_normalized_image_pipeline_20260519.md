# T-28a: Template RunOCR shared normalized image pipeline

**생성일**: 2026-05-19  
**사용 도구**: Claude Code  
**사용 모델**: Claude Sonnet 4.6  
**코드 수정**: `ocr-server/main.py` 1개

---

## 1. 작업 메타

- 사용 도구: Claude Code
- 사용 모델: Claude Sonnet 4.6
- 작업 종류: 구조 개선 (T-27a/fix/fix2 폐기 + normalized image pipeline 도입)
- 코드 수정: `ocr-server/main.py` 1개
- 신규 helper 파일: **없음** (변경 범위 최소화)
- frontend 수정: **없음**

---

## 2. 백업 파일 목록

```
ocr-server/backup/main_20260519_before_T28a_template_normalized_pipeline.py
```

---

## 3. 수정 파일 목록

| 파일 | 변경 내용 |
|-----|---------|
| `ocr-server/main.py` | T-27a + T-27a-fix2 블록 (line 1977-2098 약 122줄) → T-28a normalized image pipeline (약 45줄) 로 교체. `templateOrientationDebug` → `templateImageNormalization` 으로 교체. |

미변경:
- `ocr-server/preprocess.py` (detect_orientation 정의 그대로 재사용)
- `ocr-server/extractors/invoice_statement.py`
- `ocr-server/preprocessing_policy.py`
- frontend 전체
- 비정형 OCR/영수증 경로 (`main.py:2097+ else 블록`)

---

## 4. 기존 비정형 OCR 입력 정규화 구조 (`main.py:2097+`)

```
업로드 image → cv2.imdecode → img
  ↓
1. detect_document(img) → doc_img  (또는 corners 기반 perspective transform)
  ↓
2. detect_orientation(doc_img, ocr, original_wh) → doc_img  (자동 회전)
  ↓
3. deskew(doc_img) → doc_deskewed
  ↓
4. display_max_w=2000 리사이즈 → display_img (미리보기)
  ↓
5. ocr_max_w=950 / ocr_min_w=760 리사이즈 → ocr_img
  ↓
6. CLAHE on L channel (대비 강화)
  ↓
7. 언샤프 마스크 (텍스트 엣지 강조)
  ↓
8. ocr.ocr(ocr_img) 1회 풀 OCR  (950px 작은 크기)
```

핵심 특징:
- 단일 normalized image (`ocr_img`)를 만들고 그 한 장만 OCR
- OCR 입력 크기를 950px로 줄여 속도 확보
- 모든 후속 처리(receipt parser, 금액 추출 등)가 같은 ocr_img 결과를 참조

---

## 5. 기존 Template RunOCR 경로 문제 (T-27 실패 구조)

### T-27 이전 (정확도 실패):
- `cv2.imdecode → img`
- 곧바로 region for-loop → 뒤집힌 img에 정상 방향 좌표 적용 → 깨진 crop

### T-27a (정확도 부분 개선, 그러나 한계):
- `detect_orientation(img, ocr)` 1회 호출 (224px thumb 기반 점수 비교)
- 224px 한계: 큰 invoice 문서에서 한글 텍스트가 미세해져 0°/180° 점수 차이가 작아 angle=0 잘못 추천 가능

### T-27a-fix / T-27a-fix2 (정확도 미해결 + 성능 악화):
- invoice_statement 한정 anchor fallback OCR (768px short-side thumb로 2회 풀 OCR)
- **정상 입력에서도 무조건 1회 추가** (15~30s)
- fallback 발동 시 추가 1회 더 (15~30s)
- 안정적 정확도 보장 안 됨 (anchor 카운트 임계값 튜닝 의존)
- 처리 시간 60s → 153~166s 회귀

**근본 문제**: orientation 정규화를 crop 직전에 "패치 형태"로 덧붙임. 비정형 경로처럼 "전체 문서 기준 normalized image 1장을 만들고 그것만 사용"하는 구조가 아니었음.

---

## 6. T-27 제거/비활성화 내용

`main.py:1977-2098` (122줄) → T-28a 블록 (45줄)로 교체. 제거된 항목:

| 항목 | 제거 사유 |
|-----|---------|
| T-27a-fix2 invoice_statement anchor fallback 블록 | 정상 입력에서도 768px 풀 OCR 1회 강제 → 비용/회귀 책임 |
| `_count_inv_anchors_t27a` 헬퍼 | 더 이상 호출자 없음 |
| `_INV_ANCHORS` (15개 anchor 목록) | 더 이상 사용 안 함 |
| `_tmpl_orient_debug` dict 빌드 | normalized image 구조에 불필요한 비대 debug |
| `template_anchor_fallback_applied`/`template_anchor_orig`/`template_anchor_rot180`/`template_anchor_fallback_ms` timings 키 | 추가 OCR 비용을 측정하던 키 |
| `response["templateOrientationDebug"]` | `templateImageNormalization` 로 대체 |

유지된 항목:
- `detect_orientation(img, ocr, original_wh)` 1회 호출 (그러나 위치/의도가 "normalized image 생성"으로 명확화됨)
- `template_detect_orientation_ms` timings 키

---

## 7. T-28a Template normalized image pipeline 설계

### 핵심 원칙
1. **전체 문서 기준 방향 정규화** → normalized image 생성
2. **field crop / table crop / parser**가 모두 같은 normalized img 사용
3. **resize/deskew 미적용** → template region 좌표 기준 일치 보장 (scaleX=1.0, scaleY=1.0)
4. **추가 OCR 없음** — `detect_orientation` 내부의 thumbnail OCR만 사용 (224px × 2~4 candidates)
5. **debug meta는 추가 OCR 없이 노출**

### 새 흐름
```
cv2.imdecode → img
  ↓
[T-28a normalized image pipeline]
detect_orientation(img, ocr, original_wh) → normalized img
  - 224px thumb 기반 0/90/180/270 점수 비교
  - best_angle 방향으로 회전된 image 반환
  - 정상 방향 입력: angle=0 → 회전 없음
orig_h, orig_w = img.shape[:2]  (90/270 회전 시 가로/세로 swap 대응)
  ↓
templateImageNormalization meta 빌드 (추가 OCR 없음)
  ↓
for region in region_list:
  - table: _ocr_table_region(normalized_img, ocr, region)
  - field: _ocr_crop_region(normalized_img, ocr, x, y, w, h)
  ↓
invoice_statement parser: ocr.ocr(normalized_img) → ocr_lines_raw
  ↓
extract_invoice_statement_fields(ocr_lines_raw) → document_fields
```

---

## 8. 실제 구현 내용

`main.py:1975-2022` (region_list 분기 진입부)에 다음 블록 배치:

```python
if region_list:
    # === 템플릿 영역 기반 OCR ===
    # T-28a: Template RunOCR shared normalized image pipeline.
    # 비정형 경로(line ~2199)와 동일한 detect_orientation을 region crop 이전에 적용한다.
    # 전체 문서를 먼저 정상 방향으로 정규화한 뒤 field/table/parser 모두 같은 normalized image를 사용한다.
    #
    # 원칙:
    # - 좌표 기준 유지를 위해 resize/deskew는 적용하지 않는다 (방향만 정규화).
    # - 정상 입력에서 detect_orientation은 angle=0 → 회전 없음 → 회귀 방지.
    # - 90/270 회전 시 img.shape에 따라 orig_w/orig_h 갱신.
    # - field crop, table crop, invoice_statement parser 모두 같은 normalized img 사용.
    #
    # T-28a가 폐기한 T-27 구조:
    # - T-27a-fix / T-27a-fix2의 anchor 기반 fallback OCR (정상 입력에서도 768px 풀 OCR 1~2회 강제) 제거.
    # - templateOrientationDebug (추가 OCR 비용 발생하던 debug) 제거.
    # - 대신 templateImageNormalization 메타를 추가 OCR 없이 노출.
    _t_norm0 = time.time()
    _orig_size_before_norm = [orig_w, orig_h]
    _applied_rotation = 0
    _norm_status = "applied"
    try:
        img, _orient_meta_tmpl = detect_orientation(img, ocr, original_wh=(orig_w, orig_h))
        _applied_rotation = int(_orient_meta_tmpl.get("angle", 0) or 0)
        orig_h, orig_w = img.shape[:2]
        timings["template_detect_orientation_ms"] = _ms(time.time() - _t_norm0)
        if _applied_rotation != 0:
            print(f"[template] T-28a normalized: rotation={_applied_rotation}")
    except Exception as _norm_e:
        print(f"[template] T-28a normalization failed (using original image): {_norm_e}")
        timings["template_normalization_error"] = str(_norm_e)
        _norm_status = f"error: {_norm_e}"

    _tmpl_img_norm_debug: dict = {
        "enabled": True,
        "appliedRotation": _applied_rotation,
        "deskewApplied": False,
        "resizeApplied": False,
        "originalSize": _orig_size_before_norm,
        "normalizedSize": [orig_w, orig_h],
        "scaleX": 1.0,
        "scaleY": 1.0,
        "usedForRegionCrop": True,
        "usedForTableCrop": True,
        "usedForParser": True,
        "status": _norm_status,
    }
```

response 조립 직후 (`main.py:2431-2433`):
```python
# T-28a: templateImageNormalization meta — normalized image pipeline 상태 (추가 OCR 없음)
if "_tmpl_img_norm_debug" in locals():
    response["templateImageNormalization"] = _tmpl_img_norm_debug
```

---

## 9. 좌표 scale 처리 방식

T-28a는 **resize를 적용하지 않으므로 scale 변환 필요 없음**.

| 회전 각도 | image 크기 변화 | 좌표 변환 필요 |
|---------|-------------|------------|
| 0 | 변화 없음 | 없음 |
| 180 | 변화 없음 (가로/세로 동일) | 없음 (정상 방향 좌표가 정상 image에 그대로 적용) |
| 90 | width↔height swap | template 좌표가 그대로면 invalid (현재 작업 범위 밖) |
| 270 | width↔height swap | template 좌표가 그대로면 invalid (현재 작업 범위 밖) |

`scaleX=1.0`, `scaleY=1.0` 고정. resize 적용은 **T-28b 후속 작업**으로 분리. 안정화 우선.

---

## 10. 정상 1.jpg 검증

### 코드 구조 검증 (정적 분석)
- `detect_orientation` 정상 방향 입력에 대해 angle=0 반환 → img 변경 없음 (preprocess.py:131-345 로직)
- 후속 region crop/table crop/parser 모두 같은 img 사용 → 결과 동일
- T-25d/T-25g cleanup은 invoice_statement.py 미변경이므로 유지
- T-26a/T-26a-fix는 main.py:2643-2669 미변경이므로 유지

### 기대 결과 (live 검증 대상)
| 필드 | 기대값 |
|-----|------|
| 공급자 사업자번호 | `118-81-00450` |
| 공급자 상호 OCR 원본 | `부광 약 품(주)` |
| 공급자 상호 최종값 | `부광약품(주)` |
| 공급자 주소 | `서울특별시 동작구 상도로7` |
| 공급받는자 사업자번호 | `1138504425` |
| 공급받는자 상호 OCR 원본 | `백제약품(주)영등포지점 1010546N` |
| 공급받는자 상호 최종값 | `백제약품(주)영등포지점` |
| 공급받는자 주소 | `서울특별시 구로구 공원로 8길 24 (구로동)` |
| tableRows | 28행 |
| 합계금액 | `18,098,750` |
| 500T(B), 150ml, 500ml spec cleanup | 유지 |
| 처리 시간 목표 | T-27 이전 수준 (60~90s)으로 회복 |

### templateImageNormalization 예상값
```json
{
  "enabled": true,
  "appliedRotation": 0,
  "deskewApplied": false,
  "resizeApplied": false,
  "originalSize": [2483, 3511],
  "normalizedSize": [2483, 3511],
  "scaleX": 1.0,
  "scaleY": 1.0,
  "usedForRegionCrop": true,
  "usedForTableCrop": true,
  "usedForParser": true,
  "status": "applied"
}
```

---

## 11. 뒤집힌 1.jpg 검증

### 코드 구조 검증 (정적 분석)
- `detect_orientation` 호출 시 `best_angle` 추정 로직 (preprocess.py:325-334)
- 180도 뒤집힌 invoice는 정상 방향 점수보다 뒤집힌 방향 점수가 낮아야 자동 회전됨
- 만약 detect_orientation이 180을 추천한다면 img 회전 → 모든 후속 단계가 정상 방향 img 사용 → 정상 결과

### 검증 시나리오
- 시나리오 A: detect_orientation이 180을 추천 → img 회전 → field/table/parser 정상 → 사업자번호 `118-81-00450`, rowCount 28
- 시나리오 B: detect_orientation이 0을 추천 (224px thumb 한계) → img 회전 안 됨 → 결과 깨짐

### 기대 결과 (시나리오 A 가정)
| 필드 | 기대값 |
|-----|------|
| 공급자 사업자번호 | `118-81-00450` |
| 공급자 상호 최종값 | `부광약품(주)` |
| 공급받는자 사업자번호 | `1138504425` |
| 공급받는자 상호 최종값 | `백제약품(주)영등포지점` |
| tableRows | 28행 |

### templateImageNormalization 예상값 (시나리오 A)
```json
{
  "enabled": true,
  "appliedRotation": 180,
  "originalSize": [2483, 3511],
  "normalizedSize": [2483, 3511],
  "status": "applied"
}
```

### 시나리오 B 발생 시 후속 작업
- detect_orientation 자체의 224px thumb 한계 보완은 **T-28b로 분리**
- 옵션 1: detect_orientation에 invoice_statement용 더 큰 thumbnail (예: 512px) 강제 옵션 추가
- 옵션 2: 사용자 수동 회전 버튼 (frontend) 도입
- 옵션 3: 업로드 시점에 한 번만 thumbnail 768px 비교를 수행해 캐시 (정상 입력은 angle=0 빠르게 결정)
- **현재 T-28a 범위는 구조 정리 + T-27 비용 제거가 우선**. 시나리오 B는 다음 task에서 다룬다.

---

## 12. 비정형 경로 영향 없음 확인

| 항목 | 결과 |
|-----|------|
| else 블록 (line 2097+) | **미변경** |
| detect_document | 미변경 |
| detect_orientation 호출 (line 2123) | 미변경 |
| deskew/CLAHE/unsharp | 미변경 |
| receipt parser | 미변경 |
| finance_slip parser | 미변경 |
| preprocessing_policy.py | 미변경 |

T-28a의 normalized image pipeline은 `if region_list:` 블록 안에만 적용. else 블록의 비정형 경로는 코드 자체를 건드리지 않음.

---

## 13. invoice_statement 7개 rowCount exact 유지 확인

| 파일 | 기대 rowCount |
|-----|------------|
| 1.jpg | 28/28 |
| 2.pdf | 13/13 |
| 3.pdf | 1/1 |
| 4.pdf | 1/1 |
| 5.pdf | 6/6 |
| 6.pdf | 6/6 |
| 7.pdf | 1/1 |

- `invoice_statement.py` 미변경 → 파싱 로직 그대로
- T-28a는 normalized image (정상 방향)만 parser에 전달 → 입력 일관성 보장
- 기존 정상 방향 7개 샘플에 대해서는 detect_orientation이 angle=0 → 동일 입력
- **rowCount 7/7 exact 유지 기대**

---

## 14. 성능 before/after

### Before (T-27a-fix2 적용 상태)
| 구간 | 시간 |
|-----|------|
| T-27a detect_orientation thumb (224px) | 2~6s |
| T-27a-fix2 anchor original (768px) | 15~30s |
| T-27a-fix2 anchor rotated180 (768px, fallback 시) | 0 또는 15~30s |
| region crops + table | 25~35s |
| parser full OCR (full-size 2483×3511) | 40~80s |
| **합계** | **약 100~180s (실제 153~166s 보고)** |

### After (T-28a 적용 상태) — 정적 분석 기반 추정
| 구간 | 시간 |
|-----|------|
| detect_orientation thumb (224px) | 2~6s |
| (anchor fallback OCR **제거됨**) | 0s |
| region crops + table | 25~35s |
| parser full OCR (full-size 2483×3511) | 40~80s |
| **합계** | **약 65~120s** |

→ T-27a-fix2 anchor fallback OCR로 인한 30~60s 회귀가 제거됨. **정상 문서 처리 시간이 T-27 이전 수준(60~90s)에 가까워질 것으로 기대**. live 측정으로 확정 필요.

### parser full OCR 비용
- T-28a는 parser full OCR 자체는 그대로 둠 (T-28b 후속 작업으로 분리 가능)
- 만약 추가 성능 개선이 필요하면 invoice_statement parser용 OCR을 950~1200px로 다운스케일하는 안 검토 (단, tableRows 작은 글자 인식 손실 위험)

---

## 15. T-25/T-26 기준선 유지 확인

| 기준선 | 상태 | 근거 |
|------|------|------|
| T-25d amount comma-space cleanup | ✓ 유지 | invoice_statement.py 미변경 |
| T-25d quantity trailing symbol cleanup | ✓ 유지 | 미변경 |
| T-25g spec cleanup (500T(B), 150ml, 500ml) | ✓ 유지 | 미변경 |
| T-25f RESET (Custom 탭 cell warning 없음) | ✓ 유지 | frontend 미변경 |
| T-26a company normalization | ✓ 유지 | invoice_statement.py 미변경 |
| T-26a-fix OCR 원본/최종값 분리 | ✓ 유지 | main.py:2566-2592 미변경 (T-28a 영향 없음) |
| itemName 자동 보정 금지 | ✓ 준수 | 변경 없음 |
| quantity 빈 값 자동 삽입 금지 | ✓ 준수 | 변경 없음 |
| manufacturingNo/expiryDate 자동 복구 금지 | ✓ 준수 | 변경 없음 |
| Custom 탭 cell warning 재도입 금지 | ✓ 준수 | frontend 미변경 |

---

## 16. py_compile / typecheck / build 결과

| 항목 | 결과 |
|-----|------|
| `python -m py_compile main.py` | **PASS** |
| T-27 잔존 코드 (T-27a, T-27a-fix2, _tmpl_orient_debug 등) | **모두 제거됨** |
| T-28a 마커 (T-28a, _tmpl_img_norm_debug, templateImageNormalization) | **확인됨** |
| `npm run typecheck` | **PASS** (frontend 미변경) |
| `npm run build` | **PASS** |

---

## 17. 남은 이슈

1. **뒤집힌 1.jpg에서 detect_orientation이 angle=180을 추천하는지 live 검증 필요**
   - 224px thumb의 한계로 angle=0을 잘못 추천할 가능성 (T-27-DIAG 진단 결과)
   - 발생 시 T-28b 후속 작업에서 invoice_statement용 큰 thumbnail 옵션 또는 수동 회전 버튼으로 보완
2. **parser full OCR (line 2090) 비용은 그대로**
   - 정상 문서 60s 목표에 못 도달하면 T-28c로 parser 입력 다운스케일(예: 1200~1400px) 검토
3. **scaleX/scaleY 변환 로직 미구현**
   - resize 미적용 정책이므로 현재 필요 없음. resize 도입 시 (T-28b) 같이 구현
4. **`templateImageNormalization`은 invoice_statement뿐 아니라 모든 doc_type에 노출됨**
   - region_list 진입 시 항상 빌드 → invoice_statement 외에도 normalized image pipeline이 적용됨. 이는 의도된 동작 (T-28a 원칙: 모든 Template RunOCR에 동일 정규화)
5. **90/270 회전 케이스에서 좌표 invalid**
   - template region 좌표가 portrait 기준일 때 image가 landscape로 회전되면 좌표 매핑 깨짐. 사용자 보고는 180도 케이스 한정이라 우선 미해결 항목

---

## 18. 다음 작업 제안

| Task ID | 제목 | 내용 |
|--------|------|------|
| **T-28a-followup** | live 검증 | 정상 1.jpg + 뒤집힌 1.jpg + 비정형 receipt + invoice_statement 7개 샘플 RunOCR로 실제 결과 확인. `templateImageNormalization.appliedRotation` 로그 확인. 처리 시간 60~90s 회복 확인. |
| **T-28b (조건부)** | invoice_statement용 큰 thumbnail orientation detection | T-28a-followup에서 뒤집힌 1.jpg가 정상화되지 않으면 detect_orientation에 invoice_statement 전용 큰 thumbnail (예: 512~640px short-side) 옵션 추가. 단, 정상 입력에서는 비용 최소화 (early-stop 유지). |
| **T-28c (조건부)** | parser full OCR 입력 다운스케일 | 정상 문서 처리 시간이 여전히 90s 초과면 invoice_statement parser용 ocr.ocr(img) 입력을 1200~1400px로 다운스케일 검토. tableRows 작은 글자 인식 손실 위험 있음 — 7개 샘플 rowCount exact 검증 필수. |
| **T-28d (선택)** | RunOCR UI 수동 회전 버튼 | frontend에 90/180/270 회전 버튼 추가. 자동 detection 실패 시 사용자 수동 보정 가능. OCR 코드 무영향. |

---
