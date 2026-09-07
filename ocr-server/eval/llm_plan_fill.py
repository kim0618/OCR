"""llm_plan_fill — LLM_REVIEW_PLAN.html 이 필요로 하는 숫자를 전부 뽑는다(그리고 채운다).

run 을 돌리고 나면 계획서에 들어갈 값이 한 번에 나와야 한다. 표가 20개라 손으로
옮기면 반드시 어긋난다. 그래서 Base·모델·차이·교차 2×2·비용을 한 자리에서 계산하고,
--write 면 **모델 열과 차이 열만** 문서에 써 넣는다.

    Base 만 (모델 run 전 - 문서의 현재 상태)
        python eval/llm_plan_fill.py
    500 스크리닝 - 후보 3개
        python eval/llm_plan_fill.py --model qwen=vlm_qwen_500 \\
            --model minicpm=vlm_minicpm_500 --model internvl=vlm_internvl_500 --write
    9,001 본판정 - 승자만
        python eval/llm_plan_fill.py --winner qwen=vlm_qwen_9001 --write

④ 매칭 컬럼(itemCode · itemNameMaster · Learn*)은 언제나 제외 - 기준선 46.7% 와 같은 저울.
모델 run 이 주어지면 **그 run 이 덮는 문서로 Base 를 맞춘다** - 같은 문서, 같은 셀에서만 비교한다.

**서술은 절대 건드리지 않는다.** --write 는 `<td class="... muted">?</td>` 꼴의 빈 데이터 칸만
바꾼다. 계획서는 손으로 관리하는 문서이고, 생성기가 통째로 덮어쓰면 손으로 넣은 서술이
날아간다(POC UI 에서 겪은 사고).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(HERE, "LLM", "LLM_REVIEW_PLAN.html")
BASE_RUN = os.path.join(HERE, "runs", "072_20260802_182127")
GROUPS = os.path.join(HERE, "LLM", "data", "groups_072.json")

EXCLUDE = {"itemCode", "itemNameMaster", "itemNameLearnA", "itemNameLearnB",
           "itemCodeLearnA", "itemCodeLearnB"}
SCORED = {"match", "mismatch", "ext_missing"}
HOURLY_USD = 1.00                      # g6.xlarge on-demand
PADDLE_PER_HOUR = 2606.0               # 072 실측
COLLAPSE = 0.10                        # 문서 붕괴 임계

# 계획서 표의 행 순서와 같아야 한다.
ROW_COLS = ["manufacturingNo", "expiryDate", "spec", "itemName",
            "unitPrice", "insuranceCode", "quantity", "amount"]
HEADER_FIELDS = ["buyerAddress", "buyerCompany", "supplierAddress", "taxAmount",
                 "supplyAmount", "totalAmount", "supplierCompany", "taxType",
                 "buyerBizNumber", "issueDate", "supplierBizNumber", "discountAmount"]
GROUP_ORDER = ["전처리없음", "기울기보정", "회전적용·정상", "회전적용·붕괴"]
GROUP_LABEL = {"전처리없음": "전처리 없음", "기울기보정": "기울기 보정",
               "회전적용·정상": "회전 적용 · 정상", "회전적용·붕괴": "회전 적용 · 붕괴"}
MODEL_ORDER = ["qwen", "minicpm", "internvl"]   # 계획서 표 헤더 순서와 같아야 한다
SUMMARY = ["cell 정확도", "field 정확도", "structure 실패",
           "recognition 실패", "spurious", "행수 일치 문서"]


# ─────────────────────────────────────────────────────────── 집계

def blank() -> dict:
    return {"docs": 0, "rowMatchDocs": 0,
            "cell": {"scored": 0, "match": 0, "spurious": 0},
            "field": {"scored": 0, "match": 0, "spurious": 0},
            "defect": {"structure": 0, "recognition": 0, "layout": 0, "preprocessing": 0},
            "byCol": {c: [0, 0] for c in ROW_COLS},
            "byField": {f: [0, 0] for f in HEADER_FIELDS}}


def add(acc: dict, doc: dict) -> None:
    acc["docs"] += 1
    table = doc.get("table") or {}
    if table.get("rowCountMatch"):
        acc["rowMatchDocs"] += 1
    for row in (table.get("rows") or []):
        for key, v in (row.get("cells") or {}).items():
            if key in EXCLUDE:
                continue
            if v.get("spurious"):
                acc["cell"]["spurious"] += 1
            st = v.get("status")
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
        if v.get("spurious"):
            acc["field"]["spurious"] += 1
        st = v.get("status")
        if st not in SCORED:
            continue
        acc["field"]["scored"] += 1
        acc["field"]["match"] += st == "match"
        if key in acc["byField"]:
            acc["byField"][key][0] += 1
            acc["byField"][key][1] += st == "match"
    for d in ((doc.get("buckets") or {}).get("defects") or []):
        if any(x in (d.get("location") or "") for x in EXCLUDE):
            continue
        if d.get("bucket") in acc["defect"]:
            acc["defect"][d["bucket"]] += 1


def cells_of(doc: dict) -> dict:
    """(GT행, 등장 순번, 컬럼) -> 맞았나. compare_cross 와 같은 셀 신원."""
    out, seen = {}, {}
    for row in ((doc.get("table") or {}).get("rows") or []):
        idx = str(row.get("rowIndex"))
        occ = seen.get(idx, 0)
        seen[idx] = occ + 1
        for key, v in (row.get("cells") or {}).items():
            if key in EXCLUDE or v.get("status") not in SCORED:
                continue
            out[(idx, occ, key)] = v["status"] == "match"
    return out


def load(run_dir: str, only: set | None = None) -> dict:
    out = {}
    for path in glob.glob(os.path.join(run_dir, "compare", "*.json")):
        src = os.path.basename(path)[:-5]
        if only is not None and src not in only:
            continue
        with open(path, encoding="utf-8") as fh:
            out[src] = json.load(fh)
    return out


def summarize(docs: dict, groups: dict) -> dict:
    tot = blank()
    per = {g: blank() for g in GROUP_ORDER}
    for src, doc in docs.items():
        add(tot, doc)
        g = (groups.get(src) or {}).get("group")
        if g in per:
            add(per[g], doc)
    return {"total": tot, "byGroup": per}


def metrics(acc: dict) -> dict:
    c, f, d = acc["cell"], acc["field"], acc["defect"]
    tot_def = sum(d.values())
    r = lambda m, s: (100.0 * m / s) if s else None
    return {
        "cell 정확도": r(c["match"], c["scored"]),
        "field 정확도": r(f["match"], f["scored"]),
        "structure 실패": r(d["structure"], tot_def),
        "recognition 실패": r(d["recognition"], tot_def),
        "spurious": r(c["spurious"] + f["spurious"], c["scored"] + f["scored"]),
        "행수 일치 문서": r(acc["rowMatchDocs"], acc["docs"]),
    }


def cross(base: dict, model: dict, groups: dict) -> dict:
    """문서군별 셀 2×2 · 문서 2×2 + 부류 집계."""
    z = lambda: {"keep": 0, "bothfail": 0, "revive": 0, "regress": 0}
    cellg = {g: z() for g in GROUP_ORDER}
    docg = {g: z() for g in GROUP_ORDER}
    classes = {"revived": 0, "regressed": 0, "bothfail": 0, "kept": 0}
    for src in set(base) & set(model):
        g = (groups.get(src) or {}).get("group")
        b, m = cells_of(base[src]), cells_of(model[src])
        if g in cellg:
            for k in set(b) & set(m):
                bo, mo = b[k], m[k]
                cellg[g]["keep" if bo and mo else "revive" if mo
                         else "regress" if bo else "bothfail"] += 1
        ba = sum(b.values()) / len(b) if b else None
        ma = sum(m.values()) / len(m) if m else None
        if ba is None or ma is None:
            continue
        bc, mc = ba < COLLAPSE, ma < COLLAPSE
        cls = ("revived" if bc and not mc else "regressed" if mc and not bc
               else "bothfail" if bc else "kept")
        classes[cls] += 1
        if g in docg:
            docg[g][{"revived": "revive", "regressed": "regress",
                     "bothfail": "bothfail", "kept": "keep"}[cls]] += 1
    return {"cell": cellg, "doc": docg, "classes": classes}


def cost(run_dir: str, n_hint: int = 0) -> dict | None:
    p = os.path.join(run_dir, "run_meta.json")
    if not os.path.exists(p):
        return None
    m = json.load(open(p, encoding="utf-8"))
    sec, n = m.get("elapsedSec"), (m.get("docs") or n_hint)
    if not sec or not n:
        return None
    per_h = n / sec * 3600
    return {"docs": n, "sec": sec, "perHour": per_h, "minutes": sec / 60,
            "usd": sec / 3600 * HOURLY_USD,
            "vsPaddle": PADDLE_PER_HOUR / per_h if per_h else None}


# ─────────────────────────────────────────────────────────── 출력

def fmt(v, suffix="%"):
    return "-" if v is None else "%.1f%s" % (v, suffix)


def diff(model, base, suffix="%p"):
    if model is None or base is None:
        return "-"
    return "%+.1f%s" % (model - base, suffix)


def ordered(models):
    """계획서 열 순서(Qwen · MiniCPM · InternVL)로 고정. 모르는 키는 뒤에."""
    return (sorted((n for n in models if n in MODEL_ORDER), key=MODEL_ORDER.index)
            + [n for n in models if n not in MODEL_ORDER])


def dump(base_sum, models, crosses, costs, winner):
    names = ordered(models)
    print("\n" + "=" * 100)
    print("전처리 - 문서군별 cell 정확도")
    print("=" * 100)
    hdr = "%-16s%7s%9s" % ("문서군", "문서", "Base")
    for n in names:
        hdr += "%12s%9s" % (n, "차이")
    print(hdr)
    for g in GROUP_ORDER:
        b = base_sum["byGroup"][g]
        bv = metrics(b)["cell 정확도"]
        row = "%-16s%7s%9s" % (GROUP_LABEL[g], "{:,}".format(b["docs"]), fmt(bv))
        for n in names:
            mv = metrics(models[n]["byGroup"][g])["cell 정확도"]
            row += "%12s%9s" % (fmt(mv), diff(mv, bv))
        print(row)

    for kind, title in (("cell", "교차 - 셀 이동"), ("doc", "교차 - 문서 이동")):
        if not crosses:
            break
        print("\n" + "=" * 100)
        print("%s  (문서군별)" % title)
        print("=" * 100)
        for n in names:
            print("[%s] %-16s%10s%10s%10s%10s%10s"
                  % (n, "문서군", "유지", "둘다실패", "소생", "회귀", "순증"))
            for g in GROUP_ORDER:
                c = crosses[n][kind][g]
                print("%-7s%-16s%10s%10s%10s%10s%+10s"
                      % ("", GROUP_LABEL[g], "{:,}".format(c["keep"]),
                         "{:,}".format(c["bothfail"]), "{:,}".format(c["revive"]),
                         "{:,}".format(c["regress"]), "{:,}".format(c["revive"] - c["regress"])))
            if kind == "doc":
                k = crosses[n]["classes"]
                print("%-7s부류: 살린 것 %s · 망친 것 %s · 둘 다 틀림 %s · 유지 %s"
                      % ("", "{:,}".format(k["revived"]), "{:,}".format(k["regressed"]),
                         "{:,}".format(k["bothfail"]), "{:,}".format(k["kept"])))

    print("\n" + "=" * 100)
    print("파서 - 종합")
    print("=" * 100)
    bm = metrics(base_sum["total"])
    hdr = "%-18s%9s" % ("지표", "Base")
    for n in names:
        hdr += "%12s%9s" % (n, "차이")
    print(hdr)
    for key in SUMMARY:
        row = "%-18s%9s" % (key, fmt(bm[key]))
        for n in names:
            mv = metrics(models[n]["total"])[key]
            row += "%12s%9s" % (fmt(mv), diff(mv, bm[key]))
        print(row)

    for title, keys, attr in (("파서 - 행 컬럼", ROW_COLS, "byCol"),
                              ("파서 - 헤더 필드", HEADER_FIELDS, "byField")):
        print("\n" + "=" * 100)
        print(title)
        print("=" * 100)
        hdr = "%-20s%9s%9s" % ("컬럼", "채점셀", "Base")
        for n in names:
            hdr += "%12s%9s" % (n, "차이")
        print(hdr)
        for k in keys:
            bs, bmt = base_sum["total"][attr][k]
            bv = 100.0 * bmt / bs if bs else None
            row = "%-20s%9s%9s" % (k, "{:,}".format(bs), fmt(bv))
            for n in names:
                ms, mmt = models[n]["total"][attr][k]
                mv = 100.0 * mmt / ms if ms else None
                row += "%12s%9s" % (fmt(mv), diff(mv, bv))
            print(row)

    if costs:
        print("\n" + "=" * 100)
        print("비용  (g6.xlarge on-demand $%.2f/시간 · Paddle %s장/시간)"
              % (HOURLY_USD, "{:,}".format(int(PADDLE_PER_HOUR))))
        print("=" * 100)
        print("%-20s%8s%10s%10s%9s%12s" % ("run", "장수", "소요", "장/시간", "비용", "Paddle 대비"))
        for n, c in costs.items():
            if not c:
                print("%-20s%s" % (n, "  run_meta.json 없음"))
                continue
            print("%-20s%8s%9.1f분%10s%9s%12s"
                  % (n, "{:,}".format(c["docs"]), c["minutes"],
                     "{:,.0f}".format(c["perHour"]), "$%.2f" % c["usd"],
                     "%.0f×" % c["vsPaddle"] if c["vsPaddle"] else "-"))
    if winner:
        print("\n승자 = %s  (9,001 본판정 · 교차표 열에 채운다)" % winner)


# ─────────────────────────────────────────────────────────── HTML 기입

CELLQ = re.compile(r'<td class="([a-z ]*?)muted">\?</td>')


def write_plan(base_sum, models, crosses, costs, winner):
    names = ordered(models)
    bm = metrics(base_sum["total"])

    def vals_for(sec, sub, label):
        if sec == "전처리" and sub in ("500장 - 모델 선정", "9,001장 - 본판정"):
            g = next((g for g in GROUP_ORDER if GROUP_LABEL[g] in label), None)
            use = names if sub.startswith("500") else ([winner] if winner else [])
            if not g or not use:
                return None
            bv = metrics(base_sum["byGroup"][g])["cell 정확도"]
            out = []
            for n in use:
                mv = metrics(models[n]["byGroup"][g])["cell 정확도"]
                out += [fmt(mv), diff(mv, bv)]
            return out
        if sec == "교차" and sub in ("셀 이동", "문서 이동"):
            g = next((g for g in GROUP_ORDER if GROUP_LABEL[g] in label), None)
            n = winner or (names[0] if names else None)
            if not g or not n:
                return None
            c = crosses[n]["cell" if sub == "셀 이동" else "doc"][g]
            return ["{:,}".format(c["keep"]), "{:,}".format(c["bothfail"]),
                    "{:,}".format(c["revive"]), "{:,}".format(c["regress"]),
                    "%+d" % (c["revive"] - c["regress"])]
        if sec == "비용" and sub in ("500장", "9,001장"):
            use = names if sub == "500장" else ([winner] if winner else [])
            if not use:
                return None
            key = next((k for k in ("처리량", "소요", "비용", "Paddle 대비") if k in label), None)
            if not key:
                return None
            out = []
            for n in use:
                c = costs.get(n)
                if not c:
                    return None
                mins = c["minutes"]
                out.append({"처리량": "{:,.0f}".format(c["perHour"]),
                            "소요": ("%.1f분" % mins) if mins < 90 else ("%.1f시간" % (mins / 60)),
                            "비용": "$%.2f" % c["usd"],
                            "Paddle 대비": ("%.0f×" % c["vsPaddle"]) if c["vsPaddle"] else "-"}[key])
            return out
        if sec in ("파서500", "파서9001"):
            use = names if sec == "파서500" else ([winner] if winner else [])
            if not use:
                return None
            if sub == "종합":
                key = next((k for k in SUMMARY if k in label), None)
                if not key:
                    return None
                out = []
                for n in use:
                    mv = metrics(models[n]["total"])[key]
                    out += [fmt(mv), diff(mv, bm[key])]
                return out
            attr = "byCol" if sub.startswith("행") else "byField"
            keys = ROW_COLS if attr == "byCol" else HEADER_FIELDS
            k = next((k for k in keys if "<code>%s</code>" % k in label), None)
            if not k:
                return None
            bs, bmt = base_sum["total"][attr][k]
            bv = 100.0 * bmt / bs if bs else None
            out = []
            for n in use:
                ms, mmt = models[n]["total"][attr][k]
                mv = 100.0 * mmt / ms if ms else None
                out += [fmt(mv), diff(mv, bv)]
            return out
        return None

    lines = open(PLAN, encoding="utf-8").read().split("\n")
    h2 = h3 = None
    row_label = ""
    filled = 0
    for i, ln in enumerate(lines):
        m = re.search(r"<h2>(.*?)</h2>", ln)
        if m:
            t = re.sub("<[^>]*>", "", m.group(1))
            h2 = ("전처리" if "전처리 비교" in t else "교차" if "선정 모델 교차" in t
                  else "파서500" if "파서 - 500장" in t
                  else "파서9001" if "파서 - 9,001장" in t
                  else "비용" if "후보 비교" in t else None)
            h3 = "종합" if h2 in ("파서500", "파서9001") else None
        m = re.search(r"<h3>(.*?)</h3>", ln)
        if m:
            t = re.sub("<[^>]*>", "", m.group(1))
            h3 = None
            for c in ("500장 - 모델 선정", "9,001장 - 본판정", "셀 이동", "문서 이동",
                      "종합", "행 컬럼", "헤더 필드", "500장", "9,001장"):
                if c in t:
                    h3 = c
                    break
        if "<tr" in ln:
            row_label = ln                      # 라벨은 행 첫 줄에 있다
        if not h2 or 'muted">?' not in ln:
            continue
        vals = vals_for(h2, h3, row_label if "<tr" not in ln else ln)
        if not vals:
            continue
        it = iter(vals)

        def repl(mo):
            nonlocal filled
            try:
                v = next(it)
            except StopIteration:
                return mo.group(0)
            filled += 1
            cls = mo.group(1).strip()
            return ('<td class="%s">%s</td>' % (cls, v)) if cls else "<td>%s</td>" % v

        lines[i] = CELLQ.sub(repl, ln)

    open(PLAN, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("\n→ %s  (%d칸 기입)" % (PLAN, filled))


# ─────────────────────────────────────────────────────────── main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE_RUN)
    ap.add_argument("--groups", default=GROUPS)
    ap.add_argument("--model", action="append", default=[],
                    help="이름=run디렉터리 (여러 번). 예: --model qwen=vlm_qwen_500")
    ap.add_argument("--winner", help="이름=run - 9,001 본판정·교차표에 쓸 승자")
    ap.add_argument("--sample",
                    default=os.path.join(HERE, "LLM", "data", "sample_500_sources.txt"),
                    help="모델이 없을 때 Base 를 이 표본으로 부분집계")
    ap.add_argument("--write", action="store_true", help="계획서의 모델·차이 칸을 채운다")
    ap.add_argument("--json", help="기계용 출력 경로")
    args = ap.parse_args()

    groups = json.load(open(args.groups, encoding="utf-8"))["docs"]
    runs = {}
    for spec in args.model:
        k, _, v = spec.partition("=")
        runs[k] = os.path.join(HERE, "runs", v)
    win = None
    if args.winner:
        win, _, v = args.winner.partition("=")
        runs[win] = os.path.join(HERE, "runs", v)

    if runs:
        only = set(load(next(iter(runs.values()))))     # 모델이 덮는 문서로 Base 를 맞춘다
    else:
        only = {ln.strip() for ln in open(args.sample, encoding="utf-8") if ln.strip()}

    base_docs = load(args.base, only)
    base_sum = summarize(base_docs, groups)
    print("Base %s  문서 %s  %s" % (os.path.basename(args.base), "{:,}".format(len(base_docs)),
                                  "(모델 run 과 교집합)" if runs else "(표본 부분집계)"))

    n = len(base_docs)
    costs = {"Paddle base": {"docs": n, "sec": n / PADDLE_PER_HOUR * 3600,
                             "perHour": PADDLE_PER_HOUR, "minutes": n / PADDLE_PER_HOUR * 60,
                             "usd": n / PADDLE_PER_HOUR * HOURLY_USD, "vsPaddle": 1.0}}
    models, crosses = {}, {}
    for name, rd in runs.items():
        docs = load(rd, set(base_docs))
        models[name] = summarize(docs, groups)
        crosses[name] = cross(base_docs, docs, groups)
        costs[name] = cost(rd, len(docs))
        print("  %s: %s 문서 %s" % (name, os.path.basename(rd), "{:,}".format(len(docs))))

    dump(base_sum, models, crosses, costs, win)

    if args.write:
        if not models:
            print("\n--write 는 --model / --winner 가 있어야 한다.", file=sys.stderr)
            return 1
        write_plan(base_sum, models, crosses, costs, win)

    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"base": base_sum, "models": models, "cross": crosses,
                       "cost": costs}, fh, ensure_ascii=False, indent=1)
        print("→ " + args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
