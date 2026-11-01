import { Archive, FileText, Gauge } from "lucide-react";
import type { FAQCandidateRecord, QualityReviewRecord } from "../types";

export function QualityView(props: {
  faqResult: string;
  faqScore: number;
  quality: string;
  qualityKeywords: string;
  summary: string;
  onFaqScore: (value: number) => void;
  onKeywords: (value: string) => void;
  onQuality: () => void;
  onSaveFaq: () => void;
  onSummary: () => void;
  qualityReviews: QualityReviewRecord[];
  faqCandidates: FAQCandidateRecord[];
}) {
  return (
    <div className="page">
      <div className="split">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>会话总结</h2>
              <p>基于当前接待台的对话生成</p>
            </div>
            <button className="btn" onClick={props.onSummary} type="button">
              <FileText size={15} />
              生成
            </button>
          </div>
          <div className="panel-body">
            <pre className="output-box">{props.summary}</pre>
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>回复质检</h2>
              <p>检查回复中是否命中风险关键词</p>
            </div>
            <button className="btn" onClick={props.onQuality} type="button">
              <Gauge size={15} />
              检查
            </button>
          </div>
          <div className="panel-body">
            <label className="field">
              <span>质检关键词</span>
              <input value={props.qualityKeywords} onChange={(event) => props.onKeywords(event.target.value)} />
            </label>
            <pre className="output-box">{props.quality}</pre>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>FAQ 沉淀</h2>
            <p>把最近一轮客户问题和助手回复保存为 FAQ 候选</p>
          </div>
          <button className="btn primary" onClick={props.onSaveFaq} type="button">
            <Archive size={15} />
            保存
          </button>
        </div>
        <div className="panel-body">
          <div className="field">
            <span id="faq-score-label">满意度评分：{props.faqScore}</span>
            <div className="score-row" role="radiogroup" aria-labelledby="faq-score-label">
              {[1, 2, 3, 4, 5].map((score) => (
                <button
                  aria-checked={props.faqScore === score}
                  className={props.faqScore === score ? "score-btn is-selected" : "score-btn"}
                  key={score}
                  onClick={() => props.onFaqScore(score)}
                  role="radio"
                  type="button"
                >
                  {score}
                </button>
              ))}
            </div>
          </div>
          <pre className="output-box">{props.faqResult}</pre>
        </div>
      </section>

      <div className="split">
        <section className="panel">
          <div className="panel-head">
            <h2>最近质检</h2>
            <span className="badge">{props.qualityReviews.length}</span>
          </div>
          {props.qualityReviews.length ? (
            <div className="record-list">
              {props.qualityReviews.slice(0, 8).map((item) => (
                <div className="record-row" key={item.id}>
                  <strong>{item.structured_result?.risk_level ?? "未评级"}</strong>
                  <span title={item.result || item.content}>{item.result || item.content || "无内容"}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="panel-body"><p className="empty">暂无历史质检记录。</p></div>
          )}
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>FAQ 候选</h2>
            <span className="badge">{props.faqCandidates.length}</span>
          </div>
          {props.faqCandidates.length ? (
            <div className="record-list">
              {props.faqCandidates.slice(0, 8).map((item) => (
                <div className="record-row" key={item.id}>
                  <strong>{item.status ?? "待处理"}</strong>
                  <span title={item.question}>{item.question || "未命名问题"}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="panel-body"><p className="empty">暂无 FAQ 候选。</p></div>
          )}
        </section>
      </div>
    </div>
  );
}
