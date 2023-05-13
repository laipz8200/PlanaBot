from plana.objects.messages.base import ArrayMessages
from plana.objects.send_group_msg import SendGroupMessageParams


def send_group_msg(
    group_id: int, message: ArrayMessages | str, *args, **kwargs
) -> None:
    if isinstance(message, str):
        text = message
        message = ArrayMessages()
        message.add_text(text)
    action = SendGroupMessageParams(
        params=SendGroupMessageParams(
            group_id=group_id, message=message, *args, **kwargs
        )
    )
    return action
