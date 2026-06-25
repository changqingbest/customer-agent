import json
import re
from pathlib import Path

from customer_agent.models import KnowledgeItem, RetrievalResult


TOKEN_RE = re.compile(r"[a-z0-9\-\+\.]+", re.IGNORECASE)
STOPWORDS = {"a", "an", "the", "to", "of", "for", "and", "or", "can", "you", "we", "is", "are", "with", "my"}


def tokenize(text: str) -> set[str]:
    lower = text.lower()
    tokens = {token for token in TOKEN_RE.findall(lower) if token not in STOPWORDS}
    phrase_map = {
        "stainless steel": "stainless steel",
        "surface treatment": "surface treatment",
        "lead time": "lead time",
        "how to buy": "how to buy",
        "metal bracket": "bracket",
        "支架": "bracket",
        "金属支架": "bracket",
        "图纸": "drawing",
        "样品": "sample",
        "按图": "drawing",
        "定制": "custom",
        "不锈钢": "stainless steel",
        "铝合金": "aluminum",
        "起订量": "moq",
        "报价": "quotation",
        "价格": "quotation",
        "交期": "lead time",
        "物流": "shipping",
        "运费": "shipping",
        "海运": "shipping",
        "空运": "shipping",
        "快递": "shipping",
        "发德国": "shipping",
        "怎么购买": "how to buy",
        "怎么买": "how to buy",
        "怎么选": "how to choose",
        "主要产品": "products",
        "做什么产品": "products",
        "外壳": "enclosure",
        "机箱": "enclosure",
        "售后": "support",
        "退换": "support",
        "尺寸不对": "support",
    }
    for phrase, mapped in phrase_map.items():
        if phrase in lower or phrase in text:
            tokens.add(mapped)
    return tokens


class KnowledgeBase:
    def __init__(self, knowledge_path: Path):
        raw_items = json.loads(knowledge_path.read_text(encoding="utf-8"))
        self.items = [
            KnowledgeItem(
                id=item["id"],
                category=item["category"],
                title=item["title"],
                content=item["content"],
                quote=item["quote"],
                keywords=item.get("keywords", []),
                source_path=knowledge_path.name,
            )
            for item in raw_items
        ]

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        query_tokens = tokenize(query)
        results: list[RetrievalResult] = []
        for item in self.items:
            item_tokens = tokenize(" ".join([item.title, item.content, item.quote, *item.keywords]))
            matched = sorted(query_tokens & item_tokens)
            keyword_bonus = sum(0.08 for keyword in item.keywords if keyword.lower() in query.lower() or keyword in query)
            score = min(len(matched) / max(len(query_tokens), 1) + keyword_bonus, 1.0)
            if score > 0:
                results.append(RetrievalResult(item=item, score=score, matched_terms=matched))
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]
