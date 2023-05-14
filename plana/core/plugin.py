import asyncio
import typing
import uuid

from pydantic import BaseModel

from plana.actions.get_login_info import create_get_login_info_action
from plana.actions.send_group_msg import create_send_group_msg_action
from plana.actions.send_private_msg import create_send_private_msg_action
from plana.core.config import PlanaConfig
from plana.objects.action import Action
from plana.objects.get_login_info import LoginInfo
from plana.objects.messages.array_messages import ArrayMessage

if typing.TYPE_CHECKING:
    from plana.objects.messages.group_message import GroupMessage
    from plana.objects.messages.private_message import PrivateMessage


class Plugin(BaseModel):
    queue: asyncio.Queue
    lock: asyncio.Lock
    response: dict[str, dict]
    prefix: str | None = None
    master_only: bool = False
    config: PlanaConfig

    class Config:
        arbitrary_types_allowed = True

    async def on_group(self, group_message: "GroupMessage"):
        pass

    async def on_group_prefix(self, group_message: "GroupMessage"):
        pass

    async def on_private(self, private_message: "PrivateMessage"):
        pass

    async def on_private_prefix(self, private_message: "PrivateMessage"):
        pass

    async def handle_on_group(self, group_message: "GroupMessage"):
        group_message.load_plugin(self)
        return await self.on_group(group_message)

    async def handle_on_group_prefix(self, group_message: "GroupMessage"):
        group_message.load_plugin(self)
        new_message = group_message.remove_prefix(self.prefix)
        return await self.on_group_prefix(new_message)

    async def handle_on_private(self, private_message: "PrivateMessage"):
        private_message.load_plugin(self)
        return await self.on_private(private_message)

    async def handle_on_private_prefix(self, private_message: "PrivateMessage"):
        private_message.load_plugin(self)
        new_message = private_message.remove_prefix(self.prefix)
        return await self.on_private_prefix(new_message)

    async def send_group_message(self, group_id: int, message: ArrayMessage | str):
        await self.queue.put(create_send_group_msg_action(group_id, message))

    async def send_private_message(self, user_id: int, message: ArrayMessage | str):
        await self.queue.put(create_send_private_msg_action(user_id, message))

    async def get_login_info(self) -> LoginInfo:
        action = create_get_login_info_action()
        response = await self._send_action_with_response(action)
        return LoginInfo(**response["data"])

    async def _send_action_with_response(self, action: Action) -> dict:
        uid = str(uuid.uuid4())
        action.echo = uid
        async with self.lock:
            event = asyncio.Event()
            self.response[uid] = {"event": event}
        asyncio.create_task(self.queue.put(action))
        response = await self._wait_for_response(event, uid)
        return response

    async def _wait_for_response(self, event: asyncio.Event, key: str) -> dict:
        await event.wait()
        async with self.lock:
            return self.response[key]["response"]
