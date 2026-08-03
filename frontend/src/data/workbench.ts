import type { ScenarioPreset, SupportFunction } from "../types";

export const SUPPORT_FUNCTIONS: SupportFunction[] = [
  {
    key: "product_description",
    label: "商品介绍",
    description: "提炼商品卖点、规格、适配场景，辅助售前解释。"
  },
  {
    key: "product_recommend",
    label: "导购推荐",
    description: "根据预算、用途和偏好生成推荐，并说明差异。"
  },
  {
    key: "order_check",
    label: "订单查询",
    description: "查询客户历史订单、商品明细与订单状态。"
  },
  {
    key: "package_track",
    label: "物流跟踪",
    description: "结合订单信息查看包裹轨迹和履约节点。"
  },
  {
    key: "order_refund",
    label: "退款退货",
    description: "核对售后条件，生成退款退货处理建议。"
  }
];

export const SCENARIOS: ScenarioPreset[] = [
  {
    id: "sales",
    label: "售前导购",
    tone: "解释清楚差异，给出可落地推荐。",
    functions: ["product_description", "product_recommend"],
    prompts: [
      "我想买一款支持无线充的车载支架，预算在 150 元以内，适合长途通勤的有哪些？",
      "推荐两款适合夏季通勤、颜值高一点的车内收纳产品。",
      "车载香薰和除味包有什么区别，哪种更适合新车？"
    ]
  },
  {
    id: "order",
    label: "订单查询",
    tone: "先查订单，再解释状态和下一步。",
    functions: ["order_check"],
    prompts: [
      "帮我查一下这个账号之前买过哪些商品。",
      "我想看看账号下所有订单的状态。",
      "帮我查一下腰靠垫这款商品的订单情况。"
    ]
  },
  {
    id: "logistics",
    label: "物流咨询",
    tone: "把当前节点、预计进度和异常处理说清楚。",
    functions: ["order_check", "package_track"],
    prompts: [
      "我之前买的腰靠垫现在送到哪里了？",
      "帮我查一下最近一笔订单的物流进度。",
      "订单还没发货吗？我想知道现在是什么状态。"
    ]
  },
  {
    id: "refund",
    label: "售后退款",
    tone: "先安抚，再核对条件，最后给出处理路径。",
    functions: ["order_check", "order_refund"],
    prompts: [
      "我收到的商品和预期不太一样，想了解一下退货退款流程。",
      "帮我看看这笔订单现在还能不能申请退款。",
      "这个商品我不想要了，想直接发起退款。"
    ]
  }
];

export const DEFAULT_ACCOUNT_ID = "100000";

export const FUNCTION_LABELS = new Map(SUPPORT_FUNCTIONS.map((item) => [item.key, item.label]));
