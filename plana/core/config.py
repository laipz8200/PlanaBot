from pydantic import BaseModel


class PlanaConfig(BaseModel):
    master_id: int = 10000
    allowed_groups: list[int] = []
    enabled_plugins: list[str] = ["echo", "bilibili"]
