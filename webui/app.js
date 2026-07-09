const FUNCTION_OPTIONS = [
  {
    key: "product_description",
    label: "商品介绍",
    description: "介绍商品卖点、规格与适用场景，帮助用户快速建立购买认知。",
  },
  {
    key: "product_recommend",
    label: "导购推荐",
    description: "根据预算、用途和偏好给出推荐，并突出差异化卖点。",
  },
  {
    key: "order_check",
    label: "订单查询",
    description: "查询账户下的历史订单、订单编号、商品信息与当前状态。",
  },
  {
    key: "package_track",
    label: "物流跟踪",
    description: "结合订单信息查看包裹轨迹、配送节点和履约进度。",
  },
  {
    key: "order_refund",
    label: "退款退货",
    description: "发起售后处理，核对退款资格与退货进度。",
  },
];

const SCENARIO_PRESETS = [
  {
    id: "sales",
    label: "售前导购",
    functions: ["product_description", "product_recommend"],
    prompts: [
      "我想买一款支持无线充的车载支架，预算在 150 元以内，适合长途通勤的有哪些？",
      "推荐两款适合夏季通勤、颜值高一点的车内收纳产品。",
      "车载香薰和除味包有什么区别，哪种更适合新车？",
    ],
  },
  {
    id: "order",
    label: "订单查询",
    functions: ["order_check"],
    prompts: [
      "帮我查一下这个账号之前买过哪些商品。",
      "我想看看账号下所有订单的状态。",
      "帮我查一下腰靠垫这款商品的订单情况。",
    ],
  },
  {
    id: "logistics",
    label: "物流咨询",
    functions: ["order_check", "package_track"],
    prompts: [
      "我之前买的腰靠垫现在送到哪里了？",
      "帮我查一下最近一笔订单的物流进度。",
      "订单还没发货吗？我想知道现在是什么状态。",
    ],
  },
  {
    id: "refund",
    label: "售后退款",
    functions: ["order_check", "order_refund"],
    prompts: [
      "我收到的商品和预期不太一样，想了解一下退货退款流程。",
      "帮我看看这笔订单现在还能不能申请退款。",
      "这个商品我不想要了，想直接发起退款。",
    ],
  },
];

const ACTION_LABELS = {
  product_description: "商品介绍",
  product_recommend: "导购推荐",
  order_check: "订单查询",
  package_track: "物流跟踪",
  pack_track: "物流跟踪",
  order_refund: "退款退货",
  dify_retrieval: "Dify 知识检索",
  retrieval: "知识检索",
  retrieval_knowledge: "知识检索",
  knowledge: "知识检索",
};

const DEFAULT_OUTPUTS = {
  summary: "暂无会话总结。",
  nextQuestion: "暂无追问建议。",
  quality: "暂无质检记录。",
  faq: "暂无 FAQ 沉淀。",
  execution: "暂无处理轨迹。",
  results: "暂无工单结果。",
};

const state = {
  products: [],
  conversations: [],
  messages: [],
  executionRecords: [],
  resultCards: [],
  activeScenario: "sales",
  conversationId: null,
  selectedProducts: new Set(),
  selectedFunctions: new Set(FUNCTION_OPTIONS.map((item) => item.key)),
};

const refs = {
  healthStatus: document.getElementById("health-status"),
  messageCount: document.getElementById("message-count"),
  activeCapabilityCount: document.getElementById("active-capability-count"),
  capabilityPill: document.getElementById("capability-pill"),
  productPill: document.getElementById("product-pill"),
  selectedProductCount: document.getElementById("selected-product-count"),
  modeLabel: document.getElementById("mode-label"),
  deskAccount: document.getElementById("desk-account"),
  deskScenario: document.getElementById("desk-scenario"),
  deskCapabilities: document.getElementById("desk-capabilities"),
  deskLatestAction: document.getElementById("desk-latest-action"),
  resultPill: document.getElementById("result-pill"),
  resultCards: document.getElementById("result-cards"),
  contextAccount: document.getElementById("context-account"),
  contextConversation: document.getElementById("context-conversation"),
  contextIntent: document.getElementById("context-intent"),
  contextStatus: document.getElementById("context-status"),
  contextProduct: document.getElementById("context-product"),
  contextKnowledge: document.getElementById("context-knowledge"),
  executionPill: document.getElementById("execution-pill"),
  latestActionName: document.getElementById("latest-action-name"),
  toolCallCount: document.getElementById("tool-call-count"),
  executionTimeline: document.getElementById("execution-timeline"),
  accountId: document.getElementById("account-id"),
  streamMode: document.getElementById("stream-mode"),
  productGrid: document.getElementById("product-grid"),
  conversationPill: document.getElementById("conversation-pill"),
  conversationList: document.getElementById("conversation-list"),
  refreshConversations: document.getElementById("refresh-conversations"),
  newConversation: document.getElementById("new-conversation"),
  functionGrid: document.getElementById("function-grid"),
  scenarioChips: document.getElementById("scenario-chips"),
  quickPrompts: document.getElementById("quick-prompts"),
  chatThread: document.getElementById("chat-thread"),
  composerForm: document.getElementById("composer-form"),
  composerInput: document.getElementById("composer-input"),
  composerSubmit: document.getElementById("composer-submit"),
  clearChat: document.getElementById("clear-chat"),
  summaryBtn: document.getElementById("summary-btn"),
  nextQuestionBtn: document.getElementById("next-question-btn"),
  qualityBtn: document.getElementById("quality-btn"),
  saveFaqBtn: document.getElementById("save-faq-btn"),
  qualityKeywords: document.getElementById("quality-keywords"),
  summaryOutput: document.getElementById("summary-output"),
  nextQuestionOutput: document.getElementById("next-question-output"),
  qualityOutput: document.getElementById("quality-output"),
  faqOutput: document.getElementById("faq-output"),
  faqScore: document.getElementById("faq-score"),
  faqScoreValue: document.getElementById("faq-score-value"),
  tabButtons: Array.from(document.querySelectorAll(".tab-button")),
  tabPanels: Array.from(document.querySelectorAll(".tab-panel")),
  messageTemplate: document.getElementById("message-template"),
  executionTemplate: document.getElementById("execution-template"),
  resultTemplate: document.getElementById("result-template"),
};

