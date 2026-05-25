from langchain_openai import OpenAI, OpenAIEmbeddings

from config.config import AgentConfig
import os

class Embedding:
    def __init__(self):
        config = AgentConfig()
        self.model = config.embedding_model_name
        self.embedder = OpenAIEmbeddings(
            model=self.model,
            api_key=os.getenv("api_key"),
            base_url=os.getenv("base_url"),
            check_embedding_ctx_length=False,
            tiktoken_enabled=False,
        )


    def embedding_text(self,text:list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(text)

    def embedding_query(self,text:str) -> list[float]:
        return self.embedder.embed_query(text)
