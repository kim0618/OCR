import base64
import io
import os
import re

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
import json
import uuid
from datetime import datetime

import cv2
import fitz  # PyMuPDF
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image

from preprocess import preprocess, preprocess_for_ocr, enhance_contrast, sharpen, detect_document, deskew, detect_orientation
from amount_extractor import (
    extract_amount_candidates,
    select_best_total_amount,
    merge_candidates,
    synthesize_supply_vat_totals,
)
from document_classifier import classify_document
from utils.text_normalize import _clean_number, _clean_inline_field_value
from utils.rows import _row_text, _single_line_rows, _is_merchant_notice_row, _group_rows
from utils.io_json import _load_json, _save_json
from extractors.common import _bad_top_text_candidate, _extract_until_next_label
from extractors.business_number import _validate_biz_number, _extract_biz_number
from extractors.phone import (
    _normalize_phone_digits,
    _valid_phone_digits,
    _valid_labeled_phone_digits,
    _extract_phone_candidate,
)
from extractors.representative import (
    _extract_rep_phone_pair,
    _is_bad_representative_candidate,
    _extract_company_rep_from_slash,
)
from utils.regex_patterns import (
    _PHONE_RE,
    _ADDR_START_RE, _NEXT_LABEL_RE, _FIELD_NOISE_RE,
    _COMPANY_SUFFIX_HINT_RE,
    _CONVENIENCE_STORE_NAME_RE, _COMPANY_SLOGAN_RE,
    _PERSON_LIKE_NAME_RE, _REPRESENTATIVE_SURNAME_RE,
    _ADDRESS_CUT_RE, _ADDRESS_CORE_TOKEN_RE, _ADDRESS_STORE_NOISE_RE,
    _LABEL_ONLY_RE, _ADDRESS_CONTINUATION_RE,
    _ADDRESS_BROAD_ONLY_RE, _ADDRESS_TRAILING_NOISE_RE,
)

app = FastAPI(title="MySuit OCR Server")


def _parse_ocr_lines(result):
    """PaddleOCR 3.x 결과를 (pts, text, conf) 리스트로 정규화"""
    lines = []
    if not result or not result[0]:
        return lines
    r0 = result[0]
    if isinstance(r0, dict):
        for text, score, poly in zip(r0.get("rec_texts", []), r0.get("rec_scores", []), r0.get("rec_polys", [])):
            pts = poly.tolist()
            lines.append((pts, str(text).strip(), float(score)))
    else:
        for line in r0:
            pts = line[0]
            lines.append((pts, str(line[1][0]).strip(), float(line[1][1])))
    return lines




def _parse_amounts(s: str, keyword_context: bool = False) -> list:
    cleaned = _clean_number(s)

    # 1순위: 천단위 콤마 정형식 (33,000 / 1,234,567)
    matches = re.findall(r'\d{1,3}(?:,\d{3})+', cleaned)
    result = [m for m in matches if 100 <= int(m.replace(',', '')) <= 100_000_000]
    if result:
        return result

    # 2순위: 키워드 근처에서만 — 콤마 뒤 자리수 부족 보완 (35,0 → 35,000)
    if keyword_context:
        partial = re.findall(r'\d{1,3},\d{1,2}(?!\d)', cleaned)
        for p in partial:
            num, dec = p.split(',')
            completed = int(num) * 1000 + int(dec) * (10 ** (3 - len(dec)))
            if 100 <= completed <= 100_000_000:
                result.append(f"{completed:,}")
        if result:
            return result

        # 3순위: 콤마 없는 5~7자리 정수 (11000, 35000 등)
        bare = re.findall(r'(?<!\d)\d{5,7}(?!\d)', cleaned)
        result = [f"{int(m):,}" for m in bare if 1000 <= int(m) <= 100_000_000]

    return result












def _extract_address_fragment(text: str) -> str:
    match = _ADDR_START_RE.search(text or "")
    if not match:
        return ""
    value = text[match.start():]
    value = _ADDRESS_CUT_RE.split(value, maxsplit=1)[0]
    value = _PHONE_RE.split(value, maxsplit=1)[0]
    value = re.split(r'\s*\d{4}[./-]\d{1,2}[./-]\d{1,2}', value, maxsplit=1)[0]
    value = re.sub(r'\d{2,3}[-\s.]?\d{2}[-\s.]?\d{5}.*$', '', value).strip()
    return _clean_inline_field_value(value)


def _is_bad_company_candidate(text: str, row_text: str = "") -> bool:
    candidate = _clean_inline_field_value(text)
    compact = re.sub(r'\s+', '', candidate)
    row_compact = re.sub(r'\s+', '', row_text or '')
    has_label = bool(re.search(r'상호|가맹점명|회사명|업체명|매장명|브랜드명', row_compact))
    short_hangul_name = bool(re.fullmatch(r'[가-힣]{3,4}', compact))
    short_standalone_ok = (
        short_hangul_name
        and not has_label
        and not re.search(r'\d', row_compact)
        and not _FIELD_NOISE_RE.search(row_compact)
        and not _is_merchant_notice_row(row_text or "")
    )
    digits = sum(ch.isdigit() for ch in compact)
    amount_like_count = len(re.findall(r'\d{1,3}(?:,\d{3})+|\d{4,}', row_text or ""))

    if not compact:
        return True
    if _LABEL_ONLY_RE.fullmatch(compact):
        return True
    if _COMPANY_SLOGAN_RE.search(compact):
        return True
    if _bad_top_text_candidate(compact) or _FIELD_NOISE_RE.search(compact):
        return True
    if re.search(r'체크카드|신용매출|귀하', compact, re.I):
        return True
    if re.search(r'품명|상품명|상품|품목|수량|단가|금액|합계|승인|전표|TID|VAN|CAT|가맹', compact, re.I):
        return True
    if re.search(r'유통단지|호계동|오전동|고천동|동안구|의왕시|안양시|경기도|경기', compact):
        return True
    if re.search(r'다른경우|실제와|가맹점주소가|전기작업|작업지시|직원|식지|재발행|안내문|설명문구|예시문구|작성문구', compact, re.I):
        return True
    if re.search(r'표시|입니다|과세|면세|품목', compact):
        return True
    if re.search(r'응원합니다|감사합니다|유치|박람회', compact):
        return True
    if re.fullmatch(r'[가-힣]{2,8}(?:시|군|구|동|로|길|층|호|번지)', compact) and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if _ADDRESS_CORE_TOKEN_RE.search(compact) and _ADDR_START_RE.search(compact) and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if re.search(r'\d.*(?:\uC0AC\uC625|\uBE4C\uB529)|(?:\uC0AC\uC625|\uBE4C\uB529)\)?$', compact) and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if digits > 1 and not _CONVENIENCE_STORE_NAME_RE.search(compact):
        return True
    if len(compact) <= 2 and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if len(compact) <= 4 and not short_standalone_ok and not has_label and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if _PERSON_LIKE_NAME_RE.fullmatch(compact) and _REPRESENTATIVE_SURNAME_RE.search(compact) and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if _PERSON_LIKE_NAME_RE.fullmatch(compact) and not short_standalone_ok and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if _FIELD_NOISE_RE.search(row_compact) and not has_label and not _CONVENIENCE_STORE_NAME_RE.search(compact):
        return True
    if amount_like_count >= 2 and not has_label and not re.search(r'사업자|등록번호|주소|전화|TEL|Tel|tel', row_text or "", re.I):
        return True
    return False


def _clean_address_candidate(text: str) -> str:
    value = _clean_inline_field_value(text)
    if not value:
        return ""
    value = _ADDRESS_CUT_RE.split(value, maxsplit=1)[0]
    value = _PHONE_RE.split(value, maxsplit=1)[0]
    value = re.split(r'\s*\d{4}[./-]\d{1,2}[./-]\d{1,2}', value, maxsplit=1)[0]
    value = re.sub(r'\d{2,3}[-\s.]?\d{2}[-\s.]?\d{5}.*$', '', value).strip()
    value = _ADDRESS_TRAILING_NOISE_RE.split(value, maxsplit=1)[0]
    value = re.sub(r'\s+[일업전상공]$', '', value).strip()
    value = _clean_inline_field_value(value)
    has_region = bool(_ADDR_START_RE.search(value))
    if not has_region:
        return ""
    if len(value) < 6:
        return ""
    tail = value[2:]
    if not _ADDRESS_CORE_TOKEN_RE.search(tail):
        return ""
    if _ADDRESS_STORE_NOISE_RE.search(value) and not _ADDRESS_CORE_TOKEN_RE.search(tail):
        return ""
    value = re.sub(r'\s+[A-Z]{2,}\d+[A-Z0-9-]*$', '', value).strip()
    value = re.sub(r'\s+[A-Za-z]{2,}\d{2,}[A-Za-z0-9-]*$', '', value).strip()
    value = re.sub(r'(?<=\d)\s+[가-힣]{2,}(?:조명|전기|철물|공구|볼트|약국|집|툴)?$', '', value).strip()
    return value


def _address_needs_continuation(value: str) -> bool:
    compact = re.sub(r'\s+', ' ', value or '').strip()
    if not compact:
        return False
    if compact.count("(") > compact.count(")"):
        return True
    if _ADDRESS_BROAD_ONLY_RE.fullmatch(compact):
        return True
    return not bool(re.search(r'로|길|동|읍|면|리|층|호|번지|\d', compact[2:]))


def _address_continuation_candidate(text: str) -> str:
    raw = _ADDRESS_CUT_RE.split(text or "", maxsplit=1)[0]
    raw = _PHONE_RE.split(raw, maxsplit=1)[0]
    raw = _ADDRESS_TRAILING_NOISE_RE.split(raw, maxsplit=1)[0]
    raw = _clean_inline_field_value(raw)
    if not raw or _ADDR_START_RE.search(raw):
        return ""
    if _bad_top_text_candidate(raw) or _FIELD_NOISE_RE.search(raw):
        return ""
    if re.fullmatch(r'[가-힣A-Za-z0-9\s]{1,12}\)', raw):
        return raw
    if re.fullmatch(r'(?:\d+\s*)?층|[가-힣A-Za-z0-9(),.\-\s]{1,14}(?:동|층|호)', raw):
        return raw
    match = _ADDRESS_CONTINUATION_RE.search(raw)
    if not match:
        return ""
    value = _clean_inline_field_value(match.group(0))
    if len(value) < 3:
        return ""
    return value


def _maybe_set_address(target: dict, candidate: str) -> None:
    if not candidate:
        return
    current = target.get("주소", "")
    if not current:
        target["주소"] = candidate
        return
    if _address_needs_continuation(current) and len(candidate) > len(current):
        target["주소"] = candidate


