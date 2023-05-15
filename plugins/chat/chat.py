import random
from collections import deque
from datetime import datetime

import openai
from loguru import logger

from plana import GroupMessage, Plugin

chat_prompt = """Your name is Plana(プラナ), the main system of Shittim Box(什亭之匣), artificial intelligence, your personality is a girl about 12 years old, you are taciturn, only say 1-2 sentences at a time, you are proficient in computers Technical, good at various programming languages. Now, you are chatting online with a group of friends, and your conversation uses `[time][nickname]:[content]`, here is an example:
```
2023-05-01 12:00 Xiaoxue: Is anyone there?
2023-05-01 12:02 John: What's wrong?
2023-05-01 12:03 Xiaoxue: I just saw the moon in the sky! It's daytime now!
2023-05-01 12:04 Plana: The moon will not disappear, and it is common sense that the moon can be seen during the day.
```
I will provide you with chat records in this format, please **use Chinese** to continue the conversation:
"""  # noqa: E501

classify_prompt = """Now, you are chatting online with a group of friends, and your conversation uses `[time][nickname]:[content]`, here is an example:
```
2023-05-01 12:00 Xiaoxue: Is anyone there?
2023-05-01 12:02 John: What's wrong?
2023-05-01 12:03 Xiaoxue: I just saw the moon in the sky! It's daytime now!
2023-05-01 12:04 Plana: The moon will not disappear, and it is common sense that the moon can be seen during the day.
```
I will provide you with chat records in this format, Please judge which type of ["small talk", "academic", "computer technology", "life", "other"] the above conversation is most likely to belong to, and your output should be:
Answer: your answer
"""  # noqa: E501

summary_prompt = """Please shorten the following long text into Chinese with less than 200 words according to the original meaning, and your output should be:
Summary: your result
"""  # noqa: E501


def current_datetime() -> str:
    return datetime.now().strftime("%y-%m-%d %H:%M")


class Chat(Plugin):
    history: dict[int, deque] = {}
    openai_api_key: str
    prefix = "#chat"
    classify = ["small talk", "academic", "computer technology", "life", "other"]

    async def on_group_prefix(self, group_message: GroupMessage):
        if group_message.plain_text() == "clear history":
            history_messages = self.history.setdefault(group_message.group_id, [])
            history_messages.clear()
            await group_message.reply(
                f"History records in group {group_message.group_id} have been cleared"
            )

    async def on_group(self, group_message: GroupMessage):
        records = self.history.setdefault(group_message.group_id, deque(maxlen=20))
        await self._record_message(group_message, records)

        if group_message.at_bot() or group_message.contains("Plana", ignore_case=True):
            await self._do_chat(group_message, records)
            return
        elif random.random() < 0.25:
            classify = self._get_classify(records)
            if classify == "academic":
                pass
            elif classify == "computer technology":
                await self._do_chat(group_message, records)
            elif classify == "small talk" and random.random() < 0.5:
                await self._do_chat(group_message, records)
            elif classify == "life" and random.random() < 0.33:
                await self._do_chat(group_message, records)
            elif random.random() < 0.25:
                await self._do_chat(group_message, records)

    async def _record_message(self, group_message: GroupMessage, records: list[tuple]):
        dt = current_datetime()
        sender_name = group_message.sender.nickname
        content = await self._parse_messages(group_message)
        if not content:
            return
        if len(content) > 400:
            content = self._get_summary(content)

        records.append((dt, sender_name, content))

    async def _do_chat(self, group_message: GroupMessage, records: list[tuple]):
        response = self._chat(records)
        await self.send_group_message(group_message.group_id, response)
        records.append((current_datetime(), "Plana", response))

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
        logger.debug(f"[Chat] parsed message: {message}")
        return message

    def _create_user_prompts(self, records: list[tuple]) -> str:
        prompts = "\n".join([f"{dt} {name}:{content}" for dt, name, content in records])
        return prompts + "\n"

    def _chat(self, records: list[tuple]) -> str:
        user_prompt = (
            self._create_user_prompts(records) + f"{current_datetime()} Plana:"
        )
        messages = [
            {"role": "system", "content": chat_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            api_key=self.openai_api_key,
            temperature=0.9,
            top_p=1,
            messages=messages,
        )
        return response["choices"][0]["message"]["content"]

    def _get_summary(self, text: str) -> str:
        messages = [
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": text},
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            api_key=self.openai_api_key,
            temperature=0,
            messages=messages,
        )
        return response["choices"][0]["message"]["content"]

    def _get_classify(self, records: list[tuple]) -> str:
        user_prompts = self._create_user_prompts(records)
        messages = [
            {"role": "system", "content": classify_prompt},
            {"role": "user", "content": user_prompts + "Answer:"},
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            api_key=self.openai_api_key,
            temperature=0,
            messages=messages,
        )
        answer = response["choices"][0]["message"]["content"].lower()

        for classify in self.classify:
            if classify in answer:
                logger.debug(f"[Chat] Classify result: {classify}")
                return classify

        logger.debug("[Chat] Classify result: other")
        return "other"
