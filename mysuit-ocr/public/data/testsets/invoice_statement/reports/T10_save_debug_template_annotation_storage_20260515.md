# T-10-save-debug Template annotation 저장 플로우 점검 결과

작성일: 2026-05-15

## 1. 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `mysuit-ocr/src/components/ocr/core/export.ts` | `buildExportPayload`에 `documentType` 파라미터 추가 |
| `mysuit-ocr/src/components/ocr/OcrAnnotator.tsx` | PDF 렌더링(pdf.js) 추가, `documentType` state 추가, selectedTemplate 로드 시 documentType 복원 |
| `mysuit-ocr/src/components/ocr/OcrRightPanel.tsx` | `documentType`/`setDocumentType` props 추가, select UI 추가 |
| `ocr-server/scripts/verify_invoice_statement_template_runocr_e2e_t10_rerun.py` | `BASE_URL` 8130 → 9099 수정 |
| `ocr-server/scripts/verify_invoice_statement_template_runocr_e2e_t10.py` | `BASE_URL` 8130 → 9099 수정 |

## 2. 백업 파일

| 백업 파일 |
|-----------|
| `mysuit-ocr/backup/OcrAnnotator_20260515_before_T10_save_debug.tsx` |
| `mysuit-ocr/backup/export_20260515_before_T10_save_debug.ts` |
| `mysuit-ocr/backup/OcrRightPanel_20260515_before_T10_save_debug.tsx` |
| `ocr-server/backup/verify_t10_rerun_20260515_before_T10_save_debug.py` |
| `ocr-server/backup/templates_20260515_before_T10_save_debug.json` |

## 3. 핵심 요약

**근본 원인 (2가지)**:

1. **OcrAnnotator PDF 렌더링 불가** (주요 원인): `onPickFile`이 `new Image(); img.src = pdfDataURL` 방식으로 PDF를 이미지로 로드하려 해서 실패. `loaded` 상태가 null이 되어 저장 버튼이 disabled. 즉, 2.pdf~7.pdf는 UI에서 아예 annotation 작업 자체가 불가능했음.

2. **`documentType` exportPayload 미포함**: `export.ts`의 `buildExportPayload()`가 `documentType`을 payload에 포함하지 않아, 저장된 template에 OCR 라우팅에 필요한 documentType이 빠짐. TPL-31D13CF3(1.jpg)의 documentType은 이전 T-9-fix에서 수동 삽입된 것으로 추정.

**부가 문제**:
- T-10/T-10-rerun 스크립트의 `BASE_URL`이 8130으로 잘못 설정됨 (실제 backend: 9099). OCR API 호출이 전부 실패하는 원인.

## 4. Template 저장 UI 경로

| 항목 | 결과 |
|------|------|
| 저장 handler | `OcrAnnotator.saveTemplateJson()` (line 134) |
| API endpoint | `POST /templates` (proxied via Next.js rewrites → `http://127.0.0.1:9099/templates`) |
| payload 주요 필드 | `templateName`, `file.name`, `image.{width,height,src}`, `regions[]` |
| documentType 포함 | **수정 전: 미포함** / 수정 후: 포함 (select UI에서 선택 시) |
| regions 포함 | ✅ (fieldType, x/y/width/height, table, colGuides 모두 포함) |
| table colGuides 포함 | ✅ (export.ts의 normalizeColGuides → colGuides + colX 모두 포함) |
| localStorage 사용 | ✅ (localStorage `mysuit_ocr_templates` — 항상 선행 저장) |
| backend API 사용 | ✅ (try/catch — 실패 시 "임시 저장소에 저장됨" 알림) |
| 저장 버튼 disabled 조건 | `!loaded` — PDF 로드 불가 시 버튼 비활성화됨 (수정 전 PDF 저장 불가 원인) |

## 5. backend 저장 API 경로

| 항목 | 결과 |
|------|------|
| save endpoint | `POST /templates` (main.py line 712) |
| load endpoint | `GET /templates` (main.py line 706) |
| save file path | `ocr-server/data/templates.json` (`DATA_DIR = os.path.dirname(__file__)/data`) |
| load file path | 동일: `ocr-server/data/templates.json` |
| T-10 script read path | `BACKEND_DIR / "data/templates.json"` = 동일 경로 ✅ |
| 경로 일치 여부 | **✅ 일치** (경로 불일치 문제 아님) |
| Next.js proxy 설정 | `.env.local`: `BACKEND_URL=http://127.0.0.1:9099` → `next.config.ts` rewrites `/templates` 정상 |

