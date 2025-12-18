from src.config import settings
from src.vendor_processing.ai.llm import get_embedding_client


def embed_text(
    *,
    text: str,
) -> list[float]:
    llm = get_embedding_client(model=settings.EMBEDDING_MODEL)
    return llm.embed_query(text)
