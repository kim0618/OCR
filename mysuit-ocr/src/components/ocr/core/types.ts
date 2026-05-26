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
 * TPL-12A: 행 개별 조정용 sparse override.
 * 각 행 인덱스에 대해 y(절대 위치) 또는 height(절대 높이)를 덮어쓴다.
 * locked 은 향후 UI 잠금용 reserved 필드 (현재 materializer 는 무시).
 * Backward compat: rowOverrides 가 없으면 기존 repeat-only 동작.
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
