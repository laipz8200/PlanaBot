from plana.objects.messages.base import ArrayMessages
from plana.objects.send_private_msg import (
    SendPrivateMessageAction,
    SendPrivateMessageParams,
)


def create_send_private_msg_action(
    user_id: int,
    messages: ArrayMessages | str,
    *args,
    **kwargs,
) -> None:
    if isinstance(messages, str):
        text = messages
        messages = ArrayMessages()
        messages.add_text(text)
    action = SendPrivateMessageAction(
        params=SendPrivateMessageParams(
            user_id=user_id, message=messages, *args, **kwargs
        )
    )
    return action