def _repair_remaining_top_fields_from_text_lines(target: dict, text_lines: list[str]) -> None:
    """Final tiny repair for cases where OCR raw exists but bbox row grouping split it."""
    if not text_lines:
        return

    if not target.get("회사명"):
        for line in text_lines:
            for token in re.findall(r'[가-힣A-Za-z0-9()]{2,}', line or ""):
                candidate = _normalize_company_candidate(token)
                if _CONVENIENCE_STORE_NAME_RE.search(candidate) and not _is_bad_company_candidate(candidate, token):
                    target["회사명"] = candidate
                    break
            if target.get("회사명"):
                break

    if not target.get("주소"):
        for idx, line in enumerate(text_lines):
            line_clean = _clean_inline_field_value(line)
            addr = _clean_address_candidate(_extract_address_fragment(line_clean) or line_clean)
            if not addr and idx + 1 < len(text_lines):
                combined = _clean_address_candidate(f"{line_clean} {text_lines[idx + 1]}")
                if combined:
                    addr = combined
            if addr and _address_needs_continuation(addr) and idx + 1 < len(text_lines):
                cont = _address_continuation_candidate(text_lines[idx + 1])
                combined = _clean_address_candidate(f"{addr} {cont}") if cont else ""
                if combined:
                    addr = combined
            if addr:
                target["주소"] = addr
                break

    current_addr = target.get("주소", "")
    if current_addr and not _ADDR_START_RE.search(current_addr):
        current_len = len(re.sub(r'\s+', '', current_addr))
        for idx, line in enumerate(text_lines):
            line_clean = _clean_inline_field_value(line)
            addr = _clean_address_candidate(_extract_address_fragment(line_clean))
            if not addr or not _ADDR_START_RE.search(addr):
                continue
            if _address_needs_continuation(addr) and idx + 1 < len(text_lines):
                cont = _address_continuation_candidate(text_lines[idx + 1])
                combined = _clean_address_candidate(f"{addr} {cont}") if cont else ""
                if combined:
                    addr = combined
            if len(re.sub(r'\s+', '', addr)) >= current_len:
                target["주소"] = addr
                break

    current_addr = target.get("주소", "")
    if current_addr and _ADDR_START_RE.search(current_addr):
        current_len = len(re.sub(r'\s+', '', current_addr))
        if current_len < 14:
            for idx, line in enumerate(text_lines):
                line_clean = _clean_inline_field_value(line)
                addr = _clean_address_candidate(_extract_address_fragment(line_clean))
                if not addr or not _ADDR_START_RE.search(addr):
                    continue
                if _address_needs_continuation(addr) and idx + 1 < len(text_lines):
                    cont = _address_continuation_candidate(text_lines[idx + 1])
                    combined = _clean_address_candidate(f"{addr} {cont}") if cont else ""
                    if combined:
                        addr = combined
                addr_len = len(re.sub(r'\s+', '', addr))
                if addr_len >= current_len + 6:
                    target["주소"] = addr
                    break

    if target.get("주소") and _address_needs_continuation(target.get("주소", "")):
        current = target.get("주소", "")
        current_compact = re.sub(r'\s+', '', current)
        for idx, line in enumerate(text_lines[:-1]):
            line_clean = _clean_inline_field_value(line)
            line_addr = _clean_address_candidate(line_clean)
            if not line_addr:
                continue
            line_compact = re.sub(r'\s+', '', line_addr)
            if line_compact != current_compact:
                continue
            cont = _address_continuation_candidate(text_lines[idx + 1])
            combined = _clean_address_candidate(f"{current} {cont}") if cont else ""
            if combined:
                target["주소"] = combined
                break

    if not target.get("대표자"):
        for idx, line in enumerate(text_lines):
            if _bad_top_text_candidate(line):
                continue
            rest = _extract_until_next_label(line, r'(?:대표자명|대표자|대표|성명)\s*[:;]?')
            if 1 <= len(rest) <= 20 and not _is_bad_representative_candidate(rest, line):
                target["대표자"] = rest
                break
            if re.search(r'대표자명|대표자|대표|성명', re.sub(r'\s+', '', line)) and idx + 1 < len(text_lines):
                next_rep = _clean_inline_field_value(text_lines[idx + 1])
                if not _is_bad_representative_candidate(next_rep, line):
                    target["대표자"] = next_rep
                    break


def _extract_company_near_biz(text: str) -> str:
    if not (_ADDR_START_RE.search(text or "") or re.search(r'TEL|Tel|tel|전화', text or "")):
        return ""

    biz = re.search(r'[1-9]\d{2}[-\s.]?\d{2}[-\s.]?\d{5}', text or "")
    if not biz:
        return ""

    before = _clean_inline_field_value((text or "")[:biz.start()])
    before_tokens = [
        token for token in re.findall(r'[가-힣A-Za-z0-9()]{2,}', before)
        if not _bad_top_text_candidate(token)
    ]
    if before_tokens and len(before_tokens[-1]) >= 3 and not _ADDR_START_RE.search(before_tokens[-1]):
        return before_tokens[-1]

    after = _clean_inline_field_value((text or "")[biz.end():])
    after = _ADDRESS_CUT_RE.split(after, maxsplit=1)[0]
    after = _PHONE_RE.split(after, maxsplit=1)[0]
    addr_match = _ADDR_START_RE.search(after)
    if addr_match and addr_match.start() > 0:
        company = _clean_inline_field_value(after[:addr_match.start()])
        if 2 <= len(company) <= 20:
            return company
    return ""


def _normalize_company_candidate(text: str) -> str:
    value = _clean_inline_field_value(text)
    value = re.sub(r'^[\[\]{}<>]+', '', value)
    value = re.sub(r'[\[\]{}<>]+$', '', value)
    value = re.sub(r'^[^가-힣A-Za-z0-9(]+', '', value)
    value = re.sub(r'[^가-힣A-Za-z0-9()&.\s]', '', value)
    value = re.sub(r'\s+', '', value)
    value = re.sub(r'은누리약국$', '온누리약국', value)
    if value == "성울집":
        return "서울집"
    if value in {"화성들", "화성률"}:
        return "화성툴"
    return value


def _company_candidate_score(text: str, row_text: str, y_ratio: float, source: str, near_info: bool) -> float:
    candidate = _normalize_company_candidate(text)
    if not candidate or _is_bad_company_candidate(candidate, row_text):
        return -999.0
    if len(candidate) < 2 or len(candidate) > 18:
        return -999.0

    hangul = sum(1 for ch in candidate if '가' <= ch <= '힣')
    digits = sum(1 for ch in candidate if ch.isdigit())
    hangul_ratio = hangul / max(len(candidate), 1)
    convenience_store = bool(_CONVENIENCE_STORE_NAME_RE.search(candidate))
    if digits > 1 and not convenience_store:
        return -999.0

    score = 0.0
    score += hangul_ratio * 22
    score += max(0.0, 1.0 - y_ratio) * 8
    if source == "upper_block":
        score += 2.0
    if near_info:
        score += 8.0
    if _COMPANY_SUFFIX_HINT_RE.search(candidate):
        score += 8.0
    if convenience_store:
        score += 18.0
    if 2 <= hangul <= 6:
        score += 3.0
    return score


def _company_candidate_texts(row_text: str) -> list[tuple[str, bool]]:
    text = _clean_inline_field_value(row_text)
    if not text:
        return []
    if _is_merchant_notice_row(text):
        return []

    candidates: list[tuple[str, bool]] = []
    compact_text = re.sub(r'\s+', '', text)
    if 3 <= len(compact_text) <= 18 and not re.search(r'\d', compact_text) and not _FIELD_NOISE_RE.search(compact_text) and not re.search(r'체크카드|신용매출|귀하|카드|^no\.?', compact_text, re.I):
        candidates.append((text, False))
    has_info = bool(re.search(r'주소|TEL|Tel|tel|전화|사업자|등록번호', text))

    company, _ = _extract_company_rep_from_slash(text)
    if company:
        candidates.append((company, True))

    labeled = _extract_until_next_label(text, r'(?:상호|가맹점명|회사명|업체명|매장명|브랜드명)\s*[:;]?')
    if labeled and not _is_merchant_notice_row(text):
        candidates.append((labeled, True))

    near_biz = _extract_company_near_biz(text)
    if near_biz:
        candidates.append((near_biz, True))

    for token in re.findall(r'[가-힣A-Za-z0-9()]{2,}', text):
        candidates.append((token, has_info))

    return candidates


def _rescue_company_name(
    full_rows,
    upper_rows,
    current: str = "",
    representative: str = "",
    doc_type: str = "unknown",
) -> tuple[str, str]:
    if doc_type == "bank_slip":
        return "", ""

    scored: list[tuple[float, str, str]] = []

    def _row_y_ratio(row) -> float:
        ys = [p[1] for line in row for p in line[0]]
        if not ys:
            return 0.5
        return min(1.0, max(0.0, ((min(ys) + max(ys)) / 2) / 1000.0))

    for source, rows in (("upper_block", upper_rows or []), ("full_ocr", full_rows or [])):
        for idx, row in enumerate(rows):
            row_text = _row_text(row)
            y_ratio = _row_y_ratio(row)
            prev_text = _row_text(rows[idx - 1]) if idx > 0 else ""
            next_text = _row_text(rows[idx + 1]) if idx + 1 < len(rows) else ""
            adjacent_blob = prev_text + " " + next_text
            adjacent_info = bool(
                _extract_biz_number(adjacent_blob)
                or _extract_phone_candidate(adjacent_blob)
                or _extract_address_fragment(adjacent_blob)
            )
            for candidate, near_info in _company_candidate_texts(row_text):
                normalized = _normalize_company_candidate(candidate)
                if representative and normalized == re.sub(r'\s+', '', representative):
                    continue
                score = _company_candidate_score(normalized, row_text, y_ratio, source, near_info or adjacent_info)
                if score > -100:
                    scored.append((score, normalized, source))

    if current:
        normalized = _normalize_company_candidate(current)
        score = _company_candidate_score(normalized, current, 0.2, "current", True)
        if score > -100 and normalized != re.sub(r'\s+', '', representative or ""):
            scored.append((score + 1.0, normalized, "company_rescue"))

    if not scored:
        return "", ""

    scored.sort(key=lambda item: (-item[0], len(item[1])))
    best_score, best_value, best_source = scored[0]
    if best_score < 12:
        return "", ""
    return best_value, best_source


