# 학습 루프 심층 점검 보고서

_작성: 2026-06-16 · 기준: 현재 working tree + run `034_20260616_113615` · 모드: 읽기 전용 감사_

## 1. 요약 판정

**GPU 이전 판정: NO-GO.**

블로커는 점수 산출의 핵심 분모 문제다. rich 표 비교에서 `rowIndex`로 매칭된 행만 셀 점수에 들어가며, `gtOnlyRowIdx`에 남은 GT 행의 셀은 `ext_missing`으로 분모에 들어가지 않는다. 예: run 034의 `6-3.jpg`는 `rowsGt=6`, `rowsExt=1`, `gtOnlyRowIdx=2..6`인데 셀 분모가 5칸뿐이다. 행 누락을 구조 결함으로 태깅하더라도, 표 cell accuracy 자체는 누락 행 전체를 반영하지 못한다.

따라서 현재 루프의 field 집계와 run 무결성은 대체로 믿을 수 있지만, **cell accuracy와 cell trend는 행 누락/행 정렬 실패가 있는 구간에서 과소 페널티 또는 왜곡 가능성이 있어 의사결정 지표로 쓰기 어렵다.**

## 2. 발견 표

| ID | 영역 | 부류 | 심각도 | 파일:줄 | 관찰/증거 | 권고 |
|---|---|---|---|---|---|---|
| F-01 | A3/A4/C3 | measurement-bug | Critical | `ocr-server/eval/compare_table.py:114-119`, `126-151`, `153-165`; `ocr-server/eval/runs/034_20260616_113615/study/compare/6-3.jpg.json:210-218`, `290-298` | 비교는 매칭된 `pairs`만 순회한다. `6-3.jpg`는 GT 행 2-6이 `gtOnlyRowIdx`로 남지만 셀 분모는 row1의 5 scored cell뿐이다. | unmatched GT 행의 non-empty GT cells를 `ext_missing`으로 cellCounts에 포함하거나, 별도 structural-miss denominator를 cell accuracy/trend와 함께 게이트해야 한다. |
| F-02 | C3 | invariant-gap | Critical | `ocr-server/eval/phase3_check.py:79-81`, `ocr-server/eval/phase4_check.py:49-83`; run evidence `compare_summary.json:350-360` | checker는 `cell scored == match+mismatch+ext_missing`만 확인한다. `rowsGt=6/rowsExt=1` 같은 경우도 cross-foot은 통과한다. | checker에 `gtOnlyRowIdx` 존재 시 기대 셀 누락 수와 cell denominator 관계를 검증하는 invariant를 추가한다. |
| F-03 | B1/B2 | silent-failure | Medium | `ocr-server/eval/compare_run.py:45-50`; `ocr-server/eval/checker.py:63-87` | `compare_run`은 sample JSON 누락/깨짐 시 즉시 예외로 중단된다. checker의 manifest crosscheck는 누락을 잡지만 compare 단계 자체는 부분 산출물 후 중단될 수 있다. | run/compare 단계의 실패 산출물을 명시적으로 `status=error` 또는 compare error record로 남겨 후속 report에서 침묵하지 않게 한다. |
| F-04 | B3/F5 | gpu-risk | Medium | `ocr-server/eval/run_batch.py:61-64`, `225-230`; `metrics.json:180-217` | source 분류는 `extractionSource` 문자열에 `"free"` 포함 여부다. run 034는 free 6, fallback 18로 합계는 OK지만, 문자열 계약이 바뀌면 분포/trend가 오염된다. | 서버 응답에 stable enum(`free`/`fallback`)을 두거나 checker가 known source raw set을 기록/경고한다. |
| F-05 | D1/D2 | ok / operational-risk | Medium | `ocr-server/eval/metrics.py:218-264`; `ocr-server/eval/trend.py:35-44`, `76-82`; `contract.py:145-169` | sqlite는 `(testset, runTs)` PK + `INSERT OR REPLACE`라 같은 runTs 재실행은 멱등. trend는 testset별 rows를 timestamp key로 안정 정렬하고 sampleCount 변경 시 비교 보류. 단 sqlite는 바이너리라 AWS/로컬 양방향 쓰기 시 git 충돌 위험. | GPU eval을 단방향 산출물로 운용하고, 로컬은 보고서 소비/코드 수정만 수행한다. |
| F-06 | F1 | ok | Low | `ocr-server/main.py:1123-1128`, `3278-3279` | sed 대상 확인: `PP-OCRv5_mobile_det` 1회, `device="cpu"` 1회, `paddle_device` 1회. `PP-OCRv5_server_det`/`device="gpu"`는 0회. | 현재 문자열 치환은 다중매치 위험 낮음. 치환 후 `paddle_device` 라벨도 같이 바꿔 trend/report 혼동을 막는다. |
| F-07 | F2 | gpu-risk | High | `ocr-server/main.py:1162-1164`, `2610-2621`, `2662-2663`, `3078-3079`; `extractors/table_region.py:48-69`, `132-141`; `main.py:1241`, `1276`, `1442`, `1452`, `1673` | CPU/mobile OCR에 맞춘 상수: OCR width 950/760, confidence 0.3, bbox pad/height floor, y-row gap `0.025`, table bbox `pad_ratio=0.012`, min bbox 20px. server_det는 line split/box density가 바뀔 수 있다. | GPU 첫 run은 score delta보다 free/fallback 분포, rowCount mismatch, align/gtOnly/extOnly 변화를 별도 기준선으로 본다. |
| F-08 | B5/E1 | ok | Low | `ocr-server/eval/run_batch.py:98`, `120-124`, `197-208`; `main.py:3035-3048`; run meta `run_meta.json:44-52` | `captureOcrSnapshot=1`은 응답에 sidecar envelope를 추가하고, run_batch가 `_ocrSnapshot`을 pop해 `snapshots/`에 저장한다. run 034 samples에는 snapshot key가 없고 snapshots는 24개다. | 유지. checker glob은 `samples/*.json`, `compare/*.json`만 보므로 snapshots는 채점에서 분리된다. |
| F-09 | G | ok | Low | `main.py:67`, `3149`; `extractors/invoice_statement_free.py:122` | `sanitize_party_name_fields` 리네임 추정 건은 현재 `sanitize_document_scalar_fields`로 import/call/def가 정합. 죽은 참조 없음. | 유지. |

