import {
  Activity,
  Archive,
  Bot,
  ClipboardCheck,
  Clock3,
  FileText,
  Gauge,
  History,
  Inbox,
  Loader2,
  MessageSquareText,
  PackageCheck,
  RotateCcw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  UserRound
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { DEFAULT_ACCOUNT_ID, FUNCTION_LABELS, SCENARIOS, SUPPORT_FUNCTIONS } from "./data/workbench";
import type {
  BotUsage,
  ChatMessage,
  ConversationSummary,
  ExecutionRecord,
  Product,
  ResultCard,
  ScenarioPreset
} from "./types";

const viewItems = [
  { id: "desk", label: "接待", icon: MessageSquareText },
  { id: "history", label: "会话", icon: History },
  { id: "products", label: "货架", icon: PackageCheck },
  { id: "quality", label: "质检", icon: ClipboardCheck },
  { id: "settings", label: "配置", icon: Settings }
] as const;

type ViewId = (typeof viewItems)[number]["id"];

const roleLabels: Record<string, string> = {
  user: "客户",
  assistant: "助手",
  system: "记录",
  tool: "工具"
};

export function App() {
  const [activeView, setActiveView] = useState<ViewId>("desk");
  const [activeScenarioId, setActiveScenarioId] = useState(SCENARIOS[0].id);
  const [accountId, setAccountId] = useState(DEFAULT_ACCOUNT_ID);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProducts, setSelectedProducts] = useState<Set<string>>(new Set());
  const [selectedFunctions, setSelectedFunctions] = useState<Set<string>>(
    new Set(SCENARIOS[0].functions)
  );
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "system",
      content: "当前接待已准备。选择场景、商品范围和服务能力后，可以开始处理客户消息。"
    }
  ]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [health, setHealth] = useState<"online" | "offline" | "checking">("checking");
  const [resultCards, setResultCards] = useState<ResultCard[]>([]);
  const [executionRecords, setExecutionRecords] = useState<ExecutionRecord[]>([]);
  const [summary, setSummary] = useState("暂无会话总结。");
  const [quality, setQuality] = useState("暂无质检记录。");
  const [faqResult, setFaqResult] = useState("暂无 FAQ 沉淀。");
  const [qualityKeywords, setQualityKeywords] = useState("夸大承诺、绝对化用语、服务态度");
  const [faqScore, setFaqScore] = useState(5);
  const [notice, setNotice] = useState<string | null>(null);

  const activeScenario = useMemo(
    () => SCENARIOS.find((item) => item.id === activeScenarioId) ?? SCENARIOS[0],
    [activeScenarioId]
  );

  const latestUserMessage = [...messages].reverse().find((item) => item.role === "user");
  const latestAssistantMessage = [...messages].reverse().find((item) => item.role === "assistant");
  const selectedProductNames = Array.from(selectedProducts);
  const selectedFunctionKeys = Array.from(selectedFunctions);

  useEffect(() => {
    refreshHealth();
    loadProducts();
    loadConversations(accountId);
  }, []);

  async function refreshHealth() {
    setHealth("checking");
    try {
      await api.health();
      setHealth("online");
    } catch {
      setHealth("offline");
    }
  }

  async function loadProducts() {
    try {
      const payload = await api.products();
      setProducts(payload.products ?? []);
      setSelectedProducts(new Set((payload.products ?? []).map((item) => item.name)));
    } catch (error) {
      showNotice(error instanceof Error ? error.message : "商品数据加载失败");
    }
  }

  async function loadConversations(nextAccountId = accountId) {
    try {
      const payload = await api.conversations(nextAccountId);
      setConversations(payload.conversations ?? []);
    } catch (error) {
      showNotice(error instanceof Error ? error.message : "历史会话加载失败");
    }
  }

  async function openConversation(id: string) {
    try {
      const payload = await api.conversation(id, accountId);
      setConversationId(payload.id);
      setMessages(
        payload.messages?.length
          ? payload.messages
          : [{ role: "system", content: "这条历史会话没有可展示的消息。" }]
      );
      setActiveView("desk");
      showNotice("历史会话已载入");
      const insights = collectInsights(payload.messages ?? []);
      setExecutionRecords(insights.executions);
      setResultCards(insights.results);
    } catch (error) {
      showNotice(error instanceof Error ? error.message : "会话载入失败");
    }
  }

  function switchScenario(scenario: ScenarioPreset) {
    setActiveScenarioId(scenario.id);
    setSelectedFunctions(new Set(scenario.functions));
  }

  function toggleFunction(key: string) {
    setSelectedFunctions((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  function toggleProduct(name: string) {
    setSelectedProducts((current) => {
      const next = new Set(current);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || isSending) {
      return;
    }

    const userMessage: ChatMessage = { role: "user", content };
    const history = messages.filter((item) => item.role !== "system");
    setMessages((current) => [...current, userMessage, { role: "assistant", content: "正在生成回复..." }]);
    setDraft("");
    setIsSending(true);

    try {
      const payload = await api.chat({
        message: content,
        accountId,
        conversationId,
        supportFunctions: selectedFunctionKeys,
        productList: selectedProductNames,
        history
      });
      const answer = payload.answer || "后端没有返回内容。";
      setConversationId(payload.conversation_id ?? conversationId);
      setMessages((current) => [
        ...current.slice(0, -1),
        {
          role: "assistant",
          content: answer,
          metadata: {
            bot_usage: payload.bot_usage,
            conversation_id: payload.conversation_id
          }
        }
      ]);
      const insights = botUsageToInsights(payload.bot_usage);
      setExecutionRecords(insights.executions);
      setResultCards(insights.results);
      await loadConversations(accountId);
    } catch (error) {
      setMessages((current) => [
        ...current.slice(0, -1),
        {
          role: "system",
          content: `请求失败：${error instanceof Error ? error.message : "未知错误"}`
        }
      ]);
    } finally {
      setIsSending(false);
    }
  }

  async function handleSummary() {
    try {
      setSummary("正在生成会话总结...");
      const payload = await api.summary(messages.filter((item) => item.role !== "system"));
      setSummary(payload.summary || "暂无可总结内容。");
    } catch (error) {
      setSummary(`生成失败：${error instanceof Error ? error.message : "未知错误"}`);
    }
  }

  async function handleQuality() {
    try {
      setQuality("正在检查最新回复...");
      const content = latestAssistantMessage?.content || messages.map((item) => item.content).join("\n");
      const payload = await api.quality(
        content,
        qualityKeywords,
        conversationId,
        accountId
      );
      const structured = payload.structured_result;
      const prefix = structured
        ? `风险等级：${structured.risk_level ?? "unknown"}，命中 ${structured.hit_count ?? 0} 条\n`
        : "";
      setQuality(`${prefix}${payload.result || "没有返回质检说明。"}`);
    } catch (error) {
      setQuality(`质检失败：${error instanceof Error ? error.message : "未知错误"}`);
    }
  }

  async function handleSaveFaq() {
    try {
      const question = latestUserMessage?.content;
      const answer = latestAssistantMessage?.content;
      if (!question || !answer) {
        setFaqResult("需要至少一轮客户问题和助手回复后才能沉淀 FAQ。");
        return;
      }
      setFaqResult("正在保存 FAQ...");
      const payload = await api.saveFaq({
        question,
        answer,
        score: faqScore,
        accountId,
        conversationId
      });
      setFaqResult(payload.message === "success" ? "FAQ 已保存到后端知识沉淀接口。" : "FAQ 已提交。");
    } catch (error) {
      setFaqResult(`保存失败：${error instanceof Error ? error.message : "未知错误"}`);
    }
  }

  function startNewConversation() {
    setConversationId(null);
    setMessages([
      {
        role: "system",
        content: "已创建新接待。你可以从快捷话术开始，也可以直接输入客户问题。"
      }
    ]);
    setExecutionRecords([]);
    setResultCards([]);
    setSummary("暂无会话总结。");
    setQuality("暂无质检记录。");
    setFaqResult("暂无 FAQ 沉淀。");
  }

  function showNotice(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(null), 2600);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">客</div>
          <div>
            <strong>客服中控台</strong>
            <span>接待，履约，知识沉淀</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="主导航">
          {viewItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={activeView === item.id ? "nav-item is-active" : "nav-item"}
                onClick={() => setActiveView(item.id)}
                type="button"
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <section className="sidebar-panel">
          <div className="panel-title">
            <span>服务状态</span>
            <button className="icon-button" onClick={refreshHealth} type="button" title="刷新状态">
              <RotateCcw size={16} />
            </button>
          </div>
          <div className={`health-pill is-${health}`}>
            <span />
            {health === "online" ? "后端在线" : health === "checking" ? "检查中" : "后端离线"}
          </div>
          <label className="field">
            <span>客户账号</span>
            <input value={accountId} onChange={(event) => setAccountId(event.target.value)} />
          </label>
          <button className="secondary-button" onClick={() => loadConversations(accountId)} type="button">
            刷新会话
          </button>
        </section>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <span className="eyebrow">当前工作区</span>
            <h1>{viewItems.find((item) => item.id === activeView)?.label ?? "接待"}</h1>
            <p>把客户消息、业务工具、商品范围和质检沉淀放在一条操作链路里。</p>
          </div>
          <div className="topbar-actions">
            <button className="secondary-button" onClick={startNewConversation} type="button">
              <Inbox size={16} />
              新接待
            </button>
            <button className="primary-button" form="composer-form" disabled={isSending} type="submit">
              {isSending ? <Loader2 className="spin" size={16} /> : <Send size={16} />}
              发送
            </button>
          </div>
        </header>

        <section className="metric-grid">
          <Metric icon={MessageSquareText} label="消息数" value={String(messages.length)} />
          <Metric icon={ShieldCheck} label="启用工具" value={`${selectedFunctions.size} 项`} />
          <Metric icon={PackageCheck} label="货架范围" value={`${selectedProducts.size} 个`} />
          <Metric icon={Clock3} label="当前会话" value={conversationId ? "已归档" : "未归档"} />
        </section>

        {activeView === "desk" && (
          <DeskView
            activeScenario={activeScenario}
            conversations={conversations}
            draft={draft}
            executionRecords={executionRecords}
            isSending={isSending}
            messages={messages}
            products={products}
            resultCards={resultCards}
            selectedFunctions={selectedFunctions}
            selectedProducts={selectedProducts}
            onDraftChange={setDraft}
            onOpenConversation={openConversation}
            onPrompt={(prompt) => setDraft(prompt)}
            onScenario={switchScenario}
            onSend={handleSend}
            onToggleFunction={toggleFunction}
            onToggleProduct={toggleProduct}
          />
        )}

        {activeView === "history" && (
          <HistoryView
            accountId={accountId}
            conversations={conversations}
            onOpenConversation={openConversation}
            onRefresh={() => loadConversations(accountId)}
          />
        )}

        {activeView === "products" && (
          <ProductsView
            products={products}
            selectedProducts={selectedProducts}
            selectedFunctions={selectedFunctions}
            onToggleFunction={toggleFunction}
            onToggleProduct={toggleProduct}
          />
        )}

        {activeView === "quality" && (
          <QualityView
            faqResult={faqResult}
            faqScore={faqScore}
            quality={quality}
            qualityKeywords={qualityKeywords}
            summary={summary}
            onFaqScore={setFaqScore}
            onKeywords={setQualityKeywords}
            onQuality={handleQuality}
            onSaveFaq={handleSaveFaq}
            onSummary={handleSummary}
          />
        )}

        {activeView === "settings" && <SettingsView />}
      </main>

      {notice && <div className="toast">{notice}</div>}
    </div>
  );
}

function DeskView(props: {
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
}) {
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
          </div>
          <span className="status-badge">本地模拟，API 已接入</span>
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
        <CustomerPanel
          executionRecords={props.executionRecords}
          messages={props.messages}
          resultCards={props.resultCards}
          selectedProducts={props.selectedProducts}
        />
        <section className="surface compact">
          <div className="section-head">
            <div>
              <span className="eyebrow">商品范围</span>
              <h2>本轮货架</h2>
            </div>
            <span className="count-badge">{props.selectedProducts.size}</span>
          </div>
          <div className="product-mini-list">
            {props.products.slice(0, 8).map((product) => (
              <label key={product.name} className="product-mini">
                <input
                  checked={props.selectedProducts.has(product.name)}
                  onChange={() => props.onToggleProduct(product.name)}
                  type="checkbox"
                />
                <span>{product.name}</span>
              </label>
            ))}
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
}) {
  const latestUser = [...props.messages].reverse().find((item) => item.role === "user");
  return (
    <section className="surface">
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

function HistoryView(props: {
  accountId: string;
  conversations: ConversationSummary[];
  onOpenConversation: (id: string) => void;
  onRefresh: () => void;
}) {
  return (
    <section className="page-grid single">
      <div className="surface">
        <div className="section-head">
          <div>
            <span className="eyebrow">会话库</span>
            <h2>历史会话</h2>
          </div>
          <button className="secondary-button" onClick={props.onRefresh} type="button">
            <RotateCcw size={16} />
            刷新
          </button>
        </div>
        <div className="table-list">
          {props.conversations.length ? (
            props.conversations.map((item) => (
              <button key={item.id} className="table-row" onClick={() => props.onOpenConversation(item.id)}>
                <span>{item.title || "未命名会话"}</span>
                <span>{item.last_message || "暂无消息"}</span>
                <span>{item.account_id || props.accountId}</span>
                <span>{formatTime(item.updated_at)}</span>
              </button>
            ))
          ) : (
            <p className="empty">这个账号还没有历史会话。</p>
          )}
        </div>
      </div>
    </section>
  );
}

function ProductsView(props: {
  products: Product[];
  selectedProducts: Set<string>;
  selectedFunctions: Set<string>;
  onToggleFunction: (key: string) => void;
  onToggleProduct: (name: string) => void;
}) {
  return (
    <section className="page-grid">
      <div className="surface">
        <div className="section-head">
          <div>
            <span className="eyebrow">商品范围</span>
            <h2>商品货架</h2>
          </div>
          <span className="count-badge">{props.products.length}</span>
        </div>
        <div className="product-grid">
          {props.products.map((product) => (
            <label key={product.name} className="product-card">
              <input
                checked={props.selectedProducts.has(product.name)}
                onChange={() => props.onToggleProduct(product.name)}
                type="checkbox"
              />
              <div className="product-thumb">{product.name.slice(0, 1)}</div>
              <div>
                <strong>{product.name}</strong>
                <p>{product.description}</p>
              </div>
            </label>
          ))}
        </div>
      </div>
      <div className="surface">
        <div className="section-head">
          <div>
            <span className="eyebrow">知识范围</span>
            <h2>能力开关</h2>
          </div>
        </div>
        <div className="check-list spacious">
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
      </div>
    </section>
  );
}

function QualityView(props: {
  faqResult: string;
  faqScore: number;
  quality: string;
  qualityKeywords: string;
  summary: string;
  onFaqScore: (value: number) => void;
  onKeywords: (value: string) => void;
  onQuality: () => void;
  onSaveFaq: () => void;
  onSummary: () => void;
}) {
  return (
    <section className="page-grid">
      <div className="surface ops">
        <div className="section-head">
          <div>
            <span className="eyebrow">复盘</span>
            <h2>会话总结</h2>
          </div>
          <button className="secondary-button" onClick={props.onSummary} type="button">
            <FileText size={16} />
            生成
          </button>
        </div>
        <pre className="output-box">{props.summary}</pre>
      </div>

      <div className="surface ops">
        <div className="section-head">
          <div>
            <span className="eyebrow">质检</span>
            <h2>回复质检</h2>
          </div>
          <button className="secondary-button" onClick={props.onQuality} type="button">
            <Gauge size={16} />
            检查
          </button>
        </div>
        <label className="field">
          <span>质检关键词</span>
          <input value={props.qualityKeywords} onChange={(event) => props.onKeywords(event.target.value)} />
        </label>
        <pre className="output-box">{props.quality}</pre>
      </div>

      <div className="surface ops wide">
        <div className="section-head">
          <div>
            <span className="eyebrow">知识沉淀</span>
            <h2>FAQ 沉淀</h2>
          </div>
          <button className="primary-button" onClick={props.onSaveFaq} type="button">
            <Archive size={16} />
            保存
          </button>
        </div>
        <label className="field">
          <span>满意度评分：{props.faqScore}</span>
          <input
            max={5}
            min={1}
            onChange={(event) => props.onFaqScore(Number(event.target.value))}
            type="range"
            value={props.faqScore}
          />
        </label>
        <pre className="output-box">{props.faqResult}</pre>
      </div>
    </section>
  );
}

function SettingsView() {
  return (
    <section className="page-grid single">
      <div className="surface">
        <div className="section-head">
          <div>
            <span className="eyebrow">运行配置</span>
            <h2>接入配置</h2>
          </div>
          <Settings size={18} />
        </div>
        <div className="settings-grid">
          <ConfigCard
            icon={Bot}
            title="大模型"
            value="DeepSeek / 智谱 / 火山引擎"
            note="通过后端 .env.local 的 LLM_PROVIDER 与 API Key 切换。"
          />
          <ConfigCard
            icon={Search}
            title="知识库"
            value="Dify Dataset"
            note="商品知识和 FAQ 分别使用 DIFY_DATASET_ID 与 DIFY_FAQ_DATASET_ID。"
          />
          <ConfigCard
            icon={Activity}
            title="业务系统"
            value="本地模拟 / HTTP 适配器"
            note="订单、物流、退款走 BUSINESS_DATA_PROVIDER。"
          />
          <ConfigCard
            icon={ShieldCheck}
            title="API 鉴权"
            value="X-API-Key / Bearer"
            note="配置 API_KEYS 后，前端部署时需要接入登录态或网关。"
          />
        </div>
      </div>
    </section>
  );
}

function Metric(props: { icon: typeof MessageSquareText; label: string; value: string }) {
  const Icon = props.icon;
  return (
    <article className="metric-card">
      <Icon size={18} />
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </article>
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

function ConfigCard(props: {
  icon: typeof Bot;
  note: string;
  title: string;
  value: string;
}) {
  const Icon = props.icon;
  return (
    <article className="config-card">
      <Icon size={20} />
      <div>
        <strong>{props.title}</strong>
        <span>{props.value}</span>
        <p>{props.note}</p>
      </div>
    </article>
  );
}

function botUsageToInsights(botUsage?: BotUsage | null): {
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

function collectInsights(messages: ChatMessage[]) {
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

function normalizeResult(toolName: string, output: unknown, id: string): ResultCard {
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

function formatValue(value: unknown): string {
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

function formatTime(value?: string) {
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
