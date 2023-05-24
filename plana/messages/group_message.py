from plana.actions.reply import create_reply
from plana.messages.base_message import BaseMessage
from plana.messages.message import Message
from plana.messages.sender import Anonymous


class GroupMessage(BaseMessage):
    group_id: int
    anonymous: Anonymous | None

    def __str__(self) -> str:
        return (
            f"[GroupMessage] {self.group_id} "
            f"{self.sender.nickname}({self.sender.user_id}): "
            f"{self.message}"
        )

    def __repr__(self) -> str:
        return str(self)

    async def reply(self, message: Message | str) -> None:
        if not self.plugin:
            raise Exception("Plugin not loaded")
        if isinstance(message, str):
            text = message
            message = Message()
            message.add_text(text)
        message.insert(0, create_reply(self.message_id))
        await self.plugin.send_group_message(self.group_id, message)
