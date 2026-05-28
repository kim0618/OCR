/**
 * raw OCR response → 화면용 OcrResult 변환 helper.
 *
 * 역할:
 * - backend `/ocr/extract` 응답을 받아 OcrResult.fields 를 화면에서 바로
 *   소비 가능한 형태로 정리한다. template 모드(region-based) 일 때는 backend
 *   가 region 별로 채워준 raw.fields 에 ko/en 라벨만 보강하고, 그 외 모드일
 *   때는 receipt_fields / finance_fields / template.fields 를 기반으로 새로
 *   조립한다.
 *
 * Boundary (반드시 지킬 것):
 * - autofill / history / restore / localStorage / React / useState / setOcrResult
 *   등 어떤 부수효과도 import 하지 않는다.
 * - autofillEngine 직접 import 금지 — 필드 키 정규화가 필요하면 caller 가
 *   `options.normalizeFieldKey` 로 함수를 주입한다.
 * - history / autofill / restore 흐름은 여전히 RunOcrWorkspace 가 담당한다.
 *
 * 변경 주의:
 * - output shape 를 바꾸면 Preview / Custom / Validation / Clean JSON /
 *   Markdown 표시 모두에 영향이 갈 수 있다.
 */
import type { OcrResult, OcrFieldResult } from "../ui/OcrResultPanel";
import { extractUnstructuredTableRows } from "./extractUnstructuredTableRows";

/**
 * INVOICE-PARITY-4B: canonical invoice scalar fields live in
 * `raw.document_fields` (supplierCompany, supplierBizNumber, buyerCompany, …,
 * totalAmount, cumulativeAmount). The unstructured field-resolution path
 * historically read only receipt_fields/finance_fields and left these general
 * fields empty (0.0%). This alias map connects user info-field labels (Korean
 * or English) to the canonical `document_fields` scalar keys.
 *
 * Scope: used ONLY by the unstructured invoice_statement field resolution
 * below. The region/template path and the table path are NOT touched.
 * Keys are whitespace-stripped so "공급자 사업자 번호" === "공급자사업자번호".
 */
const INVOICE_DOCUMENT_FIELDS_ALIAS: Record<string, string> = {
  // 공급자 (supplier)
  "공급자등록번호": "supplierBizNumber",
  "공급자사업자번호": "supplierBizNumber",
  "공급자상호": "supplierCompany",
  "공급자회사명": "supplierCompany",
  "공급자주소": "supplierAddress",
  "공급자성명": "supplierRepresentative",
  "공급자대표자": "supplierRepresentative",
  // 공급받는자 (buyer)
  "공급받는자등록번호": "buyerBizNumber",
  "공급받는자사업자번호": "buyerBizNumber",
  "공급받는자상호": "buyerCompany",
  "공급받는자회사명": "buyerCompany",
  "공급받는자주소": "buyerAddress",
  "공급받는자성명": "buyerRepresentative",
  "공급받는자대표자": "buyerRepresentative",
  // 금액 / 날짜 (amounts / dates)
  "합계금액": "totalAmount",
  "총합계금액": "totalAmount",
  "총액": "totalAmount",
  "합계": "totalAmount",
  "누계": "cumulativeAmount",
  "공급가액": "supplyAmount",
  "공급금액": "supplyAmount",
  "세액": "taxAmount",
  "부가세": "taxAmount",
  "발행일자": "issueDate",
  "작성일자": "issueDate",
  "거래일자": "issueDate",
};

/** INVOICE-PARITY-4B: strip whitespace for alias matching. */
function normalizeInvoiceAliasLabel(label: string): string {
  return String(label ?? "").replace(/\s+/g, "").trim();
}

/**
 * INVOICE-PARITY-4B: extract ONLY scalar (string/number) values from
 * `raw.document_fields`. `tableRows` (array) / `tableMeta` (object) and any
 * other object/array are intentionally EXCLUDED so the table path is never used
 * as a scalar field-value source.
 */
