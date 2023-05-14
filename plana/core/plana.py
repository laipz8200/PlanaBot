import asyncio
import copy
import importlib.util
import logging
import os
from typing import Any

import uvicorn
import yaml
from fastapi import FastAPI, WebSocket
from loguru import logger
from pydantic import BaseModel

from plana.core.plugin import Plugin
from plana.objects.messages.base import BaseMessage
from plana.objects.messages.group_message import GroupMessage
from plana.objects.messages.private_message import PrivateMessage


class PlanaConfig(BaseModel):
    master_id: int = 10000
    allowed_groups: list[int] = []
    enabled_plugins: list[str] = ["echo", "bilibili"]


class Plana:
    def __init__(
        self,
        *,
        config: PlanaConfig | None = None,
        config_file_path: str = "config.yaml",
    ) -> None:
        self.__version__ = "v0.1.0"

        logger.info("Thanks for using")
        logger.info("     ____  _        _    _   _    _")
        logger.info("    |  _ \| |      / \  | \ | |  / \\")
        logger.info("    | |_) | |     / _ \ |  \| | / _ \\")
        logger.info("    |  __/| |___ / ___ \| |\  |/ ___ \\")
        logger.info("    |_|   |_____/_/   \_\_| \_/_/   \_\\    - " + self.__version__)
        logger.info("")

        self.config = config
        if not self.config:
            self.config = PlanaConfig()

        if not os.path.exists(config_file_path):
            with open(config_file_path, "w") as f:
                yaml.dump(config.dict(), f)
            logger.critical("Please edit config.yaml and reboot")
            exit(0)

        with open(config_file_path, "r") as f:
            config_dict: dict = yaml.safe_load(f)
            if config_dict:
                for k, v in config_dict.items():
                    setattr(self.config, k, v)

        self.plugins: list[Plugin] = []
        self.actions_queue = asyncio.Queue()

        self.app = FastAPI()
        self.load_plugins(self.config.enabled_plugins)

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

        event["event"] = copy.deepcopy(event)

        if post_type in ["message", "message_sent"]:
            base_message = BaseMessage(**event)

            if base_message.message_type == "group":
                await self.handle_group_message_event(event)

            if base_message.message_type == "private":
                await self.handle_private_message_event(event)

    async def handle_private_message_event(self, event: dict):
        private_message = PrivateMessage(**event)
        sender = private_message.sender
        logger.info(
            (
                f"[Private] "
                f"{sender.nickname}({sender.user_id}): "
                f"{private_message.message}"
            )
        )

        for plugin in self.plugins:
            private_message = private_message.load_plugin(plugin)
            if (
                plugin.master_only
                and private_message.sender.user_id != self.config.master_id
            ):
                continue

            await plugin.on_private(private_message)

    async def handle_group_message_event(self, event: dict):
        group_message = GroupMessage(**event)
        sender = group_message.sender
        logger.info(
            (
                f"[Group] {group_message.group_id} "
                f"{sender.nickname}({sender.user_id}): "
                f"{group_message.message}"
            )
        )

        if group_message.group_id not in self.config.allowed_groups:
            return

        tasks = []
        for plugin in self.plugins:
            group_message = group_message.load_plugin(plugin)

            if (
                plugin.master_only
                and group_message.sender.user_id != self.config.master_id
            ):
                continue

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
        logger.info(f"{len(self.plugins)} plugins Loaded: {plugins_name}")

    async def ws_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        client_name = f"{websocket.client.host}:{websocket.client.port}"
        logger.info(f"Client {client_name} connected")

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
            logger.info(f"Client {client_name} disconnected")

    async def action_consumer(self, websocket: WebSocket):
        while True:
            if not self.actions_queue.empty():
                action = await self.actions_queue.get()
                await websocket.send_json(action.dict())
            else:
                await asyncio.sleep(0.1)
