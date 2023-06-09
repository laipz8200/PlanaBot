from plana import Plugin
from plana.messages import PrivateMessage


class WhoAreU(Plugin):
    master_only = True
    prefix = "#whoareu"

    async def on_private_prefix(self, private_message: PrivateMessage):
        info = await self.get_login_info()
        message = f"Hello, I'm {info.nickname}."
        await private_message.reply(message)
