import asyncio
import importlib.util
import inspect
import logging
import os

import uvicorn
import yaml
from fastapi import FastAPI, WebSocket
from loguru import logger

from plana.actions import Action
from plana.core.config import PlanaConfig
from plana.core.plugin import Plugin
from plana.messages import BaseMessage, GroupMessage, PrivateMessage


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

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        return uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level=logging.CRITICAL,
            access_log=False,
        )

    async def _run_broadcast(self):
        asyncio.create_task(self._broadcast())

    async def _broadcast(self):
        while True:
            try:
                action = await self.request_queue.get()
                tasks = [
                    subscriber.put(action) for subscriber in self.subscribers.values()
                ]
                asyncio.gather(*tasks)
            except Exception as e:
                logger.error(f"Failed to broadcast: {e}")

    async def _handle_event(self, post_type: str, event: dict):
        if post_type in ["message", "message_sent"]:
            base_message = BaseMessage(**event)

            if base_message.message_type == "group":
                asyncio.create_task(self._handle_group_message_event(event))

            if base_message.message_type == "private":
                asyncio.create_task(self._handle_private_message_event(event))

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
        message = PrivateMessage(**event)
        logger.info(message)
        if (
            not self.config.reply_private_message
            and message.user_id != self.config.master_id
        ):
            logger.info(f"Ignoring private message from {message.user_id}")
            return

        plugins = filter(
            lambda plugin: (not plugin.master_only)
            or (plugin.master_only and message.sender.user_id == self.config.master_id),
            self.plugins,
        )
        plugins = list(plugins)
        tasks = [plugin.handle_on_private(message) for plugin in plugins]

        plugins = filter(
            lambda plugin: plugin.prefix and message.on_prefix(plugin.prefix),
            plugins,
        )
        tasks += [plugin.handle_on_private_prefix(message) for plugin in plugins]
        asyncio.gather(*tasks)

    async def _handle_group_message_event(self, event: dict):
        message = GroupMessage(**event)
        logger.info(message)

        plugins = filter(
            lambda plugin: (message.group_id in plugin.config.allowed_groups)
            and (
                (not plugin.master_only)
                or (
                    plugin.master_only
                    and message.sender.user_id == self.config.master_id
                )
            ),
            self.plugins,
        )
        plugins = list(plugins)
        tasks = [plugin.handle_on_group(message) for plugin in plugins]

        plugins = filter(
            lambda plugin: plugin.prefix and message.on_prefix(plugin.prefix),
            plugins,
        )
        tasks += [plugin.handle_on_group_prefix(message) for plugin in plugins]
        asyncio.gather(*tasks)

    def _init_plugins(self) -> None:
        enabled_plugins = list(map(lambda x: x.lower(), self.config.enabled_plugins))
        plugins_dir = self.config.plugins_dir
        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py"):
                module_name = f"{plugins_dir}.{filename[:-3]}"
                spec = importlib.util.spec_from_file_location(
                    module_name, os.path.join(plugins_dir, filename)
                )
                if not spec:
                    continue
                module = importlib.util.module_from_spec(spec)
                loader = spec.loader
                if not loader:
                    continue
                loader.exec_module(module)
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
                    try:
                        plugin = cls(**plugin_config)
                    except Exception as e:
                        logger.warning(f"Failed to load plugin: {cls.__name__}: {e}")
                        continue
                    # FIXME: not sure if this is the best way to do this
                    plugin.response = self.response

                    self.plugins.append(plugin)
        plugins_name = ", ".join([plugin.__class__.__name__ for plugin in self.plugins])
        logger.info(f"{len(self.plugins)} plugins Loaded: {plugins_name}")

    async def _ws_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        client = websocket.client
        if not client:
            return await websocket.close()
        client_name = f"{client.host}:{client.port}"
        queue = asyncio.Queue()
        self.subscribers[client_name] = queue
        logger.info(f"Client {client_name} connected")

        asyncio.create_task(self._send_request(websocket, queue))
        async for data in websocket.iter_json():
            post_type = data.get("post_type", None)
            if post_type:
                asyncio.create_task(self._handle_event(post_type, data))
            else:
                asyncio.create_task(self._handle_response(data))
        await websocket.close()
        del self.subscribers[client_name]
        logger.info(f"Client {client_name} disconnected")

    async def _send_request(self, websocket: WebSocket, queue: asyncio.Queue):
        while True:
            action: Action = await queue.get()
            await websocket.send_json(action.dict())
            await asyncio.sleep(2)

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
        logger.info("    |  _ \\| |      / \\  | \\ | |  / \\")
        logger.info("    | |_) | |     / _ \\ |  \\| | / _ \\")
        logger.info("    |  __/| |___ / ___ \\| |\\  |/ ___ \\")
        logger.info("    |_|   |_____/_/   \\_\\_| \\_/_/   \\_\\")
        logger.info("")
        logger.info("                                  - version: " + self.__version__)

    def _load_config(self, config: PlanaConfig | None, config_file_path: str):
        if not config:
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
                        self.config.plugins_config[plugin_name] = (
                            config_obj if config_obj else {}
                        )

    def _init_app(self):
        self.app = FastAPI()
        logging.getLogger("fastapi").setLevel(logging.CRITICAL)

        self.app.add_event_handler("startup", self._print_ascii_art)
        self.app.add_event_handler("startup", self._init_plugins)
        self.app.add_event_handler("startup", self._run_broadcast)
        self.app.add_websocket_route("/ws", self._ws_endpoint)
