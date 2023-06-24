from typing import Any

from pydantic import BaseModel


class Event(BaseModel):
    time: int
    self_id: int
    post_type: str
    source: dict = {}


class Sender(BaseModel):
    user_id: int
    nickname: str
    sex: str
    age: int


class GroupSender(Sender):
    card: str
    area: str
    level: str
    role: str
    title: str


class Message(Event):
    message_type: str
    sub_type: str
    message_id: int
    user_id: int
    message: Any
    raw_message: str
    font: int
    sender: Sender


class GroupMessage(Message):
    group_id: int
    sender: GroupSender
