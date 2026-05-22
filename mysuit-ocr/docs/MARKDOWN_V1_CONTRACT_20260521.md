# MARKDOWN V1 CONTRACT 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_2A_MARKDOWN_CONTRACT_FIXTURE_LOCK_NO_PROD_MODIFY`

## 2. 운영 코드 수정 없음
- 운영 코드 수정 없음.
- `fieldsToMarkdown` 또는 Markdown helper 분리는 하지 않았다.
- 현재 `OcrResultPanel.tsx`의 `toMarkdown` 동작을 문서화한다.

## 3. 현재 함수
- 함수명: `toMarkdown`
- 위치: `src/components/upload/OcrResultPanel.tsx around line 707`
- Copy/Export: Markdown preview mode에서 `toMarkdown()` 문자열을 사용한다.

## 4. 입력 Contract
- `result.processing_time`
- `editedFields`
- table field일 때 `docTableRows` row count summary
- `fieldLabelFull`
- `parseTableField`
- `getAdoptionLabel`

## 5. 출력 Contract
- Markdown string
- 첫 줄은 `# OCR 결과`
- 처리 시간 bullet 포함
- 필드 수 bullet 포함
- Markdown table header 포함
- `editedFields` 순서대로 한 줄씩 출력
- field label/value는 pipe와 newline을 escape한다.

## 6. Table / rowIndex Contract
- Markdown v1은 구조화 tableRows 상세 rows/columns를 펼치지 않는다.
- table field는 `표 데이터(N행)` 형태의 요약만 출력한다.
- 따라서 거래명세서 rowIndex 포함/제외 정책은 Markdown 문자열에 직접 드러나지 않는다.
- rowIndex 정책 검증은 Preview/Clean JSON fixture가 담당하고, Markdown fixture는 현재 요약 문자열을 고정한다.

## 7. 제외 항목
- bbox/sourceBboxes
- raw OCR/debug
- document_fields.tableRows 상세
- docTableDisplayCols
- Raw JSON/Clean JSON payload

## 8. Helper 분리 계획
- 후보 파일: `src/lib/markdownReportBuilder.ts`
- 추천 helper: `fieldsToMarkdown`
- 입력: `processingTime`, `fields`, `docTableRows`
- 출력: `string`
- 순수성: React hook/DOM/window/localStorage/network 금지, 입력 mutation 금지.

## 9. Before / After 검증 기준
- `tmp/fixtures/markdown_v1/*.md`와 exact string equality
- line ending은 LF 기준
- Copy/Export 동작 변경 없음
- Clean JSON/Raw JSON 영향 없음
- typecheck/build PASS
