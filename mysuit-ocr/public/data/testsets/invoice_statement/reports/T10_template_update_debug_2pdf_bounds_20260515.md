# T-10 Template update debug - 2.pdf bounds 저장 반영 결과

작성일: 2026-05-15

## 1. 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `mysuit-ocr/src/components/ocr/OcrAnnotator.tsx` | edit mode에서 `template_id`를 POST payload에 포함 |

## 2. 백업 파일

| 파일 |
|------|
| `mysuit-ocr/backup/OcrAnnotator_20260515_before_T10_template_update_debug.tsx` |

## 3. 핵심 요약

**근본 원인 2가지**:

1. **TemplateWorkspace 편집 버튼 미구현**: `TemplateWorkspace.tsx` line 153의 "편집" 버튼이 `"편집 기능은 준비 중입니다."` alert만 표시. 사용자가 backend template을 UI에서 편집 불가.

2. **OcrAnnotator `template_id` POST payload 미포함**: edit mode일 때도 `exportPayload`에 `template_id`가 없어서, backend가 name-matching으로만 update. API로 생성된 template은 localStorage에 없어 template page에서 선택 불가 → edit mode 진입 불가 → `template_id` 포함 경로 자체가 미동작.

**해결**: API로 직접 TPL-A4585BC7 bounds 업데이트 (h=2112→1080, yMax=2248→1216). rowCount 13/13 달성.

## 4. 2.pdf templates.json record 조사

| template_id | source | bounds | updatedAt | 선택 여부 |
|-------------|--------|--------|-----------|-----------|
| TPL-A4585BC7 | file=2.pdf, docType=invoice_statement | x=111, y=136, w=1486, **h=1080** | 2026-05-15 13:32:59 | ✅ 선택됨 (유일) |

중복 없음. 단일 record.

## 5. UI 저장/update 경로

| 항목 | 결과 |
|------|------|
| save handler | `OcrAnnotator.saveTemplateJson()` |
| edit mode 여부 | `isEditMode = !!selectedTemplateId` |
| template_id payload 포함 | **수정 전: 미포함** / 수정 후: `selectedTemplateId` 있을 때 포함 |
| POST/PUT/PATCH | POST /templates (항상) |
| 최신 regions state 사용 | ✅ `buildExportPayload({templateName, loaded, regions, documentType})` |
| TemplateWorkspace 편집 버튼 | ❌ 미구현 ("준비 중" alert) → backend 전용 templates 편집 불가 |

## 6. backend save/update 동작

| 항목 | 결과 |
|------|------|
| id 중복 시 update | ✅ (`existing.template_id == template_id` OR `existing.template_name == name`) |
| updatedAt 갱신 | ✅ (datetime.now()) |
| regions 보존 | ✅ (전체 body를 template_json으로 저장) |
| file path | `ocr-server/data/templates.json` |
| template_id 없을 때 | 자동 생성 후 name-matching으로 update |

## 7. verify script template 선택 로직

| 항목 | 결과 |
|------|------|
| 선택 기준 | `filename ∈ EXPECTED` AND `table_region_count > 0` (첫 번째 매칭) |
| selectedTemplateId | TPL-A4585BC7 |
| selectionReason | 유일한 2.pdf+table region template |
| 다중 template 시 | 첫 번째 선택 (updatedAt 정렬 없음) |

현재 2.pdf template 1개 → 선택 문제 없음.

## 8. bounds 변경 확인

| 항목 | 이전 | 이후 | 변경 여부 |
|------|-----:|-----:|----------|
| x | 111 | 111 | 동일 |
| y | 136 | 136 | 동일 |
| width | 1486 | 1486 | 동일 |
| **height** | **2112** | **1080** | ✅ 변경 |
| **yMax** | **2248** | **1216** | ✅ 변경 |

## 9. E2E 결과

| 항목 | 결과 |
|------|------|
| 실행 여부 | ✅ (bounds-save-check script) |
| rowCount | **13** |
| expected | 13 |
| columnGuidesReceived | True |
| columnGuidesUsed | True |
| summary row 포함 | 없음 (yMax=1216으로 summary 영역 제외) |
| boundsChanged | **true** |
| decision | "rowCount 13/13 → 7.pdf/6.pdf annotation으로 이동" |

## 10. 검증 결과

- **py_compile**: 수정 없음 (OcrAnnotator.tsx TypeScript만 수정)
- **typecheck**: PASS ✅
- **bounds-save-check**: boundsChanged=true, e2eExecuted=true, rowCount=13/13 ✅
- **T-10 전체 현황**: 1.jpg 28/28 ✅, 5.pdf 6/6 ✅, 2.pdf 13/13 ✅

## 11. 다음 작업 판단

**rowCount 13/13 달성 → 7.pdf/6.pdf annotation 저장으로 이동**

남은 작업:
1. **TemplateWorkspace 편집 버튼 구현**: backend template을 UI에서 편집 가능하도록 (별도 작업)
2. **3.pdf, 4.pdf, 6.pdf, 7.pdf**: template annotation 없음 → UI에서 PDF 업로드 후 annotation 저장
3. **T-10-rerun**: 6/7 annotation 완료 후 전체 E2E 재검증
