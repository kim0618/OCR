"""demo_aa_compare — A/A(같은 설정 2회) run 의 결정성 판정.

성공 기준은 "점수가 비슷하다"가 아니라 <45,356 크롭의 개별 예측이 전부 같다>이다.
점수는 같아도 예측이 다르면 비결정성이 남아 있는 것이고, 그 상태로는
단일 실행 A/B 비교가 성립하지 않는다(2026-08-06 v5→v9 재실행: 잃음 593→718 실측).

    python eval/finetune/demo/demo_aa_compare.py 260806_XXXX 260806_YYYY

판정 출력: 개별 예측 diff 수(0 이어야 성공), 잃어버림/되살림 요약 대조, 표본 diff 목록.
scans/<tag>.jsonl 두 개를 대조하므로 두 run 모두 판정 스캔까지 끝나 있어야 한다
(타깃 26/26 실패로 스캔이 안 돌았으면 demo_report 를 수동 실행해 스캔부터 만들 것).
종료코드: 0=완전 동일, 1=차이 있음, 2=입력 문제.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

HERE = Path(__file__).resolve().parent
SCANS = HERE / "scans"


def comparable(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def load(tag: str) -> dict[str, dict]:
    p = SCANS / f"{tag}.jsonl"
    if not p.exists():
        raise SystemExit(f"스캔이 없습니다: {p}  (판정 통과 후 스캔까지 끝난 run 인지 확인)")
    rows = {}
    for line in p.open(encoding="utf-8"):
        r = json.loads(line)
        rows[r["path"]] = r
    return rows


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    tag_a, tag_b = sys.argv[1], sys.argv[2]
    a, b = load(tag_a), load(tag_b)

    only_a = a.keys() - b.keys()
    only_b = b.keys() - a.keys()
    common = a.keys() & b.keys()
    diff = [p for p in common if comparable(a[p]["pred"]) != comparable(b[p]["pred"])]

    # 요약 지표(정답/오답)도 함께 — diff 0 이면 자동으로 일치하지만, diff>0 일 때
    # "그래도 점수는 얼마나 비슷한가"를 보여줘 원인 탐색의 출발점이 된다.
    ok = lambda r: comparable(r["gt"]) == comparable(r["pred"])
    n_ok_a = sum(1 for p in common if ok(a[p]))
    n_ok_b = sum(1 for p in common if ok(b[p]))

    print(f"A={tag_a}  B={tag_b}")
    print(f"공통 크롭 {len(common):,}  (A에만 {len(only_a)} / B에만 {len(only_b)})")
    print(f"정답 수   A {n_ok_a:,} / B {n_ok_b:,}  (차이 {n_ok_b - n_ok_a:+d})")
    print(f"개별 예측 diff: {len(diff)}")

    if only_a or only_b:
        print("★크롭 집합 자체가 다릅니다 — 스캔 대상이 달랐다는 뜻이라 A/A 가 아닙니다.")
        return 2
    if not diff:
        print("=> 완전 동일. 결정성 확보 — 이후 같은 시드 단일 실행 A/B 비교가 성립합니다.")
        return 0

    print("=> 비결정성 잔존. 표본 20건:")
    for p in diff[:20]:
        print(f"   {p}\t gt={a[p]['gt']!r}\t A={a[p]['pred']!r}\t B={b[p]['pred']!r}")
    print("다음 손잡이: ① num_workers=0 재시도 ② 그래도 다르면 결정성 실패로 판정하고")
    print("            같은 설정 n회 반복(밴드 측정) 방식으로 전환.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
