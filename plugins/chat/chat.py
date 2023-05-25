import openai
from loguru import logger

from plana import Plugin
from plana.messages import BaseMessage, GroupMessage, PrivateMessage

from .utils import get_completion


class Chat(Plugin):
    prefix: str = "#chat"
    openai_api_key: str = ""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        openai.api_key = self.openai_api_key

    async def on_private_prefix(self, message: PrivateMessage) -> None:
        await self._chat(message)

    async def on_group_prefix(self, message: GroupMessage) -> None:
        await self._chat(message)

    async def _chat(self, message: BaseMessage) -> None:
        prompt = message.plain_text()
        logger.debug(f"[Chat] {prompt=}")
        response = await get_completion(prompt)
        logger.debug(f"[Chat] {response=}")
        await message.reply(response)
