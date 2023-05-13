from pydantic import BaseModel


class Sender(BaseModel):
    user_id: int | None
    nickname: str | None
    sex: str | None
    age: int | None


class Anonymous(BaseModel):
    id: int
    name: str
    flag: str
