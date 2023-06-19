import os
import typing

import openai
from langchain.agents import (
    AgentExecutor,
    AgentType,
    Tool,
    initialize_agent,
    load_tools,
)
from langchain.chat_models import ChatOpenAI
from langchain.utilities import SerpAPIWrapper
from loguru import logger

from plana import Plugin
from plana.messages import BaseMessage, GroupMessage, PrivateMessage

translate_template = """Translated the following text into {language}.
```{text}```
"""


class Chat(Plugin):
    prefix: str = "#chat"
    openai_api_key: str = ""
    serp_api_key: str = ""
    agent: typing.Any | AgentExecutor = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        openai.api_key = self.openai_api_key
        os.environ["SERPAPI_API_KEY"] = self.serp_api_key

        llm = ChatOpenAI(
            model="gpt-3.5-turbo-16k",
            temperature=0.0,
            openai_api_key=self.openai_api_key,
        )  # type: ignore

        tools = load_tools(["python_repl", "requests_all", "llm-math"], llm=llm)
        params = {"engine": "google", "gl": "us", "hl": "zh-cn"}
        search = SerpAPIWrapper(params=params)  # type: ignore
        search_tool = Tool(
            name="Search",
            description="A search engine. Useful for when you need to answer questions about current events. Input should be a search query.",  # noqa: E501
            func=search.run,
            coroutine=search.arun,
        )
        tools.append(search_tool)

        self.agent = initialize_agent(
            tools, llm, agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION, verbose=True
        )

    async def on_private_prefix(self, message: PrivateMessage) -> None:
        await self._chat(message)

    async def on_group_prefix(self, message: GroupMessage) -> None:
        await self._chat(message)

    async def _chat(self, message: BaseMessage) -> None:
        prompt = "请用中文回答: " + message.plain_text()
        try:
            response = self.agent.run(prompt)
            await message.reply(response)
        except Exception as e:
            logger.warning(f"failed to run agent: {e}")
            await message.reply("出错啦，请稍后再试")
