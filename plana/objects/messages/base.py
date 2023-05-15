from typing import Self

from pydantic import BaseModel, validator

from plana.core.plugin import Plugin
from plana.objects.messages.array_messages import ArrayMessage
from plana.objects.sender import Sender


class BaseMessage(BaseModel):
    message_type: str
    sub_type: str
    message_id: int
    user_id: int
    message: ArrayMessage
    raw_message: str
    font: int
    sender: Sender
    time: int
    self_id: int
    plugin: Plugin | None = None

    @validator("message")
    def validate_message(cls, message: str) -> ArrayMessage:
        return ArrayMessage(message)

    def load_plugin(self, plugin: Plugin):
        self.plugin = plugin

    def plain_text(self) -> str:
        return self.message.plain_text()

    def starts_with(self, text: str) -> bool:
        return self.message.starts_with(text)

    def remove_prefix(self, prefix: str) -> Self:
        obj = self.copy()
        obj.message = obj.message.remove_prefix(prefix)
        return obj

    def at_bot(self) -> bool:
        for msg in self.message:
            if (
                msg.get("type", "") == "at"
                and msg["data"]["qq"] == self.plugin.config.master_id
            ):
                return True
        return False
