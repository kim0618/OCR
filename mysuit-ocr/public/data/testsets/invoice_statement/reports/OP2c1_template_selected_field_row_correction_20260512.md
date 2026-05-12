# OP-2c-1 Template 정형 필드 출력 row 구조 보정 결과

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `src/components/ocr/OcrRightPanel.tsx` | enFieldRaw 초기화에 field.id 기본값 처리; 선택 영역 bold name/id 중복 제거; 정형/테이블 섹션에 삭제 버튼 통합 |

## 2. 백업 파일

| 백업 경로 | 원본 |
|---|---|
| `backup/OcrRightPanel_20260512_before_OP2c1.tsx` | src/components/ocr/OcrRightPanel.tsx |

## 3. 핵심 요약

- 정형 필드 선택 시 `enField`가 비어 있으면 `field.id`(e.g. `field_1`)가 영문 필드명 input의 기본값으로 표시됨
- 선택 영역에서 `{selected.name}` + `({selected.id})`를 굵게 크게 표시하던 헤더 제거
- "출력 필드 정의 (field_1)" 제목 + 우측 [삭제] 버튼 구조로 정리 (정형/테이블 모두)
- row 내부의 개별 삭제 버튼은 OP-2c부터 없었으므로 추가 변경 없음

## 4. field_1 기본값 처리

- **변경 전**: `setEnFieldRaw(selected.enField ?? "")` → enField가 없으면 placeholder만 보임
- **변경 후**: `setEnFieldRaw(selected.enField || selected.id || "")` → enField가 없으면 field.id가 input value로 표시
- **fallback 처리**: `selected.enField || selected.id || ""` 순서로 안전하게 처리
- **동작**: 사용자가 수정하면 `enFieldRaw` 갱신 → onBlur에서 `handleEnFieldBlur(id)` → region에 enField 저장

## 5. 선택 영역 UI 변경

- **field_1 중복 표시 제거**: 기존 `<b>{selected.name}</b> ({selected.id})` 헤더 블록 완전 제거
- **출력 필드 정의 row 반영**: 섹션 제목 옆에 `(field_1)` 형태로 작게 ID만 표시 (`opacity: 0.6`)
- **삭제 버튼 위치**: 섹션 제목 우측 끝에 [삭제] 버튼 배치. `deleteRegion(selected.id)` 기존 로직 사용
- **테이블 섹션**: 동일하게 `테이블필드 (table_1)` + [삭제] 버튼 구조 적용
- **미리보기 영향**: 없음. 미리보기 블록 위치/동작 유지

## 6. 삭제 버튼 정리

- **정형 field 삭제**: "출력 필드 정의 (field_1)" 제목 우측 [삭제] 버튼 → `deleteRegion(selected.id)`
- **테이블 field 삭제**: "테이블필드 (table_1)" 제목 우측 [삭제] 버튼 → `deleteRegion(selected.id)`
- **row 내부 삭제 버튼**: OP-2c에서 이미 없음. 추가 변경 없음
- **비정형 영향**: 없음. UnstructuredBuilder 미변경

## 7. 저장 구조 영향

- **enField**: `field.id` 기본값으로 초기화되어 사용자가 수정 전까지 `field.id`가 보임. onBlur에서 저장되므로 저장 구조 변경 없음
- **koField**: 변경 없음
- **canonicalField**: 변경 없음. koField 입력 → 자동 매핑 기능 동일
- **mappingStatus**: 변경 없음
- **기존 id 유지**: field_1, multi_1, check_1, table_1 변경 없음

## 8. 검증 결과

- **typecheck**: PASS (tsc --noEmit 오류 없음)
- **build**: PASS (✓ Compiled successfully in ~1.7s, 20/20 pages)
- **브라우저 확인**: 빌드 성공. dev server 재기동 후 확인 권장

## 9. 남은 문제

- enField onBlur 저장이므로, input에서 포커스를 잃지 않고 저장 버튼을 누르면 enField가 저장에 포함되지 않을 수 있음 — 향후 onSave 시 현재 enFieldRaw도 저장하는 방향 고려 가능
- RunOCR canonicalField 기반 output mapping 미반영 (→ OP-3)

## 10. 다음 추천 작업

- **OP-3**: RunOCR canonicalField 기반 output mapping (Template canonical 구조 완성, RunOCR 연결 필요)
- Template-Table-1: 테이블필드 canonicalColumn 기반 tableRows 매핑
- T-4: Test UI tableRows/tableMeta 연동
