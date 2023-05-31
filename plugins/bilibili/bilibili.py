import asyncio
import json
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
from loguru import logger

from plana import Plugin
from plana.messages.group_message import GroupMessage
from plana.messages.private_message import PrivateMessage


class Bilibili(Plugin):
    async def on_private(self, private_message: PrivateMessage):
        urls = await self.parse_message(private_message.message)
        if urls:
            await private_message.reply("\n".join(urls))

    async def on_group(self, group_message: GroupMessage):
        urls = await self.parse_message(group_message.message)
        if urls:
            await group_message.reply("\n".join(urls))

    async def parse_message(self, message: list[dict]) -> list[str]:
        short_urls = []
        for part in message:
            msg_type = part.get("type")
            if msg_type == "json":
                json_data = json.loads(part["data"]["data"])
                if get_nested_value(json_data, ["appID"], "") == "100951776":
                    if short_url := get_nested_value(
                        json_data,
                        ["meta", "detail_1", "qqdocurl"],
                    ):
                        short_urls.append(short_url)
                elif get_nested_value(json_data, ["extra", "appid"], 0) == 100951776:
                    if short_url := get_nested_value(
                        json_data,
                        ["meta", "news", "jumpUrl"],
                    ):
                        short_urls.append(short_url)
            elif msg_type == "text":
                text = part["data"]["text"]
                pattern = r"https://b23\.tv/[\w\d]+"
                short_urls = re.findall(pattern, text)

        tasks = [
            self.parse_short_url(short_url)
            for short_url in filter(lambda x: x, short_urls)
        ]
        results = await asyncio.gather(*tasks)
        return [url for url in results if url is not None]

    async def parse_short_url(self, short_url: str) -> str | None:
        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"  # noqa: E501
            }
        ) as client:
            try:
                response = await client.get(
                    short_url, follow_redirects=True, timeout=10
                )
                return self.sanitize_bilibili(str(response.url))
            except Exception as e:
                logger.error(f"failed to access bilibili url {short_url}: {e}")

    def sanitize_bilibili(self, url: str) -> str:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        filtered_params = {k: v for k, v in query_params.items() if k in ["t", "p"]}
        new_query_string = urlencode(filtered_params, doseq=True)
        new_parsed_url = parsed_url._replace(query=new_query_string)
        new_url = urlunparse(new_parsed_url)
        return new_url


def get_nested_value(dictionary, keys, default=None):
    if isinstance(dictionary, dict) and keys:
        key = keys[0]
        if key in dictionary:
            if len(keys) == 1:
                return dictionary[key]
            else:
                return get_nested_value(dictionary[key], keys[1:], default)
    return default
