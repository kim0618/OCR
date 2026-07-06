"""G1: 매칭 엔진 벤치 입력 생성 (②매칭 트랙).

062 thin snapshot을 replay(재-OCR 없음, 현재 파서)해서 표 행을 얻고, GT와 정렬한 뒤
(우리읽기 품명, 우리 파싱 단가, GT 품목코드, GT 정식명)을 `_match_engine.csv`로 낸다.
psql `_match_engine.sql`(war식 clean→trigram→가격 tiebreak, floor 스윕, spurious 동시측정)이
채점한다.

replay_compare/*.json을 직접 읽지 않고 replay를 다시 도는 이유:
  - compare 산출물의 rows[]는 matched+gt-only만 실체화하고 **ext-only(파서가 만든 행,
    GT에 없음 = spurious 모집단 ~3.8k행)는 인덱스만 남아 셀 내용이 없다.**
  - replay는 미커밋 파서 룰과 항상 일치한다(compare 사이드카의 신선도에 안 묶임).

행 종류(row_kind):
  matched  = GT행과 정렬됨 → gt_code/gt_master 채점 대상
  ext_only = 파서가 만든 행(GT 정렬 실패) → 매칭엔진이 코드 배정하면 spurious
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402
import re  # noqa: E402
from build_manifest import build_manifest  # noqa: E402
from compare_table import _align_by_content, _align_by_rowindex, _has_rowindex  # noqa: E402
from gt_loader import load_gt_aggregate  # noqa: E402
from replay_compare import replay_dispatch  # noqa: E402

RUN_TS = os.path.join("062_20260703_095853", "thin")
OUT = os.path.join(HERE, "data", "invoice_war", "_match_engine.csv")
TESTSET = "invoice_thin"

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _price(v):
    # "950.00"/"1,234" → "950"/"1234". digits-only는 950.00→95000이 되므로 소수점 인지 필수.
    m = _NUM.search(str(v or ""))
    if not m:
        return ""
    try:
        return str(int(float(m.group().replace(",", ""))))
    except ValueError:
        return ""


def main() -> int:
    run_dir = os.path.join(C.RUNS_DIR, RUN_TS)
    snap_dir = os.path.join(run_dir, "snapshots")
    if not os.path.isdir(snap_dir):
        print(f"no snapshots/ in {run_dir}"); return 2

    manifest = build_manifest(TESTSET)
    agg = load_gt_aggregate(
        os.path.normpath(os.path.join(C.HERE, manifest["gtAggregate"])),
        profile=manifest["kind"])
    gtkey_by_src = {s["sourceFile"]: s["gtKey"] for s in manifest["samples"] if s.get("gtKey")}

    snaps = sorted(f for f in os.listdir(snap_dir) if f.endswith(".json"))
    rows, n_snap, n_skip = [], 0, 0
    for f in snaps:
        src = f[:-5]
        gtkey = gtkey_by_src.get(src)
        if not gtkey or gtkey not in agg:
            n_skip += 1
            continue
        snap = json.load(open(os.path.join(snap_dir, f), encoding="utf-8"))
        ext_df, _path = replay_dispatch(snap)
        ext_rows = ext_df.get("tableRows") or []
        gt_rows = agg[gtkey]["tableRows"]
        use_rowindex = bool(gt_rows) and all(_has_rowindex(r) for r in gt_rows)
        if use_rowindex:
            pairs, _g, _e, _ng, _ne = _align_by_rowindex(gt_rows, ext_rows)
        else:
            pairs, _g, _e, _ng, _ne = _align_by_content(gt_rows, ext_rows)
        paired = {id(e) for _k, _gt, e in pairs}

        def _ext_cells(e):
            # 랭킹 tiebreak 재료: 규격(용량 신호), 수량/금액(단가 결측 역산)
            return [str(e.get("spec") or "").strip(),
                    str(e.get("quantity") or "").strip(),
                    _price(e.get("amount"))]

        for key, g, e in pairs:
            name = str(e.get("itemName") or "").strip()
            if not name:
                continue  # 매칭은 품명을 읽어야 가능
            rows.append([src, key, "matched", name, _price(e.get("unitPrice")),
                         *_ext_cells(e),
                         str(g.get("itemCode") or "").strip(),
                         str(g.get("itemNameMaster") or "").strip()])
        for e in ext_rows:
            if id(e) in paired:
                continue
            name = str(e.get("itemName") or "").strip()
            if not name:
                continue
            rows.append([src, "", "ext_only", name, _price(e.get("unitPrice")),
                         *_ext_cells(e), "", ""])
        n_snap += 1

    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["src", "row_idx", "row_kind", "our_name", "our_price",
                    "our_spec", "our_qty", "our_amount", "gt_code", "gt_master"])
        w.writerows(rows)

    n = len(rows)
    matched = [r for r in rows if r[2] == "matched"]
    extonly = [r for r in rows if r[2] == "ext_only"]
    noprice = sum(1 for r in rows if not r[4])
    nomaster_m = sum(1 for r in matched if not r[9])
    sys.stdout.reconfigure(errors="replace")
    print(f"wrote {OUT}")
    print(f"  snapshots replayed: {n_snap} (skipped no-GT: {n_skip})")
    print(f"  rows total: {n} = matched {len(matched)} + ext_only {len(extonly)}")
    print(f"  단가 결측(→fallback 대상): {noprice} ({100*noprice/n:.1f}%)")
    print(f"  spurious 모집단(ext_only + matched-GT빈칸): "
          f"{len(extonly)}+{nomaster_m} ({100*(len(extonly)+nomaster_m)/n:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
