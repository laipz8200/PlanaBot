from pydantic import BaseModel

from plana.objects.actions.action import Action
from plana.objects.messages.array_messages import ArrayMessage


class SendGroupMessageAction(Action):
    action: str = "send_group_msg"


class SendGroupMessageParams(BaseModel):
    group_id: int
    message: ArrayMessage
    auto_escape: bool = False
