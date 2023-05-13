from pydantic import BaseModel


class Action(BaseModel):
    action: str
    params: dict
    echo: str = ""
