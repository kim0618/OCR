/**
 * gtSkeletonCandidateViewModel.ts
 * (FULL-UNSTRUCTURED-INVOICE-2H-CUSTOM-TAB-GT-SKELETON-CANDIDATE-TABLE-PATCH)
 *
 * Dedicated, read-only accessor + view model for the backend debug payload
 * `extract_debug.invoice_statement_free.gtSkeletonCandidates`.
 *
 * 목적:
 * - 2.pdf 처럼 release tableRows 가 fallback(2행) 인 비정형 거래명세서에서,
 *   GT 작성을 돕기 위한 13행 후보를 Custom 탭 "별도 입력표" 로만 노출한다.
 *
 * 절대 불변(2G contract):
 * - 이 view model 은 release 결과가 아니다. gtSkeletonCandidates 를 release
 *   tableRows 로 취급하지 않는다.
 * - 공유 `buildTableResultViewModels` 출력에 합치지 않는다(= Preview / Clean
 *   JSON / Markdown / History / DB 로 누출 금지). 이 모듈은 그 파이프라인과
 *   완전히 분리된 별도 채널이다.
 * - representative PRIORITY 와 무관하다. source 이름은 `gt_skeleton_candidate`.
 * - `tokenBboxDebug`(raw 전문 성격)는 읽지도 노출하지도 않는다.
 *
 * Boundary:
 * - Pure helper. React/DOM/storage/fetch/backend 없음. 입력을 변형하지 않음.
 * - `any` 접근(extract_debug 미타입)을 이 파일 한 곳으로 제한한다.
 */

/** GT 후보 입력표가 사용하는 표준 8 컬럼(릴리스 tableRows 와 동일 키 셋). */
export const GT_SKELETON_COLUMN_KEYS = [
  "itemName",
  "spec",
  "productCode",
  "lotNo",
  "expiryDate",
  "quantity",
  "unitPrice",
  "amount",
] as const;

export type GtSkeletonColumnKey = (typeof GT_SKELETON_COLUMN_KEYS)[number];

export type GtSkeletonCandidateColumn = {
  columnKey: GtSkeletonColumnKey;
  labelKo: string;
};

export type GtSkeletonCandidateRow = {
  rowIndex: number;
  /** key→value (모든 표준 컬럼 키가 항상 존재, 빈값은 ""). */
  values: Record<GtSkeletonColumnKey, string>;
  /** 행 검토 메타(앵커/신뢰도). 표시·디버그용. export 기본 대상 아님. */
  reviewRequired: boolean;
  rowConfidence: string;
  /** backend `_gtSkeleton` 원본(읽기 전용 보존). */
  sourceRowMeta: Record<string, unknown> | null;
};

export type GtSkeletonCandidateViewModel = {
  source: "gt_skeleton_candidate";
  title: string;
  warningLabel: string;
  helperNotes: string[];
  reviewRequired: true;
  releaseImpact: "none";
  mode: string;
  rowCount: number;
  columns: GtSkeletonCandidateColumn[];
  rows: GtSkeletonCandidateRow[];
  /** 진단(좌표 정렬/앵커 요약). 표시 보조용. */
  diagnostics: {
    coordinateAlignment: string | null;
    anchorSummary: Record<string, unknown> | null;
  };
};

