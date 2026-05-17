# T-20-final OCR preprocessing 시리즈 최종 요약

## 1. 전체 결론
- 전처리 전체 기본 적용은 위험하다.
- `qualityTags` 기반 조건부 적용이 맞다.
- `debugPreprocessing` 구조는 완료됐다.
- receipt limited auto-apply 옵션 구현은 완료됐다.
- `invoice_statement`는 auto-apply 영구 제외 대상이다.
- 기본값은 `autoApplyPreprocessing=false`로 유지한다.

## 2. T-20 실험 결과
- 대상: 10개 샘플
- OCR variant: 72건
- 결과: improved 5 / unchanged 4 / regressed 1
- 주요 효과 variant:
  - `clahe`
  - `upscale_1_5x`
  - `grayscale`
  - `render_dpi_200_grayscale`
- threshold 계열은 기본 적용 금지로 판단했다.

## 3. T-20a policy/guard 설계
- `qualityTags` 기반 조건부 policy를 설계했다.
- `compare_then_select` 원칙을 확정했다.
- receipt guard를 정의했다.
- invoice rowCount guard를 정의했다.
- `invoice/2.pdf`는 blocked로 분류했다.
- `invoice/3.pdf`는 candidate로 분리했다.

## 4. T-20c qualityTags 보강
- `invoice/3.pdf`: `pdf_low_resolution`, `preprocessing_candidate`, `rowcount_guard_required`
- `invoice/2.pdf`: `dense_table`, `rowcount_guard_required`, `preprocessing_blocked`
- `pos_006`: `garbled_source`, `preprocessing_candidate`
- `card_001` / `pos_001`: `garbled_source`
- `conditional_accept`는 4건에서 5건으로 증가했다.

## 5. T-20b compare_then_select
- `preprocessing_policy.py`를 신규 추가했다.
- `get_candidates()`를 구현했다.
- `apply_receipt_guard()`를 구현했다.
- `apply_invoice_guard()`를 구현했다.
- `compare_then_select()`를 구현했다.
- 검증 결과: 9/9 PASS
- `productionApplied=false`를 유지했다.

## 6. T-20d live debug 연결
- `main.py`에 `debugPreprocessing` flag를 추가했다.
- `preprocessingDebug` 블록을 추가했다.
- `debug=false` 기존 응답 동일성을 유지했다.
- `debug=true`에서 candidate 비교가 가능해졌다.
- `productionApplied=false`를 유지했다.

## 7. T-20e API validation
- 실제 `/ocr/extract` 기준 `debug=false` vs `debug=true` 동일성 검증을 PASS했다.
- `card_002` / `medical_001` / `pos_006` / `medical_003` / `invoice3` candidate를 확인했다.
- `invoice2` blocked를 확인했다.
- auto-apply는 이 단계에서 보류 판단했다.

## 8. T-20f 정상군 회귀 검증
- 총 15개 샘플을 검증했다.
- 정상 receipt 회귀는 0건이었다.
- 정상군 `candidate_accept` 2건을 발견했다.
  - `card_001`
  - `pos_005`
- `preprocessing_candidate` 태그 필수 guard가 필요하다고 판단했다.

## 9. T-20g auto-apply guard 설계
- `decide_auto_apply_preprocessing()`를 추가했다.
- `invoice_statement`는 영구 제외했다.
- `preprocessing_candidate` 태그를 필수 조건으로 지정했다.
- `preprocessing_blocked`는 차단한다.
- 핵심 필드 손실은 차단한다.
- improvement delta > 0을 필수 조건으로 지정했다.
- false positive 금액은 차단한다.
- docType 악화는 차단한다.

## 10. T-20h preprocessing_candidate 태그 보강
- `card_002`, `medical_001`, `medical_003`에 `preprocessing_candidate`를 추가했다.
- `pos_006` 포함 autoApplyAllowed 4건을 확인했다.
- `card_001` / `pos_005` 차단을 유지했다.
- `invoice_statement` auto-apply 허용은 0건으로 유지했다.

## 11. T-20i limited auto-apply 옵션 구현
- `main.py`에 `autoApplyPreprocessing` flag를 추가했다.
- 기본값은 `false`다.
- `autoApplyPreprocessing=true`일 때 receipt + guard 통과 샘플만 `productionApplied=true`가 된다.
- `productionApplied=true` 대상:
  - `card_002` -> `clahe`
  - `medical_001` -> `clahe`
  - `pos_006` -> `upscale_1_5x`
  - `medical_003` -> `grayscale`
- `invoice_statement`는 항상 `productionApplied=false`다.
- verify script 결과: 11/11 PASS

## 12. 현재 운영 정책
| 옵션 | 기본값 | 설명 |
|---|---:|---|
| `debugPreprocessing` | `false` | 전처리 비교 debug |
| `autoApplyPreprocessing` | `false` | receipt limited auto-apply 명시적 옵션 |

## 13. 안전 기준
- 기본 OCR 결과는 기존과 동일해야 한다.
- `autoApplyPreprocessing=true` 명시가 필요하다.
- receipt 계열만 적용한다.
- `invoice_statement`는 제외한다.
- `preprocessing_candidate` 태그가 필수다.
- guard 통과가 필수다.
- original / variant / debug 정보를 보존한다.

## 14. 다음 작업 후보
1. T-21 Frontend 연결
   - RunOCR/TestWorkspace에 `debugPreprocessing`, `autoApplyPreprocessing` 옵션 추가
2. 추가 실사용 검증
3. 더 많은 receipt 샘플 확보 후 guard 재평가
4. `invoice_statement` template path debug wiring은 별도 장기 후보
5. 서버 기본값 true 전환은 아직 보류

## 15. 검증 결과
- T-20i py_compile: PASS
  - `python -m py_compile .\ocr-server\main.py .\ocr-server\preprocessing_policy.py .\ocr-server\scripts\verify_receipt_limited_auto_apply_t20i.py`
- verify script: PASS
  - `python .\ocr-server\scripts\verify_receipt_limited_auto_apply_t20i.py`
  - key assertions 11/11 PASS
  - auto-apply simulation 7/7 PASS
  - invoice_statement baseline 7/7 exact
- typecheck: PASS
  - `npm.cmd run typecheck`
- build: PASS
  - `npm.cmd run build`
  - 종료 코드 0. 출력 말미에 ESLint 설정 메시지 `nextVitals is not iterable`가 표시됐으나 build는 성공했다.

## 16. 최종 운영 판단
- T-20 시리즈의 결론은 "기본값 off + debug 비교 가능 + receipt 한정 명시적 auto-apply"다.
- 현재 상태에서 서버 기본값을 true로 전환하지 않는다.
- 운영 적용은 프론트 옵션 연결 후, 사용자가 명시적으로 켜는 방식이 적절하다.
- `invoice_statement`는 row/table 안정성이 더 중요하므로 auto-apply 대상에서 계속 제외한다.
