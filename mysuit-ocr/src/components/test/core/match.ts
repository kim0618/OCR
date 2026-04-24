import { MATCH_THRESHOLD } from "./types";

export function normalizeForCompare(v: string): string {
  return v.replace(/[\s\-,.:원()]/g, "").toLowerCase();
}

export function levenshtein(a: string, b: string): number {
  if (!a.length) return b.length;
  if (!b.length) return a.length;
  const dp: number[][] = Array.from({ length: a.length + 1 }, () =>
    new Array(b.length + 1).fill(0)
  );
  for (let i = 0; i <= a.length; i++) dp[i][0] = i;
  for (let j = 0; j <= b.length; j++) dp[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      if (a[i - 1] === b[j - 1]) dp[i][j] = dp[i - 1][j - 1];
      else dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
    }
  }
  return dp[a.length][b.length];
}

export function similarity(expected: string, actual: string): number {
  const e = normalizeForCompare(expected);
  const a = normalizeForCompare(actual);
  if (!e || !a) return 0;
  if (e === a) return 1;
  if (e.includes(a) || a.includes(e)) {
    const short = Math.min(e.length, a.length);
    const long = Math.max(e.length, a.length);
    return Math.max(0.75, short / long);
  }
  const dist = levenshtein(e, a);
  return 1 - dist / Math.max(e.length, a.length);
}

export function textSimilarity(a: string, b: string): number {
  const na = a.replace(/\s+/g, "").slice(0, 200);
  const nb = b.replace(/\s+/g, "").slice(0, 200);
  if (!na || !nb) return 0;
  if (na === nb) return 1;
  const dist = levenshtein(na, nb);
  return 1 - dist / Math.max(na.length, nb.length);
}

export type MatchResult = { score: number; ok: boolean; hasBoth: boolean };

export function matchField(expected: string, actual: string): MatchResult {
  const hasBoth = !!expected && !!actual;
  if (!hasBoth) return { score: 0, ok: false, hasBoth: false };
  const score = similarity(expected, actual);
  return { score, ok: score >= MATCH_THRESHOLD, hasBoth: true };
}
