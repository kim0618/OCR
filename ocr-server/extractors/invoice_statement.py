import re
from dataclasses import dataclass
from typing import Any


_BIZ_RE = re.compile(r"(?<!\d)([0-9OIlSB]{3})[-\s.]([0-9OIlSB]{2})[-\s.]([0-9OIlSB]{5})(?!\d)")
_AMOUNT_RE = re.compile(r"(?<!\d)([0-9OIlSB]{1,3}(?:[,.][0-9OIlSB]{3})+|[0-9OIlSB]{4,})(?!\d)")
_PHONE_RE = re.compile(r"(?:TEL|Tel|tel|\uc804\ud654)?[:\s(]*(?<!\d)(?:0\d{1,2})[-)\s]?\d{3,4}[-\s]?\d{4}(?!\d)")

_COMPANY_ANCHOR_RE = re.compile(
    r"\uc0c1\s*\ud638(?:\uba85)?|\uc0c1\uc810\uba85|\uac70\ub798\ucc98\uba85|"
    r"\ub0a9\ud488\ucc98|\ud310\ub9e4\uc790|\uacf5\uae09\uc790|\ubc95\uc778\uba85"
)
_REP_ANCHOR_RE = re.compile(r"\uc131\s*\uba85|\ub300\ud45c\uc790(?:\uba85)?")
_ADDR_ANCHOR_RE = re.compile(r"\uc8fc\s*\uc18c|\uc18c\uc7ac\uc9c0|\uc0ac\uc5c5\uc7a5")
_BUYER_PARTY_LABEL_RE = re.compile(r"\uacf5\s*\uae09\s*\ubc1b|\uacf5.{0,4}\ub294\s*\uc790|\ubc1b\s*\ub294\s*\uc790|\uac70\s*\ub798\s*\ucc98|\uadc0\s*\ud558|\uc218\s*\uc2e0")
_SUPPLIER_PARTY_LABEL_RE = re.compile(r"\uacf5\s*\uae09\s*\uc790|\ubc1c\s*\ud589\s*\ucc98|\ub9e4\s*\ucd9c\s*\ucc98")
_ADDRESS_TOKEN_RE = re.compile(
    r"\uc11c\uc6b8|\uacbd\uae30|\uc778\ucc9c|\ubd80\uc0b0|\ub300\uad6c|\uad11\uc8fc|\ub300\uc804|"
    r"\uc6b8\uc0b0|\uc138\uc885|\uac15\uc6d0|\ucda9\ubd81|\ucda9\ub0a8|\uc804\ubd81|\uc804\ub0a8|"
    r"\uacbd\ubd81|\uacbd\ub0a8|\uc81c\uc8fc|[\uac00-\ud7a3]{1,10}(?:\uc2dc|\uad70|\uad6c|\ub3d9|\uc74d|\uba74|\ub9ac)|"
    r"[\uac00-\ud7a3]{1,16}(?:\ub85c|\uae38|\ubc88\uae38)"
)
_DATE_RE = re.compile(
    r"(?<!\d)(\d{4})\s*\ub144\s*(\d{1,2})\s*\uc6d4\s*(\d{1,2})\s*\uc77c"
    r"|(?<!\d)(\d{4})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})(?!\d)"
    r"|(?<!\d)(\d{2})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})(?!\d)"
)
_SUPPLY_AMOUNT_ANCHOR_RE = re.compile(
    r"\uacf5\s*\uae09\s*\uac00\s*\uc561|\uacf5\s*\uae09\s*\uc561|\uacf5\s*\uae09\s*\uae08\s*\uc561|"
    r"\uacf5\s*\uae09\s*\ub300\s*\uac00|\uacf5\s*\uae09\s*\uac00(?![\uac00-\ud7a3])"
)
_TAX_AMOUNT_ANCHOR_RE = re.compile(
    r"\uc138\s*\uc561|\uc0c8\s*\uc561|\uc138\s*\uc775|\uc138\s*\uc545|"
    r"\ubd80\s*\uac00\s*\uc138|\ubd80\s*\uac00\s*\uc11c|\ubd80\s*\uac00\s*\uac00\s*\uce58\s*\uc138|"
    r"\bVAT\b|\bV\.A\.T\b",
    re.I,
)
_TOTAL_AMOUNT_ANCHOR_RE = re.compile(
    r"\ud569\s*\uacc4|\ucd1d\s*\uacc4|\ucd1d\s*\ud569\s*\uacc4|\ucd1d\s*\uae08\s*\uc561|"
    r"\ucd1d\s*\uc561|\ucd1d\s*\uacb0\s*\uc81c\s*\uc561|\uacf5\s*\uae09\s*\ub300\s*\uac00|"
    r"\uccad\s*\uad6c\s*\uae08\s*\uc561|\uccad\s*\uad6c\s*\uc561|\uacb0\s*\uc81c\s*\uae08\s*\uc561|"
    r"\ud569\s*\uacc4\s*\uae08\s*\uc561|\bTOTAL\b",
    re.I,
)
_SUMMARY_SUPPLY_LABEL_RE = re.compile(
    r"\uacf5\s*\uae09\s*\uac00\s*\uc561|\uacf5\s*\uae09\s*\uc561|\uacf5\s*\uae09\s*\uae08\s*\uc561|"
    r"\uacf5\s*\uae09\s*\uac00(?![\uac00-\ud7a3])|\uacfc\s*\uc138\s*\uae08\s*\uc561|"
    r"\ub9e4\s*\ucd9c\s*\uc561|\uc21c\s*\ub9e4\s*\ucd9c"
)
_SUMMARY_WEAK_SUPPLY_LABEL_RE = re.compile(r"\uc18c\s*\uacc4|\uacfc\s*\uc138")
_SUMMARY_TAX_LABEL_RE = re.compile(
    r"\uc138\s*\uc561|\uc0c8\s*\uc561|\uc138\s*\uc775|\uc138\s*\uc545|"
    r"\ubd80\s*\uac00\s*\uc138|\ubd80\s*\uac00\s*\uc11c|\ubd80\s*\uac00\s*\uac00\s*\uce58\s*\uc138|"
    r"\bVAT\b|\bV\.A\.T\b|\bTAX\b",
    re.I,
)
_SUMMARY_TOTAL_LABEL_RE = re.compile(
    r"\ud569\s*\uacc4|\ucd1d\s*\uacc4|\ucd1d\s*\ud569\s*\uacc4|\ucd1d\s*\uae08\s*\uc561|"
    r"\ucd1d\s*\uc561|\uccad\s*\uad6c\s*\uae08\s*\uc561|\uccad\s*\uad6c\s*\uc561|"
    r"\uacb0\s*\uc81c\s*\uae08\s*\uc561|\ucd1d\s*\uacf5\s*\uae09\s*\ub300\s*\uac00|"
    r"\uacf5\s*\uae09\s*\ub300\s*\uac00|\ud569\s*\uacc4\s*\uae08\s*\uc561|\bTOTAL\b",
    re.I,
)
_PROFILE_SUMMARY_FIELD_LABELS: dict[str, re.Pattern] = {
    "subtotal": re.compile(r"\uc18c\s*\uacc4"),
    "cumulativeAmount": re.compile(r"(?:\ub204|ㄴ)\s*\uacc4(?!\s*\uc794\s*\uc561)"),
    "previousBalance": re.compile(r"\uc804\s*\uc77c\s*\uc794\s*\uc561"),
    "transactionAmount": re.compile(r"(?:\ub2f9\s*\uc77c|\uae08\s*\uc77c)\s*\uac70\s*\ub798\s*\uae08\s*\uc561"),
    "cumulativeBalance": re.compile(r"\ub204\s*\uacc4\s*\uc794\s*\uc561"),
    "totalQuantity": re.compile(r"\ucd1d\s*\uc218\s*\ub7c9"),
}
_PROFILE_SUMMARY_AMOUNT_FIELDS = {
    "subtotal",
    "cumulativeAmount",
    "previousBalance",
    "transactionAmount",
    "cumulativeBalance",
}
_SUMMARY_FIELD_KEYS = (
    "subtotal",
    "cumulativeAmount",
    "previousBalance",
    "transactionAmount",
    "cumulativeBalance",
    "totalQuantity",
)
_CODE_LOT_SERIAL_RE = re.compile(
    r"\bLot\s*No\b|\bSerial\b|\uc2dc\s*\ub9ac\s*\uc5bc|\ub85c\s*\ud2b8|"
    r"\uc81c\s*\uc870\s*\ubc88\s*\ud638|\uc720\s*\ud6a8\s*(?:\uae30\s*\uac04|\uc77c\s*\uc790)|"
    r"\ud488\s*\ubaa9\s*\ucf54\s*\ub4dc|\uc81c\s*\ud488\s*\ucf54\s*\ub4dc|"
    r"[A-Z]\d{5,}|\d{5,}\s*[-/]\s*\d{5,}|\d{6,}\s*[-/]\s*\d{6,}\s*[-/]\s*\d{6,}",
    re.I,
)
_TABLE_SUMMARY_RE = re.compile(
    r"\uacf5\s*\uae09\s*\uae08\s*\uc561|\uacf5\s*\uae09\s*\uac00\s*\uc561|\uacf5\s*\uae09\s*\uc561|"
    r"\uacf5\s*\uae09\s*\uac00\ub825|\uacf5\s*\uae09\s*\ub300\s*\uac00|\uc138\s*\uc561|\uc0c8\s*\uc561|"
    r"\uc138\s*\uc775|\uc138\s*\uc545|\ubd80\s*\uac00\s*\uc138|\ubd80\s*\uac00\s*\uc11c|VAT|"
    r"\ud569\s*\uacc4|\ud568\s*\uacc4|\ud569\s*\uacc4\s*\uae08\s*\uc561|\ucd1d\s*\uacb0\s*\uc81c\s*\uc561|"
    r"\uccad\s*\uad6c\s*\uae08\s*\uc561|\uacb0\s*\uc81c\s*\uae08\s*\uc561|\uc794\s*\uc561|\ub204\s*\uacc4|"
    r"\uc778\uc218\s*\ud655\uc778|\uc778\uc218\uc790|\ucc3d\s*\uace0|Page|Fa:|\ud398\uc774\uc9c0|TOTAL",
    re.I,
)
_TABLE_HEADER_TOKEN_RE = re.compile(
    r"\ud488\s*\uba85|\ud488\s*\ubaa9|\uaddc\s*\uaca9|\uc218\s*\ub7c9|\ub2e8\s*\uac00|"
    r"\uacf5\uae09\s*\uac00\uc561|\uc138\s*\uc561|\ud569\s*\uacc4|\uae08\s*\uc561|"
    r"\ube44\s*\uace0|\uc81c\uc870\s*\ubc88\ud638|\uc720\ud6a8\s*\uae30\uac04|\ubcf4\ud5d8\s*\ucf54\ub4dc"
)
_COMPANY_HINT_RE = re.compile(
    r"\uc8fc\uc2dd\ud68c\uc0ac|\uc8fc\uc2dd\s*\ud76c\uc0ac|\(\s*\uc8fc\s*\)?|\uc8fc\)|\uc720\)|"
    r"\uc57d\s*\ud488|\uc784\ud50c\ub780\ud2b8|\ud68c\uc0ac|\uc9c0\uc810|\uc608\uc77c\uc120"
)
_COMPANY_REJECT_RE = re.compile(
    r"\uacf5\uae09\uae08\uc561|\uacf5\uae09\uac00\uc561|\uc18c\ube44\uc790\uae08\uc561|\ud569\uacc4|"
    r"\uc794\uc561|\ud488\ubaa9|\ud488\uba85|\ucf54\ub4dc|\uac70\ub798\uc77c\uc790|\uc8fc\ubb38\uc77c\uc790|"
    r"\uc601\uc5c5\uc9c0\uc810|\uc601\uc5c5\uc0ac\uc6d0|\uc57d\uc815|\ucc44\uad8c|\uc774\ud558\uc5ec\ubc31|"
    r"\ucc3d\uace0|FAX|Page|Fa:"
)
_ITEM_NAME_HINT_RE = re.compile(r"\uc815|\ucea1\uc290|\ucea1\uc2ac|\ud06c\ub9bc|\uc561|mg|ml|g|T|C", re.I)
_HEADER_LABEL_RE = re.compile(
    r"\uac70\ub798\uba85\uc138\uc11c?|\uac70\ub798\uba85\uc138\ud45c|\uacf5\uae09\uc790|\uacf5\uae09\ubc1b\ub294\uc790|"
    r"\uc0ac\uc5c5\uc790|\ub4f1\ub85d\ubc88\ud638|\ub300\ud45c\uc790|\uc8fc\uc18c|\uc18c\uc7ac\uc9c0|"
    r"\uc791\uc131|\ub144|\uc6d4|\uc77c|\uadc0\ud558|\ubc95\uc778\uba85|\uc0c1\ud638|\uc131\uba85"
)
_ADDRESS_HINT_RE = re.compile(
    r"\uc11c\uc6b8|\uacbd\uae30|\uc778\ucc9c|\ubd80\uc0b0|\ub300\uad6c|\uad11\uc8fc|\ub300\uc804|"
    r"\uc6b8\uc0b0|\uc138\uc885|\uac15\uc6d0|\ucda9\ubd81|\ucda9\ub0a8|\uc804\ubd81|\uc804\ub0a8|"
    r"\uacbd\ubd81|\uacbd\ub0a8|\uc81c\uc8fc"
)
_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
_ASCII_WORD_RE = re.compile(r"[A-Za-z]{2,}")
_TABLE_BUSINESS_CONTACT_RE = re.compile(
    r"\uc0ac\s*\uc5c5\s*\uc790\s*\ubc88\s*\ud638|\ub4f1\s*\ub85d\s*\ubc88\s*\ud638|"
    r"\ub300\s*\ud45c\s*\uc790|\uc8fc\s*\uc18c|\uc804\s*\ud654|\uc774\s*\uba54\s*\uc77c|"
    r"\uc5c5\s*\ud0dc|\uc885\s*\ubaa9|\uacf5\s*\uae09\s*\uc790|\uacf5\s*\uae09\s*\ubc1b\s*\ub294\s*\uc790|"
    r"\uac70\s*\ub798\s*\ucc98|\uadc0\s*\ud558|\uc0ac\s*\uc5c5\s*\uc7a5|\uacc4\s*\uc88c\s*\ubc88\s*\ud638|"
    r"\uc601\s*\uc5c5\s*\uc9c0\s*\uc810|\uc601\s*\uc5c5\s*\uc0ac\s*\uc6d0|\ub2f4\s*\ub2f9\s*\uc790|"
    r"\uc0c1\s*\ud638|\ubc95\s*\uc778\s*\uba85|"
    r"\uc5f0\s*\ub77d\s*\ucc98|TEL|FAX|E-?mail|Page|Fa:",
    re.I,
)
_TABLE_SUMMARY_STRONG_RE = re.compile(
    r"\ud569\s*\uacc4|\uc18c\s*\uacc4|\ucd1d\s*\uacc4|\ucd1d\s*\ud569\s*\uacc4|\uacf5\s*\uae09\s*\uac00\s*\uc561|"
    r"\uacf5\s*\uae09\s*\uac00\s*\ub825|\uacf5\s*\uae09\s*\uae08\s*\uc561|\uacf5\s*\uae09\s*\ub300\s*\uac00|\uc138\s*\uc561|"
    r"\ubd80\s*\uac00\s*\uc138|\ubd80\s*\uac00\s*\uac00\s*\uce58\s*\uc138|\uc138\s*\uc5ed|\uccad\s*\uad6c\s*\uae08\s*\uc561|"
    r"\uacb0\s*\uc81c\s*\uae08\s*\uc561|\ucd1d\s*\uacb0\s*\uc81c\s*\uc561|\uc794\s*\uc561|\ub204\s*\uacc4|"
    r"\ubbf8\s*\uc218|\uc778\s*\uc218\s*\ud655\s*\uc778|\ub2f4\s*\ub2f9\s*\uc790|TOTAL",
    re.I,
)
_TABLE_HEADER_STRONG_RE = re.compile(
    r"\ud488\s*\uba85|\ud488\s*\ubaa9|\ud488\s*\ubaa9\s*\uba85|\uaddc\s*\uaca9|\uc218\s*\ub7c9|"
    r"\ub2e8\s*\uc704|\ub2e8\s*\uac00|\uacf5\s*\uae09\s*\uac00\s*\uc561|\uacf5\s*\uae09\s*\uae08\s*\uc561|"
    r"\uae08\s*\uc561|\uc138\s*\uc561|\ubd80\s*\uac00\s*\uc138|\ud569\s*\uacc4|\ube44\s*\uace0|"
    r"\uc81c\s*\uc870\s*\ubc88\s*\ud638|\uc720\s*\ud6a8\s*\uae30\s*\uac04|\ubcf4\s*\ud5d8\s*\ucf54\s*\ub4dc|"
    r"\ud488\s*\ubaa9\s*\ucf54\s*\ub4dc",
    re.I,
)
_TABLE_STANDALONE_LABEL_RE = re.compile(
    r"^(?:\ud488\s*\uba85|\ud488\s*\ubaa9|\ud488\s*\ubaa9\s*\uba85|\uaddc\s*\uaca9|\uc218\s*\ub7c9|"
    r"\ub2e8\s*\uc704|\ub2e8\s*\uac00|\uacf5\s*\uae09\s*\uac00\s*\uc561|\uacf5\s*\uae09\s*\uae08\s*\uc561|"
    r"\uae08\s*\uc561|\uc138\s*\uc561|\ubd80\s*\uac00\s*\uc138|\ud569\s*\uacc4|\ube44\s*\uace0|"
    r"\uc0c1\s*\ud638|\uc8fc\s*\uc18c|\uc131\s*\uba85|\uc0ac\s*\uc5c5\s*\uc790\s*\ubc88\s*\ud638|"
    r"\uac70\s*\ub798\s*\uc77c\s*\uc790|\uc8fc\s*\ubb38\s*\uc77c\s*\uc790|\uc5f0\s*\ub77d\s*\ucc98|"
    r"\ucc3d\s*\uace0|\uc601\s*\uc5c5\s*\uc0ac\s*\uc6d0|\uc601\s*\uc5c5\s*\uc9c0\s*\uc810)$",
    re.I,
)
_SPEC_ONLY_RE = re.compile(r"^\d+(?:[.,]\d+)?(?:mg|ml|g|kg|t|tab|cap|caps?|c|\uc815|\ucea1\uc290|\ud3ec|\ubcd1|box|ea|p|dose|mI)(?:\([^)]+\))?$", re.I)
# T-6n: OP-* pharmaceutical item code pattern (handles OCR noise like "0P", "11OP-", "120P-")
_OP_ANCHOR_CODE_RE = re.compile(r"(?<![A-Za-z])((?:OP|0P)[-\s]?[A-Z][A-Za-z0-9]{2,})", re.I)

# T-3: canonical tableRows
_TABLE_ROW_COLUMNS = [
    "rowIndex", "itemCode", "itemName", "spec", "lotNo", "serialNo",
    "manufacturingNo", "expiryDate", "quantity", "unit", "unitPrice",
    "supplyAmount", "taxAmount", "amount", "totalAmount", "manufacturer",
    "insuranceCode", "remark",
]
_TR_EXPIRY_YYYYMMDD_RE = re.compile(r"(?<!\d)(20\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01]))(?!\d)")
_TR_EXPIRY_YYMMDD_RE = re.compile(r"(?<!\d)(\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01]))(?!\d)")
_TR_EXPIRY_YMDASH_RE = re.compile(r"(?<!\d)(20\d{2}[-./](?:0[1-9]|1[0-2])[-./](?:0[1-9]|[12]\d|3[01]))(?!\d)")
_TR_SERIAL_HYPHEN_RE = re.compile(r"(?<![A-Z0-9])(\d{6,}[-/]\d{6,}[-/]\d{6,})(?![A-Z0-9])", re.I)
_TR_ITEM_CODE_RE = re.compile(r"\b((?:[A-Z]{2,6}-)?[A-Z]{1,5}\d{3,}[A-Z0-9]*)\b")
_TR_AMOUNT_COMMA_RE = re.compile(r"\d{1,3}(?:,\d{3})+")
_TR_UNIT_RE = re.compile(r"\b(BOX|EA)\b", re.I)

# T-6/T-6c: header cell text → canonical table column mapping
# 순서 중요: 더 specific한 패턴을 먼저 (품목코드 > 품명, 합계금액 > 금액, 소비자단가 > 단가)
_HEADER_CANONICAL_MAP: list[tuple[re.Pattern[str], str]] = [
    # rowIndex — NO/순번 column (leftmost, must be first to prevent itemCode pollution)
    (re.compile(r"^(?:NO|No|no)\.?$|^순\s*번$|^번\s*호$|^N[Oo]$", re.I), "rowIndex"),
    # itemCode — 품목코드/제품코드/상품코드 (먼저 확인해 '품목' 단독보다 우선)
    (re.compile(r"품\s*목\s*코\s*드|제\s*품\s*코\s*드|상\s*품\s*코\s*드|item\s*code|product\s*code", re.I), "itemCode"),
    # insuranceCode — 보험코드/보험No 계열 (보험약가 포함, 공급가액보다 먼저)
    (re.compile(r"보\s*험\s*No|보\s*험\s*NO|보\s*험\s*번\s*호|보\s*험\s*코\s*드|보\s*험\s*약\s*가", re.I), "insuranceCode"),
    # manufacturer — 제조회사/제조사/제조원/제조업체
    (re.compile(r"제\s*조\s*회\s*사|제\s*조\s*사|제\s*조\s*원|제\s*조\s*업\s*체", re.I), "manufacturer"),
    # manufacturingNo — 제조번호 계열 (composite 헤더 포함: 제조번호/유효기간)
    (re.compile(r"제\s*조\s*번\s*호[/·\s]*유\s*효|유\s*효[/·\s]*제\s*조\s*번\s*호", re.I), "manufacturingNo"),  # composite 먼저
    (re.compile(r"제\s*조\s*번\s*호|제\s*조\s*No", re.I), "manufacturingNo"),
    # expiryDate — 유효기간/유효일자/사용기한
    (re.compile(r"유\s*효\s*기\s*간|유\s*효\s*일\s*자|사\s*용\s*기\s*한|유\s*효\s*기\s*한", re.I), "expiryDate"),
    # serialNo — Serial/S/N/시리얼 (composite 포함: 시리얼/로트No.)
    (re.compile(r"시\s*리\s*얼[/·\s]*로\s*트|Serial\s*[/·]\s*[Ll]ot", re.I), "serialNo"),  # composite 먼저
    (re.compile(r"Serial\s*(?:No|번\s*호)?|S\s*/\s*N|시\s*리\s*얼", re.I), "serialNo"),
    # lotNo — Lot/LOT/로트 계열 (LotNo, LOTNO 포함)
    (re.compile(r"Lot\s*[./]?\s*No|LOT\s*[./]?\s*No|LOTNO|LotNo|LOT[./\s]*제\s*조|로\s*트\s*[Nn][Oo]?|로\s*트|(?<!\w)LOT(?!\w)|(?<!\w)Lot(?!\w)", re.I), "lotNo"),
    # itemName — 품목/품명/제품명/상품명 (품목코드 다음에 위치)
    (re.compile(r"품\s*목\s*명|품\s*목(?!\s*[코코드])|품\s*명|제\s*품\s*명|상\s*품\s*명|명\s*칭|제\s*품(?!\s*[코])", re.I), "itemName"),
    # spec — 규격/모델
    (re.compile(r"규\s*격|모\s*델\s*명?", re.I), "spec"),
    # quantity — 수량/Qty
    (re.compile(r"수\s*량|(?<!\w)Qty(?!\w)|(?<!\w)QTY(?!\w)", re.I), "quantity"),
    # unit — 단위
    (re.compile(r"단\s*위|(?<!\w)Unit(?!\w)", re.I), "unit"),
    # unitPrice — 소비자단가/공급단가/판매단가/단가 (specific 먼저)
    (re.compile(r"소\s*비\s*자\s*단\s*가|공\s*급\s*단\s*가|판\s*매\s*단\s*가|단\s*가", re.I), "unitPrice"),
    # supplyAmount — 공급가액/공급금액/공급가 (summary와 헷갈리지 않도록 row context 기준)
    (re.compile(r"공\s*급\s*가\s*액|공\s*급\s*금\s*액|공\s*급\s*가(?![가-힣])", re.I), "supplyAmount"),
    # taxAmount — 세액/부가세/VAT
    (re.compile(r"세\s*액|부\s*가\s*세|(?<!\w)VAT(?!\w)|(?<!\w)TAX(?!\w)", re.I), "taxAmount"),
    # totalAmount — 합계금액/총금액 (금액보다 먼저)
    (re.compile(r"합\s*계\s*금\s*액|총\s*금\s*액|총\s*합\s*계", re.I), "totalAmount"),
    # amount — 금액/판매금액 (합계금액 다음에 위치)
    (re.compile(r"금\s*액|판\s*매\s*금\s*액", re.I), "amount"),
    # remark — 비고/적요
    (re.compile(r"비\s*고|적\s*요|메\s*모|참\s*고", re.I), "remark"),
]

# T-6e: expected column aliases — reverse lookup for header band detection.
# For each canonical key, these are the known OCR header text variants.
_EXPECTED_COLUMN_ALIASES: dict[str, list[str]] = {
    "rowIndex":        ["NO", "No", "순번", "번호"],
    "itemCode":        ["품목코드", "제품코드", "상품코드", "코드"],
    "itemName":        ["품목", "품명", "품목명", "제품명", "상품명", "명칭", "제품"],
    "spec":            ["규격", "규 격"],
    "lotNo":           ["LotNo", "Lot No", "LOTNO", "LOT", "로트", "로트No", "Lot"],
    "serialNo":        ["시리얼", "Serial", "S/N", "시리얼/로트No", "Serial/Lot"],
    "manufacturingNo": ["제조번호", "제조 No", "제조NO", "제조번호/유효기간"],
    "expiryDate":      ["유효기간", "유효일자", "유효기한", "사용기한", "제조번호/유효기간"],
    "quantity":        ["수량", "수 량", "Qty", "QTY"],
    "unit":            ["단위", "Unit"],
    "unitPrice":       ["단가", "소비자단가", "공급단가", "판매단가"],
    "supplyAmount":    ["공급금액", "공급가액", "공급가"],
    "taxAmount":       ["세액", "부가세", "VAT"],
    "amount":          ["금액", "판매금액"],
    "totalAmount":     ["합계금액", "합계", "총액"],
    "manufacturer":    ["제조회사", "제조사", "제조원"],
    "insuranceCode":   ["보험No", "보험NO", "보험번호", "보험코드"],
    "remark":          ["비고", "적요", "참고"],
}


@dataclass
class OcrLine:
    pts: list
    text: str
    confidence: float
    x: float
    y: float
    w: float
    h: float
    cx: float
    cy: float


@dataclass
class SummaryAmountCandidate:
    value: str
    numeric: int
    row_idx: int
    cy: float
    x: float
    text: str
    context: str
    supply_anchor: bool
    tax_anchor: bool
    total_anchor: bool


def _line_from_raw(raw: tuple) -> OcrLine | None:
    pts, text, confidence = raw
    text = (text or "").strip()
    if not text:
        return None
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    x = min(xs)
    y = min(ys)
    w = max(xs) - x
    h = max(ys) - y
    if w <= 0 or h <= 0:
        return None
    return OcrLine(pts, text, float(confidence), x, y, w, h, x + w / 2, y + h / 2)


def _canonical_digits(text: str) -> str:
    return (
        (text or "")
        .replace("O", "0")
        .replace("o", "0")
        .replace("I", "1")
        .replace("l", "1")
        .replace("S", "5")
        .replace("B", "8")
    )


def _format_biz(text: str) -> str:
    match = _BIZ_RE.search(_canonical_digits(text))
    if not match:
        return ""
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def _amount_values(text: str) -> list[str]:
    values: list[str] = []
    for match in _AMOUNT_RE.finditer(_canonical_digits(text)):
        digits = re.sub(r"\D", "", match.group(1))
        if not digits or re.fullmatch(r"(?:19|20)\d{6}", digits):
            continue
        value = int(digits)
        if 100 <= value <= 1_000_000_000:
            values.append(f"{value:,}")
    return values


def _amount_value(text: str) -> str:
    values = _amount_values(text)
    return values[-1] if values else ""


def _clean_value(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"^[\s:：;|ㆍ.\-()\[\]]+", "", value)
    value = re.sub(r"[\s:：;|ㆍ.\-()\[\]]+$", "", value)
    return value.strip()


def _strip_inline_noise(text: str) -> str:
    value = _PHONE_RE.sub("", text or "")
    value = _BIZ_RE.sub("", _canonical_digits(value))
    value = re.sub(r"\d{4}[./-]\d{1,2}[./-]\d{1,2}.*$", "", value)
    return _clean_value(value)


def _clean_company_candidate(text: str) -> str:
    value = _strip_inline_noise(text)
    value = re.sub(
        r"^(?:\uc0c1\s*\ud638(?:\uba85)?|\ubc95\uc778\uba85|\uac70\ub798\ucc98\uba85|\ub0a9\ud488\ucc98|"
        r"\ud310\ub9e4\uc790|\uacf5\uae09\uc790)\s*[:：]?",
        "",
        value,
    )
    value = _clean_value(value)
    hint = _COMPANY_HINT_RE.search(value)
    if hint:
        if hint.group(0).startswith("\uc8fc\uc2dd\ud68c\uc0ac"):
            m = re.search(r"\uc8fc\uc2dd\ud68c\uc0ac[\uac00-\ud7a3A-Za-z0-9()&.\s]{1,24}", value)
            if m:
                value = m.group(0)
        elif "(\uc8fc" in re.sub(r"\s+", "", value) or "\uc8fc)" in value:
            m = re.search(r"[\uac00-\ud7a3A-Za-z0-9&.\s]{1,24}(?:\(\s*\uc8fc\s*\)|\uc8fc\))[\uac00-\ud7a3A-Za-z0-9&.\s]{0,16}", value)
            if m:
                value = m.group(0)
    value = re.sub(r"[^가-힣A-Za-z0-9()&.\s]", "", value)
    return _clean_value(value)


def _candidate_ok(value: str, kind: str) -> bool:
    value = _clean_value(value)
    compact = re.sub(r"\s+", "", value)
    if len(compact) < 2:
        return False
    if kind == "company":
        if _COMPANY_REJECT_RE.search(value) or _HEADER_LABEL_RE.fullmatch(compact):
            return False
        if _ADDRESS_HINT_RE.search(value):
            return False
        if not _COMPANY_HINT_RE.search(value):
            return False
        if not re.search(r"[가-힣]", value):
            return False
        if re.search(r"\d", value) and not _COMPANY_HINT_RE.search(value):
            return False
        return len(compact) <= 38
    if kind == "representative":
        return bool(re.fullmatch(r"[가-힣A-Za-z\s]{2,20}", value)) and not _HEADER_LABEL_RE.search(value)
    if kind == "address":
        return bool(_ADDRESS_HINT_RE.search(value)) and len(compact) >= 6
    return True


def _group_rows(lines: list[OcrLine], tolerance_factor: float = 0.75) -> list[list[OcrLine]]:
    rows: list[list[OcrLine]] = []
    for line in sorted(lines, key=lambda item: (item.cy, item.x)):
        if not rows:
            rows.append([line])
            continue
        current = rows[-1]
        avg_y = sum(item.cy for item in current) / len(current)
        avg_h = sum(item.h for item in current) / len(current)
        if abs(line.cy - avg_y) <= max(avg_h, line.h) * tolerance_factor:
            current.append(line)
        else:
            rows.append([line])
    return [sorted(row, key=lambda item: item.x) for row in rows]


def _row_text(row: list[OcrLine]) -> str:
    return " ".join(line.text for line in sorted(row, key=lambda item: item.x)).strip()


def _table_token_count(text: str) -> int:
    compact = re.sub(r"\s+", "", text or "")
    return len(_TABLE_HEADER_TOKEN_RE.findall(compact))


def _text_has_name_signal(text: str) -> bool:
    return bool(_HANGUL_RE.search(text or "") or _ASCII_WORD_RE.search(text or ""))


