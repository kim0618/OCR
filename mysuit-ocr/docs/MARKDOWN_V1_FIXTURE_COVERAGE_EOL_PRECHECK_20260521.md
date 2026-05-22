# MARKDOWN V1 FIXTURE COVERAGE / EOL PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_2A_MARKDOWN_FIXTURE_COVERAGE_EOL_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `OcrResultPanel.tsx` 수정 없음.
- helper 추출 없음.
- `.gitattributes` 수정 없음.
- 생성/갱신 범위는 tmp 검증 스크립트, docs 리포트, Markdown v1 fixture 보강 및 manifest 보강이다.

## 3. LF/CRLF 검증 결과
| path | bytes | lines | ending | endsWithNewline | trailingWhitespaceLines | status |
| --- | ---: | ---: | --- | --- | ---: | --- |
| tmp\fixtures\markdown_v1\invoice_statement\trade_1_1jpg.md | 922 | 17 | LF | True | 0 | PASS |
| tmp\fixtures\markdown_v1\invoice_statement\trade_2_2pdf.md | 875 | 16 | LF | True | 0 | PASS |
| tmp\fixtures\markdown_v1\invoice_statement\trade_3_3pdf.md | 942 | 17 | LF | True | 0 | PASS |
| tmp\fixtures\markdown_v1\invoice_statement\trade_7_7pdf.md | 1011 | 17 | LF | True | 0 | PASS |
| tmp\fixtures\markdown_v1\receipt\tpl_003_1jpg.md | 471 | 13 | LF | True | 0 | PASS |
| tmp\fixtures\markdown_v1\receipt\tpl_003_2jpg.md | 470 | 13 | LF | True | 0 | PASS |

판정: `PASS`

## 4. Fixture Comparison Policy 제안
- Markdown fixture는 LF 기준으로 고정한다.
- FRONTEND-CLEANUP-2B helper 출력도 `\n` 기반 문자열을 생성해야 한다.
- 기본 비교는 exact string equality를 권장한다.
- Windows CRLF 우발 변환을 조기에 잡기 위해 runner는 line ending 정책을 명시적으로 출력해야 한다.
- trailing whitespace도 현재 fixture 기준으로 exact 비교한다.

## 5. Coverage 평가
- 기존 5개 fixture는 large table summary, rowIndex 유지/제외 대표, field-only receipt를 커버한다.
- Markdown v1은 tableRows를 펼치지 않으므로 거래_4~6은 문자열 패턴상 대부분 중복이다.
- 거래_7은 단일 row table summary + rowIndex 제외 케이스라 edge coverage 가치가 있어 추가했다.
- trade_7 추가 결과: `PASS` / action: `kept_existing_locked`

## 6. toMarkdown Closure Dependency
| dependency | usedFor | required helper input/handling | risk |
| --- | --- | --- | --- |
| result.processing_time | processing time summary | processingTime: number | LOW |
| editedFields | field rows and field count | fields: OcrFieldResult[] | LOW |
| fieldLabelFull | label formatting | helper can import resolveFieldLabel or receive labelResolver | MEDIUM |
| parseTableField | legacy table rowLabel fallback | move local helper with markdown builder | LOW |
| docTableRows | table summary N행 override | docTableRows?: Record<string, unknown>[] \| null | MEDIUM |
| getAdoptionLabel | 채택 column | move helper or expose adoption label function | LOW |
| docTableDisplayCols | not used by Markdown v1 | not required | LOW |
| tableMeta/documentFields | not directly used except docTableRows | not required if docTableRows passed | LOW |
| fileName/templateName/docType | not used by Markdown v1 | not required for v1 exact output | LOW |
| React state/hooks/DOM/window | not used inside toMarkdown body | must remain absent | LOW |

## 7. Helper 입력 Contract 제안
- `fields: OcrFieldResult[]`
- `processingTime: number`
- `docTableRows?: Record<string, unknown>[] | null`
- label/adoption/table parse helper는 helper 파일 내부 순수 함수로 이동하거나 명시 의존성으로 둔다.
- `docTableDisplayCols`, `tableMeta`, `templateName`, `fileName`, `docType`은 Markdown v1 exact output에는 필요하지 않다.

## 8. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | ---: | ---: |
| npm run typecheck | PASS | 0 | 1.914 |
| npm run build | PASS | 0 | 18.634 |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` observed = `True`

## 9. 다음 작업 제안
1. FRONTEND-CLEANUP-2B에서 `toMarkdown`을 순수 helper로 추출한다.
2. 이번 6개 Markdown fixture와 exact string equality를 수행한다.
3. Clean JSON fixture runner와 함께 typecheck/build를 회귀 검증에 포함한다.
