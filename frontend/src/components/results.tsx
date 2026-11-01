import { useState } from "react";
import { formatValue } from "../lib/insights";
import type { ExecutionRecord, RefundAction, RefundRecord, ResultCard } from "../types";

export function TraceList({ records }: { records: ExecutionRecord[] }) {
  return records.length ? (
    <div className="trace-list">
      {records.map((item) => (
        <details key={item.id} className="trace-item">
          <summary>
            <strong>{item.tool}</strong>
            <span>{item.action}</span>
          </summary>
          <pre>{formatValue(item.output)}</pre>
        </details>
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
          <div className="result-card-head">
            <div>
              <strong>{card.title}</strong>
              <small>{card.type}</small>
            </div>
            {card.status && (
              <span className={`refund-status is-${card.status}`}>{refundStatusLabel(card.status)}</span>
            )}
          </div>
          <dl className="kv">
            {card.fields.slice(0, 4).map((field) => (
              <KeyValue key={field.label} label={field.label} value={field.value} />
            ))}
            {card.type === "退款退货" && <RefundActors card={card} />}
          </dl>
          {card.type === "退款退货" && <RefundActions card={card} onAction={onAction} />}
        </article>
      ))}
    </div>
  ) : <p className="empty">暂无工单结果。</p>;
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  );
}

function RefundActors({ card }: { card: ResultCard }) {
  const raw = card.raw && typeof card.raw === "object" ? card.raw as RefundRecord : null;
  const actors = [
    ["审批人", raw?.approved_by],
    ["拒绝人", raw?.rejected_by],
    ["执行人", raw?.executed_by]
  ].filter((item): item is [string, string] => Boolean(item[1]));
  return (
    <>
      {actors.map(([label, value]) => (
        <KeyValue key={label} label={label} value={value} />
      ))}
    </>
  );
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
          <button className="btn sm" disabled={busy} onClick={() => run("reject")} type="button">拒绝</button>
          <button className="btn sm primary" disabled={busy} onClick={() => run("approve")} type="button">批准退款</button>
        </>
      )}
      {card.status === "approved" && (
        <button className="btn sm primary" disabled={busy} onClick={() => run("execute")} type="button">执行退款</button>
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
