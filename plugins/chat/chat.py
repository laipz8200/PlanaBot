import openai
from loguru import logger

from plana import GroupMessage, Plugin

from .utils import get_completion


class Chat(Plugin):
    prefix: str = "#chat"
    openai_api_key: str = ""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        openai.api_key = self.openai_api_key

    async def on_group_prefix(self, group_message: GroupMessage) -> None:
        prompt = group_message.plain_text()
        logger.debug(f"[Chat] {prompt=}")
        response = await get_completion(prompt)
        logger.debug(f"[Chat] {response=}")
        await group_message.reply(response)
