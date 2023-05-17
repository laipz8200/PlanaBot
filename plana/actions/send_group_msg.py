from plana.objects.actions.send_group_msg import (SendGroupMessageAction,
                                                  SendGroupMessageParams)
from plana.objects.messages.array_messages import ArrayMessage


def create_send_group_msg_action(
    group_id: int, message: ArrayMessage | str, *args, **kwargs
) -> SendGroupMessageAction:
    if isinstance(message, str):
        text = message
        message = ArrayMessage()
        message.add_text(text)
    action = SendGroupMessageAction(
        params=SendGroupMessageParams(
            group_id=group_id, message=message, *args, **kwargs
        ).dict()
    )
    return action
