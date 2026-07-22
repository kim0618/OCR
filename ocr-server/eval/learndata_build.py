"""learndata_build — 대량 run 의 compare/ + GT 에서 우리(Paddle) learndata 생성.

war `tbl_ocr_learndata_invoice_modify`(ocr_item_nm→user_item_cd) 를 우리 읽기로 재키잉.
소비 = master_match_google.sql 캐스케이드 1단계(learndata→LIKE→trigram):
  게이트 learn_count(ocr_item_nm 총수)>=3, tiebreak SIMILARITY(master item_nm, 입력)↓·|bp1_amt-price|↑.
  → 우리도 **같은 9컬럼 스키마**로 뽑아 같은 SQL/룩업에 그대로 슬롯.

소스(둘 다 run 산출물, compare 는 [3/6]서 완성됨):
  compare/<src>.json  table.rows[].cells.itemName  {gt: GT읽기, ext: 우리읽기}  ← 정렬완료
  ground_truth_rekey.json  documents[key].normalizedResult.tableRows[]  itemName/itemCode/spec/amount + _source(master_idx,brch_cd)

측정 2벌:
  (B) full   : 전체 93,708 → 배포/對Google 벤치           (기본)
  (A) heldout: --exclude replay_set_v1.txt → 9,001 제외 84,707 → 9,001 채점(비순환 효과검증)

RAM 안전: GT 1회 로드(~1.5GB) + compare per-doc 스트리밍. 전체 결과 동시로드 안 함(분석 thrash 회피).

usage (AWS, venv):
  python eval/learndata_build.py --run runs/20260720_175949 --gt data/invoice_war/ground_truth_rekey.json \
         --out data/invoice_war/learndata_full.json
  python eval/learndata_build.py --run ... --gt ... --exclude data/invoice_war/replay_set_v1.txt \
         --out data/invoice_war/learndata_heldout.json
"""
from __future__ import annotations
import argparse, json, os, glob, sys
from collections import defaultdict, Counter
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def _norm_key_from_compare_filename(fn: str) -> str:
    """compare 파일명(safe id, '/'→'__') → GT 키(<월>/<docId>/<파일>). '.json' 제거 후 __→/."""
    base = fn[:-5] if fn.endswith(".json") else fn
    return base.replace("__", "/")


