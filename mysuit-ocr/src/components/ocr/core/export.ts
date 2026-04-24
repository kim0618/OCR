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
}) {
  const { templateName, loaded, regions } = params;

  // ✅ tables 제거
  if (!loaded)
    return { templateName, file: null, image: null, regions: [] as any[] };

  return {
    templateName,
    file: { name: loaded.fileName },
    image: { width: loaded.naturalWidth, height: loaded.naturalHeight },
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
        };
      }

      return base;
    }),
  };
}
