from plana.messages.base_message import BaseMessage, Message


class PrivateMessage(BaseMessage):
    target_id: int
    temp_source: int | None

    def __str__(self) -> str:
        return (
            f"[PrivateMessage] "
            f"{self.sender.nickname}({self.sender.user_id}): "
            f"{self.message}"
        )

    def __repr__(self) -> str:
        return str(self)

    async def reply(self, message: Message | str) -> None:
        if isinstance(message, str):
            text = message
            message = Message()
            message.add_text(text)
        if not self.plugin:
            raise Exception("Plugin not loaded")
        await self.plugin.send_private_message(self.user_id, message)
