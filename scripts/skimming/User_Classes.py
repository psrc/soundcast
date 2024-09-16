from dataclasses import dataclass
from typing import List


@dataclass
class UserClass:
    name: str
    description: str
    vot: int
    mode: str
    toll: str
    time: str
    distance: str


@dataclass
class UserClasses:
    users: List[UserClass]


def create_user_class_dict(user_classes):
    user_class_dict = {}
    for user_type in user_classes.keys():
        record_list = []
        for record in user_classes[user_type]:
            user = UserClass(
                record.get("Name"),
                record.get("Description"),
                record.get("Value of Time"),
                record.get("Mode"),
                record.get("Toll"),
                record.get("Time"),
                record.get("Distance"),
            )
            record_list.append(user)
        users = UserClasses(record_list)
        user_class_dict[user_type] = users
    return user_class_dict
