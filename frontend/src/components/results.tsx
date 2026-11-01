import { useState } from "react";
import { formatValue } from "../lib/insights";
import type { ExecutionRecord, RefundAction, RefundRecord, ResultCard } from "../types";

export function TraceList({ records }: { records: ExecutionRecord[] }) {
  return records.length ? (
    <div className="trace-list">
      {records.map((item) => (
        <article key={item.id} className="trace-item">
          <strong>{item.tool}</strong>
          <span>{item.action}</span>
          <pre>{formatValue(item.output)}</pre>
        </article>
      ))}
    </div>
  ) : <p className="empty">暂无工具调用。</p>;
}

export function ResultList({
  cards,
  onAction
}: {
  cards: ResultCard[];
  onAction: (refundId: string, action: RefundAction) => Promise<void>;
}) {
  return cards.length ? (
    <div className="result-list">
      {cards.map((card) => (
        <article key={card.id} className="result-card">
          <strong>{card.title}</strong>
          <span>{card.type}</span>
          {card.status && <span className={`refund-status is-${card.status}`}>{refundStatusLabel(card.status)}</span>}
          {card.fields.slice(0, 4).map((field) => (
            <p key={field.label}><b>{field.label}</b>{field.value}</p>
          ))}
          {card.type === "退款退货" && <RefundActors card={card} />}
          {card.type === "退款退货" && <RefundActions card={card} onAction={onAction} />}
        </article>
      ))}
    </div>
  ) : <p className="empty">暂无工单结果。</p>;
}

function RefundActors({ card }: { card: ResultCard }) {
  const raw = card.raw && typeof card.raw === "object" ? card.raw as RefundRecord : null;
  const actors = [
    ["审批人", raw?.approved_by],
    ["拒绝人", raw?.rejected_by],
    ["执行人", raw?.executed_by]
  ].filter(([, value]) => value);
  return actors.length ? (
    <>
      {actors.map(([label, value]) => (
        <p key={label}><b>{label}</b>{value}</p>
      ))}
    </>
  ) : null;
}

function RefundActions({
  card,
  onAction
}: {
  card: ResultCard;
  onAction: (refundId: string, action: RefundAction) => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const raw = card.raw && typeof card.raw === "object" ? card.raw as RefundRecord : null;
  const refundId = raw?.refund_id || raw?.id;
  if (!refundId || !card.status || ["executed", "rejected"].includes(card.status)) return null;
  const resolvedRefundId = refundId;

  async function run(action: RefundAction) {
    setBusy(true);
    try {
      await onAction(resolvedRefundId, action);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="refund-actions">
      {card.status === "pending_approval" && (
        <>
          <button className="secondary-button" disabled={busy} onClick={() => run("reject")} type="button">拒绝</button>
          <button className="primary-button" disabled={busy} onClick={() => run("approve")} type="button">批准退款</button>
        </>
      )}
      {card.status === "approved" && (
        <button className="primary-button" disabled={busy} onClick={() => run("execute")} type="button">执行退款</button>
      )}
    </div>
  );
}

function refundStatusLabel(status: string) {
  return {
    pending_approval: "待人工确认",
    approved: "已批准，待执行",
    executed: "退款已完成",
    rejected: "已拒绝",
    failed: "执行失败"
  }[status] || status;
}
