from plana.core.plugin import Plugin
from plana.objects.messages.private_message import PrivateMessage


class WhoAreU(Plugin):
    master_only = True
    prefix = "!whoareu"

    async def on_private_prefix(self, private_message: PrivateMessage):
        info = await self.get_login_info()
        message = f"Hello, I'm {info.nickname}."
        await private_message.reply(message)
