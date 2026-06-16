# 학습 루프 심층 점검 브리프 (GPU 이전 전 / Codex 실행용)

_작성 2026-06-16 · 대상 실행자: Codex · 모드: **읽기 전용 감사(audit)**, 코드 수정 금지_

---

## 0. 목적

곧 OCR 서버를 **로컬 CPU → AWS GPU**로 옮긴다. GPU에서 eval을 돌리고 그 리포트를 git으로 받아 로컬에서 파서를 고치는 round-trip 체제로 간다. 그 전에 **학습 루프(eval 하니스) 전체가 측정적으로 신뢰할 수 있는지** 심층 점검한다.

> 핵심 질문: **"이 루프가 내는 숫자(필드/셀 정확도, free/fallback, 트렌드)를 믿고 의사결정해도 되는가?"**
> 점수가 틀리면 GPU에서 아무리 좋아져도 잘못된 방향으로 고치게 된다. **측정의 정합성 > 점수 자체.**

## 1. 점검 원칙 (반드시 준수)

1. **측정 우선·시스템 관점.** 개별 샘플 정답을 맞히는 게 목적이 아니다. *측정 파이프라인·불변식·실패 분류*가 옳은지를 본다. 한두 케이스로 일반화·조기단정 금지.
2. **부류로 분해.** 발견은 부류로 묶어 보고: `measurement-bug`(점수 자체가 틀림) / `silent-failure`(에러가 점수에 안 잡힘) / `invariant-gap`(게이트가 못 잡는 구멍) / `gpu-risk`(CPU에 캘리브된 상수·임계) / `ok`(확인됨).
3. **증거 필수.** 모든 발견은 `파일:줄` + 재현/관찰 근거를 단다. 추측은 "가설"로 명시.
4. **읽기 전용.** 코드·`public/data`·GT·lock 문서·run 산출물 수정 금지. **보호파일**(`main.py`, `amount_extractor.py`, `document_classifier.py`, suppression/orientation/baseline 정책)은 읽기만. 수정 제안은 보고서에 분리 기재.
5. **6장은 probe.** study 6 base(+변주)는 수천장 전 *일반화 유효성 가늠*용이다. "지금 룰 고치자"로 몰지 말 것 — 루프가 **그 가늠을 정확히 하는지**만 본다.

## 2. 루프 아키텍처 & 파일맵

파이프라인(`run_all.py`):
```
build_manifest → run_batch → compare(compare_run) → metrics → report → checker → trend
```

| 파일 (`ocr-server/eval/`) | 역할 | 점검 우선순위 |
|---|---|---|
| `contract.py` | GT 계약·testset 프로파일·경로·변주 규칙 (SSOT) | 🔴 높음 |
| `gt_loader.py` | GT 파싱/로딩 | 🔴 높음 |
| `normalize.py` | 필드 정규화(amount/qty/bizno/date/code/index/text) | 🔴 높음 |
| `build_manifest.py` | active/canned/변주 샘플 목록 구성 | 🟠 중 |
| `run_batch.py` | 라이브 OCR POST·결과 기록·스냅샷 사이드카 | 🔴 높음 |
| `compare_run.py` / `compare_fields.py` / `compare_table.py` | 추출값 vs GT 비교(스칼라/표) | 🔴 높음 |
| `metrics.py` | micro/macro·perField·byPath·difficultySplit·coverage 집계 | 🔴 높음 |
| `report.py` / `report_compare.py` | 리포트 렌더 | 🟡 낮 |
| `checker.py` + `phase0~4_check.py` / `p0_thin_check.py` | **게이트**(자기점검 7체크) | 🔴 높음 |
| `trend.py` + `metrics_timeseries.sqlite` | 시계열·델타 | 🟠 중 |
| `buckets.py` | 실패 버킷/전처리 인지 계측 | 🟠 중 |
| `replay_free.py` (신규) | 스냅샷→free 추출기 재실행(재-OCR 0) | 🟠 중 |
| `gen_thin_fixture.py` | thin(canned) 픽스처 down-projection | 🟡 낮 |
| `diag_*`, `probe_*`, `smoke_*`, `test_*` | 진단/스모크(루프 비핵심) | 🟡 낮 |

