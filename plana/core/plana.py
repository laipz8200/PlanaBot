import copy
import os
import asyncio
from fastapi import FastAPI, WebSocket
import importlib.util
from typing import Any

from loguru import logger
import uvicorn
from plana.core.plugin import Plugin

from plana.objects.messages.base import BaseMessage
from plana.objects.messages.group_message import create_group_message
from plana.objects.messages.private_message import create_private_message
import logging


class Plana:
    def __init__(self, enabled_plugins: list[str]) -> None:
        self.__version__ = "v0.1.0"

        logger.info("Thanks for using")
        logger.info("     ____  _        _    _   _    _")
        logger.info("    |  _ \| |      / \  | \ | |  / \\")
        logger.info("    | |_) | |     / _ \ |  \| | / _ \\")
        logger.info("    |  __/| |___ / ___ \| |\  |/ ___ \\")
        logger.info("    |_|   |_____/_/   \_\_| \_/_/   \_\\    - " + self.__version__)
        logger.info("")

        self.plugins: list[Plugin] = []
        self.actions_queue = asyncio.Queue()
        self.load_plugins(enabled_plugins)

        self.app = FastAPI()

        logging.getLogger("fastapi").setLevel(logging.CRITICAL)

        self.app.add_websocket_route("/ws", self.ws_endpoint)

    def run(self):
        uvicorn.run(
            self.app,
            host="127.0.0.1",
            port=8000,
            log_level=logging.CRITICAL,
            access_log=False,
        )

    async def process(self, event: dict) -> Any:
        post_type = event.get("post_type", None)
        if not post_type:
            return

        event["origin_event"] = copy.deepcopy(event)

        if post_type in ["message", "message_sent"]:
            base_message = BaseMessage(**event)

            if base_message.message_type == "group":
                await self.handle_group_message(event)

            if base_message.message_type == "private":
                for plugin in self.plugins:
                    private_message = create_private_message(event, plugin)
                    await plugin.on_private(private_message)

    async def handle_group_message(self, message: dict):
        tasks = []
        for plugin in self.plugins:
            group_message = create_group_message(message, plugin)
            tasks.append(plugin.on_group(group_message))
            if plugin.prefix and group_message.starts_with(plugin.prefix):
                group_message = group_message.remove_prefix(plugin.prefix)
                tasks.append(plugin.on_group_prefix(group_message))
        await asyncio.gather(*tasks)

    def load_plugins(self, enabled_plugins: list[str]) -> list[Plugin]:
        enabled_plugins = list(map(lambda x: x.lower(), enabled_plugins))
        for filename in os.listdir("plugins"):
            if filename.endswith(".py"):
                module_name = f"plugins.{filename[:-3]}"
                spec = importlib.util.spec_from_file_location(
                    module_name, f"plugins/{filename}"
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Plugin)
                        and attr is not Plugin
                        and attr_name.lower() in enabled_plugins
                    ):
                        obj = attr()
                        obj.queue = self.actions_queue
                        self.plugins.append(obj)
        plugins_name = ", ".join([plugin.__class__.__name__ for plugin in self.plugins])
        logger.info(f"Loaded {len(self.plugins)} plugins: {plugins_name}")

    async def ws_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        logger.info(f"Client {websocket.client_id} connected to ws endpoint")

        consumer_task = asyncio.create_task(self.action_consumer(websocket))
        try:
            async for event in websocket.iter_json():
                try:
                    await self.process(event)
                except Exception as e:
                    logger.error("=== Error Info ===")
                    logger.error(f"Event: {event}")
                    logger.error(f"Error: {e}")
                    logger.error("==================")
        except Exception:
            consumer_task.cancel()
            await consumer_task
        finally:
            await websocket.close()
            logger.info(f"Client {websocket.client_id} disconnected from ws endpoint")

    async def action_consumer(self, websocket: WebSocket):
        while True:
            if not self.actions_queue.empty():
                action = await self.actions_queue.get()
                await websocket.send_json(action.dict())
            else:
                await asyncio.sleep(0.1)
