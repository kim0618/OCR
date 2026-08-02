---
name: project-t10-header-skip
description: T-10-fix-6pdf-auto-header-row-skip 작업 완료 및 결과 — 6.pdf rowCount 7/6→6/6 fix
metadata: 
  node_type: memory
  type: project
  originSessionId: eebe7758-3bc3-4c5f-9f5a-9e82f356aea8
---

T-10-fix: template_colguides_expected_columns 경로에서 header-like row 자동 제외 로직 추가 완료 (2026-05-16).

**Why:** 6.pdf에서 tableBounds가 헤더 행을 포함할 때, colGuides 경로가 "NO 제품코드 5 24001 270305"를 데이터 row로 오인하여 rowCount 7/6 over 발생.

**핵심 변경:**
- `_COLGUIDES_HEADER_EXTRA_KW_RE` 정규식 추가 (NO, 제품코드, 제품명, 번호 등 포함)
- `_COLGUIDES_MIXED_ITEM_CODE_RE` 정규식 추가 (ANDC300C 같은 mixed-case 제품코드 보호)
- `_is_colguides_header_like_row()` 함수 추가 — skip_contact_filter=True 경로에서만 적용
- `_extract_items_using_boundaries()` 에 새 필터 삽입 (colGuides path only)
- `table_debug` dict에 `headerRowsSkippedCount/Samples/AppliedSource` 추가
- `tableMeta`에 위 debug 필드 노출

**결과:** E2E 7/7 exact (1.jpg 28, 2.pdf 13, 3.pdf 1, 4.pdf 1, 5.pdf 6, 6.pdf 6, 7.pdf 1)

**How to apply:** 앞으로 invoice_statement.py OCR extractor 수정 시, colGuides 경로(`skip_contact_filter=True`)에서 header row 필터가 적용된다는 점을 인지. 일반 경로나 OP-anchor 경로에는 적용 안됨.
