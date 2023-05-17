from plana import Plugin
from plana.messages.group_message import GroupMessage
from plana.messages.private_message import PrivateMessage


class Echo(Plugin):
    prefix = "#echo"
    master_only = True

    async def on_group_prefix(self, group_message: GroupMessage):
        command = group_message.plain_text()
        if command == "get_group_msg_history":
            messages = [
                msg.plain_text()
                for msg in await self.get_group_msg_history(group_message.group_id)
            ]
            await group_message.reply("\n".join(messages))
        else:
            await group_message.reply(group_message.message)

    async def on_private_prefix(self, private_message: PrivateMessage):
        await private_message.reply(private_message.message)
