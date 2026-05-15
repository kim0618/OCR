# T-10-save-debug-fix Template 저장 대상 서버/경로 보정 결과

작성일: 2026-05-15

## 1. 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `mysuit-ocr/src/components/ocr/OcrAnnotator.tsx` | PDF 렌더링 DPI 수정: `scale=1800/width` → `scale=200/72` (backend PyMuPDF 200 DPI와 좌표계 일치) |

## 2. 백업 파일

| 파일 |
|------|
| `mysuit-ocr/backup/OcrAnnotator_20260515_before_T10_save_debug_fix.tsx` |

## 3. 핵심 요약

**추가로 발견된 문제**: OcrAnnotator PDF 렌더링 DPI와 backend PDF 렌더링 DPI 불일치.

- Frontend(T-10-save-debug에서 수정된 코드): `scale = 1800 / baseViewport.width`
  - 5.pdf (595pt width): scale≈3.025 → 렌더링 1800×1271px
- Backend(PyMuPDF): `pix = page.get_pixmap(dpi=200)` → 200/72 = 2.778 scale
  - 5.pdf: 1654×1169px

**좌표계 불일치 폭**: 1800 vs 1654 (x: ~9% 차이), 1271 vs 1169 (y: ~9% 차이)

이 불일치가 있으면, UI에서 사용자가 annotation한 template 좌표가 backend OCR 좌표계와 맞지 않아 table extraction이 실패함.

**수정**: `scale = 200 / 72` (2.778)로 변경 → frontend와 backend 동일 DPI → 좌표계 일치.

## 4. frontend 저장 요청 경로

| 항목 | 결과 |
|------|------|
| 저장 함수 | `OcrAnnotator.saveTemplateJson()` |
| API endpoint | `POST /templates` (상대경로 → Next.js rewrite) |
| baseURL | `.env.local`: `BACKEND_URL=http://127.0.0.1:9099` |
| expected 9099 여부 | ✅ 일치 (`next.config.ts` rewrites `/templates` → `${BACKEND_URL}/templates`) |
| 실제 호출 URL | `http://127.0.0.1:9099/templates` |
| proxy 연결 테스트 | ✅ `8089/templates → 9099/templates` POST 성공 확인 |

## 5. 저장 payload 확인

| 필드 | 존재 여부 | 비고 |
|------|-----------|------|
| documentType | ✅ T-10-save-debug에서 수정 완료 | select UI에서 선택 시 포함 |
| file.name (fileName) | ✅ | 실제 파일명 저장 (예: "5.pdf") |
| regions | ✅ | 전체 region 배열 포함 |
| table region (fieldType=table) | ✅ | colGuides + colX 포함 |
| colGuides | ✅ (region.table.colGuides) | normalized 0-1 ratios |
| colX | ✅ (region.table.colX) | absolute pixel positions (backend에서 사용) |
| image.width/height | ✅ | PDF 렌더링 크기 (수정 후: 1654×1169 for 5.pdf) |

## 6. backend 저장 API 확인

| 항목 | 결과 |
|------|------|
| save endpoint | `POST /templates` (main.py line 712) |
| save file path | `ocr-server/data/templates.json` |
| load file path | 동일 |
| T-10 script read path | `BACKEND_DIR / "data/templates.json"` ✅ 동일 |
| 경로 일치 여부 | **✅ 완전 일치** |

## 7. templates.json 경로 조사

| 경로 | 존재 | template count | 새 record (5.pdf) |
|------|------|:-:|---|
| `ocr-server/data/templates.json` | ✅ | 7 | ✅ TPL-A6B12CED |
| `mysuit-ocr/public/data/templates.json` | ❌ | — | — |

## 8. 원인

| 문제 | 원인 | 수정 여부 |
|------|------|------|
| PDF 렌더링 DPI 불일치 | Frontend: 1800/baseWidth scale. Backend: 200 DPI (200/72=2.778). 동일 PDF를 다른 해상도로 렌더링 → 좌표계 불일치 | ✅ 수정 (200/72) |
| 저장 경로 불일치 | 없음 - 동일 경로 확인 | 해당 없음 |
| Proxy 불일치 | 없음 - 8089→9099 정상 | 해당 없음 |
| documentType 누락 | T-10-save-debug에서 이미 수정 | ✅ (이전 작업) |

**주요 원인**: PDF 렌더링 DPI 불일치. 사용자가 UI에서 annotation한 좌표가 frontend 1800px 기준이지만, backend는 200 DPI(≈1654px) 기준으로 OCR. 좌표가 9% 오프셋으로 맞지 않아 table extraction 실패.

## 9. 수정 결과

- OcrAnnotator PDF rendering: `scale = 200 / 72` → 5.pdf = 1654×1169px, 2.pdf = 1654×2338px
- Backend PDF rendering: `dpi=200` → 동일한 1654×1169px, 1654×2338px
- **좌표계 완전 일치** ✅

## 10. 저장 테스트 결과

| 샘플 | 저장 방식 | templates.json 반영 | T-10 발견 | E2E rowCount |
|------|-----------|---------------------|-----------|--------------|
| 5.pdf | API (line-detection coords) | ✅ TPL-A6B12CED | ✅ 실행가능 | 9/6 (summary 행 포함, 좌표 정밀화 필요) |
| 2.pdf | API (line-detection coords) | ✅ TPL-A4585BC7 | ✅ 실행가능 | T-10 실행됨 (rowCount 별도 확인) |
| 1.jpg | 기존 | ✅ TPL-31D13CF3 | ✅ 실행가능 | 28/28 exact ✅ |

### 5.pdf rowCount 9/6 원인
- 라인 감지로 추출한 좌표(y=39~882)가 summary 행을 포함
- row 7-9: 빈 행 + 합계금액 행 → 실제 item 행은 6개 맞음
- 정밀한 UI annotation (stopKeywords 설정 포함)으로 해결 가능

## 11. 검증 결과

- **typecheck**: `npm run typecheck` → **PASS** ✅
- **T-10 after save-debug**: apiExecuted=3, rowCountExactAmongExecuted=1/3, missingSavedAnnotations=4 (3.pdf/4.pdf/6.pdf/7.pdf)
- **proxy test**: `8089/templates` → `9099` POST 성공 ✅
- **backend connectivity**: `9099/health → {"status":"ok"}` ✅

## 12. 다음 작업 판단

**저장 경로 정상화됨 → UI에서 2~7.pdf annotation 저장 후 T-10-rerun**

단, UI annotation 시 다음 사항 확인 필요:
1. **dev server 재시작**: `npm run dev` → DPI 수정이 반영된 버전 실행
2. **PDF 업로드 후 table region + colGuides 정밀하게 설정**
3. **stopKeywords 설정**: summary 행 제외를 위한 키워드 (예: "합계", "소계")
4. **문서 유형 select**: `invoice_statement` 선택

**즉각 실행 가능한 다음 단계**:
- 3.pdf, 4.pdf, 6.pdf, 7.pdf는 T-10 기대 rowCount 1로 단순 → UI 정밀 annotation 후 저장하면 바로 E2E 가능
- 5.pdf, 2.pdf는 복잡한 레이아웃으로 정밀 annotation 후 E2E 재확인 필요
