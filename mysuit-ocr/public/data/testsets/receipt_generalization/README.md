# receipt_generalization 샘플셋

계획 문서: docs/RECEIPT_GENERALIZATION_TESTSET_PLAN_20260426.md

---

## 목적

baseline(10장) / google(11장) 이후, 영수증 계열 일반화 성능을 추가로 검증하기 위한 신규 샘플셋.

- card_receipt 과적합 방지 확인
- pos_receipt / food_cafe_receipt / medical_receipt 다양성 확보
- finance_slip / handwritten suppression 정상 동작 확인

---

## 샘플 수집 기준

- 실물 영수증 직접 촬영 우선
- 기존 baseline/google tuning에 사용하지 않은 미사용 샘플 사용 가능
- 공개/합성 샘플은 보조용으로만
- **민감정보(카드번호, 환자정보, 개인 이름 등) 마스킹 필수**
- 병원/약국 샘플은 처방 내용 포함 여부 주의

---

## 파일명 규칙

documentType 접두어 + 순번:

```
pos_001.jpg       POS/마트/편의점 영수증
pos_002.jpg
food_001.jpg      음식점/카페 영수증
food_002.jpg
card_001.jpg      카드전표/일반 영수증
medical_001.jpg   병원/약국 영수증
finance_001.jpg   은행/금융 전표 (suppression 확인용)
unknown_001.jpg   미분류
```

---

## 권장 documentType 비율 (15~30장 기준)

| documentType | 권장 장수 | 비율 |
|---|---|---|
| pos_receipt | 5~10장 | 30~40% |
| food_cafe_receipt | 4~8장 | 20~30% |
| card_receipt | 3~6장 | 15~20% |
| medical_receipt | 2~4장 | 10~15% |
| finance_slip | 1~3장 | 5~10% |
| unknown | 0~2장 | 선택 |

---

## manifest.json 작성 방법

샘플 이미지 추가 후 manifest.json의 items 배열에 아래 형식으로 추가:

```json
{
  "filename": "pos_001.jpg",
  "documentType": "pos_receipt",
  "qualityTags": ["small_text"],
  "difficulty": "medium",
  "expectedStatus": "selected",
  "notes": "편의점 영수증. 텍스트 작음."
}
```

---

## 최초 validation 원칙

1. 샘플 수집 및 manifest 작성 완료 후 Run All 실행
2. **코드 수정 없이** initial validation만 수행
3. 결과 파일: `validation_results_receipt_generalization_initial.json`
4. 실패 패턴 분석 후 보정 여부 판단
5. 보정 시 반드시 baseline_fast → google → baseline 회귀 확인
