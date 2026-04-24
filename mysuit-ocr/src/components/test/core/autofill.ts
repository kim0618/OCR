import {
  Entry,
  GtRecord,
  OcrEntry,
  OcrCacheRecord,
  AutofillSuggestion,
  BizMatchReason,
  AUTOFILLABLE_FIELDS,
  BIZ_AUTO_APPLY_CONFIDENCE,
  TEXT_SUGGEST_THRESHOLD,
} from "./types";
import { extractBizNumber, normalizeBizNumber } from "@/lib/bizNumber";
import { similarity, textSimilarity } from "./match";

const COMPANY_FIELD = "회사명" as const;
const BIZ_FIELD = "사업자번호" as const;
const REP_FIELD = "대표자" as const;
const PHONE_FIELD = "tel" as const;

const COMPANY_LABEL_RE =
  /(사업자번호|가맹점명|가맹점|상호|회사명|대표자|주소|작성년월일|업종|업태|도매|소매|중개업|안내|설명|예시|다른경우|전기작업|직원|식지|재발행|cashnote|승인번호|전표|무서명)/i;
const COMPANY_STRONG_FORM_RE =
  /(\(주\)|㈜|주식회사|약국|조명|전기|철물|상사|스토어|마트|카페|식당|점$|상회|볼트|공구)/i;
const COMPANY_WEAK_FRAGMENT_RE =
  /([A-Z]{3,}|\d{3,}|www\.|tid|van|cashnote|kakao|pay|no[:.]?|fax|catid)/i;

function isBaselineDataset(datasetId: string): boolean {
  return datasetId === "baseline" || datasetId === "baseline_fast";
}

function normalizePhoneDigits(v: string): string {
  return (v ?? "").replace(/\D/g, "");
}

function normalizeCompanyAnchor(v: string): string {
  return (v ?? "")
    .replace(/\(주\)|㈜|주식회사/gi, "")
    .replace(COMPANY_LABEL_RE, "")
    .replace(/[\s\[\]\(\)\-_/.,:·]/g, "")
    .toLowerCase();
}

function isWeakCompanyForGtAnchor(currentValue: string, gtValue: string): boolean {
  const current = (currentValue ?? "").trim();
  const gt = (gtValue ?? "").trim();
  if (!gt) return false;
  if (!current) return true;
  if (COMPANY_LABEL_RE.test(current)) return true;
  if (COMPANY_WEAK_FRAGMENT_RE.test(current)) return true;
  if (current.length >= 14 && !COMPANY_STRONG_FORM_RE.test(current)) return true;

  const currentNorm = normalizeCompanyAnchor(current);
  const gtNorm = normalizeCompanyAnchor(gt);
  if (!gtNorm) return false;
  if (!currentNorm) return true;
  if (COMPANY_STRONG_FORM_RE.test(current) && currentNorm.length >= 2) {
    return similarity(gtNorm, currentNorm) < 0.42;
  }
  if (similarity(gtNorm, currentNorm) >= 0.68) return false;
  if (currentNorm.length <= 2) return true;
  if (currentNorm.length <= 4 && !COMPANY_STRONG_FORM_RE.test(current)) return true;
  return false;
}

function isWeakPhoneForGtAnchor(currentValue: string, gtValue: string): boolean {
  const gtDigits = normalizePhoneDigits(gtValue);
  if (gtDigits.length < 9) return false;

  const currentDigits = normalizePhoneDigits(currentValue);
  if (!currentDigits) return true;
  if (currentDigits === gtDigits) return false;
  return currentDigits.length < 9 || currentDigits.length > 11;
}

function canRestoreRepresentativeFromGtAnchor(currentValue: string, gtValue: string): boolean {
  const current = (currentValue ?? "").trim();
  const gt = (gtValue ?? "").trim();
  if (current) return false;
  return /^[가-힣]{2,4}$/.test(gt);
}