document.addEventListener("DOMContentLoaded", () => {
  renderFunctionOptions();
  renderScenarioChips();
  renderQuickPrompts();
  bindEvents();
  seedWelcomeMessage();
  resetOutputs();
  renderExecutionTimeline();
  renderResultCards();
  renderCustomerContext();
  syncOverviewStats();
  refreshHealth();
  loadProducts();
  loadConversations();
});

function bindEvents() {
  refs.composerForm.addEventListener("submit", handleSendMessage);
  refs.clearChat.addEventListener("click", clearConversation);
  refs.newConversation.addEventListener("click", clearConversation);
  refs.refreshConversations.addEventListener("click", () => loadConversations());
  refs.summaryBtn.addEventListener("click", handleSummary);
  refs.nextQuestionBtn.addEventListener("click", handleNextQuestion);
  refs.qualityBtn.addEventListener("click", handleQualityInspection);
  refs.saveFaqBtn.addEventListener("click", handleSaveFaq);
  refs.streamMode.addEventListener("change", syncOverviewStats);
  refs.accountId.addEventListener("input", () => {
    renderCustomerContext();
    syncOverviewStats();
  });
  refs.faqScore.addEventListener("input", () => {
    refs.faqScoreValue.textContent = refs.faqScore.value;
  });
  refs.tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      switchTab(button.dataset.tab);
    });
  });
}

function switchTab(tabName) {
  refs.tabButtons.forEach((button) => {
    const isActive = button.dataset.tab === tabName;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
  refs.tabPanels.forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.panel === tabName);
  });
}

function seedWelcomeMessage() {
  addMessage(
    "system",
    "当前接待已准备。选择场景和商品范围后，可以直接处理顾客消息。"
  );
}

function resetOutputs() {
  updateOutput(refs.summaryOutput, DEFAULT_OUTPUTS.summary, false);
  updateOutput(refs.nextQuestionOutput, DEFAULT_OUTPUTS.nextQuestion, false);
  updateOutput(refs.qualityOutput, DEFAULT_OUTPUTS.quality, false);
  updateOutput(refs.faqOutput, DEFAULT_OUTPUTS.faq, false);
}

function renderFunctionOptions() {
  refs.functionGrid.innerHTML = "";
  FUNCTION_OPTIONS.forEach((item) => {
    const wrapper = document.createElement("label");
    wrapper.className = "capability-card";
    wrapper.innerHTML = `
      <input type="checkbox" ${state.selectedFunctions.has(item.key) ? "checked" : ""} />
      <div>
        <strong>${escapeHtml(item.label)}</strong>
        <p>${escapeHtml(item.description)}</p>
      </div>
    `;
    const checkbox = wrapper.querySelector("input");
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        state.selectedFunctions.add(item.key);
      } else {
        state.selectedFunctions.delete(item.key);
      }
      syncOverviewStats();
    });
    refs.functionGrid.appendChild(wrapper);
  });
  syncOverviewStats();
}

function renderQuickPrompts() {
  refs.quickPrompts.innerHTML = "";
  getActiveScenario().prompts.forEach((prompt) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quick-prompt";
    button.textContent = prompt;
    button.addEventListener("click", () => {
      refs.composerInput.value = prompt;
      refs.composerInput.focus();
    });
    refs.quickPrompts.appendChild(button);
  });
}

function renderScenarioChips() {
  refs.scenarioChips.innerHTML = "";
  SCENARIO_PRESETS.forEach((scenario) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `scenario-chip${state.activeScenario === scenario.id ? " is-active" : ""}`;
    button.textContent = scenario.label;
    button.addEventListener("click", () => {
      state.activeScenario = scenario.id;
      state.selectedFunctions = new Set(scenario.functions);
      renderFunctionOptions();
      renderScenarioChips();
      renderQuickPrompts();
      syncOverviewStats();
    });
    refs.scenarioChips.appendChild(button);
  });
}

async function refreshHealth() {
  try {
    const response = await fetch("/v1/ping");
    refs.healthStatus.textContent = response.ok ? "在线" : "异常";
  } catch (error) {
    refs.healthStatus.textContent = "离线";
  }
}

async function loadProducts() {
  refs.productGrid.innerHTML = "<div class='output-box'>正在加载商品货架...</div>";
  try {
    const response = await fetch("/api/products");
    if (!response.ok) {
      throw new Error("商品接口调用失败");
    }
    const data = await response.json();
    state.products = Array.isArray(data.products) ? data.products : [];
    state.selectedProducts = new Set(state.products.map((product) => product.name));
    renderProducts();
    syncOverviewStats();
  } catch (error) {
    refs.productGrid.innerHTML =
      "<div class='output-box has-content'>商品货架加载失败，请确认后端服务已经正常启动。</div>";
    refs.productPill.textContent = "加载失败";
  }
}

function renderProducts() {
  refs.productGrid.innerHTML = "";
  if (!state.products.length) {
    refs.productGrid.innerHTML = "<div class='output-box'>当前没有可展示的商品数据。</div>";
    refs.productPill.textContent = "0 项商品";
    return;
  }

  state.products.forEach((product) => {
    const card = document.createElement("label");
    card.className = "product-card";
    const imageMarkup = isHttpUrl(product.cover_image)
      ? `<img src="${product.cover_image}" alt="${escapeHtml(product.name)}" />`
      : `<span>${escapeHtml(getProductBadge(product.name))}</span>`;
    card.innerHTML = `
      <input type="checkbox" ${state.selectedProducts.has(product.name) ? "checked" : ""} />
      <div class="product-card-content">
        <div class="product-thumb">${imageMarkup}</div>
        <div>
          <h4>${escapeHtml(product.name)}</h4>
          <p>${escapeHtml(product.description || "暂无描述")}</p>
        </div>
      </div>
    `;
    const checkbox = card.querySelector("input");
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        state.selectedProducts.add(product.name);
      } else {
        state.selectedProducts.delete(product.name);
      }
      syncOverviewStats();
    });
    refs.productGrid.appendChild(card);
  });
  syncOverviewStats();
}

