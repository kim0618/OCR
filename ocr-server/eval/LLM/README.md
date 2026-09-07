# LLM 비교 — Paddle 파이프라인을 VLM 으로 대체했을 때의 차이 측정

하이브리드(2층 보강)가 아니다. **우리가 Paddle 로 만든 것을 VLM 으로 갈아끼우면 얼마나 달라지나**를 잰다.
층 = ①전처리 ②인식 ③파서. **④매칭은 제외** — itemCode·itemNameMaster 는 마스터 DB 산출물이라 ②③의 그림자다.

기준선은 run 072 를 ④ 제외로 재계산한 **cell 46.7%(280,901/602,111) · field 58.7%(61,985/105,531)**.
헤드라인 51.2% 와 비교하지 말 것 — 저울이 다르다.

범위는 회의(2026-09-03)에서 **전처리 + 파서**로 좁혔다. 인식 탭은 보류이고, 재개 조건은 그 둘에서 승자가 나오는 것.

---

## 폴더 구조 — 역할별

### 루트 = 사람이 여는 문서

| 파일 | 역할 |
|---|---|
| `LLM_REVIEW_PLAN.html` | **본 문서.** 탭 = 비용 / 전처리 / 파서 / 인식(보류). 숫자만 담고 실물은 링크로 뺀다 |
| `LLM_SUMMARY.html` | 선행 하이브리드 검토(2026-08-28). 이번 대체 검토와는 별개 문서 |
| `LLM_CASES_REVIVED.html` | 소생 — Base 붕괴 → 모델 정상 |
| `LLM_CASES_REGRESSED.html` | 회귀 — Base 정상 → 모델 붕괴 |
| `LLM_CASES_BOTHFAIL.html` | 양쪽 붕괴 |

`LLM_CASES_*.html` 셋은 지금 **플레이스홀더**다. VLM run 이 끝나면 `eval/llm_cases_report.py` 가 덮어쓴다.
표본만 싣지 않고 부류 전량을 싣는 이유 = 회귀가 12건이냐 300건이냐로 채택이 뒤집히기 때문.

### `inputs/` = 러너·셋업이 먹는 것

| 파일 | 역할 |
|---|---|
| `prompt_v1.md` | 룰 이식 v1. `## SYSTEM` / `## USER` 절을 러너가 파싱. 동의어·보일러플레이트 DROP·헤더스킵·선두순번·빈칸추측 금지 + `full_text` + 스키마. **v2 는 승자 확정 후 + 전량 재실행과만** |
| `sample_500.txt` | 500장 층화표본. `llm_runner --list` 가 받는 **eval/ 기준 이미지 경로**(sourceFile 아님) |
| `smoke_50.txt` | 환경 확정 게이트 50장. 500 밖에서 뽑고 행수 상위 10장 강제 |
| `canned_response.json` | 서버 없이 러너 형식만 검증할 때(`--canned`) |

목록 파일은 **LF 로 쓴다**(AWS 로 건너간다). CRLF 면 경로가 전부 안 맞는 것처럼 보인다.

### `data/` = 채점·분석이 다시 읽는 것

| 파일 | 역할 |
|---|---|
| `groups_072.json` | 9,001 문서 전량의 문서군 라벨 + 전처리 텔레메트리 + Base 셀 점수·붕괴 여부 |
| `sample_500_sources.txt` | 500 표본의 sourceFile — 채점·대조용 |
| `smoke_50_sources.txt` | 스모크 50 의 sourceFile |
| `sample_500_manifest.tsv` | **표본 500 에 무엇이 들어 있나** — 문서군·행수·Base 정확도·붕괴·회전각·경로 (엑셀로 열림) |
| `smoke_50_manifest.tsv` | 스모크 50 의 같은 표 |

**표본 이미지를 따로 복사해 모아두지 않는다.** 실물은 `data/invoice_war/images_replay/` 9,001장이
단일 출처이고 GT 도 전량 하나(`ground_truth_replay.json`)다. 500장만 폴더로 복사하면
사본이 하나 더 생기고(141MB · git 미추적이라 전송 수단도 따로 필요), 무엇보다
**채점 기준이 두 개**가 된다 — 068 목록과 072 기준선이 어긋났던 사고와 같은 형태다.
GT 도 쪼개지 않는다. `compare_run` 은 문서 단위로 전량 GT 와 대조하고 부분 run 은 `--skip-missing` 이 처리한다.
&ldquo;무엇이 들어 있나&rdquo;는 바이트 사본이 아니라 위 manifest 로 읽는다(`eval/llm_manifest.py`).

### `_rehearsal/` = 068→072 리허설. **VLM 이 아니다**

교차 채점기(`compare_cross.py`)와 갤러리 생성기가 실제로 도는지 확인하려고
Paddle run 두 개(068 vs 072)를 맞대본 결과다. 형식 확인용으로만 보고, 수치는 인용하지 말 것.

---

## 실행 순서

실행 스크립트는 다른 운영 스크립트와 같이 `~/OCR/` 에 둔다(`run-eval.sh` · `start-backend.sh` 옆).
`eval/LLM/inputs/` 는 러너가 **먹는 데이터**(프롬프트·목록) 자리이지 스크립트 자리가 아니다.