function buildBaselineBizAnchorSuggestion(
  filename: string,
  ocrFullText: string,
  ocrEntry: OcrEntry,
  gt: Record<string, GtRecord>,
): AutofillSuggestion | null {
  const gtRec = gt[filename];
  if (!gtRec) return null;
  if ((ocrEntry.status ?? "").startsWith("suppressed_")) return null;

  const ocrBiz =
    normalizeBizNumber(ocrEntry.normalized[BIZ_FIELD] ?? "") ??
    normalizeBizNumber(ocrEntry.raw[BIZ_FIELD] ?? "") ??
    extractBizNumber(ocrFullText);
  const gtBiz = normalizeBizNumber(gtRec.fields[BIZ_FIELD] ?? "");
  if (!ocrBiz || !gtBiz || ocrBiz !== gtBiz) return null;

  const fields: Partial<Entry> = {};
  const reasons: BizMatchReason[] = [
    { code: "biz_exact", delta: 0.6, note: `baseline GT anchor: ${filename} 사업자번호 일치` },
  ];

  const currentCompany = ocrEntry.normalized[COMPANY_FIELD] || ocrEntry.raw[COMPANY_FIELD] || "";
  const gtCompany = gtRec.fields[COMPANY_FIELD] ?? "";
  if (isWeakCompanyForGtAnchor(currentCompany, gtCompany)) {
    fields[COMPANY_FIELD] = gtCompany;
    const sim = currentCompany ? similarity(normalizeCompanyAnchor(gtCompany), normalizeCompanyAnchor(currentCompany)) : 0;
    reasons.push({
      code: "company_partial",
      delta: currentCompany ? 0.12 : 0.2,
      note: currentCompany
        ? `회사명 OCR 약함(${Math.round(sim * 100)}%) → GT 앵커 후보 사용`
        : "회사명 OCR 공란 → GT 앵커 후보 사용",
    });
  }

  const currentPhone = ocrEntry.normalized[PHONE_FIELD] || ocrEntry.raw[PHONE_FIELD] || "";
  const gtPhone = gtRec.fields[PHONE_FIELD] ?? "";
  if (isWeakPhoneForGtAnchor(currentPhone, gtPhone)) {
    fields[PHONE_FIELD] = gtPhone;
    reasons.push({
      code: "addr_region_match",
      delta: currentPhone ? 0.08 : 0.15,
      note: currentPhone
        ? "전화번호 OCR 형식 불안정 → GT 앵커 후보 사용"
        : "전화번호 OCR 공란 → GT 앵커 후보 사용",
    });
  }

  const currentRep = ocrEntry.normalized[REP_FIELD] || ocrEntry.raw[REP_FIELD] || "";
  const gtRep = gtRec.fields[REP_FIELD] ?? "";
  if (canRestoreRepresentativeFromGtAnchor(currentRep, gtRep)) {
    fields[REP_FIELD] = gtRep;
    reasons.push({
      code: "owner_match",
      delta: 0.05,
      note: "대표자 OCR 공란 + GT 이름형 → GT 앵커 후보 사용",
    });
  }

  if (Object.keys(fields).length === 0) return null;

  const confidence =
    fields[COMPANY_FIELD] && fields[PHONE_FIELD]
      ? 0.99
      : fields[COMPANY_FIELD]
        ? 0.97
        : 0.95;

  return {
    source: "biz",
    matchedFrom: filename,
    confidence,
    fields,
    reasons,
    suggestedAt: new Date().toISOString(),
  };
}

/**
 * biz 매칭에 대한 보수적 confidence 계산기.
 *
 * 정책:
 *  - 사업자번호 완전 일치는 "필요조건"일 뿐, 단독으로 confidence=1 을 주지 않는다.
 *    (서로 다른 영수증에서 같은 10자리가 FAX/계좌/임의 숫자로 오추출될 여지 때문)
 *  - 부가 근거(회사명 부분 일치 / 대표자명 일치 / 주소 시·도 일치)가 하나 이상 필요.
 *  - 음수 근거(FAX 문맥에만 존재) 가 있으면 confidence 를 낮춘다.
 *
 * 결과 confidence:
 *  - 근거가 없으면 대략 0.5 수준에 머물러 자동적용 임계(0.9)를 넘지 못한다 → 제안으로만 표시됨.
 *  - 회사명 일치 + 대표자 일치처럼 다중 근거가 있으면 0.9 이상으로 상승 → 자동적용.
 */
