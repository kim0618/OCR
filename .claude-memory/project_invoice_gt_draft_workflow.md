---
name: project_invoice_gt_draft_workflow
description: "UI GT Draft 워크플로 상태(1V/1W): 1.jpg draft 거의 준비됨(row11만 확인), 5.pdf draft 미생성+:9099 stale. draft 스키마=draft-gt-document.v1, candidate.source 출처enum은 export-safety 위반 아님"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2aeb5efc-9329-48ca-863a-3476260ca40a
---

2026-06-02 1W(UI GT Draft result review) 완료, 운영 무수정.

**UI-export draft 실제 스키마** (gtDraftBuilder 출력, §9 예상과 다름):
top-level = `schemaVersion`("draft-gt-document.v1"), `documentType`, `resultMode`("unstructured_template"), `orientationGt`, `normalizedResult{fields,tableRows}`, `excludedRows`, `reviewMeta`, `sourceMeta`, `builderMeta{builderVersion,warnings,exportBlocked}`, `sampleId`, `sourceFile`, `candidates{candidateFields,unmappedTextCandidates,userSelectedFields}`. fields는 {key,value,labelKo,...}; tableRows는 영어 key(rowIndex/rowType/itemName/spec/productCode/lotNo/expiryDate/quantity/unitPrice/amount/amountOnly/missingFields/fieldStatus/reviewStatus/excludeReason/sourceRowMeta).

**export-safety 주의(중요/재사용)**: candidate의 `source` 값에 `raw_ocr_fields` / `full_text_line` 같은 **출처 enum 라벨**이 들어 있음. 이는 후보가 어디서 왔는지 표시하는 메타이며 **raw OCR/full_text 덤프가 아님 → export-safety 위반 아님**. 단순 substring 스캔(`full_text`/`raw_ocr`)은 오탐하므로, 검토 시 **forbidden KEY + data:image/base64 run** 기준으로만 판정할 것. (1.jpg draft 122KB, base64 없음 → safe.)

**현재 GT 워크플로 상태(1W 검토 결과)**:
- **1.jpg**: draft 존재(Downloads `001_RUN-0833D73D__draft_gt.json`), 검토 = **NEEDS_MINOR_USER_FIX**. 구조/대표행(알베릭스연질캡슬/90c/23010-72ea)/row18·19·20/candidate(허용15종,userSel0)/export 모두 정상. 유일 이슈: **row11(lot 23001A1-10ea) quantity=10** ↔ parser 기대 빈값(1L 가드). 원본 대조 확인 필요(27,900÷2,790=10 산술만으로 확정 금지). 확인되면 READY_FOR_FINAL_REVIEW.
- **5.pdf**: **draft 미생성(DRAFT_NOT_FOUND)**. Downloads의 export 2개가 둘 다 1.jpg(`RUN-1F493F46`는 또 다른 1.jpg, 잘못된 key `합계금액` 잔존). 원인: **:9099가 여전히 stale(1U 이전)** — 재시작 없이는 5.pdf 회전(1V STEP 0). → 5.pdf는 :9099 재시작 후 정방향 확인+idx3 가드 적용해 `005_original__draft_gt.json` 재export 필요.

**다음**: row11 확인 + 5.pdf draft 생성 → 1W 재검토 → 둘 다 READY면 `FULL-UNSTRUCTURED-INVOICE-1X-FINAL-GT-PROMOTION-PRECHECK`. final GT/manifest/data/gt는 아직 미생성. 관련 [[project_invoice_5pdf_orientation]] [[project_invoice_1q_column_mapping]]. 산출물 `tmp/full_unstructured_invoice_1w_*` + checker(37그룹 PASS).
