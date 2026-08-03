import type {
  ChatMessage,
  ChatResponse,
  ConversationDetail,
  ConversationsResponse,
  FAQResponse,
  HealthResponse,
  ProductListResponse,
  QualityResponse,
  SummaryResponse
} from "../types";

type RequestOptions = {
  method?: "GET" | "POST";
  body?: unknown;
  signal?: AbortSignal;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(path, {
    method: options.method ?? "GET",
    headers:
      options.body === undefined
        ? undefined
        : {
            "Content-Type": "application/json"
          },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal
  });

  const text = await response.text();
  const payload = text ? safeJson(text) : {};

  if (!response.ok) {
    throw new Error(extractError(payload, response.status));
  }

  return payload as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return { message: text };
  }
}

function extractError(payload: unknown, status: number): string {
  if (payload && typeof payload === "object") {
    const detail = "detail" in payload ? (payload as { detail?: unknown }).detail : undefined;
    if (detail && typeof detail === "object" && "message" in detail) {
      return String((detail as { message?: unknown }).message);
    }
    if (typeof detail === "string") {
      return detail;
    }
    if ("message" in payload) {
      return String((payload as { message?: unknown }).message);
    }
  }
  return `请求失败，状态码 ${status}`;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  ready: () => request<HealthResponse>("/ready"),
  products: () => request<ProductListResponse>("/api/products"),
  conversations: (accountId: string, limit = 30) =>
    request<ConversationsResponse>(
      `/api/conversations?limit=${limit}&account_id=${encodeURIComponent(accountId)}`
    ),
  conversation: (conversationId: string, accountId: string) =>
    request<ConversationDetail>(
      `/api/conversations/${encodeURIComponent(conversationId)}?account_id=${encodeURIComponent(
        accountId
      )}`
    ),
  chat: (input: {
    message: string;
    accountId: string;
    conversationId?: string | null;
    supportFunctions: string[];
    productList: string[];
    history: ChatMessage[];
  }) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: {
        message: input.message,
        account_id: input.accountId,
        conversation_id: input.conversationId || undefined,
        support_functions: input.supportFunctions,
        product_list: input.productList,
        history: input.history,
        model: "customer-service-agent"
      }
    }),
  summary: (messages: ChatMessage[]) =>
    request<SummaryResponse>("/api/summary", {
      method: "POST",
      body: {
        messages,
        model: "customer-service-agent"
      }
    }),
  quality: (content: string, keywords: string) =>
    request<QualityResponse>("/api/quality-check", {
      method: "POST",
      body: {
        content,
        keywords,
        model: "customer-service-agent"
      }
    }),
  saveFaq: (input: { question: string; answer: string; score: number; accountId: string }) =>
    request<FAQResponse>("/api/faqs", {
      method: "POST",
      body: {
        question: input.question.slice(0, 100),
        answer: input.answer.slice(0, 500),
        score: input.score,
        account_id: input.accountId
      }
    })
};
