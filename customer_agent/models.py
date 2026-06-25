from dataclasses import dataclass


@dataclass
class KnowledgeItem:
    id: str
    category: str
    title: str
    content: str
    quote: str
    keywords: list[str]
    source_path: str


@dataclass
class RetrievalResult:
    item: KnowledgeItem
    score: float
    matched_terms: list[str]
