# 학습 루프 시스템 점검 보고서 - 2026-06-16

_작성: 2026-06-16 · 범위: 읽기 전용 시스템 진단 · 대상: 수천장 실데이터/GPU/server_det 확장 전 게이트_

## 0. 결론

현재 루프는 **작은 회귀 실험을 반복하는 측정 하네스**로는 이미 중요한 골격을 갖췄다. `run_all -> checker`의 자동 게이트, GT 계약, normalization golden, per-field/per-path/macro/slice 지표, snapshot replay의 씨앗은 좋다.

하지만 **수천장 실데이터로 들어가기 전에는 NO-GO**다. 이유는 한 가지가 크다. 표 메트릭이 통째 누락 행을 헤드라인 cell accuracy에 반영하지 못하고, checker도 그 정의 약점을 통과시킨다. 이 상태에서는 "행을 거의 못 뽑았는데 맞춘 셀만 완벽"한 샘플이 전체 성능을 좋게 보이게 할 수 있다. 여기에 trend가 micro 일부만 저장하고, qualityTag/실데이터/모델 버전축이 비어 있어 일반화 판단과 GPU 전환 비교가 흔들린다.

## 1. 루트 성숙도 맵

| 영역 | 현재 | 목표 | 격차 | 성숙도 |
|---|---|---|---|---:|
| 데이터 수급 | `invoice_study` 24 active = 6 base x variants, `invoice_thin` 6 canned | 다벤더/다품질/실제 DB 표본 수천장, holdout 분리 | 현재 다양성은 6 레이아웃에 가깝고 변주는 독립 레이아웃이 아님 | 1 |
| GT | rich 계약과 thin 계약 공존, loader 게이트 있음 | 실데이터 GT 생산/검수/오류율 측정/버전 관리 | thin은 canned fixture라 실제 DB-ETL 계약 검증 전 | 1 |
| 평가 실행 | `run_batch` 병렬 POST, canned 재생, snapshot sidecar | 대량 run 큐/재시도/샘플 단위 재현/스토리지 분리 | 파일 JSON 산출물 폭증, timeout/worker 튜닝 수동 | 1 |
| 측정 정의 | field/macro/byPath/coverage/slices 보유 | 누락 행/0행/정렬 실패를 헤드라인이 정직하게 반영 | W1 때문에 cell headline 오염 가능 | 1 |
| 개선 루프 | buckets와 free snapshot replay 씨앗 | 원인귀속 신뢰도 검증, 일반 룰 승격 루프 | 휴리스틱과 중복계상, free 비중 낮음 | 1 |
| 회귀 안전망 | checker 7단계, phase4 cross-foot | slice별/최악군/모델전환별 regression gate | micro 중심 trend, cell 정의 약점 미검출 | 1 |
| 버전/재현성 | run_meta에 서버 URL/요청/manifestCounts 저장 | OCR 모델/코드 SHA/GT schema/data version/snapshot schema 저장 | server_det 전환 불연속점 추적 부족 | 1 |
| 인프라 | eval/runs JSON + sqlite | DB/object storage, code plane과 data plane 분리 | 수천장 x run 산출물이 git/FS에 부담 | 1 |

성숙도 기준: 0 없음, 1 소표본 하네스, 2 스케일 전 파일럿 가능, 3 운영 학습 루프 가능.

## 2. 약점 표

