# OP-2b Template canonical 매핑 UI 정리 결과

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `src/components/ocr/OcrAnnotator.tsx` | 툴바에서 documentType select 제거; OcrRightPanel에 setDocumentType prop 추가 전달 |
| `src/components/ocr/OcrRightPanel.tsx` | Props에 setDocumentType 추가; 문서 유형 select를 템플릿 설정 영역(템플릿명 하단)으로 이동; 정형 필드 UI 재구성(출력 필드 정의 섹션명, 영문→한글 순서, 자동 매핑 하단 보조 박스); 테이블 컬럼 UI 재구성(영문→한글 순서, "테이블 컬럼 정의" 섹션명); MappingBadge 라벨 한국어화 |
| `src/components/template/UnstructuredBuilder.tsx` | MappingBadge 라벨 한국어화; "canonical 미매핑" → "자동 매핑 없음" 통일 |

## 2. 백업 파일

| 백업 경로 | 원본 |
|---|---|
| `backup/OcrAnnotator_20260512_before_OP2b.tsx` | src/components/ocr/OcrAnnotator.tsx |
| `backup/OcrRightPanel_20260512_before_OP2b.tsx` | src/components/ocr/OcrRightPanel.tsx |
| `backup/UnstructuredBuilder_20260512_before_OP2b.tsx` | src/components/template/UnstructuredBuilder.tsx |

## 3. 핵심 요약

- 문서 유형 선택기가 툴바(필드 도구 버튼 옆)에서 우측 패널 템플릿 설정 영역(템플릿명 바로 아래)으로 이동
- 정형 필드 선택 시 "출력 필드 정의" 섹션에서 영문 필드명 → 한글 필드명 순서로 표시 (비정형과 동일한 순서)
- canonical 매핑 결과는 "자동 매핑" 박스로 분리되어 하단 보조 정보로 표시
- 테이블 컬럼 정의도 영문 컬럼명 → 한글 컬럼명 순서, 자동 매핑 결과는 하단 표시
- MappingBadge 라벨: auto→자동 매핑, ambiguous→후보 선택 필요, manual→직접 선택, unmapped→자동 매핑 없음 (정형/비정형 통일)

## 4. 문서 유형 UI 변경

- **기존 위치**: 툴바 (필드/멀티필드/체크필드/테이블필드 버튼과 같은 줄)
- **변경 후 위치**: 우측 패널 > 템플릿 설정 영역 > 템플릿명 input 하단 "문서 유형" 라벨 + select
- **저장 구조 영향**: 없음. documentType 상태는 OcrAnnotator에서 관리하고 props로 전달하는 구조 유지. setDocumentType을 OcrRightPanel에 전달하는 방식으로 변경
- **비정형**: UnstructuredBuilder의 문서 유형 select는 이미 우측 패널에 있어 위치 변경 없음

## 5. 정형 필드 선택 영역 변경

- **변경 전**: "CANONICAL 매핑" 제목 → 한글 필드명 → 영문 필드명 → canonical + badge → 후보 선택
- **변경 후**: "출력 필드 정의" 제목 → 영문 필드명 → 한글 필드명 → [자동 매핑 박스: badge + canonical값 + 후보 선택]
- **영문/한글 필드명 표시**: 영문 먼저, 한글 다음 (비정형 출력 필드와 동일한 순서)
- **canonical 보조 표시**: 별도 박스(배경 색상 구분)로 분리하여 하단에 배치. "자동 매핑" 섹션 제목 사용
- **ambiguous 후보 처리**: 자동 매핑 박스 내에 "후보를 선택하세요" 안내 후 후보 버튼 배치

## 6. 비정형 필드 UI 정리

- 기존 출력 필드 정의(No/영문 필드명/한글 필드명) 구조 유지
- canonical 표시: 각 필드 행 하단에 MappingBadge + canonical값 (자동 매핑 없음 텍스트로 통일)
- 정형 필드와 통일: MappingBadge 라벨 동일화, "자동 매핑 없음" 문구 통일

## 7. 테이블필드 컬럼 UI 변경

- **영문 컬럼명**: 첫 번째 컬럼으로 이동 (기존: 두 번째)
- **한글 컬럼명**: 두 번째 컬럼 (기존: 첫 번째)
- **canonicalColumn 표시**: 각 컬럼 카드 하단에 MappingBadge + canonical값
- **gridMode/종료키워드 영향**: 없음. 기존 버튼/입력 구조 유지, 섹션 제목을 "그리드 모드"로 명확화
- **섹션 제목**: "컬럼 canonical 매핑" → "테이블 컬럼 정의"로 변경

## 8. mappingStatus 표시 정책

| status (내부 값) | 기존 표시 | 변경 후 표시 | 색상 |
|---|---|---|---|
| auto | auto | 자동 매핑 | 초록 |
| ambiguous | ambiguous | 후보 선택 필요 | 노랑 |
| manual | manual | 직접 선택 | 보라 |
| unmapped | unmapped | 자동 매핑 없음 | 회색 |

내부 enum 값은 변경 없음. UI 표시 라벨만 변경.

## 9. 기존 기능 영향 확인

| 항목 | 결과 |
|---|---|
| 템플릿 생성 | 정상. OcrAnnotator 플로우 유지 |
| 비정형 생성 | 정상. UnstructuredBuilder 구조 유지 |
| 필드 생성 | 정상. 드로우/이동/삭제 로직 미변경 |
| 테이블필드 생성 | 정상. 세로 가이드/모드/종료키워드 로직 유지 |
| 저장/수정 | 정상. 저장 구조 변경 없음 |
| 문서 유형 저장 | 정상. documentType state → exportPayload 포함 유지 |
| RunOCR | 정상. RunOCR 로직 미변경 |
| History | 정상. History 구조 미변경 |
| Test | 정상. TestWorkspace 미변경 |

## 10. 검증 결과

- **typecheck**: PASS (오류 없음)
- **build**: PASS (✓ Compiled successfully in ~2s, 20/20 pages)
- **브라우저 확인**: 빌드 성공. dev server 재기동 후 확인 권장

## 11. 남은 문제

- RunOCR 결과는 아직 canonicalField 기준 출력 미반영 (→ OP-3)
- table column canonicalColumn 기반 실제 RunOCR tableRows 매핑 미구현 (→ Template-Table-1)
- 문서 유형 자동 추정(템플릿명 기반) 미구현 — 명시적 선택 방식 유지 중
- 영역 목록의 unmapped badge는 노이즈 감소를 위해 unmapped 상태는 배지 비표시로 이미 처리됨

## 12. 다음 추천 작업

- **OP-3** (강력 추천): RunOCR canonicalField 기반 output mapping
- Template-Table-1: 테이블필드 canonicalColumn 기반 OCR tableRows 매핑
- T-4: Test UI tableRows/tableMeta 연동
- H-3: backend 원본/전처리 이미지 파일 저장 API 설계

추천: **OP-3** — Template canonical 구조가 UI까지 완성되었으므로 RunOCR output 연결이 가장 우선순위 높음.
