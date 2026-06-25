import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class Settings:
    knowledge_path: Path
    app_log_path: Path
    trace_log_path: Path
    llm_mode: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    top_k: int
    min_relevance_score: float


def get_settings() -> Settings:
    load_dotenv(BASE_DIR / ".env")
    log_dir = BASE_DIR / "logs"
    return Settings(
        knowledge_path=BASE_DIR / "knowledge" / "company_knowledge.json",
        app_log_path=log_dir / "app.log",
        trace_log_path=log_dir / "traces.jsonl",
        llm_mode=os.getenv("LLM_MODE", "mock").strip().lower() or "mock",
        llm_base_url=os.getenv("LLM_BASE_URL", "").strip(),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini").strip(),
        top_k=int(os.getenv("TOP_K", "4")),
        min_relevance_score=float(os.getenv("MIN_RELEVANCE_SCORE", "0.18")),
    )