## 6. templates.json 경로 조사

| 경로 | 존재 | template count | 1.jpg TPL-31D13CF3 존재 | 2~7 존재 |
|------|------|:-:|------|------|
| `ocr-server/data/templates.json` | ✅ (1.3 MB) | 5 | ✅ (docType=invoice_statement, 9 regions, 1 table, 6 colGuides) | ❌ |
| `mysuit-ocr/public/data/templates.json` | ❌ 없음 | — | — | — |
| localStorage `mysuit_ocr_templates` | 브라우저 내부 | 알 수 없음 | 알 수 없음 | 알 수 없음 |
| backend save ↔ T-10 read 경로 | **동일** | — | — | — |

## 7. 원인 분석

| 문제 | 원인 | 수정 여부 |
|------|------|------|
| 2.pdf~7.pdf template 저장 불가 | OcrAnnotator `onPickFile`이 PDF를 `new Image()`로 로드 시도 → img.onerror → `loaded=null` → 저장 버튼 disabled | ✅ 수정: pdf.js로 PDF 렌더링 추가 |
| documentType 저장 누락 | `export.ts`의 `buildExportPayload()`에 documentType 파라미터 없음 | ✅ 수정: documentType 파라미터 + UI select 추가 |
| T-10/rerun 스크립트 BASE_URL 오류 | `BASE_URL = 8130` (backend 실제 포트: 9099) → OCR extract 호출 전부 실패 | ✅ 수정: 9099로 변경 |
| 저장 경로 불일치 | 없음 (save path = read path = T-10 script path 모두 동일) | 해당 없음 |
| Next.js proxy 설정 | `.env.local` BACKEND_URL=9099로 정상 설정됨 | 해당 없음 |

## 8. 저장 테스트 결과

5.pdf 최소 payload (documentType=invoice_statement, table region 포함, colGuides 6개)를 `POST /templates` API로 직접 호출하여 저장 테스트 수행.

| 테스트 | 결과 | 비고 |
|--------|------|------|
| save API 호출 | ✅ PASS | template_id=TPL-D0FA389E 자동 생성 |
| templates.json 반영 | ✅ PASS | file=5.pdf, docType=invoice_statement, tableRegions=1, colGuides=6 확인 |
| T-10 script 발견 | ✅ PASS | 시뮬레이션: 5.pdf → TPL-D0FA389E 발견 |
| RunOCR E2E 가능 | 미실행 | 테스트 template이므로 실제 좌표 아님. 실제 annotation 후 E2E 가능 |
| 테스트 template 삭제 | ✅ | DELETE /templates/TPL-D0FA389E로 정리 완료 |

## 9. 검증 결과

- **py_compile**: `verify_invoice_statement_template_runocr_e2e_t10_rerun.py` ✅ OK
- **py_compile**: `verify_invoice_statement_template_runocr_e2e_t10.py` ✅ OK
- **typecheck**: `npm run typecheck` → 오류 없음 ✅
- **build**: `npm run build` → `/template` 페이지 포함 전체 빌드 성공 ✅
- **T-10-rerun**: BASE_URL 수정 완료. 실제 annotation 저장 후 실행 권장.

## 10. 다음 작업 판단

**상태**: PDF 저장 플로우 정상화됨 + documentType 페이로드 수정 완료.

**다음 단계**:

1. **UI에서 2.pdf~7.pdf annotation 저장** (T-10-seed 대신 직접 UI 저장):
   - `http://localhost:8089/template` 접속
   - "템플릿 생성" 선택
   - 각 파일(2.pdf~7.pdf) 업로드 → pdf.js로 렌더링됨 (수정 후 작동)
   - 문서 유형 select에서 `invoice_statement` 선택
   - table region + colGuides 설정
   - "저장" 버튼 → `POST /templates` 호출 → templates.json 반영

2. **T-10-rerun 실행** (`python scripts/verify_invoice_statement_template_runocr_e2e_t10_rerun.py`):
   - BASE_URL=9099로 수정되어 OCR extract 호출 정상 작동 예상
   - 2.pdf~7.pdf template이 저장된 후 실행

**결론**: 저장 플로우 정상화됨 → UI에서 2~7.pdf annotation 저장 후 T-10-rerun
