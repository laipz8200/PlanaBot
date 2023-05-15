from pydantic import BaseModel

from plana.objects.action import Action


class GetGroupMemberInfoAction(Action):
    action = "get_group_member_info"


class GetGroupMemberInfoParams(BaseModel):
    group_id: int
    user_id: int
    no_cache: bool = False


class GroupMemberInfo(BaseModel):
    group_id: int
    user_id: int
    nickname: str
    card: str
    sex: str
    age: int
    # TODO: add more fields
