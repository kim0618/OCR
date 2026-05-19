# T-28b LIVE PROOF: template orientation runtime

**Date:** 2026-05-19  
**Tool:** Claude Code  
**Model:** Claude Sonnet 4.6  

---

## 1. 사용 도구와 모델

- 도구: Claude Code
- 모델: Claude Sonnet 4.6

---

## 2. 코드 수정 여부

**없음.** 이번 작업은 T-28b 코드가 live 서버에 반영됐는지, raw backend response를 직접 확인하는 증명 작업이다.

---

## 3. live 서버 T-28b 반영 여부

### 서버 상태

| 항목 | 값 |
|---|---|
| 서버 포트 | 9099 |
| 서버 PID | 6020 |
| 서버 시작 시간 | **2026-05-19 19:11:24** |
| preprocess.py 수정 시간 | 2026-05-19 19:06 |
| main.py 수정 시간 | 2026-05-19 19:07 |

→ 서버 시작 시간(19:11:24)이 코드 수정(19:06~19:07) **이후**이므로 T-28b 코드가 로드됨.

### 코드 반영 증명

```bash
# live preprocess.py vs backup 비교
live:   target_short: int = 224,   # 파라미터
        skip_second_pass: bool = False,  # 파라미터 추가
backup: target_short = 224         # 하드코딩만 존재 (파라미터 없음)
```

→ `preprocess.py`와 `main.py` 모두 T-28b 변경 내용이 live 파일에 존재함.

---

## 4. raw backend response 확인 방법

**curl로 직접 백엔드 API 호출:**

```
POST http://localhost:9099/ocr/extract
file: c:/OCR/mysuit-ocr/public/data/testsets/invoice_statement/1/1-1.jpg
template_id: TPL-31D13CF3 (invoice_statement, 10 regions)
```

**응답 파일:** `C:\Users\user\AppData\Local\Temp\t28b_raw_response.json` (625,352 bytes)

**스크린샷 일치 확인:**
- 스크린샷 field_1 값: `[배달]서울`
- raw response field_1 값: `서울 [배달]`
→ 동일 텍스트 (순서만 미세 차이). 같은 또는 유사한 템플릿 사용 확인됨.

---

## 5. templateImageNormalization 값 (raw response)

```json
{
  "enabled": true,
  "appliedRotation": 180,
  "orientationTargetShort": 512,
  "orientationMode": "invoice_template_0_180",
  "originalSize": [3000, 4000],
  "normalizedSize": [3000, 4000],
  "usedForRegionCrop": true,
  "usedForTableCrop": true,
  "usedForParser": true,
  "status": "applied"
}
```

→ `templateImageNormalization`이 raw response에 **존재함** (T-28b 정상 실행).

---

## 6. appliedRotation 값

**appliedRotation = 180**

T-28b detect_orientation이 1-1.jpg(뒤집힌 거래명세서)를 **올바르게** 180도로 판단함.

- `orientationTargetShort = 512` → invoice_statement 전용 512px thumbnail 사용됨
- `orientationMode = invoice_template_0_180` → 0/180도 비교만 수행됨

---

## 7. field 결과 비교

### region crop fields (template 좌표 기반)

| No | name | value | conf |
|---|---|---|---|
| 1 | field_1 (공급자 사업자번호) | **서울 [배달]** ✗ | 0.994 |
| 2 | field_2 (공급자 상호) | **부광약품(주)** ✓ | 0.872 |
| 3 | field_3 (공급자 주소) | **-1 -T - 등록** ✗ | 0.811 |
| 4 | field_4 (공급자 성명) | **세서** ✗ | 0.997 |
| 5 | field_5 (공급받는자 사업자번호) | **추** ✗ | 0.787 |
| 6 | field_6 (공급받는자 상호) | **백제약품(주)영등포지점** ✓ | 0.961 |
| 7 | field_7 (공급받는자 주소) | **028690211 호 D202 등록 1138504425** ✗ | 0.997 |
| 8 | field_8 (공급받는자 성명) | (공백) | 0.0 |
| 9 | table_1 (품목표) | 표 데이터 (26행) | 0.978 |
| 10 | field_9 (합계금액) | **30 7,3 그** ✗ | 0.771 |

### invoice_statement parser output (document_fields)

| 항목 | 값 | 기대값 | 일치 |
|---|---|---|---|
| supplierCompany | 부광약품(주) | 부광약품(주) | ✓ |
| supplierAddress | 서울특별시 동작구 상도로7 | 서울특별시 동작구 상도로7 | ✓ |
| buyerCompany | 백제약품(주)영등포지점 | 백제약품(주)영등포지점 | ✓ |
| totalAmount | 18,098,750 | 18,098,750 | ✓ |
| supplierBusinessNo | (공백) | 118-81-00450 | ✗ |
| buyerBusinessNo | (공백) | 1138504425 | ✗ |
| tableRows | (공백) | 28 | ✗ |

### invoice_statement parser 내부 발견 (extract_debug.invoice_statement.party_candidates)

