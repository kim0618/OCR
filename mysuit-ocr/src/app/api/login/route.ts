import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const userId = body.user_id || "test";

  return NextResponse.json({
    resultMap: {
      accessToken: "local-test-token",
      user_id: userId,
      user_nm: userId,
      adminYn: "Y",
      masterYn: "N",
      comp_cd: "LOCAL",
      comp_nm: "로컬 테스트",
      envMysuitUrl: "",
      envMagellanVersion: "",
    },
  });
}
