from plana.actions.quick_operation import create_quick_operation_action
from plana.core.plugin import Plugin

from plana.objects.messages.base import ArrayMessages, BaseMessage


class PrivateMessage(BaseMessage, Plugin):
    target_id: int
    temp_source: int | None

    async def reply(self, message: ArrayMessages | str, *args, **kwargs):
        if isinstance(message, str):
            text = message
            message = ArrayMessages()
            message.add_text(text)
        await self.queue.put(
            create_quick_operation_action(self.origin_event, {"reply": message})
        )


def create_private_message(message: dict, plugin: Plugin) -> PrivateMessage:
    msg = PrivateMessage(**plugin.dict(), **message)
    return msg
