from pydantic import BaseModel

from plana.objects.action import Action


class GetLoginInfo(Action):
    action = "get_login_info"


class LoginInfo(BaseModel):
    nickname: str
    user_id: int
