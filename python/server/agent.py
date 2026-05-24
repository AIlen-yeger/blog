import os
from os import system
from typing import Any

from config.config import AgentConfig
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from database.mysql_db import MysqlRepo
from utils.path_tools import get_abs_path


class ChatModel:
    def __init__(self):
        config = AgentConfig()
        self.model = os.getenv("MODEL")
        self.api_key = os.getenv("API_KEY")
        self.api_url = os.getenv("API_URL")
        self.temperature = config.get("temperature")
        self.chat_llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            api_url=self.api_url,
            temperature=self.temperature,
        )
        self.mysql_db = MysqlRepo()


    def chat(self,question:str,session_id:str,user_id:int,limit:int=5):
         """获取历史记录和提示词模板"""

         prompt_path = get_abs_path("prompt/system_prompt")
         with open(prompt_path, "r") as f:
             system_prompt = f.read()

         history_message = self.mysql_db.get_recent_history(session_id=session_id,user_id=user_id, limit=limit)

         messages = [
             SystemMessage(content=system_prompt),
             *self._to_lc_messages(history_message),
             HumanMessage(content=question),
         ]

         full_answer = []
         for chunk in self.chat_llm.stream(messages=messages):
             content = chunk.content
             if isinstance(content,str):
                 delta = content
             elif isinstance(content,list):
                 delta = "".join(
                     str(item.get("text", "")) for item in content if isinstance(item, dict)
                 )
             else:
                 delta = ""

             if delta:
                 full_answer.append(delta)
                 yield {"type": "delta", "content": delta}

         answer = "".join(full_answer).strip()

         self.mysql_db.save_turn(
             session_id=session_id,
             user_question=question,
             assistant_answer=answer,
         )

    @staticmethod
    def _to_lc_messages(history_messages: list[dict[str, str]]) -> list[Any]:
        lc_messages: list[Any] = []
        for m in history_messages:
            role = (m.get("role") or "").strip().lower()
            content = (m.get("content") or "").strip()
            if not content:
                continue
            if role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        return lc_messages

