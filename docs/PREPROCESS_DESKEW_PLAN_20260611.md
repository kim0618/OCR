# 전처리 deskew 안정화 계획 (2026-06-11 핸드오프)

> 새 채팅방 인수인계용 자기완결 문서. 이 문서 + `OCR/CLAUDE.md` + 메모리(`project_preprocess_image_deskew_gap`, `project_learn_loop_infra_plan`, `feedback_user_runs_not_me`)만으로 P0부터 실행 가능.

## 0. 한 줄 목표
각도로 찍은 거래명세서 사진(변주)이 전처리에서 안 펴져 표가 깨지는 문제를, **deskew 각도검출을 고쳐 24장에서 안정화**한 뒤 실데이터(수천장)로 진행한다. 전처리 안 잡고 실데이터 흘리면 오류가 전처리 잡음에 묻혀 파서/인식 신호를 못 읽음.

## 1. 작업 규칙 (반드시)
- **실행은 사용자가 한다.** 서버 기동·`run_all`·스크립트 실행 전부 사용자 몫. AI는 코드/도구 준비 + 복붙 명령만 제공. (메모리 `feedback_user_runs_not_me`)
- **분석=우선순위로 정리해 추천**, 선택지 떠넘기지 말 것. 원시건수 함정 제거(인식오류는 OCR모델=룰대상 아님). (메모리 `feedback_analysis_prioritize`)
- **측정 우선, 소표본=가설.** 게이트 달린 단계별 플랜을 함께 잠그고 시작. (메모리 `feedback_planning_style`, `feedback_eval_loop_probe_not_perfect`)
- deskew/orientation = **보호로직**(CLAUDE.md Do-Not-Modify). 변경은 명시 게이트 + over-apply 가드 + base 무회귀. deskew 함수 알고리즘/threshold(0.5)는 그동안 불변으로 지켜옴 → **내부 수정보다 각도소스 교체로 우회.**
- 코드=`ocr-server/eval/`(측정) + `ocr-server/`(운영). 결과=`runs/`. `public/data`·OCR 인식 무수정. 편집 전 `ocr-server/backup/`에 타임스탬프 백업.

## 2. 근본원인 (run 006 24장, 확정)
각도 변주 JPG에서 표 숫자가 행을 넘나들며 깨짐(예: 5-2.jpg `quantity="100 400,000"`에서 400,000은 다음 행 값). 파서가 아니라 **전처리 기하 미보정**이 뿌리.

**메커니즘 (`main.py` 2438~2502 확인):**
- deskew()는 **이미지에도 실행됨**(2440 `deskew(doc_img)`).
- 변주 전부 `deskew applied=false, normalizedAngle=0.0` → **기울기 0°로 오측정하고 스킵.** 코드 주석(2470): "deskew()의 minAreaRect 각도가 **표/테두리에 락온**". 각도검출이 표 테두리에 락온돼 기운 사진을 0°로 오판.
- `fileType=="image"→"image_not_target"`(2455)은 deskew 실행이 아니라 **over-apply 되돌림 가드(PDF 전용, 3O산물)** 분기일 뿐. PDF/이미지 구분은 본질 아님(PDF도 비트맵 렌더 후 OCR).

**측정 split (오류 419건):** 룰대상(OCR읽음)170 / OCR바닥(안읽음)249. 숫자컬럼(수량34·단가16·금액16)=룰대상이나 뿌리는 전처리. itemName(바닥75)·주소·대표자·사업자번호=OCR바닥=룰 불가. (스크립트 `OCR/tmp/rule_vs_ocrfloor_split_006.py`)

## 3. 베이스라인
- **run `006_20260611_144308`** = 24장(base 6 + 변주 18) 기준점. study 필드 42.6% / 셀 72.3%, thin(canned) 67.6%/89.5%.
- base 6장은 정상(5.pdf 셀 96.7%, 1.jpg 94.3%). 변주가 평균을 끌어내림 = 전처리 문제.
- run 006의 checker FAIL은 **옛 "6장 기대" 게이트 버그였을 뿐 수치엔 영향 없음** → 아래 4번에서 수정 완료. 재실행하면 PASS.

