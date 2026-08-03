# -*- coding: utf-8 -*-
"""demo_report/demo_summary 샘플 생성 — 실제 실행 시 나올 HTML 미리보기.

만드는 것(모두 eval/finetune/demo/samples/):
  DEMO_REPORT_1차_1단계_샘플.html   base 가 못 읽던 품명 1개 소생
  DEMO_REPORT_1차_2단계_샘플.html   + 잃어버린 품명 1개 회수 = 1차 완료(누적 2개)
  DEMO_REPORT_2차_1단계_샘플.html   ★1차 모델 위에서 시작 - 그 모델이 못 읽는 품명 소생
  DEMO_REPORT_2차_2단계_샘플.html   + 잃어버린 품명 회수 = 2차 완료(누적 4개)
  DEMO_SUMMARY_샘플.html            회차 탭 종합(요약·1·2차 채움 / 3·4차 예정)

실데이터: 타깃 선정 근거는 최신 기준셋 리플레이(9,001장) 실집계 그대로.
가데이터: 아직 학습을 안 돌렸으므로 판정용 크롭 예측(base/FT)은 예상 시나리오,
          크롭 이미지도 글자 렌더로 대체(모양만).
"""
import json, os, sys, glob, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# 가짜 코퍼스/예측은 레포에 남기지 않는다(임시 폴더). 산출물은 demo/samples/ 만.
SCRATCH = tempfile.mkdtemp(prefix="demo_report_sample_")
FAKE = os.path.join(SCRATCH, "sample_corpus")
os.makedirs(os.path.join(FAKE, "crops"), exist_ok=True)
os.makedirs(os.path.join(FAKE, "dataset"), exist_ok=True)
OUT_DIR = os.path.join(HERE, "finetune", "demo", "samples")
os.makedirs(OUT_DIR, exist_ok=True)

sys.path.insert(0, HERE)
import demo_report as dr

TARGET = "디아세렌캡슐"
# 선정 근거는 실데이터 — eval/runs 의 최신 기준셋 리플레이(없으면 demo_report 가 스킵)
REPLAY = dr._latest_replay_run() or ""

from PIL import Image, ImageDraw, ImageFont

hits = []
for fp in (glob.glob(os.path.join(REPLAY, "compare", "*.json")) if REPLAY else []):
    try:
        j = json.load(open(fp, encoding="utf-8"))
    except Exception:
        continue
    for r in (j.get("table") or {}).get("rows") or []:
        c = (r.get("cells") or {}).get("itemName")
        if c and TARGET in (c.get("gtNorm") or "").replace(" ", ""):
            hits.append((j.get("sourceFile"), c.get("gt"), c.get("ext")))
            break
print(f"타깃 문서 {len(hits)}건 — 상위 3건: {hits[:3]}")

