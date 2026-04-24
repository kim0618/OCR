import axios from "axios";
import { clearLogin, getStoredLogin } from "./login";

class ApiResponseError extends Error {
  code?: string;
  status?: number;

  constructor(message: string, code?: string, status?: number) {
    super(message);
    this.name = "ApiResponseError";
    this.code = code;
    this.status = status;
  }
}

function normalizeToken(token?: string) {
  if (!token) return "";
  const trimmed = token.trim();
  return trimmed.startsWith("Bearer ") ? trimmed.substring(7).trim() : trimmed;
}

function extractResponseMessage(data: unknown) {
  if (!data || typeof data !== "object") return "";
  const obj = data as Record<string, unknown>;
  const candidates = [
    obj.ResultMsg,
    obj.message,
    obj.msg,
    typeof obj.error === "string" ? obj.error : "",
  ];

  for (const item of candidates) {
    if (typeof item === "string" && item.trim()) {
      return item.trim();
    }
  }

  return "";
}

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
  withCredentials: true,
});

function isPublicPath(url?: string) {
  if (!url) return false;
  const path = url.startsWith("http") ? (() => {
    try {
      return new URL(url).pathname;
    } catch {
      return url;
    }
  })() : url;

  return ["/login", "/join", "/changePassWord", "/pwSendMail"].some((item) => path === item || path.endsWith(item));
}

api.interceptors.request.use((config) => {
  const login = getStoredLogin();
  const pureToken = normalizeToken(login?.accessToken);
  const publicPath = isPublicPath(config.url);

  config.headers = config.headers ?? {};

  if (pureToken && !publicPath) {
    config.headers.Authorization = `Bearer ${pureToken}`;
  } else if (publicPath && 'Authorization' in config.headers) {
    delete (config.headers as Record<string, unknown>).Authorization;
  }

  const isPlainObject =
    config.data &&
    typeof config.data === "object" &&
    !(config.data instanceof FormData) &&
    !(config.data instanceof URLSearchParams);

  if (isPlainObject) {
    const body = { ...config.data } as Record<string, unknown>;

    if (!publicPath && login?.user_id) {
      if (body.gvLoginId == null || body.gvLoginId === "") {
        body.gvLoginId = login.user_id;
      }
      if (body.user_id == null || body.user_id === "") {
        body.user_id = login.user_id;
      }
    }

    config.data = body;
  }

  return config;
});

api.interceptors.response.use(
  (response) => {
    const data = response.data as
      | { ResultCode?: string; ResultMsg?: string; loginCode?: string; message?: string }
      | undefined;

    if (data?.loginCode === "9999") {
      clearLogin();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      return Promise.reject(new ApiResponseError("로그인 세션이 만료되었습니다.", "9999", 401));
    }

    if (data?.ResultCode === "Validation") {
      return Promise.reject(
        new ApiResponseError(data.ResultMsg || "요청 처리 중 오류가 발생했습니다.", "Validation", response.status),
      );
    }

    return response;
  },
  (error) => {
    const status = error?.response?.status;
    const message =
      extractResponseMessage(error?.response?.data) ||
      (status === 401 ? "인증이 만료되었습니다. 다시 로그인해 주세요." : "요청 처리 중 오류가 발생했습니다.");

    if (status === 401) {
      clearLogin();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }

    return Promise.reject(new ApiResponseError(message, String(status || "ERROR"), status));
  },
);

export default api;
export { ApiResponseError };
