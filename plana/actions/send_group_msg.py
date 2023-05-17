from pydantic import BaseModel

from plana.actions.action import Action
from plana.messages import Message


class SendGroupMessageAction(Action):
    action: str = "send_group_msg"


class SendGroupMessageParams(BaseModel):
    group_id: int
    message: Message
    auto_escape: bool = False


def create_send_group_msg_action(
    group_id: int, message: Message | str, *args, **kwargs
) -> SendGroupMessageAction:
    if isinstance(message, str):
        text = message
        message = Message()
        message.add_text(text)
    action = SendGroupMessageAction(
        params=SendGroupMessageParams(
            group_id=group_id, message=message, *args, **kwargs
        ).dict()
    )
    return action
