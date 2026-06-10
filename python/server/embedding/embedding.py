import logging

import httpx

from langchain_openai import OpenAIEmbeddings

from config.config import AgentConfig, embedding_configured

logger = logging.getLogger(__name__)


def openai_sync_http_client(timeout: float = 120.0) -> httpx.Client:
    """
    trust_env=False：不读取 HTTP_PROXY/HTTPS_PROXY。
    常见报错 EOF occurred in violation of protocol 多由错误代理在 TLS 握手时截断导致。
    """
    return httpx.Client(trust_env=False, timeout=timeout)


def _normalize_embedding_base_url(url: str) -> str:
    base = (url or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/v1"):
        return base
    return base + "/v1"


class EmbeddingClient:
    def __init__(self) -> None:
        config = AgentConfig()
        self.model_name = (config.embedding_model_name or "").strip()
        self._ready = embedding_configured(config)
        self.embedder: OpenAIEmbeddings | None = None
        if self._ready:
            self.embedder = OpenAIEmbeddings(
                model=self.model_name,
                api_key=config.embedding_api_key,
                base_url=_normalize_embedding_base_url(config.embedding_base_url),
                http_client=openai_sync_http_client(),
                check_embedding_ctx_length=False,
                tiktoken_enabled=False,
            )
        else:
            logger.debug(
                "[embedding] disabled: set EMBEDDING_MODEL_NAME / EMBEDDING_API_KEY / EMBEDDING_BASE_URL"
            )

    @property
    def ready(self) -> bool:
        return self._ready and self.embedder is not None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts or not self.embedder:
            return []
        return self.embedder.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        if not self.embedder:
            return []
        return self.embedder.embed_query(text or "")
