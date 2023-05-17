from plana import Plugin
from plana.messages.group_message import GroupMessage
from plana.messages.private_message import PrivateMessage


class Echo(Plugin):
    prefix = "#echo"
    master_only = True

    async def on_group_prefix(self, group_message: GroupMessage):
        await group_message.reply(group_message.message)

    async def on_private_prefix(self, private_message: PrivateMessage):
        await private_message.reply(private_message.message)
