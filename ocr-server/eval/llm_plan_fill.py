"""llm_plan_fill — LLM_REVIEW_PLAN.html 의 Base 열에 넣을 숫자를 072 compare/ 에서 뽑는다.

모델 열은 VLM run 이 끝나야 채워지지만, Base 열과 채점셀·문서수는 전부 로컬에서 나온다.
같은 스크립트를 500 표본 부분집계와 9,001 전량에 돌려 두 섹션을 함께 채운다.

④ 매칭 컬럼(itemCode · itemNameMaster · Learn*)은 언제나 제외 - 기준선 46.7% 와 같은 저울.

문서를 직접 고쳐 쓰지 않고 숫자만 찍는다. 계획서는 손으로 관리하는 문서라
생성기가 통째로 덮어쓰면 손으로 넣은 서술이 날아간다(POC UI 에서 겪은 사고).

CLI:
    python eval/llm_plan_fill.py                    # 500 + 9,001 둘 다
    python eval/llm_plan_fill.py --json out.json    # 기계용
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))

EXCLUDE = {"itemCode", "itemNameMaster", "itemNameLearnA", "itemNameLearnB",
           "itemCodeLearnA", "itemCodeLearnB"}
SCORED = {"match", "mismatch", "ext_missing"}

ROW_COLS = ["manufacturingNo", "expiryDate", "spec", "itemName",
            "unitPrice", "insuranceCode", "quantity", "amount"]
HEADER_FIELDS = ["buyerAddress", "buyerCompany", "supplierAddress", "taxAmount",
                 "supplyAmount", "totalAmount", "supplierCompany", "taxType",
                 "buyerBizNumber", "issueDate", "supplierBizNumber", "discountAmount"]
GROUP_ORDER = ["전처리없음", "기울기보정", "회전적용·정상", "회전적용·붕괴"]


def blank() -> dict:
    return {
        "docs": 0, "rowMatchDocs": 0,
        "cell": {"scored": 0, "match": 0, "spurious": 0},
        "field": {"scored": 0, "match": 0, "spurious": 0},
        "defect": {"structure": 0, "recognition": 0, "layout": 0, "preprocessing": 0},
        "byCol": {c: [0, 0] for c in ROW_COLS},      # [scored, match]
        "byField": {f: [0, 0] for f in HEADER_FIELDS},
    }


def add(acc: dict, doc: dict) -> None:
    acc["docs"] += 1
    table = doc.get("table") or {}
    if table.get("rowCountMatch"):
        acc["rowMatchDocs"] += 1

    for row in (table.get("rows") or []):
        for key, v in (row.get("cells") or {}).items():
            if key in EXCLUDE:
                continue
            st = v.get("status")
            if v.get("spurious"):
                acc["cell"]["spurious"] += 1
            if st not in SCORED:
                continue
            acc["cell"]["scored"] += 1
            acc["cell"]["match"] += st == "match"
            if key in acc["byCol"]:
                acc["byCol"][key][0] += 1
                acc["byCol"][key][1] += st == "match"

    for key, v in ((doc.get("fields") or {}).get("perField") or {}).items():
        if key in EXCLUDE:
            continue
        st = v.get("status")
        if v.get("spurious"):
            acc["field"]["spurious"] += 1
        if st not in SCORED:
            continue
        acc["field"]["scored"] += 1
        acc["field"]["match"] += st == "match"
        if key in acc["byField"]:
            acc["byField"][key][0] += 1
            acc["byField"][key][1] += st == "match"

    # 결함 버킷. location 이 ④ 컬럼을 가리키면 세지 않는다.
    for d in ((doc.get("buckets") or {}).get("defects") or []):
        loc = d.get("location") or ""
        if any(x in loc for x in EXCLUDE):
            continue
        b = d.get("bucket")
        if b in acc["defect"]:
            acc["defect"][b] += 1


def pct(m: int, s: int) -> str:
    return "{:.1f}%".format(100 * m / s) if s else "-"


def report(name: str, acc: dict, groups: dict[str, dict] | None) -> None:
    c, f = acc["cell"], acc["field"]
    dfc = acc["defect"]
    tot_def = sum(dfc.values())
    print("\n" + "=" * 74)
    print("{}   문서 {:,}".format(name, acc["docs"]))
    print("=" * 74)
    print("  cell 정확도(행 컬럼)   {:>7}   {:,} / {:,}".format(
        pct(c["match"], c["scored"]), c["match"], c["scored"]))
    print("  field 정확도(헤더 12)  {:>7}   {:,} / {:,}".format(
        pct(f["match"], f["scored"]), f["match"], f["scored"]))
    print("  structure 실패        {:>7}   {:,} / {:,} 결함".format(
        pct(dfc["structure"], tot_def), dfc["structure"], tot_def))
    print("  recognition 실패      {:>7}   {:,}".format(
        pct(dfc["recognition"], tot_def), dfc["recognition"]))
    print("  spurious(환각)        {:>7}   셀 {:,} + 필드 {:,}".format(
        pct(c["spurious"] + f["spurious"], c["scored"] + f["scored"]),
        c["spurious"], f["spurious"]))
    print("  행수 일치 문서        {:>7}   {:,} / {:,}".format(
        pct(acc["rowMatchDocs"], acc["docs"]), acc["rowMatchDocs"], acc["docs"]))
    print("  (참고) layout {:,} · preprocessing {:,}".format(dfc["layout"], dfc["preprocessing"]))

    print("\n  행 컬럼" + " " * 14 + "채점셀      Base")
    for col, (s, m) in sorted(acc["byCol"].items(), key=lambda kv: (kv[1][1] / kv[1][0]) if kv[1][0] else 0):
        print("    {:<20}{:>8,}{:>10}".format(col, s, pct(m, s)))
    print("\n  헤더 필드" + " " * 12 + "채점셀      Base")
    for col, (s, m) in sorted(acc["byField"].items(), key=lambda kv: (kv[1][1] / kv[1][0]) if kv[1][0] else 0):
        print("    {:<20}{:>8,}{:>10}".format(col, s, pct(m, s)))

    if groups:
        print("\n  문서군" + " " * 12 + "문서     채점셀   Base cell    붕괴문서")
        for g in GROUP_ORDER:
            a = groups.get(g)
            if not a:
                continue
            print("    {:<16}{:>6,}{:>10,}{:>11}{:>10,}".format(
                g, a["docs"], a["cell"]["scored"],
                pct(a["cell"]["match"], a["cell"]["scored"]), a["collapsed"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=os.path.join(HERE, "runs", "072_20260802_182127"))
    ap.add_argument("--groups", default=os.path.join(HERE, "LLM", "data", "groups_072.json"))
    ap.add_argument("--sample", default=os.path.join(HERE, "LLM", "data", "sample_500_sources.txt"))
    ap.add_argument("--collapse", type=float, default=0.10)
    ap.add_argument("--json", help="기계용 출력 경로")
    args = ap.parse_args()

    meta = json.load(open(args.groups, encoding="utf-8"))["docs"]
    sample = {ln.strip() for ln in open(args.sample, encoding="utf-8") if ln.strip()}

    full, sub = blank(), blank()
    gfull = {g: blank() | {"collapsed": 0} for g in GROUP_ORDER}
    gsub = {g: blank() | {"collapsed": 0} for g in GROUP_ORDER}

    for path in glob.glob(os.path.join(args.run, "compare", "*.json")):
        src = os.path.basename(path)[:-5]
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        g = (meta.get(src) or {}).get("group")
        collapsed = (meta.get(src) or {}).get("collapsed")
        add(full, doc)
        if g in gfull:
            add(gfull[g], doc)
            gfull[g]["collapsed"] += bool(collapsed)
        if src in sample:
            add(sub, doc)
            if g in gsub:
                add(gsub[g], doc)
                gsub[g]["collapsed"] += bool(collapsed)

    report("9,001 본판정  (Base = 072 전량)", full, gfull)
    report("500 표본  (Base = 072 부분집계)", sub, gsub)

    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"full": full, "sample": sub,
                       "groupsFull": gfull, "groupsSample": gsub}, fh,
                      ensure_ascii=False, indent=1)
        print("\n→ " + args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
