import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    whatsapp_token: str
    phone_number_id: str
    recipient_number: str
    arxiv_categories: tuple[str, ...] = (
        "cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.RO", "cs.NE"
    )
    max_papers: int = 3
    summary_max_words: int = 120
    whatsapp_max_message_length: int = 4096
    gemini_model: str = "gemini-2.0-flash"
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 2.0

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            whatsapp_token=os.getenv("WHATSAPP_TOKEN"),
            phone_number_id=os.getenv("PHONE_NUMBER_ID"),
            recipient_number=os.getenv("RECIPIENT_NUMBER"),
        )
