import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { TESTSETS, getTestset } from "@/lib/testsets";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const testset = getTestset(searchParams.get("dataset"));
  const dir = path.join(process.cwd(), "public", "data", "testsets", testset.folder);
  const exts = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf"];
  let files: string[] = [];

  try {
    files = fs
      .readdirSync(dir)
      .filter((filename) => exts.includes(path.extname(filename).toLowerCase()))
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  } catch {
    // Missing dataset folders should render as empty tabs.
  }

  return NextResponse.json({
    testsets: TESTSETS,
    current: testset.id,
    imageBaseUrl: testset.path,
    images: files,
  });
}
