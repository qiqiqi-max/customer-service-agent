import { Check, Loader2, MessageSquareText, Send } from "lucide-react";
import { FormEvent, KeyboardEvent, useEffect, useRef } from "react";
import { ContextPanel } from "../components/ContextPanel";
import { Popover } from "../components/Popover";
import { SCENARIOS, SUPPORT_FUNCTIONS } from "../data/workbench";
import type {
  ChatMessage,
  ConversationSummary,
  ExecutionRecord,
  Product,
  RefundAction,
  ResultCard,
  ScenarioPreset
} from "../types";

export function DeskView(props: {
  activeScenario: ScenarioPreset;
  contextOpen: boolean;
  conversationId: string | null;
  conversations: ConversationSummary[];
  draft: string;
  executionRecords: ExecutionRecord[];
  isSending: boolean;
  messages: ChatMessage[];
  products: Product[];
  resultCards: ResultCard[];
  selectedFunctions: Set<string>;
  selectedProducts: Set<string>;
  onCloseContext: () => void;
  onDraftChange: (value: string) => void;
  onOpenConversation: (id: string) => void;
  onPrompt: (prompt: string) => void;
  onScenario: (scenario: ScenarioPreset) => void;
  onSend: (event: FormEvent<HTMLFormElement>) => void;
  onToggleFunction: (key: string) => void;
  onToggleProduct: (name: string) => void;
  onRefundAction: (refundId: string, action: RefundAction) => Promise<void>;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const hasConversation = props.messages.some((item) => item.role === "user" || item.role === "assistant");

  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [props.messages, props.isSending]);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  }

  return (
    <div className="desk">
      <section className="chat panel">
        <div className="chat-toolbar">
          <Popover label="场景" value={props.activeScenario.label}>
            {(close) => SCENARIOS.map((scenario) => {
              const selected = scenario.id === props.activeScenario.id;
              return (
                <button
                  key={scenario.id}
                  className={selected ? "option is-selected" : "option"}
                  onClick={() => {
                    props.onScenario(scenario);
                    close();
                  }}
                  type="button"
                >
                  {selected ? <Check size={16} /> : <span className="option-check" />}
                  <span>
                    <strong>{scenario.label}</strong>
                    <small>{scenario.tone}</small>
                  </span>
                </button>
              );
            })}
          </Popover>

          <Popover label="工具" value={`${props.selectedFunctions.size} 项`}>
            <div className="popover-head">切换场景会重置为该场景的默认工具</div>
            {SUPPORT_FUNCTIONS.map((item) => (
              <label key={item.key} className={props.selectedFunctions.has(item.key) ? "option is-selected" : "option"}>
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
          </Popover>

          <Popover label="货架" value={`${props.selectedProducts.size}/${props.products.length}`}>
            {props.products.length ? props.products.map((product) => (
              <label key={product.name} className={props.selectedProducts.has(product.name) ? "option is-selected" : "option"}>
                <input
                  checked={props.selectedProducts.has(product.name)}
                  onChange={() => props.onToggleProduct(product.name)}
                  type="checkbox"
                />
                <span>
                  <strong>{product.name}</strong>
                </span>
              </label>
            )) : <p className="empty">商品数据暂未载入。</p>}
          </Popover>

          <span className="toolbar-spacer" />
          <span className={props.conversationId ? "archive-state is-saved" : "archive-state"}>
            {props.conversationId ? "会话已归档" : "新会话，发送后归档"}
          </span>
        </div>

        <div className="message-list" ref={listRef} aria-live="polite">
          {hasConversation ? (
            props.messages.map((message, index) => (
              <MessageItem key={`${message.role}-${index}`} message={message} />
            ))
          ) : (
            <div className="welcome">
              <div className="welcome-icon"><MessageSquareText size={22} /></div>
              <h2>{props.activeScenario.label}</h2>
              <p>{props.activeScenario.tone}选一条示例问题开始，或直接输入客户消息。</p>
              {props.messages.map((message, index) => (
                <MessageItem key={`${message.role}-${index}`} message={message} />
              ))}
              <div className="prompt-list">
                {props.activeScenario.prompts.map((prompt) => (
                  <button key={prompt} className="prompt-card" onClick={() => props.onPrompt(prompt)} type="button">
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}
          {props.isSending && (
            <div className="msg is-assistant">
              <span className="msg-role">助手</span>
              <div className="bubble" aria-label="正在生成回复">
                <span className="typing"><span /><span /><span /></span>
              </div>
            </div>
          )}
        </div>

        <form className="composer" onSubmit={props.onSend} ref={formRef}>
          {hasConversation && (
            <div className="prompt-chips">
              {props.activeScenario.prompts.map((prompt) => (
                <button key={prompt} className="prompt-chip" onClick={() => props.onPrompt(prompt)} title={prompt} type="button">
                  {prompt}
                </button>
              ))}
            </div>
          )}
          <div className="composer-box">
            <textarea
              aria-label="客户消息"
              onChange={(event) => props.onDraftChange(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入客户问题，例如：我之前买的腰靠垫现在送到哪里了？"
              rows={2}
              value={props.draft}
            />
            <div className="composer-foot">
              <span>Ctrl + Enter 发送，Enter 换行</span>
              <button className="btn primary" disabled={props.isSending || !props.draft.trim()} type="submit">
                {props.isSending ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
                发送
              </button>
            </div>
          </div>
        </form>
      </section>

      <ContextPanel
        activeScenario={props.activeScenario}
        conversationId={props.conversationId}
        conversations={props.conversations}
        executionRecords={props.executionRecords}
        messages={props.messages}
        open={props.contextOpen}
        resultCards={props.resultCards}
        selectedFunctionCount={props.selectedFunctions.size}
        selectedProductCount={props.selectedProducts.size}
        onClose={props.onCloseContext}
        onOpenConversation={props.onOpenConversation}
        onRefundAction={props.onRefundAction}
      />
    </div>
  );
}

function MessageItem({ message }: { message: ChatMessage }) {
  if (message.role === "user" || message.role === "assistant") {
    return (
      <article className={`msg is-${message.role}`}>
        <span className="msg-role">{message.role === "user" ? "客户" : "助手"}</span>
        <div className="bubble">{message.content}</div>
      </article>
    );
  }
  return <p className="msg-notice">{message.content}</p>;
}