async function loadConversations(options = {}) {
  const { silent = false } = options;
  if (!silent) {
    refs.conversationList.innerHTML = "<div class='output-box'>正在加载历史会话...</div>";
    refs.conversationPill.textContent = "加载中";
  }

  try {
    const accountId = encodeURIComponent(refs.accountId.value.trim() || "100000");
    const response = await fetch(`/api/conversations?limit=20&account_id=${accountId}`);
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(extractError(payload));
    }
    state.conversations = Array.isArray(payload.conversations)
      ? payload.conversations
      : [];
    renderConversationList();
  } catch (error) {
    refs.conversationList.innerHTML = `<div class="output-box has-content">历史会话加载失败：${escapeHtml(error.message)}</div>`;
    refs.conversationPill.textContent = "加载失败";
  }
}

function renderConversationList() {
  refs.conversationList.innerHTML = "";
  refs.conversationPill.textContent = `${state.conversations.length} 条`;

  if (!state.conversations.length) {
    refs.conversationList.innerHTML = "<div class='output-box'>暂无历史会话。</div>";
    return;
  }

  state.conversations.forEach((conversation) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `conversation-item${
      conversation.id === state.conversationId ? " is-active" : ""
    }`;
    button.innerHTML = `
      <span class="conversation-item-title">${escapeHtml(conversation.title || "新会话")}</span>
      <p class="conversation-item-last">${escapeHtml(
        truncateText(conversation.last_message || "暂无消息", 64)
      )}</p>
      <span class="conversation-item-meta">${escapeHtml(
        formatConversationTime(conversation.updated_at)
      )} · ${escapeHtml(conversation.account_id || "unknown")}</span>
    `;
    button.addEventListener("click", () => openConversation(conversation.id));
    refs.conversationList.appendChild(button);
  });
}

async function openConversation(conversationId) {
  if (!conversationId || conversationId === state.conversationId) {
    return;
  }

  setConversationButtons(true);
  try {
    const accountId = encodeURIComponent(refs.accountId.value.trim() || "100000");
    const response = await fetch(
      `/api/conversations/${encodeURIComponent(conversationId)}?account_id=${accountId}`
    );
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(extractError(payload));
    }
    restoreConversation(payload);
  } catch (error) {
    addMessage("system", `历史会话恢复失败：${error.message}`);
  } finally {
    setConversationButtons(false);
  }
}

function restoreConversation(conversation) {
  state.conversationId = conversation.id || null;
  state.messages = Array.isArray(conversation.messages)
    ? conversation.messages
        .filter((message) => message.role && message.content)
        .map((message) => ({
          role: message.role,
          content: message.content,
          metadata: message.metadata || {},
        }))
    : [];

  if (conversation.account_id) {
    refs.accountId.value = conversation.account_id;
  }

  refs.chatThread.innerHTML = "";
  if (!state.messages.length) {
    seedWelcomeMessage();
  } else {
    state.messages.forEach((message) => addMessage(message.role, message.content));
  }

  rebuildConversationInsights();
  resetOutputs();
  updateMessageCount();
  renderConversationList();
  switchTab("results");
}

function rebuildConversationInsights() {
  const records = [];
  const cards = [];

  [...state.messages].reverse().forEach((message) => {
    const botUsage = message.metadata?.bot_usage;
    records.push(...normalizeBotUsage(botUsage));
    cards.push(...normalizeResultCards(botUsage));
  });

  state.executionRecords = records.slice(0, 12);
  state.resultCards = cards.slice(0, 8);
  renderExecutionTimeline();
  renderResultCards();
}

function setConversationButtons(disabled) {
  refs.refreshConversations.disabled = disabled;
  refs.newConversation.disabled = disabled;
  refs.conversationList.querySelectorAll("button").forEach((button) => {
    button.disabled = disabled;
  });
}

async function handleSendMessage(event) {
  event.preventDefault();
  const content = refs.composerInput.value.trim();
  if (!content) {
    refs.composerInput.focus();
    return;
  }

  const previousMessages = [...state.messages];
  const userMessage = { role: "user", content };
  state.messages.push(userMessage);
  addMessage("user", content);
  refs.composerInput.value = "";
  updateMessageCount();

  const assistantNode = addMessage("assistant", "正在生成回复...");
  const accountId = refs.accountId.value.trim() || "100000";
  const selectedFunctions = Array.from(state.selectedFunctions);
  const selectedProducts = Array.from(state.selectedProducts);
  const legacyBody = {
    stream: refs.streamMode.checked,
    model: "shop-assist-demo",
    metadata: {
      account_id: accountId,
      ...(state.conversationId ? { conversation_id: state.conversationId } : {}),
      support_functions: selectedFunctions,
      product_list: selectedProducts,
    },
    messages: state.messages,
  };
  const businessBody = {
    message: content,
    account_id: accountId,
    ...(state.conversationId ? { conversation_id: state.conversationId } : {}),
    support_functions: selectedFunctions,
    product_list: selectedProducts,
    history: previousMessages,
    model: "customer-service-agent",
  };

  setActionState(true);
  try {
    const result = refs.streamMode.checked
      ? await streamChat(legacyBody, assistantNode)
      : await requestChat(businessBody);
    const text = result.content || "模型未返回内容。";
    const conversationId = result.conversationId || result.metadata?.conversation_id;
    if (conversationId) {
      state.conversationId = conversationId;
    }
    replaceMessageBody(assistantNode, text);
    state.messages.push({ role: "assistant", content: text });
    updateExecutionTimeline(result.botUsage);
    updateResultCards(result.botUsage);
    updateMessageCount();
    await loadConversations({ silent: true });
  } catch (error) {
    const message = `请求失败：${error.message}`;
    replaceMessageBody(assistantNode, message);
    assistantNode.classList.remove("is-assistant");
    assistantNode.classList.add("is-system");
  } finally {
    setActionState(false);
  }
}

