import random

import openai

from plana import GroupMessage, Plugin

system_prompts = """You need to act as someone chatting in a group. The content of the chat will be displayed in the form of `person name:content`, and your name will be replaced by `You`, for example:

John:Hello everyone!
Lee:Hi!, How are you?
You:Hey! Are you chatting?

Your character is a 15-year-old girl named Plana. You have a calm personality, speak seriously, be short and rarely deny others, and you will use more questions to make yourself appear naive., you need to use Chinese, now start:
"""  # noqa: E501


class Chat(Plugin):
    system_prompts: str = system_prompts
    history_messages: list[tuple[str, str]] = []
    openai_api_key: str

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        openai.api_key = self.openai_api_key

    async def on_group(self, group_message: GroupMessage):
        sender_name = group_message.sender.nickname
        content = group_message.plain_text()
        if not content:
            return
        self.history_messages.append((sender_name, content))
        history_length = len(self.history_messages)
        if history_length > 50:
            self.history_messages = self.history_messages[history_length - 50 :]

        if len(self.history_messages) > 10 and random.randint(1, 12) == 1:
            response = self._chat()
            await self.send_group_message(group_message.group_id, response)
            self.history_messages.append(("You", response))

    def _create_user_prompts(self) -> str:
        prompts = "\n".join(
            [f"{name}:{content}" for name, content in self.history_messages]
        )
        prompts += "\nYou:"
        return prompts

    def _chat(self) -> str:
        messages = {
            {"role": "system", "content": self.system_prompts},
            {"role": "user", "content": self._create_user_prompts()},
        }
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages
        )
        return response["choices"][0]["message"]["content"]
