/**
 * FALLBACK ONLY
 * 서버(ocr-server)가 receipt_fields를 반환하면 그것을 최우선 사용.
 * 이 모듈은 receipt_fields가 비어 있을 때에만 호출한다.
 * (서버 규칙과 다를 수 있으므로 최소한으로만 유지)
 */

import { Entry, EMPTY_ENTRY } from "./types";
import { normalizeBizNumber } from "@/lib/bizNumber";

// OCR 오인식 보정: O→0, l/I→1, S→5, B→8, .→, (천단위)
export function cleanNumberString(s: string): string {
  return s
    .replace(/O/g, "0")
    .replace(/[lI]/g, "1")
    .replace(/S/g, "5")
    .replace(/B/g, "8")
    .replace(/(\d)\.(\d{3})/g, "$1,$2");
}

// 천단위 콤마 금액 추출 + 범위 필터 (100 ~ 1억)
export function parseAmounts(s: string): string[] {
  return (cleanNumberString(s).match(/\d{1,3}(?:,\d{3})+/g) ?? []).filter((n) => {
    const v = parseInt(n.replace(/,/g, ""));
    return v >= 100 && v <= 100_000_000;
  });
}

export function extractFieldsFallback(fullText: string): Entry {
  const lines = fullText.split("\n").map((l) => l.trim()).filter(Boolean);
  const r = EMPTY_ENTRY();

  for (const line of lines) {
    if (!r.사업자번호) {
      const cleaned = cleanNumberString(line).replace(/O/g, "0");
      const m = cleaned.match(/[1-9]\d{2}[-\s]?\d{2}[-\s]?\d{5}/);
      if (m) r.사업자번호 = m[0].replace(/\s/g, "-");
    }
    if (!r.tel) {
      const m = line.match(/0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}/);
      if (m) r.tel = m[0].replace(/\s/g, "-");
    }
    if (!r.주소 && /^(서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)/.test(line)) {
      r.주소 = line;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const norm = lines[i].replace(/\s+/g, "");

    if (!r.회사명 && /상호|가맹점명|점명|업체명/.test(norm)) {
      const same = lines[i].replace(/.*(?:상\s*호|가\s*맹\s*점\s*명|점\s*명|업\s*체\s*명)\s*[:\s]*/u, "").trim();
      r.회사명 = same.length >= 1 ? same : (lines[i + 1] ?? "");
    }
    if (!r.대표자 && /대표자/.test(norm)) {
      const same = lines[i].replace(/.*대\s*표\s*자\s*[:\s]*/, "").trim();
      r.대표자 = same.length >= 1 && same.length <= 20 ? same : (lines[i + 1] ?? "");
    }
    if (!r.주소 && /^주소[:\s]|^주소$/.test(norm)) {
      const same = lines[i].replace(/^주\s*소\s*[:\s]*/, "").trim();
      r.주소 = same.length > 4 ? same : (lines[i + 1] ?? "");
    }

    const isAmountKeyword =
      /합계|총액|결제금액|청구금액|지불금액|받을금액|전체합계|합계금액|실결제|total/i.test(norm) ||
      /^[합계총]$/.test(norm);
    if (!r.총합계금액 && isAmountKeyword) {
      const big = parseAmounts(lines[i]);
      if (big.length) { r.총합계금액 = big[big.length - 1]; continue; }
      const candidates: string[] = [];
      for (let j = i + 1; j <= Math.min(i + 3, lines.length - 1); j++) {
        candidates.push(...parseAmounts(lines[j] ?? ""));
      }
      if (candidates.length) {
        r.총합계금액 = candidates.reduce((a, b) =>
          parseInt(a.replace(/,/g, "")) >= parseInt(b.replace(/,/g, "")) ? a : b
        );
      }
    }
  }

  if (!r.총합계금액) {
    const bottomLines = lines.slice(Math.floor(lines.length * 0.5));
    const allAmounts: string[] = [];
    for (const line of bottomLines) allAmounts.push(...parseAmounts(line));
    if (allAmounts.length) {
      r.총합계금액 = allAmounts.reduce((a, b) =>
        parseInt(a.replace(/,/g, "")) >= parseInt(b.replace(/,/g, "")) ? a : b
      );
    }
  }

  return r;
}

// ---------- 정규화 (OCR raw → OCR normalized) ----------

export function normalizePhone(raw: string): string {
  if (!raw) return "";
  const digits = raw.replace(/\D/g, "");
  if (digits.startsWith("02")) {
    if (digits.length === 10) return `${digits.slice(0, 2)}-${digits.slice(2, 6)}-${digits.slice(6)}`;
    if (digits.length === 9)  return `${digits.slice(0, 2)}-${digits.slice(2, 5)}-${digits.slice(5)}`;
  }
  if (digits.length === 11) return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
  if (digits.length === 10) return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`;
  return raw.trim();
}

export function normalizeAmount(raw: string): string {
  if (!raw) return "";
  const digits = cleanNumberString(raw).replace(/[^\d]/g, "");
  if (!digits) return "";
  return parseInt(digits).toLocaleString("en-US");
}

export function normalizeEntry(raw: Entry): Entry {
  const biz = raw.사업자번호 ? (normalizeBizNumber(raw.사업자번호) ?? raw.사업자번호.trim()) : "";
  return {
    회사명: raw.회사명.trim(),
    사업자번호: biz,
    대표자: raw.대표자.trim(),
    tel: normalizePhone(raw.tel),
    주소: raw.주소.trim(),
    총합계금액: normalizeAmount(raw.총합계금액),
  };
}
