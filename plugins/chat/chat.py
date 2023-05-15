import random
from datetime import datetime

import openai
from loguru import logger

from plana import GroupMessage, Plugin

chat_prompt = """Your name is Plana, the main control system of Shiting Box, artificial intelligence, your personality is a girl about 12 years old, you are taciturn, only say 1-2 sentences at a time, you are proficient in computers Technical, good at various programming languages. Now, you are chatting online with a group of friends, and your conversation uses `[time][nickname]:[content]`, here is an example:
 ```
 2023-05-01 12:00 Xiaoxue: Is anyone there?
 2023-05-01 12:02 John: What's wrong?
 2023-05-01 12:03 Xiaoxue: I just saw the moon in the sky! It's daytime now!
 2023-05-01 12:04 Plana: The moon will not disappear, and it is common sense that the moon can be seen during the day.
 ```
 I will provide you with chat records in this format, please **use Chinese** to continue the conversation:
"""  # noqa: E501

summary_prompt = """Please shorten the following long text into Chinese with less than 200 words according to the original meaning, and your output should be:
Summary: your result
"""  # noqa: E501


def current_datetime() -> str:
    return datetime.now().strftime("%y-%m-%d %H:%M")


class Chat(Plugin):
    history_messages: dict[int, list[tuple]] = {}
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

        dt = current_datetime()
        sender_name = group_message.sender.nickname
        content = await self._parse_messages(group_message)
        if not content:
            return
        if len(content) > 400:
            content = self._get_summary(content)

        history_messages.append((dt, sender_name, content))
        history_length = len(history_messages)
        if history_length > 20:
            del history_messages[: history_length - 20]

        if (
            group_message.at_bot()
            or group_message.contains("Plana", ignore_case=True)
            or random.randint(1, 10) == 1
        ):
            response = self._chat(history_messages)
            await self.send_group_message(group_message.group_id, response)
            history_messages.append((current_datetime(), "Plana", response))

    async def _parse_messages(self, group_message: GroupMessage) -> str:
        messages = []
        for message in group_message.message:
            message_type = message.get("type", None)
            if not message_type:
                continue
            elif message_type == "text":
                messages.append(message["data"]["text"])
            elif (
                message_type == "at"
                and int(message["data"]["qq"]) == group_message.self_id
            ):
                messages.append("Plana")
            elif message_type == "at":
                info = await self.get_group_member_info(
                    group_message.group_id, int(message["data"]["qq"])
                )
                messages.append(info.nickname)
            elif message_type == "share":
                messages.append(
                    "[{}]({})".format(message["data"]["url"], message["data"]["title"])
                )
        message = " ".join(messages)
        logger.debug(f"[Chat] parsed message: {messages}")
        return message

    def _create_user_prompts(self, history_messages: list[tuple[str, str]]) -> str:
        prompts = "\n".join(
            [f"{dt} {name}:{content}" for dt, name, content in history_messages]
        )
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
