from pydantic import BaseModel


class PlanaConfig(BaseModel):
    master_id: int = 10000
    allowed_groups: list[int] = []
    enabled_plugins: list[str] = ["echo", "bilibili"]
    plugins_dir: str = "plugins"
    plugins_config: dict = {}
    reply_private_message: bool = False
