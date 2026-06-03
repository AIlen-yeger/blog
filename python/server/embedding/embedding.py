import httpx

from langchain_openai import OpenAIEmbeddings

from config.config import AgentConfig


def openai_sync_http_client(timeout: float = 120.0) -> httpx.Client:
    """
    trust_env=False：不读取 HTTP_PROXY/HTTPS_PROXY。
    常见报错 EOF occurred in violation of protocol 多由错误代理在 TLS 握手时截断导致。
    """
    return httpx.Client(trust_env=False, timeout=timeout)

class EmbeddingClient:
    def __init__(self):
        config = AgentConfig()
        self.model_name = config.embedding_model_name
        self.embedder = OpenAIEmbeddings(
            model=self.model_name,
            api_key=config.embedding_api_key,
            base_url=config.embedding_base_url,
            http_client=openai_sync_http_client(),
            check_embedding_ctx_length=False,
            tiktoken_enabled=False,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        #调用embedder的向量化方法处理得到向量
        return self.embedder.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.embedder.embed_query(text or "")