**⚠️ 미커밋 변경 주의:** 2026-06-16 11:34에 `compare_fields.py`, `compare_table.py`, `metrics.py`, `report.py`, `run_all.py`, `extractors/invoice_statement_free.py`가 직접 수정됨(working tree). run 034는 checker PASS했지만 *"checker가 통과했다 ≠ 측정이 옳다"*. **이 6개 변경분을 특히 정밀 검증**할 것.

## 3. 실행 방법 (관찰용)

```powershell
cd D:\Free_Vue\OCR\ocr-server
.\.venv\Scripts\Activate.ps1
# 백엔드(별 터미널, 9099): uvicorn main:app --host 0.0.0.0 --port 9099 --reload
python eval\run_all.py                 # 전체 루프 1커맨드 (study + thin)
python eval\checker.py --testset invoice_study   # 게이트 단독
python eval\replay_free.py --testset invoice_study  # 파서 재생 충실도
```
최신 run: `eval/runs/<ts>/` (배치는 `<ts>/study/`·`<ts>/thin/`). 기준 run = **034_20260616_113615** (checker 2/2 PASS, study 63.1%/61.8%).

## 4. 점검 영역 (A~H)

### A. 측정 정합성 (최우선)
- **A1 정규화(normalize.py):** golden(`golden/normalization_golden.json`) 케이스가 실제 필드 분포를 대표하나? 통화/수량/사업자번호/날짜의 엣지(공백·콤마·전각·하이픈·통화기호·음수·0)가 누락 없이 커버되나? golden에 *없는* 실데이터 변형이 오탐/미탐을 내는지 표본으로 확인.
- **A2 스칼라 비교(compare_fields.py):** 매칭이 정규화 후 비교인가? **char-level vs exact** 정책이 필드별로 일관적인가? cross-party 오배정(공급자↔공급받는자), 라벨이 값으로 새는 케이스(예 "총수량"이 대표자에)가 어떻게 집계되나?
- **A3 표 비교(compare_table.py):** 행 정렬 — rich는 `rowIndex`, thin은 content-aligned. 정렬 실패 시 **전행 mismatch로 번지는 폭발**이 없나? 행수 불일치(rowsGt≠rowsExt) 처리. 셀 micro/macro 정의 일관성.
- **A4 집계(metrics.py):** checker가 보장하는 cross-foot(아래 §5) **외에** 검증 안 되는 경로가 있나? micro(일치÷전체칸)와 macro(샘플평균)가 정의대로 계산되나? 빈 분모(0칸 샘플) 0-division 가드?
- **A5 스퓨리어스(false positive):** GT 빈칸인데 추출이 채운 건이 정확도에서 제외되고 **별도로만** 카운트되나(이중계상/누락 없이)? run 034에 2건 보고됨 — 정의 확인.

### B. Run 무결성
- **B1 타임아웃/드롭:** `run_batch` timeout=600s. 초과 샘플이 **에러로 잡히나 아니면 조용히 누락**되나? 누락이 분모에서 빠져 점수를 부풀리지 않나? (메모리: 드롭=run 회귀 노이즈)
- **B2 에러 격리:** `run_one`의 예외가 `status=error`로 기록되고 checker parse-rate에 반영되나? HTTP≠200, `document_fields` 누락 경로 확인.
- **B3 free/fallback 분류:** `_classify_source` — `extractionSource`에 "free" 포함=free. 분류 오류 시 free 파서 성과를 fallback으로 오인할 위험.
- **B4 페이지 정책:** 서버 page-0 스코프(멀티페이지 PDF도 0페이지). `multiPage` 플래그가 하드페일 아니라 기록만 하는지(설계대로).
- **B5 스냅샷 무해성(신규):** `captureOcrSnapshot=1`이 채점 경로/응답계약을 안 바꾸나? `samples/*.json`(rec)에 `_ocrSnapshot`가 **안 남는지**(pop 확인). `snapshots/`가 checker glob·report·metrics에 안 걸리는지(별도 폴더·명시경로만 접근 — 확인됨, 회귀 없는지 재확인).

