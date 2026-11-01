import { FUNCTION_LABELS } from "../data/workbench";
import type { BotUsage, ChatMessage, ExecutionRecord, ResultCard } from "../types";

export function botUsageToInsights(botUsage?: BotUsage | null): {
  executions: ExecutionRecord[];
  results: ResultCard[];
} {
  const actions = botUsage?.action_details ?? [];
  const executions: ExecutionRecord[] = [];
  const results: ResultCard[] = [];

  actions.forEach((action, actionIndex) => {
    (action.tool_details ?? []).forEach((tool, toolIndex) => {
      const toolName = tool.name || action.name || "tool";
      executions.push({
        id: `${actionIndex}-${toolIndex}-${toolName}`,
        action: action.name || "工具调用",
        tool: FUNCTION_LABELS.get(toolName) || toolName,
        input: tool.input,
        output: tool.output
      });
      results.push(normalizeResult(toolName, tool.output, `${actionIndex}-${toolIndex}`));
    });
  });

  return { executions, results: results.filter(Boolean) };
}

export function collectInsights(messages: ChatMessage[]) {
  return messages.reduce(
    (acc, message) => {
      const usage = message.metadata?.bot_usage as BotUsage | undefined;
      const insights = botUsageToInsights(usage);
      acc.executions.push(...insights.executions);
      acc.results.push(...insights.results);
      return acc;
    },
    { executions: [] as ExecutionRecord[], results: [] as ResultCard[] }
  );
}

export function normalizeResult(toolName: string, output: unknown, id: string): ResultCard {
  const value = Array.isArray(output) ? output[0] : output;
  const fields =
    value && typeof value === "object"
      ? Object.entries(value as Record<string, unknown>)
          .slice(0, 6)
          .map(([label, fieldValue]) => ({ label, value: formatValue(fieldValue) }))
      : [{ label: "结果", value: formatValue(output) }];

  return {
    id: `${toolName}-${id}`,
    type: FUNCTION_LABELS.get(toolName) || toolName,
    title: inferTitle(toolName, value),
    status: value && typeof value === "object" && toolName === "order_refund"
      ? String((value as Record<string, unknown>).status || "") || undefined
      : undefined,
    fields,
    raw: output
  };
}

function inferTitle(toolName: string, value: unknown) {
  if (value && typeof value === "object") {
    const item = value as Record<string, unknown>;
    return String(item.product_name || item.order_id || item.document_name || item.title || toolName);
  }
  return FUNCTION_LABELS.get(toolName) || toolName;
}

export function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "暂无";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value, null, 2);
}

export function formatTime(value?: string) {
  if (!value) {
    return "暂无时间";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}
