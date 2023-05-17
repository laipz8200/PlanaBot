import asyncio
import xml.etree.ElementTree as ET

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from pydantic import BaseModel

from plana import Plugin


class AnimeItem(BaseModel):
    title: str
    link: str


class MikanAnime(Plugin):
    rss_url: str
    previous_records: list[str] = []

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        scheduler = AsyncIOScheduler()
        scheduler.add_job(self.check_update, "cron", hour="0-2,18-23")
        scheduler.start()

    async def check_update(self) -> None:
        logger.debug("[MikanAnime] Start check update")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.rss_url, timeout=3)
            except Exception as e:
                logger.error(f"[Mikan] Failed to fetch rss: {e}")
                return

        rss: ET.Element = ET.fromstring(response.text)
        rss_items = filter(
            lambda item: item.find("title") and item.find("link"),
            rss.findall("./channel/item"),
        )

        anime_items: list[AnimeItem] = [
            AnimeItem(title=i.find("title").text, link=i.find("link").text)  # type: ignore  # noqa: E501
            for i in rss_items
        ]

        if not anime_items:
            return

        message_list: list[str] = [
            f"{i.title}\n{i.link}"
            for i in filter(lambda i: i.title not in self.previous_records, anime_items)
        ]
        message_list.insert(0, "老师, 你订阅的番剧更新了:")
        message: str = "\n".join(message_list)

        asyncio.gather(
            *[
                self.send_group_message(gid, message)
                for gid in self.config.allowed_groups
            ]
        )
        self.previous_records = [i.title for i in anime_items]
