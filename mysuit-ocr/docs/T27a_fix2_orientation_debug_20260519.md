# T-27a-fix2: Template orientation fallback 강화 + templateOrientationDebug

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**코드 수정**: `ocr-server/main.py` 1개

---

## 1. T-27a-fix가 왜 아직 실패했는지

### 조건이 너무 관대했다

T-27a-fix의 anchor fallback 조건:
- `_orig_anchors < 4` — 뒤집힌 이미지에서 anchor가 3개 이하여야 검사 시작
- `_rot_anchors > _orig_anchors + 1` — 180도 회전 image가 단 2개만 더 많아도 적용

실제 1.jpg 뒤집힌 케이스에서 OCR 결과:
- `detect_orientation` → angle=0 (224px thumb 한계로 잘못 추천)
- anchor 카운트 자체가 확인되지 않아 조건 미충족 가능성 있음
- 조건이 충족되어도 임계값이 너무 낮아 노이즈에 취약

### 추가 문제: anchor 목록이 10개뿐

기존 10개 anchor에서 뒤집힌 이미지에서도 잘 보이는 짧은 한글들만 있었다. 정상 방향 OCR에서만 나타나는 `등록번호`, `상호`, `사업장주소` 등이 빠져 있었다.

---

## 2. 백업 파일

```
ocr-server/backup/main_20260519_before_T27a_fix2_orientation_live_failure.py
```

---

## 3. 수정 파일

| 파일 | 변경 내용 |
|-----|---------|
| `ocr-server/main.py` | T-27a-fix 블록 → T-27a-fix2 강화판으로 교체 + templateOrientationDebug 추가 |

`preprocess.py`, `invoice_statement.py`, `preprocessing_policy.py`, frontend — **전부 미변경**.

---

## 4. 핵심 변경 사항

### 4-1. anchor 목록 확장 (10→15개)

```python
_INV_ANCHORS = (
    "거래명세서", "공급자", "공급받는자", "사업자", "품목",
    "규격", "수량", "단가", "금액", "합계",
    "등록번호", "상호", "사업장주소", "유효기간", "소계",  # ← 신규 추가
)
```

### 4-2. 임계값 강화

| 항목 | T-27a-fix (이전) | T-27a-fix2 (현재) |
|-----|----------------|-----------------|
| fallback 검사 시작 임계값 | `orig < 4` | `orig < 5` |
| 180도 회전 적용 조건 | `rot > orig + 1` | `rot >= orig + 2 AND rot >= 4` |

### 4-3. templateOrientationDebug 추가

response에 항상 포함 (invoice_statement 외에는 `enabled: false`로):

```json
{
  "templateOrientationDebug": {
    "enabled": true,
    "docType": "invoice_statement",
    "detectOrientationAngle": 0,
    "fallbackChecked": true,
    "fallbackApplied": true,
    "appliedRotation": "180",
    "originalAnchorCount": 1,
    "rotated180AnchorCount": 8,
    "usedImageForRegionCrop": "rotated180",
    "usedImageForTableCrop": "rotated180",
    "usedImageForParser": "rotated180",
    "reason": "fallback APPLIED: rot180_anchors=8 >= orig_anchors+2(3) AND rot180_anchors >= 4",
    "fallbackMs": 1240
  }
}
```

---

## 5. fallback 발동 판단 흐름

```
detect_orientation(img) → angle=0 (224px thumb 한계로 잘못 추천일 수 있음)

↓ T-27a-fix2 (invoice_statement 한정)

img 768px thumb OCR → original anchor count
  if orig < 5:
    img_180 = cv2.rotate(img, ROTATE_180)
    img_180 768px thumb OCR → rot180 anchor count
    if rot180 >= orig + 2 AND rot180 >= 4:
      img = img_180  ← 정상화 적용
      _tmpl_orient_debug["fallbackApplied"] = True
      _tmpl_orient_debug["usedImageFor*"] = "rotated180"
    else:
      img 유지 (fallback 미발동)
  else:
    img 유지 (orig anchor 충분 → 이미 정상 방향)
```

---

## 6. 정상 1.jpg 예상 동작

`detect_orientation` → angle=0  
`orig_anchors` ≥ 5 (15개 중 대부분 매칭)  
→ fallback 미발동 → img 변경 없음 → **기존 결과 그대로**

```json
{
  "templateOrientationDebug": {
    "fallbackApplied": false,
    "originalAnchorCount": 10,
    "rotated180AnchorCount": null,
    "reason": "fallback skipped: orig_anchors=10 >= 5 (image already well-oriented)"
  }
}
```

---

## 7. 뒤집힌 1.jpg 예상 동작

`detect_orientation` → angle=0 (잘못된 추천)  
`orig_anchors` ≈ 0~2 (뒤집힌 이미지에서 한글 anchor 거의 안 보임)  
→ fallback 발동 → 180도 회전 → `rot_anchors` ≈ 8~13  
→ 조건 충족 (`rot >= orig+2 AND rot >= 4`) → img 정상화

```json
{
  "templateOrientationDebug": {
    "fallbackApplied": true,
    "appliedRotation": "180",
    "originalAnchorCount": 1,
    "rotated180AnchorCount": 9,
    "usedImageForRegionCrop": "rotated180",
    "usedImageForTableCrop": "rotated180",
    "usedImageForParser": "rotated180"
  }
}
```

| 필드 | Before (T-27a-fix) | After (T-27a-fix2 기대) |
|-----|------------------|----------------------|
| 공급자 사업자번호 | `서울 [배달]` (깨짐) | **`118-81-00450`** |
| 공급자 상호 최종값 | `부광약품(주)` (T-26a-fix 우연 정상) | **`부광약품(주)`** |
| 공급받는자 사업자번호 | `추` (깨짐) | **`1138504425`** |
| 품목표 rowCount | 25 (깨짐) | **28** |
| 합계금액 | `30 7,3그` (깨짐) | **`18,098,750`** |

---

## 8. py_compile / typecheck / build

| 항목 | 결과 |
|-----|------|
| `py_compile main.py` | **OK** |
| T-27a-fix2 블록 검증 (detect_orientation → fix2 → for loop) | **확인됨** |
| `npm run typecheck` | **PASS** |
| `npm run build` | **PASS** |

---

## 9. 다음 작업

1. **즉시 검증**: 서버 재시작 후 뒤집힌 1.jpg RunOCR 실행
   - `templateOrientationDebug.fallbackApplied == true` 확인
   - `rowCount == 28` 확인
   - 공급자 사업자번호 `118-81-00450` 확인
2. **정상 1.jpg 회귀 확인**: `fallbackApplied == false`, 결과 동일
3. **비정형 영수증 회귀 확인**: `templateOrientationDebug` 없음 (unstructured path)
4. **T-27b (선택)**: 90/270도 케이스 발견 시 fallback 확장
