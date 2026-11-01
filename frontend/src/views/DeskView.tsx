import { Loader2, Send, UserRound } from "lucide-react";
import { FormEvent, useState } from "react";
import { TraceList, ResultList } from "../components/results";
import { SCENARIOS, SUPPORT_FUNCTIONS } from "../data/workbench";
import { formatValue } from "../lib/insights";
import type {
  ChatMessage,
  ConversationSummary,
  ExecutionRecord,
  Product,
  RefundAction,
  ResultCard,
  ScenarioPreset
} from "../types";

const roleLabels: Record<string, string> = {
  user: "客户",
  assistant: "助手",
  system: "记录",
  tool: "工具"
};

export function DeskView(props: {
  activeScenario: ScenarioPreset;
  conversations: ConversationSummary[];
  draft: string;
  executionRecords: ExecutionRecord[];
  isSending: boolean;
  messages: ChatMessage[];
  products: Product[];
  resultCards: ResultCard[];
  selectedFunctions: Set<string>;
  selectedProducts: Set<string>;
  onDraftChange: (value: string) => void;
  onOpenConversation: (id: string) => void;
  onPrompt: (prompt: string) => void;
  onScenario: (scenario: ScenarioPreset) => void;
  onSend: (event: FormEvent<HTMLFormElement>) => void;
  onToggleFunction: (key: string) => void;
  onToggleProduct: (name: string) => void;
  onRefundAction: (refundId: string, action: RefundAction) => Promise<void>;
}) {
  const [contextTab, setContextTab] = useState<"overview" | "products" | "trace" | "results">("overview");

  return (
    <section className="desk-layout">
      <aside className="left-rail">
        <section className="surface">
          <div className="section-head">
            <div>
              <span className="eyebrow">接待场景</span>
              <h2>处理范围</h2>
            </div>
          </div>
          <div className="scenario-list">
            {SCENARIOS.map((scenario) => (
              <button
                key={scenario.id}
                className={scenario.id === props.activeScenario.id ? "scenario is-active" : "scenario"}
                onClick={() => props.onScenario(scenario)}
                type="button"
              >
                <strong>{scenario.label}</strong>
                <span>{scenario.tone}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="surface">
          <div className="section-head">
            <div>
              <span className="eyebrow">服务能力</span>
              <h2>工具权限</h2>
            </div>
            <span className="count-badge">{props.selectedFunctions.size}</span>
          </div>
          <div className="check-list">
            {SUPPORT_FUNCTIONS.map((item) => (
              <label key={item.key} className="check-card">
                <input
                  checked={props.selectedFunctions.has(item.key)}
                  onChange={() => props.onToggleFunction(item.key)}
                  type="checkbox"
                />
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
              </label>
            ))}
          </div>
        </section>

        <section className="surface compact">
          <div className="section-head">
            <div>
              <span className="eyebrow">最近会话</span>
              <h2>接待记录</h2>
            </div>
          </div>
          <div className="conversation-list">
            {props.conversations.length ? (
              props.conversations.slice(0, 6).map((item) => (
                <button key={item.id} className="conversation-row" onClick={() => props.onOpenConversation(item.id)}>
                  <strong>{item.title || "未命名会话"}</strong>
                  <span>{item.last_message || "暂无消息"}</span>
                </button>
              ))
            ) : (
              <p className="empty">暂无历史会话。</p>
            )}
          </div>
        </section>
      </aside>

      <section className="chat-column surface">
        <div className="section-head">
          <div>
            <span className="eyebrow">{props.activeScenario.label}</span>
            <h2>接待对话</h2>
            <p>{props.activeScenario.tone}</p>
          </div>
          <span className="status-badge">接入已就绪</span>
        </div>

        <div className="prompt-strip">
          {props.activeScenario.prompts.map((prompt) => (
            <button key={prompt} onClick={() => props.onPrompt(prompt)} type="button">
              {prompt}
            </button>
          ))}
        </div>

        <div className="message-list">
          {props.messages.map((message, index) => (
            <article key={`${message.role}-${index}-${message.content.slice(0, 12)}`} className={`message ${message.role}`}>
              <div className="avatar">{message.role === "assistant" ? "助" : message.role === "user" ? "客" : "记"}</div>
              <div>
                <span>{roleLabels[message.role] ?? message.role}</span>
                <p>{message.content}</p>
              </div>
            </article>
          ))}
        </div>

        <form className="composer" id="composer-form" onSubmit={props.onSend}>
          <textarea
            onChange={(event) => props.onDraftChange(event.target.value)}
            placeholder="输入客户问题，例如：我之前买的腰靠垫现在送到哪里了？"
            value={props.draft}
          />
          <div className="composer-actions">
            <span>输入完成后点击发送，Enter 保留为换行</span>
            <button className="primary-button" disabled={props.isSending} type="submit">
              {props.isSending ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
              发送消息
            </button>
          </div>
        </form>
      </section>

      <aside className="right-rail">
        <section className="surface context-panel">
          <div className="section-head">
            <div>
              <span className="eyebrow">辅助信息</span>
              <h2>工作上下文</h2>
            </div>
          </div>
          <div className="context-tabs" role="tablist" aria-label="工作上下文">
            {([
              ["overview", "概况"],
              ["products", `货架 ${props.products.length}`],
              ["trace", `工具 ${props.executionRecords.length}`],
              ["results", `结果 ${props.resultCards.length}`],
            ] as const).map(([value, label]) => (
              <button
                key={value}
                className={contextTab === value ? "context-tab is-active" : "context-tab"}
                onClick={() => setContextTab(value)}
                role="tab"
                aria-selected={contextTab === value}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
          <div className="context-content">
            {contextTab === "overview" && (
              <CustomerPanel
                executionRecords={props.executionRecords}
                messages={props.messages}
                resultCards={props.resultCards}
                selectedProducts={props.selectedProducts}
                compact
              />
            )}
            {contextTab === "products" && (
              <div className="product-mini-list">
                {props.products.length ? props.products.map((product) => (
                  <label key={product.name} className="product-mini">
                    <input
                      checked={props.selectedProducts.has(product.name)}
                      onChange={() => props.onToggleProduct(product.name)}
                      type="checkbox"
                    />
                    <span>{product.name}</span>
                  </label>
                )) : <p className="empty">商品数据暂未载入。</p>}
              </div>
            )}
            {contextTab === "trace" && (
              <TraceList records={props.executionRecords} />
            )}
            {contextTab === "results" && (
              <ResultList cards={props.resultCards} onAction={props.onRefundAction} />
            )}
          </div>
        </section>
      </aside>
    </section>
  );
}

function CustomerPanel(props: {
  executionRecords: ExecutionRecord[];
  messages: ChatMessage[];
  resultCards: ResultCard[];
  selectedProducts: Set<string>;
  compact?: boolean;
}) {
  const latestUser = [...props.messages].reverse().find((item) => item.role === "user");
  return (
    <section className={props.compact ? "context-inner" : "surface"}>
      <div className="section-head">
        <div>
          <span className="eyebrow">客户档案</span>
          <h2>本轮概况</h2>
        </div>
        <UserRound size={18} />
      </div>
      <div className="profile-grid">
        <Info label="最近诉求" value={latestUser?.content || "尚未开始"} />
        <Info label="选中商品" value={`${props.selectedProducts.size} 个`} />
        <Info label="工具动作" value={`${props.executionRecords.length} 条`} />
        <Info label="工单结果" value={`${props.resultCards.length} 条`} />
      </div>
      <div className="tabs-panel">
        <h3>工具轨迹</h3>
        {props.executionRecords.length ? (
          props.executionRecords.slice(0, 5).map((item) => (
            <article key={item.id} className="trace-item">
              <strong>{item.tool}</strong>
              <span>{item.action}</span>
              <pre>{formatValue(item.output)}</pre>
            </article>
          ))
        ) : (
          <p className="empty">暂无工具调用。</p>
        )}
      </div>
      <div className="tabs-panel">
        <h3>结果卡片</h3>
        {props.resultCards.length ? (
          props.resultCards.map((card) => (
            <article key={card.id} className="result-card">
              <strong>{card.title}</strong>
              <span>{card.type}</span>
              {card.fields.slice(0, 4).map((field) => (
                <p key={field.label}>
                  <b>{field.label}</b>
                  {field.value}
                </p>
              ))}
            </article>
          ))
        ) : (
          <p className="empty">暂无工单结果。</p>
        )}
      </div>
    </section>
  );
}

function Info(props: { label: string; value: string }) {
  return (
    <div className="info-cell">
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </div>
  );
}
