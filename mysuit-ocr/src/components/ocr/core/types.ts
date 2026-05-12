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

export type TableMeta = {
  mode?: "repeat" | "auto";
  rowTemplate?: Rect;
  rows?: Rect[];
  colGuides?: number[];
  stopKeywords?: string[];
  tableName?: string;
  columns?: TableColumnDef[];
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
