import { X } from "lucide-react";
import { useState } from "react";
import type {
  ChatMessage,
  ConversationSummary,
  ExecutionRecord,
  RefundAction,
  ResultCard,
  ScenarioPreset
} from "../types";
import { ResultList, TraceList } from "./results";

type ContextTab = "overview" | "trace" | "results";

export function ContextPanel(props: {
  activeScenario: ScenarioPreset;
  conversationId: string | null;
  conversations: ConversationSummary[];
  executionRecords: ExecutionRecord[];
  messages: ChatMessage[];
  open: boolean;
  resultCards: ResultCard[];
  selectedFunctionCount: number;
  selectedProductCount: number;
  onClose: () => void;
  onOpenConversation: (id: string) => void;
  onRefundAction: (refundId: string, action: RefundAction) => Promise<void>;
}) {
  const [tab, setTab] = useState<ContextTab>("overview");
  const latestUser = [...props.messages].reverse().find((item) => item.role === "user");
  const tabs: [ContextTab, string, number | null][] = [
    ["overview", "概况", null],
    ["trace", "工具", props.executionRecords.length],
    ["results", "结果", props.resultCards.length]
  ];

  return (
    <>
      {props.open && <div className="drawer-backdrop" onClick={props.onClose} />}
      <aside className={props.open ? "context panel is-open" : "context panel"} aria-label="工作上下文">
        <div className="context-head">
          <h2>工作上下文</h2>
          <button className="icon-btn" onClick={props.onClose} title="收起面板" type="button">
            <X size={16} />
          </button>
        </div>
        <div className="tabs" role="tablist" aria-label="工作上下文">
          {tabs.map(([value, label, count]) => (
            <button
              key={value}
              aria-selected={tab === value}
              className={tab === value ? "tab is-active" : "tab"}
              onClick={() => setTab(value)}
              role="tab"
              type="button"
            >
              {label}
              {count !== null && <span className={count ? "badge accent" : "badge"}>{count}</span>}
            </button>
          ))}
        </div>

        <div className="context-body" role="tabpanel">
          {tab === "overview" && (
            <>
              <section>
                <h3 className="section-label">本轮概况</h3>
                <dl className="kv">
                  <dt>接待场景</dt>
                  <dd>{props.activeScenario.label}</dd>
                  <dt>工具权限</dt>
                  <dd>{props.selectedFunctionCount} 项</dd>
                  <dt>商品范围</dt>
                  <dd>{props.selectedProductCount} 个</dd>
                  <dt>工具调用</dt>
                  <dd>{props.executionRecords.length} 条</dd>
                  <dt>工单结果</dt>
                  <dd>{props.resultCards.length} 条</dd>
                </dl>
              </section>
              <section>
                <h3 className="section-label">最近诉求</h3>
                {latestUser ? <p className="quote">{latestUser.content}</p> : <p className="empty">尚未开始接待。</p>}
              </section>
              <section>
                <h3 className="section-label">最近会话</h3>
                {props.conversations.length ? (
                  <div className="recent-list">
                    {props.conversations.slice(0, 6).map((item) => (
                      <button
                        key={item.id}
                        className={item.id === props.conversationId ? "recent-item is-current" : "recent-item"}
                        onClick={() => props.onOpenConversation(item.id)}
                        type="button"
                      >
                        <strong>{item.title || "未命名会话"}</strong>
                        <span>{item.last_message || "暂无消息"}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="empty">暂无历史会话。</p>
                )}
              </section>
            </>
          )}
          {tab === "trace" && <TraceList records={props.executionRecords} />}
          {tab === "results" && <ResultList cards={props.resultCards} onAction={props.onRefundAction} />}
        </div>
      </aside>
    </>
  );
}