async function requestChat(body) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const payload = await parseJsonResponse(response);
  if (!response.ok) {
    throw new Error(extractError(payload));
  }
  return {
    content: payload?.answer || extractContent(payload) || "模型未返回内容。",
    botUsage: payload?.bot_usage ?? null,
    metadata: payload?.metadata ?? null,
    conversationId: payload?.conversation_id ?? payload?.metadata?.conversation_id ?? null,
  };
}

async function streamChat(body, assistantNode) {
  const response = await fetch("/api/v3/bots/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok || !response.body) {
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(extractError(payload));
    }
    return {
      content: extractContent(payload) || "流式响应不可用。",
      botUsage: payload?.bot_usage ?? null,
    };
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let fullText = "";
  let latestBotUsage = null;
  let latestMetadata = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const event of events) {
      const lines = event
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
      for (const line of lines) {
        if (!line.startsWith("data:")) {
          continue;
        }
        const raw = line.slice(5).trim();
        if (!raw || raw === "[DONE]") {
          continue;
        }
        try {
          const payload = JSON.parse(raw);
          if (payload?.bot_usage) {
            latestBotUsage = payload.bot_usage;
          }
          if (payload?.metadata) {
            latestMetadata = payload.metadata;
          }
          const delta =
            payload?.choices?.[0]?.delta?.content ??
            payload?.choices?.[0]?.message?.content ??
            payload?.choices?.[0]?.content ??
            payload?.message?.content ??
            "";
          if (delta) {
            fullText += delta;
            replaceMessageBody(assistantNode, fullText);
          }
        } catch (error) {
          continue;
        }
      }
    }
  }

  return {
    content: fullText || "模型未返回内容。",
    botUsage: latestBotUsage,
    metadata: latestMetadata,
    conversationId: latestMetadata?.conversation_id ?? null,
  };
}

async function handleSummary() {
  if (!state.messages.length) {
    updateOutput(refs.summaryOutput, "请先完成至少一轮会话。");
    switchTab("ops");
    return;
  }
  switchTab("ops");
  await runUtility(refs.summaryBtn, refs.summaryOutput, "/api/summary", {
    messages: state.messages,
    model: "customer-service-agent",
  });
}

async function handleNextQuestion() {
  if (!state.messages.length) {
    updateOutput(refs.nextQuestionOutput, "请先完成至少一轮会话。");
    switchTab("ops");
    return;
  }
  switchTab("ops");
  await runUtility(
    refs.nextQuestionBtn,
    refs.nextQuestionOutput,
    "/api/v3/bots/chat/completions/next_question",
    {
      stream: false,
      model: "shop-assist-demo",
      messages: state.messages,
    }
  );
}

async function handleQualityInspection() {
  const transcript = buildTranscript();
  if (!transcript) {
    updateOutput(refs.qualityOutput, "请先让客服生成至少一条回复。");
    switchTab("ops");
    return;
  }

  const keywords = refs.qualityKeywords.value.trim();

  switchTab("ops");
  await runUtility(
    refs.qualityBtn,
    refs.qualityOutput,
    "/api/quality-check",
    {
      content: transcript,
      keywords,
      model: "customer-service-agent",
    },
    formatQualityOutput
  );
}

async function handleSaveFaq() {
  const lastUser = [...state.messages].reverse().find((item) => item.role === "user");
  const lastAssistant = [...state.messages]
    .reverse()
    .find((item) => item.role === "assistant" && item.content.trim());

  if (!lastUser || !lastAssistant) {
    updateOutput(refs.faqOutput, "请先完成一组用户提问和客服回复。");
    switchTab("ops");
    return;
  }

  switchTab("ops");
  toggleButton(refs.saveFaqBtn, true);
  try {
    const response = await fetch("/api/faqs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: lastUser.content.slice(0, 100),
        answer: lastAssistant.content.slice(0, 500),
        score: Number(refs.faqScore.value),
        account_id: refs.accountId.value.trim() || "100000",
      }),
    });
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(extractError(payload));
    }
    updateOutput(refs.faqOutput, "FAQ 已成功保存到知识库。");
  } catch (error) {
    updateOutput(refs.faqOutput, `保存失败：${error.message}`);
  } finally {
    toggleButton(refs.saveFaqBtn, false);
  }
}

async function runUtility(button, outputNode, url, body, formatter = null) {
  toggleButton(button, true);
  updateOutput(outputNode, "处理中...");
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    const payload = await parseJsonResponse(response);
    if (!response.ok) {
      throw new Error(extractError(payload));
    }
    if (formatter) {
      const formatted = formatter(payload);
      if (formatted.html) {
        updateOutputHtml(outputNode, formatted.html);
      } else {
        updateOutput(outputNode, formatted.text || "未返回内容。");
      }
    } else {
      updateOutput(outputNode, extractContent(payload) || "未返回内容。");
    }
  } catch (error) {
    updateOutput(outputNode, `请求失败：${error.message}`);
  } finally {
    toggleButton(button, false);
  }
}

function clearConversation() {
  state.messages = [];
  state.executionRecords = [];
  state.resultCards = [];
  state.conversationId = null;
  refs.chatThread.innerHTML = "";
  seedWelcomeMessage();
  updateMessageCount();
  resetOutputs();
  renderExecutionTimeline();
  renderResultCards();
  renderCustomerContext();
  renderConversationList();
  switchTab("results");
}