### C. 게이트(checker) 완전성
- **C1 7체크 커버리지:** normalization-golden, phase0(GT파싱), phase1(manifest/loader), phase2(run결과), phase3(compare), phase4(metrics/report), manifest↔run 크로스체크. **각 phase가 실제로 무엇을 단언하나** 읽어서 정리. "통과 조건"이 너무 느슨해 무의미하지 않나?
- **C2 rich vs thin 게이트 비대칭:** thin은 `thin_self_consistency`(범용 cross-foot), rich는 phase2/3/4. **rich 경로가 thin만큼 강한가?** 한쪽만 잡는 결함 클래스가 있나.
- **C3 못 잡는 구멍(invariant-gap):** checker가 통과해도 틀릴 수 있는 시나리오를 능동적으로 찾을 것 — 예: GT 자체가 깨졌는데 통과? 전부 fallback인데 "정상"으로 보임? 행 정렬 실패가 cross-foot은 통과시키며 점수만 오염?

### D. 트렌드/시계열
- **D1 sqlite 쓰기(metrics_timeseries.sqlite):** 멱등한가? 같은 ts 재run 시 중복행/덮어쓰기? 스키마.
- **D2 델타 기준선:** trend가 "직전 run"을 어떻게 고르나(mtime? ts? testset 필터?). 잘못된 기준선과 비교해 ▲▼를 거꾸로 낼 위험.
- **D3 round-trip 충돌:** sqlite는 바이너리 → AWS와 로컬이 둘 다 쓰면 git 충돌. **운용상 eval은 GPU 단방향**이어야 함(보고서에 명시 권고).

### E. 결정성/재현성
- **E1 파서 결정성:** 고정 OCR 입력에서 추출기가 결정론적인가? `replay_free`의 FAITHFUL이 이를 증명(run 034: free 경로 6/6 FAITHFUL). DIFFERS=fallback(정상). **재생이 깨지는 비결정 소스**(dict 순서, set, 시간/난수)가 추출기에 없나.
- **E2 OCR 비결정성:** CPU 스레딩/배치 순서로 OCR 라인 순서가 흔들리나? 흔들리면 점수 변동성으로 잡힘(타임아웃과 별개) — 측정 안정성 영향 평가.

### F. GPU 준비성 (이번 이전의 핵심)
- **F1 device/모델 토글:** AWS는 `main.py`에 3개 sed 적용 — `device="cpu"→"gpu"`, `PP-OCRv5_mobile_det→PP-OCRv5_server_det`, `paddle_device` 라벨. **이 3개 sed의 대상 문자열이 현재 코드에 정확히 1회씩 존재**하는지 확인(다중매치·미스매치 시 sed 오작동).
- **F2 CPU 캘리브 상수 탐지(중요):** 루프/추출기에 **CPU·mobile OCR에 맞춰진 임계·해상도·픽셀 상수**가 있나? GPU/server_det는 라인 수·박스가 달라져 free↔fallback 분기와 행 검출이 바뀐다. 예: 950px 저해상 가정, 표-bbox 픽셀 임계, 행 그룹핑 y-갭, confidence 컷(0.3 등). **이들이 device-민감하면 GPU에서 측정이 흔들림** → 목록화.
- **F3 GT 상수의 device 독립성:** `contract.py`의 `EXPECTED_ROWS`(1.jpg:28 등)는 **GT 사실(검증된 행수)**이라 device 무관이어야 한다. 혹시 CPU-OCR로 역산된 값이 섞였는지 확인.
- **F4 타임아웃:** 600s는 로컬 CPU 변동성 흡수용. GPU에선 무관·무해(확인만).
- **F5 server_det 첫-run 영향:** GPU에서 free/fallback 분포가 바뀌면 **점수 비교의 연속성**이 끊긴다. 루프가 이를 트렌드에서 정직히 드러내나(분포 변화 가시화)?

