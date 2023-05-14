import asyncio
import copy
import importlib.util
import inspect
import logging
import os
from typing import Any

import uvicorn
import yaml
from fastapi import FastAPI, WebSocket
from loguru import logger

from plana.core.config import PlanaConfig
from plana.core.plugin import Plugin
from plana.objects.messages.base import BaseMessage
from plana.objects.messages.group_message import GroupMessage
from plana.objects.messages.private_message import PrivateMessage


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

        if os.path.exists(config_file_path):
            with open(config_file_path, "r") as f:
                config_dict: dict = yaml.safe_load(f)
                if config_dict:
                    for k, v in config_dict.items():
                        setattr(self.config, k, v)
        else:
            logger.info("No config file found, using default config")

        plugins_dir = self.config.plugins_dir
        for plugin_name in os.listdir(plugins_dir):
            plugin_dir = os.path.join(plugins_dir, plugin_name)
            if os.path.isdir(plugin_dir):
                config_file = os.path.join(plugin_dir, "config.yaml")
                if os.path.isfile(config_file):
                    with open(config_file) as f:
                        config_obj = yaml.safe_load(f)
                        self.config.plugins_config[plugin_name] = config_obj

        self.plugins: list[Plugin] = []
        self.actions_queue = asyncio.Queue()

        self.app = FastAPI()
        self.app.add_event_handler("startup", self.load_plugins)

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

    def load_plugins(self) -> list[Plugin]:
        enabled_plugins = list(map(lambda x: x.lower(), self.config.enabled_plugins))
        plugins_dir = self.config.plugins_dir
        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py"):
                module_name = f"{plugins_dir}.{filename[:-3]}"
                spec = importlib.util.spec_from_file_location(
                    module_name, os.path.join(plugins_dir, filename)
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            elif os.path.isdir(os.path.join(plugins_dir, filename)):
                module_name = f"{plugins_dir}.{filename}"
                module = importlib.import_module(module_name)
            else:
                continue
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, Plugin)
                    and obj is not Plugin
                    and obj.__name__.lower() in enabled_plugins
                ):
                    plugin_config = {
                        "queue": self.actions_queue,
                        "config": self.config.copy().dict(),
                    }
                    plugin_config = self.merge_dict(
                        plugin_config, self.config.plugins_config.get(filename, {})
                    )
                    plugin = obj(**plugin_config)

                    self.plugins.append(plugin)
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

    def merge_dict(self, dict1, dict2):
        for key in dict2:
            if key in dict1:
                if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                    self.merge_dict(dict1[key], dict2[key])
                else:
                    dict1[key] = dict2[key]
            else:
                dict1[key] = dict2[key]
        return dict1
