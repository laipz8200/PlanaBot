from pydantic import BaseModel

from plana.objects.action import Action
from plana.objects.messages.array_messages import ArrayMessage


class SendPrivateMessageAction(Action):
    action: str = "send_private_msg"


class SendPrivateMessageParams(BaseModel):
    user_id: int
    group_id: int | None
    message: ArrayMessage
    auto_escape: bool = False
