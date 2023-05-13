from pydantic import BaseModel
from plana.actions.base import Action
from plana.objects.messages.base import ArrayMessages


class SendPrivateMessageAction(Action):
    action: str = "send_private_msg"


class SendPrivateMessageParams(BaseModel):
    user_id: int
    group_id: int | None
    message: ArrayMessages
    auto_escape: bool = False
