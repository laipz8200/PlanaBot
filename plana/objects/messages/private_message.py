from plana.objects.messages.base import ArrayMessage, BaseMessage


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

    async def reply(self, message: ArrayMessage | str):
        if isinstance(message, str):
            text = message
            message = ArrayMessage()
            message.add_text(text)
        await self.plugin.send_private_message(self.sender.user_id, message)
