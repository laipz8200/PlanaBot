import xml.etree.ElementTree as ET

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from plana import Plugin


class MikanAnime(Plugin):
    rss_url: str
    previous_records: list[str] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        scheduler = AsyncIOScheduler()
        scheduler.add_job(self.check_update, "cron", hour="18-23")
        scheduler.start()

    async def check_update(self):
        logger.info("[MikanAnime] Start check update")
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.rss_url, timeout=3)
            except Exception as e:
                logger.error(f"[Mikan] Failed to fetch rss: {e}")
                return

        rss = ET.fromstring(response.text)
        items = rss.findall("./channel/item")
        rs = [
            {"title": item.find("title").text, "link": item.find("link").text}
            for item in filter(
                lambda item: item.find("title").text not in self.previous_records,
                items,
            )
        ]
        if not rs:
            return
        self.previous_records = [r["title"] for r in rs]
        message = "\n".join(
            ["你订阅的番剧更新啦!!!"] + [f'{i["title"]}\n详情: {i["link"]}' for i in rs]
        )
        for gid in self.config.allowed_groups:
            await self.send_group_message(gid, message)
