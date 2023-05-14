from pydantic import BaseModel

from plana.objects.base import Action


class GetLoginInfo(Action):
    action = "get_login_info"
    echo: str


class LoginInfo(BaseModel):
    nickname: str
    user_id: int
