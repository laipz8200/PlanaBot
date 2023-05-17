import openai

from plana import GroupMessage, Plugin
from plugins.chat.utils import get_completion


class Chat(Plugin):
    prefix: str = "#chat"
    openai_api_key: str = ""
    enabled_groups: set[int] = set()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.enabled_groups = set(self.config.allowed_groups)
        openai.api_key = self.openai_api_key

    async def on_group_prefix(self, group_message: GroupMessage) -> None:
        command = group_message.plain_text()
        await group_message.reply(await get_completion(command))
