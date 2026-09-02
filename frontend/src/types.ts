export type Role = "user" | "assistant" | "system" | "tool";

export type Product = {
  name: string;
  description: string;
  cover_image: string;
};

export type ProductListResponse = {
  products: Product[];
  total: number;
};

export type ChatMessage = {
  role: Role;
  content: string;
  metadata?: Record<string, unknown>;
};

export type ConversationSummary = {
  id: string;
  account_id?: string;
  title?: string;
  last_message?: string;
  updated_at?: string;
  created_at?: string;
};

export type ConversationDetail = ConversationSummary & {
  messages?: ChatMessage[];
};

export type ConversationsResponse = {
  conversations?: ConversationSummary[];
  total?: number;
};

export type ToolDetail = {
  name?: string;
  input?: unknown;
  output?: unknown;
};

export type ActionDetail = {
  name?: string;
  tool_details?: ToolDetail[];
};

export type BotUsage = {
  action_details?: ActionDetail[];
  [key: string]: unknown;
};

export type ChatResponse = {
  conversation_id?: string;
  answer?: string;
  metadata?: Record<string, unknown>;
  bot_usage?: BotUsage | null;
};

export type QualityStructuredResult = {
  risk_level?: "none" | "low" | "medium" | "high";
  score?: number;
  hit_count?: number;
  hits?: Array<{
    keyword?: string;
    level?: string;
    reason?: string;
  }>;
  suggestions?: string[];
};

export type QualityResponse = {
  result?: string;
  structured_result?: QualityStructuredResult;
  metadata?: Record<string, unknown>;
  bot_usage?: BotUsage | null;
};

export type SummaryResponse = {
  summary?: string;
  metadata?: Record<string, unknown>;
  bot_usage?: BotUsage | null;
};

export type FAQResponse = {
  message?: string;
};

export type ToolCallRecord = { id?: number; tool_name?: string; input_json?: unknown; output_json?: unknown; created_at?: number };
export type QualityReviewRecord = { id?: number; conversation_id?: string; content?: string; result?: string; structured_result?: QualityStructuredResult; created_at?: number };
export type FAQCandidateRecord = { id?: number; question?: string; answer?: string; score?: number; status?: string; created_at?: number };

export type HealthResponse = {
  status?: string;
  service?: string;
  checks?: Record<string, boolean>;
};

export type SupportFunction = {
  key: string;
  label: string;
  description: string;
};

export type ScenarioPreset = {
  id: string;
  label: string;
  tone: string;
  functions: string[];
  prompts: string[];
};

export type ResultCard = {
  id: string;
  type: string;
  title: string;
  status?: string;
  fields: Array<{ label: string; value: string }>;
  raw?: unknown;
};

export type RefundStatus = "pending_approval" | "approved" | "executed" | "rejected" | "failed";

export type RefundRecord = {
  id?: string;
  refund_id?: string;
  account_id?: string;
  order_id?: string;
  reason?: string;
  status?: RefundStatus | string;
  message?: string;
  failure_reason?: string | null;
  created_at?: number;
  updated_at?: number;
};

export type ExecutionRecord = {
  id: string;
  action: string;
  tool: string;
  input: unknown;
  output: unknown;
};
