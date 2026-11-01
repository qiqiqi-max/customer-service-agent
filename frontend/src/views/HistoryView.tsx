import { RotateCcw } from "lucide-react";
import { formatTime } from "../lib/insights";
import type { ConversationSummary } from "../types";

export function HistoryView(props: {
  accountId: string;
  conversations: ConversationSummary[];
  onOpenConversation: (id: string) => void;
  onRefresh: () => void;
  page: number;
  pageSize: number;
  total: number;
  onPage: (page: number) => void;
  onPageSize: (pageSize: number) => void;
}) {
  const pageCount = Math.max(1, Math.ceil(props.total / props.pageSize));
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
        <div className="pagination-bar">
          <span>共 {props.total} 条，第 {props.page} / {pageCount} 页</span>
          <label>
            每页
            <select value={props.pageSize} onChange={(event) => props.onPageSize(Number(event.target.value))}>
              <option value={20}>20 条</option>
              <option value={50}>50 条</option>
            </select>
          </label>
          <button className="secondary-button" disabled={props.page <= 1} onClick={() => props.onPage(props.page - 1)} type="button">上一页</button>
          <button className="secondary-button" disabled={props.page >= pageCount} onClick={() => props.onPage(props.page + 1)} type="button">下一页</button>
        </div>
      </div>
    </section>
  );
}
