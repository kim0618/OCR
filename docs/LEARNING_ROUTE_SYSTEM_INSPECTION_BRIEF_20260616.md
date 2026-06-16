# 학습 루프 심층 점검 브리프 (검증판) — Codex 실행용

_작성 2026-06-16 · 대상: Codex · 모드: **읽기 전용 시스템 진단**_

> 이 문서는 작성자가 측정 핵심 코드(`run_batch.py`·`compare_run.py`·`compare_fields.py`·`compare_table.py`·`metrics.py`·`gt_loader.py`·`buckets.py`·`checker.py`·`contract.py`)를 **직접 읽고 검증한 사실** 위에 썼다. §1은 *현재 루프의 실제 구조*, §3은 *코드로 이미 확인된 약점*(추정 아님), §4는 *스케일·GPU·실데이터에서 Codex가 확장 점검할 것*이다.

---

## 0. 목적

학습 루프가 **현재 베이스(24장)에서 수천장 실데이터로 확장**되고 **실제 개선/학습을 반복**할 때, 어디가 부러지고 무엇이 중요한가. 특정 run의 점수가 맞냐가 아니라 **루프라는 시스템이 스케일에서 신뢰되고 일반화로 가는가**.

## 1. 현재 학습루프 — 검증된 실제 구조

**파이프라인** (`run_all.py`):
```
build_manifest → run_batch → compare_run → metrics → report → checker → trend
```
| 단계 | 입력 → 출력 | 핵심 |
|---|---|---|
| `build_manifest(testset)` | testset 프로파일 → active/canned 샘플목록 | study=24(6문서×{원본+각도변주3}), thin=6 canned(모형) |
| `run_batch` | 이미지 → `/ocr/extract` POST → `samples/<src>.json` | rec={documentFields, extractionPath(free/fallback), preprocess telemetry}. + 신규 `snapshots/` 사이드카 |
| `compare_run` | rec + GT → `compare/<src>.json` + `compare_summary.json` | `load_gt`+`compare_fields`+`compare_table`+`tag_sample` |
| `metrics.compute_metrics` | compare/*.json → `metrics.json` + `metrics_timeseries.sqlite` | micro/macro·perField·byPath·coverage·slices·buckets |
| `report`/`report_compare` | metrics → md/html | "가설" 배너(소표본 정직성) |
| `checker`(+phase0~4) | run → PASS/FAIL 7체크 | **게이트** (자기점검; PASS여야 수치 신뢰) |
| `trend` | sqlite → 델타 | ▲▼ 추세 |

**평가 베이스 (정정 확정):** **24 이미지 = 6 distinct 문서/레이아웃(1·3·4·5·6·7) × {원본+각도변주 3}.** → **레이아웃 다양성=6, 각도 강건성 표본=24.** 변주는 같은 문서의 각도 재촬영이라 *새 레이아웃이 아니다*. 일반화(데이터 다양성)는 6에 가깝고, 회전 강건성은 24로 본다.

**점수 정의 (코드 검증):**
- **필드**(`compare_fields.py`): GT가 준 키만 채점. status = match/mismatch/ext_missing/**gt_empty(제외)**. `fieldAccuracy = match/scored`. **spurious**(GT 빈칸인데 추출이 채움) = 별도 집계, 정확도엔 불산입. **coverage** = gtPresent → matched / extAttemptedMiss / extNotAttempted(미시도). `_spurious_tag`로 rule/learn 라우팅.
- **표/셀**(`compare_table.py`): 행 정렬 = **rowIndex(rich, 위치 오라클)** 또는 **content(thin, 유사도 greedy thr=0.30)**. **⚠️ 매칭된 행(pairs)의 셀만 채점** — `gtOnlyRowIdx`(통째 누락 행)는 셀 분모에 안 들어감. `cellAccuracy = match/scored`.
- **집계**(`metrics.py`): overall=**micro(항목가중**, 큰 표 지배) + **macro(샘플평균)**. byPath=**free/fallback** 분리. editedSplit·difficultySplit·slices(extractionPath/supplier/layout/qualityTag/profile). buckets 4종.
- **버킷**(`buckets.py`, 휴리스틱): recognition(글자오류)/structure(오배정·행수)/layout(컬럼시프트)/preprocessing(샘플 붕괴=방향/deskew). 전처리 신호는 `extract_debug.preprocess`에서. *"소표본 태그는 가설"*.
- **GT 로딩**(`gt_loader.py`): schemaVersion 게이트, rich는 COMMON_12 필수, **excludedRows는 분리(절대 miss 아님)**, 중복 labelEn 거부. thin은 gt.keys()만 채점.

**checker 7불변식(이미 보장):** normalization-golden / phase0(GT파싱) / phase1(manifest·loader) / phase2(run결과) / phase3(compare) / phase4(metrics: perField·byPath·difficultySplit·coverage cross-foot, 분모분할) / manifest↔run(parse-rate 100%).

## 2. 무엇이 중요한가 (load-bearing)

- **측정 신뢰의 축:** GT 계약(gt_loader) → 정규화(normalize golden) → 정렬(compare_table 행정렬) → cross-foot(checker phase4). 이 사슬 중 하나만 틀려도 모든 숫자가 오염.
- **일반화 판별의 축:** macro·slices·byPath·coverage·buckets. **micro만 보면 큰 표 1벤더가 지배해 "핵심 다수가 깨져도 좋아 보임".** 스케일에선 이 축이 정직성의 전부.
- **자동 게이트:** checker. 단 *"checker PASS ≠ 측정이 옳다"* — cross-foot이 맞아도 정의 자체가 약하면 통과함(§3 W1이 그 예).

## 3. 코드로 이미 확인된 약점 (검증됨 — Codex가 스케일 관점서 확대 평가)

| ID | 약점 (file:line) | 스케일/GPU에서의 영향 | 부류 |
|---|---|---|---|
| **W1** | **셀 메트릭이 통째-누락 행을 못 봄.** `compare_table.py:127`이 matched 행 셀만 채점, `gtOnlyRowIdx`는 분모 밖. 게다가 `metrics.py:110`이 macro_cell을 cellAccuracy≠None일 때만 적재 → **전 행 누락 샘플(scored=0→None)은 micro·macro 양쪽서 소멸.** | 수천장에선 "6행 중 1행만 추출, 그게 완벽" → cellAccuracy 100%로 보임. **최악 샘플이 지표에서 사라짐** = 일반화 측정 실패. (구조신호 rowCountMatch·gtOnlyRowIdx·buckets는 잡지만 헤드라인 미반영) | `generalization-gap` |
| **W2** | **trend는 micro만 기록.** `metrics.py:_TS_COLS` = field/cell micro + free/fallback + buckets. macro·coverage·slices·spurious 미적재. | micro 오르면서 macro·최악군 악화돼도 추세가 "개선"으로 보임. | `generalization-gap` |
| **W3** | **slices 코드만 있고 데이터 없음.** `metrics.py:78,156` qualityTag→"untagged"(실태그 미존재), supplier=현재 6종, layout=single/multi. | 벤더·조건별 약점 가시화가 스케일의 핵심인데 **qualityTags·다벤더 데이터가 아직 없음**(data-gap). 코드 경로는 준비됨. | `data-gap` |
| **W4** | **OCR품질 민감 상수들이 박혀 있음.** content 정렬 thr=0.30·유사도 가중 0.5/0.35/0.15(`compare_table.py:74,77`), buckets sample_failed miss_rate≥0.7·cell_acc≤0.3(`buckets.py:158`), 전처리 임계 "24장 캘리브"(`buckets.py:53`), crop conf컷 0.3. | **server_det는 라인·박스 밀도가 달라짐** → 행정렬·버킷귀속·free/fallback 분기가 흔들려 *측정이 device에 종속*. GPU 전환=불연속점. | `gpu-risk` |
| **W5** | **버킷은 휴리스틱·소표본 가설.** `buckets.py:4`. preprocessing은 sample-level advisory로 `tally[PREPROCESSING]+=1`(`:177`)인데 원 defect의 버킷을 안 빼서 **이중계상** 가능. | 스케일에서 원인귀속(룰대상 vs OCR바운드 vs GPU몫) 자동 트리아지의 신뢰도 미검증. | `improvement` |
| **W6** | **free(일반) 경로 의존도 낮음.** run 034: free 6 / fallback 18. | 실데이터엔 템플릿 없어 **free가 주력이어야** 하는데 대부분 fallback(template/reference)으로 떨어짐. "범용 OCR" 목표와의 핵심 갭. 스냅샷 replay가 진단 도구. | `scale-blocker` |

## 4. Codex가 점검·확장할 것 (스케일·GPU·실데이터)

§3의 W1~W6를 **수천장·다벤더·server_det** 관점으로 확대하고, **빠진 약점을 능동 발굴**한다. 영역별 질문:

- **측정 정합성:** W1과 *같은 클래스*의 다른 은폐(미시도 필드, 빈 추출, 0행, 정렬 실패가 cell분모 왜곡) 전수. checker가 통과시키는 *정의 약점* 능동 탐색.
- **일반화 판별:** documentType·qualityTags·벤더·난이도 슬라이스가 스케일에서 작동하나(W3). micro/macro 괴리·최악군 추적·오버핏 탐지(holdout/교차) 장치 유무.
- **run 스케일:** `run_batch` 순차 POST(workers=4)·timeout 600s·산출물 폭증(samples·compare·snapshots JSON × 수천 × 매 run)이 파일시스템·git에서 버티나 → DB/스토리지 전환 시점.
- **GT 수급(병목):** 실 GT는 모형(thin). 수천장 GT를 무슨 비용·일관성으로? `draft-gt-document.v1`/thin war-column 계약이 Phase7 DB-ETL과 정합한가. GT 오류율 측정.
- **버전·재현성:** OCR모델(mobile→server→차기)·파서·GT·스냅샷 버전축 관리되나. 6/16 파서 리네임으로 replay 깨졌던 것처럼 버전 불일치 상시 위험. **스냅샷에 모델·코드 버전 태깅** 필요. trend가 server_det 전환을 불연속점으로 끊나(W2·W4).
- **회귀 안전망:** baseline lock이 평균만 보나 → 슬라이스별 회귀(전체↑인데 핵심 벤더↓) 탐지. OCR 변동성 대비 신호 분리.
- **free 성숙(W6):** 왜 fallback으로 떨어지나(헤더/컬럼별칭 인식, 표-크롭 재OCR, 저해상 — 메모리). 스냅샷 replay로 진단해 *일반 룰*로 끌어올리는 로드맵.
- **인프라:** localStorage/IndexedDB→DB 마이그레이션(메모리), git 바이너리(sqlite)·대량 JSON round-trip의 스케일 붕괴 → 데이터평면(DB) vs 코드평면(git) 분리.

## 5. 산출물 (`docs/LEARNING_ROUTE_SYSTEM_REPORT_20260616.md`)

1. **루트 성숙도 맵** — 데이터수급/GT/평가/측정/개선/회귀/버전/인프라 각 단계: 현재/목표/격차/성숙도(0~3).
2. **약점 표** — §3 W1~W6 *재검증 결과* + 신규 발견. 컬럼: `ID | 영역 | 부류 | 심각도 | file:line/run근거 | 스케일 영향 | 권고`. 부류=`measurement-bug`/`generalization-gap`/`scale-blocker`/`data-gap`/`gpu-risk`/`improvement`/`ok`.
3. **스케일 진입 선결 게이트** — 수천장 실데이터 전 *반드시* 갖출 것(우선순위).
4. **일반화 측정 처방** — 누락-실패 가시화(W1)·슬라이스(W3)·trend 확장(W2)·오버핏 탐지 구체안.
5. **free 성숙 로드맵**(W6) · **GPU 측정 드리프트 상수 목록**(W4).

심각도: **Critical**=점수가 틀림/게이트가 결함 통과/스케일 진입 차단 → NO-GO. **High**=일반화 오측정·GPU 드리프트. **Medium**=효율·운용. **Low**=문서.

## 6. 스코프 밖
- 코드·GT·`public/data`·run 산출물·보호파일(`main.py`/`amount_extractor.py`/`document_classifier.py`/suppression·orientation·baseline 정책) 수정. 발견·권고만.
- 개별 샘플 정답 맞추기(두더지잡기). 모델 fine-tune 실행. 전처리 deskew 결함 *자체* 수정 — 단 루프가 그걸 *계측·분류*하는지는 평가.

---
_검증 기반 브리프. 발견은 보고서로, 결정은 사람이._