### G. 미커밋 변경 검증 (11:34 직접수정 6파일)
`compare_fields.py / compare_table.py / metrics.py / report.py / run_all.py / extractors/invoice_statement_free.py` —
- 변경 의도와 실제 동작이 일치하나? 비교/집계 의미를 바꿨다면 **불변식(§5)이 여전히 성립**하나?
- `invoice_statement_free.py`의 함수 리네임(예 `sanitize_party_name_fields`→`sanitize_document_scalar_fields`)이 **모든 호출부와 정합**한가? 죽은 참조/누락 import 없나.
- 이 변경들이 점수 정의를 바꿨다면 **트렌드 비교가 사과-오렌지**가 되는지 평가.

### H. 엣지/조용한 실패
- 변주 GT 상속(`base_source`: `1-1.jpg`→`1.jpg`) 정확성. 미지 base 변주가 조용히 채점되지 않나.
- excluded 샘플(`2.pdf`: GT/이미지 없음) 처리. pending_gt 탐지.
- 0행/빈 추출의 분모 처리. 유니코드/공백 정규화 경계.

## 5. 불변식 카탈로그 (반드시 성립해야 함)

checker가 이미 단언하는 것(여기서 *추가로* 깨지는 경로를 찾을 것):
1. `Σ perField.scored == overall.field.scored`, `Σ perField.match == overall.field.match`
2. `Σ byPath.field.scored == overall.field.scored`
3. `Σ difficultySplit.scored == overall.field.scored`
4. `coverage.gtPresent == overall.scored` 그리고 `coverage.matched == overall.match`
5. `gtPresent == matched + extAttemptedMiss + extNotAttempted + mismatch` (분모 분할)
6. 모든 active 샘플이 `samples/`에 존재 + `status==ok` + `compare/` 파일 존재 (parse-rate 100%)
7. report.md에 "가설" 배너 존재(소표본 정직성 표기)

**추가로 확인할 불변식(checker 미보장 가능):**
- micro·macro가 동일 분모/분자 정의에서 도출되나.
- spurious가 정확도 분모에 **들어가지 않으나** 별도 카운트엔 정확히 1회.
- 표 셀 채점 칸 수 = Σ(행 × 비교대상 열). 행 정렬 실패가 이 칸 수를 왜곡하지 않나.
- free/fallback 합 == ok 샘플 수.

## 6. 산출물(Codex가 낼 것)

`docs/LEARNING_LOOP_AUDIT_REPORT_20260616.md`로 작성. 형식:

1. **요약 판정:** GPU 이전 **GO / NO-GO**, 그리고 NO-GO면 블로커 목록(파일:줄).
2. **발견 표** — 부류별:

   | ID | 영역 | 부류 | 심각도 | 파일:줄 | 관찰/증거 | 권고(수정은 별도) |
   |---|---|---|---|---|---|---|
   (`measurement-bug`/`silent-failure`/`invariant-gap`/`gpu-risk`/`ok`)
3. **불변식 점검 결과:** §5 각 항목 PASS/FAIL + 근거.
4. **GPU 준비성:** F1~F5 결론 + **CPU-캘리브 상수 목록**(F2)이 핵심 산출.
5. **미커밋 6파일 검증 결과**(G).
6. **남은 가설/추가 측정 제안**(소표본이라 단정 못 한 것).

심각도 기준: **Critical**=점수가 틀림/게이트가 결함을 통과시킴 → NO-GO. **High**=GPU에서 측정 흔들림. **Medium**=엣지/조용한 실패. **Low**=문서/표기.

## 7. 스코프 밖 (하지 말 것)
- OCR 인식/전처리 로직 개선, 룰 추가, 보호파일 수정.
- `public/data`·GT·lock 문서·run 산출물 변경.
- 개별 샘플 정답 맞추기(=두더지잡기). 루프 *측정 능력*만 본다.
- 전처리 deskew 각도오판은 **알려진 OCR/전처리 결함**(메모리)이며 루프 버그 아님 — 루프가 그걸 *정확히 계측*하는지만 평가(buckets/preprocess telemetry).

---
_이 브리프는 읽기 전용 감사용이다. 발견을 보고서로 내고, 수정 여부는 사람이 결정한다._
