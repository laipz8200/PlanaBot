import asyncio
import copy
import importlib.util
import inspect
import logging
import os

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

        self.lock = asyncio.Lock()
        self.request_queue = asyncio.Queue()
        self.subscribers: dict[str, asyncio.Queue] = {}
        self.plugins: list[Plugin] = []
        self.response: dict[str, dict] = {"_version": {}}

        self._load_config(config, config_file_path)
        self._init_app()

    def run(self):
        uvicorn.run(
            self.app,
            host="127.0.0.1",
            port=8000,
            log_level=logging.CRITICAL,
            access_log=False,
        )

    async def _run_broadcast(self):
        asyncio.create_task(self._broadcast())

    async def _broadcast(self):
        while True:
            try:
                action = await self.request_queue.get()
                for subscriber in self.subscribers.values():
                    await subscriber.put(action)
            except Exception as e:
                logger.error(f"Failed to broadcast: {e}")

    async def _handle_event(self, post_type: str, event: dict):
        event["event"] = copy.deepcopy(event)

        if post_type in ["message", "message_sent"]:
            base_message = BaseMessage(**event)

            if base_message.message_type == "group":
                await self._handle_group_message_event(event)

            if base_message.message_type == "private":
                await self._handle_private_message_event(event)

    async def _handle_response(self, response: dict):
        status = response.get("status", "")
        if not status:
            logger.warning(f"[Response] status not found in {response}")
        if status == "failed":
            logger.error(f"[Response] action failed in {response}")
        echo = response.get("echo", "")
        if echo:
            async with self.lock:
                event: asyncio.Event = self.response[echo]["event"]
                self.response[echo]["response"] = response
                event.set()

    async def _handle_private_message_event(self, event: dict):
        private_message = PrivateMessage(**event)
        sender = private_message.sender
        logger.info(
            (
                f"[Private] "
                f"{sender.nickname}({sender.user_id}): "
                f"{private_message.message}"
            )
        )

        tasks = []
        for plugin in self.plugins:
            private_message = private_message.load_plugin(plugin)
            if (
                plugin.master_only
                and private_message.sender.user_id != self.config.master_id
            ):
                continue

            tasks.append(plugin.on_private(private_message))

            if plugin.prefix and private_message.starts_with(plugin.prefix):
                message = private_message.remove_prefix(plugin.prefix)
                tasks.append(plugin.on_private_prefix(message))

        await asyncio.gather(*tasks)

    async def _handle_group_message_event(self, event: dict):
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
                message = group_message.remove_prefix(plugin.prefix)
                tasks.append(plugin.on_group_prefix(message))

        await asyncio.gather(*tasks)

    def _init_plugins(self) -> list[Plugin]:
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
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(cls, Plugin)
                    and cls is not Plugin
                    and cls.__name__.lower() in enabled_plugins
                ):
                    plugin_config = {
                        "queue": self.request_queue,
                        "response": self.response,
                        "lock": self.lock,
                        "config": self.config.copy().dict(),
                    }
                    plugin_config = self._merge_dict(
                        plugin_config, self.config.plugins_config.get(filename, {})
                    )
                    plugin = cls(**plugin_config)
                    plugin.response = self.response

                    self.plugins.append(plugin)
        plugins_name = ", ".join([plugin.__class__.__name__ for plugin in self.plugins])
        logger.info(f"{len(self.plugins)} plugins Loaded: {plugins_name}")

    async def _ws_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        client_name = f"{websocket.client.host}:{websocket.client.port}"
        queue = asyncio.Queue()
        self.subscribers[client_name] = queue
        logger.info(f"Client {client_name} connected")

        consumer_task = asyncio.create_task(self._send_request(websocket, queue))
        try:
            async for data in websocket.iter_json():
                post_type = data.get("post_type", None)
                try:
                    if not post_type:
                        asyncio.create_task(self._handle_response(data))
                    else:
                        asyncio.create_task(self._handle_event(post_type, data))
                except Exception as e:
                    logger.error("=== Error Info ===")
                    logger.error(f"Event: {data}")
                    logger.error(f"Error: {e}")
                    logger.error("==================")
        except Exception:
            consumer_task.cancel()
            await consumer_task
        finally:
            await websocket.close()
            del self.subscribers[client_name]
            logger.info(f"Client {client_name} disconnected")

    async def _send_request(self, websocket: WebSocket, queue: asyncio.Queue):
        while True:
            try:
                action = await queue.get()
                await websocket.send_json(action.dict())
            except Exception as e:
                logger.error("=== Error Info ===")
                logger.error(f"Action: {action}")
                logger.error(f"Error: {e}")
                logger.error("==================")

    def _merge_dict(self, dict1, dict2):
        for key in dict2:
            if key in dict1:
                if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                    self._merge_dict(dict1[key], dict2[key])
                else:
                    dict1[key] = dict2[key]
            else:
                dict1[key] = dict2[key]
        return dict1

    def _print_ascii_art(self):
        logger.info("Thanks for using")
        logger.info("     ____  _        _    _   _    _")
        logger.info("    |  _ \| |      / \  | \ | |  / \\")
        logger.info("    | |_) | |     / _ \ |  \| | / _ \\")
        logger.info("    |  __/| |___ / ___ \| |\  |/ ___ \\")
        logger.info("    |_|   |_____/_/   \_\_| \_/_/   \_\\    - " + self.__version__)
        logger.info("")

    def _load_config(self, config: PlanaConfig | None, config_file_path: str):
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

    def _init_app(self):
        self.app = FastAPI()
        logging.getLogger("fastapi").setLevel(logging.CRITICAL)

        self.app.add_event_handler("startup", self._print_ascii_art)
        self.app.add_event_handler("startup", self._init_plugins)
        self.app.add_event_handler("startup", self._run_broadcast)
        self.app.add_websocket_route("/ws", self._ws_endpoint)