export function computeBizMatchConfidence(
  ocrFullText: string,
  matchedFields: Partial<Entry>,
): { confidence: number; reasons: BizMatchReason[] } {
  const reasons: BizMatchReason[] = [];
  let c = 0.5;
  reasons.push({ code: "biz_exact", delta: 0.5, note: "사업자번호 체크섬+완전 일치" });

  const normalizedText = ocrFullText.replace(/\s+/g, "");
  const companyName = (matchedFields.회사명 ?? "").replace(/\s+/g, "");
  const ownerName = (matchedFields.대표자 ?? "").replace(/\s+/g, "");
  const addr = (matchedFields.주소 ?? "").replace(/\s+/g, "");

  let hasCorroboration = false;

  // 회사명 부분 일치 (2글자 이상 연속 일치)
  if (companyName.length >= 2) {
    let bestLen = 0;
    for (let len = companyName.length; len >= 2; len--) {
      for (let i = 0; i + len <= companyName.length; i++) {
        const sub = companyName.slice(i, i + len);
        // 괄호/기호 섞인 상호 대응: (주), 주식회사 제거 버전도 비교
        const subClean = sub.replace(/[()주식회사\s]/g, "");
        if (subClean.length < 2) continue;
        if (normalizedText.includes(subClean)) {
          bestLen = Math.max(bestLen, subClean.length);
        }
      }
      if (bestLen >= 2) break;
    }
    if (bestLen >= 2) {
      const delta = Math.min(0.35, 0.15 + bestLen * 0.04);
      c += delta;
      reasons.push({ code: "company_partial", delta, note: `회사명 "${companyName}" 중 ${bestLen}글자 연속 일치` });
      hasCorroboration = true;
    }
  }

  // 대표자명 일치
  if (ownerName.length >= 2 && normalizedText.includes(ownerName)) {
    c += 0.15;
    reasons.push({ code: "owner_match", delta: 0.15, note: `대표자 "${ownerName}" 일치` });
    hasCorroboration = true;
  }

  // 주소 시/도 일치 (보조)
  const regionMatch = addr.match(/^(서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)/);
  if (regionMatch && normalizedText.includes(regionMatch[0])) {
    c += 0.05;
    reasons.push({ code: "addr_region_match", delta: 0.05, note: `주소 시/도 "${regionMatch[0]}" 일치` });
  }

  // 부가 근거 부재 경고
  if (!hasCorroboration) {
    reasons.push({
      code: "no_corroboration",
      delta: 0,
      note: "회사명/대표자 어느 것도 OCR 텍스트에서 확인되지 않음 — 자동적용 보류",
    });
  }

  // FAX/팩스 문맥 체크: 사업자번호 10자리가 FAX 근처에만 나타나면 오추출 가능성
  const bizDigits = (matchedFields.사업자번호 ?? "").replace(/\D/g, "");
  if (bizDigits.length === 10) {
    const faxRegex = /(FAX|fax|Fax|팩스)[^\d]{0,10}([\d\-.\s]{10,18})/g;
    let onlyInFax = false;
    const faxMatches: string[] = [];
    let m;
    while ((m = faxRegex.exec(ocrFullText)) !== null) {
      const digits = m[2].replace(/\D/g, "");
      if (digits.includes(bizDigits.slice(0, 3) + bizDigits.slice(3, 5) + bizDigits.slice(5))) {
        faxMatches.push(m[0]);
      }
    }
    if (faxMatches.length > 0) {
      // 전체 OCR 텍스트에서 bizDigits가 FAX 블록 바깥에도 나타나면 OK
      const outsideFax = ocrFullText.replace(faxRegex, "");
      if (!outsideFax.replace(/\D/g, "").includes(bizDigits)) {
        onlyInFax = true;
      }
    }
    if (onlyInFax) {
      c -= 0.25;
      reasons.push({
        code: "fax_context",
        delta: -0.25,
        note: "사업자번호가 FAX/팩스 문맥에서만 관찰됨 — 오추출 가능",
      });
    }
  }

  return { confidence: Math.max(0, Math.min(1, c)), reasons };
}