| ID | 영역 | 부류 | 심각도 | file:line/run근거 | 스케일 영향 | 권고 |
|---|---|---|---|---|---|---|
| W1 | 표 셀 정확도 | measurement-bug | Critical | `compare_table.py:127-166`, `metrics.py:107-111` | 매칭된 행의 셀만 분모에 들어가고 `gtOnlyRowIdx`는 cell denominator 밖이다. 전 행 누락으로 `cellAccuracy=None`인 샘플은 macro에서도 빠진다. | `missingRowCellPenalty` 또는 `tableRecall`을 헤드라인에 추가. GT 행 x 채점 가능 셀 기준의 `cellRecall`을 별도/기본 지표로 승격. |
| W2 | 추세 저장 | generalization-gap | High | `metrics.py:220-262` | timeseries는 field/cell micro, free/fallback field, bucket만 저장한다. macro, coverage, slices, spurious, row miss 추세가 사라진다. | sqlite schema v2: macro, row recall, coverage, spurious, slice worst-N, model/version columns 추가. |
| W3 | 슬라이스 데이터 | data-gap | High | `metrics.py:79-86`, `metrics.py:151-157`, run 034 `qualityTag=untagged` | slice 코드 경로는 있지만 품질태그가 없어 회전/저해상/스캔/사진 조건별 일반화 판단이 불가하다. | manifest에 `qualityTags`, `condition`, `captureSource`, `vendorId/layoutId` 명시. variant는 angle robustness로 따로 묶기. |
| W4 | OCR/GPU 민감 상수 | gpu-risk | High | `compare_table.py:77`, `buckets.py:158-177`, `run_batch.py:155-160` | content align threshold 0.30, sample_failed 임계, timeout 등이 detector/box 밀도 변화에 민감하다. server_det 전환 시 측정 결과가 모델 성능인지 지표 드리프트인지 분리하기 어렵다. | mobile/server_det 병렬 calibration run. 상수와 모델을 run_meta에 기록하고 threshold sensitivity 리포트 추가. |
| W5 | 버킷 휴리스틱 | improvement | Medium | `buckets.py:1-13`, `buckets.py:123-149`, `buckets.py:158-177` | preprocessing은 sample-level advisory로 추가 tally만 하므로 recognition/structure와 중복계상될 수 있다. 자동 트리아지 신뢰도는 아직 미검증이다. | bucket은 "원인 후보"로 유지하되 exclusive primaryCause와 advisory flags를 분리. 수동 라벨 표본으로 precision 측정. |
| W6 | free 경로 성숙 | scale-blocker | Critical | run 034 study `free=6/fallback=18`, `run_batch.py:225-231` | 실데이터에는 템플릿 fallback이 없거나 약하므로 free가 주력이어야 한다. 현재 대부분 fallback이면 범용 학습 루프가 아닌 템플릿 회귀 루프가 된다. | fallback 원인 코드를 저장하고 snapshot replay로 header/alias/column/low-res 실패를 일반 룰 backlog로 전환. |
| W7 | checker blind spot | measurement-bug | Critical | `phase4_check.py:34-86`, `checker.py:97-114` | checker는 field cross-foot, byPath, difficulty, coverage는 보지만 cell denominator와 row-miss 반영 정의를 검증하지 않는다. W1이 PASS된다. | phase4에 `rowRecall`, `gtOnlyRowIdx` 합계, cell denominator 정책 cross-foot을 추가. W1 fixture를 golden regression으로 고정. |
| W8 | 변주 샘플 독립성 | generalization-gap | High | `build_manifest.py:63-85`, `contract.py:185-214`, run 034 `active=24` | 24장은 6문서의 각도/조건 변주다. macro sample 평균이 레이아웃 다양성보다 회전 강건성에 더 가깝다. | report/trend에 `distinctDocumentCount`, `variantGroupMacro`, `baseVsVariant`를 분리 표기. |
| W9 | thin/DB 경로 미검증 | data-gap | High | `contract.py:117-136`, `run_batch.py:121-143` | `invoice_thin`은 canned rec 재생이라 실제 DB-ETL, 실 GT 품질, live OCR path를 검증하지 않는다. | Phase7 전 실제 ETL 샘플 30~100건으로 thin live/canned parity gate 생성. |
| W10 | 버전 재현성 | scale-blocker | High | `run_batch.py:232-244`, `compare_run.py:53-64` | run_meta에 OCR 모델명, detector, parser commit, GT/data version, snapshot schema가 없다. 파서 rename/replay 깨짐 같은 불연속이 반복될 수 있다. | run_meta와 snapshot에 `codeRevision`, `ocrEngine`, `detectorProfile`, `parserVersion`, `gtVersion` 저장. trend는 버전 변경을 segment로 끊기. |
| W11 | 산출물 스토리지 | scale-blocker | Medium | `run_batch.py:193-217`, `metrics.py:220`, `ocr-server/eval/runs/*` | samples/compare/snapshots/report/sqlite가 run마다 파일로 늘어난다. 수천장 x 다회차면 git/FS/리포트 렌더가 병목이 된다. | 원본/스냅샷은 object storage, metrics/compare는 DB, repo에는 코드와 manifest schema만 유지. |
| W12 | 필드 coverage의 표현 한계 | improvement | Medium | `compare_fields.py:63-108`, `metrics.py:200-205` | coverage는 field에는 있으나 table에는 없다. 또 mismatch는 coverage 객체 안에 별도 키가 없어 해석이 phase4 공식에 의존한다. | field/table 공통 `present/matched/missing/wrong/notAttempted` 스키마로 정리. report에는 attempt와 correctness를 분리. |

## 3. 스케일 진입 선결 게이트

