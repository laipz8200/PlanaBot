import asyncio
import uuid

from pydantic import BaseModel

from plana.actions import Action, GetLoginInfo, GroupMemberInfo, LoginInfo
from plana.actions.get_group_member_info import GetGroupMemberInfo
from plana.actions.get_group_msg_history import GetGroupMsgHistory
from plana.actions.send_group_msg import SendGroupMessage
from plana.actions.send_private_msg import SendPrivateMessage
from plana.core.config import PlanaConfig
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

    async def on_group(self, group_message: GroupMessage):
        pass

    async def on_group_prefix(self, group_message: GroupMessage):
        pass

    async def on_private(self, private_message: PrivateMessage):
        pass

    async def on_private_prefix(self, private_message: PrivateMessage):
        pass

    async def handle_on_group(self, group_message: GroupMessage):
        group_message.load_plugin(self)
        return await self.on_group(group_message)

    async def handle_on_group_prefix(self, group_message: GroupMessage):
        group_message.load_plugin(self)
        if self.prefix:
            new_message = group_message.remove_prefix(self.prefix)
            return await self.on_group_prefix(new_message)

    async def handle_on_private(self, private_message: PrivateMessage):
        private_message.load_plugin(self)
        return await self.on_private(private_message)

    async def handle_on_private_prefix(self, private_message: PrivateMessage):
        private_message.load_plugin(self)
        if self.prefix:
            new_message = private_message.remove_prefix(self.prefix)
            return await self.on_private_prefix(new_message)

    async def send_group_message(self, group_id: int, message: Message | str):
        action = SendGroupMessage(params={"group_id": group_id, "message": message})
        await self.queue.put(action)

    async def send_private_message(self, user_id: int, message: Message | str):
        action = SendPrivateMessage(params={"user_id": user_id, "message": message})
        await self.queue.put(action)

    async def get_login_info(self) -> LoginInfo:
        action = GetLoginInfo()
        response = await self._send_action_with_response(action)
        return LoginInfo(**response["data"])

    async def get_group_member_info(
        self, group_id: int, user_id: int
    ) -> GroupMemberInfo:
        action = GetGroupMemberInfo(params={"group_id": group_id, "user_id": user_id})
        response = await self._send_action_with_response(action)
        return GroupMemberInfo(**response["data"])

    async def get_group_msg_history(self, group_id: int) -> list[GroupMessage]:
        action = GetGroupMsgHistory(params={"group_id": group_id})
        response = await self._send_action_with_response(action)
        return [GroupMessage(**msg) for msg in response["data"]["messages"]]

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
