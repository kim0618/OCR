"""gt_trust — GT 셀별 신뢰등급 태깅 (사이드카, 읽기전용 로직).

war GT는 품목명(itemNameMaster)·코드만 사람 검증(gold)이고, 숫자·날짜는 구글 raw 그대로(미검증).
그대로 GT로 채점하면 "틀린 GT로 우리를 오판"하므로, 셀마다 신뢰등급을 매겨
채점·표시에서 unverified 불일치는 우리 오류로 단정하지 않게 한다.

등급:
  gold          사람/마스터 검증값 (itemNameMaster, itemCode, 마스터조인 회사/주소, 체크섬 통과 사업자번호)
  self_verified 자가검산 통과 (행 수량×단가=금액)
  reference     구글 raw 참조값 (itemName 원문 = 인식 head-to-head용, 정답 아님)
  unverified    검증수단 없음/실패 (구글 raw 숫자·날짜·규격) → 불일치해도 우리 오류로 단정 금지

usage(자가검증):  python eval/gt_trust.py            # ground_truth_2606.json 신뢰분포 출력
"""
from __future__ import annotations

import os
import re

GOLD = "gold"
SELF = "self_verified"
REF = "reference"
UNV = "unverified"

# 마스터 조인/사람검증에서 온 헤더필드
_MASTER_FIELDS = {"supplierCompany", "supplierAddress", "buyerCompany", "buyerAddress", "taxType"}
_BIZNO_FIELDS = {"supplierBizNumber", "buyerBizNumber"}


def _num(s):
    if s is None:
        return None
    t = re.sub(r"[^0-9.\-]", "", str(s))
    if t in ("", "-", ".", "-.", "--"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def verify_row_arithmetic(row: dict) -> bool | None:
    """수량×단가 == 금액 ?  (검증불가=None)"""
    q, up, amt = _num(row.get("quantity")), _num(row.get("unitPrice")), _num(row.get("amount"))
    if q is None or up is None or amt is None:
        return None
    return abs(q * up - amt) < 0.5


def verify_bizno(s) -> bool | None:
    """한국 사업자등록번호 체크digit 검증 (10자리 아니면 None)."""
    if s is None:
        return None
    d = re.sub(r"\D", "", str(s))
    if len(d) != 10:
        return None
    n = [int(c) for c in d]
    w = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    tot = sum(n[i] * w[i] for i in range(9)) + (n[8] * 5) // 10
    return (10 - (tot % 10)) % 10 == n[9]


def _date_ok(s) -> bool:
    if not s:
        return False
    d = re.sub(r"\D", "", str(s))
    if len(d) != 8:
        return False
    y, m, dd = int(d[:4]), int(d[4:6]), int(d[6:8])
    return 2000 <= y <= 2100 and 1 <= m <= 12 and 1 <= dd <= 31


def tag_field(label: str, value) -> str:
    if label in _BIZNO_FIELDS:
        return GOLD if verify_bizno(value) else UNV
    if label in _MASTER_FIELDS:
        return GOLD
    if label == "issueDate":
        return GOLD if _date_ok(value) else UNV
    # totalAmount/taxAmount/supplyAmount/discountAmount/documentNumber 등 = 구글 raw 숫자
    return UNV


def tag_row(row: dict) -> dict:
    """행의 셀별 등급. 숫자 trio는 산술검증으로 self_verified/unverified."""
    arith = verify_row_arithmetic(row)
    trio = SELF if arith else UNV  # None(검증불가)도 unverified
    tags = {}
    for k in row:
        if k in ("quantity", "unitPrice", "amount"):
            tags[k] = trio
        elif k == "itemNameMaster" or k == "itemCode":
            tags[k] = GOLD
        elif k == "itemName":
            tags[k] = REF  # 구글 raw 원문 = 인식 head-to-head용
        else:  # spec, expiryDate, manufacturingNo
            tags[k] = UNV
    return tags


def tag_document(gt_doc: dict) -> dict:
    """gt_loader 형태(normalizedResult.fields[]/tableRows[]) -> 셀별 등급."""
    nr = gt_doc.get("normalizedResult", gt_doc)
    fields = {}
    for f in nr.get("fields", []):
        lab = f.get("labelEn")
        if lab:
            fields[lab] = tag_field(lab, f.get("value"))
    rows = [tag_row(r) for r in nr.get("tableRows", [])]
    return {"fields": fields, "rows": rows}


def _selftest():
    import json
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "data", "invoice_war", "ground_truth_2606.json")
    d = json.load(open(p, encoding="utf-8"))
    docs = d.get("documents", {})
    rows_total = rows_self = rows_unv = 0
    bizno_total = bizno_ok = 0
    for doc in docs.values():
        t = tag_document(doc)
        for f in doc.get("normalizedResult", {}).get("fields", []):
            if f.get("labelEn") in _BIZNO_FIELDS:
                bizno_total += 1
                if verify_bizno(f.get("value")):
                    bizno_ok += 1
        for r in doc.get("normalizedResult", {}).get("tableRows", []):
            a = verify_row_arithmetic(r)
            if a is None:
                continue
            rows_total += 1
            if a:
                rows_self += 1
            else:
                rows_unv += 1
    print(f"docs={len(docs)}")
    print(f"rows checkable={rows_total}  self_verified(arith)={rows_self} "
          f"({100*rows_self/rows_total:.1f}%)  unverified={rows_unv}")
    print(f"bizno fields={bizno_total}  checksum_ok={bizno_ok} "
          f"({100*bizno_ok/bizno_total:.1f}%)" if bizno_total else "bizno fields=0")


if __name__ == "__main__":
    _selftest()
