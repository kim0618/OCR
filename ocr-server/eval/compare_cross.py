"""compare_cross - 두 run 을 같은 셀에서 맞대어 소생 · 회귀를 가른다.

정확도 평균만 보면 안이 뒤바뀐 걸 못 본다. Base 40% 와 모델 40% 가 전혀 다른 40% 일 수 있다.
compare/ 의 셀 판정은 GT 행에 앵커되어 있으므로 셀 하나의 신원이 (문서, GT행, 컬럼) 으로
두 run 사이에 고정된다. 그 신원으로 네 칸을 만든다.

    유지   Base 맞음 모델 맞음      소생   Base 틀림 모델 맞음
    양쪽실패 Base 틀림 모델 틀림    회귀   Base 맞음 모델 틀림
    순증 = 소생 - 회귀

문서 단위는 cell 정확도가 임계 미만이면 '붕괴' 로 본다. 072 전량 분포는 완만한 단봉이라
임계가 다소 임의적이므로 여러 임계에서 함께 내고 결론이 흔들리는지 본다(기본 5 · 10 · 20%).

④ 매칭 컬럼(itemCode · itemNameMaster · Learn*)은 양쪽 다 제외한다 - 기준선 46.7% 와 같은 저울.

CLI:
    python eval/compare_cross.py --base runs/072_.../compare --model runs/XXX/compare
    python eval/compare_cross.py --base ... --model ... --out eval/LLM/data/cases.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

# 콘솔이 cp949 면 한글 외 기호에서 죽는다 - 출력 때문에 --out 쓰기가 날아간 적이 있다
sys.stdout.reconfigure(encoding="utf-8")

EXCLUDE = {"itemCode", "itemNameMaster", "itemNameLearnA", "itemNameLearnB",
           "itemCodeLearnA", "itemCodeLearnB"}
SCORED = {"match", "mismatch", "ext_missing"}
THRESHOLDS = (0.05, 0.10, 0.20)
MAIN_T = 0.10

HERE = os.path.dirname(os.path.abspath(__file__))


def orient_case(sample_path: str) -> dict:
    """전처리 텔레메트리로 '원본이 어땠고 우리가 무엇을 했나'를 가른다.

    같은 '소생'이라도 원인이 전혀 다르다 - 우리가 멀쩡한 세로 문서를 눕힌 것(우리 버그)과
    원본이 원래 누워 있던 것(VLM 실력)은 회수 가능한 몫이 다르다.
    180° 는 세로를 세로로 두므로 '눕힘'이 아니다 - 각도까지 봐야 갈린다.
    """
    import json as _j
    try:
        with open(sample_path, encoding="utf-8") as fh:
            pp = (_j.load(fh).get("preprocess") or {})
    except Exception:                                  # noqa: BLE001
        return {}
    o = pp.get("orientation") or {}
    pol = o.get("policy") or {}
    sz = pol.get("originalSize") or {}
    w, h = sz.get("width"), sz.get("height")
    if not (w and h):
        return {}
    applied = o.get("finalAppliedAfterPolicy")
    if applied is None:
        applied = o.get("applied")
    ang = (o.get("angle") or 0) if applied else 0
    before = "가로" if w > h else "세로"
    after = ("세로" if before == "가로" else "가로") if ang in (90, 270) else before
    if before == "세로" and after == "가로":
        cause = "전처리 실패 - 세운 걸 눕힘"          # 똑바로 선 문서를 90/270 으로 눕혔다 = 우리 버그
    elif before == "가로" and after == "세로":
        cause = "전처리 정상 - 누운 걸 세움"          # 누워 있던 원본을 바로 세웠다 = 전처리는 제 몫을 했다
    elif before == "가로":
        cause = "전처리 미적용 - 누운 채"          # 누운 원본을 건드리지 않았다
    else:
        cause = "전처리 정상 - 그대로 둠"            # 세로 유지(0° 또는 180°) - 방향은 그대로다
    return {"origOrient": before, "afterOrient": after, "angle": ang, "orientCause": cause}
REPLAY_DIR = os.path.join(HERE, "data", "invoice_war", "images_replay")


def _cells(path: str) -> dict[tuple[str, int, str], bool]:
    """(GT행, 그 행번호의 등장 순번, 컬럼) -> 맞았나. 채점 대상이 아닌 칸은 담지 않는다.

    rowIndex 만 쓰면 한 문서 안의 중복 rowIndex 가 덮어써져 셀이 사라지고
    (072 자기비교에서 602,111 -> 580,345), 행 목록 '위치'를 쓰면 두 run 이 서로
    다른 GT 행을 매칭했을 때 같은 GT 행이 다른 위치에 앉아 신원이 어긋난다
    (068->072 에서 769,420칸이 한쪽 전용으로 버려짐). 등장 순번은 둘 다 피한다 -
    다른 run 이 행을 몇 개 더 매칭했든 같은 rowIndex 의 n번째끼리 만난다.
    """
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    out = {}
    seen: dict[str, int] = {}
    for row in ((doc.get("table") or {}).get("rows") or []):
        idx = str(row.get("rowIndex"))
        occ = seen.get(idx, 0)
        seen[idx] = occ + 1
        for key, verdict in (row.get("cells") or {}).items():
            if key in EXCLUDE:
                continue
            status = verdict.get("status")
            if status not in SCORED:
                continue
            out[(idx, occ, key)] = status == "match"
    return out


def _image_path(source_file: str) -> str | None:
    """compare 의 sourceFile 에서 원본 경로를 되짚는다. '2501__4823__NAME.jpg' 꼴."""
    parts = (source_file or "").split("__")
    if len(parts) < 3:
        return None
    rel = os.path.join(REPLAY_DIR, parts[0], parts[1], "__".join(parts[2:]))
    return rel if os.path.exists(rel) else None


def fail_kind(base_path: str, model_path: str) -> dict:
    """실패의 성격을 가른다 - 회전 라벨만으로는 안 보이는 것.

    모델이 행 개수와 위치를 맞혔는데도 셀이 통째로 틀리는 일이 있다. 컬럼을 한 칸씩
    밀어 읽으면(제조사 컬럼이 품명 앞에 오는 양식 등) GT 행과 하나도 매칭되지 않아
    100칸이 전부 ext_missing 이 된다. 글자를 못 읽은 게 아니라 자리를 잘못 잡은 것이라
    회전·화질과 무관하고, 프롬프트가 답할 몫이다.
    """
    out = {}
    for lab, path in (("base", base_path), ("model", model_path)):
        try:
            with open(path, encoding="utf-8") as fh:
                t = (json.load(fh).get("table") or {})
        except Exception:                                  # noqa: BLE001
            continue
        out[lab + "RowGt"] = t.get("rowCountGt")
        out[lab + "RowExt"] = t.get("rowCountExt")
        out[lab + "RowMatched"] = len(t.get("matchedRowIdx") or [])
    mg, me, mm = out.get("modelRowGt"), out.get("modelRowExt"), out.get("modelRowMatched")
    if mm == 0 and me:
        out["failKind"] = "행 매칭 0 - 컬럼 밀림" if mg == me else "행 매칭 0"
    elif mg and me and mg != me:
        out["failKind"] = f"행수 불일치 {me}/{mg}"
    elif mm is not None and mg and mm < mg:
        out["failKind"] = f"행 일부 매칭 {mm}/{mg}"
    else:
        out["failKind"] = "행 매칭 정상"
    return out


def _acc(cells: dict) -> float | None:
    return (sum(cells.values()) / len(cells)) if cells else None


def cross(base_dir: str, model_dir: str) -> dict:
    base_files = {os.path.basename(p): p for p in glob.glob(os.path.join(base_dir, "*.json"))}
    model_files = {os.path.basename(p): p for p in glob.glob(os.path.join(model_dir, "*.json"))}
    shared = sorted(set(base_files) & set(model_files))

    cell = {"keep": 0, "revive": 0, "regress": 0, "bothfail": 0}
    skipped_cells = 0
    docs = []

    for name in shared:
        b, m = _cells(base_files[name]), _cells(model_files[name])
        keys = set(b) & set(m)
        skipped_cells += len(set(b) ^ set(m))
        move = 0
        per = {"keep": 0, "revive": 0, "regress": 0, "bothfail": 0}
        for k in keys:
            bo, mo = b[k], m[k]
            if bo and mo:
                per["keep"] += 1
            elif not bo and mo:
                per["revive"] += 1
                move += 1
            elif bo and not mo:
                per["regress"] += 1
                move -= 1
            else:
                per["bothfail"] += 1
        for k, v in per.items():
            cell[k] += v
        with open(base_files[name], encoding="utf-8") as fh:
            src = json.load(fh).get("sourceFile") or name
        oc = orient_case(os.path.join(os.path.dirname(base_dir), "samples", src + ".json"))
        oc.update(fail_kind(base_files[name], model_files[name]))
        docs.append({
            "docId": name[:-5] if name.endswith(".json") else name,
            "sourceFile": src,
            **oc,
            "imagePath": _image_path(src),
            "group": None,          # 문서군은 samples/ 회수 후 채운다
            "baseAcc": _acc(b),
            "modelAcc": _acc(m),
            "cellMove": move,
            "cells": per,
        })

    doc_tables = {}
    for t in THRESHOLDS:
        tab = {"keep": 0, "revive": 0, "regress": 0, "bothfail": 0, "skip": 0}
        for d in docs:
            ba, ma = d["baseAcc"], d["modelAcc"]
            if ba is None or ma is None:
                tab["skip"] += 1
                continue
            bc, mc = ba < t, ma < t          # collapsed?
            if bc and not mc:
                tab["revive"] += 1
            elif mc and not bc:
                tab["regress"] += 1
            elif bc and mc:
                tab["bothfail"] += 1
            else:
                tab["keep"] += 1
        doc_tables[f"{t:.2f}"] = tab

    for d in docs:
        ba, ma = d["baseAcc"], d["modelAcc"]
        if ba is None or ma is None:
            d["class"] = "skip"
        else:
            bc, mc = ba < MAIN_T, ma < MAIN_T
            d["class"] = ("revived" if bc and not mc else
                          "regressed" if mc and not bc else
                          "bothfail" if bc and mc else "kept")

    return {
        "baseDir": base_dir, "modelDir": model_dir,
        "docsShared": len(shared),
        "docsBaseOnly": len(set(base_files) - set(model_files)),
        "docsModelOnly": len(set(model_files) - set(base_files)),
        "cell": cell, "cellSkipped": skipped_cells,
        "doc": doc_tables, "mainThreshold": MAIN_T,
        "docs": docs,
    }


def report(r: dict) -> None:
    c = r["cell"]
    total = sum(c.values())
    print(f"문서 {r['docsShared']:,} (Base 만 {r['docsBaseOnly']} · 모델만 {r['docsModelOnly']})")
    print(f"셀 {total:,}  (한쪽에만 채점된 칸 {r['cellSkipped']:,} 제외)\n")
    print("셀 이동")
    print(f"  유지     {c['keep']:8,}")
    print(f"  둘 다 실패 {c['bothfail']:8,}")
    print(f"  소생     {c['revive']:8,}   Base 틀림 -> 모델 맞음")
    print(f"  회귀     {c['regress']:8,}   Base 맞음 -> 모델 틀림")
    print(f"  순증     {c['revive'] - c['regress']:+8,}")
    if total:
        print(f"  정확도   Base {100*(c['keep']+c['regress'])/total:.1f}%"
              f"  ->  모델 {100*(c['keep']+c['revive'])/total:.1f}%")

    print("\n문서 이동 (붕괴 임계별)")
    print(f"  {'임계':>6} {'유지':>7} {'둘다붕괴':>8} {'소생':>7} {'회귀':>7} {'순증':>7}")
    for t, tab in r["doc"].items():
        print(f"  {float(t)*100:5.0f}% {tab['keep']:7,} {tab['bothfail']:8,} "
              f"{tab['revive']:7,} {tab['regress']:7,} {tab['revive']-tab['regress']:+7,}")

    print()
    print("부류 × 회전 원인  (같은 부류라도 회수 가능한 몫이 다르다)")
    print(f"  {'부류':<10} {'원인':<12} {'문서':>5} {'셀순증':>8}")
    agg = {}
    for d in r["docs"]:
        if d["class"] == "kept":
            continue
        k = (d["class"], d.get("orientCause") or "불명")
        a = agg.setdefault(k, [0, 0])
        a[0] += 1
        a[1] += d.get("cellMove") or 0
    for (cls, cause), (n, mv) in sorted(agg.items(), key=lambda x: (x[0][0], -x[1][0])):
        print(f"  {cls:<10} {cause:<12} {n:>5,} {mv:>+8,}")

    kinds = {}
    for d in r["docs"]:
        kinds[d["class"]] = kinds.get(d["class"], 0) + 1
    print(f"\n임계 {r['mainThreshold']*100:.0f}% 기준 부류: "
          + " · ".join(f"{k} {v:,}" for k, v in sorted(kinds.items())))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="Base run 의 compare 디렉터리")
    ap.add_argument("--model", required=True, help="비교 대상 run 의 compare 디렉터리")
    ap.add_argument("--out", help="부류별 문서 목록을 JSON 으로 (llm_cases_report.py --cases 입력)")
    ap.add_argument("--top", type=int, default=0, help="--out 에 부류마다 상위 N 개만")
    ap.add_argument("--all", action="store_true",
                    help="--out 에 부류가 그대로인 문서(kept)도 넣는다 - 전처리 판정은 읽기 결과와 무관하게 전량에 내린다")
    args = ap.parse_args()

    r = cross(args.base, args.model)

    if args.out:
        want = ("revived", "regressed", "bothfail") + (("kept",) if args.all else ())
        docs = [d for d in r["docs"] if d["class"] in want]
        docs.sort(key=lambda d: -abs(d["cellMove"] or 0))
        if args.top:
            kept, seen = [], {}
            for d in docs:
                seen[d["class"]] = seen.get(d["class"], 0) + 1
                if seen[d["class"]] <= args.top:
                    kept.append(d)
            docs = kept
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"summary": {k: v for k, v in r.items() if k != "docs"},
                       "docs": docs}, fh, ensure_ascii=False, indent=1)
        print(f"\n{args.out}  (문서 {len(docs):,})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
