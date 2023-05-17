from plana.objects.messages.array_messages import ArrayMessage
from plana.objects.messages.base import BaseMessage
from plana.objects.messages.reply import create_reply
from plana.objects.messages.sender import Anonymous


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

    async def reply(self, message: ArrayMessage | str):
        if not self.plugin:
            raise Exception("Plugin not loaded")
        if isinstance(message, str):
            text = message
            message = ArrayMessage()
            message.add_text(text)
        message.insert(0, create_reply(self.message_id))
        await self.plugin.send_group_message(self.group_id, message)
