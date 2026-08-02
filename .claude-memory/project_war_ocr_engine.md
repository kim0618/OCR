---
name: project_war_ocr_engine
description: 경쟁사(백제/war) OCR 엔진 = 구글 Document AI (확정). 커스텀학습 vs 범용OCR은 URL증거만으론 미확정(2026-07-10 정정). easyOCR는 전환전 레거시
metadata: 
  node_type: memory
  type: project
  originSessionId: 03cae375-76f7-4148-823f-6e64de9dcc19
---

**경쟁사(백제약품/war) OCR 엔진 = 구글 Document AI (확정).** 단 **커스텀 학습 프로세서인지 vs 구글 범용 사전학습 OCR인지는 미확정**(2026-07-10 정정, 사용자가 "구글이 커스텀 아니지 않냐" 반문 → 재평가). 원증거 파일은 현재 작업트리에 없어 재검증 불가, 기록된 근거로만 판정.

증거 (.class 바이너리 문자열):
- `_waranalysis/WEB-INF/classes/net/baekje/ocr/engine/manager/OcrManager.class` 내 문자열: `s-documentai.googleapis.com`(= `{region}-documentai.googleapis.com`), `documentai`, `processorId`, `processorVersions/`, `processors/`
- `OcrServiceImpl.class`: `processorId`

**★2026-07-10 정정(과단정 철회):** `processorVersions/`는 **커스텀 증거 아님** — Document AI의 **모든** 프로세서(스톡 범용 Document OCR 포함, 예 `pretrained-ocr-v2.0`)가 동일하게 `processors/{id}/processorVersions/{ver}` 경로로 호출됨. 즉 URL만으론 커스텀/범용 구분 불가. 구별하려면 processor **타입**(OCR_PROCESSOR vs CUSTOM_EXTRACTION)이나 버전ID 형태(스톡=`pretrained-*`, 커스텀=해시/사용자명)를 봐야 하는데 그 config는 미보유. **오히려 범용 OCR + learndata 후처리보정 구조일 공산이 큼**(구글 범용 OCR 자체가 강함).

**★내 초기 오판 정정:** application-real.properties:63의 `easyOCR_1_parse.py`는 **전환 전 레거시**. 실제 엔진은 외부 파이썬 스크립트가 아니라 Java(OcrManager)가 직접 구글 Document AI 호출. 첫 조사가 틀린 이유 = properties 텍스트만 보고 .class 바이너리 문자열 상수를 안 뜯음. easyOCR 결론은 폐기.

**구조:** OCR층(구글 Document AI, 범용/커스텀 미확정) + learndata SQL 보정층 2겹. .war엔 훈련코드/모델파일 없음(구글 관리형 클라우드거나 애초에 학습 안 함).

**How to apply:**
- baseline_matrix "Google" 라벨 **맞음**(GT=구글 Document AI 출력).
- base 품명 26.7% 낮은 건 OCR약함 아니라 "raw글자 vs 마스터정식명" 차이. 글자 인식 자체는 강함.
- ★**8.7pp 격차(우리72.5 vs 구글81.2, 둘다 learndata無 master통과)=순수 OCR 읽기품질 차**(Paddle vs 구글읽기). 구글이 커스텀이든 범용이든 우리 할 일은 **Paddle을 구글만큼 읽게** = 파인튜닝. 단 상대가 범용이면 "구글 범용OCR 품질"을 좇는 데이터규모 싸움이라 냉정한 목표.
- 매칭(learndata/master)은 엔진무관 — [[project_baseline_matrix_stages]] 재현 로직 유효.