# compare 에는 bbox 가 없으므로, 샘플 크롭은 텍스트 렌더로 대체(모양만 제시)
def make_crop(path, text, w=200, h=34):
    img = Image.new("RGB", (w, h), (252, 252, 252))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("malgun.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    d.rectangle([0, 0, w - 1, h - 1], outline=(200, 208, 216))
    d.text((8, 7), text, fill=(28, 32, 38), font=font)
    img.save(path, "JPEG", quality=92)

# 모델 체인 시나리오 — 단계마다 바로 앞 모델 위에서 이어 학습(트리 줄기).
#   base → m1(디아세렌캡슐) → m2(+세파클러캡슐250mg) = 1차 완료(누적 2)
#        → m3(+비탁스캡슐) → m4(+앤틱스캡슐) = 2차 완료(누적 4)
#
# ★판정 크롭 수·오독 문자열은 072 기준셋(9,001장) 실측이다(demo_target_basis.py):
#     디아세렌캡슐      18셀/16문서  base 오독 18 ("디아세렌캡슬" 18)
#     세파클러캡슐250mg 24셀/24문서  base 오독 20 + 누락 4
#     비탁스캡슐        16셀/12문서  base 오독 16
#     앤틱스캡슐        13셀/11문서  base 오독 13
#   전부 base 정답 0 = "한 번도 못 읽던 품명".
#   ★학습 크롭 수는 코퍼스(AWS)에만 있어 로컬에서 셀 수 없다 → 샘플에서는 '미측정'.
#     실제 값은 AWS 에서 demo_corpus_count.py 로 세어 채운다.
# 각 항목: (품명, 시작 모델이 낸 오독, 기준셋 판정 셀 수, 크롭 폭)
PLAN = [
    (TARGET, "디아세렌캡슬", 18, 200),
    ("세파클러캡슐250mg", "세파클러캡슬250mg", 24, 250),
    ("비탁스캡슐", "비탁스캡슬", 16, 200),
    ("앤틱스캡슐", "앤틱스캡슬", 13, 200),
]
preds = os.path.join(SCRATCH, "sample_predictions.jsonl")


def _rows_for(names, broken=()):
    """누적 타깃들의 판정 크롭 — 시작 모델은 못 읽고 파인튜닝은 읽는 시나리오.

    broken 에 든 품명은 '이번 학습이 이전 회차 품명을 다시 깨뜨린' 경우 —
    리포트가 그걸 잡아내는지(회차 미완료 경고) 보여주기 위한 시나리오.
    """
    out = []
    for nm in names:
        gt, wrong, n, w = next(x for x in PLAN if x[0] == nm)
        for i in range(n):
            fn = f"{abs(hash(gt)) % 10**8}_{i}.jpg"
            make_crop(os.path.join(FAKE, "crops", fn), gt, w=w)
            ft = wrong if (nm in broken and i == 0) else gt   # 한 장이라도 틀리면 미달
            out.append({"path": f"crops/{fn}", "gt": gt, "base": wrong, "finetuned": ft})
    return out


def _stage(names, broken=()):
    """manifest + 예측 파일을 그 단계 상태로 갱신.

    학습 크롭 관련 수치(targetTrainUnique·oversampledTo·anchor)는 아직 확정 전이라
    일부러 비운다 → 리포트가 '미측정(코퍼스 집계 필요)'으로 표시한다. 판정 크롭 수는
    기준셋 실측(PLAN)에서 나온다.
    """
    rows = _rows_for(names, broken)
    json.dump({"mode": "demo", "targets": list(names),
               "targetCrops": {n: next(x[2] for x in PLAN if x[0] == n) for n in names},
               "counts": {"test": len(rows)},
               "basisNote": "판정 크롭 = 기준셋 9,001 실측 · 학습 크롭 = 코퍼스 집계 전",
               "seed": 20260803},
              open(os.path.join(FAKE, "dataset", "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    with open(preds, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

dr.MANIFEST = os.path.join(FAKE, "dataset", "manifest.json")
dr.CORPUS_DIR = FAKE
dr.PREDICTIONS_JSONL = preds
dr.RUNS_DIR = os.path.join(HERE, "runs")
dr.LATEST_OUT = os.path.join(OUT_DIR, "DEMO_REPORT.html")
dr._demo_run_dir = lambda tag: OUT_DIR
# 샘플은 GPU 추론 없이, 준비해 둔 예측 파일을 그대로 쓴다.
dr._predict_pairs = lambda compare_dir: [json.loads(l) for l in open(preds, encoding="utf-8")
                                         if l.strip()]


# 실행번호는 파일명 안전 문자만 허용(한글은 _report_id 가 제거) → ASCII 태그로 생성 후
# 사람이 알아보기 쉬운 이름으로 옮긴다. compare 인자로 회차 체인(2회차=1회차 모델)을 표현.
def _emit(tag: str, final_name: str, compare_step: int = 0) -> str:
    sys.argv = ["demo_report.py", "--run-tag", tag]
    if compare_step:
        sys.argv += ["--compare-dir", "(sample)", "--compare-step", str(compare_step)]
    dr.main()
    src = os.path.join(OUT_DIR, f"DEMO_REPORT_{tag}.html")
    dst = os.path.join(OUT_DIR, final_name)
    os.replace(src, dst)
    return dst


NAMES = [x[0] for x in PLAN]
# 1회차 — 시작 모델 = official base
_stage(NAMES[:1])
print("1차 1단계:", _emit("SAMPLE_R1S1", "DEMO_REPORT_1차_1단계_샘플.html"))

# ★2번째 모델 1차 시도는 실패 시나리오(새 타깃은 읽었지만 1단계 품명을 잃음).
#   재시도가 '2-1 모델'로 카운트되는 것을 실행 이력 탭에서 보여주기 위함.
_stage(NAMES[:2], broken=(TARGET,))
_emit("SAMPLE_R1S2_FAIL", "DEMO_REPORT_1차_2단계_실패_샘플.html", 1)
_stage(NAMES[:2])
print("1차 2단계:", _emit("SAMPLE_R1S2", "DEMO_REPORT_1차_2단계_샘플.html", 1))

# 2회차 — 시작 모델 = 1회차 결과 모델(이어받기)
#  ★1단계에서 1회차 품명(세파클러캡슐250mg)을 다시 잃는 시나리오를 일부러 넣었다.
#    회차 진행 중에도 이전 것이 깨질 수 있고, 리포트가 그걸 잡아 '미완료'로 표시하는지
#    보여주기 위함. 2단계에서 회복되어 누적 4개로 회차 완료.
_stage(NAMES[:3], broken=("세파클러캡슐250mg",))
print("2차 1단계:", _emit("SAMPLE_R2S1", "DEMO_REPORT_2차_1단계_샘플.html", 2))
_stage(NAMES[:4])
print("2차 2단계:", _emit("SAMPLE_R2S2", "DEMO_REPORT_2차_2단계_샘플.html", 3))
os.remove(os.path.join(OUT_DIR, "DEMO_REPORT.html"))   # 최신본 포인터는 샘플에 불필요

# --- 회차 탭 종합본 샘플 (요약 + 1·2차 채움, 3·4차 '예정') ---
import demo_summary as ds

# 실행 이력의 '학습/AWS 비용' 열은 RUN_HISTORY.jsonl(kind=finetune)에서 온다. 샘플에는
# 그 기록이 없으므로, 실제 실행 시 어떻게 보이는지 알 수 있도록 예시 값을 주입한다.
# (미니셋 학습 ~10분 · g6.xlarge $1.0/h 기준 추정)
_FAKE_HIST = {
    "SAMPLE_R1S1":      {"elapsedSec": 640, "estimatedCostUsd": 0.18, "epochsCompleted": 30,
                         "epochsPlanned": 30, "bestAcc": 0.612},
    "SAMPLE_R1S2_FAIL": {"elapsedSec": 705, "estimatedCostUsd": 0.20, "epochsCompleted": 30,
                         "epochsPlanned": 30, "bestAcc": 0.588},
    "SAMPLE_R1S2":      {"elapsedSec": 1180, "estimatedCostUsd": 0.33, "epochsCompleted": 50,
                         "epochsPlanned": 50, "bestAcc": 0.641},
    "SAMPLE_R2S1":      {"elapsedSec": 812, "estimatedCostUsd": 0.23, "epochsCompleted": 30,
                         "epochsPlanned": 30, "bestAcc": 0.629},
    "SAMPLE_R2S2":      {"elapsedSec": 903, "estimatedCostUsd": 0.25, "epochsCompleted": 30,
                         "epochsPlanned": 30, "bestAcc": 0.655},
}
ds._run_history_index = lambda: _FAKE_HIST

sys.argv = ["demo_summary.py", "--input-dir", OUT_DIR, "--rounds", "4",
            "--out", os.path.join(OUT_DIR, "DEMO_SUMMARY_샘플.html")]
ds.main()
