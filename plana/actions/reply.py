from pydantic import BaseModel


class Reply(BaseModel):
    type: str = "reply"
    data: dict


def create_reply(message_id: int) -> Reply:
    return Reply(
        data={
            "id": message_id,
        }
    )