```
① g6.xlarge 전환 (stop → 타입 변경 → start)   ← T4 로는 8B bf16 이 안 올라간다
② cd ~/OCR && git pull
③ bash ~/OCR/run-vlm-setup.sh qwen           ← 백엔드 자동으로 내림. 스모크는 큐윈 하나면 된다
④ bash ~/OCR/run-vlm-serve.sh qwen           ← tmux 세션 vllm, 뜰 때까지 대기
⑤ bash ~/OCR/run-vlm-smoke.sh qwen           ← A/B 두 번 + 게이트 요약
⑥ 나머지 두 모델 받아 500×3 (+50 재실행 = 결정성) → 로컬 채점 → 승자
⑦ 승자 9,001 본판정
```

| 스크립트 | 하는 일 |
|---|---|
| `~/OCR/vlm-env.sh` | 공통 - nvme 경로 · 모델 repo id · g6/nvme/백엔드 가드. 나머지가 source 한다 |
| `~/OCR/run-vlm-setup.sh` | vLLM venv(nvme, python3.12 별도) + 모델 내려받기. 서버는 안 띄움 |
| `~/OCR/run-vlm-serve.sh` | tmux 세션 `vllm` 으로 기동, 뜰 때까지 폴링. 로그 `~/OCR/logs/vllm.log` |
| `~/OCR/run-vlm-smoke.sh` | 스모크 50 A/B + 게이트 5종 요약(오류 수 · 행수 상위10 · VRAM · 오버헤드 · 소요 역산) |

**Base 는 새로 돌리지 않는다.** 072 가 9,001 전량을 덮으므로 500장의 정확도·`samples/`·`processed/` 는
전부 부분집계로 나오고(`llm_plan_fill.py`), 따로 잴 것은 처리량뿐인데 그건 072 의 2,606장/h 에서 환산한다.
백엔드를 올렸다 내리는 왕복이 사라져 g6 전환 직후 구간이 단순해진다.

승자 기준 = **cell 정확도 1순위, ±3%p 안이면 처리량.**

## 만드는 쪽 스크립트 (`eval/` 바로 아래)

| 스크립트 | 하는 일 |
|---|---|
| `llm_sample_500.py` | 072 samples → 문서군 4분류 + 표본 500 + 스모크 50. 목록은 `inputs/`, 라벨은 `data/` 로 나눠 쓴다 |
| `llm_runner.py` | vLLM 을 돌려 **run_batch 와 같은 레이아웃**으로 저장 → 채점이 기존 경로를 그대로 탄다 |
| `compare_run.py` | run → `compare/`. 부분 run 은 `--skip-missing` |
| `compare_cross.py` | 두 run 의 같은 셀을 맞대어 유지/소생/회귀/양쪽실패 2×2 |
| `llm_cases_report.py` | 부류별 실물 갤러리(카드 = 원본 / Base 전처리 후 / 모델 전처리 후 3장) |
| `llm_plan_fill.py` | **계획서가 필요로 하는 숫자를 전부 계산하고 `--write` 로 채운다** |
| `llm_manifest.py` | 표본에 무엇이 들어 있는지 TSV 한 장으로 (`data/*_manifest.tsv`) |

## run 이 끝나면 - 계획서 채우기

채점은 로컬에서 한다. AWS 에서 받을 것은 `runs/<run>/` 의 `samples/` 와 `run_meta.json` 뿐이다.

```bash
# 1) run -> compare/   (부분 run 은 --skip-missing)
python eval/compare_run.py --ts vlm_qwen_500 --testset invoice_replay --skip-missing

# 2) 계획서 채우기 - 500 스크리닝(후보 3개)
python eval/llm_plan_fill.py --model qwen=vlm_qwen_500     --model minicpm=vlm_minicpm_500 --model internvl=vlm_internvl_500 --write

# 3) 승자 확정 후 - 9,001 본판정 + 교차표
python eval/llm_plan_fill.py --winner qwen=vlm_qwen_9001 --write

# 4) 부류별 실물 갤러리
python eval/compare_cross.py --base runs/072_20260802_182127/compare     --model runs/vlm_qwen_9001/compare --out eval/LLM/data/cases.json
python eval/llm_cases_report.py --kind revived   --cases eval/LLM/data/cases.json
python eval/llm_cases_report.py --kind regressed --cases eval/LLM/data/cases.json
python eval/llm_cases_report.py --kind bothfail  --cases eval/LLM/data/cases.json
```

`llm_plan_fill.py` 가 한 번에 내는 것 - 문서군별 cell 정확도·차이 · 교차 2×2(셀·문서, 문서군별) ·
파서 종합 6지표 · 행 컬럼 8 · 헤더 필드 12 · 처리량/소요/비용/Paddle 대비.
모델이 주어지면 **그 run 이 덮는 문서로 Base 를 다시 집계**하므로 항상 같은 문서·같은 셀에서 비교한다.
`--write` 는 **빈 데이터 칸만** 바꾼다 - 서술과 Base 열은 건드리지 않는다.
열 순서는 `MODEL_ORDER`(qwen · minicpm · internvl)로 고정이라 CLI 입력 순서와 무관하다.

## 저울 규칙 (전 실험 공통)

- ④ 컬럼 제외 · 숫자 GT 는 산술앵커 통과 행만 · 크롭 문맥 금지 · 학습에 쓴 크롭 채점 금지
- spurious(환각) = GT 빈칸을 채운 것 · 결정성(같은 입력 2회 완전일치)은 필수 칸
- 문서 붕괴 임계 = cell 10%, 민감도로 5·20% 병기
- 셀 신원 = **(rowIndex, 등장 순번, 컬럼)**. pos 를 쓰면 교차에서 어긋나고 rowIndex 만 쓰면 중복이 덮어써진다
