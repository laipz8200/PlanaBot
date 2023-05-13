from plana.objects.messages.base import ArrayMessage
from plana.objects.send_group_msg import SendGroupMessageAction, SendGroupMessageParams


def create_send_group_msg_action(
    group_id: int, message: ArrayMessage | str, *args, **kwargs
) -> None:
    if isinstance(message, str):
        text = message
        message = ArrayMessage()
        message.add_text(text)
    action = SendGroupMessageAction(
        params=SendGroupMessageParams(
            group_id=group_id, message=message, *args, **kwargs
        )
    )
    return action
