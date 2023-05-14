import uuid

from plana.objects.get_login_info import GetLoginInfo


def create_get_login_info_action() -> GetLoginInfo:
    action = GetLoginInfo(echo=str(uuid.uuid4()))
    return action
