from plana.objects.messages.base import ArrayMessage
from plana.objects.send_private_msg import (
    SendPrivateMessageAction,
    SendPrivateMessageParams,
)


def create_send_private_msg_action(
    user_id: int,
    message: ArrayMessage | str,
    *args,
    **kwargs,
) -> None:
    if isinstance(message, str):
        text = message
        message = ArrayMessage()
        message.add_text(text)
    action = SendPrivateMessageAction(
        params=SendPrivateMessageParams(
            user_id=user_id, message=message, *args, **kwargs
        )
    )
    return action
