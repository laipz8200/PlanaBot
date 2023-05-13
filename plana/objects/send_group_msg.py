from pydantic import BaseModel
from plana.actions.base import Action
from plana.objects.messages.base import ArrayMessages


class SendGroupMessageAction(Action):
    action: str = "send_group_msg"


class SendGroupMessageParams(BaseModel):
    group_id: int
    message: ArrayMessages
    auto_escape: bool = False