## 4. 이번 세션에 끝낸 것 (eval 하니스, 재실행 대기)
변경 파일(`ocr-server/eval/`, 측정 전용. 백업=`backup/*_20260611_before_variant_gate_and_timing.py`, `*_before_variant_pairing.py`):
- `build_manifest.py`: 변주(`<base>-<N>.<ext>`)가 base GT 상속하도록 페어링. 변주 패턴 SSOT=`contract._VARIANT_RE`. (qualityTags 미부여 — 추측 금지)
- `contract.py`: `base_source()`, `expected_active_sources()`(base+변주) 추가.
- `phase1/2/3_check.py`: "6장 고정" 점검 → `expected_active_sources()`(동적 24)로. base 6은 회귀 앵커로 유지.
- `run_all.py`: 데이터셋별+배치 wall-clock 측정 → 종합보고서(SUMMARY.md/html)에 "소요 시간" 컬럼+헤더 추가.
- 검증: 컴파일 OK, `expected_active_sources()`=24, manifest active=24. **단, 깨끗한 재실행(checker PASS 확인)은 아직 안 함.**

→ **새 방 첫 실행(사용자):** 서버 띄우고 `cd D:\Free_Vue\OCR\ocr-server; .\.venv\Scripts\python.exe eval\run_all.py --all` → study checker PASS + SUMMARY 소요시간 확인. 이게 깨끗한 24장 baseline.

## 5. 게이트 플랜 (P1 삭제됨, 잠금 대기)
- **P0 — 계측 (AI 준비 / 사용자 실행):** 변주별 ① deskew가 왜 0° 냈나(테두리 락온 확인) ② OCR 토큰 baseline로 잰 **진짜 기울기/원근** ③ 잔여tilt ↔ 셀정확도 상관. **Gate:** 상관 확인 = "전처리가 원인" 정량 확정.
- ~~P1 각도 GT 라벨~~ **삭제** — 기준=base 정립, 이미 셀-vs-base로 채점됨. 새 라벨 불필요.
- **P2 — 실패 특정:** deskew 각도검출 테두리 락온 / over-apply 가드 PDF전용. **Gate:** 실패 버킷·빈도.
- **P3 — 최소 패치 (한 번에 하나, 보호로직 우회):** deskew **각도소스를 토큰 baseline 기반**으로(테두리 락온 회피) + over-apply 가드 **PDF/이미지 통일**. deskew 함수 코어 불변. **Gate(이중):** base 6 무회귀 ∧ 변주 잔여tilt↓.
- **P4 — 24장 재측정 (사용자 실행):** `run_all --all` → trend가 006 대비 델타. 전처리 버킷↓·변주 셀↑·base 무변화. **Gate:** 변주 개선 ∧ base 회귀 0 = 전처리 안정화 완료.
- **P5 — 실데이터:** 24장 안정 확인 후 수천장(100레이아웃×각도) 진행. 파서 룰(170건)은 전처리 안정 후 재평가(상당수 자동 소멸 예상).

## 6. 핵심 경로
- 전처리/deskew: `ocr-server/main.py` 2438~2502 (deskew 호출+정책), `ocr-server/preprocess.py`(`deskew`, `measure_skew_angle`, `detect_orientation` — main.py:19 import)
- eval 하니스: `ocr-server/eval/` (`run_all.py`, `build_manifest.py`, `contract.py`, `phase[1-4]_check.py`, `checker.py`, `metrics.py`, `report.py`, `trend.py`)
- 베이스라인 결과: `ocr-server/eval/runs/006_20260611_144308/`
- 테스트셋: `mysuit-ocr/public/data/testsets/invoice_study/` (base 6 + 변주 18 `{1,3,4,5,6,7}-{1,2,3}.jpg` + `GT/`)
- 서버: 9099 (`.venv\Scripts\python.exe main.py`), 추출엔드포인트 `/ocr/extract`
- 분석 스크립트: `OCR/tmp/rule_vs_ocrfloor_split_006.py`

## 7. 새 방 시작법
1. 이 문서 + `OCR/CLAUDE.md` + 메모리 읽기.
2. (선택) 사용자가 `run_all --all` 한 번 돌려 4번 게이트수정 반영된 **깨끗한 baseline** 확보.
3. **P5 플랜 잠그기** → P0 계측 도구 AI 준비 → 사용자 실행 → 결과로 P2~P4 진행.
