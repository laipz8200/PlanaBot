from plana.objects.actions.get_group_member_info import (
    GetGroupMemberInfoAction, GetGroupMemberInfoParams)


def create_get_group_member_info_action(
    group_id: int, user_id: int
) -> GetGroupMemberInfoAction:
    return GetGroupMemberInfoAction(
        params=GetGroupMemberInfoParams(group_id=group_id, user_id=user_id).dict()
    )