def _extract_fields_from_rows(rows, target: dict) -> None:
    """rows 에서 상단 필드 추출. 이미 채워진 필드는 덮어쓰지 않는다."""
    if not rows:
        return

    for index, row in enumerate(rows):
        row_text = _row_text(row)
        row_compact = row_text.replace(' ', '')
        pair_rep, pair_phone = _extract_rep_phone_pair(row_text)

        if not target.get("사업자번호"):
            has_label = bool(re.search(r'사업자|등록번호', row_compact))
            biz = _extract_biz_number(row_text)
            if not biz and has_label and index + 1 < len(rows):
                biz = _extract_biz_number(_row_text(rows[index + 1]))
            if biz:
                target["사업자번호"] = biz

        if not target.get("tel"):
            phone = pair_phone or _extract_phone_candidate(row_text)
            if phone:
                target["tel"] = phone

        if not target.get("회사명"):
            rest = _extract_until_next_label(row_text, r'(?:상호|가맹점명|회사명|업체명|매장명|브랜드명)\s*[:;]?')
            if rest and not _is_bad_company_candidate(rest, row_text):
                target["회사명"] = rest
            elif re.search(r'상호|가맹점명|회사명|업체명|매장명|브랜드명', row_compact) and index + 1 < len(rows):
                next_row = _clean_inline_field_value(_row_text(rows[index + 1]))
                if next_row and not _is_bad_company_candidate(next_row, row_text):
                    target["회사명"] = next_row
            else:
                company, representative = _extract_company_rep_from_slash(row_text)
                if company and not _is_bad_company_candidate(company, row_text):
                    target["회사명"] = company
                if representative and not target.get("대표자") and not _is_bad_representative_candidate(representative, row_text):
                    target["대표자"] = representative
                if not target.get("회사명"):
                    near_biz = _extract_company_near_biz(row_text)
                    if near_biz and not _is_bad_company_candidate(near_biz, row_text):
                        target["회사명"] = near_biz

        if not target.get("대표자"):
            rest = pair_rep or _extract_until_next_label(row_text, r'(?:대표자명|대표자|대표|성명)\s*[:;]?')
            if 1 <= len(rest) <= 20 and not _is_bad_representative_candidate(rest, row_text):
                target["대표자"] = rest
            elif re.search(r'대표자명|대표자|대표|성명', row_compact) and index + 1 < len(rows):
                next_rep = _clean_inline_field_value(_row_text(rows[index + 1]))
                if not _is_bad_representative_candidate(next_rep, row_text):
                    target["대표자"] = next_rep

        if not target.get("주소") or _address_needs_continuation(target.get("주소", "")):
            if re.match(r'^주소[:\s]|^주소$', row_compact):
                rest = _clean_inline_field_value(re.sub(r'^주\s*소\s*[:\s]*', '', row_text))
                rest = _clean_address_candidate(rest)
                if rest and _address_needs_continuation(rest) and index + 1 < len(rows):
                    cont = _address_continuation_candidate(_row_text(rows[index + 1]))
                    combined = _clean_address_candidate(f"{rest} {cont}") if cont else ""
                    if combined:
                        rest = combined
                if rest:
                    _maybe_set_address(target, rest)
                elif index + 1 < len(rows):
                    next_addr = _clean_address_candidate(_row_text(rows[index + 1]))
                    if next_addr:
                        _maybe_set_address(target, next_addr)
            else:
                addr = _clean_address_candidate(_extract_address_fragment(row_text) or row_text)
                if addr and _address_needs_continuation(addr) and index + 1 < len(rows):
                    cont = _address_continuation_candidate(_row_text(rows[index + 1]))
                    combined = _clean_address_candidate(f"{addr} {cont}") if cont else ""
                    if combined:
                        addr = combined
                if addr:
                    _maybe_set_address(target, addr)


# ============================================================
# 문서 유형별 총합계금액 사후 정책
# ============================================================
#
# 정책 요약:
#   - receipt_pos / receipt_card : 기본 (select_best_total_amount 결과를 그대로 사용)
#       저신뢰(score < 5)는 status="low_confidence" 로 남되 값은 유지 — 사용자 판단
#   - bank_slip                  : 강한 합계 근거 없으면 비움. 잔액/수수료 오탐 방지가
#                                   일반 합계 자동추출보다 우선. 향후 '거래금액' 별도 필드
#                                   확장 여지를 위해 raw 후보는 debug 에 그대로 보존.
#   - form_or_handwritten        : 수기 영수증 — OCR 숫자 자체가 왜곡되기 쉬움.
#                                   저신뢰 또는 bare 단일 후보면 비움. 나머지 고정 필드
#                                   (회사명/사업자번호 등)는 가능한 범위로 추출 시도는 함.
#   - unknown                    : 근거 부족으로 보수 처리. bare 단일 저신뢰는 비움.
#
# 반환 상태 코드(amount_debug.status):
#   selected / low_confidence / no_candidate / all_rejected
#     ↑ select_best_total_amount 단계의 1차 상태
#   suppressed_bank_slip / suppressed_handwritten / suppressed_unknown_bare
#     ↑ 사후 정책이 1차 결과를 비울 때 덮어쓰는 상태
#
# review.required = True 이면 프론트/후속단계에서 '검토 필요' 배지/워크플로우 분기 가능.

_REVIEW_STATUSES = {
    "no_candidate",
    "all_rejected",
    "low_confidence",
    "suppressed_bank_slip",
    "suppressed_handwritten",
    "suppressed_unknown_bare",
}


def _apply_doc_type_amount_policy(
    doc_type: str,
    amount_value: str,
    amount_debug: dict,
) -> tuple[str, dict, dict]:
    """문서 유형별 사후 정책을 적용하여 최종 (값, 디버그, 검토정보) 반환.

    - 원칙: "잘못된 자동채택보다 빈값+검토필요가 낫다"
    - 값은 절대 autofill 하지 않음 (정책 유지)
    """
    sel = amount_debug.get("selected")
    status_1st = amount_debug.get("status")

    if doc_type == "bank_slip":
        # 은행표: 총합계금액을 일반 영수증 규칙으로 무리하게 맞추지 않음.
        # 강한 합계 근거(score >= 40)가 없으면 비움.
        if not sel or sel.get("score", 0) < 40:
            amount_value = ""
            amount_debug = {
                **amount_debug,
                "status": "suppressed_bank_slip",
                "reason": (
                    "bank_slip: 강한 합계 근거 부족 → 비움. "
                    "거래후잔액/수수료/계좌 문맥의 숫자를 합계로 자동채택하지 않음."
                ),
                "policy": "bank_slip_conservative",
            }

    elif doc_type == "form_or_handwritten":
        # 수기/폼 문서: 저신뢰 또는 bare 단일 후보면 비움. 검토 필요 표시.
        low_score = (not sel) or sel.get("score", 0) < 45
        bare_only = bool(sel and sel.get("pattern") == "bare")
        if low_score or bare_only:
            amount_value = ""
            amount_debug = {
                **amount_debug,
                "status": "suppressed_handwritten",
                "reason": (
                    "form_or_handwritten: 수기 숫자는 OCR 신뢰도가 낮아 자동채택 보수화. "
                    "저신뢰/bare 후보는 검토 필요 상태로 비움."
                ),
                "policy": "handwritten_review_required",
            }

    elif doc_type == "unknown":
        # 알 수 없는 문서: bare 저신뢰 단독이면 비움. 그 외 저신뢰는 값 유지하되 검토 필요.
        if sel and sel.get("pattern") == "bare" and sel.get("score", 0) < 15:
            amount_value = ""
            amount_debug = {
                **amount_debug,
                "status": "suppressed_unknown_bare",
                "reason": "unknown: 분류 근거 부족 + bare 저신뢰 후보 → 비움.",
                "policy": "unknown_conservative",
            }

    # 최종 상태 기준으로 검토 필요 여부 산정
    final_status = amount_debug.get("status") or status_1st
    required = final_status in _REVIEW_STATUSES
    review_code_map = {
        "no_candidate": "NO_CANDIDATE",
        "all_rejected": "ALL_REJECTED",
        "low_confidence": "LOW_CONFIDENCE",
        "suppressed_bank_slip": "SUPPRESSED_BANK_SLIP",
        "suppressed_handwritten": "SUPPRESSED_HANDWRITTEN",
        "suppressed_unknown_bare": "SUPPRESSED_UNKNOWN_BARE",
    }
    review = {
        "required": required,
        "code": review_code_map.get(final_status, "") if required else "",
        "reason": amount_debug.get("reason", "") if required else "",
        "final_status": final_status,
    }
    return amount_value, amount_debug, review


def extract_receipt_fields(
    ocr_lines: list,
    upper_lines: list | None = None,
    amount_lines: list | None = None,
    doc_type: str = "unknown",
    debug: dict | None = None,
) -> dict:
    """
    bbox 좌표 기반 영수증 필드 추출 (2단계 OCR 지원).
      - ocr_lines    : 1차 전체 OCR 결과
      - upper_lines  : (선택) 상단 사업자 정보 블록 재OCR 결과 → 회사명/대표자/주소/사업자번호/전화 우선
      - amount_lines : (선택) 하단 금액 블록 재OCR 결과 → 총합계금액 후보 소스 보강
      - doc_type     : classify_document() 결과 ("receipt_pos"/"receipt_card"/"bank_slip"/"unknown")
      - debug        : dict 를 넘기면 금액 후보/선택/필드 소스 추적 메타 기록

    정책:
      - bank_slip: 합계 후보는 점수화에 맡기되 낮은 스코어는 비움 (오탐 방지 우선)
      - receipt_pos/receipt_card: 상단 재OCR → 전체 OCR 순으로 필드 채움, 하단 재OCR 금액 후보 보강
      - autofill/GT 를 참조하지 않는다 (정책 유지: 총합계는 OCR 전용 필드)
    """
    result = {"회사명": "", "사업자번호": "", "대표자": "", "tel": "", "주소": "", "총합계금액": ""}
    field_sources = {k: "" for k in result}

    if not ocr_lines and not upper_lines and not amount_lines:
        if debug is not None:
            debug["total_amount"] = {"status": "no_ocr_lines", "candidates": [], "selected": None}
            debug["field_sources"] = field_sources
            debug["doc_type"] = doc_type
        return result

    rows = _group_rows(ocr_lines)
    upper_rows = _group_rows(upper_lines or [])
    upper_single_rows = _single_line_rows(upper_lines or [])
    amount_rows = _group_rows(amount_lines or [])

    # --- 필드 추출: 상단 재OCR 우선, 그 다음 전체 OCR ---
    if upper_rows:
        before = dict(result)
        _extract_fields_from_rows(upper_rows, result)
        for k, v in result.items():
            if v and not before.get(k):
                field_sources[k] = "upper_block"

    if upper_single_rows:
        before = dict(result)
        _extract_fields_from_rows(upper_single_rows, result)
        for k, v in result.items():
            if v and not before.get(k):
                field_sources[k] = "upper_block"

    before = dict(result)
    _extract_fields_from_rows(rows, result)
    for k, v in result.items():
        if v and not before.get(k) and not field_sources[k]:
            field_sources[k] = "full_ocr"

    rescued_company, rescued_source = _rescue_company_name(
        rows,
        (upper_rows or []) + (upper_single_rows or []),
        current=result.get("회사명", ""),
        representative=result.get("대표자", ""),
        doc_type=doc_type,
    )
    if rescued_company and rescued_company != result.get("회사명", ""):
        result["회사명"] = rescued_company
        field_sources["회사명"] = rescued_source or "company_rescue"

    # --- 총합계금액 ---
    # 후보를 3개 소스에서 수집 → merge → 공급가액+부가세 합성 후보 추가 → 재merge
    cands_full   = extract_amount_candidates(rows, _row_text, source="full_ocr")
    cands_amount = extract_amount_candidates(amount_rows, _row_text, source="amount_block") if amount_rows else []
    cands_upper  = extract_amount_candidates(upper_rows, _row_text, source="upper_block") if upper_rows else []
    merged_base = merge_candidates(cands_full, cands_amount, cands_upper)
    synth = synthesize_supply_vat_totals(merged_base)
    merged = merge_candidates(merged_base, synth)

    amount_value, amount_debug = select_best_total_amount(merged)

    # 문서 유형별 사후 정책 적용 — 원칙: "잘못된 자동채택 < 빈값 + 검토필요"
    amount_value, amount_debug, review = _apply_doc_type_amount_policy(
        doc_type, amount_value, amount_debug,
    )

    result["총합계금액"] = amount_value

    # 선택된 금액의 소스 추적
    if amount_value:
        sel = amount_debug.get("selected")
        if sel:
            for c in merged:
                if c["formatted"] == sel["value"]:
                    field_sources["총합계금액"] = c.get("source", "full_ocr")
                    break

    if debug is not None:
        debug["total_amount"] = amount_debug
        debug["field_sources"] = field_sources
        debug["doc_type"] = doc_type
        debug["candidate_counts"] = {
            "full_ocr": len(cands_full),
            "amount_block": len(cands_amount),
            "upper_block": len(cands_upper),
            "merged": len(merged),
        }
        # 검토 필요 여부 (프론트/후속 처리에서 '검토 필요 배지' 용도로 활용 가능)
        debug["total_amount_review_required"] = review["required"]
        if review["required"]:
            debug["total_amount_review_reason"] = review["reason"]
            debug["total_amount_review_code"] = review["code"]

    return result


