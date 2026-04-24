import type { AxiosResponse } from "axios";
import api, { ApiResponseError } from "./axios";

type UiLike = {
  withLoading: <T>(fn: () => Promise<T>) => Promise<T>;
  alert: (arg: string | { title?: string; message: string; okText?: string }) => Promise<void>;
};

export type RunApiOptions<T> = {
  action: () => Promise<T>;
  loading?: boolean;
  successMessage?: string;
  errorMessage?: string;
  silent?: boolean;
  rethrow?: boolean;
};

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof ApiResponseError) {
    return error.message || "요청 처리 중 오류가 발생했습니다.";
  }

  if (typeof error === "object" && error !== null) {
    const err = error as {
      message?: unknown;
      code?: unknown;
      response?: {
        status?: unknown;
        data?: Record<string, unknown>;
      };
    };

    const data = err.response?.data;
    const serverMessage =
      data?.ResultMsg ??
      data?.message ??
      data?.msg ??
      (typeof data?.error === "string" ? data.error : undefined);

    if (typeof serverMessage === "string" && serverMessage.trim()) {
      return serverMessage.trim();
    }

    const status = typeof err.response?.status === "number" ? err.response.status : undefined;

    if (status === 401) return "인증이 만료되었습니다. 다시 로그인해 주세요.";
    if (status === 403) return "접근 권한이 없습니다.";
    if (status === 404) return "요청한 API를 찾을 수 없습니다.";
    if (status === 500) return "서버 내부 오류가 발생했습니다.";

    if (err.code === "ERR_NETWORK") {
      return "서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요.";
    }

    if (typeof err.message === "string" && err.message.trim()) {
      return err.message.trim();
    }
  }

  return "요청 처리 중 오류가 발생했습니다.";
}

export function unwrapData<T = unknown>(response: AxiosResponse | undefined | null): T | undefined {
  const data = response?.data as
    | {
        resultMap?: T;
        resultData?: T;
        data?: T;
      }
    | T
    | undefined;

  if (!data) return undefined;
  if (typeof data === "object" && data !== null) {
    const obj = data as { resultMap?: T; resultData?: T; data?: T };
    if (obj.resultMap !== undefined) return obj.resultMap;
    if (obj.resultData !== undefined) return obj.resultData;
    if (obj.data !== undefined) return obj.data;
  }

  return data as T;
}

export function unwrapList<T = unknown>(
  response: AxiosResponse | undefined | null,
  key = "boardList",
): T[] {
  const data = unwrapData<Record<string, unknown>>(response);
  const list = data?.[key];
  return Array.isArray(list) ? (list as T[]) : [];
}

export async function runApi<T>(ui: UiLike, options: RunApiOptions<T>): Promise<T | undefined> {
  const {
    action,
    loading = true,
    successMessage,
    errorMessage,
    silent = false,
    rethrow = false,
  } = options;

  try {
    const result = loading ? await ui.withLoading(action) : await action();

    if (successMessage) {
      await ui.alert(successMessage);
    }

    return result;
  } catch (error) {
    const message = errorMessage || getApiErrorMessage(error);

    if (!silent) {
      await ui.alert(message);
    }

    if (rethrow) {
      throw error;
    }

    return undefined;
  }
}

export function downloadBlob(blob: Blob, fileName: string) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export async function runDownloadApi(
  ui: UiLike,
  action: () => Promise<AxiosResponse<Blob>>,
  fileName: string,
  errorMessage = "파일 다운로드 중 오류가 발생했습니다.",
) {
  const response = await runApi(ui, {
    action,
    errorMessage,
  });

  if (!response) return;

  downloadBlob(response.data, fileName);
}

export { api };
