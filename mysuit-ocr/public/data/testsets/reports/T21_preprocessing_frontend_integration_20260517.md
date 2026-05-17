# T-21 RunOCR 자동 preprocessing 적용 흐름 + TestWorkspace debug 표시 결과

## 1. 수정 파일
- `mysuit-ocr/src/components/test/core/types.ts` — `PreprocessingDebug` 타입 추가, `OcrResponse`/`OcrEntry` 확장
- `mysuit-ocr/src/components/test/TestWorkspace.tsx` — `fetchOcr` 옵션 파라미터, 전처리 검증 체크박스, `PreprocessingDebugPanel` 컴포넌트

## 2. 백업 파일
- `mysuit-ocr/backup/TestWorkspace_20260517_before_T21_preprocessing_ui.tsx`
- `mysuit-ocr/backup/types_test_core_20260517_before_T21_preprocessing_ui.ts`

## 3. 핵심 요약
- TestWorkspace: "전처리 Debug" / "자동 보정" 체크박스 추가 (기본값 false)
- fetchOcr: debugPreprocessing / autoApplyPreprocessing / qualityTagsJson 전달
- PreprocessingDebugPanel: 적용됨 / 후보 있음 / 표 문서 제외 / 오류 상태 표시
- RunOCR (UploadWorkspace): **선택 A** — autoApplyPreprocessing 미전달, 추후 Phase 3 연결
- 백엔드 OCR 로직 및 기본 결과 변경 없음 (T-20i verify PASS 유지)

## 4. API 파라미터 연결
| 화면 | debugPreprocessing | autoApplyPreprocessing | qualityTagsJson | 비고 |
|---|---|---|---|---|
| TestWorkspace RunOne | 체크박스 값 | 체크박스 값 | manifest qualityTags | 검증 전용 옵션 |
| TestWorkspace RunAll | 체크박스 값 | 체크박스 값 | manifest qualityTags | 검증 전용 옵션 |
| UploadWorkspace RunOCR | 미전달 (false) | 미전달 (false) | 미전달 | 선택 A: 기존 동일 |

## 5. TestWorkspace 변경
- **옵션**: Run OCR / Run All 버튼 오른쪽에 "전처리 Debug" + "자동 보정" 체크박스
- **기본값**: 둘 다 false (기존 동작 완전 동일)
- **전처리 Debug ON**: backend에 debugPreprocessing=true 전달 → preprocessingDebug 응답 → 패널 표시
- **자동 보정 ON**: autoApplyPreprocessing=true 전달 → receipt+guard 통과 시 productionApplied=true

## 6. RunOCR 변경
- **사용자 옵션 노출**: 없음 (복잡한 variant 선택 비노출)
- **자동 판단 방식**: 선택 A — 현재는 autoApplyPreprocessing 미전달
- **적용 이유**: T-20i까지 TestWorkspace 검증만 완료. RunOCR은 충분한 실사용 검증 후 Phase 3 연결 권장
- **추후 연결**: UploadWorkspace.tsx FormData에 receipt + preprocessing_candidate 시 내부 전달 가능

## 7. preprocessingDebug 표시
| 상태 | 표시 문구 | 아이콘 |
|---|---|---|
| productionApplied=true | 보정 OCR 적용됨 (적용 variant) | ✓ 초록 |
| candidate 있음, 미적용 | 전처리 후보 있음 — 현재 원본 OCR 유지 | ◌ 노랑 |
| invoice_excluded | 표 문서 — 자동 보정 제외 | — 회색 |
| 오류 | 전처리 오류 (오류 메시지) | 빨강 |
| 후보 없음 | (패널 미표시) | — |

## 8. invoice_statement 정책 표시
- `autoApplyDecision.reason = ["invoice_excluded_from_auto_apply"]` → 별도 문구 표시
- "거래명세서 표 문서는 행 수 안정성을 우선하여 자동 전처리 적용 대상에서 제외됩니다."
- 기존 rowCount exact 표시와 독립 (DocumentDetailPanel 충돌 없음)

## 9. 검증 결과
- backend verify (T-20i): PASS 11/11 assertions
- typecheck: PASS
- build: PASS
- 기존 RunOne/RunAll (옵션 off): 기존 동작 유지 (옵션 default false)

## 10. 다음 작업 판단
- **T-21 완료**: TestWorkspace 전처리 UI 연결 1차 마감
- **RunOCR 자동 적용**: Phase 3 연결은 보류 (선택 A)
  - 충분한 TestWorkspace 검증 후 UploadWorkspace에 내부 전달 구조 추가
- **추가 검토 가능**: "자동 보정 적용됨" 배지를 RunOCR 결과 패널에도 표시
