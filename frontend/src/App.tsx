import { ClipboardCheck, History, MessageSquareText, PackageCheck, PanelRight, Plus, RotateCcw, Settings } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { DEFAULT_ACCOUNT_ID, SCENARIOS } from "./data/workbench";
import { botUsageToInsights, collectInsights, normalizeResult } from "./lib/insights";
import { useMediaQuery } from "./lib/useMediaQuery";
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
  { id: "desk", label: "接待", title: "客户接待", subtitle: "处理客户消息，查看工具调用和工单结果", icon: MessageSquareText },
  { id: "history", label: "会话", title: "历史会话", subtitle: "按账号查看已归档的接待记录", icon: History },
  { id: "products", label: "货架", title: "商品货架", subtitle: "选择助手可以介绍和推荐的商品与能力", icon: PackageCheck },
  { id: "quality", label: "质检", title: "质检复盘", subtitle: "会话总结、回复质检与 FAQ 沉淀", icon: ClipboardCheck },
  { id: "settings", label: "配置", title: "接入配置", subtitle: "访问密钥与后端接入说明", icon: Settings }
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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
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
  const isWide = useMediaQuery("(min-width: 1200px)");
  const [contextOpen, setContextOpen] = useState(isWide);

  const activeScenario = useMemo(
    () => SCENARIOS.find((item) => item.id === activeScenarioId) ?? SCENARIOS[0],
    [activeScenarioId]
  );
  const activeViewItem = useMemo(
    () => viewItems.find((item) => item.id === activeView) ?? viewItems[0],
    [activeView]
  );
  const healthLabel = health === "online" ? "后端在线" : health === "checking" ? "检查中" : "后端离线";

  const latestUserMessage = [...messages].reverse().find((item) => item.role === "user");
  const latestAssistantMessage = [...messages].reverse().find((item) => item.role === "assistant");
  const selectedProductNames = Array.from(selectedProducts);
  const selectedFunctionKeys = Array.from(selectedFunctions);

  useEffect(() => {
    refreshHealth();
    loadProducts();
    loadConversations(accountId, 1, conversationPageSize);
  }, []);

  // The context panel is docked on wide screens and a drawer on narrow ones.
  useEffect(() => {
    setContextOpen(isWide);
  }, [isWide]);

  useEffect(() => {
    if (!contextOpen || isWide) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setContextOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [contextOpen, isWide]);

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
    setMessages((current) => [...current, userMessage]);
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
        ...current,
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
        ...current,
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
    setMessages([]);
    setDraft("");
    setActiveView("desk");
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
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">客</div>
          <div>
            <strong>客服中控台</strong>
            <small>接待 · 履约 · 知识沉淀</small>
          </div>
        </div>

        <nav className="nav" aria-label="主导航">
          {viewItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                aria-current={activeView === item.id ? "page" : undefined}
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

        <div className="sidebar-foot">
          <span className={`status-dot is-${health}`}>{healthLabel}</span>
          <button className="icon-btn" onClick={refreshHealth} title="刷新服务状态" type="button">
            <RotateCcw size={15} />
          </button>
        </div>
      </aside>

      <main className="workspace">
        <header className="page-header">
          <div className="page-title">
            <h1>{activeViewItem.title}</h1>
            <p>{activeViewItem.subtitle}</p>
          </div>
          <div className="page-actions">
            <label className="account-field" title="客户账号">
              <span>账号</span>
              <input
                aria-label="客户账号"
                onChange={(event) => setAccountId(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void loadConversations(accountId, 1, conversationPageSize);
                }}
                value={accountId}
              />
              <button
                className="icon-btn"
                onClick={() => loadConversations(accountId, 1, conversationPageSize)}
                title="按账号刷新会话"
                type="button"
              >
                <RotateCcw size={14} />
              </button>
            </label>
            <button className="btn" onClick={startNewConversation} title="新接待" type="button">
              <Plus size={16} />
              <span className="btn-text">新接待</span>
            </button>
            {activeView === "desk" && (
              <button
                aria-pressed={contextOpen}
                className={contextOpen ? "btn is-active" : "btn"}
                onClick={() => setContextOpen((current) => !current)}
                title={contextOpen ? "收起上下文面板" : "展开上下文面板"}
                type="button"
              >
                <PanelRight size={16} />
                <span className="btn-text">上下文</span>
                {resultCards.length > 0 && <span className="badge accent">{resultCards.length}</span>}
              </button>
            )}
          </div>
        </header>

        <div className={activeView === "desk" ? "page-body is-desk" : "page-body"}>
          {activeView === "desk" && (
            <DeskView
              activeScenario={activeScenario}
              contextOpen={contextOpen}
              conversationId={conversationId}
              conversations={conversations}
              draft={draft}
              executionRecords={executionRecords}
              isSending={isSending}
              messages={messages}
              products={products}
              resultCards={resultCards}
              selectedFunctions={selectedFunctions}
              selectedProducts={selectedProducts}
              onCloseContext={() => setContextOpen(false)}
              onDraftChange={setDraft}
              onOpenConversation={(id) => {
                if (!isWide) setContextOpen(false);
                void openConversation(id);
              }}
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
              conversationId={conversationId}
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
        </div>
      </main>

      {notice && <div className="toast" role="status">{notice}</div>}
    </div>
  );
}
