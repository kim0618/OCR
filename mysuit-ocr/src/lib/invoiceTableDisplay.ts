/**
 * invoiceTableDisplay.ts
 * invoice_statement tableRows 컬럼 표시 공통 helper
 *
 * TestWorkspace(Test 탭)와 OcrResultPanel(RunOCR Preview)에서 동일하게 사용.
 * 이 파일은 UI 표시 전용 — tableRows 원본 데이터를 수정하지 않음.
 */

// ── 타입 ─────────────────────────────────────────────────────────────────────

export type InvoiceDisplayCol = { key: string; labelKo: string };

// ── 우선순위 컬럼 목록 (canonical + custom) ────────────────────────────────

/**
 * 사용자에게 표시 가능한 컬럼의 우선순위 목록.
 * 이 목록에 없는 키(_rawText, _source, composite 계열 등 내부 키)는
 * buildInvoicePreviewCols / allowlist 기반 hasValue fallback에서 제외됨.
 */
export const INVOICE_TABLE_COL_PRIORITY: readonly InvoiceDisplayCol[] = [
  { key: "itemCode",          labelKo: "품목코드" },
  { key: "itemName",          labelKo: "품목명" },
  { key: "spec",              labelKo: "규격" },
  { key: "lotNo",             labelKo: "LOT/제조번호" },
  { key: "serialNo",          labelKo: "Serial" },
  { key: "manufacturingNo",   labelKo: "제조번호" },
  { key: "expiryDate",        labelKo: "유효기간" },
  { key: "quantity",          labelKo: "수량" },
  { key: "unit",              labelKo: "단위" },
  { key: "consumerUnitPrice", labelKo: "소비자단가" },
  { key: "supplyUnitPrice",   labelKo: "공급단가" },
  { key: "unitPrice",         labelKo: "단가" },
  { key: "supplyAmount",      labelKo: "공급금액" },
  { key: "taxAmount",         labelKo: "세액" },
  { key: "amount",            labelKo: "금액" },
  { key: "totalAmount",       labelKo: "합계금액" },
  { key: "manufacturer",      labelKo: "제조사" },
  { key: "insuranceCode",     labelKo: "보험No" },
  { key: "remark",            labelKo: "비고" },
] as const;

/**
 * canonical + custom 키 → 한글 라벨 맵.
 * TestWorkspace colLabelMap, OcrResultPanel _ALL_COL_LABEL_MAP의 공통 기반.
 * manifest displayLabelMap은 별도로 override 가능 (TestWorkspace 전용).
 */
export const INVOICE_COL_LABEL_MAP: Record<string, string> = {
  rowIndex: "번호",
  ...Object.fromEntries(INVOICE_TABLE_COL_PRIORITY.map((c) => [c.key, c.labelKo])),
  // custom composite/variant keys (TestWorkspace CUSTOM_COL_LABELS와 동일)
  consumerUnitPrice:            "소비자단가",
  supplyUnitPrice:              "공급단가",
  manufacturingExpiry:          "제조번호/유효기간",
  manufacturingExpiryComposite: "제조번호/유효기간",
  serialLot:                    "시리얼/로트No.",
  serialLotComposite:           "시리얼/로트No.",
};

// ── 내부 키 판별 ──────────────────────────────────────────────────────────────

const _INTERNAL_KEYS = new Set([
  "_rawText", "rawText", "_source", "source",
  "manufacturingExpiryComposite", "serialLotComposite",
  "rowIndex", "lineIndex", "_confidence", "confidence",
  "bbox", "extractionSource",
]);

/**
 * 내부/debug/composite 키이면 true.
 * 이 키들은 사용자용 품목표 컬럼이 아니므로 Preview에서 숨김.
 */
export function isInternalTableKey(key: string): boolean {
  if (_INTERNAL_KEYS.has(key)) return true;
  if (key.startsWith("_")) return true;
  if (key.includes("Composite") || key.includes("Debug") || key.includes("Warning")) return true;
  return false;
}

// ── 셀 값 정규화 + 의미 없는 값 판정 ──────────────────────────────────────────

/**
 * 셀 값을 정규화된 문자열로 변환.
 * null/undefined → "", Unicode dash → "-", 제로폭 공백 제거.
 */
export function normalizeTableCell(v: unknown): string {
  if (v === null || v === undefined) return "";
  return String(v)
    .replace(/[​‌‍﻿ ]/g, "")
    .replace(/[–—−－―]/g, "-")
    .trim();
}

const _MEANINGLESS = new Set(["", "-", "n/a", "null", "none", "undefined"]);

/**
 * 정규화된 셀 문자열이 의미 없는 값인지 판정 (대소문자 무시).
 */
