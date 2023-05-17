import asyncio
import typing
import uuid

from pydantic import BaseModel

from plana.actions import (
    Action,
    GetLoginInfo,
    GroupMemberInfo,
    LoginInfo,
    create_get_group_member_info_action,
    create_send_group_msg_action,
    create_send_private_msg_action,
)
from plana.actions.get_group_msg_history import GetGroupMsgHistory
from plana.core.config import PlanaConfig

if typing.TYPE_CHECKING:
    from plana.messages import GroupMessage, Message, PrivateMessage


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
        if self.prefix:
            new_message = group_message.remove_prefix(self.prefix)
            return await self.on_group_prefix(new_message)

    async def handle_on_private(self, private_message: "PrivateMessage"):
        private_message.load_plugin(self)
        return await self.on_private(private_message)

    async def handle_on_private_prefix(self, private_message: "PrivateMessage"):
        private_message.load_plugin(self)
        if self.prefix:
            new_message = private_message.remove_prefix(self.prefix)
            return await self.on_private_prefix(new_message)

    async def send_group_message(self, group_id: int, message: "Message | str"):
        await self.queue.put(create_send_group_msg_action(group_id, message))

    async def send_private_message(self, user_id: int, message: "Message | str"):
        await self.queue.put(create_send_private_msg_action(user_id, message))

    async def get_login_info(self) -> LoginInfo:
        action = GetLoginInfo()
        response = await self._send_action_with_response(action)
        return LoginInfo(**response["data"])

    async def get_group_member_info(
        self, group_id: int, user_id: int
    ) -> GroupMemberInfo:
        action = create_get_group_member_info_action(group_id, user_id)
        response = await self._send_action_with_response(action)
        return GroupMemberInfo(**response["data"])

    async def get_group_msg_history(self) -> list["GroupMessage"]:
        action = GetGroupMsgHistory()
        response = await self._send_action_with_response(action)
        return [GroupMessage(**msg) for msg in response["data"]]

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
