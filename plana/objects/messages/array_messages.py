from copy import deepcopy
from typing import Self


class ArrayMessage(list):
    def plain_text(self) -> str:
        return " ".join(
            [
                m["data"]["text"]
                for m in filter(lambda m: m.get("type", "") == "text", self)
            ]
        ).strip()

    def add_text(self, text: str):
        self.append({"type": "text", "data": {"text": text}})

    def starts_with(self, text: str) -> bool:
        if (
            len(self) > 0
            and self[0]["type"] == "text"
            and self[0]["data"]["text"].startswith(text)
        ):
            return True
        return False

    def remove_prefix(self, prefix: str) -> Self:
        obj = deepcopy(self)
        if self.starts_with(prefix):
            obj[0]["data"]["text"] = obj[0]["data"]["text"][len(prefix) :]
        return obj
