# T-28d: Document Bbox Template Coordinate Normalization

**Date:** 2026-05-19  
**Tool:** Claude Code  
**Model:** Claude Sonnet 4.6  

---

## 1. 사용 도구와 모델
- 도구: Claude Code
- 모델: Claude Sonnet 4.6

---

## 2. 원인 (T-28c 실패 이유)

T-28c의 전체 이미지 크기 비율 스케일(3000/2483=1.208, 4000/3511=1.139)은 부족했다.

**실측 데이터 (OCR 직접 스캔):**

| 필드 | 템플릿 y (1.jpg) | 실제 y (회전된 1-1.jpg) | 차이 |
|---|---|---|---|
| 사업자번호 | 405 | 720~807 (center≈764) | **+359px** |
| 공급자 상호 | 524 | 840~907 (center≈874) | **+350px** |
| 공급자 주소 | 642 | 957~1010 (center≈984) | **+342px** |

→ 비율 스케일 후에도 y 오프셋이 ~315px 잔존 (스케일 후 461 vs 실제 764)

**원인:** 1-1.jpg는 문서 타이틀/헤더 영역이 1.jpg 스캔에 비해 더 많이 포함됨. 절대 y 오프셋(~350px)이 단순 비율 변환으로는 보정 불가.

**올바른 접근:**
좌표 변환 대신 **파서 전체 이미지 OCR 결과로 field 값을 직접 패치**한다.
파서는 이미 올바른 값을 추출하고 있으나 template field에 반영이 안 됐을 뿐.

---

## 3. 백업 파일 목록

| 백업 파일 |
|---|
| `backup/main_20260519_before_T28d_document_bbox_coordinate_normalization.py` |

---

## 4. 수정 파일 목록

| 파일 | 변경 내용 |
|---|---|
| `ocr-server/main.py` | T-28d: T-26a-fix 이후 파서 출력으로 모든 invoice 필드 패치 |

---

## 5. 핵심 수정 내용

### 위치
T-26a-fix 블록 직후 (`main.py` ~2648)

### Step 1: supplierBusinessNo 보완
`extract_debug.invoice_statement.party_candidates.bizs`에서 `x < split_x` 항목 사용:
```python
for _e28 in (_t28d_pc.get("bizs") or []):
    if float(_e28[0]) < _t28d_split_x and _e28[2]:
        _t28d_doc["supplierBusinessNo"] = str(_e28[2])
        break
```

### Step 2: buyerBusinessNo 보완
`ocr_lines_raw`에서 `x > split_x` 위치의 10자리 숫자 패턴 검색:
```python
_biz10 = re.compile(r'\d{10}')
for _pts28, _txt28, _cf28 in ocr_lines_raw:
    _cx28 = (sum x coords) / count
    if _cx28 <= _t28d_split_x: continue
    _clean28 = re.sub(r'[-\s]', '', _txt28)
    if _biz10.search(_clean28): _t28d_doc["buyerBusinessNo"] = ...
```

### Step 3: koField → document_fields 매핑 패치
T-26a-fix 패턴 확장. 모든 invoice 필드 커버:

| koField | document_fields key |
|---|---|
| 공급자 사업자 번호 | supplierBusinessNo |
| 공급자 주소 | supplierAddress |
| 공급자 성명 | supplierRepresentative |
| 공급받는자 사업자 번호 | buyerBusinessNo |
| 공급받는자 주소 | buyerAddress |
| 공급받는자 성명 | buyerRepresentative |
| 합계금액 | totalAmount |

**안전 조건:** `if not _nv28: continue` (파서 값이 없으면 크롭 결과 유지)  
**역호환성:** `if _ov28 == _nv28: continue` (크롭 값이 이미 맞으면 변경 없음 → 정상 1.jpg 비영향)

---

## 6. 드라이런 검증 결과 (T-28b 응답 데이터 기반)

T-28b raw response를 입력으로 T-28d 로직을 시뮬레이션:

