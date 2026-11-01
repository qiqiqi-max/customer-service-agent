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
    <section className="page-grid">
      <div className="surface ops">
        <div className="section-head">
          <div>
            <span className="eyebrow">复盘</span>
            <h2>会话总结</h2>
          </div>
          <button className="secondary-button" onClick={props.onSummary} type="button">
            <FileText size={16} />
            生成
          </button>
        </div>
        <pre className="output-box">{props.summary}</pre>
      </div>

      <div className="surface ops">
        <div className="section-head">
          <div>
            <span className="eyebrow">质检</span>
            <h2>回复质检</h2>
          </div>
          <button className="secondary-button" onClick={props.onQuality} type="button">
            <Gauge size={16} />
            检查
          </button>
        </div>
        <label className="field">
          <span>质检关键词</span>
          <input value={props.qualityKeywords} onChange={(event) => props.onKeywords(event.target.value)} />
        </label>
        <pre className="output-box">{props.quality}</pre>
      </div>

      <div className="surface ops wide">
        <div className="section-head">
          <div>
            <span className="eyebrow">知识沉淀</span>
            <h2>FAQ 沉淀</h2>
          </div>
          <button className="primary-button" onClick={props.onSaveFaq} type="button">
            <Archive size={16} />
            保存
          </button>
        </div>
        <label className="field">
          <span>满意度评分：{props.faqScore}</span>
          <div className="score-options" role="radiogroup" aria-label="满意度评分">
            {[1, 2, 3, 4, 5].map((score) => (
              <button
                aria-checked={props.faqScore === score}
                className={props.faqScore === score ? "score-option is-selected" : "score-option"}
                key={score}
                onClick={() => props.onFaqScore(score)}
                role="radio"
                type="button"
              >
                {score}
              </button>
            ))}
          </div>
        </label>
        <pre className="output-box">{props.faqResult}</pre>
      </div>

      <div className="surface ops wide">
        <div className="section-head"><div><span className="eyebrow">历史记录</span><h2>最近质检</h2></div></div>
        {props.qualityReviews.length ? props.qualityReviews.slice(0, 8).map((item) => (
          <div className="record-row" key={item.id}>
            <strong>{item.structured_result?.risk_level ?? "未评级"}</strong>
            <span>{item.result || item.content || "无内容"}</span>
          </div>
        )) : <p className="muted">暂无历史质检记录</p>}
      </div>

      <div className="surface ops wide">
        <div className="section-head"><div><span className="eyebrow">知识审核</span><h2>FAQ 候选</h2></div></div>
        {props.faqCandidates.length ? props.faqCandidates.slice(0, 8).map((item) => (
          <div className="record-row" key={item.id}>
            <strong>{item.status ?? "待处理"}</strong>
            <span>{item.question || "未命名问题"}</span>
          </div>
        )) : <p className="muted">暂无 FAQ 候选</p>}
      </div>
    </section>
  );
}
