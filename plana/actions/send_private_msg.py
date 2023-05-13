from plana.objects.messages.base import ArrayMessages
from plana.objects.send_private_msg import (
    SendPrivateMessageAction,
    SendPrivateMessageParams,
)


def send_private_msg(
    user_id: int,
    message: ArrayMessages | str,
    *args,
    **kwargs,
) -> None:
    if isinstance(message, str):
        text = message
        message = ArrayMessages()
        message.add_text(text)
    action = SendPrivateMessageAction(
        params=SendPrivateMessageParams(
            user_id=user_id, message=message, *args, **kwargs
        )
    )
    return action
