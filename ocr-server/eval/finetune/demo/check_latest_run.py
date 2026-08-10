"""AWS 최신 데모 run 을 회수해 재집계하고 채택 판정까지 한 번에.

새 세션에서 "24배 확인해" 한마디로 끝나게 하는 진입점이다. 하는 일:
  1) AWS 에서 아직 로컬에 없는 demo/NNN_<태그> 산출물과 스캔을 찾아 내려받는다
  2) recount_reviewed_gt.py 로 재집계(새 스캔은 자동 인식된다)
  3) 기준 모델(BASELINE) 대비 채택 조건 4가지를 표로 찍는다
  4) 기준 모델은 맞고 새 모델이 틀린 <신규 손실> 경로를 파일로 남긴다

    python eval/finetune/demo/check_latest_run.py             # 회수 + 재집계 + 판정
    python eval/finetune/demo/check_latest_run.py --no-fetch  # 로컬 것만으로 판정
    python eval/finetune/demo/check_latest_run.py --baseline 260804_1623

★AWS 가 꺼져 있으면 --no-fetch 로 로컬 상태만 본다. 학습 실행은 사용자가 한다.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# 윈도우 콘솔 기본 코드페이지(cp949)에서 한글이 깨지지 않게 출력만 UTF-8 로 고정한다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HERE = Path(__file__).resolve().parent
OCR_SERVER = HERE.parents[2]
SCANS = HERE / "scans"
RECOUNT = HERE / "GT_REVIEW_RECOUNT.json"
REMOTE = "~/OCR/ocr-server/eval/finetune/demo"

HOST = os.environ.get("OCR_AWS_HOST", "ubuntu@3.37.51.240")
KEY_CANDIDATES = [
    os.environ.get("OCR_AWS_KEY", ""),
    "/tmp/ocr.pem",
    r"C:\Users\jinsung\Desktop\[신규] 프리세일즈\1_OCR\1_키페어\mysuit-ocr.pem",
]
# ★기준 = 결정론 앵커 8,016(48배) 모델(2026-08-10 확정). 새 run 의 채택 여부는
#  이 값(잃음 548 / 되살림 8,278 / 순증 +7,730 / 타깃 26/26)을 넘느냐로 정한다.
#  옛 12배 260804_1623 은 비결정적 단일 관측이라 기준선으로 쓰지 않는다.
BASELINE = "260807_1302"


def _key() -> str:
    for k in KEY_CANDIDATES:
        if k and Path(k).exists():
            return k
    raise SystemExit("SSH 키를 찾지 못했습니다. OCR_AWS_KEY 로 경로를 지정하세요.")


def _ssh(cmd: str, key: str) -> str:
    out = subprocess.run(
        ["ssh", "-i", key, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=25",
         HOST, cmd],
        capture_output=True, text=True, timeout=300,
        encoding="utf-8", errors="replace")
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "ssh 실패")
    return out.stdout


def _scp(remote: str, local: Path, key: str) -> bool:
    local.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["scp", "-i", key, "-o", "StrictHostKeyChecking=no", "-r",
         f"{HOST}:{remote}", str(local)],
        capture_output=True, text=True, timeout=600,
        encoding="utf-8", errors="replace")
    return r.returncode == 0


def fetch() -> list[str]:
    """AWS 에만 있는 run 을 내려받고, 새로 받은 태그 목록을 돌려준다."""
    key = _key()
    remote_runs = _ssh(f"ls -d {REMOTE}/[0-9][0-9][0-9]_* 2>/dev/null || true", key).split()
    local_tags = {Path(p).name.split("_", 1)[1] for p in glob.glob(str(HERE / "[0-9][0-9][0-9]_*"))}
    new: list[str] = []
    for rp in remote_runs:
        folder = rp.rstrip("/").split("/")[-1]
        tag = folder.split("_", 1)[1]
        fetched = False
        if tag not in local_tags:
            print(f"[회수] {folder}")
            if not _scp(f"{REMOTE}/{folder}", HERE / folder, key):
                print(f"  ★리포트 회수 실패: {folder}")
                continue
            fetched = True

        # 한 궤적 에폭 실험은 <tag>_ep08, <tag>_ep12 와 exact ep20인 <tag>를
        # 함께 만든다. 리포트 폴더가 이미 로컬에 있어도 뒤늦게 완료된 스캔은 받아야 한다.
        remote_scans = _ssh(
            f"ls {REMOTE}/scans/{tag}*.jsonl 2>/dev/null || true", key).split()
        for remote_scan in remote_scans:
            name = remote_scan.rsplit("/", 1)[-1]
            if (SCANS / name).exists():
                continue
            if _scp(f"{REMOTE}/scans/{name}", SCANS / name, key):
                print(f"  스캔 {name}")
                fetched = True
            else:
                print(f"  ★스캔 회수 실패: {name}")

        # target 26/26 및 체크포인트 해시는 가중치 전체를 받지 않고 작은 증거 파일만 회수.
        has_epoch_scans = any("_ep" in path.rsplit("/", 1)[-1] for path in remote_scans)
        local_epoch = HERE / folder / "epoch_ladder"
        if has_epoch_scans and _scp(
            f"~/OCR/ocr-server/eval/finetune/versions/run_{tag}/epochs/EPOCH_LADDER.tsv",
            local_epoch / "EPOCH_LADDER.tsv", key):
            for epoch in ("08", "12", "20"):
                _scp(
                    f"~/OCR/ocr-server/eval/finetune/versions/run_{tag}/epochs/"
                    f"epoch_{epoch}/TARGET_EVAL.json",
                    local_epoch / f"epoch_{epoch}_TARGET_EVAL.json", key)
        if fetched:
            new.append(tag)
    if new:
        _scp("~/OCR/ocr-server/eval/RUN_HISTORY.jsonl", OCR_SERVER / "eval", key)
    return new


def recount() -> dict:
    r = subprocess.run([sys.executable, str(HERE / "recount_reviewed_gt.py")],
                       capture_output=True, text=True, cwd=str(OCR_SERVER),
                       encoding="utf-8", errors="replace")
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        raise SystemExit("재집계 실패 - 위 메시지를 확인하세요.")
    subprocess.run([sys.executable, str(OCR_SERVER / "eval" / "demo_summary.py")],
                   capture_output=True, text=True, cwd=str(OCR_SERVER),
                   encoding="utf-8", errors="replace")
    return json.loads(RECOUNT.read_text(encoding="utf-8"))


def judge(data: dict, baseline: str) -> None:
    runs = data["runs"]
    base_run = runs.get(baseline)
    if not base_run:
        raise SystemExit(f"기준 모델 {baseline} 이 재집계에 없습니다.")
    newer = sorted(t for t in runs if t > baseline)
    print(f"\n평가 크롭 {data['evaluatedCrops']:,} · base 정답 {data['baseCorrect']:,}"
          f" ({100 * data['baseCorrect'] / data['evaluatedCrops']:.2f}%)")
    # ★①은 <글자가 틀린 것>만 센다(2026-08-10). 꼬리 기호·행번호 구분자만 다른 몫은
    #  품명 글자를 다 맞게 읽은 것이라 ③(표기만 다름)으로 합산한다. 판정도 이 기준이다.
    def _lost(r: dict) -> int:
        return r.get("lostChar", r["lost"])

    def _nota(r: dict) -> int:
        return r.get("notationOnly", 0) + r.get("lostNotation", 0)

    # run 폴더가 `NNN_<태그>` 라 앞 번호가 곧 버전이다. 태그만으로는 헷갈려서 함께 찍는다.
    def _ver(tag: str) -> str:
        for d in glob.glob(str(HERE / f"*_{tag}")):
            name = Path(d).name.split("_", 1)[0]
            if name.isdigit():
                return f"v{int(name)}"
        return ""

    print(f"{'':<5}{'run':<14}{'정답':>9}{'①잃어버림':>11}{'②못읽음':>10}"
          f"{'③표기만':>10}{'되살림':>9}{'순증':>9}")
    for tag in list(runs):
        r = runs[tag]
        mark = " ←기준" if tag == baseline else (" ←신규" if tag in newer else "")
        print(f"{_ver(tag):<5}{tag:<14}{r['correct']:>9,}{_lost(r):>11,}"
              f"{r.get('unread', 0):>10,}{_nota(r):>10,}{r['revived']:>9,}"
              f"{r['revived'] - _lost(r):>+9,}{mark}")
    if not newer:
        print("\n새 run 이 없습니다. AWS 에서 실행 후 다시 확인하세요.")
        return
    for tag in newer:
        r, b = runs[tag], base_run
        rep = HERE / f"{[Path(p).name for p in glob.glob(str(HERE / f'*_{tag}'))][0]}" \
            if glob.glob(str(HERE / f"*_{tag}")) else None
        passed = None
        if rep:
            j = json.loads(next(rep.glob("DEMO_REPORT_*.json")).read_text(encoding="utf-8"))
            passed = (j.get("summary") or {}).get("allPass")
            tgt = j["targets"][0]["verdict"]
        print(f"\n=== {tag} 채택 판정 (기준 {baseline}) ===")
        # ★채택 조건 3개(2026-08-10 사용자 확정). 되살림·순증은 지표에서 뺐다.
        #  주지표 = 잃어버림(못 읽게 되는 게 계속 생기면 신뢰가 안 된다).
        #  단 '정답 총량 하한'을 같이 둔다 — 그게 없으면 잃어버림 29건 줄이자고
        #  정답 704건을 잃는 교환(260810_1037 실측, 25:1)이 통과해버린다.
        rows = [
            ("타깃 판정 26/26 유지",
             f"{tgt['ft']}/{tgt['n']}" if rep else "?", "-", bool(passed)),
            ("① 잃어버림 감소(글자)", f"{_lost(r):,}", f"{_lost(b):,}",
             _lost(r) < _lost(b)),
            ("전체 정답 유지·증가", f"{r['correct']:,}", f"{b['correct']:,}",
             r["correct"] >= b["correct"]),
        ]
        for name, got, ref, ok in rows:
            print(f"  {'OK ' if ok else '✗  '} {name:<22} {got:>10}   (기준 {ref})")
        allok = all(x[3] for x in rows)
        print(f"  => {'채택 가능' if allok else '조건 미달 - 기준 모델 유지 권장'}")
        nl = HERE / f"NEW_LOSS_{tag}_vs_{baseline}.txt"
        if nl.exists():
            n = len([x for x in nl.read_text(encoding="utf-8").splitlines() if x.strip()])
            print(f"  신규 손실(기준은 맞고 이 모델이 틀림) {n:,}건 -> {nl.name}")
            print("  ★실물 확인 전에는 채택하지 않는다.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true", help="AWS 회수 없이 로컬만")
    ap.add_argument("--baseline", default=BASELINE)
    args = ap.parse_args()
    if not args.no_fetch:
        try:
            got = fetch()
            print(f"[회수] 새 run {len(got)}개" if got else "[회수] 새 run 없음")
        except Exception as exc:                     # AWS 꺼짐 등
            print(f"[회수] 건너뜀 ({exc}) - 로컬 상태로만 판정합니다")
    judge(recount(), args.baseline)


if __name__ == "__main__":
    main()