## 3. 불변식 점검 결과

| 불변식 | 결과 | 근거 |
|---|---|---|
| `Σ perField.scored == overall.field.scored`, `Σ perField.match == overall.field.match` | PASS | 재계산: 244/154 = `metrics.json:7-14`. |
| `Σ byPath.field.scored == overall.field.scored` | PASS | fallback 176 + free 68 = 244. |
| `Σ difficultySplit.scored == overall.field.scored` | PASS | 재계산 244/154. |
| `coverage.gtPresent == overall.scored`, `coverage.matched == overall.match` | PASS | `metrics.json:262-268` = 244/154. |
| `gtPresent == matched + extAttemptedMiss + extNotAttempted + mismatch` | PASS | 244 = 154 + 36 + 0 + 54. |
| active samples in `samples/`, `status==ok`, compare exists | PASS | run meta `ok=24`, `error=0`, free/fallback 6/18 (`run_meta.json:44-52`). |
| report hypothesis banner exists | PASS by checker design | `phase4_check.py:84-90` checks report length/banner after render. |
| micro/macro definitions | PASS | `metrics.py:103-110`, `158-177`; run 034 field micro 63.1%, macro 61.8%, cell micro 74.3%, macro 41.5%. |
| spurious excluded from accuracy but counted once | PASS | `compare_fields.py:77-111`, `compare_table.py:134-148`, `metrics.json:162-171`; recompute field 1, cell 8. |
| table scored cells = all GT non-empty cells across GT rows | FAIL | F-01. unmatched GT rows are outside `rows` loop and not scored. |
| free/fallback sum == ok samples | PASS | run 034: 6 + 18 = 24 (`run_meta.json:44-52`). |

## 4. GPU 준비성

**F1 device/model sed:** PASS. `main.py`의 대상 문자열은 각각 1회다.

**F2 CPU-calibrated constants:** High risk. 목록:

- OCR resize: `ocr_max_w=950`, `ocr_min_w=760` (`main.py:2610-2621`).
- confidence cutoff: crop OCR `c >= 0.3`, full OCR `confidence < 0.3` skip (`main.py:1162-1164`, `2662-2663`).
- bbox/y grouping ratios: `ocr_h * 0.025`, `ocr_w * 0.025`, row grouping `th * 0.025` (`main.py:1241`, `1276`, `1442`, `1452`, `1673`).
- table region bbox: `_rows_by_y(... tol_factor=0.6)`, `pad_ratio=0.012`, min bbox `20x20` (`extractors/table_region.py:48-69`, `132-141`).
- full-res table re-OCR is explicitly compensating for 950px free first pass (`main.py:3078-3079`).

**F3 EXPECTED_ROWS:** OK as contract facts. `contract.py:116-134`, `177-179` define expected rows per base sample; variants inherit base via `base_source` (`contract.py:188-198`). No evidence they are recomputed from current OCR output.

**F4 timeout:** OK/neutral. `run_batch.py:153-160` default 600s; timeout exceptions become `status=error` in `run_one` (`run_batch.py:126-129`) and checker requires zero errors.

**F5 first GPU run continuity:** Risk. Trend will honestly show sampleCount changes and byPath split, but score continuity can break because server_det may change free/fallback distribution and row alignment. GPU first run should be treated as a new measurement baseline, not a direct rule-regression verdict.

## 5. 미커밋 6파일 검증

- `compare_fields.py`: spurious is parallel to `gt_empty` and does not enter `scored`; coverage split is internally consistent. OK.
- `compare_table.py`: spurious handling is OK, but unmatched GT rows are not converted into cell misses. Critical measurement bug.
- `metrics.py`: micro/macro and cross-foot aggregation are internally consistent. sqlite write is idempotent via `INSERT OR REPLACE`. OK with operational sqlite conflict caveat.
- `report.py`: report includes micro/macro, spurious, slices, examples. It displays rowCount mismatch but cannot fix the underlying denominator. OK as renderer.
- `run_all.py`: orchestrates manifest/run/compare/metrics/report/checker and isolates testset failures. OK as orchestrator, but it inherits checker blind spot.
- `extractors/invoice_statement_free.py`: sanitizer rename is wired through current import/call sites. No dead reference found.

## 6. 남은 가설 / 추가 측정 제안

1. Add a read-only probe that recomputes expected table denominator from GT rows and reports `unscoredGtCellsDueToMissingRows` per sample. Run it before GPU migration and compare against current cellCounts.
2. On first GPU run, publish a separate “measurement continuity” block: free/fallback distribution, rowCount mismatch count, sum `gtOnlyRowIdx`/`extOnlyRowIdx`, OCR line count distribution, and preprocess telemetry.
3. Treat sqlite as generated GPU-side history. Do not let AWS and local both append to `metrics_timeseries.sqlite`.
4. Expand normalization golden for real edge cases found in GT/extraction: full-width digits, negative/zero amounts, currency symbols, decimal quantities, business-number OCR separators. Current golden passing proves regression safety, not representativeness.