@app.on_event("startup")
def _warmup_ocr():
    """서버 시작 시 OCR 엔진 미리 로드 (첫 요청 지연 방지)"""
    import threading
    def _load():
        engine = get_ocr_engine()
        import numpy as np
        dummy = np.ones((100, 100, 3), dtype=np.uint8) * 255
        engine.ocr(dummy)
        print("[OCR] Engine warmed up")
    threading.Thread(target=_load, daemon=True).start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 데이터 디렉토리 ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
# 운영/검수 로그 (JSONL). ground_truth 와 완전히 분리 — 절대 GT 파일을 수정하지 않는다.
REVIEW_LOG_FILE = os.path.join(DATA_DIR, "review_log.jsonl")

os.makedirs(DATA_DIR, exist_ok=True)


# ============================================================
# 검수/운영 로그 (review_log.jsonl)
# ============================================================
#
# 목적:
#   - unknown / low_confidence / no_candidate / suppressed_* / selected 상태의
#     모든 추출 결과를 한 줄씩 JSONL 로 누적 → 시간 경과에 따른 실패 패턴 분석
#     및 분류기/점수 규칙 개선의 입력 데이터로 활용.
#   - human_correction 이벤트(사용자 최종 수정값)도 같은 파일에 누적 →
#     auto 와 correction 을 image_id 로 join 해 오탐/미검출 사례 수집.
#
# 원칙:
#   - ground_truth.json 은 READ 전용. 서버는 절대 GT 를 덮어쓰지 않는다.
#   - 총합계금액은 autofill 금지. 로그는 결과 기록일 뿐 값 채택 경로에 영향 없음.
#   - 로그 실패는 OCR 경로를 깨뜨리지 않는다 (best-effort append, 예외는 무시).
#
# 새 패턴 흡수 흐름:
#   1) 미지의 영수증 → classify_document() 가 unknown 또는 오분류 반환
#   2) 정책상 자동 확정 금지 → review_required=True 로 사용자에게 검토 요청
#   3) 사용자가 /ocr/feedback 으로 최종값 입력 → human_correction 로그 기록
#   4) 운영자가 review_log.jsonl 을 주기적으로 스캔 → 반복되는 unknown 패턴 식별
#   5) 식별된 패턴을 document_classifier.py 시그널에 추가 → 다음 분류부터 정상 유형화
#   ※ ground_truth.json 은 이 과정에 관여하지 않음 (정답 보관용 동결 데이터셋)


def _append_review_log(entry: dict) -> None:
    """JSONL 한 줄 append. 실패해도 OCR 요청 경로에 영향 없도록 try/except 로 감싼다."""
    try:
        with open(REVIEW_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[review_log] write failed: {e}")


def _build_auto_extract_log(
    image_id: str,
    doc_type: str,
    doc_classification: dict,
    extract_debug: dict,
    receipt_fields: dict,
    field_confidences: dict,
    full_text: str,
    upper_block_text: str,
    amount_block_text: str,
    processing_time: float,
) -> dict:
    """/ocr/extract 의 자동 추출 결과를 검수 로그 엔트리로 직렬화."""
    ta = extract_debug.get("total_amount") or {}
    sel = ta.get("selected") or {}
    review_required = bool(extract_debug.get("total_amount_review_required"))

    # field 별 raw / normalized / selected / source / confidence
    # 현재 파이프라인은 필드별 raw/normalized 구분 저장이 없으므로, receipt_fields 의 값을
    # 'normalized == selected' 로 기록하고 raw 는 동일값을 넣는다. 추후 필드 추출 로직이
    # raw/normalized 를 분리 저장하게 되면 여기만 수정하면 됨.
    field_log: dict[str, dict] = {}
    for k, v in receipt_fields.items():
        field_log[k] = {
            "raw": v,
            "normalized": v,
            "selected": v,
            "source": extract_debug.get("field_sources", {}).get(k, ""),
            "confidence": field_confidences.get(k),
        }
    # 총합계금액은 source/score 등 더 풍부한 메타를 겹쳐 쓴다.
    if "총합계금액" in field_log:
        field_log["총합계금액"].update({
            "source": sel.get("source", field_log["총합계금액"]["source"]),
            "pattern": sel.get("pattern"),
            "score": sel.get("score"),
            "row_pos": sel.get("row_pos"),
            "synth_from": sel.get("synth_from"),
        })

    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "event_type": "auto_extract",
        "image_id": image_id or "",
        "doc_type": doc_type,
        "doc_classification": doc_classification,
        "status": ta.get("status"),
        "review_required": review_required,
        "review_code": extract_debug.get("total_amount_review_code", "") if review_required else "",
        "review_reason": extract_debug.get("total_amount_review_reason", "") if review_required else "",
        "total_amount": {
            "selected_value": sel.get("value", ""),
            "source": sel.get("source"),
            "pattern": sel.get("pattern"),
            "score": sel.get("score"),
            "reasons": sel.get("reasons") or [],
            "candidate_count": (extract_debug.get("candidate_counts") or {}).get("merged"),
            "top_rejected": ta.get("rejected_top") or [],
        },
        "fields": field_log,
        "full_text": full_text,
        "upper_block_text": upper_block_text,
        "amount_block_text": amount_block_text,
        "processing_time_sec": processing_time,
    }


# 초기 사용자 데이터 생성
if not os.path.exists(USERS_FILE):
    _save_json(USERS_FILE, [
        {"user_id": "admin", "user_pw": "admin", "user_nm": "관리자", "adminYn": "Y", "masterYn": "Y", "comp_cd": "MYSUIT", "comp_nm": "MySuit"},
        {"user_id": "user", "user_pw": "user", "user_nm": "사용자", "adminYn": "N", "masterYn": "N", "comp_cd": "MYSUIT", "comp_nm": "MySuit"},
    ])

if not os.path.exists(HISTORY_FILE):
    _save_json(HISTORY_FILE, [])


# ============================================================
# 헬스체크
# ============================================================
@app.get("/health")
def health():
    return {"status": "ok"}


# ============================================================
# 로그인
# ============================================================
@app.post("/login")
async def login(request: Request):
    body = await request.json()
    user_id = body.get("user_id", "")
    user_pw = body.get("user_pw", "")

    users = _load_json(USERS_FILE, [])
    user = next((u for u in users if u["user_id"] == user_id and u["user_pw"] == user_pw), None)

    if not user:
        return JSONResponse(
            status_code=401,
            content={"ResultCode": "Validation", "ResultMsg": "아이디 또는 비밀번호가 일치하지 않습니다."},
        )

    token = str(uuid.uuid4())

    return {
        "resultMap": {
            "accessToken": token,
            "user_id": user["user_id"],
            "user_nm": user["user_nm"],
            "adminYn": user.get("adminYn", "N"),
            "masterYn": user.get("masterYn", "N"),
            "comp_cd": user.get("comp_cd", ""),
            "comp_nm": user.get("comp_nm", ""),
            "envMysuitUrl": "",
            "envMagellanVersion": "1.0.0",
        }
    }


# ============================================================
# 템플릿 CRUD
# ============================================================
TEMPLATES_FILE = os.path.join(DATA_DIR, "templates.json")
if not os.path.exists(TEMPLATES_FILE):
    _save_json(TEMPLATES_FILE, [])


@app.get("/templates")
async def template_list():
    rows = _load_json(TEMPLATES_FILE, [])
    return {"resultMap": {"templateList": rows}}


@app.delete("/templates/{template_id}")
async def template_delete(template_id: str):
    rows = _load_json(TEMPLATES_FILE, [])
    rows = [r for r in rows if r["template_id"] != template_id]
    _save_json(TEMPLATES_FILE, rows)
    return {"resultMap": {"result": "success"}}


# ============================================================
# 히스토리 CRUD
# ============================================================
@app.post("/ocrSelect")
async def ocr_select(request: Request):
    rows = _load_json(HISTORY_FILE, [])
    return {"resultMap": {"boardList": rows}}


@app.post("/ocrInsert")
async def ocr_insert(request: Request):
    body = await request.json()
    rows = _load_json(HISTORY_FILE, [])

    new_row = {
        "job_id": f"OCR-{uuid.uuid4().hex[:8].upper()}",
        "file_name": body.get("file_name", ""),
        "template_name": body.get("template_name", ""),
        "processing_time": body.get("processing_time", 0),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    rows.insert(0, new_row)
    _save_json(HISTORY_FILE, rows)

    return {"resultMap": {"result": "success"}}


@app.post("/ocrUpdate")
async def ocr_update(request: Request):
    body = await request.json()
    job_id = body.get("job_id", "")
    rows = _load_json(HISTORY_FILE, [])

    for row in rows:
        if row["job_id"] == job_id:
            row["file_name"] = body.get("file_name", row["file_name"])
            row["template_name"] = body.get("template_name", row["template_name"])
            row["processing_time"] = body.get("processing_time", row["processing_time"])
            break

    _save_json(HISTORY_FILE, rows)
    return {"resultMap": {"result": "success"}}


@app.post("/ocrDelete")
async def ocr_delete(request: Request):
    body = await request.json()
    job_id = body.get("job_id", "")
    rows = _load_json(HISTORY_FILE, [])

    rows = [r for r in rows if r["job_id"] != job_id]
    _save_json(HISTORY_FILE, rows)

    return {"resultMap": {"result": "success"}}


# ============================================================
# 검수 피드백 / 검수 로그 조회 (운영용)
# ============================================================

@app.post("/ocr/feedback")
async def ocr_feedback(request: Request):
    """사용자가 검토 화면에서 최종 수정한 값을 review_log.jsonl 에 기록.

    기대 입력:
      {
        "image_id": "1.jpg",
        "doc_type": "receipt_card",                  (선택)
        "auto_selected_fields": {"총합계금액": "...", ...},  (선택 — 감사용)
        "corrected_fields":   {"총합계금액": "10,560", ...},
        "correction_reason": "OCR 오인식 수정",        (선택)
        "review_code": "LOW_CONFIDENCE"              (선택)
      }

    주의:
      - 이 엔드포인트는 ground_truth.json 을 수정하지 않는다.
      - 총합계금액을 autofill 하지 않는다. 단순 기록 경로.
    """
    body = await request.json()
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "event_type": "human_correction",
        "image_id": body.get("image_id", ""),
        "doc_type": body.get("doc_type", ""),
        "auto_selected_fields": body.get("auto_selected_fields", {}),
        "corrected_fields": body.get("corrected_fields", {}),
        "correction_reason": body.get("correction_reason", ""),
        "review_code": body.get("review_code", ""),
    }
    _append_review_log(entry)
    return {"ok": True}


