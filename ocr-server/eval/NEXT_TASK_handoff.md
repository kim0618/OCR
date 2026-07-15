# 다음 작업 핸드오프 — invoice_statement free/fallback 회수 루프

_작성 2026-06-17. 직전 세션(Claude) 연속용. 이 문서만으로 이어서 진행 가능하도록 자족 기술._

## 0. 한 줄 요약

거래명세서(invoice_statement) 비정형 추출의 평가 루프를 돌려 룰을 보강 중.
baseline run = `053_20260617_142725` (필드 64.3% / 셀 74.7%). **방금 3G 게이트 수정을
working tree에 적용(미커밋), 게이트 레벨만 검증됨 → 순 cell 효과를 replay로 채점하는 게
즉시 다음 스텝.**

## 1. 평가 루프 작동 방식 (필수 이해)

- 위치: `ocr-server/eval/`. run 결과 = `eval/runs/<ts>/<testset>/`.
- **스냅샷 replay = 디바이스 무관 "파서 진실".** run이 이미지별 OCR 입력 envelope를
  `runs/<ts>/study/snapshots/<img>.json`에 얼려둠. 파서를 재-OCR 없이 재실행 가능.
  파서는 GPU/CPU 어디서든 동일 CPU 코드 → **여기서 본 parser 결론은 GPU 프로덕션에 그대로
  전이됨.** "GPU 가서 확인/고치자"로 미루지 말 것(검출 server_det는 이미 검증→무효).
- 로컬 루프 (재-OCR/서버/AWS 불요) — **이 두 개만 돌리면 됨**:
  ```
  cd ocr-server
  .\.venv\Scripts\python.exe eval\replay_compare.py --ts 053_20260617_142725/study
  .\.venv\Scripts\python.exe eval\parser_drop_classify.py --compare-dir replay_compare
  ```
  → `PARSER_DROP_CLASSIFY_replay_compare.html`(브라우저로 봄). parser_drop_classify가
  HTML 쓴 직후 `replay_summary.append_history`로 **이번 KPI를 영구 로그
  `runs/<ts>/study/replay_history.json`에 한 줄 추가(변화 있을 때만)** 하고 누적 표를 HTML
  상단에 주입(셀%/필드%/parser_drop/spurious/Δ). git/커밋 무관 — **돌릴 때마다 자동 누적.**
  로그가 없으면 최초 1회만 git 과거 커밋에서 시드. 별도 명령 불필요. `replay_history.json`은
  커밋해두면 이력 보존됨.
  → `runs/053.../study/replay_compare/<img>.json` (수정 파서 재채점, GT 대비 compare 스키마)
  → `PARSER_DROP_CLASSIFY_replay_compare.{md,json,html}` (결함 분류). 둘 다 사이드카(읽기전용,
  checker 무영향). `.html`을 브라우저로 보면 KPI+샘플별점수+부류×패턴.
- **결함 분류 용어:** parser_drop = GT값이 OCR출력에 실재(회수가능) / recognition = OCR이
  글자 자체를 못 읽음(OCR바운드). 패턴 drop(통째누락)/mislocate(엉뚱컬럼)/wrongpick(다른토큰선택).
- 경로: free(비정형 룰 파서, `invoice_statement_free.py`) / fallback(`invoice_statement.py`,
  free 게이트 탈락 시). 셀 정확도 free 84.5% >> fallback 40.5%. **18/24장이 fallback.**

## 2. 실행 규약 (중요)

- **스크립트/서버/eval run은 사용자가 직접 실행.** 에이전트는 코드 수정 + 커맨드 준비만.
  (단, free 단독 read-only 진단 `python -c`로 파서 import해 돌리는 건 분석 용도로 허용됨.)
- `.venv` 자동 사용, `pip install` 제안 금지.
- 기능 게이트에 env 플래그 금지 — doc-type 등 코드 게이트로 바로 켜라.
- 모델/fine-tune/KIE 얘기 금지(직접 물을 때만). **룰 보강만.**
- `main.py`도 이제 **정상 커밋/push 대상**(2026-07-14~). cpu/gpu 분기는 `runtime_config.py`
  단일 파일에만 격리돼 있어(main.py 는 `RT.DEVICE` 참조만) main.py push 가 AWS 와 안 부딪힘.
  divergence 관리가 필요한 파일은 `runtime_config.py` 뿐.