function extractDocumentFieldsScalar(documentFields: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (!documentFields || typeof documentFields !== "object" || Array.isArray(documentFields)) return out;
  for (const [key, value] of Object.entries(documentFields as Record<string, unknown>)) {
    if (typeof value === "string") out[key] = value;
    else if (typeof value === "number" && Number.isFinite(value)) out[key] = String(value);
    // boolean / object / array (tableRows, tableMeta, …) deliberately skipped
  }
  return out;
}

/**
 * INVOICE-PARITY-4B: resolve a user info-field label (ko or en) to a
 * `document_fields` scalar value via direct key match or the canonical alias
 * map. Returns undefined when no meaningful (non-empty) value is found.
 */
function pickInvoiceDocumentField(
  scalar: Record<string, string>,
  ...labels: string[]
): { key: string; value: string } | undefined {
  for (const label of labels) {
    if (!label) continue;
    // direct document_fields key (e.g. enField="supplierCompany")
    if (label in scalar && String(scalar[label]).trim().length > 0) {
      return { key: label, value: scalar[label] };
    }
    const aliasKey = INVOICE_DOCUMENT_FIELDS_ALIAS[normalizeInvoiceAliasLabel(label)];
    if (aliasKey && aliasKey in scalar && String(scalar[aliasKey]).trim().length > 0) {
      return { key: aliasKey, value: scalar[aliasKey] };
    }
  }
  return undefined;
}

/**
 * buildRunOcrResult 가 실제로 읽는 template 의 최소 구조 타입.
 * 프로젝트 전역 TemplateItem 과의 강결합을 피하고 RunOcrWorkspace 와의 순환
 * import 를 막기 위해 structural minimum 만 노출한다.
 *
 * TPL-7: 비정형(unstructured) 템플릿에 한해 documentType / info / tables 가
 * optional 로 추가된다. 모두 optional 이며, 기존 legacy fields-only 템플릿은
 * 이 필드 없이도 동일하게 동작한다.
 */
export type BuildRunOcrResultTemplate = {
  mode?: string;
  documentType?: string;
  regions?: Array<{
    koField?: string;
    enField?: string;
    canonicalField?: string;
    [key: string]: unknown;
  }>;
  fields?: Array<{ no?: number; enField?: string; koField?: string }>;
  /** TPL-7: unstructuredDefinition.UnstructuredInfoField 의 structural subset. */
  info?: Array<{
    key?: string;
    labelKo?: string;
    labelEn?: string;
    aliases?: string[];
    no?: number;
    order?: number;
    [key: string]: unknown;
  }>;
  /** TPL-7: unstructuredDefinition.UnstructuredTableDef 의 structural subset. */
  tables?: Array<{
    tableKey?: string;
    labelKo?: string;
    labelEn?: string;
    columns?: Array<{
      columnKey?: string;
      labelKo?: string;
      labelEn?: string;
      [key: string]: unknown;
    }>;
    [key: string]: unknown;
  }>;
};

/**
 * buildRunOcrResult 의 옵션. 현재는 필드 키 정규화 함수 1개만 받는다.
 *
 * `normalizeFieldKey` 는 caller(`RunOcrWorkspace`) 가 autofillEngine 의
 * `normalizeAutofillFieldKey` 를 주입하는 지점이다. 이 모듈이 autofillEngine
 * 을 직접 import 하지 않도록 의존성 주입 형태로 분리한 boundary 결정.
 * 미지정 시 identity 함수로 동작해 단독 테스트가 가능하다.
 */
export type BuildRunOcrResultOptions = {
  normalizeFieldKey?: (field: string) => string;
};

