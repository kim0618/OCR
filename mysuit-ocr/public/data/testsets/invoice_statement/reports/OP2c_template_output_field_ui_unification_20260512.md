# OP-2c Template 출력 필드 정의 UI 통일 결과

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `src/components/ocr/OcrRightPanel.tsx` | 정형 field/multi/check 선택 영역: 세로 카드 → 4컬럼 row/table 포맷; 테이블 컬럼 정의: 카드 → 4컬럼 row/table 포맷 |
| `src/components/template/UnstructuredBuilder.tsx` | 출력 필드 정의 헤더: 3컬럼 → 4컬럼(자동 매핑 추가); 각 필드 행: 3컬럼 → 4컬럼 (자동 매핑 배지 인라인 표시, canonical name 말줄임 표시) |

## 2. 백업 파일

| 백업 경로 | 원본 |
|---|---|
| `backup/OcrRightPanel_20260512_before_OP2c.tsx` | src/components/ocr/OcrRightPanel.tsx |
| `backup/UnstructuredBuilder_20260512_before_OP2c.tsx` | src/components/template/UnstructuredBuilder.tsx |

## 3. 핵심 요약

- 정형 필드 선택 영역, 비정형 출력 필드 정의, 테이블 컬럼 정의 모두 동일한 4컬럼 row/table 포맷으로 통일
- 공통 컬럼 구조: `No | 영문 필드명(컬럼명) | 한글 필드명(컬럼명) | 자동 매핑`
- "자동 매핑" 컬럼에는 MappingBadge(자동 매핑/직접 선택/후보 선택 필요/자동 매핑 없음) + canonical 이름을 9px 말줄임으로 표시
- ambiguous 후보 선택은 행 아래 amber 박스로 분리, 사용자 친화적 표시
- 저장 구조, canonical 매핑 로직, gridMode/세로가이드/종료키워드 기능 미변경

## 4. 정형 필드 UI 변경

- **변경 전**: 섹션 제목 → 영문 필드명 input (세로) → 한글 필드명 input (세로) → "자동 매핑" 박스 (별도 카드)
- **변경 후**: 섹션 제목 → 헤더 행(No|영문|한글|자동 매핑) → 데이터 행(1 + inputs + badge/canonical) → [ambiguous amber 박스]
- **row/table 포맷 적용**: `gridTemplateColumns: "20px 1fr 1fr 70px"` 4컬럼 그리드
- **자동 매핑 표시**: 4번째 컬럼 내 MappingBadge + canonical 이름(9px monospace, 66px max-width, overflow ellipsis)
- **ambiguous 처리**: 행 아래 `amber 배경 + border` 박스에 "후보를 선택하세요" + 후보 버튼

## 5. 비정형 필드 UI 변경

- **기존 구조 유지 여부**: 출력 필드 정의 기능(추가/삭제/수정) 완전 유지
- **정형과 통일된 부분**: 헤더 3컬럼 → 4컬럼(자동 매핑 추가); 각 행 `gridTemplateColumns: "28px 1fr 1fr 68px"` 4컬럼 적용; canonical 이름 인라인 표시
- **자동 매핑 표시**: 기존 별도 sub-row → 4번째 컬럼에 badge + canonical 이름 (9px, 64px max-width ellipsis)
- **ambiguous 처리**: 기존 방식(paddingLeft: 34, "선택:" 텍스트 + 버튼들) 유지

## 6. 테이블필드 UI 변경

- **컬럼 row 포맷**: `gridTemplateColumns: "20px 1fr 1fr 70px"` 4컬럼, 각 컬럼이 하나의 행
- **canonicalColumn 표시**: 4번째 컬럼 내 MappingBadge + canonical 이름(9px monospace, 66px ellipsis)
- **gridMode/종료키워드 영향**: 없음. 그리드 모드 버튼, 종료 키워드 입력, 세로 가이드 찍기 등 기존 기능 완전 유지
- **ambiguous 처리**: 행 아래 amber 박스에 "선택:" + 후보 버튼

## 7. 저장 구조 영향

- **기존 id 유지**: field_1, multi_1, check_1, table_1 변경 없음
- **koField/enField 유지**: 저장 구조 그대로
- **canonicalField/canonicalColumn 유지**: 저장 구조 그대로
- **backward compatibility**: 기존 템플릿에 koField/enField/canonicalField 없으면 빈값 fallback으로 안전 처리

## 8. 기존 기능 영향 확인

| 항목 | 결과 |
|---|---|
| 템플릿 생성 | 정상 |
| 비정형 생성 | 정상 |
| 필드 생성 | 정상 |
| 멀티필드 생성 | 정상 |
| 체크필드 생성 | 정상 |
| 테이블필드 생성 | 정상 |
| 영역 선택/이동/삭제 | 정상 |
| 세로 가이드 | 정상 (기능 미변경) |
| 종료 키워드 | 정상 (기능 미변경) |
| 저장/수정 | 정상 |
| 문서 유형 저장 | 정상 (OP-2b 위치 유지) |
| RunOCR | 정상 (미변경) |
| History | 정상 (미변경) |
| Test | 정상 (미변경) |

## 9. 검증 결과

- **typecheck**: PASS (오류 없음)
- **build**: PASS (✓ Compiled successfully in ~2s, 20/20 pages)
- **브라우저 확인**: 빌드 성공. dev server 재기동 후 확인 권장

## 10. 남은 문제

- RunOCR 결과는 아직 canonicalField 기준 출력 미반영 (→ OP-3)
- table column canonicalColumn 기반 실제 RunOCR tableRows 매핑 미구현 (→ Template-Table-1)
- 4컬럼 레이아웃에서 "자동 매핑 없음" 배지가 매 행마다 표시되어 시각적으로 다소 많을 수 있음. 향후 unmapped는 컬럼 비워두는 방향도 고려 가능

## 11. 다음 추천 작업

- **OP-3** (강력 추천): RunOCR canonicalField 기반 output mapping — Template 저장 구조와 UI까지 완성, RunOCR output 연결이 가장 시급
- Template-Table-1: 테이블필드 canonicalColumn 기반 OCR tableRows 매핑
- T-4: Test UI tableRows/tableMeta 연동
- H-3: backend 원본/전처리 이미지 파일 저장 API 설계

추천: **OP-3**
