// Template/Unstructured 양쪽 "문서 유형" 드롭다운 공용 helper.
//
// CLAUDE.md "Document Type Policy"에 따라 documentType은 실제 세부 유형
// (card_receipt / pos_receipt / food_cafe_receipt / finance_slip /
//  medical_receipt / invoice_statement / tax_invoice / unknown ...)을
// 의미한다. 사용자에게는 단순화된 그룹 드롭다운만 노출하지만, 저장값은
// 자동 감지된 세부 유형을 그대로 보존한다 (파서 분기/baseline 정합성).

export type DocumentTypeGroup = "" | "receipt" | "invoice_statement" | "tax_invoice";

export const DOCUMENT_TYPE_GROUP_OPTIONS: ReadonlyArray<{ value: DocumentTypeGroup; label: string }> = [
  { value: "",                 label: "선택 안 함" },
  { value: "receipt",          label: "영수증" },
  { value: "invoice_statement", label: "거래명세서" },
  { value: "tax_invoice",      label: "세금계산서" },
];

// "영수증" 그룹에 속하는 세부 유형들.
// finance_slip(금융전표)도 영수증 계열로 묶기로 한 사용자 결정에 따름.
// 백엔드(document_classifier.classify_document)가 실제로 반환하는 이름과
// CLAUDE.md Document Type Policy의 표준 이름이 일부 다르기 때문에 양쪽 모두
// 영수증 그룹에 매핑한다 (receipt_pos == pos_receipt 등).
const RECEIPT_DETAILS: ReadonlySet<string> = new Set([
  "receipt",
  // CLAUDE.md 표준 이름
  "card_receipt",
  "pos_receipt",
  "food_cafe_receipt",
  "finance_slip",
  "medical_receipt",
  // 백엔드(document_classifier) 실제 반환 이름
  "receipt_card",
  "receipt_pos",
  "bank_slip",
]);

// 세부 documentType → UI 그룹값.
// unknown / 빈 문자열 / 매핑되지 않는 값은 "" 으로 떨어진다.
export function getDocumentTypeGroup(detail: string | null | undefined): DocumentTypeGroup {
  if (!detail) return "";
  if (RECEIPT_DETAILS.has(detail)) return "receipt";
  if (detail === "invoice_statement") return "invoice_statement";
  if (detail === "tax_invoice") return "tax_invoice";
  return "";
}

// 사용자가 드롭다운에서 group을 새로 선택했을 때 저장할 documentType.
// - "" → 빈 값 (선택 안 함)
// - 현재 detail이 같은 group에 속하면 그대로 유지 (자동 감지값 보존)
// - 다른 group으로 바뀌면 새 group을 documentType으로 사용
export function applyDocumentTypeGroupChange(currentDetail: string, newGroup: string): string {
  if (!newGroup) return "";
  if (getDocumentTypeGroup(currentDetail) === newGroup) return currentDetail;
  return newGroup;
}
