import json
import re
from collections import deque

from loguru import logger

from plana import GroupMessage, Plugin
from plana.objects.messages.array_messages import ArrayMessage
from plugins.chat.utils import get_completion, set_api_key

from .prompts import chat_with_format


class Chat(Plugin):
    prefix: str = "#chat"
    history: dict[int, deque] = {}
    openai_api_key: str = ""
    enabled_groups: set[int] = set()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        set_api_key(self.openai_api_key)

    async def on_group_prefix(self, group_message: GroupMessage) -> None:
        command = group_message.plain_text()
        if command == "reset":
            self.history[group_message.group_id] = deque(maxlen=3)
            await group_message.reply(
                f"History in group {group_message.group_id} have been reset"
            )
        elif command == "disable":
            self.enabled_groups.remove(group_message.group_id)
            await group_message.reply(f"Disabled in group {group_message.group_id}")
        elif command == "enable":
            self.enabled_groups.add(group_message.group_id)
            await group_message.reply(f"Enabled in group {group_message.group_id}")
        else:
            await group_message.reply("Unknown command")

    async def on_group(self, group_message: GroupMessage) -> None:
        if group_message.group_id not in self.enabled_groups:
            return

        if group_message.on_prefix(self.prefix):
            return

        records = self.history.setdefault(group_message.group_id, deque(maxlen=3))
        supported_message = list(
            filter(lambda x: x["type"] in ["text", "at"], group_message.message)
        )
        if not supported_message:
            return
        message = {"user_id": group_message.user_id, "message": supported_message}
        records.append(message)

        response = get_completion(
            chat_with_format.format(self_id=group_message.self_id),
            prompt="History:" + json.dumps(list(records), ensure_ascii=False),
        )
        logger.debug(f"{response=}")

        try:
            groups = re.findall(r"\[(.*)\]", response)
            response_json = json.loads(groups[-1])
            logger.debug(f"{response_json=}")
            reply = ArrayMessage(response_json["message"])
            message = {"user_id": group_message.self_id, "message": response_json}
            records.append(message)
            await self.send_group_message(group_message.group_id, reply)
        except Exception as e:
            error_msg = f"Failed to parse response: {e}, response: {response}"
            logger.error(error_msg)
            await self.send_group_message(group_message.group_id, error_msg)
