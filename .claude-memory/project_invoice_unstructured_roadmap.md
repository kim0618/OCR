---
name: invoice-unstructured-roadmap
description: "거래명세서 \"완전 비정형\" OCR 6단계 로드맵 + 현재 단계. 학습 방향(A/B), 데이터 제약, 게이트 원칙"
metadata: 
  node_type: memory
  type: project
  originSessionId: f976f5f5-7cb0-4892-9e4b-40453e4c9d76
---

거래명세서(invoice_statement)를 "완전 비정형"(템플릿/컬럼 좌표 지정 없음)으로 추출·학습하는 방향으로 진행. 2026-05-29 6단계 로드맵 합의.

**사용자 mental model 5단계 (2026-06-08 확인):**
1. 7장 양식별 GT 작성 (**현재 진행 중**) — 1.jpg, 2~7.pdf
2. 7 양식 × 3~4 variant 샘플 추가 + GT 작성 (= 1W의 35개 계획과 동일)
3. 35장으로 비정형 extractor 파이널 검증 (= 기존 3단계 7장 baseline + 오류 4버킷)
4. 학습 인프라 구축 (분할/메트릭/야간배치/회귀감지/GT 스키마) (= 기존 4단계)
5. 수천 장 데이터 도입 후 본격 학습 (= 기존 5~6단계)
- 게이트: 2→3은 variant GT 전부 완성 후. 3→4는 35장 결과 분석 완료 후 (35장으로 아키텍처 확정 금지). 4→5는 수천 장 데이터 확보 후. 수천 장은 **아직 없음**.

**Why:** 템플릿/비정형 템플릿 두 방식은 결국 컬럼을 지정하는 방식인데, 그 전에 완전 비정형이 먼저 필요하다는 판단. 세 방식 모두 같은 `document_fields`/`tableRows` 공통 출력 구조를 채우게 해서, 한 방식 개선이 공유 전처리/OCR/출력구조를 통해 다른 방식으로 전이되게 하는 게 핵심 설계.

**핵심 사실/결정:**
- "학습"은 RunOCR(추론)이 아니라 오프라인 GPU(AWS) 배치 작업. 화면 아님.
- 학습 1차 타깃 = **B(구조화/KIE: 읽은 텍스트를 올바른 필드/컬럼·가변 로우로 배치)**. A(글자 인식 fine-tune)는 평가 하니스가 인식 병목이라 판정할 때만. 거래명세서는 도트프린터/도장/흐림으로 A가 병목일 수도 있어 측정으로 결정.
- 아키텍처: **OCR+KIE 우선, VLM은 비교 실험**. supplier/site/layout holdout 성능으로 최종 결정.
- 평가 split은 랜덤 금지, **supplier/site/layout 단위 holdout 필수** (같은 양식이 train/test 동시 포함 시 성능 과대평가).

**데이터 제약(중요):** 거래명세서 수천 장 데이터는 **아직 없음**. 그래서 5~6단계(수집/라벨링/학습)는 데이터 확보 전까지 불가. ~~현재 GT는 7장짜리 헤더/요약 레벨뿐이라 per-row 테이블 정답이 없음~~ → **2026-06-09 갱신: `testsets/invoice_study/`에 per-row GT 6장 생성됨**(draft-gt-document.v1, scalar+tableRows+bbox, 2.pdf 제외). per-row 정답 갭 해소. 이를 fixture로 평가/개선 루프 인프라 구축 = [[project_learn_loop_infra_plan]] (새 채팅방서 Phase 0부터).

**단계(데이터 없이 가능 = 0~4):**
- 0: 현재 템플릿/비정형 템플릿 1.jpg parity close-out (timebox, blocking만 수정)
- 1: 전처리 안정성 검증 (1.jpg 기준 + 변형 1-1/1-2/1-3, 보존율 측정)
- 2: RunOCR 완전 비정형 진입점 (template_id 없이 documentType=invoice_statement 고정)
- 3: 7장 baseline 측정 + 오류 4버킷 분류 + A/B 병목 **가설**(확정 아님)
- 4: GT 라벨 스키마 확정 (document fields / tableRows / optional bbox / validation rules)
- 5: 데이터 수집/라벨링 (수천 장, holdout split) — 데이터 필요
- 6: 아키텍처 확정 + 학습 + holdout 재평가 — 데이터 필요

**현재 위치(2026-05-29):** **0단계 parity close-out 완료 = GO**(작업명 FRONTEND-INVOICE-RESULT-PARITY-4L-UI-SMOKE-CLOSEOUT). env-cleared fresh 서버(9098)와 재기동 9099 양쪽에서: 비정형 1.jpg env 없이 used=True/fallbackUsed=False/source=invoice_statement_free/mode=unstructured/**28행**/소계 row 없음/첫 행 `헥사메던액0.12%`·1,050·420,000/scalarMerge filledKeys 9개; 일반 템플릿 `거래_1`(TPL-31D13CF3)은 region path 유지·28행·회귀 없음. compile/build/typecheck/4K checker/4L checker 전부 PASS, 운영 코드·data 무변경. 산출물: `tmp/run_frontend_invoice_result_parity_4l_route_smoke.py`, `..._summary.json`, `..._ui_smoke_closeout.md`, `tmp/check_frontend_invoice_result_parity_4l.py`. **UI 시각 확인은 BLOCKED-NEEDS-HUMAN**(Playwright 미설치 + 비정형 템플릿이 브라우저 localStorage 의존).