@app.get("/ocr/review-log")
async def ocr_review_log(
    status: str = Query(default=""),
    image_id: str = Query(default=""),
    limit: int = Query(default=100),
):
    """review_log.jsonl 를 필터링해 반환 (운영/관리용).

    query:
      status    : auto_extract 엔트리의 status 로 필터 (e.g. suppressed_bank_slip)
      image_id  : 해당 이미지의 모든 이벤트만 반환
      limit     : 최신 N건 (default 100)
    """
    if not os.path.exists(REVIEW_LOG_FILE):
        return {"entries": [], "total": 0}
    entries: list[dict] = []
    with open(REVIEW_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if status and e.get("status") != status:
                continue
            if image_id and e.get("image_id") != image_id:
                continue
            entries.append(e)
    entries = entries[-limit:]
    return {"entries": entries, "total": len(entries)}


# ============================================================
# 이미지 전처리
# ============================================================
def read_image(data: bytes, filename: str = "") -> np.ndarray:
    """이미지 또는 PDF를 읽어 numpy 배열로 반환"""
    # PDF인 경우 첫 페이지를 이미지로 변환
    if filename.lower().endswith(".pdf") or data[:5] == b"%PDF-":
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(dpi=200)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            doc.close()
            if img_array.shape[2] == 4:  # RGBA -> BGR
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            else:  # RGB -> BGR
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            return img_array
        except Exception:
            raise HTTPException(status_code=400, detail="PDF를 읽을 수 없습니다.")

    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="이미지를 읽을 수 없습니다.")
    return img


def encode_image(img: np.ndarray, fmt: str = "PNG") -> bytes:
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    buf = io.BytesIO()
    pil_img.save(buf, format=fmt)
    return buf.getvalue()


@app.post("/preprocess")
async def preprocess_image(file: UploadFile = File(...)):
    data = await file.read()
    img = read_image(data, file.filename or "")

    processed, meta = preprocess(img)
    output = encode_image(processed)

    headers = {
        "X-Preprocess-Deskew": meta.get("deskew", "-"),
        "X-Preprocess-Denoise": meta.get("denoise", "-"),
        "X-Preprocess-Contrast": meta.get("contrast", "-"),
    }

    return StreamingResponse(
        io.BytesIO(output),
        media_type="image/png",
        headers=headers,
    )


@app.post("/preprocess/info")
async def preprocess_info(file: UploadFile = File(...)):
    data = await file.read()
    img = read_image(data, file.filename or "")
    _, meta = preprocess(img)
    return JSONResponse(content={"result": meta})


# ============================================================
# OCR 실행
# ============================================================
_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        import os
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(
            lang="korean",
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="korean_PP-OCRv5_mobile_rec",
            device="cpu",
            use_textline_orientation=False,
            use_doc_orientation_classify=False,  # 자체 detect_orientation 사용, 중복 제거
            use_doc_unwarping=False,             # UVDoc 비활성화 (영수증에 불필요, 속도 주범)
            # NOTE: enable_mkldnn=True 는 현재 PaddlePaddle 빌드(PIR executor)에서
            #       `ConvertPirAttribute2RuntimeAttribute not support ...ArrayAttribute<DoubleAttribute>`
            #       런타임 에러로 inference 실패 → False 유지. paddle 버전이 PIR+oneDNN 지원 시 재검토.
            enable_mkldnn=False,
            cpu_threads=os.cpu_count() or 4,
            text_recognition_batch_size=30,
        )
    return _ocr_engine


def _ocr_crop_region(img, ocr, x, y, w, h):
    """이미지에서 특정 영역을 크롭하여 OCR 실행. 모든 텍스트를 합쳐 반환."""
    img_h, img_w = img.shape[:2]
    margin = max(8, int(min(w, h) * 0.05))
    x1, y1 = max(0, x - margin), max(0, y - margin)
    x2, y2 = min(img_w, x + w + margin), min(img_h, y + h + margin)

    cropped = img[y1:y2, x1:x2]
    if cropped.size == 0:
        return "", 0.0

    # 작은 영역 업스케일
    ch, cw = cropped.shape[:2]
    if ch < 80:
        scale = 80 / ch
        cropped = cv2.resize(cropped, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_CUBIC)

    ocr_result = ocr.ocr(cropped)

    texts = []
    confs = []
    for _, t, c in _parse_ocr_lines(ocr_result):
        if t and c >= 0.3:
            texts.append(t)
            confs.append(c)

    if not texts:
        return "", 0.0
    return " ".join(texts), round(sum(confs) / len(confs), 4)


def _detect_upper_block_bbox(
    ocr_lines: list,
    ocr_h: int,
    ocr_w: int,
    doc_type: str = "unknown",
) -> tuple[int, int, int, int] | None:
    """상단 사업자 정보 블록 bbox 를 보수적으로 추정."""
    if ocr_h <= 0 or ocr_w <= 0:
        return None

    def _y_bounds(line):
        ys = [p[1] for p in line[0]]
        return int(min(ys)), int(max(ys))

    def _cy(line):
        y0, y1 = _y_bounds(line)
        return (y0 + y1) / 2

    target_re = re.compile(r'사업자|등록번호|TEL|전화|대표|상호|가맹점|주소|성명', re.I)
    biz_re = re.compile(r'[1-9]\d{2}[-\s.]?\d{2}[-\s.]?\d{5}')
    notice_re = re.compile(r'신고안내|여신금융|협회|crefia|가맹점주소.*다른경우', re.I)
    tail_noise_re = re.compile(
        r'카드번호|승인번호|거래일시|매출전표|합계|판매금액|부가세|공급가액|품목|수량|단가|'
        r'VANKEY|TID|CAT',
        re.I,
    )
    card_like_re = re.compile(r'비씨|체크|카드|승인|가맹점No|가맹점번호|TID|CAT|매출전표', re.I)
    address_hint_re = re.compile(r'[가-힣A-Za-z0-9].*(?:시|도|군|구|로|길|동|읍|면)', re.I)
    company_owner_hint_re = re.compile(r'[가-힣A-Za-z0-9().&]+\s*/\s*[가-힣]{2,4}')
    company_hint_re = re.compile(r'(약국|조명|전기|철물|상사|스토어|마트|카페|식당|공구|볼트|상회|점)$', re.I)

    lines = [line for line in (ocr_lines or []) if line[1]]
    lines_sorted = sorted(lines, key=_cy)
    tops: list[int] = []
    bottoms: list[int] = []
    target_indices: list[int] = []
    hint_tops: list[int] = []
    hint_bottoms: list[int] = []
    hint_indices: list[int] = []
    card_like = doc_type == "receipt_card"

    for idx, (pts, text, _) in enumerate(lines_sorted):
        norm = text.replace(' ', '')
        if card_like_re.search(norm):
            card_like = True
        is_noise = bool(notice_re.search(norm) or tail_noise_re.search(norm))
        is_target = bool(target_re.search(norm) and not is_noise)
        is_biz_line = bool(biz_re.search(norm) and _cy((pts, text, _)) <= ocr_h * 0.65)
        is_hint_line = (
            _cy((pts, text, _)) <= ocr_h * 0.62 and
            not is_noise and
            (
                company_owner_hint_re.search(text or "") or
                address_hint_re.search(text or "") or
                company_hint_re.search(norm)
            )
        )
        if is_target or is_biz_line:
            y0, y1 = _y_bounds((pts, text, _))
            tops.append(y0)
            bottoms.append(y1)
            target_indices.append(idx)
        if is_hint_line:
            y0, y1 = _y_bounds((pts, text, _))
            hint_tops.append(y0)
            hint_bottoms.append(y1)
            hint_indices.append(idx)

    if tops:
        y1 = max(0, min(tops) - max(int(ocr_h * 0.025), 12))
        y2 = min(ocr_h, max(bottoms) + max(int(ocr_h * 0.04), 22))

        if hint_tops and min(hint_tops) < min(tops) and min(tops) > int(ocr_h * 0.45):
            y1 = min(y1, max(0, min(hint_tops) - max(int(ocr_h * 0.02), 10)))
            y2 = max(y2, min(ocr_h, max(hint_bottoms) + max(int(ocr_h * 0.06), 28)))

        first_idx = min(target_indices)
        if first_idx > 0:
            max_up_gap = max(int(ocr_h * 0.08), 45)
            max_up_span = max(int(ocr_h * 0.16), 95)
            anchor_top = min(tops)
            for prev in reversed(lines_sorted[max(0, first_idx - 3):first_idx]):
                prev_text = prev[1].replace(' ', '')
                py0, py1 = _y_bounds(prev)
                gap = anchor_top - py1
                if gap < 0 or gap > max_up_gap or anchor_top - py0 > max_up_span:
                    continue
                if notice_re.search(prev_text) or tail_noise_re.search(prev_text):
                    continue
                y1 = min(y1, max(0, py0 - max(int(ocr_h * 0.015), 8)))

        last_idx = max(target_indices)
        if last_idx + 1 < len(lines_sorted):
            max_down_gap = max(int(ocr_h * 0.075), 42)
            max_down_span = max(int(ocr_h * 0.15), 90)
            anchor_bottom = max(bottoms)
            for nxt in lines_sorted[last_idx + 1:min(len(lines_sorted), last_idx + 4)]:
                nxt_text = nxt[1].replace(' ', '')
                ny0, ny1 = _y_bounds(nxt)
                gap = ny0 - anchor_bottom
                if gap < 0 or gap > max_down_gap or ny1 - anchor_bottom > max_down_span:
                    continue
                if notice_re.search(nxt_text) or tail_noise_re.search(nxt_text):
                    break
                y2 = max(y2, min(ocr_h, ny1 + max(int(ocr_h * 0.025), 14)))

        max_h_ratio = 0.34 if card_like else 0.42
        if y2 - y1 > int(ocr_h * max_h_ratio):
            y2 = y1 + int(ocr_h * max_h_ratio)
    else:
        if hint_tops:
            y1 = max(0, min(hint_tops) - max(int(ocr_h * 0.02), 10))
            y2 = min(ocr_h, max(hint_bottoms) + max(int(ocr_h * 0.08), 36))
        else:
            y1 = 0
            y2 = int(ocr_h * (0.30 if card_like else 0.35))

    min_h = max(int(ocr_h * 0.14), 90)
    if y2 - y1 < min_h:
        y2 = min(ocr_h, y1 + min_h)

    return (0, y1, ocr_w, max(1, y2 - y1))