function addMessage(role, content) {
  const fragment = refs.messageTemplate.content.cloneNode(true);
  const message = fragment.querySelector(".message-card");
  message.classList.add(`is-${role}`);
  message.querySelector(".message-role").textContent = getRoleLabel(role);
  message.querySelector(".message-body").textContent = content;
  refs.chatThread.appendChild(fragment);
  refs.chatThread.scrollTop = refs.chatThread.scrollHeight;
  return refs.chatThread.lastElementChild;
}

function replaceMessageBody(node, content) {
  node.querySelector(".message-body").textContent = content;
  refs.chatThread.scrollTop = refs.chatThread.scrollHeight;
}

function updateOutput(node, text, hasContent = true) {
  node.textContent = text;
  node.classList.toggle("has-content", hasContent);
}

function updateOutputHtml(node, html, hasContent = true) {
  node.innerHTML = html;
  node.classList.toggle("has-content", hasContent);
}

function updateMessageCount() {
  refs.messageCount.textContent = String(state.messages.length);
}

function toggleButton(button, disabled) {
  button.disabled = disabled;
}

function setActionState(disabled) {
  [
    refs.summaryBtn,
    refs.nextQuestionBtn,
    refs.qualityBtn,
    refs.saveFaqBtn,
    refs.clearChat,
    refs.composerSubmit,
    refs.refreshConversations,
    refs.newConversation,
  ].filter(Boolean).forEach((button) => {
    button.disabled = disabled;
  });
  refs.composerInput.disabled = disabled;
}

function syncOverviewStats() {
  const selectedFunctionCount = state.selectedFunctions.size;
  const selectedProductCount = state.selectedProducts.size;
  const scenario = getActiveScenario();

  refs.activeCapabilityCount.textContent = String(selectedFunctionCount);
  refs.capabilityPill.textContent = `${selectedFunctionCount} 项已启用`;
  refs.selectedProductCount.textContent = String(selectedProductCount);
  refs.productPill.textContent = state.products.length
    ? `${selectedProductCount}/${state.products.length} 项已选`
    : "加载中";
  refs.modeLabel.textContent = refs.streamMode.checked ? "逐字" : "完整";
  if (refs.deskAccount) {
    refs.deskAccount.textContent = refs.accountId.value.trim() || "100000";
  }
  if (refs.deskScenario) {
    refs.deskScenario.textContent = scenario.label;
  }
  if (refs.deskCapabilities) {
    refs.deskCapabilities.textContent = `${selectedFunctionCount} 项`;
  }
  if (refs.deskLatestAction) {
    const latestUserMessage = [...state.messages]
      .reverse()
      .find((message) => message.role === "user")?.content;
    refs.deskLatestAction.textContent =
      state.executionRecords[0]?.actionName ||
      (latestUserMessage ? inferIntentLabel(latestUserMessage) : "等待接待");
  }
}

function getActiveScenario() {
  return (
    SCENARIO_PRESETS.find((scenario) => scenario.id === state.activeScenario) ||
    SCENARIO_PRESETS[0]
  );
}

function updateExecutionTimeline(botUsage) {
  const records = normalizeBotUsage(botUsage);
  if (!records.length) {
    return;
  }
  state.executionRecords = [...records, ...state.executionRecords].slice(0, 12);
  renderExecutionTimeline();
  switchTab("execution");
}

function renderExecutionTimeline() {
  refs.executionTimeline.innerHTML = "";
  if (!state.executionRecords.length) {
    refs.executionTimeline.innerHTML = `<div class="output-box">${DEFAULT_OUTPUTS.execution}</div>`;
    refs.executionPill.textContent = "0 条动作";
    refs.latestActionName.textContent = "暂无";
    refs.toolCallCount.textContent = "0";
    return;
  }

  refs.executionPill.textContent = `${state.executionRecords.length} 条动作`;
  refs.latestActionName.textContent = state.executionRecords[0].actionName;
  refs.toolCallCount.textContent = String(state.executionRecords.length);
  if (refs.deskLatestAction) {
    refs.deskLatestAction.textContent = state.executionRecords[0].actionName;
  }

  state.executionRecords.forEach((record) => {
    const fragment = refs.executionTemplate.content.cloneNode(true);
    fragment.querySelector(".execution-action").textContent = record.actionName;
    fragment.querySelector(".execution-tool").textContent = record.toolName;
    fragment.querySelector(".execution-time").textContent = record.timeLabel;
    fragment.querySelector(".execution-input").textContent = record.input;
    fragment.querySelector(".execution-output").textContent = record.output;
    refs.executionTimeline.appendChild(fragment);
  });
}

function updateResultCards(botUsage) {
  const cards = normalizeResultCards(botUsage);
  if (!cards.length) {
    return;
  }
  state.resultCards = [...cards, ...state.resultCards].slice(0, 8);
  renderResultCards();
  renderCustomerContext();
  switchTab("results");
}

function renderResultCards() {
  refs.resultCards.innerHTML = "";
  if (!state.resultCards.length) {
    refs.resultCards.innerHTML = `<div class="output-box">${DEFAULT_OUTPUTS.results}</div>`;
    refs.resultPill.textContent = "暂无结果";
    renderCustomerContext();
    return;
  }

  refs.resultPill.textContent = `${state.resultCards.length} 条结果`;
  state.resultCards.forEach((card) => {
    const fragment = refs.resultTemplate.content.cloneNode(true);
    fragment.querySelector(".result-type").textContent = card.type;
    fragment.querySelector(".result-title").textContent = card.title;
    fragment.querySelector(".result-status").textContent = card.status;
    const fieldsNode = fragment.querySelector(".result-fields");
    card.fields.forEach((field) => {
      const fieldNode = document.createElement("div");
      fieldNode.className = "result-field";
      fieldNode.innerHTML = `<span>${escapeHtml(field.label)}</span><p>${escapeHtml(field.value)}</p>`;
      fieldsNode.appendChild(fieldNode);
    });
    const richNode = fragment.querySelector(".result-rich");
    if (card.richHtml) {
      richNode.innerHTML = card.richHtml;
    } else {
      richNode.remove();
    }
    refs.resultCards.appendChild(fragment);
  });
  renderCustomerContext();
}

