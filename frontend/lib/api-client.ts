import type { AgentChatRequest, AgentChatResponse } from "../types/agent";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

export type HealthResponse = {
  status: string;
  environment: string;
  ai_provider: string;
  market_data_provider: string;
};

export type StockSummary = {
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  price: number;
  change_percent: number;
  data_status: string;
  source: string;
};

export type PriceBar = {
  trading_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type StockHistoryResponse = {
  symbol: string;
  interval: "1d" | "1w";
  data_status: string;
  source: string;
  bars: PriceBar[];
  warning?: string;
};

type ErrorPayload = {
  detail?: string | Array<{ msg?: string }>;
  message?: string;
};

export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;

  constructor(message: string, status: number, payload?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function errorMessage(payload: ErrorPayload | null, status: number) {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    const messages = payload.detail.map((item) => item.msg).filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  if (payload?.message) return payload.message;
  return `API request failed with status ${status}.`;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(
      "Cannot reach the backend. Check that the API is running and the frontend URL is configured.",
      0,
      error,
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? ((await response.json()) as unknown)
    : await response.text();

  if (!response.ok) {
    throw new ApiError(
      errorMessage(
        typeof payload === "object" && payload !== null
          ? (payload as ErrorPayload)
          : null,
        response.status,
      ),
      response.status,
      payload,
    );
  }
  return payload as T;
}

export const apiClient = {
  health(signal?: AbortSignal) {
    return request<HealthResponse>("/api/v1/health", { signal });
  },

  listStocks(query?: string, signal?: AbortSignal) {
    const search = query?.trim()
      ? `?query=${encodeURIComponent(query.trim())}`
      : "";
    return request<StockSummary[]>(`/api/v1/stocks${search}`, { signal });
  },

  getStock(symbol: string, signal?: AbortSignal) {
    return request<StockSummary>(
      `/api/v1/stocks/${encodeURIComponent(symbol.trim().toUpperCase())}`,
      { signal },
    );
  },

  getStockHistory(symbol: string, days = 30, signal?: AbortSignal) {
    const normalizedDays = Math.min(90, Math.max(5, Math.trunc(days)));
    return request<StockHistoryResponse>(
      `/api/v1/stocks/${encodeURIComponent(symbol.trim().toUpperCase())}/history?days=${normalizedDays}`,
      { signal },
    );
  },

  chat(payload: AgentChatRequest, signal?: AbortSignal) {
    return request<AgentChatResponse>("/api/v1/agent/chat", {
      method: "POST",
      body: JSON.stringify(payload),
      signal,
    });
  },
};
