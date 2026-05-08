export const runtime = "nodejs";
export const maxDuration = 300;

function backendExtractUrl(): string {
  const base = process.env.BACKEND_URL || "http://localhost:8000";
  return `${base.replace(/\/$/, "")}/ocr/extract`;
}

export async function POST(request: Request) {
  try {
    const incoming = await request.formData();
    const forwarded = new FormData();

    for (const [key, value] of incoming.entries()) {
      forwarded.append(key, value);
    }

    const backendResponse = await fetch(backendExtractUrl(), {
      method: "POST",
      body: forwarded,
    });
    const body = await backendResponse.text();
    const contentType = backendResponse.headers.get("content-type") || "text/plain; charset=utf-8";

    return new Response(body, {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      headers: {
        "content-type": contentType,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("[api/ocr-extract] proxy failed", error);
    return Response.json(
      {
        detail: "OCR backend proxy failed",
        message,
      },
      { status: 502 },
    );
  }
}
