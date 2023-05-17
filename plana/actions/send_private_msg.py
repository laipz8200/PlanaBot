from plana.objects.actions.send_private_msg import (SendPrivateMessageAction,
                                                    SendPrivateMessageParams)
from plana.objects.messages.array_messages import ArrayMessage


def create_send_private_msg_action(
    user_id: int,
    message: ArrayMessage | str,
    *args,
    **kwargs,
) -> SendPrivateMessageAction:
    if isinstance(message, str):
        text = message
        message = ArrayMessage()
        message.add_text(text)
    action = SendPrivateMessageAction(
        params=SendPrivateMessageParams(
            user_id=user_id, message=message, *args, **kwargs
        ).dict()
    )
    return action
