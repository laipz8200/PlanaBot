from pydantic import BaseModel

from plana.actions.action import Action


class QuickOperationAction(Action):
    action: str = ".handle_quick_operation"


class QuickOperationParams(BaseModel):
    context: dict
    operation: dict


def create_quick_operation_action(
    context: dict, operation: dict
) -> QuickOperationAction:
    return QuickOperationAction(
        params=QuickOperationParams(context=context, operation=operation).dict()
    )