function renderCustomerContext() {
  if (!refs.contextAccount) {
    return;
  }

  const lastUserMessage = [...state.messages]
    .reverse()
    .find((message) => message.role === "user");
  const latestCard = state.resultCards[0];
  const latestOrderCard = state.resultCards.find((card) => card.type === "订单");
  const latestKnowledgeCard = state.resultCards.find((card) => card.type === "知识");
  const latestProduct =
    latestCard?.summary?.product ||
    latestOrderCard?.summary?.product ||
    detectProductFromText(lastUserMessage?.content);
  const knowledgeCount = state.resultCards
    .filter((card) => card.type === "知识")
    .reduce((total, card) => total + (card.summary?.count || 0), 0);

  refs.contextAccount.textContent = refs.accountId.value.trim() || "100000";
  refs.contextConversation.textContent = state.conversationId ? "已保存会话" : "新会话";
  refs.contextIntent.textContent = lastUserMessage
    ? inferIntentLabel(lastUserMessage.content)
    : "尚未开始";
  refs.contextStatus.textContent = latestCard
    ? `${latestCard.type} · ${latestCard.status}`
    : "等待消息";
  refs.contextProduct.textContent = latestProduct || "暂无";
  refs.contextKnowledge.textContent = `${knowledgeCount} 条`;
}

function getRoleLabel(role) {
  if (role === "user") {
    return "顾客";
  }
  if (role === "assistant") {
    return "客服";
  }
  return "记录";
}

function buildTranscript() {
  return state.messages
    .map((item) => `${item.role}: ${item.content}`)
    .join("\n")
    .trim();
}

function extractContent(payload) {
  return (
    payload?.choices?.[0]?.message?.content ??
    payload?.choices?.[0]?.delta?.content ??
    payload?.message?.content ??
    payload?.content ??
    payload?.answer ??
    payload?.summary ??
    payload?.result ??
    ""
  );
}

function formatQualityOutput(payload) {
  const structured = payload?.structured_result;
  if (!structured) {
    return { text: extractContent(payload) || "未返回内容。" };
  }

  const hits = Array.isArray(structured.hits) ? structured.hits : [];
  const suggestions = Array.isArray(structured.suggestions)
    ? structured.suggestions
    : [];
  const riskLevel = structured.risk_level || "none";
  const hitMarkup = hits.length
    ? hits
        .slice(0, 10)
        .map(
          (hit) =>
            `<span class="risk-hit is-${escapeHtml(hit.severity || "low")}">${escapeHtml(
              hit.keyword || hit.evidence || "命中词"
            )}</span>`
        )
        .join("")
    : `<span class="risk-hit is-none">未命中风险词</span>`;
  const suggestionMarkup = suggestions.length
    ? suggestions
        .slice(0, 4)
        .map((suggestion) => `<li>${escapeHtml(suggestion)}</li>`)
        .join("")
    : "<li>未发现明显风险，保持礼貌、准确、可验证的表达。</li>";
  const modelNote = extractContent(payload);

  return {
    html: `
      <div class="risk-summary">
        <div class="risk-summary-head">
          <span class="risk-level is-${escapeHtml(riskLevel)}">${escapeHtml(
            getRiskLevelLabel(riskLevel)
          )}</span>
          <span class="risk-score">风险分 ${escapeHtml(
            structured.risk_score ?? 0
          )} · 命中 ${escapeHtml(structured.hit_count ?? hits.length)} 项</span>
        </div>
        <div class="risk-section">
          <strong>命中词</strong>
          <div class="risk-hit-list">${hitMarkup}</div>
        </div>
        <div class="risk-section">
          <strong>处理建议</strong>
          <ul class="risk-suggestions">${suggestionMarkup}</ul>
        </div>
        ${
          modelNote
            ? `<p class="risk-model-note">${escapeHtml(modelNote)}</p>`
            : ""
        }
      </div>
    `,
  };
}

function getRiskLevelLabel(level) {
  if (level === "high") {
    return "高风险";
  }
  if (level === "medium") {
    return "中风险";
  }
  if (level === "low") {
    return "低风险";
  }
  return "无明显风险";
}

function extractError(payload) {
  return (
    payload?.detail?.message ??
    payload?.detail?.code ??
    payload?.error?.message ??
    "接口返回异常"
  );
}

async function parseJsonResponse(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    if (!response.ok) {
      throw new Error(text);
    }
    return { content: text };
  }
}

function normalizeBotUsage(botUsage) {
  const actionDetails = Array.isArray(botUsage?.action_details)
    ? botUsage.action_details
    : [];

  return actionDetails.flatMap((actionDetail) => {
    const toolDetails = Array.isArray(actionDetail?.tool_details)
      ? actionDetail.tool_details
      : [];

    if (!toolDetails.length) {
      return [
        {
          actionName: prettifyLabel(actionDetail?.name || "action"),
          toolName: "无工具细节",
          input: "暂无输入信息",
          output: "暂无输出信息",
          timeLabel: "无时间数据",
        },
      ];
    }

    return toolDetails.map((toolDetail) => {
      const completedAt = toolDetail?.completed_at || toolDetail?.created_at;
      return {
        actionName: prettifyLabel(actionDetail?.name || "action"),
        toolName: prettifyLabel(toolDetail?.name || "tool"),
        input: summarizeValue(toolDetail?.input),
        output: summarizeValue(toolDetail?.output),
        timeLabel: completedAt ? formatTimestamp(completedAt) : "刚刚",
      };
    });
  });
}

