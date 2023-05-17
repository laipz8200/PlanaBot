from pydantic import BaseModel

from plana.actions.action import Action
from plana.messages import Message


class SendPrivateMessageAction(Action):
    action: str = "send_private_msg"


class SendPrivateMessageParams(BaseModel):
    user_id: int
    group_id: int | None
    message: Message
    auto_escape: bool = False


def create_send_private_msg_action(
    user_id: int,
    message: Message | str,
    *args,
    **kwargs,
) -> SendPrivateMessageAction:
    if isinstance(message, str):
        text = message
        message = Message()
        message.add_text(text)
    action = SendPrivateMessageAction(
        params=SendPrivateMessageParams(
            user_id=user_id, message=message, *args, **kwargs
        ).dict()
    )
    return action
