"""잃어버림(①) 크롭에서 <실제로 깨진 글자> 목록을 뽑아 앵커 겨냥 선발의 입력으로 만든다.

왜 글자 단위인가 (2026-08-10 실측):
  앵커 구성을 '순수한글 크롭 비율' 같은 크롭 단위 지표로 잡으면 잘못 센다 —
  `로수반정10mg` 은 '영문+숫자 혼재' 로 분류되지만 한글을 5자 담고 있다.
  548 손실의 한글 오독은 롱테일이라(최다 혼동쌍이 8건) 층 비율이 아니라
  <그 글자를 앵커에서 몇 번 보여줬나>가 실제 방어력이다.
  현행 8,016 앵커는 깨진 한글 106종 중 14종을 <한 번도> 안 보여주고 있었다.

출력: target_chars_<tag>.json — 한글/영문/숫자별 [글자, 깨진횟수] 목록.
      build_demo_dataset.py --anchor-target-chars 가 이 파일을 읽는다.

    python eval/finetune/demo/build_target_chars.py                 # 기본 태그
    python eval/finetune/demo/build_target_chars.py 260807_1302
"""
from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from recount_reviewed_gt import (  # noqa: E402
    HERE, comparable, load_policy, load_scan, name_key,
)

# 앵커 겨냥에서 제외할 글자. ㈜ 는 품명 정답풀에 10장뿐이라(2026-08-10 AWS 실측)
# 앵커로 덮을 수 없다 — 후처리 몫으로 넘긴다. 여기 넣어두면 겨냥 선발이 헛돌지 않는다.
EXCLUDE = {"주", "유"}
DEFAULT_TAG = "260807_1302"


def edit_ops(gt: str, pred: str) -> list[tuple[str, str, str]]:
    """comparable 문자열 간 최소 편집 연산. (kind, gt글자, pred글자)."""
    a, b = comparable(gt), comparable(pred)
    n, m = len(a), len(b)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    out: list[tuple[str, str, str]] = []
    i, j = n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] and a[i - 1] == b[j - 1]:
            i, j = i - 1, j - 1
        elif i and j and d[i][j] == d[i - 1][j - 1] + 1:
            out.append(("sub", a[i - 1], b[j - 1])); i, j = i - 1, j - 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            out.append(("del", a[i - 1], "")); i -= 1
        else:
            out.append(("ins", "", b[j - 1])); j -= 1
    return out[::-1]


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TAG
    keep = {
        line.strip()
        for line in (HERE / "basis_keep.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    overrides, excluded_names, _ = load_policy()
    base = load_scan("000_base.jsonl", keep)
    cur = load_scan(f"{tag}.jsonl", keep)

    hangul, english, digit = Counter(), Counter(), Counter()
    lost = 0
    for path, brow in base.items():
        key = name_key(brow["gt"])
        if key in excluded_names or path not in cur:
            continue
        gt = overrides.get(key, brow["gt"])
        # ① 잃어버림 = base 가 맞게 읽던 크롭을 이 모델이 틀린 것
        if comparable(gt) != comparable(brow["pred"]):
            continue
        if comparable(gt) == comparable(cur[path]["pred"]):
            continue
        lost += 1
        for kind, g, p in edit_ops(gt, cur[path]["pred"]):
            # 삽입(모델이 없는 글자를 넣음)은 '보여줘야 할 글자'가 아니다.
            ch = g if kind in ("sub", "del") else ""
            if not ch or ch in EXCLUDE:
                continue
            if "가" <= ch <= "힣":
                hangul[ch] += 1
            elif ch.isascii() and ch.isalpha():
                english[ch] += 1
            elif ch.isdigit():
                digit[ch] += 1

    payload = {
        "schemaVersion": "demo-anchor-target-chars.v1",
        "sourceRun": tag,
        "lostCrops": lost,
        "excludedChars": sorted(EXCLUDE),
        "note": "① 잃어버림 크롭의 편집연산에서 <GT 쪽 글자>만 모은 것. "
                "앵커가 이 글자들을 충분히 보여주고 있는지가 방어력의 실측 지표.",
        "chars": {
            "hangul": hangul.most_common(),
            "english": english.most_common(),
            "digit": digit.most_common(),
        },
    }
    out = HERE / f"target_chars_{tag}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    print(f"wrote {out}")
    print(f"  잃어버림 {lost}크롭 → 깨진 글자 한글 {len(hangul)}종 / "
          f"영문 {len(english)}종 / 숫자 {len(digit)}종")
    print(f"  한글 상위: {hangul.most_common(12)}")
    print(f"  영문 상위: {english.most_common(8)}")


if __name__ == "__main__":
    main()