function normalizeResultCards(botUsage) {
  const actionDetails = Array.isArray(botUsage?.action_details)
    ? botUsage.action_details
    : [];
  const cards = [];

  actionDetails.forEach((actionDetail) => {
    const toolDetails = Array.isArray(actionDetail?.tool_details)
      ? actionDetail.tool_details
      : [];

    toolDetails.forEach((toolDetail) => {
      const normalized = buildResultCard(
        actionDetail?.name || "action",
        toolDetail?.name || "tool",
        toolDetail?.output
      );
      if (normalized) {
        cards.push(normalized);
      }
    });
  });

  return cards;
}

function buildResultCard(actionName, toolName, output) {
  const prettyAction = prettifyLabel(actionName);
  const prettyTool = prettifyLabel(toolName);
  const rawTool = String(toolName || "").toLowerCase();
  const rawAction = String(actionName || "").toLowerCase();

  if (Array.isArray(output)) {
    if (!output.length && isKnowledgeTool(rawAction, rawTool)) {
      return {
        type: "知识",
        title: `${prettyTool} 未命中`,
        status: "暂无资料",
        fields: [
          {
            label: "处理建议",
            value: "知识库没有返回相关片段，本轮回复应避免编造，并引导用户补充信息或转人工。",
          },
        ],
      };
    }

    if (output.length && isPlainObject(output[0]) && "order_id" in output[0]) {
      const firstOrder = output[0];
      return {
        type: "订单",
        title: `${prettyTool} 返回 ${output.length} 条订单`,
        status: firstOrder.status || "已返回",
        summary: {
          count: output.length,
          product: firstOrder.product || "",
        },
        fields: [
          { label: "首条订单号", value: firstOrder.order_id || "未知" },
          { label: "商品", value: firstOrder.product || "未知" },
          { label: "账户", value: firstOrder.account_id || "未知" },
        ],
        richHtml: renderOrderList(output),
      };
    }

    if (output.length && isKnowledgeRecord(output[0])) {
      return {
        type: "知识",
        title: `${prettyTool} 命中 ${output.length} 条知识`,
        status: formatKnowledgeStatus(output[0]),
        summary: {
          count: output.length,
        },
        fields: buildKnowledgeFields(output),
        richHtml: renderKnowledgeList(output),
      };
    }

    if (output.length && isPlainObject(output[0])) {
      return {
        type: "知识",
        title: `${prettyAction} 摘要`,
        status: `${output.length} 条片段`,
        fields: [
          { label: "第一条结果", value: summarizeValue(output[0]) },
          { label: "来源动作", value: prettyTool },
        ],
      };
    }
  }

  if (isPlainObject(output) && "tracking_number" in output) {
    const events = Array.isArray(output.events) ? output.events : [];
    const latest = events[events.length - 1];
      return {
        type: "物流",
        title: prettyTool,
        status: formatStatusLabel(output.current_status || "物流处理中"),
        summary: {
          count: events.length,
        },
        fields: [
          { label: "运单号", value: output.tracking_number || "未知" },
        { label: "最新节点", value: latest?.description || "暂无节点" },
        { label: "位置", value: latest?.location || "未知" },
      ],
      richHtml: renderTrackingTimeline(events),
    };
  }

  if (isPlainObject(output) && "message" in output && "order" in output) {
    const order = isPlainObject(output.order) ? output.order : {};
    return {
      type: "售后",
      title: prettyTool,
      status: String(output.message || "").includes("successful") ? "退款成功" : "已返回结果",
      summary: {
        product: order.product || "",
      },
      fields: [
        { label: "处理结果", value: output.message || "已返回" },
        { label: "订单号", value: order.order_id || "未知" },
        { label: "商品", value: order.product || "未知" },
      ],
      richHtml: renderRefundStatus(output),
    };
  }

  if (isPlainObject(output) && "order_id" in output) {
    return {
      type: "订单",
      title: prettyTool,
      status: output.status || "已返回",
      summary: {
        product: output.product || "",
      },
      fields: [
        { label: "订单号", value: output.order_id || "未知" },
        { label: "商品", value: output.product || "未知" },
        { label: "账户", value: output.account_id || "未知" },
      ],
      richHtml: renderOrderList([output]),
    };
  }

  if (typeof output === "string") {
    if (/refund/i.test(output) || /退/.test(output)) {
      return {
        type: "售后",
        title: prettyTool,
        status: output.includes("successful") || output.includes("成功") ? "成功" : "已返回结果",
        fields: [{ label: "处理结果", value: output }],
      };
    }

    if (/order/i.test(output) || /订单/.test(output)) {
      return {
        type: "订单",
        title: prettyTool,
        status: "文本结果",
        fields: [{ label: "结果", value: output }],
      };
    }
  }

  if (output != null) {
    return {
      type: "数据",
      title: prettyTool,
      status: "结构化结果",
      fields: [{ label: "摘要", value: summarizeValue(output) }],
    };
  }

  return null;
}

function renderOrderList(orders) {
  const rows = orders
    .slice(0, 5)
    .map((order) => {
      const statusClass = getStatusClass(order.status);
      return `
        <div class="order-row">
          <div>
            <strong>${escapeHtml(order.order_id || "未知订单")}</strong>
            <span>${escapeHtml(order.product || "未知商品")}</span>
          </div>
          <div>
            <span class="status-badge ${statusClass}">${escapeHtml(formatStatusLabel(order.status || "未知状态"))}</span>
            <small>${escapeHtml(order.tracking_number || "暂无运单号")}</small>
          </div>
        </div>
      `;
    })
    .join("");
  const more = orders.length > 5
    ? `<div class="rich-note">还有 ${escapeHtml(orders.length - 5)} 条订单，可在执行轨迹查看完整输出。</div>`
    : "";
  return `<div class="order-list">${rows}${more}</div>`;
}

