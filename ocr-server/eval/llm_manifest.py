"""llm_manifest — 표본에 무엇이 들어 있는지 한 장의 표로 낸다.

이미지를 복사해 모아두지 않는 이유: 실물은 `data/invoice_war/images_replay/` 9,001장이
단일 출처이고 GT 도 전량 하나다. 500장만 따로 폴더에 복사하면 사본이 하나 더 생기고
(141MB · git 미추적이라 전송 수단도 따로 필요) 무엇보다 **채점 기준이 두 개**가 된다 -
068 목록과 072 기준선이 어긋났던 사고와 같은 형태다.

필요한 건 바이트 사본이 아니라 "무엇이 들어 있나"를 읽을 수 있는 표라서, 목록·문서군·
행수·Base 점수를 TSV 한 장으로 낸다. 작아서 git 에 올라가고 엑셀로 열린다.

CLI:
    python eval/llm_manifest.py                    # 500 + 스모크 50 둘 다
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
LLM = os.path.join(HERE, "LLM")

COLS = ["sourceFile", "문서군", "행수", "Base_cell", "붕괴", "회전각",
        "orientMargin", "기울기", "imagePath"]


def rows(sources: list[str], docs: dict) -> list[list[str]]:
    out = []
    for src in sources:
        f = docs.get(src) or {}
        acc = f.get("cellAcc")
        out.append([
            src,
            f.get("group") or "-",
            str(f.get("rowCount") if f.get("rowCount") is not None else "-"),
            ("%.1f%%" % (100 * acc)) if acc is not None else "-",
            "Y" if f.get("collapsed") else "",
            str(f.get("orientAngle") if f.get("orientApplied") else 0),
            str(f.get("orientMargin") if f.get("orientMargin") is not None else "-"),
            "Y" if f.get("deskewApplied") else "",
            f.get("imagePath") or "-",
        ])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", default=os.path.join(LLM, "data", "groups_072.json"))
    args = ap.parse_args()

    docs = json.load(open(args.groups, encoding="utf-8"))["docs"]

    for name, src_file, out_file in (
            ("표본 500", "sample_500_sources.txt", "sample_500_manifest.tsv"),
            ("스모크 50", "smoke_50_sources.txt", "smoke_50_manifest.tsv")):
        src_path = os.path.join(LLM, "data", src_file)
        if not os.path.exists(src_path):
            print("건너뜀 - 없음: " + src_path)
            continue
        sources = [l.strip() for l in io.open(src_path, encoding="utf-8") if l.strip()]
        table = rows(sources, docs)
        out = os.path.join(LLM, "data", out_file)
        with io.open(out, "w", encoding="utf-8-sig", newline="\n") as fh:   # 엑셀용 BOM
            fh.write("\t".join(COLS) + "\n")
            for r in table:
                fh.write("\t".join(r) + "\n")

        # 요약
        by = {}
        for r in table:
            by[r[1]] = by.get(r[1], 0) + 1
        collapsed = sum(1 for r in table if r[4] == "Y")
        rc = [int(r[2]) for r in table if r[2].isdigit()]
        print("\n%s  %d장  -> %s" % (name, len(table), out))
        for g, n in sorted(by.items(), key=lambda kv: -kv[1]):
            print("   %-16s %4d" % (g, n))
        print("   붕괴 %d · 행수 최대 %d / 중앙 %d"
              % (collapsed, max(rc or [0]), sorted(rc)[len(rc) // 2] if rc else 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
