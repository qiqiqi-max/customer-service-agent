import { Inbox, Loader2, MessageSquareText, History, PackageCheck, ClipboardCheck, RotateCcw, Send, Settings } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { DEFAULT_ACCOUNT_ID, SCENARIOS } from "./data/workbench";
import { botUsageToInsights, collectInsights, normalizeResult } from "./lib/insights";
import type {
  ChatMessage,
  ConversationSummary,
  ExecutionRecord,
  FAQCandidateRecord,
  QualityReviewRecord,
  Product,
  RefundAction,
  ResultCard,
  RefundRecord,
  ScenarioPreset
} from "./types";
import { DeskView } from "./views/DeskView";
import { HistoryView } from "./views/HistoryView";
import { ProductsView } from "./views/ProductsView";
import { QualityView } from "./views/QualityView";
import { SettingsView } from "./views/SettingsView";

const viewItems = [
  { id: "desk", label: "接待", icon: MessageSquareText },
  { id: "history", label: "会话", icon: History },
  { id: "products", label: "货架", icon: PackageCheck },
  { id: "quality", label: "质检", icon: ClipboardCheck },
  { id: "settings", label: "配置", icon: Settings }
] as const;

type ViewId = (typeof viewItems)[number]["id"];

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
  const [conversationPage, setConversationPage] = useState(1);
  const [conversationPageSize, setConversationPageSize] = useState(20);
  const [conversationTotal, setConversationTotal] = useState(0);
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
  const [qualityReviews, setQualityReviews] = useState<QualityReviewRecord[]>([]);
  const [faqCandidates, setFaqCandidates] = useState<FAQCandidateRecord[]>([]);

  const activeScenario = useMemo(
    () => SCENARIOS.find((item) => item.id === activeScenarioId) ?? SCENARIOS[0],
    [activeScenarioId]
  );
  const activeViewItem = useMemo(
    () => viewItems.find((item) => item.id === activeView) ?? viewItems[0],
    [activeView]
  );
  const workspaceStats = [
    { label: "场景", value: activeScenario.label },
    { label: "工具", value: `${selectedFunctions.size} 项` },
    { label: "货架", value: `${selectedProducts.size} 个` },
    { label: "会话", value: conversationId ? "已归档" : "未归档" }
  ];

  const latestUserMessage = [...messages].reverse().find((item) => item.role === "user");
  const latestAssistantMessage = [...messages].reverse().find((item) => item.role === "assistant");
  const selectedProductNames = Array.from(selectedProducts);
  const selectedFunctionKeys = Array.from(selectedFunctions);

  useEffect(() => {
    refreshHealth();
    loadProducts();
    loadConversations(accountId, 1, conversationPageSize);
  }, []);

  useEffect(() => {
    if (activeView === "quality") void loadQualityHistory();
  }, [activeView, accountId, conversationId]);

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

  async function loadConversations(nextAccountId = accountId, page = conversationPage, pageSize = conversationPageSize) {
    try {
      const payload = await api.conversations(nextAccountId, pageSize, (page - 1) * pageSize);
      setConversations(payload.conversations ?? []);
      setConversationPage(page);
      setConversationTotal(payload.total ?? 0);
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
      const toolPayload = await api.toolCalls(id, accountId);
      setExecutionRecords((toolPayload.tool_calls ?? []).map((item, index) => ({
        id: String(item.id ?? index),
        action: "历史工具调用",
        tool: item.tool_name ?? "未命名工具",
        input: item.input_json,
        output: item.output_json
      })));
    } catch (error) {
      showNotice(error instanceof Error ? error.message : "会话载入失败");
    }
  }

  async function loadQualityHistory() {
    try {
      const [reviews, candidates] = await Promise.all([
        api.qualityReviews(accountId, conversationId),
        api.faqCandidates(accountId)
      ]);
      setQualityReviews(reviews.reviews ?? []);
      setFaqCandidates(candidates.candidates ?? []);
    } catch (error) {
      showNotice(error instanceof Error ? error.message : "复盘记录加载失败");
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
      const summaryMessages = messages.filter(
        (item) => item.role === "user" || item.role === "assistant"
      );
      if (
        !summaryMessages.some((item) => item.role === "user") ||
        !summaryMessages.some((item) => item.role === "assistant")
      ) {
        setSummary("请先完成一轮客户提问和客服回复，再生成会话总结。");
        return;
      }
      setSummary("正在生成会话总结...");
      const payload = await api.summary(summaryMessages);
      setSummary(payload.summary || "暂无可总结内容。");
    } catch (error) {
      setSummary(`生成失败：${error instanceof Error ? error.message : "未知错误"}`);
    }
  }

  async function handleQuality() {
    try {
      setQuality("正在检查当前会话的完整对话...");
      const content = messages
        .filter((item) => item.role === "user" || item.role === "assistant")
        .map((item) => `${item.role}: ${item.content}`)
        .join("\n");
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

  async function handleRefundAction(
    refundId: string,
    action: RefundAction
  ) {
    try {
      const payload = await api.refundAction(refundId, action, accountId);
      setResultCards((current) => current.map((card) => {
        const raw = card.raw && typeof card.raw === "object" ? card.raw as RefundRecord : null;
        const cardRefundId = raw?.refund_id || raw?.id;
        return cardRefundId === refundId
          ? normalizeResult("order_refund", payload, card.id)
          : card;
      }));
      showNotice(payload.message || "退款状态已更新");
    } catch (error) {
      showNotice(error instanceof Error ? error.message : "退款操作失败");
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

  function handleCredentialsChange(message: string) {
    showNotice(message);
    void loadProducts();
    void loadConversations(accountId, 1, conversationPageSize);
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
          <div className="topbar-copy">
            <span className="eyebrow">当前工作区</span>
            <h1>{activeViewItem.label}</h1>
            <p>把客户消息、工具结果、商品范围和质检复盘放在同一个操作面里。</p>
            <div className="chip-row" aria-label="工作区概览">
              <span className={`inline-status is-${health}`}>
                {health === "online" ? "后端在线" : health === "checking" ? "检查中" : "后端离线"}
              </span>
              {workspaceStats.map((item) => (
                <span key={item.label} className="workspace-chip">
                  <em>{item.label}</em>
                  <strong>{item.value}</strong>
                </span>
              ))}
            </div>
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
            onRefundAction={handleRefundAction}
          />
        )}

        {activeView === "history" && (
          <HistoryView
            accountId={accountId}
            conversations={conversations}
            onOpenConversation={openConversation}
            onRefresh={() => loadConversations(accountId, conversationPage, conversationPageSize)}
            page={conversationPage}
            pageSize={conversationPageSize}
            total={conversationTotal}
            onPage={(page) => loadConversations(accountId, page, conversationPageSize)}
            onPageSize={(pageSize) => loadConversations(accountId, 1, pageSize)}
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
            qualityReviews={qualityReviews}
            faqCandidates={faqCandidates}
          />
        )}

        {activeView === "settings" && <SettingsView onCredentialsChange={handleCredentialsChange} />}
      </main>

      {notice && <div className="toast">{notice}</div>}
    </div>
  );
}
