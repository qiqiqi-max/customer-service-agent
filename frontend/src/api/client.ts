import type {
  ChatMessage,
  ChatResponse,
  ConversationDetail,
  ConversationsResponse,
  FAQResponse,
  HealthResponse,
  ProductListResponse,
  QualityResponse,
  RefundRecord,
  SummaryResponse
  , ToolCallRecord, QualityReviewRecord, FAQCandidateRecord
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
  conversations: (accountId: string, limit = 20, offset = 0) =>
    request<ConversationsResponse>(
      `/api/conversations?limit=${limit}&offset=${offset}&account_id=${encodeURIComponent(accountId)}`
    ),
  conversation: (conversationId: string, accountId: string) =>
    request<ConversationDetail>(
      `/api/conversations/${encodeURIComponent(conversationId)}?account_id=${encodeURIComponent(
        accountId
      )}`
    ),
  toolCalls: (conversationId: string, accountId: string, limit = 100) =>
    request<{ conversation_id: string; tool_calls: ToolCallRecord[] }>(
      `/api/conversations/${encodeURIComponent(
        conversationId
      )}/tool-calls?account_id=${encodeURIComponent(accountId)}&limit=${limit}`
    ),
  qualityReviews: (accountId: string, conversationId?: string | null, limit = 50) =>
    request<{ reviews: QualityReviewRecord[]; total?: number }>(
      `/api/quality-reviews?account_id=${encodeURIComponent(accountId)}${conversationId ? `&conversation_id=${encodeURIComponent(conversationId)}` : ""}&limit=${limit}`
    ),
  faqCandidates: (accountId: string, limit = 50) =>
    request<{ candidates: FAQCandidateRecord[]; total?: number }>(
      `/api/faq-candidates?account_id=${encodeURIComponent(accountId)}&limit=${limit}`
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
  quality: (
    content: string,
    keywords: string,
    conversationId?: string | null,
    accountId?: string
  ) =>
    request<QualityResponse>("/api/quality-check", {
      method: "POST",
      body: {
        content,
        keywords,
        account_id: accountId || "100000",
        conversation_id: conversationId || undefined,
        model: "customer-service-agent"
      }
    }),
  saveFaq: (input: {
    question: string;
    answer: string;
    score: number;
    accountId: string;
    conversationId?: string | null;
  }) =>
    request<FAQResponse>("/api/faqs", {
      method: "POST",
      body: {
        question: input.question.slice(0, 100),
        answer: input.answer.slice(0, 500),
        score: input.score,
        account_id: input.accountId,
        conversation_id: input.conversationId || undefined
      }
    })
  ,refundAction: (refundId: string, action: "approve" | "reject" | "execute", accountId: string) =>
    request<RefundRecord>(`/api/refunds/${encodeURIComponent(refundId)}/${action}`, {
      method: "POST",
      body: { account_id: accountId }
    })
};