| 필드 | Before | After T-28d |
|---|---|---|
| field_1 (공급자 사업자번호) | `"서울 [배달]"` | **`"118-81-00450"`** ✓ |
| field_3 (공급자 주소) | `"-1 -T - 등록"` | **`"서울특별시 동작구 상도로7"`** ✓ |
| field_9 (합계금액) | `"30 7,3 그"` | **`"18,098,750"`** ✓ |
| field_5 (공급받는자 사업자번호) | `"추"` | SKIP (buyerBusinessNo empty in T-28b data) |
| field_7 (공급받는자 주소) | `"028690211..."` | SKIP (buyerAddress empty in T-28b data) |

> **주:** field_5, field_7 SKIP은 T-28b 당시 파서 추출 실패 기인. 새 live 호출에서는 다를 수 있음.  
> buyerBusinessNo는 Step 2 (ocr_lines_raw 검색)로 "1138504425" 추출 예정.

---

## 7. 뒤집힌 1-1.jpg 검증 (서버 재시작 후 라이브 테스트 필요)

**서버 재시작 필요:**
- 현재 서버: PID 7148, 시작 19:55:04 (T-28c 코드 로드)
- T-28d 수정: 20:17
- 서버 재시작 후 라이브 RunOCR 실행

**기대 결과:**

| 필드 | 기대값 |
|---|---|
| appliedRotation | 180 |
| field_1 공급자 사업자번호 | 118-81-00450 |
| field_2 공급자 상호 | 부광약품(주) |
| field_3 공급자 주소 | 서울특별시 동작구 상도로7 |
| field_5 공급받는자 사업자번호 | 1138504425 |
| field_6 공급받는자 상호 | 백제약품(주)영등포지점 |
| field_9 합계금액 | 18,098,750 |
| tableRows | 28행 |

---

## 8. 정상 1.jpg 검증

1.jpg → 템플릿 기준(2483×3511)으로 크롭 정상 → 크롭 값 = 파서 값 → `if _ov28 == _nv28: continue` 조건으로 패치 SKIP → **기존 결과 완전 유지**.

---

## 9. 성능 결과

T-28d 추가 연산:
- `party_candidates.bizs` 리스트 순회: O(n) 나노초
- `ocr_lines_raw` 순회 + regex: O(lines) ~ 수 밀리초
- 추가 OCR 호출: **없음**

→ 처리 시간에 유의미한 영향 없음.

---

## 10. 기준선 유지 확인

| 기준선 | 상태 |
|---|---|
| T-25/T-26 기준선 | OCR 로직 수정 없음 ✓ |
| invoice_statement 7개 rowCount exact | 비템플릿 경로, T-28d 무영향 ✓ |
| T-28a/T-28b normalized pipeline | 유지 ✓ |
| T-28c coordinate scaling | 유지 (T-28d는 추가 패치 레이어) ✓ |
| 비정형 OCR/영수증 경로 | `if region_list` 조건으로 완전 제외 ✓ |
| py_compile | PASS ✓ |

---

## 11. 남은 한계

- **buyerBusinessNo**: `ocr_lines_raw` 검색이 필요하며, "1138504425"가 복합 텍스트 "028690211 호 D2024 등록 1138504425"에 포함된 경우 추출 가능. 단독 텍스트면 즉시 추출.
- **buyerAddress**: 파서가 buyerAddress를 추출하지 못하면 field_7은 여전히 잘못된 크롭 결과 유지.
- **table rows**: table_1은 파서 output이 아닌 크롭 기반이므로 여전히 26행일 수 있음 (정상 28행은 파서의 `document_fields.rowCount`에서 확인).

---

## 12. 다음 작업 제안

1. **서버 재시작 → 라이브 1-1.jpg RunOCR 검증** (field_1, field_5, field_9 확인)
2. **buyerAddress 보완**: 파서가 buyerAddress를 정확히 추출하는지 확인, 실패 시 `ocr_lines_raw` 주소 패턴 검색 추가
3. **buyerRepresentative 보완**: 파서 추출 여부 확인
4. **T-28d field_7 결과 확인**: 파서가 "서울특별시 구로구 공원로 8길 24 (구로동)"을 추출하면 자동 패치됨
