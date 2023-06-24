import importlib.util
import inspect
import logging
import os

import uvicorn
from fastapi import FastAPI, WebSocket
from loguru import logger

from plana.events import Event, GroupMessage, Message


class Application:
    def handle(self, e: Event) -> None:
        pass


class EventHandler:
    def __init__(self) -> None:
        self.subscribers: list[Application] = []

    def append_to_stream(self, e: Event) -> None:
        for subscriber in self.subscribers:
            subscriber.handle(e)


class Plugin(Application):
    def __init__(self, bot: "Plana"):
        self._bot = bot
        self._event_handler = self._bot.event_handler
        self._event_handler.subscribers.append(self)

    def handle(self, e: Event) -> None:
        if not isinstance(e, dict):
            return
        pt = e.get("post_type")
        match pt:
            case "message":
                msg = Message(**e.source)
                msg.source = e
                self._handle_message(msg)
            case _:
                return

    def _handle_message(self, msg: Message) -> None:
        match msg.message_type:
            case "group":
                group_msg = GroupMessage(**msg.source)
                group_msg.source = msg.source
                self._handle_group_message(group_msg)
            case "private":
                return
            case _:
                return

    def _handle_group_message(self, msg: GroupMessage) -> None:
        if msg.sub_type != "normal":
            return
        self.on_group(self._bot, msg)

    def on_group(self, bot: "Plana", msg: GroupMessage) -> None:
        ...


class Plana:
    def __init__(
        self,
        bot_id: int,
        master: int,
        event_handler: EventHandler | None = None,
    ) -> None:
        self.__version__ = "v0.2.0"
        self._id = bot_id
        self._master = master
        self._event_handler = event_handler or EventHandler()
        self._plugins: list[Plugin] = []

        self._init_app()

    @property
    def id(self) -> int:
        return self._id

    @property
    def master(self) -> int:
        return self._master

    @property
    def event_handler(self) -> EventHandler:
        return self._event_handler

    def run(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        return uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level=logging.CRITICAL,
            access_log=False,
        )

    def _load_plugins(self) -> None:
        dst = "plugins"
        for file in os.listdir(dst):
            if file.endswith(".py"):
                module = f"{dst}.{file[:-3]}"
                spec = importlib.util.spec_from_file_location(
                    module, os.path.join(dst, file)
                )
                if not spec:
                    continue
                module = importlib.util.module_from_spec(spec)
                loader = spec.loader
                if not loader:
                    continue
                loader.exec_module(module)
            elif os.path.isdir(os.path.join(dst, file)):
                module = f"{dst}.{file}"
                module = importlib.import_module(module)
            else:
                continue
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, Plugin) and cls is not Plugin:
                    try:
                        plugin = cls(self)
                        self._plugins.append(plugin)
                    except Exception as e:
                        logger.warning(f"Failed to load plugin: {cls.__name__}: {e}")
                        continue
        name_list = ", ".join([plugin.__class__.__name__ for plugin in self._plugins])
        logger.info(f"{len(self._plugins)} plugins Loaded: {name_list}")

    async def _ws_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        client = websocket.client
        if not client:
            return await websocket.close()
        client_name = f"{client.host}:{client.port}"
        logger.info(f"Client {client_name} connected")

        async for data in websocket.iter_json():
            event = Event(**data)
            event.source = data
            self._event_handler.append_to_stream(event)
        await websocket.close()
        logger.info(f"Client {client_name} disconnected")

    def _welcome(self):
        logger.info("Thanks for using")
        logger.info("     ____  _        _    _   _    _")
        logger.info("    |  _ \\| |      / \\  | \\ | |  / \\")
        logger.info("    | |_) | |     / _ \\ |  \\| | / _ \\")
        logger.info("    |  __/| |___ / ___ \\| |\\  |/ ___ \\")
        logger.info("    |_|   |_____/_/   \\_\\_| \\_/_/   \\_\\")
        logger.info("")
        logger.info("                                  - version: " + self.__version__)

    def _init_app(self):
        self.app = FastAPI()
        logging.getLogger("fastapi").setLevel(logging.CRITICAL)

        self.app.add_event_handler("startup", self._welcome)
        self.app.add_event_handler("startup", self._load_plugins)
        self.app.add_websocket_route("/ws", self._ws_endpoint)