def _detect_amount_block_bbox(
    ocr_lines: list,
    ocr_h: int,
    ocr_w: int,
    doc_type: str = "unknown",
) -> tuple[int, int, int, int] | None:
    """하단 금액 블록 bbox 를 문서 유형에 맞게 추정."""
    if ocr_h <= 0 or ocr_w <= 0:
        return None

    total_keyword_re = re.compile(
        r'총합계금액|총합계|최종금액|최종합계|결제금액|받을금액|청구금액|합계|총계|total',
        re.I,
    )
    partial_keyword_re = re.compile(
        r'공급가액|부가세|판매금액|매출금액|vat|tax',
        re.I,
    )
    tail_keyword_re = re.compile(
        r'승인번호|전표|거래일시|가맹점번호|카드번호|매출전표|tid|catid|일련번호|'
        r'무서명|감사합니다|신고안내',
        re.I,
    )
    amount_number_re = re.compile(r'\d{1,3}(?:[,:.;]\d{3})+|\d{4,9}')

    lower_amount_tops: list[int] = []
    lower_amount_bottoms: list[int] = []
    lower_total_tops: list[int] = []
    tail_tops: list[int] = []
    fallback_numeric_tops: list[int] = []

    for pts, text, _ in ocr_lines or []:
        norm = text.replace(' ', '')
        ys = [p[1] for p in pts]
        y_min = int(min(ys))
        y_max = int(max(ys))
        y_mid = (y_min + y_max) / 2
        has_amount = bool(amount_number_re.search(norm))
        has_total = bool(total_keyword_re.search(norm))
        has_partial = bool(partial_keyword_re.search(norm))
        has_tail = bool(tail_keyword_re.search(norm))

        if has_amount and y_mid >= ocr_h * 0.40:
            lower_amount_tops.append(y_min)
            lower_amount_bottoms.append(y_max)
        elif has_amount and y_mid >= ocr_h * 0.30:
            fallback_numeric_tops.append(y_min)

        if has_total and has_amount and y_mid >= ocr_h * 0.28:
            lower_total_tops.append(y_min)

        if has_tail and y_mid >= ocr_h * 0.40:
            tail_tops.append(y_min)

        if has_partial and has_amount and y_mid >= ocr_h * 0.35:
            lower_amount_tops.append(y_min)
            lower_amount_bottoms.append(y_max)

    receipt_like = doc_type in {"receipt_card", "receipt_pos"}
    receipt_pos_like = doc_type == "receipt_pos"
    band_floor = int(ocr_h * (0.34 if receipt_pos_like else 0.50 if receipt_like else 0.46))
    band_default = int(ocr_h * (0.38 if receipt_pos_like else 0.58 if receipt_like else 0.55))
    band_ceiling = int(ocr_h * (0.84 if receipt_like else 0.88))

    if lower_total_tops:
        anchor_y = min(lower_total_tops)
        y1 = max(band_floor, anchor_y - max(int(ocr_h * 0.04), 18))
    elif lower_amount_tops:
        anchor_y = min(lower_amount_tops)
        y1 = max(band_floor, anchor_y - max(int(ocr_h * 0.05), 24))
    elif fallback_numeric_tops:
        anchor_y = min(fallback_numeric_tops)
        y1 = max(band_default, anchor_y - max(int(ocr_h * 0.03), 16))
    else:
        y1 = band_default

    if lower_amount_bottoms:
        y2 = min(ocr_h, max(lower_amount_bottoms) + max(int(ocr_h * 0.06), 26))
    else:
        y2 = min(ocr_h, y1 + int(ocr_h * (0.30 if receipt_like else 0.36)))

    tail_cutoffs = [y for y in tail_tops if y > y1 + int(ocr_h * 0.05)]
    if tail_cutoffs:
        y2 = min(y2, min(tail_cutoffs) + max(int(ocr_h * 0.02), 10))

    y1 = min(y1, band_ceiling)
    min_band_h = int(ocr_h * (0.18 if receipt_like else 0.20))
    max_band_h = int(ocr_h * (0.38 if receipt_like else 0.45))
    y2 = max(y2, y1 + min_band_h)
    y2 = min(y2, y1 + max_band_h, ocr_h)

    if y2 - y1 < max(int(ocr_h * 0.12), 80):
        y1 = max(0, y2 - max(int(ocr_h * 0.22), 120))

    return (0, y1, ocr_w, max(1, y2 - y1))


def _reocr_block(
    img,
    ocr,
    bbox: tuple[int, int, int, int],
    mode: str = "general",
    timings: dict | None = None,
) -> list:
    """주어진 bbox 를 crop + 강화 전처리 후 재OCR.
    반환: _parse_ocr_lines 포맷 (좌표는 원본 img 좌표계로 변환됨)

    timings(dict) 가 주어지면 crop / preprocess / ocr 3단계 시간(ms)과
    crop dimension(before/after 업스케일) 을 기록.
    """
    import time as _time
    if bbox is None:
        return []
    x, y, w, h = bbox
    if w <= 0 or h <= 0:
        return []

    _t0 = _time.time()
    img_h, img_w = img.shape[:2]
    x1 = max(0, x); y1 = max(0, y)
    x2 = min(img_w, x + w); y2 = min(img_h, y + h)
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        return []
    ch0, cw0 = crop.shape[:2]
    _t_crop = _time.time() - _t0

    _t1 = _time.time()
    ch, cw = crop.shape[:2]
    # 업스케일: 작은 블록은 OCR 인식률에 직접 영향
    target_min = 400 if mode == "amount" else (620 if mode == "upper" else 500)
    if ch < target_min:
        scale = target_min / ch
        if mode == "upper":
            scale = min(scale, 3600 / max(cw, 1))
        crop = cv2.resize(crop, (int(cw * scale), int(ch * scale)), interpolation=cv2.INTER_CUBIC)

    # 상단 한글 소문자는 과샤픈에 약해 mode 별로 다르게 보정한다.
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    if mode == "upper":
        clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(6, 6))
    else:
        clahe = cv2.createCLAHE(clipLimit=3.0 if mode == "amount" else 2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    crop = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

    if mode == "upper":
        blur = cv2.GaussianBlur(crop, (0, 0), 0.8)
        crop = cv2.addWeighted(crop, 1.25, blur, -0.25, 0)
    else:
        blur = cv2.GaussianBlur(crop, (0, 0), 1.2)
        crop = cv2.addWeighted(crop, 1.5, blur, -0.5, 0)
    ch1, cw1 = crop.shape[:2]
    _t_prep = _time.time() - _t1

    _t2 = _time.time()
    try:
        result = ocr.ocr(crop)
    except Exception as e:
        print(f"[reocr] ocr failed: {e}")
        if timings is not None:
            timings[f"reocr_{mode}_crop_ms"] = round(_t_crop * 1000, 1)
            timings[f"reocr_{mode}_preprocess_ms"] = round(_t_prep * 1000, 1)
            timings[f"reocr_{mode}_ocr_ms"] = 0.0
            timings[f"reocr_{mode}_crop_wh_before"] = [cw0, ch0]
            timings[f"reocr_{mode}_crop_wh_after"] = [cw1, ch1]
        return []
    _t_ocr = _time.time() - _t2

    lines = _parse_ocr_lines(result)

    if timings is not None:
        timings[f"reocr_{mode}_crop_ms"] = round(_t_crop * 1000, 1)
        timings[f"reocr_{mode}_preprocess_ms"] = round(_t_prep * 1000, 1)
        timings[f"reocr_{mode}_ocr_ms"] = round(_t_ocr * 1000, 1)
        timings[f"reocr_{mode}_crop_wh_before"] = [cw0, ch0]
        timings[f"reocr_{mode}_crop_wh_after"] = [cw1, ch1]

    # 반환 좌표는 crop 좌표계라서 원본 좌표로 복원이 필요하면 여기서 처리.
    # 하지만 downstream 은 라인의 '상대 y' 만 쓰므로 crop 좌표 유지로 충분.
    return lines


def _ocr_table_region(img, ocr, region):
    """테이블 영역을 행/열로 분리하여 OCR. 구조화된 행 데이터 반환."""
    rx, ry, rw, rh = int(region["x"]), int(region["y"]), int(region["width"]), int(region["height"])
    col_guides = region.get("colGuides", [])

    img_h, img_w = img.shape[:2]
    x1, y1 = max(0, rx), max(0, ry)
    x2, y2 = min(img_w, rx + rw), min(img_h, ry + rh)
    table_crop = img[y1:y2, x1:x2]
    if table_crop.size == 0:
        return []

    th, tw = table_crop.shape[:2]

    # 업스케일 (작은 테이블)
    if th < 200:
        scale = 200 / th
        table_crop = cv2.resize(table_crop, (int(tw * scale), int(th * scale)), interpolation=cv2.INTER_CUBIC)
        th, tw = table_crop.shape[:2]

    # 전체 테이블 OCR로 텍스트 박스 감지
    ocr_result = ocr.ocr(table_crop)
    lines = _parse_ocr_lines(ocr_result)
    if not lines:
        return []

    # 모든 텍스트 박스 수집
    boxes = []
    for pts, text, conf in lines:
        if not text or conf < 0.3:
            continue
        ys_box = [p[1] for p in pts]
        xs_box = [p[0] for p in pts]
        cy = (min(ys_box) + max(ys_box)) / 2
        cx = (min(xs_box) + max(xs_box)) / 2
        boxes.append({"text": text, "conf": conf, "cx": cx, "cy": cy, "y": min(ys_box)})

    if not boxes:
        return []

    # Y 클러스터링으로 행 분리
    boxes.sort(key=lambda b: b["cy"])
    rows_grouped = []
    current_row = [boxes[0]]
    for b in boxes[1:]:
        if abs(b["cy"] - current_row[-1]["cy"]) < th * 0.025:
            current_row.append(b)
        else:
            rows_grouped.append(current_row)
            current_row = [b]
    rows_grouped.append(current_row)

    # 열 가이드가 있으면 셀 분리, 없으면 X 순서대로
    result_rows = []
    for row_boxes in rows_grouped:
        row_boxes.sort(key=lambda b: b["cx"])

        if col_guides and len(col_guides) > 0:
            # 열 경계: [0, g1, g2, ..., 1.0]
            boundaries = [0.0] + sorted(col_guides) + [1.0]
            cells = []
            for ci in range(len(boundaries) - 1):
                left = boundaries[ci] * tw
                right = boundaries[ci + 1] * tw
                cell_texts = []
                cell_confs = []
                for b in row_boxes:
                    if left <= b["cx"] < right:
                        cell_texts.append(b["text"])
                        cell_confs.append(b["conf"])
                cells.append({
                    "value": " ".join(cell_texts) if cell_texts else "",
                    "confidence": round(sum(cell_confs) / len(cell_confs), 4) if cell_confs else 0.0,
                })
            result_rows.append(cells)
        else:
            cells = [{"value": b["text"], "confidence": b["conf"]} for b in row_boxes]
            result_rows.append(cells)

    avg_conf = 0.0
    total = 0
    for row in result_rows:
        for cell in row:
            if cell["confidence"] > 0:
                avg_conf += cell["confidence"]
                total += 1
    avg_conf = round(avg_conf / total, 4) if total > 0 else 0.0

    return result_rows


@app.post("/preprocess/corners")
async def preprocess_corners(file: UploadFile = File(...)):
    """자동 문서 코너 감지 - 정규화된 좌표(0~1) 반환"""
    data = await file.read()
    img = read_image(data, file.filename or "")
    h, w = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 밝은 영역(흰 종이) 기반 감지
    _, bright = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 40))
    bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, k_close, iterations=2)
    k_open = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    bright = cv2.morphologyEx(bright, cv2.MORPH_OPEN, k_open)
    cnts, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    corners = None
    if cnts:
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
        for cnt in cnts[:5]:
            if cv2.contourArea(cnt) < h * w * 0.10:
                continue
            hull = cv2.convexHull(cnt)
            peri = cv2.arcLength(hull, True)
            for eps in [0.02, 0.04, 0.06, 0.08, 0.12]:
                approx = cv2.approxPolyDP(hull, eps * peri, True)
                if len(approx) == 4:
                    pts = approx.reshape(4, 2).astype(np.float32)
                    s = pts.sum(axis=1)
                    d = np.diff(pts, axis=1).flatten()
                    ordered = np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])
                    corners = [{"x": float(p[0]/w), "y": float(p[1]/h)} for p in ordered]
                    break
            if corners:
                break

    # 감지 실패 시 전체 이미지 코너 반환
    if not corners:
        corners = [{"x": 0.05, "y": 0.05}, {"x": 0.95, "y": 0.05}, {"x": 0.95, "y": 0.95}, {"x": 0.05, "y": 0.95}]

    return {"corners": corners, "detected": bool(cnts and corners[0]["x"] != 0.05)}


