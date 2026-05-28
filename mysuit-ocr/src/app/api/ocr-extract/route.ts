export const runtime = "nodejs";
export const maxDuration = 300;

function backendExtractUrl(): string {
  // 백엔드는 항상 9099 (uvicorn). .env.local의 BACKEND_URL이 비어 있어도
  // 8000 같은 잘못된 포트로 떨어지지 않도록 fallback도 9099로 못박는다.
  const base = process.env.BACKEND_URL || "http://127.0.0.1:9099";
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
