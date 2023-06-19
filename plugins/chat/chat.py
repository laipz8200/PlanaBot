import os
import typing
from typing import Any, List, Optional, Sequence

import openai
from langchain.agents import Agent, AgentExecutor, AgentOutputParser, Tool, load_tools
from langchain.agents.chat.base import ChatAgent
from langchain.base_language import BaseLanguageModel
from langchain.callbacks.base import BaseCallbackManager
from langchain.chains.llm import LLMChain
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

SYSTEM_MESSAGE_PREFIX = """Answer the following questions **IN CHINESE** as best you can. You have access to the following tools:"""  # noqa: E501
FORMAT_INSTRUCTIONS = """The way you use the tools is by specifying a json blob.
Specifically, this json should have a `action` key (with the name of the tool to use) and a `action_input` key (with the input to the tool going here).

The only values that should be in the "action" field are: {tool_names}

The $JSON_BLOB MUST only contain a SINGLE action, do NOT return a list of multiple actions. Here is an example of a valid $JSON_BLOB:

```
{{{{
  "action": $TOOL_NAME,
  "action_input": $INPUT
}}}}
```

ALWAYS use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action:
```
$JSON_BLOB
```
Observation: the result of the action
... (this Thought/Action/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question"""  # noqa: E501
SYSTEM_MESSAGE_SUFFIX = """\nBegin! Reminder to always answer in Chinese and use the exact characters `Final Answer` when responding."""  # noqa: E501
HUMAN_MESSAGE = "{input}\n\n{agent_scratchpad}"


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

    @classmethod
    def from_llm_and_tools(
        cls,
        llm: BaseLanguageModel,
        tools: Sequence[BaseTool],
        callback_manager: Optional[BaseCallbackManager] = None,
        output_parser: Optional[AgentOutputParser] = None,
        system_message_prefix: str = SYSTEM_MESSAGE_PREFIX,
        system_message_suffix: str = SYSTEM_MESSAGE_SUFFIX,
        human_message: str = HUMAN_MESSAGE,
        format_instructions: str = FORMAT_INSTRUCTIONS,
        input_variables: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Agent:
        """Construct an agent from an LLM and tools."""
        cls._validate_tools(tools)
        prompt = cls.create_prompt(
            tools,
            system_message_prefix=system_message_prefix,
            system_message_suffix=system_message_suffix,
            human_message=human_message,
            format_instructions=format_instructions,
            input_variables=input_variables,
        )
        llm_chain = LLMChain(
            llm=llm,
            prompt=prompt,
            callback_manager=callback_manager,
        )
        tool_names = [tool.name for tool in tools]
        _output_parser = output_parser or cls._get_default_output_parser()
        return cls(
            llm_chain=llm_chain,
            allowed_tools=tool_names,
            output_parser=_output_parser,
            **kwargs,
        )


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
            description="一个搜索引擎。当您需要回答有关当前事件的问题时非常有用。输入应该是一组关键词。",  # noqa: E501
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
        question = message.plain_text()
        try:
            response = self.agent.run(question)
            await message.reply(response)
        except Exception as e:
            logger.warning(f"failed to run agent: {e}")
            await message.reply("出错啦，请稍后再试")
