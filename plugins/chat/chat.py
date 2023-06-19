import os
import typing
from typing import List, Optional, Sequence

import openai
from langchain.agents import AgentExecutor, Tool, load_tools
from langchain.agents.chat.base import ChatAgent
from langchain.agents.chat.prompt import (
    FORMAT_INSTRUCTIONS,
    HUMAN_MESSAGE,
    SYSTEM_MESSAGE_PREFIX,
    SYSTEM_MESSAGE_SUFFIX,
)
from langchain.chat_models import ChatOpenAI
from langchain.prompts.base import BasePromptTemplate
from langchain.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain.tools.base import BaseTool
from langchain.utilities import SerpAPIWrapper
from loguru import logger

from plana import Plugin
from plana.messages import BaseMessage, GroupMessage, PrivateMessage

translate_template = """Translated the following text into {language}.
```{text}```
"""


class CustomChatAgent(ChatAgent):
    @classmethod
    def create_prompt(
        cls,
        tools: Sequence[BaseTool],
        system_message_prefix: str = SYSTEM_MESSAGE_PREFIX,
        system_message_suffix: str = SYSTEM_MESSAGE_SUFFIX,
        human_message: str = HUMAN_MESSAGE,
        format_instructions: str = FORMAT_INSTRUCTIONS,
        input_variables: Optional[List[str]] = None,
    ) -> BasePromptTemplate:
        tool_strings = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
        tool_names = ", ".join([tool.name for tool in tools])
        format_instructions = format_instructions.format(tool_names=tool_names)
        template = "\n\n".join(
            [
                system_message_prefix,
                tool_strings,
                format_instructions,
                system_message_suffix,
                human_message,
            ]
        )
        messages = [
            # SystemMessagePromptTemplate.from_template(template),
            HumanMessagePromptTemplate.from_template(template),
        ]
        if input_variables is None:
            input_variables = ["input", "agent_scratchpad"]
        return ChatPromptTemplate(input_variables=input_variables, messages=messages)  # type: ignore  # noqa: E501


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

        self.agent = AgentExecutor.from_agent_and_tools(
            agent=CustomChatAgent.from_llm_and_tools(llm, tools, callback_manager=None),
            tools=tools,
            callback_manager=None,
            verbose=True,
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
