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
| `setup_vllm_nvme.sh` | g6 전환 후 vLLM venv + 모델 3개를 `/opt/dlami/nvme` 에 올린다 |

목록 파일은 **LF 로 쓴다**(AWS 로 건너간다). CRLF 면 경로가 전부 안 맞는 것처럼 보인다.

### `data/` = 채점·분석이 다시 읽는 것

| 파일 | 역할 |
|---|---|
| `groups_072.json` | 9,001 문서 전량의 문서군 라벨 + 전처리 텔레메트리 + Base 셀 점수·붕괴 여부 |
| `sample_500_sources.txt` | 500 표본의 sourceFile — 채점·대조용 |
| `smoke_50_sources.txt` | 스모크 50 의 sourceFile |

### `_rehearsal/` = 068→072 리허설. **VLM 이 아니다**

교차 채점기(`compare_cross.py`)와 갤러리 생성기가 실제로 도는지 확인하려고
Paddle run 두 개(068 vs 072)를 맞대본 결과다. 형식 확인용으로만 보고, 수치는 인용하지 말 것.

---

## 실행 순서

```
① g6.xlarge 전환 (stop → 타입 변경 → start)     ← T4 로는 8B bf16 이 안 올라간다
② git pull
③ 백엔드 내리기 (fuser -k 9099/tcp)              ← RAM 15G, vLLM 과 동시 기동은 행업
④ bash eval/LLM/inputs/setup_vllm_nvme.sh
⑤ 스모크 50 — 게이트 5종 + full_text A/B
⑥ 500×3 모델 (+50 재실행 = 결정성) → 로컬 채점 → 승자
⑦ 승자 9,001 본판정
```

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

## 저울 규칙 (전 실험 공통)

- ④ 컬럼 제외 · 숫자 GT 는 산술앵커 통과 행만 · 크롭 문맥 금지 · 학습에 쓴 크롭 채점 금지
- spurious(환각) = GT 빈칸을 채운 것 · 결정성(같은 입력 2회 완전일치)은 필수 칸
- 문서 붕괴 임계 = cell 10%, 민감도로 5·20% 병기
- 셀 신원 = **(rowIndex, 등장 순번, 컬럼)**. pos 를 쓰면 교차에서 어긋나고 rowIndex 만 쓰면 중복이 덮어써진다
