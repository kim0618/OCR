"""llm_derive_run — run 의 samples 를 복사해 '양쪽 같은 후처리' 를 적용한 파생 run 을 만들고 채점한다.

Base 와 VLM 은 같은 문서를 읽어도 뒤에 붙는 후처리가 달라서, 그대로 비교하면 읽기 실력이 아니라
후처리 차이를 재게 된다(2026-09-15 확인). 이 스크립트는 원본 run 을 건드리지 않고 사본에만
후처리를 맞춘 뒤 compare_run 으로 다시 채점한다. 계획서는 이 파생 run 을 읽는다.

    --lot-merge   행의 manufacturingNo 가 비어 있고 lotNo 에 값이 있으면 그 값을 manufacturingNo 로.
                  Base 파서는 LOT 를 lotNo 에 따로 두는데 GT(war prod_no)는 manufacturingNo 뿐이다.
                  VLM 은 lotNo 를 내지 않아 무영향.
    --base-chain  VLM 에 Base 후처리 체인을 **그대로** 적용한다(main.py 파서 이후 순서, 아래 CHAIN).
                  Base 는 서버에서 이미 거쳤으므로 VLM 에만 켠다.

Base 후처리 체인 분류(2026-09-15 전수 · main.py:3563~3861):
    값만으로 도는 16개   → CHAIN 에 그대로(금액 가드 sanitize 포함 - "Base 그대로" 원칙)
    OCR 라인·좌표 필요 11개 → VLM 에는 재료가 없어 적용 불가(HA 행추가 · 약품칸 채우기 · 품명 입양 ·
                            행 합성 · 좌표 숫자열 복원 3종 · 밴드 품명 입양 · 합계 교체 · 고해상 재OCR ·
                            사업자번호 후보 재선택)
    채점 제외 칸만 3개    → 무관(품목 마스터 매칭 · 보험코드 · 스칼라 기본값)
  예외 1개 - 사업자번호 역할 교정: Base 의 refine_*_bizno 는 공급자 칸에 백제 지점 번호가 있으면 OCR 라인에서
  다른 후보를 다시 고른다. VLM 은 OCR 라인이 없어 원형은 0장 발동하므로, **같은 판별(지점 번호 목록)로
  두 칸을 맞바꾸는 방식**으로 옮긴다. 방법만 다르고 판단 기준은 같다.

    python eval/llm_derive_run.py --src 072_20260802_182127 --dst 072_20260802_182127_post --lot-merge
    python eval/llm_derive_run.py --src vlm_qwen_500r --dst vlm_qwen_500r_post --lot-merge --base-chain
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))


def lot_merge(df: dict) -> int:
    n = 0
    for r in df.get("tableRows") or []:
        if isinstance(r, dict) and not str(r.get("manufacturingNo") or "").strip() \
                and str(r.get("lotNo") or "").strip():
            r["manufacturingNo"] = str(r["lotNo"]).strip()
            n += 1
    return n


def build_chain():
    """main.py 파서 이후 체인 중 값만으로 도는 룰(순서 그대로) + 사업자번호 역할 교정 + 거래처 교체."""
    from extractors.master_match import (fill_party_match, strip_trailing_item_classification,
                                         strip_leading_item_code, strip_duplicate_item_pack_tail,
                                         strip_trailing_item_page_fraction)
    from extractors.invoice_statement_free import (
        sanitize_document_scalar_fields, drop_boilerplate_table_rows, salvage_blob_amount,
        split_merged_item_name, recover_shifted_item_name, fill_arith_empty_amount,
        fix_swapped_qty_unitprice, fill_arith_empty_quantity, fix_totals_arithmetic,
        fill_spec_from_item_name, _get_buyer_branch_biznos)
    from extractors.invoice_statement import recover_postjoin_same_row_amounts

    branch = _get_buyer_branch_biznos()
    dig = lambda v: re.sub(r"\D", "", str(v or ""))

    def rows(fn):
        def f(df, st):
            df["tableRows"], _ = fn(df.get("tableRows") or [])
        return f

    def sanitize(df, st):
        sanitize_document_scalar_fields(df)

    def totals(df, st):
        fix_totals_arithmetic(df, [])          # OCR 라인이 없으니 산술 유도 부분만 돈다

    def role_swap(df, st):
        s, b = dig(df.get("supplierBizNumber")), dig(df.get("buyerBizNumber"))
        if s in branch and b not in branch:    # 공급자 칸에 백제 지점 번호 = 역할이 뒤바뀐 것
            for x, y in (("supplierBizNumber", "buyerBizNumber"), ("supplierCompany", "buyerCompany"),
                         ("supplierAddress", "buyerAddress")):
                df[x], df[y] = df.get(y), df.get(x)
            st["roleSwap"] += 1

    def party(df, st):
        _, dbg = fill_party_match(df)
        st["partyDocs"] += bool(dbg.get("supplier"))

    return [
        sanitize, rows(drop_boilerplate_table_rows), rows(salvage_blob_amount), rows(split_merged_item_name),
        rows(recover_shifted_item_name), rows(strip_trailing_item_classification), rows(strip_leading_item_code),
        rows(recover_postjoin_same_row_amounts), rows(fill_arith_empty_amount), rows(fix_swapped_qty_unitprice),
        rows(fill_arith_empty_quantity), totals, rows(fill_spec_from_item_name),
        role_swap,                                           # ← refine_*_bizno 자리(변형)
        rows(strip_duplicate_item_pack_tail), rows(strip_trailing_item_page_fraction),
        party,                                               # ← fill_party_match 자리
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="원본 run 이름(runs/ 아래)")
    ap.add_argument("--dst", required=True, help="파생 run 이름(runs/ 아래, 없어야 한다)")
    ap.add_argument("--lot-merge", action="store_true")
    ap.add_argument("--base-chain", action="store_true")
    ap.add_argument("--testset", default="invoice_replay")
    a = ap.parse_args()
    if not (a.lot_merge or a.base_chain):
        ap.error("--lot-merge 나 --base-chain 중 하나는 있어야 한다")

    src = os.path.join(HERE, "runs", a.src)
    dst = os.path.join(HERE, "runs", a.dst)
    if not os.path.isdir(os.path.join(src, "samples")):
        raise SystemExit("원본 samples 가 없다: %s" % src)
    if os.path.exists(dst):
        raise SystemExit("이미 있다: %s - 지우고 다시" % dst)

    chain = build_chain() if a.base_chain else []
    os.makedirs(os.path.join(dst, "samples"))
    stat = {"docs": 0, "lotRows": 0, "roleSwap": 0, "partyDocs": 0}
    for f in sorted(os.listdir(os.path.join(src, "samples"))):
        if not f.endswith(".json"):
            continue
        d = json.load(io.open(os.path.join(src, "samples", f), encoding="utf-8"))
        df = d.get("documentFields") or {}
        if a.lot_merge:
            stat["lotRows"] += lot_merge(df)
        for step in chain:
            step(df, stat)
        d["documentFields"] = df
        with open(os.path.join(dst, "samples", f), "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False)
        stat["docs"] += 1

    # 처리량·실패 수는 원본 run 의 것이다(후처리는 추론 시간을 바꾸지 않는다)
    for name in ("run_meta.json", "errors.jsonl"):
        if os.path.exists(os.path.join(src, name)):
            shutil.copy(os.path.join(src, name), os.path.join(dst, name))
    with open(os.path.join(dst, "derive_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"src": a.src, "lotMerge": a.lot_merge, "baseChain": a.base_chain, **stat}, fh,
                  ensure_ascii=False, indent=1)

    import compare_run as CR
    with contextlib.redirect_stdout(io.StringIO()):
        CR.compare_run(a.dst, a.testset, skip_missing=True)
    n_cmp = len(os.listdir(os.path.join(dst, "compare")))
    print("%s → %s · 문서 %d · LOT 병합 %d · 역할 교정 %d · 거래처 교체 %d · 채점 %d" % (
        a.src, a.dst, stat["docs"], stat["lotRows"], stat["roleSwap"], stat["partyDocs"], n_cmp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