/**
 * raw OCR 응답을 화면용 `OcrResult` 로 변환한다.
 *
 * 분기:
 * - `template && template.mode !== "unstructured"` : region-based 템플릿.
 *   backend 가 채운 raw.fields 에 template.regions 의 ko/en/canonicalField
 *   라벨만 보강해 반환.
 * - 그 외 (template 미지정 또는 unstructured): receipt_fields / finance_fields
 *   를 기반으로 OcrFieldResult 를 새로 조립. template.fields 가 있으면 그
 *   순서대로, 없으면 receipt 우선 → 비어 있으면 finance 로 fallback.
 *
 * 옵션 `normalizeFieldKey` 는 receipt/finance 맵에서 라벨로 값을 lookup 할
 * 때 키 alias 정규화에 사용된다. autofillEngine 직접 import 회피용 의존성
 * 주입 지점.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function buildRunOcrResult(raw: any, template?: BuildRunOcrResultTemplate, options?: BuildRunOcrResultOptions): OcrResult {
  const normalizeFieldKey = options?.normalizeFieldKey ?? ((field: string) => field);

  // 템플릿이 없거나 mode 가 "unstructured" 인 경우 Test 탭과 동일하게
  // receipt_fields / finance_fields 기반으로 fields 를 재구성한다.
  // 템플릿이 있고 region-based(mode !== "unstructured") 이면 백엔드가 region 별로
  // 추출해 둔 raw.fields 를 그대로 사용한다.
  if (template && template.mode !== "unstructured") {
    // Enrich raw.fields with ko/en labels from template regions so the
    // Preview overlay and result table show human-readable field names.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const regions: any[] = (template as any).regions ?? [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const enriched = ((raw.fields ?? []) as any[]).map((field: any, i: number) => {
      const region = regions[i] ?? {};
      return {
        ...field,
        ko: field.ko || String(region.koField ?? "").trim() || "",
        en: field.en || String(region.enField ?? region.canonicalField ?? "").trim() || "",
      };
    });
    return { ...raw, fields: enriched };
  }

  const receiptFields = raw.receipt_fields ?? {};
  const financeFields = raw.finance_fields ?? {};

  // INVOICE-PARITY-4B: document_fields scalar source for the unstructured
  // invoice field resolution. Only consulted when the document is an
  // invoice_statement, so receipt/finance behavior for every other doc type is
  // byte-identical. Scalar-only (tableRows/tableMeta excluded by the extractor).
  const documentFieldsScalar = extractDocumentFieldsScalar(
    (raw as { document_fields?: unknown })?.document_fields,
  );
  const isInvoiceStatement =
    (typeof template?.documentType === "string" && template.documentType.trim() === "invoice_statement")
    || (typeof (raw as { doc_type?: unknown })?.doc_type === "string"
      && (raw as { doc_type?: string }).doc_type === "invoice_statement");

  // TPL-7: 신규 비정형 schema(info[])가 있으면 info를 우선 사용해 lookup용 pseudo
  // fields를 만든다. info가 없으면 legacy template.fields[]를 그대로 사용해
  // 기존 영수증/fields-only 경로 100% 호환을 유지한다.
  const templateInfo = Array.isArray(template?.info) ? template!.info! : [];
  const legacyFields = template?.fields ?? [];
  const templateFields: Array<{ no?: number; enField?: string; koField?: string }> =
    templateInfo.length > 0
      ? templateInfo.map((entry, idx) => {
          const rawEn = typeof entry?.labelEn === "string" ? entry.labelEn
            : typeof entry?.key === "string" ? entry.key
            : "";
          const en = String(rawEn).trim();
          const rawKo = typeof entry?.labelKo === "string" ? entry.labelKo
            : typeof entry?.labelEn === "string" ? entry.labelEn
            : typeof entry?.key === "string" ? entry.key
            : "";
          const ko = String(rawKo).trim();
          const noVal = typeof entry?.no === "number" && Number.isFinite(entry.no)
            ? entry.no
            : typeof entry?.order === "number" && Number.isFinite(entry.order)
              ? entry.order
              : idx + 1;
          return { no: noVal, enField: en, koField: ko };
        })
      : legacyFields;
  const resultFields: OcrFieldResult[] = [];

  // 한글 라벨 ↔ 백엔드 키(영문 short form) alias.
  // 백엔드 receipt_fields 키: 회사명, 사업자번호, 대표자, tel, 주소, 총합계금액
  // 템플릿이 koField="전화번호" 로 정의되어 있어도 receipt_fields["tel"] 을 가져오게 함.
  const RECEIPT_ALIAS: Record<string, string> = {
    "전화번호": "tel",
    "Tel": "tel",
    "TEL": "tel",
  };
  const pickValue = (map: Record<string, unknown>, label: string): { key: string; value: unknown } | undefined => {
    if (!label) return undefined;
    if (label in map) return { key: label, value: map[label] };
    const alias = RECEIPT_ALIAS[label];
    if (alias && alias in map) return { key: alias, value: map[alias] };
    const normalizedLabel = normalizeFieldKey(label);
    for (const [key, value] of Object.entries(map)) {
      if (normalizeFieldKey(key) === normalizedLabel) return { key, value };
    }
    return undefined;
  };

  if (templateFields.length > 0) {
    templateFields.forEach((field, index) => {
      const ko = String(field.koField ?? "").trim();
      const en = String(field.enField ?? "").trim();
      // INVOICE-PARITY-4B: for invoice_statement, prefer the canonical
      // document_fields scalar value (supplierCompany / buyerBizNumber / …).
      // This fills the general fields that previously showed 0.0% empty. Other
      // doc types fall straight through to the unchanged receipt/finance path.
      const docFieldPick = isInvoiceStatement
        ? pickInvoiceDocumentField(documentFieldsScalar, ko, en)
        : undefined;
      const picked = docFieldPick
        ?? pickValue(receiptFields, ko)
        ?? pickValue(receiptFields, en)
        ?? pickValue(financeFields, ko)
        ?? pickValue(financeFields, en)
        ?? { key: "", value: "" };
      const value = picked.value;
      resultFields.push({
        name: ko || en || `field_${index + 1}`,
        ko,
        en,
        field_type: "field",
        value: String(value ?? ""),
        confidence: value ? 1 : 0,
        bbox: [0, 0, 0, 0],
      });
    });
  } else if (Object.keys(receiptFields).length > 0) {
    Object.entries(receiptFields).forEach(([name, value]) => {
      resultFields.push({
        name,
        field_type: "field",
        value: String(value ?? ""),
        confidence: value ? 1 : 0,
        bbox: [0, 0, 0, 0],
      });
    });
  }

  if (resultFields.length === 0 && Object.keys(financeFields).length > 0) {
    Object.entries(financeFields).forEach(([name, value]) => {
      resultFields.push({
        name,
        field_type: "field",
        value: String(value ?? ""),
        confidence: value ? 1 : 0,
        bbox: [0, 0, 0, 0],
      });
    });
  }

  // TPL-7: 비정형 신규 schema metadata를 result에 안전하게 첨부한다.
  // - documentType: 빈 문자열이면 첨부하지 않음 (helper omit policy와 일치).
  // - tables: skeleton만 보존 (rows: [] — 실제 row extraction은 TPL-8 범위).
  //
  // result 객체는 spread(...raw)로 시작하므로 추가 키는 OcrResult 타입에 없어도
  // raw: any 추론 경로를 통해 허용된다. UI는 아직 이 메타를 모르므로 변경 없음.
  const result: OcrResult = {
    ...raw,
    fields: resultFields.length > 0 ? resultFields : (raw.fields ?? []),
  };
  const docType = typeof template?.documentType === "string"
    ? template.documentType.trim()
    : "";
  if (docType.length > 0) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (result as any).documentType = docType;
  }
  if (Array.isArray(template?.tables) && template!.tables!.length > 0) {
    // TPL-8B: project backend canonical `document_fields.tableRows` onto the
    // user's first table when documentType === "invoice_statement". Other
    // tables and other documentTypes get the legacy `[]` skeleton.
    const projectedRows = extractUnstructuredTableRows({
      raw,
      documentType: template?.documentType,
      tables: template!.tables,
    });
    const tables = template!.tables!.map((t, idx) => {
      const cols = Array.isArray(t?.columns) ? t!.columns! : [];
      return {
        tableKey: typeof t?.tableKey === "string" ? t.tableKey : "",
        labelKo: typeof t?.labelKo === "string" ? t.labelKo : "",
        ...(typeof t?.labelEn === "string" ? { labelEn: t.labelEn } : {}),
        columns: cols.map((c) => ({
          columnKey: typeof c?.columnKey === "string" ? c.columnKey : "",
          labelKo: typeof c?.labelKo === "string" ? c.labelKo : "",
          ...(typeof c?.labelEn === "string" ? { labelEn: c.labelEn } : {}),
        })),
        rows: (projectedRows[idx] ?? []) as Record<string, string>[],
      };
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (result as any).unstructuredTables = tables;
  }
  return result;
}