export function isMeaninglessTableValue(s: string): boolean {
  return _MEANINGLESS.has(s.toLowerCase());
}

/**
 * tableRows 전체에서 특정 key가 의미 있는 값을 하나라도 가지는지 확인.
 */
export function hasMeaningfulTableValue(
  rows: Record<string, unknown>[],
  key: string,
): boolean {
  return rows.some((row) => !isMeaninglessTableValue(normalizeTableCell(row[key])));
}

// ── UI-PREVIEW-ROWINDEX-1: rowIndex 표시 정책 ────────────────────────────────

/**
 * UI-PREVIEW-ROWINDEX-1: rowIndex 컬럼을 사용자 표시 컬럼으로 노출할지 결정.
 *
 * 표시 (true) 조건 — 다음 중 하나라도 true:
 *   1. externalExpectedKeys (manifest tableExpectedColumns / template tableColumns 등
 *      caller가 전달한 expected keys 집합)에 "rowIndex" 포함
 *   2. tableMeta.expectedColumnKeys 에 "rowIndex" 포함 (백엔드가 실제 컬럼으로 선언)
 *
 * 다음 신호 단독으로는 표시하지 않음 (parser 내부 1..N 생성 가능성):
 *   - tableMeta.columns 에 "rowIndex" 가 있는 경우
 *   - tableRows 안에 rowIndex 값이 채워져 있는 경우
 *
 * 본 함수는 표시 정책만 결정하며 document_fields.tableRows 원본은 변경하지 않는다.
 */
export function shouldDisplayRowIndex(
  tableMeta: Record<string, unknown> | null | undefined,
  externalExpectedKeys?: readonly string[] | null,
): boolean {
  if (externalExpectedKeys && externalExpectedKeys.length > 0) {
    for (const k of externalExpectedKeys) {
      if (k === "rowIndex") return true;
    }
  }
  const expKeys = tableMeta?.expectedColumnKeys;
  if (Array.isArray(expKeys)) {
    for (const k of expKeys) {
      if (String(k) === "rowIndex") return true;
    }
  }
  return false;
}

// ── 중복 제거 유틸 (lot/mfg/itemCode — private) ───────────────────────────────

const _LOT_KEYS = new Set(["lotNo", "serialLot", "lot", "lotNumber"]);
const _MFG_KEYS = new Set(["manufacturingNo", "manufactureNo", "mfgNo"]);
const _ITEMCODE_KEYS = new Set(["itemCode", "productCode"]);
const _PREFIX_MATCH_MIN_LEN = 4;

function _meaningfulRatio(rows: Record<string, unknown>[], key: string): number {
  if (rows.length === 0) return 0;
  let cnt = 0;
  for (const row of rows) {
    if (!isMeaninglessTableValue(normalizeTableCell(row[key]))) cnt++;
  }
  return cnt / rows.length;
}

function _isLotDupOfMfg(lot: string, mfg: string): boolean {
  if (lot === mfg) return true;
  if (lot.length < _PREFIX_MATCH_MIN_LEN || mfg.length === 0) return false;
  if (mfg.startsWith(lot)) return true;
  if (mfg.startsWith("C" + lot) || mfg.startsWith("c" + lot)) return true;
  return false;
}

function _meaninglessOrDupRatio(
  rows: Record<string, unknown>[],
  key1: string,
  key2: string,
): number {
  if (rows.length === 0) return 0;
  let cnt = 0;
  for (const row of rows) {
    const v1 = normalizeTableCell(row[key1]);
    const v2 = normalizeTableCell(row[key2]);
    if (isMeaninglessTableValue(v1) || _isLotDupOfMfg(v1, v2)) cnt++;
  }
  return cnt / rows.length;
}

// ── 핵심 함수: tableMeta 기반 컬럼 결정 + dedup ──────────────────────────────

/**
 * 공통 tableRows 표시 컬럼 결정 함수.
 * TestWorkspace(InvoiceTableRowsPanel "detected" 경로)와 RunOCR Preview(OcrResultPanel)가 동일하게 사용.
 *
 * 우선순위:
 *   1. tableMeta.expectedColumnKeys → 순서·라벨 참고 + hasValue 필터
 *   2. tableMeta.columns → 순서·라벨 참고 + hasValue 필터
 *   3. INVOICE_TABLE_COL_PRIORITY allowlist + hasValue fallback
 *
 * 후처리 (내부 키 제외 이후 적용):
 *   - itemCode 계열: meaningful 비율 5% 이하면 숨김 (대부분 빈값이면 노이즈)
 *   - lot/mfg 중복: lotNo가 95% 이상 manufacturingNo와 동일(prefix 포함)이면 lotNo 숨김
 *   - lot 노이즈: itemCode 표가 확인되고 mfgNo가 전혀 없으면 lotNo 숨김
 *   - serialNo 중복: serialNo가 lotNo와 95% 이상 동일이면 숨김
 *
 * tableRows 원본은 수정하지 않음.
 */
