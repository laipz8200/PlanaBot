from plana.objects.messages.base import ArrayMessages
from plana.objects.send_group_msg import SendGroupMessageAction, SendGroupMessageParams


def create_send_group_msg_action(
    group_id: int, messages: ArrayMessages | str, *args, **kwargs
) -> None:
    if isinstance(messages, str):
        text = messages
        messages = ArrayMessages()
        messages.add_text(text)
    action = SendGroupMessageAction(
        params=SendGroupMessageParams(
            group_id=group_id, message=messages, *args, **kwargs
        )
    )
    return action
