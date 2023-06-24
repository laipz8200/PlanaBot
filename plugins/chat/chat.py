import httpx
import openai
from loguru import logger
from openai_agent.completions import get_function_completion
from openai_agent.functions import Function
from openai_agent.messages import Message, UserMessage

from plana import Plugin
from plana.messages import BaseMessage, GroupMessage, PrivateMessage


def get(url: str) -> str:
    """Get text from url.

    :param url: URL
    """
    return httpx.get(url).text


functions = [Function.load_from_func(get)]


class Chat(Plugin):
    prefix: str = "#chat"
    openai_api_key: str = ""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        openai.api_key = self.openai_api_key

    async def on_group(self, message: GroupMessage) -> None:
        if not message.at_bot():
            return
        await self._chat(message)

    async def on_private_prefix(self, message: PrivateMessage) -> None:
        await self._chat(message)

    async def on_group_prefix(self, message: GroupMessage) -> None:
        await self._chat(message)

    async def _chat(self, message: BaseMessage) -> None:
        question = message.plain_text()
        messages: list[Message] = [UserMessage(content=question)]
        try:
            response = get_function_completion(
                model="gpt-3.5-turbo-16k-0613",
                messages=messages,
                functions=functions,
            )
            await message.reply(response.content)
        except Exception as e:
            logger.warning(f"failed to run agent: {e}")
            await message.reply("出错啦，请稍后再试")