- AWS는 하루치 모아 1회 push → GPU run으로 일괄 스케일 검증. micro-edit마다 GPU 불요.

## 3. 완료된 작업

### P1 (커밋+푸시 완료) — `extractors/invoice_statement.py`
fallback 캐노니컬 빌더가 `itemCode`만 출력하고 `productCode`를 안 냄(eval/free 계약은
productCode). 각도변주는 코드토큰을 spec으로 오배정. 수정:
- `_TABLE_ROW_COLUMNS` + `_empty_table_row`에 `productCode` 추가.
- 헬퍼 `_fb_looks_like_product_code` / `_fb_normalize_product_code`.
- `_build_canonical_table_rows` 루프에 승격 블록(itemCode 미러, 아니면 spec→productCode + spec clear).
- replay 결과: 셀 779→791/1043, productCode drop 21→10, spec spurious 9→1, 회귀0.

### 3G (working tree, **미커밋**, 게이트 레벨만 검증) — `extractors/invoice_statement_free.py`
**문제:** 5-1/5-2/5-3(공급자5 각도변주)에서 free가 행 6개를 제대로 생성(itemName 100%,
amount 100%, unitPrice 100%, 금액합이 문서 totalAmount와 정확히 일치)하는데, **quantity
parseable 67%** 하나 때문에 `_evaluate_release_threshold`가 `fallbackRequired=True`로 통째
fallback(40% 셀) 강등. 기존 수량-옵셔널 완화(3F, line ~2786)는 **columnar_2d 전략 행에만**
적용 → relaxed_line 산출인 5-x를 못 구함.

**수정 (3곳):**
1. 헬퍼 `_table_amount_sum_reconciles(rows, full_text)` 추가(`_evaluate_release_threshold` 앞).
   행 amount 합 == full_text 내 독립 money 스칼라(±0.5%)면 True. (columnar diag의 ~2442-2461 미러)
2. `_evaluate_release_threshold`에 param `amount_sum_reconciles: bool=False` + **3G 분기**
   (columnar 3F 블록 직후): columnar 완화 미적용 & amount_sum_reconciles & itemName=1.0 &
   amount=1.0 & unitPrice≥0.8 & no metadata/forbidden & qty_missing≤0.5 → 수량 관련 fail_reason
   3개 제거(3F와 동일 relaxed_ready 재계산). 산술 정합이 안전망(columnar의 confidence 대체).
3. 호출부(line ~3586): `release_amount_reconciles = _table_amount_sum_reconciles(table_rows, source_text)`
   계산해 param 전달.

**게이트 검증(free 단독, read-only):**
- 5-1/5-2/5-3 → fallbackRequired False, free_valid True (free 승격) ✓
- 3-1/7-1/6-3/6-1/4-2 → 계속 True 강등(쓰레기 오승격 0) ✓ (3-1=은행줄, 7-1=주소줄, 6-3=0행: 금액합 정합 실패)
- 1.jpg/5.pdf/1-1.jpg → free 유지(회귀 0) ✓

## 4. ★ 즉시 다음 스텝 — 3G 순 cell 효과 채점

게이트 결정은 검증됨. **하지만 free의 5-x 출력은 itemName에 productCode가 붙고
(`두피나액30ML DPNL30M`) spec에 노이즈가 있음**(free 경로 컬럼 분리가 P1만큼 깔끔치 않음).
승격이 순이득(행·금액 회복)인지 일부 상쇄(itemName/spec 분리 품질)인지 **full 채점 필요.**

실행:
```
cd ocr-server
.\.venv\Scripts\python.exe eval\replay_compare.py --ts 053_20260617_142725/study
.\.venv\Scripts\python.exe eval\parser_drop_classify.py --compare-dir replay_compare
```
확인:
1. 5-1/5-2/5-3 경로 fallback→free, 셀 정확도 상승(현재 53/60/57%).
2. 전체 셀 74.7%에서 상승, 회귀 0(1.jpg/5.pdf 등 기존 free 불변).
3. spurious 미상승.

**결정 게이트:**
- 순이득 & 무회귀 → **3G 커밋**(invoice_statement_free.py). 메시지 예:
  `fix(invoice/free): 비-columnar 수량-옵셔널 릴리스(3G) — 금액합 정합 게이트로 공급자5 각도변주 free 잔류`
- free의 itemName/spec 분리가 깎아먹으면 → **후속 작업 A**(아래).

