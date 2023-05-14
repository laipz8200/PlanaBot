from plana.actions.quick_operation import create_quick_operation_action
from plana.objects.messages.base import ArrayMessage, BaseMessage


class PrivateMessage(BaseMessage):
    target_id: int
    temp_source: int | None

    async def reply(self, message: ArrayMessage | str):
        if isinstance(message, str):
            text = message
            message = ArrayMessage()
            message.add_text(text)
        await self.queue.put(
            create_quick_operation_action(self.event, {"reply": message})
        )
