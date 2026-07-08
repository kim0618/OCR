"""finetune_progress — PaddleX 학습 로그를 왼쪽 '진행/전체' 카운터로 정리.

장황한 PaddleX 학습 줄을 파이프로 받아, 진행 줄만 깔끔하게 바꿔 출력한다:
  [  1,234/  8,832  14%] ep 2/8  loss 0.42  acc 0.780  eta 1:23:45
전체 = epoch당 iter × 총 epoch. 진행이 아닌 줄(다운로드/평가결과/에러)은 그대로 통과.

    # 지금 도는 학습 실시간으로 깔끔히 보기 (재시작 불필요):
    tail -f ~/OCR/logs/finetune.log | .venv/bin/python eval/finetune_progress.py
    # run-finetune.sh 는 train 출력을 이걸로 통과시켜 로그 자체가 깔끔해짐.
"""
import re
import sys

RE_IPE = re.compile(r"train dataloader has (\d+) iters")
RE_STEP = re.compile(r"epoch: \[(\d+)/(\d+)\].*?global_step: (\d+)")
RE_ACC = re.compile(r" acc: ([\d.]+)")
RE_LOSS = re.compile(r" loss: ([\d.]+)")
RE_ETA = re.compile(r"eta: ([\d:]+)")


def _f(rx, line, default="?"):
    m = rx.search(line)
    return m.group(1) if m else default


def main() -> int:
    ipe = None  # iters per epoch
    for line in sys.stdin:
        line = line.rstrip("\n")
        m = RE_IPE.search(line)
        if m:
            ipe = int(m.group(1))
            print(f"  (epoch당 {ipe:,} step)")
            sys.stdout.flush()
            continue
        m = RE_STEP.search(line)
        if m:
            ep, tot_ep, step = int(m.group(1)), int(m.group(2)), int(m.group(3))
            loss, acc, eta = _f(RE_LOSS, line), _f(RE_ACC, line), _f(RE_ETA, line)
            if ipe:
                overall = (ep - 1) * ipe + step
                total = tot_ep * ipe
                pct = 100.0 * overall / total if total else 0.0
                print(f"[{overall:>8,}/{total:<8,} {pct:4.1f}%] ep {ep}/{tot_ep}  "
                      f"loss {loss}  acc {acc}  eta {eta}")
            else:
                print(f"[ep {ep}/{tot_ep} step {step:>6}]  loss {loss}  acc {acc}  eta {eta}")
            sys.stdout.flush()
            continue
        print(line)  # 진행 아닌 줄(다운로드·평가·에러)은 그대로
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