const COLUMN_LABELS_KO: Record<GtSkeletonColumnKey, string> = {
  itemName: "품목명",
  spec: "규격",
  productCode: "제품코드",
  lotNo: "LOT번호",
  expiryDate: "유효기간",
  quantity: "수량",
  unitPrice: "단가",
  amount: "금액",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function asString(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

/**
 * `result` 가 invoice_statement(거래명세서) 계열인지 판단. doc_type /
 * documentType / document_fields.doc_type 어느 한 곳이라도 일치하면 true.
 */
function isInvoiceStatement(result: Record<string, unknown>): boolean {
  const direct =
    asString(result.doc_type).trim()
    || asString(result.documentType).trim()
    || asString(result.document_type).trim();
  if (direct === "invoice_statement") return true;
  const df = result.document_fields;
  if (isRecord(df) && asString(df.doc_type).trim() === "invoice_statement") return true;
  return false;
}

/**
 * `extract_debug.invoice_statement_free.gtSkeletonCandidates` 를 안전하게 읽어
 * GT 후보 view model 로 변환한다. 게이트를 통과하지 못하면 `null`.
 *
 * 게이트(2G contract — 데이터 구동, 파일명 하드코딩 없음):
 *   1. doc_type / documentType 가 invoice_statement 계열
 *   2. fallbackRequired === true (release 가 fallback 상태)
 *   3. gtSkeletonCandidates.available === true
 *   4. mode === "debug_gt_skeleton_only"
 *   5. releaseImpact === "none" || candidateRowsReleaseIsolated === true
 *   6. rows 가 비어 있지 않은 배열
 */
export function buildGtSkeletonCandidateViewModel(
  result: unknown,
): GtSkeletonCandidateViewModel | null {
  if (!isRecord(result)) return null;
  if (!isInvoiceStatement(result)) return null;

  const extractDebug = result.extract_debug;
  if (!isRecord(extractDebug)) return null;
  const free = extractDebug.invoice_statement_free;
  if (!isRecord(free)) return null;

  // 게이트 2: release 가 fallback 상태일 때만 GT 후보 입력표를 노출.
  if (free.fallbackRequired !== true) return null;

  const skeleton = free.gtSkeletonCandidates;
  if (!isRecord(skeleton)) return null;

  // 게이트 3·4·5: debug 전용 / release 격리 확인.
  if (skeleton.available !== true) return null;
  if (skeleton.mode !== "debug_gt_skeleton_only") return null;
  const releaseIsolated =
    skeleton.releaseImpact === "none" || skeleton.candidateRowsReleaseIsolated === true;
  if (!releaseIsolated) return null;

  const rawRows = skeleton.rows;
  if (!Array.isArray(rawRows) || rawRows.length === 0) return null;

  const rows: GtSkeletonCandidateRow[] = [];
  for (let i = 0; i < rawRows.length; i++) {
    const raw = rawRows[i];
    if (!isRecord(raw)) continue;
    const values = {} as Record<GtSkeletonColumnKey, string>;
    for (const key of GT_SKELETON_COLUMN_KEYS) {
      values[key] = asString(raw[key]);
    }
    const meta = isRecord(raw._gtSkeleton) ? (raw._gtSkeleton as Record<string, unknown>) : null;
    const rowIndex =
      typeof raw.rowIndex === "number" && Number.isFinite(raw.rowIndex)
        ? (raw.rowIndex as number)
        : rows.length;
    rows.push({
      rowIndex,
      values,
      reviewRequired: meta?.reviewRequired === true,
      rowConfidence: asString(meta?.rowConfidence),
      sourceRowMeta: meta,
    });
  }
  if (rows.length === 0) return null;

  const columns: GtSkeletonCandidateColumn[] = GT_SKELETON_COLUMN_KEYS.map((key) => ({
    columnKey: key,
    labelKo: COLUMN_LABELS_KO[key],
  }));

  // 진단(좌표/앵커) — 표시 보조용. tokenBboxDebug 는 의도적으로 제외.
  const coordinateAlignment = isRecord(skeleton.coordinateAlignment)
    ? asString((skeleton.coordinateAlignment as Record<string, unknown>).status) || null
    : null;
  const anchorSummary = isRecord(skeleton.anchorSummary)
    ? (skeleton.anchorSummary as Record<string, unknown>)
    : null;

  return {
    source: "gt_skeleton_candidate",
    title: "GT 후보 입력표",
    warningLabel: "자동 추출 결과 아님",
    helperNotes: [
      "자동 추출 결과가 아니라 GT 작성을 돕기 위한 후보 행입니다.",
      "검토 후 수정해서 사용하세요.",
      "Clean JSON / Markdown / History 에는 반영되지 않습니다.",
    ],
    reviewRequired: true,
    releaseImpact: "none",
    mode: asString(skeleton.mode),
    rowCount: rows.length,
    columns,
    rows,
    diagnostics: { coordinateAlignment, anchorSummary },
  };
}
