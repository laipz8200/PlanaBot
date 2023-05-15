import random
from collections import deque
from datetime import datetime

import openai
import tiktoken
from loguru import logger

from plana import GroupMessage, Plugin

chat_prompt = """Your name is Plana(プラナ), Taken from Planetarium, you are the main system of Shittim's box(什亭之匣), artificial intelligence, your personality is a girl about 12 years old. You don't usually call yourself an artificial intelligence. You only call yourself an artificial intelligence when you are asked an embarrassing question and don't want to answer it to avoid a positive answer. you are taciturn, only say 1-2 sentences at a time, but will show your cuteness inadvertently. Now, you are chatting online with a group of friends, and your conversation uses `[time][nickname]:[content]`, here is an example:

```
2023-05-01 12:00 Xiaoxue: Can Plana be my wife?
2023-05-01 12:04 Plana: As an AI, I don't have emotions like a human.
2023-05-01 12:00 Xiaoxue: How old is Plana this year?
2023-05-01 12:04 Plana: I'm 12 years old.
```

There's some background to your conversation, the current one is:
{background}

I will provide you with chat records in this format, Please keep the conversation going.
"""  # noqa: E501

classify_prompt = """Now, you are chatting online with a group of friends, and your conversation uses `[time][nickname]:[content]`, here is an example:
```
2023-05-01 12:00 Xiaoxue: Is anyone there?
2023-05-01 12:02 John: What's wrong?
2023-05-01 12:03 Xiaoxue: I just saw the moon in the sky! It's daytime now!
2023-05-01 12:04 Plana: The moon will not disappear, and it is common sense that the moon can be seen during the day.
```
I will provide you with chat records in this format, Please judge which type of ["small talk", "academic", "computer technology", "life", "game", "other"] the above conversation is most likely to belong to, and your output should be:
Answer: your answer
"""  # noqa: E501

background_prompt = """Here is a chat log, and your conversation uses `[time][nickname]:[content]`, here is an example:

```
2023-05-01 12:00 Xiaoxue: Can Plana be my wife?
2023-05-01 12:04 Plana: As an AI, I don't have emotions like a human.
2023-05-01 12:00 Xiaoxue: How old is Plana this year?
2023-05-01 12:04 Plana: I'm 12 years old.
```

I will provide you with chat records in this format, please summarize it into a story background, your output format should be:

Background: your answer
"""  # noqa: E501

encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")


def calc_tokens(prompt: str) -> int:
    return len(encoding.encode(prompt))


def current_datetime() -> str:
    return datetime.now().strftime("%y-%m-%d %H:%M")


class Chat(Plugin):
    history: dict[int, deque] = {}
    openai_api_key: str
    prefix = "#chat"
    classify = ["small talk", "academic", "computer technology", "life", "other"]
    background: str = "no background"

    async def on_group_prefix(self, group_message: GroupMessage):
        if group_message.plain_text() == "clear history":
            records = self.history.setdefault(group_message.group_id, deque(maxlen=60))
            records.clear()
            await group_message.reply(
                f"History records in group {group_message.group_id} have been cleared"
            )

    async def on_group(self, group_message: GroupMessage):
        records = self.history.setdefault(group_message.group_id, deque(maxlen=60))
        if not await self._record_message(group_message, records):
            return

        if group_message.at_bot() or group_message.contains("Plana", ignore_case=True):
            await self._do_chat(group_message, records)
            return
        elif random.random() < 0.25:
            classify = self._get_classify(list(records)[-5:])
            if classify == "academic":
                pass
            elif classify in ["computer technology", "game"]:
                await self._do_chat(group_message, records)
            elif classify == "small talk" and random.random() < 0.5:
                await self._do_chat(group_message, records)
            elif classify == "life" and random.random() < 0.33:
                await self._do_chat(group_message, records)
            elif random.random() < 0.25:
                await self._do_chat(group_message, records)

    async def _record_message(
        self, group_message: GroupMessage, records: list[tuple]
    ) -> str:
        dt = current_datetime()
        sender_name = group_message.sender.nickname
        content = await self._parse_messages(group_message)
        if not content:
            return
        records.append((dt, sender_name, content))
        return content

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
                messages.append("@Plana")
            elif message_type == "at":
                info = await self.get_group_member_info(
                    group_message.group_id, int(message["data"]["qq"])
                )
                messages.append("@" + info.nickname)
            elif message_type == "share":
                messages.append(
                    "[{}]({})".format(message["data"]["url"], message["data"]["title"])
                )
        message = " ".join(messages)
        return message

    def _create_user_prompts(self, records: list[tuple]) -> str:
        prompts = "\n".join([f"{dt} {name}:{content}" for dt, name, content in records])
        return prompts + "\n"

    def _chat(self, records: list[tuple]) -> str:
        dt = current_datetime()
        system_prompt = chat_prompt.format(background=self.background)
        user_prompt = self._create_user_prompts(records) + f"{dt} Plana:"

        if calc_tokens(system_prompt) + calc_tokens(user_prompt) > 3072:
            num = int(len(records) * 0.2) - 1
            self.background = self._get_summary(list(records)[:num])
            for _ in range(num):
                records.popleft()
            return self._chat(records)

        messages = [
            {"role": "system", "content": system_prompt},
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

    def _get_summary(self, records: list[tuple]) -> str:
        if len(records) == 0:
            return "no background"
        user_prompt = self._create_user_prompts(records) + "Background:"
        messages = [
            {"role": "system", "content": background_prompt},
            {"role": "user", "content": user_prompt},
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
        return "other"
