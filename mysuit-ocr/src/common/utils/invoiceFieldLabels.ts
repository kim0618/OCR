/** UI-only label mapping for invoice_statement canonical field keys. */
export const INVOICE_FIELD_KO: Record<string, string> = {
  supplierName: "공급자",
  supplierCompany: "공급자",
  supplierBusinessNo: "공급자 사업자번호",
  supplierCeo: "공급자 대표",
  supplierAddress: "공급자 주소",
  supplierTel: "공급자 전화",
  buyerName: "공급받는자",
  buyerCompany: "공급받는자",
  buyerBusinessNo: "받는자 사업자번호",
  buyerCeo: "받는자 대표",
  buyerAddress: "받는자 주소",
  buyerTel: "받는자 전화",
  issueDate: "일자",
  date: "일자",
  supplyAmount: "공급가",
  taxAmount: "세액",
  totalAmount: "합계",
  tableRows: "표 데이터",
  table: "표 데이터",
  itemName: "품명",
  itemCode: "품목코드",
  spec: "규격",
  quantity: "수량",
  unit: "단위",
  unitPrice: "단가",
  amount: "금액",
  lotNo: "LOT번호",
  serialNo: "Serial",
  serialLotComposite: "시리얼/로트No.",
  manufacturingExpiryComposite: "제조번호/유효기간",
  expiryDate: "유효기간",
  manufacturingNo: "제조번호",
  rowIndex: "순번",
};

/**
 * Resolve display label for a field.
 * Priority: ko prop > name→mapping lookup > en prop > name fallback
 */
export function resolveFieldLabel(opts: {
  name?: string;
  ko?: string;
  en?: string;
}): { primary: string; secondary: string | null } {
  const { name = "", ko = "", en = "" } = opts;

  if (ko) return { primary: ko, secondary: en || name || null };

  // Try to match name against the mapping (canonical key or table)
  const mapped = name ? INVOICE_FIELD_KO[name] ?? null : null;
  if (mapped) return { primary: mapped, secondary: en || name || null };

  if (en) return { primary: en, secondary: name || null };

  return { primary: name || "-", secondary: null };
}

/** Short display string: "한글라벨 (en/name)" */
export function fieldDisplayLabel(opts: { name?: string; ko?: string; en?: string }): string {
  const { primary, secondary } = resolveFieldLabel(opts);
  if (secondary && secondary !== primary) return `${primary} (${secondary})`;
  return primary;
}
