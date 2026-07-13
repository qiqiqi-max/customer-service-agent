// 客服工作台 - 优化版 JavaScript

const state = {
  messages: [],
  conversationId: null,
  isStreaming: false
};

const refs = {
  chatThread: document.getElementById("chat-thread"),
  composerForm: document.getElementById("composer-form"),
  composerInput: document.getElementById("composer-input"),
  composerSubmit: document.getElementById("composer-submit"),
  clearChat: document.getElementById("clear-chat"),
  accountId: document.getElementById("account-id"),
  streamMode: document.getElementById("stream-mode"),
  newConversation: document.getElementById("new-conversation"),
  refreshConversations: document.getElementById("refresh-conversations"),
  summaryBtn: document.getElementById("summary-btn"),
  summaryOutput: document.getElementById("summary-output"),
  resultCards: document.getElementById("result-cards"),
  executionTimeline: document.getElementById("execution-timeline")
};

// Tab 切换
document.querySelectorAll(".tab-button").forEach(button => {
  button.addEventListener("click", () => {
    const tabName = button.dataset.tab;
    
    document.querySelectorAll(".tab-button").forEach(b => {
      b.classList.remove("is-active");
      b.setAttribute("aria-selected", "false");
    });
    
    document.querySelectorAll(".tab-panel").forEach(p => {
      p.classList.remove("is-active");
    });
    
    button.classList.add("is-active");
    button.setAttribute("aria-selected", "true");
    document.querySelector(`[data-panel="${tabName}"]`).classList.add("is-active");
  });
});

// 添加消息到界面
function addMessage(role, content) {
  const template = document.getElementById("message-template");
  const clone = template.content.cloneNode(true);
  
  const card = clone.querySelector(".message-card");
  card.classList.add(`is-${role}`);
  
  const avatar = clone.querySelector(".message-avatar");
  avatar.textContent = role === "user" ? "客" : "助";
  
  const body = clone.querySelector(".message-body");
  body.textContent = content;
  
  refs.chatThread.appendChild(clone);
  refs.chatThread.scrollTop = refs.chatThread.scrollHeight;
}

// 发送消息
refs.composerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  
  const message = refs.composerInput.value.trim();
  if (!message || state.isStreaming) return;
  
  state.isStreaming = true;
  refs.composerSubmit.disabled = true;
  refs.composerSubmit.textContent = "处理中...";
  
  addMessage("user", message);
  refs.composerInput.value = "";
  
  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        account_id: refs.accountId.value,
        conversation_id: state.conversationId,
        stream: refs.streamMode.value === "true"
      })
    });
    
    if (!response.ok) throw new Error("请求失败");
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantMessage = "";
    let messageElement = null;
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");
      
      for (const line of lines) {
        if (!line.trim() || !line.startsWith("data: ")) continue;
        
        const data = line.slice(6);
        if (data === "[DONE]") break;
        
        try {
          const json = JSON.parse(data);
          
          if (json.type === "chunk" && json.content) {
            assistantMessage += json.content;
            
            if (!messageElement) {
              const template = document.getElementById("message-template");
              const clone = template.content.cloneNode(true);
              const card = clone.querySelector(".message-card");
              card.classList.add("is-assistant");
              const avatar = clone.querySelector(".message-avatar");
              avatar.textContent = "助";
              messageElement = clone.querySelector(".message-body");
              refs.chatThread.appendChild(clone);
            }
            
            messageElement.textContent = assistantMessage;
            refs.chatThread.scrollTop = refs.chatThread.scrollHeight;
          }
          
          if (json.type === "result" && json.content) {
            if (!messageElement) {
              addMessage("assistant", json.content);
            }
          }
          
          if (json.conversation_id) {
            state.conversationId = json.conversation_id;
          }
        } catch (err) {
          console.warn("解析失败:", err);
        }
      }
    }
  } catch (err) {
    addMessage("assistant", `抱歉，处理出错：${err.message}`);
  } finally {
    state.isStreaming = false;
    refs.composerSubmit.disabled = false;
    refs.composerSubmit.textContent = "发送";
  }
});

// 清空对话
refs.clearChat.addEventListener("click", () => {
  if (!confirm("确定清空对话记录？")) return;
  
  refs.chatThread.innerHTML = "";
  state.messages = [];
  state.conversationId = null;
});

// 新会话
refs.newConversation.addEventListener("click", () => {
  refs.chatThread.innerHTML = "";
  state.messages = [];
  state.conversationId = null;
  addMessage("assistant", "你好，我是智能客服助手，有什么可以帮您？");
});

// 生成总结
refs.summaryBtn.addEventListener("click", async () => {
  if (state.messages.length === 0) {
    alert("暂无对话记录");
    return;
  }
  
  refs.summaryBtn.disabled = true;
  refs.summaryBtn.textContent = "生成中...";
  refs.summaryOutput.textContent = "正在生成总结...";
  
  try {
    const response = await fetch("/summary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conversation_id: state.conversationId
      })
    });
    
    if (!response.ok) throw new Error("生成失败");
    
    const data = await response.json();
    refs.summaryOutput.textContent = data.summary || "生成失败";
  } catch (err) {
    refs.summaryOutput.textContent = `生成失败：${err.message}`;
  } finally {
    refs.summaryBtn.disabled = false;
    refs.summaryBtn.textContent = "生成会话总结";
  }
});

// 初始化
window.addEventListener("DOMContentLoaded", () => {
  addMessage("assistant", "你好，我是智能客服助手，有什么可以帮您？");
});
