import type { LoadedImage, Rect, Region } from "./types";
import { calcMultiSubRegions, normalizeRatios } from "./ops";
import { normalizeColGuides } from "./table";

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
        base.table = {
          mode,
          rowTemplate: r.table?.rowTemplate
            ? roundRect(r.table.rowTemplate)
            : null,
          rows: Array.isArray(r.table?.rows)
            ? r.table!.rows!.map((rr) => roundRect(rr))
            : [],
          colGuides: guides,
          colX,
          stopKeywords: Array.isArray(r.table?.stopKeywords)
            ? r.table!.stopKeywords!.slice(0, 30)
            : [],
          // OP-2: 테이블 이름 + 컬럼 canonical 매핑
          ...(r.table?.tableName ? { tableName: r.table.tableName } : {}),
          ...(Array.isArray(r.table?.columns) ? { columns: r.table!.columns } : {}),
        };
      }

      return base;
    }),
  };
}
