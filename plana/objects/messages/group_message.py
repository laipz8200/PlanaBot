from plana.actions.quick_operation import create_quick_operation_action
from plana.core.plugin import Plugin
from plana.objects.messages.array_messages import ArrayMessages
from plana.objects.messages.base import BaseMessage
from plana.objects.sender import Anonymous


class GroupMessage(BaseMessage, Plugin):
    group_id: int
    anonymous: Anonymous | None

    async def reply(self, message: ArrayMessages | str, at_sender: bool = False):
        if isinstance(message, str):
            text = message
            message = ArrayMessages()
            message.add_text(text)
        await self.queue.put(
            create_quick_operation_action(
                self.origin_event, {"at_sender": at_sender, "reply": message}
            )
        )


def create_group_message(message: dict, plugin: Plugin) -> GroupMessage:
    msg = GroupMessage(**plugin.dict(), **message)
    return msg
