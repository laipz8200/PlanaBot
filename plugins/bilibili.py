import asyncio
import httpx
import re
import json
from plana.core.plugin import Plugin
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from plana.objects.messages.private_message import PrivateMessage


class Bilibili(Plugin):
    async def on_private(self, private_message: PrivateMessage):
        urls = await self.parse_messages(private_message.message)
        if urls:
            await private_message.reply(
                self.queue,
                "I found the following URLs in your message:\n" + "\n".join(urls),
            )

    async def parse_messages(self, messages: list[dict]) -> list[str]:
        short_urls = []
        for message in messages:
            msg_type = message.get("type")
            if msg_type == "json":
                json_data = json.loads(message["data"]["data"])
                if "哔哩哔哩" in json_data.get("prompt", ""):
                    meta = json_data.get("meta", {})
                    detail_1 = meta.get("detail_1", {})
                    short_url = detail_1.get("qqdocurl")
                    short_urls.append(short_url)
            elif msg_type == "text":
                text = message["data"]["text"]
                pattern = r"https://b23\.tv/[\w\d]+"
                short_urls = re.findall(pattern, text)

        tasks = [
            self.parse_short_url(short_url)
            for short_url in filter(lambda x: x, short_urls)
        ]
        return await asyncio.gather(*tasks)

    async def parse_short_url(self, short_url: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get(short_url, follow_redirects=True)
        return self.sanitize_bilibili(str(response.url))

    def sanitize_bilibili(self, url: str) -> str:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        filtered_params = {k: v for k, v in query_params.items() if k == "p"}
        new_query_string = urlencode(filtered_params, doseq=True)
        new_parsed_url = parsed_url._replace(query=new_query_string)
        new_url = urlunparse(new_parsed_url)
        return new_url
