# Customer Service Agent 优化任务计划书

## 1. 项目目标

把当前项目从“可演示的智能客服 Demo”升级为“可接入真实业务系统的客服 Agent 原型”。

核心目标：

- 支持多模型供应商：火山引擎、DeepSeek、智谱，以及后续 OpenAI-compatible 模型。
- 支持可替换知识库：火山知识库、Dify 知识库。
- 支持统一工具调用：订单查询、物流查询、退款处理、知识检索等能力不依赖单一模型供应商。
- 支持真实客服工作台体验：会话管理、知识命中展示、质检、FAQ 沉淀、人工接管。
- 支持工程化交付：测试、配置、Docker、文档、可观测性。

## 2. 当前状态

已完成：

- 本地 mock 模式。
- DeepSeek / 智谱 / 火山模型切换。
- Dify / 火山知识库切换。
- Dify 检索命中结果展示。
- Dify 未命中防胡编提示。
- FAQ 可保存到 Dify 或本地 mock。
- Docker 基础启动配置。
- 基础单元测试。

待加强：

- DeepSeek / 智谱尚未完整接入统一 tool calling。
- 会话仍主要依赖前端传递 messages。
- API 路径仍偏 demo 风格。
- 订单、物流、退款仍是 mock 数据。
- 缺少统一日志、调用耗时、模型成本统计。

## 3. 总体技术路线

```text
前端客服工作台
  ↓
标准业务 API / 兼容旧 API
  ↓
会话管理层
  ↓
Agent 编排层
  ├─ 模型 Provider：火山 / DeepSeek / 智谱 / OpenAI-compatible
  ├─ 知识 Provider：Dify / 火山 / mock
  └─ Tool Registry：订单 / 物流 / 退款 / FAQ / 商品
  ↓
业务数据层：mock / 真实 API / 数据库
```

## 4. 阶段计划

### 阶段一：统一 Agent 能力

目标：不管使用 DeepSeek、智谱还是火山，都能稳定调用同一套工具。

任务：

- [x] 抽象 provider-independent tool registry。
- [x] 为 OpenAI-compatible 模型增加 tool calling loop。
- [x] 支持工具：`order_check`、`pack_track`、`order_refund`。
- [x] 工具结果统一写入 `bot_usage.action_details`。
- [x] 前端继续复用现有结果卡片展示工具结果。
- [x] 补工具调用单元测试。

验收标准：

- DeepSeek/智谱路径下，用户问订单时能触发 `order_check`。
- 用户问物流时能触发 `pack_track`。
- 用户问退款时能触发 `order_refund`。
- 右侧“业务结果”和“执行轨迹”能看到工具调用。
- 测试通过。

### 阶段二：会话管理

目标：后端保存会话，不再完全依赖前端传完整上下文。

任务：

- [x] 增加 SQLite 存储。
- [x] 新增 `conversation_id`。
- [x] 保存 user / assistant / tool 消息。
- [x] 增加会话列表接口。
- [x] 增加会话详情接口。
- [x] 支持完整前端会话恢复。

验收标准：

- 刷新页面后可恢复历史会话。
- 每轮工具调用和模型回复可追溯。

### 阶段三：标准业务 API

目标：保留旧 API，同时提供更清晰的业务接口。

任务：

- [x] 新增 `POST /api/chat`。
- [x] 新增 `GET /api/products`。
- [x] 新增 `GET /api/conversations`。
- [x] 新增 `POST /api/faqs`。
- [x] 统一响应格式。
- [x] 增加 API Key 鉴权。

验收标准：

- 外部系统可以用更简单的业务 API 接入。
- 旧前端和旧接口继续可用。

### 阶段四：真实业务数据接入准备

目标：让订单、物流、退款从 mock 平滑替换为真实接口。

任务：

- [ ] 抽象 `OrderRepository`。
- [ ] 抽象 `LogisticsProvider`。
- [ ] 抽象 `RefundService`。
- [ ] mock 实现保留。
- [ ] 增加真实 HTTP API 实现模板。

验收标准：

- 切换数据源不需要改 Agent 层。

### 阶段五：质检与运营增强

目标：让客服系统具备持续运营能力。

任务：

- [x] 增加规则型质检词库。
- [x] 质检输出结构化：风险等级、命中词、建议话术。
- [ ] FAQ 保存前支持人工编辑。
- [ ] FAQ 去重。
- [ ] 会话总结归档。

验收标准：

- 风险话术能在前端高亮。
- FAQ 沉淀流程可控。

### 阶段六：前端工作台产品化

目标：从演示页面升级为更接近真实客服 SaaS 的工作台。

任务：

- [x] 左侧会话队列。
- [x] 中间聊天窗口。
- [ ] 右侧用户画像、订单、物流、知识命中、质检结果。
- [ ] AI 回复可编辑后发送。
- [ ] 一键复制回复。
- [ ] 转人工状态。

验收标准：

- 能模拟真实客服日常工作流。

### 阶段七：部署和可观测性

目标：项目可稳定部署和排查问题。

任务：

- [ ] 增加请求日志。
- [ ] 增加模型调用耗时。
- [ ] 增加工具调用耗时。
- [ ] 增加错误日志。
- [ ] 增加 token / 成本统计。
- [ ] 增加 `/health` 和 `/ready`。
- [ ] CI 中运行测试。

验收标准：

- 出问题时能快速定位是模型、知识库、工具还是配置问题。

## 5. 推荐执行顺序

1. 统一 OpenAI-compatible tool calling。
2. 增加会话存储。
3. 新增标准业务 API。
4. 前端会话队列和右侧信息面板升级。
5. 质检规则库。
6. 真实业务数据接口模板。
7. 可观测性和部署增强。

## 6. 风险与注意事项

- DeepSeek / 智谱对 tool calling 的兼容细节可能略有差异，需要保留降级策略。
- Dify 知识库未命中时必须避免模型编造。
- 退款工具未来接真实系统前必须增加权限和二次确认。
- API Key 不应写入 Git。
- 当前仓库历史里 `.venv` 状态混杂，后续提交前应清理索引。

## 7. 当前立即执行项

本轮执行：

- [x] 实现 OpenAI-compatible provider 的统一 tool calling loop。
- [x] 将 `order_check`、`pack_track`、`order_refund` 接入 DeepSeek / 智谱路径。
- [x] 保持火山和 mock 路径兼容。
- [x] 补测试并重启本地服务。
