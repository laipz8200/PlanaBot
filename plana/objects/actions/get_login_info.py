from pydantic import BaseModel

from plana.objects.actions.action import Action


class GetLoginInfo(Action):
    action: str = "get_login_info"


class LoginInfo(BaseModel):
    nickname: str
    user_id: int