**2B 완료(2026-05-29):** main.py full-OCR 분기에 explicit documentType override 적용됨 — marker `FULL_UNSTRUCTURED_INVOICE_DOCUMENTTYPE_OVERRIDE_PATCH_2B`(~L2352), `doc_type = _explicit_doc_type or _classified_doc_type`(~L2355). region 분기는 L2196-2197. 이제 template_id 없이 `documentType=invoice_statement`만 보내도 분류기 의존 없이 free path 진입. (main.py uncommitted dirty.)

**2C precheck 완료(2026-05-29):** RunOCR no-template 완전비정형 UI mode 정적 분석. 결론: (1) RunOCR 실행이 `activeTemplateId`에 강결합 — `canRunOcr`(RunOcrWorkspace L1130)+`runOcr` early-return(L841)이 템플릿 강제. (2) payload의 documentType/templateMode/isUnstructuredTemplate/regions/template_id 전부 activeTemplate 유래(L856-863) → 템플릿 없으면 free path 트리거 값 없음. (3) **품목표 table은 템플릿 없이도 표시 OK**(document_fields.tableRows, OcrResultPanel L761; VM docType=result.doc_type, tableResultViewModel L423; 4I materialize L844). (4) **scalar 필드(공급자/합계 등)는 template info[] 필요**(mapOcrResponse L272 templateFields 순회) → **default 거래명세서 display schema 필요**. buildOcrFormData·mapOcrResponse·OcrResultPanel·backend 변경 불필요. **권장 2D = Option A**: RunOCR 카드행에 "템플릿 없음/완전비정형(거래명세서)" 카드 + client-side 합성 기본 거래명세서 템플릿(mode unstructured, documentType invoice_statement, info[]+tables[] 기본 schema)으로 payload·결과매핑을 기존 경로로 재사용, RunOcrWorkspace 단일 파일 + 합성 템플릿이면 충분. templateMode 값은 `unstructured` 재사용(backend `==unstructured` 체크). 산출물: tmp/run_full_unstructured_invoice_no_template_ui_mode_probe_2c.py, _summary.json, _precheck.md, check_..._2c.py.

**2D 완료(2026-05-29):** RunOcrWorkspace.tsx **단일 파일**(+98줄)에 완전비정형 진입점 구현. client-side 합성 템플릿 `DEFAULT_UNSTRUCTURED_INVOICE_TEMPLATE`(id `__FULL_UNSTRUCTURED_INVOICE__`, mode unstructured, documentType invoice_statement, regions [], info[] 13 scalar 필드(labelEn=canonical document_fields 키), tables[] 품목표 7컬럼) + RunOCR 카드행에 "템플릿 없음 / 완전 비정형(거래명세서)" 카드 + `resolveActiveTemplate(id,templates)`(synthetic id면 합성 반환) + payload `templateId: isFullUnstructuredInvoiceId ? "" : activeTemplateId`(synthetic id backend 미전송). run gate는 무변경(synthetic id가 truthy activeTemplateId라 통과). buildOcrFormData/mapOcrResponse/OcrResultPanel/tableResultViewModel/backend **전부 무수정**. route smoke(env-cleared 9097): A 합성(template_id 미전송)=used True/28행/free_parser/소계 없음/scalarMerge 9, B 기존 비정형=28행 회귀없음, C 일반 거래_1=28행 template_region 회귀없음. build/typecheck/2D checker PASS. 합성 카드는 하드코딩이라 localStorage 불요 → UI 즉시 테스트 가능(자동 UI는 Playwright 부재로 BLOCKED-NEEDS-HUMAN). 산출물: tmp/run_..._probe_2d.py, _summary.json, _patch.md, check_..._2d.py.

**2D 후속 + 2E(2026-05-29):** 사용자가 RunOCR 카드 이름을 **`비정형`**(span+template name)으로 변경, 전용 이미지 `mysuit-ocr/public/images/no-template-invoice-preview.svg`(보라색 점선문서+반짝임)로 `거래명세서_비정형` 카드와 시각 구분. **2E UI smoke close-out=GO**: 사용자가 브라우저(8089)에서 비정형 카드→1.jpg 실행 직접 확인 — 필드 14건(scalar 13+품목표 1)/품목표 28행/첫 행 헥사메던액0.12%·1,050·420,000/소계 없음/Custom editable/`비정형 테이블` 문구 없음. 산출물 tmp/full_unstructured_invoice_2e_*. RunOcrWorkspace hash 18c935c2(2D+rename). review_log.jsonl은 사용자 수동 run 흔적(작업 무관).

