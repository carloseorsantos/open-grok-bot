import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Carregar variáveis do .env caso exista
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()
    
    # Groq (Default free provider)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    # Ollama (Local)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # OpenAI / Compatible
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ALLOWED_USERS: str = os.getenv("TELEGRAM_ALLOWED_USERS", "")

    # Browser
    BROWSER_HEADLESS: bool = os.getenv("BROWSER_HEADLESS", "true").lower() in ("true", "1", "yes")
    BROWSER_TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", "30000"))

    # Paths
    DATABASE_PATH: Path = BASE_DIR / os.getenv("DATABASE_PATH", "data/open_grok.db")
    WORKSPACE_DIR: Path = BASE_DIR / os.getenv("WORKSPACE_DIR", "workspace_output")
    SCREENSHOTS_DIR: Path = BASE_DIR / "screenshots"

    def __post_init__(self):
        # Garantir diretórios necessários
        self.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        self.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def allowed_telegram_ids(self) -> list[int]:
        if not self.TELEGRAM_ALLOWED_USERS:
            return []
        ids = []
        for item in self.TELEGRAM_ALLOWED_USERS.split(","):
            item = item.strip()
            if item.isdigit():
                ids.append(int(item))
        return ids


settings = Settings()