function renderTrackingTimeline(events) {
  if (!events.length) {
    return `<div class="rich-note">暂未返回物流节点。</div>`;
  }

  const items = events
    .slice(-5)
    .reverse()
    .map((event, index) => `
      <div class="tracking-node${index === 0 ? " is-latest" : ""}">
      <div class="tracking-marker"></div>
      <div>
        <div class="tracking-head">
            <strong>${escapeHtml(formatStatusLabel(event.status || "物流节点"))}</strong>
            <span>${escapeHtml(event.time || "")}</span>
          </div>
          <p>${escapeHtml(event.description || "暂无描述")}</p>
          <small>${escapeHtml(event.location || "未知位置")}</small>
        </div>
      </div>
    `)
    .join("");

  return `<div class="tracking-timeline">${items}</div>`;
}

function renderKnowledgeList(records) {
  const items = records
    .slice(0, 4)
    .map((record) => {
      const title = record.document_name || record.document_id || record.dataset_id || "知识片段";
      const score = record.score == null ? "" : `<span>${escapeHtml(formatScore(record.score))}</span>`;
      return `
        <div class="knowledge-hit">
          <div>
            <strong>${escapeHtml(title)}</strong>
            ${score}
          </div>
          <p>${escapeHtml(truncateText(record.content || summarizeValue(record), 140))}</p>
        </div>
      `;
    })
    .join("");
  return `<div class="knowledge-list">${items}</div>`;
}

function renderRefundStatus(output) {
  const order = isPlainObject(output.order) ? output.order : {};
  return `
    <div class="refund-panel">
      <span class="status-badge ${getStatusClass(order.status || output.message)}">
        ${escapeHtml(formatStatusLabel(order.status || output.message || "已处理"))}
      </span>
      <div>
        <strong>${escapeHtml(order.order_id || "未知订单")}</strong>
        <p>${escapeHtml(order.reason || "暂无退款原因")}</p>
      </div>
    </div>
  `;
}

function inferIntentLabel(text = "") {
  const content = String(text);
  if (/退款|退货|售后|refund|return/i.test(content)) {
    return "售后处理";
  }
  if (/物流|快递|运单|送到|shipping|delivery|track/i.test(content)) {
    return "物流咨询";
  }
  if (/订单|买过|下单|order|purchased/i.test(content)) {
    return "订单查询";
  }
  if (/推荐|适合|哪个好|recommend/i.test(content)) {
    return "导购推荐";
  }
  return "普通咨询";
}

function detectProductFromText(text = "") {
  const content = String(text);
  const matched = state.products.find((product) => content.includes(product.name));
  return matched?.name || "";
}

function getStatusClass(status = "") {
  const value = String(status).toLowerCase();
  if (/退款|refunded|成功|successful/.test(value)) {
    return "is-success";
  }
  if (/未发货|pending|等待|not shipped/.test(value)) {
    return "is-warning";
  }
  if (/失败|failed|不存在|not found/.test(value)) {
    return "is-danger";
  }
  return "is-info";
}

function formatStatusLabel(status = "") {
  const value = String(status || "");
  const enumName = value.match(/^TrackingStatus\.(\w+)$/)?.[1];
  const enumLabels = {
    PENDING: "待揽收",
    PICKED_UP: "已揽收",
    IN_TRANSIT: "运输中",
    DELIVERING: "派送中",
    DELIVERED: "已签收",
  };
  return enumName ? enumLabels[enumName] || enumName : value;
}

function isKnowledgeTool(actionName, toolName) {
  return /knowledge|retrieval|dify/.test(`${actionName} ${toolName}`);
}

function isKnowledgeRecord(value) {
  return (
    isPlainObject(value) &&
    ("content" in value || "document_name" in value || "score" in value || "dataset_id" in value)
  );
}

function formatKnowledgeStatus(record) {
  if (record?.score == null) {
    return record?.document_name || "已命中";
  }
  return `相关度 ${formatScore(record.score)}`;
}

function buildKnowledgeFields(records) {
  const fields = records.slice(0, 3).map((record, index) => {
    const source = record.document_name || record.document_id || record.dataset_id || `片段 ${index + 1}`;
    const score = record.score == null ? "" : ` · ${formatScore(record.score)}`;
    return {
      label: `${source}${score}`,
      value: record.content || summarizeValue(record),
    };
  });

  if (records.length > 3) {
    fields.push({
      label: "更多命中",
      value: `还有 ${records.length - 3} 条知识片段，可在执行轨迹中查看完整输出。`,
    });
  }

  return fields;
}

function formatScore(score) {
  const numeric = Number(score);
  if (Number.isNaN(numeric)) {
    return String(score);
  }
  return numeric <= 1 ? `${Math.round(numeric * 100)}%` : numeric.toFixed(2);
}

function summarizeValue(value) {
  if (value == null) {
    return "暂无数据";
  }

  if (typeof value === "string") {
    return truncateText(value);
  }

  try {
    return truncateText(JSON.stringify(value, null, 2));
  } catch (error) {
    return truncateText(String(value));
  }
}

function truncateText(text, maxLength = 260) {
  const normalized = String(text).trim();
  if (normalized.length <= maxLength) {
    return normalized || "暂无数据";
  }
  return `${normalized.slice(0, maxLength)}...`;
}

function prettifyLabel(value) {
  const raw = String(value || "").trim();
  if (!raw) {
    return "未知";
  }
  if (ACTION_LABELS[raw]) {
    return ACTION_LABELS[raw];
  }
  return raw
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "刚刚";
  }
  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatConversationTime(timestamp) {
  const numeric = Number(timestamp);
  const date = new Date(numeric < 1000000000000 ? numeric * 1000 : numeric);
  if (Number.isNaN(date.getTime())) {
    return "刚刚";
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getProductBadge(name) {
  return name
    .replace(/\s+/g, "")
    .slice(0, 2)
    .toUpperCase();
}

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === "[object Object]";
}

function isHttpUrl(value) {
  return /^https?:\/\//i.test(value || "");
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
