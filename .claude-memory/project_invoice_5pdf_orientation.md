---
name: project_invoice_5pdf_orientation
description: "5.pdf detect_orientation misrotation(가로→세로 90°): 1T 진단 → 1U patch로 해소 → 1U-after precheck로 PARTIAL_READY(5/6 산술정확, idx3만 review). UI GT 작업 가능"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2aeb5efc-9329-48ca-863a-3476260ca40a
---

2026-06-02 FULL-UNSTRUCTURED-INVOICE-1T precheck 완료 (precheck-only, 운영코드 무수정).

**확정 결론**: 5.pdf가 RunOCR에서 회전돼 보이는 원인은 **`ocr-server/preprocess.py`의 `detect_orientation`** (main.py 비정형 경로 line ~2249에서 호출)이 **정방향 landscape 문서를 90° 회전해 portrait로 만들기** 때문. rootCauseCategory = **PREPROCESS_ORIENTATION_MISROTATION**.

증거 (fresh 단명 uvicorn :9190, 상시 :9099 미접촉):
- PDF metadata: page rotation=**0**, mediabox=**landscape**, 회전 메타 없음 → 원인 아님.
- render: fitz get_pixmap(dpi=200) = landscape, rotation-zeroed도 landscape → 정상 렌더, 원인 아님.
- route timings: `original_image_wh [1654,1169] landscape → doc_img_wh_after_orientation [1169,1654] portrait`, rotatedDoc=true.
- OCR bbox: 5.pdf tallFrac **0.954**/wideFrac 0.034 (텍스트 세로=틀어진 프레임) vs 대조군 1.jpg wideFrac **0.925**(정상).
- UI: frontend는 backend `processed_image`(post-orientation OCR 이미지)를 그대로 표시(RunOcrWorkspace.tsx:1203 `ocrDisplayUrl = processedImageUrl ?? displayUrl`), 자체 rotate 없음 → UI-only 아님.

**메커니즘**: `detect_orientation`에서 입력이 landscape면 `landscape_first=True`→ first_pass=(90,270)만 점수화하고 `strong_landscape_first_pass` 등 early-stop 시 **angle 0을 한 번도 평가 안 함** → natively-landscape 문서가 강제 90/270 회전. main.py line ~2022-2027 주석도 224px thumbnail 오판 위험 경고.

**범위**: 5.pdf 전용 아님 — 2.pdf도 misrotation(portrait→landscape, tallFrac 0.933)이나 이미 hard-case fallback. 1.jpg는 portrait→portrait_first라 rotatedDoc=false로 영향 없음.

**상태 재분류**: 5.pdf = ORIENTATION_PREPROCESS_DEFECT → **UI GT Draft HOLD** (1S의 freeValid/rowCount 6은 방향 정상성 보증 못 함; tableRows는 90° 회전 프레임 위에 생성됨). 1.jpg는 GT READY 유지([[project_invoice_1q_column_mapping]]).

**1U 완료(Codex/GPT-5)**: `preprocess.py` detect_orientation에 `zero_angle_evaluated_before_early_stop`(landscape_first에서 early-stop 전 angle 0 평가) + `native_landscape_zero_guard` 추가. 백업 `ocr-server/backup/preprocess_before_FULL_UNSTRUCTURED_INVOICE_1U_5PDF_PREPROCESS_ORIENTATION_PATCH.py`.

**1U-after precheck 완료(2026-06-02, Claude Code, 운영 무수정)**: fresh uvicorn :9191로 재검증. 5.pdf orientation **해소 확정** — after_orientation=landscape, rotatedDoc=**false**, horizontalTextDominant=**true**(wideBoxFrac 0.977). 정방향 tableRows 품질: rowCount 6, **5/6 산술정확**(q×u=amount), 소계/누계 혼입 0, 빈 quantity 0, NRFS75M=spec(idx5, 3000/550/1,650,000 정확). 단 **idx3**(300×545=163,500 vs amount 163,635, spec 누락)이 알려진 OCR 금액 불일치 → **review 대상, 자동보정 안 함**. draft smoke: exportBlocked=false, export-safe. 회귀: 1.jpg rotatedDoc=false/rowCount 28/대표행·suspect 보존, 2.pdf auto-release 없음.

**결정**: 5.pdf = **UI_GT_RESUME_PARTIAL_READY_FOR_5PDF** (ORIENTATION_FIXED_TABLE_PARTIAL_READY). manual-review guard와 함께 UI GT Draft 작업 가능, idx3 정정 후 final 승격. parser patch는 단일샘플 근거 부족이라 보류(추가 landscape 거래명세서에서 체계적 mismatch 재현 시 재검토).

**다음**: `FULL-UNSTRUCTURED-INVOICE-1V-5PDF-UI-GT-DRAFT-WITH-MANUAL-REVIEW-GUARD` (또는 1.jpg와 묶어 1V-UI-GT-DRAFT-CREATION-1JPG-5PDF). 산출물 `tmp/full_unstructured_invoice_1u_5pdf_table_mapping_after_orientation_*` + checker(44그룹 PASS).

산출물: `tmp/full_unstructured_invoice_1t_5pdf_*`(summary/report/pdf_metadata/render/preprocess/route/table_impact/patch_target) + checker `.mjs`(40그룹 PASS). 관련 [[project_invoice_unstructured_roadmap]].