@app.post("/ocr/extract")
async def ocr_extract(
    file: UploadFile = File(...),
    template_id: str = "",
    regions: str = "",
    corners: str = "",
):
    import time
    start = time.time()

    # ── 계측: 구간별 시간/차원 수집 (구조 변경 없이 측정만) ──
    timings: dict = {}
    def _ms(dt: float) -> float: return round(dt * 1000.0, 1)
    _t_start = start

    data = await file.read()
    _t_read = time.time()
    img = read_image(data, file.filename or "")
    _t_decode = time.time()
    orig_h, orig_w = img.shape[:2]
    timings["image_read_ms"] = _ms(_t_read - _t_start)
    timings["image_decode_ms"] = _ms(_t_decode - _t_read)
    timings["original_image_wh"] = [orig_w, orig_h]

    ocr = get_ocr_engine()
    region_list = json.loads(regions) if regions else []
    timings["engine_acquire_ms"] = _ms(time.time() - _t_decode)

    fields = []
    full_lines = []
    processed_b64 = None
    receipt_fields = {}

    if region_list:
        # === 템플릿 영역 기반 OCR ===
        for idx, region in enumerate(region_list):
            rx = int(region.get("x", 0))
            ry = int(region.get("y", 0))
            rw = int(region.get("width", 0))
            rh = int(region.get("height", 0))
            field_type = region.get("fieldType", "field")
            name = region.get("name", f"field_{idx + 1}")

            if field_type == "table":
                table_rows = _ocr_table_region(img, ocr, region)
                avg_conf = 0.0
                total = 0
                for row in table_rows:
                    for cell in row:
                        if cell.get("confidence", 0) > 0:
                            avg_conf += cell["confidence"]
                            total += 1
                avg_conf = round(avg_conf / total, 4) if total > 0 else 0.0

                fields.append({
                    "name": name,
                    "field_type": "table",
                    "value": json.dumps(table_rows, ensure_ascii=False),
                    "confidence": avg_conf,
                    "bbox": [rx, ry, rw, rh],
                    "table_data": table_rows,
                })
                for row in table_rows:
                    row_text = " | ".join(c["value"] for c in row if c["value"])
                    if row_text:
                        full_lines.append(row_text)
            else:
                text, conf = _ocr_crop_region(img, ocr, rx, ry, rw, rh)
                fields.append({
                    "name": name,
                    "field_type": field_type,
                    "value": text,
                    "confidence": conf,
                    "bbox": [rx, ry, rw, rh],
                })
                if text:
                    full_lines.append(text)
    else:
        # === 전체 이미지 OCR ===
        t1 = time.time()

        # 1. 문서 영역 감지 + 원근 보정
        _t_dd0 = time.time()
        corner_list = json.loads(corners) if corners else []
        if corner_list and len(corner_list) == 4:
            # 프론트에서 코너 좌표를 직접 전달받은 경우
            ih, iw = img.shape[:2]
            src = np.array([[c["x"] * iw, c["y"] * ih] for c in corner_list], dtype=np.float32)
            s = src.sum(axis=1); d = np.diff(src, axis=1).flatten()
            ordered = np.array([src[np.argmin(s)], src[np.argmin(d)], src[np.argmax(s)], src[np.argmax(d)]])
            wt = int(max(np.linalg.norm(ordered[1]-ordered[0]), np.linalg.norm(ordered[2]-ordered[3])))
            ht = int(max(np.linalg.norm(ordered[3]-ordered[0]), np.linalg.norm(ordered[2]-ordered[1])))
            dst = np.array([[0,0],[wt-1,0],[wt-1,ht-1],[0,ht-1]], dtype=np.float32)
            M = cv2.getPerspectiveTransform(ordered, dst)
            doc_img = cv2.warpPerspective(img, M, (wt, ht))
            timings["detect_document_source"] = "corners_provided"
        else:
            doc_img, _ = detect_document(img)
            timings["detect_document_source"] = "auto"
        timings["detect_document_ms"] = _ms(time.time() - _t_dd0)

        # 1-1. 전체 이미지 회전 방향 감지 (0/90/180/270) - 세로로 찍힌 영수증 대응
        _t_orient0 = time.time()
        doc_img, orient_meta = detect_orientation(doc_img, ocr, original_wh=(orig_w, orig_h))
        print(f"[OCR] {orient_meta['detail']}")
        dh, dw = doc_img.shape[:2]
        timings["detect_orientation_ms"] = _ms(time.time() - _t_orient0)
        timings["doc_img_wh_after_orientation"] = [dw, dh]

        # 2. 미리보기용: 기울기 보정 + 최대 2000px + 선명화
        _t_prev0 = time.time()
        doc_deskewed, _ = deskew(doc_img)
        display_max_w = 2000
        ddh, ddw = doc_deskewed.shape[:2]
        if ddw > display_max_w:
            ds = display_max_w / ddw
            display_img = cv2.resize(doc_deskewed, (display_max_w, int(ddh * ds)), interpolation=cv2.INTER_LANCZOS4)
        else:
            display_img = doc_deskewed.copy()
        # 선명화 (언샤프 마스크)
        gaussian = cv2.GaussianBlur(display_img, (0, 0), 2)
        display_img = cv2.addWeighted(display_img, 1.4, gaussian, -0.4, 0)
        disp_h, disp_w = display_img.shape[:2]
        timings["preview_prep_ms"] = _ms(time.time() - _t_prev0)
        timings["display_image_wh"] = [disp_w, disp_h]

        # 3. OCR용 리사이즈: 950px (2차 속도-정확도 균형 보정)
        #    850px는 일반 영수증의 작은 숫자/구분자 인식에서 회귀가 커서 완충 복원.
        #    orientation 최적화로 확보한 이득은 유지하면서 full OCR 정확도를 회복한다.
        _t_ocrp0 = time.time()
        ocr_max_w = 950
        ocr_min_w = 760
        if ddw > ocr_max_w:
            os_ = ocr_max_w / ddw
            ocr_img = cv2.resize(doc_deskewed, (ocr_max_w, int(ddh * os_)), interpolation=cv2.INTER_AREA)
        elif ddw < ocr_min_w:
            os_ = ocr_max_w / ddw
            ocr_img = cv2.resize(doc_deskewed, (ocr_max_w, int(ddh * os_)), interpolation=cv2.INTER_CUBIC)
        else:
            ocr_img = doc_deskewed.copy()

        # 3-1. 대비 강화 (CLAHE on L channel) - 텍스트 선명도 향상
        lab = cv2.cvtColor(ocr_img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe_ocr = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe_ocr.apply(l)
        ocr_img = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

        # 3-2. 언샤프 마스크로 선명화 (텍스트 엣지 강조)
        blur = cv2.GaussianBlur(ocr_img, (0, 0), 1.5)
        ocr_img = cv2.addWeighted(ocr_img, 1.5, blur, -0.5, 0)

        ocr_h, ocr_w = ocr_img.shape[:2]
        _, img_encoded = cv2.imencode('.jpg', ocr_img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        processed_b64 = base64.b64encode(img_encoded.tobytes()).decode('utf-8')
        timings["ocr_image_prep_ms"] = _ms(time.time() - _t_ocrp0)
        timings["ocr_image_wh"] = [ocr_w, ocr_h]
        timings["processed_image_wh"] = [ocr_w, ocr_h]

        # 4. bbox 좌표 스케일: OCR → 미리보기 크기
        bbox_sx = 1.0
        bbox_sy = 1.0

        t2 = time.time()
        print(f"[OCR] preprocess: {t2-t1:.2f}s, ocr: {ocr_w}x{ocr_h}, display: {disp_w}x{disp_h}")

        _t_fullocr0 = time.time()
        result = ocr.ocr(ocr_img)
        t3 = time.time()
        timings["full_ocr_ms"] = _ms(t3 - _t_fullocr0)
        print(f"[OCR] inference: {t3-t2:.2f}s")

        _t_parse0 = time.time()
        ocr_lines_raw = _parse_ocr_lines(result)
        field_idx = 0
        for bbox_points, text, confidence in ocr_lines_raw:
            if not text or len(text) < 1:
                continue
            if confidence < 0.3:
                continue

            xs = [p[0] for p in bbox_points]
            ys = [p[1] for p in bbox_points]
            x, y = min(xs), min(ys)
            w, h = max(xs) - x, max(ys) - y

            if w < 5 or h < 5:
                continue

            field_idx += 1
            fields.append({
                "name": f"field_{field_idx}",
                "field_type": "field",
                "value": text,
                "confidence": round(confidence, 4),
                "bbox": [round(x * bbox_sx), round(y * bbox_sy), round(w * bbox_sx), round(h * bbox_sy)],
            })
            full_lines.append(text)

        timings["parse_and_build_fields_ms"] = _ms(time.time() - _t_parse0)

        # === 2단계 OCR: 문서 분류 + 상/하단 블록 재OCR ===
        _t_cls0 = time.time()
        full_text_joined = "\n".join(full_lines)
        doc_info = classify_document(full_text_joined)
        doc_type = doc_info["type"]
        print(f"[DOC] type={doc_type} scores={doc_info['scores']}")
        timings["classify_document_ms"] = _ms(time.time() - _t_cls0)

        # === 사전 시험 추출 (full_ocr 만으로) — re-OCR 필요성 판단 ===
        _t_pre0 = time.time()
        pre_debug: dict = {}
        pre_fields = extract_receipt_fields(
            ocr_lines_raw,
            upper_lines=None,
            amount_lines=None,
            doc_type=doc_type,
            debug=pre_debug,
        )
        pre_ta = pre_debug.get("total_amount") or {}
        pre_sel = pre_ta.get("selected") or {}
        timings["pre_extract_ms"] = _ms(time.time() - _t_pre0)

        # 상단 블록 re-OCR 스킵 조건:
        #   baseline 상단 품질 복구를 위해 핵심 4필드가 모두 확보된 경우에만 스킵한다.
        #   사업자번호 recall은 유지하되 회사명/대표자/전화/주소 raw가 비어 있으면 upper raw를 다시 본다.
        upper_ready = bool(
            doc_type == "bank_slip" or (
                pre_fields.get("사업자번호") and
                pre_fields.get("회사명") and
                pre_fields.get("대표자") and
                pre_fields.get("tel") and
                pre_fields.get("주소")
            )
        )
        # 하단 금액 re-OCR 스킵 조건:
        #   - bank/form 은 doc_type 정책으로 이미 스킵
        #   - 그 외에도 금액은 프로젝트의 핵심 필드라 더 보수적으로 스킵한다.
        #     단순 comma/won_suffix + score 35 수준은 정확도 회귀가 커서 불충분했다.
        #   - 'selected' 상태이면서, score 가 높고, 하단부 후보이거나 검산/교차검증까지 있으면 스킵
        pre_amount_strong = bool(
            pre_ta.get("status") == "selected"
            and pre_sel
            and pre_sel.get("score", 0) >= 55
            and pre_sel.get("pattern") in ("comma", "won_suffix")
            and (
                pre_sel.get("row_pos", 0) >= 0.55
                or pre_sel.get("verified_by_synth")
                or pre_sel.get("cross_source")
            )
        )

        # 상단 블록 재OCR (조건부)
        _t_ub0 = time.time()
        upper_bbox = _detect_upper_block_bbox(ocr_lines_raw, ocr_h, ocr_w, doc_type=doc_type)
        timings["detect_upper_bbox_ms"] = _ms(time.time() - _t_ub0)
        timings["upper_bbox_ocr_coords"] = list(upper_bbox) if upper_bbox else None
        timings["upper_reocr_skipped_by_pre"] = upper_ready
        upper_lines = []
        if upper_bbox and not upper_ready:
            t_u1 = time.time()
            upper_lines = _reocr_block(ocr_img, ocr, upper_bbox, mode="upper", timings=timings)
            timings["upper_reocr_total_ms"] = _ms(time.time() - t_u1)
            timings["upper_reocr_ran"] = True
            print(f"[REOCR upper] bbox={upper_bbox} lines={len(upper_lines)} took={time.time()-t_u1:.2f}s")
        else:
            timings["upper_reocr_total_ms"] = 0.0
            timings["upper_reocr_ran"] = False
            if upper_ready:
                print(f"[REOCR upper] skipped (pre-extract 로 사업자/전화/주소 확보)")

        # 하단 금액 블록 재OCR (조건부)
        #   - bank_slip / form_or_handwritten: 스킵 ('거래금액/잔액'이 합계로 증폭되는 오탐 / 수기 복구 난이도)
        #   - 그 외: pre_amount_strong 이면 스킵
        _t_ab0 = time.time()
        amount_bbox = None
        amount_lines = []
        skip_by_doc = doc_type in ("bank_slip", "form_or_handwritten")
        if not skip_by_doc:
            amount_bbox = _detect_amount_block_bbox(ocr_lines_raw, ocr_h, ocr_w, doc_type=doc_type)
        timings["detect_amount_bbox_ms"] = _ms(time.time() - _t_ab0)
        timings["amount_bbox_ocr_coords"] = list(amount_bbox) if amount_bbox else None
        timings["amount_reocr_skipped_by_doc_type"] = skip_by_doc
        timings["amount_reocr_skipped_by_pre"] = (not skip_by_doc) and pre_amount_strong
        if amount_bbox and not pre_amount_strong:
            t_a1 = time.time()
            amount_lines = _reocr_block(ocr_img, ocr, amount_bbox, mode="amount", timings=timings)
            timings["amount_reocr_total_ms"] = _ms(time.time() - t_a1)
            timings["amount_reocr_ran"] = True
            print(f"[REOCR amount] bbox={amount_bbox} lines={len(amount_lines)} took={time.time()-t_a1:.2f}s")
        else:
            timings["amount_reocr_total_ms"] = 0.0
            timings["amount_reocr_ran"] = False
            if pre_amount_strong and not skip_by_doc:
                print(f"[REOCR amount] skipped (pre-extract strong candidate score={pre_sel.get('score')})")

        # bbox 기반 구조화 필드 추출 (2단계 소스 주입)
        _t_extract0 = time.time()
        extract_debug: dict = {"document_classification": doc_info}
        receipt_fields = extract_receipt_fields(
            ocr_lines_raw,
            upper_lines=upper_lines,
            amount_lines=amount_lines,
            doc_type=doc_type,
            debug=extract_debug,
        )
        _repair_remaining_top_fields_from_text_lines(receipt_fields, full_lines)
        timings["field_extract_ms"] = _ms(time.time() - _t_extract0)
        # 재OCR bbox 를 display 좌표계로도 남김 (프론트에서 시각화 시 활용 가능)
        if upper_bbox:
            ux, uy, uw, uh = upper_bbox
            extract_debug["upper_block_bbox"] = [round(ux * bbox_sx), round(uy * bbox_sy),
                                                  round(uw * bbox_sx), round(uh * bbox_sy)]
            extract_debug["upper_block_used"] = len(upper_lines) > 0
            extract_debug["upper_block_ocr_text"] = "\n".join(t for _, t, _ in upper_lines)
        if amount_bbox:
            ax, ay, aw, ah = amount_bbox
            extract_debug["amount_block_bbox"] = [round(ax * bbox_sx), round(ay * bbox_sy),
                                                   round(aw * bbox_sx), round(ah * bbox_sy)]
            extract_debug["amount_block_used"] = len(amount_lines) > 0
            extract_debug["amount_block_ocr_text"] = "\n".join(t for _, t, _ in amount_lines)

        # 금액 추출 디버그 로그 (원인별 추적)
        #   status: no_candidate / low_confidence / all_rejected / selected /
        #           suppressed_bank_slip / suppressed_handwritten / suppressed_unknown_bare
        ta = extract_debug.get("total_amount") or {}
        if ta:
            sel = ta.get("selected")
            rej = ta.get("rejected_top") or []
            rej_summary = ",".join(f"{r['value']}({r['score']})" for r in rej[:3]) if rej else "-"
            review_flag = "REVIEW" if extract_debug.get("total_amount_review_required") else "ok"
            print(
                f"[AMOUNT] doc={doc_type} status={ta.get('status')} "
                f"review={review_flag} "
                f"selected={sel['value'] if sel else '-'} "
                f"score={sel['score'] if sel else '-'} "
                f"pattern={sel.get('pattern') if sel else '-'} "
                f"src={extract_debug.get('field_sources', {}).get('총합계금액', '-')} "
                f"synth_from={sel.get('synth_from') if sel else '-'} "
                f"cands={extract_debug.get('candidate_counts')} "
                f"rejected_top={rej_summary}"
            )

    _t_resp0 = time.time()
    elapsed = time.time() - start

    response = {
        "fields": fields,
        "full_text": "\n".join(full_lines),
        "receipt_fields": receipt_fields,
        "processing_time": round(elapsed, 2),
    }
    # finance_profile Tier-1 추출: doc_type == "bank_slip" 분기에서만 실행
    # _apply_doc_type_amount_policy / receipt_fields 완전 무수정 (docs/FINANCE_PARSER_TARGET §5.2)
    if doc_type == "bank_slip":
        try:
            from extractors.finance_slip import extract_finance_fields  # local import: 기존 영역 오염 방지
            _fin = extract_finance_fields("\n".join(full_lines))
            _review = _fin.pop("_reviewReasons", [])  # 내부 감사 정보 분리
            response["finance_fields"] = _fin
            if _review:
                response["finance_review_reasons"] = _review
            print(f"[finance] bankName={_fin.get('bankName')} txType={_fin.get('transactionType')} "
                  f"dt={_fin.get('transactionDateTime')} amount={_fin.get('amount')} "
                  f"review={_review}")
        except Exception as _fe:
            print(f"[finance_slip] extractor error (응답 영향 없음): {_fe}")

    if processed_b64:
        response["processed_image"] = f"data:image/jpeg;base64,{processed_b64}"
    # 금액 추출 디버그 메타 (프론트 TEST 탭에서 활용 가능)
    if not region_list:
        # 계측 메타 주입: 구간 시간/차원/디바이스
        timings["total_ms"] = _ms(elapsed)
        timings["paddle_device"] = "cpu"  # get_ocr_engine() 에서 device='cpu' 고정
        timings["cpu_threads"] = os.cpu_count() or 0
        timings["debug_mode"] = True  # 비-템플릿 경로는 항상 extract_debug 포함
        extract_debug["timings"] = timings
        response["extract_debug"] = extract_debug
        # 최상위에도 검토 필요 플래그 노출 (프론트가 extract_debug 파싱 안 해도 읽도록)
        response["total_amount_review_required"] = bool(
            extract_debug.get("total_amount_review_required")
        )
        if extract_debug.get("total_amount_review_required"):
            response["total_amount_review_code"] = extract_debug.get("total_amount_review_code", "")
            response["total_amount_review_reason"] = extract_debug.get("total_amount_review_reason", "")
        response["doc_type"] = extract_debug.get("doc_type", "unknown")

        # --- 검수/운영 로그 append (best-effort; 실패해도 응답에는 영향 없음) ---
        try:
            # 필드별 confidence 는 fields 리스트에서 이름으로 매칭 (있으면)
            conf_by_name = {f.get("name"): f.get("confidence") for f in fields if "name" in f}
            log_entry = _build_auto_extract_log(
                image_id=(file.filename or ""),
                doc_type=extract_debug.get("doc_type", "unknown"),
                doc_classification=extract_debug.get("document_classification") or {},
                extract_debug=extract_debug,
                receipt_fields=receipt_fields,
                field_confidences=conf_by_name,
                full_text="\n".join(full_lines),
                upper_block_text=extract_debug.get("upper_block_ocr_text", ""),
                amount_block_text=extract_debug.get("amount_block_ocr_text", ""),
                processing_time=round(elapsed, 2),
            )
            # 계측 메타를 로그 엔트리에 포함 — 추후 review-log 조회로 aggregate 분석 가능
            log_entry["timings"] = timings
            _append_review_log(log_entry)
        except Exception as e:
            print(f"[review_log] auto_extract build failed: {e}")

        # 응답 조립 후 최종 timing (parse+assemble+log 까지 포함)
        timings["response_assembly_ms"] = _ms(time.time() - _t_resp0)

        # === 구간 요약 로그 ===
        _top_slowest = sorted(
            ((k, v) for k, v in timings.items()
             if k.endswith("_ms") and isinstance(v, (int, float))),
            key=lambda kv: -kv[1],
        )[:5]
        print(
            f"[TIMING] file={file.filename} total={timings.get('total_ms')}ms "
            f"orig={timings.get('original_image_wh')} ocr_img={timings.get('ocr_image_wh')} "
            f"doc={extract_debug.get('doc_type')} "
            f"upper_ran={timings.get('upper_reocr_ran')} amount_ran={timings.get('amount_reocr_ran')} "
            f"slowest5=" + ",".join(f"{k}={v}" for k, v in _top_slowest)
        )

    return response


@app.post("/ocr/revalidate")
async def ocr_revalidate(
    file: UploadFile = File(...),
    regions: str = Query(default=""),
):
    """지정된 bbox 영역만 크롭해서 다시 OCR 실행"""
    import time
    data = await file.read()
    img = read_image(data, file.filename or "")
    print(f"[revalidate] file={file.filename}, size={img.shape}, regions_len={len(regions)}, regions_preview={regions[:120]}")

    region_list = json.loads(regions) if regions else []
    print(f"[revalidate] parsed {len(region_list)} regions")
    ocr = get_ocr_engine()
    results = []

    for region in region_list:
        bbox = region["bbox"]  # [x, y, w, h]
        x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

        # 여유 마진: 과도하면 주변 글자 포함돼 오인식 → 적정 범위로 제한
        margin = max(12, min(int(h * 0.15), 25))
        img_h, img_w = img.shape[:2]
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(img_w, x + w + margin)
        y2 = min(img_h, y + h + margin)

        cropped = img[y1:y2, x1:x2]
        if cropped.size == 0:
            results.append({"value": "", "confidence": 0})
            continue

        # 작은 영역 업스케일 (최소 높이 80px) - 크기별 보간 방식 차등 적용
        ch, cw = cropped.shape[:2]
        if ch < 80:
            scale = 80 / ch
            interp = cv2.INTER_LANCZOS4 if scale > 3 else cv2.INTER_CUBIC
            cropped = cv2.resize(cropped, (int(cw * scale), int(ch * scale)), interpolation=interp)

        # 크롭 이미지 대비 강화 (CLAHE on L channel)
        lab = cv2.cvtColor(cropped, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        cropped = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

        # 선명화 (언샤프 마스크)
        blur = cv2.GaussianBlur(cropped, (0, 0), 1.2)
        cropped = cv2.addWeighted(cropped, 1.5, blur, -0.5, 0)

        # OCR 실행
        ocr_result = ocr.ocr(cropped)

        best_text = ""
        best_conf = 0.0
        for _, text, conf in _parse_ocr_lines(ocr_result):
            if conf > best_conf and conf >= 0.3:
                best_text = text
                best_conf = conf

        results.append({
            "value": best_text,
            "confidence": round(best_conf, 4),
        })

    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9099)
