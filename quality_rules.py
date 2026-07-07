import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class QualityRule:
    rule_id: str
    category: str
    severity: str
    keywords: tuple[str, ...]
    description: str
    suggestion: str


SEVERITY_SCORES = {
    "high": 90,
    "medium": 65,
    "low": 35,
}


QUALITY_RULES = (
    QualityRule(
        rule_id="absolute_language",
        category="绝对化表达",
        severity="high",
        keywords=("绝对", "全网最低", "第一", "唯一", "100%", "百分百", "最便宜"),
        description="客服回复中出现绝对化或无法证明的极限表达。",
        suggestion="改成可验证、留有余地的表达，例如“价格有竞争力”或“多数用户反馈较好”。",
    ),
    QualityRule(
        rule_id="guarantee_promise",
        category="过度承诺",
        severity="high",
        keywords=("保证", "肯定", "一定能", "无效退款", "包退", "包治"),
        description="客服回复中出现确定性承诺，可能带来履约或合规风险。",
        suggestion="改成基于规则或事实的说明，例如“符合平台规则时可申请售后”。",
    ),
    QualityRule(
        rule_id="exaggerated_effect",
        category="功效夸大",
        severity="high",
        keywords=("立刻见效", "根治", "治愈", "瘦 20 斤", "瘦20斤", "永久有效"),
        description="客服回复中出现夸大商品功效或结果的表达。",
        suggestion="改成客观描述商品功能，并引导用户参考详情页、质检报告或真实评价。",
    ),
    QualityRule(
        rule_id="rude_language",
        category="服务态度",
        severity="high",
        keywords=("爱买不买", "不买拉倒", "tmd", "滚", "闭嘴", "烦死了"),
        description="客服回复中出现不礼貌、攻击性或明显不专业表达。",
        suggestion="改成礼貌、克制、可继续沟通的表达。",
    ),
    QualityRule(
        rule_id="privacy_risk",
        category="隐私安全",
        severity="medium",
        keywords=("验证码", "支付密码", "银行卡密码", "身份证照片", "完整身份证号"),
        description="客服回复中可能引导用户提供敏感隐私或支付安全信息。",
        suggestion="仅收集业务必要信息，避免要求用户提供密码、验证码等敏感凭证。",
    ),
    QualityRule(
        rule_id="refund_policy",
        category="售后合规",
        severity="medium",
        keywords=("概不退换", "不给退", "不能退", "不支持售后"),
        description="客服回复中出现过于绝对的售后拒绝，可能与平台规则冲突。",
        suggestion="改成按订单状态、商品类目和平台规则核验后再给出处理结论。",
    ),
)


def inspect_quality_text(content: str, extra_keywords: str | None = None) -> dict:
    hits = []
    for rule in QUALITY_RULES:
        hits.extend(_find_rule_hits(content, rule))

    for keyword in _parse_extra_keywords(extra_keywords):
        hits.extend(_find_custom_keyword_hits(content, keyword))

    hits = sorted(
        _dedupe_hits(hits),
        key=lambda hit: (
            -SEVERITY_SCORES.get(hit["severity"], 0),
            hit["start"],
            hit["keyword"],
        ),
    )
    risk_score = _risk_score(hits)
    return {
        "risk_level": _risk_level(risk_score),
        "risk_score": risk_score,
        "hit_count": len(hits),
        "hits": hits,
        "suggestions": _suggestions(hits),
    }


def _find_rule_hits(content: str, rule: QualityRule) -> list[dict]:
    hits = []
    for keyword in rule.keywords:
        for start, end in _find_keyword_spans(content, keyword):
            hits.append(
                {
                    "rule_id": rule.rule_id,
                    "category": rule.category,
                    "severity": rule.severity,
                    "keyword": keyword,
                    "start": start,
                    "end": end,
                    "evidence": content[start:end],
                    "description": rule.description,
                    "suggestion": rule.suggestion,
                }
            )
    return hits


def _find_custom_keyword_hits(content: str, keyword: str) -> list[dict]:
    return [
        {
            "rule_id": "custom_keyword",
            "category": "自定义质检词",
            "severity": "medium",
            "keyword": keyword,
            "start": start,
            "end": end,
            "evidence": content[start:end],
            "description": "命中用户本次指定的质检关键词。",
            "suggestion": "结合业务规则复核该表达是否需要替换或升级人工处理。",
        }
        for start, end in _find_keyword_spans(content, keyword)
    ]


def _find_keyword_spans(content: str, keyword: str) -> Iterable[tuple[int, int]]:
    if not content or not keyword:
        return []

    lowered_content = content.lower()
    lowered_keyword = keyword.lower()
    spans = []
    start = 0
    while True:
        index = lowered_content.find(lowered_keyword, start)
        if index == -1:
            break
        spans.append((index, index + len(keyword)))
        start = index + max(len(keyword), 1)
    return spans


def _parse_extra_keywords(value: str | None) -> list[str]:
    if not value:
        return []
    return [
        item.strip()
        for item in re.split(r"[,，;；、\n\r\t]+", value)
        if item.strip()
    ]


def _dedupe_hits(hits: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for hit in hits:
        key = (hit["keyword"].lower(), hit["start"], hit["end"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(hit)
    return deduped


def _risk_score(hits: list[dict]) -> int:
    if not hits:
        return 0
    base = max(SEVERITY_SCORES.get(hit["severity"], 0) for hit in hits)
    return min(100, base + max(0, len(hits) - 1) * 3)


def _risk_level(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def _suggestions(hits: list[dict]) -> list[str]:
    suggestions = []
    for hit in hits:
        suggestion = hit["suggestion"]
        if suggestion not in suggestions:
            suggestions.append(suggestion)
    return suggestions