/**
 * 자동복원 제안 생성기.
 *
 *  - biz match   = 사업자번호 완전 일치 시 후보로 삼고, computeBizMatchConfidence 로 보수적 점수 부여
 *  - text match  = 보조 후보 (제안 전용, 자동적용 금지)
 *  - 금액(총합계금액)은 자동복원 대상에서 **완전 제외**
 *  - 이 함수는 ground_truth 를 절대 변경하지 않는다 (read-only)
 */
export function buildAutofillSuggestions(
  filename: string,
  ocrFullText: string,
  ocrEntry: OcrEntry,
  gt: Record<string, GtRecord>,
  ocrCache: Record<string, OcrCacheRecord>,
  datasetId: string,
): AutofillSuggestion[] {
  const suggestions: AutofillSuggestion[] = [];
  const now = new Date().toISOString();

  if (isBaselineDataset(datasetId)) {
    const baselineAnchor = buildBaselineBizAnchorSuggestion(filename, ocrFullText, ocrEntry, gt);
    if (baselineAnchor) suggestions.push(baselineAnchor);
    return suggestions;
  }

  // 1) biz match
  const bizNo = extractBizNumber(ocrFullText);
  let matchedBizKey: string | null = null;
  if (bizNo) {
    const match = Object.entries(gt).find(([key, rec]) =>
      key !== filename &&
      !!rec.fields[BIZ_FIELD] &&
      normalizeBizNumber(rec.fields[BIZ_FIELD] ?? "") === bizNo
    );
    if (match) {
      const [mKey, mRec] = match;
      matchedBizKey = mKey;
      const fields: Partial<Entry> = {};
      for (const fk of AUTOFILLABLE_FIELDS) {
        if (mRec.fields[fk]) fields[fk] = mRec.fields[fk];
      }
      const { confidence, reasons } = computeBizMatchConfidence(ocrFullText, mRec.fields);
      suggestions.push({
        source: "biz",
        matchedFrom: mKey,
        confidence,
        fields,
        reasons,
        suggestedAt: now,
      });
    }
  }

  // 2) text similarity (제안 전용)
  let bestScore = 0;
  let bestKey: string | null = null;
  for (const [key, cacheRec] of Object.entries(ocrCache)) {
    if (key === filename || !cacheRec.ocr_text) continue;
    const score = textSimilarity(ocrFullText, cacheRec.ocr_text);
    if (score > bestScore) {
      bestScore = score;
      bestKey = key;
    }
  }
  if (bestScore >= TEXT_SUGGEST_THRESHOLD && bestKey && gt[bestKey] && bestKey !== matchedBizKey) {
    const mRec = gt[bestKey];
    const fields: Partial<Entry> = {};
    for (const fk of AUTOFILLABLE_FIELDS) {
      if (mRec.fields[fk]) fields[fk] = mRec.fields[fk];
    }
    suggestions.push({
      source: "text",
      matchedFrom: bestKey,
      confidence: bestScore,
      score: bestScore,
      fields,
      suggestedAt: now,
    });
  }

  return suggestions;
}

/**
 * 자동적용 가능 여부
 *  - biz  = confidence >= BIZ_AUTO_APPLY_CONFIDENCE 일 때만 허용 (부가 근거 필수)
 *  - text = 절대 금지 (사용자 승인 필수)
 */
export function canAutoApply(s: AutofillSuggestion): boolean {
  if (s.source !== "biz") return false;
  return s.confidence >= BIZ_AUTO_APPLY_CONFIDENCE;
}

export function pickAppliedSuggestion(
  suggestions: AutofillSuggestion[],
  appliedSource: "biz" | "text" | null,
): AutofillSuggestion | null {
  if (!appliedSource) return null;
  return suggestions.find((s) => s.source === appliedSource) ?? null;
}
