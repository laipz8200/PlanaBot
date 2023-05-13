from pydantic import BaseModel


class BaseNotice(BaseModel):
    notice_type: str
