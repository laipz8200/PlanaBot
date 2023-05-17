from pydantic import BaseModel

from plana.actions.action import Action


class GetGroupMemberInfoAction(Action):
    action: str = "get_group_member_info"


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


def create_get_group_member_info_action(
    group_id: int, user_id: int
) -> GetGroupMemberInfoAction:
    return GetGroupMemberInfoAction(
        params=GetGroupMemberInfoParams(group_id=group_id, user_id=user_id).dict()
    )
