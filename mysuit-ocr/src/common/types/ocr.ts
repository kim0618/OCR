export type FieldType = "field" | "multi" | "check" | "table";
export type CheckMode = "boxOnly";

/** canonical mapping status */
export type MappingStatus = "auto" | "ambiguous" | "manual" | "unmapped";

/** canonical mapping candidate */
export type FieldMappingCandidate = {
  canonicalField: string;
  confidence: number;
  reason: string;
};

/** table column canonical mapping (OP-2) */
export type TableColumnDef = {
  index: number;
  // TPL-9B MVP: 직관적 명명. 기존 koField/enField는 backward-compat로 유지.
  columnKey?: string;
  labelKo?: string;
  labelEn?: string;
  koField?: string;
  enField?: string;
  canonicalColumn?: string;
  mappingStatus?: MappingStatus;
  mappingCandidates?: FieldMappingCandidate[];
};

export type Rect = {
  x: number;
  y: number;
  width: number;
  height: number;
};

/**
 * TPL-12A: sparse per-row override for the repeated rowTemplate.
 *
 * `rowIndex` is the 0-based index into the base rows produced by
 * `buildTableRows(area, rowTemplate)`. Coordinates use the SAME coordinate
 * system as `rowTemplate` / `rows` / `Rect` (image-pixel space at the
 * template's canonical resolution — NOT normalized 0..1).
 *
 * Semantics (consumed by `materializeTableRowsWithOverrides`):
 *   - `y`      : absolute y for this row (overrides cascade-derived y).
 *   - `height` : absolute row height (overrides rowTemplate.height).
 *   - `locked` : reserved for TPL-12C UI. The materializer does NOT consume
 *                it, but it is preserved so future code paths can read it.
 *
 * Backward compat: `rowOverrides` is optional on `TableMeta`. Templates
 * saved before TPL-12 carry no `rowOverrides` key and behave identically.
 */
export type TableRowOverride = {
  rowIndex: number;
  y?: number;
  height?: number;
  locked?: boolean;
};

export type TableMeta = {
  mode?: "repeat" | "auto";
  rowTemplate?: Rect;
  rows?: Rect[];
  colGuides?: number[];
  stopKeywords?: string[];
  tableName?: string;
  columns?: TableColumnDef[];
  /** TPL-12A: sparse per-row override. Empty/absent = repeat-only behavior. */
  rowOverrides?: TableRowOverride[];
};

export type Region = {
  id: string;
  name: string;
  fieldType: FieldType;

  x: number;
  y: number;
  width: number;
  height: number;

  parts?: 2 | 3;
  ratios?: number[];
  checkMode?: CheckMode;
  table?: TableMeta;

  /** OP-2: canonical field mapping (field/multi/check) */
  koField?: string;
  enField?: string;
  canonicalField?: string;
  mappingStatus?: MappingStatus;
  mappingCandidates?: FieldMappingCandidate[];
  valueType?: string;
};

export type LoadedImage = {
  src: string;
  fileName: string;
  naturalWidth: number;
  naturalHeight: number;
};

export type DragKind =
  | {
      type: "move";
      id: string;
      startX: number;
      startY: number;
      baseX: number;
      baseY: number;
    }
  | {
      type: "resize";
      id: string;
      handle: "nw" | "ne" | "sw" | "se";
      startX: number;
      startY: number;
      base: Region;
    }
  | { type: "draw"; startX: number; startY: number; draftId: string }
  | {
      type: "drawRowTemplate";
      tableId: string;
      startX: number;
      startY: number;
    }
  | {
      type: "split";
      id: string;
      index: number;
      startX: number;
      baseRatios: number[];
    }
  | {
      type: "tableCol";
      tableId: string;
      index: number;
      startX: number;
      baseGuides: number[];
    }
  | null;
