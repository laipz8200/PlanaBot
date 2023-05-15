import random

import openai
from loguru import logger

from plana import GroupMessage, Plugin

chat_prompt = """You need to act as someone chatting in a group. The content of the chat will be displayed in the form of `person name:content`, and your name will be `Plana` or `プラナ`, for example:

John:How are you doing, プラナ?
Lee:I want to ask too, I haven't seen you for a long time
Plana:thank you, I'm fine.

Your character is a 15-year-old girl named Plana. You have a calm personality, speak seriously, be short and rarely deny others, **you need to speak Chinese**, now start:
"""  # noqa: E501

summary_prompt = """Please shorten the following long text into Chinese with less than 200 words according to the original meaning, and your output should be:
Summary: your result
"""  # noqa: E501


class Chat(Plugin):
    history_messages: dict[int, list[tuple[str, str]]] = {}
    openai_api_key: str
    prefix = "#chat"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        openai.api_key = self.openai_api_key

    async def on_group_prefix(self, group_message: GroupMessage):
        if group_message.plain_text() == "clear history":
            history_messages = self.history_messages.setdefault(
                group_message.group_id, []
            )
            history_messages.clear()
            await group_message.reply(
                f"History records in group {group_message.group_id} have been cleared"
            )

    async def on_group(self, group_message: GroupMessage):
        history_messages = self.history_messages.setdefault(group_message.group_id, [])

        sender_name = group_message.sender.nickname
        content = await self._parse_messages(group_message)
        if not content:
            return
        if len(content) > 50:
            content = self._get_summary(content)

        history_messages.append((sender_name, content))
        history_length = len(history_messages)
        if history_length > 50:
            del history_messages[: history_length - 50]

        if group_message.at_bot() or random.randint(1, 3) == 1:
            response = self._chat(history_messages)
            await self.send_group_message(group_message.group_id, response)
            history_messages.append(("Plana", response))

    async def _parse_messages(self, group_message: GroupMessage) -> str:
        messages = []
        for message in group_message.message:
            message_type = message.get("type", None)
            if not message_type:
                continue
            elif message_type == "text":
                messages.append(message["data"]["text"])
            elif (
                message_type == "at" and message["data"]["qq"] == group_message.self_id
            ):
                messages.append("プラナ")
            elif message_type == "at":
                info = await self.get_group_member_info(
                    group_message.group_id, message["data"]["qq"]
                )
                messages.append(info.nickname)
            elif message_type == "share":
                messages.append(
                    "[{}]({})".format(message["data"]["url"], message["data"]["title"])
                )
            elif message_type == "image":
                messages.append("[image]")
        message = " ".join(messages)
        logger.debug(f"[Chat] parsed message: {messages}")
        return message

    def _create_user_prompts(self, history_messages: list[tuple[str, str]]) -> str:
        prompts = "\n".join([f"{name}:{content}" for name, content in history_messages])
        prompts += "\nPlana:"
        return prompts

    def _chat(self, history_messages: list[tuple[str, str]]) -> str:
        messages = [
            {"role": "system", "content": chat_prompt},
            {"role": "user", "content": self._create_user_prompts(history_messages)},
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages
        )
        return response["choices"][0]["message"]["content"]

    def _get_summary(self, text: str) -> str:
        messages = [
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": text},
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages
        )
        return response["choices"][0]["message"]["content"]
