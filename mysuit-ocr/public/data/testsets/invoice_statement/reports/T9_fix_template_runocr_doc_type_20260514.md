# T-9-fix Template/RunOCR documentType 라우팅 보정 결과

**작업일**: 2026-05-14
**모델**: Claude Code Sonnet

---

## 1. 수정 파일

| 파일 | 수정 내용 |
|---|---|
| `ocr-server/main.py` | `documentType: str = Form("")` 파라미터 추가 + doc_type 결정 우선순위 |
| `mysuit-ocr/src/components/upload/UploadWorkspace.tsx` | TemplateItem.documentType 추가 + FormData 전송 |
| `ocr-server/data/templates.json` | TPL-31D13CF3에 documentType: invoice_statement 추가 |

## 2. 백업 파일

- `backup/main_20260514_before_T9_fix_template_doc_type.py`
- `backup/RunOCR_20260514_before_T9_fix_template_doc_type.tsx`
- `backup/templates_20260514_before_T9_fix_template_doc_type.json`

## 3. 핵심 요약

Template/RunOCR 경로에서 1.jpg가 receipt_pos로 오분류되던 문제 해결.

원인: classify_document()가 template field 텍스트를 receipt_pos로 분류
해결: doc_type 결정 우선순위 신설 (explicit payload > template_json.documentType > classify_document)

결과: doc_type=invoice_statement, rowCount=28/28

## 4. 기존 문제

| 항목 | fix 전 |
|---|---|
| template path doc_type | receipt_pos |
| tableRows | 0/28 |
| invoice_statement extractor | 미진입 |

## 5. Template metadata 조사

| 항목 | 결과 |
|---|---|
| template_id | TPL-31D13CF3 |
| template_name | 거래_1 |
| documentType (fix 후) | invoice_statement |
| table region count | 0 (field 타입만) |
| colGuides | 없음 |

## 6. documentType 우선순위

1. explicit payload documentType (새로 추가)
2. template_json.documentType (새로 추가)
3. classify_document() 결과 (기존 fallback 유지)

## 7. RunOCR payload 변경

| 필드 | 비고 |
|---|---|
| template_id | 기존 |
| regions | 기존 |
| documentType | T-9-fix 신규 (template.documentType 있을 때만) |

## 8. 1.jpg E2E 결과

| 항목 | Mode A (template_id only) | Mode B (explicit documentType) |
|---|---|---|
| doc_type | invoice_statement | invoice_statement |
| template_path | True | True |
| rowCount | 28/28 | 28/28 |
| tableMeta 존재 | True | True |
| extractionSource | header_column_mapping | header_column_mapping |
| tableBoundsUsed | True | True |

## 9. 2.pdf~7.pdf

저장된 template annotation 없음 (모두 skipped).
Test 탭 경로에서 7/7 rowCount 정상.

## 10. 검증 결과

| 항목 | 결과 |
|---|---|
| py_compile main.py | PASS |
| E2E script (Mode A + B) | PASS |
| typecheck | PASS |
| build | PASS |

## 11. 다음 작업 판단

T-9-fix 완료.
- columnGuidesUsed=False: table region이 없으므로 colX 없음 (정상)
- extractionSource=header_column_mapping: 자동 헤더 감지 경로 정상
- 2~7.pdf template 저장 후 동일 방식 E2E 가능
