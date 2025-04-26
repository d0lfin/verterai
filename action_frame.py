from typing import TypedDict, Optional


class ActionFrame(TypedDict):
    element: dict
    type: str
    data: Optional[str]