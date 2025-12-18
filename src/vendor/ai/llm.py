from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def get_llm_client(*, model: str = "gpt-4o-mini") -> ChatOpenAI:
    return ChatOpenAI(model=model)


def get_embedding_client(*, model: str = "text-embedding-3-small") -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=model)