def _gt_row_index(gt_doc: dict) -> tuple[dict, dict]:
    """한 GT 문서 → ({itemName: row}, _source). row 에 itemCode/spec/amount 포함."""
    nr = gt_doc.get("normalizedResult") or {}
    by_name: dict[str, dict] = {}
    for r in nr.get("tableRows") or []:
        nm = (r.get("itemName") or "").strip()
        if nm and nm not in by_name:      # 첫 등장 우선(동명 중복은 드묾)
            by_name[nm] = r
    return by_name, (gt_doc.get("_source") or {})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run dir (runs/<ts>) — compare/ 사용")
    ap.add_argument("--gt", required=True, help="ground_truth_rekey.json")
    ap.add_argument("--out", required=True, help="출력 learndata json")
    ap.add_argument("--exclude", default=None,
                    help="이 목록(replay_set_v1.txt, <월>/<docId>/<파일> 줄) 문서 제외 → held-out build")
    args = ap.parse_args()

    run_dir = args.run if os.path.isabs(args.run) else os.path.join(HERE, args.run)
    cmp_dir = os.path.join(run_dir, "compare")
    if not os.path.isdir(cmp_dir):
        # 중첩(runs/<ts>/<sub>/compare) 대비
        subs = glob.glob(os.path.join(run_dir, "*", "compare"))
        cmp_dir = subs[0] if subs else cmp_dir
    if not os.path.isdir(cmp_dir):
        print(f"no compare/ in {run_dir}"); return 2

    exclude: set[str] = set()
    if args.exclude:
        for ln in open(args.exclude, encoding="utf-8"):
            s = ln.strip()
            if s:
                exclude.add(s)
        print(f"[exclude] {len(exclude):,} 문서 제외(held-out)")

    print(f"[gt] 로딩 {args.gt} ...")
    gt_docs = json.load(open(args.gt, encoding="utf-8")).get("documents") or {}
    print(f"[gt] {len(gt_docs):,} 문서")

    rows: list[dict] = []            # event-log (9컬럼 tbl_ocr_learndata_invoice_modify 형)
    n_docs = n_pairs = n_skip_nogt = n_excluded = 0
    reg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    idx = 0

    files = sorted(os.listdir(cmp_dir))
    for i, fn in enumerate(files, 1):
        if not fn.endswith(".json"):
            continue
        key = _norm_key_from_compare_filename(fn)
        if key in exclude:
            n_excluded += 1
            continue
        gt_doc = gt_docs.get(key)
        if not gt_doc:
            continue
        try:
            cmp = json.load(open(os.path.join(cmp_dir, fn), encoding="utf-8"))
        except Exception:
            continue
        by_name, src = _gt_row_index(gt_doc)
        if not by_name:
            continue
        n_docs += 1
        master_idx = src.get("master_idx")
        brch = src.get("brch_cd")
        item_seq = 0
        for r in (cmp.get("table") or {}).get("rows") or []:
            cell = (r.get("cells") or {}).get("itemName") or {}
            gt_name = (cell.get("gt") or "").strip()
            our_read = (cell.get("ext") or "").strip()
            if not gt_name or not our_read:      # 정렬된 쌍만(gt·ext 둘 다)
                continue
            grow = by_name.get(gt_name)
            if not grow:
                continue
            code = (grow.get("itemCode") or "").strip()
            if not code:                          # 정답코드 없으면 learndata 불가
                n_skip_nogt += 1
                continue
            item_seq += 1
            idx += 1
            rows.append({
                "idx": idx,
                "invoice_seq": master_idx,
                "item_seq": item_seq,
                "ocr_item_nm": our_read,                              # ★우리 읽기 (키)
                "user_item_cd": code,                                 # ★GT 정답코드
                "user_item_st": (grow.get("spec") or "").strip() or None,
                "user_item_order_amt": (grow.get("amount") or "").strip() or None,
                "brch_cd": brch,
                "reg_date": reg,
            })
            n_pairs += 1
        if i % 20000 == 0:
            print(f"  {i}/{len(files)} (docs={n_docs} pairs={n_pairs})", flush=True)

    # 집계 통계(소비 게이트 learn_count>=3 관점)
    per_reading = Counter(x["ocr_item_nm"] for x in rows)
    ge3 = sum(1 for c in per_reading.values() if c >= 3)
    reading_codes = defaultdict(set)
    for x in rows:
        reading_codes[x["ocr_item_nm"]].add(x["user_item_cd"])
    multi = sum(1 for s in reading_codes.values() if len(s) > 1)

    out = {
        "schemaVersion": "learndata-ours.v1",
        "table": "tbl_ocr_learndata_invoice_modify",
        "builtFrom": os.path.basename(run_dir.rstrip("/")),
        "excludeList": args.exclude,
        "excludedDocs": n_excluded,
        "summary": {
            "docs": n_docs, "rows": len(rows),
            "distinctReadings": len(per_reading),
            "readingsLearnCountGe3": ge3,
            "readingsMultiCode": multi,
            "noGtCodeSkipped": n_skip_nogt,
        },
        "rows": rows,
    }
    out_path = args.out if os.path.isabs(args.out) else os.path.join(HERE, args.out)
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[done] docs {n_docs:,} → learndata rows {len(rows):,} "
          f"(고유읽기 {len(per_reading):,}, learn_count≥3 {ge3:,}, 다중코드 {multi:,}, "
          f"GT코드無 스킵 {n_skip_nogt:,}) -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
