"""Fixed and environment-backed configuration for DATA 260 Homework 6."""

from dataclasses import dataclass
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def env_bool(name: str, default: bool) -> bool:
    """Read a conservative boolean environment setting."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    sid4: str = "0686"
    port_base: int = 8686
    prefix: str = "s0686"
    seed: int = 686
    verify_seed: int = 260686
    domain_id: int = 6
    domain: str = "Rental Housing Listings"
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "s0686_doc")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
    short_term_n: int = int(os.getenv("SHORT_TERM_N", "12"))
    summarize_every_user_msgs: int = int(os.getenv("SUMMARIZE_EVERY_USER_MSGS", "5"))
    episodic_top_k: int = int(os.getenv("EPISODIC_TOP_K", "3"))
    file_memory_enabled: bool = env_bool("FILE_MEMORY_ENABLED", True)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


settings = Settings()