def _is_business_contact_line(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    if _TABLE_STANDALONE_LABEL_RE.fullmatch(compact):
        return True
    return bool(
        _TABLE_BUSINESS_CONTACT_RE.search(text)
        or _ADDRESS_HINT_RE.search(text)
        or re.search(r"[\uac00-\ud7a3]{1,12}(?:\ub85c|\uae38)\s*\d", compact)
        or re.search(r"\d+\s*\([\uac00-\ud7a3]{1,12}\ub3d9\)", compact)
        or _BIZ_RE.search(_canonical_digits(text))
        or _PHONE_RE.search(text)
        or re.fullmatch(r"(?:\d{1,4}[-./]){2,}\d{1,6}", compact)
    )


def _is_table_header_row(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    if _TABLE_STANDALONE_LABEL_RE.fullmatch(compact):
        return True
    token_count = len(_TABLE_HEADER_STRONG_RE.findall(compact))
    digit_count = len(re.findall(r"\d", compact))
    return token_count >= 2 and digit_count <= 2


def _is_summary_row_for_items(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    if not _TABLE_SUMMARY_STRONG_RE.search(text):
        return False
    if _is_table_header_row(text):
        return True
    name_chars = len(re.findall(r"[\uac00-\ud7a3A-Za-z]", compact))
    amount_count = len(_amount_values(text))
    # A strong summary label with mostly numeric content should not become an item row.
    if amount_count >= 1 and name_chars <= 14:
        return True
    return bool(re.fullmatch(r"(?:TOTAL|[\uac00-\ud7a3\s]*(?:\ud569\uacc4|\ucd1d\uacc4|VAT|TOTAL)[\uac00-\ud7a3\s]*)[:\-\s0-9,.]*", text, re.I))


def _has_non_name_table_anchor(item: dict[str, Any]) -> bool:
    for key in (
        "itemCode", "spec", "lotNo", "serialNo", "manufacturingNo", "expiryDate",
        "quantity", "unit", "unitPrice", "supplyAmount", "taxAmount", "amount",
        "totalAmount", "manufacturer", "insuranceCode", "remark",
        "serialLotComposite", "manufacturingExpiryComposite",
    ):
        if str(item.get(key) or "").strip():
            return True
    return False


def _is_item_name_only_split_row(item: dict[str, Any], accepted_count: int) -> bool:
    if accepted_count <= 0:
        return False
    if not str(item.get("itemName") or "").strip():
        return False
    return not _has_non_name_table_anchor(item)


def _is_bad_table_data_row(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    return bool(
        not compact
        or _is_business_contact_line(text)
        or _is_summary_row_for_items(text)
        or _HEADER_LABEL_RE.search(text)
        or _ADDRESS_HINT_RE.search(text)
        or _TOTAL_AMOUNT_ANCHOR_RE.search(text)
        or _TABLE_SUMMARY_RE.search(text)
        or _BIZ_RE.search(_canonical_digits(text))
        or _PHONE_RE.search(text)
        or re.search(r"(?:\ub85c|길)\d+|\d+\([가-힣]+동\)|[가-힣]+동\)", compact)
        or re.search(r"\uc0ac\uc5c5\uc7a5|\uc8fc\uc18c|\uc131\uba85|\ub300\ud45c|\uc138\uc561|\ud569\uacc4|FAX|TEL|Page|\ucc3d\uace0|\uc778\uc218\ud655\uc778", text)
    )


def _is_table_header_only_row(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    if _is_table_header_row(text):
        return True
    token_count = _table_token_count(compact)
    digit_count = len(re.findall(r"\d", compact))
    return token_count >= 2 and digit_count <= 1


def _is_numeric_detail_line(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact or _is_business_contact_line(text) or _is_table_header_row(text) or _is_summary_row_for_items(text):
        return False
    digit_count = len(re.findall(r"\d", compact))
    if digit_count == 0:
        return False
    alpha_count = len(re.findall(r"[A-Za-z\uac00-\ud7a3]", compact))
    if re.search(r"TABLET|ABLET|CAPSULE|CAPS?|TAB|CAP", text or "", re.I) and alpha_count > digit_count:
        return False
    if _amount_values(text):
        return True
    if _SPEC_ONLY_RE.fullmatch(compact):
        return True
    if re.fullmatch(r"[A-Z0-9][A-Z0-9_\-/.]{1,24}", compact, re.I):
        return True
    return digit_count >= max(1, alpha_count)


def _is_probable_item_name_line(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if len(compact) < 2 or len(compact) > 90:
        return False
    if _is_business_contact_line(text) or _is_table_header_row(text) or _is_summary_row_for_items(text):
        return False
    if _COMPANY_HINT_RE.search(text) and not re.search(r"mg|ml|g|T|C|BOX|CAP|TAB|\uc815|\ucea1|\uc561|\ud06c\ub9bc", text, re.I):
        return False
    if re.fullmatch(r"[0-9,.\-_/()]+", compact):
        return False
    if _SPEC_ONLY_RE.fullmatch(compact):
        return False
    if _is_code_only_table_row(text):
        return False
    if re.fullmatch(r"[A-Z0-9_\-/.]{2,24}", compact, re.I) and not re.search(r"TABLET|CAPSULE|CAPS?|ABLET|TAB|CAP", compact, re.I):
        return False
    return _text_has_name_signal(text)


def _is_item_name_like(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if _is_probable_item_name_line(text):
        return True
    if len(compact) < 3 or len(compact) > 70:
        return False
    if _is_bad_table_data_row(text) or _is_table_header_only_row(text):
        return False
    if _COMPANY_HINT_RE.search(text) or re.search(r"\ub300\ud45c|\ub2f4\ub2f9|\uac70\ub798\ucc98|\uc8fc\ubb38", text):
        return False
    if _ADDRESS_HINT_RE.search(text) or re.search(r"(?:\ub85c|길)\d+|\d+\([가-힣]+동\)|[가-힣]+동\)", compact):
        return False
    if re.fullmatch(r"[A-Za-z0-9,.\-_/()]+", compact):
        return False
    if re.search(r"\d", compact) and re.search(r"mg|ml|g|T|C|\d{2,}", compact, re.I):
        return bool(re.search(r"[가-힣]", compact) or re.search(r"[A-Za-z]{3,}", compact))
    return bool(re.search(r"[가-힣A-Za-z0-9]{2,}(?:정|액|캡슐|캡슬|산|크림|겔|시럽|플란정)$", compact))


def _is_code_only_table_row(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if re.search(r"TABLET|ABLET|CAPSULE|CAPS?|TAB|CAP|\ucea1\uc290|\ucea1\uc2ac|mg|ml", text or "", re.I):
        return False
    return bool(
        re.fullmatch(r"[A-Z]{2,}[A-Z0-9_\-/.]{2,18}", compact)
        or re.fullmatch(r"[A-Z]+-[A-Z0-9_\-/.]{2,18}", compact)
        or re.fullmatch(r"\d{2,5}[-/.]\d{2,5}", compact)
    )


def _nearby_numeric_tail(rows: list[list[OcrLine]], start_idx: int, page_h: float) -> str:
    tail: list[str] = []
    base_y = sum(item.cy for item in rows[start_idx]) / len(rows[start_idx])
    for row in rows[start_idx + 1 : start_idx + 5]:
        row_y = sum(item.cy for item in row) / len(row)
        if row_y - base_y > page_h * 0.10:
            break
        text = _row_text(row)
        if _is_bad_table_data_row(text) or _is_table_header_only_row(text):
            continue
        if re.search(r"\d", text):
            tail.append(text)
        if len(tail) >= 3:
            break
    return " ".join(tail)


def _table_data_candidate_text(rows: list[list[OcrLine]], idx: int, page_h: float) -> str:
    text = _row_text(rows[idx])
    if _is_bad_table_data_row(text) or _is_table_header_only_row(text):
        return ""
    if _is_code_only_table_row(text):
        return ""
    if not re.search(r"[가-힣]", text) and not re.search(r"TABLET|CAPSULE|CAPS?|ABLET", text, re.I):
        return ""
    if re.search(r"\d", text) and _table_row_score(text) > 0:
        return text
    if _is_item_name_like(text):
        tail = _nearby_numeric_tail(rows, idx, page_h)
        if tail:
            return f"{text} {tail}".strip()
    return ""


def _text_order_table_fallback(lines: list[OcrLine]) -> list[str]:
    item_texts: list[str] = []
    for line in lines:
        text = _clean_value(line.text)
        if _is_item_name_like(text):
            item_texts.append(text)
    if not item_texts:
        return []
    return item_texts


def _table_row_score(text: str) -> float:
    if _is_bad_table_data_row(text):
        return -999.0
    score = 0.0
    amount_count = len(_amount_values(text))
    digit_count = len(re.findall(r"\d", text))
    hangul_count = len(re.findall(r"[가-힣]", text))
    score += min(amount_count, 3) * 4
    score += min(digit_count, 20) * 0.15
    score += min(hangul_count, 20) * 0.12
    if _ITEM_NAME_HINT_RE.search(text):
        score += 7
    if re.search(r"[가-힣]", text) and re.search(r"\d", text):
        score += 4
    if len(_amount_values(text)) >= 2 and not _ITEM_NAME_HINT_RE.search(text):
        score -= 4
    if len(text) > 120:
        score -= 2
    return score


def _summarize_table_row(text: str) -> str:
    parts = text.split()
    if len(parts) <= 10:
        return text[:120]
    head = parts[:4]
    tail = [p for p in parts[4:] if re.search(r"\d|,|[A-Za-z]", p)][:8]
    return " ".join(head + tail)[:120]


def _has_product_hint(text: str) -> bool:
    return bool(
        re.search(
            r"(?:\uc815|\uc561|\ud06c\ub9bc|\uc2dc\ub7fd|\uac94)$|"
            r"\ucea1\uc290|\ucea1\uc2ac|TABLET|ABLET|CAPSULE|CAPS?|"
            r"\d+(?:[.,]\d+)?\s*(?:mg|ml|g|kg|t|c|p|tab|cap|dose)",
            text or "",
            re.I,
        )
    )


def _is_compact_catalog_code(text: str) -> bool:
    compact = re.sub(r"[\s._\-/]+", "", text or "")
    return bool(
        not _HANGUL_RE.search(compact)
        and re.fullmatch(r"[A-Z]{2,}\d+[A-Z0-9]{0,10}", compact, re.I)
        and not re.search(r"TABLET|ABLET|CAPSULE|CAPS?|TAB|CAP", text or "", re.I)
    )


def _dedupe_table_rows(rows: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for text in rows:
        value = _clean_value(text)
        if not value:
            continue
        key = re.sub(r"[\s,._/\-]+", "", _canonical_digits(value)).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _item_name_from_row_text(text: str) -> str:
    parts = [part for part in re.split(r"\s+", text or "") if part]
    name_parts: list[str] = []
    for part in parts:
        compact = re.sub(r"[^\w\uac00-\ud7a3]", "", part)
        if not compact:
            continue
        if _amount_values(part) or re.fullmatch(r"\d+(?:[.,]\d+)?", compact):
            break
        if re.fullmatch(r"[A-Z0-9][A-Z0-9_\-/.]{1,24}", compact, re.I) and name_parts:
            break
        name_parts.append(part)
        if len(" ".join(name_parts)) >= 60:
            break
    value = _clean_value(" ".join(name_parts))
    return value or _clean_value(text)[:60]


def _numbers_from_row_text(text: str) -> list[str]:
    values: list[str] = []
    for token in re.split(r"\s+", _canonical_digits(text or "")):
        token = token.strip()
        if not token:
            continue
        match = re.fullmatch(r"(?:\u20a9\s*)?(\d{1,3}(?:[,.]\d{3})+|\d+(?:[.]\d+)?)(?:\s*\uc6d0)?", token)
        if not match:
            continue
        raw = match.group(1)
        digits = re.sub(r"\D", "", raw)
        if not digits:
            continue
        if re.fullmatch(r"(?:19|20)\d{6}", digits):
            continue
        values.append(f"{int(digits):,}" if len(digits) >= 4 else raw)
    return values


def _table_money_values(text: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r"(?<!\d)(\d{1,3}(?:[,.]\d{3})+)(?!\d)", _canonical_digits(text or "")):
        raw = match.group(1)
        digits = re.sub(r"\D", "", raw)
        if not digits or re.fullmatch(r"(?:19|20)\d{6}", digits):
            continue
        numeric = int(digits)
        if 100 <= numeric <= 1_000_000_000:
            values.append(f"{numeric:,}")
    return values


def _is_code_or_lot_number(value: str) -> bool:
    compact = re.sub(r"[\s,._/\-]+", "", _canonical_digits(value or ""))
    if not compact:
        return False
    if re.fullmatch(r"(?:19|20)\d{6}", compact):
        return True
    if re.fullmatch(r"\d{5,8}", compact):
        return True
    if re.search(r"[A-Za-z]", compact) and re.search(r"\d", compact):
        return True
    return False


def _item_dict_from_row_text(text: str) -> dict[str, str]:
    item_name = _item_name_from_row_text(text)
    spec = _spec_from_row_text(text, item_name)
    rest_for_numbers = (text or "").strip()
    if item_name and rest_for_numbers.startswith(item_name):
        rest_for_numbers = rest_for_numbers[len(item_name):].strip()
    if spec and rest_for_numbers.startswith(spec):
        rest_for_numbers = rest_for_numbers[len(spec):].strip()
    amounts = _table_money_values(rest_for_numbers)
    numbers = _numbers_from_row_text(rest_for_numbers)
    quantity = ""
    unit_price = ""
    if numbers:
        amount_set = set(amounts)
        small_numbers = [
            value
            for value in numbers
            if value not in amount_set
            and not _is_code_or_lot_number(value)
            and int(re.sub(r"\D", "", value) or "0") <= 10000
        ]
        if small_numbers:
            quantity = small_numbers[0]
    if len(amounts) >= 2:
        unit_price = amounts[-2]
    supply_amount = ""
    tax_amount = ""
    total_amount = ""
    if len(amounts) >= 3:
        supply_amount = amounts[-3]
        tax_amount = amounts[-2]
        total_amount = amounts[-1]
    elif len(amounts) >= 1:
        single_num = int(amounts[-1].replace(",", ""))
        if single_num >= 50_000:
            supply_amount = amounts[-1]
    return {
        "itemName": item_name,
        "spec": spec,
        "quantity": quantity,
        "unitPrice": unit_price,
        "supplyAmount": supply_amount,
        "taxAmount": tax_amount,
        "totalAmount": total_amount,
        "amount": supply_amount,
        "rawText": _summarize_table_row(text),
        "source": "ocr",
        "sourceBboxes": [],
    }


def _table_item_column_score(item: dict[str, Any]) -> int:
    score = 0
    for key in ("itemName", "spec", "quantity", "unitPrice", "supplyAmount", "taxAmount", "totalAmount"):
        val = str(item.get(key) or "").strip()
        if not val:
            continue
        # T-7a: Don't count clearly garbled values in the score —
        # e.g. quantity containing Korean text is a misassigned column cell.
        if key == "quantity" and (
            re.search(r"[가-힣]", val)
            or (len(val) > 20 and not re.fullmatch(r"[\d,.\s]+", val))
        ):
            continue
        score += 1
    if item.get("sourceBboxes"):
        score += 1
    return score


def _spec_from_row_text(text: str, item_name: str) -> str:
    rest = (text or "").strip()
    if item_name and rest.startswith(item_name):
        rest = rest[len(item_name):].strip()
    parts: list[str] = []
    for part in re.split(r"\s+", rest):
        if not part:
            continue
        if _amount_values(part):
            break
        compact = re.sub(r"[^\w\uac00-\ud7a3|*./-]", "", part)
        digits = re.sub(r"\D", "", compact)
        if _is_code_or_lot_number(part) and not re.search(
            r"mg|ml|g|kg|t|tab|cap|capsule|tablet|dose|box|p|\ud3ec|\uc815|\ucea1\uc290|\ucea1\uc2ac",
            compact,
            re.I,
        ):
            break
        if re.fullmatch(r"\d+(?:[.,]\d+)?", compact):
            break
        if re.fullmatch(r"(?:19|20)\d{6}", digits or ""):
            break
        if len(parts) >= 4:
            break
        parts.append(part)
    return _clean_value(" ".join(parts))[:80]


def _bbox_dict(line: OcrLine) -> dict[str, float]:
    return {
        "x": round(line.x, 2),
        "y": round(line.y, 2),
        "w": round(line.w, 2),
        "h": round(line.h, 2),
    }


def _item_dict_from_structured_text(text: str, source_lines: list[OcrLine]) -> dict[str, Any]:
    item = _item_dict_from_row_text(text)
    item["rawText"] = _summarize_table_row(text)
    item["sourceBboxes"] = [_bbox_dict(line) for line in sorted(source_lines, key=lambda line: (line.cy, line.x))]
    return item


def _table_row_preview_from_item(item: dict[str, Any]) -> str:
    parts = [
        str(item.get("itemName") or ""),
        str(item.get("spec") or ""),
        str(item.get("supplyAmount") or item.get("amount") or ""),
        str(item.get("taxAmount") or ""),
        str(item.get("totalAmount") or ""),
    ]
    value = " ".join(part for part in parts if part).strip()
    return _summarize_table_row(value or str(item.get("rawText") or ""))


_TABLE_NOTICE_RE = re.compile(
    r"\uc804\uc790\uc7a5\ubd80|\uc6f9\uc11c\ube44\uc2a4|\uacc4\uc57d\ucf54\ub4dc|\uc0c1\ud488\ub2e8\ud488|"
    r"\uac70\ub798\uba85\uc138\uc11c|\uac70\ub798\uba85\uc138\ud45c|\uacf5\s*\uae09\s*\ubc1b|\uacf5\s*\uae09\s*\uc790|"
    r"\uc0ac\uc5c5\uc790|\ub4f1\ub85d\ubc88\ud638|\ub300\ud45c|\uc131\uba85|\uc8fc\uc18c|\uc5c5\ud0dc|\uc885\ubaa9|"
    r"\uc804\ud654|\uc5f0\ub77d\ucc98|TEL|FAX|\uc778\uc218|\ud655\uc778|\uc11c\uba85|Page|PAGE|\ud398\uc774\uc9c0|"
    r"\ub2f4\ub2f9\uc790|\uac70\ub798\ucc98|\uc8fc\ubb38\uc11c|\uc601\uc5c5\uc0ac\uc6d0|\uc601\uc5c5\uc9c0\uc810|"
    r"\ud300\s*\uc9c0?\uc810\s*\ucf54\ub4dc|\uc9c0\uc810\s*\ucf54\ub4dc|\ud300\s*.*\ucf54\ub4dc",
    re.I,
)


def _is_table_notice_or_party_line(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    if _TABLE_NOTICE_RE.search(text or ""):
        return True
    if _BIZ_RE.search(_canonical_digits(text)) or _PHONE_RE.search(text or ""):
        return True
    if _ADDRESS_HINT_RE.search(text or "") and re.search(r"(?:\ub85c|\uae38|\\d)", compact):
        return True
    return False


def _has_strong_item_signal(text: str) -> bool:
    """True if text has a strong positive signal of being a table item data row.

    Used to override contact/notice filters in the colGuides path within tableBounds,
    where the bounds already constrain the extraction area.
    """
    # OP- style pharmaceutical item code (allow for minor OCR noise)
    if re.search(r"\bOP[-\s][A-Za-z0-9]{2,}", text, re.I):
        return True
    # Standalone row index 1-13 at start of text (whitespace-separated)
    # Exclude page-count patterns like "1 /1" (page 1 of 1)
    if re.match(r"^\s*(?:1[0-3]|[1-9])[\s\t]", text):
        if not re.match(r"^\s*\d+\s*/", text):
            return True
    return False


def _find_op_anchor_lines(lines: list["OcrLine"]) -> list["OcrLine"]:
    """Find individual OCR lines that contain OP-* pharmaceutical item codes, sorted by x."""
    return sorted(
        [l for l in lines if _OP_ANCHOR_CODE_RE.search(l.text or "")],
        key=lambda l: l.cx,
    )


def _extract_op_anchor_code(text: str) -> str:
    """Extract and normalize the first OP-* code from OCR text."""
    m = _OP_ANCHOR_CODE_RE.search(text or "")
    if not m:
        return ""
    code = m.group(1).upper()
    code = re.sub(r"^0P", "OP", code)
    code = re.sub(r"\s+", "-", code)
    return code


def _op_anchor_reconstruct_table(
    lines: list["OcrLine"],
    page_h: float,
    page_w: float,
    expected_columns: dict[str, Any],
    table_bounds: dict[str, float] | None = None,
    debug: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """T-6n: Reconstruct transposed invoice table using OP-* codes as column anchors.

    For documents where items are laid out as horizontal columns (transposed table),
    e.g. 2.pdf where 13 items each occupy one vertical column. Each OP-* code found
    in the OCR output becomes one item row in the output.
    """
    # Scope: apply table_bounds if given, else full page (exclude footer)
    y0 = table_bounds.get("yMin", 0.0) if table_bounds else 0.0
    y1 = table_bounds.get("yMax", page_h * 0.92) if table_bounds else page_h * 0.92
    x0 = table_bounds.get("xMin", 0.0) if table_bounds else 0.0
    x1 = table_bounds.get("xMax", page_w) if table_bounds else page_w

    scope = [l for l in lines if y0 <= l.cy <= y1 and x0 <= l.cx <= x1]

    # Find OP-* anchor lines (each = one item column)
    anchors = _find_op_anchor_lines(scope)
    anchor_count = len(anchors)

    if anchor_count < 3:
        if debug is not None:
            debug["opAnchorCount"] = anchor_count
            debug["opAnchorSamples"] = []
        return []

    # Compute initial per-column half-width from minimum anchor spacing
    anchor_xs = [a.cx for a in anchors]
    if anchor_count >= 2:
        min_spacing = min(anchor_xs[i + 1] - anchor_xs[i] for i in range(anchor_count - 1))
        avg_spacing = (anchor_xs[-1] - anchor_xs[0]) / (anchor_count - 1)
        col_half_w = max(min_spacing * 0.55, 8.0)
    else:
        avg_spacing = page_w / (anchor_count + 1)
        col_half_w = max(avg_spacing * 0.45, 8.0)

    # T-6n y-band expansion: some item columns may not have OP-* OCR-readable codes.
    # Only expand RIGHTWARD from the last OP-* anchor — left-side non-OP lines are noise.
    # Items 1-3 (rightmost in the transposed layout) appear after the last detected anchor.
    avg_anchor_y = sum(a.cy for a in anchors) / anchor_count
    max_anchor_h = max((a.h for a in anchors), default=20.0)
    y_tol = max(max_anchor_h * 0.75, 12.0)
    x_expand_left = anchor_xs[-1] + col_half_w * 0.3   # just past the last anchor
    x_expand_right = anchor_xs[-1] + avg_spacing * 4.5  # up to 4 more columns

    anchor_set = set(id(a) for a in anchors)
    extra_anchors: list["OcrLine"] = []
    for line in scope:
        if id(line) in anchor_set:
            continue
        if not abs(line.cy - avg_anchor_y) <= y_tol:
            continue
        if not (x_expand_left <= line.cx <= x_expand_right):
            continue
        text = _clean_value(line.text)
        if not text:
            continue
        # Quality gates for extra anchors: must look like an item code, not contact/noise
        if len(text) < 2:
            continue  # single chars (digits/letters) are noise
        if re.search(r"[가-힣]", text):
            continue  # Korean text → not item codes
        if _is_business_contact_line(text):
            continue  # company/address info
        if _is_table_notice_or_party_line(text):
            continue  # notice/party info
        if re.search(r"\d{5,}", re.sub(r"[,.]", "", text)):
            continue  # long number sequences (amounts, postal codes)
        # Skip summary/header lines
        if _is_summary_row_for_items(text) or _is_table_header_row(text):
            continue
        extra_anchors.append(line)
        anchor_set.add(id(line))

    if extra_anchors:
        all_anchors = sorted(anchors + extra_anchors, key=lambda l: l.cx)
        # Deduplicate anchors within half a column-width of each other
        deduped: list["OcrLine"] = [all_anchors[0]]
        for a in all_anchors[1:]:
            if a.cx - deduped[-1].cx >= col_half_w * 0.7:
                deduped.append(a)
        anchors = deduped
        anchor_xs = [a.cx for a in anchors]
        anchor_count = len(anchors)
        if anchor_count >= 2:
            min_spacing = min(anchor_xs[i + 1] - anchor_xs[i] for i in range(anchor_count - 1))
            col_half_w = max(min_spacing * 0.55, 8.0)

    if debug is not None:
        debug["opAnchorCount"] = anchor_count
        debug["opAnchorSamples"] = [f"x={round(a.cx, 0)} '{a.text[:30]}'" for a in anchors[:8]]

    # Anchor set for quick membership check
    anchor_set = set(id(a) for a in anchors)

    # Assign non-anchor scope lines to their nearest anchor column
    column_lines: list[list["OcrLine"]] = [[] for _ in anchors]
    for line in scope:
        if id(line) in anchor_set:
            continue
        dists = [abs(line.cx - ax) for ax in anchor_xs]
        nearest_i = min(range(anchor_count), key=lambda i: dists[i])
        if dists[nearest_i] <= col_half_w * 2.5:
            column_lines[nearest_i].append(line)

    # Prepare expected-column key lists
    required = expected_columns.get("required") or []
    optional = expected_columns.get("optional") or []
    all_keys = list(dict.fromkeys(required + optional))
    canonical_set = set(_TABLE_ROW_COLUMNS)
    non_can = [k for k in all_keys if k not in canonical_set and k != "rowIndex"]

    # Summary y-cutoff: ignore lines clearly in document footer
    summary_y_cut = page_h * 0.82

    items: list[dict[str, Any]] = []

    for i, anchor in enumerate(anchors):
        col_lines = sorted(column_lines[i], key=lambda l: l.cy)

        item: dict[str, Any] = {k: "" for k in _TABLE_ROW_COLUMNS if k != "rowIndex"}
        for nck in non_can:
            item[nck] = ""
        item["source"] = "op_anchor_reconstructed_table"
        item["_row_y"] = anchor.cy
        item["rawText"] = _clean_value(anchor.text)
        item["sourceBboxes"] = [_bbox_dict(anchor)] + [_bbox_dict(l) for l in col_lines[:4]]

        # itemCode from the anchor itself
        # T-6m: only use raw fallback if it looks like a valid code (≥3 chars); single chars are noise
        _op_code_val = _extract_op_anchor_code(anchor.text)
        if not _op_code_val:
            _raw_fb = _clean_value(anchor.text)
            _op_code_val = _raw_fb if len(_raw_fb) >= 3 else ""
        item["itemCode"] = _op_code_val

        # Classify other lines in this column
        for line in col_lines:
            if line.cy > summary_y_cut:
                continue
            text = _clean_value(line.text)
            if not text:
                continue
            # Skip if another OP-* anchor (not the column's own code)
            if _OP_ANCHOR_CODE_RE.search(text):
                continue
            # Skip summary/total lines
            if _is_summary_row_for_items(text):
                continue

            # Korean text → itemName candidate (skip header-only tokens)
            if re.search(r"[가-힣]", text) and not _is_table_header_row(text):
                if not item.get("itemName"):
                    item["itemName"] = text[:60]
                continue

            # T-6m: Latin multi-char drug names — allow digits (e.g. "CECLOR 500mg")
            # Guard: not a pure code pattern [A-Za-z]{1-3}+digits (those go to insuranceCode below)
            if re.search(r"[A-Za-z]{3,}", text) and not re.fullmatch(r"[A-Za-z]{1,3}\d{2,}", text.strip()):
                if not item.get("itemName"):
                    item["itemName"] = text[:60]
                continue

            # T-6m: Insurance/classification code — moved BEFORE amount check so "A123456"
            # is not consumed by _amount_values (which finds "123456" in range 100-1B).
            # Extended pattern: 1-3 letters + 2+ digits (e.g. "A123456", "B12345", "BJ12")
            if re.fullmatch(r"[A-Za-z]{1,3}\d{2,}", text.strip()):
                if not item.get("insuranceCode"):
                    item["insuranceCode"] = text.strip()
                continue

            # Amount values (formatted numbers with commas, 100–1B range)
            amt_vals = _amount_values(text)
            if amt_vals:
                for price_key in ("consumerUnitPrice", "supplyUnitPrice", "supplyAmount"):
                    target_ok = price_key in canonical_set or price_key in non_can
                    if target_ok and not item.get(price_key):
                        item[price_key] = amt_vals[0]
                        break
                continue

            # Small integer → quantity
            compact_digits = re.sub(r"\D", "", text)
            if compact_digits and 1 <= len(compact_digits) <= 4:
                try:
                    val = int(compact_digits)
                    if 1 <= val <= 9999 and not item.get("quantity"):
                        item["quantity"] = str(val)
                        continue
                except ValueError:
                    pass

        items.append(item)

    # Gap-fill: if anchor texts embed a row count hint (e.g. "13 OP-NA0300" → 13 items),
    # and actual anchors found < that count, add empty placeholder rows to reach the total.
    max_row_hint = anchor_count
    for a in anchors:
        m = re.match(r"^\s*(\d{1,2})\s", _clean_value(a.text) or "")
        if m:
            val = int(m.group(1))
            if 5 <= val <= 50:
                max_row_hint = max(max_row_hint, val)

    if max_row_hint > len(items):
        for _ in range(max_row_hint - len(items)):
            gap_item: dict[str, Any] = {k: "" for k in _TABLE_ROW_COLUMNS if k != "rowIndex"}
            for nck in non_can:
                gap_item[nck] = ""
            gap_item["source"] = "op_anchor_reconstructed_table"
            gap_item["_row_y"] = avg_anchor_y
            gap_item["rawText"] = ""
            gap_item["sourceBboxes"] = []
            items.append(gap_item)

    if debug is not None:
        debug["opAnchorRowsBuilt"] = len(items)

    return items


# ── T-8a: Multiline column layout post-processing ────────────────────────────
# Pharmaceutical supply invoices sometimes have a "column-per-field" layout:
# all item names in one column, all item codes in another, etc.
# OCR reads these column-by-column (or section-by-section), producing a flat
# text where codes / prices / amounts appear as sequential blocks, separate from
# item names. This post-processor reconnects them to the correct rows.

_MULTILINE_ITEM_CODE_RE = re.compile(r"^[A-Z][A-Z0-9]{4,9}$")
_MULTILINE_AMOUNT_RE = re.compile(r"^\d{1,3}(?:,\d{3})+$")
_MULTILINE_LABEL_STRIP_RE = re.compile(r"\s+")


def _ml_find_consecutive_code_block(texts: list[str], n: int) -> list[str]:
    """Find a window of exactly N consecutive OCR lines all matching pharmaceutical
    item-code pattern: all-uppercase alphanumeric, 5-10 chars, at least one digit.
    """
    _has_digit = re.compile(r"\d")
    for start in range(len(texts) - n + 1):
        window = texts[start : start + n]
        if all(
            _MULTILINE_ITEM_CODE_RE.match(t)
            and _has_digit.search(t)
            and not t.isdigit()
            for t in window
        ):
            return list(window)
    return []


def _ml_find_values_after_label(
    texts: list[str], label_exact: str, n: int, min_digit_len: int = 3
) -> list[str]:
    """Find N comma-formatted number values appearing after an exact label token."""
    label_pos = -1
    for i, t in enumerate(texts):
        if _MULTILINE_LABEL_STRIP_RE.sub("", t) == label_exact and len(t) <= 6:
            label_pos = i
    if label_pos < 0:
        return []
    vals: list[str] = []
    for text in texts[label_pos + 1 : label_pos + 1 + n * 8]:
        if not text:
            continue
        if _MULTILINE_AMOUNT_RE.match(text):
            digits = re.sub(r"\D", "", text)
            if len(digits) >= min_digit_len:
                vals.append(text)
                if len(vals) == n:
                    break
    return vals if len(vals) == n else []


def _ml_find_quantity_values_after_label(texts: list[str], n: int) -> list[str]:
    """T-9a: Find a conservative quantity block in multiline layouts."""
    label_pos = -1
    for i, text in enumerate(texts):
        compact = _MULTILINE_LABEL_STRIP_RE.sub("", text or "")
        if compact in {"\uc218\ub7c9", "Qty", "QTY"} and len(text or "") <= 8:
            label_pos = i
            break
    if label_pos < 0:
        return []

    stop_re = re.compile(
        r"\ub2e8\s*\uac00|\uae08\s*\uc561|\uacf5\s*\uae09|\uc138\s*\uc561|"
        r"\ud569\s*\uacc4|\ubd80\s*\uac00|\bVAT\b|\bTAX\b",
        re.I,
    )
    vals: list[str] = []
    for text in texts[label_pos + 1 : label_pos + 1 + n * 8]:
        value = _clean_value(text)
        if not value:
            continue
        if stop_re.search(value):
            break
        compact = re.sub(r"\s+", "", _canonical_digits(value))
        if not re.fullmatch(r"\d{1,4}", compact):
            continue
        numeric = int(compact)
        if 1 <= numeric <= 9999:
            vals.append(str(numeric))
            if len(vals) == n:
                break
    return vals if len(vals) == n else vals


def _ml_build_name_to_ocr_order(
    texts: list[str], row_names: list[str], n: int
) -> list[int]:
    """Map each tableRow (by row index) to its position in the OCR item-name sequence.

    Returns a list of length n where result[row_idx] = ocr_seq_index (0-based),
    or an empty list if mapping cannot be established for all rows.
    """
    seen_rows: set[int] = set()
    ocr_order: list[tuple[int, int]] = []  # (ocr_pos, row_idx)

    for ocr_pos, text in enumerate(texts):
        if not text or len(text) < 3:
            continue
        for row_idx, name in enumerate(row_names):
            if row_idx in seen_rows or not name:
                continue
            # Match by exact equality or significant substring
            if text == name or (len(text) >= 6 and text in name) or (len(name) >= 6 and name in text):
                ocr_order.append((ocr_pos, row_idx))
                seen_rows.add(row_idx)
                break
        if len(ocr_order) == n:
            break

    if len(ocr_order) != n:
        return []

    ocr_order.sort(key=lambda x: x[0])
    result = [n] * n  # sentinel = n means unmapped
    for seq_idx, (_, row_idx) in enumerate(ocr_order):
        result[row_idx] = seq_idx

    return [] if any(v == n for v in result) else result


def _postprocess_multiline_column_layout(
    lines: list["OcrLine"],
    rows: list[dict[str, Any]],
    expected_columns: dict[str, list[str]] | None,
) -> dict[str, Any]:
    """T-8a: Recover itemCode / unitPrice / amount for multiline-column PDFs.

    Guard conditions:
      - rows >= 2
      - expected columns include itemCode, unitPrice, or amount
      - those columns are mostly empty (>= 50% rows missing)
      - OCR contains exactly N-element code/price/amount blocks

    Returns: {applied, filledKeys, warnings, candidateCounts}
    """
    out: dict[str, Any] = {"applied": False, "filledKeys": [], "warnings": [], "candidateCounts": {}}
    n = len(rows)
    if n < 2 or not expected_columns:
        return out

    required = set(expected_columns.get("required") or [])
    optional = set(expected_columns.get("optional") or [])
    all_exp = required | optional

    want_code = "itemCode" in all_exp
    want_quantity = "quantity" in all_exp
    want_price = "unitPrice" in all_exp
    want_amount = "amount" in all_exp

    if not (want_code or want_quantity or want_price or want_amount):
        return out

    # Skip columns that are already mostly filled
    def _mostly_missing(key: str) -> bool:
        missing = sum(1 for r in rows if not str(r.get(key) or "").strip())
        return missing >= max(1, n // 2)

    want_code = want_code and _mostly_missing("itemCode")
    want_quantity = want_quantity and _mostly_missing("quantity")
    want_price = want_price and _mostly_missing("unitPrice")
    want_amount = want_amount and _mostly_missing("amount")

    if not (want_code or want_quantity or want_price or want_amount):
        return out

    # Sort OCR lines by (y, x) — spatial reading order
    ocr_texts = [_clean_value(l.text) for l in sorted(lines, key=lambda l: (l.cy, l.x))]

    # Establish OCR order of item names
    row_names = [str(r.get("itemName") or "").strip() for r in rows]
    row_to_ocr = _ml_build_name_to_ocr_order(ocr_texts, row_names, n)

    if len(row_to_ocr) != n:
        out["warnings"].append("multiline_layout_order_mismatch:item names not found in OCR order")
        return out

    # Extract candidate blocks
    codes = _ml_find_consecutive_code_block(ocr_texts, n) if want_code else []
    quantities = _ml_find_quantity_values_after_label(ocr_texts, n) if want_quantity else []
    prices = _ml_find_values_after_label(ocr_texts, "단가", n, min_digit_len=2) if want_price else []
    amounts = _ml_find_values_after_label(ocr_texts, "금액", n, min_digit_len=4) if want_amount else []

    out["candidateCounts"] = {
        "itemCode": len(codes),
        "quantity": len(quantities),
        "unitPrice": len(prices),
        "amount": len(amounts),
    }

    applied = False

    for row_idx, row in enumerate(rows):
        ocr_i = row_to_ocr[row_idx]
        if not (0 <= ocr_i < n):
            continue
        if want_code and len(codes) == n and not str(row.get("itemCode") or "").strip():
            row["itemCode"] = codes[ocr_i]
            applied = True
        if want_quantity and len(quantities) == n and not str(row.get("quantity") or "").strip():
            row["quantity"] = quantities[ocr_i]
            applied = True
        if want_price and len(prices) == n and not str(row.get("unitPrice") or "").strip():
            row["unitPrice"] = prices[ocr_i]
            applied = True
        if want_amount and len(amounts) == n and not str(row.get("amount") or "").strip():
            row["amount"] = amounts[ocr_i]
            applied = True

    # Collect missing-source warnings
    if want_code and len(codes) != n:
        out["warnings"].append(
            f"itemCode:source_missing:품목코드 블록 {len(codes)}/{n}개 발견 (expected {n})"
        )
    if want_quantity and len(quantities) != n:
        reason = "source_missing" if len(quantities) == 0 else "ambiguous_numeric_candidates"
        out["warnings"].append(
            f"quantity:{reason}:quantity candidates {len(quantities)}/{n}; kept existing empty values"
        )
    if want_price and len(prices) != n:
        out["warnings"].append(
            f"unitPrice:source_missing:단가 {len(prices)}/{n}개 발견 (expected {n})"
        )
    if want_amount and len(amounts) != n:
        out["warnings"].append(
            f"amount:source_missing:금액 {len(amounts)}/{n}개 발견 (expected {n})"
        )

    for key, cands in [("itemCode", codes), ("quantity", quantities), ("unitPrice", prices), ("amount", amounts)]:
        if len(cands) == n and (
            (key == "itemCode" and want_code)
            or (key == "quantity" and want_quantity)
            or (key == "unitPrice" and want_price)
            or (key == "amount" and want_amount)
        ):
            out["filledKeys"].append(key)

    if applied:
        out["applied"] = True
        out["warnings"].insert(0, "multiline_layout_mapping_applied")

    return out


def _item_start_score(text: str) -> float:
    value = _clean_value(text)
    compact = re.sub(r"\s+", "", value)
    if len(compact) < 3 or len(compact) > 100:
        return -999.0
    if _is_table_notice_or_party_line(value) or _is_summary_row_for_items(value) or _is_table_header_only_row(value):
        return -999.0
    if _is_code_only_table_row(value) or _is_numeric_detail_line(value):
        return -999.0
    if re.search(r"[\[\]]", value) and not re.search(r"TABLET|CAPSULE|CAPS?|TAB|CAP", value, re.I):
        return -40.0
    product_hint = _has_product_hint(value)
    score = 0.0
    if product_hint:
        score += 18
    if _ITEM_NAME_HINT_RE.search(value):
        score += 8
    if re.search(r"TABLET|CAPSULE|CAPS?|ABLET|TAB|CAP", value, re.I):
        score += 12
    if _HANGUL_RE.search(value):
        score += 5
    if re.search(r"\d", value):
        score += 2
    if _amount_values(value):
        score += 2
    if len(compact) <= 4 and not product_hint:
        score -= 10
    if re.fullmatch(r"[A-Z0-9_\-/.]{2,24}", compact, re.I) and not re.search(r"TABLET|CAPSULE|CAPS?|TAB|CAP", value, re.I):
        score -= 12
    if not product_hint and not re.search(r"TABLET|CAPSULE|CAPS?|ABLET", value, re.I):
        score -= 6
    return score


def _is_structured_item_start(text: str) -> bool:
    return _item_start_score(text) >= 8


def _is_item_detail_line(text: str) -> bool:
    value = _clean_value(text)
    compact = re.sub(r"\s+", "", value)
    if not compact:
        return False
    if re.fullmatch(r"(?:19|20)\d{2}[./-]?\d{1,2}[./-]?\d{1,2}(?:[-/]\d{1,5})?", compact):
        return False
    if _is_table_notice_or_party_line(value) or _is_table_header_only_row(value) or _is_summary_row_for_items(value):
        return False
    return bool(_is_numeric_detail_line(value) or _amount_values(value) or _SPEC_ONLY_RE.fullmatch(compact))


def _nearby_detail_lines_for_item(
    rows: list[list[OcrLine]],
    idx: int,
    page_h: float,
) -> list[tuple[int, list[OcrLine], str]]:
    details: list[tuple[int, list[OcrLine], str]] = []
    base_y = _row_center_y(rows[idx])
    # Same visual row fragments can be split by OCR because their baselines differ a little.
    for near_idx in range(max(0, idx - 3), min(len(rows), idx + 4)):
        if near_idx == idx:
            continue
        row_y = _row_center_y(rows[near_idx])
        if abs(row_y - base_y) > page_h * 0.035:
            continue
        text = _row_text(rows[near_idx])
        if _is_structured_item_start(text):
            continue
        if _is_table_notice_or_party_line(text) or _is_table_header_only_row(text) or _is_summary_row_for_items(text):
            continue
        if _is_item_detail_line(text):
            details.append((near_idx, rows[near_idx], text))
    for near_idx in range(idx + 1, min(len(rows), idx + 8)):
        row_y = _row_center_y(rows[near_idx])
        if row_y - base_y > page_h * 0.16:
            break
        text = _row_text(rows[near_idx])
        if _is_structured_item_start(text):
            break
        if _is_table_notice_or_party_line(text) or _is_table_header_only_row(text) or _is_summary_row_for_items(text):
            if details:
                break
            continue
        if _is_item_detail_line(text):
            details.append((near_idx, rows[near_idx], text))
            if len(details) >= 6 or _amount_values(text):
                if len(details) >= 2:
                    break
    details.sort(key=lambda item: (abs(_row_center_y(item[1]) - base_y), item[0]))
    return details[:6]


def _structured_text_order_items(lines: list[OcrLine]) -> list[dict[str, Any]]:
    # T-6: sort by (cy, x) so text-order follows visual top-to-bottom order
    ordered = sorted([line for line in lines if _clean_value(line.text)], key=lambda l: (l.cy, l.x))
    items: list[dict[str, Any]] = []
    for idx, line in enumerate(ordered):
        text = _clean_value(line.text)
        if not _is_structured_item_start(text):
            continue
        detail_lines: list[OcrLine] = []
        detail_texts: list[str] = []
        for nxt in ordered[idx + 1 : idx + 8]:
            nxt_text = _clean_value(nxt.text)
            if _is_structured_item_start(nxt_text):
                break
            if _is_item_detail_line(nxt_text):
                detail_lines.append(nxt)
                detail_texts.append(nxt_text)
                if len(detail_lines) >= 5 or _amount_values(nxt_text):
                    if len(detail_lines) >= 2:
                        break
            elif detail_lines:
                break
        candidate = _clean_value(" ".join([text] + detail_texts))
        if not _is_valid_final_item_text(candidate):
            candidate = text
        if not _is_valid_final_item_text(candidate):
            continue
        items.append(_item_dict_from_structured_text(candidate, [line] + detail_lines))
    return items


def _structured_table_items(lines: list[OcrLine], page_h: float) -> list[dict[str, Any]]:
    rows = _group_rows(lines)
    items: list[dict[str, Any]] = []
    consumed_detail_indices: set[int] = set()
    for idx, row in enumerate(rows):
        if idx in consumed_detail_indices:
            continue
        row_y = _row_center_y(row)
        if row_y < page_h * 0.02 or row_y > page_h * 0.93:
            continue
        text = _row_text(row)
        if not _is_structured_item_start(text):
            continue
        details = _nearby_detail_lines_for_item(rows, idx, page_h)
        detail_texts = [item[2] for item in details]
        source_lines = list(row)
        for detail_idx, detail_row, _ in details:
            consumed_detail_indices.add(detail_idx)
            source_lines.extend(detail_row)
        candidate = _clean_value(" ".join([text] + detail_texts))
        if not _is_valid_final_item_text(candidate):
            candidate = text
        if not _is_valid_final_item_text(candidate):
            continue
        items.append(_item_dict_from_structured_text(candidate, source_lines))

    text_order_items = _structured_text_order_items(lines)
    if len(text_order_items) > len(items):
        items = text_order_items

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        item_name = str(item.get("itemName") or "")
        raw_text = str(item.get("rawText") or "")
        key = re.sub(r"[\s,._/\-]+", "", _canonical_digits(item_name + "|" + raw_text)).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _is_valid_final_item_text(text: str) -> bool:
    value = _clean_value(text)
    if not value:
        return False
    name = _item_name_from_row_text(value)
    compact_name = re.sub(r"\s+", "", name)
    if len(compact_name) < 2:
        return False
    product_hint = _has_product_hint(value)
    if _is_compact_catalog_code(value) or _is_compact_catalog_code(name):
        return False
    if _COMPANY_HINT_RE.search(value) and not product_hint:
        return False
    if re.search(r"\(\s*\uc8fc\s*\)|\uc8fc\s*\)|\uc8fc\uc2dd|\ud68c\uc0ac", value):
        return False
    if _is_table_header_row(name) or _is_business_contact_line(name) or _is_summary_row_for_items(name):
        return False
    if _is_code_only_table_row(value) or (_is_code_only_table_row(name) and not product_hint):
        return False
    if _is_numeric_detail_line(value) and not (product_hint or _is_probable_item_name_line(name)):
        return False
    if re.search(
        r"^(?:\uc804?\uc77c?\uc794\uc561|\uc794\uc561|\uc8fc\ubb38\uc11c|\uc8fc\ubb38NO|\ub2e8\uac00|\ub2e8\ubb50|"
        r"\uc218\ub7c9|\uacf5\uae09|\uc138\uc561|\ud569\uacc4|\uac70\ub798\uc77c\uc790|\uc8fc\ubb38\uc77c\uc790|"
        r"\ud488\ubaa9\ucf54\ub4dc|\uacc4\uc57d\ucf54\ub4dc|\uac70\ub798\uba85\uc138|\ub2f4\uac00|\ub204\uacc4|"
        r".*(?:\uac70\ub798\uae08\uc561|\uc794\uc561|\uc794\uace0|\uae08\uc561)$)",
        compact_name,
        re.I,
    ):
        return False
    if re.search(r"[\uac00-\ud7a3]{2,4}[,/][\uac00-\ud7a3]{2,4}", name):
        return False
    if len(compact_name) <= 4 and not product_hint:
        return False
    if re.fullmatch(r"[0-9A-Za-z\uac00-\ud7a3]{1,3}", compact_name) and not _amount_values(value):
        return False
    if re.fullmatch(r"[\uac00-\ud7a3]{1,3}", compact_name) and not re.search(
        r"(?:\uc815|\uc561|\ud06c\ub9bc)$|\ucea1\uc290|\ucea1\uc2ac|mg|ml|\d\s*g|tab|cap|box|dose",
        value,
        re.I,
    ):
        return False
    if re.search(r"^(?:\uc138\s*[\uc561\uc5ed\ud45c]|\uacf5\s*\uae09|\ud569\s*\uacc4|TOTAL)$", compact_name, re.I):
        return False
    return _text_has_name_signal(name) and (product_hint or bool(_amount_values(value)) or len(re.findall(r"\d", value)) >= 2)


def _collect_numeric_tail_rows(rows: list[list[OcrLine]], start_idx: int, page_h: float) -> list[tuple[int, str]]:
    tail: list[tuple[int, str]] = []
    base_y = _row_center_y(rows[start_idx])
    for idx in range(start_idx + 1, min(len(rows), start_idx + 8)):
        row_y = _row_center_y(rows[idx])
        if row_y - base_y > page_h * 0.16:
            break
        text = _row_text(rows[idx])
        if _is_table_header_row(text) or _is_business_contact_line(text) or _is_summary_row_for_items(text):
            break
        if _has_product_hint(text) and _is_probable_item_name_line(text):
            break
        if _is_numeric_detail_line(text):
            tail.append((idx, text))
            if len(tail) >= 5 or _amount_values(text):
                # Continue one more nearby numeric row for unit price/amount pairs.
                if len(tail) >= 2:
                    break
        elif tail:
            break
    return tail


def _extract_table_row_texts(rows: list[list[OcrLine]], page_h: float, header_index: int) -> list[str]:
    data_rows: list[str] = []
    consumed_indices: set[int] = set()
    start_idx = max(header_index + 1, 0) if header_index >= 0 else 0
    for idx in range(start_idx, len(rows)):
        if idx in consumed_indices:
            continue
        row = rows[idx]
        row_y = _row_center_y(row)
        if row_y < page_h * 0.16 or row_y > page_h * 0.92:
            continue
        text = _row_text(row)
        if _is_table_header_row(text) or _is_business_contact_line(text) or _is_summary_row_for_items(text):
            continue
        candidate = ""
        if _is_probable_item_name_line(text):
            tail = _collect_numeric_tail_rows(rows, idx, page_h)
            tail_texts = [item[1] for item in tail]
            if tail_texts or re.search(r"\d", text) or _has_product_hint(text):
                candidate = " ".join([text] + tail_texts)
                consumed_indices.update(item[0] for item in tail)
        elif re.search(r"\d", text) and _text_has_name_signal(text) and _table_row_score(text) > 1:
            candidate = text
        if not candidate:
            continue
        if not _has_product_hint(candidate) and not _amount_values(candidate) and not any(_is_numeric_detail_line(part) for part in candidate.splitlines()):
            continue
        data_rows.append(_summarize_table_row(candidate))
    return [text for text in _dedupe_table_rows(data_rows) if _is_valid_final_item_text(text)]


def _find_table_header_y(lines: list[OcrLine], page_h: float) -> float | None:
    for row in _group_rows(lines):
        text = _row_text(row)
        row_y = sum(item.cy for item in row) / len(row)
        if row_y >= page_h * 0.22 and _table_token_count(text) >= 2:
            return min(item.y for item in row)
    return None


# ── T-6: header-based column structure mapping ────────────────────────────────

def _match_header_to_canonical(text: str) -> str | None:
    """Map a header cell text to a canonical column key. Returns None if not matched."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    for pattern, key in _HEADER_CANONICAL_MAP:
        if pattern.search(t):
            return key
    return None


def _find_structured_header_row(
    rows: list[list[OcrLine]], page_h: float
) -> tuple[int, list[OcrLine]] | None:
    """Find the header row (index, merged lines) with ≥2 canonical column matches.
    Handles multi-line headers by merging adjacent candidate rows.
    """
    # Collect candidate rows with at least 1 canonical match
    # (idx, row_y, score, row)
    candidates: list[tuple[int, float, int, list[OcrLine]]] = []
    for idx, row in enumerate(rows):
        row_y = _row_center_y(row)
        if row_y < page_h * 0.08 or row_y > page_h * 0.85:
            continue
        score = 0
        for line in row:
            # T-6d-fix: count canonical matches including multi-canonical composite tokens
            parts = re.split(r"\s+", line.text.strip())
            matched_keys: set[str] = set()
            for part in parts:
                k = _match_header_to_canonical(part)
                if k is not None:
                    matched_keys.add(k)
            if not matched_keys:
                k = _match_header_to_canonical(line.text)
                if k is not None:
                    matched_keys.add(k)
            for k in matched_keys:
                score += 1
                if k in ("itemName", "quantity"):
                    score += 1  # bonus for key columns
        if score >= 1:
            candidates.append((idx, row_y, score, row))

    if not candidates:
        return None

    # 1) Best single row with ≥2 matches
    best_single = max(candidates, key=lambda c: c[2])
    if best_single[2] >= 2:
        return best_single[0], best_single[3]

    # 2) Merge adjacent rows (multi-line header) to reach ≥2 matches
    for i in range(len(candidates) - 1):
        idx_a, y_a, score_a, row_a = candidates[i]
        idx_b, y_b, score_b, row_b = candidates[i + 1]
        if abs(y_b - y_a) > page_h * 0.06:
            continue
        merged = row_a + row_b
        merged_score = 0
        for line in merged:
            parts = re.split(r"\s+", line.text.strip())
            matched_keys_m: set[str] = set()
            for part in parts:
                k = _match_header_to_canonical(part)
                if k is not None:
                    matched_keys_m.add(k)
            if not matched_keys_m:
                k = _match_header_to_canonical(line.text)
                if k is not None:
                    matched_keys_m.add(k)
            merged_score += len(matched_keys_m)
        if merged_score >= 2:
            return idx_a, merged

    return None


def _extract_multi_canonical_from_token(text: str, line: "OcrLine") -> list[dict[str, Any]]:
    """For a composite header token (e.g. '소비자단가 공급단가'), extract all canonical keys.
    Returns a list of virtual cell dicts with approximate x positions split within the token.
    """
    parts = re.split(r"\s+", (text or "").strip())
    matches: list[tuple[str, float]] = []  # (canonical_key, approx_x)
    for i, part in enumerate(parts):
        canon = _match_header_to_canonical(part)
        if canon is not None:
            # Approximate x as evenly spaced within the token
            frac = (i + 0.5) / max(len(parts), 1)
            matches.append((canon, line.x + line.w * frac))
    if len(matches) <= 1:
        return []  # not composite
    cells = []
    for canon, approx_x in matches:
        w_frac = line.w / max(len(matches), 1)
        cells.append({
            "canonical_key": canon,
            "cx": approx_x,
            "x1": approx_x - w_frac * 0.4,
            "x2": approx_x + w_frac * 0.4,
        })
    return cells


def _build_column_boundaries(
    header_row: list[OcrLine], page_w: float
) -> list[dict[str, Any]]:
    """Build sorted column boundaries from header cells. Returns [] if < 2 columns found.
    T-6c: uses cell edges for more accurate boundaries; first column starts at header x1.
    T-6d-fix: handles composite header tokens (e.g. '소비자단가 공급단가').
    """
    cells: list[dict[str, Any]] = []
    for line in sorted(header_row, key=lambda l: l.cx):
        # Try composite split first
        multi = _extract_multi_canonical_from_token(line.text, line)
        if multi:
            cells.extend(multi)
            continue
        canonical = _match_header_to_canonical(line.text)
        if canonical is None:
            continue
        cells.append({
            "canonical_key": canonical,
            "cx": line.cx,
            "x1": line.x,
            "x2": line.x + line.w,
        })
    # Deduplicate: keep leftmost occurrence of each canonical key
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for cell in cells:
        if cell["canonical_key"] not in seen:
            seen.add(cell["canonical_key"])
            deduped.append(cell)
    if len(deduped) < 2:
        return []

    # Build boundaries: use edge midpoints (more accurate than center midpoints)
    # First column: start at header cell's left edge (not 0) to avoid unmatched left columns
    boundaries: list[dict[str, Any]] = []
    for i, cell in enumerate(deduped):
        if i == 0:
            # Start near the first canonical header's left edge
            x_start = max(0.0, cell["x1"] - cell.get("w", 20) * 0.8)
        else:
            prev = deduped[i - 1]
            gap_mid = (prev["x2"] + cell["x1"]) / 2.0
            # Fallback to center midpoint if cells overlap
            if gap_mid <= prev["cx"]:
                gap_mid = (prev["cx"] + cell["cx"]) / 2.0
            x_start = gap_mid

        if i == len(deduped) - 1:
            x_end = page_w
        else:
            nxt = deduped[i + 1]
            gap_mid = (cell["x2"] + nxt["x1"]) / 2.0
            if gap_mid >= nxt["cx"]:
                gap_mid = (cell["cx"] + nxt["cx"]) / 2.0
            x_end = gap_mid

        boundaries.append({
            "canonical_key": cell["canonical_key"],
            "x_start": x_start,
            "x_end": x_end,
            "header_cx": cell["cx"],
        })
    return boundaries


def _assign_canonical_by_x(cx: float, boundaries: list[dict[str, Any]]) -> str | None:
    """Return canonical key for a center_x within column boundaries.
    T-6c: falls back to nearest column when slightly outside boundary (OCR positional variance).
    """
    for b in boundaries:
        if b["x_start"] <= cx < b["x_end"]:
            return b["canonical_key"]
    # Proximity fallback: find nearest header center
    if not boundaries:
        return None
    nearest = min(boundaries, key=lambda b: abs(cx - b.get("header_cx", (b["x_start"] + b["x_end"]) / 2.0)))
    header_cx = nearest.get("header_cx", (nearest["x_start"] + nearest["x_end"]) / 2.0)
    # T-6h: allow up to 70% of average column width as tolerance (was 55%)
    # Wider tolerance handles OCR positional variance where value doesn't align with header.
    avg_col_w = (boundaries[-1]["x_end"] - boundaries[0]["x_start"]) / max(1, len(boundaries))
    if abs(cx - header_cx) <= avg_col_w * 0.70:
        return nearest["canonical_key"]
    return None


def _split_composite_cell_value(
    canonical_key: str, value: str, item: dict[str, Any]
) -> None:
    """For composite canonical columns (e.g. manufacturingNo that includes expiryDate),
    try to split the cell value and assign secondary canonical key."""
    item[canonical_key] = value
    if canonical_key == "manufacturingNo":
        # Check if value contains a date-like component → split to expiryDate
        expiry = _tr_extract_expiry_date(value)
        if expiry and not item.get("expiryDate"):
            item["expiryDate"] = expiry
            # Remove date part from manufacturingNo
            non_date = re.sub(r"20\d{6}|\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])", "", value).strip()
            non_date = re.sub(r"[-/.\s]+", " ", non_date).strip()
            if non_date:
                item["manufacturingNo"] = _clean_value(non_date)
    elif canonical_key == "serialNo":
        # Check if value looks more like lotNo (short 4-6 digit number)
        compact = re.sub(r"\D", "", value)
        if compact and len(compact) <= 6 and not item.get("lotNo"):
            item["lotNo"] = value  # put in lotNo as well (secondary)


def _table_items_from_header_mapping(
    lines: list[OcrLine], page_h: float, page_w: float,
    debug: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Extract table items by x-position column mapping. Falls back to [] if header not found.
    T-6c: multi-line header support, composite column handling, proximity-based assignment.
    T-6d: debug info support.
    """
    # T-6g-fix: use tighter row grouping (0.55) so adjacent table rows are not merged
    rows = _group_rows(lines, tolerance_factor=0.55)
    header_result = _find_structured_header_row(rows, page_h)
    if debug is not None:
        debug["headerFound"] = header_result is not None
    if header_result is None:
        return []
    header_idx, header_row = header_result
    boundaries = _build_column_boundaries(header_row, page_w)

    if debug is not None:
        debug["headerY"] = _row_center_y(header_row)
        debug["headerScore"] = sum(1 for l in header_row if _match_header_to_canonical(l.text) is not None)
        debug["headerLines"] = [l.text for l in sorted(header_row, key=lambda l: l.x)]
        debug["boundaryCount"] = len(boundaries)
        debug["boundaries"] = [
            {"canonical_key": b["canonical_key"], "x_start": round(b["x_start"], 1), "x_end": round(b["x_end"], 1)}
            for b in boundaries
        ]
        debug["rejectedRows"] = []

    if len(boundaries) < 2:
        return []
    has_name_col = any(b["canonical_key"] == "itemName" for b in boundaries)
    header_y = max(_row_center_y(header_row), _row_center_y(rows[header_idx]))
    last_header_y = header_y

    items: list[dict[str, Any]] = []
    for idx in range(header_idx + 1, len(rows)):
        row = rows[idx]
        row_y = _row_center_y(row)
        if row_y <= last_header_y or row_y > page_h * 0.93:
            continue
        text = _row_text(row)
        if _is_summary_row_for_items(text):
            if debug is not None:
                debug["rejectedRows"].append({"reason": "summary_row", "text": text[:60], "y": round(row_y, 1)})
            # T-6g-fix: raise break threshold to 0.85 so rolling subtotals mid-table
            # don't terminate extraction too early for multi-group invoice tables.
            if items and row_y >= page_h * 0.85:
                break
            continue
        if _is_table_header_row(text) or _is_business_contact_line(text):
            if row_y < header_y + page_h * 0.04:
                last_header_y = row_y
            if debug is not None:
                debug["rejectedRows"].append({"reason": "header_or_contact", "text": text[:60], "y": round(row_y, 1)})
            continue

        col_texts: dict[str, list[str]] = {}
        for line in sorted(row, key=lambda l: l.x):
            cv = _clean_value(line.text)
            if not cv:
                continue
            key = _assign_canonical_by_x(line.cx, boundaries)
            if key is not None:
                col_texts.setdefault(key, []).append(cv)

        item: dict[str, Any] = {k: "" for k in _TABLE_ROW_COLUMNS if k != "rowIndex"}
        item["rawText"] = _summarize_table_row(text)
        item["sourceBboxes"] = [_bbox_dict(l) for l in row]
        item["source"] = "header_column_mapping"
        item["_row_y"] = row_y

        for key, texts in col_texts.items():
            if key in item:
                merged = _clean_value(" ".join(t for t in texts if t))
                _split_composite_cell_value(key, merged, item)

        if has_name_col:
            if not item.get("itemName"):
                # T-6d-fix / T-6g: allow rows without itemName if other data fields are present
                has_code = bool(item.get("itemCode"))
                has_qty = bool(item.get("quantity"))
                has_price = bool(item.get("unitPrice") or item.get("amount") or item.get("supplyAmount"))
                has_ins = bool(item.get("insuranceCode"))
                has_lot = bool(item.get("lotNo") or item.get("serialNo") or item.get("manufacturingNo"))
                has_exp = bool(item.get("expiryDate") or item.get("manufacturingNo"))
                has_spec_val = bool(item.get("spec"))
                row_has_data = (
                    (has_code and (has_qty or has_price))
                    or (has_qty and has_price)
                    or (has_ins and has_code)
                    or (has_lot and has_qty)
                    or (has_lot and has_price)                    # T-6g
                    or (has_exp and has_qty)                     # T-6g
                    or (has_spec_val and (has_qty or has_price)) # T-6g
                    or (has_lot and has_exp)                     # T-6g-fix: lot+expiry
                    or (has_code and has_lot)                    # T-6g-fix: code+lot
                    or (has_code and has_exp)                    # T-6g-fix: code+expiry
                )
                if not row_has_data:
                    if debug is not None:
                        debug["rejectedRows"].append({"reason": "no_item_name", "text": text[:60], "y": round(row_y, 1)})
                    continue
                if debug is not None:
                    debug["rejectedRows"].append({"reason": "no_item_name_allowed", "text": text[:60], "y": round(row_y, 1)})
            elif _is_table_notice_or_party_line(item["itemName"]):
                if debug is not None:
                    debug["rejectedRows"].append({"reason": "notice_or_party", "itemName": item["itemName"][:40], "y": round(row_y, 1)})
                continue
        else:
            has_val = any(item.get(k) for k in ("itemCode", "quantity", "unitPrice", "amount", "lotNo", "serialNo"))
            if not has_val:
                if debug is not None:
                    debug["rejectedRows"].append({"reason": "no_meaningful_value", "text": text[:60], "y": round(row_y, 1)})
                continue

        items.append(item)

    return items


# ── T-6e: expectedColumns-based header matching and extraction ────────────────


def _score_row_for_expected_columns(
    row: list["OcrLine"],
    expected_keys: set[str],
) -> tuple[int, dict[str, "OcrLine"]]:
    """Score a row by how many expectedColumns headers are found.

    Returns (score, {canonical_key: best_matching_line}).
    +1 bonus for itemName or quantity match.
    """
    matched: dict[str, "OcrLine"] = {}

    for line in row:
        # Try full text first
        key = _match_header_to_canonical(line.text)
        if key and key in expected_keys and key not in matched:
            matched[key] = line
            continue
        # Try individual space-split parts (handles composite tokens)
        parts = re.split(r"\s+", line.text.strip())
        if len(parts) > 1:
            for part in parts:
                k = _match_header_to_canonical(part)
                if k and k in expected_keys and k not in matched:
                    matched[k] = line

    score = len(matched)
    for k in matched:
        if k in ("itemName", "quantity"):
            score += 1  # bonus for essential columns
    return score, matched


def _find_expected_header_band(
    rows: list[list["OcrLine"]],
    page_h: float,
    expected_keys: set[str],
    table_bounds: dict[str, float] | None = None,
) -> tuple[int, list["OcrLine"], dict[str, "OcrLine"], int] | None:
    """Find the row with the most expectedColumns header matches.

    Returns (row_idx, header_row, matched_dict, score) or None if < 2 matches.
    Handles multi-line headers by checking adjacent row merges.
    Excludes party/contact/address blocks from header candidates.
    """
    y_min = table_bounds.get("yMin", page_h * 0.05) if table_bounds else page_h * 0.05
    y_max = table_bounds.get("yMax", page_h * 0.85) if table_bounds else page_h * 0.85

    candidates: list[tuple[int, float, int, list["OcrLine"], dict[str, "OcrLine"]]] = []

    for idx, row in enumerate(rows):
        row_y = _row_center_y(row)
        if row_y < y_min or row_y > y_max:
            continue

        text = _row_text(row)
        # Skip party/contact/address rows
        if _TABLE_BUSINESS_CONTACT_RE.search(text):
            continue
        if _BIZ_RE.search(_canonical_digits(text)):
            continue

        score, matched = _score_row_for_expected_columns(row, expected_keys)
        if score >= 2:
            candidates.append((idx, row_y, score, row, matched))

    if not candidates:
        return None

    # Sort by score descending, then y ascending (prefer higher score, earlier row)
    candidates.sort(key=lambda c: (-c[2], c[1]))
    best_idx, best_y, best_score, best_row, best_matched = candidates[0]

    # Try merging adjacent rows (multi-line header) to improve score
    for i in range(len(candidates)):
        idx_a, y_a, _sa, row_a, _ma = candidates[i]
        for j in range(i + 1, len(candidates)):
            idx_b, y_b, _sb, row_b, _mb = candidates[j]
            if abs(y_b - y_a) > page_h * 0.06:
                continue
            merged_row = row_a + row_b
            merged_score, merged_matched = _score_row_for_expected_columns(merged_row, expected_keys)
            if merged_score > best_score:
                best_score = merged_score
                best_idx = min(idx_a, idx_b)
                best_row = merged_row
                best_matched = merged_matched

    # T-6i: when table_bounds constrains the search area, lower the score threshold to 1.
    # Within a bounded region noise is reduced, so a single matched header is sufficient.
    min_score = 1 if table_bounds else 2
    if best_score < min_score:
        return None

    return best_idx, best_row, best_matched, best_score


def _build_boundaries_from_expected_columns(
    matched_dict: dict[str, "OcrLine"],
    expected_keys_ordered: list[str],
    page_w: float,
    table_x_min: float = 0.0,
    table_x_max: float | None = None,
    required_keys: set[str] | None = None,
    allow_single_match: bool = False,
) -> list[dict[str, Any]]:
    """Build column boundaries from matched expected header positions.

    - Matched headers → source: "expected_header"
    - Missing required headers → source: "interpolated_expected"
    - Optional headers with no match are excluded (T-6h: avoids column compression).
    - rowIndex columns are marked display_only=True and excluded from cell assignment.

    Returns sorted list of boundary dicts.
    """
    if table_x_max is None:
        table_x_max = page_w

    # T-6i: when table_bounds constrains the search area, allow a single matched header
    # to anchor boundary interpolation (reduced noise inside bounded region).
    _min_matches = 1 if (allow_single_match and required_keys and len(required_keys) >= 3) else 2
    if len(matched_dict) < _min_matches:
        return []

    # Collect positions for matched expected keys
    # (order_idx, key, x_left, cx, x_right, source)
    all_positions: list[tuple[int, str, float, float, float, str]] = []

    for key in expected_keys_ordered:
        if key in matched_dict:
            line = matched_dict[key]
            i = expected_keys_ordered.index(key)
            all_positions.append((i, key, line.x, line.cx, line.x + line.w, "expected_header"))

    matched_pos = list(all_positions)  # copy of matched-only

    # T-6h: count effective columns for half-width calculation
    # Only count required unmatched columns (optional unmatched are skipped)
    effective_count = len(matched_dict) + sum(
        1 for k in expected_keys_ordered
        if k not in matched_dict and (required_keys is None or k in required_keys)
    )
    half = (table_x_max - table_x_min) / max(effective_count, 1) * 0.4

    # Interpolate missing expected keys
    for key in expected_keys_ordered:
        if key in matched_dict:
            continue
        # T-6h: skip optional columns that have no matched header — interpolating them
        # compresses required column widths and causes boundary misalignment.
        if required_keys is not None and key not in required_keys:
            continue
        idx = expected_keys_ordered.index(key)

        prev_p = [(i, xl, cx, xr) for i, k, xl, cx, xr, _ in matched_pos if i < idx]
        next_p = [(i, xl, cx, xr) for i, k, xl, cx, xr, _ in matched_pos if i > idx]

        if not prev_p and not next_p:
            continue

        if not prev_p:
            ni, nx_l, ncx, nx_r = min(next_p, key=lambda t: t[0])
            span = (nx_r - table_x_min) / max(effective_count, 1)
            cx_est = max(table_x_min + span * 0.5, ncx - span * (ni - idx + 1))
        elif not next_p:
            pi, px_l, pcx, px_r = max(prev_p, key=lambda t: t[0])
            span = (table_x_max - px_l) / max(effective_count - pi, 1)
            cx_est = min(table_x_max - span * 0.5, pcx + span * (idx - pi))
        else:
            pi, px_l, pcx, px_r = max(prev_p, key=lambda t: t[0])
            ni, nx_l, ncx, nx_r = min(next_p, key=lambda t: t[0])
            gap = max(ni - pi, 1)
            frac = (idx - pi) / gap
            cx_est = pcx + frac * (ncx - pcx)

        all_positions.append((idx, key, cx_est - half, cx_est, cx_est + half, "interpolated_expected"))

    all_positions.sort(key=lambda t: (t[0], t[3]))  # sort by order_idx then cx

    if len(all_positions) < 2:
        return []

    # Build boundary edges using adjacent midpoints
    boundaries: list[dict[str, Any]] = []
    for i, (ord_idx, key, x_left, cx, x_right, source) in enumerate(all_positions):
        if i == 0:
            # T-6h: first column always starts at the table left edge so leftmost
            # tokens (e.g. item names) are captured even when the header is not found.
            x_start = table_x_min
        else:
            prev_x_right = all_positions[i - 1][4]
            gap_mid = (prev_x_right + x_left) / 2.0
            if gap_mid <= all_positions[i - 1][3]:
                gap_mid = (all_positions[i - 1][3] + cx) / 2.0
            x_start = gap_mid

        if i == len(all_positions) - 1:
            x_end = table_x_max
        else:
            next_x_left = all_positions[i + 1][2]
            gap_mid = (x_right + next_x_left) / 2.0
            if gap_mid >= all_positions[i + 1][3]:
                gap_mid = (cx + all_positions[i + 1][3]) / 2.0
            x_end = gap_mid

        boundaries.append({
            "canonical_key": key,
            "x_start": x_start,
            "x_end": x_end,
            "header_cx": cx,
            "source": source,
            "display_only": key == "rowIndex",
        })

    return boundaries


def _build_boundaries_from_column_guides(
    required_keys: list[str],
    all_keys: list[str],
    column_guides_ocr: list[float],
    table_bounds: dict[str, float],
    page_w: float,
    debug: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build column boundaries directly from Template colGuides (absolute OCR-space x positions).

    T-6j: Bypasses header OCR detection. Used when template provides explicit column dividers.

    column_guides_ocr: sorted absolute x positions of column DIVIDERS in OCR coordinate space.
    For N columns, expects N-1 dividers. Handles mismatches gracefully.
    """
    xMin = table_bounds.get("xMin", 0.0)
    xMax = table_bounds.get("xMax", page_w)

    n_cols = len(required_keys)
    sorted_guides = sorted(g for g in column_guides_ocr if xMin <= g <= xMax)
    n_guides = len(sorted_guides)
    mismatch: str | None = None

    # Build divider list: [xMin, ...guides..., xMax]
    if n_guides == n_cols - 1:
        # Perfect match: N-1 dividers for N columns
        dividers = [xMin] + sorted_guides + [xMax]
    elif n_guides >= n_cols:
        # Too many guides: use first N-1
        dividers = [xMin] + sorted_guides[: n_cols - 1] + [xMax]
        mismatch = f"too_many:{n_guides}vs{n_cols - 1}"
    elif n_guides > 0:
        # Fewer guides than needed: split largest gap until we have N+1 dividers
        dividers = [xMin] + sorted_guides + [xMax]
        while len(dividers) - 1 < n_cols:
            gaps = [(dividers[i + 1] - dividers[i], i) for i in range(len(dividers) - 1)]
            _, split_at = max(gaps)
            mid = (dividers[split_at] + dividers[split_at + 1]) / 2.0
            dividers.insert(split_at + 1, mid)
        mismatch = f"fewer:{n_guides}vs{n_cols - 1}"
    else:
        # No guides: distribute evenly
        step = (xMax - xMin) / max(n_cols, 1)
        dividers = [xMin + i * step for i in range(n_cols + 1)]
        mismatch = "no_guides_even_split"

    boundaries: list[dict[str, Any]] = []
    for i, key in enumerate(required_keys):
        x_start = dividers[i] if i < len(dividers) else xMin
        x_end = dividers[i + 1] if i + 1 < len(dividers) else xMax
        boundaries.append({
            "canonical_key": key,
            "x_start": x_start,
            "x_end": x_end,
            "header_cx": (x_start + x_end) / 2.0,
            "source": "template_colguide",
            "display_only": key == "rowIndex",
        })

    if debug is not None:
        debug["columnGuideMode"] = "boundary_lines" if mismatch is None else "interpolated"
        debug["columnGuideExpectedCount"] = n_cols - 1
        debug["columnGuideActualCount"] = n_guides
        debug["columnGuideOcrSpace"] = sorted_guides
        debug["columnGuideMismatch"] = mismatch
        debug["columnGuideBoundaries"] = [
            {"key": b["canonical_key"], "x": [round(b["x_start"], 1), round(b["x_end"], 1)]}
            for b in boundaries
        ]

    return boundaries


def _extract_items_using_boundaries(
    scope_rows: list[list["OcrLine"]],
    boundaries: list[dict[str, Any]],
    table_bounds: dict[str, float] | None,
    page_h: float,
    required: list[str],
    all_keys: list[str],
    non_canonical_expected_keys: list[str],
    debug: dict[str, Any] | None = None,
    skip_contact_filter: bool = False,
) -> list[dict[str, Any]]:
    """Extract table items using pre-built column boundaries.

    T-6j: shared extraction logic used by both colGuides path and header-detection path.
    Does NOT require a known header row — scans all rows in table_bounds area.
    """
    y_min_row = (table_bounds.get("yMin", 0.0)) if table_bounds else 0.0
    # T-6l-fix: same 0.98 cutoff as _table_items_with_expected_columns
    y_max_row = (table_bounds.get("yMax", page_h * 0.98)) if table_bounds else page_h * 0.98
    display_only_keys = {b["canonical_key"] for b in boundaries if b.get("display_only", False)}
    has_name_col = any(b["canonical_key"] == "itemName" for b in boundaries)
    data_expected_keys = [k for k in all_keys if k != "rowIndex"]
    _canonical_col_set = set(_TABLE_ROW_COLUMNS)
    non_can = [k for k in all_keys if k not in _canonical_col_set and k != "rowIndex"]
    items: list[dict[str, Any]] = []
    _cand_before = 0
    _cand_after = 0

    for row in scope_rows:
        row_y = _row_center_y(row)
        if row_y < y_min_row or row_y > y_max_row:
            continue
        _cand_before += 1
        text = _row_text(row)
        if _is_table_header_row(text):
            if debug is not None:
                (debug.setdefault("rejectedRows", [])).append(
                    {"reason": "header_or_contact", "text": text[:60], "y": round(row_y, 1)}
                )
            continue
        # T-6j-fix: pre-compute strong item signal for colGuides bypass
        _signal = skip_contact_filter and _has_strong_item_signal(text)
        if _is_business_contact_line(text) and not _signal:
            if debug is not None:
                (debug.setdefault("rejectedRows", [])).append(
                    {"reason": "header_or_contact", "text": text[:60], "y": round(row_y, 1)}
                )
            continue
        if _is_summary_row_for_items(text):
            if debug is not None:
                (debug.setdefault("rejectedRows", [])).append(
                    {"reason": "summary_row", "text": text[:60], "y": round(row_y, 1)}
                )
            continue
        # T-6j-fix: notice_or_party filter also bypassed by strong item signal
        if _is_table_notice_or_party_line(text) and not _signal:
            if debug is not None:
                (debug.setdefault("rejectedRows", [])).append(
                    {"reason": "notice_or_party", "text": text[:60], "y": round(row_y, 1)}
                )
            continue

        col_texts: dict[str, list[str]] = {}
        for line in sorted(row, key=lambda l: l.x):
            cv = _clean_value(line.text)
            if not cv:
                continue
            key = _assign_canonical_by_x(line.cx, boundaries)
            if key is not None and key not in display_only_keys:
                col_texts.setdefault(key, []).append(cv)

        item: dict[str, Any] = {k: "" for k in _TABLE_ROW_COLUMNS if k != "rowIndex"}
        for _nck in non_can:
            item[_nck] = ""
        item["rawText"] = _summarize_table_row(text)
        item["sourceBboxes"] = [_bbox_dict(l) for l in row]
        item["source"] = "template_colguides_expected_columns"
        item["_row_y"] = row_y

        for key, texts in col_texts.items():
            if key in item:
                merged = _clean_value(" ".join(t for t in texts if t))
                _split_composite_cell_value(key, merged, item)

        # T-6g-fix: clear comma-formatted amounts from date/code fields
        for _date_key in ("expiryDate", "manufacturingNo", "lotNo"):
            _val = str(item.get(_date_key) or "")
            if _val and re.search(r"\d{1,3}(?:,\d{3})+", _val) and not re.search(r"[가-힣A-Za-z]", _val):
                item[_date_key] = ""

        expected_col_hit_count = sum(1 for k in data_expected_keys if item.get(k))
        if _is_item_name_only_split_row(item, len(items)):
            if debug is not None:
                (debug.setdefault("rejectedRows", [])).append(
                    {"reason": "item_name_only_split", "text": text[:60], "y": round(row_y, 1),
                     "expectedColumnHitCount": expected_col_hit_count}
                )
            continue

        if not any(item.get(k) for k in (required + non_can)):
            if debug is not None:
                (debug.setdefault("rejectedRows", [])).append(
                    {"reason": "no_meaningful_value", "text": text[:60], "y": round(row_y, 1)}
                )
            continue

        if has_name_col and not item.get("itemName"):
            has_code = bool(item.get("itemCode"))
            has_qty = bool(item.get("quantity"))
            has_price = bool(item.get("unitPrice") or item.get("amount") or item.get("supplyAmount"))
            has_lot = bool(item.get("lotNo") or item.get("serialNo") or item.get("manufacturingNo"))
            has_exp = bool(item.get("expiryDate") or item.get("manufacturingNo"))
            has_spec_val = bool(item.get("spec"))
            row_has_data = (
                expected_col_hit_count >= 2
                or (has_code and (has_qty or has_price))
                or (has_qty and has_price)
                or (has_lot and has_qty)
                or (has_lot and has_price)
                or (has_exp and has_qty)
                or (has_spec_val and (has_qty or has_price))
                or (has_lot and has_exp)
                or (has_code and has_lot)
                or (has_code and has_exp)
            )
            if not row_has_data:
                if debug is not None:
                    (debug.setdefault("rejectedRows", [])).append(
                        {"reason": "no_item_name", "text": text[:60], "y": round(row_y, 1),
                         "expectedColumnHitCount": expected_col_hit_count}
                    )
                continue

        if debug is not None:
            (debug.setdefault("rowCandidates", [])).append({
                "y": round(row_y, 1),
                "itemName": item.get("itemName", "")[:30],
                "quantity": item.get("quantity", ""),
                "expectedColumnHitCount": expected_col_hit_count,
                "text": text[:40],
            })
        _cand_after += 1
        items.append(item)

    if debug is not None:
        debug["rowCandidateCountBeforeFilter"] = _cand_before
        debug["rowCandidateCountAfterFilter"] = _cand_after

    return items


def _table_items_with_expected_columns(
    lines: list["OcrLine"],
    page_h: float,
    page_w: float,
    expected_columns: dict[str, list[str]],
    table_bounds: dict[str, float] | None = None,
    debug: dict[str, Any] | None = None,
    column_guides: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Extract table rows using expectedColumns as header matching hint.

    Flow (T-6j: column_guides path):
    0. If column_guides provided: build boundaries directly, skip header detection.
    Flow (standard):
    1. Build ordered expected key list from required + optional
    2. Find the y-band where expected headers cluster
    3. Build column boundaries (with interpolation for missing headers)
    4. Extract rows below the header band
    5. Return [] on failure (caller falls back to auto-detection)
    """
    required = expected_columns.get("required") or []
    optional = expected_columns.get("optional") or []
    # Preserve order: required first, then optional, deduplicated
    seen: set[str] = set()
    all_keys: list[str] = []
    for k in required + optional:
        if k not in seen:
            seen.add(k)
            all_keys.append(k)
    expected_set = set(all_keys)

    if debug is not None:
        debug["expectedColumns"] = all_keys
        debug["extractionSource"] = "expected_columns_header_match"

    if not all_keys:
        return []

    # Filter lines to table_bounds if provided
    if table_bounds:
        y_min_b = table_bounds.get("yMin", 0.0)
        y_max_b = table_bounds.get("yMax", page_h)
        x_min_b = table_bounds.get("xMin", 0.0)
        x_max_b = table_bounds.get("xMax", page_w)
        scope_lines = [
            l for l in lines
            if y_min_b <= l.cy <= y_max_b and x_min_b <= l.cx <= x_max_b
        ]
        tx_min = x_min_b
        tx_max = x_max_b
    else:
        scope_lines = lines
        tx_min = 0.0
        tx_max = page_w

    # T-6g-fix: tighter row grouping so densely-spaced table rows are not merged
    scope_rows = _group_rows(scope_lines, tolerance_factor=0.55)

    # T-6j: colGuides path — bypass header detection entirely when template provides
    # explicit column dividers. Works even when OCR garbles the column header text.
    if column_guides and table_bounds and len(column_guides) > 0:
        cg_debug: dict[str, Any] = {}
        cg_boundaries = _build_boundaries_from_column_guides(
            required, all_keys, column_guides, table_bounds, page_w, debug=cg_debug,
        )
        if debug is not None:
            debug.update(cg_debug)
            debug["headerSkippedBecauseColGuides"] = True
            debug["extractionSource"] = "template_colguides_expected_columns"
            debug["tableBoundsUsed"] = True
            debug["tableBoundsSource"] = table_bounds.get("source", "template")
            debug["headerBandFound"] = False
            debug["columnGuidesReceived"] = True
            debug["columnGuidesCount"] = len(column_guides)
            debug["columnGuidesUsedAttempted"] = True
            debug["rejectedRows"] = []
            debug["rowCandidates"] = []
        if len(cg_boundaries) >= 2:
            result = _extract_items_using_boundaries(
                scope_rows, cg_boundaries, table_bounds, page_h, required, all_keys,
                non_canonical_expected_keys=[], debug=debug,
                skip_contact_filter=True,
            )
            if result:
                return result
        if debug is not None:
            debug["fallbackReason"] = "colguides_path_yielded_no_items"

    # Find header band
    header_result = _find_expected_header_band(scope_rows, page_h, expected_set, table_bounds)

    if debug is not None:
        debug["headerBandFound"] = header_result is not None
        debug["tableBoundsUsed"] = bool(table_bounds)
        debug["tableBoundsSource"] = (table_bounds.get("source", "explicit") if table_bounds else "none")
        debug["tableBounds"] = table_bounds

    if header_result is None:
        if debug is not None:
            debug["fallbackReason"] = "expected_header_band_not_found"
        return []

    header_idx, header_row, matched_dict, header_score = header_result

    if debug is not None:
        debug["selectedHeaderBand"] = {
            "y": round(_row_center_y(header_row), 1),
            "score": header_score,
            "matchedHeaders": {k: round(line.cx, 1) for k, line in matched_dict.items()},
        }
        debug["matchedHeaders"] = list(matched_dict.keys())
        debug["missingExpectedHeaders"] = [k for k in required if k not in matched_dict]

    # Build boundaries — T-6h: pass required_keys so optional unmatched columns are excluded
    # T-6i: allow_single_match when table_bounds provided (bounded area has less noise)
    boundaries = _build_boundaries_from_expected_columns(
        matched_dict, all_keys, page_w, table_x_min=tx_min, table_x_max=tx_max,
        required_keys=set(required),
        allow_single_match=bool(table_bounds),
    )

    if debug is not None:
        debug["interpolatedColumns"] = [b["canonical_key"] for b in boundaries if b.get("source") == "interpolated_expected"]
        debug["boundaries"] = [
            {
                "canonicalKey": b["canonical_key"],
                "xStart": round(b["x_start"], 1),
                "xEnd": round(b["x_end"], 1),
                "source": b.get("source", "unknown"),
                "displayOnly": b.get("display_only", False),
            }
            for b in boundaries
        ]
        debug["rejectedRows"] = []
        debug["rowCandidates"] = []

    if len(boundaries) < 2:
        if debug is not None:
            debug["fallbackReason"] = "boundary_build_failed"
        return []

    display_only_keys = {b["canonical_key"] for b in boundaries if b.get("display_only", False)}
    has_name_col = any(b["canonical_key"] == "itemName" for b in boundaries)
    # T-6g: data keys to count expected column hits (exclude displayOnly rowIndex)
    data_expected_keys = [k for k in all_keys if k != "rowIndex"]
    # T-6h: non-canonical expected keys (e.g. serialLotComposite, consumerUnitPrice)
    _canonical_col_set = set(_TABLE_ROW_COLUMNS)
    non_canonical_expected_keys = [k for k in all_keys if k not in _canonical_col_set and k != "rowIndex"]
    header_y = _row_center_y(header_row)
    last_header_y = header_y

    items: list[dict[str, Any]] = []

    # T-6i: when table_bounds is provided, use its yMax as the row extraction limit.
    # T-6l-fix: extend default cutoff from 0.96 to 0.98 to capture bottom-of-page rows
    # (e.g. 6.pdf landscape page where row 6 center y ≈ 97% of page height).
    _row_y_max = table_bounds.get("yMax", page_h * 0.98) if table_bounds else page_h * 0.98

    for idx in range(header_idx + 1, len(scope_rows)):
        row = scope_rows[idx]
        row_y = _row_center_y(row)
        if row_y <= last_header_y or row_y > _row_y_max:
            continue

        text = _row_text(row)

        if _is_summary_row_for_items(text):
            if debug is not None:
                debug["rejectedRows"].append({
                    "reason": "summary_row", "text": text[:60], "y": round(row_y, 1),
                })
            # T-6g-fix: raise break threshold to 0.85 so rolling subtotals (소계/누계)
            # mid-table don't trigger premature break for multi-group tables like 1.jpg.
            min_before_break = min(3, len(required)) if required else 2
            if items and len(items) >= min_before_break and row_y >= page_h * 0.85:
                if debug is not None:
                    debug["rowEndReason"] = f"summary_row at y={round(row_y,1)} after {len(items)} rows"
                break
            continue

        if _is_table_header_row(text) or _is_business_contact_line(text):
            if row_y < header_y + page_h * 0.04:
                last_header_y = row_y
            if debug is not None:
                debug["rejectedRows"].append({
                    "reason": "header_or_contact", "text": text[:60], "y": round(row_y, 1),
                })
            continue
        if _is_table_notice_or_party_line(text):
            if debug is not None:
                debug["rejectedRows"].append({
                    "reason": "notice_or_party", "text": text[:60], "y": round(row_y, 1),
                })
            continue

        col_texts: dict[str, list[str]] = {}
        for line in sorted(row, key=lambda l: l.x):
            cv = _clean_value(line.text)
            if not cv:
                continue
            key = _assign_canonical_by_x(line.cx, boundaries)
            if key is not None and key not in display_only_keys:
                col_texts.setdefault(key, []).append(cv)

        item: dict[str, Any] = {k: "" for k in _TABLE_ROW_COLUMNS if k != "rowIndex"}
        # T-6h: also initialize non-canonical expected keys so boundary tokens can be stored
        for _nck in non_canonical_expected_keys:
            item[_nck] = ""
        item["rawText"] = _summarize_table_row(text)
        item["sourceBboxes"] = [_bbox_dict(l) for l in row]
        item["source"] = "expected_columns_header_match"
        item["_row_y"] = row_y

        for key, texts in col_texts.items():
            if key in item:
                merged = _clean_value(" ".join(t for t in texts if t))
                _split_composite_cell_value(key, merged, item)

        # T-6g-fix: clear date/code fields that contain comma-formatted amounts
        # e.g. expiryDate='18,098,750' is an amount, not a date → would falsely
        # inflate expected_col_hit_count and cause summary rows to slip through.
        for _date_key in ("expiryDate", "manufacturingNo", "lotNo"):
            _val = str(item.get(_date_key) or "")
            if _val and re.search(r"\d{1,3}(?:,\d{3})+", _val) and not re.search(r"[가-힣A-Za-z]", _val):
                item[_date_key] = ""

        # T-6g: count expected column hits for smarter validity check
        expected_col_hit_count = sum(1 for k in data_expected_keys if item.get(k))
        if _is_item_name_only_split_row(item, len(items)):
            if debug is not None:
                debug["rejectedRows"].append({
                    "reason": "item_name_only_split", "text": text[:60], "y": round(row_y, 1),
                    "expectedColumnHitCount": expected_col_hit_count,
                })
            continue

        # Row validity
        if has_name_col:
            if not item.get("itemName"):
                has_code = bool(item.get("itemCode"))
                has_qty = bool(item.get("quantity"))
                has_price = bool(item.get("unitPrice") or item.get("amount") or item.get("supplyAmount"))
                has_ins = bool(item.get("insuranceCode"))
                has_lot = bool(item.get("lotNo") or item.get("serialNo") or item.get("manufacturingNo"))
                has_exp = bool(item.get("expiryDate") or item.get("manufacturingNo"))
                has_spec_val = bool(item.get("spec"))

                # T-7a: Quantity-only row merger — when a row has ONLY a quantity value
                # and no itemName, merge it into the preceding accepted item if:
                #   (a) quantity is in expected columns
                #   (b) the preceding item has serialLotComposite/unit but no quantity
                #   (c) only the quantity column has a value in this row
                #   (d) the quantity is a plausible numeric value (1–100,000)
                # This handles PDFs where the quantity cell is on a slightly different y-band.
                if (
                    has_qty
                    and expected_col_hit_count == 1
                    and "quantity" in expected_set
                    and items
                    and not items[-1].get("quantity")
                    and (
                        items[-1].get("serialLotComposite")
                        or (items[-1].get("unit") and items[-1].get("serialNo"))
                    )
                ):
                    _qty_str = str(item["quantity"])
                    _qty_digits = re.sub(r"\D", "", _qty_str)
                    if _qty_digits and 1 <= int(_qty_digits) <= 100_000:
                        items[-1]["quantity"] = _qty_str
                        if debug is not None:
                            debug["rejectedRows"].append({
                                "reason": "quantity_merged_into_preceding",
                                "text": text[:60], "y": round(row_y, 1),
                                "mergedQty": _qty_str,
                            })
                        continue

                row_has_data = (
                    expected_col_hit_count >= 2                       # T-6g: primary: 2+ expected cols
                    or (has_code and (has_qty or has_price))
                    or (has_qty and has_price)
                    or (has_ins and has_code)
                    or (has_lot and has_qty)
                    or (has_lot and has_price)                        # T-6g: lot + amount
                    or (has_exp and has_qty)                          # T-6g: expiry + qty
                    or (has_spec_val and (has_qty or has_price))      # T-6g: spec + qty/price
                    or (has_lot and has_exp)                          # T-6g-fix: lot+expiry (lot table)
                    or (has_code and has_lot)                         # T-6g-fix: code+lot (lot table)
                    or (has_code and has_exp)                         # T-6g-fix: code+expiry (lot table)
                )
                if not row_has_data:
                    if debug is not None:
                        debug["rejectedRows"].append({
                            "reason": "no_item_name", "text": text[:60], "y": round(row_y, 1),
                            "expectedColumnHitCount": expected_col_hit_count,
                        })
                    continue
            elif _is_table_notice_or_party_line(item["itemName"]):
                if debug is not None:
                    debug["rejectedRows"].append({
                        "reason": "notice_or_party", "text": text[:60], "y": round(row_y, 1),
                        "expectedColumnHitCount": expected_col_hit_count,
                    })
                continue
        else:
            has_val = any(item.get(k) for k in ("itemCode", "quantity", "unitPrice", "amount", "lotNo", "serialNo"))
            if not has_val and expected_col_hit_count < 2:
                if debug is not None:
                    debug["rejectedRows"].append({
                        "reason": "no_meaningful_value", "text": text[:60], "y": round(row_y, 1),
                        "expectedColumnHitCount": expected_col_hit_count,
                    })
                continue

        if debug is not None:
            debug["rowCandidates"].append({
                "y": round(row_y, 1),
                "itemName": item.get("itemName", "")[:30],
                "quantity": item.get("quantity", ""),
                "text": text[:40],
                "expectedColumnHitCount": expected_col_hit_count,
            })
        items.append(item)

    if debug is not None:
        debug["finalRows"] = len(items)
        if not items and "fallbackReason" not in debug:
            debug["fallbackReason"] = "no_valid_rows_extracted"

    return items


def _normalize_date(full_text: str) -> str:
    match = _DATE_RE.search(full_text or "")
    if not match:
        compact = re.sub(r"\D", "", full_text or "")
        m = re.search(r"(20\d{2})(\d{2})(\d{2})", compact)
        if not m:
            return ""
        year, month, day = m.group(1), m.group(2), m.group(3)
    elif match.group(1):
        year, month, day = match.group(1), match.group(2), match.group(3)
    elif match.group(4):
        year, month, day = match.group(4), match.group(5), match.group(6)
    else:
        yy = int(match.group(7))
        year = str(2000 + yy if yy < 70 else 1900 + yy)
        month, day = match.group(8), match.group(9)
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _same_row_candidates(lines: list[OcrLine], anchor: OcrLine) -> list[OcrLine]:
    return [
        line
        for line in lines
        if line is not anchor and abs(line.cy - anchor.cy) <= max(anchor.h, line.h) * 1.2 and line.x > anchor.x
    ]


def _value_after_anchor(lines: list[OcrLine], anchor_re: re.Pattern, kind: str) -> str:
    ordered = sorted(lines, key=lambda line: (line.y, line.x))
    for idx, line in enumerate(ordered):
        match = anchor_re.search(line.text)
        if not match:
            continue
        same_line = _clean_value(line.text[match.end():])
        if kind == "company":
            same_line = _clean_company_candidate(same_line)
        if _candidate_ok(same_line, kind):
            return same_line
        for peer in _same_row_candidates(ordered, line):
            candidate = _clean_company_candidate(peer.text) if kind == "company" else _clean_value(peer.text)
            if _candidate_ok(candidate, kind):
                return candidate
        for nxt in ordered[idx + 1 : idx + 4]:
            candidate = _clean_company_candidate(nxt.text) if kind == "company" else _clean_value(nxt.text)
            if _candidate_ok(candidate, kind):
                return candidate
    return ""


def _company_candidates(lines: list[OcrLine], page_h: float, limit_y: float) -> list[tuple[float, float, str]]:
    candidates: list[tuple[float, float, str]] = []
    seen: set[str] = set()
    for line in sorted(lines, key=lambda item: (item.y, item.x)):
        if line.cy > limit_y or line.cy > page_h * 0.78:
            continue
        candidate = _clean_company_candidate(line.text)
        if not _candidate_ok(candidate, "company"):
            continue
        key = re.sub(r"\s+", "", candidate)
        if key in seen:
            continue
        seen.add(key)
        candidates.append((line.cx, line.cy, candidate))
    return candidates


def _biz_candidates(lines: list[OcrLine], limit_y: float) -> list[tuple[float, float, str, OcrLine]]:
    candidates: list[tuple[float, float, str, OcrLine]] = []
    seen: set[str] = set()
    for line in sorted(lines, key=lambda item: (item.x, item.y)):
        if line.cy > limit_y:
            continue
        value = _format_biz(line.text)
        if not value or value in seen:
            continue
        seen.add(value)
        candidates.append((line.cx, line.cy, value, line))
    return candidates


def _nearest_company(
    biz: tuple[float, float, str, OcrLine],
    companies: list[tuple[float, float, str]],
    used: set[str],
    page_w: float,
    page_h: float,
    side: str | None = None,
    split_x: float | None = None,
) -> str:
    bx, by, _, _ = biz
    scored: list[tuple[float, str]] = []
    for cx, cy, company in companies:
        key = re.sub(r"\s+", "", company)
        if key in used:
            continue
        if side and split_x is not None:
            in_side = cx <= split_x if side == "left" else cx > split_x
            if not in_side:
                continue
        dx = abs(cx - bx) / max(page_w, 1)
        dy = abs(cy - by) / max(page_h, 1)
        if dx > 0.45 or dy > 0.28:
            continue
        hint_bonus = -0.10 if _COMPANY_HINT_RE.search(company) else 0
        scored.append((dx * 1.5 + dy + hint_bonus, company))
    if not scored:
        return ""
    scored.sort(key=lambda item: item[0])
    return scored[0][1]


def _local_company_near_biz(
    lines: list[OcrLine],
    biz: tuple[float, float, str, OcrLine],
    used: set[str],
    page_w: float,
    page_h: float,
) -> str:
    bx, by, _, _ = biz
    scored: list[tuple[float, str]] = []
    for line in lines:
        candidate = _clean_company_candidate(line.text)
        if not _candidate_ok(candidate, "company"):
            continue
        key = re.sub(r"\s+", "", candidate)
        if key in used:
            continue
        dx = abs(line.cx - bx) / max(page_w, 1)
        dy = abs(line.cy - by) / max(page_h, 1)
        if dx > 0.24 or dy > 0.24:
            continue
        if _TOTAL_AMOUNT_ANCHOR_RE.search(line.text) or _TABLE_HEADER_TOKEN_RE.search(line.text):
            continue
        scored.append((dx * 1.2 + dy, candidate))
    if not scored:
        return ""
    scored.sort(key=lambda item: item[0])
    return scored[0][1]


def _fallback_company_for_side(
    companies: list[tuple[float, float, str]],
    side: str,
    split_x: float,
    used: set[str],
) -> str:
    pool = [
        (abs(cx - split_x), company)
        for cx, _, company in companies
        if (cx <= split_x if side == "left" else cx > split_x)
        and re.sub(r"\s+", "", company) not in used
    ]
    if not pool:
        return ""
    pool.sort(key=lambda item: item[0])
    return pool[0][1]


def _assign_unique_fallbacks(
    supplier: dict[str, str],
    buyer: dict[str, str],
    companies: list[tuple[float, float, str]],
    split_x: float,
    used_companies: set[str],
) -> None:
    left = [
        (abs(cx - split_x), company)
        for cx, _, company in companies
        if cx <= split_x and re.sub(r"\s+", "", company) not in used_companies
    ]
    right = [
        (abs(cx - split_x), company)
        for cx, _, company in companies
        if cx > split_x and re.sub(r"\s+", "", company) not in used_companies
    ]
    left.sort(key=lambda item: item[0])
    right.sort(key=lambda item: item[0])

    if not supplier["company"] and left:
        supplier["company"] = left[0][1]
        used_companies.add(re.sub(r"\s+", "", supplier["company"]))
    if not buyer["company"] and right:
        buyer["company"] = right[0][1]
        used_companies.add(re.sub(r"\s+", "", buyer["company"]))

    remaining = [
        (cx, company)
        for cx, _, company in companies
        if re.sub(r"\s+", "", company) not in used_companies
    ]
    if not supplier["company"] and not buyer["company"] and len(remaining) >= 2:
        remaining.sort(key=lambda item: item[0])
        supplier["company"] = remaining[0][1]
        buyer["company"] = remaining[-1][1]
    elif not supplier["company"] and remaining:
        remaining.sort(key=lambda item: item[0])
        supplier["company"] = remaining[0][1]
    elif not buyer["company"] and remaining:
        remaining.sort(key=lambda item: item[0])
        buyer["company"] = remaining[-1][1]


def _address_near(lines: list[OcrLine], x_center: float, y_center: float, page_w: float, page_h: float) -> str:
    candidates: list[tuple[float, str]] = []
    for line in lines:
        if abs(line.cx - x_center) / max(page_w, 1) > 0.45 or abs(line.cy - y_center) / max(page_h, 1) > 0.25:
            continue
        text = _clean_value(line.text)
        if _candidate_ok(text, "address"):
            candidates.append((abs(line.cy - y_center), text))
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1] if candidates else ""


def _rep_near(lines: list[OcrLine], x_center: float, y_center: float, page_w: float, page_h: float) -> str:
    scoped = [
        line
        for line in lines
        if abs(line.cx - x_center) / max(page_w, 1) <= 0.35 and abs(line.cy - y_center) / max(page_h, 1) <= 0.22
    ]
    return _value_after_anchor(scoped, _REP_ANCHOR_RE, "representative")


def _is_representative_candidate(text: str) -> bool:
    value = _clean_value(text)
    value = re.sub(r"^(?:\ub300\s*\ud45c(?:\uc790|\uc790\uba85)?|\uc131\s*\uba85|\ub300\s*\ud45c\s*\uc774\s*\uc0ac)\s*[:：]?", "", value).strip()
    compact = re.sub(r"\s+", "", value)
    if not compact or re.search(r"\d", compact):
        return False
    if _TABLE_STANDALONE_LABEL_RE.fullmatch(compact) or _TABLE_BUSINESS_CONTACT_RE.search(value):
        return False
    if _COMPANY_HINT_RE.search(value) or _ADDRESS_HINT_RE.search(value) or re.search(r"(?:\ub85c|\uae38|\ubc88\uae38)\s*\d*|\d+\s*\([\uac00-\ud7a3]{1,12}\ub3d9\)", value):
        return False
    if re.search(
        r"\ud2b9\uae30|\uae30\ud0c0|\uc5f0\ub77d|\ubd80\uac00|\ubc30\uc1a1|\ud488\ubaa9|\ub2f4\ub2f9|\ucf54\ub4dc|"
        r"\uacc4\uc57d|\uc794\uc561|\uc138\ud45c|\uac70\ub798\uba85\uc138|\uc0c1\ud750|\uc0c1\ud638|\uc5c5\ud14c|\uc5c5\ud0dc|\ucd1d\ubaa9|\ud1b5\ubaa9|"
        r"\uc591\uc57d|\ub3c4\uba54|\uc6d4\ub9d0|\ub9e4\uc7a5|\uc74c\uc2dd|\uc678\uc57d|\uacf5\uae09|"
        r"\uc778\uc218|\uc778\s*\uc218|\ud655\uc778|\uc11c\uba85|\ubcf4\uad00",
        value,
    ):
        return False
    if re.fullmatch(r"[\uac00-\ud7a3]{2,5}(?:[,/][\uac00-\ud7a3]{2,5})?", compact):
        return True
    return bool(re.fullmatch(r"[A-Z][A-Z\s.]{3,30}", value))


def _clean_representative_candidate(text: str) -> str:
    value = _clean_value(text)
    match = _REP_ANCHOR_RE.search(value)
    if match:
        value = value[match.end() :]
    value = re.sub(r"^(?:\ub300\s*\ud45c(?:\uc790|\uc790\uba85)?|\uc131\s*\uba85|\ub300\s*\ud45c\s*\uc774\s*\uc0ac)\s*[:：]?", "", value).strip()
    value = re.sub(r"\(\s*\uc778\s*\)|[\[\]()]|[:：]", "", value).strip()
    value = re.sub(r"^([\uac00-\ud7a3]{2,5})\s*\uc778$", r"\1", value).strip()
    return value if _is_representative_candidate(value) else ""


def _representative_from_scope(lines: list[OcrLine]) -> str:
    ordered = sorted(lines, key=lambda item: (item.y, item.x))
    for idx, line in enumerate(ordered):
        if not _REP_ANCHOR_RE.search(line.text):
            continue
        same = _clean_representative_candidate(_REP_ANCHOR_RE.sub("", line.text, count=1))
        if same:
            return same
        for peer in _same_row_candidates(ordered, line):
            candidate = _clean_representative_candidate(peer.text)
            if candidate:
                return candidate
        for nxt in ordered[idx + 1 : idx + 5]:
            candidate = _clean_representative_candidate(nxt.text)
            if candidate:
                return candidate
    candidates: list[tuple[int, str]] = []
    for line in ordered:
        candidate = _clean_representative_candidate(line.text)
        if candidate:
            score = 10
            if "," in candidate or "/" in candidate:
                score += 12
            if re.fullmatch(r"[\uac00-\ud7a3]{2,3}", candidate):
                score += 4
            candidates.append((score, candidate))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: -item[0])
    return candidates[0][1]


def _should_replace_representative(current: str, candidate: str) -> bool:
    if not candidate:
        return False
    if not current:
        return True
    current_ascii = bool(re.fullmatch(r"[A-Z][A-Z\s.]{2,30}", current))
    candidate_ascii = bool(re.fullmatch(r"[A-Z][A-Z\s.]{3,30}", candidate))
    if current_ascii and candidate_ascii and len(re.sub(r"\s+", "", candidate)) >= len(re.sub(r"\s+", "", current)) + 3:
        return True
    return not _is_representative_candidate(current)


def _is_address_candidate_line(text: str) -> bool:
    value = _clean_value(text)
    compact = re.sub(r"\s+", "", value)
    if len(compact) < 5:
        return False
    if _BIZ_RE.search(_canonical_digits(value)) or _PHONE_RE.search(value):
        return False
    if _COMPANY_HINT_RE.search(value) or _REP_ANCHOR_RE.search(value):
        return False
    if _TABLE_SUMMARY_RE.search(value) or _TABLE_HEADER_TOKEN_RE.search(value) or _has_product_hint(value):
        return False
    if _amount_values(value) and not _ADDRESS_TOKEN_RE.search(value):
        return False
    return bool(_ADDRESS_TOKEN_RE.search(value) or re.search(r"\d+\s*\([\uac00-\ud7a3]{1,12}\ub3d9\)", compact))


def _clean_address_candidate_line(text: str) -> str:
    value = _clean_value(text)
    value = re.sub(r"^(?:\uc8fc\s*\uc18c|\uc18c\s*\uc7ac\s*\uc9c0|\uc0ac\s*\uc5c5\s*\uc7a5(?:\s*\uc8fc\s*\uc18c)?)\s*[:：]?", "", value).strip()
    return value if _is_address_candidate_line(value) else ""


def _is_address_tail_fragment(text: str) -> bool:
    """Return True if text looks like an address tail continuation.

    Accepts lines like '302호(당산동4가, SK V1 센터)' that follow an address
    ending with a unit number, but rejects table rows, phone-only lines, etc.
    """
    value = _clean_value(text or "")
    if not value or len(re.sub(r"\s+", "", value)) < 3:
        return False
    if _BIZ_RE.search(_canonical_digits(value)) or _PHONE_RE.search(value):
        return False
    if _TABLE_SUMMARY_RE.search(value) or _TABLE_HEADER_TOKEN_RE.search(value):
        return False
    if _has_product_hint(value):
        return False
    if re.search(r"인수|확인|서명|주문|담당자|영업|팀지점", value):
        return False
    has_addr_token = bool(_ADDRESS_TOKEN_RE.search(value))
    has_unit = bool(re.search(r"\d+\s*(?:층|호|번지)", value))
    has_building = bool(re.search(r"\([가-힣A-Za-z0-9\s]{2,20}\)", value))
    return has_addr_token or has_unit or has_building


def _extract_address_from_mixed_company_line(text: str) -> str:
    """Extract address portion from a line mixing company name and address.

    Handles patterns like:
      '백제약품(주)영등포지점 : (17811) 경기도 평택시 청북읍 청북로 175 (현곡리)'
    Returns only the address portion, or '' if not safely extractable.
    Note: avoids _clean_value to preserve leading parentheses (postal codes).
    """
    value = (text or "").strip()
    if not value:
        return ""

    def _safe_strip_addr(v: str) -> str:
        v = _PHONE_RE.split(v, maxsplit=1)[0]
        v = re.sub(r"\s+[A-Za-z]\.\s*$", "", v)  # strip trailing "T." "F." etc.
        v = re.sub(r"[\s:；.,]+$", "", v).strip()
        return v

    def _is_valid_addr_fragment(v: str) -> bool:
        compact = re.sub(r"\s+", "", v)
        return (re.match(r"^\(\d{5}\)", v) or _CITY_PREFIX_RE.match(compact)) and len(compact) > 5

    # Strategy 1: after colon separator
    colon_match = re.search(r"[:：]\s*", value)
    if colon_match:
        after_colon = _safe_strip_addr(value[colon_match.end():])
        if _is_valid_addr_fragment(after_colon):
            return after_colon

    # Strategy 2: from postal code pattern
    postal_match = re.search(r"\(\d{5}\)", value)
    if postal_match:
        candidate = _safe_strip_addr(value[postal_match.start():])
        if len(re.sub(r"\s+", "", candidate)) > 5:
            return candidate

    # Strategy 3: from first city/region prefix occurrence (must be after some prefix)
    compact_value = re.sub(r"\s+", "", value)
    city_match = _CITY_PREFIX_RE.search(compact_value)
    if city_match and city_match.start() > 0:
        city_token = city_match.group(0)
        pos = value.find(city_token[:2])
        if pos > 0:
            candidate = _safe_strip_addr(value[pos:])
            if len(re.sub(r"\s+", "", candidate)) > 5:
                return candidate

    return ""


def _address_from_scope(lines: list[OcrLine]) -> str:
    ordered = sorted(lines, key=lambda item: (item.y, item.x))
    candidates: list[tuple[int, int, str]] = []
    for idx, line in enumerate(ordered):
        candidate = _clean_address_candidate_line(line.text)
        if not candidate:
            continue
        score = len(_ADDRESS_TOKEN_RE.findall(candidate)) * 4 + min(len(candidate), 50)
        if _ADDR_ANCHOR_RE.search(line.text):
            score += 10
        candidates.append((score, idx, candidate))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: (-item[0], item[1]))
    _, idx, first = candidates[0]
    parts = [first]
    for near in ordered[idx + 1 : idx + 3]:
        extra = _clean_address_candidate_line(near.text)
        if extra and extra not in parts:
            parts.append(extra)
    if len(parts) == 1:
        for near in reversed(ordered[max(0, idx - 2) : idx]):
            extra = _clean_address_candidate_line(near.text)
            if extra and extra not in parts:
                parts.insert(0, extra)
                break
    if len(parts) >= 2 and _ADDRESS_HINT_RE.search(parts[1]) and not _ADDRESS_HINT_RE.search(parts[0]):
        parts[0], parts[1] = parts[1], parts[0]
    return _clean_value(" ".join(parts))


def _party_for_biz_value(
    supplier: dict[str, str],
    buyer: dict[str, str],
    value: str,
    fallback_role: str,
) -> tuple[str, dict[str, str]]:
    if supplier.get("bizNumber") == value:
        return "supplier", supplier
    if buyer.get("bizNumber") == value:
        return "buyer", buyer
    return (fallback_role, supplier if fallback_role == "supplier" else buyer)


def _looks_like_customer_company(company: str) -> bool:
    value = company or ""
    return bool(re.search(r"\uc9c0\s*\uc810|\uac70\s*\ub798\s*\ucc98|\ub0a9\s*\ud488\s*\ucc98|\uadc0\s*\ud558|\uc601\s*\uc5c5\s*\uc18c", value))


def _swap_party_payloads(supplier: dict[str, str], buyer: dict[str, str]) -> None:
    for key in ("company", "bizNumber", "representative", "address"):
        supplier[key], buyer[key] = buyer.get(key, ""), supplier.get(key, "")


def _party_norm(value: str) -> str:
    return re.sub(r"[\s:()\[\],._/\-]+", "", value or "").lower()


def _strip_cross_party_address(address: str, other_company: str) -> str:
    if not address or not other_company:
        return address
    if _party_norm(other_company) and _party_norm(other_company) in _party_norm(address):
        return ""
    return address


def _strip_overlapping_party_address(address: str, other_address: str) -> str:
    if not address or not other_address:
        return address
    value = _clean_value(address)
    other = _clean_value(other_address)
    if not value or not other:
        return address
    if value.startswith(other) and len(value) > len(other) + 3:
        rest = _clean_value(value[len(other) :])
        return rest if _is_address_candidate_line(rest) else value
    return address


def _dedupe_cross_party_representative(supplier: dict[str, str], buyer: dict[str, str], debug: dict[str, Any]) -> None:
    supplier_rep = supplier.get("representative", "")
    buyer_rep = buyer.get("representative", "")
    if not supplier_rep or not buyer_rep or _party_norm(supplier_rep) != _party_norm(buyer_rep):
        return
    supplier_customer_like = _looks_like_customer_company(supplier.get("company", ""))
    buyer_customer_like = _looks_like_customer_company(buyer.get("company", ""))
    if buyer_customer_like and not supplier_customer_like:
        buyer["representative"] = ""
        debug.setdefault("duplicateRepresentativeDecision", []).append(
            {
                "candidate": supplier_rep,
                "selectedRole": "supplier",
                "rejectedRole": "buyer",
                "reason": "same_candidate_supplier_block_preferred",
            }
        )
    elif supplier_customer_like and not buyer_customer_like:
        supplier["representative"] = ""
        debug.setdefault("duplicateRepresentativeDecision", []).append(
            {
                "candidate": buyer_rep,
                "selectedRole": "buyer",
                "rejectedRole": "supplier",
                "reason": "same_candidate_buyer_block_preferred",
            }
        )


def _remove_cross_party_address_fragments(supplier: dict[str, str], buyer: dict[str, str], debug: dict[str, Any]) -> None:
    supplier_address = supplier.get("address", "")
    buyer_address = buyer.get("address", "")
    cleaned_supplier = _strip_cross_party_address(supplier_address, buyer.get("company", ""))
    cleaned_buyer = _strip_cross_party_address(buyer_address, supplier.get("company", ""))
    cleaned_supplier = _strip_overlapping_party_address(cleaned_supplier, cleaned_buyer)
    cleaned_buyer = _strip_overlapping_party_address(cleaned_buyer, cleaned_supplier)
    if cleaned_supplier != supplier_address:
        supplier["address"] = cleaned_supplier
        debug.setdefault("addressFragmentDecision", []).append(
            {
                "role": "supplier",
                "fragment": supplier_address,
                "selected": cleaned_supplier,
                "reason": "rejected_cross_party_company_fragment",
            }
        )
    if cleaned_buyer != buyer_address:
        buyer["address"] = cleaned_buyer
        debug.setdefault("addressFragmentDecision", []).append(
            {
                "role": "buyer",
                "fragment": buyer_address,
                "selected": cleaned_buyer,
                "reason": "rejected_cross_party_company_fragment",
            }
        )


def _rebalance_customer_company_hint(supplier: dict[str, str], buyer: dict[str, str], debug: dict[str, Any]) -> None:
    supplier_company = supplier.get("company", "")
    buyer_company = buyer.get("company", "")
    if not supplier_company or not _looks_like_customer_company(supplier_company):
        return
    if buyer_company and _looks_like_customer_company(buyer_company):
        return

    if buyer.get("bizNumber"):
        _swap_party_payloads(supplier, buyer)
        debug["applied"].append("party.swap_customer_hint")
        return

    moved = {
        "company": supplier.get("company", ""),
        "bizNumber": supplier.get("bizNumber", ""),
        "representative": supplier.get("representative", ""),
        "address": supplier.get("address", ""),
    }
    supplier["company"] = buyer_company
    supplier["bizNumber"] = ""
    supplier["representative"] = ""
    supplier["address"] = ""
    buyer.update(moved)
    debug["applied"].append("party.move_customer_hint")


def _ordered_scope(lines: list[OcrLine], start_idx: int, end_idx: int) -> list[OcrLine]:
    ordered = sorted(lines, key=lambda item: (item.y, item.x))
    return ordered[max(0, start_idx) : min(len(ordered), end_idx)]


def _line_indices(lines: list[OcrLine]) -> dict[int, int]:
    return {id(line): idx for idx, line in enumerate(sorted(lines, key=lambda item: (item.y, item.x)))}


def _apply_party_block_refinements(
    supplier: dict[str, str],
    buyer: dict[str, str],
    all_lines: list[OcrLine],
    bizs: list[tuple[float, float, str, OcrLine]],
    page_h: float,
    page_w: float,
) -> dict[str, Any]:
    ordered = sorted(all_lines, key=lambda item: (item.y, item.x))
    index_by_id = _line_indices(all_lines)
    debug: dict[str, Any] = {"mode": "", "applied": []}
    if not bizs:
        return debug
    sorted_bizs = sorted(bizs, key=lambda item: index_by_id.get(id(item[3]), 0))
    biz_indices = [index_by_id.get(id(item[3]), 0) for item in sorted_bizs]

    if len(sorted_bizs) >= 2 and biz_indices[1] - biz_indices[0] <= 6:
        scope_end = min(len(ordered), biz_indices[1] + 26)
        header_scope = ordered[biz_indices[0] : scope_end]
        blob = " ".join(line.text for line in header_scope)
        x_span = max(item[0] for item in sorted_bizs[:2]) - min(item[0] for item in sorted_bizs[:2])
        y_span = max(item[1] for item in sorted_bizs[:2]) - min(item[1] for item in sorted_bizs[:2])
        side_by_side = x_span >= page_w * 0.22 and y_span <= page_h * 0.10
        if side_by_side:
            sorted_bizs = sorted(sorted_bizs[:2], key=lambda item: item[0])
            role_order = ["supplier", "buyer"]
        else:
            role_order = ["buyer", "supplier"] if _BUYER_PARTY_LABEL_RE.search(blob) and not _SUPPLIER_PARTY_LABEL_RE.search(blob) else ["supplier", "buyer"]
        rep_candidates = [(line.cx, _clean_representative_candidate(line.text)) for line in header_scope]
        rep_candidates = [(x, value) for x, value in rep_candidates if value]
        address_candidates = [(line.cx, _clean_address_candidate_line(line.text)) for line in header_scope]
        address_candidates = [(x, value) for x, value in address_candidates if value]
        reps = [value for _, value in rep_candidates]
        addresses = [value for _, value in address_candidates]
        debug.update({"mode": "shared_stacked_block", "roleOrder": role_order, "sideBySide": side_by_side, "reps": reps, "addresses": addresses})
        role_to_party = {"supplier": supplier, "buyer": buyer}
        for role, biz in zip(role_order, sorted_bizs[:2]):
            role_to_party[role]["bizNumber"] = biz[2]
        for pos, role in enumerate(role_order):
            party = role_to_party[role]
            duplicate_rep = party.get("representative", "") and any(
                party.get("representative") == other.get("representative")
                for other_role, other in role_to_party.items()
                if other_role != role
            )
            rep = ""
            addr = ""
            if side_by_side:
                biz_x = sorted_bizs[pos][0]
                if rep_candidates:
                    rep = min(rep_candidates, key=lambda item: abs(item[0] - biz_x))[1]
                if address_candidates:
                    addr = min(address_candidates, key=lambda item: abs(item[0] - biz_x))[1]
            else:
                rep = reps[pos] if pos < len(reps) else ""
                addr = addresses[pos] if pos < len(addresses) else ""
            if rep and (_should_replace_representative(party.get("representative", ""), rep) or duplicate_rep):
                party["representative"] = rep
                debug["applied"].append(f"{role}.representative")
            if addr:
                party["address"] = addr
                debug["applied"].append(f"{role}.address")
        _rebalance_customer_company_hint(supplier, buyer, debug)
        return debug

    for pos, biz in enumerate(sorted_bizs[:2]):
        idx = biz_indices[pos]
        prev_idx = biz_indices[pos - 1] if pos > 0 else -1
        next_idx = biz_indices[pos + 1] if pos + 1 < len(biz_indices) else len(ordered)
        start = max(prev_idx + 1, idx - 12)
        end = min(next_idx, idx + 18)
        scope = ordered[start:end]
        fallback_role = "supplier" if pos == 0 else "buyer"
        role, party = _party_for_biz_value(supplier, buyer, biz[2], fallback_role)
        rep = _representative_from_scope(scope)
        addr = _address_from_scope(scope)
        if _should_replace_representative(party.get("representative", ""), rep):
            party["representative"] = rep
            debug["applied"].append(role + ".representative")
        if addr:
            party["address"] = addr
            debug["applied"].append(role + ".address")
    debug["mode"] = "per_biz_window"
    _rebalance_customer_company_hint(supplier, buyer, debug)
    return debug


def _apply_address_continuation_post(
    supplier: dict[str, str],
    buyer: dict[str, str],
    all_lines: list[OcrLine],
    bizs: list[tuple[float, float, str, OcrLine]],
    page_w: float,
    page_h: float,
) -> dict[str, Any]:
    """Post-extraction: extend partial addresses with continuation fragments.

    Runs after all party assignments and cross-party cleanup.
    Prevents cross-party mixing via x-zone and proximity checks.
    Returns debug dict with addressContinuationDecisions.
    """
    ordered = sorted(all_lines, key=lambda item: (item.y, item.x))

    biz_pos: dict[str, tuple[float, float]] = {}
    for bx, by, bval, _ in bizs:
        if bval == supplier.get("bizNumber") and "supplier" not in biz_pos:
            biz_pos["supplier"] = (bx, by)
        elif bval == buyer.get("bizNumber") and "buyer" not in biz_pos:
            biz_pos["buyer"] = (bx, by)

    debug: dict[str, Any] = {"decisions": []}

    for role in ("supplier", "buyer"):
        party = supplier if role == "supplier" else buyer
        opposite = buyer if role == "supplier" else supplier
        current_addr = party.get("address", "")
        if not current_addr:
            continue

        role_pos = biz_pos.get(role)
        opp_pos = biz_pos.get("buyer" if role == "supplier" else "supplier")
        biz_x = role_pos[0] if role_pos else (page_w * 0.25 if role == "buyer" else page_w * 0.75)
        x_zone = page_w * 0.42
        x_min = biz_x - x_zone
        x_max = biz_x + x_zone
        opp_x = opp_pos[0] if opp_pos else None

        decision: dict[str, Any] = {
            "role": role,
            "beforeAddress": current_addr,
            "accepted": [],
            "rejected": [],
        }

        # Find the OCR source line of current address
        compact_addr = re.sub(r"\s+", "", current_addr)
        addr_prefix = compact_addr[:min(len(compact_addr), 12)]
        addr_source_idx = -1
        for i, line in enumerate(ordered):
            compact_line = re.sub(r"\s+", "", _clean_value(line.text))
            if addr_prefix[:8] and addr_prefix[:8] in compact_line:
                addr_source_idx = i
                break

        if addr_source_idx < 0:
            decision["rejected"].append({"reason": "source_line_not_found", "prefix": addr_prefix[:20]})
            debug["decisions"].append(decision)
            continue

        addr_source_line = ordered[addr_source_idx]

        # --- TAIL continuation: look AFTER source line ---
        for offset in range(1, 5):
            next_idx = addr_source_idx + offset
            if next_idx >= len(ordered):
                break
            nxt = ordered[next_idx]
            nxt_text = _clean_value(nxt.text)

            reject_reason = None
            if nxt.cx < x_min or nxt.cx > x_max:
                reject_reason = "x_zone_mismatch"
            elif opp_x is not None and abs(nxt.cx - opp_x) < abs(nxt.cx - biz_x) - page_w * 0.04:
                reject_reason = "closer_to_opposite"
            elif abs(nxt.cy - addr_source_line.cy) > page_h * 0.10:
                reject_reason = "y_too_far"
            elif opposite.get("bizNumber") and opposite["bizNumber"].replace("-", "") in re.sub(r"\D", "", nxt_text):
                reject_reason = "contains_opposite_biz"
            elif re.sub(r"\s+", "", nxt_text)[:8] in compact_addr:
                reject_reason = "already_in_address"

            if reject_reason:
                decision["rejected"].append({"type": "tail", "offset": offset, "line": nxt_text[:40], "reason": reject_reason})
                if reject_reason in ("closer_to_opposite", "y_too_far", "contains_opposite_biz"):
                    break
                continue

            if _is_address_tail_fragment(nxt_text):
                combined = _clean_value(f"{party['address']} {nxt_text}")
                if len(re.sub(r"\s+", "", combined)) <= 130:
                    party["address"] = combined
                    current_addr = combined
                    compact_addr = re.sub(r"\s+", "", current_addr)
                    decision["accepted"].append({"type": "tail", "offset": offset, "line": nxt_text[:50]})
            else:
                decision["rejected"].append({"type": "tail", "offset": offset, "line": nxt_text[:40], "reason": "not_tail_fragment"})
                if not _is_address_candidate_line(nxt_text):
                    break

        # --- PREFIX continuation: look BEFORE source line (only for prefix_missing) ---
        struct_status = _classify_address_partial_status(current_addr).get("addressSimilarityStatus", "")
        if struct_status == "prefix_missing":
            for offset in range(1, 6):
                prev_idx = addr_source_idx - offset
                if prev_idx < 0:
                    break
                prv = ordered[prev_idx]
                prv_text = _clean_value(prv.text)

                if prv.cx < x_min - page_w * 0.08 or prv.cx > x_max + page_w * 0.08:
                    decision["rejected"].append({"type": "prefix", "offset": -offset, "line": prv_text[:40], "reason": "x_zone_mismatch"})
                    continue
                if _TABLE_SUMMARY_RE.search(prv_text) or _TABLE_HEADER_TOKEN_RE.search(prv_text):
                    decision["rejected"].append({"type": "prefix", "offset": -offset, "line": prv_text[:40], "reason": "table_noise"})
                    continue
                if _BIZ_RE.search(_canonical_digits(prv_text)):
                    decision["rejected"].append({"type": "prefix", "offset": -offset, "line": prv_text[:40], "reason": "biz_line"})
                    continue

                extracted = ""

                # Try as a direct clean address line (handles standalone postal/city prefix lines)
                clean_addr = _clean_address_candidate_line(prv_text)
                if clean_addr:
                    compact_clean = re.sub(r"\s+", "", clean_addr)
                    if (_CITY_PREFIX_RE.match(compact_clean) or re.match(r"^\(\d{5}\)", clean_addr)) and compact_clean[:8] not in compact_addr:
                        extracted = clean_addr

                # Try extracting from company-mixed or phone-mixed lines
                if not extracted and (_COMPANY_HINT_RE.search(prv_text) or _PHONE_RE.search(prv_text)):
                    ext_candidate = _extract_address_from_mixed_company_line(prv_text)
                    if ext_candidate:
                        compact_ext = re.sub(r"\s+", "", ext_candidate)
                        if (_CITY_PREFIX_RE.match(compact_ext) or re.match(r"^\(\d{5}\)", ext_candidate)) and compact_ext[:6] not in compact_addr:
                            extracted = ext_candidate

                if extracted:
                    opp_biz_val = opposite.get("bizNumber", "")
                    if opp_biz_val and opp_biz_val.replace("-", "") in re.sub(r"\D", "", extracted):
                        decision["rejected"].append({"type": "prefix", "offset": -offset, "line": prv_text[:40], "reason": "extracted_has_opposite_biz"})
                        continue
                    compact_ext = re.sub(r"\s+", "", extracted)
                    if compact_ext[:6] not in compact_addr:
                        # Use simple strip to preserve leading ( in postal codes
                        combined = re.sub(r"\s+", " ", f"{extracted} {party['address']}").strip()
                        if len(re.sub(r"\s+", "", combined)) <= 130:
                            party["address"] = combined
                            current_addr = combined
                            compact_addr = re.sub(r"\s+", "", current_addr)
                            decision["accepted"].append({"type": "prefix", "offset": -offset, "line": prv_text[:40], "extracted": extracted[:50]})
                            break
                    else:
                        decision["rejected"].append({"type": "prefix", "offset": -offset, "line": prv_text[:40], "reason": "already_in_address"})
                else:
                    decision["rejected"].append({"type": "prefix", "offset": -offset, "line": prv_text[:40], "reason": "no_prefix_extracted"})

        decision["afterAddress"] = party.get("address", "")
        debug["decisions"].append(decision)

    return debug


def _recover_missing_supplier_fields(
    supplier: dict[str, str],
    buyer: dict[str, str],
    all_lines: list[OcrLine],
    page_w: float,
    page_h: float,
) -> dict[str, Any]:
    """Post-extraction fallback: when supplierCompany is set but bizNumber/
    representative/address are blank, search OCR lines near the supplier company
    anchor to recover the missing fields. Only modifies supplier dict."""
    debug: dict[str, Any] = {
        "enabled": False,
        "supplierCompany": supplier.get("company", ""),
        "anchorLine": None,
        "anchorBbox": None,
        "searchWindow": None,
        "selected": {"supplierBizNumber": "", "supplierRepresentative": "", "supplierAddress": ""},
        "candidates": {"bizNumbers": [], "representatives": [], "addresses": []},
        "rejected": [],
        "finalDecision": "",
    }

    supplier_company = supplier.get("company", "")
    if not supplier_company:
        debug["finalDecision"] = "skip: supplierCompany blank"
        return debug

    missing_fields = [f for f in ("bizNumber", "representative", "address") if not supplier.get(f, "")]
    if not missing_fields:
        debug["finalDecision"] = "skip: all supplier fields already filled"
        return debug

    debug["enabled"] = True

    buyer_biz_digits = (buyer.get("bizNumber") or "").replace("-", "")
    buyer_rep_norm = _party_norm(buyer.get("representative", "") or "")
    buyer_addr = buyer.get("address", "")
    buyer_addr_prefix = re.sub(r"\s+", "", buyer_addr)[:8] if buyer_addr else ""
    buyer_company_compact = re.sub(r"\s+", "", buyer.get("company", "") or "")

    ordered = sorted(all_lines, key=lambda item: (item.y, item.x))
    company_compact = re.sub(r"\s+", "", supplier_company)

    anchor_line: OcrLine | None = None
    anchor_idx = -1
    best_anchor_score = -1
    for idx, line in enumerate(ordered):
        line_compact = re.sub(r"\s+", "", line.text)
        for n in (6, 4, 3):
            if len(company_compact) >= n and company_compact[:n] in line_compact:
                # Score: match_len * 100 + bonus if company fills most of the line (cleaner anchor)
                fill_ratio = min(len(company_compact), len(line_compact)) / max(len(line_compact), 1)
                score = n * 100 + int(fill_ratio * 80)
                if score > best_anchor_score:
                    best_anchor_score = score
                    best_match_len = n
                    anchor_line = line
                    anchor_idx = idx
                break

    if anchor_line is None or best_match_len < 3:
        debug["finalDecision"] = "skip: anchor line not found"
        return debug

    debug["anchorLine"] = anchor_line.text[:60]
    debug["anchorBbox"] = {
        "x": round(anchor_line.x, 1), "y": round(anchor_line.y, 1),
        "cx": round(anchor_line.cx, 1), "cy": round(anchor_line.cy, 1),
    }

    window_start = max(0, anchor_idx - 15)
    window_end = min(len(ordered), anchor_idx + 15)
    window_lines = ordered[window_start:window_end]
    debug["searchWindow"] = {"start": window_start, "end": window_end, "count": len(window_lines)}

    buyer_anchor_x: float | None = None
    if buyer_biz_digits:
        for line in ordered:
            if buyer_biz_digits in re.sub(r"\D", "", _canonical_digits(line.text)):
                buyer_anchor_x = line.cx
                break
    if buyer_anchor_x is None and buyer_company_compact and len(buyer_company_compact) >= 4:
        for line in ordered:
            if buyer_company_compact[:min(6, len(buyer_company_compact))] in re.sub(r"\s+", "", line.text):
                buyer_anchor_x = line.cx
                break

    anchor_cx = anchor_line.cx

    def _is_contaminated(line: OcrLine, text: str) -> tuple[bool, str]:
        t_digits = re.sub(r"\D", "", _canonical_digits(text))
        if buyer_biz_digits and buyer_biz_digits in t_digits:
            return True, "contains_buyer_biz"
        t_compact = re.sub(r"\s+", "", text)
        if buyer_company_compact and len(buyer_company_compact) >= 4 and buyer_company_compact[:min(6, len(buyer_company_compact))] in t_compact:
            return True, "contains_buyer_company"
        if buyer_anchor_x is not None:
            d_sup = abs(line.cx - anchor_cx)
            d_buy = abs(line.cx - buyer_anchor_x)
            if d_buy < d_sup - page_w * 0.10:
                return True, "closer_to_buyer_anchor"
        return False, ""

    safe_window = [line for line in window_lines if not _is_contaminated(line, line.text)[0]]

    # bizNumber recovery
    if "bizNumber" in missing_fields:
        biz_cands: list[tuple[float, str]] = []
        for line in safe_window:
            value = _format_biz(line.text)
            if not value:
                continue
            if buyer_biz_digits and value.replace("-", "") == buyer_biz_digits:
                debug["rejected"].append({"candidate": value, "field": "bizNumber", "reason": "same_as_buyer_biz"})
                continue
            dist = abs(line.cy - anchor_line.cy) / max(page_h, 1)
            biz_cands.append((dist, value))
        debug["candidates"]["bizNumbers"] = [v for _, v in biz_cands[:5]]
        if biz_cands:
            biz_cands.sort(key=lambda item: item[0])
            supplier["bizNumber"] = biz_cands[0][1]
            debug["selected"]["supplierBizNumber"] = biz_cands[0][1]

    # representative recovery
    if "representative" in missing_fields:
        recovered_rep = _representative_from_scope(safe_window)
        if recovered_rep:
            if buyer_rep_norm and _party_norm(recovered_rep) == buyer_rep_norm:
                debug["rejected"].append({"candidate": recovered_rep, "field": "representative", "reason": "same_as_buyer_rep"})
                recovered_rep = ""
        if not recovered_rep:
            # Label-anchored fallback: x-zone contamination을 우회하고 window 전체에서
            # REP_ANCHOR 레이블이 있는 라인을 탐색 (레이블 자체가 strong evidence)
            for win_line in sorted(window_lines, key=lambda l: abs(l.cy - anchor_line.cy)):
                if not _REP_ANCHOR_RE.search(win_line.text):
                    continue
                # 여전히 buyer biz 포함 라인은 reject
                if buyer_biz_digits and buyer_biz_digits in re.sub(r"\D", "", _canonical_digits(win_line.text)):
                    debug["rejected"].append({"candidate": win_line.text[:30], "field": "representative", "reason": "contains_buyer_biz_label_anchored"})
                    continue
                c = _clean_representative_candidate(win_line.text)
                if not c:
                    continue
                if buyer_rep_norm and _party_norm(c) == buyer_rep_norm:
                    debug["rejected"].append({"candidate": c, "field": "representative", "reason": "same_as_buyer_rep_label_anchored"})
                    continue
                recovered_rep = c
                break
        if recovered_rep:
            supplier["representative"] = recovered_rep
            debug["selected"]["supplierRepresentative"] = recovered_rep
        debug["candidates"]["representatives"] = [recovered_rep] if recovered_rep else []

    # address recovery
    if "address" in missing_fields:
        safe_window_addr = [
            line for line in safe_window
            if not (buyer_addr_prefix and re.sub(r"\s+", "", line.text)[:len(buyer_addr_prefix)] == buyer_addr_prefix)
        ]
        recovered_addr = _address_from_scope(safe_window_addr)
        if recovered_addr:
            recovered_prefix = re.sub(r"\s+", "", recovered_addr)[:8]
            if buyer_addr_prefix and recovered_prefix == buyer_addr_prefix:
                debug["rejected"].append({"candidate": recovered_addr[:40], "field": "address", "reason": "same_prefix_as_buyer_address"})
                recovered_addr = ""
        if recovered_addr:
            supplier["address"] = recovered_addr
            debug["selected"]["supplierAddress"] = recovered_addr
        debug["candidates"]["addresses"] = [recovered_addr[:50]] if recovered_addr else []

    now_filled = [f for f in missing_fields if supplier.get(f, "")]
    debug["finalDecision"] = f"recovered {len(now_filled)}/{len(missing_fields)}: {now_filled}"
    return debug


def _extract_party_fields(
    header_lines: list[OcrLine],
    all_lines: list[OcrLine],
    page_w: float,
    page_h: float,
    header_limit_y: float,
) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    split_x = page_w * 0.5
    candidate_limit_y = max(header_limit_y, page_h * 0.90)
    companies = _company_candidates(all_lines, page_h, candidate_limit_y)
    bizs = _biz_candidates(all_lines, candidate_limit_y)
    supplier = {"company": "", "bizNumber": "", "representative": "", "address": ""}
    buyer = {"company": "", "bizNumber": "", "representative": "", "address": ""}
    used_companies: set[str] = set()

    if len(bizs) >= 2:
        biz_span_x = max(item[0] for item in bizs) - min(item[0] for item in bizs)
        stacked_blocks = biz_span_x <= page_w * 0.18
        if stacked_blocks:
            supplier_biz, buyer_biz = sorted(bizs, key=lambda item: item[1])[:2]
            buyer["bizNumber"] = buyer_biz[2]
            supplier["bizNumber"] = supplier_biz[2]
            buyer["company"] = _nearest_company(buyer_biz, companies, used_companies, page_w, page_h, None, None)
            if not buyer["company"]:
                buyer["company"] = _local_company_near_biz(all_lines, buyer_biz, used_companies, page_w, page_h)
            if buyer["company"]:
                used_companies.add(re.sub(r"\s+", "", buyer["company"]))
            supplier["company"] = _nearest_company(supplier_biz, companies, used_companies, page_w, page_h, None, None)
            if not supplier["company"]:
                supplier["company"] = _local_company_near_biz(all_lines, supplier_biz, used_companies, page_w, page_h)
            if supplier["company"]:
                used_companies.add(re.sub(r"\s+", "", supplier["company"]))
            buyer["representative"] = _rep_near(all_lines, buyer_biz[0], buyer_biz[1], page_w, page_h)
            supplier["representative"] = _rep_near(all_lines, supplier_biz[0], supplier_biz[1], page_w, page_h)
            buyer["address"] = _address_near(all_lines, buyer_biz[0], buyer_biz[1], page_w, page_h)
            supplier["address"] = _address_near(all_lines, supplier_biz[0], supplier_biz[1], page_w, page_h)
        else:
            left_biz, right_biz = sorted(bizs, key=lambda item: item[0])[:2]
            left_company = _nearest_company(left_biz, companies, used_companies, page_w, page_h, "left", split_x)
            right_company = _nearest_company(right_biz, companies, used_companies, page_w, page_h, "right", split_x)
            left_is_customer = _looks_like_customer_company(left_company)
            right_is_customer = _looks_like_customer_company(right_company)
            if left_is_customer and not right_is_customer:
                supplier_biz, buyer_biz = right_biz, left_biz
                supplier_side, buyer_side = "right", "left"
                supplier_company, buyer_company = right_company, left_company
            else:
                supplier_biz, buyer_biz = left_biz, right_biz
                supplier_side, buyer_side = "left", "right"
                supplier_company, buyer_company = left_company, right_company
            supplier["bizNumber"] = supplier_biz[2]
            buyer["bizNumber"] = buyer_biz[2]
            supplier["company"] = supplier_company
            if supplier["company"]:
                used_companies.add(re.sub(r"\s+", "", supplier["company"]))
            buyer["company"] = buyer_company
            if buyer["company"]:
                used_companies.add(re.sub(r"\s+", "", buyer["company"]))
            supplier_scope = [line for line in header_lines if (line.cx <= split_x if supplier_side == "left" else line.cx > split_x)]
            buyer_scope = [line for line in header_lines if (line.cx <= split_x if buyer_side == "left" else line.cx > split_x)]
            supplier["representative"] = _rep_near(supplier_scope, supplier_biz[0], supplier_biz[1], page_w, page_h)
            buyer["representative"] = _rep_near(buyer_scope, buyer_biz[0], buyer_biz[1], page_w, page_h)
            supplier["address"] = _address_near(supplier_scope, supplier_biz[0], supplier_biz[1], page_w, page_h)
            buyer["address"] = _address_near(buyer_scope, buyer_biz[0], buyer_biz[1], page_w, page_h)
    elif len(bizs) == 1:
        bx, by, value, _ = bizs[0]
        target = supplier if bx <= split_x else buyer
        side = "left" if bx <= split_x else "right"
        target["bizNumber"] = value
        target["company"] = _nearest_company(bizs[0], companies, used_companies, page_w, page_h, side, split_x)
        if not target["company"]:
            target["company"] = _local_company_near_biz(all_lines, bizs[0], used_companies, page_w, page_h)
        if target["company"]:
            used_companies.add(re.sub(r"\s+", "", target["company"]))
        target["representative"] = _rep_near(header_lines, bx, by, page_w, page_h)
        target["address"] = _address_near(header_lines, bx, by, page_w, page_h)

    _assign_unique_fallbacks(supplier, buyer, companies, split_x, used_companies)

    pre_refine_debug: dict[str, Any] = {"applied": []}
    if (
        supplier.get("bizNumber")
        and not supplier.get("company")
        and buyer.get("company")
        and _looks_like_customer_company(buyer.get("company", ""))
        and not buyer.get("bizNumber")
    ):
        buyer["bizNumber"] = supplier.get("bizNumber", "")
        buyer["representative"] = supplier.get("representative", "")
        buyer["address"] = supplier.get("address", "")
        supplier["bizNumber"] = ""
        supplier["representative"] = ""
        supplier["address"] = ""
        pre_refine_debug["applied"].append("single_biz.move_to_customer_company")

    if not supplier["representative"] and not supplier.get("bizNumber"):
        supplier["representative"] = _value_after_anchor([l for l in header_lines if l.cx <= split_x], _REP_ANCHOR_RE, "representative")
    if not buyer["representative"] and not buyer.get("bizNumber"):
        buyer["representative"] = _value_after_anchor([l for l in header_lines if l.cx > split_x], _REP_ANCHOR_RE, "representative")
    if not supplier["address"]:
        supplier["address"] = _value_after_anchor([l for l in header_lines if l.cx <= split_x], _ADDR_ANCHOR_RE, "address")
    if not buyer["address"]:
        buyer["address"] = _value_after_anchor([l for l in header_lines if l.cx > split_x], _ADDR_ANCHOR_RE, "address")

    block_debug = _apply_party_block_refinements(supplier, buyer, all_lines, bizs, page_h, page_w)
    if pre_refine_debug["applied"]:
        block_debug.setdefault("preRefine", pre_refine_debug)
    _dedupe_cross_party_representative(supplier, buyer, block_debug)
    _remove_cross_party_address_fragments(supplier, buyer, block_debug)
    continuation_debug = _apply_address_continuation_post(supplier, buyer, all_lines, bizs, page_w, page_h)
    supplier_recovery_debug = _recover_missing_supplier_fields(supplier, buyer, all_lines, page_w, page_h)

    return supplier, buyer, {
        "companies": companies,
        "bizs": [(round(x), round(y), value) for x, y, value, _ in bizs],
        "split_x": split_x,
        "block_refinement": block_debug,
        "addressContinuation": continuation_debug,
        "supplierCompanyAnchorFallback": supplier_recovery_debug,
    }


def _extract_amount_near(lines: list[OcrLine], anchor_re: re.Pattern) -> str:
    ordered = sorted(lines, key=lambda line: (line.y, line.x))
    for idx, line in enumerate(ordered):
        if not anchor_re.search(line.text):
            continue
        value = _amount_value(line.text)
        if value:
            return value
        row_text = " ".join(peer.text for peer in _same_row_candidates(ordered, line))
        value = _amount_value(row_text)
        if value:
            return value
        for prev in reversed(ordered[max(0, idx - 4) : idx]):
            if _BIZ_RE.search(_canonical_digits(prev.text)) or _PHONE_RE.search(prev.text):
                continue
            value = _amount_value(prev.text)
            if value:
                return value
        for nxt in ordered[idx + 1 : idx + 9]:
            if _BIZ_RE.search(_canonical_digits(nxt.text)) or _PHONE_RE.search(nxt.text):
                continue
            value = _amount_value(nxt.text)
            if value:
                return value
    return ""


def _large_amount_value(text: str, min_value: int = 10_000) -> str:
    values = [
        value
        for value in _amount_values(text)
        if int(value.replace(",", "")) >= min_value
    ]
    return values[-1] if values else ""


def _extract_amount_near_reading_order(lines: list[OcrLine], anchor_re: re.Pattern) -> str:
    for idx, line in enumerate(lines):
        if not anchor_re.search(line.text):
            continue
        window = list(reversed(lines[max(0, idx - 6) : idx])) + lines[idx : idx + 12]
        for item in window:
            if _BIZ_RE.search(_canonical_digits(item.text)) or _PHONE_RE.search(item.text):
                continue
            value = _large_amount_value(item.text)
            if value:
                return value
    return ""


def _row_center_y(row: list[OcrLine]) -> float:
    return sum(item.cy for item in row) / len(row)


def _row_has_item_context(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    return bool(
        _is_item_name_like(text)
        or _is_code_only_table_row(text)
        or re.search(r"\ud488\s*\uba85|\ud488\s*\ubaa9|\ud488\s*\ucf54\ub4dc|\uc218\s*\ub7c9|\ub2e8\s*\uac00", text)
        or re.search(r"[A-Z]{2,}[A-Z0-9]{2,}\s+\d", compact)
    )


def _row_has_non_summary_noise(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    return bool(
        _ADDRESS_HINT_RE.search(text)
        or _BIZ_RE.search(_canonical_digits(text))
        or _PHONE_RE.search(text)
        or _DATE_RE.search(text)
        or re.search(r"\uc0ac\uc5c5\uc790|\ub4f1\ub85d\ubc88\ud638|\uc804\s*\ud654|FAX|TEL|\uacc4\uc88c|\uc740\ud589|Page|\ud398\uc774\uc9c0", text, re.I)
        or re.fullmatch(r"(?:\d{1,3}[-./]){2,}\d{1,5}", compact)
    )


def _summary_anchor_flags(text: str) -> tuple[bool, bool, bool]:
    return (
        bool(_SUPPLY_AMOUNT_ANCHOR_RE.search(text)),
        bool(_TAX_AMOUNT_ANCHOR_RE.search(text)),
        bool(_TOTAL_AMOUNT_ANCHOR_RE.search(text) or re.search(r"\ud568\s*\uacc4", text)),
    )


def _nearby_summary_context(rows: list[list[OcrLine]], idx: int, page_h: float) -> str:
    base_y = _row_center_y(rows[idx])
    parts: list[str] = []
    for near_idx in range(max(0, idx - 1), min(len(rows), idx + 2)):
        near_y = _row_center_y(rows[near_idx])
        if abs(near_y - base_y) <= page_h * 0.045:
            parts.append(_row_text(rows[near_idx]))
    return " ".join(parts)


def _footer_summary_candidates(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
) -> tuple[list[SummaryAmountCandidate], float]:
    rows = _group_rows(lines)
    footer_start = max(page_h * 0.68, (table_header_y or 0) + page_h * 0.18)
    if not rows:
        return [], footer_start

    candidates: list[SummaryAmountCandidate] = []
    for idx, row in enumerate(rows):
        text = _row_text(row)
        cy = _row_center_y(row)
        if cy < footer_start or cy > page_h * 0.94:
            continue
        if _row_has_non_summary_noise(text):
            continue
        context = _nearby_summary_context(rows, idx, page_h)
        has_summary_anchor = bool(_TABLE_SUMMARY_RE.search(context) or _TOTAL_AMOUNT_ANCHOR_RE.search(context))
        if _row_has_item_context(text) and not has_summary_anchor:
            continue
        supply_anchor, tax_anchor, total_anchor = _summary_anchor_flags(context)
        if not (has_summary_anchor or supply_anchor or tax_anchor or total_anchor):
            continue
        for line in row:
            if _row_has_non_summary_noise(line.text):
                continue
            for value in _amount_values(line.text):
                numeric = int(value.replace(",", ""))
                if numeric < 10_000:
                    continue
                candidates.append(
                    SummaryAmountCandidate(
                        value=value,
                        numeric=numeric,
                        row_idx=idx,
                        cy=cy,
                        x=line.x,
                        text=line.text,
                        context=context,
                        supply_anchor=supply_anchor,
                        tax_anchor=tax_anchor,
                        total_anchor=total_anchor,
                    )
                )
        if not any(item.row_idx == idx for item in candidates):
            for value in _amount_values(text):
                numeric = int(value.replace(",", ""))
                if numeric >= 10_000:
                    candidates.append(
                        SummaryAmountCandidate(
                            value=value,
                            numeric=numeric,
                            row_idx=idx,
                            cy=cy,
                            x=min(item.x for item in row),
                            text=text,
                            context=context,
                            supply_anchor=supply_anchor,
                            tax_anchor=tax_anchor,
                            total_anchor=total_anchor,
                        )
                    )
    return candidates, footer_start


def _summary_candidate_base_score(candidate: SummaryAmountCandidate, footer_start: float, page_h: float, role: str) -> float:
    score = 0.0
    if footer_start <= candidate.cy <= page_h * 0.94:
        score += 8
        score += min(max((candidate.cy - footer_start) / max(page_h * 0.24, 1), 0), 1) * 4
    if _TABLE_SUMMARY_RE.search(candidate.context):
        score += 6
    if role == "supply" and candidate.supply_anchor:
        score += 13
    if role == "tax" and candidate.tax_anchor:
        score += 13
    if role == "total" and candidate.total_anchor:
        score += 13
    if _row_has_item_context(candidate.text) and not _TABLE_SUMMARY_RE.search(candidate.context):
        score -= 18
    if _row_has_non_summary_noise(candidate.context):
        score -= 24
    if candidate.cy < page_h * 0.55:
        score -= 20
    return score


def _amounts_close(left: int, right: int) -> bool:
    tolerance = max(2_500, int(max(left, right) * 0.001))
    return abs(left - right) <= tolerance


def _summary_amount_pool(lines: list[OcrLine], min_value: int = 10_000) -> list[tuple[int, str, int, float, str]]:
    rows = _group_rows(lines)
    pool: list[tuple[int, str, int, float, str]] = []
    seen: set[tuple[int, int]] = set()
    for idx, row in enumerate(rows):
        text = _row_text(row)
        if _row_has_non_summary_noise(text):
            continue
        context_parts = [
            _row_text(rows[near_idx])
            for near_idx in range(max(0, idx - 4), min(len(rows), idx + 5))
        ]
        context = " ".join(context_parts)
        cy = _row_center_y(row)
        for value in _amount_values(text):
            numeric = int(value.replace(",", ""))
            if numeric < min_value:
                continue
            key = (idx, numeric)
            if key in seen:
                continue
            seen.add(key)
            pool.append((numeric, value, idx, cy, context))
    return pool


def _summary_role_flags_for_labels(text: str) -> tuple[bool, bool, bool, bool]:
    return (
        bool(_SUMMARY_SUPPLY_LABEL_RE.search(text)),
        bool(_SUMMARY_WEAK_SUPPLY_LABEL_RE.search(text)),
        bool(_SUMMARY_TAX_LABEL_RE.search(text)),
        bool(_SUMMARY_TOTAL_LABEL_RE.search(text)),
    )


def _summary_label_window_amounts(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
    existing_total: str = "",
) -> tuple[dict[str, str], dict[str, Any]]:
    rows = _group_rows(lines)
    debug: dict[str, Any] = {"source": "", "candidateCount": 0}
    if not rows:
        return {}, debug

    total_num = int(existing_total.replace(",", "")) if existing_total else 0
    footer_start = max(page_h * 0.58, (table_header_y or 0) + page_h * 0.08)
    scored: dict[str, list[tuple[float, str, int, str, str, int, int, dict[str, Any]]]] = {
        "supplyAmount": [],
        "taxAmount": [],
        "totalAmount": [],
    }

    def add_scored_candidate(
        role: str,
        score: float,
        value: str,
        numeric: int,
        label_text: str,
        amount_text: str,
        label_idx: int,
        amount_idx: int,
        meta: dict[str, Any] | None = None,
    ) -> None:
        scored[role].append((score, value, numeric, label_text, amount_text, label_idx, amount_idx, meta or {}))

    for label_idx, row in enumerate(rows):
        label_text = _row_text(row)
        label_context = " ".join(
            _row_text(rows[near_idx])
            for near_idx in range(max(0, label_idx - 1), min(len(rows), label_idx + 2))
        )
        supply_label, weak_supply_label, tax_label, total_label = _summary_role_flags_for_labels(label_context)
        if not (supply_label or weak_supply_label or tax_label or total_label):
            continue
        if _row_has_non_summary_noise(label_text) and not _TABLE_SUMMARY_RE.search(label_context):
            continue

        roles: list[tuple[str, bool]] = []
        if supply_label:
            roles.append(("supplyAmount", False))
        elif weak_supply_label:
            roles.append(("supplyAmount", True))
        if tax_label:
            roles.append(("taxAmount", False))
        if total_label:
            roles.append(("totalAmount", False))

        for near_idx in range(max(0, label_idx - 18), min(len(rows), label_idx + 19)):
            near_text = _row_text(rows[near_idx])
            near_cy = _row_center_y(rows[near_idx])
            if _row_has_non_summary_noise(near_text) and not _TABLE_SUMMARY_RE.search(f"{label_context} {near_text}"):
                continue
            values = _amount_values(near_text)
            if not values:
                continue
            distance = abs(near_idx - label_idx)
            same_row = near_idx == label_idx
            candidate_context = f"{label_context} {near_text}"
            for value in values:
                numeric = int(value.replace(",", ""))
                if numeric < 10_000:
                    continue
                for role, is_weak_supply in roles:
                    if role == "supplyAmount":
                        if total_num and numeric >= total_num * 0.98:
                            continue
                        if total_num and numeric > total_num * 1.2:
                            continue
                    elif role == "taxAmount":
                        if total_num and numeric >= total_num * 0.35:
                            continue
                    elif role == "totalAmount":
                        if total_num and not _amounts_close(numeric, total_num) and numeric < total_num * 0.2:
                            continue

                    score = 38.0
                    if same_row:
                        score += 12
                    elif distance <= 2:
                        score += 10
                    elif distance <= 6:
                        score += 5
                    elif distance <= 14:
                        score += 1
                    else:
                        score -= 5
                    if near_cy >= page_h * 0.58:
                        score += 10
                    elif near_cy >= page_h * 0.38:
                        score += 3
                    else:
                        score -= 6
                    if table_header_y is not None and near_cy >= table_header_y + page_h * 0.08:
                        score += 5
                    if _TABLE_SUMMARY_RE.search(candidate_context):
                        score += 10
                    if role == "supplyAmount" and _SUMMARY_SUPPLY_LABEL_RE.search(label_context):
                        score += 10
                    if role == "taxAmount" and _SUMMARY_TAX_LABEL_RE.search(label_context):
                        score += 10
                    if role == "totalAmount" and _SUMMARY_TOTAL_LABEL_RE.search(label_context):
                        score += 10
                    if is_weak_supply:
                        score -= 14
                    if _row_has_item_context(near_text) and not _TABLE_SUMMARY_RE.search(candidate_context):
                        score -= 18
                    if _row_has_non_summary_noise(candidate_context):
                        score -= 16
                    if role == "taxAmount" and total_num and 0.06 <= numeric / max(total_num, 1) <= 0.13:
                        score += 7
                    if role == "totalAmount" and total_num and _amounts_close(numeric, total_num):
                        score += 18
                    dense_amount_row = len(values) >= 6
                    if dense_amount_row:
                        score -= 14
                    add_scored_candidate(
                        role,
                        score,
                        value,
                        numeric,
                        label_text,
                        near_text,
                        label_idx,
                        near_idx,
                        {
                            "path": "visual_row",
                            "visualRowDistance": distance,
                            "ocrOrderDistance": None,
                            "footerRegion": near_cy >= footer_start,
                            "sameVisualRow": same_row,
                            "denseAmountRow": dense_amount_row,
                            "tableBodyLike": bool(_row_has_item_context(near_text) and not _TABLE_SUMMARY_RE.search(candidate_context)),
                        },
                    )

    for label_idx, line in enumerate(lines):
        label_context = " ".join(item.text for item in lines[max(0, label_idx - 1) : min(len(lines), label_idx + 2)])
        supply_label, weak_supply_label, tax_label, total_label = _summary_role_flags_for_labels(label_context)
        if not (supply_label or weak_supply_label or tax_label or total_label):
            continue
        roles = []
        if supply_label:
            roles.append(("supplyAmount", False))
        elif weak_supply_label:
            roles.append(("supplyAmount", True))
        if tax_label:
            roles.append(("taxAmount", False))
        if total_label:
            roles.append(("totalAmount", False))
        for near_idx in range(max(0, label_idx - 22), min(len(lines), label_idx + 23)):
            amount_line = lines[near_idx]
            amount_text = amount_line.text
            if _BIZ_RE.search(_canonical_digits(amount_text)) or _PHONE_RE.search(amount_text):
                continue
            if _DATE_RE.search(amount_text) and not _TABLE_SUMMARY_RE.search(label_context):
                continue
            values = _amount_values(amount_text)
            if not values:
                continue
            distance = abs(near_idx - label_idx)
            for value in values:
                numeric = int(value.replace(",", ""))
                if numeric < 10_000:
                    continue
                for role, is_weak_supply in roles:
                    if role == "supplyAmount":
                        if total_num and (numeric >= total_num * 0.98 or numeric > total_num * 1.2):
                            continue
                    elif role == "taxAmount" and total_num and numeric >= total_num * 0.35:
                        continue
                    elif role == "totalAmount" and total_num and not _amounts_close(numeric, total_num) and numeric < total_num * 0.2:
                        continue
                    score = 48.0
                    if distance == 0:
                        score += 13
                    elif distance <= 4:
                        score += 11
                    elif distance <= 10:
                        score += 6
                    elif distance <= 16:
                        score += 3
                    else:
                        score -= 4
                    if amount_line.cy >= page_h * 0.58:
                        score += 8
                    elif amount_line.cy >= page_h * 0.35:
                        score += 3
                    if role == "supplyAmount" and _SUMMARY_SUPPLY_LABEL_RE.search(label_context):
                        score += 14
                    if role == "taxAmount" and _SUMMARY_TAX_LABEL_RE.search(label_context):
                        score += 14
                    if role == "totalAmount" and _SUMMARY_TOTAL_LABEL_RE.search(label_context):
                        score += 14
                    if is_weak_supply:
                        score -= 18
                    if _row_has_item_context(amount_text) and not _TABLE_SUMMARY_RE.search(label_context):
                        score -= 10
                    if role == "taxAmount" and total_num and 0.06 <= numeric / max(total_num, 1) <= 0.13:
                        score += 7
                    if role == "totalAmount" and total_num and _amounts_close(numeric, total_num):
                        score += 18
                    add_scored_candidate(
                        role,
                        score,
                        value,
                        numeric,
                        line.text,
                        amount_text,
                        label_idx,
                        near_idx,
                        {
                            "path": "ocr_order",
                            "visualRowDistance": round(abs(amount_line.cy - line.cy), 2),
                            "ocrOrderDistance": distance,
                            "footerRegion": amount_line.cy >= footer_start,
                            "sameVisualRow": abs(amount_line.cy - line.cy) <= max(line.h, amount_line.h) * 1.4,
                            "denseAmountRow": len(values) >= 6,
                            "tableBodyLike": bool(_row_has_item_context(amount_text) and not _TABLE_SUMMARY_RE.search(label_context)),
                        },
                    )

    for role_items in scored.values():
        role_items.sort(key=lambda item: (-item[0], abs(item[6] - item[5]), -item[2]))
    debug["candidateCount"] = sum(len(items) for items in scored.values())
    best_supply = scored["supplyAmount"][0] if scored["supplyAmount"] else None
    best_tax = scored["taxAmount"][0] if scored["taxAmount"] else None
    best_total = scored["totalAmount"][0] if scored["totalAmount"] else None

    checksum_ok = False
    if best_supply and best_tax and total_num:
        checksum_ok = _amounts_close(best_supply[2] + best_tax[2], total_num)
    if checksum_ok:
        scored["supplyAmount"][0] = (best_supply[0] + 22, *best_supply[1:])
        scored["taxAmount"][0] = (best_tax[0] + 22, *best_tax[1:])
        best_supply = scored["supplyAmount"][0]
        best_tax = scored["taxAmount"][0]

    result: dict[str, str] = {}
    if best_supply and (checksum_ok or (not total_num and best_supply[0] >= 76 and abs(best_supply[6] - best_supply[5]) <= 3)):
        result["supplyAmount"] = best_supply[1]
    if best_tax and (checksum_ok or (not total_num and best_tax[0] >= 74 and abs(best_tax[6] - best_tax[5]) <= 3)):
        result["taxAmount"] = best_tax[1]
    if best_total and best_total[0] >= 58:
        result["totalAmount"] = best_total[1]

    if result:
        debug["source"] = "summary_label_window"
    if best_supply:
        supply_meta = best_supply[7]
        rejected_reasons: list[str] = []
        selected = result.get("supplyAmount") == best_supply[1]
        if total_num and not checksum_ok:
            rejected_reasons.append("rejected_no_checksum")
        if not scored["taxAmount"]:
            rejected_reasons.append("rejected_no_tax_candidate")
        if supply_meta.get("denseAmountRow"):
            rejected_reasons.append("rejected_dense_mixed_amount_row")
        if supply_meta.get("tableBodyLike"):
            rejected_reasons.append("rejected_table_body_amount")
        if total_num and not supply_meta.get("footerRegion"):
            rejected_reasons.append("rejected_not_footer_region")
        debug["singleSupplyDecision"] = {
            "candidate": best_supply[1],
            "score": round(best_supply[0], 2),
            "selected": selected,
            "reason": "label_window_checksum" if selected and checksum_ok else ("label_position_single_supply" if selected else ",".join(rejected_reasons or ["rejected_weak_single_supply"])),
            "meta": supply_meta,
            "competingSupplyCandidates": [
                {
                    "value": item[1],
                    "score": round(item[0], 2),
                    "path": item[7].get("path", ""),
                    "reason": "candidate_ranked_lower",
                }
                for item in scored["supplyAmount"][1:6]
            ],
        }
    debug["best"] = {
        role: (
            {
                "score": round(items[0][0], 2),
                "value": items[0][1],
                "label": items[0][3],
                "amountText": items[0][4],
                "rowDistance": abs(items[0][6] - items[0][5]),
                "meta": items[0][7],
            }
            if items
            else None
        )
        for role, items in scored.items()
    }
    debug["checksumOk"] = checksum_ok
    return result, debug


def _quantity_values(text: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r"(?<![\dA-Za-z])(\d{1,3}(?:[,.]\d{3})+|\d{1,6})(?![\dA-Za-z])", _canonical_digits(text or "")):
        raw = match.group(1)
        digits = re.sub(r"\D", "", raw)
        if not digits:
            continue
        numeric = int(digits)
        if 1 <= numeric <= 10_000_000:
            values.append(f"{numeric:,}")
    return values


def _summary_field_values_for_text(field_key: str, text: str) -> list[str]:
    if field_key == "totalQuantity":
        return _quantity_values(text)
    return [
        value
        for value in _amount_values(text)
        if int(value.replace(",", "")) >= 100
    ]


def _summary_field_candidate_reject_reason(field_key: str, text: str, has_exact_label: bool) -> str:
    compact = re.sub(r"\s+", "", text or "")
    if field_key in _PROFILE_SUMMARY_AMOUNT_FIELDS and len(_amount_values(text)) > 5:
        return "dense_mixed_amount_row"
    if _BIZ_RE.search(_canonical_digits(text)) or _PHONE_RE.search(text):
        return "business_or_phone_context"
    if _CODE_LOT_SERIAL_RE.search(text):
        return "code_lot_serial_context"
    if field_key == "totalQuantity":
        if not has_exact_label and re.search(r"\d{5,}|[A-Z]{2,}\d+|\d+\s*(?:T|C|mg|ml|g|ea|BOX)", text, re.I):
            return "quantity_without_total_quantity_label"
        if re.search(r"\d{5,}\s*[-/]\s*\d{5,}", compact):
            return "hyphen_serial_context"
        return ""
    if _DATE_RE.search(text) and not has_exact_label:
        return "date_context_without_exact_label"
    if _row_has_item_context(text) and not has_exact_label:
        return "table_body_without_exact_label"
    return ""


def _extract_profile_summary_fields(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
) -> tuple[dict[str, str], dict[str, Any]]:
    rows = _group_rows(lines)
    debug: dict[str, Any] = {
        "source": "summary_field_label_window",
        "enabled": True,
        "fields": {},
        "candidates": [],
        "rejected": [],
    }
    if not rows:
        return {}, debug

    scored: dict[str, list[tuple[float, str, str, str, int, int, dict[str, Any]]]] = {
        key: [] for key in _SUMMARY_FIELD_KEYS
    }

    def add_candidate(
        field_key: str,
        value: str,
        label: str,
        label_text: str,
        amount_text: str,
        label_idx: int,
        amount_idx: int,
        path: str,
        same_row: bool,
        source_line: OcrLine | None,
    ) -> None:
        has_exact_label = bool(_PROFILE_SUMMARY_FIELD_LABELS[field_key].search(amount_text))
        reject_reason = _summary_field_candidate_reject_reason(field_key, amount_text, has_exact_label or same_row)
        if field_key == "cumulativeAmount" and not re.search(r"\uc18c\s*\uacc4", f"{label_text} {amount_text}"):
            reject_reason = "cumulative_amount_without_subtotal_context"
        if (
            field_key in _PROFILE_SUMMARY_AMOUNT_FIELDS
            and path == "ocr_order"
            and not has_exact_label
        ):
            reject_reason = "amount_line_without_summary_field_label"
        meta = {
            "path": path,
            "sameVisualRow": same_row,
            "rowDistance": abs(amount_idx - label_idx),
            "sourceLineIndex": amount_idx,
            "bbox": (
                [round(source_line.x), round(source_line.y), round(source_line.w), round(source_line.h)]
                if source_line is not None
                else None
            ),
        }
        record = {
            "fieldKey": field_key,
            "label": label,
            "value": value,
            "sourceText": amount_text,
            "sourceLineIndex": amount_idx,
            "reason": "label_window",
            "meta": meta,
        }
        if reject_reason:
            debug["rejected"].append({**record, "reason": reject_reason})
            return
        numeric = int(value.replace(",", ""))
        if field_key in _PROFILE_SUMMARY_AMOUNT_FIELDS and numeric < 1_000:
            debug["rejected"].append({**record, "reason": "amount_too_small"})
            return
        score = 60.0
        distance = abs(amount_idx - label_idx)
        if same_row:
            score += 22
        elif distance <= 1:
            score += 16
        elif distance <= 3:
            score += 10
        elif distance <= 6:
            score += 4
        else:
            score -= 10
        if "," in value:
            score += 5
        if _PROFILE_SUMMARY_FIELD_LABELS[field_key].search(amount_text):
            score += 12
        if table_header_y is not None and source_line is not None and source_line.cy >= table_header_y:
            score -= 8
        if source_line is not None and source_line.cy >= page_h * 0.88:
            score -= 3
        debug["candidates"].append({**record, "score": round(score, 2)})
        scored[field_key].append((score, value, label, amount_text, label_idx, amount_idx, meta))

    for label_idx, row in enumerate(rows):
        row_text = _row_text(row)
        label_context = " ".join(
            _row_text(rows[near_idx])
            for near_idx in range(max(0, label_idx - 1), min(len(rows), label_idx + 2))
        )
        for field_key, label_re in _PROFILE_SUMMARY_FIELD_LABELS.items():
            label_match = label_re.search(label_context)
            if not label_match:
                continue
            label = label_match.group(0)
            for near_idx in range(max(0, label_idx - 3), min(len(rows), label_idx + 4)):
                near_row = rows[near_idx]
                near_text = _row_text(near_row)
                values = _summary_field_values_for_text(field_key, near_text)
                for value in values:
                    source_line = next((line for line in near_row if value.replace(",", "") in re.sub(r"\D", "", line.text)), None)
                    add_candidate(
                        field_key,
                        value,
                        label,
                        row_text,
                        near_text,
                        label_idx,
                        near_idx,
                        "visual_row",
                        near_idx == label_idx,
                        source_line,
                    )

    for label_idx, line in enumerate(lines):
        label_context = " ".join(item.text for item in lines[max(0, label_idx - 1) : min(len(lines), label_idx + 2)])
        for field_key, label_re in _PROFILE_SUMMARY_FIELD_LABELS.items():
            label_match = label_re.search(label_context)
            if not label_match:
                continue
            label = label_match.group(0)
            for near_idx in range(max(0, label_idx - 8), min(len(lines), label_idx + 9)):
                amount_line = lines[near_idx]
                values = _summary_field_values_for_text(field_key, amount_line.text)
                for value in values:
                    add_candidate(
                        field_key,
                        value,
                        label,
                        line.text,
                        amount_line.text,
                        label_idx,
                        near_idx,
                        "ocr_order",
                        abs(amount_line.cy - line.cy) <= max(line.h, amount_line.h) * 1.5,
                        amount_line,
                    )

    result: dict[str, str] = {}
    for field_key, items in scored.items():
        items.sort(key=lambda item: (-item[0], abs(item[5] - item[4]), -int(item[1].replace(",", ""))))
        selected = items[0] if items else None
        if selected and selected[0] >= 55:
            result[field_key] = selected[1]
            debug["fields"][field_key] = {
                "value": selected[1],
                "label": selected[2],
                "sourceText": selected[3],
                "sourceLineIndex": selected[5],
                "confidence": round(selected[0], 2),
                "reason": "label_window",
                "meta": selected[6],
            }
        else:
            debug["fields"][field_key] = None
    debug["selectedFieldKeys"] = [key for key in _SUMMARY_FIELD_KEYS if result.get(key)]
    debug["candidateCount"] = len(debug["candidates"])
    debug["rejectedCount"] = len(debug["rejected"])
    return result, debug


def _summary_total_evidence(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
    total: str,
    supply: str = "",
    tax: str = "",
) -> dict[str, Any]:
    debug: dict[str, Any] = {"value": total or "", "source": "", "score": 0.0, "reason": ""}
    if not total:
        debug["reason"] = "no_total"
        return debug
    total_num = int(total.replace(",", ""))
    checksum_total = False
    if supply and tax:
        supply_num = int(supply.replace(",", ""))
        tax_num = int(tax.replace(",", ""))
        checksum_total = supply_num > tax_num > 0 and _amounts_close(supply_num + tax_num, total_num)
    rows = _group_rows(lines)
    footer_start = max(page_h * 0.58, (table_header_y or 0) + page_h * 0.08)
    occurrences: list[dict[str, Any]] = []
    competing: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        text = _row_text(row)
        cy = _row_center_y(row)
        values = _amount_values(text)
        if not values:
            continue
        context = " ".join(_row_text(rows[near_idx]) for near_idx in range(max(0, idx - 2), min(len(rows), idx + 3)))
        for value in values:
            numeric = int(value.replace(",", ""))
            score = 20.0
            reasons: list[str] = []
            if _amounts_close(numeric, total_num):
                score += 30
                reasons.append("matches_selected_total")
            if _SUMMARY_TOTAL_LABEL_RE.search(context) or _TOTAL_AMOUNT_ANCHOR_RE.search(context):
                score += 22
                reasons.append("total_label_context")
            if _TABLE_SUMMARY_RE.search(context):
                score += 10
                reasons.append("summary_context")
            if cy >= footer_start:
                score += 10
                reasons.append("footer_region")
            elif cy < page_h * 0.35:
                score -= 8
                reasons.append("upper_region")
            if _row_has_item_context(text) and not _TABLE_SUMMARY_RE.search(context):
                score -= 18
                reasons.append("table_body_like")
            if _row_has_non_summary_noise(context):
                score -= 16
                reasons.append("party_or_noise_context")
            item = {
                "value": value,
                "score": round(score, 2),
                "row": idx,
                "cy": round(cy, 2),
                "text": text,
                "reasons": reasons,
            }
            if _amounts_close(numeric, total_num):
                occurrences.append(item)
            else:
                competing.append(item)

    occurrences.sort(key=lambda item: (-item["score"], item["row"]))
    competing.sort(key=lambda item: (-item["score"], -int(str(item["value"]).replace(",", ""))))
    if occurrences:
        best = occurrences[0]
        source = "summary_region_total" if best["score"] >= 62 else "low_confidence_total_existing"
        if checksum_total:
            source = "summary_checksum_total"
            best["score"] = max(float(best["score"]), 78.0)
            best["reasons"] = list(dict.fromkeys(list(best.get("reasons") or []) + ["supply_tax_checksum"]))
        debug.update(
            {
                "source": source,
                "score": best["score"],
                "reason": ",".join(best["reasons"] or ["amount_value_match"]),
                "bestOccurrence": best,
            }
        )
    elif checksum_total:
        debug.update(
            {
                "source": "summary_checksum_total",
                "score": 78.0,
                "reason": "supply_tax_checksum,total_value_not_found_in_summary_rows",
            }
        )
    else:
        debug.update(
            {
                "source": "low_confidence_total_existing",
                "score": 0.0,
                "reason": "selected_total_not_found_in_summary_rows",
            }
        )
    debug["occurrences"] = occurrences[:3]
    debug["competingCandidates"] = competing[:5]
    return debug


def _summary_amount_token_risk(text: str, value: str) -> dict[str, Any]:
    digits = re.sub(r"\D", "", value or "")
    compact = _canonical_digits(text or "")
    token_hits = [
        token
        for token in re.split(r"\s+", compact)
        if digits and digits in re.sub(r"\D", "", token)
    ]
    embedded_code = any(re.search(r"[A-Za-z]", token) and re.search(r"\d", token) for token in token_hits)
    date_like = bool(re.search(r"(?:19|20)\d{6}", re.sub(r"\D", "", compact)))
    code_lot_like = bool(
        embedded_code
        or (token_hits and any(_is_code_or_lot_number(token) for token in token_hits))
        or (len(digits) in (5, 6, 8) and not _TABLE_SUMMARY_RE.search(text or ""))
    )
    return {
        "codeLotLike": code_lot_like,
        "dateLike": date_like,
        "embeddedCode": embedded_code,
        "tokens": token_hits[:3],
    }


def _summary_block_reconstruction_debug(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
    supply: str = "",
    tax: str = "",
    total: str = "",
) -> dict[str, Any]:
    rows = _group_rows(lines)
    debug: dict[str, Any] = {"blocks": [], "amountCandidates": [], "selected": {}, "rejected": []}
    if not rows:
        return debug

    footer_start = max(page_h * 0.58, (table_header_y or 0) + page_h * 0.08)
    row_infos: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        text = _row_text(row)
        cy = _row_center_y(row)
        values = _amount_values(text)
        supply_label, weak_supply_label, tax_label, total_label = _summary_role_flags_for_labels(text)
        labels: list[str] = []
        if supply_label or weak_supply_label:
            labels.append("supply")
        if tax_label:
            labels.append("tax")
        if total_label:
            labels.append("total")
        summary_like = bool(labels or _TABLE_SUMMARY_RE.search(text))
        table_body_like = bool(_row_has_item_context(text) and not summary_like)
        party_like = bool(_row_has_non_summary_noise(text))
        amounts: list[dict[str, Any]] = []
        for value in values:
            risk = _summary_amount_token_risk(text, value)
            amount = {
                "value": value,
                "numeric": int(value.replace(",", "")),
                "row": idx,
                "x": round(min(item.x for item in row), 2),
                "y": round(cy, 2),
                "text": text,
                "risk": risk,
                "footerRegion": cy >= footer_start,
                "afterTableRows": bool(table_header_y is not None and cy >= table_header_y + page_h * 0.08),
                "tableBodyLike": table_body_like,
                "partyLike": party_like,
            }
            amounts.append(amount)
            debug["amountCandidates"].append(amount)
        eligible = bool(summary_like or amounts) and cy >= page_h * 0.18
        row_infos.append(
            {
                "idx": idx,
                "row": row,
                "text": text,
                "cy": cy,
                "eligible": eligible,
                "labels": labels,
                "summaryLike": summary_like,
                "tableBodyLike": table_body_like,
                "partyLike": party_like,
                "amounts": amounts,
                "denseAmountRow": len(values) >= 6,
            }
        )

    blocks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    previous_idx = -99
    previous_y = -9999.0
    for info in row_infos:
        if not info["eligible"]:
            if current:
                blocks.append(current)
                current = []
            continue
        gap_ok = info["idx"] - previous_idx <= 2 and abs(info["cy"] - previous_y) <= page_h * 0.18
        if current and not gap_ok:
            blocks.append(current)
            current = []
        current.append(info)
        previous_idx = info["idx"]
        previous_y = info["cy"]
    if current:
        blocks.append(current)

    selected_values = {
        "supplyAmount": supply,
        "taxAmount": tax,
        "totalAmount": total,
    }
    selected_compact = {role: value for role, value in selected_values.items() if value}
    block_debug: list[dict[str, Any]] = []
    for block_id, block in enumerate(blocks):
        block_amounts = [amount for info in block for amount in info["amounts"]]
        if not block_amounts and not any(info["labels"] for info in block):
            continue
        label_types = sorted({label for info in block for label in info["labels"]})
        y_values = [info["cy"] for info in block]
        x_values = [line.x for info in block for line in info["row"]]
        footer_region = sum(1 for info in block if info["cy"] >= footer_start) >= max(1, len(block) // 2)
        after_table = bool(table_header_y is not None and min(y_values) >= table_header_y + page_h * 0.08)
        dense = any(info["denseAmountRow"] for info in block)
        table_body_count = sum(1 for info in block if info["tableBodyLike"])
        party_count = sum(1 for info in block if info["partyLike"])
        code_lot_count = sum(1 for amount in block_amounts if amount["risk"]["codeLotLike"] or amount["risk"]["dateLike"])
        summary_label_score = len(label_types) * 14 + (10 if "total" in label_types else 0)
        amount_column_buckets: dict[int, int] = {}
        for amount in block_amounts:
            bucket = int(round(amount["x"] / 50.0) * 50)
            amount_column_buckets[bucket] = amount_column_buckets.get(bucket, 0) + 1
        column_consistency = max(amount_column_buckets.values()) if amount_column_buckets else 0
        block_score = 20.0 + summary_label_score + min(len(block_amounts), 6) * 4
        if footer_region:
            block_score += 12
        if after_table:
            block_score += 8
        if column_consistency >= 2:
            block_score += 6
        if dense:
            block_score -= 10
        block_score -= table_body_count * 8
        block_score -= party_count * 6
        block_score -= code_lot_count * 10
        selected_candidates: dict[str, Any] = {}
        rejected_candidates: list[dict[str, Any]] = []
        for amount in block_amounts:
            matched_role = next((role for role, value in selected_compact.items() if amount["value"] == value), "")
            reason: list[str] = []
            if amount["risk"]["codeLotLike"] or amount["risk"]["dateLike"]:
                reason.append("code_lot_date_like")
            if amount["tableBodyLike"]:
                reason.append("table_body_like")
            if amount["partyLike"]:
                reason.append("party_like")
            if dense:
                reason.append("dense_block")
            if matched_role:
                selected_candidates[matched_role] = {
                    "value": amount["value"],
                    "row": amount["row"],
                    "risk": amount["risk"],
                    "reason": "selected_current_field",
                }
            else:
                rejected_candidates.append(
                    {
                        "value": amount["value"],
                        "row": amount["row"],
                        "reason": ",".join(reason or ["competing_amount"]),
                    }
                )
        block_item = {
            "blockId": block_id,
            "rows": [info["idx"] for info in block],
            "rowCount": len(block),
            "labels": label_types,
            "amountTokens": [
                {
                    "value": amount["value"],
                    "row": amount["row"],
                    "risk": amount["risk"],
                    "tableBodyLike": amount["tableBodyLike"],
                    "partyLike": amount["partyLike"],
                }
                for amount in block_amounts[:12]
            ],
            "yRange": [round(min(y_values), 2), round(max(y_values), 2)],
            "xRange": [round(min(x_values), 2), round(max(x_values), 2)] if x_values else [],
            "footerRegion": footer_region,
            "afterTableRows": after_table,
            "denseAmountRow": dense,
            "tableBodyLikeScore": table_body_count,
            "codeLotLikeScore": code_lot_count,
            "partyLikeScore": party_count,
            "summaryLabelScore": summary_label_score,
            "amountColumnCandidates": sorted(amount_column_buckets.items(), key=lambda item: (-item[1], item[0]))[:4],
            "blockScore": round(block_score, 2),
            "selectedCandidates": selected_candidates,
            "rejectedCandidates": rejected_candidates[:8],
        }
        block_debug.append(block_item)

    block_debug.sort(key=lambda item: (-item["blockScore"], item["blockId"]))
    debug["blocks"] = block_debug[:8]
    for role, value in selected_compact.items():
        debug["selected"][role] = next(
            (
                {"blockId": block["blockId"], "blockScore": block["blockScore"], **candidate}
                for block in block_debug
                for selected_role, candidate in block["selectedCandidates"].items()
                if selected_role == role and candidate["value"] == value
            ),
            {"value": value, "blockId": None, "blockScore": 0, "reason": "selected_value_not_in_summary_block"},
        )
    debug["rejected"] = [
        {"blockId": block["blockId"], "blockScore": block["blockScore"], **candidate}
        for block in block_debug[:4]
        for candidate in block["rejectedCandidates"][:4]
    ][:12]
    return debug


def _summary_total_suppression_decision(
    total: str,
    supply: str,
    tax: str,
    total_debug: dict[str, Any],
    block_debug: dict[str, Any],
) -> dict[str, Any]:
    decision: dict[str, Any] = {
        "selectedTotalBeforeSuppression": total or "",
        "selectedTotalAfterSuppression": total or "",
        "suppressed": False,
        "reason": "",
        "riskFlags": [],
        "positiveEvidence": [],
        "suppressedTotalCandidates": [],
    }
    if not total:
        decision["reason"] = "no_total"
        return decision

    total_num = int(total.replace(",", ""))
    positive: list[str] = []
    risk_flags: list[str] = []
    source = str(total_debug.get("source") or "")
    evidence_reason = str(total_debug.get("reason") or "")

    if source == "summary_checksum_total" or "supply_tax_checksum" in evidence_reason:
        positive.append("checksum")
    if source == "summary_region_total":
        positive.append("summary_region_total")
    if re.search(r"total_label_context|summary_context", evidence_reason):
        positive.append("summary_label_context")
    if supply and tax:
        supply_num = int(supply.replace(",", ""))
        tax_num = int(tax.replace(",", ""))
        if supply_num > tax_num > 0 and _amounts_close(supply_num + tax_num, total_num):
            positive.append("supply_tax_checksum")

    selected_total = block_debug.get("selected", {}).get("totalAmount")
    selected_block: dict[str, Any] | None = None
    if isinstance(selected_total, dict):
        block_id = selected_total.get("blockId")
        selected_block = next(
            (block for block in block_debug.get("blocks", []) if block.get("blockId") == block_id),
            None,
        )
        risk = selected_total.get("risk") if isinstance(selected_total.get("risk"), dict) else {}
        if risk.get("codeLotLike"):
            risk_flags.append("codeLotLike")
        if risk.get("embeddedCode"):
            risk_flags.append("embeddedCode")
        if risk.get("dateLike"):
            risk_flags.append("dateLike")
        tokens = " ".join(str(token) for token in risk.get("tokens", []) if token)
        if re.search(r"[A-Za-z]+\d|\d+[A-Za-z]+", tokens):
            risk_flags.append("embeddedAlphaNumeric")
        if re.search(r"\d{4,}[-.]\d{4,}[-.]\d{4,}", tokens):
            risk_flags.append("hyphenSerial")

    best_occurrence = total_debug.get("bestOccurrence") if isinstance(total_debug.get("bestOccurrence"), dict) else {}
    source_text = str(best_occurrence.get("text") or "")
    if re.search(r"\d{4,}[-.]\d{4,}[-.]\d{4,}", source_text):
        risk_flags.append("hyphenSerial")
    if re.search(r"[A-Za-z]+\d{4,}|\d{4,}[A-Za-z]+", source_text):
        risk_flags.append("embeddedAlphaNumeric")
    if re.search(r"Lot\s*No|LOT|Serial|시리얼|로트|유효일자|제품코드|상품코드|품목코드|총수량|수량|단위", source_text, re.I):
        risk_flags.append("lot_serial_quantity_context")
    if "table_body_like" in evidence_reason:
        risk_flags.append("tableBodyLike")
    if "party_or_noise_context" in evidence_reason:
        risk_flags.append("partyOrNoiseContext")
    if source == "low_confidence_total_existing" or float(total_debug.get("score") or 0) < 50:
        risk_flags.append("lowConfidence")

    if selected_block:
        if selected_block.get("tableBodyLikeScore", 0) > 0:
            risk_flags.append("tableBodyLike")
        if selected_block.get("codeLotLikeScore", 0) > 0:
            risk_flags.append("codeLotLikeBlock")
        if not selected_block.get("labels"):
            risk_flags.append("noSummaryLabel")
        if float(selected_block.get("blockScore") or 0) < 20:
            risk_flags.append("weakSummaryBlock")
        else:
            positive.append("summary_block_score")
        if selected_block.get("summaryLabelScore", 0) > 0:
            positive.append("summary_block_label")

    risk_flags = list(dict.fromkeys(risk_flags))
    positive = list(dict.fromkeys(positive))
    decision["riskFlags"] = risk_flags
    decision["positiveEvidence"] = positive

    strong_positive = bool({"checksum", "supply_tax_checksum", "summary_block_label"} & set(positive))
    high_risk = bool({"codeLotLike", "embeddedCode", "hyphenSerial", "embeddedAlphaNumeric", "lot_serial_quantity_context"} & set(risk_flags))
    weak_context = bool({"lowConfidence", "tableBodyLike", "noSummaryLabel", "weakSummaryBlock"} & set(risk_flags))

    if high_risk and weak_context and not strong_positive:
        decision["suppressed"] = True
        decision["selectedTotalAfterSuppression"] = ""
        decision["reason"] = "suppressed_code_lot_like_total"
        decision["suppressedTotalCandidates"] = [
            {
                "amount": total,
                "reason": "suppressed_code_lot_like_total",
                "riskFlags": risk_flags,
                "positiveEvidence": positive,
                "sourceText": source_text,
                "source": source,
                "score": total_debug.get("score", 0),
                "confidence": "suppressed",
            }
        ]
    else:
        decision["reason"] = "kept_summary_total"
    return decision


def _infer_summary_pair_from_amount_pool(
    lines: list[OcrLine],
    total: str = "",
    allow_synthesized_total: bool = False,
) -> tuple[dict[str, str], dict[str, Any]]:
    total_num = int(total.replace(",", "")) if total else 0
    pool = _summary_amount_pool(lines)
    debug: dict[str, Any] = {"source": "", "candidateCount": len(pool)}
    if len(pool) < 2:
        return {}, debug

    scored: list[tuple[float, int, int, int, str, str, str, str]] = []
    for supply_num, supply_value, supply_idx, supply_y, supply_text in pool:
        for tax_num, tax_value, tax_idx, tax_y, tax_text in pool:
            if supply_num <= tax_num or supply_idx == tax_idx and supply_num == tax_num:
                continue
            ratio = tax_num / supply_num
            if not 0.05 <= ratio <= 0.15:
                continue
            synthesized = supply_num + tax_num
            if total_num and not _amounts_close(synthesized, total_num):
                continue
            row_span = abs(supply_idx - tax_idx)
            if row_span > 24:
                continue
            score = 40.0
            if total_num:
                score += 35
            elif allow_synthesized_total:
                score += 12
            if abs(ratio - 0.1) <= 0.015:
                score += 14
            if row_span <= 4:
                score += 10
            elif row_span <= 12:
                score += 4
            context = f"{supply_text} {tax_text}"
            if _SUPPLY_AMOUNT_ANCHOR_RE.search(context):
                score += 10
            if _TAX_AMOUNT_ANCHOR_RE.search(context):
                score += 10
            if _row_has_item_context(supply_text):
                score -= 8
            if _row_has_item_context(tax_text):
                score -= 8
            scored.append((score, synthesized, supply_num, tax_num, supply_value, tax_value, supply_text, tax_text))

    if not scored:
        return {}, debug
    scored.sort(key=lambda item: (-item[0], -item[1]))
    score, synthesized, _, _, supply_value, tax_value, supply_text, tax_text = scored[0]
    if total_num and score < 62:
        debug["bestScore"] = round(score, 2)
        return {}, debug
    if not total_num and (not allow_synthesized_total or score < 58):
        debug["bestScore"] = round(score, 2)
        return {}, debug

    result = {
        "supplyAmount": supply_value,
        "taxAmount": tax_value,
    }
    if total_num:
        result["totalAmount"] = f"{total_num:,}"
    elif allow_synthesized_total:
        result["totalAmount"] = f"{synthesized:,}"
    debug.update(
        {
            "source": "amount_pair_checksum",
            "bestScore": round(score, 2),
            "supply": [supply_value, supply_text],
            "tax": [tax_value, tax_text],
            "total": result.get("totalAmount", ""),
        }
    )
    return result, debug


def _extract_footer_summary_triple(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
    existing_total: str = "",
) -> tuple[dict[str, str], dict[str, Any]]:
    candidates, footer_start = _footer_summary_candidates(lines, page_h, table_header_y)
    debug: dict[str, Any] = {"source": "", "candidateCount": len(candidates)}
    if len(candidates) < 2:
        return {}, debug

    existing_total_num = int(existing_total.replace(",", "")) if existing_total else 0
    scored: list[tuple[float, SummaryAmountCandidate, SummaryAmountCandidate, SummaryAmountCandidate | None, int]] = []
    for supply_candidate in candidates:
        for tax_candidate in candidates:
            if supply_candidate is tax_candidate:
                continue
            supply_num = supply_candidate.numeric
            tax_num = tax_candidate.numeric
            if supply_num <= 0 or tax_num <= 0 or supply_num <= tax_num:
                continue
            tax_ratio = tax_num / supply_num
            if not 0.05 <= tax_ratio <= 0.15:
                continue
            synthesized_num = supply_num + tax_num
            if existing_total_num and synthesized_num > existing_total_num * 5:
                continue
            total_matches = [
                item
                for item in candidates
                if _amounts_close(item.numeric, synthesized_num) and item is not supply_candidate and item is not tax_candidate
            ]
            if existing_total_num and _amounts_close(synthesized_num, existing_total_num):
                total_matches.append(
                    SummaryAmountCandidate(
                        value=f"{existing_total_num:,}",
                        numeric=existing_total_num,
                        row_idx=max(supply_candidate.row_idx, tax_candidate.row_idx),
                        cy=max(supply_candidate.cy, tax_candidate.cy),
                        x=max(supply_candidate.x, tax_candidate.x),
                        text="existing_total",
                        context=f"{supply_candidate.context} {tax_candidate.context}",
                        supply_anchor=False,
                        tax_anchor=False,
                        total_anchor=True,
                    )
                )
            if not total_matches and not existing_total_num:
                total_matches.append(None)
            for total_candidate in total_matches:
                total_num = total_candidate.numeric if total_candidate else synthesized_num
                if existing_total_num and total_num < existing_total_num * 0.2:
                    continue
                row_span = max(supply_candidate.row_idx, tax_candidate.row_idx, total_candidate.row_idx if total_candidate else tax_candidate.row_idx) - min(
                    supply_candidate.row_idx, tax_candidate.row_idx, total_candidate.row_idx if total_candidate else tax_candidate.row_idx
                )
                y_values = [supply_candidate.cy, tax_candidate.cy]
                if total_candidate:
                    y_values.append(total_candidate.cy)
                y_span = max(y_values) - min(y_values)
                if row_span > 3 or y_span > page_h * 0.08:
                    continue

                score = 40.0
                score += _summary_candidate_base_score(supply_candidate, footer_start, page_h, "supply")
                score += _summary_candidate_base_score(tax_candidate, footer_start, page_h, "tax")
                if total_candidate:
                    score += _summary_candidate_base_score(total_candidate, footer_start, page_h, "total")
                else:
                    score += 6
                if row_span <= 1:
                    score += 12
                elif row_span == 2:
                    score += 6
                if y_span <= page_h * 0.035:
                    score += 8
                if supply_candidate.supply_anchor and tax_candidate.tax_anchor:
                    score += 10
                if total_candidate and total_candidate.total_anchor:
                    score += 8
                if existing_total_num and _amounts_close(total_num, existing_total_num):
                    score += 18
                if total_num == synthesized_num:
                    score += 5
                if abs(tax_ratio - 0.1) <= 0.015:
                    score += 8
                scored.append((score, supply_candidate, tax_candidate, total_candidate, synthesized_num))

    if not scored:
        return {}, debug
    scored.sort(key=lambda item: (-item[0], -item[4]))
    score, supply_candidate, tax_candidate, total_candidate, synthesized_num = scored[0]
    if score < 78:
        debug["bestScore"] = round(score, 2)
        return {}, debug

    result = {
        "supplyAmount": supply_candidate.value,
        "taxAmount": tax_candidate.value,
        "totalAmount": total_candidate.value if total_candidate else f"{synthesized_num:,}",
    }
    debug.update(
        {
            "source": "footer_summary_triple",
            "bestScore": round(score, 2),
            "supplySource": "footer_supply_anchor" if supply_candidate.supply_anchor else "footer_summary_amount",
            "taxSource": "footer_tax_anchor" if tax_candidate.tax_anchor else "footer_summary_amount",
            "totalSource": "footer_total_anchor" if total_candidate and total_candidate.total_anchor else "synthesized_supply_tax",
            "supply": [supply_candidate.value, round(supply_candidate.x), round(supply_candidate.cy), supply_candidate.text],
            "tax": [tax_candidate.value, round(tax_candidate.x), round(tax_candidate.cy), tax_candidate.text],
            "total": (
                [total_candidate.value, round(total_candidate.x), round(total_candidate.cy), total_candidate.text]
                if total_candidate
                else [f"{synthesized_num:,}", None, None, "synthesized_supply_tax"]
            ),
        }
    )
    return result, debug


def _extract_footer_total_amount(lines: list[OcrLine], page_h: float, table_header_y: float | None) -> str:
    rows = _group_rows(lines)
    if not rows:
        return ""
    footer_start = max(page_h * 0.68, (table_header_y or 0) + page_h * 0.18)
    summary_rows: list[tuple[int, str, float]] = []
    for idx, row in enumerate(rows):
        text = _row_text(row)
        cy = _row_center_y(row)
        if cy < footer_start or cy > page_h * 0.94:
            continue
        if _row_has_item_context(text) and not _TABLE_SUMMARY_RE.search(text):
            continue
        if _TABLE_SUMMARY_RE.search(text) or _TOTAL_AMOUNT_ANCHOR_RE.search(text):
            summary_rows.append((idx, text, cy))

    candidates: list[tuple[float, int, str]] = []
    for idx, text, cy in summary_rows:
        neighborhood = [text]
        for near_idx in (idx - 1, idx + 1, idx + 2):
            if 0 <= near_idx < len(rows):
                near_text = _row_text(rows[near_idx])
                near_cy = _row_center_y(rows[near_idx])
                if abs(near_cy - cy) <= page_h * 0.055 and not _row_has_item_context(near_text):
                    neighborhood.append(near_text)
        blob = " ".join(neighborhood)
        for value in _amount_values(blob):
            numeric = int(value.replace(",", ""))
            score = 20.0
            if _TOTAL_AMOUNT_ANCHOR_RE.search(blob) or re.search(r"\ud569\s*\uacc4|\ud568\s*\uacc4|TOTAL", blob, re.I):
                score += 12
            if re.search(r"\uacf5\uae09\s*\uac00\uc561|\uacf5\uae09\s*\uae08\uc561|\uc138\s*\uc561|\ubd80\uac00\s*\uc138", blob):
                score += 5
            score += min(max((cy - footer_start) / max(page_h * 0.25, 1), 0), 1) * 6
            candidates.append((score, numeric, value))

    if not candidates:
        footer_lines = [
            line
            for line in lines
            if footer_start <= line.cy <= page_h * 0.94
            and not _row_has_item_context(line.text)
            and not _BIZ_RE.search(_canonical_digits(line.text))
            and not _PHONE_RE.search(line.text)
        ]
        for line in footer_lines:
            text = line.text
            if not (_TABLE_SUMMARY_RE.search(text) or _TOTAL_AMOUNT_ANCHOR_RE.search(text)):
                continue
            for value in _amount_values(text):
                candidates.append((18.0, int(value.replace(",", "")), value))

    if not candidates:
        return ""
    candidates.sort(key=lambda item: (-item[0], -item[1]))
    return candidates[0][2]


def _extract_amount_fields(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
    debug: dict[str, Any] | None = None,
) -> dict[str, str]:
    start_y = max((table_header_y or page_h * 0.45), page_h * 0.35)
    bottom = [line for line in lines if line.cy >= start_y]
    if not bottom:
        bottom = lines
    supply = _extract_amount_near(bottom, _SUPPLY_AMOUNT_ANCHOR_RE)
    tax = _extract_amount_near(bottom, _TAX_AMOUNT_ANCHOR_RE)
    if not supply:
        supply = _extract_amount_near_reading_order(lines, _SUPPLY_AMOUNT_ANCHOR_RE)
    if not tax:
        tax = _extract_amount_near_reading_order(lines, _TAX_AMOUNT_ANCHOR_RE)
    if supply and int(supply.replace(",", "")) < 10_000:
        supply = ""
    if tax and int(tax.replace(",", "")) < 10_000:
        tax = ""
    footer_total = _extract_footer_total_amount(lines, page_h, table_header_y)
    total = footer_total or _extract_amount_near(bottom, _TOTAL_AMOUNT_ANCHOR_RE)
    labeled_summary, labeled_debug = _summary_label_window_amounts(lines, page_h, table_header_y, existing_total=total)
    if labeled_debug.get("checksumOk"):
        supply = labeled_summary.get("supplyAmount", supply)
        tax = labeled_summary.get("taxAmount", tax)
        total = labeled_summary.get("totalAmount", total)
    if not supply:
        supply = labeled_summary.get("supplyAmount", "")
    if not tax:
        tax = labeled_summary.get("taxAmount", "")
    if not total:
        total = labeled_summary.get("totalAmount", "")
    summary_triple, summary_debug = _extract_footer_summary_triple(lines, page_h, table_header_y, existing_total=total)
    pair_debug: dict[str, Any] = {}
    used_summary_triple = False
    if summary_triple:
        triple_total_num = int(summary_triple["totalAmount"].replace(",", ""))
        total_num = int(total.replace(",", "")) if total else 0
        if not total or _amounts_close(triple_total_num, total_num) or triple_total_num > total_num:
            supply = summary_triple["supplyAmount"]
            tax = summary_triple["taxAmount"]
            total = summary_triple["totalAmount"]
            used_summary_triple = True
        elif total_num and triple_total_num <= total_num * 5:
            supply = summary_triple["supplyAmount"]
            tax = summary_triple["taxAmount"]
            used_summary_triple = True
    values = _amount_values("\n".join(line.text for line in bottom))
    tail_max = max(values, key=lambda item: int(item.replace(",", ""))) if values else ""
    synthesized_total = ""
    if supply and tax:
        supply_num = int(supply.replace(",", ""))
        tax_num = int(tax.replace(",", ""))
        if supply_num > tax_num > 0:
            synthesized_total = f"{supply_num + tax_num:,}"
    if synthesized_total:
        synth_num = int(synthesized_total.replace(",", ""))
        total_num = int(total.replace(",", "")) if total else 0
        if not total or (synth_num > total_num and synth_num <= total_num * 5):
            total = synthesized_total
    total_num_for_pair = int(total.replace(",", "")) if total else 0
    weak_total = bool(total_num_for_pair and total_num_for_pair < 10_000 and not used_summary_triple)
    pair_summary, pair_debug = _infer_summary_pair_from_amount_pool(
        lines,
        total="" if weak_total else total,
        allow_synthesized_total=weak_total,
    )
    if pair_summary:
        pair_total_num = int(pair_summary.get("totalAmount", "0").replace(",", ""))
        current_total_num = int(total.replace(",", "")) if total else 0
        if weak_total or not total or (current_total_num and _amounts_close(pair_total_num, current_total_num)):
            supply = pair_summary.get("supplyAmount", supply)
            tax = pair_summary.get("taxAmount", tax)
            total = pair_summary.get("totalAmount", total)
            used_summary_triple = True
    if tail_max and (
        not total
        or (not synthesized_total and int(tail_max.replace(",", "")) > int(total.replace(",", "")) * 1.5)
    ):
        if not total or int(tail_max.replace(",", "")) > int(total.replace(",", "")):
            total = tail_max
    if total:
        total_num = int(total.replace(",", ""))
        supply_absurd = bool(supply and int(supply.replace(",", "")) > total_num * 5)
        if supply_absurd:
            supply = ""
        if supply_absurd and tax and int(tax.replace(",", "")) > total_num * 0.5:
            tax = ""
        if not used_summary_triple:
            if supply and tax:
                supply_num = int(supply.replace(",", ""))
                tax_num = int(tax.replace(",", ""))
                if supply_num > tax_num > 0 and not _amounts_close(supply_num + tax_num, total_num):
                    supply = ""
                    tax = ""
            if tax and int(tax.replace(",", "")) >= total_num * 0.3:
                tax = ""
            if supply and int(supply.replace(",", "")) >= total_num * 0.98:
                supply = ""
    total_debug = _summary_total_evidence(lines, page_h, table_header_y, total, supply=supply, tax=tax)
    block_debug = _summary_block_reconstruction_debug(lines, page_h, table_header_y, supply=supply, tax=tax, total=total)
    suppression_decision = _summary_total_suppression_decision(total, supply, tax, total_debug, block_debug)
    if suppression_decision.get("suppressed"):
        total = ""
    single_supply_decision = labeled_debug.get("singleSupplyDecision")
    if single_supply_decision and single_supply_decision.get("candidate"):
        candidate_value = single_supply_decision.get("candidate")
        candidate_block = next(
            (
                item
                for item in block_debug.get("rejected", [])
                if item.get("value") == candidate_value
            ),
            next(
                (
                    item
                    for item in block_debug.get("selected", {}).values()
                    if isinstance(item, dict) and item.get("value") == candidate_value
                ),
                None,
            ),
        )
        if not candidate_block:
            candidate_block = next(
                (
                    {
                        "blockId": block.get("blockId"),
                        "blockScore": block.get("blockScore"),
                        "reason": "candidate_in_summary_block",
                        "risk": amount.get("risk"),
                    }
                    for block in block_debug.get("blocks", [])
                    for amount in block.get("amountTokens", [])
                    if amount.get("value") == candidate_value
                ),
                None,
            )
        if candidate_block:
            single_supply_decision["summaryBlockId"] = candidate_block.get("blockId")
            single_supply_decision["blockScore"] = candidate_block.get("blockScore")
            single_supply_decision["blockReason"] = candidate_block.get("reason")
            if candidate_block.get("risk"):
                single_supply_decision["blockRisk"] = candidate_block.get("risk")
    if debug is not None:
        debug["amount_label_window"] = labeled_debug
        debug["amount_summary_triple"] = summary_debug
        debug["amount_pair_checksum"] = pair_debug
        debug["amount_total_evidence"] = total_debug
        debug["amount_summary_blocks"] = block_debug
        debug["totalSuppressionDecision"] = suppression_decision
        debug["suppressedTotalCandidates"] = suppression_decision.get("suppressedTotalCandidates", [])
    return {"supplyAmount": supply, "taxAmount": tax, "totalAmount": total}


def _detect_table(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
    expected_columns: dict[str, list[str]] | None = None,
    table_bounds: dict[str, float] | None = None,
    column_guides: list[float] | None = None,
) -> dict[str, str]:
    rows = _group_rows(lines)
    header_index = -1
    for idx, row in enumerate(rows):
        row_y = sum(item.cy for item in row) / len(row)
        if table_header_y is not None and abs(row_y - table_header_y) <= max(item.h for item in row) * 2:
            header_index = idx
            break
        if _table_token_count(_row_text(row)) >= 2:
            header_index = idx
            break

    table_detected = header_index >= 0
    data_rows: list[str] = _extract_table_row_texts(rows, page_h, header_index)
    if table_detected:
        header_y = max(item.cy for item in rows[header_index])
        for idx in range(header_index + 1, len(rows)):
            row = rows[idx]
            text = _row_text(row)
            row_y = sum(item.cy for item in row) / len(row)
            if row_y <= header_y or row_y >= page_h * 0.90:
                continue
            if _is_summary_row_for_items(text):
                break
            if _is_table_header_only_row(text):
                continue
            candidate = _table_data_candidate_text(rows, idx, page_h)
            if candidate:
                data_rows.append(candidate)
        data_rows = [text for text in _dedupe_table_rows(data_rows) if _is_valid_final_item_text(text)]

    if not data_rows:
        body_start = min((table_header_y or page_h * 0.25), page_h * 0.25)
        body_rows = [
            (idx, _row_text(row))
            for idx, row in enumerate(rows)
            if body_start <= sum(item.cy for item in row) / len(row) <= page_h * 0.88
        ]
        data_rows = [
            candidate
            for idx, _ in body_rows
            if (candidate := _table_data_candidate_text(rows, idx, page_h))
        ]
        if not data_rows:
            data_rows = [
                text
                for _, text in body_rows
                if re.search(r"\d", text)
                and len(text) >= 3
                and not _is_code_only_table_row(text)
                and not _is_numeric_detail_line(text)
                and not _is_table_header_only_row(text)
                and _table_row_score(text) > 0
            ]
        data_rows = [text for text in _dedupe_table_rows(data_rows) if _is_valid_final_item_text(text)]
        table_detected = table_detected or len(data_rows) >= 2

    if not data_rows:
        item_line_candidates: list[tuple[float, float, float, str]] = []
        numeric_lines = [
            line
            for line in lines
            if page_h * 0.18 <= line.cy <= page_h * 0.88
            and re.search(r"\d", line.text or "")
            and not _is_bad_table_data_row(line.text)
            and not _is_table_header_only_row(line.text)
        ]
        for line in lines:
            if not (page_h * 0.18 <= line.cy <= page_h * 0.88):
                continue
            text = _clean_value(line.text)
            if not _is_item_name_like(text):
                continue
            nearby = [
                item
                for item in numeric_lines
                if item is not line
                and (
                    (0 < item.cy - line.cy <= page_h * 0.12)
                    or abs(item.cy - line.cy) <= page_h * 0.04
                )
            ]
            nearby.sort(key=lambda item: (abs(item.cy - line.cy), item.x))
            if not nearby and not re.search(r"\d", text):
                continue
            preview = " ".join([text] + [item.text for item in nearby[:4]])
            score = _table_row_score(preview) + 10
            item_line_candidates.append((score, line.cy, line.x, preview))
        if item_line_candidates:
            item_line_candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
            data_rows = [_summarize_table_row(item_line_candidates[0][3])]
            table_detected = True

    if not data_rows:
        line_candidates: list[tuple[float, float, float, str]] = []
        for line in lines:
            if not (page_h * 0.18 <= line.cy <= page_h * 0.88):
                continue
            text = _clean_value(line.text)
            if len(text) < 3 or not re.search(r"\d", text):
                continue
            if _is_code_only_table_row(text) or _is_numeric_detail_line(text):
                continue
            if _is_bad_table_data_row(text) or _is_table_header_only_row(text):
                continue
            if not re.search(r"[가-힣]", text) and not re.search(r"TABLET|CAPSULE|CAPS?|ABLET", text, re.I):
                continue
            score = _table_row_score(text)
            if _ITEM_NAME_HINT_RE.search(text):
                score += 8
            if score <= 2:
                continue
            line_candidates.append((score, line.cy, line.x, text))
        if line_candidates:
            line_candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
            _, first_y, _, first_text = line_candidates[0]
            nearby = [
                (x, text)
                for _, cy, x, text in line_candidates
                if abs(cy - first_y) <= page_h * 0.08 and text != first_text
            ]
            nearby.sort(key=lambda item: item[0])
            preview = " ".join([first_text] + [text for _, text in nearby[:5]])
            data_rows = [_summarize_table_row(preview)]
            table_detected = True

    if not data_rows:
        data_rows = _text_order_table_fallback(lines)
        table_detected = table_detected or bool(data_rows)
    if not data_rows:
        data_rows = [
            _clean_value(line.text)
            for line in lines
            if 0 <= line.cy <= page_h * 0.92
            and _has_product_hint(line.text)
            and not _is_business_contact_line(line.text)
            and not _is_table_header_row(line.text)
            and not _is_summary_row_for_items(line.text)
        ]
        table_detected = table_detected or bool(data_rows)

    data_rows = [text for text in _dedupe_table_rows(data_rows) if _is_valid_final_item_text(text)]
    if not data_rows:
        data_rows = [
            _clean_value(line.text)
            for line in lines
            if 0 <= line.cy <= page_h * 0.92
            and _has_product_hint(line.text)
            and _is_valid_final_item_text(line.text)
        ]

    legacy_items = [_item_dict_from_row_text(text) for text in data_rows]
    structured_items = _structured_table_items(lines, page_h)
    legacy_score = sum(_table_item_column_score(item) for item in legacy_items)
    structured_score = sum(_table_item_column_score(item) for item in structured_items)
    if structured_items and (
        not legacy_items
        or len(structured_items) > len(legacy_items)
        or (len(structured_items) == len(legacy_items) and structured_score > legacy_score)
        or _is_table_notice_or_party_line(str(legacy_items[0].get("rawText") or ""))
        or not _has_product_hint(str(legacy_items[0].get("itemName") or legacy_items[0].get("rawText") or ""))
    ):
        table_items = structured_items
    else:
        table_items = legacy_items

    page_w = max((line.x + line.w for line in lines), default=1000.0) if lines else 1000.0

    # T-6e: expectedColumns-based header matching (preferred path when available)
    expected_debug: dict[str, Any] = {}
    expected_items: list[dict[str, Any]] = []
    if expected_columns:
        expected_items = _table_items_with_expected_columns(
            lines, page_h, page_w, expected_columns, table_bounds, debug=expected_debug,
            column_guides=column_guides,
        )

    if expected_items:
        table_items = expected_items
        header_debug: dict[str, Any] = expected_debug
        header_used = True
    else:
        # T-6: try header-based column mapping (auto-detection fallback)
        # T-6j-fix-2pdf: preserve colGuides debug fields even when colGuides path yields nothing,
        # so tableDebug shows columnGuidesUsedAttempted / rowCandidateCountBeforeFilter / AfterFilter.
        _cg_debug_fields = {
            k: expected_debug[k]
            for k in ("columnGuidesUsedAttempted", "columnGuidesReceived", "columnGuidesCount",
                      "rowCandidateCountBeforeFilter", "rowCandidateCountAfterFilter",
                      "fallbackReason", "rowCandidates")
            if k in expected_debug
        }
        # Store colGuides rejectedRows separately to avoid clobbering header_mapping's rejectedRows
        if "rejectedRows" in expected_debug:
            _cg_debug_fields["colGuidesRejectedRows"] = expected_debug["rejectedRows"]
        header_debug = {}
        header_items = _table_items_from_header_mapping(lines, page_h, page_w, debug=header_debug)
        # Merge preserved colGuides debug into header_debug without overwriting header-mapping fields
        for k, v in _cg_debug_fields.items():
            header_debug.setdefault(k, v)
        # T-7a: compare score as well as count so garbled header_items (all-empty values)
        # don't silently replace legacy items that already have itemName/amounts filled.
        _header_score = sum(_table_item_column_score(item) for item in header_items)
        _current_score = sum(_table_item_column_score(item) for item in table_items)
        header_used = bool(
            header_items
            and (
                not table_items
                or len(header_items) > len(table_items)
                or (len(header_items) == len(table_items) and _header_score >= _current_score)
            )
        )
        if header_used:
            table_items = header_items

    # T-6n: OP anchor reconstruction — for transposed/compressed tables where
    # OP-* item codes far outnumber what standard extraction recovered.
    # Guard: ≥3 OP-* anchors found AND anchors > current table_items count.
    if expected_columns:
        _op_anchors_quick = _find_op_anchor_lines(lines)
        _op_anchor_count = len(_op_anchors_quick)
        if _op_anchor_count >= 3 and _op_anchor_count > len(table_items):
            _op_debug: dict[str, Any] = {}
            _op_items = _op_anchor_reconstruct_table(
                lines, page_h, page_w, expected_columns,
                table_bounds=table_bounds, debug=_op_debug,
            )
            if _op_items and len(_op_items) > len(table_items):
                _prev_source = str((table_items[0].get("source") or "") if table_items else "")
                _prev_count = len(table_items)
                table_items = _op_items
                header_debug["opAnchorReconstructionAttempted"] = True
                header_debug["opAnchorCount"] = _op_debug.get("opAnchorCount", _op_anchor_count)
                header_debug["opAnchorSamples"] = _op_debug.get("opAnchorSamples", [])
                header_debug["opAnchorRowsBuilt"] = _op_debug.get("opAnchorRowsBuilt", 0)
                header_debug["previousExtractionSource"] = _prev_source
                header_debug["previousRowCount"] = _prev_count
                header_debug["reconstructedRowCount"] = len(_op_items)

    # T-6: sort table_items by y-coordinate so rowIndex follows visual order
    def _item_y_key(item: dict[str, Any]) -> float:
        if "_row_y" in item:
            return float(item["_row_y"])
        bboxes = item.get("sourceBboxes") or []
        if bboxes:
            return min(float(b.get("y", 0)) for b in bboxes)
        return 0.0

    table_items = sorted(table_items, key=_item_y_key)

    data_rows = [str(item.get("rawText") or "") for item in table_items]
    table_detected = table_detected or bool(table_items)

    # Determine extraction source for debug
    first_source = str((table_items[0].get("source") or "") if table_items else "")
    if first_source == "op_anchor_reconstructed_table":
        extraction_source = "op_anchor_reconstructed_table"  # T-6n
    elif first_source == "template_colguides_expected_columns":
        extraction_source = "template_colguides_expected_columns"  # T-6j
    elif first_source == "expected_columns_header_match":
        extraction_source = "expected_columns_header_match"
    elif first_source == "header_column_mapping":
        extraction_source = "header_column_mapping"
    elif table_items is structured_items:
        extraction_source = "structured_items"
    else:
        extraction_source = "legacy_text_items"

    # T-6d/T-6e: tableDebug — 진단 정보
    table_debug: dict[str, Any] = {
        "headerUsed": header_used,
        "headerRowFound": header_debug.get("headerFound", header_debug.get("headerBandFound", False)),
        "headerY": header_debug.get("headerY") or (
            header_debug.get("selectedHeaderBand", {}).get("y") if isinstance(header_debug.get("selectedHeaderBand"), dict) else None
        ),
        "headerScore": header_debug.get("headerScore", header_debug.get("selectedHeaderBand", {}).get("score", 0) if isinstance(header_debug.get("selectedHeaderBand"), dict) else 0),
        "headerLines": header_debug.get("headerLines", list(header_debug.get("matchedHeaders", []))),
        "boundaryCount": header_debug.get("boundaryCount", len(header_debug.get("boundaries", []))),
        "boundaries": header_debug.get("boundaries", []),
        "rowCandidateCount": len(table_items),
        "rejectedRows": header_debug.get("rejectedRows", []),
        "tableBoundsEstimate": {
            "xMin": min((line.x for line in lines), default=0.0),
            "xMax": max((line.x + line.w for line in lines), default=page_w),
            "yHeader": header_debug.get("headerY"),
            "yBottom": page_h * 0.93,
        },
        "fallbackSource": extraction_source,
        # T-6e additions
        "extractionSource": extraction_source,
        "expectedColumnsUsed": bool(expected_items),
        "tableBoundsUsed": bool(table_bounds),
        "expectedColumns": header_debug.get("expectedColumns", []),
        "matchedHeaders": header_debug.get("matchedHeaders", []),
        "missingExpectedHeaders": header_debug.get("missingExpectedHeaders", []),
        "interpolatedColumns": header_debug.get("interpolatedColumns", []),
        "selectedHeaderBand": header_debug.get("selectedHeaderBand"),
        "rowEndReason": header_debug.get("rowEndReason"),
        "fallbackReason": header_debug.get("fallbackReason"),
        # T-6j-fix: propagate colGuides debug from expected_debug/header_debug
        "columnGuidesReceived": header_debug.get("columnGuidesReceived", False),
        "columnGuidesCount": header_debug.get("columnGuidesCount", 0),
        "columnGuidesOcrSpace": header_debug.get("columnGuideOcrSpace", []),
        "columnGuideMode": header_debug.get("columnGuideMode", ""),
        "columnGuideMismatch": header_debug.get("columnGuideMismatch"),
        "tableBoundsSource": header_debug.get("tableBoundsSource", ""),
        # T-6j-fix-2pdf: row filter debug
        "columnGuidesUsedAttempted": header_debug.get("columnGuidesUsedAttempted", False),
        "rowCandidateCountBeforeFilter": header_debug.get("rowCandidateCountBeforeFilter"),
        "rowCandidateCountAfterFilter": header_debug.get("rowCandidateCountAfterFilter"),
        "colGuidesRejectedRows": header_debug.get("colGuidesRejectedRows", []),
        # T-6n: OP anchor reconstruction debug
        "opAnchorReconstructionAttempted": header_debug.get("opAnchorReconstructionAttempted", False),
        "opAnchorCount": header_debug.get("opAnchorCount"),
        "opAnchorSamples": header_debug.get("opAnchorSamples", []),
        "opAnchorRowsBuilt": header_debug.get("opAnchorRowsBuilt"),
        "opAnchorRejectedReasonCounts": header_debug.get("opAnchorRejectedReasonCounts", {}),
        "previousExtractionSource": header_debug.get("previousExtractionSource"),
        "previousRowCount": header_debug.get("previousRowCount"),
        "reconstructedRowCount": header_debug.get("reconstructedRowCount"),
    }

    return {
        "tableDetected": "Y" if table_detected else "N",
        "rowCount": str(len(table_items)) if table_items else "",
        "firstRowPreview": _table_row_preview_from_item(table_items[0]) if table_items else "",
        "tableRows": table_items,
        "items": table_items,
        "tableDebug": table_debug,
    }


# ── T-3: canonical tableRows helpers ─────────────────────────────────────────

def _empty_table_row(row_index: int, raw_text: str = "") -> dict[str, Any]:
    return {
        "rowIndex": row_index,
        "itemCode": "", "itemName": "", "spec": "", "lotNo": "", "serialNo": "",
        "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "",
        "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "",
        "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "",
        "_rawText": raw_text,
        "_confidence": None,
        "_source": "invoice_statement_table_parser",
    }


def _tr_extract_expiry_date(text: str) -> str:
    m = _TR_EXPIRY_YYYYMMDD_RE.search(text)
    if m:
        return m.group(1)
    m = _TR_EXPIRY_YMDASH_RE.search(text)
    if m:
        return re.sub(r"[-./]", "", m.group(1))
    m = _TR_EXPIRY_YYMMDD_RE.search(text)
    if m:
        return m.group(1)
    return ""


def _tr_extract_serial(text: str) -> str:
    m = _TR_SERIAL_HYPHEN_RE.search(text)
    return m.group(1) if m else ""


def _tr_extract_unit(text: str) -> str:
    m = _TR_UNIT_RE.search(text)
    return m.group(1).upper() if m else ""


def _tr_extract_item_code(text: str, item_name: str, spec: str) -> str:
    rest = text
    for part in (item_name, spec):
        if part and rest.startswith(part):
            rest = rest[len(part):].strip()
    for m in _TR_ITEM_CODE_RE.finditer(rest):
        candidate = m.group(1)
        if _HANGUL_RE.search(candidate):
            continue
        compact = re.sub(r"\D", "", candidate)
        if len(compact) < 3:
            continue
        return candidate
    return ""


def _tr_extract_lot(text: str, item_name: str, spec: str, expiry_str: str) -> str:
    # Search full rawText for lot-like 4-6 digit numbers
    amount_matches = {m.group() for m in _TR_AMOUNT_COMMA_RE.finditer(text)}
    candidates: list[tuple[int, str]] = []
    for m in re.finditer(r"(?<!\d)(\d{4,6})(?!\d)", text):
        val = m.group(1)
        if val == expiry_str:
            continue
        if val in amount_matches:
            continue
        if len(val) == 6:
            try:
                mm, dd = int(val[2:4]), int(val[4:6])
                if 1 <= mm <= 12 and 1 <= dd <= 31:
                    continue
            except ValueError:
                pass
        num = int(val)
        if num <= 100:
            continue
        if num > 999999:
            continue
        candidates.append((m.start(), val))
    if not candidates:
        return ""
    # Prefer candidates after item_name
    item_end = 0
    if item_name and item_name in text:
        item_end = text.index(item_name) + len(item_name)
    after = [c for c in candidates if c[0] >= item_end]
    return (after or candidates)[0][1]


def _estimate_table_profile(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "unknown"
    n = len(rows)
    has_lot = any(r.get("lotNo") for r in rows)
    has_serial = any(r.get("serialNo") for r in rows)
    has_amount = any(r.get("amount") or r.get("supplyAmount") for r in rows)
    has_code = any(r.get("itemCode") for r in rows)
    if n == 1:
        return "single_item_table"
    if has_serial and not has_amount:
        return "serial_quantity_table"
    if has_lot and not has_amount:
        return "lot_serial_quantity_table"
    if has_code and not has_lot:
        return "item_quantity_table" if n <= 3 else "multi_item_table"
    return "multi_item_table"


def _canonical_row_preview(row: dict[str, Any]) -> str:
    parts = [
        str(row.get("itemName") or ""),
        str(row.get("spec") or ""),
        str(row.get("lotNo") or row.get("serialNo") or ""),
        str(row.get("quantity") or ""),
        str(row.get("amount") or row.get("supplyAmount") or ""),
    ]
    return " ".join(p for p in parts if p)[:100]


def _build_canonical_table_rows(
    table_items: list[dict[str, Any]],
    expected_columns: dict[str, list[str]] | None = None,
    matched_column_keys: list[str] | None = None,
) -> dict[str, Any]:
    canonical_rows: list[dict[str, Any]] = []
    col_fill: dict[str, int] = {c: 0 for c in _TABLE_ROW_COLUMNS}

    # T-6: sort items by y-coordinate before assigning rowIndex
    def _item_y_key_inner(item: dict[str, Any]) -> float:
        if "_row_y" in item:
            return float(item["_row_y"])
        bboxes = item.get("sourceBboxes") or []
        if bboxes:
            return min(float(b.get("y", 0)) for b in bboxes)
        return 0.0

    sorted_items = sorted(table_items, key=_item_y_key_inner)

    # T-6: all canonical columns (except rowIndex) to copy from item
    _ALL_COPY_KEYS = (
        "itemName", "itemCode", "spec", "lotNo", "serialNo", "manufacturingNo",
        "expiryDate", "quantity", "unit", "unitPrice",
        "supplyAmount", "taxAmount", "amount", "totalAmount",
        "manufacturer", "insuranceCode", "remark",
    )

    for idx, item in enumerate(sorted_items):
        raw_text = str(item.get("rawText") or "")
        row = _empty_table_row(idx + 1, raw_text)

        # T-6: copy ALL pre-populated canonical columns from item (not just 8)
        for key in _ALL_COPY_KEYS:
            val = str(item.get(key) or "")
            if val:
                row[key] = val

        # T-6h: copy non-canonical expected keys (e.g. serialLotComposite, consumerUnitPrice)
        for key, val in item.items():
            if key not in row and key not in {
                "rawText", "sourceBboxes", "source", "_row_y",
            } and str(val or ""):
                row[key] = str(val)

        # T-6: apply regex-based extraction only for columns still empty
        if raw_text:
            if not row.get("serialNo"):
                serial = _tr_extract_serial(raw_text)
                if serial:
                    row["serialNo"] = serial
            if not row.get("expiryDate"):
                expiry = _tr_extract_expiry_date(raw_text)
                if expiry:
                    row["expiryDate"] = expiry
            else:
                expiry = row["expiryDate"]
            if not row.get("lotNo"):
                lot = _tr_extract_lot(raw_text, row["itemName"], row["spec"], expiry)
                if lot:
                    row["lotNo"] = lot
            if not row.get("unit"):
                unit = _tr_extract_unit(raw_text)
                if unit:
                    row["unit"] = unit
            if not row.get("itemCode"):
                code = _tr_extract_item_code(raw_text, row["itemName"], row["spec"])
                if code:
                    row["itemCode"] = code

        # T-6h: auto-populate composite display keys from component fields
        if not row.get("manufacturingExpiryComposite"):
            mfg = str(row.get("manufacturingNo") or "").strip()
            exp = str(row.get("expiryDate") or "").strip()
            if mfg or exp:
                row["manufacturingExpiryComposite"] = " / ".join(filter(None, [mfg, exp]))
        if not row.get("serialLotComposite"):
            ser = str(row.get("serialNo") or "").strip()
            lot = str(row.get("lotNo") or "").strip()
            if ser or lot:
                row["serialLotComposite"] = " / ".join(filter(None, [ser, lot]))

        # T-6m: post-process unit column — if value looks like a lot-number pattern
        # (e.g. "0350823-231024-200811"), move to lotNo and clear unit.
        if row.get("unit") and not row.get("lotNo"):
            _unit_chk = str(row["unit"])
            if re.search(r"\d{6,}[-/]\d{6}", _unit_chk):
                row["lotNo"] = _unit_chk
                row["unit"] = ""

        # T-6m: post-process quantity column — if it starts with a unit-prefix (BOX/EA/…),
        # extract unit and leave only the numeric part as quantity.
        if row.get("quantity") and not row.get("unit"):
            _qty_chk = str(row["quantity"])
            _qty_unit_m = re.match(r"^(BOX|EA|TAB|CAP|BOTTLE|AMP|VIAL)\s+(.+)$", _qty_chk, re.I)
            if _qty_unit_m:
                row["unit"] = _qty_unit_m.group(1).upper()
                row["quantity"] = _qty_unit_m.group(2).strip()

        # T-7a: Validate quantity — if it contains Korean characters or is clearly
        # a misassigned cell (long garbled text), clear it.
        # Keeps numeric quantities like "1,000" (len of digits ≤ 7).
        if row.get("quantity"):
            _qty_v = str(row["quantity"])
            _qty_clean = re.sub(r"[,.\s]", "", _qty_v)
            if re.search(r"[가-힣]", _qty_v) or (len(_qty_v) > 20 and not re.fullmatch(r"[\d,.\s]+", _qty_v)):
                row["quantity"] = ""

        for col in _TABLE_ROW_COLUMNS:
            if row.get(col):
                col_fill[col] += 1

        canonical_rows.append(row)

    required_filled = sum(
        1 for r in canonical_rows if r.get("itemName") or r.get("quantity")
    ) if canonical_rows else 0
    if not canonical_rows:
        extraction_status = "not_extracted"
    elif required_filled == len(canonical_rows):
        extraction_status = "partial"
    elif required_filled > 0:
        extraction_status = "partial"
    else:
        extraction_status = "parser_not_ready"

    table_profile = _estimate_table_profile(canonical_rows)
    actual_columns = [c for c in _TABLE_ROW_COLUMNS if col_fill.get(c, 0) > 0]

    # T-6e-fix / T-6h: expected schema processing — now includes non-canonical keys
    _valid_col_set = set(_TABLE_ROW_COLUMNS)
    expected_required: list[str] = []
    expected_all_keys: list[str] = []
    if expected_columns:
        req = expected_columns.get("required") or []
        opt = expected_columns.get("optional") or []
        _seen_exp: set[str] = set()
        for k in req + opt:
            if k not in _seen_exp:
                _seen_exp.add(k)
                expected_all_keys.append(k)  # T-6h: include non-canonical keys too
        expected_required = list(req)  # T-6h: include non-canonical required keys
        # Ensure all expected keys exist in every canonical row (empty string if no value)
        for row in canonical_rows:
            for key in expected_all_keys:
                if key not in row or row[key] is None:
                    row[key] = ""

    matched_keys_clean = [k for k in (matched_column_keys or []) if k in _valid_col_set]
    # T-6h: value columns include non-canonical keys that have at least one value
    non_canonical_filled = [
        k for k in expected_all_keys
        if k not in _valid_col_set and any(str(row.get(k) or "") for row in canonical_rows)
    ]
    value_column_keys = actual_columns + non_canonical_filled
    missing_expected_required = [k for k in expected_required if k not in value_column_keys]

    # T-6: detect source to aid debugging
    sources = {str(item.get("source") or "legacy") for item in sorted_items}
    debug_source = "header_column_mapping" if "header_column_mapping" in sources else "existing_table_detection"

    table_meta: dict[str, Any] = {
        "tableProfile": table_profile,
        "gridMode": "",
        "rowCount": len(canonical_rows),
        "columns": actual_columns,
        "firstRowPreview": _canonical_row_preview(canonical_rows[0]) if canonical_rows else "",
        "endKeywordMatched": None,
        "extractionStatus": extraction_status,
    }

    # T-6e-fix: add expected schema fields to tableMeta when available
    if expected_all_keys:
        table_meta["expectedColumnKeys"] = expected_all_keys
        table_meta["matchedColumnKeys"] = matched_keys_clean
        table_meta["valueColumnKeys"] = value_column_keys
        table_meta["missingExpectedColumnKeys"] = missing_expected_required

    # T-6m: value mapping diagnostics
    if expected_all_keys and canonical_rows:
        _n = len(canonical_rows)
        _filled_keys = [
            k for k in expected_all_keys
            if sum(1 for r in canonical_rows if str(r.get(k) or "").strip()) > 0
        ]
        _missing_keys = [k for k in expected_all_keys if k not in _filled_keys]
        _total_cells = _n * len(expected_all_keys)
        _filled_cells = sum(
            sum(1 for k in expected_all_keys if str(r.get(k) or "").strip())
            for r in canonical_rows
        )
        table_meta["expectedValueFillRate"] = round(_filled_cells / _total_cells * 100, 1) if _total_cells else 0.0
        table_meta["expectedFilledKeys"] = _filled_keys
        table_meta["expectedMissingKeys"] = _missing_keys
        table_meta["valueMappingWarnings"] = []

        # T-8b: Add OCR source missing warnings for required columns where
        # every row is empty because the OCR source is absent or unclear.
        # Distinguishes "not extracted yet" from "no OCR source available."
        # Guard: column must be in required (not just optional), and must be
        # ALL-missing across every row in this table.
        _t8b_required_set = set(expected_columns.get("required") or [])
        for _t8b_key, _t8b_label, _t8b_reason in [
            (
                "insuranceCode",
                "보험No",
                "OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지",
            ),
        ]:
            if _t8b_key in _t8b_required_set and _t8b_key in _missing_keys:
                table_meta["valueMappingWarnings"].append(
                    f"{_t8b_key}:ocr_source_missing:{_t8b_label} {_t8b_reason}"
                )

    return {
        "tableRows": canonical_rows,
        "tableMeta": table_meta,
        "tableRowsDebug": {
            "enabled": True,
            "source": debug_source,
            "rowCandidateCount": len(table_items),
            "generatedRowCount": len(canonical_rows),
            "columnFillCounts": col_fill,
            "rejectedRows": 0,
            "notes": [],
            # T-6e-fix
            "expectedColumnsApplied": bool(expected_all_keys),
            "expectedColumnKeys": expected_all_keys,
            "matchedColumnKeys": matched_keys_clean,
            "valueColumnKeys": value_column_keys,
            "missingExpectedColumnKeys": missing_expected_required,
            "displaySchemaColumnKeys": expected_all_keys or actual_columns,
            "columnSchemaSource": "expected_columns" if expected_all_keys else "actual_detected",
        },
    }


def _normalization_record(
    field: str,
    field_type: str,
    role: str,
    raw: str,
    normalized: str,
    rules: list[dict[str, str]],
    address_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "field": field,
        "fieldType": field_type,
        "role": role,
        "rawValue": raw,
        "normalizedValue": normalized,
        "valueChanged": False,
        "appliedRules": rules,
    }
    if address_analysis:
        record["addressSimilarityAnalysis"] = address_analysis
    return record


def _add_norm_rule(rules: list[dict[str, str]], rule: str, before: str, after: str, confidence: str, reason: str) -> None:
    if before == after:
        return
    rules.append({"rule": rule, "before": before, "after": after, "confidence": confidence, "reason": reason})


def _normalize_invoice_biz_number(value: str) -> tuple[str, list[dict[str, str]]]:
    raw = _clean_value(value)
    rules: list[dict[str, str]] = []
    digits = re.sub(r"\D", "", _canonical_digits(raw))
    if len(digits) == 10:
        normalized = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        _add_norm_rule(rules, "biz_number_hyphen_format", raw, normalized, "safe", "business_number_field_only")
        return normalized, rules
    return raw, rules


def _normalize_invoice_company_name(value: str) -> tuple[str, list[dict[str, str]]]:
    raw = _clean_value(value)
    rules: list[dict[str, str]] = []
    normalized = re.sub(r"\s+", " ", raw).strip()
    _add_norm_rule(rules, "company_trim_spacing", raw, normalized, "safe", "company_field_spacing")
    before = normalized
    normalized = re.sub(r"\s+", "", normalized)
    _add_norm_rule(rules, "company_internal_space_compare", before, normalized, "safe_compare", "company_field_compare_value")
    before = normalized
    normalized = re.sub(r"\(\s*\uc8fc\s*$", "(\uc8fc)", normalized)
    normalized = re.sub(r"\(\s*\uc8fc\s*\)", "(\uc8fc)", normalized)
    normalized = re.sub(r"\uc8fc\s*\)", "\uc8fc)", normalized)
    _add_norm_rule(rules, "company_parenthesis_joo", before, normalized, "safe", "clear_corporation_suffix_parenthesis")
    before = normalized
    normalized = re.sub(r"^\uc8fc\uc2dd\ud68c\uc0ac(?=\S)", "\uc8fc\uc2dd\ud68c\uc0ac ", normalized)
    _add_norm_rule(rules, "company_jusik_spacing", before, normalized, "safe_compare", "company_field_readability")
    before = normalized
    normalized = normalized.replace("\uc8fc\uc2dd\ud76c\uc0ac", "\uc8fc\uc2dd\ud68c\uc0ac")
    _add_norm_rule(rules, "company_ocr_confusion_jusik", before, normalized, "debug_only", "company_field_ocr_confusion")
    if re.search(r"\ubc31\uacc4\uc57d\ud1b5|\uc601\ud48d\ud45c\uc9c0\uc815", normalized):
        rules.append(
            {
                "rule": "skipped_low_confidence_company_correction",
                "before": normalized,
                "after": normalized,
                "confidence": "debug_only",
                "reason": "specific_company_like_ocr_confusion_not_applied",
            }
        )
    return normalized, rules


def _normalize_invoice_representative(value: str) -> tuple[str, list[dict[str, str]]]:
    raw = _clean_value(value)
    rules: list[dict[str, str]] = []
    normalized = re.sub(r"\s+", " ", raw).strip()
    _add_norm_rule(rules, "representative_trim_spacing", raw, normalized, "safe", "representative_field_spacing")
    before = normalized
    normalized = re.sub(r"\s*[,/]\s*", ", ", normalized)
    _add_norm_rule(rules, "representative_separator_spacing", before, normalized, "safe", "multiple_representative_separator")
    if re.fullmatch(r"[\uac00-\ud7a3]{2,4}", normalized or ""):
        rules.append(
            {
                "rule": "skipped_single_character_name_correction",
                "before": normalized,
                "after": normalized,
                "confidence": "debug_only",
                "reason": "person_name_ocr_correction_risk",
            }
        )
    if re.fullmatch(r"[A-Z][A-Z\s.]{3,30}", normalized or ""):
        rules.append(
            {
                "rule": "skipped_english_name_spelling_correction",
                "before": normalized,
                "after": normalized,
                "confidence": "debug_only",
                "reason": "english_name_ocr_spelling_risk",
            }
        )
    return normalized, rules


_CITY_PREFIX_RE = re.compile(
    r"^(?:서울특별시|서울특발시|서울|경기도|인천광역시|인천|부산광역시|부산|"
    r"대구광역시|대구|광주광역시|광주|대전광역시|대전|울산광역시|울산|"
    r"세종특별자치시|세종|강원도|강원|충청북도|충북|충청남도|충남|"
    r"전라북도|전북|전라남도|전남|경상북도|경북|경상남도|경남|제주특별자치도|제주)"
)


def _classify_address_partial_status(normalized: str) -> dict[str, Any]:
    """Structural analysis of normalized OCR address (no GT required).

    Returns addressSimilarityStatus indicating how structurally complete the
    address appears, helping downstream debug display distinguish genuine
    mismatches from prefix/tail truncations.
    """
    v = (normalized or "").strip()
    compact = re.sub(r"\s+", "", v)
    if not compact:
        return {"addressSimilarityStatus": "fragment_only", "matchedTokenTypes": [], "appearsTruncated": False, "partialReason": "empty value"}

    has_postal = bool(re.match(r"^\(\d{5}\)", v))
    has_city = bool(_CITY_PREFIX_RE.match(compact))
    has_district = bool(re.search(r"[가-힣]{1,8}(?:시|군|구)", compact))
    has_subdistrict = bool(re.search(r"[가-힣]{1,8}(?:읍|면|동|리)", compact))
    has_road = bool(re.search(r"[가-힣]{2,16}(?:로|길)", compact))
    has_unit = bool(re.search(r"\d+(?:층|호)|번지", compact))
    has_bldg_paren = bool(re.search(r"\([가-힣A-Za-z0-9\s]{2,18}\)", v))
    appears_truncated = bool(
        re.search(r",\s*$", v)
        or (v.count("(") > v.count(")"))
        or re.search(r"(?:로|길)\s*\d+(?:-\d+)?\s*$", v.rstrip(","))
    )

    token_types: list[str] = []
    if has_postal:
        token_types.append("postal_code")
    if has_city:
        token_types.append("city_prefix")
    if has_district:
        token_types.append("district")
    if has_subdistrict:
        token_types.append("subdistrict")
    if has_road:
        token_types.append("road")
    if has_unit:
        token_types.append("unit_detail")
    if has_bldg_paren:
        token_types.append("building_parenthesis")

    has_prefix = has_city or has_postal
    has_core = has_subdistrict or has_road

    if not has_prefix and has_core:
        status = "prefix_missing"
        reason = "city/region prefix absent; starts from subdistrict or road level"
    elif has_prefix and appears_truncated:
        status = "tail_truncated"
        reason = "city prefix present but address appears truncated"
    elif has_prefix and has_core:
        status = "complete"
        reason = "address appears structurally complete"
    else:
        status = "fragment_only"
        reason = "only minimal address fragment detected"

    return {
        "addressSimilarityStatus": status,
        "matchedTokenTypes": token_types,
        "appearsTruncated": appears_truncated,
        "partialReason": reason,
    }


def _space_invoice_address(value: str) -> str:
    result = value
    result = re.sub(r"^\(?(\d{5})\)?\s*", r"(\1) ", result)
    result = re.sub(r"(\uc11c\uc6b8\ud2b9\ubcc4\uc2dc)(?=[\uac00-\ud7a3])", r"\1 ", result)
    result = re.sub(r"(\uc11c\uc6b8)(?!\ud2b9)(?=[\uac00-\ud7a3])", r"\1 ", result)
    result = re.sub(r"([\uac00-\ud7a3]{1,8}\uad6c)(?=[\uac00-\ud7a3])", r"\1 ", result)
    result = re.sub(r"([\uac00-\ud7a3]{1,16}\ub85c\d+\uae38)(\d)", r"\1 \2", result)
    result = re.sub(r"([\uac00-\ud7a3]{1,16}(?:\ub85c|\uae38))(\d)", r"\1 \2", result)
    result = re.sub(r"([\uac00-\ud7a3]{1,16}\ub85c) (\d+\uae38)", r"\1\2", result)
    result = re.sub(r",\s*", ", ", result)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def _normalize_invoice_address(value: str) -> tuple[str, list[dict[str, str]]]:
    raw = _clean_value(value)
    rules: list[dict[str, str]] = []
    normalized = re.sub(r"\s+", " ", raw).strip()
    _add_norm_rule(rules, "address_trim_spacing", raw, normalized, "safe", "address_field_spacing")
    for before_text in ("\uc11c\uc6b8\ud2b9\ubc95\uc2dc", "\uc11c\uc6b8\ud2b9\ubc1c\uc2dc", "\uc11c\uc6b8\ub85d\ubcc4\uc2dc", "\uc11c\uc6b8\ud2b9\ubc8c\uc2dc"):
        before = normalized
        normalized = normalized.replace(before_text, "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc")
        _add_norm_rule(rules, "address_ocr_city_correction", before, normalized, "safe", "address_field_only_city_ocr_correction")
    before = normalized
    normalized = normalized.replace("\ucfe0\ub85c\uad6c", "\uad6c\ub85c\uad6c")
    _add_norm_rule(rules, "address_ocr_district_correction", before, normalized, "safe", "address_field_only_district_ocr_correction")
    before = normalized
    normalized = _space_invoice_address(normalized)
    _add_norm_rule(rules, "address_spacing_compare", before, normalized, "safe_compare", "address_field_comparison_spacing")
    before = normalized
    if normalized.count("(") == normalized.count(")") + 1 and re.search(r"\([\uac00-\ud7a3A-Za-z0-9\s]+$", normalized):
        normalized += ")"
    _add_norm_rule(rules, "address_missing_closing_parenthesis", before, normalized, "safe_compare", "clear_missing_address_parenthesis")
    return normalized, rules


def _normalize_invoice_party_fields(fields: dict[str, Any]) -> dict[str, Any]:
    specs = [
        ("supplierCompany", "company", "supplier", _normalize_invoice_company_name),
        ("supplierBizNumber", "business_number", "supplier", _normalize_invoice_biz_number),
        ("supplierRepresentative", "representative", "supplier", _normalize_invoice_representative),
        ("supplierAddress", "address", "supplier", _normalize_invoice_address),
        ("buyerCompany", "company", "buyer", _normalize_invoice_company_name),
        ("buyerBizNumber", "business_number", "buyer", _normalize_invoice_biz_number),
        ("buyerRepresentative", "representative", "buyer", _normalize_invoice_representative),
        ("buyerAddress", "address", "buyer", _normalize_invoice_address),
    ]
    field_records: list[dict[str, Any]] = []
    normalized_fields: dict[str, str] = {}
    for field, field_type, role, normalizer in specs:
        raw = str(fields.get(field) or "")
        normalized, rules = normalizer(raw)
        normalized_fields[field] = normalized
        if raw or rules:
            addr_analysis: dict[str, Any] | None = None
            if field_type == "address" and raw:
                addr_analysis = _classify_address_partial_status(normalized)
                partial_status = addr_analysis.get("addressSimilarityStatus", "")
                if partial_status in ("prefix_missing", "tail_truncated", "fragment_only"):
                    rules = list(rules) + [{
                        "rule": f"address_partial_{partial_status}",
                        "before": normalized,
                        "after": normalized,
                        "confidence": "debug_only",
                        "reason": addr_analysis.get("partialReason", f"address structure: {partial_status}"),
                    }]
            field_records.append(_normalization_record(field, field_type, role, raw, normalized, rules, addr_analysis))
    return {
        "strategy": "debug_only_raw_fields_preserved",
        "valueDirectChange": False,
        "normalizedFields": normalized_fields,
        "fields": field_records,
    }


def extract_invoice_statement_fields(
    ocr_lines_raw: list[tuple],
    debug: dict[str, Any] | None = None,
    table_expected_columns: dict[str, list[str]] | None = None,
    table_bounds: dict[str, float] | None = None,
    column_guides: list[float] | None = None,
) -> dict[str, str]:
    lines = [line for raw in ocr_lines_raw if (line := _line_from_raw(raw))]
    fields = {
        "supplierCompany": "",
        "supplierBizNumber": "",
        "supplierRepresentative": "",
        "supplierAddress": "",
        "buyerCompany": "",
        "buyerBizNumber": "",
        "buyerRepresentative": "",
        "buyerAddress": "",
        "issueDate": "",
        "supplyAmount": "",
        "taxAmount": "",
        "totalAmount": "",
        "subtotal": "",
        "cumulativeAmount": "",
        "previousBalance": "",
        "transactionAmount": "",
        "cumulativeBalance": "",
        "totalQuantity": "",
        "tableDetected": "N",
        "rowCount": "",
        "firstRowPreview": "",
    }
    if not lines:
        return fields

    page_w = max(line.x + line.w for line in lines)
    page_h = max(line.y + line.h for line in lines)
    table_header_y = _find_table_header_y(lines, page_h)
    header_limit_y = min((table_header_y - page_h * 0.02) if table_header_y else page_h * 0.62, page_h * 0.68)
    header_limit_y = max(header_limit_y, page_h * 0.22)
    header_lines = [line for line in lines if line.cy <= header_limit_y]

    supplier, buyer, party_debug = _extract_party_fields(header_lines, lines, page_w, page_h, header_limit_y)
    amount_debug: dict[str, Any] = {}
    amounts = _extract_amount_fields(lines, page_h, table_header_y, debug=amount_debug)
    summary_fields, summary_fields_debug = _extract_profile_summary_fields(lines, page_h, table_header_y)
    table = _detect_table(
        lines, page_h, table_header_y,
        expected_columns=table_expected_columns,
        table_bounds=table_bounds,
        column_guides=column_guides,
    )
    full_text = "\n".join(line.text for line in lines)
    tdbg = table.get("tableDebug") or {}
    _matched_keys = tdbg.get("matchedHeaders", [])
    canonical = _build_canonical_table_rows(
        table.get("tableRows") or table.get("items") or [],
        expected_columns=table_expected_columns,
        matched_column_keys=_matched_keys,
    )

    # T-6e: propagate extraction metadata into tableMeta
    canonical["tableMeta"]["extractionSource"] = tdbg.get("extractionSource", "")
    canonical["tableMeta"]["expectedColumnsUsed"] = tdbg.get("expectedColumnsUsed", False)
    canonical["tableMeta"]["tableBoundsUsed"] = tdbg.get("tableBoundsUsed", False)
    # T-6j-fix: expose colGuides debug in tableMeta
    canonical["tableMeta"]["columnGuidesReceived"] = tdbg.get("columnGuidesReceived", False)
    canonical["tableMeta"]["columnGuidesUsed"] = bool(tdbg.get("columnGuidesReceived") and tdbg.get("extractionSource") == "template_colguides_expected_columns")
    canonical["tableMeta"]["columnGuidesCount"] = tdbg.get("columnGuidesCount", 0)
    canonical["tableMeta"]["tableBoundsSource"] = tdbg.get("tableBoundsSource", "")
    # T-6j-fix-2pdf: row filter debug in tableMeta
    canonical["tableMeta"]["columnGuidesUsedAttempted"] = tdbg.get("columnGuidesUsedAttempted", False)
    canonical["tableMeta"]["rowCandidateCountBeforeFilter"] = tdbg.get("rowCandidateCountBeforeFilter")
    canonical["tableMeta"]["rowCandidateCountAfterFilter"] = tdbg.get("rowCandidateCountAfterFilter")
    # T-6n: OP anchor reconstruction debug in tableMeta
    canonical["tableMeta"]["opAnchorReconstructionAttempted"] = tdbg.get("opAnchorReconstructionAttempted", False)
    canonical["tableMeta"]["opAnchorCount"] = tdbg.get("opAnchorCount")
    canonical["tableMeta"]["opAnchorRowsBuilt"] = tdbg.get("opAnchorRowsBuilt")
    canonical["tableMeta"]["reconstructedRowCount"] = tdbg.get("reconstructedRowCount")
    canonical["tableMeta"]["previousRowCount"] = tdbg.get("previousRowCount")

    # T-7a: For single-row tables, push document-level amounts into the row
    # when the row-level column is empty AND the expected columns include it.
    # Guard: rowCount==1, doc-level amount is non-empty, row-level is empty.
    # Safe for single-item invoices where doc total == row total.
    if (
        table_expected_columns
        and canonical["tableMeta"].get("rowCount") == 1
        and canonical["tableRows"]
    ):
        _t7a_row = canonical["tableRows"][0]
        _t7a_tec_all = set(
            (table_expected_columns.get("required") or [])
            + (table_expected_columns.get("optional") or [])
        )
        _t7a_pushdown_warnings: list[str] = []
        for _t7a_key, _t7a_src in [
            ("taxAmount", "taxAmount"),
            ("supplyAmount", "supplyAmount"),
            ("totalAmount", "totalAmount"),
        ]:
            if (
                _t7a_key in _t7a_tec_all
                and not _t7a_row.get(_t7a_key)
                and amounts.get(_t7a_src)
            ):
                _t7a_row[_t7a_key] = amounts[_t7a_src]
                _t7a_pushdown_warnings.append(f"{_t7a_key}=doc_level_pushdown")
        if _t7a_pushdown_warnings:
            canonical["tableMeta"].setdefault("valueMappingWarnings", []).extend(_t7a_pushdown_warnings)

    # T-8a: Multiline column layout post-processing for legacy_text_items tables.
    # Reconnects itemCode/unitPrice/amount from separate OCR blocks to existing rows.
    # Guard: extractionSource==legacy_text_items, rowCount>=2, expected cols present.
    if (
        table_expected_columns
        and canonical["tableMeta"].get("extractionSource") == "legacy_text_items"
        and canonical["tableMeta"].get("rowCount", 0) >= 2
    ):
        _t8a = _postprocess_multiline_column_layout(
            lines,
            canonical["tableRows"],
            table_expected_columns,
        )
        if _t8a.get("applied"):
            canonical["tableMeta"]["multilineLayoutMappingApplied"] = True
            canonical["tableMeta"]["multilineLayoutFilledKeys"] = _t8a.get("filledKeys", [])
            canonical["tableMeta"]["multilineLayoutCandidateCounts"] = _t8a.get("candidateCounts", {})
            # Re-compute fill stats after rows were enriched
            _t8a_all_keys = list(dict.fromkeys(
                (table_expected_columns.get("required") or [])
                + (table_expected_columns.get("optional") or [])
            ))
            if _t8a_all_keys and canonical["tableRows"]:
                _t8a_n = len(canonical["tableRows"])
                _t8a_filled_keys = [
                    k for k in _t8a_all_keys
                    if sum(1 for r in canonical["tableRows"] if str(r.get(k) or "").strip()) > 0
                ]
                _t8a_missing_keys = [k for k in _t8a_all_keys if k not in _t8a_filled_keys]
                _t8a_total = _t8a_n * len(_t8a_all_keys)
                _t8a_filled_cells = sum(
                    sum(1 for k in _t8a_all_keys if str(r.get(k) or "").strip())
                    for r in canonical["tableRows"]
                )
                canonical["tableMeta"]["expectedValueFillRate"] = (
                    round(_t8a_filled_cells / _t8a_total * 100, 1) if _t8a_total else 0.0
                )
                canonical["tableMeta"]["expectedFilledKeys"] = _t8a_filled_keys
                canonical["tableMeta"]["expectedMissingKeys"] = _t8a_missing_keys
        if _t8a.get("warnings"):
            canonical["tableMeta"].setdefault("valueMappingWarnings", []).extend(_t8a["warnings"])

    fields.update(
        {
            "supplierCompany": supplier["company"],
            "supplierBizNumber": supplier["bizNumber"],
            "supplierRepresentative": supplier["representative"],
            "supplierAddress": supplier["address"],
            "buyerCompany": buyer["company"],
            "buyerBizNumber": buyer["bizNumber"],
            "buyerRepresentative": buyer["representative"],
            "buyerAddress": buyer["address"],
            "issueDate": _normalize_date(full_text),
            **amounts,
            **summary_fields,
            **table,
            "tableRows": canonical["tableRows"],
            "tableMeta": canonical["tableMeta"],
        }
    )

    if debug is not None:
        normalization_debug = _normalize_invoice_party_fields(fields)
        debug["invoice_statement"] = {
            "page_size": [round(page_w), round(page_h)],
            "table_header_y": round(table_header_y) if table_header_y else None,
            "header_limit_y": round(header_limit_y),
            "header_line_count": len(header_lines),
            "party_candidates": {
                **party_debug,
                "companies": [(round(x), round(y), value) for x, y, value in party_debug["companies"]],
            },
            "supplier_nonempty": [key for key, value in supplier.items() if value],
            "buyer_nonempty": [key for key, value in buyer.items() if value],
            "amount_nonempty": [key for key, value in amounts.items() if value],
            "summaryFields_nonempty": [key for key, value in summary_fields.items() if value],
            "summaryFieldsMapping": summary_fields_debug,
            "amount_label_window": amount_debug.get("amount_label_window", {}),
            "amount_total_evidence": amount_debug.get("amount_total_evidence", {}),
            "amount_summary_blocks": amount_debug.get("amount_summary_blocks", {}),
            "amount_summary_triple": amount_debug.get("amount_summary_triple", {}),
            "amount_pair_checksum": amount_debug.get("amount_pair_checksum", {}),
            "totalSuppressionDecision": amount_debug.get("totalSuppressionDecision", {}),
            "suppressedTotalCandidates": amount_debug.get("suppressedTotalCandidates", []),
            "normalization": normalization_debug,
            "addressContinuation": party_debug.get("addressContinuation", {}),
            "supplierCompanyAnchorFallback": party_debug.get("supplierCompanyAnchorFallback", {}),
            "table": table,
            "tableRowsDebug": canonical["tableRowsDebug"],
        }

    return fields