export function buildInvoicePreviewCols(
  tableMeta: Record<string, unknown> | null | undefined,
  rows: Record<string, unknown>[],
  externalExpectedKeys?: readonly string[] | null,
): InvoiceDisplayCol[] {
  // 후보 키 목록 결정 (순서/라벨 참고용)
  let candidateKeys: string[] = [];

  // 1순위: expectedColumnKeys
  const expKeys = tableMeta?.expectedColumnKeys;
  if (Array.isArray(expKeys) && expKeys.length > 0) {
    candidateKeys = expKeys
      .map(String)
      .filter((k) => k !== "rowIndex" && !isInternalTableKey(k));
  }

  // 2순위: detected columns
  if (candidateKeys.length === 0) {
    const detCols = tableMeta?.columns;
    if (Array.isArray(detCols) && detCols.length > 0) {
      candidateKeys = detCols
        .map(String)
        .filter((k) => k !== "rowIndex" && !isInternalTableKey(k));
    }
  }

  // 3순위: INVOICE_TABLE_COL_PRIORITY allowlist
  if (candidateKeys.length === 0) {
    candidateKeys = INVOICE_TABLE_COL_PRIORITY.map((c) => c.key);
  }

  // T-PREVIEW-LABEL-1: tableMeta.columnLabels 우선 사용 (원본 헤더 라벨)
  // 우선순위: columnLabels[key] → INVOICE_COL_LABEL_MAP[key] → key 자체
  const colLabels = tableMeta?.columnLabels as Record<string, string> | undefined;
  const resolveLabel = (k: string): string =>
    colLabels?.[k] || INVOICE_COL_LABEL_MAP[k] || k;

  // hasValue 필터: 실제 의미 있는 값이 있는 컬럼만
  if (rows.length === 0) return [];
  let cols = candidateKeys
    .filter((k) => hasMeaningfulTableValue(rows, k))
    .map((k) => ({ key: k, labelKo: resolveLabel(k) }));

  // ── 후처리 dedup ──

  // itemCode 계열 majority rule: meaningful 비율 5% 이하면 숨김
  cols = cols.filter((c) => {
    if (!_ITEMCODE_KEYS.has(c.key)) return true;
    return _meaningfulRatio(rows, c.key) > 0.05;
  });

  // lot/mfg 중복 제거 (prefix match 포함, 95% 이상이면 lotNo 숨김)
  const mfgKey = cols.find((c) => _MFG_KEYS.has(c.key))?.key;
  if (mfgKey) {
    const toRemove = new Set<string>();
    for (const col of cols.filter((c) => _LOT_KEYS.has(c.key))) {
      if (_meaninglessOrDupRatio(rows, col.key, mfgKey) >= 0.95) toRemove.add(col.key);
    }
    if (toRemove.size > 0) cols = cols.filter((c) => !toRemove.has(c.key));
  }

  // lot 노이즈 제거: itemCode 기반 표에서 mfgNo 없으면 lotNo는 OCR 노이즈
  if (
    cols.some((c) => _LOT_KEYS.has(c.key)) &&
    hasMeaningfulTableValue(rows, "itemCode") &&
    !hasMeaningfulTableValue(rows, "manufacturingNo")
  ) {
    cols = cols.filter((c) => !_LOT_KEYS.has(c.key));
  }

  // serialNo vs lotNo 중복 제거 (95% 이상 동일이면 serialNo 숨김)
  if (cols.some((c) => c.key === "serialNo") && cols.some((c) => c.key === "lotNo")) {
    if (_meaninglessOrDupRatio(rows, "serialNo", "lotNo") >= 0.95) {
      cols = cols.filter((c) => c.key !== "serialNo");
    }
  }

  // UI-PREVIEW-ROWINDEX-1: rowIndex prepend 정책
  // - 값 존재만으로(hasMeaningfulTableValue) prepend 하지 않음 (parser 1..N 생성 가능)
  // - tableMeta.expectedColumnKeys 또는 externalExpectedKeys 에 rowIndex 가 있을 때만 prepend
  // - 라벨 우선순위:
  //   1. tableMeta.columnLabels?.rowIndex (forward-compatible: 백엔드가 원본 헤더 추가 시 자동 적용)
  //   2. INVOICE_COL_LABEL_MAP["rowIndex"] = "번호" (현재 fallback)
  if (shouldDisplayRowIndex(tableMeta, externalExpectedKeys)) {
    cols = [{ key: "rowIndex", labelKo: resolveLabel("rowIndex") }, ...cols];
  }

  return cols;
}

