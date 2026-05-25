import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { DATASET_FOLDERS } from "@/common/config/testsets";

function cachePath(req: Request) {
  const { searchParams } = new URL(req.url);
  const folder = DATASET_FOLDERS[searchParams.get("dataset") || "baseline"] || DATASET_FOLDERS.baseline;
  const base = path.join(process.cwd(), "public", "data", "testsets", folder);
  fs.mkdirSync(base, { recursive: true });
  return path.join(base, "autofill_cache.json");
}

export async function GET(req: Request) {
  try {
    return NextResponse.json(JSON.parse(fs.readFileSync(cachePath(req), "utf-8")));
  } catch {
    return NextResponse.json({});
  }
}

export async function POST(req: Request) {
  const body = await req.json();
  fs.writeFileSync(cachePath(req), JSON.stringify(body, null, 2), "utf-8");
  return NextResponse.json({ ok: true });
}
