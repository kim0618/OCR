import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { DATASET_FOLDERS } from "@/common/config/testsets";

type GtRecord = { fields: Record<string, string>; type: string; updated_at: string; financeFields?: Record<string, string>; documentFields?: Record<string, string> };
type OcrCacheRecord = { ocr_text: string; scanned_at: string };

function datasetPaths(req: Request) {
  const { searchParams } = new URL(req.url);
  const folder = DATASET_FOLDERS[searchParams.get("dataset") || "baseline"] || DATASET_FOLDERS.baseline;
  const base = path.join(process.cwd(), "public", "data", "testsets", folder);
  fs.mkdirSync(base, { recursive: true });
  return {
    gtPath: path.join(base, "ground_truth.json"),
    cachePath: path.join(base, "ocr_cache.json"),
  };
}

function parseAndMigrate(raw: Record<string, unknown>): {
  gt: Record<string, GtRecord>;
  extracted: Record<string, OcrCacheRecord>;
} {
  const gt: Record<string, GtRecord> = {};
  const extracted: Record<string, OcrCacheRecord> = {};

  for (const [key, val] of Object.entries(raw)) {
    if (!val || typeof val !== "object") continue;
    const v = val as Record<string, unknown>;
    const fields = ("fields" in v ? v.fields : val) as Record<string, string>;
    gt[key] = {
      fields,
      type: (v.type as string) || "영수증",
      updated_at: (v.updated_at as string) || "",
      ...(v.financeFields && typeof v.financeFields === "object"
        ? { financeFields: v.financeFields as Record<string, string> }
        : {}),
      ...(v.documentFields && typeof v.documentFields === "object"
        ? { documentFields: v.documentFields as Record<string, string> }
        : {}),
    };
    if (typeof v.ocr_text === "string" && v.ocr_text) {
      extracted[key] = { ocr_text: v.ocr_text, scanned_at: (v.updated_at as string) || "" };
    }
  }
  return { gt, extracted };
}

export async function GET(req: Request) {
  const { gtPath, cachePath } = datasetPaths(req);
  try {
    const raw = JSON.parse(fs.readFileSync(gtPath, "utf-8"));
    const { gt, extracted } = parseAndMigrate(raw);

    if (Object.keys(extracted).length > 0) {
      let existingCache: Record<string, OcrCacheRecord> = {};
      try {
        existingCache = JSON.parse(fs.readFileSync(cachePath, "utf-8"));
      } catch {
        existingCache = {};
      }
      const mergedCache = { ...extracted, ...existingCache };
      fs.writeFileSync(cachePath, JSON.stringify(mergedCache, null, 2), "utf-8");
      fs.writeFileSync(gtPath, JSON.stringify(gt, null, 2), "utf-8");
    }

    return NextResponse.json(gt);
  } catch {
    return NextResponse.json({});
  }
}

export async function POST(req: Request) {
  const { gtPath } = datasetPaths(req);
  const body = await req.json();
  fs.writeFileSync(gtPath, JSON.stringify(body, null, 2), "utf-8");
  return NextResponse.json({ ok: true });
}
