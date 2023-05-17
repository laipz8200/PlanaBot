from copy import deepcopy
from typing import Self


class Message(list):
    def plain_text(self) -> str:
        return ", ".join(
            [m["data"]["text"] for m in filter(lambda m: m["type"] == "text", self)]
        ).strip()

    def add_text(self, text: str) -> None:
        self.append({"type": "text", "data": {"text": text}})

    def on_prefix(self, prefix: str) -> bool:
        if (
            len(self) > 0
            and self[0]["type"] == "text"
            and self[0]["data"]["text"].startswith(prefix)
        ):
            return True
        return False

    def remove_prefix(self, prefix: str) -> Self:
        obj = deepcopy(self)
        if self.on_prefix(prefix):
            obj[0]["data"]["text"] = obj[0]["data"]["text"][len(prefix) :]
        return obj
