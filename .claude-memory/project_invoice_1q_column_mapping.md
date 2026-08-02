---
name: project_invoice_1q_column_mapping
description: "1.jpg 완전비정형 표 컬럼 섞임(spec/lotNo)=backend 문제로 1Q 확정 → 1R 파서 패치 → 1S smoke로 HOLD 해제(UI_GT_RESUME_READY)"
metadata: 
  node_type: memory
  type: project
  originSessionId: e73d3e87-6f67-4b09-a924-9c9837617aad
---

2026-06-02 FULL-UNSTRUCTURED-INVOICE-1Q precheck 완료 (precheck-only, 운영코드 무수정).

**확정 결론**: 1.jpg 완전 비정형 표의 컬럼 섞임은 frontend 표시가 아니라 **backend `tableRows` 데이터 문제**.
- 섞임 범위: `spec` / `lotNo` / `itemName 꼬리` 3컬럼, **하단 블록 행 8~27 (20행)** 한정.
- `expiryDate / quantity / unitPrice / amount`는 좌표(템플릿 등가) 기준과 **0건 불일치** = 정상.
- 메커니즘: `_group_ocr_items_into_row_texts`가 cx/bbox를 버리고 텍스트 평탄화 → `_parse_table_row_candidate`가 토큰 순서로 `spec=첫 숫자 앞 마지막 라벨토큰` 배정. OCR이 LOT를 `23010-72ea`처럼 **한 토큰으로 병합**(20개, 모두 cxBand=lotNo에 정확히 위치) → spec으로 흡수, lotNo는 `\d{5,}`만 인식해 빈값, 진짜 규격은 itemName 꼬리로.
- frontend `extractUnstructuredTableRows`는 columnKey 순수복사 → 범인 아님.
- 1L 보정 numeric rows(11/18/19/20) 현행코드 유지 확인. free rowCount 28 유지.

**다음 작업**: `FULL-UNSTRUCTURED-INVOICE-1R-1JPG-FREE-TABLE-COLUMN-MAPPING-PARSER-PATCH`
(파일 `ocr-server/extractors/invoice_statement_free.py`, 함수 `_parse_table_row_candidate`/`_group_ocr_items_into_row_texts`. 방향: cx/bbox x-band로 spec/lotNo 배정 또는 `LOTCODE-Nea` 토큰 분해기. 가드: 1.jpg 하드코딩 금지, 산술 quantity 금지, 상단블록/baseline 회귀 금지, 템플릿박스 의존 금지).

**해제됨 (2026-06-02)**: 1R(Codex/GPT-5, `_looks_like_lot_code_with_unit_suffix`+shift-repair) + 1S smoke로 HOLD **해제 → UI_GT_RESUME_READY**. 1S에서 현재소스 단명 uvicorn(:9189)으로 route→draft 검증: 1.jpg rowCount 28, 대표행 `알베릭스연질캡슬/90c/23010-72ea` route·draft 일치, 1Q target mismatch 20/20 개선 유지, row11/18/19/20 numeric 보존, 5.pdf rowCount 6 유지, 2.pdf auto-release 없음, candidate/export-safety contract 유지. 이제 실제 UI에서 1.jpg/5.pdf GT Draft 작업 가능. (운영 비정형 템플릿은 브라우저 localStorage 전용 — backend templates.json 비정형 0개; 좌표 x-band는 검증 reference로만.)

다음: 사용자가 UI에서 GT Draft 생성 → `FULL-UNSTRUCTURED-INVOICE-1T-UI-GT-DRAFT-RESULT-REVIEW`. 1P handoff 문서의 1.jpg HOLD 문구는 갱신 대상(`1S-UI-HANDOFF-DOC-REFRESH`).

산출물: `tmp/full_unstructured_invoice_1q_1jpg_*`(1Q) + `tmp/full_unstructured_invoice_1s_*`(1S: route/draft compact·summary·report·ui_decision·checker 43그룹 PASS). 관련 [[project_invoice_unstructured_roadmap]].
