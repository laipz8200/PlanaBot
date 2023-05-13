from pydantic import BaseModel


class ReplyData(BaseModel):
    id: int


class Reply(BaseModel):
    type: str = "reply"
    data: ReplyData


def create_reply(message_id: int) -> Reply:
    return Reply.parse_obj(
        {
            "data": {
                "id": message_id,
            }
        }
    )
