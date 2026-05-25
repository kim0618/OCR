import type { LoadedImage, Rect, Region } from "../../../common/types/ocr";
import { calcMultiSubRegions, normalizeRatios } from "../../../common/utils/ocrCanvasOps";
import {
  materializeTableRowsWithOverrides,
  normalizeColGuides,
} from "../../../common/utils/ocrTableRegion";

function roundRect(r: Rect) {
  return {
    x: Math.round(r.x),
    y: Math.round(r.y),
    width: Math.round(r.width),
    height: Math.round(r.height),
  };
}

export function buildExportPayload(params: {
  templateName: string;
  loaded: LoadedImage | null;
  regions: Region[];
  documentType?: string;
}) {
  const { templateName, loaded, regions, documentType } = params;

  // ✅ tables 제거
  if (!loaded)
    return { templateName, file: null, image: null, regions: [] as any[] };

  return {
    templateName,
    ...(documentType ? { documentType } : {}),
    file: { name: loaded.fileName },
    // src 포함 — 템플릿 재로드 시 이미지 복원에 사용
    image: { width: loaded.naturalWidth, height: loaded.naturalHeight, src: loaded.src },
    regions: regions.map((r) => {
      const base: any = {
        id: r.id,
        name: r.name,
        fieldType: r.fieldType,
        x: Math.round(r.x),
        y: Math.round(r.y),
        width: Math.round(r.width),
        height: Math.round(r.height),
      };

      // koField/enField 등 메타 — 모든 타입(table 포함)에 포함
      if (r.koField !== undefined) base.koField = r.koField;
      if (r.enField !== undefined) base.enField = r.enField;
      if (r.canonicalField !== undefined) base.canonicalField = r.canonicalField;
      if (r.mappingStatus !== undefined) base.mappingStatus = r.mappingStatus;
      if (r.valueType !== undefined) base.valueType = r.valueType;

      if (r.fieldType === "multi") {
        const parts = r.parts ?? 2;
        const ratios = normalizeRatios(parts, r.ratios);
        base.parts = parts;
        base.ratios = ratios;
        const rr: Region = { ...r, parts, ratios };
        base.subRegions = calcMultiSubRegions(rr);
      }

      if (r.fieldType === "check") base.checkMode = "boxOnly";

      if (r.fieldType === "table") {
        const guides = normalizeColGuides(r.table?.colGuides);
        const mode = (r.table?.mode ?? "repeat") as "repeat" | "auto";
        const anchor = r.table?.rowTemplate
          ? r.table.rowTemplate
          : ({ x: r.x, y: r.y, width: r.width, height: r.height } as Rect);
        const colX = guides.map((g) => Math.round(anchor.x + anchor.width * g));
        // TPL-12B: when rowOverrides is present, fold them into rows via the
        // pure materialization helper. When absent (legacy templates), keep
        // the original rows verbatim — saved output is byte-identical to the
        // pre-TPL-12B contract. rowOverrides itself is preserved as a
        // separate key for round-trip / future edits (frontend-only metadata;
        // backend ignores it).
        const baseRowsForSave: Rect[] = Array.isArray(r.table?.rows)
          ? r.table!.rows!.map((rr) => ({ ...rr }))
          : [];
        const hasRowOverrides = Array.isArray(r.table?.rowOverrides);
        const area: Rect = { x: r.x, y: r.y, width: r.width, height: r.height };
        const savedRows: Rect[] = hasRowOverrides
          ? materializeTableRowsWithOverrides(
              baseRowsForSave,
              r.table!.rowOverrides,
              area,
            ).map((rr) => roundRect(rr))
          : baseRowsForSave.map((rr) => roundRect(rr));
        base.table = {
          mode,
          rowTemplate: r.table?.rowTemplate
            ? roundRect(r.table.rowTemplate)
            : null,
          rows: savedRows,
          colGuides: guides,
          colX,
          stopKeywords: Array.isArray(r.table?.stopKeywords)
            ? r.table!.stopKeywords!.slice(0, 30)
            : [],
          // OP-2: 테이블 이름 + 컬럼 canonical 매핑
          ...(r.table?.tableName ? { tableName: r.table.tableName } : {}),
          ...(Array.isArray(r.table?.columns) ? { columns: r.table!.columns } : {}),
          // TPL-12B: sparse per-row overrides preserved verbatim when present.
          // Absent input → key omitted (legacy byte-compat).
          ...(hasRowOverrides
            ? { rowOverrides: r.table!.rowOverrides!.map((ov) => ({ ...ov })) }
            : {}),
        };
      }

      return base;
    }),
  };
}
