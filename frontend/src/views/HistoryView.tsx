import { RotateCcw } from "lucide-react";
import { formatTime } from "../lib/insights";
import type { ConversationSummary } from "../types";

export function HistoryView(props: {
  accountId: string;
  conversationId: string | null;
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
    <div className="page">
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>历史会话</h2>
            <p>账号 {props.accountId} · 点击一行在接待台中打开</p>
          </div>
          <button className="btn" onClick={props.onRefresh} type="button">
            <RotateCcw size={15} />
            刷新
          </button>
        </div>
        {props.conversations.length ? (
          <table className="data-table">
            <thead>
              <tr>
                <th className="col-title">标题</th>
                <th className="col-last">最近消息</th>
                <th className="col-account">账号</th>
                <th className="col-time">更新时间</th>
              </tr>
            </thead>
            <tbody>
              {props.conversations.map((item) => (
                <tr
                  key={item.id}
                  aria-current={item.id === props.conversationId ? "true" : undefined}
                  onClick={() => props.onOpenConversation(item.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") props.onOpenConversation(item.id);
                  }}
                  tabIndex={0}
                >
                  <td className="col-title">{item.title || "未命名会话"}</td>
                  <td className="col-last">{item.last_message || "暂无消息"}</td>
                  <td className="col-account">{item.account_id || props.accountId}</td>
                  <td className="col-time">{formatTime(item.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="panel-body">
            <p className="empty">这个账号还没有历史会话。</p>
          </div>
        )}
        <div className="pager">
          <span className="pager-info">共 {props.total} 条 · 第 {props.page} / {pageCount} 页</span>
          <label>
            每页{" "}
            <select value={props.pageSize} onChange={(event) => props.onPageSize(Number(event.target.value))}>
              <option value={20}>20 条</option>
              <option value={50}>50 条</option>
            </select>
          </label>
          <button className="btn sm" disabled={props.page <= 1} onClick={() => props.onPage(props.page - 1)} type="button">
            上一页
          </button>
          <button className="btn sm" disabled={props.page >= pageCount} onClick={() => props.onPage(props.page + 1)} type="button">
            下一页
          </button>
        </div>
      </section>
    </div>
  );
}
