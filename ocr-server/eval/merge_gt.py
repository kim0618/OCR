"""merge_gt — 월별 GT(ground_truth_25MM.json)들을 한 배치의 단일 집계로 병합.

거래명세서 thin testset 은 GT 를 **단일 집계 파일 하나**로 읽는다(contract.py 의
invoice_thin.gt_aggregate = ground_truth_2606.json). 10만장을 반반(1차/2차)으로
올릴 때 각 배치가 여러 달을 걸치므로, 그 달들의 GT `documents` 를 하나로 합쳐
그 파일명으로 내보낸다.

    # 1차 배치용: 2501~2506 병합 → AWS 가 읽는 파일명으로
    python eval/merge_gt.py --months 2501 2502 2503 2504 2505 2506 \
        -o eval/data/invoice_war/ground_truth_2606.json

    # 2차 배치용: 2507~2512 병합 (같은 파일명으로 교체 업로드)
    python eval/merge_gt.py --months 2507 2508 2509 2510 2511 2512 \
        -o eval/data/invoice_war/ground_truth_2606.json

입력 파일: eval/data/invoice_war/ground_truth_<month>.json (구조 = {schemaVersion,
profile, month, documents:{<docKey>:entry}}). 출력도 같은 스키마, documents 만 합침.
docKey 중복 시 경고하고 뒤에 온 것으로 덮음(같은 문서가 두 달에 있을 일은 없어야 정상).
"""
from __future__ import annotations

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "invoice_war")


def merge(months: list[str], out_path: str) -> int:
    merged_docs: dict = {}
    schema = profile = None
    dup = 0
    used_months = []
    for m in months:
        p = os.path.join(DATA, f"ground_truth_{m}.json")
        if not os.path.exists(p):
            print(f"  [skip] 없음: {p}")
            continue
        gt = json.load(open(p, encoding="utf-8"))
        schema = schema or gt.get("schemaVersion")
        profile = profile or gt.get("profile")
        docs = gt.get("documents", {})
        for k, v in docs.items():
            if k in merged_docs:
                dup += 1
            merged_docs[k] = v
        used_months.append(m)
        print(f"  [ok] {m}: {len(docs):,} docs  (누적 {len(merged_docs):,})")

    if not used_months:
        print("병합할 월 GT 가 하나도 없음 — --months 와 파일 경로 확인")
        return 1

    out = {
        "schemaVersion": schema,
        "profile": profile,
        "month": "+".join(used_months),   # 병합 배치 표시
        "documents": merged_docs,
    }
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"\n[병합 완료] {out_path}")
    print(f"  월: {'+'.join(used_months)}  ·  문서 {len(merged_docs):,}건  ·  {mb:.1f}MB"
          + (f"  ·  ⚠️ 중복 docKey {dup}건(뒤엣것으로 덮음)" if dup else ""))
    print("  → 이 파일을 AWS eval/data/invoice_war/ground_truth_2606.json 로 scp")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", nargs="+", required=True,
                    help="병합할 월들 (예: 2501 2502 ... — ground_truth_<월>.json)")
    ap.add_argument("-o", "--out", required=True, help="출력 집계 파일 경로")
    args = ap.parse_args()
    return merge(args.months, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
