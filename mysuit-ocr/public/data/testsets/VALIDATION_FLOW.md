권장 검증 순서

1. 작은 수정 후: `google_fast` 또는 `baseline_fast`만 먼저 실행
2. 방향이 맞으면: `baseline` / `google` 대표셋 실행
3. 최종 반영 전: full regression 실행

의도

- `baseline_fast`: 회귀 민감 축을 빠르게 확인
- `google_fast`: 실전형 일반화 흔들림을 빠르게 확인
- `baseline` / `google`: 대표셋 기준 검증
- 전체셋: 최종 반영 전 마지막 확인
