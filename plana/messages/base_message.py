from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, validator

from plana.messages.message import Message
from plana.messages.sender import Sender

if TYPE_CHECKING:
    from plana import Plugin


class BaseMessage(BaseModel):
    message_type: str
    sub_type: str
    message_id: int
    user_id: int
    message: Message
    raw_message: str
    font: int
    sender: Sender
    time: int
    self_id: int
    plugin: Any = None

    @validator("message")
    def validate_message(cls, message: str) -> Message:
        return Message(message)

    def load_plugin(self, plugin: "Plugin") -> None:
        self.plugin = plugin

    def plain_text(self) -> str:
        return self.message.plain_text()

    def on_prefix(self, prefix: str) -> bool:
        return self.message.on_prefix(prefix)

    def remove_prefix(self, prefix: str) -> Self:
        obj = self.copy()
        obj.message = obj.message.remove_prefix(prefix)
        return obj

    def at_bot(self) -> bool:
        for msg in self.message:
            if msg.get("type", "") == "at" and int(msg["data"]["qq"]) == self.self_id:
                return True
        return False

    def contains(self, text: str, ignore_case: bool = False) -> bool:
        if ignore_case:
            return text.lower() in self.plain_text().lower()
        return text in self.plain_text()

    async def reply(self, message: Message | str) -> None:
        raise NotImplementedError
