import asyncio
import typing

from pydantic import BaseModel
from plana.actions.send_group_msg import create_send_group_msg_action
from plana.actions.send_private_msg import create_send_private_msg_action

from plana.objects.messages.array_messages import ArrayMessage

if typing.TYPE_CHECKING:
    from plana.objects.messages.group_message import GroupMessage
    from plana.objects.messages.private_message import PrivateMessage


class Plugin(BaseModel):
    queue: asyncio.Queue | None = None
    prefix: str | None = None

    class Config:
        arbitrary_types_allowed = True

    async def send_group_message(self, group_id: int, message: ArrayMessage | str):
        await self.queue.put(create_send_group_msg_action(group_id, message))

    async def send_private_message(self, user_id: int, message: ArrayMessage | str):
        await self.queue.put(create_send_private_msg_action(user_id, message))

    async def on_group(self, group_message: "GroupMessage"):
        pass

    async def on_group_prefix(self, group_message: "GroupMessage"):
        pass

    async def on_private(self, private_message: "PrivateMessage"):
        pass