## 5. 후속 작업 (우선순위)

### A. free 경로 productCode/spec 분리 (3G가 itemName/spec로 손실 시)
free 5-x 행: row1 `itemName='두피나액30ML DPNL30M'`(productCode glued), `spec='L0Q'`;
row2 `itemName='노루모에이스산250G캔 O'`, `spec='INAP250G'`(productCode가 spec에). free 경로엔
P1식 분리가 부분만 있음(`invoice_statement_free.py` line ~3150 `_normalize_success_table_rows`에
spec→productCode 승격 존재하나 itemName glued는 미처리). itemName 꼬리의 productCode 토큰 분리 +
spec 노이즈 정리 = 명확한 후속.

### B. 약품명 마스터 사전 교정 (최대 단일 레버, **데이터 게이트**)
itemName 결함 91건 중 **ed≤2 = 57건**(예: `헥사메딘액`→`핵사메단액`, `아젭틴정`→`아집틴청`).
알려진 약품명에서 1~2글자 빗나감 → 외부 마스터(고객 품목 카탈로그 / 공개 의약품 DB)에 fuzzy
대조하면 회수. **GT 파생 사전은 순환 과적합이라 금지.** 룰(CPU, replay 검증 가능). 마스터 소스
확보 여부가 블로커 → 사용자에게 확인 필요.

### C. 나머지 free 강등 케이스
- 6-3: free 0행(tableDetected=N) — free 테이블 검출이 이 레이아웃을 못 잡음.
- 3-1/7-1: free가 은행/주소 줄을 표 행으로 오인(table 영역 오검출). 둘 다 free 검출 개선 영역.

### 손대지 말 것 (측정상 plateau/천장)
- warp-scatter(6-1: 코드/품명/lot이 다른 y밴드로 전단) = 각도 기하, CPU=과적합·GPU도 무효.
- recognition ed≥3 garbled(~24 itemName) = 저해상(950px) 글자 천장. 표-크롭 재OCR(서버 재OCR=AWS) 영역.
- 24장은 **probe**(수천장 전 시스템 유효성 가늠용)지 완벽보정 대상 아님. per-case 두더지잡기 금지.

## 6. 핵심 파일·심볼

- `extractors/invoice_statement_free.py`
  - `_evaluate_release_threshold` (~2730): 릴리스 게이트(fallbackRequired 결정). rules 임계값
    `minQuantityParseableRatio=0.7`, `smallTableMinReleaseReadyRatio=0.99`. 3F(columnar)/3G(비-columnar) 완화.
  - `_table_amount_sum_reconciles` (신규): 금액합 정합 안전망.
  - `_is_valid_invoice_statement_free_result` (~3130): 최종 게이트(fallbackRequired is False 등).
  - `extract_invoice_statement_free` (~3530): 진입점. 호출부 release 평가 ~3586.
- `extractors/invoice_statement.py` (fallback)
  - `_build_canonical_table_rows` (~6490): P1 productCode 승격 위치.
  - `_TABLE_ROW_COLUMNS` / `_empty_table_row`: 캐노니컬 컬럼(P1로 productCode 추가됨).
- `eval/replay_compare.py` / `eval/parser_drop_classify.py`: 로컬 루프.
- baseline: `eval/runs/053_20260617_142725/study/` (snapshots/, compare/, replay_compare/, PARSER_DROP_CLASSIFY*).

## 7. free 단독 진단 스니펫 (게이트 거동 빠른 확인)

```python
import sys, json
sys.path.insert(0, '.')  # run from ocr-server/
from extractors.invoice_statement_free import extract_invoice_statement_free
RUN = 'eval/runs/053_20260617_142725/study/snapshots'
def deser(s):
    out = []
    for r in (s or []):
        try: out.append((r[0], r[1], r[2]))
        except Exception: pass
    return out
def run(img):
    snap = json.load(open(f'{RUN}/{img}.json', encoding='utf-8'))
    sz = snap.get('image_size') or [0, 0]
    return extract_invoice_statement_free(
        ocr_lines_raw=deser(snap.get('ocr_lines_raw')), full_text=snap.get('full_text', ''),
        image_size=(int(sz[0]), int(sz[1])), doc_type=snap.get('doc_type', 'invoice_statement'),
        context=snap.get('context') or {})
# res['tableMeta']['fallbackRequired'], res['tableRows']
```
