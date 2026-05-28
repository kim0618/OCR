// 정형 Template + 비정형 Unstructured 양쪽 "표준 컬럼" select 공용 옵션.
//
// 사용자는 자유롭게 columnKey/labelKo를 입력할 수 있고, 이 select는 backend
// canonical key와 매핑되는 표준값을 빠르게 채워 넣기 위한 단축키 역할이다.
// Test 전용 profiles.ts에 의존하지 않기 위해 인라인 상수로 둔다.

export type CanonicalColumnOption = { value: string; labelKo: string };

export const CANONICAL_COLUMN_OPTIONS: ReadonlyArray<CanonicalColumnOption> = [
  { value: "",             labelKo: "" },
  { value: "itemName",     labelKo: "품목명" },
  { value: "spec",         labelKo: "규격" },
  { value: "quantity",     labelKo: "수량" },
  { value: "unitPrice",    labelKo: "단가" },
  { value: "supplyAmount", labelKo: "공급가액" },
  { value: "taxAmount",    labelKo: "세액" },
  { value: "amount",       labelKo: "금액" },
  { value: "lotNo",        labelKo: "제조번호" },
  { value: "expiryDate",   labelKo: "유효기간" },
  { value: "itemCode",     labelKo: "품목코드" },
  { value: "unit",         labelKo: "단위" },
  { value: "remark",       labelKo: "비고" },
];

// option.value === "" → "선택 안 함", 그 외 → "value (labelKo)" 표기.
export function canonicalColumnLabel(opt: CanonicalColumnOption): string {
  return opt.value === "" ? "선택 안 함" : `${opt.value} (${opt.labelKo})`;
}

// columnKey가 표준 옵션 value와 일치하면 그 value, 아니면 빈 문자열.
// 비정형처럼 canonicalColumn 같은 별도 필드 없이 select를 컴퓨티드로 표시할 때 사용.
export function findCanonicalValueByKey(columnKey: string | null | undefined): string {
  if (!columnKey) return "";
  const hit = CANONICAL_COLUMN_OPTIONS.find((o) => o.value === columnKey);
  return hit ? hit.value : "";
}