**no-template 완전비정형 거래명세서 진입점이 backend(2B)+frontend(2D)+UI확인(2E)로 end-to-end 닫힘.** **1A 완료(2026-05-29):** 전처리 안정성 측정 하니스 구축(재실행 가능). 변형 파일은 `invoice_statement/1/` 하위(1-1/1-2/1-3). **raw/OFF는 route 미지원**(full-OCR 경로가 고정 always-on 전처리 체인 detect_document→orientation→deskew→resize950→CLAHE→unsharp, main.py ~2243-2296, disable 폼파라미터 없음) → **직접 callable로 측정**(harness가 get_ocr_engine 동일 config PaddleOCR + extract_invoice_statement_free를 enhancement OFF/resize-only로 호출; 운영 코드 무수정). processed/ON=route. 지표: token-set F1/numeric/money preservation, keyFieldPreservation(13 scalar), tableRows, amountCellPreservation(문자열 diff 금지, line-order 비의존). **결과(소표본 3장=가설):** 전처리는 **강한 양의 기여**(1-1/1-2 raw rows=2·F1 0.10~0.13 → processed rows=28·F1 0.81~0.86, 금액 cell 0.9~0.98, row 2→28 복구) = 회귀 아님/“전처리가 망친” 케이스 아님. 단 strict bar(token F1≥0.95, keyField 100%) 미달(keyField 0.6~0.7) → **게이트 NO-GO(strict)**, blocking = **회전/열화 변형의 scalar 문자 인식 정확도 한계**(전처리 아님). 깨끗한 reference는 raw도 F1 0.92/28행(전처리 기여 작음). 1A checker PASS(하니스/체커 정상, 게이트는 측정결과). 산출물 tmp/full_unstructured_invoice_1a_*. 

다음: **FULL-UNSTRUCTURED-INVOICE-3A — 7장 baseline + 오류 4버킷 + A/B 병목 가설**(1A가 인식(A) 병목 신호를 줌; 7장으로 검증). 소표본으로 아키텍처 확정 금지.

**2A precheck 결과(2026-05-29 기준 — 코드 위치는 재확인 권장):**
- `extract_invoice_statement_free`는 **독립 모듈** `ocr-server/extractors/invoice_statement_free.py`(def ~1318), main.py에서 import(~62)·호출(~2680). (별도 파일 맞음)
- `/ocr/extract` form 필드: `template_id/regions/documentType/templateMode/isUnstructuredTemplate` (main.py ~1899-1913).
- 템플릿 없이도 비정형 표시 가능: `templateMode=='unstructured'` → `_is_unstructured_template` (main.py ~1951). free path 게이트 `not region_list and _is_unstructured_template`(main.py ~2674)는 template_id 불요.
- **2B 핵심 패치 지점**: free path는 `if doc_type=='invoice_statement'`(main.py ~2576) 하위. 그런데 region 없는 full-OCR 분기에선 doc_type을 `classify_document()`로만 결정(main.py ~2350)하고, `documentType` form 오버라이드는 region 분기(~2197)에만 적용됨. → **2B = full-OCR 분기에도 explicit documentType 오버라이드 적용**해야 "documentType=invoice_statement 고정"이 분류기 의존 없이 결정적으로 동작. 기존 거래명세서_비정형 템플릿도 동일 full-OCR 분기라 0단계 parity는 classify_document가 1.jpg를 invoice_statement로 잡는지에 의존(0단계에서 먼저 확인).

**1W 로드맵 재정렬(2026-06-02):** 목표를 **"자동 추출 완벽화" → "GT editable skeleton 확보"** 로 명시 재정렬(운영 무수정 precheck). 초기 학습/평가 세트 = **original 7 + family별 variant 4 = 35개** (계획만; original 7 draft 완성 전 variant 생성·학습세트 확정 금지). 샘플 matrix(관측 1N/1U-after): 1.jpg=GT_EDITABLE(row11만 확인), 5.pdf=GT_EDITABLE_WITH_REVIEW(draft 재생성+:9099 재시작 필요), 2/3/4/6/7=NOT_GT_EDITABLE_YET(각 독립 skeleton precheck 2A~2E; 단 1U orientation fix 이후 fresh :9099 재측정 필요 — 특히 6.pdf rowCount 6은 승급 유망). 추천 next=1X-1JPG-ROW11-ORIGINAL-CONFIRMATION(P1) / 1X-5PDF-DRAFT-RECREATE-FRESH-9099(P1) → 2A-2PDF-SKELETON(P2). 산출물 `tmp/full_unstructured_invoice_1w_gt_editability_*` + dataset_plan_35_samples + next_actions + checker(31그룹 PASS). 상세 워크플로 상태 [[project_invoice_gt_draft_workflow]].

**How to apply:** 거래명세서 OCR 작업 요청 시 이 단계 맥락으로 해석. 7장 결과로 아키텍처 확정하지 말 것. 전처리는 이미 구현돼 있음(ocr-server/preprocess.py) — 검증/튜닝 단계지 신규 구축 아님. 관련: [[invoice-statement-prep]], [[data-storage-architecture]].
