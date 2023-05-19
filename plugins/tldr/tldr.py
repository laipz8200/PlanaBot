import re

import openai

from plana import Plugin
from plana.messages import GroupMessage

from .assistant import assistant


class TLDR(Plugin):
    prefix: str = "#tldr"
    openai_api_key: str = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        openai.api_key = self.openai_api_key

    async def on_group_prefix(self, group_message: GroupMessage) -> None:
        command = group_message.plain_text()
        # 判断command是不是合法 url
        if not re.match(r"^https?://.*", command):
            await group_message.reply("老师, 请输入正确的网络地址")
        else:
            try:
                summary = await assistant.summarize_from_url(command)
                await group_message.reply(summary)
            except Exception as e:
                await group_message.reply(f"老师, 遇到了错误: {e}")
