import { NextResponse } from "next/server";

const NTS_API_URL = "https://api.odcloud.kr/api/nts-businessman/v1/status";

export async function POST(req: Request) {
  const { bizNumbers } = await req.json();
  if (!bizNumbers?.length) return NextResponse.json({ error: "no bizNumbers" }, { status: 400 });

  const apiKey = process.env.NTS_API_KEY;
  if (!apiKey) {
    // API 키 없으면 체크섬만 통과된 것으로 응답 (개발 모드)
    return NextResponse.json({
      data: bizNumbers.map((b: string) => ({ b_no: b.replace(/-/g, ""), b_stt: "계속사업자", b_stt_cd: "01", tax_type: "부가가치세 일반과세자", end_dt: "" })),
    });
  }

  try {
    const res = await fetch(`${NTS_API_URL}?serviceKey=${apiKey}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ b_no: bizNumbers.map((b: string) => b.replace(/-/g, "")) }),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    console.error("NTS API error", e);
    return NextResponse.json({ error: "api_failed" }, { status: 502 });
  }
}