1. **W1/W7 먼저 수정:** 누락 행을 반영한 table recall/cell recall을 헤드라인과 checker에 넣는다. 전 행 누락, 0행 추출, 1행만 추출, rowIndex 중복 fixture를 regression으로 고정한다.
2. **trend v2:** micro만 보지 말고 macro, variantGroupMacro, worst slice, coverage, row recall, spurious, free ratio, model/version을 저장한다.
3. **버전 태깅:** run_meta/snapshot/metrics에 OCR engine, detector profile, parser version, code revision, GT version을 기록한다.
4. **실데이터 pilot:** 다벤더 30~100장으로 qualityTags/vendor/layout/captureSource를 채운다. 같은 문서 변주는 robustness slice로 분리한다.
5. **free path gate:** fallback ratio가 일정 이상이면 GO 불가. fallback 이유별 tally와 replay 가능한 snapshot이 있어야 한다.
6. **스토리지 분리 기준:** 100장 이상 반복 run부터 eval/runs JSON을 장기 저장소로 보지 말고 DB/object storage 설계를 시작한다.

## 4. 일반화 측정 처방

- 헤드라인을 `fieldMicro/fieldMacro/cellPrecisionLike(현행)/cellRecall/tableRowRecall`로 분리한다. 현행 cellAccuracy는 "매칭된 행 안에서의 셀 정확도"라는 이름으로 낮춘다.
- macro는 sample macro와 document-group macro를 함께 낸다. `1.jpg`, `1-1.jpg`, `1-2.jpg`, `1-3.jpg`는 같은 layout group이다.
- slices는 최소 `vendorId`, `layoutId`, `qualityTags`, `captureSource`, `rotationVariant`, `documentType`, `extractionPath`, `detectorProfile`이 필요하다.
- worst-N 샘플과 worst slice를 trend에 저장한다. 평균 개선이 있어도 핵심 벤더/문서군이 악화되면 FAIL로 본다.
- holdout을 분리한다. 룰을 만들 때 사용한 문서군과 새 벤더/새 레이아웃 문서군의 지표를 같은 표에 섞지 않는다.

## 5. free 성숙 로드맵

1. `extractionPath=fallback`마다 free 실패 사유를 저장한다: table_not_detected, header_alias_miss, column_boundary_low_conf, low_resolution, orientation/preprocess, validation_reject 등.
2. snapshot replay를 free 전용 단위 테스트처럼 사용한다. OCR 재실행 없이 parser 변경이 어떤 실패 사유를 줄였는지 본다.
3. header/column alias는 템플릿 특화 패치가 아니라 공통 alias 사전과 confidence 기반 후보군으로 승격한다.
4. 표 crop 재OCR/저해상 보정은 메모리와 latency를 별도 계측한다. 정확도만 오르고 비용이 폭발하면 server_det pilot에서 병목이 된다.
5. 목표 gate: 실데이터 pilot에서 free ratio, free field/cell recall, fallback reason distribution이 함께 개선되어야 한다.

## 6. GPU/server_det 드리프트 상수 목록

| 상수/정의 | 위치 | 위험 |
|---|---|---|
| content row align threshold `0.30` | `compare_table.py:77` | detector가 라인 분할을 바꾸면 greedy matching 결과가 달라짐 |
| row similarity 가중치 `0.5/0.35/0.15` | `compare_table.py:73-75` | 품명 OCR 품질과 금액/수량 인식 비중이 모델별로 달라짐 |
| preprocessing `miss_rate >= 0.7` | `buckets.py:158-167` | GPU에서 field miss profile이 바뀌면 preprocessing으로 과소/과대 귀속 |
| `cell_acc <= 0.3` sample_failed | `buckets.py:158-160` | W1 때문에 누락 행이 cell_acc에 안 잡히면 sample_failed도 둔감해짐 |
| workers/timeout | `run_batch.py:155-160`, `run_all.py:355-358` | 서버 처리량/메모리/timeout 실패가 성능 실패처럼 섞일 수 있음 |
| extractionPath 분류 | `run_batch.py:48-52` | `extractionSource` naming 변경 시 free/fallback 집계가 흔들릴 수 있음 |

## 7. 최종 판정

**스케일 진입 판정: NO-GO.**

단, 이는 루프가 나쁘다는 뜻이 아니다. 지금 루프는 "어디가 위험한지 드러낼 만큼" 이미 자랐다. 다음 단계의 핵심은 새 OCR 룰을 더하는 것이 아니라, **나쁜 실패가 평균 속으로 사라지지 못하게 측정 정의와 추세 저장을 먼저 잠그는 것**이다. W1/W7, trend v2, version tagging, qualityTag/실데이터 pilot이 끝나면 수천장 확장 판단을 다시 할 수 있다.
