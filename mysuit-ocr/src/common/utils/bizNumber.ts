/**
 * 사업자등록번호 정규화 + 체크섬 검증
 *
 * 입력: 다양한 표기 (138-81-68468 / 1388168468 / 138 81 68468 / 138.81.68468 ...)
 * 출력: "138-81-68468" (표준 형식) 또는 null (유효하지 않음)
 */

export function normalizeBizNumber(raw: string): string | null {
  // 숫자만 추출
  const digits = raw.replace(/\D/g, "");

  // 10자리여야 함
  if (digits.length !== 10) return null;

  // 체크섬 검증
  if (!validateChecksum(digits)) return null;

  // XXX-XX-XXXXX 포맷으로 반환
  return `${digits.slice(0, 3)}-${digits.slice(3, 5)}-${digits.slice(5)}`;
}

/**
 * 사업자등록번호 체크섬 알고리즘
 * 가중치: [1,3,7,1,3,7,1,3,5], 9번째 자리는 (d*5 + floor(d*5/10)) 방식
 */
function validateChecksum(digits: string): boolean {
  const weights = [1, 3, 7, 1, 3, 7, 1, 3, 5];
  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(digits[i]) * weights[i];
  }
  // 9번째 자리 처리 (인덱스 8)
  sum += Math.floor((parseInt(digits[8]) * 5) / 10);
  const checkDigit = (10 - (sum % 10)) % 10;
  return checkDigit === parseInt(digits[9]);
}

/**
 * 흔한 OCR 오인식 문자 → 숫자 매핑
 * O/o → 0, I/l → 1, S → 5, B → 8, Z → 2, G → 6
 */
const OCR_CHAR_FIXES: Record<string, string> = {
  O: "0", o: "0", Q: "0", D: "0",
  I: "1", l: "1", "|": "1",
  Z: "2", z: "2",
  S: "5", s: "5",
  G: "6", b: "6",
  T: "7",
  B: "8",
  g: "9", q: "9",
};

function applyCharFixes(raw: string): string {
  let fixed = "";
  for (const ch of raw) {
    fixed += OCR_CHAR_FIXES[ch] ?? ch;
  }
  return fixed;
}

/**
 * OCR 텍스트에서 사업자번호 추출 + 정규화
 * 1차: 그대로 매칭
 * 2차: OCR 오인식 문자 교정 후 재시도 (O→0, I→1 등)
 */
export function extractBizNumber(text: string): string | null {
  // 1차: 원본 그대로 체크섬 검증
  const pattern = /[1-9]\d{2}[\s\-.]?\d{2}[\s\-.]?\d{5}/g;
  const candidates = text.match(pattern) ?? [];
  for (const candidate of candidates) {
    const normalized = normalizeBizNumber(candidate);
    if (normalized) return normalized;
  }

  // 2차: 문자 교정 후 재매칭 (O→0 등)
  const fixed = applyCharFixes(text);
  const fixedCandidates = fixed.match(pattern) ?? [];
  for (const candidate of fixedCandidates) {
    const normalized = normalizeBizNumber(candidate);
    if (normalized) return normalized;
  }

  // 3차: 숫자+문자 혼합 10자리 패턴 (예: "138-8I-6846O" 같은 케이스)
  const loosePattern = /[1-9IlZzSsGbTBgq]{1}[0-9OoIlZzSsGbTBgq|DQ]{2}[\s\-.]?[0-9OoIlZzSsGbTBgq|DQ]{2}[\s\-.]?[0-9OoIlZzSsGbTBgq|DQ]{5}/g;
  const looseCandidates = text.match(loosePattern) ?? [];
  for (const candidate of looseCandidates) {
    const normalized = normalizeBizNumber(applyCharFixes(candidate));
    if (normalized) return normalized;
  }

  return null;
}