```json
{
  "bizs": [[882, 764, "118-81-00450"]],
  "companies": [
    [2056, 828, "백제약품(주)영등포지점"],
    [866, 874,  "부 광약 품(주"]
  ],
  "page_size": [2913, 3731]
}
```

→ 파서가 회전된 이미지에서 `"118-81-00450"`을 **올바르게 인식**했으나 1개 BIZ만 발견되어 supplier/buyer 할당 로직에서 실패.

---

## 8. 원인 확정: **Case C**

**C: appliedRotation=180이지만 region crop 필드가 여전히 잘못됨**

### 근거

| 항목 | 값 |
|---|---|
| appliedRotation | **180** (올바르게 감지됨) |
| parser 동작 | **정상** (회전 이미지에서 올바른 텍스트 추출) |
| region crop 동작 | **실패** (잘못된 좌표 기준) |

### 세부 원인: 템플릿 좌표 해상도 불일치

| 이미지 | 크기 (W×H) |
|---|---|
| 1.jpg (정상, 템플릿 정의 기준 추정) | 2483×3511 |
| 1-1.jpg (뒤집힌, live 테스트 대상) | 3000×4000 |

**Scale factor:** X=1.208×, Y=1.139×

| field | bbox (template) | 올바른 좌표 (1-1.jpg 기준) | 오차 |
|---|---|---|---|
| field_1 | (250, 405, 695, 110) | (302, 462, 840, 125) | ~52px, ~57px |
| field_9 | (1940, 3155, 477, 75) | (2344, 3596, 576, 85) | ~404px, **441px** |

→ field_9 (합계금액)의 Y 오차가 441px로 매우 큼 → 다른 텍스트 영역 크롭 → "30 7,3 그" 출력.

**T-28b는 방향 감지를 올바르게 수행했다. 문제는 방향 감지 이후 region crop 좌표가 1-1.jpg 해상도와 맞지 않는 것이다.** 이는 T-28b의 실패가 아니라 별도의 좌표 스케일 문제다.

---

## 9. 성능 결과

| 항목 | 값 |
|---|---|
| processing_time | **197.91초** |
| 예상 범위 (T-28a) | ~110초 |
| 실패 기준 (T-27) | 153~166초 |

→ **성능 회귀 발생.** 197.91초는 T-28a(110초) 대비 88초 초과, T-27 실패 기준(153초)도 초과.

**추정 원인:**
- 512px thumbnail OCR: 224px 대비 픽셀 수 ~5.2배 → 방향 판단 OCR 2회 각각 더 느려짐
- invoice_statement 파서의 풀 이미지 OCR이 여전히 주요 시간 소요
- 별도 검증 필요: 정상 1.jpg도 동일 수준인지 확인

---

## 10. 다음 작업 제안

### 즉시 필요 (T-28b 완성)

**Sub-issue 1: 템플릿 좌표 해상도 스케일 문제**
- 원인: 템플릿 region 좌표가 2483×3511 기준, 1-1.jpg는 3000×4000
- 해결 방향: 템플릿 적용 시 이미지 해상도에 맞게 좌표 스케일 정규화, OR 1-1.jpg를 1.jpg와 동일 해상도로 촬영
- 관련 코드: `main.py` 내 region crop 좌표 적용 부분 (rx, ry, rw, rh 적용 시 이미지 크기 반영)

**Sub-issue 2: 성능 회귀 조사**
- 512px thumbnail이 실제로 어느 정도 시간을 추가하는지 측정
- 정상 1.jpg도 같은 수준(197초)인지, 아니면 1-1.jpg 특이 케이스인지 확인
- 필요시 target_short=384로 조정하여 정확도/속도 균형 재조정

**Sub-issue 3: BIZ number 파서 단독 추출 실패**
- 파서가 "118-81-00450"을 찾았으나 `supplierBusinessNo` 할당 실패 (1개만 발견 시 split 실패)
- invoice_statement 파서 로직 검토 필요 (코드 수정은 다음 단계)

### 장기 방향

- 거래명세서 RunOCR에서 region crop 대신 document_fields(parser output) 우선 사용 검토
- 또는 template 좌표를 이미지 비율 기준으로 저장하는 구조 개선

---

## 11. 요약

| 검증 항목 | 결과 |
|---|---|
| T-28b 코드 live 반영 | ✅ 확인 (서버 시작 시간이 코드 수정 이후) |
| templateImageNormalization 존재 | ✅ raw response에 존재 |
| appliedRotation | **180** ✅ (올바르게 감지됨) |
| orientationTargetShort | **512** ✅ (invoice_statement 전용 경로) |
| orientationMode | **invoice_template_0_180** ✅ |
| 파서 "118-81-00450" 인식 | ✅ (extract_debug에서 확인) |
| region crop field_1 | ✗ "서울 [배달]" (좌표 불일치) |
| 원인 확정 | **Case C** — 좌표 해상도 불일치 |
| 성능 | ⚠️ 197.91초 (회귀 발생, 별도 조사 필요) |
