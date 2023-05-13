import asyncio
import typing

from pydantic import BaseModel

if typing.TYPE_CHECKING:
    from plana.objects.messages.group_message import GroupMessage
    from plana.objects.messages.private_message import PrivateMessage


class Plugin(BaseModel):
    queue: asyncio.Queue | None = None
    prefix: str | None = None

    class Config:
        arbitrary_types_allowed = True

    async def on_group(self, group_message: "GroupMessage"):
        pass

    async def on_group_prefix(self, group_message: "GroupMessage"):
        pass

    async def on_private(self, private_message: "PrivateMessage"):
        pass
