/**
 * OCR API 호출 helper.
 *
 * 역할:
 * - endpoint 결정 (NEXT_PUBLIC_BACKEND_URL 유무 → `${backend}/ocr/extract`
 *   vs `/api/ocr-extract` 라우트).
 * - buildOcrFormData 로 FormData 구성을 위임.
 * - POST fetch / `!res.ok` 체크 / `res.json()` 파싱까지 담당.
 *
 * Boundary (반드시 지킬 것):
 * - UI loading/error state, response mapping, history/autofill/restore 를
 *   여기 두지 않는다 — RunOcrWorkspace 의 try/catch/finally 가 담당.
 * - response JSON shape 를 변환하지 않고 raw 로 반환한다 (downstream 의
 *   `json?.full_text`, `json?.receipt_fields?.["사업자번호"]`, buildRunOcrResult
 *   호출 흐름을 무손실 보존하기 위함).
 * - 에러 메시지 `"OCR 요청 실패"` 는 RunOcrWorkspace 의 catch 블록과 묶여
 *   있어 임의 변경 금지.
 */
import { buildOcrFormData, type BuildOcrFormDataInput } from "./buildOcrFormData";

/**
 * runOcrRequest 의 입력. buildOcrFormData 입력에 optional `endpoint` override
 * 만 더해진다. 미지정 시 환경변수 기반 기본 endpoint 가 사용된다.
 */
export type RunOcrRequestInput = BuildOcrFormDataInput & {
  endpoint?: string;
};

export type RunOcrRawResponse = Record<string, unknown>;

// Returns the raw `res.json()` value as-is to preserve the downstream
// consumption pattern in RunOcrWorkspace (which inspects ad-hoc fields like
// `json?.full_text`, `json?.receipt_fields?.["사업자번호"]`). Typed as `any`
// for parity with the prior inline `await res.json()` behavior; consumers
// that want a stricter type can narrow via `RunOcrRawResponse`.
/**
 * OCR `/ocr/extract` 요청을 한 번 실행하고 raw JSON 응답을 그대로 반환한다.
 *
 * 처리 흐름:
 * 1. endpoint 결정 (`input.endpoint` > 환경변수 기반 기본값).
 * 2. buildOcrFormData(input) 로 FormData 구성.
 * 3. POST fetch.
 * 4. `!res.ok` 면 `new Error("OCR 요청 실패")` throw.
 * 5. `await res.json()` 결과 그대로 반환.
 *
 * 반환 타입이 `any` 인 것은 downstream consumer (RunOcrWorkspace 의
 * buildRunOcrResult 등) 가 임의 필드를 ad-hoc 접근하는 패턴과의 1:1 parity 를
 * 보존하기 위한 의도된 선택이다.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function runOcrRequest(input: RunOcrRequestInput): Promise<any> {
  const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || "";
  const ocrEndpoint = input.endpoint ?? (backendBase ? `${backendBase}/ocr/extract` : "/api/ocr-extract");
  const formData = buildOcrFormData(input);
  const res = await fetch(ocrEndpoint, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("OCR 요청 실패");
  return await res.json();
}
