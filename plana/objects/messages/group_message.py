from plana.actions.send_group_msg import create_send_group_msg_action
from plana.core.plugin import Plugin
from plana.objects.messages.array_messages import ArrayMessage
from plana.objects.messages.base import BaseMessage
from plana.objects.messages.reply import create_reply
from plana.objects.sender import Anonymous


class GroupMessage(BaseMessage, Plugin):
    group_id: int
    anonymous: Anonymous | None

    async def reply(self, message: ArrayMessage | str):
        if isinstance(message, str):
            text = message
            message = ArrayMessage()
            message.add_text(text)
        message.insert(0, create_reply(self.message_id))
        await self.queue.put(create_send_group_msg_action(self.group_id, message))


def create_group_message(message: dict, plugin: Plugin) -> GroupMessage:
    msg = GroupMessage(**plugin.dict(), **message)
    return msg
