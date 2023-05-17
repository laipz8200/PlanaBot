import json
import openai
from loguru import logger

from plana import GroupMessage, Plugin
from plana.messages import Message
from .utils import get_completion
from .prompts import chat_prompt


class Chat(Plugin):
    prefix: str = "#chat"
    openai_api_key: str = ""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        openai.api_key = self.openai_api_key

    async def on_group_prefix(self, group_message: GroupMessage) -> None:
        group_messages = await self.get_group_msg_history(group_message.group_id)
        history_list = [
            f"{message.user_id}: {message.remove_prefix(self.prefix).plain_text()}"
            for message in group_messages
        ]
        prompt = chat_prompt.format(history_list="\n".join(history_list))
        response = await get_completion(prompt)
        try:
            response_json = json.loads(response)
            user_id = response_json["mention_user_id"]
            content = response_json["content"]
            message = Message()
            message.add_at(user_id)
            message.add_text(content)
            await self.send_group_message(group_message.group_id, message)
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            await group_message.reply("Sorry, please try again later.")
